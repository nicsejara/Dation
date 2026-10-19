-- Phase 10: append-only activity from committed product actions; no historical backfill.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='60s';
ALTER TABLE public.audit_events ADD COLUMN object_type text, ADD COLUMN object_id uuid,
 ADD COLUMN decision_case_id uuid, ADD COLUMN node_id text, ADD COLUMN event_key text;
CREATE INDEX audit_events_case_time_idx ON public.audit_events(workspace_id,decision_case_id,created_at DESC,id DESC);
CREATE INDEX audit_events_legacy_case_time_idx ON public.audit_events(workspace_id,(metadata_json->>'case_id'),created_at DESC,id DESC);
CREATE UNIQUE INDEX audit_events_event_key_idx ON public.audit_events(workspace_id,event_key) WHERE event_key IS NOT NULL;
REVOKE UPDATE,DELETE,TRUNCATE ON public.audit_events FROM service_role;

-- Only trusted service requests can mutate business tables. These headers are
-- overwritten by the BFF; tenant/client headers are never forwarded as authority.
CREATE FUNCTION dation_private.activity_actor(wid uuid) RETURNS uuid
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE headers jsonb=coalesce(nullif(current_setting('request.headers',true),''),'{}')::jsonb; uid uuid;
BEGIN
 IF headers->>'x-dation-workspace-id' IS NOT NULL AND headers->>'x-dation-workspace-id'<>wid::text THEN RAISE EXCEPTION 'Activity workspace mismatch' USING ERRCODE='42501'; END IF;
 uid=coalesce(nullif(current_setting('dation.actor_user_id',true),''),nullif(headers->>'x-dation-actor-id',''))::uuid;
 IF uid IS NOT NULL THEN PERFORM dation_private.data_actor(wid,uid,true); END IF;
 RETURN uid;
END; $$;
CREATE FUNCTION dation_private.activity_kind(kind text,meta jsonb) RETURNS text
LANGUAGE sql IMMUTABLE SET search_path=public,pg_temp AS $$
 SELECT CASE kind WHEN 'team.invited' THEN 'member.invited' WHEN 'team.invitation_accepted' THEN 'member.joined'
 WHEN 'team.invitation_revoked' THEN 'member.invitation_revoked' WHEN 'team.member_updated' THEN
 CASE WHEN meta->'after'->>'status'='disabled' AND meta->'before'->>'status' IS DISTINCT FROM 'disabled' THEN 'member.disabled'
 WHEN meta->'after'->>'status'='active' AND meta->'before'->>'status'='disabled' THEN 'member.enabled'
 WHEN meta->'after'->>'access_role' IS DISTINCT FROM meta->'before'->>'access_role' THEN 'member.role_changed'
 ELSE 'member.updated' END ELSE kind END
$$;
CREATE FUNCTION dation_private.activity_enrich() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE kind text=dation_private.activity_kind(NEW.event_type,NEW.metadata_json); candidate text;
BEGIN
 candidate=NEW.metadata_json->>'case_id';
 IF NEW.decision_case_id IS NULL AND candidate ~* '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$' THEN NEW.decision_case_id=candidate::uuid; END IF;
 IF NEW.decision_case_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM decision_cases WHERE id=NEW.decision_case_id AND workspace_id=NEW.workspace_id) THEN RAISE EXCEPTION 'Activity case mismatch' USING ERRCODE='42501'; END IF;
 NEW.node_id=coalesce(NEW.node_id,NEW.metadata_json->>'node_id');
 IF NEW.object_type IS NULL THEN
  NEW.object_type=CASE WHEN kind LIKE 'workspace.%' THEN 'workspace' WHEN kind IN('member.invited','member.invitation_revoked') THEN 'invitation' WHEN kind LIKE 'member.%' THEN 'member' WHEN kind='decision.assigned' THEN 'decision_case' WHEN kind='decision.approved' THEN 'run' ELSE NULL END;
  candidate=coalesce(NEW.metadata_json->>'run_id',NEW.metadata_json->>'user_id',NEW.metadata_json->>'invitation_id',NEW.decision_case_id::text);
  IF NEW.object_type='workspace' THEN NEW.object_id=NEW.workspace_id;
  ELSIF kind='member.joined' THEN NEW.object_id=NEW.actor_user_id;
  ELSIF candidate ~* '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$' THEN NEW.object_id=candidate::uuid; END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER activity_enrich BEFORE INSERT ON public.audit_events FOR EACH ROW EXECUTE FUNCTION dation_private.activity_enrich();

CREATE FUNCTION dation_private.activity_capture() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE row_data jsonb=CASE WHEN TG_OP='DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END;
 wid uuid=(row_data->>'workspace_id')::uuid; uid uuid; kind text; object_kind text; cid uuid; nid text; meta jsonb='{}';
BEGIN
 uid=dation_private.activity_actor(wid);
 IF TG_TABLE_NAME='datasets' THEN
  object_kind='dataset';
  IF TG_OP='INSERT' THEN
   uid=coalesce(uid,(row_data->>'uploaded_by_user_id')::uuid); kind='dataset.uploaded';
  ELSIF TG_OP='DELETE' THEN kind='dataset.deleted';
  ELSIF OLD.archived_at IS NULL AND NEW.archived_at IS NOT NULL THEN kind='dataset.archived';
  ELSIF OLD.archived_at IS NOT NULL AND NEW.archived_at IS NULL THEN kind='dataset.restored';
  END IF;
  meta=jsonb_build_object('dataset_type',row_data->>'dataset_type','row_count',row_data->'row_count');
  IF kind IS NOT NULL THEN INSERT INTO audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,metadata_json) VALUES(wid,uid,kind,object_kind,(row_data->>'id')::uuid,meta); END IF;
  IF TG_OP<>'DELETE' AND row_data->'profile_json'->'valid' IN('true'::jsonb,'false'::jsonb) AND
   (TG_OP='INSERT' OR OLD.profile_json IS DISTINCT FROM NEW.profile_json) THEN
   INSERT INTO audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,metadata_json)
   VALUES(wid,uid,'dataset.validated','dataset',(row_data->>'id')::uuid,meta||jsonb_build_object('valid',row_data->'profile_json'->'valid'));
  END IF;
 ELSIF TG_TABLE_NAME='decision_cases' THEN
  object_kind='decision_case';cid=(row_data->>'id')::uuid;
  IF TG_OP='INSERT' THEN uid=coalesce(uid,(row_data->>'created_by_user_id')::uuid);kind='decision_case.created';
  ELSIF OLD.status<>'archived' AND NEW.status='archived' THEN kind='decision_case.archived';
  ELSIF OLD.status='archived' AND NEW.status<>'archived' THEN kind='decision_case.restored';
  ELSIF NEW.label IS DISTINCT FROM OLD.label THEN kind='decision_case.renamed'; END IF;
 ELSE
  object_kind='run';cid=(row_data->>'decision_case_id')::uuid;nid=row_data->>'node_id';meta=jsonb_build_object('source','system');
  IF TG_OP='INSERT' THEN
   kind=CASE NEW.status WHEN 'queued' THEN 'run.queued' WHEN 'running' THEN 'run.started' WHEN 'completed' THEN 'run.completed' WHEN 'error' THEN 'run.failed' ELSE NULL END;
   IF NEW.status='queued' THEN uid=coalesce(uid,(row_data->>'created_by_user_id')::uuid);meta='{}';ELSIF uid IS NOT NULL THEN meta='{}'; END IF;
  ELSIF NEW.status IS DISTINCT FROM OLD.status THEN
   kind=CASE NEW.status WHEN 'running' THEN 'run.started' WHEN 'completed' THEN 'run.completed' WHEN 'error' THEN 'run.failed' ELSE NULL END;
   -- Workers have no actor. A real user cancellation keeps its verified actor.
   IF uid IS NOT NULL THEN meta='{}'; END IF;
  END IF;
 END IF;
 IF TG_TABLE_NAME<>'datasets' AND kind IS NOT NULL THEN
  INSERT INTO audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,decision_case_id,node_id,metadata_json)
  VALUES(wid,uid,kind,object_kind,(row_data->>'id')::uuid,cid,nid,meta);
  IF TG_TABLE_NAME='decision_runs' THEN
  IF kind='run.completed' AND nid IN('logistics_assignment','logistics_scheduling') AND NEW.approved_at IS NULL AND EXISTS(SELECT 1 FROM decision_cases WHERE id=cid AND workspace_id=wid AND status<>'archived') AND
   (nid='logistics_assignment' OR EXISTS(SELECT 1 FROM decision_runs WHERE id=NEW.upstream_run_id AND workspace_id=wid AND decision_case_id=cid AND node_id='logistics_assignment' AND approved_at IS NOT NULL AND superseded_at IS NULL)) THEN
   INSERT INTO audit_events(workspace_id,event_type,object_type,object_id,decision_case_id,node_id,metadata_json)
   VALUES(wid,'decision.submitted','run',NEW.id,cid,nid,jsonb_build_object('source','system','automatic',true));
  END IF;
 END IF;
 END IF;
 RETURN NULL;
END; $$;
CREATE TRIGGER activity_dataset AFTER INSERT OR UPDATE OR DELETE ON public.datasets FOR EACH ROW EXECUTE FUNCTION dation_private.activity_capture();
CREATE TRIGGER activity_case AFTER INSERT OR UPDATE ON public.decision_cases FOR EACH ROW EXECUTE FUNCTION dation_private.activity_capture();
CREATE TRIGGER activity_run AFTER INSERT OR UPDATE ON public.decision_runs FOR EACH ROW EXECUTE FUNCTION dation_private.activity_capture();

CREATE FUNCTION public.platform_activity(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid DEFAULT NULL,
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
  'case_id',e.cid,'node_id',coalesce(e.node_id,e.metadata_json->>'node_id'),'created_at',e.created_at,
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

CREATE FUNCTION public.platform_record_export(target_workspace_id uuid,actor_user_id uuid,target_run_id uuid,
 export_format text,operation_id uuid,content_sha256 text,content_bytes integer)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE r decision_runs; previous audit_events; key text;
BEGIN
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
 IF NOT EXISTS(SELECT 1 FROM workspace_ddas WHERE workspace_id=target_workspace_id AND dda_id='logistics' AND status='enabled') THEN RAISE EXCEPTION 'DDA not enabled' USING ERRCODE='42501'; END IF;
 SELECT * INTO r FROM decision_runs WHERE id=target_run_id AND workspace_id=target_workspace_id AND status='completed';
 IF NOT FOUND THEN RAISE EXCEPTION 'Exportable run not found' USING ERRCODE='P0002'; END IF;
 IF export_format IS NULL OR export_format NOT IN('csv','json') OR operation_id IS NULL OR content_sha256 IS NULL OR content_sha256 !~ '^[a-f0-9]{64}$' OR content_bytes IS NULL OR content_bytes<1 THEN RAISE EXCEPTION 'Invalid export' USING ERRCODE='22023'; END IF;
 key='export:'||actor_user_id::text||':'||operation_id::text;
 INSERT INTO audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,decision_case_id,node_id,event_key,metadata_json)
 VALUES(target_workspace_id,actor_user_id,'export.generated','run',r.id,r.decision_case_id,r.node_id,key,
  jsonb_build_object('format',export_format,'bytes',content_bytes,'sha256',content_sha256)) ON CONFLICT(workspace_id,event_key) WHERE event_key IS NOT NULL DO NOTHING;
 SELECT * INTO previous FROM audit_events WHERE workspace_id=target_workspace_id AND event_key=key;
 IF previous.object_id<>r.id OR previous.metadata_json->>'format'<>export_format OR previous.metadata_json->>'sha256'<>content_sha256 THEN RAISE EXCEPTION 'Export request changed' USING ERRCODE='55006'; END IF;
 RETURN jsonb_build_object('id',previous.id);
END; $$;
REVOKE ALL ON FUNCTION dation_private.activity_actor(uuid),dation_private.activity_kind(text,jsonb),dation_private.activity_enrich(),dation_private.activity_capture() FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_activity(uuid,uuid,uuid,integer,timestamptz,uuid),public.platform_record_export(uuid,uuid,uuid,text,uuid,text,integer) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_activity(uuid,uuid,uuid,integer,timestamptz,uuid),public.platform_record_export(uuid,uuid,uuid,text,uuid,text,integer) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
