-- Phase 6: workspace library, derived packs and recoverable, authorized deletion.
-- Additive; no historical uploader backfill and no movement of existing objects.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';
ALTER TABLE public.datasets ADD COLUMN uploaded_by_user_id uuid REFERENCES auth.users(id);
ALTER TABLE public.datasets ADD COLUMN deletion_requested_at timestamptz;
CREATE TABLE dation_private.dataset_deletions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES public.workspaces(id),
 dataset_id uuid NOT NULL UNIQUE, actor_user_id uuid NOT NULL REFERENCES auth.users(id),
 storage_bucket text NOT NULL, storage_path text NOT NULL,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN('pending','completed')),
 created_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz
);
CREATE INDEX dataset_deletions_workspace_pending ON dation_private.dataset_deletions(workspace_id) WHERE status='pending';
REVOKE ALL ON dation_private.dataset_deletions FROM PUBLIC,anon,authenticated,service_role;
CREATE TABLE dation_private.dataset_uploads (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES public.workspaces(id),
 dataset_id uuid NOT NULL UNIQUE,actor_user_id uuid NOT NULL REFERENCES auth.users(id),
 storage_bucket text NOT NULL,storage_path text NOT NULL,filename text NOT NULL,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN('pending','failed','discarding','stored','discarded')),
 created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX dataset_uploads_workspace_pending ON dation_private.dataset_uploads(workspace_id,created_at DESC) WHERE status IN('pending','failed','discarding');
REVOKE ALL ON dation_private.dataset_uploads FROM PUBLIC,anon,authenticated,service_role;

CREATE FUNCTION dation_private.data_actor(wid uuid,uid uuid,writing boolean DEFAULT false)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE role_name text;
BEGIN
 SELECT m.access_role INTO role_name FROM workspace_members m JOIN workspaces w ON w.id=m.workspace_id
 JOIN auth.users u ON u.id=m.user_id WHERE m.workspace_id=wid AND m.user_id=uid AND m.status='active'
 AND w.status='active' AND u.email_confirmed_at IS NOT NULL;
 IF NOT FOUND OR (writing AND role_name='viewer') THEN RAISE EXCEPTION 'Workspace access denied' USING ERRCODE='42501'; END IF;
 RETURN role_name;
END; $$;

CREATE FUNCTION dation_private.dataset_referenced(wid uuid,did uuid)
RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=public,pg_temp AS $$
DECLARE relation_name text; used boolean;
BEGIN
 -- Conservative: include JSON evidence and indirect/version references, even in
 -- archived cases and terminal runs. This rare destructive action may scan.
 FOR relation_name IN SELECT unnest(ARRAY['datasets','decision_cases','decision_runs','dispatch_run_jobs',
 'decision_case_reconciliations','decision_approval_events','decision_comparative_analyses',
 'decision_explanations','decision_messages','decision_chat_turns','decision_interpretation_sources']) LOOP
  EXECUTE format('SELECT EXISTS(SELECT 1 FROM public.%I t WHERE workspace_id=$1 %s AND jsonb_path_exists(to_jsonb(t),''$.** ? (@ == $id)'',jsonb_build_object(''id'',$2::text)))',
   relation_name,CASE WHEN relation_name='datasets' THEN 'AND id<>$2' ELSE '' END) INTO used USING wid,did;
  IF used THEN RETURN true; END IF;
 END LOOP;
 RETURN false;
END; $$;

CREATE FUNCTION dation_private.guard_dataset_deletion() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE pending record;
BEGIN
 -- Concurrent reference creation holds a shared workspace lock. Preparing or
 -- finishing deletion takes the exclusive lock before checking all evidence.
 PERFORM pg_advisory_xact_lock_shared(hashtextextended('dation-data:'||NEW.workspace_id::text,0));
 IF TG_TABLE_NAME='datasets' THEN
  IF TG_OP='UPDATE' AND NEW.uploaded_by_user_id IS DISTINCT FROM OLD.uploaded_by_user_id THEN
   RAISE EXCEPTION 'Uploader identity is immutable' USING ERRCODE='22023';
  END IF;
  IF TG_OP='INSERT' AND NEW.uploaded_by_user_id IS NOT NULL THEN
   PERFORM dation_private.data_actor(NEW.workspace_id,NEW.uploaded_by_user_id,true);
  END IF;
  IF TG_OP='INSERT' AND EXISTS(SELECT 1 FROM dation_private.dataset_uploads WHERE dataset_id=NEW.id AND status IN('discarding','discarded')) THEN
   RAISE EXCEPTION 'Upload was discarded' USING ERRCODE='22023'; END IF;
 END IF;
 FOR pending IN SELECT dataset_id FROM dation_private.dataset_deletions WHERE workspace_id=NEW.workspace_id AND status='pending' LOOP
  IF TG_TABLE_NAME='datasets' AND (to_jsonb(NEW)->>'id')=pending.dataset_id::text THEN CONTINUE; END IF;
  IF jsonb_path_exists(to_jsonb(NEW),'$.** ? (@ == $id)',jsonb_build_object('id',pending.dataset_id::text)) THEN
   RAISE EXCEPTION 'Dataset deletion is pending' USING ERRCODE='22023';
  END IF;
 END LOOP;
 RETURN NEW;
END; $$;
DO $$ DECLARE relation_name text; BEGIN
 FOR relation_name IN SELECT unnest(ARRAY['datasets','decision_cases','decision_runs','dispatch_run_jobs',
 'decision_case_reconciliations','decision_approval_events','decision_comparative_analyses',
 'decision_explanations','decision_messages','decision_chat_turns','decision_interpretation_sources']) LOOP
  EXECUTE format('CREATE TRIGGER data_hub_deletion_guard BEFORE INSERT OR UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION dation_private.guard_dataset_deletion()',relation_name);
 END LOOP;
END; $$;

CREATE FUNCTION dation_private.hub_dataset(d public.datasets) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT jsonb_build_object('id',d.id,'label',d.label,'original_filename',d.original_filename,
 'canonical_filename',d.canonical_filename,'dataset_type',d.dataset_type,'schema_version',d.schema_version,
 'row_count',d.row_count,'column_count',d.column_count,'size_bytes',d.size_bytes,'created_at',d.created_at,
 'archived_at',d.archived_at,'is_default',d.is_default,'parent_dataset_id',d.parent_dataset_id,
 'deletion_pending',d.deletion_requested_at IS NOT NULL,
 'validation',CASE WHEN d.profile_json->'valid'='true' THEN 'validated' WHEN d.profile_json->'valid'='false' THEN 'issues' ELSE 'unknown' END,
 'uploaded_by',CASE WHEN d.uploaded_by_user_id IS NULL THEN NULL ELSE
 (SELECT jsonb_build_object('id',p.id,'name',coalesce(nullif(trim(concat_ws(' ',p.first_name,p.last_name)),''),'Usuario del workspace'))
 FROM profiles p JOIN workspace_members m ON m.user_id=p.id WHERE p.id=d.uploaded_by_user_id AND m.workspace_id=d.workspace_id) END,
 'case_count',(SELECT count(*) FROM decision_cases c WHERE c.workspace_id=d.workspace_id AND (c.orders_dataset_id=d.id OR c.fleet_dataset_id=d.id)),
 'run_count',(SELECT count(*) FROM decision_runs r WHERE r.workspace_id=d.workspace_id AND (r.dataset_id=d.id OR r.orders_dataset_id=d.id OR r.fleet_dataset_id=d.id)))
$$;

CREATE FUNCTION public.platform_data_hub(target_workspace_id uuid,actor_user_id uuid,
 resource text DEFAULT 'datasets',filter_name text DEFAULT 'all',search_text text DEFAULT '',
 target_dataset_id uuid DEFAULT NULL,orders_id uuid DEFAULT NULL,fleet_id uuid DEFAULT NULL,
 page_limit integer DEFAULT 25,page_offset integer DEFAULT 0)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE answer jsonb; target datasets; role_name text; used boolean;
BEGIN
 role_name=dation_private.data_actor(target_workspace_id,actor_user_id);
 IF resource NOT IN('datasets','dataset','packs','pack') OR filter_name NOT IN('all','orders','fleet','validated','issues','archived')
 OR page_limit NOT BETWEEN 1 AND 50 OR page_offset NOT BETWEEN 0 AND 1000000 OR length(search_text)>120 THEN
 RAISE EXCEPTION 'Invalid library query' USING ERRCODE='22023'; END IF;
 IF resource IN('dataset','pack') THEN
  IF resource='dataset' THEN
   SELECT * INTO target FROM datasets WHERE workspace_id=target_workspace_id AND id=target_dataset_id;
   IF NOT FOUND THEN RAISE EXCEPTION 'Dataset not found' USING ERRCODE='P0002'; END IF;
   used=dation_private.dataset_referenced(target_workspace_id,target.id);
   SELECT jsonb_build_object('dataset',dation_private.hub_dataset(target),
    'validation_report',coalesce(target.profile_json-'preview','{}'),
    'used_in',coalesce((SELECT jsonb_agg(to_jsonb(c)) FROM (SELECT id,status,created_at FROM decision_cases
     WHERE workspace_id=target_workspace_id AND (orders_dataset_id=target.id OR fleet_dataset_id=target.id)
     ORDER BY created_at DESC,id DESC LIMIT page_limit OFFSET page_offset) c),'[]'),
    'can_archive',role_name<>'viewer' AND target.dataset_type IN('orders','fleet') AND NOT target.is_default AND target.deletion_requested_at IS NULL,
    'can_delete',role_name<>'viewer' AND target.archived_at IS NOT NULL AND NOT target.is_default AND NOT used,
    'referenced',used) INTO answer;
   RETURN answer;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM decision_cases WHERE workspace_id=target_workspace_id AND orders_dataset_id=orders_id AND fleet_dataset_id=fleet_id) THEN
   RAISE EXCEPTION 'Data Pack not found' USING ERRCODE='P0002'; END IF;
 END IF;
 IF resource='datasets' THEN
  WITH matched AS (SELECT d.* FROM datasets d WHERE d.workspace_id=target_workspace_id
   AND CASE WHEN filter_name='archived' THEN d.archived_at IS NOT NULL ELSE d.archived_at IS NULL END
   AND (filter_name NOT IN('orders','fleet') OR d.dataset_type=filter_name)
   AND (filter_name<>'validated' OR d.profile_json->'valid'='true')
   AND (filter_name<>'issues' OR d.profile_json->'valid'='false')
   AND (search_text='' OR strpos(lower(concat_ws(' ',d.original_filename,d.canonical_filename,d.label)),lower(search_text))>0)),
  page AS (SELECT * FROM matched ORDER BY created_at DESC,id DESC LIMIT page_limit OFFSET page_offset)
  SELECT jsonb_build_object('items',coalesce((SELECT jsonb_agg(dation_private.hub_dataset(p::public.datasets) ORDER BY p.created_at DESC,p.id DESC) FROM page p),'[]'),
   'total',(SELECT count(*) FROM matched),'limit',page_limit,'offset',page_offset,
   'incomplete_uploads',coalesce((SELECT jsonb_agg(to_jsonb(u)) FROM
    (SELECT id,filename,created_at,status FROM dation_private.dataset_uploads u
     WHERE u.workspace_id=target_workspace_id AND (u.status IN('failed','discarding') OR (u.status='pending' AND u.created_at<now()-interval '15 minutes'))
     AND NOT EXISTS(SELECT 1 FROM datasets d WHERE d.id=u.dataset_id AND d.workspace_id=target_workspace_id)
     ORDER BY created_at DESC,id DESC LIMIT 10) u),'[]')) INTO answer;
  RETURN answer;
 END IF;
 -- A Data Pack is the immutable Orders/Fleet pair already used by cases.
 WITH pairs AS (SELECT c.orders_dataset_id,c.fleet_dataset_id,min(c.created_at) created_at,count(*) case_count
  FROM decision_cases c WHERE c.workspace_id=target_workspace_id GROUP BY c.orders_dataset_id,c.fleet_dataset_id),
 matched AS (SELECT p.*,dation_private.hub_dataset(o) orders,dation_private.hub_dataset(f) fleet,
  coalesce(nullif(o.label,''),o.canonical_filename,o.original_filename)||' + '||coalesce(nullif(f.label,''),f.canonical_filename,f.original_filename) label,
  o.profile_json->'valid'='true' AND f.profile_json->'valid'='true' validated
  FROM pairs p JOIN datasets o ON o.id=p.orders_dataset_id AND o.workspace_id=target_workspace_id
  JOIN datasets f ON f.id=p.fleet_dataset_id AND f.workspace_id=target_workspace_id
  WHERE (resource<>'pack' OR (p.orders_dataset_id=orders_id AND p.fleet_dataset_id=fleet_id))
  AND (search_text='' OR strpos(lower(concat_ws(' ',o.label,o.original_filename,o.canonical_filename,f.label,f.original_filename,f.canonical_filename)),lower(search_text))>0)),
 page AS (SELECT * FROM matched ORDER BY created_at DESC,orders_dataset_id,fleet_dataset_id
  LIMIT CASE WHEN resource='pack' THEN 1 ELSE page_limit END OFFSET CASE WHEN resource='pack' THEN 0 ELSE page_offset END)
 SELECT jsonb_build_object('items',coalesce((SELECT jsonb_agg(to_jsonb(p) ORDER BY p.created_at DESC,p.orders_dataset_id,p.fleet_dataset_id) FROM page p),'[]'),
  'total',(SELECT count(*) FROM matched),'limit',page_limit,'offset',page_offset) INTO answer;
 IF resource='pack' THEN
  RETURN jsonb_build_object('pack',answer->'items'->0,'used_in',coalesce((SELECT jsonb_agg(to_jsonb(c)) FROM
   (SELECT id,status,created_at FROM decision_cases WHERE workspace_id=target_workspace_id AND orders_dataset_id=orders_id AND fleet_dataset_id=fleet_id
    ORDER BY created_at DESC,id DESC LIMIT page_limit OFFSET page_offset) c),'[]'));
 END IF;
 RETURN answer;
END; $$;

CREATE FUNCTION public.platform_dataset_upload(target_workspace_id uuid,actor_user_id uuid,operation text,
 target_dataset_id uuid DEFAULT NULL,operation_id uuid DEFAULT NULL,object_bucket text DEFAULT NULL,
 object_path text DEFAULT NULL,filename text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE intent dation_private.dataset_uploads; stored datasets;
BEGIN
 PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true);
 IF operation NOT IN('prepare','stored','failed','discard','finish') THEN RAISE EXCEPTION 'Invalid upload operation' USING ERRCODE='22023'; END IF;
 IF operation<>'prepare' AND NOT pg_try_advisory_xact_lock(hashtextextended('dation-data:'||target_workspace_id::text,0)) THEN
  RAISE EXCEPTION 'Workspace data is busy; retry' USING ERRCODE='55006'; END IF;
 IF operation='prepare' THEN
  IF target_dataset_id IS NULL OR length(coalesce(filename,'')) NOT BETWEEN 1 AND 512 OR
   object_bucket IS NULL OR object_path IS NULL OR split_part(object_path,'/',1)<>target_workspace_id::text
   OR split_part(object_path,'/',2)<>target_dataset_id::text OR array_length(string_to_array(object_path,'/'),1)<>3
   OR split_part(object_path,'/',3) IN('','.','..') THEN RAISE EXCEPTION 'Invalid upload identity' USING ERRCODE='22023'; END IF;
  INSERT INTO dation_private.dataset_uploads(workspace_id,actor_user_id,dataset_id,storage_bucket,storage_path,filename)
   VALUES(target_workspace_id,actor_user_id,target_dataset_id,object_bucket,object_path,filename) RETURNING * INTO intent;
  RETURN jsonb_build_object('operation_id',intent.id);
 END IF;
 SELECT * INTO intent FROM dation_private.dataset_uploads WHERE id=operation_id AND workspace_id=target_workspace_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Upload not found' USING ERRCODE='P0002'; END IF;
 SELECT * INTO stored FROM datasets WHERE id=intent.dataset_id AND workspace_id=target_workspace_id;
 IF FOUND THEN
  IF stored.storage_bucket<>intent.storage_bucket OR stored.storage_path<>intent.storage_path THEN RAISE EXCEPTION 'Upload identity mismatch' USING ERRCODE='42501'; END IF;
  UPDATE dation_private.dataset_uploads SET status='stored',updated_at=clock_timestamp() WHERE id=intent.id;
  RETURN jsonb_build_object('cleared',true,'stored',true);
 END IF;
 IF intent.status IN('stored','discarded') THEN RETURN jsonb_build_object('cleared',true); END IF;
 IF operation='stored' THEN RAISE EXCEPTION 'Stored dataset not found' USING ERRCODE='P0002'; END IF;
 IF operation='failed' THEN
  IF intent.status='pending' THEN UPDATE dation_private.dataset_uploads SET status='failed',updated_at=clock_timestamp() WHERE id=intent.id; END IF;
  RETURN jsonb_build_object('pending',true);
 END IF;
 IF operation='finish' THEN
  UPDATE dation_private.dataset_uploads SET status='discarded',updated_at=clock_timestamp() WHERE id=intent.id;
  RETURN jsonb_build_object('cleared',true);
 END IF;
 IF intent.status='pending' AND intent.created_at>now()-interval '15 minutes' THEN
  RAISE EXCEPTION 'Upload is still active' USING ERRCODE='55006'; END IF;
 UPDATE dation_private.dataset_uploads SET status='discarding',updated_at=clock_timestamp() WHERE id=intent.id;
 RETURN jsonb_build_object('cleared',false,'operation_id',intent.id,'dataset_id',intent.dataset_id,
  'storage_bucket',intent.storage_bucket,'storage_path',intent.storage_path);
END; $$;

CREATE FUNCTION public.platform_dataset_delete(target_workspace_id uuid,actor_user_id uuid,target_dataset_id uuid,
 operation text DEFAULT 'prepare',operation_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE target datasets; intent dation_private.dataset_deletions;
BEGIN
 PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true);
 IF operation NOT IN('prepare','finish') THEN RAISE EXCEPTION 'Invalid delete operation' USING ERRCODE='22023'; END IF;
 IF NOT pg_try_advisory_xact_lock(hashtextextended('dation-data:'||target_workspace_id::text,0)) THEN
  RAISE EXCEPTION 'Workspace data is busy; retry' USING ERRCODE='55006'; END IF;
 SELECT * INTO intent FROM dation_private.dataset_deletions WHERE dataset_id=target_dataset_id AND workspace_id=target_workspace_id FOR UPDATE;
 IF FOUND AND intent.status='completed' THEN RETURN jsonb_build_object('deleted',true); END IF;
 SELECT * INTO target FROM datasets WHERE id=target_dataset_id AND workspace_id=target_workspace_id FOR UPDATE NOWAIT;
 IF NOT FOUND THEN RAISE EXCEPTION 'Dataset not found' USING ERRCODE='P0002'; END IF;
 IF target.archived_at IS NULL OR target.is_default OR dation_private.dataset_referenced(target_workspace_id,target_dataset_id) THEN
  RAISE EXCEPTION 'Archive first; referenced datasets must be retained' USING ERRCODE='22023'; END IF;
 IF operation='prepare' THEN
  IF intent.id IS NULL THEN
   INSERT INTO dation_private.dataset_deletions(workspace_id,dataset_id,actor_user_id,storage_bucket,storage_path)
    VALUES(target_workspace_id,target_dataset_id,actor_user_id,target.storage_bucket,target.storage_path) RETURNING * INTO intent;
   UPDATE datasets SET deletion_requested_at=clock_timestamp() WHERE id=target_dataset_id AND workspace_id=target_workspace_id;
  END IF;
  RETURN jsonb_build_object('deleted',false,'operation_id',intent.id,'storage_bucket',intent.storage_bucket,'storage_path',intent.storage_path);
 END IF;
 IF intent.id IS NULL OR operation_id IS DISTINCT FROM intent.id OR target.deletion_requested_at IS NULL THEN
  RAISE EXCEPTION 'Prepare deletion before finishing' USING ERRCODE='42501'; END IF;
 DELETE FROM datasets WHERE id=target_dataset_id AND workspace_id=target_workspace_id;
 UPDATE dation_private.dataset_deletions SET status='completed',completed_at=clock_timestamp() WHERE id=intent.id;
 RETURN jsonb_build_object('deleted',true);
EXCEPTION WHEN lock_not_available THEN
 RAISE EXCEPTION 'Dataset is busy; retry' USING ERRCODE='55006';
END; $$;

REVOKE ALL ON FUNCTION public.platform_data_hub(uuid,uuid,text,text,text,uuid,uuid,uuid,integer,integer) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.platform_dataset_delete(uuid,uuid,uuid,text,uuid) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.platform_dataset_upload(uuid,uuid,text,uuid,uuid,text,text,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_data_hub(uuid,uuid,text,text,text,uuid,uuid,uuid,integer,integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.platform_dataset_delete(uuid,uuid,uuid,text,uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.platform_dataset_upload(uuid,uuid,text,uuid,uuid,text,text,text) TO service_role;
REVOKE ALL ON FUNCTION dation_private.data_actor(uuid,uuid,boolean),
 dation_private.dataset_referenced(uuid,uuid),dation_private.guard_dataset_deletion(),
 dation_private.hub_dataset(public.datasets) FROM PUBLIC,anon,authenticated,service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
