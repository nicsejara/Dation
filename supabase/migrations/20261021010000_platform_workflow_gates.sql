-- V2 Phase 5. Existing cases remain legacy; assignments/history are preserved.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';

-- The release activates this private switch only after the matching API and UI
-- are ready. It can be disabled for an application rollback without rewriting
-- a case, an assignment or approval evidence.
ALTER TABLE dation_private.platform_release ADD COLUMN workflow_gates_enabled boolean NOT NULL DEFAULT false;

ALTER TABLE public.decision_cases ADD COLUMN workflow_policy_version smallint NOT NULL DEFAULT 0
 CHECK(workflow_policy_version IN(0,1));
ALTER TABLE public.decision_cases ALTER COLUMN workflow_policy_version SET DEFAULT 1;
CREATE FUNCTION dation_private.protect_workflow_policy() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 IF TG_OP='INSERT' THEN NEW.workflow_policy_version=1;
 ELSIF NEW.workflow_policy_version IS DISTINCT FROM OLD.workflow_policy_version THEN
  RAISE EXCEPTION 'Workflow policy is immutable' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER case_workflow_policy BEFORE INSERT OR UPDATE OF workflow_policy_version
 ON public.decision_cases FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workflow_policy();

-- Called in the same transaction as admission/approval. Team and assignment
-- mutations use this same workspace lock, preventing eligibility races.
CREATE FUNCTION dation_private.require_workflow_responsibility(wid uuid,cid uuid,stage text,gate text)
RETURNS void LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE c public.decision_cases; person uuid;
BEGIN
 PERFORM 1 FROM public.workspaces WHERE id=wid FOR UPDATE;
 SELECT * INTO c FROM public.decision_cases WHERE workspace_id=wid AND id=cid FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
 IF c.status='archived' THEN RAISE EXCEPTION 'Restore case before continuing' USING ERRCODE='22023'; END IF;
 IF c.workflow_policy_version=0 OR NOT (SELECT workflow_gates_enabled FROM dation_private.platform_release WHERE singleton) THEN RETURN; END IF;
 IF gate IN('data','execute') THEN
  SELECT owner_user_id INTO person FROM dation_private.workflow_stage_assignments
   WHERE workspace_id=wid AND decision_case_id=cid AND stage_key='data_preparation';
  IF NOT dation_private.responsibility_eligible(wid,person,'data') THEN
   RAISE EXCEPTION 'Seleccioná un responsable de datos activo y elegible antes de continuar.' USING ERRCODE='P0001';
  END IF;
 END IF;
 IF gate='execute' THEN
  SELECT owner_user_id INTO person FROM public.decision_assignments
   WHERE workspace_id=wid AND decision_case_id=cid AND node_id=stage;
  IF NOT dation_private.responsibility_eligible(wid,person,'decision_owner') THEN
   RAISE EXCEPTION 'Seleccioná un responsable de la decisión activo y elegible antes de ejecutar.' USING ERRCODE='P0001';
  END IF;
 ELSIF gate='approve' THEN
  SELECT approver_user_id INTO person FROM public.decision_assignments
   WHERE workspace_id=wid AND decision_case_id=cid AND node_id=stage;
  IF NOT dation_private.responsibility_eligible(wid,person,'approver') THEN
   RAISE EXCEPTION 'Seleccioná un aprobador asignado activo y elegible antes de aprobar.' USING ERRCODE='P0001';
  END IF;
 ELSIF gate<>'data' THEN RAISE EXCEPTION 'Invalid workflow gate' USING ERRCODE='22023';
 END IF;
END; $$;

-- Capture ownership when a run is admitted, independently of its actual actor.
-- Assignment events alone cannot establish this ordering across waiting
-- transactions whose audit timestamps may predate lock acquisition.
CREATE FUNCTION dation_private.execution_responsibility_snapshot(wid uuid,cid uuid,nid text)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT jsonb_strip_nulls(jsonb_build_object(
  'data_responsible_user_id',d.owner_user_id,'data_assignment_updated_at',d.updated_at,
  'decision_owner_user_id',a.owner_user_id,'decision_assignment_updated_at',a.updated_at))
 FROM (SELECT 1) x
 LEFT JOIN dation_private.workflow_stage_assignments d ON d.workspace_id=wid AND d.decision_case_id=cid AND d.stage_key='data_preparation'
 LEFT JOIN public.decision_assignments a ON a.workspace_id=wid AND a.decision_case_id=cid AND a.node_id=nid;
$$;

CREATE FUNCTION public.platform_validate_data_stage(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
BEGIN
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
 PERFORM dation_private.require_workflow_responsibility(target_workspace_id,target_case_id,'data_preparation','data');
 RETURN jsonb_build_object('case_id',target_case_id,'ready',true);
END; $$;

-- One CAS transaction for technical access and the canonical responsibility set.
CREATE FUNCTION public.platform_update_member_foundation(target_workspace_id uuid,actor_user_id uuid,member_user_id uuid,
 expected_updated_at timestamptz,new_role text,new_status text,new_business_roles text[])
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE member public.workspace_members; result jsonb;
BEGIN
 PERFORM 1 FROM public.workspaces WHERE id=target_workspace_id FOR UPDATE;
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id,true);
 SELECT * INTO member FROM public.workspace_members WHERE workspace_id=target_workspace_id AND user_id=member_user_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Member not found' USING ERRCODE='P0002'; END IF;
 -- Update responsibilities while the actor still has Admin access. This also
 -- allows an Admin to demote themself when another active Admin remains.
 result=public.platform_set_member_responsibilities(target_workspace_id,actor_user_id,member_user_id,expected_updated_at,new_business_roles);
 SELECT * INTO member FROM public.workspace_members WHERE workspace_id=target_workspace_id AND user_id=member_user_id;
 PERFORM public.platform_update_member(target_workspace_id,actor_user_id,member_user_id,member.updated_at,new_role,member.business_role,new_status);
 SELECT * INTO member FROM public.workspace_members WHERE workspace_id=target_workspace_id AND user_id=member_user_id;
 RETURN result||jsonb_build_object('user_id',member_user_id,'status',new_status,'access_role',new_role,'updated_at',member.updated_at);
END; $$;

-- Evolve the current functions in place; retain their idempotency, lifecycle,
-- attribution, admission limits, approval evidence, reconciliation and grants.
DO $$ DECLARE source text; anchor text; BEGIN
 source=pg_get_functiondef('public.platform_workflow_responsibilities(uuid,uuid,uuid,text,text,timestamptz,uuid,uuid)'::regprocedure);
 anchor='''gates_enforced'',false';
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected responsibility contract'; END IF;
 source=replace(source,anchor,'''gates_enforced'',c.workflow_policy_version=1 AND (SELECT workflow_gates_enabled FROM dation_private.platform_release WHERE singleton),''policy_version'',c.workflow_policy_version');
 source=replace(source,'(new_owner_user_id IS NOT NULL AND NOT dation_private.responsibility_eligible',
  '(new_owner_user_id IS DISTINCT FROM previous_owner AND new_owner_user_id IS NOT NULL AND NOT dation_private.responsibility_eligible');
 source=replace(source,'(new_approver_user_id IS NOT NULL AND NOT dation_private.responsibility_eligible',
  '(new_approver_user_id IS DISTINCT FROM previous_approver AND new_approver_user_id IS NOT NULL AND NOT dation_private.responsibility_eligible');
 EXECUTE source;

 source=pg_get_functiondef('public.platform_assign_decision(uuid,uuid,uuid,text,timestamptz,uuid,uuid)'::regprocedure);
 anchor=$anchor$ FOREACH uid IN ARRAY ARRAY[new_owner_user_id,new_approver_user_id] LOOP
 IF uid IS NOT NULL AND NOT EXISTS(SELECT 1 FROM workspace_members m JOIN auth.users u ON u.id=m.user_id AND u.email_confirmed_at IS NOT NULL
 WHERE m.workspace_id=target_workspace_id AND m.user_id=uid AND m.status='active' AND m.access_role IN('admin','operator')) THEN RAISE EXCEPTION 'Assignee must be an active writer in this workspace' USING ERRCODE='22023'; END IF;
 END LOOP;$anchor$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected assignment contract'; END IF;
 EXECUTE replace(source,anchor,$insert$
 -- A retained historical person may stay while the other field changes, but
 -- a repeated assignment cannot reinstall an ineligible person.
 IF (new_owner_user_id IS NOT NULL AND NOT dation_private.responsibility_eligible(target_workspace_id,new_owner_user_id,'decision_owner') AND
       (new_owner_user_id IS DISTINCT FROM assignment.owner_user_id OR new_approver_user_id IS NOT DISTINCT FROM assignment.approver_user_id)) OR
    (new_approver_user_id IS NOT NULL AND NOT dation_private.responsibility_eligible(target_workspace_id,new_approver_user_id,'approver') AND
       (new_approver_user_id IS DISTINCT FROM assignment.approver_user_id OR new_owner_user_id IS NOT DISTINCT FROM assignment.owner_user_id)) THEN
  RAISE EXCEPTION 'Assignee responsibility is not eligible' USING ERRCODE='22023';
 END IF;
$insert$);

 source=pg_get_functiondef('dation_private.enqueue_dispatch_run(jsonb,jsonb,text,integer)'::regprocedure);
 anchor='    -- Serialize admission, but never calculation. Replays do not consume capacity.';
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected admission lock contract'; END IF;
 source=replace(source,anchor,'    perform 1 from public.workspaces where id=dation_private.workspace_id() for update;'||chr(10)||anchor);
 anchor='    if (select count(*) from public.dispatch_run_jobs';
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected admission capacity contract'; END IF;
 EXECUTE replace(source,anchor,$insert$
    if (run_payload->>'decision_case_id') is not null then
      perform dation_private.require_workflow_responsibility(dation_private.workspace_id(),
        (run_payload->>'decision_case_id')::uuid,run_payload->>'node_id','execute');
    end if;
$insert$||anchor);

 source=pg_get_functiondef('dation_private.approve_decision_run_version(uuid,uuid,text)'::regprocedure);
 anchor=' -- Date the approval after acquiring the case lock, not when the waiting request began.';
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected approval retry contract'; END IF;
 EXECUTE replace(source,anchor,$insert$
 PERFORM dation_private.require_workflow_responsibility(dation_private.workspace_id(),target_case_id,target_node_id,'approve');
$insert$||anchor);

 source=pg_get_functiondef('dation_private.activity_capture()'::regprocedure);
 anchor='IF NEW.status=''queued'' THEN uid=coalesce(uid,(row_data->>''created_by_user_id'')::uuid);meta=''{}'';';
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected admission audit contract'; END IF;
 EXECUTE replace(source,anchor,'IF NEW.status=''queued'' THEN uid=coalesce(uid,(row_data->>''created_by_user_id'')::uuid);meta=dation_private.execution_responsibility_snapshot(wid,cid,nid);');

 source=pg_get_functiondef('public.platform_activity(uuid,uuid,uuid,integer,timestamptz,uuid)'::regprocedure);
 anchor='''stage_key'',e.metadata_json->''stage_key'',';
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected activity allowlist'; END IF;
 EXECUTE replace(source,anchor,anchor||'''data_responsible_user_id'',e.metadata_json->''data_responsible_user_id'',''decision_owner_user_id'',e.metadata_json->''decision_owner_user_id'',''assigned_approver_user_id'',e.metadata_json->''assigned_approver_user_id'',''data_assignment_updated_at'',e.metadata_json->''data_assignment_updated_at'',''decision_assignment_updated_at'',e.metadata_json->''decision_assignment_updated_at'',');
END; $$;

REVOKE ALL ON FUNCTION dation_private.protect_workflow_policy(),dation_private.require_workflow_responsibility(uuid,uuid,text,text) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION dation_private.execution_responsibility_snapshot(uuid,uuid,text) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_validate_data_stage(uuid,uuid,uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_validate_data_stage(uuid,uuid,uuid) TO service_role;
REVOKE ALL ON FUNCTION public.platform_update_member_foundation(uuid,uuid,uuid,timestamptz,text,text,text[]) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_update_member_foundation(uuid,uuid,uuid,timestamptz,text,text,text[]) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
