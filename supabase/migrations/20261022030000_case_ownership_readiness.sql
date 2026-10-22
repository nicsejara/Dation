-- Saga 3 B/C: canonical owners and server-enforced initial Case readiness.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';
ALTER TABLE public.decision_cases ADD COLUMN attributes_applied_at timestamptz;
UPDATE public.decision_cases SET attributes_applied_at=updated_at WHERE nullif(trim(label),'') IS NOT NULL AND category IS NOT NULL;
CREATE FUNCTION dation_private.apply_case_attributes() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 NEW.attributes_applied_at=CASE WHEN nullif(trim(NEW.label),'') IS NOT NULL AND NEW.category IS NOT NULL THEN clock_timestamp() ELSE NULL END;
 RETURN NEW;
END; $$;
CREATE TRIGGER case_attributes_applied BEFORE INSERT OR UPDATE OF label,category,description ON public.decision_cases
 FOR EACH ROW EXECUTE FUNCTION dation_private.apply_case_attributes();
REVOKE ALL ON FUNCTION dation_private.apply_case_attributes() FROM PUBLIC,anon,authenticated,service_role;

-- Retire Steward operationally without deleting its historical assignment/role.
CREATE OR REPLACE FUNCTION dation_private.member_roles(wid uuid,uid uuid) RETURNS text[]
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT coalesce(array_agg(role ORDER BY role),'{}'::text[]) FROM (
  SELECT DISTINCT CASE responsibility WHEN 'data_steward' THEN 'data_owner' ELSE responsibility END role
  FROM dation_private.member_responsibilities WHERE workspace_id=wid AND user_id=uid) roles;
$$;
INSERT INTO dation_private.member_responsibilities SELECT workspace_id,user_id,'data_owner'
 FROM dation_private.member_responsibilities WHERE responsibility='data_steward' ON CONFLICT DO NOTHING;
INSERT INTO dation_private.workflow_stage_assignments
 SELECT workspace_id,decision_case_id,'data_owner',owner_user_id,updated_by,updated_at
 FROM dation_private.workflow_stage_assignments WHERE stage_key IN('data_steward','data_preparation') AND owner_user_id IS NOT NULL
 ORDER BY CASE stage_key WHEN 'data_steward' THEN 0 ELSE 1 END
 ON CONFLICT(workspace_id,decision_case_id,stage_key) DO UPDATE
 SET owner_user_id=excluded.owner_user_id,updated_by=excluded.updated_by,updated_at=excluded.updated_at
 WHERE workflow_stage_assignments.owner_user_id IS NULL;

CREATE OR REPLACE FUNCTION dation_private.require_workflow_responsibility(wid uuid,cid uuid,stage text,gate text)
RETURNS void LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE c decision_cases; person uuid; uid uuid=nullif(current_setting('dation.actor_user_id',true),'')::uuid; role_name text;
BEGIN
 PERFORM 1 FROM workspaces WHERE id=wid FOR UPDATE;
 SELECT * INTO c FROM decision_cases WHERE workspace_id=wid AND id=cid FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
 IF c.status='archived' THEN RAISE EXCEPTION 'Restore case before continuing' USING ERRCODE='22023'; END IF;
 IF NOT (SELECT workflow_gates_enabled FROM dation_private.platform_release WHERE singleton) THEN RETURN; END IF;
 IF gate IN('data','execute','configure') THEN
  IF c.attributes_applied_at IS NULL OR nullif(trim(c.label),'') IS NULL OR c.category IS NULL THEN
   RAISE EXCEPTION 'Aplicá los atributos del Case antes de continuar.' USING ERRCODE='P0001'; END IF;
  SELECT owner_user_id INTO person FROM dation_private.workflow_stage_assignments WHERE workspace_id=wid AND decision_case_id=cid AND stage_key='data_owner';
  IF NOT dation_private.responsibility_eligible(wid,person,'data_owner') THEN
   RAISE EXCEPTION 'Asigná un Data Owner activo y elegible antes de continuar.' USING ERRCODE='P0001'; END IF;
 END IF;
 IF gate IN('execute','approve','configure') THEN
  SELECT owner_user_id INTO person FROM decision_assignments WHERE workspace_id=wid AND decision_case_id=cid AND node_id=stage;
  IF NOT dation_private.responsibility_eligible(wid,person,'decision_owner') THEN
   RAISE EXCEPTION 'Asigná un Decision Owner activo y elegible antes de continuar.' USING ERRCODE='P0001'; END IF;
  SELECT access_role INTO role_name FROM workspace_members WHERE workspace_id=wid AND user_id=uid AND status='active';
  IF gate IN('execute','approve') AND uid IS DISTINCT FROM person AND role_name IS DISTINCT FROM 'admin' THEN
   RAISE EXCEPTION 'Decision Owner or Admin required' USING ERRCODE='42501'; END IF;
 ELSIF gate<>'data' THEN RAISE EXCEPTION 'Invalid gate' USING ERRCODE='22023'; END IF;
END; $$;
CREATE OR REPLACE FUNCTION dation_private.execution_responsibility_snapshot(wid uuid,cid uuid,nid text)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT jsonb_strip_nulls(jsonb_build_object('data_responsible_user_id',d.owner_user_id,'data_owner_user_id',d.owner_user_id,
  'data_assignment_updated_at',d.updated_at,'decision_owner_user_id',a.owner_user_id,'decision_assignment_updated_at',a.updated_at))
 FROM (SELECT 1) x LEFT JOIN dation_private.workflow_stage_assignments d ON d.workspace_id=wid AND d.decision_case_id=cid AND d.stage_key='data_owner'
 LEFT JOIN decision_assignments a ON a.workspace_id=wid AND a.decision_case_id=cid AND a.node_id=nid;
$$;

CREATE OR REPLACE FUNCTION public.platform_assign_decision(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid,target_node_id text,expected_updated_at timestamptz,new_owner_user_id uuid,new_approver_user_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE assignment decision_assignments;
BEGIN
 PERFORM 1 FROM workspaces WHERE id=target_workspace_id FOR UPDATE;
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id,true);
 PERFORM 1 FROM decision_cases WHERE workspace_id=target_workspace_id AND id=target_case_id AND status<>'archived' FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Case not found or archived' USING ERRCODE='P0002'; END IF;
 IF target_node_id NOT IN('logistics_assignment','logistics_scheduling') OR target_node_id IS NULL THEN RAISE EXCEPTION 'Invalid node' USING ERRCODE='22023'; END IF;
 SELECT * INTO assignment FROM decision_assignments WHERE workspace_id=target_workspace_id AND decision_case_id=target_case_id AND node_id=target_node_id FOR UPDATE;
 IF assignment.updated_at IS DISTINCT FROM expected_updated_at THEN RAISE EXCEPTION 'Assignment changed' USING ERRCODE='55006'; END IF;
 IF new_approver_user_id IS NOT NULL AND new_approver_user_id IS DISTINCT FROM new_owner_user_id AND new_approver_user_id IS DISTINCT FROM assignment.approver_user_id THEN
  RAISE EXCEPTION 'Use the Decision Owner; separate approvers are retired' USING ERRCODE='22023'; END IF;
 IF new_owner_user_id IS DISTINCT FROM assignment.owner_user_id THEN
  IF new_owner_user_id IS NOT NULL AND NOT dation_private.responsibility_eligible(target_workspace_id,new_owner_user_id,'decision_owner') THEN
   RAISE EXCEPTION 'Assignee responsibility is not eligible' USING ERRCODE='22023'; END IF;
  INSERT INTO decision_assignments(workspace_id,decision_case_id,node_id,owner_user_id)
   VALUES(target_workspace_id,target_case_id,target_node_id,new_owner_user_id)
   ON CONFLICT(decision_case_id,node_id) DO UPDATE SET owner_user_id=excluded.owner_user_id,updated_at=clock_timestamp()
   RETURNING * INTO assignment;
  INSERT INTO audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,decision_case_id,node_id,metadata_json)
   VALUES(target_workspace_id,actor_user_id,'decision.owner_changed','decision_case',target_case_id,target_case_id,target_node_id,
    jsonb_build_object('stage_key',target_node_id,'new_user_id',new_owner_user_id));
 END IF;
 RETURN jsonb_build_object('updated_at',assignment.updated_at);
END; $$;

-- Compatibility response keys refer to the same Owner; there is no second assignment.
CREATE OR REPLACE FUNCTION public.platform_workflow_responsibilities(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid,operation text DEFAULT 'read',target_stage_key text DEFAULT NULL,expected_updated_at timestamptz DEFAULT NULL,new_owner_user_id uuid DEFAULT NULL,new_approver_user_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE role_name text; c decision_cases; stage dation_private.workflow_stage_assignments; result jsonb;
BEGIN
 IF operation IS NULL OR operation NOT IN('read','write') THEN RAISE EXCEPTION 'Invalid operation' USING ERRCODE='22023'; END IF;
 IF operation='write' THEN PERFORM 1 FROM workspaces WHERE id=target_workspace_id FOR UPDATE; END IF;
 role_name=dation_private.team_actor(target_workspace_id,actor_user_id,operation='write');
 SELECT * INTO c FROM decision_cases WHERE workspace_id=target_workspace_id AND id=target_case_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
 IF operation='write' THEN
  IF c.status='archived' THEN RAISE EXCEPTION 'Restore case before assigning' USING ERRCODE='22023'; END IF;
  IF target_stage_key IS NULL OR target_stage_key NOT IN('data_preparation','data_owner','logistics_assignment','logistics_scheduling') THEN RAISE EXCEPTION 'Invalid stage' USING ERRCODE='22023'; END IF;
  IF target_stage_key IN('data_preparation','data_owner') THEN
   target_stage_key='data_owner';
   IF new_approver_user_id IS NOT NULL THEN RAISE EXCEPTION 'Data is not a decision node' USING ERRCODE='22023'; END IF;
   SELECT * INTO stage FROM dation_private.workflow_stage_assignments WHERE workspace_id=target_workspace_id AND decision_case_id=target_case_id AND stage_key='data_owner' FOR UPDATE;
   IF stage.updated_at IS DISTINCT FROM expected_updated_at THEN RAISE EXCEPTION 'Assignment changed' USING ERRCODE='55006'; END IF;
   IF new_owner_user_id IS DISTINCT FROM stage.owner_user_id THEN
    IF new_owner_user_id IS NOT NULL AND NOT dation_private.responsibility_eligible(target_workspace_id,new_owner_user_id,'data_owner') THEN RAISE EXCEPTION 'Assignee responsibility is not eligible' USING ERRCODE='22023'; END IF;
    INSERT INTO dation_private.workflow_stage_assignments VALUES(target_workspace_id,target_case_id,'data_owner',new_owner_user_id,actor_user_id,clock_timestamp())
     ON CONFLICT(workspace_id,decision_case_id,stage_key) DO UPDATE SET owner_user_id=excluded.owner_user_id,updated_by=excluded.updated_by,updated_at=excluded.updated_at;
    INSERT INTO audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,decision_case_id,metadata_json)
     VALUES(target_workspace_id,actor_user_id,'stage.responsible_changed','decision_case',target_case_id,target_case_id,
      jsonb_build_object('stage_key','data_owner','previous_user_id',stage.owner_user_id,'new_user_id',new_owner_user_id));
   END IF;
  ELSE
   PERFORM public.platform_assign_decision(target_workspace_id,actor_user_id,target_case_id,target_stage_key,expected_updated_at,new_owner_user_id,new_approver_user_id);
  END IF;
 END IF;
 WITH stages AS (
  SELECT 'data_owner' key,a.owner_user_id,a.updated_at FROM (SELECT 1) x LEFT JOIN dation_private.workflow_stage_assignments a
   ON a.workspace_id=target_workspace_id AND a.decision_case_id=target_case_id AND a.stage_key='data_owner'
  UNION ALL SELECT n.key,a.owner_user_id,a.updated_at FROM (VALUES('logistics_assignment'),('logistics_scheduling')) n(key)
   LEFT JOIN decision_assignments a ON a.workspace_id=target_workspace_id AND a.decision_case_id=target_case_id AND a.node_id=n.key)
 SELECT jsonb_object_agg(key,jsonb_build_object('owner',dation_private.team_person(target_workspace_id,owner_user_id),'updated_at',updated_at,
  'approver',CASE WHEN key='data_owner' THEN NULL ELSE dation_private.team_person(target_workspace_id,owner_user_id) END,
  'approver_eligible',key<>'data_owner' AND dation_private.responsibility_eligible(target_workspace_id,owner_user_id,'decision_owner'),
  'owner_eligible',dation_private.responsibility_eligible(target_workspace_id,owner_user_id,CASE WHEN key='data_owner' THEN 'data_owner' ELSE 'decision_owner' END),
  'can_execute',role_name IN('admin','operator') AND (role_name='admin' OR owner_user_id=actor_user_id),
  'can_approve',role_name IN('admin','operator') AND (role_name='admin' OR owner_user_id=actor_user_id))) INTO result FROM stages;
 result=jsonb_set(result,'{data_preparation}',result->'data_owner');
 RETURN jsonb_build_object('case_id',target_case_id,'stages',result,'can_assign',role_name='admin' AND c.status<>'archived',
  'can_prepare',role_name<>'viewer','gates_enforced',(SELECT workflow_gates_enabled FROM dation_private.platform_release WHERE singleton),
  'attributes_applied',c.attributes_applied_at IS NOT NULL,'policy_version',c.workflow_policy_version);
END; $$;

CREATE OR REPLACE FUNCTION dation_private.case_collaboration(wid uuid,cid uuid,uid uuid) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT coalesce(jsonb_object_agg(n.node_id,jsonb_build_object('owner',dation_private.team_person(wid,a.owner_user_id),
  'approver',dation_private.team_person(wid,a.owner_user_id),'updated_at',a.updated_at,'can_execute',dation_private.responsibility_eligible(wid,a.owner_user_id,'decision_owner') AND (m.access_role='admin' OR m.access_role='operator' AND a.owner_user_id=uid),
  'can_approve',dation_private.responsibility_eligible(wid,a.owner_user_id,'decision_owner') AND (m.access_role='admin' OR m.access_role='operator' AND a.owner_user_id=uid),
  'admin_override',m.access_role='admin' AND a.owner_user_id IS NOT NULL AND a.owner_user_id<>uid)), '{}')
 FROM (VALUES('logistics_assignment'),('logistics_scheduling'),('logistics_final_assignment')) n(node_id)
 JOIN workspace_members m ON m.workspace_id=wid AND m.user_id=uid AND m.status='active'
 LEFT JOIN decision_assignments a ON a.workspace_id=wid AND a.decision_case_id=cid AND a.node_id=n.node_id;
$$;

-- Reuse the approval transaction, actor attribution and idempotency, using Owner.
DO $$ DECLARE source text; anchor text;
BEGIN
 source=pg_get_functiondef('dation_private.approve_decision_run_version(uuid,uuid,text)'::regprocedure);
 anchor='SELECT approver_user_id INTO assigned FROM public.decision_assignments';
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected approval ownership contract'; END IF;
 source=replace(source,anchor,'SELECT owner_user_id INTO assigned FROM public.decision_assignments');
 source=replace(source,'Assigned approver required','Decision Owner required');
 source=replace(source,'''assigned_approver_user_id'',assigned','''assigned_decision_owner_user_id'',assigned');
 EXECUTE source;
 source=pg_get_functiondef('dation_private.center_portfolio_facts(uuid,uuid,text)'::regprocedure);
 source=replace(source,'assignment.approver_user_id','assignment.owner_user_id');
 source=replace(source,'(member_role=''admin'' OR (member_role=''operator''',
  'dation_private.responsibility_eligible(wid,assignment.owner_user_id,''decision_owner'') AND (member_role=''admin'' OR (member_role=''operator''');
 EXECUTE source;
END; $$;
CREATE FUNCTION public.platform_validate_decision_stage(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid,target_node_id text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
BEGIN
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
 IF target_node_id NOT IN('logistics_assignment','logistics_scheduling') OR target_node_id IS NULL THEN RAISE EXCEPTION 'Invalid node' USING ERRCODE='22023'; END IF;
 PERFORM set_config('dation.actor_user_id',actor_user_id::text,true);
 PERFORM dation_private.require_workflow_responsibility(target_workspace_id,target_case_id,target_node_id,'configure');
 IF target_node_id='logistics_scheduling' AND NOT EXISTS(SELECT 1 FROM decision_runs
  WHERE workspace_id=target_workspace_id AND decision_case_id=target_case_id AND node_id='logistics_assignment'
   AND approved_at IS NOT NULL AND superseded_at IS NULL) THEN
  RAISE EXCEPTION 'Aprobá la decisión anterior antes de configurar.' USING ERRCODE='P0001'; END IF;
 RETURN jsonb_build_object('case_id',target_case_id,'node_id',target_node_id,'ready',true);
END; $$;
REVOKE ALL ON FUNCTION public.platform_validate_decision_stage(uuid,uuid,uuid,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_validate_decision_stage(uuid,uuid,uuid,text) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
