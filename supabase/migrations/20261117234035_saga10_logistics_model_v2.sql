-- Saga 10 G1: opt-in configuration evolution. No backfill or engine activation.
-- Existing JSONB snapshots, tenant FKs, RLS, CAS and immutable triggers remain.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';
ALTER TABLE dation_private.platform_release
 ADD COLUMN IF NOT EXISTS saga10_schema_enabled boolean NOT NULL DEFAULT false,
 ADD COLUMN IF NOT EXISTS saga10_ui_enabled boolean NOT NULL DEFAULT false,
 ADD COLUMN IF NOT EXISTS saga10_optimization_enabled boolean NOT NULL DEFAULT false;

-- Preserve the exact v1 validator and its behavior on every old snapshot.
DO $$ BEGIN
 IF to_regprocedure('dation_private.saga10_configuration_v1_valid(jsonb)') IS NULL THEN
  ALTER FUNCTION dation_private.t3_configuration_valid(jsonb) RENAME TO saga10_configuration_v1_valid;
 END IF;
END $$;

CREATE OR REPLACE FUNCTION dation_private.saga10_catalog_valid(c jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE p jsonb; part jsonb; key text;
BEGIN
 IF jsonb_typeof(c) IS DISTINCT FROM 'object' OR c-ARRAY['profile','input_mode','split_policy','compatibility_policy','co_load_pairs','products','logistic_units','presentations']<>'{}'
 OR coalesce(c->>'profile','') NOT IN('PALLETIZED','PACKAGED','DRY_BULK','LIQUID_BULK','SPECIALIZED','MIXED')
 OR coalesce(c->>'input_mode','') NOT IN('direct','catalog') OR coalesce(c->>'split_policy','') NOT IN('INDIVISIBLE','DISCRETE','CONTINUOUS')
 OR coalesce(c->>'compatibility_policy','') NOT IN('UNIFORM_DECLARED','CATEGORIZED') THEN RETURN false; END IF;
 FOREACH key IN ARRAY ARRAY['products','logistic_units','presentations','co_load_pairs'] LOOP
  IF jsonb_typeof(c->key) IS DISTINCT FROM 'array' THEN RETURN false; END IF;
 END LOOP;
 IF jsonb_array_length(c->'products')>100 OR jsonb_array_length(c->'logistic_units')>50 OR jsonb_array_length(c->'presentations')>200 OR jsonb_array_length(c->'co_load_pairs')>100 THEN RETURN false; END IF;
 IF c->>'input_mode'='direct' THEN RETURN jsonb_array_length(c->'products')+jsonb_array_length(c->'logistic_units')+jsonb_array_length(c->'presentations')=0; END IF;
 IF jsonb_array_length(c->'products')=0 OR jsonb_array_length(c->'presentations')=0 THEN RETURN false; END IF;
 IF EXISTS(SELECT 1 FROM jsonb_array_elements(c->'products') x GROUP BY x->>'product_id' HAVING count(*)>1)
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(c->'products') x GROUP BY lower(btrim(x->>'name')) HAVING count(*)>1)
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(c->'products') x WHERE x->>'code' IS NOT NULL GROUP BY lower(x->>'code') HAVING count(*)>1)
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(c->'logistic_units') x GROUP BY x->>'logistic_unit_id' HAVING count(*)>1)
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(c->'presentations') x GROUP BY x->>'presentation_id' HAVING count(*)>1) THEN RETURN false; END IF;
 FOR p IN SELECT x FROM jsonb_array_elements(c->'products') x LOOP
  IF jsonb_typeof(p) IS DISTINCT FROM 'object' OR coalesce(p->>'product_id','') !~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$'
   OR length(btrim(coalesce(p->>'name',''))) NOT BETWEEN 1 AND 120 OR length(btrim(coalesce(p->>'unit_label',''))) NOT BETWEEN 1 AND 40
   OR coalesce(p->>'units_per_package','') !~ '^[1-9][0-9]{0,6}$' OR (p->>'units_per_package')::numeric>1000000
   OR jsonb_typeof(p->'compatibility_groups') IS DISTINCT FROM 'array' THEN RETURN false; END IF;
 END LOOP;
 FOR p IN SELECT x FROM jsonb_array_elements(c->'logistic_units') x LOOP
  IF coalesce(p->>'logistic_unit_id','') !~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$' OR length(btrim(coalesce(p->>'label',''))) NOT BETWEEN 1 AND 120
   OR coalesce(p->>'type','') NOT IN('PALLET','BOX','CRATE','BIG_BAG','OTHER') THEN RETURN false; END IF;
 END LOOP;
 FOR p IN SELECT x FROM jsonb_array_elements(c->'presentations') x LOOP
  IF coalesce(p->>'presentation_id','') !~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$' OR length(btrim(coalesce(p->>'label',''))) NOT BETWEEN 1 AND 120
   OR coalesce(p->>'quantity_kind','') NOT IN('DISCRETE','CONTINUOUS') OR coalesce(p->>'quantity_unit','') NOT IN('presentation','kg','t','m3','l')
   OR jsonb_typeof(p->'components') IS DISTINCT FROM 'array' OR jsonb_array_length(p->'components') NOT BETWEEN 1 AND 30 THEN RETURN false; END IF;
  IF p->>'logistic_unit_id' IS NOT NULL AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(c->'logistic_units') u WHERE u->>'logistic_unit_id'=p->>'logistic_unit_id') THEN RETURN false; END IF;
  IF EXISTS(SELECT 1 FROM jsonb_array_elements(p->'components') x GROUP BY x->>'product_id' HAVING count(*)>1) THEN RETURN false; END IF;
  FOR part IN SELECT x FROM jsonb_array_elements(p->'components') x LOOP
   IF NOT EXISTS(SELECT 1 FROM jsonb_array_elements(c->'products') x WHERE x->>'product_id'=part->>'product_id')
    OR coalesce(part->>'quantity','') !~ '^[0-9]+(\.[0-9]{1,6})?$' OR (part->>'quantity')::numeric<=0 THEN RETURN false; END IF;
   IF p->>'quantity_kind'='DISCRETE' AND (part->>'quantity')::numeric<>trunc((part->>'quantity')::numeric) THEN RETURN false; END IF;
  END LOOP;
  IF p->>'quantity_kind'='DISCRETE' AND p->>'quantity_unit'<>'presentation' OR p->>'quantity_kind'='CONTINUOUS' AND (p->>'quantity_unit'='presentation' OR p->>'logistic_unit_id' IS NOT NULL OR jsonb_array_length(p->'components')<>1)
   OR c->>'split_policy'='DISCRETE' AND p->>'quantity_kind'='CONTINUOUS' THEN RETURN false; END IF;
 END LOOP;
 RETURN true;
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN RETURN false;
END $$;

CREATE OR REPLACE FUNCTION dation_private.t3_configuration_valid(value jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
BEGIN
 IF value->>'version'='1' THEN RETURN dation_private.saga10_configuration_v1_valid(value); END IF;
 IF value->'version' IS DISTINCT FROM '2'::jsonb OR NOT dation_private.saga10_catalog_valid(value->'cargo')
 OR jsonb_typeof(value->'consolidation_permitted') IS DISTINCT FROM 'boolean'
 OR jsonb_typeof(value->'resource_categories') IS DISTINCT FROM 'array' OR jsonb_array_length(value->'resource_categories')>20
 OR EXISTS(SELECT 1 FROM jsonb_array_elements_text(value->'resource_categories') x WHERE x !~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')
 OR (SELECT count(*)<>count(DISTINCT x) FROM jsonb_array_elements_text(value->'resource_categories') x)
 OR (value->>'split_permitted')::boolean IS DISTINCT FROM (value#>>'{cargo,split_policy}'<>'INDIVISIBLE')
 OR (value->>'homogeneous_loads_declared')::boolean IS DISTINCT FROM (value#>>'{cargo,compatibility_policy}'='UNIFORM_DECLARED') THEN RETURN false; END IF;
 RETURN dation_private.saga10_configuration_v1_valid((value-ARRAY['cargo','consolidation_permitted','resource_categories'])||'{"version":1}'::jsonb);
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN RETURN false;
END $$;

-- Move the latest existing RPC intact behind a checked public facade. Its
-- workspace locks, permissions, optimistic revisions and replay checks remain.
DO $$ DECLARE source text; BEGIN
 IF to_regprocedure('dation_private.saga10_foundation_v1(uuid,uuid,text,jsonb)') IS NULL THEN
  ALTER FUNCTION public.platform_ultimate_foundation(uuid,uuid,text,jsonb) RENAME TO saga10_foundation_v1;
  ALTER FUNCTION public.saga10_foundation_v1(uuid,uuid,text,jsonb) SET SCHEMA dation_private;
  SELECT pg_get_functiondef('dation_private.saga10_foundation_v1(uuid,uuid,text,jsonb)'::regprocedure) INTO source;
  IF position('''logistics_model_config_v1''' IN source)=0 OR position('''ULTIMATE_DOMAIN_V1'',actor_user_id' IN source)=0 THEN RAISE EXCEPTION 'Saga10 foundation source differs; review before migrating'; END IF;
  source=replace(source,'''logistics_model_config_v1''','CASE WHEN m.draft_config_jsonb->>''version''=''2'' THEN ''logistics_model_config_v2'' ELSE ''logistics_model_config_v1'' END');
  source=replace(source,'''ULTIMATE_DOMAIN_V1'',actor_user_id','CASE WHEN m.draft_config_jsonb->>''version''=''2'' THEN ''SAGA10_DOMAIN_V2'' ELSE ''ULTIMATE_DOMAIN_V1'' END,actor_user_id');
  EXECUTE source;
 END IF;
END $$;

CREATE OR REPLACE FUNCTION public.platform_ultimate_foundation(target_workspace_id uuid,actor_user_id uuid,operation text,arguments jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE flags dation_private.platform_release; value jsonb; prior jsonb; result jsonb;
BEGIN
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
 SELECT * INTO flags FROM dation_private.platform_release WHERE singleton;
 IF operation IN('model_create','model_update') THEN value=arguments->'configuration'; END IF;
 IF operation='model_publish' THEN SELECT draft_config_jsonb INTO value FROM public.logistics_models WHERE workspace_id=target_workspace_id AND id=(arguments->>'model_id')::uuid; END IF;
 IF operation='case_create' THEN SELECT config_jsonb INTO value FROM public.logistics_model_versions WHERE workspace_id=target_workspace_id AND id=(arguments->>'logistics_model_version_id')::uuid; END IF;
 IF value->>'version'='2' AND NOT coalesce(flags.saga10_schema_enabled,false) THEN RAISE EXCEPTION 'Saga10 schema closed' USING ERRCODE='42501'; END IF;
 IF operation='model_update' THEN
  SELECT draft_config_jsonb INTO prior FROM public.logistics_models WHERE workspace_id=target_workspace_id AND id=(arguments->>'model_id')::uuid;
  IF prior->>'version'='2' AND value->>'version' IS DISTINCT FROM '2' THEN RAISE EXCEPTION 'Explicit clone required; no automatic v2 downgrade' USING ERRCODE='22023'; END IF;
 END IF;
 result=dation_private.saga10_foundation_v1(target_workspace_id,actor_user_id,operation,arguments);
 IF operation='capabilities' THEN RETURN result||jsonb_build_object('saga10_schema_enabled',flags.saga10_schema_enabled,
  'saga10_ui_enabled',flags.saga10_schema_enabled AND flags.saga10_ui_enabled,
  'saga10_optimization_enabled',flags.saga10_schema_enabled AND flags.saga10_optimization_enabled); END IF;
 RETURN result;
END $$;

-- Independent optimization gate, also enforced for callers of the SQL RPC.
DO $$ BEGIN
 IF to_regprocedure('dation_private.saga10_execution_v1(uuid,uuid,text,jsonb)') IS NULL THEN
  ALTER FUNCTION public.platform_ultimate_execution(uuid,uuid,text,jsonb) RENAME TO saga10_execution_v1;
  ALTER FUNCTION public.saga10_execution_v1(uuid,uuid,text,jsonb) SET SCHEMA dation_private;
 END IF;
END $$;
CREATE OR REPLACE FUNCTION public.platform_ultimate_execution(target_workspace_id uuid,actor_user_id uuid,operation text,arguments jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb; is_v2 boolean; enabled boolean;
BEGIN
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
 SELECT saga10_schema_enabled AND saga10_optimization_enabled INTO enabled FROM dation_private.platform_release WHERE singleton;
 IF operation='admit' THEN
  SELECT v.config_jsonb->>'version'='2' INTO is_v2 FROM public.decision_cases c JOIN public.logistics_model_versions v
   ON v.workspace_id=c.workspace_id AND v.id=c.logistics_model_version_id
   WHERE c.workspace_id=target_workspace_id AND c.id=(arguments->>'case_id')::uuid;
  IF is_v2 AND NOT coalesce(enabled,false) THEN RAISE EXCEPTION 'Saga10 optimization closed' USING ERRCODE='42501'; END IF;
 END IF;
 result=dation_private.saga10_execution_v1(target_workspace_id,actor_user_id,operation,arguments);
 IF operation='state' AND result#>>'{model_version,config_jsonb,version}'='2' THEN
  RETURN result||jsonb_build_object('admissions_enabled',coalesce((result->>'admissions_enabled')::boolean,false) AND coalesce(enabled,false),
   'scheduling_enabled',coalesce((result->>'scheduling_enabled')::boolean,false) AND coalesce(enabled,false));
 END IF;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION dation_private.saga10_execution_v1(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_ultimate_execution(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_ultimate_execution(uuid,uuid,text,jsonb) TO service_role;

REVOKE ALL ON FUNCTION dation_private.saga10_configuration_v1_valid(jsonb),dation_private.saga10_catalog_valid(jsonb),dation_private.t3_configuration_valid(jsonb),dation_private.saga10_foundation_v1(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_ultimate_foundation(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_ultimate_foundation(uuid,uuid,text,jsonb) TO service_role;
COMMIT;
