-- T10: existing chat/messages/provenance stores only. No result mutation.
CREATE FUNCTION public.platform_ultimate_copilot(
 target_workspace_id uuid, actor_user_id uuid, target_run_id uuid,
 target_turn_id uuid, intent_hash text, operation text, payload jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE role_name text; r public.decision_runs; t public.decision_chat_turns;
 source public.decision_interpretation_sources; answer jsonb; stamp timestamptz;
 intent jsonb=payload->'intent'; receipt jsonb=payload->'receipt';
BEGIN
 role_name=dation_private.team_actor(target_workspace_id,actor_user_id);
 IF (role_name='viewer' AND operation<>'history') OR operation NOT IN('read','record','history') OR operation IS NULL
    OR target_turn_id IS NULL OR intent_hash IS NULL OR intent_hash !~ '^[0-9a-f]{64}$' THEN
  RAISE EXCEPTION 'Copilot access or request denied' USING ERRCODE='42501'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.workspace_ddas WHERE workspace_id=target_workspace_id AND dda_id='logistics' AND status='enabled') THEN
  RAISE EXCEPTION 'DDA unavailable' USING ERRCODE='42501'; END IF;
 SELECT * INTO r FROM public.decision_runs WHERE workspace_id=target_workspace_id AND id=target_run_id FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Run access denied' USING ERRCODE='42501'; END IF;
 IF r.workflow_version<>2 OR r.status<>'completed' OR r.result_package_version IS DISTINCT FROM 1 THEN
  RAISE EXCEPTION 'Published Run required' USING ERRCODE='22023'; END IF;
 IF operation='history' THEN
  IF coalesce((payload->>'offset')::integer,0) NOT BETWEEN 0 AND 1000000 THEN
   RAISE EXCEPTION 'Invalid history page' USING ERRCODE='22023'; END IF;
  SELECT coalesce(jsonb_agg(x.body ORDER BY x.created_at DESC,x.turn_id),'[]') INTO answer FROM (
   SELECT history_turn.created_at,history_turn.turn_id,jsonb_build_object('turn_id',history_turn.turn_id,'created_at',history_turn.created_at,
    'question',q.content,'receipt',m.content::jsonb,'prompt_version',history_turn.prompt_version,'provider',history_turn.provider,'model',history_turn.model) AS body
   FROM public.decision_chat_turns history_turn JOIN public.decision_messages m ON m.turn_id=history_turn.turn_id AND m.role='assistant' AND m.workspace_id=target_workspace_id
   JOIN public.decision_messages q ON q.turn_id=history_turn.turn_id AND q.role='user' AND q.workspace_id=target_workspace_id
   JOIN public.decision_interpretation_sources s ON s.chat_turn_id=history_turn.turn_id AND s.workspace_id=target_workspace_id
    AND s.run_id=r.id AND s.result_fingerprint=r.result_fingerprint AND s.provenance_version=2
   WHERE history_turn.workspace_id=target_workspace_id AND history_turn.run_id=r.id ORDER BY history_turn.created_at DESC,history_turn.turn_id LIMIT 21 OFFSET coalesce((payload->>'offset')::integer,0)
  ) x;
  RETURN jsonb_build_object('rows',CASE WHEN jsonb_array_length(answer)>20 THEN answer-20 ELSE answer END,
    'offset',coalesce((payload->>'offset')::integer,0),'next_offset',CASE WHEN jsonb_array_length(answer)>20 THEN coalesce((payload->>'offset')::integer,0)+20 END);
 END IF;
 -- Per-turn serialization preserves exact intent replay without provider reruns.
 PERFORM pg_advisory_xact_lock(hashtextextended(target_turn_id::text,0));
 SELECT * INTO t FROM public.decision_chat_turns WHERE turn_id=target_turn_id;
 IF FOUND THEN
  IF t.workspace_id IS DISTINCT FROM target_workspace_id OR t.run_id IS DISTINCT FROM target_run_id OR t.question_hash IS DISTINCT FROM intent_hash THEN
   RAISE EXCEPTION 'Turn intention conflict' USING ERRCODE='22023'; END IF;
  SELECT * INTO source FROM public.decision_interpretation_sources WHERE chat_turn_id=target_turn_id AND workspace_id=target_workspace_id AND provenance_version=2;
  IF NOT FOUND OR source.result_fingerprint IS DISTINCT FROM r.result_fingerprint THEN
   RAISE EXCEPTION 'Turn provenance conflict' USING ERRCODE='22023'; END IF;
  SELECT content::jsonb INTO STRICT answer FROM public.decision_messages
   WHERE turn_id=target_turn_id AND workspace_id=target_workspace_id AND role='assistant';
  RETURN answer;
 END IF;
 IF operation='read' THEN RETURN NULL; END IF;
 IF intent IS NULL OR receipt IS NULL OR jsonb_typeof(receipt)<>'object'
  OR octet_length(receipt::text)>20000 OR length(intent->>'question') NOT BETWEEN 1 AND 4000
  OR intent->>'schema_version' IS DISTINCT FROM 'decision_intent_v2'
  OR intent#>>'{provenance,run_id}' IS DISTINCT FROM target_run_id::text
  OR intent#>>'{provenance,result_fingerprint}' IS DISTINCT FROM r.result_fingerprint
  OR receipt->'provenance' IS DISTINCT FROM intent->'provenance'
  OR receipt->>'context_hash' IS DISTINCT FROM intent->>'context_hash'
  OR receipt->>'mode' IS DISTINCT FROM intent->>'mode'
  OR receipt->'selected_entity' IS DISTINCT FROM intent->'selected_entity'
  OR payload->>'prompt_version' IS DISTINCT FROM 'ULTIMATE_APPROVAL_COPILOT_V1'
  OR jsonb_typeof(payload->'evidence_refs') IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'Invalid Copilot provenance' USING ERRCODE='22023'; END IF;
 stamp=clock_timestamp();
 INSERT INTO public.decision_chat_turns(workspace_id,turn_id,run_id,question_hash,created_at,provider,model,knowledge_version,prompt_version)
 VALUES(target_workspace_id,target_turn_id,target_run_id,intent_hash,stamp,receipt#>>'{provider_info,provider}',receipt#>>'{provider_info,model}','DATION_REASONS_V1','ULTIMATE_APPROVAL_COPILOT_V1');
 INSERT INTO public.decision_messages(workspace_id,run_id,created_at,role,content,provider,model,knowledge_version,turn_id) VALUES
 (target_workspace_id,target_run_id,stamp,'user',intent->>'question',NULL,NULL,'DATION_REASONS_V1',target_turn_id),
 (target_workspace_id,target_run_id,stamp+interval '1 microsecond','assistant',receipt::text,receipt#>>'{provider_info,provider}',receipt#>>'{provider_info,model}','DATION_REASONS_V1',target_turn_id);
 INSERT INTO public.decision_interpretation_sources(workspace_id,run_id,chat_turn_id,provenance_version,result_fingerprint,
  decision_context_schema,decision_context_hash,mode,selected_entity,evidence_refs)
 VALUES(target_workspace_id,target_run_id,target_turn_id,2,r.result_fingerprint,'decision_context_v1',intent->>'context_hash',
  intent->>'mode',nullif(intent->'selected_entity','null'::jsonb),payload->'evidence_refs');
 RETURN receipt;
END; $$;
REVOKE ALL ON FUNCTION public.platform_ultimate_copilot(uuid,uuid,uuid,uuid,text,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_ultimate_copilot(uuid,uuid,uuid,uuid,text,text,jsonb) TO service_role;
