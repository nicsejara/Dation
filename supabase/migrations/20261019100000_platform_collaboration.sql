-- Phase 8: confirmed-email invitations, workspace roles and per-node assignments.
-- No accounts, invitations, assignments or emails are created by this migration.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';
ALTER TABLE public.workspace_members ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.workspace_members ADD CONSTRAINT member_business_responsibility
 CHECK(business_role IS NULL OR business_role IN('data_owner','data_steward','decision_owner','approver'));
CREATE TABLE public.workspace_invitations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),workspace_id uuid NOT NULL REFERENCES public.workspaces(id),
 email text NOT NULL CHECK(email=lower(trim(email)) AND length(email) BETWEEN 3 AND 254 AND email ~ '^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$'),
 access_role text NOT NULL CHECK(access_role IN('admin','operator','viewer')),business_role text
 CHECK(business_role IS NULL OR business_role IN('data_owner','data_steward','decision_owner','approver')),
 status text NOT NULL DEFAULT 'pending' CHECK(status IN('pending','accepted','revoked')),
 invited_by uuid NOT NULL REFERENCES auth.users(id),accepted_by uuid REFERENCES auth.users(id),
 expires_at timestamptz NOT NULL DEFAULT now()+interval '7 days',accepted_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX workspace_invitation_pending_email ON public.workspace_invitations(workspace_id,email) WHERE status='pending';
CREATE INDEX workspace_invitation_recipient ON public.workspace_invitations(email,created_at DESC);
CREATE TABLE public.decision_assignments (
 workspace_id uuid NOT NULL REFERENCES public.workspaces(id),decision_case_id uuid NOT NULL,node_id text NOT NULL
 CHECK(node_id IN('logistics_assignment','logistics_scheduling','logistics_final_assignment')),
 owner_user_id uuid,approver_user_id uuid,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(decision_case_id,node_id),
 FOREIGN KEY(workspace_id,decision_case_id) REFERENCES public.decision_cases(workspace_id,id),
 FOREIGN KEY(workspace_id,owner_user_id) REFERENCES public.workspace_members(workspace_id,user_id),
 FOREIGN KEY(workspace_id,approver_user_id) REFERENCES public.workspace_members(workspace_id,user_id)
);
CREATE INDEX decision_assignments_workspace ON public.decision_assignments(workspace_id,owner_user_id,approver_user_id);
ALTER TABLE public.workspace_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.decision_assignments ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.workspace_invitations,public.decision_assignments FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT ON public.decision_assignments TO authenticated;
CREATE POLICY tenant_read ON public.decision_assignments FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
-- Mutations and invitation email disclosure use the checked service-only RPCs.

CREATE FUNCTION dation_private.team_actor(wid uuid,uid uuid,admin_only boolean DEFAULT false) RETURNS text
LANGUAGE plpgsql STABLE SET search_path=public,pg_temp AS $$
DECLARE role_name text;
BEGIN
 SELECT m.access_role INTO role_name FROM workspace_members m JOIN workspaces w ON w.id=m.workspace_id
 JOIN auth.users u ON u.id=m.user_id AND u.email_confirmed_at IS NOT NULL
 WHERE m.workspace_id=wid AND m.user_id=uid AND m.status='active' AND w.status='active';
 IF NOT FOUND OR (admin_only AND role_name<>'admin') THEN RAISE EXCEPTION 'Team access denied' USING ERRCODE='42501'; END IF;
 RETURN role_name;
END; $$;
CREATE FUNCTION dation_private.team_person(wid uuid,uid uuid) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT jsonb_build_object('id',m.user_id,'name',coalesce(nullif(p.display_name,''),'Miembro del equipo'),
 'active',m.status='active','access_role',m.access_role)
 FROM workspace_members m LEFT JOIN profiles p ON p.id=m.user_id WHERE m.workspace_id=wid AND m.user_id=uid;
$$;
CREATE FUNCTION dation_private.case_collaboration(wid uuid,cid uuid,uid uuid) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT coalesce(jsonb_object_agg(n.node_id,jsonb_build_object(
 'owner',dation_private.team_person(wid,a.owner_user_id),'approver',dation_private.team_person(wid,a.approver_user_id),
 'updated_at',a.updated_at,'can_approve',m.access_role='admin' OR (m.access_role='operator' AND (a.approver_user_id IS NULL OR a.approver_user_id=uid)),
 'admin_override',m.access_role='admin' AND a.approver_user_id IS NOT NULL AND a.approver_user_id<>uid)), '{}')
 FROM (VALUES('logistics_assignment'),('logistics_scheduling'),('logistics_final_assignment')) n(node_id)
 JOIN workspace_members m ON m.workspace_id=wid AND m.user_id=uid AND m.status='active'
 LEFT JOIN decision_assignments a ON a.workspace_id=wid AND a.decision_case_id=cid AND a.node_id=n.node_id;
$$;
CREATE FUNCTION public.platform_team(target_workspace_id uuid,actor_user_id uuid,search_text text DEFAULT '',page_limit integer DEFAULT 25,page_offset integer DEFAULT 0,candidates_only boolean DEFAULT false)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE role_name text; members jsonb; invitations jsonb; total bigint;
BEGIN
 role_name=dation_private.team_actor(target_workspace_id,actor_user_id);
 IF length(search_text)>120 OR page_limit NOT BETWEEN 1 AND 50 OR page_offset NOT BETWEEN 0 AND 1000000 THEN RAISE EXCEPTION 'Invalid page' USING ERRCODE='22023'; END IF;
 WITH matched AS MATERIALIZED (
 SELECT m.*,u.email,coalesce(nullif(p.display_name,''),'Miembro del equipo') AS name
 FROM workspace_members m JOIN auth.users u ON u.id=m.user_id LEFT JOIN profiles p ON p.id=m.user_id
 WHERE m.workspace_id=target_workspace_id AND (NOT candidates_only OR (m.status='active' AND m.access_role IN('admin','operator') AND u.email_confirmed_at IS NOT NULL))
 AND (search_text='' OR strpos(lower(concat_ws(' ',p.display_name,u.email)),lower(search_text))>0)),
 page AS (SELECT * FROM matched ORDER BY name,user_id LIMIT page_limit OFFSET page_offset)
 SELECT coalesce((SELECT jsonb_agg(to_jsonb(page) ORDER BY name,user_id) FROM page),'[]'),(SELECT count(*) FROM matched) INTO members,total;
 invitations='[]';
 IF role_name='admin' AND NOT candidates_only THEN
 SELECT coalesce(jsonb_agg(to_jsonb(i) ORDER BY i.created_at DESC,i.id DESC),'[]') INTO invitations
 FROM (SELECT id,email,access_role,business_role,CASE WHEN expires_at<=now() THEN 'expired' ELSE status END AS status,expires_at,created_at,updated_at
 FROM workspace_invitations WHERE workspace_id=target_workspace_id AND status='pending'
 AND (search_text='' OR strpos(email,lower(search_text))>0) ORDER BY created_at DESC,id DESC LIMIT page_limit OFFSET page_offset) i;
 END IF;
 RETURN jsonb_build_object('members',members,'invitations',invitations,'total',total,'invitation_total',
 CASE WHEN role_name='admin' AND NOT candidates_only THEN (SELECT count(*) FROM workspace_invitations WHERE workspace_id=target_workspace_id AND status='pending' AND (search_text='' OR strpos(email,lower(search_text))>0)) ELSE 0 END,
 'limit',page_limit,'offset',page_offset);
END; $$;
CREATE FUNCTION public.platform_invite_member(target_workspace_id uuid,actor_user_id uuid,invite_email text,invite_role text,invite_business_role text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE invitation workspace_invitations;
BEGIN
 PERFORM 1 FROM workspaces WHERE id=target_workspace_id FOR UPDATE;
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id,true);
 IF invite_email IS NULL OR invite_role IS NULL OR invite_email<>lower(trim(invite_email)) OR length(invite_email)>254 OR invite_email !~ '^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$'
 OR invite_role NOT IN('admin','operator','viewer') OR (invite_business_role IS NOT NULL AND invite_business_role NOT IN('data_owner','data_steward','decision_owner','approver')) THEN RAISE EXCEPTION 'Invalid invitation' USING ERRCODE='22023'; END IF;
 IF EXISTS(SELECT 1 FROM workspace_members m JOIN auth.users u ON u.id=m.user_id WHERE m.workspace_id=target_workspace_id AND lower(u.email)=invite_email) THEN
 RAISE EXCEPTION 'Member already exists; manage the member instead' USING ERRCODE='22023'; END IF;
 -- Revoke expired invitations before issuing a fresh one; active duplicates fail.
 UPDATE workspace_invitations SET status='revoked',updated_at=clock_timestamp() WHERE workspace_id=target_workspace_id AND email=invite_email AND status='pending' AND expires_at<=now();
 IF EXISTS(SELECT 1 FROM workspace_invitations WHERE workspace_id=target_workspace_id AND email=invite_email AND status='pending') THEN RAISE EXCEPTION 'Invitation already pending' USING ERRCODE='22023'; END IF;
 INSERT INTO workspace_invitations(workspace_id,email,access_role,business_role,invited_by) VALUES(target_workspace_id,invite_email,invite_role,invite_business_role,actor_user_id) RETURNING * INTO invitation;
 INSERT INTO audit_events(workspace_id,actor_user_id,event_type,metadata_json) VALUES(target_workspace_id,actor_user_id,'team.invited',jsonb_build_object('invitation_id',invitation.id,'email',invite_email,'access_role',invite_role,'business_role',invite_business_role));
 RETURN jsonb_build_object('id',invitation.id,'email',invitation.email,'expires_at',invitation.expires_at,'updated_at',invitation.updated_at);
END; $$;
CREATE FUNCTION public.platform_revoke_invitation(target_workspace_id uuid,actor_user_id uuid,invitation_id uuid,expected_updated_at timestamptz)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE invitation workspace_invitations;
BEGIN
 PERFORM 1 FROM workspaces WHERE id=target_workspace_id FOR UPDATE;
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id,true);
 SELECT * INTO invitation FROM workspace_invitations WHERE workspace_id=target_workspace_id AND id=invitation_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Invitation not found' USING ERRCODE='P0002'; END IF;
 IF invitation.status<>'pending' OR invitation.updated_at IS DISTINCT FROM expected_updated_at THEN RAISE EXCEPTION 'Invitation changed' USING ERRCODE='55006'; END IF;
 UPDATE workspace_invitations SET status='revoked',updated_at=clock_timestamp() WHERE id=invitation_id;
 INSERT INTO audit_events(workspace_id,actor_user_id,event_type,metadata_json) VALUES(target_workspace_id,actor_user_id,'team.invitation_revoked',jsonb_build_object('invitation_id',invitation_id));
 RETURN jsonb_build_object('id',invitation_id,'status','revoked');
END; $$;
CREATE FUNCTION public.platform_received_invitations(actor_user_id uuid,invitation_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE account auth.users; invitation workspace_invitations; member workspace_members;
BEGIN
 IF NOT coalesce((SELECT admissions_open FROM dation_private.platform_release WHERE singleton),false) THEN RAISE EXCEPTION 'Admissions closed' USING ERRCODE='42501'; END IF;
 SELECT * INTO account FROM auth.users WHERE id=actor_user_id AND email_confirmed_at IS NOT NULL;
 IF NOT FOUND THEN RAISE EXCEPTION 'Confirmed identity required' USING ERRCODE='42501'; END IF;
 IF invitation_id IS NULL THEN
 RETURN jsonb_build_object('items',coalesce((SELECT jsonb_agg(to_jsonb(i)) FROM (
 SELECT i.id,w.name AS workspace_name,i.access_role,i.business_role,i.expires_at FROM workspace_invitations i JOIN workspaces w ON w.id=i.workspace_id
 WHERE i.email=lower(account.email) AND i.status='pending' AND i.expires_at>now() AND w.status='active'
 AND EXISTS(SELECT 1 FROM workspace_members m WHERE m.workspace_id=i.workspace_id AND m.user_id=i.invited_by AND m.status='active' AND m.access_role='admin')
 ORDER BY i.created_at DESC,i.id LIMIT 50) i),'[]'));
 END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(actor_user_id::text,0));
 SELECT * INTO invitation FROM workspace_invitations WHERE id=invitation_id AND email=lower(account.email);
 IF NOT FOUND THEN RAISE EXCEPTION 'Invitation not found' USING ERRCODE='P0002'; END IF;
 PERFORM 1 FROM workspaces WHERE id=invitation.workspace_id AND status='active' FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Workspace unavailable' USING ERRCODE='42501'; END IF;
 SELECT * INTO invitation FROM workspace_invitations WHERE id=invitation_id FOR UPDATE;
 IF invitation.status='accepted' AND invitation.accepted_by=actor_user_id THEN
 PERFORM dation_private.team_actor(invitation.workspace_id,actor_user_id);
 RETURN jsonb_build_object('workspace_id',invitation.workspace_id,'already_accepted',true);
 END IF;
 IF invitation.status<>'pending' OR invitation.expires_at<=now() THEN RAISE EXCEPTION 'Invitation expired or revoked' USING ERRCODE='22023'; END IF;
 PERFORM dation_private.team_actor(invitation.workspace_id,invitation.invited_by,true);
 IF EXISTS(SELECT 1 FROM workspace_members WHERE workspace_id=invitation.workspace_id AND user_id=actor_user_id) THEN RAISE EXCEPTION 'Existing member cannot accept an invitation' USING ERRCODE='22023'; END IF;
 INSERT INTO profiles(id) VALUES(actor_user_id) ON CONFLICT DO NOTHING;
 INSERT INTO workspace_members(workspace_id,user_id,access_role,business_role,invited_by,joined_at)
 VALUES(invitation.workspace_id,actor_user_id,invitation.access_role,invitation.business_role,invitation.invited_by,clock_timestamp());
 UPDATE profiles SET active_workspace_id=invitation.workspace_id,updated_at=clock_timestamp() WHERE id=actor_user_id;
 UPDATE workspace_invitations SET status='accepted',accepted_by=actor_user_id,accepted_at=clock_timestamp(),updated_at=clock_timestamp() WHERE id=invitation_id;
 INSERT INTO audit_events(workspace_id,actor_user_id,event_type,metadata_json) VALUES(invitation.workspace_id,actor_user_id,'team.invitation_accepted',jsonb_build_object('invitation_id',invitation_id,'access_role',invitation.access_role,'business_role',invitation.business_role));
 RETURN jsonb_build_object('workspace_id',invitation.workspace_id,'already_accepted',false);
END; $$;
CREATE FUNCTION public.platform_update_member(target_workspace_id uuid,actor_user_id uuid,member_user_id uuid,expected_updated_at timestamptz,new_role text,new_business_role text,new_status text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE member workspace_members;
BEGIN
 PERFORM 1 FROM workspaces WHERE id=target_workspace_id FOR UPDATE;
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id,true);
 SELECT * INTO member FROM workspace_members WHERE workspace_id=target_workspace_id AND user_id=member_user_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Member not found' USING ERRCODE='P0002'; END IF;
 IF member.updated_at IS DISTINCT FROM expected_updated_at THEN RAISE EXCEPTION 'Member changed' USING ERRCODE='55006'; END IF;
 IF new_role IS NULL OR new_status IS NULL OR new_role NOT IN('admin','operator','viewer') OR new_status NOT IN('active','disabled') OR
 (new_business_role IS NOT NULL AND new_business_role NOT IN('data_owner','data_steward','decision_owner','approver')) THEN RAISE EXCEPTION 'Invalid role' USING ERRCODE='22023'; END IF;
 IF member.access_role='admin' AND member.status='active' AND (new_role<>'admin' OR new_status<>'active') AND NOT EXISTS(
 SELECT 1 FROM workspace_members m JOIN auth.users u ON u.id=m.user_id AND u.email_confirmed_at IS NOT NULL
 WHERE m.workspace_id=target_workspace_id AND m.user_id<>member_user_id AND m.access_role='admin' AND m.status='active') THEN
 RAISE EXCEPTION 'Keep at least one active administrator' USING ERRCODE='22023'; END IF;
 UPDATE workspace_members SET access_role=new_role,business_role=new_business_role,status=new_status,updated_at=clock_timestamp()
 WHERE workspace_id=target_workspace_id AND user_id=member_user_id;
 INSERT INTO audit_events(workspace_id,actor_user_id,event_type,metadata_json) VALUES(target_workspace_id,actor_user_id,'team.member_updated',
 jsonb_build_object('user_id',member_user_id,'before',jsonb_build_object('access_role',member.access_role,'business_role',member.business_role,'status',member.status),'after',jsonb_build_object('access_role',new_role,'business_role',new_business_role,'status',new_status)));
 RETURN jsonb_build_object('user_id',member_user_id,'status',new_status);
END; $$;
CREATE FUNCTION public.platform_assign_decision(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid,target_node_id text,expected_updated_at timestamptz,new_owner_user_id uuid,new_approver_user_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE assignment decision_assignments; uid uuid;
BEGIN
 PERFORM 1 FROM workspaces WHERE id=target_workspace_id FOR UPDATE;
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id,true);
 PERFORM 1 FROM decision_cases WHERE id=target_case_id AND workspace_id=target_workspace_id AND status<>'archived' FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Active case not found' USING ERRCODE='P0002'; END IF;
 IF target_node_id IS NULL OR target_node_id NOT IN('logistics_assignment','logistics_scheduling','logistics_final_assignment') THEN RAISE EXCEPTION 'Invalid node' USING ERRCODE='22023'; END IF;
 SELECT * INTO assignment FROM decision_assignments WHERE decision_case_id=target_case_id AND node_id=target_node_id FOR UPDATE;
 IF assignment.updated_at IS DISTINCT FROM expected_updated_at THEN RAISE EXCEPTION 'Assignment changed' USING ERRCODE='55006'; END IF;
 FOREACH uid IN ARRAY ARRAY[new_owner_user_id,new_approver_user_id] LOOP
 IF uid IS NOT NULL AND NOT EXISTS(SELECT 1 FROM workspace_members m JOIN auth.users u ON u.id=m.user_id AND u.email_confirmed_at IS NOT NULL
 WHERE m.workspace_id=target_workspace_id AND m.user_id=uid AND m.status='active' AND m.access_role IN('admin','operator')) THEN RAISE EXCEPTION 'Assignee must be an active writer in this workspace' USING ERRCODE='22023'; END IF;
 END LOOP;
 INSERT INTO decision_assignments(workspace_id,decision_case_id,node_id,owner_user_id,approver_user_id)
 VALUES(target_workspace_id,target_case_id,target_node_id,new_owner_user_id,new_approver_user_id)
 ON CONFLICT(decision_case_id,node_id) DO UPDATE SET owner_user_id=excluded.owner_user_id,approver_user_id=excluded.approver_user_id,updated_at=clock_timestamp()
 RETURNING * INTO assignment;
 INSERT INTO audit_events(workspace_id,actor_user_id,event_type,metadata_json) VALUES(target_workspace_id,actor_user_id,'decision.assigned',
 jsonb_build_object('case_id',target_case_id,'node_id',target_node_id,'owner_user_id',new_owner_user_id,'approver_user_id',new_approver_user_id));
 RETURN jsonb_build_object('updated_at',assignment.updated_at);
END; $$;

CREATE FUNCTION public.platform_case_collaboration(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
BEGIN
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
 IF NOT EXISTS(SELECT 1 FROM decision_cases WHERE workspace_id=target_workspace_id AND id=target_case_id) THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
 RETURN dation_private.case_collaboration(target_workspace_id,target_case_id,actor_user_id);
END; $$;

-- Preserve the existing approval evidence, retry behavior and reconciliation.
CREATE OR REPLACE FUNCTION dation_private.approve_decision_run_version(target_run_id uuid, target_case_id uuid, target_node_id text)
 RETURNS SETOF decision_runs
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
DECLARE target public.decision_runs%rowtype; source public.decision_runs%rowtype;
 approval_time timestamptz; member_role text; assigned uuid; next_assignment public.decision_assignments;
BEGIN
 -- Serialize permission/assignment changes with approval, before the case lock.
 PERFORM 1 FROM public.workspaces WHERE id=dation_private.workspace_id() FOR UPDATE;
 member_role=dation_private.team_actor(dation_private.workspace_id(),nullif(current_setting('dation.actor_user_id',true),'')::uuid);
 IF member_role='viewer' THEN RAISE EXCEPTION 'Writer required' USING ERRCODE='42501'; END IF;
 SELECT approver_user_id INTO assigned FROM public.decision_assignments
 WHERE workspace_id=dation_private.workspace_id() AND decision_case_id=target_case_id AND node_id=target_node_id;
 IF assigned IS NOT NULL AND assigned::text<>current_setting('dation.actor_user_id') AND member_role<>'admin' THEN
 RAISE EXCEPTION 'Assigned approver required' USING ERRCODE='42501'; END IF;
 -- Lock the shared case first, before any candidate. This also serializes parent/child approvals.
 PERFORM 1 FROM public.decision_cases WHERE id=target_case_id FOR UPDATE;
 SELECT * INTO target FROM public.decision_runs WHERE id=target_run_id FOR UPDATE;
 IF NOT FOUND OR target.status<>'completed' OR target.decision_case_id IS DISTINCT FROM target_case_id
    OR target.node_id IS DISTINCT FROM target_node_id OR NOT (
      target_node_id='logistics_assignment' AND target.schema_version='assignment_v1'
      OR target_node_id='logistics_scheduling' AND target.schema_version='scheduling_v1') THEN
   RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='La corrida no puede aprobarse para ese Decision Case';
 END IF;
 IF target.superseded_at IS NOT NULL THEN
   RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Una aprobación anterior no puede reactivarse; ejecutá una nueva alternativa';
 END IF;
 IF target.upstream_run_id IS NOT NULL THEN
   SELECT * INTO source FROM public.decision_runs WHERE id=target.upstream_run_id;
   IF NOT FOUND OR source.decision_case_id IS DISTINCT FROM target_case_id
     OR source.status<>'completed' OR source.approved_at IS NULL OR source.superseded_at IS NOT NULL THEN
     RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='La corrida upstream ya no es la decisión aprobada vigente';
   END IF;
 END IF;
 IF EXISTS(SELECT 1 FROM public.decision_cases WHERE id=target_case_id AND status='archived') THEN
 RAISE EXCEPTION 'Restore the case before approving' USING ERRCODE='22023'; END IF;
 IF target.approved_at IS NOT NULL THEN
   RETURN NEXT target; RETURN; -- A retry preserves actor/time and emits no second event.
 END IF;
 -- Date the approval after acquiring the case lock, not when the waiting request began.
 approval_time := clock_timestamp();
 INSERT INTO public.decision_approval_events(run_id,case_id,node_id,action,actor,actor_user_id,occurred_at,replacement_run_id)
   SELECT id,target_case_id,target_node_id,'superseded',('user:'||current_setting('dation.actor_user_id')),current_setting('dation.actor_user_id')::uuid,approval_time,target_run_id
   FROM public.decision_runs WHERE decision_case_id=target_case_id AND node_id=target_node_id
     AND approved_at IS NOT NULL AND superseded_at IS NULL;
 UPDATE public.decision_runs SET superseded_at=approval_time,superseded_by_run_id=target_run_id
   WHERE decision_case_id=target_case_id AND node_id=target_node_id AND id<>target_run_id
     AND approved_at IS NOT NULL AND superseded_at IS NULL;
 UPDATE public.decision_runs SET approved_at=approval_time,approved_by=('user:'||current_setting('dation.actor_user_id')),approved_by_user_id=current_setting('dation.actor_user_id')::uuid,
   configuration_json=jsonb_set(configuration_json,'{decision_case}',
     coalesce(configuration_json->'decision_case','{}'::jsonb)||jsonb_build_object(
       'case_id',target_case_id::text,'node_id',target_node_id,'status','approved','approved_at',approval_time)),
   result_json=jsonb_set(result_json,'{decision_case}',
     coalesce(result_json->'decision_case','{}'::jsonb)||jsonb_build_object(
       'case_id',target_case_id::text,'node_id',target_node_id,'status','approved','approved_at',approval_time))
   WHERE id=target_run_id;
 INSERT INTO public.decision_approval_events(run_id,case_id,node_id,action,actor,actor_user_id,occurred_at)
   VALUES(target_run_id,target_case_id,target_node_id,'approved',('user:'||current_setting('dation.actor_user_id')),current_setting('dation.actor_user_id')::uuid,approval_time);
 SELECT * INTO next_assignment FROM public.decision_assignments WHERE decision_case_id=target_case_id AND node_id='logistics_scheduling';
 INSERT INTO public.audit_events(workspace_id,actor_user_id,event_type,metadata_json)
 VALUES(dation_private.workspace_id(),current_setting('dation.actor_user_id')::uuid,'decision.approved',
 jsonb_build_object('case_id',target_case_id,'node_id',target_node_id,'run_id',target_run_id,
 'admin_override',member_role='admin' AND assigned IS NOT NULL AND assigned::text<>current_setting('dation.actor_user_id'),
 'assigned_approver_user_id',assigned,'next_node_id',CASE WHEN target_node_id='logistics_assignment' THEN 'logistics_scheduling' ELSE NULL END,
 'next_owner_user_id',CASE WHEN target_node_id='logistics_assignment' THEN next_assignment.owner_user_id ELSE NULL END,
 'next_approver_user_id',CASE WHEN target_node_id='logistics_assignment' THEN next_assignment.approver_user_id ELSE NULL END));
 RETURN QUERY SELECT * FROM public.decision_runs WHERE id=target_run_id;
END;
$function$
;

-- Extend the existing bounded snapshots; no duplicate workflow state.
CREATE OR REPLACE FUNCTION public.platform_decision_center(target_workspace_id uuid,actor_user_id uuid,
 target_case_id uuid DEFAULT NULL,filter_name text DEFAULT 'all',search_text text DEFAULT '',dda text DEFAULT 'all',
 target_node_id text DEFAULT NULL,page_limit integer DEFAULT 25,page_offset integer DEFAULT 0)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE current_case decision_cases; answer jsonb; history jsonb;
BEGIN
 PERFORM dation_private.data_actor(target_workspace_id,actor_user_id);
 PERFORM set_config('dation.workspace_id',target_workspace_id::text,true);
 IF filter_name NOT IN('all','in_progress','review','completed','archived') OR dda NOT IN('all','logistics')
 OR length(search_text)>120 OR page_limit NOT BETWEEN 1 AND 50 OR page_offset NOT BETWEEN 0 AND 1000000
 OR (target_node_id IS NOT NULL AND target_node_id NOT IN('logistics_assignment','logistics_scheduling','logistics_final_assignment')) THEN
  RAISE EXCEPTION 'Invalid center query' USING ERRCODE='22023'; END IF;
 IF target_case_id IS NOT NULL THEN
  SELECT * INTO current_case FROM decision_cases WHERE id=target_case_id AND workspace_id=target_workspace_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
  answer=dation_private.center_bundle(current_case)||jsonb_build_object('collaboration',dation_private.case_collaboration(target_workspace_id,current_case.id,actor_user_id));
  IF target_node_id IS NOT NULL THEN
   SELECT coalesce(jsonb_agg(dation_private.center_run(r) ORDER BY r.created_at DESC,r.id DESC),'[]') INTO history
   FROM (SELECT * FROM decision_runs WHERE workspace_id=target_workspace_id AND decision_case_id=current_case.id AND node_id=target_node_id
     ORDER BY created_at DESC,id DESC LIMIT page_limit OFFSET page_offset) r;
   RETURN answer||jsonb_build_object('runs',history,'node_id',target_node_id,'limit',page_limit,'offset',page_offset);
  END IF;
  RETURN answer||jsonb_build_object('orders',(SELECT dation_private.hub_dataset(d) FROM datasets d WHERE id=current_case.orders_dataset_id AND workspace_id=target_workspace_id),
   'fleet',(SELECT dation_private.hub_dataset(d) FROM datasets d WHERE id=current_case.fleet_dataset_id AND workspace_id=target_workspace_id),
   'run_people',coalesce((SELECT jsonb_object_agg(r.id::text,dation_private.center_run(r)) FROM decision_runs r
    WHERE r.workspace_id=target_workspace_id AND r.decision_case_id=current_case.id AND r.id IN
     (SELECT (value->k->>'id')::uuid FROM jsonb_each(answer->'summaries') CROSS JOIN (VALUES('latest'),('approved')) v(k))),'{}'));
 END IF;
 WITH base AS MATERIALIZED (SELECT c.*,(dation_private.center_bundle(c)||jsonb_build_object('collaboration',dation_private.case_collaboration(target_workspace_id,c.id,actor_user_id))) bundle FROM decision_cases c WHERE c.workspace_id=target_workspace_id
  AND (dda='all' OR c.domain=dda) AND (search_text='' OR strpos(lower(concat_ws(' ',c.id::text,'DC-'||substr(c.id::text,1,8),c.label)),lower(search_text))>0)),
 matched AS (SELECT * FROM base WHERE CASE filter_name
  WHEN 'all' THEN bundle->>'status'<>'archived'
  WHEN 'archived' THEN bundle->>'status'='archived'
  WHEN 'completed' THEN bundle->>'status'='completed'
  WHEN 'review' THEN (bundle->>'in_review')::boolean
  ELSE bundle->>'status'='active' AND NOT (bundle->>'in_review')::boolean END),
 page AS (SELECT * FROM matched ORDER BY last_activity_at DESC,id DESC LIMIT page_limit OFFSET page_offset)
 SELECT jsonb_build_object('items',coalesce((SELECT jsonb_agg(bundle ORDER BY last_activity_at DESC,id DESC) FROM page),'[]'),
  'total',(SELECT count(*) FROM matched),'limit',page_limit,'offset',page_offset) INTO answer;
 RETURN answer;
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
     'last_activity_at',c.last_activity_at),
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
   SELECT work.*,count(*) OVER() AS total FROM work ORDER BY last_activity_at DESC,case_id DESC,node_id LIMIT 5
  ) SELECT coalesce(jsonb_agg(to_jsonb(candidates)-'total'
      ORDER BY last_activity_at DESC,case_id DESC,node_id),'[]'),coalesce(max(total),0)
    INTO attention,attention_total FROM candidates;
 END IF;
 RETURN jsonb_build_object('recent_cases',recent,
   'attention',jsonb_build_object('items',attention,'total',attention_total));
END; $$;

REVOKE ALL ON FUNCTION dation_private.team_actor(uuid,uuid,boolean),dation_private.team_person(uuid,uuid),dation_private.case_collaboration(uuid,uuid,uuid) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_team(uuid,uuid,text,integer,integer,boolean),public.platform_invite_member(uuid,uuid,text,text,text),public.platform_revoke_invitation(uuid,uuid,uuid,timestamptz),public.platform_received_invitations(uuid,uuid),public.platform_update_member(uuid,uuid,uuid,timestamptz,text,text,text),public.platform_assign_decision(uuid,uuid,uuid,text,timestamptz,uuid,uuid),public.platform_case_collaboration(uuid,uuid,uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_team(uuid,uuid,text,integer,integer,boolean),public.platform_invite_member(uuid,uuid,text,text,text),public.platform_revoke_invitation(uuid,uuid,uuid,timestamptz),public.platform_received_invitations(uuid,uuid),public.platform_update_member(uuid,uuid,uuid,timestamptz,text,text,text),public.platform_assign_decision(uuid,uuid,uuid,text,timestamptz,uuid,uuid),public.platform_case_collaboration(uuid,uuid,uuid) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;

