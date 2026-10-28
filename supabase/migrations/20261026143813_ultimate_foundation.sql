-- T2 expansion only. No cohort activation, publishers, admission RPCs or backfill.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';

CREATE TABLE dation_private.decision_definition_versions (
 version text PRIMARY KEY CHECK(version ~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$'),
 definition_hash text NOT NULL CHECK(definition_hash ~ '^[0-9a-f]{64}$'),
 definition_jsonb jsonb NOT NULL CHECK(jsonb_typeof(definition_jsonb)='object'),
 created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE dation_private.decision_definition_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE dation_private.decision_definition_versions FORCE ROW LEVEL SECURITY;
REVOKE ALL ON dation_private.decision_definition_versions FROM PUBLIC,anon,authenticated,service_role;

CREATE TABLE public.logistics_models (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 workspace_id uuid NOT NULL REFERENCES public.workspaces(id) ON DELETE RESTRICT,
 name text NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 120),
 description text CHECK(length(description)<=1000),
 status text NOT NULL DEFAULT 'active' CHECK(status IN('active','archived')),
 revision bigint NOT NULL DEFAULT 1 CHECK(revision>0),
 created_by uuid NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(workspace_id,id),
 FOREIGN KEY(workspace_id,created_by) REFERENCES public.workspace_members(workspace_id,user_id) ON DELETE RESTRICT
);
CREATE INDEX logistics_models_listing ON public.logistics_models(workspace_id,status,updated_at DESC,id);
CREATE INDEX logistics_models_creator ON public.logistics_models(workspace_id,created_by);

-- Versions represent published snapshots; drafts/publication workflows belong to T3.
CREATE TABLE public.logistics_model_versions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 workspace_id uuid NOT NULL,
 model_id uuid NOT NULL,
 version integer NOT NULL CHECK(version>0),
 graph_definition_version text NOT NULL REFERENCES dation_private.decision_definition_versions(version) ON DELETE RESTRICT,
 config_schema_version text NOT NULL CHECK(length(config_schema_version) BETWEEN 1 AND 128),
 config_jsonb jsonb NOT NULL CHECK(jsonb_typeof(config_jsonb)='object'),
 contract_descriptor_jsonb jsonb NOT NULL CHECK(jsonb_typeof(contract_descriptor_jsonb)='object'),
 config_hash text NOT NULL CHECK(config_hash ~ '^[0-9a-f]{64}$'),
 contract_hash text NOT NULL CHECK(contract_hash ~ '^[0-9a-f]{64}$'),
 contract_registry_version text NOT NULL CHECK(length(contract_registry_version) BETWEEN 1 AND 128),
 published_by uuid NOT NULL,
 published_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(model_id,version), UNIQUE(workspace_id,id), UNIQUE(workspace_id,model_id,id),
 UNIQUE(workspace_id,id,graph_definition_version),
 FOREIGN KEY(workspace_id,model_id) REFERENCES public.logistics_models(workspace_id,id) ON DELETE RESTRICT,
 FOREIGN KEY(workspace_id,published_by) REFERENCES public.workspace_members(workspace_id,user_id) ON DELETE RESTRICT
);
CREATE INDEX logistics_model_versions_graph ON public.logistics_model_versions(graph_definition_version);
CREATE INDEX logistics_model_versions_publisher ON public.logistics_model_versions(workspace_id,published_by);

ALTER TABLE public.decision_cases
 ADD COLUMN workflow_version smallint NOT NULL DEFAULT 1 CHECK(workflow_version IN(1,2)),
 ADD COLUMN logistics_model_version_id uuid,
 ADD COLUMN planning_start date,
 ADD COLUMN planning_end date,
 ADD COLUMN operating_mode text CHECK(operating_mode IN('OPERATIONAL','SIMULATION')),
 ADD COLUMN case_policy_schema_version text,
 ADD COLUMN case_policy_jsonb jsonb,
 ADD COLUMN case_policy_hash text CHECK(case_policy_hash ~ '^[0-9a-f]{64}$'),
 ADD COLUMN context_frozen_at timestamptz,
 ADD COLUMN graph_definition_version text,
 ALTER COLUMN orders_dataset_id DROP NOT NULL,
 ALTER COLUMN fleet_dataset_id DROP NOT NULL,
 ALTER COLUMN input_signature DROP NOT NULL,
 ADD CONSTRAINT ultimate_case_context CHECK(CASE WHEN workflow_version=1 THEN
   orders_dataset_id IS NOT NULL AND fleet_dataset_id IS NOT NULL AND input_signature IS NOT NULL
   AND num_nonnulls(logistics_model_version_id,planning_start,planning_end,operating_mode,
     case_policy_schema_version,case_policy_jsonb,case_policy_hash,context_frozen_at,graph_definition_version)=0
  ELSE orders_dataset_id IS NULL AND fleet_dataset_id IS NULL AND input_signature IS NULL
   AND num_nonnulls(logistics_model_version_id,planning_start,planning_end,operating_mode,
     case_policy_schema_version,case_policy_jsonb,case_policy_hash,graph_definition_version)=8
   AND planning_start<=planning_end AND case_policy_schema_version='case_policy_v1'
   AND jsonb_typeof(case_policy_jsonb)='object' END),
 ADD CONSTRAINT ultimate_case_model FOREIGN KEY(workspace_id,logistics_model_version_id,graph_definition_version)
   REFERENCES public.logistics_model_versions(workspace_id,id,graph_definition_version) ON DELETE RESTRICT,
 ADD CONSTRAINT ultimate_case_model_identity UNIQUE(workspace_id,id,logistics_model_version_id);
CREATE INDEX ultimate_cases_model ON public.decision_cases(workspace_id,logistics_model_version_id,graph_definition_version)
 WHERE workflow_version=2;

CREATE TABLE public.case_data_packs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 workspace_id uuid NOT NULL,
 case_id uuid NOT NULL,
 current_version_id uuid,
 revision bigint NOT NULL DEFAULT 1 CHECK(revision>0),
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(workspace_id,id), UNIQUE(workspace_id,case_id), UNIQUE(workspace_id,case_id,id),
 FOREIGN KEY(workspace_id,case_id) REFERENCES public.decision_cases(workspace_id,id) ON DELETE RESTRICT
);
CREATE TABLE public.case_data_pack_versions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 workspace_id uuid NOT NULL,
 case_id uuid NOT NULL,
 pack_id uuid NOT NULL,
 version integer NOT NULL CHECK(version>0),
 manifest_hash text NOT NULL CHECK(manifest_hash ~ '^[0-9a-f]{64}$'),
 contract_set_hash text NOT NULL CHECK(contract_set_hash ~ '^[0-9a-f]{64}$'),
 created_by uuid NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 -- Server-only guard: entries must be inserted in their version's creation transaction.
 created_xid xid8 NOT NULL DEFAULT pg_current_xact_id(),
 UNIQUE(pack_id,version), UNIQUE(workspace_id,id), UNIQUE(workspace_id,case_id,id),
 UNIQUE(workspace_id,case_id,pack_id,id),
 FOREIGN KEY(workspace_id,case_id,pack_id) REFERENCES public.case_data_packs(workspace_id,case_id,id) ON DELETE RESTRICT,
 FOREIGN KEY(workspace_id,created_by) REFERENCES public.workspace_members(workspace_id,user_id) ON DELETE RESTRICT
);
CREATE INDEX case_data_pack_versions_history ON public.case_data_pack_versions(workspace_id,case_id,version DESC);
CREATE INDEX case_data_pack_versions_creator ON public.case_data_pack_versions(workspace_id,created_by);
ALTER TABLE public.case_data_packs ADD CONSTRAINT ultimate_pack_current_version
 FOREIGN KEY(workspace_id,case_id,id,current_version_id)
 REFERENCES public.case_data_pack_versions(workspace_id,case_id,pack_id,id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX case_data_packs_current ON public.case_data_packs(workspace_id,case_id,id,current_version_id);

ALTER TABLE public.datasets
 ADD COLUMN data_contract_id text,
 ADD COLUMN data_contract_hash text CHECK(data_contract_hash ~ '^[0-9a-f]{64}$'),
 ADD COLUMN normalizer_version text,
 ADD COLUMN canonical_sha256 text CHECK(canonical_sha256 ~ '^[0-9a-f]{64}$'),
 DROP CONSTRAINT datasets_dataset_type_check,
 ADD CONSTRAINT datasets_dataset_type_check CHECK(dataset_type IN('logistics_legacy','orders','fleet','transport_demand','transport_resources')),
 ADD CONSTRAINT ultimate_dataset_contract CHECK(CASE WHEN dataset_type IN('transport_demand','transport_resources') THEN
  num_nonnulls(data_contract_id,data_contract_hash,normalizer_version,canonical_sha256,sha256,schema_version)=6
   AND length(data_contract_id) BETWEEN 1 AND 128 AND length(normalizer_version) BETWEEN 1 AND 128
  ELSE num_nonnulls(data_contract_id,data_contract_hash,normalizer_version,canonical_sha256)=0 END),
 ADD CONSTRAINT ultimate_dataset_interpretation_identity UNIQUE(workspace_id,id,data_contract_id,data_contract_hash,sha256,canonical_sha256,normalizer_version);
-- Preserve datasets_dispatch_hash_key's legacy partial predicate without modification.
CREATE UNIQUE INDEX datasets_ultimate_interpretation ON public.datasets(workspace_id,dataset_type,sha256,data_contract_hash)
 WHERE dataset_type IN('transport_demand','transport_resources') AND sha256 IS NOT NULL;

CREATE TABLE public.case_data_pack_entries (
 pack_version_id uuid NOT NULL,
 slot_key text NOT NULL CHECK(slot_key IN('transport_demand','transport_resources','scheduling_enrichment')),
 workspace_id uuid NOT NULL,
 case_id uuid NOT NULL,
 dataset_id uuid NOT NULL,
 contract_id text NOT NULL,
 contract_hash text NOT NULL CHECK(contract_hash ~ '^[0-9a-f]{64}$'),
 raw_sha256 text NOT NULL CHECK(raw_sha256 ~ '^[0-9a-f]{64}$'),
 canonical_sha256 text NOT NULL CHECK(canonical_sha256 ~ '^[0-9a-f]{64}$'),
 normalizer_version text NOT NULL,
 normalized_bucket text NOT NULL CHECK(normalized_bucket ~ '^[a-z0-9][a-z0-9-]{0,62}$'),
 normalized_path text NOT NULL,
 record_count bigint NOT NULL CHECK(record_count>=0),
 PRIMARY KEY(pack_version_id,slot_key),
 FOREIGN KEY(workspace_id,case_id,pack_version_id) REFERENCES public.case_data_pack_versions(workspace_id,case_id,id) ON DELETE RESTRICT,
 FOREIGN KEY(workspace_id,dataset_id,contract_id,contract_hash,raw_sha256,canonical_sha256,normalizer_version)
  REFERENCES public.datasets(workspace_id,id,data_contract_id,data_contract_hash,sha256,canonical_sha256,normalizer_version) ON DELETE RESTRICT,
 CHECK(normalized_path=workspace_id::text||'/normalized/'||dataset_id::text||'/'||canonical_sha256||'.json')
);
CREATE INDEX case_data_pack_entries_dataset ON public.case_data_pack_entries(workspace_id,dataset_id);
CREATE INDEX case_data_pack_entries_case ON public.case_data_pack_entries(workspace_id,case_id,pack_version_id);

ALTER TABLE public.decision_runs
 ADD COLUMN workflow_version smallint NOT NULL DEFAULT 1 CHECK(workflow_version IN(1,2)),
 ADD COLUMN logistics_model_version_id uuid,
 ADD COLUMN data_pack_version_id uuid,
 ADD COLUMN graph_definition_version text REFERENCES dation_private.decision_definition_versions(version) ON DELETE RESTRICT,
 ADD COLUMN case_policy_hash text CHECK(case_policy_hash ~ '^[0-9a-f]{64}$'),
 ADD COLUMN node_policy_hash text CHECK(node_policy_hash ~ '^[0-9a-f]{64}$'),
 ADD COLUMN contract_hash text CHECK(contract_hash ~ '^[0-9a-f]{64}$'),
 ADD COLUMN input_context_hash text CHECK(input_context_hash ~ '^[0-9a-f]{64}$'),
 ADD COLUMN transit_model_version text,
 ADD COLUMN runtime_profile text,
 ADD COLUMN result_schema_version integer,
 ADD COLUMN invalidated_by_pack_version_id uuid,
 ADD CONSTRAINT ultimate_run_invalidation_cause CHECK(invalidated_by_pack_version_id IS NULL OR superseded_at IS NOT NULL),
 ADD CONSTRAINT ultimate_run_model FOREIGN KEY(workspace_id,decision_case_id,logistics_model_version_id)
  REFERENCES public.decision_cases(workspace_id,id,logistics_model_version_id) ON DELETE RESTRICT,
 ADD CONSTRAINT ultimate_run_pack FOREIGN KEY(workspace_id,decision_case_id,data_pack_version_id)
  REFERENCES public.case_data_pack_versions(workspace_id,case_id,id) ON DELETE RESTRICT,
 ADD CONSTRAINT ultimate_run_invalidation_pack FOREIGN KEY(workspace_id,decision_case_id,invalidated_by_pack_version_id)
  REFERENCES public.case_data_pack_versions(workspace_id,case_id,id) ON DELETE RESTRICT,
 ADD CONSTRAINT ultimate_run_context CHECK(CASE WHEN workflow_version=1 THEN
   schema_version NOT IN('transport_plan_v1','day_scheduling_v1') AND num_nonnulls(logistics_model_version_id,data_pack_version_id,graph_definition_version,case_policy_hash,node_policy_hash,
    contract_hash,input_context_hash,transit_model_version,runtime_profile,result_schema_version,invalidated_by_pack_version_id)=0
  ELSE num_nonnulls(decision_case_id,node_id,logistics_model_version_id,data_pack_version_id,graph_definition_version,case_policy_hash,
    node_policy_hash,contract_hash,input_context_hash,transit_model_version,runtime_profile,result_schema_version)=12
   AND orders_dataset_id IS NULL AND fleet_dataset_id IS NULL AND engine_version='2.0.0' AND result_schema_version=1
   AND transit_model_version='DATION_TRANSIT_V1' AND runtime_profile=schema_version
   AND ((node_id='logistics_assignment' AND schema_version='transport_plan_v1' AND engine_name='transport_plan')
     OR (node_id='logistics_scheduling' AND schema_version='day_scheduling_v1' AND engine_name='day_scheduling')) END);
CREATE INDEX ultimate_runs_context ON public.decision_runs(workspace_id,decision_case_id,data_pack_version_id);
CREATE INDEX ultimate_runs_model ON public.decision_runs(workspace_id,decision_case_id,logistics_model_version_id);
CREATE INDEX ultimate_runs_graph ON public.decision_runs(graph_definition_version);
CREATE INDEX ultimate_runs_invalidated ON public.decision_runs(workspace_id,decision_case_id,invalidated_by_pack_version_id)
 WHERE invalidated_by_pack_version_id IS NOT NULL;

ALTER TABLE public.decision_approval_events
 ADD COLUMN reason_code text CHECK(reason_code IN('INPUT_READ_SET_CHANGED','UPSTREAM_INVALIDATED','RUN_REPLACED')),
 ADD COLUMN caused_by_pack_version_id uuid,
 ADD CONSTRAINT ultimate_approval_pack FOREIGN KEY(workspace_id,case_id,caused_by_pack_version_id)
  REFERENCES public.case_data_pack_versions(workspace_id,case_id,id) ON DELETE RESTRICT,
 ADD CONSTRAINT ultimate_approval_cause CHECK(CASE WHEN reason_code='INPUT_READ_SET_CHANGED' THEN
   caused_by_pack_version_id IS NOT NULL AND action='superseded'
  ELSE caused_by_pack_version_id IS NULL END);
CREATE INDEX ultimate_approval_cause ON public.decision_approval_events(workspace_id,case_id,caused_by_pack_version_id)
 WHERE caused_by_pack_version_id IS NOT NULL;
ALTER TABLE public.decision_runs DROP CONSTRAINT decision_runs_superseded_requires_approval_check;
ALTER TABLE public.decision_runs ADD CONSTRAINT decision_runs_superseded_requires_approval_check CHECK(
 superseded_at IS NULL OR approved_at IS NOT NULL OR superseded_by_run_id IS NOT NULL
 OR (workflow_version=2 AND invalidated_by_pack_version_id IS NOT NULL));

CREATE FUNCTION dation_private.ultimate_immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'Published Ultimate snapshot is immutable' USING ERRCODE='22023'; END; $$;
CREATE TRIGGER ultimate_definition_immutable BEFORE UPDATE OR DELETE ON dation_private.decision_definition_versions
 FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_immutable();
CREATE TRIGGER ultimate_model_version_immutable BEFORE UPDATE OR DELETE ON public.logistics_model_versions
 FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_immutable();
CREATE TRIGGER ultimate_pack_version_immutable BEFORE UPDATE OR DELETE ON public.case_data_pack_versions
 FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_immutable();
CREATE TRIGGER ultimate_pack_entry_immutable BEFORE UPDATE OR DELETE ON public.case_data_pack_entries
 FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_immutable();

CREATE FUNCTION dation_private.ultimate_dataset_identity() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF ROW(NEW.data_contract_id,NEW.data_contract_hash,NEW.normalizer_version,NEW.canonical_sha256)
 IS DISTINCT FROM ROW(OLD.data_contract_id,OLD.data_contract_hash,OLD.normalizer_version,OLD.canonical_sha256) THEN
  RAISE EXCEPTION 'Dataset interpretation is immutable; create a new version' USING ERRCODE='22023'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER ultimate_dataset_identity BEFORE UPDATE ON public.datasets
 FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_dataset_identity();

CREATE FUNCTION dation_private.ultimate_case_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='UPDATE' THEN
  IF NEW.workflow_version<>OLD.workflow_version OR NEW.logistics_model_version_id IS DISTINCT FROM OLD.logistics_model_version_id
    OR NEW.graph_definition_version IS DISTINCT FROM OLD.graph_definition_version THEN
   RAISE EXCEPTION 'Case cohort/model binding is immutable' USING ERRCODE='22023'; END IF;
  IF OLD.workflow_version=2 AND (NEW.state_json IS DISTINCT FROM OLD.state_json OR
   (OLD.context_frozen_at IS NOT NULL AND ROW(NEW.planning_start,NEW.planning_end,NEW.operating_mode,
     NEW.case_policy_schema_version,NEW.case_policy_jsonb,NEW.case_policy_hash,NEW.context_frozen_at)
    IS DISTINCT FROM ROW(OLD.planning_start,OLD.planning_end,OLD.operating_mode,
     OLD.case_policy_schema_version,OLD.case_policy_jsonb,OLD.case_policy_hash,OLD.context_frozen_at))) THEN
   RAISE EXCEPTION 'Ultimate context cannot be overwritten by a legacy write' USING ERRCODE='22023'; END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER ultimate_case_context_guard BEFORE UPDATE ON public.decision_cases
 FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_case_guard();

CREATE FUNCTION dation_private.ultimate_pack_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE cohort smallint; version_xid xid8; actual_type text;
BEGIN
 IF TG_TABLE_NAME='case_data_packs' THEN
  SELECT workflow_version INTO cohort FROM public.decision_cases WHERE workspace_id=NEW.workspace_id AND id=NEW.case_id;
  IF cohort IS NOT NULL AND cohort<>2 THEN RAISE EXCEPTION 'Progressive Pack requires an Ultimate Case' USING ERRCODE='22023'; END IF;
  IF TG_OP='UPDATE' AND ROW(NEW.id,NEW.workspace_id,NEW.case_id,NEW.created_at)
    IS DISTINCT FROM ROW(OLD.id,OLD.workspace_id,OLD.case_id,OLD.created_at) THEN
   RAISE EXCEPTION 'Pack identity is immutable' USING ERRCODE='22023'; END IF;
 ELSIF TG_TABLE_NAME='case_data_pack_versions' THEN NEW.created_xid=pg_current_xact_id();
 ELSE
  SELECT created_xid INTO version_xid FROM public.case_data_pack_versions
   WHERE workspace_id=NEW.workspace_id AND case_id=NEW.case_id AND id=NEW.pack_version_id;
  IF NOT FOUND THEN RETURN NEW; END IF; -- The composite FK rejects an absent/cross-tenant version.
  IF version_xid IS DISTINCT FROM pg_current_xact_id() THEN
   RAISE EXCEPTION 'Entries belong to the immutable version creation transaction' USING ERRCODE='22023'; END IF;
  SELECT dataset_type INTO actual_type FROM public.datasets WHERE workspace_id=NEW.workspace_id AND id=NEW.dataset_id;
  IF NOT FOUND THEN RETURN NEW; END IF; -- The interpretation FK is authoritative.
  IF NEW.slot_key IN('transport_demand','transport_resources') AND actual_type IS DISTINCT FROM NEW.slot_key THEN
   RAISE EXCEPTION 'Pack slot conflicts with dataset contract' USING ERRCODE='22023'; END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER ultimate_pack_guard BEFORE INSERT OR UPDATE ON public.case_data_packs FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_pack_guard();
CREATE TRIGGER ultimate_pack_version_creation BEFORE INSERT ON public.case_data_pack_versions FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_pack_guard();
CREATE TRIGGER ultimate_pack_entry_creation BEFORE INSERT ON public.case_data_pack_entries FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_pack_guard();
CREATE TRIGGER ultimate_model_workspace BEFORE UPDATE ON public.logistics_models
 FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workspace();

CREATE FUNCTION dation_private.ultimate_case_pack_complete() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_TABLE_NAME='decision_cases' THEN
  IF NEW.workflow_version=2 AND NOT EXISTS(SELECT 1 FROM public.case_data_packs
   WHERE workspace_id=NEW.workspace_id AND case_id=NEW.id AND current_version_id IS NOT NULL) THEN
   RAISE EXCEPTION 'Ultimate Case and initial Pack/version must commit together' USING ERRCODE='23514'; END IF;
 ELSE
  IF EXISTS(SELECT 1 FROM public.case_data_packs WHERE id=NEW.id AND current_version_id IS NULL) THEN
   RAISE EXCEPTION 'Stable Pack must commit with a current version' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NULL;
END; $$;
CREATE CONSTRAINT TRIGGER ultimate_case_pack_complete AFTER INSERT ON public.decision_cases
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_case_pack_complete();
CREATE CONSTRAINT TRIGGER ultimate_pack_complete AFTER INSERT OR UPDATE ON public.case_data_packs
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_case_pack_complete();

CREATE FUNCTION dation_private.ultimate_run_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE c public.decision_cases;
BEGIN
 IF NEW.decision_case_id IS NOT NULL THEN
  SELECT * INTO c FROM public.decision_cases WHERE workspace_id=NEW.workspace_id AND id=NEW.decision_case_id;
  IF FOUND AND c.workflow_version<>NEW.workflow_version THEN
   RAISE EXCEPTION 'Run/Case cohorts differ' USING ERRCODE='22023'; END IF;
 END IF;
 IF TG_OP='UPDATE' AND ROW(NEW.workflow_version,NEW.logistics_model_version_id,NEW.data_pack_version_id,
  NEW.graph_definition_version,NEW.case_policy_hash,NEW.node_policy_hash,NEW.contract_hash,NEW.input_context_hash,
  NEW.transit_model_version,NEW.runtime_profile,NEW.result_schema_version)
 IS DISTINCT FROM ROW(OLD.workflow_version,OLD.logistics_model_version_id,OLD.data_pack_version_id,
  OLD.graph_definition_version,OLD.case_policy_hash,OLD.node_policy_hash,OLD.contract_hash,OLD.input_context_hash,
  OLD.transit_model_version,OLD.runtime_profile,OLD.result_schema_version) THEN
  RAISE EXCEPTION 'Run context pinning is immutable' USING ERRCODE='22023'; END IF;
 IF NEW.workflow_version=2 THEN
  IF c.context_frozen_at IS NULL OR NEW.case_policy_hash IS DISTINCT FROM c.case_policy_hash
    OR NEW.graph_definition_version IS DISTINCT FROM c.graph_definition_version THEN
   RAISE EXCEPTION 'Run requires the frozen Case policy/graph' USING ERRCODE='22023'; END IF;
  IF NOT EXISTS(SELECT 1 FROM public.case_data_pack_entries WHERE workspace_id=NEW.workspace_id
    AND case_id=NEW.decision_case_id AND pack_version_id=NEW.data_pack_version_id
    AND slot_key='transport_demand' AND dataset_id=NEW.dataset_id) THEN
   RAISE EXCEPTION 'Run primary raw Demand must belong to its Pack' USING ERRCODE='22023'; END IF;
  IF NEW.status='completed' AND (NEW.result_json->>'result_schema' IS DISTINCT FROM NEW.schema_version
    OR NEW.result_json->>'result_schema_version' IS DISTINCT FROM NEW.result_schema_version::text) THEN
   RAISE EXCEPTION 'Run/package schema mismatch' USING ERRCODE='22023'; END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER ultimate_run_context_guard BEFORE INSERT OR UPDATE ON public.decision_runs
 FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_run_guard();

-- Explicit object ACLs neutralize broad Supabase defaults for NEW objects only.
DO $$ DECLARE relation_name text; BEGIN
 FOREACH relation_name IN ARRAY ARRAY['logistics_models','logistics_model_versions','case_data_packs','case_data_pack_versions','case_data_pack_entries'] LOOP
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',relation_name);
  EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY',relation_name);
  EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC,anon,authenticated,service_role',relation_name);
  EXECUTE format('GRANT SELECT ON public.%I TO authenticated,service_role',relation_name);
  EXECUTE format('CREATE POLICY tenant_read ON public.%I FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id))',relation_name);
 END LOOP;
END; $$;
REVOKE ALL ON FUNCTION dation_private.ultimate_immutable(),dation_private.ultimate_case_guard(),
 dation_private.ultimate_pack_guard(),dation_private.ultimate_case_pack_complete(),dation_private.ultimate_run_guard(),dation_private.ultimate_dataset_identity()
 FROM PUBLIC,anon,authenticated,service_role;

-- Targeted dual-reader changes preserve existing function identities/ACLs/authority.
DO $reader$ DECLARE source text; BEGIN
 source=pg_get_functiondef('dation_private.list_decision_cases(text,integer,integer,boolean)'::regprocedure);
 IF strpos(source,'FROM page c JOIN public.datasets o')=0 OR strpos(source,'JOIN public.datasets f ON f.id=c.fleet_dataset_id')=0 THEN
  RAISE EXCEPTION 'Unexpected Case-list reader; review compatibility'; END IF;
 source=replace(source,'FROM page c JOIN public.datasets o','FROM page c LEFT JOIN public.datasets o');
 source=replace(source,'JOIN public.datasets f ON f.id=c.fleet_dataset_id','LEFT JOIN public.datasets f ON f.id=c.fleet_dataset_id');
 source=replace(source,'CASE WHEN summary_only THEN','CASE WHEN o.id IS NULL THEN NULL WHEN summary_only THEN');
 -- The second projection refers to f, not o.
 source=replace(source,'CASE WHEN o.id IS NULL THEN NULL WHEN summary_only THEN jsonb_build_object('||chr(10)||'     ''id'',f.id',
  'CASE WHEN f.id IS NULL THEN NULL WHEN summary_only THEN jsonb_build_object('||chr(10)||'     ''id'',f.id');
 EXECUTE source;
 source=pg_get_functiondef('public.platform_home(uuid,uuid)'::regprocedure);
 IF strpos(source,'JOIN datasets o ON o.id=c.orders_dataset_id')=0 THEN RAISE EXCEPTION 'Unexpected Home reader'; END IF;
 source=replace(source,'JOIN datasets o ON o.id=c.orders_dataset_id','LEFT JOIN datasets o ON o.id=c.orders_dataset_id');
 source=replace(source,'''last_activity_at'',c.last_activity_at,''is_demo''',
  '''workflow_version'',c.workflow_version,''logistics_model_version_id'',c.logistics_model_version_id,''planning_start'',c.planning_start,''planning_end'',c.planning_end,''last_activity_at'',c.last_activity_at,''is_demo''');
 source=replace(source,'o.canonical_filename,o.original_filename)',
  'o.canonical_filename,o.original_filename,''DC-''||upper(left(c.id::text,8)))');
 EXECUTE source;
 source=pg_get_functiondef('dation_private.dataset_referenced(uuid,uuid)'::regprocedure);
 source=replace(source,'BEGIN'||chr(10),'BEGIN'||chr(10)||
  ' IF EXISTS(SELECT 1 FROM public.case_data_pack_entries WHERE workspace_id=wid AND dataset_id=did) THEN RETURN true; END IF;'||chr(10));
 EXECUTE source;
 source=pg_get_functiondef('dation_private.dataset_case_usage(uuid,uuid)'::regprocedure);
 source=replace(source,'(c.orders_dataset_id=did OR c.fleet_dataset_id=did OR EXISTS(',
  '(c.orders_dataset_id=did OR c.fleet_dataset_id=did OR EXISTS(SELECT 1 FROM public.case_data_pack_entries e WHERE e.workspace_id=wid AND e.case_id=c.id AND e.dataset_id=did) OR EXISTS(');
 EXECUTE source;
END; $reader$;

NOTIFY pgrst,'reload schema';
COMMIT;
