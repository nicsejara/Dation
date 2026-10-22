-- Saga 3 A: reopen on admission, preserve every execution and approval event.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';
ALTER TABLE public.decision_runs DROP CONSTRAINT decision_runs_superseded_requires_approval_check;
ALTER TABLE public.decision_runs ADD CONSTRAINT decision_runs_superseded_requires_approval_check
 CHECK(superseded_at IS NULL OR approved_at IS NOT NULL OR superseded_by_run_id IS NOT NULL);

CREATE FUNCTION dation_private.invalidate_run_lineage(admitted public.decision_runs) RETURNS void
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE sequence text[]=ARRAY['logistics_assignment','logistics_scheduling','logistics_final_assignment'];
 position integer; affected text[]; reopening boolean; stamp timestamptz=clock_timestamp();
BEGIN
 position=array_position(sequence,admitted.node_id);
 IF admitted.decision_case_id IS NULL OR position IS NULL THEN RETURN; END IF;
 PERFORM 1 FROM workspaces WHERE id=admitted.workspace_id FOR UPDATE;
 PERFORM 1 FROM decision_cases WHERE workspace_id=admitted.workspace_id AND id=admitted.decision_case_id FOR UPDATE;
 SELECT EXISTS(SELECT 1 FROM decision_runs WHERE workspace_id=admitted.workspace_id
  AND decision_case_id=admitted.decision_case_id AND node_id=admitted.node_id
  AND id<>admitted.id AND approved_at IS NOT NULL AND superseded_at IS NULL) INTO reopening;
 affected=sequence[(position+1):array_length(sequence,1)];
 IF reopening THEN affected=array_prepend(admitted.node_id,coalesce(affected,ARRAY[]::text[])); END IF;
 INSERT INTO decision_approval_events(workspace_id,run_id,case_id,node_id,action,actor,actor_user_id,occurred_at,replacement_run_id)
 SELECT workspace_id,id,decision_case_id,node_id,'superseded',coalesce('user:'||admitted.created_by_user_id,'system:run_reopening'),
  admitted.created_by_user_id,stamp,admitted.id FROM decision_runs
 WHERE workspace_id=admitted.workspace_id AND decision_case_id=admitted.decision_case_id
  AND node_id=ANY(affected) AND id<>admitted.id AND approved_at IS NOT NULL AND superseded_at IS NULL;
 UPDATE decision_runs SET superseded_at=stamp,superseded_by_run_id=admitted.id
 WHERE workspace_id=admitted.workspace_id AND decision_case_id=admitted.decision_case_id
  AND node_id=ANY(affected) AND id<>admitted.id AND superseded_at IS NULL;
END; $$;
CREATE FUNCTION dation_private.reopen_on_run_admission() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN PERFORM dation_private.invalidate_run_lineage(NEW); RETURN NEW; END; $$;
CREATE TRIGGER decision_runs_reopen AFTER INSERT ON public.decision_runs
 FOR EACH ROW EXECUTE FUNCTION dation_private.reopen_on_run_admission();
REVOKE ALL ON FUNCTION dation_private.invalidate_run_lineage(public.decision_runs),dation_private.reopen_on_run_admission()
 FROM PUBLIC,anon,authenticated,service_role;

-- Order current/latest by actual admission time, after workspace/case locks.
-- A waiting transaction's start timestamp must not backdate the new current Run.
DO $$ DECLARE source text;
BEGIN
 source=pg_get_functiondef('dation_private.enqueue_dispatch_run(jsonb,jsonb,text,integer)'::regprocedure);
 IF strpos(source,'id, dataset_id, orders_dataset_id, fleet_dataset_id, schema_version,')=0 OR
    strpos(source,'target_id, (run_payload ->> ''dataset_id'')::uuid,')=0 THEN RAISE EXCEPTION 'Unexpected admission timestamp contract'; END IF;
 source=replace(source,'id, dataset_id, orders_dataset_id, fleet_dataset_id, schema_version,','id, created_at, dataset_id, orders_dataset_id, fleet_dataset_id, schema_version,');
 source=replace(source,'target_id, (run_payload ->> ''dataset_id'')::uuid,','target_id, clock_timestamp(), (run_payload ->> ''dataset_id'')::uuid,');
 EXECUTE source;
END; $$;

-- Existing candidates become current under the same rule; no evidence is rewritten.
DO $$ DECLARE r public.decision_runs;
BEGIN
 FOR r IN SELECT latest.* FROM (SELECT DISTINCT ON(workspace_id,decision_case_id,node_id) *
  FROM decision_runs WHERE decision_case_id IS NOT NULL ORDER BY workspace_id,decision_case_id,node_id,created_at DESC,id DESC) latest
  WHERE EXISTS(SELECT 1 FROM decision_runs a WHERE a.workspace_id=latest.workspace_id AND a.decision_case_id=latest.decision_case_id
   AND a.node_id=latest.node_id AND a.id<>latest.id AND a.approved_at IS NOT NULL AND a.superseded_at IS NULL
   AND a.approved_at<latest.created_at) ORDER BY latest.created_at,latest.id
 LOOP PERFORM dation_private.invalidate_run_lineage(r); END LOOP;
END; $$;

-- A persisted Case's inputs never change, even before its first execution.
DO $$ DECLARE source text; anchor text;
BEGIN
 source=pg_get_functiondef('public.protect_persistence_identity()'::regprocedure);
 anchor=$a$   IF ROW(NEW.id,NEW.created_at,NEW.domain) IS DISTINCT FROM ROW(OLD.id,OLD.created_at,OLD.domain)
      OR (ROW(NEW.orders_dataset_id,NEW.fleet_dataset_id,NEW.input_signature)
        IS DISTINCT FROM ROW(OLD.orders_dataset_id,OLD.fleet_dataset_id,OLD.input_signature)
        AND EXISTS(SELECT 1 FROM public.decision_runs WHERE workspace_id=OLD.workspace_id AND decision_case_id=OLD.id)) THEN$a$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected Case guard'; END IF;
 EXECUTE replace(source,anchor,$a$   IF ROW(NEW.id,NEW.created_at,NEW.domain,NEW.orders_dataset_id,NEW.fleet_dataset_id,NEW.input_signature)
      IS DISTINCT FROM ROW(OLD.id,OLD.created_at,OLD.domain,OLD.orders_dataset_id,OLD.fleet_dataset_id,OLD.input_signature) THEN$a$);
END; $$;

CREATE OR REPLACE FUNCTION public.platform_replace_case_data_pack(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid,
 expected_updated_at timestamptz,orders_id uuid,fleet_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE c decision_cases; next_case decision_cases; next_id uuid;
BEGIN
 PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true);
 PERFORM set_config('dation.workspace_id',target_workspace_id::text,true);
 PERFORM set_config('dation.actor_user_id',actor_user_id::text,true);
 PERFORM 1 FROM workspaces WHERE id=target_workspace_id FOR UPDATE;
 SELECT * INTO c FROM decision_cases WHERE workspace_id=target_workspace_id AND id=target_case_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
 IF expected_updated_at IS DISTINCT FROM c.updated_at THEN RAISE EXCEPTION 'Case changed; refresh' USING ERRCODE='55006'; END IF;
 IF NOT EXISTS(SELECT 1 FROM datasets WHERE workspace_id=target_workspace_id AND id=orders_id AND dataset_type='orders' AND deletion_requested_at IS NULL)
 OR NOT EXISTS(SELECT 1 FROM datasets WHERE workspace_id=target_workspace_id AND id=fleet_id AND dataset_type='fleet' AND deletion_requested_at IS NULL) THEN
  RAISE EXCEPTION 'Invalid Data Pack' USING ERRCODE='22023'; END IF;
 IF (c.orders_dataset_id,c.fleet_dataset_id)=(orders_id,fleet_id) THEN
  RETURN jsonb_build_object('id',c.id,'updated_at',c.updated_at,'created',false);
 END IF;
 -- Stable per source Case/Data Pack so a network retry cannot duplicate the fork.
 next_id=md5(target_workspace_id::text||target_case_id::text||orders_id::text||fleet_id::text)::uuid;
 INSERT INTO decision_cases(id,workspace_id,schema_version,domain,status,orders_dataset_id,fleet_dataset_id,input_signature,label,category,description,state_json)
 VALUES(next_id,target_workspace_id,'decision_case_v2',c.domain,'active',orders_id,fleet_id,orders_id::text||':'||fleet_id::text,c.label,c.category,c.description,'{}'::jsonb)
 ON CONFLICT(id) DO NOTHING;
 SELECT * INTO STRICT next_case FROM decision_cases WHERE workspace_id=target_workspace_id AND id=next_id
  AND orders_dataset_id=orders_id AND fleet_dataset_id=fleet_id;
 RETURN jsonb_build_object('id',next_case.id,'updated_at',next_case.updated_at,'created',true,'predecessor_id',c.id);
END; $$;
NOTIFY pgrst,'reload schema';
COMMIT;
