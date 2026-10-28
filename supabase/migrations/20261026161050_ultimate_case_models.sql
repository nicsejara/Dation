-- T3 only: checked Model/Case setup and first-admission context freeze.
-- No admissions, Pack publishing, graph resolver, engines or release activation.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';

ALTER TABLE dation_private.platform_release ADD COLUMN ultimate_foundation_enabled boolean NOT NULL DEFAULT false;
ALTER TABLE public.logistics_models
 ADD COLUMN draft_config_jsonb jsonb CHECK(draft_config_jsonb IS NULL OR jsonb_typeof(draft_config_jsonb)='object'),
 ADD COLUMN draft_config_hash text CHECK(draft_config_hash ~ '^[0-9a-f]{64}$'),
 ADD COLUMN creation_intent_hash text CHECK(creation_intent_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE public.logistics_model_versions ADD COLUMN source_model_revision bigint CHECK(source_model_revision>0);
ALTER TABLE public.decision_cases
 ADD COLUMN horizon_type text CHECK(horizon_type IN('DAILY','WEEKLY','MONTHLY','CUSTOM')),
 ADD COLUMN creation_intent_hash text CHECK(creation_intent_hash ~ '^[0-9a-f]{64}$');

-- Release-controlled structural reference for Model bindings, not a state resolver.
-- T1 fixture graph identities remain untouched. New execution capabilities stay off.
INSERT INTO dation_private.decision_definition_versions(version,definition_hash,definition_jsonb)
VALUES('ULTIMATE_FOUNDATION_V1','723c6fe85946adf7108492251451722f2100b7e7aeecb887e78da3d952f9786f',
 '{"schema_version":"decision_definition_reference_v1","version":"ULTIMATE_FOUNDATION_V1","node_ids":["logistics_assignment","logistics_scheduling"],"domain_contract_registry_version":"ULTIMATE_DOMAIN_V1","execution_available":false}');

CREATE FUNCTION dation_private.t3_configuration_valid(value jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE key text; arr jsonb;
BEGIN
 IF jsonb_typeof(value) IS DISTINCT FROM 'object' OR value->>'version' IS DISTINCT FROM '1' OR jsonb_typeof(value->'version') IS DISTINCT FROM 'number'
 OR NOT value ?& ARRAY['version','operating_role','transport_pattern','allowed_sources','active_dimensions','primary_dimension',
   'split_permitted','homogeneous_loads_declared','currency_policy','own_cost_model','external_cost_models','per_km_billing_bases']
 OR value-ARRAY['version','operating_role','transport_pattern','allowed_sources','active_dimensions','primary_dimension',
   'split_permitted','homogeneous_loads_declared','currency_policy','own_cost_model','external_cost_models','per_km_billing_bases']<>'{}'
 OR coalesce(value->>'operating_role','') NOT IN('SHIPPER','LOGISTICS_PROVIDER','HYBRID')
 OR value->>'transport_pattern' IS DISTINCT FROM 'DIRECT' OR value->>'own_cost_model' IS DISTINCT FROM 'OWN_OPERATING_CYCLE'
 OR jsonb_typeof(value->'split_permitted') IS DISTINCT FROM 'boolean'
 OR jsonb_typeof(value->'homogeneous_loads_declared') IS DISTINCT FROM 'boolean' THEN RETURN false; END IF;
 FOREACH key IN ARRAY ARRAY['allowed_sources','active_dimensions','external_cost_models','per_km_billing_bases'] LOOP
  arr=value->key;
  IF jsonb_typeof(arr) IS DISTINCT FROM 'array' OR jsonb_array_length(arr)>4
   OR (SELECT count(*)<>count(DISTINCT x) FROM jsonb_array_elements_text(arr) x) THEN RETURN false; END IF;
 END LOOP;
 IF jsonb_array_length(value->'allowed_sources')=0 OR jsonb_array_length(value->'active_dimensions')=0
 OR EXISTS(SELECT 1 FROM jsonb_array_elements_text(value->'allowed_sources') x WHERE x IS NULL OR x NOT IN('OWN','EXTERNAL'))
 OR EXISTS(SELECT 1 FROM jsonb_array_elements_text(value->'active_dimensions') x WHERE x IS NULL OR x NOT IN('pallets','weight_kg','volume_m3','units'))
 OR NOT (value->'active_dimensions') ? coalesce(value->>'primary_dimension','')
 OR EXISTS(SELECT 1 FROM jsonb_array_elements_text(value->'external_cost_models') x WHERE x IS NULL OR x NOT IN('PER_TRIP','PER_KM'))
 OR EXISTS(SELECT 1 FROM jsonb_array_elements_text(value->'per_km_billing_bases') x WHERE x IS NULL OR x NOT IN('ONE_WAY','ROUND_TRIP'))
 OR ((value->'allowed_sources') ? 'EXTERNAL' AND jsonb_array_length(value->'external_cost_models')=0)
 OR ((value->'external_cost_models') ? 'PER_KM' AND jsonb_array_length(value->'per_km_billing_bases')=0) THEN RETURN false; END IF;
 arr=value->'currency_policy';
 RETURN coalesce(jsonb_typeof(arr)='object' AND arr ?& ARRAY['currency','minor_units','rounding']
  AND arr-ARRAY['currency','minor_units','rounding']='{}' AND arr->>'currency' ~ '^[A-Z]{3}$'
  AND jsonb_typeof(arr->'minor_units')='number' AND arr->>'minor_units' ~ '^[0-6]$'
  AND arr->>'rounding'='ROUND_HALF_UP',false);
END; $$;

CREATE FUNCTION dation_private.t3_policy_valid(value jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE item jsonb; total numeric=0;
BEGIN
 IF jsonb_typeof(value) IS DISTINCT FROM 'object' OR value->>'version' IS DISTINCT FROM '1' OR jsonb_typeof(value->'version') IS DISTINCT FROM 'number'
 OR NOT value ?& ARRAY['version','primary_goal','guardrails','preferences']
 OR value-ARRAY['version','primary_goal','guardrails','preferences']<>'{}'
 OR coalesce(value->>'primary_goal','') NOT IN('MINIMIZE_COST','MAXIMIZE_SERVICE','MAXIMIZE_OWN_CAPACITY','MINIMIZE_TRIPS','BALANCED','CUSTOM')
 OR jsonb_typeof(value->'guardrails') IS DISTINCT FROM 'array' OR jsonb_typeof(value->'preferences') IS DISTINCT FROM 'array'
 THEN RETURN false; END IF;
 IF jsonb_array_length(value->'guardrails')>4 OR jsonb_array_length(value->'preferences')>4 THEN RETURN false; END IF;
 FOR item IN SELECT x FROM jsonb_array_elements(value->'guardrails') x LOOP
  IF NOT item ?& ARRAY['kind','limit','hard'] OR item-ARRAY['kind','limit','hard']<>'{}'
   OR coalesce(item->>'kind','') NOT IN('MINIMUM_DEMAND_COVERAGE','CRITICAL_DEMAND_COVERAGE','MAXIMUM_EXTERNAL_SHARE','MINIMUM_OWN_SHARE')
   OR item->'hard' IS DISTINCT FROM 'true'::jsonb OR coalesce(item->>'limit','') !~ '^(0(\.[0-9]{1,4})?|1(\.0{1,4})?)$' THEN RETURN false; END IF;
 END LOOP;
 FOR item IN SELECT x FROM jsonb_array_elements(value->'preferences') x LOOP
  IF NOT item ?& ARRAY['kind','weight'] OR item-ARRAY['kind','weight']<>'{}'
   OR coalesce(item->>'kind','') NOT IN('COST','TRIPS','SERVICE','OWN_CAPACITY')
   OR coalesce(item->>'weight','') !~ '^(0(\.[0-9]{1,4})?|1(\.0{1,4})?)$' THEN RETURN false; END IF;
  total=total+(item->>'weight')::numeric;
 END LOOP;
 RETURN (SELECT count(*)=count(DISTINCT x->>'kind') FROM jsonb_array_elements(value->'guardrails') x)
  AND (SELECT count(*)=count(DISTINCT x->>'kind') FROM jsonb_array_elements(value->'preferences') x)
  AND (jsonb_array_length(value->'preferences')=0 OR total=1)
  AND (value->>'primary_goal'<>'CUSTOM' OR jsonb_array_length(value->'preferences')>0);
END; $$;

CREATE FUNCTION dation_private.t3_case_context(c public.decision_cases,uid uuid) RETURNS jsonb
LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE role_name text; enabled boolean;
BEGIN
 role_name=dation_private.team_actor(c.workspace_id,uid);
 SELECT ultimate_foundation_enabled INTO enabled FROM dation_private.platform_release WHERE singleton;
 RETURN jsonb_build_object('case',to_jsonb(c),'model_version',(SELECT to_jsonb(v) FROM public.logistics_model_versions v WHERE v.workspace_id=c.workspace_id AND v.id=c.logistics_model_version_id),
  'model',(SELECT to_jsonb(m)-'draft_config_jsonb' FROM public.logistics_models m JOIN public.logistics_model_versions v ON v.workspace_id=m.workspace_id AND v.model_id=m.id WHERE v.workspace_id=c.workspace_id AND v.id=c.logistics_model_version_id),
  'pack',(SELECT to_jsonb(p) FROM public.case_data_packs p WHERE p.workspace_id=c.workspace_id AND p.case_id=c.id),
  'pack_version',(SELECT to_jsonb(v)-'created_xid' FROM public.case_data_packs p JOIN public.case_data_pack_versions v ON v.workspace_id=p.workspace_id AND v.case_id=p.case_id AND v.pack_id=p.id AND v.id=p.current_version_id WHERE p.workspace_id=c.workspace_id AND p.case_id=c.id),
  'entry_count',(SELECT count(*) FROM public.case_data_pack_entries e JOIN public.case_data_packs p ON p.workspace_id=e.workspace_id AND p.case_id=e.case_id AND p.current_version_id=e.pack_version_id WHERE p.workspace_id=c.workspace_id AND p.case_id=c.id),
  'responsibilities',public.platform_workflow_responsibilities(c.workspace_id,uid,c.id),
  'permissions',jsonb_build_object('can_edit',enabled AND role_name IN('admin','operator') AND c.status<>'archived',
   'can_assign',enabled AND role_name='admin' AND c.status<>'archived',
   'can_edit_mathematical',enabled AND role_name IN('admin','operator') AND c.status<>'archived' AND c.context_frozen_at IS NULL
    AND NOT EXISTS(SELECT 1 FROM public.decision_runs WHERE workspace_id=c.workspace_id AND decision_case_id=c.id)));
END; $$;

CREATE FUNCTION public.platform_ultimate_foundation(target_workspace_id uuid,actor_user_id uuid,operation text,arguments jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE role_name text; enabled boolean; dda boolean; m public.logistics_models; v public.logistics_model_versions;
 c public.decision_cases; item jsonb; changes jsonb; owner_id uuid; expected_stamp timestamptz; target uuid;
 page_limit integer; page_offset integer; search_text text; result jsonb;
BEGIN
 role_name=dation_private.team_actor(target_workspace_id,actor_user_id);
 SELECT ultimate_foundation_enabled INTO enabled FROM dation_private.platform_release WHERE singleton;
 SELECT EXISTS(SELECT 1 FROM public.workspace_ddas WHERE workspace_id=target_workspace_id AND dda_id='logistics' AND status='enabled') INTO dda;
 IF operation='capabilities' THEN RETURN jsonb_build_object('enabled',enabled AND dda,'can_create_case',enabled AND dda AND role_name IN('admin','operator'),
  'can_manage_models',enabled AND dda AND role_name='admin','can_assign',enabled AND dda AND role_name='admin','runtime_execution_available',false); END IF;
 IF NOT dda THEN RAISE EXCEPTION 'DDA access denied' USING ERRCODE='42501'; END IF;
 IF operation IS NULL OR operation NOT IN('model_list','model_get','model_create','model_update','model_publish','case_get','case_create','case_update')
  OR jsonb_typeof(arguments) IS DISTINCT FROM 'object' OR octet_length(arguments::text)>524288 THEN
  RAISE EXCEPTION 'Invalid foundation operation' USING ERRCODE='22023'; END IF;
 IF operation IN('model_create','model_update','model_publish','case_create','case_update') THEN
  PERFORM 1 FROM public.workspaces WHERE id=target_workspace_id FOR UPDATE;
  role_name=dation_private.team_actor(target_workspace_id,actor_user_id,operation IN('model_create','model_update','model_publish'));
  SELECT ultimate_foundation_enabled INTO enabled FROM dation_private.platform_release WHERE singleton;
  IF NOT EXISTS(SELECT 1 FROM public.workspace_ddas WHERE workspace_id=target_workspace_id AND dda_id='logistics' AND status='enabled') THEN RAISE EXCEPTION 'DDA access denied' USING ERRCODE='42501'; END IF;
  IF role_name='viewer' THEN RAISE EXCEPTION 'Read-only membership' USING ERRCODE='42501'; END IF;
  IF NOT enabled THEN RAISE EXCEPTION 'Ultimate creation is closed' USING ERRCODE='P0002'; END IF;
  PERFORM set_config('dation.workspace_id',target_workspace_id::text,true);
  PERFORM set_config('dation.actor_user_id',actor_user_id::text,true);
 END IF;

 IF operation='model_list' THEN
  page_limit=coalesce((arguments->>'limit')::integer,25);page_offset=coalesce((arguments->>'offset')::integer,0);search_text=coalesce(arguments->>'search_text','');
  IF page_limit NOT BETWEEN 1 AND 50 OR page_offset NOT BETWEEN 0 AND 1000000 OR length(search_text)>120 THEN RAISE EXCEPTION 'Invalid page' USING ERRCODE='22023'; END IF;
  WITH matched AS (SELECT * FROM public.logistics_models WHERE workspace_id=target_workspace_id
   AND (coalesce((arguments->>'include_archived')::boolean,false) OR status='active')
   AND (search_text='' OR strpos(lower(name),lower(search_text))>0)),
  page AS (SELECT * FROM matched ORDER BY updated_at DESC,id LIMIT page_limit OFFSET page_offset)
  SELECT jsonb_build_object('items',coalesce((SELECT jsonb_agg(to_jsonb(p)-'draft_config_jsonb'||jsonb_build_object('versions',
    (SELECT coalesce(jsonb_agg(jsonb_build_object('id',vv.id,'version',vv.version,'published_at',vv.published_at) ORDER BY vv.version DESC),'[]') FROM public.logistics_model_versions vv WHERE vv.workspace_id=p.workspace_id AND vv.model_id=p.id)) ORDER BY p.updated_at DESC,p.id) FROM page p),'[]'),
   'total',(SELECT count(*) FROM matched),'limit',page_limit,'offset',page_offset) INTO result;
  RETURN result;
 END IF;

 IF operation IN('model_get','model_update','model_publish') THEN
  SELECT * INTO m FROM public.logistics_models WHERE workspace_id=target_workspace_id AND id=(arguments->>'model_id')::uuid;
  IF NOT FOUND THEN RAISE EXCEPTION 'Model not found' USING ERRCODE='P0002'; END IF;
 END IF;
 IF operation='model_create' THEN
  target=(arguments->>'id')::uuid;
  SELECT * INTO m FROM public.logistics_models WHERE id=target;
  IF FOUND THEN
   IF m.workspace_id<>target_workspace_id THEN RAISE EXCEPTION 'Model not found' USING ERRCODE='P0002'; END IF;
   IF m.creation_intent_hash IS DISTINCT FROM arguments->>'creation_intent_hash' THEN RAISE EXCEPTION 'Creation intent changed' USING ERRCODE='55006'; END IF;
  ELSE
   IF NOT dation_private.t3_configuration_valid(arguments->'configuration') OR coalesce(arguments->>'configuration_hash','') !~ '^[0-9a-f]{64}$'
    OR coalesce(arguments->>'creation_intent_hash','') !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'Invalid Model configuration' USING ERRCODE='22023'; END IF;
   INSERT INTO public.logistics_models(id,workspace_id,name,description,created_by,draft_config_jsonb,draft_config_hash,creation_intent_hash)
   VALUES(target,target_workspace_id,arguments->>'name',arguments->>'description',actor_user_id,arguments->'configuration',arguments->>'configuration_hash',arguments->>'creation_intent_hash') RETURNING * INTO m;
   INSERT INTO public.audit_events(workspace_id,actor_user_id,event_type,object_type,object_id) VALUES(target_workspace_id,actor_user_id,'logistics_model.created','logistics_model',m.id);
  END IF;
 ELSIF operation='model_update' THEN
  IF m.revision IS DISTINCT FROM (arguments->>'expected_revision')::bigint THEN RAISE EXCEPTION 'Model changed' USING ERRCODE='55006'; END IF;
  IF NOT dation_private.t3_configuration_valid(arguments->'configuration') OR coalesce(arguments->>'configuration_hash','') !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'Invalid Model configuration' USING ERRCODE='22023'; END IF;
  UPDATE public.logistics_models SET name=arguments->>'name',description=arguments->>'description',status=arguments->>'status',draft_config_jsonb=arguments->'configuration',
   draft_config_hash=arguments->>'configuration_hash',revision=revision+1,updated_at=clock_timestamp() WHERE id=m.id AND workspace_id=target_workspace_id RETURNING * INTO m;
  INSERT INTO public.audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,metadata_json) VALUES(target_workspace_id,actor_user_id,'logistics_model.updated','logistics_model',m.id,jsonb_build_object('revision',m.revision));
 ELSIF operation='model_publish' THEN
  SELECT * INTO v FROM public.logistics_model_versions WHERE id=(arguments->>'version_id')::uuid;
  IF FOUND THEN
   IF v.workspace_id<>target_workspace_id OR v.model_id<>m.id THEN RAISE EXCEPTION 'Version not found' USING ERRCODE='P0002'; END IF;
   IF v.source_model_revision IS DISTINCT FROM (arguments->>'expected_revision')::bigint THEN RAISE EXCEPTION 'Publish intent changed' USING ERRCODE='55006'; END IF;
   RETURN jsonb_build_object('version',to_jsonb(v),'model_revision',m.revision,'replayed',true);
  END IF;
  IF m.revision IS DISTINCT FROM (arguments->>'expected_revision')::bigint OR m.draft_config_hash IS DISTINCT FROM arguments->>'configuration_hash' THEN RAISE EXCEPTION 'Model changed' USING ERRCODE='55006'; END IF;
  IF m.status<>'active' OR NOT dation_private.t3_configuration_valid(m.draft_config_jsonb)
   OR coalesce(arguments->>'contract_hash','') !~ '^[0-9a-f]{64}$'
   OR arguments#>>'{contract_descriptor,schema_version}' IS DISTINCT FROM 'ultimate_model_domain_reference_v1'
   OR arguments#>>'{contract_descriptor,configuration_hash}' IS DISTINCT FROM m.draft_config_hash THEN RAISE EXCEPTION 'Invalid publication' USING ERRCODE='22023'; END IF;
  INSERT INTO public.logistics_model_versions(id,workspace_id,model_id,version,graph_definition_version,config_schema_version,config_jsonb,
   contract_descriptor_jsonb,config_hash,contract_hash,contract_registry_version,published_by,source_model_revision)
  VALUES((arguments->>'version_id')::uuid,target_workspace_id,m.id,(SELECT coalesce(max(version),0)+1 FROM public.logistics_model_versions WHERE model_id=m.id),
   'ULTIMATE_FOUNDATION_V1','logistics_model_config_v1',m.draft_config_jsonb,arguments->'contract_descriptor',m.draft_config_hash,arguments->>'contract_hash','ULTIMATE_DOMAIN_V1',actor_user_id,m.revision) RETURNING * INTO v;
  UPDATE public.logistics_models SET revision=revision+1,updated_at=clock_timestamp() WHERE id=m.id RETURNING * INTO m;
  INSERT INTO public.audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,metadata_json)
   VALUES(target_workspace_id,actor_user_id,'logistics_model.version_published','logistics_model',m.id,jsonb_build_object('version_id',v.id,'version',v.version));
  RETURN jsonb_build_object('version',to_jsonb(v),'model_revision',m.revision,'replayed',false);
 END IF;
 IF operation IN('model_get','model_create','model_update') THEN
  RETURN jsonb_build_object('model',to_jsonb(m),'versions',coalesce((SELECT jsonb_agg(to_jsonb(vv) ORDER BY vv.version DESC)
   FROM public.logistics_model_versions vv WHERE vv.workspace_id=target_workspace_id AND vv.model_id=m.id),'[]'));
 END IF;

 target=(arguments->>CASE WHEN operation='case_create' THEN 'id' ELSE 'case_id' END)::uuid;
 SELECT * INTO c FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=target;
 IF operation='case_create' THEN
  IF FOUND THEN
   IF c.workflow_version<>2 OR c.creation_intent_hash IS DISTINCT FROM arguments->>'creation_intent_hash' THEN RAISE EXCEPTION 'Creation intent changed' USING ERRCODE='55006'; END IF;
   RETURN dation_private.t3_case_context(c,actor_user_id);
  END IF;
  IF EXISTS(SELECT 1 FROM public.decision_cases WHERE id=target) THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
  SELECT * INTO v FROM public.logistics_model_versions WHERE workspace_id=target_workspace_id AND id=(arguments->>'logistics_model_version_id')::uuid;
  IF NOT FOUND THEN RAISE EXCEPTION 'Model Version not found' USING ERRCODE='P0002'; END IF;
  SELECT * INTO m FROM public.logistics_models WHERE workspace_id=target_workspace_id AND id=v.model_id;
  IF m.status<>'active' OR NOT dation_private.t3_configuration_valid(v.config_jsonb) THEN RAISE EXCEPTION 'Choose an active published Model Version' USING ERRCODE='22023'; END IF;
  IF length(coalesce(trim(arguments->>'name'),'')) NOT BETWEEN 1 AND 120
   OR NOT dation_private.t3_policy_valid(arguments->'case_policy') OR coalesce(arguments->>'case_policy_hash','') !~ '^[0-9a-f]{64}$'
   OR coalesce(arguments->>'horizon_type','') NOT IN('DAILY','WEEKLY','MONTHLY','CUSTOM')
   OR coalesce(arguments->>'creation_intent_hash','') !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'Invalid Case context' USING ERRCODE='22023'; END IF;
  owner_id=(arguments->>'decision_owner_user_id')::uuid;
  IF role_name='admin' AND owner_id IS NULL THEN RAISE EXCEPTION 'Choose a Decision Owner' USING ERRCODE='22023'; END IF;
  IF owner_id IS NOT NULL AND role_name<>'admin' THEN RAISE EXCEPTION 'Only Admin may assign owners' USING ERRCODE='42501'; END IF;
  IF owner_id IS NOT NULL AND NOT dation_private.responsibility_eligible(target_workspace_id,owner_id,'decision_owner') THEN RAISE EXCEPTION 'Owner is not eligible' USING ERRCODE='22023'; END IF;
  INSERT INTO public.decision_cases(id,workspace_id,schema_version,workflow_version,label,description,category,logistics_model_version_id,
   planning_start,planning_end,horizon_type,operating_mode,case_policy_schema_version,case_policy_jsonb,case_policy_hash,graph_definition_version,created_by_user_id,creation_intent_hash)
  VALUES(target,target_workspace_id,'decision_case_v2',2,arguments->>'name',arguments->>'description',
   CASE arguments->>'horizon_type' WHEN 'WEEKLY' THEN 'weekly' WHEN 'MONTHLY' THEN 'monthly' WHEN 'DAILY' THEN 'live_operation' ELSE 'extraordinary' END,
   v.id,(arguments->>'planning_start')::date,(arguments->>'planning_end')::date,arguments->>'horizon_type',arguments->>'operating_mode','case_policy_v1',arguments->'case_policy',arguments->>'case_policy_hash',v.graph_definition_version,actor_user_id,arguments->>'creation_intent_hash') RETURNING * INTO c;
  INSERT INTO public.case_data_packs(id,workspace_id,case_id) VALUES((arguments->>'pack_id')::uuid,target_workspace_id,c.id);
  INSERT INTO public.case_data_pack_versions(id,workspace_id,case_id,pack_id,version,manifest_hash,contract_set_hash,created_by)
   VALUES((arguments->>'pack_version_id')::uuid,target_workspace_id,c.id,(arguments->>'pack_id')::uuid,1,arguments->>'manifest_hash',arguments->>'contract_set_hash',actor_user_id);
  UPDATE public.case_data_packs SET current_version_id=(arguments->>'pack_version_id')::uuid WHERE workspace_id=target_workspace_id AND case_id=c.id;
  IF owner_id IS NOT NULL THEN
   PERFORM public.platform_assign_decision(target_workspace_id,actor_user_id,c.id,'logistics_assignment',NULL,owner_id,NULL);
   PERFORM public.platform_assign_decision(target_workspace_id,actor_user_id,c.id,'logistics_scheduling',NULL,owner_id,NULL);
  END IF;
  RETURN dation_private.t3_case_context(c,actor_user_id);
 END IF;
 IF NOT FOUND OR c.workflow_version<>2 THEN RAISE EXCEPTION 'Ultimate Case not found' USING ERRCODE='P0002'; END IF;
 IF operation='case_get' THEN RETURN dation_private.t3_case_context(c,actor_user_id); END IF;
 SELECT * INTO c FROM public.decision_cases WHERE workspace_id=target_workspace_id AND id=target FOR UPDATE;
 IF c.updated_at IS DISTINCT FROM (arguments->>'expected_updated_at')::timestamptz THEN RAISE EXCEPTION 'Case changed' USING ERRCODE='55006'; END IF;
 IF c.status='archived' THEN RAISE EXCEPTION 'Restore Case before editing' USING ERRCODE='22023'; END IF;
 changes=arguments->'changes';
 IF jsonb_typeof(changes) IS DISTINCT FROM 'object' OR changes-ARRAY['name','description','planning_start','planning_end','horizon_type','operating_mode','case_policy','case_policy_hash']<>'{}'
  OR (changes?'case_policy' AND NOT dation_private.t3_policy_valid(changes->'case_policy'))
  OR (changes?'name' AND nullif(trim(changes->>'name'),'') IS NULL)
  OR jsonb_typeof(arguments->'owner_updates') IS DISTINCT FROM 'array' OR jsonb_array_length(arguments->'owner_updates')>2 THEN
  RAISE EXCEPTION 'Invalid context update' USING ERRCODE='22023'; END IF;
 IF jsonb_array_length(arguments->'owner_updates')>0 AND role_name<>'admin' THEN RAISE EXCEPTION 'Only Admin may assign owners' USING ERRCODE='42501'; END IF;
 IF (SELECT count(*)<>count(DISTINCT x->>'node_id') FROM jsonb_array_elements(arguments->'owner_updates') x) THEN RAISE EXCEPTION 'Duplicate owner update' USING ERRCODE='22023'; END IF;
 UPDATE public.decision_cases SET label=CASE WHEN changes?'name' THEN changes->>'name' ELSE label END,
  description=CASE WHEN changes?'description' THEN changes->>'description' ELSE description END,
  planning_start=CASE WHEN changes?'planning_start' THEN (changes->>'planning_start')::date ELSE planning_start END,
  planning_end=CASE WHEN changes?'planning_end' THEN (changes->>'planning_end')::date ELSE planning_end END,
  horizon_type=CASE WHEN changes?'horizon_type' THEN changes->>'horizon_type' ELSE horizon_type END,
  operating_mode=CASE WHEN changes?'operating_mode' THEN changes->>'operating_mode' ELSE operating_mode END,
  case_policy_jsonb=CASE WHEN changes?'case_policy' THEN changes->'case_policy' ELSE case_policy_jsonb END,
  case_policy_hash=CASE WHEN changes?'case_policy' THEN changes->>'case_policy_hash' ELSE case_policy_hash END,
  updated_at=clock_timestamp(),last_activity_at=clock_timestamp()
 WHERE workspace_id=target_workspace_id AND id=c.id RETURNING * INTO c;
 FOR item IN SELECT x FROM jsonb_array_elements(arguments->'owner_updates') x LOOP
  PERFORM public.platform_assign_decision(target_workspace_id,actor_user_id,c.id,item->>'node_id',
   (item->>'expected_updated_at')::timestamptz,(item->>'owner_user_id')::uuid,NULL);
 END LOOP;
 INSERT INTO public.audit_events(workspace_id,actor_user_id,event_type,object_type,object_id,decision_case_id,metadata_json)
 VALUES(target_workspace_id,actor_user_id,'decision_case.context_updated','decision_case',c.id,c.id,
  jsonb_build_object('fields',(SELECT coalesce(jsonb_agg(k),'[]') FROM jsonb_object_keys(changes) k)));
 RETURN dation_private.t3_case_context(c,actor_user_id);
END; $$;

CREATE FUNCTION dation_private.t3_model_identity() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF ROW(NEW.id,NEW.workspace_id,NEW.created_by,NEW.created_at,NEW.creation_intent_hash)
  IS DISTINCT FROM ROW(OLD.id,OLD.workspace_id,OLD.created_by,OLD.created_at,OLD.creation_intent_hash)
  OR NEW.revision<>OLD.revision+1 THEN RAISE EXCEPTION 'Model identity/revision is immutable' USING ERRCODE='22023'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER t3_model_identity BEFORE UPDATE ON public.logistics_models FOR EACH ROW EXECUTE FUNCTION dation_private.t3_model_identity();

CREATE FUNCTION dation_private.t3_context_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF OLD.workflow_version=2 THEN
  IF NEW.creation_intent_hash IS DISTINCT FROM OLD.creation_intent_hash THEN RAISE EXCEPTION 'Creation intent is immutable' USING ERRCODE='22023'; END IF;
  IF (OLD.context_frozen_at IS NOT NULL OR EXISTS(SELECT 1 FROM public.decision_runs WHERE workspace_id=OLD.workspace_id AND decision_case_id=OLD.id))
   AND ROW(NEW.planning_start,NEW.planning_end,NEW.horizon_type,NEW.operating_mode,NEW.case_policy_jsonb,NEW.case_policy_hash)
    IS DISTINCT FROM ROW(OLD.planning_start,OLD.planning_end,OLD.horizon_type,OLD.operating_mode,OLD.case_policy_jsonb,OLD.case_policy_hash) THEN
   RAISE EXCEPTION 'El horizonte y la política están congelados desde la primera admisión.' USING ERRCODE='22023'; END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER t3_context_guard BEFORE UPDATE ON public.decision_cases FOR EACH ROW EXECUTE FUNCTION dation_private.t3_context_guard();
CREATE FUNCTION dation_private.t3_freeze_on_admission() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE c public.decision_cases;
BEGIN
 IF NEW.workflow_version<>2 THEN RETURN NEW; END IF;
 PERFORM 1 FROM public.workspaces WHERE id=NEW.workspace_id FOR UPDATE;
 SELECT * INTO c FROM public.decision_cases WHERE workspace_id=NEW.workspace_id AND id=NEW.decision_case_id FOR UPDATE;
 IF c.workflow_version=2 AND c.context_frozen_at IS NULL THEN
  UPDATE public.decision_cases SET context_frozen_at=clock_timestamp(),updated_at=clock_timestamp()
   WHERE workspace_id=c.workspace_id AND id=c.id;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER a_ultimate_context_freeze BEFORE INSERT ON public.decision_runs FOR EACH ROW EXECUTE FUNCTION dation_private.t3_freeze_on_admission();

REVOKE ALL ON FUNCTION dation_private.t3_configuration_valid(jsonb),dation_private.t3_policy_valid(jsonb),
 dation_private.t3_case_context(public.decision_cases,uuid),dation_private.t3_model_identity(),dation_private.t3_context_guard(),dation_private.t3_freeze_on_admission()
 FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_ultimate_foundation(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_ultimate_foundation(uuid,uuid,text,jsonb) TO service_role;
DO $$ DECLARE source text; BEGIN
 source=pg_get_functiondef('public.platform_home(uuid,uuid)'::regprocedure);
 IF strpos(source,'''workflow_version'',c.workflow_version')=0 THEN RAISE EXCEPTION 'Unexpected Home compatibility reader'; END IF;
 source=replace(source,'''workflow_version'',c.workflow_version',
  '''foundation_context_available'',c.workflow_version=2 AND c.creation_intent_hash IS NOT NULL,''workflow_version'',c.workflow_version');
 EXECUTE source;
END; $$;
NOTIFY pgrst,'reload schema';
COMMIT;
