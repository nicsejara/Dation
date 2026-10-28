-- T4: exact input candidates, private object provenance and complete Pack publication.
-- No graph resolver, execution, approval mutation or production Storage configuration.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';
ALTER TABLE dation_private.platform_release ADD COLUMN ultimate_data_pack_enabled boolean NOT NULL DEFAULT false;

CREATE TABLE dation_private.ultimate_input_objects (
 workspace_id uuid NOT NULL, dataset_id uuid NOT NULL, model_version_id uuid NOT NULL,
 normalized_bucket text NOT NULL CHECK(normalized_bucket ~ '^[a-z0-9][a-z0-9-]{0,62}$'),
 normalized_path text NOT NULL CHECK(normalized_path ~ ('^'||workspace_id::text||'/normalized/'||dataset_id::text||'/[0-9a-f]{64}[.]json$')),
 normalized_size bigint NOT NULL CHECK(normalized_size BETWEEN 1 AND 10485760),
 summary jsonb NOT NULL CHECK(jsonb_typeof(summary)='object' AND octet_length(summary::text)<=65536),
 created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(workspace_id,dataset_id),
 FOREIGN KEY(workspace_id,dataset_id) REFERENCES public.datasets(workspace_id,id) ON DELETE RESTRICT,
 FOREIGN KEY(workspace_id,model_version_id) REFERENCES public.logistics_model_versions(workspace_id,id) ON DELETE RESTRICT
);
CREATE INDEX ultimate_input_objects_model ON dation_private.ultimate_input_objects(workspace_id,model_version_id);
CREATE TRIGGER t4_input_objects_immutable BEFORE UPDATE OR DELETE ON dation_private.ultimate_input_objects FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_immutable();

CREATE TABLE dation_private.ultimate_input_uploads (
 id uuid PRIMARY KEY, workspace_id uuid NOT NULL, case_id uuid NOT NULL, model_version_id uuid NOT NULL,
 entity text NOT NULL CHECK(entity IN('transport_demand','transport_resources')),
 reserved_dataset_id uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(), dataset_id uuid,
 actor_user_id uuid NOT NULL, intent_hash text NOT NULL CHECK(intent_hash ~ '^[0-9a-f]{64}$'),
 contract_id text NOT NULL CHECK(length(contract_id) BETWEEN 1 AND 128), contract_hash text NOT NULL CHECK(contract_hash ~ '^[0-9a-f]{64}$'),
 normalizer_version text NOT NULL CHECK(length(normalizer_version) BETWEEN 1 AND 128),
 raw_sha256 text NOT NULL CHECK(raw_sha256 ~ '^[0-9a-f]{64}$'), canonical_sha256 text NOT NULL CHECK(canonical_sha256 ~ '^[0-9a-f]{64}$'),
 raw_size bigint NOT NULL CHECK(raw_size BETWEEN 1 AND 10485760), normalized_size bigint NOT NULL CHECK(normalized_size BETWEEN 1 AND 10485760),
 record_count bigint NOT NULL CHECK(record_count BETWEEN 1 AND 10000), column_count integer NOT NULL CHECK(column_count BETWEEN 1 AND 50),
 filename text NOT NULL CHECK(length(filename) BETWEEN 1 AND 120), storage_bucket text NOT NULL CHECK(storage_bucket ~ '^[a-z0-9][a-z0-9-]{0,62}$'),
 profile jsonb NOT NULL CHECK(jsonb_typeof(profile)='object' AND octet_length(profile::text)<=262144),
 summary jsonb NOT NULL CHECK(jsonb_typeof(summary)='object' AND octet_length(summary::text)<=65536),
 status text NOT NULL DEFAULT 'PREPARED' CHECK(status IN('PREPARED','READY','DISCARDING','DISCARDED')),
 cleanup_pending boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(workspace_id,case_id,id),
 FOREIGN KEY(workspace_id,case_id,model_version_id) REFERENCES public.decision_cases(workspace_id,id,logistics_model_version_id) ON DELETE RESTRICT,
 FOREIGN KEY(workspace_id,dataset_id) REFERENCES public.datasets(workspace_id,id) ON DELETE RESTRICT,
 FOREIGN KEY(workspace_id,actor_user_id) REFERENCES public.workspace_members(workspace_id,user_id) ON DELETE RESTRICT,
 CHECK((status='READY')=(dataset_id IS NOT NULL) OR status IN('DISCARDING','DISCARDED'))
);
CREATE INDEX ultimate_input_uploads_case ON dation_private.ultimate_input_uploads(workspace_id,case_id,created_at DESC,id);
CREATE INDEX ultimate_input_uploads_dataset ON dation_private.ultimate_input_uploads(workspace_id,dataset_id);

CREATE TABLE dation_private.ultimate_pack_publications (
 id uuid PRIMARY KEY, workspace_id uuid NOT NULL, case_id uuid NOT NULL, pack_version_id uuid NOT NULL,
 intent_hash text NOT NULL CHECK(intent_hash ~ '^[0-9a-f]{64}$'), actor_user_id uuid NOT NULL,
 previous_version_id uuid NOT NULL, changes jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(workspace_id,case_id,pack_version_id) REFERENCES public.case_data_pack_versions(workspace_id,case_id,id) ON DELETE RESTRICT,
 FOREIGN KEY(workspace_id,case_id,previous_version_id) REFERENCES public.case_data_pack_versions(workspace_id,case_id,id) ON DELETE RESTRICT,
 FOREIGN KEY(workspace_id,actor_user_id) REFERENCES public.workspace_members(workspace_id,user_id) ON DELETE RESTRICT
);
CREATE INDEX ultimate_pack_publications_case ON dation_private.ultimate_pack_publications(workspace_id,case_id,created_at DESC);
CREATE TRIGGER t4_publications_immutable BEFORE UPDATE OR DELETE ON dation_private.ultimate_pack_publications FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_immutable();

CREATE FUNCTION dation_private.t4_entry(wid uuid,slot text,did uuid) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('slot_key',slot,'dataset_id',d.id,'contract_id',d.data_contract_id,'contract_hash',d.data_contract_hash,
  'raw_sha256',d.sha256,'canonical_sha256',d.canonical_sha256,'normalizer_version',d.normalizer_version,
  'normalized_bucket',o.normalized_bucket,'normalized_path',o.normalized_path,'normalized_size',o.normalized_size,
  'record_count',d.row_count,'storage_bucket',d.storage_bucket,'storage_path',d.storage_path,'raw_size',d.size_bytes,'summary',o.summary)
 FROM public.datasets d JOIN dation_private.ultimate_input_objects o ON o.workspace_id=d.workspace_id AND o.dataset_id=d.id
 WHERE d.workspace_id=wid AND d.id=did AND d.dataset_type=slot AND d.deletion_requested_at IS NULL;
$$;

CREATE FUNCTION dation_private.t4_upload(j dation_private.ultimate_input_uploads) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT to_jsonb(j)||jsonb_build_object('storage_path',j.workspace_id::text||'/'||j.reserved_dataset_id::text||'/input.csv',
  'normalized_path',j.workspace_id::text||'/normalized/'||j.reserved_dataset_id::text||'/'||j.canonical_sha256||'.json');
$$;

CREATE FUNCTION dation_private.t4_entries(wid uuid,cid uuid,selection jsonb,contracts jsonb) RETURNS jsonb
LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE item jsonb; did uuid; model uuid; entry jsonb; result jsonb='{}'; slot text;
BEGIN
 SELECT logistics_model_version_id INTO model FROM public.decision_cases WHERE workspace_id=wid AND id=cid;
 IF jsonb_typeof(selection) IS DISTINCT FROM 'array' OR jsonb_array_length(selection) NOT BETWEEN 1 AND 2
  OR (SELECT count(*)<>count(DISTINCT x->>'slot_key') FROM jsonb_array_elements(selection) x) THEN RAISE EXCEPTION 'Invalid slot selection' USING ERRCODE='22023'; END IF;
 SELECT coalesce(jsonb_object_agg(e.slot_key,dation_private.t4_entry(wid,e.slot_key,e.dataset_id)),'{}') INTO result
  FROM public.case_data_packs p JOIN public.case_data_pack_entries e ON e.workspace_id=p.workspace_id AND e.pack_version_id=p.current_version_id
  WHERE p.workspace_id=wid AND p.case_id=cid;
 FOR item IN SELECT x FROM jsonb_array_elements(selection) x LOOP
  slot=item->>'slot_key';
  IF coalesce(slot,'') NOT IN('transport_demand','transport_resources') OR num_nonnulls(item->>'upload_id',item->>'dataset_id')<>1 THEN RAISE EXCEPTION 'Invalid semantic slot' USING ERRCODE='22023'; END IF;
  IF item?'upload_id' THEN
   SELECT dataset_id INTO did FROM dation_private.ultimate_input_uploads WHERE workspace_id=wid AND case_id=cid AND id=(item->>'upload_id')::uuid AND entity=slot AND status='READY';
  ELSE did=(item->>'dataset_id')::uuid; END IF;
  entry=dation_private.t4_entry(wid,slot,did);
  IF entry IS NULL OR entry->>'contract_hash' IS DISTINCT FROM contracts->>slot
   OR NOT EXISTS(SELECT 1 FROM dation_private.ultimate_input_objects o JOIN public.datasets d ON d.workspace_id=o.workspace_id AND d.id=o.dataset_id
    WHERE o.workspace_id=wid AND o.dataset_id=did AND o.model_version_id=model AND d.archived_at IS NULL) THEN
   RAISE EXCEPTION 'Input is not compatible with this Model Version' USING ERRCODE='22023'; END IF;
  result=jsonb_set(result,ARRAY[slot],entry);
 END LOOP;
 IF EXISTS(SELECT 1 FROM jsonb_each(result) x WHERE x.value='null'::jsonb) THEN RAISE EXCEPTION 'Missing immutable input metadata' USING ERRCODE='22023'; END IF;
 RETURN (SELECT coalesce(jsonb_agg(value ORDER BY key),'[]') FROM jsonb_each(result));
END; $$;

CREATE FUNCTION public.platform_ultimate_data_pack(target_workspace_id uuid,actor_user_id uuid,operation text,arguments jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE role_name text; c public.decision_cases; p public.case_data_packs; v public.case_data_pack_versions;
 j dation_private.ultimate_input_uploads; pub dation_private.ultimate_pack_publications; d public.datasets;
 item jsonb; entries jsonb; did uuid; target uuid; published uuid; number integer; enabled boolean; old_entries jsonb; changes jsonb;
BEGIN
 role_name=dation_private.data_actor(target_workspace_id,actor_user_id);
 IF operation IS NULL OR operation NOT IN('state','history','upload_get','prepare','store','plan','publish','replay','compatible','dataset_get','dataset_archive','version_get','discard','cleanup','cleanup_finish')
  OR jsonb_typeof(arguments) IS DISTINCT FROM 'object' OR octet_length(arguments::text)>1048576 THEN RAISE EXCEPTION 'Invalid Pack operation' USING ERRCODE='22023'; END IF;
 IF operation IN('dataset_get','dataset_archive') THEN
  SELECT * INTO d FROM public.datasets WHERE workspace_id=target_workspace_id AND id=(arguments->>'dataset_id')::uuid AND deletion_requested_at IS NULL;
  IF NOT FOUND OR d.dataset_type NOT IN('transport_demand','transport_resources') THEN RAISE EXCEPTION 'Input not found' USING ERRCODE='P0002'; END IF;
  IF operation='dataset_archive' THEN
   PERFORM 1 FROM public.workspaces WHERE id=target_workspace_id FOR UPDATE;
   PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true);
   PERFORM set_config('dation.workspace_id',target_workspace_id::text,true);PERFORM set_config('dation.actor_user_id',actor_user_id::text,true);
   UPDATE public.datasets SET archived_at=CASE WHEN (arguments->>'archived')::boolean THEN clock_timestamp() ELSE NULL END WHERE workspace_id=target_workspace_id AND id=d.id;
   RETURN jsonb_build_object('archived',(arguments->>'archived')::boolean);
  END IF;
  RETURN jsonb_build_object('dataset',to_jsonb(d),'entry',dation_private.t4_entry(target_workspace_id,d.dataset_type,d.id));
 END IF;
 target=(arguments->>'case_id')::uuid;
 SELECT * INTO c FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=target AND workflow_version=2;
 IF NOT FOUND THEN RAISE EXCEPTION 'Ultimate Case not found' USING ERRCODE='P0002'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.workspace_ddas WHERE workspace_id=target_workspace_id AND dda_id='logistics' AND status='enabled') THEN RAISE EXCEPTION 'DDA denied' USING ERRCODE='42501'; END IF;
 SELECT * INTO p FROM public.case_data_packs WHERE workspace_id=target_workspace_id AND case_id=c.id;
 IF operation='replay' THEN
  PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true);
  SELECT * INTO pub FROM dation_private.ultimate_pack_publications WHERE id=(arguments->>'publication_id')::uuid;
  IF NOT FOUND THEN RETURN jsonb_build_object('replayed',false); END IF;
  IF pub.workspace_id<>target_workspace_id OR pub.case_id<>c.id THEN RAISE EXCEPTION 'Publication not found' USING ERRCODE='P0002'; END IF;
  IF pub.intent_hash IS DISTINCT FROM arguments->>'intent_hash' THEN RAISE EXCEPTION 'Publication intent changed' USING ERRCODE='55006'; END IF;
  RETURN jsonb_build_object('replayed',true,'publication',to_jsonb(pub),'version',(SELECT to_jsonb(x) FROM public.case_data_pack_versions x WHERE workspace_id=target_workspace_id AND id=pub.pack_version_id));
 END IF;
 IF operation IN('prepare','store','plan','publish','discard','cleanup','cleanup_finish') THEN
  PERFORM 1 FROM public.workspaces WHERE id=target_workspace_id FOR UPDATE;
  PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true);
  SELECT * INTO c FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=target FOR UPDATE;
  SELECT * INTO p FROM public.case_data_packs WHERE workspace_id=target_workspace_id AND case_id=target FOR UPDATE;
  IF NOT EXISTS(SELECT 1 FROM public.workspace_ddas WHERE workspace_id=target_workspace_id AND dda_id='logistics' AND status='enabled') THEN RAISE EXCEPTION 'DDA denied' USING ERRCODE='42501'; END IF;
  -- Resolve a committed publication before mutable revision/flag/archive checks.
  IF operation='publish' THEN
   SELECT * INTO pub FROM dation_private.ultimate_pack_publications WHERE id=(arguments->>'publication_id')::uuid;
   IF FOUND THEN
    IF pub.workspace_id<>target_workspace_id OR pub.case_id<>target THEN RAISE EXCEPTION 'Publication not found' USING ERRCODE='P0002'; END IF;
    IF pub.intent_hash IS DISTINCT FROM arguments->>'intent_hash' THEN RAISE EXCEPTION 'Publication intent changed' USING ERRCODE='55006'; END IF;
    RETURN jsonb_build_object('replayed',true,'publication',to_jsonb(pub),'version',(SELECT to_jsonb(x) FROM public.case_data_pack_versions x WHERE workspace_id=target_workspace_id AND id=pub.pack_version_id));
   END IF;
  END IF;
  SELECT ultimate_foundation_enabled AND ultimate_data_pack_enabled INTO enabled FROM dation_private.platform_release WHERE singleton;
  IF NOT enabled THEN RAISE EXCEPTION 'Ultimate input publication is closed' USING ERRCODE='P0002'; END IF;
  IF c.status='archived' THEN RAISE EXCEPTION 'Restore Case before editing inputs' USING ERRCODE='22023'; END IF;
  PERFORM set_config('dation.workspace_id',target_workspace_id::text,true);PERFORM set_config('dation.actor_user_id',actor_user_id::text,true);
 END IF;
 IF operation IN('state','history') THEN
  SELECT ultimate_foundation_enabled AND ultimate_data_pack_enabled INTO enabled FROM dation_private.platform_release WHERE singleton;
  RETURN jsonb_build_object('case',to_jsonb(c),'pack',to_jsonb(p),'model_version',(SELECT to_jsonb(x) FROM public.logistics_model_versions x WHERE workspace_id=target_workspace_id AND id=c.logistics_model_version_id),
   'version',(SELECT to_jsonb(x) FROM public.case_data_pack_versions x WHERE workspace_id=target_workspace_id AND id=p.current_version_id),
   'latest_version',(SELECT max(version) FROM public.case_data_pack_versions WHERE workspace_id=target_workspace_id AND pack_id=p.id),
   'entries',coalesce((SELECT jsonb_agg(dation_private.t4_entry(target_workspace_id,e.slot_key,e.dataset_id) ORDER BY e.slot_key) FROM public.case_data_pack_entries e WHERE e.workspace_id=target_workspace_id AND e.pack_version_id=p.current_version_id),'[]'),
   'uploads',coalesce((SELECT jsonb_agg(dation_private.t4_upload(x) ORDER BY created_at DESC,id) FROM (SELECT * FROM dation_private.ultimate_input_uploads WHERE workspace_id=target_workspace_id AND case_id=target AND status<>'DISCARDED' ORDER BY created_at DESC,id LIMIT 20) x),'[]'),
   'history',coalesce((SELECT jsonb_agg(to_jsonb(x) ORDER BY version DESC) FROM (SELECT * FROM public.case_data_pack_versions WHERE workspace_id=target_workspace_id AND pack_id=p.id ORDER BY version DESC LIMIT 20 OFFSET greatest(0,least(coalesce((arguments->>'offset')::integer,0),1000000))) x),'[]'),
   'history_total',(SELECT count(*) FROM public.case_data_pack_versions WHERE workspace_id=target_workspace_id AND pack_id=p.id),
   'enabled',enabled,'can_edit',enabled AND role_name<>'viewer' AND c.status<>'archived','runtime_execution_available',false);
 END IF;
 IF operation='version_get' THEN
  SELECT * INTO v FROM public.case_data_pack_versions WHERE workspace_id=target_workspace_id AND case_id=target AND id=(arguments->>'version_id')::uuid;
  IF NOT FOUND THEN RAISE EXCEPTION 'Pack Version not found' USING ERRCODE='P0002'; END IF;
  RETURN jsonb_build_object('version',to_jsonb(v),'entries',coalesce((SELECT jsonb_agg(dation_private.t4_entry(target_workspace_id,e.slot_key,e.dataset_id) ORDER BY e.slot_key) FROM public.case_data_pack_entries e WHERE e.workspace_id=target_workspace_id AND e.pack_version_id=v.id),'[]'));
 END IF;
 IF operation='compatible' THEN
  IF coalesce(arguments->>'entity','') NOT IN('transport_demand','transport_resources') THEN RAISE EXCEPTION 'Invalid entity' USING ERRCODE='22023'; END IF;
  RETURN jsonb_build_object('items',coalesce((SELECT jsonb_agg(to_jsonb(x)) FROM (SELECT ds.id,ds.original_filename,ds.row_count,ds.created_at,ds.data_contract_hash FROM public.datasets ds JOIN dation_private.ultimate_input_objects o ON o.workspace_id=ds.workspace_id AND o.dataset_id=ds.id
   WHERE ds.workspace_id=target_workspace_id AND ds.dataset_type=arguments->>'entity' AND ds.data_contract_hash=arguments->>'contract_hash'
    AND o.model_version_id=c.logistics_model_version_id AND ds.archived_at IS NULL AND ds.deletion_requested_at IS NULL ORDER BY ds.created_at DESC,ds.id LIMIT 25 OFFSET greatest(0,least(coalesce((arguments->>'offset')::integer,0),1000000))) x),'[]'));
 END IF;
 IF operation='prepare' THEN
  SELECT * INTO j FROM dation_private.ultimate_input_uploads WHERE id=(arguments->>'upload_id')::uuid;
  IF FOUND THEN
   IF j.workspace_id<>target_workspace_id OR j.case_id<>target THEN RAISE EXCEPTION 'Upload not found' USING ERRCODE='P0002'; END IF;
   IF j.intent_hash IS DISTINCT FROM arguments->>'intent_hash' THEN RAISE EXCEPTION 'Upload intent changed' USING ERRCODE='55006'; END IF;
   RETURN dation_private.t4_upload(j);
  END IF;
  IF coalesce(arguments->>'entity','') NOT IN('transport_demand','transport_resources') OR arguments#>>'{profile,valid}' IS DISTINCT FROM 'true' THEN RAISE EXCEPTION 'Validated input required' USING ERRCODE='22023'; END IF;
  INSERT INTO dation_private.ultimate_input_uploads(id,workspace_id,case_id,model_version_id,entity,actor_user_id,intent_hash,contract_id,contract_hash,normalizer_version,raw_sha256,canonical_sha256,raw_size,normalized_size,record_count,column_count,filename,storage_bucket,profile,summary)
   VALUES((arguments->>'upload_id')::uuid,target_workspace_id,target,c.logistics_model_version_id,arguments->>'entity',actor_user_id,arguments->>'intent_hash',arguments->>'contract_id',arguments->>'contract_hash',arguments->>'normalizer_version',arguments->>'raw_sha256',arguments->>'canonical_sha256',(arguments->>'raw_size')::bigint,(arguments->>'normalized_size')::bigint,(arguments->>'record_count')::bigint,(arguments->>'column_count')::integer,arguments->>'filename',arguments->>'storage_bucket',arguments->'profile',arguments->'summary') RETURNING * INTO j;
  RETURN dation_private.t4_upload(j);
 END IF;
 IF operation IN('upload_get','store','discard','cleanup','cleanup_finish') THEN
  SELECT * INTO j FROM dation_private.ultimate_input_uploads WHERE workspace_id=target_workspace_id AND case_id=target AND id=(arguments->>'upload_id')::uuid FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Upload not found' USING ERRCODE='P0002'; END IF;
  IF operation='upload_get' THEN RETURN dation_private.t4_upload(j); END IF;
  IF operation='store' THEN
   IF j.status='READY' THEN RETURN dation_private.t4_upload(j); END IF;
   IF j.status<>'PREPARED' OR j.raw_sha256 IS DISTINCT FROM arguments->>'verified_raw_sha256' OR j.canonical_sha256 IS DISTINCT FROM arguments->>'verified_canonical_sha256' THEN RAISE EXCEPTION 'Upload is not complete or was discarded' USING ERRCODE='22023'; END IF;
   SELECT * INTO d FROM public.datasets WHERE workspace_id=target_workspace_id AND dataset_type=j.entity AND sha256=j.raw_sha256 AND data_contract_hash=j.contract_hash;
   IF FOUND THEN
    IF d.canonical_sha256<>j.canonical_sha256 OR d.normalizer_version<>j.normalizer_version OR d.archived_at IS NOT NULL OR d.deletion_requested_at IS NOT NULL
     OR NOT EXISTS(SELECT 1 FROM dation_private.ultimate_input_objects WHERE workspace_id=target_workspace_id AND dataset_id=d.id AND model_version_id=j.model_version_id) THEN RAISE EXCEPTION 'Stored interpretation unavailable' USING ERRCODE='22023'; END IF;
   ELSE
    INSERT INTO public.datasets(id,workspace_id,dataset_type,original_filename,canonical_filename,storage_bucket,storage_path,mime_type,size_bytes,sha256,status,row_count,column_count,schema_version,profile_json,uploaded_by_user_id,data_contract_id,data_contract_hash,normalizer_version,canonical_sha256)
     VALUES(j.reserved_dataset_id,target_workspace_id,j.entity,j.filename,j.entity||'.csv',j.storage_bucket,target_workspace_id::text||'/'||j.reserved_dataset_id::text||'/input.csv','text/csv',j.raw_size,j.raw_sha256,'uploaded',j.record_count,j.column_count,j.entity||'_v1',j.profile,j.actor_user_id,j.contract_id,j.contract_hash,j.normalizer_version,j.canonical_sha256) RETURNING * INTO d;
    INSERT INTO dation_private.ultimate_input_objects(workspace_id,dataset_id,model_version_id,normalized_bucket,normalized_path,normalized_size,summary)
     VALUES(target_workspace_id,d.id,j.model_version_id,j.storage_bucket,target_workspace_id::text||'/normalized/'||d.id::text||'/'||j.canonical_sha256||'.json',j.normalized_size,j.summary);
   END IF;
   UPDATE dation_private.ultimate_input_uploads SET dataset_id=d.id,status='READY',cleanup_pending=d.id<>reserved_dataset_id,updated_at=clock_timestamp() WHERE id=j.id RETURNING * INTO j;
   RETURN dation_private.t4_upload(j);
  END IF;
  IF operation='discard' THEN
   -- READY metadata is durable/reusable; discard the candidate link only.
   UPDATE dation_private.ultimate_input_uploads SET status='DISCARDED',cleanup_pending=(dataset_id IS NULL OR dataset_id<>reserved_dataset_id),updated_at=clock_timestamp() WHERE id=j.id RETURNING * INTO j;
  ELSIF operation='cleanup_finish' THEN
   UPDATE dation_private.ultimate_input_uploads SET cleanup_pending=false,updated_at=clock_timestamp() WHERE id=j.id RETURNING * INTO j;
  END IF;
  IF operation IN('discard','cleanup') AND j.cleanup_pending AND NOT EXISTS(SELECT 1 FROM public.datasets WHERE id=j.reserved_dataset_id) THEN
   RETURN dation_private.t4_upload(j)||jsonb_build_object('may_delete_reserved_objects',true);
  END IF;
  RETURN dation_private.t4_upload(j)||jsonb_build_object('may_delete_reserved_objects',false);
 END IF;
 entries=dation_private.t4_entries(target_workspace_id,target,arguments->'selection',arguments->'contracts');
 IF operation='plan' THEN RETURN jsonb_build_object('pack',to_jsonb(p),'entries',entries,'next_version',(SELECT max(version)+1 FROM public.case_data_pack_versions WHERE workspace_id=target_workspace_id AND pack_id=p.id)); END IF;
 IF p.revision IS DISTINCT FROM (arguments->>'expected_revision')::bigint OR p.current_version_id IS DISTINCT FROM (arguments->>'expected_current_version_id')::uuid THEN RAISE EXCEPTION 'Pack changed; candidate retained' USING ERRCODE='55006'; END IF;
 IF entries IS DISTINCT FROM arguments->'entries' OR coalesce(arguments->>'manifest_hash','') !~ '^[0-9a-f]{64}$' OR coalesce(arguments->>'contract_set_hash','') !~ '^[0-9a-f]{64}$' OR coalesce(arguments->>'intent_hash','') !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'Incomplete manifest' USING ERRCODE='22023'; END IF;
 SELECT coalesce(jsonb_object_agg(e.slot_key,jsonb_build_object('raw_sha256',e.raw_sha256,'canonical_sha256',e.canonical_sha256,'contract_hash',e.contract_hash)),'{}') INTO old_entries FROM public.case_data_pack_entries e WHERE e.workspace_id=target_workspace_id AND e.pack_version_id=p.current_version_id;
 SELECT coalesce(jsonb_agg(jsonb_build_object('slot_key',x->>'slot_key','previous',old_entries->(x->>'slot_key'),'current',jsonb_build_object('raw_sha256',x->>'raw_sha256','canonical_sha256',x->>'canonical_sha256','contract_hash',x->>'contract_hash')) ORDER BY x->>'slot_key'),'[]') INTO changes
  FROM jsonb_array_elements(entries) x WHERE old_entries->(x->>'slot_key') IS DISTINCT FROM jsonb_build_object('raw_sha256',x->>'raw_sha256','canonical_sha256',x->>'canonical_sha256','contract_hash',x->>'contract_hash');
 SELECT max(version)+1 INTO number FROM public.case_data_pack_versions WHERE workspace_id=target_workspace_id AND pack_id=p.id;
 published=(arguments->>'version_id')::uuid;
 INSERT INTO public.case_data_pack_versions(id,workspace_id,case_id,pack_id,version,manifest_hash,contract_set_hash,created_by) VALUES(published,target_workspace_id,target,p.id,number,arguments->>'manifest_hash',arguments->>'contract_set_hash',actor_user_id) RETURNING * INTO v;
 FOR item IN SELECT x FROM jsonb_array_elements(entries) x LOOP
  INSERT INTO public.case_data_pack_entries(pack_version_id,slot_key,workspace_id,case_id,dataset_id,contract_id,contract_hash,raw_sha256,canonical_sha256,normalizer_version,normalized_bucket,normalized_path,record_count)
   VALUES(v.id,item->>'slot_key',target_workspace_id,target,(item->>'dataset_id')::uuid,item->>'contract_id',item->>'contract_hash',item->>'raw_sha256',item->>'canonical_sha256',item->>'normalizer_version',item->>'normalized_bucket',item->>'normalized_path',(item->>'record_count')::bigint);
 END LOOP;
 INSERT INTO dation_private.ultimate_pack_publications(id,workspace_id,case_id,pack_version_id,intent_hash,actor_user_id,previous_version_id,changes)
  VALUES((arguments->>'publication_id')::uuid,target_workspace_id,target,v.id,arguments->>'intent_hash',actor_user_id,p.current_version_id,changes) RETURNING * INTO pub;
 UPDATE public.case_data_packs SET current_version_id=v.id,revision=revision+1 WHERE workspace_id=target_workspace_id AND id=p.id;
 UPDATE public.decision_cases SET updated_at=clock_timestamp(),last_activity_at=clock_timestamp() WHERE workspace_id=target_workspace_id AND id=target;
 INSERT INTO public.audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,decision_case_id,metadata_json) VALUES(target_workspace_id,actor_user_id,'case_data_pack.published','case_data_pack',p.id,target,jsonb_build_object('version_id',v.id,'version',v.version,'changes',changes));
 RETURN jsonb_build_object('replayed',false,'publication',to_jsonb(pub),'version',to_jsonb(v));
END; $$;

-- New normalized metadata is a durable consumer: old delete journals cannot remove
-- one of its two objects. Published Pack FKs continue to protect historical inputs.
DO $$ DECLARE source text; BEGIN
 source=pg_get_functiondef('dation_private.dataset_referenced(uuid,uuid)'::regprocedure);
 source=replace(source,'BEGIN'||chr(10),'BEGIN'||chr(10)||' IF EXISTS(SELECT 1 FROM dation_private.ultimate_input_objects WHERE workspace_id=wid AND dataset_id=did) THEN RETURN true; END IF;'||chr(10));
 EXECUTE source;
 source=pg_get_functiondef('public.platform_data_hub(uuid,uuid,text,text,text,uuid,uuid,uuid,integer,integer)'::regprocedure);
 IF strpos(source,'target.dataset_type IN(''orders'',''fleet'')')=0 THEN RAISE EXCEPTION 'Unexpected Dataset Library archive projection'; END IF;
 source=replace(source,'target.dataset_type IN(''orders'',''fleet'')','target.dataset_type IN(''orders'',''fleet'',''transport_demand'',''transport_resources'')');
 EXECUTE source;
END; $$;
DO $$ DECLARE rel text; BEGIN
 FOREACH rel IN ARRAY ARRAY['ultimate_input_objects','ultimate_input_uploads','ultimate_pack_publications'] LOOP
  EXECUTE format('ALTER TABLE dation_private.%I ENABLE ROW LEVEL SECURITY',rel);
  EXECUTE format('ALTER TABLE dation_private.%I FORCE ROW LEVEL SECURITY',rel);
  EXECUTE format('REVOKE ALL ON dation_private.%I FROM PUBLIC,anon,authenticated,service_role',rel);
 END LOOP;
END; $$;
REVOKE ALL ON FUNCTION dation_private.t4_entry(uuid,text,uuid),dation_private.t4_upload(dation_private.ultimate_input_uploads),dation_private.t4_entries(uuid,uuid,jsonb,jsonb) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_ultimate_data_pack(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_ultimate_data_pack(uuid,uuid,text,jsonb) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
