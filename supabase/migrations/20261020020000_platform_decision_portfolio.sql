-- V2 Phase 2: bounded portfolio projection; no persistent workflow/data changes.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';

CREATE FUNCTION dation_private.center_portfolio_facts(wid uuid,uid uuid,member_role text)
RETURNS TABLE(case_id uuid,life text,review_count bigint,pending_count bigint,approved_count bigint,running_count bigint)
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 WITH latest AS MATERIALIZED (
  SELECT DISTINCT ON(r.decision_case_id,r.node_id) r.decision_case_id,r.node_id,r.id,r.status,r.upstream_run_id,r.approved_at,r.superseded_at
  FROM decision_runs r WHERE r.workspace_id=wid AND r.node_id IN('logistics_assignment','logistics_scheduling')
  ORDER BY r.decision_case_id,r.node_id,r.created_at DESC,r.id DESC
 ), approved AS MATERIALIZED (
  SELECT r.decision_case_id,r.node_id,r.id,r.upstream_run_id FROM decision_runs r
  WHERE r.workspace_id=wid AND r.node_id IN('logistics_assignment','logistics_scheduling') AND r.approved_at IS NOT NULL AND r.superseded_at IS NULL
 ), nodes AS (
  SELECT c.id,
   l.id IS NOT NULL AND l.approved_at IS NULL AND l.superseded_at IS NULL AS candidate,
   l.status, a.id IS NOT NULL AND (n.node_id='logistics_assignment' OR a.upstream_run_id=source.id) AS current_approval,
   l.id IS NOT NULL AND l.approved_at IS NULL AND l.superseded_at IS NULL AND l.status='completed'
    AND (n.node_id='logistics_assignment' OR l.upstream_run_id=source.id) AS reviewing,
   (member_role='admin' OR (member_role='operator' AND (assignment.approver_user_id IS NULL OR assignment.approver_user_id=uid)))
    AND EXISTS(SELECT 1 FROM workspace_ddas d WHERE d.workspace_id=wid AND d.dda_id=c.domain AND d.status='enabled') AS can_approve
  FROM decision_cases c CROSS JOIN (VALUES('logistics_assignment'),('logistics_scheduling')) n(node_id)
  LEFT JOIN latest l ON l.decision_case_id=c.id AND l.node_id=n.node_id
  LEFT JOIN approved a ON a.decision_case_id=c.id AND a.node_id=n.node_id
  LEFT JOIN approved source ON source.decision_case_id=c.id AND source.node_id='logistics_assignment'
  LEFT JOIN decision_assignments assignment ON assignment.workspace_id=wid AND assignment.decision_case_id=c.id AND assignment.node_id=n.node_id
  WHERE c.workspace_id=wid AND c.domain='logistics'
 ), counts AS (
  SELECT id,count(*) FILTER(WHERE reviewing) reviews,count(*) FILTER(WHERE reviewing AND can_approve) pending,
   count(*) FILTER(WHERE current_approval) approvals,count(*) FILTER(WHERE candidate AND status IN('queued','running')) running,
   bool_or(candidate) unfinished FROM nodes GROUP BY id
 )
 SELECT c.id,CASE WHEN c.status='archived' THEN 'archived'
  WHEN c.domain='logistics' AND counts.approvals=2 AND NOT counts.unfinished THEN 'completed'
  WHEN c.domain='logistics' THEN 'active' ELSE c.status END,
  coalesce(counts.reviews,0),coalesce(counts.pending,0),coalesce(counts.approvals,0),coalesce(counts.running,0)
 FROM decision_cases c LEFT JOIN counts ON counts.id=c.id WHERE c.workspace_id=wid
$$;

CREATE FUNCTION public.platform_decision_portfolio(target_workspace_id uuid,actor_user_id uuid,
 target_case_id uuid DEFAULT NULL,filter_name text DEFAULT 'all',search_text text DEFAULT '',dda text DEFAULT 'all',
 target_node_id text DEFAULT NULL,page_limit integer DEFAULT 25,page_offset integer DEFAULT 0,owner_filter text DEFAULT 'all')
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE member_role text; answer jsonb; selected_owner uuid;
BEGIN
 member_role=dation_private.data_actor(target_workspace_id,actor_user_id);
 PERFORM set_config('dation.workspace_id',target_workspace_id::text,true);
 IF filter_name NOT IN('all','in_progress','review','pending_approval','approved','completed','archived')
 OR dda IS NULL OR length(dda)>48 OR dda!~'^[a-z0-9_-]+$' OR length(search_text)>120
 OR page_limit NOT BETWEEN 1 AND 50 OR page_offset NOT BETWEEN 0 AND 1000000 OR owner_filter IS NULL THEN
  RAISE EXCEPTION 'Invalid portfolio query' USING ERRCODE='22023'; END IF;
 IF owner_filter NOT IN('all','me','unassigned') THEN
  BEGIN selected_owner=owner_filter::uuid; EXCEPTION WHEN invalid_text_representation THEN
   RAISE EXCEPTION 'Invalid owner filter' USING ERRCODE='22023'; END;
 ELSIF owner_filter='me' THEN selected_owner=actor_user_id; END IF;
 IF target_case_id IS NOT NULL THEN
  answer=public.platform_decision_center(target_workspace_id,actor_user_id,target_case_id,'all','','all',target_node_id,page_limit,page_offset);
  IF target_node_id IS NULL THEN
   answer=answer||jsonb_build_object('responsibilities',public.platform_workflow_responsibilities(target_workspace_id,actor_user_id,target_case_id));
  END IF;
  RETURN answer;
 END IF;
 WITH facts AS MATERIALIZED(SELECT * FROM dation_private.center_portfolio_facts(target_workspace_id,actor_user_id,member_role)),
 base AS(SELECT c.*,f.life,f.review_count,f.pending_count,f.approved_count,f.running_count FROM decision_cases c JOIN facts f ON f.case_id=c.id
  WHERE c.workspace_id=target_workspace_id AND (dda='all' OR c.domain=dda)
   AND (search_text='' OR strpos(lower(concat_ws(' ',c.id::text,'DC-'||substr(c.id::text,1,8),c.label)),lower(search_text))>0)
   AND (owner_filter='all' OR
    (owner_filter='unassigned' AND NOT EXISTS(SELECT 1 FROM decision_assignments a WHERE a.workspace_id=target_workspace_id AND a.decision_case_id=c.id AND a.owner_user_id IS NOT NULL)
     AND NOT EXISTS(SELECT 1 FROM dation_private.workflow_stage_assignments a WHERE a.workspace_id=target_workspace_id AND a.decision_case_id=c.id AND a.owner_user_id IS NOT NULL)) OR
    (selected_owner IS NOT NULL AND (EXISTS(SELECT 1 FROM decision_assignments a WHERE a.workspace_id=target_workspace_id AND a.decision_case_id=c.id AND a.owner_user_id=selected_owner)
     OR EXISTS(SELECT 1 FROM dation_private.workflow_stage_assignments a WHERE a.workspace_id=target_workspace_id AND a.decision_case_id=c.id AND a.owner_user_id=selected_owner))))),
 matched AS(SELECT * FROM base WHERE CASE filter_name WHEN 'archived' THEN life='archived' WHEN 'completed' THEN life='completed'
  WHEN 'in_progress' THEN life='active' WHEN 'review' THEN life<>'archived' AND review_count>0
  WHEN 'pending_approval' THEN life<>'archived' AND pending_count>0 WHEN 'approved' THEN life<>'archived' AND approved_count>0 ELSE life<>'archived' END),
 page AS(SELECT * FROM matched ORDER BY last_activity_at DESC,id DESC LIMIT page_limit OFFSET page_offset),
 owners AS(SELECT owner_user_id id FROM decision_assignments WHERE workspace_id=target_workspace_id AND owner_user_id IS NOT NULL
  UNION SELECT owner_user_id FROM dation_private.workflow_stage_assignments WHERE workspace_id=target_workspace_id AND owner_user_id IS NOT NULL)
 SELECT jsonb_build_object('summary',jsonb_build_object(
  'active_cases',(SELECT count(*) FROM facts WHERE life='active'),
  'in_review',(SELECT coalesce(sum(review_count),0) FROM facts WHERE life<>'archived'),
  'pending_approval',(SELECT coalesce(sum(pending_count),0) FROM facts WHERE life<>'archived'),
  'approved',(SELECT coalesce(sum(approved_count),0) FROM facts WHERE life<>'archived')),
  'items',coalesce((SELECT jsonb_agg((dation_private.center_bundle(c)||jsonb_build_object(
   'collaboration',dation_private.case_collaboration(target_workspace_id,p.id,actor_user_id),
   'portfolio_facts',jsonb_build_object('review',p.review_count,'pending',p.pending_count,'approved',p.approved_count,'running',p.running_count))) ORDER BY p.last_activity_at DESC,p.id DESC)
   FROM decision_cases c JOIN page p ON p.id=c.id WHERE c.workspace_id=target_workspace_id),'[]'),
  'total',(SELECT count(*) FROM matched),'limit',page_limit,'offset',page_offset,
  'owner_options',coalesce((SELECT jsonb_agg(person ORDER BY person->>'name') FROM(
   SELECT dation_private.team_person(target_workspace_id,id) person FROM owners ORDER BY id=selected_owner DESC NULLS LAST,id LIMIT 100) people),'[]'),
  'dda_options',coalesce((SELECT jsonb_agg(DISTINCT domain) FROM decision_cases WHERE workspace_id=target_workspace_id),'[]')) INTO answer;
 RETURN answer;
END; $$;
REVOKE ALL ON FUNCTION dation_private.center_portfolio_facts(uuid,uuid,text) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_decision_portfolio(uuid,uuid,uuid,text,text,text,text,integer,integer,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_decision_portfolio(uuid,uuid,uuid,text,text,text,text,integer,integer,text) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
