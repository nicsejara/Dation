-- T2 metadata preparation. No object upload, publishing RPC or Storage configuration.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';
ALTER TABLE public.decision_runs
 ADD COLUMN result_package_version integer,
 ADD COLUMN assembler_version text,
 ADD COLUMN artifact_manifest_hash text CHECK(artifact_manifest_hash ~ '^[0-9a-f]{64}$'),
 ADD COLUMN core_fingerprint text CHECK(core_fingerprint ~ '^[0-9a-f]{64}$'),
 ADD CONSTRAINT ultimate_run_result_identity UNIQUE(workspace_id,id,result_fingerprint),
 ADD CONSTRAINT ultimate_run_publication CHECK(CASE WHEN workflow_version=1 THEN
   num_nonnulls(result_package_version,assembler_version,artifact_manifest_hash,core_fingerprint)=0
  ELSE (result_package_version IS NULL OR result_package_version=1) AND
   (status<>'completed' OR (num_nonnulls(result_package_version,assembler_version,artifact_manifest_hash,core_fingerprint,result_fingerprint)=5
     AND result_json#>>'{fingerprints,result_fingerprint}' IS NOT DISTINCT FROM result_fingerprint
     AND result_json#>>'{fingerprints,core_result_fingerprint}' IS NOT DISTINCT FROM core_fingerprint
     AND result_json->>'assembler_version' IS NOT DISTINCT FROM assembler_version)) END);

CREATE TABLE public.decision_result_artifacts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 workspace_id uuid NOT NULL,
 run_id uuid NOT NULL,
 kind text NOT NULL CHECK(kind IN('CORE','EVIDENCE','ENTITY_EVIDENCE','DETAIL_DATASET','VISUAL','EXPORT_ROWS','AI_BASE','ALTERNATIVE_PLAN')),
 part_key text NOT NULL CHECK(part_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$'),
 artifact_schema text NOT NULL CHECK(artifact_schema IN('transport_trip_v1','demand_resolution_v1','resource_usage_v1',
  'day_schedule_trip_v1','resource_timeline_v1','service_analysis_v1','entity_evidence_v1','reason_emission_v1',
  'export_rows_v1','decision_context_v1','engine_core_v1','engine_evidence_v1','sankey_projection_v1','day_gantt_projection_v1')),
 schema_version integer NOT NULL CHECK(schema_version=1),
 content_sha256 text NOT NULL CHECK(content_sha256 ~ '^[0-9a-f]{64}$'),
 size_bytes bigint NOT NULL CHECK(size_bytes>=0),
 media_type text NOT NULL CHECK(media_type IN('application/json','application/x-ndjson')),
 storage_bucket text NOT NULL CHECK(storage_bucket ~ '^[a-z0-9][a-z0-9-]{0,62}$'),
 storage_path text NOT NULL,
 assembler_version text NOT NULL CHECK(assembler_version ~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$'),
 core_fingerprint text NOT NULL CHECK(core_fingerprint ~ '^[0-9a-f]{64}$'),
 result_fingerprint text CHECK(result_fingerprint ~ '^[0-9a-f]{64}$'),
 publication_state text NOT NULL DEFAULT 'PREPARED' CHECK(publication_state IN('PREPARED','READY')),
 lookup_keys text[] NOT NULL DEFAULT '{}' CHECK(cardinality(lookup_keys)<=100 AND array_position(lookup_keys,NULL) IS NULL),
 producer_lease_token uuid NOT NULL,
 producer_generation bigint NOT NULL CHECK(producer_generation>0),
 producer_metadata jsonb NOT NULL CHECK(jsonb_typeof(producer_metadata)='object' AND octet_length(producer_metadata::text)<=16384),
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(workspace_id,id), UNIQUE(workspace_id,run_id,kind,part_key,content_sha256),
 UNIQUE(storage_bucket,storage_path),
 FOREIGN KEY(workspace_id,run_id) REFERENCES public.decision_runs(workspace_id,id) ON DELETE RESTRICT,
 CONSTRAINT ultimate_artifact_published_run FOREIGN KEY(workspace_id,run_id,result_fingerprint)
  REFERENCES public.decision_runs(workspace_id,id,result_fingerprint) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
 CHECK((publication_state='PREPARED' AND result_fingerprint IS NULL)
   OR (publication_state='READY' AND result_fingerprint IS NOT NULL)),
 CHECK(storage_path=workspace_id::text||'/runs/'||run_id::text||'/'||lower(kind)||'/'||part_key||'/'||content_sha256||
   CASE WHEN media_type='application/json' THEN '.json' ELSE '.jsonl' END)
);
CREATE INDEX decision_result_artifacts_lookup ON public.decision_result_artifacts(workspace_id,run_id,kind,part_key);
CREATE INDEX decision_result_artifacts_binding ON public.decision_result_artifacts(workspace_id,run_id,result_fingerprint);
CREATE INDEX decision_result_artifacts_entities ON public.decision_result_artifacts USING gin(lookup_keys);
ALTER TABLE public.decision_result_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.decision_result_artifacts FORCE ROW LEVEL SECURITY;
-- Storage locators remain server-only; membership-checked retrieval is T8.
REVOKE ALL ON public.decision_result_artifacts FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT ON public.decision_result_artifacts TO service_role;

CREATE FUNCTION dation_private.ultimate_artifact_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE key text;
BEGIN
 IF TG_OP<>'INSERT' THEN
  IF OLD.publication_state='READY' THEN RAISE EXCEPTION 'READY artifact is immutable' USING ERRCODE='22023'; END IF;
  IF TG_OP='DELETE' THEN RETURN OLD; END IF;
  IF (to_jsonb(NEW)-'publication_state'-'result_fingerprint') IS DISTINCT FROM
     (to_jsonb(OLD)-'publication_state'-'result_fingerprint') THEN
   RAISE EXCEPTION 'Prepared artifact identity is immutable' USING ERRCODE='22023'; END IF;
 END IF;
 FOREACH key IN ARRAY NEW.lookup_keys LOOP
  IF key !~ '^(ORDER|TRIP|RESOURCE|ALTERNATIVE|EXCEPTION)/[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$' THEN
   RAISE EXCEPTION 'Invalid entity lookup key' USING ERRCODE='22023'; END IF;
 END LOOP;
 IF NOT EXISTS(SELECT 1 FROM public.decision_runs WHERE workspace_id=NEW.workspace_id AND id=NEW.run_id AND workflow_version=2) THEN
  RAISE EXCEPTION 'Artifacts require an Ultimate Run' USING ERRCODE='22023'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER ultimate_artifact_identity BEFORE INSERT OR UPDATE OR DELETE ON public.decision_result_artifacts
 FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_artifact_guard();

-- Deferred so a future publisher can bind metadata and the package in one transaction.
-- This proves the metadata/package binding, not remote bytes or a worker lease fence (T8).
CREATE FUNCTION dation_private.ultimate_artifact_ready() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE a public.decision_result_artifacts; r public.decision_runs; descriptor jsonb;
BEGIN
 SELECT * INTO a FROM public.decision_result_artifacts WHERE id=NEW.id;
 IF NOT FOUND OR a.publication_state<>'READY' THEN RETURN NULL; END IF;
 SELECT * INTO r FROM public.decision_runs WHERE workspace_id=a.workspace_id AND id=a.run_id;
 descriptor=jsonb_build_object('artifact_id',a.id,'workspace_id',a.workspace_id,'run_id',a.run_id,
  'kind',a.kind,'part_key',a.part_key,'artifact_schema',a.artifact_schema,'schema_version',a.schema_version,
  'content_sha256',a.content_sha256,'size_bytes',a.size_bytes,'media_type',a.media_type,
  'core_fingerprint',a.core_fingerprint,'assembler_version',a.assembler_version);
 IF r.status<>'completed' OR r.result_package_version IS DISTINCT FROM 1
  OR r.result_fingerprint IS DISTINCT FROM a.result_fingerprint OR r.core_fingerprint IS DISTINCT FROM a.core_fingerprint
  OR r.assembler_version IS DISTINCT FROM a.assembler_version OR r.artifact_manifest_hash IS NULL
  OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(coalesce(r.result_json#>'{artifact_manifest,artifacts}','[]')) item
    WHERE item @> descriptor) THEN
  RAISE EXCEPTION 'READY artifact requires its exact published Run/manifest binding' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END; $$;
CREATE CONSTRAINT TRIGGER ultimate_artifact_ready AFTER INSERT OR UPDATE ON public.decision_result_artifacts
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_artifact_ready();

CREATE FUNCTION dation_private.ultimate_publication_identity() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF OLD.status IN('completed','error') AND ROW(NEW.result_package_version,NEW.assembler_version,NEW.artifact_manifest_hash,NEW.core_fingerprint)
 IS DISTINCT FROM ROW(OLD.result_package_version,OLD.assembler_version,OLD.artifact_manifest_hash,OLD.core_fingerprint) THEN
  RAISE EXCEPTION 'Terminal publication metadata is immutable' USING ERRCODE='22023'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER ultimate_publication_identity BEFORE UPDATE ON public.decision_runs
 FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_publication_identity();

ALTER TABLE public.decision_interpretation_sources
 ADD COLUMN provenance_version integer,
 ADD COLUMN result_fingerprint text CHECK(result_fingerprint ~ '^[0-9a-f]{64}$'),
 ADD COLUMN decision_context_schema text,
 ADD COLUMN decision_context_hash text CHECK(decision_context_hash ~ '^[0-9a-f]{64}$'),
 ADD COLUMN mode text,
 ADD COLUMN selected_entity jsonb,
 ADD COLUMN evidence_refs jsonb,
 ADD CONSTRAINT ultimate_interpretation_provenance CHECK(CASE WHEN provenance_version IS NULL THEN
   num_nonnulls(result_fingerprint,decision_context_schema,decision_context_hash,mode,selected_entity,evidence_refs)=0
  ELSE provenance_version=2 AND num_nonnulls(result_fingerprint,decision_context_schema,decision_context_hash,mode,evidence_refs)=5
   AND decision_context_schema='decision_context_v1' AND mode IN('EXPLAIN','EXPLORE','COMPARE','REVIEW')
   AND jsonb_typeof(evidence_refs)='array' AND octet_length(evidence_refs::text)<=51200
   AND (selected_entity IS NULL OR (jsonb_typeof(selected_entity)='object' AND
     selected_entity ?& ARRAY['type','id'] AND selected_entity-'type'-'id'='{}'::jsonb AND
     jsonb_typeof(selected_entity->'type')='string' AND jsonb_typeof(selected_entity->'id')='string' AND
     selected_entity->>'type' IN('CASE','TRIP','ORDER','RESOURCE','ALTERNATIVE') AND
     selected_entity->>'id' ~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')) END),
 ADD CONSTRAINT ultimate_interpretation_result FOREIGN KEY(workspace_id,run_id,result_fingerprint)
  REFERENCES public.decision_runs(workspace_id,id,result_fingerprint) ON DELETE RESTRICT;
CREATE INDEX ultimate_interpretation_context ON public.decision_interpretation_sources(workspace_id,run_id,result_fingerprint,decision_context_hash)
 WHERE provenance_version IS NOT NULL;

CREATE FUNCTION dation_private.ultimate_interpretation_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE ref jsonb;
BEGIN
 IF TG_OP='UPDATE' THEN
  IF NEW IS DISTINCT FROM OLD THEN RAISE EXCEPTION 'Interpretation provenance is immutable' USING ERRCODE='22023'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.provenance_version IS NOT NULL THEN
  IF NOT EXISTS(SELECT 1 FROM public.decision_runs WHERE workspace_id=NEW.workspace_id AND id=NEW.run_id
    AND result_fingerprint=NEW.result_fingerprint AND workflow_version=2 AND status='completed' AND result_package_version=1) THEN
   RAISE EXCEPTION 'Interpretation requires the published Ultimate result' USING ERRCODE='22023'; END IF;
  FOR ref IN SELECT value FROM jsonb_array_elements(NEW.evidence_refs) LOOP
   IF NOT EXISTS(SELECT 1 FROM public.decision_result_artifacts WHERE workspace_id=NEW.workspace_id AND run_id=NEW.run_id
     AND result_fingerprint=NEW.result_fingerprint AND publication_state='READY'
     AND id::text=ref->>'artifact_id' AND content_sha256=ref->>'content_sha256') THEN
    RAISE EXCEPTION 'Interpretation evidence must belong to the same published Run' USING ERRCODE='22023'; END IF;
  END LOOP;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER ultimate_interpretation_guard BEFORE INSERT OR UPDATE ON public.decision_interpretation_sources
 FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_interpretation_guard();
REVOKE ALL ON FUNCTION dation_private.ultimate_artifact_guard(),dation_private.ultimate_artifact_ready(),
 dation_private.ultimate_publication_identity(),dation_private.ultimate_interpretation_guard()
 FROM PUBLIC,anon,authenticated,service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
