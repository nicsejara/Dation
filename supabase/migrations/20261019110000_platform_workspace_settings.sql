-- Phase 9: workspace preferences. Free is the current universal product policy.
-- No billing tables, payment data, account changes or commercial backfill.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';
CREATE FUNCTION public.platform_workspace_settings(target_workspace_id uuid,actor_user_id uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE workspace workspaces;
BEGIN
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
 SELECT * INTO workspace FROM workspaces WHERE id=target_workspace_id;
 RETURN jsonb_build_object('workspace',to_jsonb(workspace),
  'ddas',coalesce((SELECT jsonb_agg(jsonb_build_object('dda_id',d.dda_id,'status',d.status) ORDER BY d.dda_id) FROM workspace_ddas d WHERE d.workspace_id=target_workspace_id),'[]'),
  'plan',jsonb_build_object('code','free','name','Free','status','active','price_amount',0,'billing_mode','free',
   'requires_payment_method',false,'trial_ends_at',NULL,'member_limit',NULL),
  'members',jsonb_build_object('active',(SELECT count(*) FROM workspace_members WHERE workspace_id=target_workspace_id AND status='active'),
   'total',(SELECT count(*) FROM workspace_members WHERE workspace_id=target_workspace_id)));
END; $$;
CREATE FUNCTION public.platform_update_workspace(target_workspace_id uuid,actor_user_id uuid,expected_updated_at timestamptz,section_name text,changes jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE workspace workspaces; before_values jsonb; after_values jsonb; allowed text[];
BEGIN
 SELECT * INTO workspace FROM workspaces WHERE id=target_workspace_id FOR UPDATE NOWAIT;
 PERFORM dation_private.team_actor(target_workspace_id,actor_user_id,true);
 IF workspace.updated_at IS DISTINCT FROM expected_updated_at THEN RAISE EXCEPTION 'Workspace changed; refresh' USING ERRCODE='55006'; END IF;
 IF section_name IS NULL OR section_name NOT IN('general','operation') OR changes IS NULL OR jsonb_typeof(changes)<>'object' THEN
 RAISE EXCEPTION 'Invalid settings section' USING ERRCODE='22023'; END IF;
 allowed=CASE WHEN section_name='general' THEN ARRAY['name','country','language','timezone'] ELSE ARRAY['currency','weight_unit','distance_unit','logistics_unit'] END;
 IF (changes-allowed)<>'{}'::jsonb OR NOT changes ?& allowed OR EXISTS(SELECT 1 FROM jsonb_each(changes) WHERE jsonb_typeof(value)<>'string') THEN
 RAISE EXCEPTION 'Invalid settings fields' USING ERRCODE='22023'; END IF;
 IF section_name='general' THEN
  IF length(trim(changes->>'name')) NOT BETWEEN 2 AND 120 OR changes->>'country' !~ '^[A-Z]{2}$' OR changes->>'language' NOT IN('es','en','pt')
   OR NOT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name=changes->>'timezone') THEN RAISE EXCEPTION 'Invalid general preferences' USING ERRCODE='22023'; END IF;
  before_values=jsonb_build_object('name',workspace.name,'country',workspace.country,'language',workspace.language,'timezone',workspace.timezone);
  UPDATE workspaces SET name=trim(changes->>'name'),country=changes->>'country',language=changes->>'language',timezone=changes->>'timezone',updated_at=clock_timestamp()
   WHERE id=target_workspace_id RETURNING * INTO workspace;
  after_values=jsonb_build_object('name',workspace.name,'country',workspace.country,'language',workspace.language,'timezone',workspace.timezone);
 ELSE
  IF changes->>'currency' NOT IN('ARS','BRL','CLP','COP','EUR','MXN','PEN','USD','UYU') OR changes->>'weight_unit' NOT IN('kg','t')
   OR changes->>'distance_unit' NOT IN('km','mi') OR changes->>'logistics_unit' NOT IN('units','pallets','cases') THEN RAISE EXCEPTION 'Invalid operational preferences' USING ERRCODE='22023'; END IF;
  before_values=jsonb_build_object('currency',workspace.currency,'weight_unit',workspace.weight_unit,'distance_unit',workspace.distance_unit,'logistics_unit',workspace.logistics_unit);
  UPDATE workspaces SET currency=changes->>'currency',weight_unit=changes->>'weight_unit',distance_unit=changes->>'distance_unit',logistics_unit=changes->>'logistics_unit',updated_at=clock_timestamp()
   WHERE id=target_workspace_id RETURNING * INTO workspace;
  after_values=jsonb_build_object('currency',workspace.currency,'weight_unit',workspace.weight_unit,'distance_unit',workspace.distance_unit,'logistics_unit',workspace.logistics_unit);
 END IF;
 INSERT INTO audit_events(workspace_id,actor_user_id,event_type,metadata_json) VALUES(target_workspace_id,actor_user_id,'workspace.settings_updated',
  jsonb_build_object('section',section_name,'before',before_values,'after',after_values));
 RETURN jsonb_build_object('workspace',to_jsonb(workspace));
EXCEPTION WHEN lock_not_available THEN RAISE EXCEPTION 'Workspace is busy; refresh' USING ERRCODE='55006';
END; $$;
REVOKE ALL ON FUNCTION public.platform_workspace_settings(uuid,uuid),public.platform_update_workspace(uuid,uuid,timestamptz,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_workspace_settings(uuid,uuid),public.platform_update_workspace(uuid,uuid,timestamptz,text,jsonb) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
