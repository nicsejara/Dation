-- A companion artifact, never a business decision_run or a case-node transition.
BEGIN;
CREATE TABLE public.decision_comparative_analyses (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 base_run_id uuid NOT NULL UNIQUE REFERENCES public.decision_runs(id) ON DELETE RESTRICT,
 base_result_fingerprint text NOT NULL,
 source_mode text NOT NULL CHECK(source_mode IN('existing','computed')),
 status text NOT NULL CHECK(status IN('queued','running','completed','error')),
 request_json jsonb NOT NULL,
 result_json jsonb,
 result_fingerprint text,
 progress_json jsonb NOT NULL DEFAULT '{"stage":"queued"}',
 error_message text,
 duration_ms bigint,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 started_at timestamptz,
 finished_at timestamptz,
 available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 deadline_at timestamptz NOT NULL DEFAULT clock_timestamp()+interval '30 minutes',
 generation integer NOT NULL DEFAULT 1,
 attempts integer NOT NULL DEFAULT 0,
 max_attempts integer NOT NULL DEFAULT 3 CHECK(max_attempts BETWEEN 1 AND 5),
 lease_token uuid,
 lease_expires_at timestamptz,
 heartbeat_at timestamptz,
 UNIQUE(base_run_id,id),
 CHECK((status='running' AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL)
    OR (status<>'running' AND lease_token IS NULL AND lease_expires_at IS NULL)),
 CHECK(status<>'completed' OR (jsonb_typeof(result_json)='object' AND result_fingerprint IS NOT NULL))
);
CREATE INDEX comparative_jobs_claim_idx ON public.decision_comparative_analyses(available_at,created_at) WHERE status IN('queued','running');
ALTER TABLE public.decision_comparative_analyses ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_comparative_analyses FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT,INSERT,UPDATE ON public.decision_comparative_analyses TO service_role;

CREATE FUNCTION public.protect_comparative_analysis() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.base_run_id IS DISTINCT FROM OLD.base_run_id OR
    NEW.base_result_fingerprint IS DISTINCT FROM OLD.base_result_fingerprint OR
    (NEW.request_json-'_observability') IS DISTINCT FROM (OLD.request_json-'_observability') THEN
  RAISE EXCEPTION 'Comparative identity is immutable' USING ERRCODE='22023';
 END IF;
 IF OLD.status='completed' AND NEW IS DISTINCT FROM OLD THEN
  RAISE EXCEPTION 'Completed comparative evidence is immutable' USING ERRCODE='22023';
 END IF;
 IF NEW.generation IS DISTINCT FROM OLD.generation AND NOT
    (OLD.status='error' AND NEW.status='queued' AND NEW.generation=OLD.generation+1) THEN
  RAISE EXCEPTION 'Invalid comparative retry' USING ERRCODE='22023';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER comparative_identity BEFORE UPDATE ON public.decision_comparative_analyses FOR EACH ROW EXECUTE FUNCTION public.protect_comparative_analysis();

CREATE FUNCTION public.enqueue_comparative_analysis(target_base_id uuid,job_request jsonb,existing_result jsonb DEFAULT NULL,retry_failed boolean DEFAULT false)
RETURNS SETOF public.decision_comparative_analyses LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE base decision_runs; current decision_comparative_analyses; fingerprint text;
BEGIN
 PERFORM pg_advisory_xact_lock(701013);
 SELECT * INTO base FROM decision_runs WHERE id=target_base_id FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Base run not found' USING ERRCODE='P0002'; END IF;
 IF base.status<>'completed' OR base.schema_version<>'assignment_v1' THEN
  RAISE EXCEPTION 'Completed Assignment required' USING ERRCODE='22023';
 END IF;
 fingerprint=coalesce(base.result_fingerprint,base.result_json->>'result_fingerprint');
 IF fingerprint IS NULL OR job_request->>'base_run_id' IS DISTINCT FROM target_base_id::text OR
    job_request->>'engine_name' IS DISTINCT FROM base.engine_name OR
    job_request->>'engine_version' IS DISTINCT FROM base.engine_version OR
    job_request->>'schema_version' IS DISTINCT FROM base.schema_version OR
    job_request->'configuration' IS DISTINCT FROM ((base.result_json->'configuration')-'options') OR
    job_request->'options' IS DISTINCT FROM ((base.result_json->'configuration'->'options')||'{"analysis_depth":"comparative"}'::jsonb) OR
    (existing_result IS NOT NULL AND existing_result IS DISTINCT FROM base.result_json) THEN
  RAISE EXCEPTION 'Comparative intention does not match persisted base' USING ERRCODE='22023';
 END IF;
 SELECT * INTO current FROM decision_comparative_analyses WHERE base_run_id=target_base_id FOR UPDATE;
 IF FOUND AND (current.status<>'error' OR NOT retry_failed) THEN
  RETURN NEXT current; RETURN;
 END IF;
 IF existing_result IS NULL AND (SELECT count(*) FROM decision_comparative_analyses WHERE status IN('queued','running'))>=16 THEN
  RAISE EXCEPTION 'Comparative queue full' USING ERRCODE='53300';
 END IF;
 IF current.id IS NOT NULL THEN
  UPDATE decision_comparative_analyses SET status='queued',generation=generation+1,attempts=0,
   lease_token=NULL,lease_expires_at=NULL,heartbeat_at=NULL,request_json=job_request,
   available_at=clock_timestamp(),deadline_at=clock_timestamp()+interval '30 minutes',
   started_at=NULL,finished_at=NULL,error_message=NULL,result_json=NULL,result_fingerprint=NULL,duration_ms=NULL,
   progress_json='{"stage":"queued"}' WHERE id=current.id;
 ELSE
  INSERT INTO decision_comparative_analyses(base_run_id,base_result_fingerprint,source_mode,status,request_json,
   result_json,result_fingerprint,finished_at,progress_json,duration_ms)
  VALUES(target_base_id,fingerprint,CASE WHEN existing_result IS NULL THEN 'computed' ELSE 'existing' END,
   CASE WHEN existing_result IS NULL THEN 'queued' ELSE 'completed' END,job_request,
   existing_result,CASE WHEN existing_result IS NULL THEN NULL ELSE fingerprint END,
   CASE WHEN existing_result IS NULL THEN NULL ELSE clock_timestamp() END,
   CASE WHEN existing_result IS NULL THEN '{"stage":"queued"}'::jsonb ELSE '{"stage":"completed"}'::jsonb END,
   CASE WHEN existing_result IS NULL THEN NULL ELSE 0 END);
 END IF;
 RETURN QUERY SELECT * FROM decision_comparative_analyses WHERE base_run_id=target_base_id;
END; $$;

CREATE FUNCTION public.claim_comparative_analysis(worker_token uuid,lease_seconds integer DEFAULT 120)
RETURNS SETOF public.decision_comparative_analyses LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE target uuid;
BEGIN
 UPDATE decision_comparative_analyses SET status='error',lease_token=NULL,lease_expires_at=NULL,finished_at=clock_timestamp(),
  error_message='El análisis agotó su plazo o sus intentos de recuperación.',progress_json='{"stage":"error","reason":"recovery_exhausted"}'
 WHERE status IN('queued','running') AND (deadline_at<=clock_timestamp() OR
  (status='running' AND lease_expires_at<=clock_timestamp() AND attempts>=max_attempts));
 SELECT id INTO target FROM decision_comparative_analyses WHERE
  ((status='queued' AND available_at<=clock_timestamp()) OR (status='running' AND lease_expires_at<=clock_timestamp()))
  AND attempts<max_attempts AND deadline_at>clock_timestamp()
 ORDER BY available_at,created_at FOR UPDATE SKIP LOCKED LIMIT 1;
 IF NOT FOUND THEN RETURN; END IF;
 UPDATE decision_comparative_analyses SET status='running',attempts=attempts+1,lease_token=worker_token,
  heartbeat_at=clock_timestamp(),started_at=coalesce(started_at,clock_timestamp()),
  lease_expires_at=least(deadline_at,clock_timestamp()+make_interval(secs=>greatest(30,least(lease_seconds,300)))),
  progress_json=jsonb_build_object('stage','validating','attempt',attempts+1)
 WHERE id=target;
 RETURN QUERY SELECT * FROM decision_comparative_analyses WHERE id=target;
END; $$;

CREATE FUNCTION public.heartbeat_comparative_analysis(target_analysis_id uuid,worker_token uuid,lease_seconds integer DEFAULT 120,progress jsonb DEFAULT NULL)
RETURNS boolean LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 UPDATE decision_comparative_analyses SET heartbeat_at=clock_timestamp(),
  lease_expires_at=least(deadline_at,clock_timestamp()+make_interval(secs=>greatest(30,least(lease_seconds,300)))),
  progress_json=coalesce(progress,progress_json)
 WHERE id=target_analysis_id AND status='running' AND lease_token=worker_token AND
  lease_expires_at>clock_timestamp() AND deadline_at>clock_timestamp();
 RETURN FOUND;
END; $$;

CREATE FUNCTION public.finish_comparative_analysis(target_analysis_id uuid,worker_token uuid,terminal_values jsonb)
RETURNS SETOF public.decision_comparative_analyses LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE target decision_comparative_analyses; base decision_runs; outcome text=terminal_values->>'status';
BEGIN
 IF outcome IS NULL OR outcome NOT IN('completed','error') THEN RAISE EXCEPTION 'Invalid outcome'; END IF;
 SELECT * INTO target FROM decision_comparative_analyses WHERE id=target_analysis_id FOR UPDATE;
 IF NOT FOUND OR target.status<>'running' OR target.lease_token IS DISTINCT FROM worker_token OR
  target.lease_expires_at<=clock_timestamp() OR target.deadline_at<=clock_timestamp() THEN RETURN; END IF;
 SELECT * INTO STRICT base FROM decision_runs WHERE id=target.base_run_id;
 IF outcome='completed' AND (
  jsonb_typeof(terminal_values->'result_json') IS DISTINCT FROM 'object' OR
  terminal_values->'result_json'->'scenarios'->'selected' IS DISTINCT FROM base.result_json->'scenarios'->'selected' OR
  (terminal_values->'result_json'->'configuration')-'options' IS DISTINCT FROM (base.result_json->'configuration')-'options' OR
  terminal_values->'result_json'->'configuration'->'options' IS DISTINCT FROM target.request_json->'options' OR
  terminal_values->'result_json'->>'schema_version' IS DISTINCT FROM base.schema_version OR
  terminal_values->'result_json'->'inputs' IS DISTINCT FROM base.result_json->'inputs' OR
  terminal_values->>'result_fingerprint' IS NULL) THEN
  RAISE EXCEPTION 'Comparative must preserve the original decision' USING ERRCODE='22023';
 END IF;
 UPDATE decision_comparative_analyses SET status=outcome,finished_at=clock_timestamp(),
  result_json=terminal_values->'result_json',result_fingerprint=terminal_values->>'result_fingerprint',
  duration_ms=(terminal_values->>'duration_ms')::bigint,error_message=left(terminal_values->>'error_message',1500),
  progress_json=jsonb_build_object('stage',outcome),lease_token=NULL,lease_expires_at=NULL WHERE id=target_analysis_id;
 RETURN QUERY SELECT * FROM decision_comparative_analyses WHERE id=target_analysis_id;
END; $$;

-- Bind interpreter output to the exact evidence used; preserve original Phase 7 RPCs/catalog.
CREATE TABLE public.decision_interpretation_sources (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 run_id uuid NOT NULL REFERENCES public.decision_runs(id) ON DELETE RESTRICT,
 analysis_id uuid,
 explanation_id uuid UNIQUE REFERENCES public.decision_explanations(id) ON DELETE RESTRICT,
 chat_turn_id uuid UNIQUE REFERENCES public.decision_chat_turns(turn_id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(run_id,analysis_id) REFERENCES public.decision_comparative_analyses(base_run_id,id) ON DELETE RESTRICT,
 CHECK((explanation_id IS NOT NULL)::integer+(chat_turn_id IS NOT NULL)::integer=1)
);
ALTER TABLE public.decision_interpretation_sources ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_interpretation_sources FROM PUBLIC,anon,authenticated,service_role;
GRANT SELECT,INSERT ON public.decision_interpretation_sources TO service_role;
CREATE FUNCTION public.validate_interpretation_source() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE actual uuid;
BEGIN
 IF NEW.analysis_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM decision_comparative_analyses WHERE id=NEW.analysis_id AND base_run_id=NEW.run_id AND status='completed') THEN
  RAISE EXCEPTION 'Comparative evidence unavailable' USING ERRCODE='22023';
 END IF;
 IF NEW.chat_turn_id IS NOT NULL THEN SELECT run_id INTO actual FROM decision_chat_turns WHERE turn_id=NEW.chat_turn_id;
 ELSE SELECT run_id INTO actual FROM decision_explanations WHERE id=NEW.explanation_id; END IF;
 IF actual IS DISTINCT FROM NEW.run_id THEN RAISE EXCEPTION 'Interpreter source mismatch' USING ERRCODE='22023'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER interpretation_source_identity BEFORE INSERT ON public.decision_interpretation_sources FOR EACH ROW EXECUTE FUNCTION public.validate_interpretation_source();

CREATE FUNCTION public.read_decision_chat_turn_with_evidence(target_turn_id uuid,target_run_id uuid,intent_hash text)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=public,pg_temp AS $$
DECLARE answer jsonb; evidence uuid;
BEGIN
 answer=read_decision_chat_turn(target_turn_id,target_run_id,intent_hash);
 IF answer IS NULL THEN RETURN NULL; END IF;
 SELECT analysis_id INTO evidence FROM decision_interpretation_sources WHERE chat_turn_id=target_turn_id;
 RETURN answer||jsonb_build_object('evidence_analysis_id',evidence);
END; $$;
CREATE FUNCTION public.record_decision_chat_turn_with_evidence(target_turn_id uuid,target_run_id uuid,intent_hash text,question_text text,answer_text text,metadata jsonb,evidence_analysis_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE answer jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended(target_turn_id::text,0));
 answer=read_decision_chat_turn_with_evidence(target_turn_id,target_run_id,intent_hash);
 IF answer IS NOT NULL THEN RETURN answer; END IF;
 answer=record_decision_chat_turn(target_turn_id,target_run_id,intent_hash,question_text,answer_text,metadata);
 INSERT INTO decision_interpretation_sources(run_id,analysis_id,chat_turn_id) VALUES(target_run_id,evidence_analysis_id,target_turn_id);
 RETURN answer||jsonb_build_object('evidence_analysis_id',evidence_analysis_id);
END; $$;
CREATE FUNCTION public.record_decision_explanation_with_evidence(explanation jsonb,evidence_analysis_id uuid DEFAULT NULL)
RETURNS SETOF public.decision_explanations LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE target uuid=(explanation->>'id')::uuid;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM decision_runs WHERE id=(explanation->>'run_id')::uuid AND status='completed') THEN
  RAISE EXCEPTION 'Completed run required' USING ERRCODE='22023';
 END IF;
 INSERT INTO decision_explanations(id,run_id,provider,model,knowledge_version,prompt_version,response_json,usage_json)
 VALUES(target,(explanation->>'run_id')::uuid,explanation->>'provider',explanation->>'model',explanation->>'knowledge_version',
  explanation->>'prompt_version',explanation->'response_json',coalesce(explanation->'usage_json','{}'));
 INSERT INTO decision_interpretation_sources(run_id,analysis_id,explanation_id) VALUES((explanation->>'run_id')::uuid,evidence_analysis_id,target);
 RETURN QUERY SELECT * FROM decision_explanations WHERE id=target;
END; $$;

CREATE FUNCTION public.comparative_operational_snapshot() RETURNS jsonb LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT jsonb_build_object('queued',count(*) FILTER(WHERE status='queued'),'running',count(*) FILTER(WHERE status='running'),
  'expired_leases',count(*) FILTER(WHERE status='running' AND lease_expires_at<statement_timestamp()),
  'retried_active',count(*) FILTER(WHERE status IN('queued','running') AND attempts>1),
  'oldest_queued_seconds',coalesce(max(extract(epoch FROM statement_timestamp()-created_at)) FILTER(WHERE status='queued'),0))
 FROM decision_comparative_analyses WHERE status IN('queued','running');
$$;
CREATE FUNCTION public.current_decision_explanation(target_run_id uuid)
RETURNS SETOF public.decision_explanations LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT e.* FROM decision_explanations e
 LEFT JOIN decision_interpretation_sources source ON source.explanation_id=e.id
 LEFT JOIN decision_comparative_analyses a ON a.base_run_id=e.run_id AND a.status='completed'
 WHERE e.run_id=target_run_id
 ORDER BY ((source.analysis_id IS NOT DISTINCT FROM a.id) OR (a.source_mode='existing' AND source.analysis_id IS NULL)) DESC,
  e.created_at DESC,e.id DESC LIMIT 1;
$$;
REVOKE ALL ON FUNCTION public.protect_comparative_analysis(),public.enqueue_comparative_analysis(uuid,jsonb,jsonb,boolean),
 public.claim_comparative_analysis(uuid,integer),public.heartbeat_comparative_analysis(uuid,uuid,integer,jsonb),
 public.finish_comparative_analysis(uuid,uuid,jsonb),public.validate_interpretation_source(),
 public.read_decision_chat_turn_with_evidence(uuid,uuid,text),public.record_decision_chat_turn_with_evidence(uuid,uuid,text,text,text,jsonb,uuid),
 public.record_decision_explanation_with_evidence(jsonb,uuid),public.comparative_operational_snapshot(),public.current_decision_explanation(uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.protect_comparative_analysis(),public.enqueue_comparative_analysis(uuid,jsonb,jsonb,boolean),
 public.claim_comparative_analysis(uuid,integer),public.heartbeat_comparative_analysis(uuid,uuid,integer,jsonb),
 public.finish_comparative_analysis(uuid,uuid,jsonb),public.validate_interpretation_source(),
 public.read_decision_chat_turn_with_evidence(uuid,uuid,text),public.record_decision_chat_turn_with_evidence(uuid,uuid,text,text,text,jsonb,uuid),
 public.record_decision_explanation_with_evidence(jsonb,uuid),public.comparative_operational_snapshot(),public.current_decision_explanation(uuid) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
