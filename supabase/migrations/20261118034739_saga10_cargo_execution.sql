-- Saga 10 G4/G5. Additive, dormant runtime profile; no flags enabled.
BEGIN;
SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='90s';
DO $$ DECLARE source text; old text; replacement text; pair jsonb; BEGIN
 source=pg_get_functiondef('dation_private.saga10_execution_v1(uuid,uuid,text,jsonb)'::regprocedure);
 IF strpos(source,'saga10_engine_version text')=0 THEN
  FOR pair IN SELECT value FROM jsonb_array_elements('[["DECLARE wid uuid=target_workspace_id;", "DECLARE saga10_engine_version text; saga10_profile text; wid uuid=target_workspace_id;"], ["  schema_name=CASE node_key", "  SELECT * INTO mv FROM public.logistics_model_versions WHERE workspace_id=wid AND id=c.logistics_model_version_id;\n  saga10_engine_version=CASE WHEN node_key=''logistics_assignment'' AND mv.config_jsonb->>''version''=''2'' THEN ''3.0.0'' ELSE ''2.0.0'' END;\n  saga10_profile=CASE WHEN saga10_engine_version=''3.0.0'' THEN ''transport_plan_cargo_v2'' WHEN node_key=''logistics_assignment'' THEN ''transport_plan_v1'' ELSE ''day_scheduling_v1'' END;\n  schema_name=CASE node_key"], ["''engine_version'',''2.0.0'',''runtime_profile'',schema_name", "''engine_version'',saga10_engine_version,''runtime_profile'',saga10_profile"], ["THEN ARRAY[''case_policy'',''horizon'',''model'',''node_policy'',''transport_demand'',''transport_resources'']::text[]", "THEN CASE WHEN dation_private.saga10_required_slot_count(mv.id)=3 THEN ARRAY[''case_policy'',''horizon'',''model'',''node_policy'',''order_lines'',''transport_demand'',''transport_resources'']::text[] ELSE ARRAY[''case_policy'',''horizon'',''model'',''node_policy'',''transport_demand'',''transport_resources'']::text[] END"], ["jsonb_array_length(arguments->''entries'') IS DISTINCT FROM 2", "jsonb_array_length(arguments->''entries'') IS DISTINCT FROM dation_private.saga10_required_slot_count(mv.id)"], ["   OR ((input->''model'')-''workspace_id''", "   OR (mv.config_jsonb->>''version''=''2'' AND input#>''{model,configuration}'' IS DISTINCT FROM mv.config_jsonb)\n   OR (mv.config_jsonb->>''version''<>''2'' AND (input->''model'') ? ''configuration'')\n   OR ((input->''model'')-''configuration''-''workspace_id''"], ["IN(''transport_demand'',''transport_resources'')", "IN(''transport_demand'',''order_lines'',''transport_resources'')"], ["''DATION_TRANSIT_V1'',schema_name,1,engine_name,''2.0.0'',schema_name", "''DATION_TRANSIT_V1'',saga10_profile,1,engine_name,saga10_engine_version,schema_name"], ["''engine_version'',''2.0.0'',''schema_version'',schema_name,\n    ''runtime_profile'',schema_name", "''engine_version'',saga10_engine_version,''schema_version'',schema_name,\n    ''runtime_profile'',saga10_profile"]]'::jsonb) LOOP
   old=pair->>0;replacement=pair->>1;
   IF strpos(source,old)=0 THEN RAISE EXCEPTION 'Unexpected Saga10 execution anchor: %',old; END IF;
   source=replace(source,old,replacement);
  END LOOP;
  EXECUTE source;
 END IF;
 source=pg_get_functiondef('dation_private.t8_read_set(public.decision_runs)'::regprocedure);
 IF strpos(source,'''order_lines''')=0 THEN
  IF strpos(source,'''transport_demand'',''transport_resources'',''scheduling_enrichment''')=0 THEN RAISE EXCEPTION 'Unexpected semantic read-set'; END IF;
  EXECUTE replace(source,'''transport_demand'',''transport_resources'',''scheduling_enrichment''','''transport_demand'',''order_lines'',''transport_resources'',''scheduling_enrichment''');
 END IF;
END $$;

-- Add exactly the cargo runtime identity while retaining every v1 context gate.
ALTER TABLE public.decision_runs DROP CONSTRAINT ultimate_run_context;
ALTER TABLE public.decision_runs ADD CONSTRAINT ultimate_run_context CHECK(CASE WHEN workflow_version=1 THEN
 schema_version NOT IN('transport_plan_v1','day_scheduling_v1') AND num_nonnulls(logistics_model_version_id,data_pack_version_id,graph_definition_version,case_policy_hash,node_policy_hash,
 contract_hash,input_context_hash,transit_model_version,runtime_profile,result_schema_version,invalidated_by_pack_version_id)=0
 ELSE num_nonnulls(decision_case_id,node_id,logistics_model_version_id,data_pack_version_id,graph_definition_version,case_policy_hash,
 node_policy_hash,contract_hash,input_context_hash,transit_model_version,runtime_profile,result_schema_version)=12
 AND orders_dataset_id IS NULL AND fleet_dataset_id IS NULL AND result_schema_version=1
 AND ((engine_version='2.0.0' AND runtime_profile=schema_version) OR
      (engine_version='3.0.0' AND runtime_profile='transport_plan_cargo_v2' AND node_id='logistics_assignment'))
 AND transit_model_version='DATION_TRANSIT_V1'
 AND ((node_id='logistics_assignment' AND schema_version='transport_plan_v1' AND engine_name='transport_plan')
 OR (node_id='logistics_scheduling' AND schema_version='day_scheduling_v1' AND engine_name='day_scheduling')) END);

-- Workers authenticate through their live lease; keep the original NULL-actor
-- restriction for these three operations instead of invoking team_actor(NULL).
CREATE OR REPLACE FUNCTION public.platform_ultimate_execution(target_workspace_id uuid,actor_user_id uuid,operation text,arguments jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb; is_v2 boolean; enabled boolean;
BEGIN
 IF actor_user_id IS NOT NULL OR operation NOT IN('prepared','prepare','finish') THEN
  PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
 END IF;
 SELECT saga10_schema_enabled AND saga10_optimization_enabled INTO enabled FROM dation_private.platform_release WHERE singleton;
 IF operation IN('admit','prepared','prepare') THEN
  SELECT v.config_jsonb->>'version'='2' INTO is_v2 FROM public.decision_cases c JOIN public.logistics_model_versions v
   ON v.workspace_id=c.workspace_id AND v.id=c.logistics_model_version_id
   WHERE c.workspace_id=target_workspace_id AND c.id=coalesce((arguments->>'case_id')::uuid,
    (SELECT decision_case_id FROM public.decision_runs WHERE workspace_id=target_workspace_id AND id=(arguments->>'run_id')::uuid));
  IF is_v2 AND NOT coalesce(enabled,false) THEN RAISE EXCEPTION 'Saga10 optimization closed' USING ERRCODE='42501'; END IF;
 END IF;
 result=dation_private.saga10_execution_v1(target_workspace_id,actor_user_id,operation,arguments);
 IF operation='state' AND result#>>'{model_version,config_jsonb,version}'='2' THEN
  RETURN result||jsonb_build_object('admissions_enabled',coalesce((result->>'admissions_enabled')::boolean,false) AND coalesce(enabled,false),
   'scheduling_enabled',coalesce((result->>'scheduling_enabled')::boolean,false) AND coalesce(enabled,false));
 END IF;
 RETURN result;
END $$;

-- Match Python's optional cargo canonical projection for exact D1 -> D2 binding.
CREATE OR REPLACE FUNCTION dation_private.saga10_cargo_projection(v jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT CASE WHEN v IS NULL OR v='null'::jsonb THEN v ELSE
  v || jsonb_build_object('allocations',coalesce((SELECT jsonb_agg(
    a||jsonb_build_object('products',(SELECT jsonb_agg(p ORDER BY p->>'product_id') FROM jsonb_array_elements(a->'products') p))
    ORDER BY a->>'trip_id',a->>'order_id',a->>'line_id') FROM jsonb_array_elements(v->'allocations') a),'[]'::jsonb),
    'lines',coalesce((SELECT jsonb_agg(l ORDER BY l->>'order_id',l->>'line_id') FROM jsonb_array_elements(v->'lines') l),'[]'::jsonb)) END;
$$;
DO $$ DECLARE source text; BEGIN
 source=pg_get_functiondef('dation_private.t9_core_hash(jsonb)'::regprocedure);
 IF strpos(source,'saga10_cargo_projection')=0 THEN
  IF strpos(source,'BEGIN')=0 THEN RAISE EXCEPTION 'Unexpected Core hash projection'; END IF;
  source=replace(source,'BEGIN',
   'BEGIN IF transport ? ''cargo'' THEN transport=jsonb_set(transport,''{cargo}'',dation_private.saga10_cargo_projection(transport->''cargo'')); END IF;');
  EXECUTE source;
 END IF;
END $$;
REVOKE ALL ON FUNCTION dation_private.saga10_cargo_projection(jsonb),dation_private.saga10_execution_v1(uuid,uuid,text,jsonb),dation_private.t8_read_set(public.decision_runs) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_ultimate_execution(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_ultimate_execution(uuid,uuid,text,jsonb) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
