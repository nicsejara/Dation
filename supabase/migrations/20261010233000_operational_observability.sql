-- Additive Phase 7. Shared private workspace; historical messages stay unattributed.
BEGIN;
CREATE TABLE public.dispatch_worker_instances (
 worker_id uuid PRIMARY KEY,
 revision text NOT NULL CHECK (revision ~ '^[a-zA-Z0-9-]{1,100}$'),
 seen_at timestamptz NOT NULL,
 ready boolean NOT NULL
);
CREATE INDEX dispatch_worker_seen_idx ON public.dispatch_worker_instances(seen_at);
ALTER TABLE public.dispatch_worker_instances ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.dispatch_worker_instances FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.dispatch_worker_instances TO service_role;

CREATE FUNCTION public.report_dispatch_worker(target_worker_id uuid, worker_revision text, is_ready boolean)
RETURNS boolean LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 IF target_worker_id IS NULL OR worker_revision IS NULL OR is_ready IS NULL THEN
  RAISE EXCEPTION 'Invalid worker report' USING ERRCODE='22023';
 END IF;
 INSERT INTO dispatch_worker_instances VALUES(target_worker_id,worker_revision,clock_timestamp(),is_ready)
 ON CONFLICT(worker_id) DO UPDATE SET revision=excluded.revision,seen_at=excluded.seen_at,ready=excluded.ready;
 DELETE FROM dispatch_worker_instances WHERE seen_at < clock_timestamp()-interval '24 hours';
 RETURN true;
END; $$;

CREATE TABLE public.decision_chat_turns (
 turn_id uuid PRIMARY KEY,
 run_id uuid NOT NULL REFERENCES public.decision_runs(id) ON DELETE CASCADE,
 question_hash text NOT NULL CHECK(question_hash ~ '^[0-9a-f]{64}$'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 provider text NOT NULL CHECK(length(provider) BETWEEN 1 AND 100),
 model text NOT NULL CHECK(length(model) BETWEEN 1 AND 150),
 knowledge_version text NOT NULL CHECK(length(knowledge_version) BETWEEN 1 AND 150),
 prompt_version text NOT NULL CHECK(length(prompt_version) BETWEEN 1 AND 150),
 usage_json jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(usage_json)='object'),
 request_id uuid
);
CREATE INDEX decision_chat_turns_created_idx ON public.decision_chat_turns(created_at);
ALTER TABLE public.decision_chat_turns ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_chat_turns FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT,INSERT ON public.decision_chat_turns TO service_role;
ALTER TABLE public.decision_messages ADD COLUMN turn_id uuid REFERENCES public.decision_chat_turns(turn_id) ON DELETE CASCADE;
CREATE UNIQUE INDEX decision_messages_turn_role_idx ON public.decision_messages(turn_id,role) WHERE turn_id IS NOT NULL;
CREATE INDEX decision_messages_recent_idx ON public.decision_messages(run_id,created_at DESC,id DESC);

CREATE FUNCTION public.read_decision_chat_turn(target_turn_id uuid,target_run_id uuid,intent_hash text)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=public,pg_temp AS $$
DECLARE t decision_chat_turns; answer text;
BEGIN
 SELECT * INTO t FROM decision_chat_turns WHERE turn_id=target_turn_id;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF t.run_id IS DISTINCT FROM target_run_id OR t.question_hash IS DISTINCT FROM intent_hash THEN
  RAISE EXCEPTION 'Turn intention conflict' USING ERRCODE='22023';
 END IF;
 SELECT content INTO STRICT answer FROM decision_messages WHERE turn_id=t.turn_id AND role='assistant';
 RETURN jsonb_build_object('turn_id',t.turn_id,'run_id',t.run_id,'provider',t.provider,'model',t.model,
  'knowledge_version',t.knowledge_version,'prompt_version',t.prompt_version,'usage',t.usage_json,'answer',answer);
END; $$;

CREATE FUNCTION public.record_decision_chat_turn(target_turn_id uuid,target_run_id uuid,intent_hash text,
 question_text text,answer_text text,metadata jsonb)
RETURNS jsonb LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE replay jsonb; stamp timestamptz; usage jsonb;
BEGIN
 IF target_turn_id IS NULL OR target_run_id IS NULL OR intent_hash IS NULL OR
    length(question_text) NOT BETWEEN 2 AND 2000 OR question_text IS NULL OR
    length(answer_text) NOT BETWEEN 1 AND 20000 OR answer_text IS NULL OR
    jsonb_typeof(metadata) IS DISTINCT FROM 'object' THEN
  RAISE EXCEPTION 'Invalid chat turn' USING ERRCODE='22023';
 END IF;
 -- Serializes the same UUID without serializing unrelated conversations.
 PERFORM pg_advisory_xact_lock(hashtextextended(target_turn_id::text,0));
 replay=read_decision_chat_turn(target_turn_id,target_run_id,intent_hash);
 IF replay IS NOT NULL THEN RETURN replay; END IF;
 PERFORM 1 FROM decision_runs WHERE id=target_run_id AND status='completed' FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Completed run required' USING ERRCODE='22023'; END IF;
 IF NOT (metadata ?& ARRAY['provider','model','knowledge_version','prompt_version']) THEN
  RAISE EXCEPTION 'Missing audit metadata' USING ERRCODE='22023';
 END IF;
 -- Accept only bounded token counts; arbitrary provider metadata is never persisted.
 SELECT coalesce(jsonb_object_agg(key,value),'{}') INTO usage FROM jsonb_each(coalesce(metadata->'usage','{}'))
 WHERE key IN ('prompt_tokens','completion_tokens','total_tokens') AND value::text ~ '^[0-9]{1,10}$';
 stamp=clock_timestamp();
 INSERT INTO decision_chat_turns(turn_id,run_id,question_hash,created_at,provider,model,knowledge_version,prompt_version,usage_json,request_id)
 VALUES(target_turn_id,target_run_id,intent_hash,stamp,metadata->>'provider',metadata->>'model',
  metadata->>'knowledge_version',metadata->>'prompt_version',usage,(metadata->>'request_id')::uuid);
 INSERT INTO decision_messages(run_id,created_at,role,content,provider,model,knowledge_version,turn_id) VALUES
 (target_run_id,stamp,'user',question_text,NULL,NULL,metadata->>'knowledge_version',target_turn_id),
 (target_run_id,stamp+interval '1 microsecond','assistant',answer_text,metadata->>'provider',metadata->>'model',metadata->>'knowledge_version',target_turn_id);
 RETURN read_decision_chat_turn(target_turn_id,target_run_id,intent_hash);
END; $$;

CREATE FUNCTION public.dispatch_operational_snapshot()
RETURNS jsonb LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT jsonb_build_object(
 'sampled_at',statement_timestamp(),
 'queue',(SELECT jsonb_build_object(
  'queued',count(*) FILTER(WHERE state='queued'),
  'running',count(*) FILTER(WHERE state='running'),
  'retried_active',count(*) FILTER(WHERE state IN('queued','running') AND attempts>1),
  'expired_leases',count(*) FILTER(WHERE state='running' AND lease_expires_at<statement_timestamp()),
  'past_deadline',count(*) FILTER(WHERE state IN('queued','running') AND deadline_at<statement_timestamp()),
  'oldest_queued_seconds',coalesce(max(extract(epoch FROM statement_timestamp()-created_at)) FILTER(WHERE state='queued'),0)
 ) FROM dispatch_run_jobs WHERE state IN('queued','running')),
 'workers',(SELECT jsonb_build_object('healthy',count(*) FILTER(WHERE ready), 'reporting',count(*))
  FROM dispatch_worker_instances WHERE seen_at>statement_timestamp()-interval '90 seconds'),
 'reconciliation',(SELECT jsonb_build_object('pending',count(*),'retrying',count(*) FILTER(WHERE attempts>0),
  'oldest_pending_seconds',coalesce(max(extract(epoch FROM statement_timestamp()-available_at)) FILTER(WHERE available_at<=statement_timestamp()),0))
  FROM decision_case_reconciliations),
 'runs_24h',(SELECT jsonb_build_object('completed',count(*) FILTER(WHERE status='completed'),
  'errors',count(*) FILTER(WHERE status='error'),'duration_p95_ms',
  percentile_cont(0.95) WITHIN GROUP(ORDER BY duration_ms) FILTER(WHERE status='completed' AND duration_ms IS NOT NULL))
  FROM decision_runs WHERE created_at>statement_timestamp()-interval '24 hours'),
 'chat_24h',(SELECT jsonb_build_object('turns',count(*),
  'total_tokens',coalesce(sum((usage_json->>'total_tokens')::bigint),0))
  FROM decision_chat_turns WHERE created_at>statement_timestamp()-interval '24 hours')
 );
$$;
CREATE INDEX decision_runs_operational_idx ON public.decision_runs(created_at,status) INCLUDE(duration_ms);
REVOKE ALL ON FUNCTION public.report_dispatch_worker(uuid,text,boolean),
 public.read_decision_chat_turn(uuid,uuid,text),public.record_decision_chat_turn(uuid,uuid,text,text,text,jsonb),
 public.dispatch_operational_snapshot() FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.report_dispatch_worker(uuid,text,boolean),
 public.read_decision_chat_turn(uuid,uuid,text),public.record_decision_chat_turn(uuid,uuid,text,text,text,jsonb),
 public.dispatch_operational_snapshot() TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
