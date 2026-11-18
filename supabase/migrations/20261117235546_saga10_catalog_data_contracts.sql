-- Saga 10 G3: optional OrderLines slot, scoped to explicit v2 catalog models.
-- Transactional constraint widening; no data rewrite, index removal or activation.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';
ALTER TABLE public.datasets DROP CONSTRAINT datasets_dataset_type_check,
 ADD CONSTRAINT datasets_dataset_type_check CHECK(dataset_type IN('logistics_legacy','orders','fleet','transport_demand','transport_resources','order_lines')),
 DROP CONSTRAINT ultimate_dataset_contract,
 ADD CONSTRAINT ultimate_dataset_contract CHECK(CASE WHEN dataset_type IN('transport_demand','transport_resources','order_lines') THEN
  num_nonnulls(data_contract_id,data_contract_hash,normalizer_version,canonical_sha256,sha256,schema_version)=6
   AND length(data_contract_id) BETWEEN 1 AND 128 AND length(normalizer_version) BETWEEN 1 AND 128
  ELSE num_nonnulls(data_contract_id,data_contract_hash,normalizer_version,canonical_sha256)=0 END);
ALTER TABLE public.case_data_pack_entries DROP CONSTRAINT case_data_pack_entries_slot_key_check,
 ADD CONSTRAINT case_data_pack_entries_slot_key_check CHECK(slot_key IN('transport_demand','transport_resources','order_lines','scheduling_enrichment'));
ALTER TABLE dation_private.ultimate_input_uploads DROP CONSTRAINT ultimate_input_uploads_entity_check,
 ADD CONSTRAINT ultimate_input_uploads_entity_check CHECK(entity IN('transport_demand','transport_resources','order_lines'));
ALTER TABLE dation_private.journey_uploads DROP CONSTRAINT journey_uploads_entity_check,
 ADD CONSTRAINT journey_uploads_entity_check CHECK(entity IN('transport_demand','transport_resources','order_lines'));
CREATE UNIQUE INDEX IF NOT EXISTS datasets_saga10_lines_interpretation ON public.datasets(workspace_id,dataset_type,sha256,data_contract_hash)
 WHERE dataset_type='order_lines' AND sha256 IS NOT NULL;

CREATE OR REPLACE FUNCTION dation_private.saga10_required_slot_count(mvid uuid) RETURNS integer
LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT CASE WHEN config_jsonb->>'version'='2' AND config_jsonb#>>'{cargo,input_mode}'='catalog' THEN 3 ELSE 2 END FROM public.logistics_model_versions WHERE id=mvid;
$$;
REVOKE ALL ON FUNCTION dation_private.saga10_required_slot_count(uuid) FROM PUBLIC,anon,authenticated,service_role;

-- Extend the current function bodies in place, retaining every existing tenant,
-- permission, CAS, immutable-transaction and recovery check. Exact anchors fail
-- closed if the baseline has diverged. Reapplication recognizes its own output.
DO $$ DECLARE signature text; source text; BEGIN
 FOREACH signature IN ARRAY ARRAY['dation_private.ultimate_pack_guard()',
   'dation_private.t4_entries(uuid,uuid,jsonb,jsonb)',
   'public.platform_ultimate_data_pack(uuid,uuid,text,jsonb)',
   'public.platform_decision_journey(uuid,uuid,text,jsonb)'] LOOP
  -- After the first application the public RPCs are facades; only the preserved
  -- private bodies carry the original guards and need this extension.
  IF signature='public.platform_ultimate_data_pack(uuid,uuid,text,jsonb)' AND to_regprocedure('dation_private.saga10_pack_v1(uuid,uuid,text,jsonb)') IS NOT NULL THEN CONTINUE; END IF;
  IF signature='public.platform_decision_journey(uuid,uuid,text,jsonb)' AND to_regprocedure('dation_private.saga10_journey_v1(uuid,uuid,text,jsonb)') IS NOT NULL THEN CONTINUE; END IF;
  SELECT pg_get_functiondef(signature::regprocedure) INTO source;
  IF position('''order_lines''' IN source)>0 THEN CONTINUE; END IF;
  IF position('''transport_demand'',''transport_resources''' IN source)=0 THEN RAISE EXCEPTION 'Saga10 slot extension needs baseline review: %',signature; END IF;
  source=replace(source,'''transport_demand'',''transport_resources''','''transport_demand'',''transport_resources'',''order_lines''');
  IF signature='dation_private.t4_entries(uuid,uuid,jsonb,jsonb)' THEN
   IF position('jsonb_array_length(selection) NOT BETWEEN 1 AND 2' IN source)=0 THEN RAISE EXCEPTION 'Saga10 selection anchor differs'; END IF;
   source=replace(source,'jsonb_array_length(selection) NOT BETWEEN 1 AND 2','jsonb_array_length(selection) NOT BETWEEN 1 AND 3');
  END IF;
  IF signature='public.platform_decision_journey(uuid,uuid,text,jsonb)' THEN
   IF position('WHERE preparation_id=s.id AND selected)=2' IN source)=0 THEN RAISE EXCEPTION 'Saga10 preparation count anchor differs'; END IF;
   source=replace(source,'WHERE preparation_id=s.id AND selected)=2','WHERE preparation_id=s.id AND selected)=dation_private.saga10_required_slot_count(s.model_version_id)');
  END IF;
  EXECUTE source;
 END LOOP;
 IF to_regprocedure('dation_private.saga10_pack_v1(uuid,uuid,text,jsonb)') IS NULL THEN
  ALTER FUNCTION public.platform_ultimate_data_pack(uuid,uuid,text,jsonb) RENAME TO saga10_pack_v1;
  ALTER FUNCTION public.saga10_pack_v1(uuid,uuid,text,jsonb) SET SCHEMA dation_private;
 END IF;
 IF to_regprocedure('dation_private.saga10_journey_v1(uuid,uuid,text,jsonb)') IS NULL THEN
  ALTER FUNCTION public.platform_decision_journey(uuid,uuid,text,jsonb) RENAME TO saga10_journey_v1;
  ALTER FUNCTION public.saga10_journey_v1(uuid,uuid,text,jsonb) SET SCHEMA dation_private;
 END IF;
END $$;

CREATE OR REPLACE FUNCTION public.platform_ultimate_data_pack(target_workspace_id uuid,actor_user_id uuid,operation text,arguments jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE configuration jsonb; enabled boolean; lines_requested boolean;
BEGIN
 PERFORM dation_private.data_actor(target_workspace_id,actor_user_id);
 SELECT v.config_jsonb INTO configuration FROM public.decision_cases c JOIN public.logistics_model_versions v ON v.workspace_id=c.workspace_id AND v.id=c.logistics_model_version_id
  WHERE c.workspace_id=target_workspace_id AND c.id=(arguments->>'case_id')::uuid;
 SELECT saga10_schema_enabled INTO enabled FROM dation_private.platform_release WHERE singleton;
 lines_requested=arguments->>'entity'='order_lines';
 IF jsonb_typeof(arguments->'selection')='array' THEN lines_requested=coalesce(lines_requested,false) OR EXISTS(SELECT 1 FROM jsonb_array_elements(arguments->'selection') x WHERE x->>'slot_key'='order_lines'); END IF;
 IF lines_requested AND (configuration->>'version' IS DISTINCT FROM '2' OR configuration#>>'{cargo,input_mode}' IS DISTINCT FROM 'catalog') THEN RAISE EXCEPTION 'OrderLines requires an explicit v2 catalog' USING ERRCODE='22023'; END IF;
 IF configuration->>'version'='2' AND operation IN('prepare','publish') AND NOT coalesce(enabled,false) THEN RAISE EXCEPTION 'Saga10 schema closed' USING ERRCODE='42501'; END IF;
 RETURN dation_private.saga10_pack_v1(target_workspace_id,actor_user_id,operation,arguments);
END $$;

CREATE OR REPLACE FUNCTION public.platform_decision_journey(target_workspace_id uuid,actor_user_id uuid,operation text,arguments jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE configuration jsonb; enabled boolean;
BEGIN
 PERFORM dation_private.data_actor(target_workspace_id,actor_user_id);
 IF operation='create' THEN
  SELECT config_jsonb INTO configuration FROM public.logistics_model_versions WHERE workspace_id=target_workspace_id AND id=(arguments->>'model_version_id')::uuid;
 ELSE
  SELECT v.config_jsonb INTO configuration FROM dation_private.journey_preparations s JOIN public.logistics_model_versions v ON v.workspace_id=s.workspace_id AND v.id=s.model_version_id
   WHERE s.workspace_id=target_workspace_id AND s.id=(arguments->>'preparation_id')::uuid;
 END IF;
 SELECT saga10_schema_enabled INTO enabled FROM dation_private.platform_release WHERE singleton;
 IF arguments->>'entity'='order_lines' AND (configuration->>'version' IS DISTINCT FROM '2' OR configuration#>>'{cargo,input_mode}' IS DISTINCT FROM 'catalog') THEN RAISE EXCEPTION 'OrderLines requires an explicit v2 catalog' USING ERRCODE='22023'; END IF;
 IF configuration->>'version'='2' AND operation IN('create','upload_prepare','begin','owner','unselect') AND NOT coalesce(enabled,false) THEN RAISE EXCEPTION 'Saga10 schema closed' USING ERRCODE='42501'; END IF;
 RETURN dation_private.saga10_journey_v1(target_workspace_id,actor_user_id,operation,arguments);
END $$;
REVOKE ALL ON FUNCTION dation_private.saga10_pack_v1(uuid,uuid,text,jsonb),dation_private.saga10_journey_v1(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_ultimate_data_pack(uuid,uuid,text,jsonb),public.platform_decision_journey(uuid,uuid,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_ultimate_data_pack(uuid,uuid,text,jsonb),public.platform_decision_journey(uuid,uuid,text,jsonb) TO service_role;
COMMIT;
