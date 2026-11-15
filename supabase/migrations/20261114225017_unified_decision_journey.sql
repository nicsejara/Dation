-- UX04 additive, private staging and lifecycle journal. No release activation.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';
ALTER TABLE dation_private.platform_release ADD COLUMN unified_journey_enabled boolean NOT NULL DEFAULT false;
CREATE TABLE dation_private.journey_preparations (
 id uuid PRIMARY KEY, workspace_id uuid NOT NULL, created_by uuid NOT NULL,
 model_version_id uuid NOT NULL, parent_case_id uuid, case_id uuid,
 revision bigint NOT NULL DEFAULT 1 CHECK(revision>0),
 status text NOT NULL DEFAULT 'DRAFT' CHECK(status IN('DRAFT','VALIDATED','FINALIZING','CONSUMED','EXPIRED')),
 data_owner_user_id uuid, creation_body jsonb, creation_hash text,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL DEFAULT now()+interval '24 hours',
 UNIQUE(workspace_id,id), UNIQUE(workspace_id,case_id),
 FOREIGN KEY(workspace_id,created_by) REFERENCES public.workspace_members(workspace_id,user_id),
 FOREIGN KEY(workspace_id,model_version_id) REFERENCES public.logistics_model_versions(workspace_id,id),
 FOREIGN KEY(workspace_id,parent_case_id) REFERENCES public.decision_cases(workspace_id,id),
 FOREIGN KEY(workspace_id,case_id) REFERENCES public.decision_cases(workspace_id,id),
 CHECK(creation_body IS NULL OR (jsonb_typeof(creation_body)='object' AND octet_length(creation_body::text)<=65536))
);
CREATE UNIQUE INDEX journey_creation_identity ON dation_private.journey_preparations((creation_body->>'id')) WHERE creation_body IS NOT NULL;
CREATE INDEX journey_preparations_actor ON dation_private.journey_preparations(workspace_id,created_by,expires_at);
CREATE TABLE dation_private.journey_uploads (
 id uuid PRIMARY KEY, workspace_id uuid NOT NULL, preparation_id uuid NOT NULL,
 entity text NOT NULL CHECK(entity IN('transport_demand','transport_resources')),
 intent_hash text NOT NULL CHECK(intent_hash ~ '^[0-9a-f]{64}$'),
 metadata jsonb NOT NULL CHECK(jsonb_typeof(metadata)='object' AND octet_length(metadata::text)<=262144),
 ready boolean NOT NULL DEFAULT false, selected boolean NOT NULL DEFAULT false, cleaned boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(workspace_id,preparation_id) REFERENCES dation_private.journey_preparations(workspace_id,id)
);
CREATE UNIQUE INDEX journey_one_selected ON dation_private.journey_uploads(preparation_id,entity) WHERE selected;
CREATE TABLE dation_private.journey_case_events (
 case_id uuid PRIMARY KEY, workspace_id uuid NOT NULL, parent_case_id uuid,
 closed_at timestamptz, closed_by uuid,
 FOREIGN KEY(workspace_id,case_id) REFERENCES public.decision_cases(workspace_id,id),
 FOREIGN KEY(workspace_id,parent_case_id) REFERENCES public.decision_cases(workspace_id,id),
 FOREIGN KEY(workspace_id,closed_by) REFERENCES public.workspace_members(workspace_id,user_id)
);
CREATE FUNCTION dation_private.journey_pending_work(wid uuid,cid uuid) RETURNS boolean
LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.decision_runs r WHERE r.workspace_id=wid AND r.decision_case_id=cid AND r.status IN('queued','running'))
 OR EXISTS(SELECT 1 FROM public.dispatch_run_jobs j JOIN public.decision_runs r ON r.workspace_id=j.workspace_id AND r.id=j.run_id WHERE r.workspace_id=wid AND r.decision_case_id=cid AND j.state IN('queued','running'))
 OR EXISTS(SELECT 1 FROM public.decision_comparative_analyses a JOIN public.decision_runs r ON r.workspace_id=a.workspace_id AND r.id=a.base_run_id WHERE r.workspace_id=wid AND r.decision_case_id=cid AND a.status IN('queued','running'))
 OR EXISTS(SELECT 1 FROM dation_private.ultimate_input_uploads u WHERE u.workspace_id=wid AND u.case_id=cid AND u.status IN('PREPARED','READY')
  AND NOT EXISTS(SELECT 1 FROM public.case_data_packs p JOIN public.case_data_pack_entries e ON e.workspace_id=p.workspace_id AND e.pack_version_id=p.current_version_id WHERE p.workspace_id=wid AND p.case_id=cid AND e.dataset_id=u.dataset_id));
$$;
REVOKE ALL ON FUNCTION dation_private.journey_pending_work(uuid,uuid) FROM PUBLIC,anon,authenticated,service_role;
CREATE FUNCTION public.platform_decision_journey(target_workspace_id uuid,actor_user_id uuid,operation text,arguments jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE role_name text; s dation_private.journey_preparations; u dation_private.journey_uploads;
 c public.decision_cases; raw jsonb; owner_id uuid; chosen uuid; result jsonb; enabled boolean;
BEGIN
 role_name=dation_private.data_actor(target_workspace_id,actor_user_id);
 IF operation IS NULL OR operation NOT IN('capabilities','create','get','list','owner','upload_prepare','upload_get','upload_ready','compatible','reuse_plan','unselect','begin','finish','cleanup','cleanup_done','case_state','close','guarded_publish','lifecycles')
 OR jsonb_typeof(arguments) IS DISTINCT FROM 'object' OR octet_length(arguments::text)>524288 THEN RAISE EXCEPTION 'Invalid journey operation' USING ERRCODE='22023'; END IF;
 SELECT unified_journey_enabled AND ultimate_foundation_enabled AND ultimate_data_pack_enabled INTO enabled FROM dation_private.platform_release WHERE singleton;
 IF operation='capabilities' THEN RETURN jsonb_build_object('enabled',coalesce(enabled,false)); END IF;
 IF NOT enabled THEN RAISE EXCEPTION 'Unified journey is closed' USING ERRCODE='P0002'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.workspace_ddas WHERE workspace_id=target_workspace_id AND dda_id='logistics' AND status='enabled') THEN RAISE EXCEPTION 'DDA denied' USING ERRCODE='42501'; END IF;
 -- Same lock order as admission, Pack, context and responsibilities. CAS spans all mutations.
 PERFORM 1 FROM public.workspaces WHERE id=target_workspace_id FOR UPDATE;
 IF operation='lifecycles' THEN
  IF jsonb_typeof(arguments->'case_ids') IS DISTINCT FROM 'array' OR jsonb_array_length(arguments->'case_ids')>50 THEN RAISE EXCEPTION 'Invalid lifecycle batch' USING ERRCODE='22023'; END IF;
  RETURN coalesce((SELECT jsonb_object_agg(e.case_id::text,to_jsonb(e)) FROM dation_private.journey_case_events e WHERE e.workspace_id=target_workspace_id AND e.case_id::text IN(SELECT jsonb_array_elements_text(arguments->'case_ids'))),'{}');
 END IF;
 IF operation='guarded_publish' THEN
  PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true);
  IF EXISTS(SELECT 1 FROM public.decision_runs WHERE workspace_id=target_workspace_id AND decision_case_id=(arguments->>'case_id')::uuid) THEN RAISE EXCEPTION 'Run admitted: derive a new Case before changing inputs' USING ERRCODE='55006'; END IF;
  RETURN public.platform_ultimate_data_pack(target_workspace_id,actor_user_id,'publish',arguments->'publication_arguments');
 END IF;
 IF operation IN('case_state','close') THEN
  SELECT * INTO c FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=(arguments->>'case_id')::uuid AND workflow_version=2 FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
  raw=public.platform_ultimate_graph(target_workspace_id,actor_user_id,c.id);
  result=jsonb_build_object('snapshot',raw,'token',md5(raw::text),'has_runs',EXISTS(SELECT 1 FROM public.decision_runs WHERE workspace_id=target_workspace_id AND decision_case_id=c.id),
   'pending_work',dation_private.journey_pending_work(target_workspace_id,c.id),
   'lifecycle',(SELECT to_jsonb(e) FROM dation_private.journey_case_events e WHERE e.workspace_id=target_workspace_id AND e.case_id=c.id));
  IF operation='case_state' THEN RETURN result; END IF;
  PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true);
  IF EXISTS(SELECT 1 FROM dation_private.journey_case_events WHERE workspace_id=target_workspace_id AND case_id=c.id AND closed_at IS NOT NULL) AND c.status='archived' THEN RETURN result; END IF;
  IF c.status='archived' OR arguments->>'token' IS DISTINCT FROM result->>'token' OR arguments->>'eligible' IS DISTINCT FROM 'true'
   OR dation_private.journey_pending_work(target_workspace_id,c.id)
  THEN RAISE EXCEPTION 'Case changed or has pending work; close denied' USING ERRCODE='55006'; END IF;
  PERFORM set_config('dation.workspace_id',target_workspace_id::text,true);PERFORM set_config('dation.actor_user_id',actor_user_id::text,true);
  UPDATE public.decision_cases SET status='archived',archived_at=clock_timestamp(),updated_at=clock_timestamp() WHERE workspace_id=target_workspace_id AND id=c.id;
  INSERT INTO dation_private.journey_case_events(case_id,workspace_id,closed_at,closed_by) VALUES(c.id,target_workspace_id,clock_timestamp(),actor_user_id)
   ON CONFLICT(case_id) DO UPDATE SET closed_at=excluded.closed_at,closed_by=excluded.closed_by;
  INSERT INTO public.audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,decision_case_id,metadata_json)
   VALUES(target_workspace_id,actor_user_id,'decision_case.closed','decision_case',c.id,c.id,jsonb_build_object('reason','completed','graph_token',result->>'token'));
  RETURN result||jsonb_build_object('closed',true);
 END IF;
 IF operation='list' THEN
  RETURN jsonb_build_object('items',coalesce((SELECT jsonb_agg(to_jsonb(x)) FROM (SELECT id,model_version_id,parent_case_id,status,revision,expires_at,updated_at FROM dation_private.journey_preparations
   WHERE workspace_id=target_workspace_id AND created_by=actor_user_id AND status IN('DRAFT','VALIDATED','FINALIZING') AND (expires_at>now() OR status='FINALIZING') ORDER BY updated_at DESC LIMIT 10) x),'[]'));
 END IF;
 IF operation='create' THEN
  PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true);
  SELECT * INTO s FROM dation_private.journey_preparations WHERE id=(arguments->>'id')::uuid;
  IF FOUND THEN
   IF s.workspace_id<>target_workspace_id OR s.created_by<>actor_user_id THEN RAISE EXCEPTION 'Preparation not found' USING ERRCODE='P0002'; END IF;
   IF s.model_version_id<>(arguments->>'model_version_id')::uuid OR s.parent_case_id IS DISTINCT FROM (arguments->>'parent_case_id')::uuid THEN RAISE EXCEPTION 'Preparation identity changed' USING ERRCODE='55006'; END IF;
  ELSE
   IF (SELECT count(*) FROM dation_private.journey_preparations WHERE workspace_id=target_workspace_id AND created_by=actor_user_id AND ((expires_at>now() OR status='FINALIZING') AND status IN('DRAFT','VALIDATED','FINALIZING') OR EXISTS(SELECT 1 FROM dation_private.journey_uploads retained WHERE retained.preparation_id=journey_preparations.id AND NOT cleaned)))>=5 THEN RAISE EXCEPTION 'Pending preparation limit (5)' USING ERRCODE='55006'; END IF;
   IF NOT EXISTS(SELECT 1 FROM public.logistics_model_versions v JOIN public.logistics_models m ON m.workspace_id=v.workspace_id AND m.id=v.model_id WHERE v.workspace_id=target_workspace_id AND v.id=(arguments->>'model_version_id')::uuid AND m.status='active') THEN RAISE EXCEPTION 'Published version not found' USING ERRCODE='P0002'; END IF;
   IF arguments->>'parent_case_id' IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=(arguments->>'parent_case_id')::uuid AND workflow_version=2) THEN RAISE EXCEPTION 'Parent Case not found' USING ERRCODE='P0002'; END IF;
   INSERT INTO dation_private.journey_preparations(id,workspace_id,created_by,model_version_id,parent_case_id)
    VALUES((arguments->>'id')::uuid,target_workspace_id,actor_user_id,(arguments->>'model_version_id')::uuid,(arguments->>'parent_case_id')::uuid) RETURNING * INTO s;
  END IF;
 ELSE
  SELECT * INTO s FROM dation_private.journey_preparations WHERE workspace_id=target_workspace_id AND created_by=actor_user_id AND id=(arguments->>'preparation_id')::uuid FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Preparation not found' USING ERRCODE='P0002'; END IF;
 END IF;
 IF operation IN('cleanup','cleanup_done') THEN PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true); END IF;
 IF operation='cleanup' THEN
  IF s.status IN('DRAFT','VALIDATED') AND s.expires_at<=now() THEN UPDATE dation_private.journey_preparations SET status='EXPIRED' WHERE id=s.id RETURNING * INTO s; END IF;
  IF s.status NOT IN('EXPIRED','CONSUMED') THEN RAISE EXCEPTION 'Preparation still in use' USING ERRCODE='55006'; END IF;
  RETURN jsonb_build_object('uploads',coalesce((SELECT jsonb_agg(to_jsonb(x)) FROM dation_private.journey_uploads x WHERE preparation_id=s.id AND NOT cleaned),'[]'));
 END IF;
 IF operation='cleanup_done' THEN
  IF s.status NOT IN('EXPIRED','CONSUMED') THEN RAISE EXCEPTION 'Preparation still in use' USING ERRCODE='55006'; END IF;
  UPDATE dation_private.journey_uploads SET cleaned=true WHERE preparation_id=s.id AND id=(arguments->>'upload_id')::uuid; RETURN '{}';
 END IF;
 IF s.status IN('DRAFT','VALIDATED') AND s.expires_at<=now() THEN UPDATE dation_private.journey_preparations SET status='EXPIRED' WHERE id=s.id RETURNING * INTO s; END IF;
 IF s.status='EXPIRED' AND operation NOT IN('get','create') THEN RAISE EXCEPTION 'Preparation expired' USING ERRCODE='55006'; END IF;
 IF operation NOT IN('get','create') THEN PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true); END IF;
 IF operation='begin' AND s.creation_hash IS NOT NULL THEN
  IF s.creation_hash IS DISTINCT FROM arguments->>'creation_hash' THEN RAISE EXCEPTION 'Frozen creation intent changed' USING ERRCODE='55006'; END IF;
 ELSIF operation NOT IN('get','create','upload_get','compatible','reuse_plan','finish') THEN
  IF s.status IN('FINALIZING','CONSUMED') OR s.revision IS DISTINCT FROM (arguments->>'expected_revision')::bigint THEN RAISE EXCEPTION 'Preparation changed; reload its revision' USING ERRCODE='55006'; END IF;
  IF operation='owner' THEN
   owner_id=(arguments->>'data_owner_user_id')::uuid;
   IF role_name<>'admin' OR owner_id IS NOT NULL AND NOT dation_private.responsibility_eligible(target_workspace_id,owner_id,'data') THEN RAISE EXCEPTION 'Data Owner not eligible' USING ERRCODE='42501'; END IF;
   UPDATE dation_private.journey_preparations SET data_owner_user_id=owner_id,revision=revision+1,updated_at=clock_timestamp() WHERE id=s.id RETURNING * INTO s;
  ELSIF operation='upload_prepare' THEN
   SELECT * INTO u FROM dation_private.journey_uploads WHERE id=(arguments->>'upload_id')::uuid;
   IF FOUND THEN
    IF u.preparation_id<>s.id OR u.intent_hash IS DISTINCT FROM arguments->>'intent_hash' THEN RAISE EXCEPTION 'Upload intent changed' USING ERRCODE='55006'; END IF;
   ELSE
    IF (SELECT count(*) FROM dation_private.journey_uploads WHERE preparation_id=s.id)>=10 THEN RAISE EXCEPTION 'Preparation upload limit (10)' USING ERRCODE='55006'; END IF;
    IF coalesce(arguments->>'entity','') NOT IN('transport_demand','transport_resources') OR arguments#>>'{metadata,report,valid}' IS DISTINCT FROM 'true' THEN RAISE EXCEPTION 'Validated CSV required' USING ERRCODE='22023'; END IF;
    INSERT INTO dation_private.journey_uploads(id,workspace_id,preparation_id,entity,intent_hash,metadata) VALUES((arguments->>'upload_id')::uuid,target_workspace_id,s.id,arguments->>'entity',arguments->>'intent_hash',arguments->'metadata') RETURNING * INTO u;
   END IF;
  ELSIF operation='upload_ready' THEN
   SELECT * INTO u FROM dation_private.journey_uploads WHERE preparation_id=s.id AND id=(arguments->>'upload_id')::uuid;
   IF NOT FOUND THEN RAISE EXCEPTION 'Upload not found' USING ERRCODE='P0002'; END IF;
   UPDATE dation_private.journey_uploads SET selected=false WHERE preparation_id=s.id AND entity=u.entity;
   UPDATE dation_private.journey_uploads SET ready=true,selected=true WHERE id=u.id;
   UPDATE dation_private.journey_preparations SET revision=revision+1,status=CASE WHEN (SELECT count(*) FROM dation_private.journey_uploads WHERE preparation_id=s.id AND selected)=2 THEN 'VALIDATED' ELSE 'DRAFT' END,updated_at=clock_timestamp() WHERE id=s.id RETURNING * INTO s;
  ELSIF operation='unselect' THEN
   UPDATE dation_private.journey_uploads SET selected=false WHERE preparation_id=s.id AND entity=arguments->>'entity';
   UPDATE dation_private.journey_preparations SET revision=revision+1,status='DRAFT',updated_at=clock_timestamp() WHERE id=s.id RETURNING * INTO s;
  ELSIF operation='begin' THEN
   IF EXISTS(SELECT 1 FROM public.decision_cases WHERE id=(arguments#>>'{creation_body,id}')::uuid) OR EXISTS(SELECT 1 FROM dation_private.journey_preparations other WHERE other.id<>s.id AND other.creation_body->>'id'=arguments#>>'{creation_body,id}') THEN RAISE EXCEPTION 'Case identity already in use' USING ERRCODE='55006'; END IF;
   IF s.data_owner_user_id IS NOT NULL AND (role_name<>'admin' OR NOT dation_private.responsibility_eligible(target_workspace_id,s.data_owner_user_id,'data')) THEN RAISE EXCEPTION 'Data Owner permission changed' USING ERRCODE='42501'; END IF;
   IF s.model_version_id IS DISTINCT FROM (arguments#>>'{creation_body,logistics_model_version_id}')::uuid THEN RAISE EXCEPTION 'Model Version changed' USING ERRCODE='55006'; END IF;
   UPDATE dation_private.journey_preparations SET creation_body=arguments->'creation_body',creation_hash=arguments->>'creation_hash',status='FINALIZING',revision=revision+1,updated_at=clock_timestamp() WHERE id=s.id RETURNING * INTO s;
  ELSE RAISE EXCEPTION 'Invalid mutation' USING ERRCODE='22023'; END IF;
 END IF;
 IF operation IN('compatible','reuse_plan') THEN
  PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true);
  IF s.status NOT IN('DRAFT','VALIDATED') THEN RAISE EXCEPTION 'Preparation frozen' USING ERRCODE='55006'; END IF;
  IF operation='compatible' THEN
   RETURN jsonb_build_object('items',coalesce((SELECT jsonb_agg(to_jsonb(x)) FROM (SELECT d.id,d.original_filename,d.row_count FROM public.datasets d JOIN dation_private.ultimate_input_objects o ON o.workspace_id=d.workspace_id AND o.dataset_id=d.id WHERE d.workspace_id=target_workspace_id AND o.model_version_id=s.model_version_id AND d.dataset_type=arguments->>'entity' AND d.data_contract_hash=arguments->>'contract_hash' AND d.archived_at IS NULL AND d.deletion_requested_at IS NULL ORDER BY d.created_at DESC,d.id LIMIT 25) x),'[]'));
  END IF;
  result=dation_private.t4_entry(target_workspace_id,arguments->>'entity',(arguments->>'dataset_id')::uuid);
  IF result IS NULL OR result->>'contract_hash' IS DISTINCT FROM arguments->>'contract_hash' OR NOT EXISTS(SELECT 1 FROM dation_private.ultimate_input_objects o JOIN public.datasets d ON d.workspace_id=o.workspace_id AND d.id=o.dataset_id WHERE o.workspace_id=target_workspace_id AND o.dataset_id=(arguments->>'dataset_id')::uuid AND o.model_version_id=s.model_version_id AND d.archived_at IS NULL AND d.deletion_requested_at IS NULL) THEN RAISE EXCEPTION 'Compatible source not found' USING ERRCODE='P0002'; END IF;
  RETURN result;
 END IF;
 IF operation='upload_get' THEN
  SELECT * INTO u FROM dation_private.journey_uploads WHERE preparation_id=s.id AND id=(arguments->>'upload_id')::uuid;
  IF NOT FOUND THEN RAISE EXCEPTION 'Upload not found' USING ERRCODE='P0002'; END IF;
 END IF;
 IF operation='finish' THEN
  chosen=(s.creation_body->>'id')::uuid;
  IF s.status NOT IN('FINALIZING','CONSUMED') OR NOT EXISTS(SELECT 1 FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=chosen AND created_by_user_id=actor_user_id AND logistics_model_version_id=s.model_version_id) THEN RAISE EXCEPTION 'Creation not confirmed' USING ERRCODE='55006'; END IF;
  UPDATE dation_private.journey_preparations SET status='CONSUMED',case_id=chosen,updated_at=clock_timestamp() WHERE id=s.id RETURNING * INTO s;
  INSERT INTO dation_private.journey_case_events(case_id,workspace_id,parent_case_id) VALUES(chosen,target_workspace_id,s.parent_case_id) ON CONFLICT(case_id) DO NOTHING;
 END IF;
 RETURN jsonb_build_object('session',to_jsonb(s),'upload',to_jsonb(u),'uploads',coalesce((SELECT jsonb_agg(to_jsonb(x) ORDER BY created_at,id) FROM dation_private.journey_uploads x WHERE preparation_id=s.id),'[]'),
  'model_version',(SELECT to_jsonb(v) FROM public.logistics_model_versions v WHERE workspace_id=target_workspace_id AND id=s.model_version_id));
END; $$;
DO $$ DECLARE rel text; BEGIN
 FOREACH rel IN ARRAY ARRAY['journey_preparations','journey_uploads','journey_case_events'] LOOP
  EXECUTE format('ALTER TABLE dation_private.%I ENABLE ROW LEVEL SECURITY',rel);
  EXECUTE format('ALTER TABLE dation_private.%I FORCE ROW LEVEL SECURITY',rel);
  EXECUTE format('REVOKE ALL ON dation_private.%I FROM PUBLIC,anon,authenticated,service_role',rel);
 END LOOP;
END; $$;
REVOKE ALL ON FUNCTION public.platform_decision_journey(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_decision_journey(uuid,uuid,text,jsonb) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
