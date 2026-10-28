-- T8: disabled-by-default admission and fenced publication. Sandbox upgrade only.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';
ALTER TABLE dation_private.platform_release ADD COLUMN ultimate_admissions_enabled boolean NOT NULL DEFAULT false;

CREATE FUNCTION dation_private.t8_canonical(v jsonb) RETURNS text
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE answer text;
BEGIN
 IF jsonb_typeof(v)='object' THEN
  SELECT '{'||coalesce(string_agg(to_json(key)::text||':'||dation_private.t8_canonical(value),',' ORDER BY key COLLATE "C"),'')||'}' INTO answer FROM jsonb_each(v);
 ELSIF jsonb_typeof(v)='array' THEN
  SELECT '['||coalesce(string_agg(dation_private.t8_canonical(value),',' ORDER BY ord),'')||']' INTO answer FROM jsonb_array_elements(v) WITH ORDINALITY x(value,ord);
 ELSE answer=v::text; END IF;
 RETURN answer;
END; $$;
CREATE FUNCTION dation_private.t8_hash(kind text,v jsonb) RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT encode(sha256(convert_to(dation_private.t8_canonical(jsonb_build_object('canonical_version','DATION_CANONICAL_V1','kind',kind,'value',v)),'UTF8')),'hex');
$$;
CREATE FUNCTION dation_private.t8_package_hash(v jsonb) RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE m jsonb;
BEGIN
 SELECT coalesce(jsonb_agg(a ORDER BY a->>'kind',a->>'part_key',a->>'artifact_id'),'[]') INTO m FROM jsonb_array_elements(v#>'{artifact_manifest,artifacts}') a;
 v=jsonb_set(v,'{fingerprints}',(v->'fingerprints')-'result_fingerprint');
 v=jsonb_set(v,'{artifact_manifest,artifacts}',m);
 RETURN dation_private.t8_hash('RESULT_PACKAGE',v);
END; $$;
CREATE FUNCTION dation_private.t8_policy_projection(p jsonb) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
BEGIN
 p=p-'override_reason';
 p=jsonb_set(p,'{guardrails}',coalesce((SELECT jsonb_agg(x ORDER BY x->>'kind') FROM jsonb_array_elements(p->'guardrails') x),'[]'));
 RETURN jsonb_set(p,'{preferences}',coalesce((SELECT jsonb_agg(x ORDER BY x->>'kind') FROM jsonb_array_elements(p->'preferences') x),'[]'));
END; $$;
CREATE FUNCTION dation_private.t8_input_hash(c jsonb) RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
BEGIN
 c=c-'case_name'-'display_metadata';
 c=jsonb_set(c,'{case_policy}',dation_private.t8_policy_projection(c->'case_policy'));
 c=jsonb_set(c,'{node_policy}',dation_private.t8_policy_projection(c->'node_policy'));
 c=jsonb_set(c,'{read_set}',(SELECT jsonb_agg(x ORDER BY x->>'slot') FROM jsonb_array_elements(c->'read_set') x));
 c=jsonb_set(c,'{active_dimensions}',(SELECT jsonb_agg(x ORDER BY x) FROM jsonb_array_elements(c->'active_dimensions') x));
 RETURN dation_private.t8_hash('INPUT_CONTEXT',jsonb_build_object('context',c,'runtime_identity',jsonb_build_object(
  'engine_name','transport_plan','engine_version','2.0.0','runtime_profile','transport_plan_v1','result_schema','transport_plan_v1','result_schema_version',1),
  'transit_model_version','DATION_TRANSIT_V1','upstream',NULL));
END; $$;

CREATE TABLE dation_private.ultimate_run_publications (
 workspace_id uuid NOT NULL,run_id uuid PRIMARY KEY,package jsonb NOT NULL,
 result_fingerprint text NOT NULL CHECK(result_fingerprint ~ '^[0-9a-f]{64}$'),
 manifest_hash text NOT NULL CHECK(manifest_hash ~ '^[0-9a-f]{64}$'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(workspace_id,run_id) REFERENCES public.decision_runs(workspace_id,id) ON DELETE RESTRICT,
 CHECK(octet_length(package::text)<=1048576)
);
ALTER TABLE dation_private.ultimate_run_publications ENABLE ROW LEVEL SECURITY;
ALTER TABLE dation_private.ultimate_run_publications FORCE ROW LEVEL SECURITY;
REVOKE ALL ON dation_private.ultimate_run_publications FROM PUBLIC,anon,authenticated,service_role;
CREATE TRIGGER ultimate_preparation_immutable BEFORE UPDATE OR DELETE ON dation_private.ultimate_run_publications
 FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_immutable();

CREATE FUNCTION dation_private.t8_read_set(r public.decision_runs) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE c public.decision_cases; key text; result jsonb='{}'; value jsonb; pvid uuid;
BEGIN
 SELECT * INTO c FROM public.decision_cases WHERE workspace_id=r.workspace_id AND id=r.decision_case_id;
 SELECT current_version_id INTO pvid FROM public.case_data_packs WHERE workspace_id=r.workspace_id AND case_id=r.decision_case_id;
 FOR key IN SELECT jsonb_object_keys(r.configuration_json#>'{ultimate_graph,read_set}') LOOP
  value=NULL;
  IF key IN('transport_demand','transport_resources','scheduling_enrichment') THEN
   SELECT jsonb_build_object('canonical_sha256',e.canonical_sha256,'contract_hash',e.contract_hash,'normalizer_version',e.normalizer_version) INTO value
    FROM public.case_data_pack_entries e WHERE workspace_id=r.workspace_id AND pack_version_id=pvid AND slot_key=key;
  ELSIF key='model' THEN value=to_jsonb(c.logistics_model_version_id);
  ELSIF key='horizon' THEN value=jsonb_build_array(c.planning_start,c.planning_end);
  ELSIF key='case_policy' THEN value=to_jsonb(c.case_policy_hash);
  ELSIF key='node_policy' THEN value=to_jsonb(r.node_policy_hash);
  ELSIF key='approved:logistics_assignment' THEN
   SELECT CASE WHEN count(*)=1 THEN to_jsonb(min(id::text)) ELSE 'null'::jsonb END INTO value FROM public.decision_runs
    WHERE workspace_id=r.workspace_id AND decision_case_id=r.decision_case_id AND node_id='logistics_assignment'
    AND workflow_version=2 AND approved_at IS NOT NULL AND superseded_at IS NULL;
  ELSE RETURN NULL; END IF;
  result=result||jsonb_build_object(key,value);
 END LOOP;
 RETURN result;
END; $$;
CREATE FUNCTION dation_private.t8_fresh(r public.decision_runs) RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT r.superseded_at IS NULL AND r.configuration_json#>'{ultimate_graph,read_set}' IS NOT NULL
 AND dation_private.t8_read_set(r) IS NOT DISTINCT FROM r.configuration_json#>'{ultimate_graph,read_set}';
$$;
CREATE FUNCTION dation_private.t8_pack_invalidation() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE r public.decision_runs; uid uuid; stamp timestamptz=clock_timestamp();
BEGIN
 IF NEW.current_version_id IS NOT DISTINCT FROM OLD.current_version_id THEN RETURN NEW; END IF;
 PERFORM 1 FROM public.workspaces WHERE id=NEW.workspace_id FOR UPDATE;
 PERFORM 1 FROM public.decision_cases WHERE workspace_id=NEW.workspace_id AND id=NEW.case_id FOR UPDATE;
 SELECT created_by INTO uid FROM public.case_data_pack_versions WHERE id=NEW.current_version_id;
 FOR r IN SELECT * FROM public.decision_runs WHERE workspace_id=NEW.workspace_id AND decision_case_id=NEW.case_id
  AND workflow_version=2 AND superseded_at IS NULL ORDER BY CASE node_id WHEN 'logistics_assignment' THEN 0 ELSE 1 END,id FOR UPDATE LOOP
  IF NOT dation_private.t8_fresh(r) THEN
   IF r.approved_at IS NOT NULL THEN
    INSERT INTO public.decision_approval_events(workspace_id,run_id,case_id,node_id,action,actor,actor_user_id,occurred_at,reason_code,caused_by_pack_version_id)
     VALUES(r.workspace_id,r.id,r.decision_case_id,r.node_id,'superseded','user:'||uid,uid,stamp,'INPUT_READ_SET_CHANGED',NEW.current_version_id);
   END IF;
   UPDATE public.decision_runs SET superseded_at=stamp,invalidated_by_pack_version_id=NEW.current_version_id WHERE id=r.id;
  END IF;
 END LOOP;
 RETURN NEW;
END; $$;
CREATE TRIGGER ultimate_pack_readset_invalidation AFTER UPDATE OF current_version_id ON public.case_data_packs
 FOR EACH ROW EXECUTE FUNCTION dation_private.t8_pack_invalidation();

-- The legacy trigger stays byte-equivalent for legacy admissions. Ultimate uses
-- its two-node closure and retires all prior candidates under the admission lock.
CREATE OR REPLACE FUNCTION dation_private.reopen_on_run_admission() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN IF NEW.workflow_version=1 THEN PERFORM dation_private.invalidate_run_lineage(NEW); END IF; RETURN NEW; END; $$;
DO $$ DECLARE source text; BEGIN
 source=pg_get_functiondef('dation_private.t5_run_projection(public.decision_runs)'::regprocedure);
 IF strpos(source,'''graph_snapshot''')=0 THEN RAISE EXCEPTION 'Unexpected graph projection'; END IF;
 EXECUTE replace(source,'''graph_snapshot''','''node_policy_hash'',r.node_policy_hash,''graph_snapshot''');
END; $$;
-- T7 includes CASE evidence (for example, its Sankey destination index). Keep
-- T2's checked TYPE/id syntax and extend it to the existing T1 EntityType.
DO $$ DECLARE source text; BEGIN
 source=pg_get_functiondef('dation_private.ultimate_artifact_guard()'::regprocedure);
 IF strpos(source,'(ORDER|TRIP|RESOURCE|ALTERNATIVE|EXCEPTION)/')=0 THEN RAISE EXCEPTION 'Unexpected artifact lookup contract'; END IF;
 EXECUTE replace(source,'(ORDER|TRIP|RESOURCE|ALTERNATIVE|EXCEPTION)/','(CASE|ORDER|TRIP|RESOURCE|ALTERNATIVE|EXCEPTION)/');
END; $$;

CREATE FUNCTION public.platform_ultimate_execution(target_workspace_id uuid,actor_user_id uuid,operation text,arguments jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE wid uuid=target_workspace_id; uid uuid=actor_user_id; rid uuid=(arguments->>'run_id')::uuid; cid uuid=(arguments->>'case_id')::uuid;
 c public.decision_cases; r public.decision_runs; j public.dispatch_run_jobs; mv public.logistics_model_versions;
 p public.case_data_packs; pub dation_private.ultimate_run_publications; role_name text; owner_id uuid; data_owner uuid;
 body jsonb; input jsonb; ctx jsonb; reads jsonb; entries jsonb; policy jsonb; item jsonb; previous public.decision_runs;
 stamp timestamptz; intent text; fp text; mh text; manifest jsonb; a public.decision_result_artifacts; blockers jsonb='[]'; enabled boolean;
BEGIN
 IF operation NOT IN('state','replay','admit','read','approve','prepare','prepared','finish') OR operation IS NULL THEN RAISE EXCEPTION 'Unsupported operation' USING ERRCODE='22023'; END IF;
 IF uid IS NULL THEN
  IF operation NOT IN('prepared','prepare','finish') THEN RAISE EXCEPTION 'Actor required' USING ERRCODE='42501'; END IF;
 ELSE role_name=dation_private.team_actor(wid,uid); END IF;
 IF NOT EXISTS(SELECT 1 FROM public.workspace_ddas WHERE workspace_id=wid AND dda_id='logistics' AND status='enabled') THEN RAISE EXCEPTION 'DDA disabled' USING ERRCODE='42501'; END IF;
 PERFORM set_config('dation.workspace_id',wid::text,true);
 PERFORM set_config('dation.actor_user_id',coalesce(uid::text,''),true);
 IF rid IS NOT NULL THEN
  SELECT * INTO r FROM public.decision_runs WHERE workspace_id=wid AND id=rid AND workflow_version=2;
  IF FOUND THEN cid=r.decision_case_id; END IF;
 END IF;
 -- Lock order: workspace -> Case -> job -> Run -> artifact. Claimers lock job -> Run.
 PERFORM 1 FROM public.workspaces WHERE id=wid FOR UPDATE;
 SELECT * INTO c FROM public.decision_cases WHERE workspace_id=wid AND id=cid AND workflow_version=2 FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
 IF uid IS NOT NULL THEN role_name=dation_private.team_actor(wid,uid); END IF;
 SELECT ultimate_admissions_enabled INTO enabled FROM dation_private.platform_release WHERE singleton;
 IF operation='state' THEN
  body=public.platform_ultimate_graph(wid,uid,c.id);
  SELECT coalesce(jsonb_agg(to_jsonb(e)||jsonb_build_object('normalized_size',o.normalized_size,'model_version_id',o.model_version_id,'summary',o.summary) ORDER BY e.slot_key),'[]') INTO entries
   FROM public.case_data_pack_entries e JOIN dation_private.ultimate_input_objects o ON o.workspace_id=e.workspace_id AND o.dataset_id=e.dataset_id
   JOIN public.case_data_packs cp ON cp.workspace_id=e.workspace_id AND cp.case_id=e.case_id AND cp.current_version_id=e.pack_version_id
   WHERE e.workspace_id=wid AND e.case_id=cid;
  RETURN body||jsonb_build_object('pinned_entries',entries,'admissions_enabled',enabled);
 END IF;
 IF operation IN('replay','admit') THEN
  intent=dation_private.t8_hash('ULTIMATE_RUN_INTENT',jsonb_build_object('actor',uid,'request',arguments->'client_request'));
  SELECT * INTO j FROM public.dispatch_run_jobs WHERE workspace_id=wid AND run_id=rid;
  IF FOUND THEN
   IF j.request_fingerprint IS DISTINCT FROM intent THEN RAISE EXCEPTION 'Intention conflict' USING ERRCODE='22023'; END IF;
   RETURN jsonb_build_object('replayed',true,'run',to_jsonb(r)-'result_json'-'configuration_json');
  END IF;
  IF operation='replay' THEN RETURN jsonb_build_object('replayed',false); END IF;
  IF NOT enabled THEN RAISE EXCEPTION 'Ultimate admissions closed' USING ERRCODE='42501'; END IF;
  IF role_name NOT IN('admin','operator') OR c.status='archived' THEN RAISE EXCEPTION 'Writer required' USING ERRCODE='42501'; END IF;
  SELECT owner_user_id INTO owner_id FROM public.decision_assignments WHERE workspace_id=wid AND decision_case_id=cid AND node_id='logistics_assignment';
  SELECT owner_user_id INTO data_owner FROM dation_private.workflow_stage_assignments WHERE workspace_id=wid AND decision_case_id=cid AND stage_key='data_owner';
  IF NOT dation_private.responsibility_eligible(wid,owner_id,'decision_owner') OR NOT dation_private.responsibility_eligible(wid,data_owner,'data_owner') THEN RAISE EXCEPTION 'Eligible owners required' USING ERRCODE='22023'; END IF;
  IF role_name<>'admin' AND owner_id IS DISTINCT FROM uid THEN RAISE EXCEPTION 'Decision Owner or Admin required' USING ERRCODE='42501'; END IF;
  input=arguments->'input';ctx=input->'context';policy=ctx->'node_policy';reads=arguments->'graph_snapshot'->'read_set';
  SELECT * INTO mv FROM public.logistics_model_versions WHERE workspace_id=wid AND id=c.logistics_model_version_id;
  SELECT * INTO p FROM public.case_data_packs WHERE workspace_id=wid AND case_id=cid;
  IF (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(reads) key) IS DISTINCT FROM
    ARRAY['case_policy','horizon','model','node_policy','transport_demand','transport_resources']::text[]
   OR jsonb_array_length(arguments->'entries') IS DISTINCT FROM 2
   OR input#>>'{model,workspace_id}' IS DISTINCT FROM wid::text
   OR input#>>'{model,model_id}' IS DISTINCT FROM mv.model_id::text
   OR input#>>'{model,version_id}' IS DISTINCT FROM mv.id::text
   OR input#>>'{model,version}' IS DISTINCT FROM mv.version::text
   OR input#>>'{model,configuration_hash}' IS DISTINCT FROM mv.config_hash
   OR input#>>'{model,contract_registry_version}' IS DISTINCT FROM mv.contract_registry_version
   OR ((input->'model')-'workspace_id'-'model_id'-'version_id'-'version'-'configuration_hash'-'contract_registry_version') IS DISTINCT FROM
      (SELECT jsonb_object_agg(key,value) FROM jsonb_each(mv.config_jsonb) WHERE key IN('operating_role','transport_pattern','primary_dimension','active_dimensions','allowed_sources','homogeneous_loads_declared','split_permitted','currency_policy'))
   OR ctx->>'pack_manifest_hash' IS DISTINCT FROM (SELECT manifest_hash FROM public.case_data_pack_versions WHERE workspace_id=wid AND id=p.current_version_id)
   OR ctx->>'data_pack_version' IS DISTINCT FROM (SELECT version::text FROM public.case_data_pack_versions WHERE workspace_id=wid AND id=p.current_version_id)
   OR ctx->'active_dimensions' IS DISTINCT FROM mv.config_jsonb->'active_dimensions'
   OR ctx->'primary_dimension' IS DISTINCT FROM mv.config_jsonb->'primary_dimension'
   OR ctx->'operating_role' IS DISTINCT FROM mv.config_jsonb->'operating_role'
   OR ctx->>'case_name' IS DISTINCT FROM c.label
   OR (policy->>'override')::boolean IS DISTINCT FROM (nullif(btrim(policy->>'override_reason'),'') IS NOT NULL)
   OR (coalesce((policy->>'override')::boolean,false)=false AND policy-'override'-'override_reason' IS DISTINCT FROM c.case_policy_jsonb)
   THEN RAISE EXCEPTION 'Frozen model/read-set/policy invalid' USING ERRCODE='22023'; END IF;
  FOR item IN SELECT value FROM jsonb_array_elements(arguments->'entries') LOOP
   IF NOT EXISTS(SELECT 1 FROM public.case_data_pack_entries e JOIN dation_private.ultimate_input_objects o ON o.workspace_id=e.workspace_id AND o.dataset_id=e.dataset_id
    WHERE e.workspace_id=wid AND e.case_id=cid AND e.pack_version_id=p.current_version_id AND e.slot_key=item->>'slot_key'
    AND e.slot_key IN('transport_demand','transport_resources') AND e.dataset_id::text=item->>'dataset_id'
    AND e.canonical_sha256=item->>'canonical_sha256' AND e.contract_hash=item->>'contract_hash' AND e.normalizer_version=item->>'normalizer_version'
    AND e.normalized_bucket=item->>'normalized_bucket' AND e.normalized_path=item->>'normalized_path'
    AND o.normalized_size=(item->>'normalized_size')::bigint AND o.model_version_id=mv.id) THEN RAISE EXCEPTION 'Unbound input locator' USING ERRCODE='22023'; END IF;
  END LOOP;
  IF (SELECT jsonb_agg(x ORDER BY x->>'slot') FROM jsonb_array_elements(ctx->'read_set') x) IS DISTINCT FROM
    (SELECT jsonb_agg(jsonb_build_object('slot',e.slot_key,'canonical_sha256',e.canonical_sha256,'contract_hash',e.contract_hash,'normalizer_version',e.normalizer_version) ORDER BY e.slot_key)
     FROM public.case_data_pack_entries e WHERE e.workspace_id=wid AND e.pack_version_id=p.current_version_id AND e.slot_key IN('transport_demand','transport_resources')) THEN
   RAISE EXCEPTION 'Frozen semantic inputs invalid' USING ERRCODE='22023'; END IF;
  IF arguments#>>'{client_request,node_id}' IS DISTINCT FROM 'logistics_assignment' OR input->>'run_id' IS DISTINCT FROM rid::text
   OR ctx->>'workspace_id' IS DISTINCT FROM wid::text OR ctx->>'case_id' IS DISTINCT FROM cid::text
   OR ctx->>'logistics_model_version_id' IS DISTINCT FROM c.logistics_model_version_id::text OR ctx->>'data_pack_version_id' IS DISTINCT FROM p.current_version_id::text
   OR ctx->>'planning_start' IS DISTINCT FROM c.planning_start::text OR ctx->>'planning_end' IS DISTINCT FROM c.planning_end::text
   OR ctx->'case_policy' IS DISTINCT FROM c.case_policy_jsonb OR ctx->>'graph_version' IS DISTINCT FROM c.graph_definition_version
   OR ctx->>'model_hash' IS DISTINCT FROM mv.config_hash OR ctx->>'contract_hash' IS DISTINCT FROM mv.contract_hash
   OR ctx->'currency_policy' IS DISTINCT FROM mv.config_jsonb->'currency_policy'
   OR NOT dation_private.t3_policy_valid(policy-'override'-'override_reason') THEN RAISE EXCEPTION 'Invalid pinned input' USING ERRCODE='22023'; END IF;
  FOR item IN SELECT value FROM jsonb_array_elements(c.case_policy_jsonb->'guardrails') LOOP
   IF NOT EXISTS(SELECT 1 FROM jsonb_array_elements(policy->'guardrails') x WHERE x->>'kind'=item->>'kind' AND
    CASE WHEN item->>'kind'='MAXIMUM_EXTERNAL_SHARE' THEN (x->>'limit')::numeric<=(item->>'limit')::numeric ELSE (x->>'limit')::numeric>=(item->>'limit')::numeric END) THEN RAISE EXCEPTION 'Guardrail relaxed' USING ERRCODE='22023'; END IF;
  END LOOP;
  IF arguments#>>'{client_request,expected_context_hash}' IS DISTINCT FROM dation_private.t8_input_hash(ctx)
   OR ctx->>'data_pack_version_id' IS DISTINCT FROM arguments#>>'{client_request,data_pack_version_id}'
   OR ctx->>'logistics_model_version_id' IS DISTINCT FROM arguments#>>'{client_request,model_version_id}'
   OR policy IS DISTINCT FROM arguments#>'{client_request,node_policy}'
   OR arguments#>>'{graph_snapshot,definition_hash}' IS DISTINCT FROM (SELECT definition_hash FROM dation_private.decision_definition_versions WHERE version='ULTIMATE_DECISION_GRAPH_V1') THEN
   RAISE EXCEPTION 'Context/hash changed' USING ERRCODE='55006'; END IF;
  stamp=clock_timestamp();input=jsonb_set(input,'{result_generated_at}',to_jsonb(stamp));
  IF (SELECT count(*) FROM public.dispatch_run_jobs WHERE workspace_id=wid AND state IN('queued','running'))>=32 THEN RAISE EXCEPTION 'Queue full' USING ERRCODE='53300'; END IF;
  INSERT INTO public.decision_runs(id,workspace_id,created_by_user_id,created_at,dataset_id,workflow_version,decision_case_id,node_id,
    logistics_model_version_id,data_pack_version_id,graph_definition_version,case_policy_hash,node_policy_hash,contract_hash,input_context_hash,
    transit_model_version,runtime_profile,result_schema_version,engine_name,engine_version,schema_version,status,configuration_json,progress_json)
  VALUES(rid,wid,uid,stamp,(arguments->>'dataset_id')::uuid,2,cid,'logistics_assignment',c.logistics_model_version_id,p.current_version_id,c.graph_definition_version,
    c.case_policy_hash,dation_private.t8_hash('POLICY',dation_private.t8_policy_projection(policy)),mv.contract_hash,dation_private.t8_input_hash(ctx),
    'DATION_TRANSIT_V1','transport_plan_v1',1,'transport_plan','2.0.0','transport_plan_v1','queued',
    jsonb_build_object('ultimate_graph',arguments->'graph_snapshot','frozen_context',ctx,'node_policy',policy),jsonb_build_object('stage','queued')) RETURNING * INTO r;
  IF dation_private.t8_read_set(r) IS DISTINCT FROM reads THEN RAISE EXCEPTION 'Consumed inputs changed' USING ERRCODE='55006'; END IF;
  FOR previous IN SELECT * FROM public.decision_runs WHERE workspace_id=wid AND decision_case_id=cid AND workflow_version=2
   AND id<>rid AND superseded_at IS NULL AND node_id IN('logistics_assignment','logistics_scheduling') ORDER BY id FOR UPDATE LOOP
   IF previous.approved_at IS NOT NULL THEN
    INSERT INTO public.decision_approval_events(workspace_id,run_id,case_id,node_id,action,actor,actor_user_id,occurred_at,replacement_run_id,reason_code)
     VALUES(wid,previous.id,cid,previous.node_id,'superseded','user:'||uid,uid,stamp,rid,CASE WHEN previous.node_id='logistics_assignment' THEN 'RUN_REPLACED' ELSE 'UPSTREAM_INVALIDATED' END);
   END IF;
   UPDATE public.decision_runs SET superseded_at=stamp,superseded_by_run_id=rid WHERE id=previous.id;
  END LOOP;
  INSERT INTO public.dispatch_run_jobs(workspace_id,run_id,request_json,request_fingerprint)
   VALUES(wid,rid,jsonb_build_object('workspace_id',wid,'workflow_version',2,'engine_name','transport_plan','engine_version','2.0.0','schema_version','transport_plan_v1',
    'runtime_profile','transport_plan_v1','result_schema_version',1,'input',input,'entries',arguments->'entries','client_request',arguments->'client_request'),intent);
  RETURN jsonb_build_object('replayed',false,'run',to_jsonb(r)-'result_json'-'configuration_json');
 END IF;
 IF r.id IS NULL THEN RAISE EXCEPTION 'Run not found' USING ERRCODE='P0002'; END IF;
 IF operation IN('prepare','prepared','finish') THEN
  SELECT * INTO j FROM public.dispatch_run_jobs WHERE workspace_id=wid AND run_id=rid FOR UPDATE;
  SELECT * INTO r FROM public.decision_runs WHERE workspace_id=wid AND id=rid FOR UPDATE;
  SELECT * INTO pub FROM dation_private.ultimate_run_publications WHERE workspace_id=wid AND run_id=rid;
  IF operation='finish' AND r.status='completed' AND pub.result_fingerprint=arguments->>'result_fingerprint' THEN RETURN jsonb_build_object('replayed',true,'run',to_jsonb(r)-'configuration_json'); END IF;
  IF j.state IS DISTINCT FROM 'running' OR j.lease_token IS DISTINCT FROM (arguments->>'worker_token')::uuid OR j.lease_expires_at<=clock_timestamp() OR j.deadline_at<=clock_timestamp() THEN RAISE EXCEPTION 'Lease lost' USING ERRCODE='55006'; END IF;
  IF operation='prepared' THEN RETURN jsonb_build_object('publication',CASE WHEN pub.run_id IS NULL THEN NULL ELSE to_jsonb(pub) END,'artifacts',coalesce((SELECT jsonb_agg(to_jsonb(x) ORDER BY x.kind,x.part_key) FROM public.decision_result_artifacts x WHERE x.workspace_id=wid AND x.run_id=rid),'[]')); END IF;
  IF operation='prepare' THEN
   body=arguments->'package';fp=body#>>'{fingerprints,result_fingerprint}';manifest=body#>'{artifact_manifest,artifacts}';
   mh=encode(sha256(convert_to(dation_private.t8_canonical(manifest),'UTF8')),'hex');
   IF dation_private.t8_package_hash(body) IS DISTINCT FROM fp OR body#>>'{decision,run_id}' IS DISTINCT FROM rid::text
    OR body->'context' IS DISTINCT FROM r.configuration_json->'frozen_context' OR body#>>'{fingerprints,input_context_hash}' IS DISTINCT FROM r.input_context_hash
    OR body->>'result_schema' IS DISTINCT FROM r.schema_version OR body#>>'{engine,engine_name}' IS DISTINCT FROM r.engine_name
    OR body#>>'{engine,engine_version}' IS DISTINCT FROM r.engine_version OR body#>>'{engine,runtime_profile}' IS DISTINCT FROM r.runtime_profile
    OR body->>'result_schema_version' IS DISTINCT FROM '1' OR body#>>'{decision,node_id}' IS DISTINCT FROM r.node_id
    OR body#>>'{engine,transit_model_version}' IS DISTINCT FROM r.transit_model_version
    OR body->>'assembler_version' IS DISTINCT FROM 'RESULT_ASSEMBLER_D1_V1' OR jsonb_array_length(manifest) NOT BETWEEN 1 AND 800
    OR (SELECT count(*) FROM jsonb_array_elements(manifest) x WHERE x->>'kind'='CORE' AND x->>'artifact_schema'='engine_core_v1')<>1
    OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(manifest) x WHERE x->>'kind'='EVIDENCE' AND x->>'artifact_schema'='engine_evidence_v1')
    OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(manifest) x WHERE x->>'kind'='EXPORT_ROWS' AND x->>'artifact_schema'='export_rows_v1')
    OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(manifest) x WHERE x->>'kind'='AI_BASE' AND x->>'artifact_schema'='decision_context_v1')
    THEN RAISE EXCEPTION 'Package binding invalid' USING ERRCODE='22023'; END IF;
   IF pub.run_id IS NOT NULL THEN
    IF pub.package IS DISTINCT FROM body THEN RAISE EXCEPTION 'Prepared publication differs' USING ERRCODE='22023'; END IF;
   ELSE
    INSERT INTO dation_private.ultimate_run_publications(workspace_id,run_id,package,result_fingerprint,manifest_hash) VALUES(wid,rid,body,fp,mh);
    FOR item IN SELECT value FROM jsonb_array_elements(manifest) LOOP
     IF item->>'workspace_id' IS DISTINCT FROM wid::text OR item->>'run_id' IS DISTINCT FROM rid::text OR item->>'core_fingerprint' IS DISTINCT FROM body#>>'{fingerprints,core_result_fingerprint}'
      OR item->>'assembler_version' IS DISTINCT FROM body->>'assembler_version' OR (item->>'size_bytes')::bigint>1048576 THEN RAISE EXCEPTION 'Foreign/oversized artifact' USING ERRCODE='22023'; END IF;
     INSERT INTO public.decision_result_artifacts(id,workspace_id,run_id,kind,part_key,artifact_schema,schema_version,content_sha256,size_bytes,media_type,
      storage_bucket,storage_path,assembler_version,core_fingerprint,producer_lease_token,producer_generation,producer_metadata,lookup_keys)
     VALUES((item->>'artifact_id')::uuid,wid,rid,item->>'kind',item->>'part_key',item->>'artifact_schema',(item->>'schema_version')::integer,
      item->>'content_sha256',(item->>'size_bytes')::bigint,item->>'media_type','dda-inputs',wid::text||'/runs/'||rid::text||'/'||lower(item->>'kind')||'/'||
      (item->>'part_key')||'/'||(item->>'content_sha256')||'.json',item->>'assembler_version',item->>'core_fingerprint',j.lease_token,j.attempts,
      jsonb_build_object('runtime_profile',r.runtime_profile,'input_context_hash',r.input_context_hash,'retrieval_index',
       (arguments->'artifact_indexes'->(item->>'artifact_id'))-'entities'),
      ARRAY(SELECT (x->>0)||'/'||(x->>1) FROM jsonb_array_elements(coalesce(arguments->'artifact_indexes'->(item->>'artifact_id')->'entities','[]')) x));
    END LOOP;
   END IF;
   RETURN jsonb_build_object('package',body,'artifacts',(SELECT jsonb_agg(to_jsonb(x) ORDER BY x.kind,x.part_key) FROM public.decision_result_artifacts x WHERE x.workspace_id=wid AND x.run_id=rid));
  END IF;
  IF pub.run_id IS NULL OR pub.result_fingerprint IS DISTINCT FROM arguments->>'result_fingerprint' OR pub.manifest_hash IS DISTINCT FROM arguments->>'verified_manifest_hash'
   OR (SELECT count(*) FROM public.decision_result_artifacts WHERE workspace_id=wid AND run_id=rid)<>jsonb_array_length(pub.package#>'{artifact_manifest,artifacts}')
   OR NOT EXISTS(SELECT 1 FROM public.decision_result_artifacts WHERE workspace_id=wid AND run_id=rid AND kind='CORE' AND artifact_schema='engine_core_v1') THEN RAISE EXCEPTION 'Incomplete publication' USING ERRCODE='22023'; END IF;
  UPDATE public.decision_runs SET status='completed',finished_at=clock_timestamp(),result_json=pub.package,result_fingerprint=pub.result_fingerprint,
   result_package_version=1,assembler_version=pub.package->>'assembler_version',artifact_manifest_hash=pub.manifest_hash,
   core_fingerprint=pub.package#>>'{fingerprints,core_result_fingerprint}',summary_json=pub.package->'summary',progress_json=jsonb_build_object('stage','completed') WHERE id=rid;
  UPDATE public.decision_result_artifacts SET publication_state='READY',result_fingerprint=pub.result_fingerprint WHERE workspace_id=wid AND run_id=rid;
  UPDATE public.dispatch_run_jobs SET state='completed',lease_token=NULL,lease_expires_at=NULL WHERE workspace_id=wid AND run_id=rid;
  SELECT * INTO r FROM public.decision_runs WHERE id=rid;
  RETURN jsonb_build_object('replayed',false,'run',to_jsonb(r)-'configuration_json');
 END IF;
 -- Readers and human approval always use the published Run, never the journal.
 IF r.status<>'completed' OR r.result_fingerprint IS NULL OR r.result_fingerprint IS DISTINCT FROM arguments->>'result_fingerprint'
  OR dation_private.t8_package_hash(r.result_json) IS DISTINCT FROM r.result_fingerprint THEN RAISE EXCEPTION 'Published result not found/mismatched' USING ERRCODE='22023'; END IF;
 SELECT owner_user_id INTO owner_id FROM public.decision_assignments WHERE workspace_id=wid AND decision_case_id=cid AND node_id=r.node_id;
 IF role_name NOT IN('admin','operator') OR (role_name<>'admin' AND owner_id IS DISTINCT FROM uid) THEN blockers=blockers||'"OWNER_REQUIRED"'::jsonb; END IF;
 IF NOT dation_private.responsibility_eligible(wid,owner_id,'decision_owner') THEN blockers=blockers||'"ELIGIBLE_OWNER_REQUIRED"'::jsonb; END IF;
 IF c.status='archived' THEN blockers=blockers||'"ARCHIVED_CASE"'::jsonb; END IF;
 IF NOT dation_private.t8_fresh(r) THEN blockers=blockers||'"STALE_CONTEXT"'::jsonb; END IF;
 IF r.result_json#>>'{approval_review,decision_ready_for_review}' IS DISTINCT FROM 'true' THEN blockers=blockers||'"REVIEW_NOT_READY"'::jsonb; END IF;
 IF (SELECT count(*) FROM public.decision_result_artifacts WHERE workspace_id=wid AND run_id=rid AND result_fingerprint=r.result_fingerprint AND publication_state='READY')<>jsonb_array_length(r.result_json#>'{artifact_manifest,artifacts}') THEN blockers=blockers||'"ARTIFACTS_NOT_READY"'::jsonb; END IF;
 IF operation='approve' THEN
  IF arguments->>'case_id' IS DISTINCT FROM cid::text OR arguments->>'node_id' IS DISTINCT FROM r.node_id OR arguments->>'verified_manifest_hash' IS DISTINCT FROM r.artifact_manifest_hash THEN RAISE EXCEPTION 'Approval binding invalid' USING ERRCODE='22023'; END IF;
  IF jsonb_array_length(blockers)>0 THEN RAISE EXCEPTION 'Current approval denied' USING ERRCODE='42501'; END IF;
  IF r.approved_at IS NULL THEN
   stamp=clock_timestamp();
   UPDATE public.decision_runs SET approved_at=stamp,approved_by='user:'||uid,approved_by_user_id=uid WHERE workspace_id=wid AND id=rid;
   INSERT INTO public.decision_approval_events(workspace_id,run_id,case_id,node_id,action,actor,actor_user_id,occurred_at)
    VALUES(wid,rid,cid,r.node_id,'approved','user:'||uid,uid,stamp);
   SELECT * INTO r FROM public.decision_runs WHERE id=rid;
  END IF;
 END IF;
 RETURN jsonb_build_object('run',to_jsonb(r),'artifacts',(SELECT jsonb_agg(to_jsonb(x) ORDER BY x.kind,x.part_key) FROM public.decision_result_artifacts x WHERE x.workspace_id=wid AND x.run_id=rid),
  'overlay',jsonb_build_object('run_id',rid,'result_fingerprint',r.result_fingerprint,'approval_allowed',jsonb_array_length(blockers)=0,
   'freshness',CASE WHEN dation_private.t8_fresh(r) THEN 'CURRENT' ELSE 'STALE' END,'approval_blockers',blockers));
END; $$;

-- Legacy workers only claim legacy profiles. New workers explicitly advertise
-- dual capability through a separate service-only function.
DO $$ DECLARE source text; BEGIN
 source=pg_get_functiondef('public.claim_dispatch_job(uuid,integer)'::regprocedure);
 IF strpos(source,'where ((state=')=0 THEN RAISE EXCEPTION 'Unexpected claim contract'; END IF;
 EXECUTE replace(source,'where ((state=','where coalesce((request_json->>''workflow_version'')::integer,1)=1 AND ((state=');
END; $$;
CREATE FUNCTION public.claim_dispatch_job_v2(worker_token uuid,lease_seconds integer DEFAULT 120) RETURNS SETOF public.dispatch_run_jobs
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE j public.dispatch_run_jobs;
BEGIN
 PERFORM dation_private.maintain_dispatch_jobs();
 SELECT * INTO j FROM public.dispatch_run_jobs WHERE ((state='queued' AND available_at<=clock_timestamp()) OR (state='running' AND lease_expires_at<=clock_timestamp()))
  AND attempts<max_attempts AND deadline_at>clock_timestamp() ORDER BY available_at,created_at FOR UPDATE SKIP LOCKED LIMIT 1;
 IF NOT FOUND THEN RETURN; END IF;
 UPDATE public.dispatch_run_jobs SET state='running',attempts=attempts+1,lease_token=worker_token,heartbeat_at=clock_timestamp(),
  lease_expires_at=least(deadline_at,clock_timestamp()+make_interval(secs=>greatest(30,least(lease_seconds,300)))) WHERE run_id=j.run_id;
 UPDATE public.decision_runs SET status='running',started_at=coalesce(started_at,clock_timestamp()),progress_json=jsonb_build_object('stage','validating'),error_message=NULL
  WHERE id=j.run_id AND status IN('queued','running');
 RETURN QUERY SELECT * FROM public.dispatch_run_jobs WHERE run_id=j.run_id;
END; $$;
REVOKE ALL ON FUNCTION public.platform_ultimate_execution(uuid,uuid,text,jsonb),public.claim_dispatch_job_v2(uuid,integer) FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.platform_ultimate_execution(uuid,uuid,text,jsonb),public.claim_dispatch_job_v2(uuid,integer) TO service_role;
REVOKE ALL ON FUNCTION dation_private.t8_canonical(jsonb),dation_private.t8_hash(text,jsonb),dation_private.t8_package_hash(jsonb),
 dation_private.t8_policy_projection(jsonb),dation_private.t8_input_hash(jsonb),dation_private.t8_read_set(public.decision_runs),dation_private.t8_fresh(public.decision_runs),dation_private.t8_pack_invalidation()
 FROM PUBLIC,anon,authenticated,service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
