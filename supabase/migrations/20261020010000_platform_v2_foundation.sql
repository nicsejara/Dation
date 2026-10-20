-- V2 Phase 1: additive responsibility contracts. No mandatory workflow gates yet.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';

-- Canonical responsibility set. business_role remains a legacy single-value
-- projection; old clients can replace that set through its compatibility trigger.
CREATE TABLE dation_private.member_responsibilities (
 workspace_id uuid NOT NULL,user_id uuid NOT NULL,responsibility text NOT NULL
 CHECK(responsibility IN('data_owner','data_steward','decision_owner','approver')),
 PRIMARY KEY(workspace_id,user_id,responsibility),
 FOREIGN KEY(workspace_id,user_id) REFERENCES public.workspace_members(workspace_id,user_id) ON DELETE CASCADE
);
INSERT INTO dation_private.member_responsibilities SELECT workspace_id,user_id,business_role FROM public.workspace_members WHERE business_role IS NOT NULL;
CREATE TABLE dation_private.workflow_stage_assignments (
 workspace_id uuid NOT NULL,decision_case_id uuid NOT NULL,stage_key text NOT NULL CHECK(stage_key ~ '^[a-z][a-z0-9_]{1,63}$'),
 owner_user_id uuid,updated_by uuid REFERENCES auth.users(id),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(workspace_id,decision_case_id,stage_key),
 FOREIGN KEY(workspace_id,decision_case_id) REFERENCES public.decision_cases(workspace_id,id) ON DELETE CASCADE,
 FOREIGN KEY(workspace_id,owner_user_id) REFERENCES public.workspace_members(workspace_id,user_id)
);
ALTER TABLE dation_private.member_responsibilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE dation_private.member_responsibilities FORCE ROW LEVEL SECURITY;
ALTER TABLE dation_private.workflow_stage_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE dation_private.workflow_stage_assignments FORCE ROW LEVEL SECURITY;
REVOKE ALL ON dation_private.member_responsibilities,dation_private.workflow_stage_assignments FROM PUBLIC,anon,authenticated,service_role;

CREATE FUNCTION dation_private.member_responsibility_compat() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
BEGIN
 IF TG_OP='INSERT' OR NEW.business_role IS DISTINCT FROM OLD.business_role THEN
  DELETE FROM dation_private.member_responsibilities WHERE workspace_id=NEW.workspace_id AND user_id=NEW.user_id;
  IF NEW.business_role IS NOT NULL THEN INSERT INTO dation_private.member_responsibilities VALUES(NEW.workspace_id,NEW.user_id,NEW.business_role); END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER member_responsibility_compat AFTER INSERT OR UPDATE OF business_role ON public.workspace_members FOR EACH ROW EXECUTE FUNCTION dation_private.member_responsibility_compat();

CREATE FUNCTION dation_private.member_roles(wid uuid,uid uuid) RETURNS text[]
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT coalesce(array_agg(responsibility ORDER BY responsibility),'{}'::text[]) FROM dation_private.member_responsibilities WHERE workspace_id=wid AND user_id=uid;
$$;
CREATE FUNCTION dation_private.responsibility_eligible(wid uuid,uid uuid,required_group text) RETURNS boolean
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT EXISTS(SELECT 1 FROM public.workspace_members m JOIN auth.users u ON u.id=m.user_id
 WHERE m.workspace_id=wid AND m.user_id=uid AND m.status='active' AND m.access_role IN('admin','operator') AND u.email_confirmed_at IS NOT NULL
 AND dation_private.member_roles(wid,uid) && CASE required_group WHEN 'data' THEN ARRAY['data_owner','data_steward'] WHEN 'decision_owner' THEN ARRAY['decision_owner'] WHEN 'approver' THEN ARRAY['approver'] ELSE '{}'::text[] END);
$$;

CREATE FUNCTION public.platform_team_foundation(target_workspace_id uuid,actor_user_id uuid,search_text text DEFAULT '',page_limit integer DEFAULT 25,page_offset integer DEFAULT 0,candidates_only boolean DEFAULT false,responsibility_group text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE answer jsonb; members jsonb; total bigint;
BEGIN
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
 IF responsibility_group IS NULL THEN
  answer=public.platform_team(target_workspace_id,actor_user_id,search_text,page_limit,page_offset,candidates_only);
  SELECT coalesce(jsonb_agg(value||jsonb_build_object('business_roles',dation_private.member_roles(target_workspace_id,(value->>'user_id')::uuid)) ORDER BY ordinal),'[]') INTO members FROM jsonb_array_elements(answer->'members') WITH ORDINALITY e(value,ordinal);
  RETURN answer||jsonb_build_object('members',members);
 END IF;
 IF NOT candidates_only OR responsibility_group NOT IN('data','decision_owner','approver') OR search_text IS NULL OR length(search_text)>120 OR page_limit IS NULL OR page_limit NOT BETWEEN 1 AND 50 OR page_offset IS NULL OR page_offset NOT BETWEEN 0 AND 1000000 THEN RAISE EXCEPTION 'Invalid candidates query' USING ERRCODE='22023'; END IF;
 WITH matched AS MATERIALIZED (
  SELECT m.*,u.email,coalesce(nullif(p.display_name,''),'Miembro del equipo') name,dation_private.member_roles(m.workspace_id,m.user_id) business_roles
  FROM public.workspace_members m JOIN auth.users u ON u.id=m.user_id LEFT JOIN public.profiles p ON p.id=m.user_id
  WHERE m.workspace_id=target_workspace_id AND dation_private.responsibility_eligible(target_workspace_id,m.user_id,responsibility_group)
   AND (search_text='' OR strpos(lower(concat_ws(' ',p.display_name,u.email)),lower(search_text))>0)),
 page AS (SELECT * FROM matched ORDER BY name,user_id LIMIT page_limit OFFSET page_offset)
 SELECT coalesce((SELECT jsonb_agg(to_jsonb(p) ORDER BY name,user_id) FROM page p),'[]'),(SELECT count(*) FROM matched) INTO members,total;
 RETURN jsonb_build_object('members',members,'invitations','[]'::jsonb,'total',total,'invitation_total',0,'limit',page_limit,'offset',page_offset);
END; $$;

CREATE FUNCTION public.platform_set_member_responsibilities(target_workspace_id uuid,actor_user_id uuid,member_user_id uuid,expected_updated_at timestamptz,new_responsibilities text[])
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE member public.workspace_members; roles text[]; previous text[];
BEGIN
 PERFORM 1 FROM public.workspaces WHERE id=target_workspace_id FOR UPDATE;
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id,true);
 SELECT * INTO member FROM public.workspace_members WHERE workspace_id=target_workspace_id AND user_id=member_user_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Member not found' USING ERRCODE='P0002'; END IF;
 IF expected_updated_at IS NULL OR member.updated_at IS DISTINCT FROM expected_updated_at THEN RAISE EXCEPTION 'Member changed' USING ERRCODE='55006'; END IF;
 IF new_responsibilities IS NULL OR cardinality(new_responsibilities)>4 OR array_position(new_responsibilities,NULL) IS NOT NULL OR NOT new_responsibilities <@ ARRAY['data_owner','data_steward','decision_owner','approver'] THEN RAISE EXCEPTION 'Invalid responsibilities' USING ERRCODE='22023'; END IF;
 SELECT coalesce(array_agg(DISTINCT value ORDER BY value),'{}') INTO roles FROM unnest(new_responsibilities) t(value);
 IF cardinality(roles)<>cardinality(new_responsibilities) THEN RAISE EXCEPTION 'Duplicate responsibility' USING ERRCODE='22023'; END IF;
 previous=dation_private.member_roles(target_workspace_id,member_user_id);
 IF roles=previous THEN RETURN jsonb_build_object('business_roles',roles,'updated_at',member.updated_at); END IF;
 UPDATE public.workspace_members SET business_role=roles[1],updated_at=clock_timestamp() WHERE workspace_id=target_workspace_id AND user_id=member_user_id RETURNING * INTO member;
 DELETE FROM dation_private.member_responsibilities WHERE workspace_id=target_workspace_id AND user_id=member_user_id;
 INSERT INTO dation_private.member_responsibilities SELECT target_workspace_id,member_user_id,value FROM unnest(roles) t(value);
 INSERT INTO public.audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,metadata_json) VALUES(target_workspace_id,actor_user_id,'member.responsibilities_changed','member',member_user_id,jsonb_build_object('user_id',member_user_id,'previous',previous,'responsibilities',roles));
 RETURN jsonb_build_object('business_roles',roles,'updated_at',member.updated_at);
END; $$;

CREATE FUNCTION public.platform_workflow_responsibilities(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid,operation text DEFAULT 'read',target_stage_key text DEFAULT NULL,expected_updated_at timestamptz DEFAULT NULL,new_owner_user_id uuid DEFAULT NULL,new_approver_user_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE role_name text; c public.decision_cases; stage dation_private.workflow_stage_assignments; assignment public.decision_assignments; previous_owner uuid; previous_approver uuid; stamp timestamptz; result jsonb; assignment_field text;
BEGIN
 IF operation NOT IN('read','write') OR operation IS NULL THEN RAISE EXCEPTION 'Invalid operation' USING ERRCODE='22023'; END IF;
 IF operation='write' THEN PERFORM 1 FROM public.workspaces WHERE id=target_workspace_id FOR UPDATE; END IF;
 role_name=dation_private.team_actor(target_workspace_id,actor_user_id,operation='write');
 SELECT * INTO c FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=target_case_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
 IF operation='write' THEN
  IF c.status='archived' THEN RAISE EXCEPTION 'Restore case before assigning' USING ERRCODE='22023'; END IF;
  IF target_stage_key IS NULL OR target_stage_key NOT IN('data_preparation','logistics_assignment','logistics_scheduling') THEN RAISE EXCEPTION 'Invalid stage' USING ERRCODE='22023'; END IF;
  IF target_stage_key='data_preparation' THEN
   IF new_approver_user_id IS NOT NULL THEN RAISE EXCEPTION 'Data is not a decision node' USING ERRCODE='22023'; END IF;
   SELECT * INTO stage FROM dation_private.workflow_stage_assignments WHERE workspace_id=target_workspace_id AND decision_case_id=target_case_id AND stage_key=target_stage_key FOR UPDATE;
   previous_owner=stage.owner_user_id;stamp=stage.updated_at;
  ELSE
   SELECT * INTO assignment FROM public.decision_assignments WHERE workspace_id=target_workspace_id AND decision_case_id=target_case_id AND node_id=target_stage_key FOR UPDATE;
   previous_owner=assignment.owner_user_id;previous_approver=assignment.approver_user_id;stamp=assignment.updated_at;
  END IF;
  IF stamp IS DISTINCT FROM expected_updated_at THEN RAISE EXCEPTION 'Assignment changed' USING ERRCODE='55006'; END IF;
  IF (new_owner_user_id IS NOT NULL AND NOT dation_private.responsibility_eligible(target_workspace_id,new_owner_user_id,CASE WHEN target_stage_key='data_preparation' THEN 'data' ELSE 'decision_owner' END)) OR (new_approver_user_id IS NOT NULL AND NOT dation_private.responsibility_eligible(target_workspace_id,new_approver_user_id,'approver')) THEN RAISE EXCEPTION 'Assignee responsibility is not eligible' USING ERRCODE='22023'; END IF;
  IF previous_owner IS DISTINCT FROM new_owner_user_id OR previous_approver IS DISTINCT FROM new_approver_user_id THEN
   IF target_stage_key='data_preparation' THEN
    INSERT INTO dation_private.workflow_stage_assignments VALUES(target_workspace_id,target_case_id,target_stage_key,new_owner_user_id,actor_user_id,clock_timestamp())
    ON CONFLICT(workspace_id,decision_case_id,stage_key) DO UPDATE SET owner_user_id=excluded.owner_user_id,updated_by=excluded.updated_by,updated_at=excluded.updated_at;
   ELSE
    PERFORM public.platform_assign_decision(target_workspace_id,actor_user_id,target_case_id,target_stage_key,expected_updated_at,new_owner_user_id,new_approver_user_id);
   END IF;
   FOR assignment_field IN SELECT value FROM unnest(ARRAY['owner','approver']) t(value) LOOP
    IF (assignment_field='owner' AND previous_owner IS DISTINCT FROM new_owner_user_id) OR (assignment_field='approver' AND previous_approver IS DISTINCT FROM new_approver_user_id) THEN
     INSERT INTO public.audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,decision_case_id,node_id,metadata_json)
     VALUES(target_workspace_id,actor_user_id,CASE WHEN target_stage_key='data_preparation' THEN 'stage.responsible_' ELSE 'decision.'||assignment_field||'_' END||CASE WHEN (CASE WHEN assignment_field='owner' THEN previous_owner ELSE previous_approver END) IS NULL THEN 'assigned' ELSE 'changed' END,
      'decision_case',target_case_id,target_case_id,CASE WHEN target_stage_key='data_preparation' THEN NULL ELSE target_stage_key END,
      jsonb_build_object('case_id',target_case_id,'stage_key',target_stage_key,'previous_user_id',CASE WHEN assignment_field='owner' THEN previous_owner ELSE previous_approver END,'new_user_id',CASE WHEN assignment_field='owner' THEN new_owner_user_id ELSE new_approver_user_id END));
    END IF;
   END LOOP;
  END IF;
 END IF;
 WITH stages AS (SELECT 'data_preparation' key,a.owner_user_id,NULL::uuid approver_user_id,a.updated_at FROM (SELECT 1) x LEFT JOIN dation_private.workflow_stage_assignments a ON a.workspace_id=target_workspace_id AND a.decision_case_id=target_case_id AND a.stage_key='data_preparation'
 UNION ALL SELECT n.key,a.owner_user_id,a.approver_user_id,a.updated_at FROM (VALUES('logistics_assignment'),('logistics_scheduling')) n(key) LEFT JOIN public.decision_assignments a ON a.workspace_id=target_workspace_id AND a.decision_case_id=target_case_id AND a.node_id=n.key)
 SELECT jsonb_object_agg(key,jsonb_build_object('owner',dation_private.team_person(target_workspace_id,owner_user_id),'approver',dation_private.team_person(target_workspace_id,approver_user_id),'updated_at',updated_at,
 'owner_eligible',dation_private.responsibility_eligible(target_workspace_id,owner_user_id,CASE WHEN key='data_preparation' THEN 'data' ELSE 'decision_owner' END),'approver_eligible',dation_private.responsibility_eligible(target_workspace_id,approver_user_id,'approver'))) INTO result FROM stages;
 RETURN jsonb_build_object('case_id',target_case_id,'stages',result,'can_assign',role_name='admin' AND c.status<>'archived','gates_enforced',false);
END; $$;

-- The activity projection remains an explicit bounded allowlist.
DO $$ DECLARE source text; BEGIN
 source=pg_get_functiondef('public.platform_activity(uuid,uuid,uuid,integer,timestamptz,uuid)'::regprocedure);
 IF strpos(source,'''section'',e.metadata_json->''section'',')=0 THEN RAISE EXCEPTION 'Unexpected activity definition'; END IF;
 source=replace(source,'''section'',e.metadata_json->''section'',','''section'',e.metadata_json->''section'',''stage_key'',e.metadata_json->''stage_key'',''previous_user_id'',e.metadata_json->''previous_user_id'',''new_user_id'',e.metadata_json->''new_user_id'',');
 EXECUTE source;
END; $$;
REVOKE ALL ON FUNCTION dation_private.member_responsibility_compat(),dation_private.member_roles(uuid,uuid),dation_private.responsibility_eligible(uuid,uuid,text) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_team_foundation(uuid,uuid,text,integer,integer,boolean,text),public.platform_set_member_responsibilities(uuid,uuid,uuid,timestamptz,text[]),public.platform_workflow_responsibilities(uuid,uuid,uuid,text,text,timestamptz,uuid,uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_team_foundation(uuid,uuid,text,integer,integer,boolean,text),public.platform_set_member_responsibilities(uuid,uuid,uuid,timestamptz,text[]),public.platform_workflow_responsibilities(uuid,uuid,uuid,text,text,timestamptz,uuid,uuid) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
