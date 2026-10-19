-- Phase 11: personal first-run progress and explicit demo projections. No backfill.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='60s';

CREATE OR REPLACE FUNCTION dation_private.hub_dataset(d public.datasets) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT jsonb_build_object('id',d.id,'label',d.label,'original_filename',d.original_filename,
 'canonical_filename',d.canonical_filename,'dataset_type',d.dataset_type,'schema_version',d.schema_version,
 'row_count',d.row_count,'column_count',d.column_count,'size_bytes',d.size_bytes,'created_at',d.created_at,
 'is_demo',d.is_sample,'archived_at',d.archived_at,'is_default',d.is_default,'parent_dataset_id',d.parent_dataset_id,
 'deletion_pending',d.deletion_requested_at IS NOT NULL,
 'validation',CASE WHEN d.profile_json->'valid'='true' THEN 'validated' WHEN d.profile_json->'valid'='false' THEN 'issues' ELSE 'unknown' END,
 'uploaded_by',CASE WHEN d.uploaded_by_user_id IS NULL THEN NULL ELSE
 (SELECT jsonb_build_object('id',p.id,'name',coalesce(nullif(trim(concat_ws(' ',p.first_name,p.last_name)),''),'Usuario del workspace'))
 FROM profiles p JOIN workspace_members m ON m.user_id=p.id WHERE p.id=d.uploaded_by_user_id AND m.workspace_id=d.workspace_id) END,
 'case_count',(SELECT count(*) FROM decision_cases c WHERE c.workspace_id=d.workspace_id AND (c.orders_dataset_id=d.id OR c.fleet_dataset_id=d.id)),
 'run_count',(SELECT count(*) FROM decision_runs r WHERE r.workspace_id=d.workspace_id AND (r.dataset_id=d.id OR r.orders_dataset_id=d.id OR r.fleet_dataset_id=d.id)))
$$;

CREATE OR REPLACE FUNCTION dation_private.center_bundle(c public.decision_cases) RETURNS jsonb
LANGUAGE plpgsql STABLE SET search_path=public,pg_temp AS $$
DECLARE summaries jsonb; a jsonb; s jsonb; n jsonb; latest jsonb; pending boolean=false; reviewing boolean=false; finished boolean; life text;
BEGIN
 summaries=dation_private.decision_case_history(c.id,NULL,0,0)->'summaries';
 a=summaries->'logistics_assignment'->'approved';s=summaries->'logistics_scheduling'->'approved';
 FOR n IN SELECT value FROM jsonb_each(summaries-'logistics_final_assignment') LOOP
  latest=n->'latest';
  IF latest->>'id' IS NOT NULL AND latest->>'approved_at' IS NULL AND latest->>'superseded_at' IS NULL THEN
   pending=true;
   IF latest->>'status'='completed' AND (latest->>'node_id'='logistics_assignment' OR latest->>'upstream_run_id'=a->>'id') THEN reviewing=true; END IF;
  END IF;
 END LOOP;
 finished=coalesce(a->>'id' IS NOT NULL AND s->>'id' IS NOT NULL AND s->>'upstream_run_id'=a->>'id' AND NOT pending,false);
 life=CASE WHEN c.status='archived' THEN 'archived' WHEN finished THEN 'completed' ELSE 'active' END;
 RETURN jsonb_build_object('case',to_jsonb(c)-'state_json','state_json',c.state_json,'summaries',summaries,
  'is_demo',EXISTS(SELECT 1 FROM datasets d WHERE d.workspace_id=c.workspace_id AND d.id IN(c.orders_dataset_id,c.fleet_dataset_id) AND d.is_sample),'status',life,'in_review',life='active' AND reviewing,'created_by',dation_private.center_person(c.workspace_id,c.created_by_user_id));
END; $$;

CREATE OR REPLACE FUNCTION public.platform_home(target_workspace_id uuid, actor_user_id uuid)
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
     'last_activity_at',c.last_activity_at,'is_demo',EXISTS(SELECT 1 FROM datasets d WHERE d.workspace_id=c.workspace_id AND d.id IN(c.orders_dataset_id,c.fleet_dataset_id) AND d.is_sample)),
   'label',coalesce(nullif(c.label,''),nullif(o.label,''),o.canonical_filename,o.original_filename),
   'summaries',dation_private.decision_case_history(c.id,NULL,0,0)->'summaries'
 ) ORDER BY c.last_activity_at DESC,c.id DESC),'[]') INTO recent
 FROM (SELECT * FROM decision_cases WHERE workspace_id=target_workspace_id
   AND status IN('active','completed') ORDER BY last_activity_at DESC,id DESC LIMIT 3) c
 JOIN datasets o ON o.id=c.orders_dataset_id AND o.workspace_id=target_workspace_id;

 attention='[]'; attention_total=0;
 -- Assigned reviewers see their work; admins retain an audited override.
 IF member_role IN('admin','operator') THEN
  WITH reviews AS (
   SELECT c.id AS case_id,c.last_activity_at,r.id AS run_id,r.node_id,'review'::text AS kind
   FROM decision_cases c
   CROSS JOIN (VALUES ('logistics_assignment'::text),('logistics_scheduling')) n(node_id)
   JOIN LATERAL (SELECT id,node_id,status,approved_at,superseded_at,upstream_run_id
     FROM decision_runs WHERE workspace_id=target_workspace_id
       AND decision_case_id=c.id AND node_id=n.node_id
     ORDER BY created_at DESC,id DESC LIMIT 1) r ON true
   WHERE c.workspace_id=target_workspace_id AND c.status='active'
     AND r.status='completed' AND r.approved_at IS NULL AND r.superseded_at IS NULL
     AND (member_role='admin' OR NOT EXISTS(SELECT 1 FROM decision_assignments a WHERE a.workspace_id=target_workspace_id AND a.decision_case_id=c.id AND a.node_id=r.node_id AND a.approver_user_id IS NOT NULL AND a.approver_user_id<>actor_user_id))
     AND (r.node_id='logistics_assignment' OR EXISTS(
       SELECT 1 FROM decision_runs source WHERE source.id=r.upstream_run_id
         AND source.workspace_id=target_workspace_id AND source.decision_case_id=c.id
         AND source.node_id='logistics_assignment' AND source.status='completed'
         AND source.approved_at IS NOT NULL AND source.superseded_at IS NULL))
  ), handoffs AS (
   SELECT c.id AS case_id,c.last_activity_at,NULL::uuid AS run_id,'logistics_scheduling'::text AS node_id,'handoff'::text AS kind
   FROM decision_cases c JOIN decision_assignments a ON a.workspace_id=c.workspace_id AND a.decision_case_id=c.id
    AND a.node_id='logistics_scheduling' AND a.owner_user_id=actor_user_id
   JOIN decision_runs source ON source.workspace_id=c.workspace_id AND source.decision_case_id=c.id AND source.node_id='logistics_assignment'
    AND source.status='completed' AND source.approved_at IS NOT NULL AND source.superseded_at IS NULL
   WHERE c.workspace_id=target_workspace_id AND c.status='active'
    AND NOT EXISTS(SELECT 1 FROM decision_runs r WHERE r.workspace_id=c.workspace_id AND r.decision_case_id=c.id AND r.node_id='logistics_scheduling'
     AND r.upstream_run_id=source.id AND r.superseded_at IS NULL AND r.status IN('queued','running','completed'))
  ), work AS (SELECT * FROM reviews UNION ALL SELECT * FROM handoffs), candidates AS (
   SELECT work.*,EXISTS(SELECT 1 FROM decision_cases c JOIN datasets d ON d.workspace_id=c.workspace_id AND d.id IN(c.orders_dataset_id,c.fleet_dataset_id) WHERE c.workspace_id=target_workspace_id AND c.id=work.case_id AND d.is_sample) AS is_demo,count(*) OVER() AS total FROM work ORDER BY last_activity_at DESC,case_id DESC,node_id LIMIT 5
  ) SELECT coalesce(jsonb_agg(to_jsonb(candidates)-'total'
      ORDER BY last_activity_at DESC,case_id DESC,node_id),'[]'),coalesce(max(total),0)
    INTO attention,attention_total FROM candidates;
 END IF;
 RETURN jsonb_build_object('recent_cases',recent,
   'attention',jsonb_build_object('items',attention,'total',attention_total));
END; $$;

CREATE OR REPLACE FUNCTION public.platform_activity(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid DEFAULT NULL,
 page_limit integer DEFAULT 5,before_time timestamptz DEFAULT NULL,before_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE answer jsonb; logistics boolean;
BEGIN
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
 IF page_limit IS NULL OR page_limit NOT BETWEEN 1 AND 50 OR (before_time IS NULL)<>(before_id IS NULL) THEN RAISE EXCEPTION 'Invalid activity query' USING ERRCODE='22023'; END IF;
 IF target_case_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM decision_cases WHERE workspace_id=target_workspace_id AND id=target_case_id) THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
 SELECT EXISTS(SELECT 1 FROM workspace_ddas WHERE workspace_id=target_workspace_id AND dda_id='logistics' AND status='enabled') INTO logistics;
 WITH page AS MATERIALIZED (
  SELECT e.*,coalesce(e.decision_case_id,CASE WHEN e.metadata_json->>'case_id' ~* '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$' THEN (e.metadata_json->>'case_id')::uuid END) cid
  FROM audit_events e WHERE workspace_id=target_workspace_id
  AND (target_case_id IS NULL OR e.decision_case_id=target_case_id OR e.metadata_json->>'case_id'=target_case_id::text)
  AND (target_case_id IS NOT NULL OR logistics OR e.event_type LIKE 'workspace.%' OR e.event_type LIKE 'team.%' OR e.event_type LIKE 'member.%')
  AND (before_time IS NULL OR (e.created_at,e.id)<(before_time,before_id))
  ORDER BY e.created_at DESC,e.id DESC LIMIT page_limit+1),
 visible AS MATERIALIZED (SELECT * FROM page ORDER BY created_at DESC,id DESC LIMIT page_limit)
 SELECT jsonb_build_object('items',coalesce((SELECT jsonb_agg(jsonb_build_object(
  'id',e.id,'event_type',dation_private.activity_kind(e.event_type,e.metadata_json),'object_type',coalesce(e.object_type,CASE WHEN e.event_type LIKE 'workspace.%' THEN 'workspace' WHEN e.metadata_json->>'run_id' IS NOT NULL THEN 'run' WHEN e.cid IS NOT NULL THEN 'decision_case' ELSE NULL END),
  'object_id',coalesce(e.object_id,CASE WHEN e.event_type LIKE 'workspace.%' THEN e.workspace_id WHEN e.metadata_json->>'run_id' ~* '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$' THEN (e.metadata_json->>'run_id')::uuid ELSE e.cid END),
  'is_demo',EXISTS(SELECT 1 FROM datasets d WHERE d.workspace_id=target_workspace_id AND d.is_sample AND ((e.object_type='dataset' AND d.id=e.object_id) OR d.id IN(SELECT c.orders_dataset_id FROM decision_cases c WHERE c.id=e.cid AND c.workspace_id=target_workspace_id UNION ALL SELECT c.fleet_dataset_id FROM decision_cases c WHERE c.id=e.cid AND c.workspace_id=target_workspace_id))),'case_id',e.cid,'node_id',coalesce(e.node_id,e.metadata_json->>'node_id'),'created_at',e.created_at,
  'actor',CASE WHEN e.actor_user_id IS NULL THEN NULL ELSE coalesce(dation_private.center_person(target_workspace_id,e.actor_user_id),jsonb_build_object('id',e.actor_user_id,'name','Usuario sin perfil disponible')) END,
  'metadata',jsonb_strip_nulls(jsonb_build_object('source',e.metadata_json->'source','automatic',e.metadata_json->'automatic',
   'dataset_type',e.metadata_json->'dataset_type','row_count',e.metadata_json->'row_count','valid',e.metadata_json->'valid',
   'format',e.metadata_json->'format','bytes',e.metadata_json->'bytes','sha256',e.metadata_json->'sha256',
   'admin_override',e.metadata_json->'admin_override','section',e.metadata_json->'section',
   'access_role',coalesce(e.metadata_json->'access_role',e.metadata_json->'after'->'access_role')))) ORDER BY e.created_at DESC,e.id DESC) FROM visible e),'[]'),
  'next_cursor',CASE WHEN (SELECT count(*) FROM page)>page_limit THEN
  (SELECT jsonb_build_object('before_time',created_at,'before_id',id) FROM visible ORDER BY created_at,id LIMIT 1) ELSE NULL END)
 INTO answer;
 RETURN answer;
END; $$;

CREATE TABLE dation_private.workspace_onboarding (
 workspace_id uuid NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
 user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
 explored_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(workspace_id,user_id)
);
ALTER TABLE dation_private.workspace_onboarding ENABLE ROW LEVEL SECURITY;
ALTER TABLE dation_private.workspace_onboarding FORCE ROW LEVEL SECURITY;
REVOKE ALL ON dation_private.workspace_onboarding FROM PUBLIC,anon,authenticated,service_role;

CREATE FUNCTION public.platform_onboarding(target_workspace_id uuid,actor_user_id uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE explored timestamptz; enabled boolean; prepared boolean=false; first_run decision_runs;
BEGIN
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
 SELECT explored_at INTO explored FROM dation_private.workspace_onboarding
 WHERE workspace_id=target_workspace_id AND user_id=actor_user_id;
 SELECT EXISTS(SELECT 1 FROM workspace_ddas WHERE workspace_id=target_workspace_id AND dda_id='logistics' AND status='enabled') INTO enabled;
 IF enabled THEN
  SELECT EXISTS(SELECT 1 FROM datasets WHERE workspace_id=target_workspace_id AND dataset_type='orders' AND archived_at IS NULL AND deletion_requested_at IS NULL AND profile_json->'valid'='true')
   AND EXISTS(SELECT 1 FROM datasets WHERE workspace_id=target_workspace_id AND dataset_type='fleet' AND archived_at IS NULL AND deletion_requested_at IS NULL AND profile_json->'valid'='true') INTO prepared;
  SELECT * INTO first_run FROM decision_runs WHERE workspace_id=target_workspace_id AND status='completed' AND node_id IN('logistics_assignment','logistics_scheduling') ORDER BY created_at,id LIMIT 1;
 END IF;
 RETURN jsonb_build_object('available',true,'workspace_created',true,'explored_at',explored,'data_ready',prepared,
  'first_decision_completed',first_run.id IS NOT NULL,'logistics_enabled',enabled,
  'data_includes_demo',prepared AND EXISTS(SELECT 1 FROM datasets WHERE workspace_id=target_workspace_id AND dataset_type IN('orders','fleet') AND is_sample AND archived_at IS NULL AND deletion_requested_at IS NULL AND profile_json->'valid'='true'),
  'first_decision_demo',EXISTS(SELECT 1 FROM datasets WHERE workspace_id=target_workspace_id AND is_sample AND id IN(first_run.orders_dataset_id,first_run.fleet_dataset_id,first_run.dataset_id)));
END; $$;

CREATE FUNCTION public.platform_onboarding_explore(target_workspace_id uuid,actor_user_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
BEGIN
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
 INSERT INTO dation_private.workspace_onboarding(workspace_id,user_id) VALUES(target_workspace_id,actor_user_id)
 ON CONFLICT(workspace_id,user_id) DO NOTHING;
 RETURN public.platform_onboarding(target_workspace_id,actor_user_id);
END; $$;
REVOKE ALL ON FUNCTION public.platform_onboarding(uuid,uuid),public.platform_onboarding_explore(uuid,uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_onboarding(uuid,uuid),public.platform_onboarding_explore(uuid,uuid) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
