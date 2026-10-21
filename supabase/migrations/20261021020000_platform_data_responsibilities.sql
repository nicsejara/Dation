-- Split data roles using the existing assignment table and RPC signatures.
-- No new access roles, grants, tables, workflow policy or decision lifecycle.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';
LOCK TABLE dation_private.workflow_stage_assignments IN SHARE ROW EXCLUSIVE MODE;

-- Preserve each historical assignee, actor and version under its business role.
INSERT INTO dation_private.workflow_stage_assignments
 SELECT a.workspace_id,a.decision_case_id,
  CASE WHEN 'data_steward'=ANY(dation_private.member_roles(a.workspace_id,a.owner_user_id))
   AND NOT 'data_owner'=ANY(dation_private.member_roles(a.workspace_id,a.owner_user_id))
   THEN 'data_steward' ELSE 'data_owner' END,
  a.owner_user_id,a.updated_by,a.updated_at
 FROM dation_private.workflow_stage_assignments a
 WHERE a.stage_key='data_preparation' AND a.owner_user_id IS NOT NULL
 ON CONFLICT(workspace_id,decision_case_id,stage_key) DO NOTHING;
-- data_preparation becomes a compatibility projection, not a second assignment.
UPDATE dation_private.workflow_stage_assignments SET owner_user_id=NULL
 WHERE stage_key='data_preparation' AND owner_user_id IS NOT NULL;

DO $migration$
DECLARE source text; anchor text;
BEGIN
 source=pg_get_functiondef('dation_private.responsibility_eligible(uuid,uuid,text)'::regprocedure);
 anchor=$a$WHEN 'data' THEN ARRAY['data_owner','data_steward']$a$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected eligibility contract'; END IF;
 EXECUTE replace(source,anchor,anchor||$a$ WHEN 'data_owner' THEN ARRAY['data_owner'] WHEN 'data_steward' THEN ARRAY['data_steward']$a$);

 source=pg_get_functiondef('public.platform_team_foundation(uuid,uuid,text,integer,integer,boolean,text)'::regprocedure);
 anchor=$a$responsibility_group NOT IN('data','decision_owner','approver')$a$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected Team candidate contract'; END IF;
 EXECUTE replace(source,anchor,$a$responsibility_group NOT IN('data','data_owner','data_steward','decision_owner','approver')$a$);

 source=pg_get_functiondef('public.platform_workflow_responsibilities(uuid,uuid,uuid,text,text,timestamptz,uuid,uuid)'::regprocedure);
 anchor=$a$target_stage_key NOT IN('data_preparation','logistics_assignment','logistics_scheduling')$a$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected workflow stage contract'; END IF;
 source=replace(source,anchor,$a$target_stage_key NOT IN('data_preparation','data_owner','data_steward','logistics_assignment','logistics_scheduling')$a$);
 anchor=$a$  IF target_stage_key='data_preparation' THEN$a$;
 source=replace(source,anchor,$a$  IF target_stage_key IN('data_preparation','data_owner','data_steward') THEN$a$);
 anchor=$a$  IF target_stage_key IN('data_preparation','data_owner','data_steward') THEN$a$;
 -- Old clients can still read and assign untouched cases. A write that would
 -- ambiguously replace a split assignment fails with CAS conflict, without loss.
 source=replace(source,$a$  IF c.status='archived' THEN$a$,
  $a$  IF target_stage_key='data_preparation' AND EXISTS(SELECT 1 FROM dation_private.workflow_stage_assignments WHERE workspace_id=target_workspace_id AND decision_case_id=target_case_id AND stage_key IN('data_owner','data_steward')) THEN
   RAISE EXCEPTION 'Edit data responsibilities by role; refresh' USING ERRCODE='55006';
  END IF;
  IF target_stage_key='data_preparation' THEN
   SELECT * INTO stage FROM dation_private.workflow_stage_assignments WHERE workspace_id=target_workspace_id AND decision_case_id=target_case_id AND stage_key='data_preparation';
   IF stage.updated_at IS DISTINCT FROM expected_updated_at THEN RAISE EXCEPTION 'Assignment changed' USING ERRCODE='55006'; END IF;
   target_stage_key=CASE WHEN 'data_owner'=ANY(dation_private.member_roles(target_workspace_id,new_owner_user_id)) THEN 'data_owner' ELSE 'data_steward' END;
   expected_updated_at=NULL;
  END IF;
  IF c.status='archived' THEN$a$);
 source=replace(source,$a$CASE WHEN target_stage_key='data_preparation' THEN 'data' ELSE 'decision_owner' END$a$,
  $a$CASE WHEN target_stage_key='data_owner' THEN 'data_owner' WHEN target_stage_key='data_steward' THEN 'data_steward' WHEN target_stage_key='data_preparation' THEN 'data' ELSE 'decision_owner' END$a$);
 source=replace(source,$a$CASE WHEN target_stage_key='data_preparation' THEN$a$,
  $a$CASE WHEN target_stage_key IN('data_preparation','data_owner','data_steward') THEN$a$);
 anchor=$a$  IF previous_owner IS DISTINCT FROM new_owner_user_id OR previous_approver IS DISTINCT FROM new_approver_user_id THEN$a$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected assignment CAS contract'; END IF;
 source=replace(source,anchor,$a$  IF previous_owner IS DISTINCT FROM new_owner_user_id OR previous_approver IS DISTINCT FROM new_approver_user_id OR
   (target_stage_key IN('data_owner','data_steward') AND stamp IS NULL) THEN$a$);
 anchor=$a$WITH stages AS (SELECT 'data_preparation' key,a.owner_user_id,NULL::uuid approver_user_id,a.updated_at FROM (SELECT 1) x LEFT JOIN dation_private.workflow_stage_assignments a ON a.workspace_id=target_workspace_id AND a.decision_case_id=target_case_id AND a.stage_key='data_preparation'$a$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected responsibility read contract'; END IF;
 source=replace(source,anchor,$a$WITH stages AS (SELECT x.key,a.owner_user_id,NULL::uuid approver_user_id,a.updated_at FROM (VALUES('data_preparation'),('data_owner'),('data_steward')) x(key) LEFT JOIN dation_private.workflow_stage_assignments a ON a.workspace_id=target_workspace_id AND a.decision_case_id=target_case_id AND a.stage_key=x.key$a$);
 source=replace(source,$a$CASE WHEN key='data_preparation' THEN 'data' ELSE 'decision_owner' END$a$,
  $a$CASE WHEN key='data_owner' THEN 'data_owner' WHEN key='data_steward' THEN 'data_steward' WHEN key='data_preparation' THEN 'data' ELSE 'decision_owner' END$a$);
 anchor=$a$ RETURN jsonb_build_object('case_id',target_case_id,'stages',result$a$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected workflow response'; END IF;
 source=replace(source,anchor,$a$ IF EXISTS(SELECT 1 FROM dation_private.workflow_stage_assignments WHERE workspace_id=target_workspace_id AND decision_case_id=target_case_id AND stage_key IN('data_owner','data_steward')) THEN
  result=jsonb_set(result,'{data_preparation}',CASE
   WHEN (result->'data_owner'->>'owner_eligible')::boolean THEN result->'data_owner'
   WHEN (result->'data_steward'->>'owner_eligible')::boolean THEN result->'data_steward'
   WHEN result->'data_owner'->'owner'<>'null'::jsonb THEN result->'data_owner'
   ELSE result->'data_steward' END);
 END IF;
 RETURN jsonb_build_object('case_id',target_case_id,'stages',result$a$);
 EXECUTE source;

 source=pg_get_functiondef('dation_private.require_workflow_responsibility(uuid,uuid,text,text)'::regprocedure);
 anchor=$a$  SELECT owner_user_id INTO person FROM dation_private.workflow_stage_assignments
   WHERE workspace_id=wid AND decision_case_id=cid AND stage_key='data_preparation';$a$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected data admission contract'; END IF;
 EXECUTE replace(source,anchor,$a$  SELECT a.owner_user_id INTO person FROM dation_private.workflow_stage_assignments a
   WHERE a.workspace_id=wid AND a.decision_case_id=cid
    AND (a.stage_key IN('data_owner','data_steward') OR (a.stage_key='data_preparation' AND NOT EXISTS(
     SELECT 1 FROM dation_private.workflow_stage_assignments x WHERE x.workspace_id=wid AND x.decision_case_id=cid AND x.stage_key IN('data_owner','data_steward'))))
    AND dation_private.responsibility_eligible(wid,a.owner_user_id,CASE WHEN a.stage_key='data_preparation' THEN 'data' ELSE a.stage_key END)
   ORDER BY CASE a.stage_key WHEN 'data_owner' THEN 0 WHEN 'data_steward' THEN 1 ELSE 2 END LIMIT 1;$a$);

 source=pg_get_functiondef('dation_private.execution_responsibility_snapshot(uuid,uuid,text)'::regprocedure);
 anchor=$a$ LEFT JOIN dation_private.workflow_stage_assignments d ON d.workspace_id=wid AND d.decision_case_id=cid AND d.stage_key='data_preparation'$a$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected responsibility evidence contract'; END IF;
 source=replace(source,anchor,$a$ LEFT JOIN LATERAL (
  SELECT x.* FROM dation_private.workflow_stage_assignments x WHERE x.workspace_id=wid AND x.decision_case_id=cid
   AND (x.stage_key IN('data_owner','data_steward') OR (x.stage_key='data_preparation' AND NOT EXISTS(
    SELECT 1 FROM dation_private.workflow_stage_assignments y WHERE y.workspace_id=wid AND y.decision_case_id=cid AND y.stage_key IN('data_owner','data_steward'))))
   AND dation_private.responsibility_eligible(wid,x.owner_user_id,CASE WHEN x.stage_key='data_preparation' THEN 'data' ELSE x.stage_key END)
   ORDER BY CASE x.stage_key WHEN 'data_owner' THEN 0 WHEN 'data_steward' THEN 1 ELSE 2 END LIMIT 1
 ) d ON true$a$);
 EXECUTE source;

 -- Resolve actor names for an exact historical run through the existing
 -- history RPC, bounded to its workspace, Case and node. No new RPC or grants.
 source=pg_get_functiondef('public.platform_decision_center(uuid,uuid,uuid,text,text,text,text,integer,integer)'::regprocedure);
 anchor=$a$decision_case_id=current_case.id AND node_id=target_node_id$a$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected history filter contract'; END IF;
 EXECUTE replace(source,anchor,anchor||$a$ AND (search_text='' OR id::text=search_text)$a$);
 source=pg_get_functiondef('public.platform_decision_portfolio(uuid,uuid,uuid,text,text,text,text,integer,integer,text)'::regprocedure);
 anchor=$a$target_case_id,'all','','all',target_node_id$a$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected history forwarding contract'; END IF;
 EXECUTE replace(source,anchor,$a$target_case_id,'all',CASE WHEN target_node_id IS NOT NULL THEN search_text ELSE '' END,'all',target_node_id$a$);
END; $migration$;
NOTIFY pgrst,'reload schema';
COMMIT;
