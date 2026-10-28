from pathlib import Path
R=Path('/workspace/Dation');old=(R/'supabase/migrations/20261027140333_ultimate_result_publication.sql').read_text()
body=old[old.index('CREATE FUNCTION public.platform_ultimate_execution'):old.index('-- Legacy workers')].replace('CREATE FUNCTION public.platform_ultimate_execution','CREATE OR REPLACE FUNCTION public.platform_ultimate_execution')
body=body.replace("enabled boolean;", "enabled boolean; scheduling_enabled boolean; node_key text=coalesce(arguments->>'node_id',arguments#>>'{client_request,node_id}','logistics_assignment'); schema_name text; engine_name text; ih text; upstream public.decision_runs; source_job public.dispatch_run_jobs;")
body=body.replace('cid=r.decision_case_id; END IF;', 'cid=r.decision_case_id;node_key=r.node_id; END IF;')
body=body.replace('SELECT ultimate_admissions_enabled INTO enabled','SELECT ultimate_admissions_enabled,ultimate_scheduling_admissions_enabled INTO enabled,scheduling_enabled')
body=body.replace("IF operation='state' THEN", "IF node_key NOT IN('logistics_assignment','logistics_scheduling') THEN RAISE EXCEPTION 'Unknown node' USING ERRCODE='22023'; END IF;\n IF operation='state' THEN")
body=body.replace("RETURN body||jsonb_build_object('pinned_entries',entries,'admissions_enabled',enabled);", """IF node_key='logistics_scheduling' THEN
    SELECT * INTO upstream FROM public.decision_runs WHERE workspace_id=wid AND decision_case_id=cid AND workflow_version=2 AND node_id='logistics_assignment'
     AND approved_at IS NOT NULL AND superseded_at IS NULL AND (arguments->'source_transport_plan' IS NULL OR arguments->'source_transport_plan'='null'::jsonb OR
       (id::text=arguments#>>'{source_transport_plan,run_id}' AND result_fingerprint=arguments#>>'{source_transport_plan,result_fingerprint}'));
    IF upstream.id IS NULL OR NOT dation_private.t8_fresh(upstream) OR upstream.status<>'completed' OR (upstream.result_json#>>'{metrics,trip_count}')::integer=0 THEN
     RAISE EXCEPTION 'Exact current approved D1 required (empty plan is NOT_APPLICABLE)' USING ERRCODE='22023'; END IF;
    IF (SELECT count(*) FROM public.decision_runs WHERE workspace_id=wid AND decision_case_id=cid AND workflow_version=2 AND node_id='logistics_assignment' AND approved_at IS NOT NULL AND superseded_at IS NULL)<>1 THEN RAISE EXCEPTION 'Ambiguous approved D1' USING ERRCODE='22023'; END IF;
    SELECT * INTO source_job FROM public.dispatch_run_jobs WHERE workspace_id=wid AND run_id=upstream.id;
    body=body||jsonb_build_object('source_run',to_jsonb(upstream),'source_input',source_job.request_json->'input','source_artifacts',
     (SELECT jsonb_agg(to_jsonb(a) ORDER BY a.kind,a.part_key) FROM public.decision_result_artifacts a WHERE a.workspace_id=wid AND a.run_id=upstream.id));
   END IF;
   RETURN body||jsonb_build_object('pinned_entries',entries,'admissions_enabled',enabled,'scheduling_enabled',scheduling_enabled);""")
body=body.replace("IF NOT enabled THEN", "IF NOT enabled OR node_key='logistics_scheduling' AND NOT scheduling_enabled THEN")
body=body.replace("node_id='logistics_assignment';\n  SELECT owner_user_id", "node_id=node_key;\n  SELECT owner_user_id")
marker="  input=arguments->'input';ctx=input->'context';policy=ctx->'node_policy';reads=arguments->'graph_snapshot'->'read_set';"
body=body.replace(marker,marker+"""
  schema_name=CASE node_key WHEN 'logistics_assignment' THEN 'transport_plan_v1' ELSE 'day_scheduling_v1' END;
  engine_name=CASE node_key WHEN 'logistics_assignment' THEN 'transport_plan' ELSE 'day_scheduling' END;
  ih=dation_private.t9_input_hash(ctx,jsonb_build_object('engine_name',engine_name,'engine_version','2.0.0','runtime_profile',schema_name,'result_schema',schema_name,'result_schema_version',1),
     CASE WHEN node_key='logistics_scheduling' THEN input->'source_transport_plan' ELSE NULL END);
  IF node_key='logistics_scheduling' THEN
   SELECT * INTO upstream FROM public.decision_runs WHERE workspace_id=wid AND decision_case_id=cid AND id=(input#>>'{source_transport_plan,run_id}')::uuid
    AND workflow_version=2 AND node_id='logistics_assignment' AND approved_at IS NOT NULL AND superseded_at IS NULL AND result_fingerprint=input#>>'{source_transport_plan,result_fingerprint}';
   SELECT * INTO source_job FROM public.dispatch_run_jobs WHERE workspace_id=wid AND run_id=upstream.id;
   IF upstream.id IS NULL OR NOT dation_private.t8_fresh(upstream) OR upstream.result_fingerprint IS DISTINCT FROM arguments#>>'{client_request,source_transport_plan,result_fingerprint}'
    OR input->'source_transport_plan' IS DISTINCT FROM arguments#>'{client_request,source_transport_plan}'
    OR input#>>'{source_core,decision,run_id}' IS DISTINCT FROM upstream.id::text OR input#>>'{source_core,context,workspace_id}' IS DISTINCT FROM wid::text
    OR input#>>'{source_core,context,case_id}' IS DISTINCT FROM cid::text OR dation_private.t9_core_hash(input->'source_core') IS DISTINCT FROM upstream.core_fingerprint
    OR input#>>'{source_evidence,core_result_fingerprint}' IS DISTINCT FROM upstream.core_fingerprint
    OR input->'resources' IS DISTINCT FROM source_job.request_json#>'{input,resources}' OR input->'model' IS DISTINCT FROM source_job.request_json#>'{input,model}'
    OR input->'source_temporal_certified' IS DISTINCT FROM 'true'::jsonb OR (upstream.result_json#>>'{metrics,trip_count}')::integer=0
    THEN RAISE EXCEPTION 'Invalid exact approved D1 handoff' USING ERRCODE='22023'; END IF;
  END IF;
""")
body=body.replace("ARRAY['case_policy','horizon','model','node_policy','transport_demand','transport_resources']::text[]", "CASE WHEN node_key='logistics_assignment' THEN ARRAY['case_policy','horizon','model','node_policy','transport_demand','transport_resources']::text[] ELSE ARRAY['approved:logistics_assignment','horizon','node_policy']::text[] END")
body=body.replace("IS DISTINCT FROM 'logistics_assignment' OR input->>'run_id'", "IS DISTINCT FROM node_key OR input->>'run_id'")
body=body.replace('dation_private.t8_input_hash(ctx)', 'ih')
body=body.replace('status,configuration_json,progress_json)', 'status,configuration_json,progress_json,upstream_run_id)')
body=body.replace("2,cid,'logistics_assignment',c.logistics_model_version_id", "2,cid,node_key,c.logistics_model_version_id")
body=body.replace("'DATION_TRANSIT_V1','transport_plan_v1',1,'transport_plan','2.0.0','transport_plan_v1','queued',", "'DATION_TRANSIT_V1',schema_name,1,engine_name,'2.0.0',schema_name,'queued',")
body=body.replace("jsonb_build_object('stage','queued')) RETURNING * INTO r;", "jsonb_build_object('stage','queued'),upstream.id) RETURNING * INTO r;")
body=body.replace("AND id<>rid AND superseded_at IS NULL AND node_id IN('logistics_assignment','logistics_scheduling')", "AND id<>rid AND superseded_at IS NULL AND node_id IN('logistics_assignment','logistics_scheduling') AND (node_key='logistics_assignment' OR node_id='logistics_scheduling')")
body=body.replace("'workflow_version',2,'engine_name','transport_plan','engine_version','2.0.0','schema_version','transport_plan_v1',\n    'runtime_profile','transport_plan_v1'", "'workflow_version',2,'engine_name',engine_name,'engine_version','2.0.0','schema_version',schema_name,\n    'runtime_profile',schema_name")
body=body.replace("'client_request',arguments->'client_request'),intent);", "'client_request',arguments->'client_request')||CASE WHEN node_key='logistics_scheduling' THEN jsonb_build_object('source_package',upstream.result_json,'source_artifacts',(SELECT jsonb_agg(to_jsonb(a) ORDER BY a.kind,a.part_key) FROM public.decision_result_artifacts a WHERE a.workspace_id=wid AND a.run_id=upstream.id)) ELSE '{}'::jsonb END,intent);")
body=body.replace("OR body->>'assembler_version' IS DISTINCT FROM 'RESULT_ASSEMBLER_D1_V1'", "OR body->>'assembler_version' IS DISTINCT FROM CASE WHEN r.node_id='logistics_assignment' THEN 'RESULT_ASSEMBLER_D1_V1' ELSE 'RESULT_ASSEMBLER_D2_V1' END\n    OR r.node_id='logistics_scheduling' AND (body->'source_transport_plan' IS DISTINCT FROM j.request_json#>'{input,source_transport_plan}' OR body#>>'{fingerprints,upstream_result_fingerprint}' IS DISTINCT FROM j.request_json#>>'{input,source_transport_plan,result_fingerprint}')")
body=body.replace("IS DISTINCT FROM\n    CASE WHEN node_key='logistics_assignment' THEN ARRAY['case_policy','horizon','model','node_policy','transport_demand','transport_resources']::text[] ELSE ARRAY['approved:logistics_assignment','horizon','node_policy']::text[] END", "IS DISTINCT FROM\n    (CASE WHEN node_key='logistics_assignment' THEN ARRAY['case_policy','horizon','model','node_policy','transport_demand','transport_resources']::text[] ELSE ARRAY['approved:logistics_assignment','horizon','node_policy']::text[] END)")
body=body.replace("IS DISTINCT FROM CASE WHEN r.node_id='logistics_assignment' THEN 'RESULT_ASSEMBLER_D1_V1' ELSE 'RESULT_ASSEMBLER_D2_V1' END", "IS DISTINCT FROM (CASE WHEN r.node_id='logistics_assignment' THEN 'RESULT_ASSEMBLER_D1_V1' ELSE 'RESULT_ASSEMBLER_D2_V1' END)")
body=body.replace('jsonb_agg(to_jsonb(a) ORDER BY a.kind,a.part_key) FROM public.decision_result_artifacts a WHERE a.workspace_id=wid AND a.run_id=upstream.id','jsonb_agg(to_jsonb(ar) ORDER BY ar.kind,ar.part_key) FROM public.decision_result_artifacts ar WHERE ar.workspace_id=wid AND ar.run_id=upstream.id')
# Fail generation if a required versioned branch was not specialized.
assert 'schema_name,1,engine_name' in body and 'upstream.id) RETURNING' in body
pre="""-- T9: D2 on the same admission, queue, artifact and atomic finish protocol.
BEGIN;
SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='90s';
ALTER TABLE dation_private.platform_release ADD COLUMN ultimate_scheduling_admissions_enabled boolean NOT NULL DEFAULT false;
CREATE FUNCTION dation_private.t9_input_hash(c jsonb,identity jsonb,upstream jsonb DEFAULT NULL) RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
BEGIN
 c=c-'case_name'-'display_metadata';c=jsonb_set(c,'{case_policy}',dation_private.t8_policy_projection(c->'case_policy'));c=jsonb_set(c,'{node_policy}',dation_private.t8_policy_projection(c->'node_policy'));
 c=jsonb_set(c,'{read_set}',(SELECT jsonb_agg(x ORDER BY x->>'slot') FROM jsonb_array_elements(c->'read_set') x));c=jsonb_set(c,'{active_dimensions}',(SELECT jsonb_agg(x ORDER BY x) FROM jsonb_array_elements(c->'active_dimensions') x));
 RETURN dation_private.t8_hash('INPUT_CONTEXT',jsonb_build_object('context',c,'runtime_identity',identity,'transit_model_version','DATION_TRANSIT_V1','upstream',upstream));
END; $$;
CREATE FUNCTION dation_private.t9_core_hash(v jsonb) RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE transport jsonb=v->'transport_plan'; metrics jsonb=v->'metrics'; trips jsonb;
BEGIN
 SELECT jsonb_agg(jsonb_set(jsonb_set(t,'{orders}',(SELECT jsonb_agg(a ORDER BY a->>'order_id') FROM jsonb_array_elements(t->'orders') a)),'{reason_codes}',coalesce((SELECT jsonb_agg(x ORDER BY x) FROM jsonb_array_elements(t->'reason_codes') x),'[]')) ORDER BY t->>'trip_id') INTO trips FROM jsonb_array_elements(transport->'trips') t;
 transport=jsonb_set(transport,'{trips}',coalesce(trips,'[]'));
 transport=jsonb_set(transport,'{unassigned_demand}',coalesce((SELECT jsonb_agg(t ORDER BY t->>'order_id') FROM jsonb_array_elements(transport->'unassigned_demand') t),'[]'));
 metrics=jsonb_set(metrics,'{coverage_by_priority}',(SELECT jsonb_agg(t ORDER BY t->>'priority') FROM jsonb_array_elements(metrics->'coverage_by_priority') t));
 RETURN dation_private.t8_hash('CORE_RESULT',jsonb_build_object('contract_version',v->'contract_version','result_schema',v->'result_schema','result_schema_version',v->'result_schema_version','input_context_hash',v->'input_context_hash',
  'decision',jsonb_build_object('node_id',v#>'{decision,node_id}','decision_type',v#>'{decision,decision_type}'),'engine',(v->'engine')-'result_generated_at','feasibility',v->'feasibility','metrics',metrics,'transport_plan',transport,'schedule',v->'schedule','source_transport_plan',v->'source_transport_plan'));
END; $$;
"""
post="""
DO $$ DECLARE source text; BEGIN
 source=pg_get_functiondef('public.platform_ultimate_graph(uuid,uuid,uuid,text,text,uuid,integer,integer)'::regprocedure);
 IF strpos(source,'RETURN body||jsonb_build_object(')=0 THEN RAISE EXCEPTION 'Unexpected graph projection'; END IF;
 EXECUTE replace(source,'RETURN body||jsonb_build_object(', 'RETURN body||jsonb_build_object(''runtime_capabilities'',jsonb_build_object(''logistics_scheduling'',(SELECT ultimate_scheduling_admissions_enabled FROM dation_private.platform_release WHERE singleton)))||jsonb_build_object(');
END; $$;
REVOKE ALL ON FUNCTION dation_private.t9_input_hash(jsonb,jsonb,jsonb),dation_private.t9_core_hash(jsonb) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_ultimate_execution(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_ultimate_execution(uuid,uuid,text,jsonb) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
"""
(R/'supabase/migrations/20261027175943_ultimate_day_scheduling.sql').write_text(pre+body+post)
print('Generated T9 migration:',len((pre+body+post).splitlines()),'lines')
