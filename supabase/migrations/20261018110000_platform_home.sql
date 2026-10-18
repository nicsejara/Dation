-- Phase 4: bounded, read-only Home snapshot. Existing cases/runs remain authoritative.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';
CREATE FUNCTION public.platform_home(target_workspace_id uuid, actor_user_id uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE member_role text; recent jsonb; attention jsonb; attention_total bigint;
BEGIN
 SELECT m.access_role INTO member_role
 FROM workspace_members m JOIN workspaces w ON w.id=m.workspace_id
 JOIN profiles p ON p.id=m.user_id
 JOIN auth.users u ON u.id=m.user_id AND u.email_confirmed_at IS NOT NULL
 WHERE m.workspace_id=target_workspace_id AND m.user_id=actor_user_id
   AND m.status='active' AND w.status='active';
 IF NOT FOUND THEN RAISE EXCEPTION 'Membership denied' USING ERRCODE='42501'; END IF;
 PERFORM set_config('dation.workspace_id',target_workspace_id::text,true);

 -- Three recent, non-archived cases. Run summaries are read in this same snapshot;
 -- cached state alone must never determine an approval or the current version.
 SELECT coalesce(jsonb_agg(jsonb_build_object(
   'case',jsonb_build_object('id',c.id,'status',c.status,'state_json',c.state_json,
     'orders_dataset_id',c.orders_dataset_id,'fleet_dataset_id',c.fleet_dataset_id,
     'last_activity_at',c.last_activity_at),
   'label',coalesce(nullif(o.label,''),o.canonical_filename,o.original_filename),
   'summaries',dation_private.decision_case_history(c.id,NULL,0,0)->'summaries'
 ) ORDER BY c.last_activity_at DESC,c.id DESC),'[]') INTO recent
 FROM (SELECT * FROM decision_cases WHERE workspace_id=target_workspace_id
   AND status IN('active','completed') ORDER BY last_activity_at DESC,id DESC LIMIT 3) c
 JOIN datasets o ON o.id=c.orders_dataset_id AND o.workspace_id=target_workspace_id;

 attention='[]'; attention_total=0;
 -- Approval is currently workspace-wide for admins/operators, not a personal
 -- assignment. Do not infer owners or invent reviewer responsibilities.
 IF member_role IN('admin','operator') THEN
  WITH candidates AS (
   SELECT c.id AS case_id,c.last_activity_at,r.id AS run_id,r.node_id,
     count(*) OVER() AS total
   FROM decision_cases c
   CROSS JOIN (VALUES ('logistics_assignment'::text),('logistics_scheduling')) n(node_id)
   JOIN LATERAL (SELECT id,node_id,status,approved_at,superseded_at,upstream_run_id
     FROM decision_runs WHERE workspace_id=target_workspace_id
       AND decision_case_id=c.id AND node_id=n.node_id
     ORDER BY created_at DESC,id DESC LIMIT 1) r ON true
   WHERE c.workspace_id=target_workspace_id AND c.status='active'
     AND r.status='completed' AND r.approved_at IS NULL AND r.superseded_at IS NULL
     AND (r.node_id='logistics_assignment' OR EXISTS(
       SELECT 1 FROM decision_runs source WHERE source.id=r.upstream_run_id
         AND source.workspace_id=target_workspace_id AND source.decision_case_id=c.id
         AND source.node_id='logistics_assignment' AND source.status='completed'
         AND source.approved_at IS NOT NULL AND source.superseded_at IS NULL))
   ORDER BY c.last_activity_at DESC,c.id DESC,r.node_id LIMIT 5
  ) SELECT coalesce(jsonb_agg(to_jsonb(candidates)-'total'
      ORDER BY last_activity_at DESC,case_id DESC,node_id),'[]'),coalesce(max(total),0)
    INTO attention,attention_total FROM candidates;
 END IF;
 RETURN jsonb_build_object('recent_cases',recent,
   'attention',jsonb_build_object('items',attention,'total',attention_total));
END; $$;
REVOKE ALL ON FUNCTION public.platform_home(uuid,uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_home(uuid,uuid) TO service_role;
COMMIT;
NOTIFY pgrst,'reload schema';
