-- Human identity is separate from immutable Case/run IDs and execution evidence.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';
ALTER TABLE public.decision_cases
 ADD COLUMN category text CHECK(category IN('weekly','monthly','extraordinary','simulation','live_operation')),
 ADD COLUMN description text CHECK(description IS NULL OR length(description) BETWEEN 1 AND 1000);

CREATE FUNCTION public.platform_update_case_identity(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid,
 expected_updated_at timestamptz,identity_changes jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE c decision_cases; result jsonb;
BEGIN
 IF jsonb_typeof(identity_changes)<>'object' OR identity_changes-'label'-'category'-'description'<>'{}'::jsonb THEN
  RAISE EXCEPTION 'Invalid Case identity' USING ERRCODE='22023';
 END IF;
 -- Reuse the canonical actor, workspace, row lock, name validation and CAS.
 result=public.platform_update_case(target_workspace_id,actor_user_id,target_case_id,expected_updated_at,
  identity_changes?'label',identity_changes->>'label',NULL);
 UPDATE decision_cases SET
  category=CASE WHEN identity_changes?'category' THEN identity_changes->>'category' ELSE category END,
  description=CASE WHEN identity_changes?'description' THEN nullif(trim(identity_changes->>'description'),'') ELSE description END
 WHERE workspace_id=target_workspace_id AND id=target_case_id RETURNING * INTO c;
 RETURN result||jsonb_build_object('category',c.category,'description',c.description);
END; $$;

-- A Data Pack can change only before the first admitted execution. Keep the
-- same Case, people and technical ID, under the same lock used by admission.
DO $migration$
DECLARE source text; anchor text;
BEGIN
 source=pg_get_functiondef('public.protect_persistence_identity()'::regprocedure);
 anchor=$a$   IF ROW(NEW.id,NEW.created_at,NEW.orders_dataset_id,NEW.fleet_dataset_id,NEW.input_signature,NEW.domain)
      IS DISTINCT FROM ROW(OLD.id,OLD.created_at,OLD.orders_dataset_id,OLD.fleet_dataset_id,OLD.input_signature,OLD.domain) THEN$a$;
 IF strpos(source,anchor)=0 THEN RAISE EXCEPTION 'Unexpected Case identity guard'; END IF;
 source=replace(source,anchor,$a$   IF ROW(NEW.id,NEW.created_at,NEW.domain) IS DISTINCT FROM ROW(OLD.id,OLD.created_at,OLD.domain)
      OR (ROW(NEW.orders_dataset_id,NEW.fleet_dataset_id,NEW.input_signature)
        IS DISTINCT FROM ROW(OLD.orders_dataset_id,OLD.fleet_dataset_id,OLD.input_signature)
        AND EXISTS(SELECT 1 FROM public.decision_runs WHERE workspace_id=OLD.workspace_id AND decision_case_id=OLD.id)) THEN$a$);
 EXECUTE source;
END; $migration$;

CREATE FUNCTION public.platform_replace_case_data_pack(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid,
 expected_updated_at timestamptz,orders_id uuid,fleet_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE c decision_cases; signature text;
BEGIN
 PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true);
 PERFORM 1 FROM workspaces WHERE id=target_workspace_id FOR UPDATE;
 SELECT * INTO c FROM decision_cases WHERE workspace_id=target_workspace_id AND id=target_case_id FOR UPDATE NOWAIT;
 IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
 IF expected_updated_at IS DISTINCT FROM c.updated_at THEN RAISE EXCEPTION 'Case changed; refresh' USING ERRCODE='55006'; END IF;
 IF c.status='archived' OR EXISTS(SELECT 1 FROM decision_runs WHERE workspace_id=target_workspace_id AND decision_case_id=c.id) THEN
  RAISE EXCEPTION 'El Case ya tiene ejecuciones o está archivado. Conservá este Data Pack e iniciá otro Case.' USING ERRCODE='55006';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM datasets WHERE workspace_id=target_workspace_id AND id=orders_id AND dataset_type='orders' AND deletion_requested_at IS NULL)
 OR NOT EXISTS(SELECT 1 FROM datasets WHERE workspace_id=target_workspace_id AND id=fleet_id AND dataset_type='fleet' AND deletion_requested_at IS NULL) THEN
  RAISE EXCEPTION 'Invalid Data Pack' USING ERRCODE='22023';
 END IF;
 signature=orders_id::text||':'||fleet_id::text;
 UPDATE decision_cases SET orders_dataset_id=orders_id,fleet_dataset_id=fleet_id,input_signature=signature,
  state_json=state_json||jsonb_build_object('signature',signature,'inputs',jsonb_build_object('orders_dataset_id',orders_id,'fleet_dataset_id',fleet_id)),
  updated_at=clock_timestamp(),last_activity_at=clock_timestamp()
 WHERE workspace_id=target_workspace_id AND id=c.id RETURNING * INTO c;
 RETURN jsonb_build_object('id',c.id,'updated_at',c.updated_at);
EXCEPTION WHEN lock_not_available THEN RAISE EXCEPTION 'Case is busy; retry' USING ERRCODE='55006';
END; $$;
REVOKE ALL ON FUNCTION public.platform_update_case_identity(uuid,uuid,uuid,timestamptz,jsonb),
 public.platform_replace_case_data_pack(uuid,uuid,uuid,timestamptz,uuid,uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_update_case_identity(uuid,uuid,uuid,timestamptz,jsonb),
 public.platform_replace_case_data_pack(uuid,uuid,uuid,timestamptz,uuid,uuid) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
