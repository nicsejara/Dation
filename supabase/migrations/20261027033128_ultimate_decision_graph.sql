-- T5 read-only graph snapshot. No node-state table, admissions, engine or invalidation writes.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';

-- Definition JSON/hash is generated from the release-controlled Python registry below.
INSERT INTO dation_private.decision_definition_versions(version,definition_hash,definition_jsonb) VALUES('ULTIMATE_DECISION_GRAPH_V1','d4c7883c79ee9fd7f2406216112814d12d361f499afe814cb11a60b31ccd225a','{"schema_version":"decision_graph_definition_v1","version":"ULTIMATE_DECISION_GRAPH_V1","supported_bindings":["ULTIMATE_FOUNDATION_V1","ULTIMATE_DECISION_GRAPH_V1"],"nodes":[{"id":"logistics_assignment","version":"1","label":"Transport Plan","question":"\u00bfC\u00f3mo asignar la demanda a recursos y viajes?","implemented":true,"applicability":"ALWAYS","dependencies":[],"required_approvals":[],"required_inputs":["transport_demand","transport_resources"],"read_set":["transport_demand","transport_resources","model","horizon","case_policy","node_policy"],"decision_variables":["assignments","trips","consolidation","fractions"],"hard_constraints":["guaranteed_capacity","finite_availability","compatibility","split_policy","case_guardrails"],"soft_constraints":["case_preferences"],"objectives":["case_primary_goal"],"outputs":["transport_plan_v1"],"evidence":["engine_core_v1","decision_evidence_v1"],"downstream_contract":"approved_transport_plan_v1"},{"id":"logistics_scheduling","version":"1","label":"Day Scheduling","question":"\u00bfQu\u00e9 d\u00eda debe despacharse cada viaje aprobado?","implemented":true,"applicability":"UPSTREAM_HAS_TRIPS","dependencies":["logistics_assignment"],"required_approvals":["logistics_assignment"],"required_inputs":[],"read_set":["approved:logistics_assignment","horizon","node_policy"],"decision_variables":["dispatch_day"],"hard_constraints":["fixed_upstream_trips","inclusive_horizon","resource_cycle"],"soft_constraints":["service_dates"],"objectives":["case_primary_goal"],"outputs":["day_scheduling_v1"],"evidence":["engine_core_v1","decision_evidence_v1"],"downstream_contract":null}],"dependency_closure":{"logistics_assignment":[],"logistics_scheduling":["logistics_assignment"]}}');

CREATE FUNCTION dation_private.t5_run_projection(r public.decision_runs) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('id',r.id,'node_id',r.node_id,'status',r.status,'created_at',r.created_at,
  'approved_at',r.approved_at,'approved_by',dation_private.team_person(r.workspace_id,r.approved_by_user_id),
  'approval_actor',r.approved_by,'created_by',dation_private.team_person(r.workspace_id,r.created_by_user_id),'superseded_at',r.superseded_at,
  'upstream_run_id',r.upstream_run_id,'logistics_model_version_id',r.logistics_model_version_id,
  'case_policy_hash',r.case_policy_hash,'error',left(r.error_message,500),
  'graph_snapshot',CASE WHEN octet_length((r.configuration_json->'ultimate_graph')::text)<=16384
   THEN r.configuration_json->'ultimate_graph' ELSE NULL END,
  'result_published',r.status='completed' AND r.result_fingerprint IS NOT NULL
   AND EXISTS(SELECT 1 FROM public.decision_result_artifacts a WHERE a.workspace_id=r.workspace_id AND a.run_id=r.id
    AND a.result_fingerprint=r.result_fingerprint AND a.kind='CORE' AND a.publication_state='READY')
   AND NOT EXISTS(SELECT 1 FROM public.decision_result_artifacts a WHERE a.workspace_id=r.workspace_id AND a.run_id=r.id AND a.publication_state<>'READY'),
  'trip_count',CASE WHEN jsonb_typeof(r.result_json#>'{metrics,trip_count}')='number'
   AND r.result_json#>>'{metrics,trip_count}' ~ '^[0-9]+$' THEN r.result_json#>'{metrics,trip_count}' ELSE NULL END);
$$;
REVOKE ALL ON FUNCTION dation_private.t5_run_projection(public.decision_runs) FROM PUBLIC,anon,authenticated,service_role;

CREATE FUNCTION public.platform_ultimate_graph(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid,
 operation text DEFAULT 'snapshot',target_node_id text DEFAULT NULL,selected_run_id uuid DEFAULT NULL,
 page_limit integer DEFAULT 25,page_offset integer DEFAULT 0) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c public.decision_cases; role_name text; body jsonb; runs jsonb; selected jsonb; history jsonb; total bigint;
BEGIN
 role_name=dation_private.team_actor(target_workspace_id,actor_user_id);
 IF operation NOT IN('snapshot','configure','history','cohort') OR operation IS NULL
 OR target_node_id IS NOT NULL AND target_node_id NOT IN('logistics_assignment','logistics_scheduling')
 OR operation IN('configure','history') AND target_node_id IS NULL
 OR page_limit NOT BETWEEN 1 AND 50 OR page_offset NOT BETWEEN 0 AND 1000000 THEN
  RAISE EXCEPTION 'Invalid graph request' USING ERRCODE='22023'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.workspace_ddas WHERE workspace_id=target_workspace_id AND dda_id='logistics' AND status='enabled') THEN
  RAISE EXCEPTION 'DDA access denied' USING ERRCODE='42501'; END IF;
 -- Same order as Pack/context/admission writers. One coherent, authorized input snapshot.
 PERFORM 1 FROM public.workspaces WHERE id=target_workspace_id FOR SHARE;
 SELECT * INTO c FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=target_case_id FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
 role_name=dation_private.team_actor(target_workspace_id,actor_user_id);
 IF operation='cohort' THEN RETURN jsonb_build_object('workflow_version',c.workflow_version); END IF;
 IF c.workflow_version<>2 OR c.graph_definition_version NOT IN('ULTIMATE_FOUNDATION_V1','ULTIMATE_DECISION_GRAPH_V1') THEN
  RAISE EXCEPTION 'Unsupported graph cohort/binding' USING ERRCODE='22023'; END IF;
 IF selected_run_id IS NOT NULL THEN
  SELECT dation_private.t5_run_projection(r) INTO selected FROM public.decision_runs r
  WHERE r.workspace_id=target_workspace_id AND r.decision_case_id=c.id AND r.workflow_version=2 AND r.id=selected_run_id
   AND (target_node_id IS NULL OR r.node_id=target_node_id);
  IF NOT FOUND THEN RAISE EXCEPTION 'Run not found in Case/node' USING ERRCODE='P0002'; END IF;
 END IF;
 IF operation='history' THEN
  SELECT count(*) INTO total FROM public.decision_runs WHERE workspace_id=target_workspace_id AND decision_case_id=c.id AND workflow_version=2 AND node_id=target_node_id;
  SELECT coalesce(jsonb_agg(dation_private.t5_run_projection(r) ORDER BY r.created_at DESC,r.id DESC),'[]') INTO history
   FROM (SELECT * FROM public.decision_runs WHERE workspace_id=target_workspace_id AND decision_case_id=c.id AND workflow_version=2 AND node_id=target_node_id
    ORDER BY created_at DESC,id DESC LIMIT page_limit OFFSET page_offset) r;
  RETURN jsonb_build_object('items',history,'total',total,'limit',page_limit,'offset',page_offset);
 END IF;
 IF (SELECT count(*) FROM public.decision_runs WHERE workspace_id=target_workspace_id AND decision_case_id=c.id AND workflow_version=2 AND superseded_at IS NULL)>100 THEN
  RAISE EXCEPTION 'Ambiguous/unbounded active history' USING ERRCODE='22023'; END IF;
 body=dation_private.t3_case_context(c,actor_user_id);
 SELECT coalesce(jsonb_agg(dation_private.t5_run_projection(r)||jsonb_build_object('history_count',
  (SELECT count(*) FROM public.decision_runs h WHERE h.workspace_id=r.workspace_id AND h.decision_case_id=r.decision_case_id AND h.node_id=r.node_id))),'[]')
 INTO runs FROM public.decision_runs r WHERE r.workspace_id=target_workspace_id AND r.decision_case_id=c.id AND r.workflow_version=2 AND r.superseded_at IS NULL;
 RETURN body||jsonb_build_object('definition',(SELECT to_jsonb(d) FROM dation_private.decision_definition_versions d WHERE version='ULTIMATE_DECISION_GRAPH_V1'),
  'entries',coalesce((SELECT jsonb_agg(jsonb_build_object('slot_key',e.slot_key,'contract_hash',e.contract_hash,
   'canonical_sha256',e.canonical_sha256,'normalizer_version',e.normalizer_version,'record_count',e.record_count,
   'model_version_id',o.model_version_id,'summary',o.summary) ORDER BY e.slot_key)
   FROM public.case_data_pack_entries e JOIN dation_private.ultimate_input_objects o ON o.workspace_id=e.workspace_id AND o.dataset_id=e.dataset_id
   WHERE e.workspace_id=c.workspace_id AND e.case_id=c.id AND e.pack_version_id=(body#>>'{pack,current_version_id}')::uuid),'[]'),
  'runs',runs,'selected_run',selected,
  'history_counts',(SELECT jsonb_object_agg(n.id,(SELECT count(*) FROM public.decision_runs h
    WHERE h.workspace_id=c.workspace_id AND h.decision_case_id=c.id AND h.workflow_version=2 AND h.node_id=n.id))
    FROM (VALUES('logistics_assignment'),('logistics_scheduling')) n(id)),
  'permissions',coalesce(body->'permissions','{}')||jsonb_build_object('can_write',role_name IN('admin','operator') AND c.status<>'archived'));
END; $$;
REVOKE ALL ON FUNCTION public.platform_ultimate_graph(uuid,uuid,uuid,text,text,uuid,integer,integer) FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.platform_ultimate_graph(uuid,uuid,uuid,text,text,uuid,integer,integer) TO service_role;
COMMIT;
