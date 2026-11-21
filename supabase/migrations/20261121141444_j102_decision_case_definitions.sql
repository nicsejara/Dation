-- J1.02: additive private definition history. No production activation.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';
ALTER TABLE dation_private.platform_release ADD COLUMN j102_enabled boolean NOT NULL DEFAULT false;

-- Match the additive Python mathematical projection while retaining full
-- revision identity in Run/configuration/artifacts. Legacy contexts unchanged.
ALTER FUNCTION dation_private.t9_input_hash(jsonb,jsonb,jsonb) RENAME TO j102_legacy_input_hash;
CREATE FUNCTION dation_private.t9_input_hash(c jsonb,identity jsonb,upstream jsonb DEFAULT NULL) RETURNS text
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
BEGIN
 IF c?'decision_definition' THEN c=jsonb_set(c,'{decision_definition}',(c->'decision_definition')-'definition_revision_id'-'definition_hash'); END IF;
 RETURN dation_private.j102_legacy_input_hash(c,identity,upstream);
END $$;
REVOKE ALL ON FUNCTION dation_private.j102_legacy_input_hash(jsonb,jsonb,jsonb),dation_private.t9_input_hash(jsonb,jsonb,jsonb) FROM PUBLIC,anon,authenticated,service_role;

CREATE TABLE dation_private.case_definition_revisions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL, case_id uuid NOT NULL,
 revision bigint NOT NULL CHECK(revision>0), mutation_id uuid NOT NULL,
 prior_revision_id uuid, snapshot jsonb NOT NULL CHECK(jsonb_typeof(snapshot)='object'),
 definition_hash text NOT NULL CHECK(definition_hash ~ '^[0-9a-f]{64}$'),
 actor_user_id uuid NOT NULL REFERENCES auth.users(id), created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(workspace_id,case_id,revision), UNIQUE(workspace_id,case_id,mutation_id), UNIQUE(workspace_id,case_id,id),
 FOREIGN KEY(workspace_id,case_id) REFERENCES public.decision_cases(workspace_id,id),
 FOREIGN KEY(workspace_id,case_id,prior_revision_id) REFERENCES dation_private.case_definition_revisions(workspace_id,case_id,id)
);
ALTER TABLE dation_private.case_definition_revisions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON dation_private.case_definition_revisions FROM PUBLIC,anon,authenticated,service_role;
CREATE TRIGGER j102_definition_immutable BEFORE UPDATE OR DELETE ON dation_private.case_definition_revisions
 FOR EACH ROW EXECUTE FUNCTION dation_private.ultimate_immutable();

CREATE FUNCTION dation_private.j102_valid(d jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
BEGIN
 RETURN coalesce(jsonb_typeof(d)='object' AND
 d ?& ARRAY['schema_version','case_work_id','identity','model_binding','decision_context','case_policy','business_rules','acceptance_policy','approval_policy','provenance'] AND
 d-ARRAY['schema_version','case_work_id','identity','model_binding','decision_context','case_policy','business_rules','acceptance_policy','approval_policy','provenance']='{}' AND
 d->>'schema_version'='decision_case_definition_v2' AND (d->>'case_work_id')::uuid IS NOT NULL AND
 (d->'identity')-ARRAY['name','description']='{}' AND length(trim(d#>>'{identity,name}')) BETWEEN 1 AND 120 AND length(coalesce(d#>>'{identity,description}',''))<=1000 AND
 (d->'model_binding')-ARRAY['model_id','model_version_id','configuration_hash','contract_hash']='{}' AND
 d#>>'{model_binding,configuration_hash}' ~ '^[0-9a-f]{64}$' AND d#>>'{model_binding,contract_hash}' ~ '^[0-9a-f]{64}$' AND
 (d->'decision_context')-ARRAY['planning_start','planning_end','horizon_type','operating_mode']='{}' AND
 (d#>>'{decision_context,planning_start}')::date<=(d#>>'{decision_context,planning_end}')::date AND
 d#>>'{decision_context,horizon_type}' IN('DAILY','WEEKLY','MONTHLY','CUSTOM') AND d#>>'{decision_context,operating_mode}' IN('OPERATIONAL','SIMULATION') AND
 dation_private.t3_policy_valid(d->'case_policy') AND jsonb_array_length(d#>'{case_policy,guardrails}')=1 AND
 d#>>'{case_policy,guardrails,0,kind}'='CRITICAL_DEMAND_COVERAGE' AND
 (d->'business_rules')-ARRAY['version','prefer_own_fleet_on_cost_tie']='{}' AND d#>'{business_rules,version}'='1'::jsonb AND
 jsonb_typeof(d#>'{business_rules,prefer_own_fleet_on_cost_tie}')='boolean' AND
 (d#>'{business_rules,prefer_own_fleet_on_cost_tie}'='false'::jsonb OR
   (d#>>'{case_policy,primary_goal}'='MINIMIZE_COST' AND jsonb_array_length(d#>'{case_policy,preferences}')=0)) AND
 (d->'acceptance_policy')-ARRAY['version','metric','comparator','threshold','basis']='{}' AND d#>'{acceptance_policy,version}'='1'::jsonb AND
 d#>>'{acceptance_policy,metric}'='TOTAL_DEMAND_COVERAGE' AND d#>>'{acceptance_policy,comparator}'='GTE' AND
 d#>>'{acceptance_policy,basis}'='CANONICAL_MODEL_PRIMARY_DIMENSION' AND d#>>'{acceptance_policy,threshold}' ~ '^(0(\.[0-9]{1,4})?|1(\.0{1,4})?)$' AND
 d->'approval_policy'='{"kind":"MANUAL_DECISION_OWNER"}'::jsonb AND
 (d->'provenance'='null'::jsonb OR (jsonb_typeof(d->'provenance')='object' AND (d->'provenance')-ARRAY['parent_case_id','parent_definition_revision_id','reason']='{}' AND length(trim(d#>>'{provenance,reason}')) BETWEEN 1 AND 1000)),false);
 EXCEPTION WHEN invalid_text_representation OR datetime_field_overflow OR invalid_datetime_format THEN RETURN false;
END $$;

CREATE FUNCTION dation_private.j102_check_binding(wid uuid,uid uuid,d jsonb,new_case boolean) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE v public.logistics_model_versions; parent_id uuid; revision_id uuid;
BEGIN
 PERFORM dation_private.team_actor(wid,uid);
 IF NOT dation_private.j102_valid(d) THEN RAISE EXCEPTION 'Invalid Decision Case V2 definition' USING ERRCODE='22023'; END IF;
 SELECT * INTO v FROM public.logistics_model_versions WHERE workspace_id=wid AND id=(d#>>'{model_binding,model_version_id}')::uuid;
 IF NOT FOUND OR v.model_id IS DISTINCT FROM (d#>>'{model_binding,model_id}')::uuid OR
 v.config_hash IS DISTINCT FROM d#>>'{model_binding,configuration_hash}' OR v.contract_hash IS DISTINCT FROM d#>>'{model_binding,contract_hash}' THEN
  RAISE EXCEPTION 'Model/version/hash not found in workspace' USING ERRCODE='P0002'; END IF;
 IF new_case AND NOT EXISTS(SELECT 1 FROM public.logistics_models WHERE workspace_id=wid AND id=v.model_id AND status='active') THEN
  RAISE EXCEPTION 'Model is archived' USING ERRCODE='22023'; END IF;
 parent_id=(d#>>'{provenance,parent_case_id}')::uuid;revision_id=(d#>>'{provenance,parent_definition_revision_id}')::uuid;
 IF parent_id IS NOT NULL THEN
  IF NOT EXISTS(SELECT 1 FROM public.decision_cases WHERE workspace_id=wid AND id=parent_id) THEN RAISE EXCEPTION 'Parent Case not found' USING ERRCODE='P0002'; END IF;
  IF revision_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM dation_private.case_definition_revisions WHERE workspace_id=wid AND case_id=parent_id AND id=revision_id) THEN RAISE EXCEPTION 'Parent definition not found' USING ERRCODE='P0002'; END IF;
  IF revision_id IS NULL AND EXISTS(SELECT 1 FROM dation_private.case_definition_revisions WHERE workspace_id=wid AND case_id=parent_id) THEN RAISE EXCEPTION 'Choose an exact parent definition' USING ERRCODE='22023'; END IF;
 END IF;
END $$;

CREATE FUNCTION dation_private.j102_append(wid uuid,cid uuid,uid uuid,d jsonb,mid uuid) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE previous dation_private.case_definition_revisions;
BEGIN
 SELECT * INTO previous FROM dation_private.case_definition_revisions WHERE workspace_id=wid AND case_id=cid ORDER BY revision DESC LIMIT 1;
 IF FOUND AND previous.snapshot=d THEN RETURN; END IF;
 INSERT INTO dation_private.case_definition_revisions(workspace_id,case_id,revision,mutation_id,prior_revision_id,snapshot,definition_hash,actor_user_id)
 VALUES(wid,cid,coalesce(previous.revision,0)+1,mid,previous.id,d,
  encode(sha256(convert_to(dation_private.t8_canonical(d),'UTF8')),'hex'),uid);
END $$;

ALTER FUNCTION dation_private.t3_case_context(public.decision_cases,uuid) RENAME TO j102_legacy_case_context;
CREATE FUNCTION dation_private.t3_case_context(c public.decision_cases,uid uuid) RETURNS jsonb
LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE result jsonb; def jsonb;
BEGIN
 result=dation_private.j102_legacy_case_context(c,uid);
 SELECT to_jsonb(r) INTO def FROM dation_private.case_definition_revisions r WHERE workspace_id=c.workspace_id AND case_id=c.id ORDER BY revision DESC LIMIT 1;
 RETURN CASE WHEN def IS NULL THEN result ELSE result||jsonb_build_object('case_definition',def) END;
END $$;

-- Capture allowed metadata edits even through older authorized APIs. Frozen
-- snapshots are never updated, and unrelated freeze/activity updates add none.
CREATE FUNCTION dation_private.j102_capture_case() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE previous dation_private.case_definition_revisions; d jsonb; uid uuid; mid uuid;
BEGIN
 SELECT * INTO previous FROM dation_private.case_definition_revisions WHERE workspace_id=NEW.workspace_id AND case_id=NEW.id ORDER BY revision DESC LIMIT 1;
 IF NOT FOUND THEN RETURN NEW; END IF;
 d=coalesce(nullif(current_setting('dation.j102_definition',true),'')::jsonb,previous.snapshot);
 d=jsonb_set(d,'{identity}',jsonb_build_object('name',NEW.label,'description',NEW.description));
 d=jsonb_set(d,'{decision_context}',jsonb_build_object('planning_start',NEW.planning_start,'planning_end',NEW.planning_end,'horizon_type',NEW.horizon_type,'operating_mode',NEW.operating_mode));
 d=jsonb_set(d,'{case_policy}',NEW.case_policy_jsonb);
 IF d=previous.snapshot THEN RETURN NEW; END IF;
 IF (d-'identity') IS DISTINCT FROM (previous.snapshot-'identity') AND coalesce(current_setting('dation.j102_write',true),'')<>'on' THEN
  RAISE EXCEPTION 'Use versioned definition update' USING ERRCODE='55006'; END IF;
 IF NEW.context_frozen_at IS NOT NULL AND (d-'identity') IS DISTINCT FROM (previous.snapshot-'identity') THEN
  RAISE EXCEPTION 'Frozen definition requires a derived Case' USING ERRCODE='22023'; END IF;
 uid=nullif(current_setting('dation.actor_user_id',true),'')::uuid;
 IF uid IS NULL THEN uid=(nullif(current_setting('request.headers',true),'')::jsonb->>'x-dation-actor-id')::uuid; END IF;
 IF uid IS NULL OR dation_private.team_actor(NEW.workspace_id,uid)='viewer' THEN RAISE EXCEPTION 'Definition actor required' USING ERRCODE='42501'; END IF;
 mid=coalesce(nullif(current_setting('dation.j102_mutation',true),'')::uuid,gen_random_uuid());
 PERFORM dation_private.j102_append(NEW.workspace_id,NEW.id,uid,d,mid);
 RETURN NEW;
END $$;
CREATE TRIGGER j102_capture_case AFTER UPDATE ON public.decision_cases FOR EACH ROW EXECUTE FUNCTION dation_private.j102_capture_case();

ALTER FUNCTION public.platform_ultimate_foundation(uuid,uuid,text,jsonb) RENAME TO j102_foundation_legacy;
ALTER FUNCTION public.j102_foundation_legacy(uuid,uuid,text,jsonb) SET SCHEMA dation_private;
CREATE FUNCTION public.platform_ultimate_foundation(target_workspace_id uuid,actor_user_id uuid,operation text,arguments jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb; caps jsonb; d jsonb; c public.decision_cases; flags dation_private.platform_release;
BEGIN
 caps=dation_private.j102_foundation_legacy(target_workspace_id,actor_user_id,'capabilities','{}');
 SELECT * INTO flags FROM dation_private.platform_release WHERE singleton;
 IF operation='capabilities' THEN RETURN caps||jsonb_build_object('decision_case_v2_schema_available',true,
  'decision_case_v2_write_enabled',flags.j102_enabled AND coalesce((caps->>'enabled')::boolean,false) AND flags.unified_journey_enabled AND flags.ultimate_data_pack_enabled); END IF;
 IF operation='case_create' AND arguments->'definition_v2' IS NOT NULL AND arguments->'definition_v2'<>'null'::jsonb THEN
  IF NOT flags.j102_enabled THEN RAISE EXCEPTION 'J1.02 creation closed' USING ERRCODE='42501'; END IF;
  d=arguments->'definition_v2';PERFORM dation_private.j102_check_binding(target_workspace_id,actor_user_id,d,
    NOT EXISTS(SELECT 1 FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=(arguments->>'id')::uuid));
  IF NOT coalesce((caps->>'can_create_case')::boolean,false) THEN RAISE EXCEPTION 'Case creation denied' USING ERRCODE='42501'; END IF;
  IF NOT EXISTS(SELECT 1 FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=(arguments->>'id')::uuid) AND
   NOT EXISTS(SELECT 1 FROM dation_private.journey_preparations p WHERE p.workspace_id=target_workspace_id AND p.created_by=actor_user_id
    AND p.status='FINALIZING' AND p.model_version_id=(arguments->>'logistics_model_version_id')::uuid
    AND p.creation_body->>'id'=arguments->>'id' AND p.creation_body->'definition_v2'=d
    AND (SELECT count(*) FROM dation_private.journey_uploads u WHERE u.preparation_id=p.id AND u.selected AND u.ready)=dation_private.saga10_required_slot_count(p.model_version_id)) THEN
   RAISE EXCEPTION 'A validated exact preparation intent is required' USING ERRCODE='55006'; END IF;
  IF (d#>>'{provenance,parent_case_id}')::uuid=(arguments->>'id')::uuid OR
   (arguments->>'name') IS DISTINCT FROM d#>>'{identity,name}' OR (arguments->>'description') IS DISTINCT FROM d#>>'{identity,description}' OR
   arguments->'case_policy' IS DISTINCT FROM d->'case_policy' OR arguments->>'logistics_model_version_id' IS DISTINCT FROM d#>>'{model_binding,model_version_id}' OR
   EXISTS(SELECT 1 FROM jsonb_each(d->'decision_context') x WHERE arguments->x.key IS DISTINCT FROM x.value) THEN RAISE EXCEPTION 'Definition intent changed' USING ERRCODE='55006'; END IF;
 END IF;
 result=dation_private.j102_foundation_legacy(target_workspace_id,actor_user_id,operation,arguments);
 IF operation='case_create' AND d IS NOT NULL THEN
  IF EXISTS(SELECT 1 FROM dation_private.case_definition_revisions WHERE workspace_id=target_workspace_id AND case_id=(arguments->>'id')::uuid) THEN
   IF NOT EXISTS(SELECT 1 FROM dation_private.case_definition_revisions WHERE workspace_id=target_workspace_id AND case_id=(arguments->>'id')::uuid AND revision=1 AND snapshot=d) THEN RAISE EXCEPTION 'Definition intent changed' USING ERRCODE='55006'; END IF;
  ELSE PERFORM dation_private.j102_append(target_workspace_id,(arguments->>'id')::uuid,actor_user_id,d,(arguments->>'id')::uuid); END IF;
  SELECT * INTO c FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=(arguments->>'id')::uuid;
  result=dation_private.t3_case_context(c,actor_user_id);
 END IF;
 RETURN result;
END $$;

CREATE FUNCTION public.platform_decision_case_v2(target_workspace_id uuid,actor_user_id uuid,operation text,arguments jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c public.decision_cases; previous dation_private.case_definition_revisions; replay dation_private.case_definition_revisions;
 d jsonb; changes jsonb; result jsonb; role_name text; total bigint; n integer; off integer;
BEGIN
 role_name=dation_private.team_actor(target_workspace_id,actor_user_id);
 IF NOT EXISTS(SELECT 1 FROM public.workspace_ddas WHERE workspace_id=target_workspace_id AND dda_id='logistics' AND status='enabled') THEN RAISE EXCEPTION 'DDA access denied' USING ERRCODE='42501'; END IF;
 IF operation='validate' THEN
  IF NOT coalesce((public.platform_ultimate_foundation(target_workspace_id,actor_user_id,'capabilities','{}')->>'decision_case_v2_write_enabled')::boolean,false) OR role_name='viewer' THEN RAISE EXCEPTION 'J1.02 writes closed' USING ERRCODE='42501'; END IF;
  PERFORM dation_private.j102_check_binding(target_workspace_id,actor_user_id,arguments->'definition_v2',true);
  RETURN jsonb_build_object('valid',true,'definition_hash',encode(sha256(convert_to(dation_private.t8_canonical(arguments->'definition_v2'),'UTF8')),'hex'));
 END IF;
 IF operation='projection' THEN
  IF jsonb_array_length(arguments->'case_ids')>50 THEN RAISE EXCEPTION 'Page too large' USING ERRCODE='22023'; END IF;
  SELECT coalesce(jsonb_object_agg(listed.id,jsonb_build_object('model_id',m.id,'model_name',m.name,'model_version_id',v.id,'model_version',v.version,
    'planning_start',listed.planning_start,'planning_end',listed.planning_end,'horizon_type',listed.horizon_type,'operating_mode',listed.operating_mode,'case_policy',listed.case_policy_jsonb,
    'context_frozen_at',listed.context_frozen_at,'case_definition',def.body)),'{}') INTO result
  FROM public.decision_cases listed LEFT JOIN public.logistics_model_versions v ON v.workspace_id=listed.workspace_id AND v.id=listed.logistics_model_version_id
  LEFT JOIN public.logistics_models m ON m.workspace_id=v.workspace_id AND m.id=v.model_id
  LEFT JOIN LATERAL(SELECT to_jsonb(r) body FROM dation_private.case_definition_revisions r WHERE r.workspace_id=listed.workspace_id AND r.case_id=listed.id ORDER BY revision DESC LIMIT 1) def ON true
  WHERE listed.workspace_id=target_workspace_id AND listed.id IN(SELECT x::uuid FROM jsonb_array_elements_text(arguments->'case_ids') x);
  RETURN result;
 END IF;
 SELECT * INTO c FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=(arguments->>'case_id')::uuid;
 IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
 IF operation='run_context' THEN
  SELECT jsonb_build_object('id',r.id,'node_id',r.node_id,'status',r.status,'result_fingerprint',r.result_fingerprint,'upstream_run_id',r.upstream_run_id,
   'data_pack_version_id',r.data_pack_version_id,'logistics_model_version_id',r.logistics_model_version_id,
   'definition_binding',r.configuration_json#>'{frozen_context,decision_definition}') INTO result
   FROM public.decision_runs r WHERE r.workspace_id=c.workspace_id AND r.decision_case_id=c.id AND r.id=(arguments->>'run_id')::uuid;
  IF result IS NULL THEN RAISE EXCEPTION 'Run not found in Case' USING ERRCODE='P0002'; END IF;
  RETURN result;
 END IF;
 IF operation='history' THEN
  n=coalesce((arguments->>'limit')::integer,25);off=coalesce((arguments->>'offset')::integer,0);
  IF n NOT BETWEEN 1 AND 50 OR off NOT BETWEEN 0 AND 1000000 THEN RAISE EXCEPTION 'Invalid page' USING ERRCODE='22023'; END IF;
  SELECT count(*) INTO total FROM dation_private.case_definition_revisions WHERE workspace_id=c.workspace_id AND case_id=c.id;
  SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY revision DESC),'[]') INTO result FROM
   (SELECT * FROM dation_private.case_definition_revisions WHERE workspace_id=c.workspace_id AND case_id=c.id ORDER BY revision DESC LIMIT n OFFSET off) x;
  RETURN jsonb_build_object('items',result,'total',total,'limit',n,'offset',off,'legacy',total=0);
 END IF;
 IF operation='revision' THEN
  SELECT to_jsonb(r) INTO result FROM dation_private.case_definition_revisions r WHERE workspace_id=c.workspace_id AND case_id=c.id AND id=(arguments->>'revision_id')::uuid;
  IF result IS NULL THEN RAISE EXCEPTION 'Definition not found' USING ERRCODE='P0002'; END IF;RETURN result;
 END IF;
 IF operation<>'update' THEN RAISE EXCEPTION 'Invalid definition operation' USING ERRCODE='22023'; END IF;
 PERFORM 1 FROM public.workspaces WHERE id=target_workspace_id FOR UPDATE;
 SELECT * INTO c FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=c.id FOR UPDATE;
 IF role_name='viewer' OR NOT coalesce((public.platform_ultimate_foundation(target_workspace_id,actor_user_id,'capabilities','{}')->>'decision_case_v2_write_enabled')::boolean,false) THEN RAISE EXCEPTION 'J1.02 writes closed' USING ERRCODE='42501'; END IF;
 d=arguments->'definition_v2';PERFORM dation_private.j102_check_binding(target_workspace_id,actor_user_id,d,false);
 SELECT * INTO replay FROM dation_private.case_definition_revisions WHERE workspace_id=c.workspace_id AND case_id=c.id AND mutation_id=(arguments->>'mutation_id')::uuid;
 IF FOUND THEN
  IF replay.snapshot<>d THEN RAISE EXCEPTION 'Mutation identity reused' USING ERRCODE='55006'; END IF;
  RETURN dation_private.t3_case_context(c,actor_user_id);
 END IF;
 SELECT * INTO previous FROM dation_private.case_definition_revisions WHERE workspace_id=c.workspace_id AND case_id=c.id ORDER BY revision DESC LIMIT 1;
 IF NOT FOUND OR previous.revision IS DISTINCT FROM (arguments->>'expected_revision')::bigint OR c.updated_at IS DISTINCT FROM (arguments->>'expected_updated_at')::timestamptz THEN RAISE EXCEPTION 'Definition changed' USING ERRCODE='55006'; END IF;
 IF d->'model_binding' IS DISTINCT FROM previous.snapshot->'model_binding' OR d->'provenance' IS DISTINCT FROM previous.snapshot->'provenance' OR d->'case_work_id' IS DISTINCT FROM previous.snapshot->'case_work_id' THEN RAISE EXCEPTION 'Model/origin identity is pinned' USING ERRCODE='22023'; END IF;
 IF (c.context_frozen_at IS NOT NULL OR EXISTS(SELECT 1 FROM public.decision_runs WHERE workspace_id=c.workspace_id AND decision_case_id=c.id)) AND d-'identity' IS DISTINCT FROM previous.snapshot-'identity' THEN RAISE EXCEPTION 'Derive a new Case for mathematical changes' USING ERRCODE='22023'; END IF;
 changes=jsonb_build_object('name',d#>>'{identity,name}','description',d#>>'{identity,description}')||(d->'decision_context')||jsonb_build_object('case_policy',d->'case_policy','case_policy_hash',arguments->>'case_policy_hash');
 PERFORM set_config('dation.j102_write','on',true);PERFORM set_config('dation.j102_definition',d::text,true);PERFORM set_config('dation.j102_mutation',arguments->>'mutation_id',true);
 result=public.platform_ultimate_foundation(target_workspace_id,actor_user_id,'case_update',jsonb_build_object('case_id',c.id,'expected_updated_at',arguments->>'expected_updated_at','changes',changes,'owner_updates',coalesce(arguments->'owner_updates','[]')));
 RETURN result;
END $$;

-- Pin the additive policy at real admission, including D2's exact approved D1
-- definition. Worker completion/draining is delegated unchanged.
ALTER FUNCTION public.platform_ultimate_execution(uuid,uuid,text,jsonb) RENAME TO j102_execution_legacy;
ALTER FUNCTION public.j102_execution_legacy(uuid,uuid,text,jsonb) SET SCHEMA dation_private;
CREATE FUNCTION public.platform_ultimate_execution(target_workspace_id uuid,actor_user_id uuid,operation text,arguments jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r dation_private.case_definition_revisions; expected jsonb; source public.decision_runs; cid uuid;
BEGIN
 IF operation='admit' THEN
  PERFORM dation_private.team_actor(target_workspace_id,actor_user_id);
  PERFORM 1 FROM public.workspaces WHERE id=target_workspace_id FOR UPDATE;
  cid=(arguments->>'case_id')::uuid;
  SELECT * INTO r FROM dation_private.case_definition_revisions WHERE workspace_id=target_workspace_id AND case_id=cid ORDER BY revision DESC LIMIT 1;
  IF FOUND THEN
   IF NOT (SELECT j102_enabled FROM dation_private.platform_release WHERE singleton) THEN RAISE EXCEPTION 'J1.02 admissions closed' USING ERRCODE='42501'; END IF;
   expected=jsonb_build_object('definition_revision_id',r.id,'definition_hash',r.definition_hash,'business_rules',r.snapshot->'business_rules','acceptance_policy',r.snapshot->'acceptance_policy');
   IF arguments#>>'{client_request,node_id}'='logistics_scheduling' THEN
    SELECT * INTO source FROM public.decision_runs WHERE workspace_id=target_workspace_id AND decision_case_id=cid AND node_id='logistics_assignment'
      AND id=(arguments#>>'{input,source_transport_plan,run_id}')::uuid AND approved_at IS NOT NULL AND superseded_at IS NULL;
    IF NOT FOUND OR source.configuration_json#>'{frozen_context,decision_definition}' IS NULL THEN RAISE EXCEPTION 'Exact approved D1 definition required' USING ERRCODE='55006'; END IF;
    expected=source.configuration_json#>'{frozen_context,decision_definition}';
    IF expected->'business_rules' IS DISTINCT FROM r.snapshot->'business_rules' OR expected->'acceptance_policy' IS DISTINCT FROM r.snapshot->'acceptance_policy' THEN RAISE EXCEPTION 'Upstream policy differs' USING ERRCODE='55006'; END IF;
   END IF;
  END IF;
  IF arguments#>'{input,context,decision_definition}' IS DISTINCT FROM expected THEN RAISE EXCEPTION 'Definition binding differs' USING ERRCODE='55006'; END IF;
 END IF;
 RETURN dation_private.j102_execution_legacy(target_workspace_id,actor_user_id,operation,arguments);
END $$;
REVOKE ALL ON FUNCTION dation_private.j102_execution_legacy(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_ultimate_execution(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_ultimate_execution(uuid,uuid,text,jsonb) TO service_role;

REVOKE ALL ON FUNCTION dation_private.j102_valid(jsonb),dation_private.j102_check_binding(uuid,uuid,jsonb,boolean),
 dation_private.j102_append(uuid,uuid,uuid,jsonb,uuid),dation_private.j102_legacy_case_context(public.decision_cases,uuid),dation_private.t3_case_context(public.decision_cases,uuid),
 dation_private.j102_capture_case(),dation_private.j102_foundation_legacy(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_ultimate_foundation(uuid,uuid,text,jsonb),public.platform_decision_case_v2(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_ultimate_foundation(uuid,uuid,text,jsonb),public.platform_decision_case_v2(uuid,uuid,text,jsonb) TO service_role;
COMMIT;
