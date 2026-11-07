-- Saga 02: opt-in durable activation; migration never activates cloud.
BEGIN;
CREATE TABLE IF NOT EXISTS dation_private.execution_dispatch_policy (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 enabled boolean NOT NULL DEFAULT false, admissions_open boolean NOT NULL DEFAULT false,
 max_compute integer NOT NULL DEFAULT 2 CHECK(max_compute BETWEEN 1 AND 2),
 max_control integer NOT NULL DEFAULT 1 CHECK(max_control=1),
 workspace_daily_limit integer NOT NULL DEFAULT 50 CHECK(workspace_daily_limit BETWEEN 1 AND 50),
 global_daily_limit integer NOT NULL DEFAULT 500 CHECK(global_daily_limit BETWEEN 1 AND 500),
 delivery_daily_limit integer NOT NULL DEFAULT 1000 CHECK(delivery_daily_limit BETWEEN 1 AND 1000),
 delivery_day date NOT NULL DEFAULT CURRENT_DATE, deliveries_today integer NOT NULL DEFAULT 0,
 last_recovery_at timestamptz
);
INSERT INTO dation_private.execution_dispatch_policy(singleton) VALUES(true) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS dation_private.execution_outbox (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 workspace_id uuid NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
 kind text NOT NULL CHECK(kind IN('dispatch','comparative','reconciliation')),
 run_id uuid REFERENCES public.dispatch_run_jobs(run_id) ON DELETE CASCADE,
 analysis_id uuid REFERENCES public.decision_comparative_analyses(id) ON DELETE CASCADE,
 case_id uuid REFERENCES public.decision_cases(id) ON DELETE CASCADE,
 entity_id uuid GENERATED ALWAYS AS (coalesce(run_id,analysis_id,case_id)) STORED,
 generation bigint NOT NULL DEFAULT 1, source_version bigint,
 state text NOT NULL DEFAULT 'pending' CHECK(state IN('pending','dispatching','submitted','running','done','dead')),
 delivery_token uuid, lease_expires_at timestamptz,
 available_at timestamptz NOT NULL DEFAULT clock_timestamp(), deadline_at timestamptz NOT NULL,
 delivery_attempts integer NOT NULL DEFAULT 0 CHECK(delivery_attempts BETWEEN 0 AND 3),
 admission_day date NOT NULL DEFAULT CURRENT_DATE, admissions_today integer NOT NULL DEFAULT 0,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 reserved_at timestamptz, submitted_at timestamptz, finished_at timestamptz, provider_operation text, last_error text,
 UNIQUE(kind,entity_id),
 CHECK((kind='dispatch' AND run_id IS NOT NULL AND analysis_id IS NULL AND case_id IS NULL)
    OR (kind='comparative' AND run_id IS NULL AND analysis_id IS NOT NULL AND case_id IS NULL)
    OR (kind='reconciliation' AND run_id IS NULL AND analysis_id IS NULL AND case_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS execution_outbox_pending ON dation_private.execution_outbox(state,available_at)
 WHERE state NOT IN('done','dead');
ALTER TABLE dation_private.execution_dispatch_policy ENABLE ROW LEVEL SECURITY;
ALTER TABLE dation_private.execution_outbox ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON dation_private.execution_dispatch_policy,dation_private.execution_outbox FROM PUBLIC,anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION dation_private.queue_execution_signal(
 work_kind text,entity uuid,workspace uuid,source_version bigint,available timestamptz,deadline timestamptz,new_admission boolean DEFAULT false)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $fn$
DECLARE p dation_private.execution_dispatch_policy; used bigint;
BEGIN
 SELECT * INTO p FROM dation_private.execution_dispatch_policy WHERE singleton;
 IF NOT p.enabled THEN RETURN; END IF;
 IF new_admission THEN
  IF NOT p.admissions_open THEN RAISE EXCEPTION 'Execution admission is paused' USING ERRCODE='55000'; END IF;
  PERFORM pg_advisory_xact_lock(701920);
  SELECT coalesce(sum(admissions_today),0) INTO used FROM dation_private.execution_outbox
   WHERE admission_day=CURRENT_DATE AND workspace_id=workspace;
  IF used>=p.workspace_daily_limit THEN RAISE EXCEPTION 'Workspace execution quota reached' USING ERRCODE='53300'; END IF;
  SELECT coalesce(sum(admissions_today),0) INTO used FROM dation_private.execution_outbox WHERE admission_day=CURRENT_DATE;
  IF used>=p.global_daily_limit THEN RAISE EXCEPTION 'Execution quota reached' USING ERRCODE='53300'; END IF;
 END IF;
 INSERT INTO dation_private.execution_outbox(workspace_id,kind,run_id,analysis_id,case_id,source_version,available_at,deadline_at,admissions_today)
 VALUES(workspace,work_kind,CASE WHEN work_kind='dispatch' THEN entity END,
  CASE WHEN work_kind='comparative' THEN entity END,CASE WHEN work_kind='reconciliation' THEN entity END,
  source_version,available,deadline,CASE WHEN new_admission THEN 1 ELSE 0 END)
 ON CONFLICT(kind,entity_id) DO UPDATE SET generation=execution_outbox.generation+1,
  source_version=excluded.source_version,state='pending',delivery_token=NULL,lease_expires_at=NULL,
  available_at=excluded.available_at,deadline_at=excluded.deadline_at,delivery_attempts=0,
  updated_at=clock_timestamp(),reserved_at=NULL,submitted_at=NULL,finished_at=NULL,provider_operation=NULL,last_error=NULL,
  admission_day=CURRENT_DATE,
  admissions_today=CASE WHEN execution_outbox.admission_day=CURRENT_DATE THEN execution_outbox.admissions_today ELSE 0 END
    +CASE WHEN new_admission THEN 1 ELSE 0 END;
END; $fn$;

CREATE OR REPLACE FUNCTION dation_private.capture_execution_signal()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $fn$
DECLARE k text; entity uuid; version bigint; deadline timestamptz; state text;
BEGIN
 IF TG_TABLE_NAME='decision_case_reconciliations' THEN
  k:='reconciliation';
  IF TG_OP='DELETE' THEN
   UPDATE dation_private.execution_outbox SET state='done',finished_at=clock_timestamp(),lease_expires_at=NULL
    WHERE kind=k AND entity_id=OLD.case_id AND source_version=OLD.version;
   RETURN OLD;
  END IF;
  entity:=NEW.case_id;version:=NEW.version;deadline:=clock_timestamp()+interval '30 minutes';state:='queued';
  IF TG_OP='UPDATE' AND NEW.version=OLD.version THEN RETURN NEW; END IF;
 ELSIF TG_TABLE_NAME='dispatch_run_jobs' THEN
  k:='dispatch';entity:=NEW.run_id;deadline:=NEW.deadline_at;state:=NEW.state;
  IF TG_OP='UPDATE' AND NEW.state=OLD.state THEN RETURN NEW; END IF;
 ELSE
  k:='comparative';entity:=NEW.id;deadline:=NEW.deadline_at;state:=NEW.status;version:=NEW.generation;
  IF TG_OP='UPDATE' AND NEW.status=OLD.status AND NEW.generation=OLD.generation THEN RETURN NEW; END IF;
 END IF;
 IF state IN('completed','error') THEN
  UPDATE dation_private.execution_outbox SET state='done',finished_at=clock_timestamp(),lease_expires_at=NULL
   WHERE kind=k AND entity_id=entity;
 ELSIF state='queued' THEN
  PERFORM dation_private.queue_execution_signal(k,entity,NEW.workspace_id,version,NEW.available_at,deadline,k<>'reconciliation');
 END IF;
 RETURN NEW;
END; $fn$;
DROP TRIGGER IF EXISTS execution_dispatch_signal ON public.dispatch_run_jobs;
CREATE TRIGGER execution_dispatch_signal AFTER INSERT OR UPDATE OF state ON public.dispatch_run_jobs
 FOR EACH ROW EXECUTE FUNCTION dation_private.capture_execution_signal();
DROP TRIGGER IF EXISTS execution_comparative_signal ON public.decision_comparative_analyses;
CREATE TRIGGER execution_comparative_signal AFTER INSERT OR UPDATE OF status,generation ON public.decision_comparative_analyses
 FOR EACH ROW EXECUTE FUNCTION dation_private.capture_execution_signal();
DROP TRIGGER IF EXISTS execution_case_signal ON public.decision_case_reconciliations;
CREATE TRIGGER execution_case_signal AFTER INSERT OR UPDATE OF version OR DELETE ON public.decision_case_reconciliations
 FOR EACH ROW EXECUTE FUNCTION dation_private.capture_execution_signal();
REVOKE ALL ON FUNCTION dation_private.queue_execution_signal(text,uuid,uuid,bigint,timestamptz,timestamptz,boolean),
 dation_private.capture_execution_signal() FROM PUBLIC,anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION dation_private.execution_source(work_kind text,entity uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $fn$
DECLARE answer jsonb;
BEGIN
 IF work_kind='dispatch' THEN
  SELECT jsonb_build_object('state',j.state,'workspace_id',j.workspace_id,'deadline_at',j.deadline_at,
   'lease_token',j.lease_token,'lease_expires_at',j.lease_expires_at,'attempts',j.attempts,'max_attempts',j.max_attempts)
   INTO answer FROM public.dispatch_run_jobs j WHERE run_id=entity;
 ELSIF work_kind='comparative' THEN
  SELECT jsonb_build_object('state',j.status,'workspace_id',j.workspace_id,'deadline_at',j.deadline_at,
   'lease_token',j.lease_token,'lease_expires_at',j.lease_expires_at,'attempts',j.attempts,'max_attempts',j.max_attempts)
   INTO answer FROM public.decision_comparative_analyses j WHERE id=entity;
 ELSE
  SELECT jsonb_build_object('state','queued','workspace_id',j.workspace_id,'version',j.version,
   'updated_at',j.updated_at,'available_at',j.available_at)
   INTO answer FROM public.decision_case_reconciliations j WHERE case_id=entity;
 END IF;
 RETURN answer;
END; $fn$;

CREATE OR REPLACE FUNCTION dation_private.maintain_execution_work()
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $fn$
BEGIN
 -- Exhausted activation cannot leave an accepted decision queued forever.
 UPDATE public.dispatch_run_jobs j SET deadline_at=least(j.deadline_at,transaction_timestamp())
 WHERE (j.state='queued' OR (j.state='running' AND j.lease_expires_at<=clock_timestamp()))
  AND EXISTS(SELECT 1 FROM dation_private.execution_outbox o WHERE o.run_id=j.run_id
   AND o.delivery_attempts>=3 AND (o.lease_expires_at IS NULL OR o.lease_expires_at<=clock_timestamp()));
 PERFORM dation_private.maintain_dispatch_jobs();
 UPDATE public.decision_comparative_analyses j SET deadline_at=least(j.deadline_at,transaction_timestamp())
 WHERE (j.status='queued' OR (j.status='running' AND j.lease_expires_at<=clock_timestamp()))
  AND EXISTS(SELECT 1 FROM dation_private.execution_outbox o WHERE o.analysis_id=j.id
   AND o.delivery_attempts>=3 AND (o.lease_expires_at IS NULL OR o.lease_expires_at<=clock_timestamp()));
 UPDATE public.decision_comparative_analyses SET status='error',lease_token=NULL,lease_expires_at=NULL,
  finished_at=clock_timestamp(),error_message='El análisis agotó su plazo o sus intentos de recuperación.',
  progress_json='{"stage":"error","reason":"recovery_exhausted"}'
 WHERE status IN('queued','running') AND (deadline_at<=clock_timestamp() OR
  (status='running' AND lease_expires_at<=clock_timestamp() AND attempts>=max_attempts));
 UPDATE dation_private.execution_outbox SET state='dead',lease_expires_at=NULL,last_error='recovery_exhausted'
 WHERE state NOT IN('done','dead') AND (deadline_at<=clock_timestamp() OR
  (delivery_attempts>=3 AND (lease_expires_at IS NULL OR lease_expires_at<=clock_timestamp())));
END; $fn$;

CREATE OR REPLACE FUNCTION public.execution_runtime(operation text,arguments jsonb DEFAULT '{}',
 target_workspace_id uuid DEFAULT NULL,actor_user_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $fn$
DECLARE
 p dation_private.execution_dispatch_policy; o dation_private.execution_outbox; selected dation_private.execution_outbox;
 j public.dispatch_run_jobs; a public.decision_comparative_analyses; c public.decision_case_reconciliations;
 role text; answer jsonb; source jsonb; result jsonb:='[]'; capacity integer; active integer; affected integer;
 target uuid; token uuid; is_global boolean:=target_workspace_id IS NULL AND actor_user_id IS NULL;
 old_enabled boolean; stamp timestamptz:=clock_timestamp(); kind_filter text:=arguments->>'kind';
BEGIN
 IF jsonb_typeof(arguments) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'Invalid arguments' USING ERRCODE='22023'; END IF;
 IF NOT is_global THEN
  SELECT m.access_role INTO role FROM public.workspace_members m JOIN public.workspaces w ON w.id=m.workspace_id
   WHERE m.workspace_id=target_workspace_id AND m.user_id=actor_user_id AND m.status='active' AND w.status='active';
  IF NOT FOUND THEN RAISE EXCEPTION 'Membership denied' USING ERRCODE='42501'; END IF;
  IF operation NOT IN('policy','snapshot','reserve','submitted','defer')
   OR (role='viewer' AND operation NOT IN('policy','snapshot')) THEN
   RAISE EXCEPTION 'Execution operation denied' USING ERRCODE='42501';
  END IF;
  IF operation='snapshot' AND role<>'admin' THEN RAISE EXCEPTION 'Admin required' USING ERRCODE='42501'; END IF;
 END IF;
 SELECT * INTO p FROM dation_private.execution_dispatch_policy WHERE singleton;
 IF operation='policy' THEN
  RETURN jsonb_build_object('enabled',p.enabled,'admissions_open',p.admissions_open,
   'max_compute',p.max_compute,'max_control',p.max_control,'workspace_daily_limit',p.workspace_daily_limit,
   'global_daily_limit',p.global_daily_limit,'recovery_interval_seconds',900,'last_recovery_at',p.last_recovery_at,
   'recovery_fresh',p.last_recovery_at IS NOT NULL AND p.last_recovery_at>stamp-interval '30 minutes',
   'dispatch_budget_available',p.delivery_day<CURRENT_DATE OR p.deliveries_today<p.delivery_daily_limit);
 ELSIF operation='configure' THEN
  old_enabled:=p.enabled;
  UPDATE dation_private.execution_dispatch_policy SET enabled=coalesce((arguments->>'enabled')::boolean,enabled),
   admissions_open=coalesce((arguments->>'admissions_open')::boolean,admissions_open),
   max_compute=coalesce((arguments->>'max_compute')::integer,max_compute),
   workspace_daily_limit=coalesce((arguments->>'workspace_daily_limit')::integer,workspace_daily_limit),
   global_daily_limit=coalesce((arguments->>'global_daily_limit')::integer,global_daily_limit),
   delivery_daily_limit=coalesce((arguments->>'delivery_daily_limit')::integer,delivery_daily_limit)
   WHERE singleton RETURNING * INTO p;
  IF p.enabled AND NOT old_enabled THEN
   FOR j IN SELECT * FROM public.dispatch_run_jobs WHERE state IN('queued','running') LOOP
    PERFORM dation_private.queue_execution_signal('dispatch',j.run_id,j.workspace_id,NULL,j.available_at,j.deadline_at,false);
   END LOOP;
   FOR a IN SELECT * FROM public.decision_comparative_analyses WHERE status IN('queued','running') LOOP
    PERFORM dation_private.queue_execution_signal('comparative',a.id,a.workspace_id,a.generation,a.available_at,a.deadline_at,false);
   END LOOP;
   FOR c IN SELECT * FROM public.decision_case_reconciliations LOOP
    PERFORM dation_private.queue_execution_signal('reconciliation',c.case_id,c.workspace_id,c.version,c.available_at,stamp+interval '30 minutes',false);
   END LOOP;
  END IF;
  RETURN jsonb_build_object('enabled',p.enabled,'admissions_open',p.admissions_open);
 ELSIF operation='snapshot' THEN
  SELECT jsonb_build_object('pending',count(*) FILTER(WHERE state IN('pending','dispatching','submitted')),
   'running',count(*) FILTER(WHERE state='running'),'dead',count(*) FILTER(WHERE state='dead'),
   'expired_leases',count(*) FILTER(WHERE state IN('dispatching','submitted','running') AND lease_expires_at<stamp),
   'oldest_pending_seconds',coalesce(max(extract(epoch FROM stamp-available_at)) FILTER(WHERE state NOT IN('done','dead')),0))
   INTO answer FROM dation_private.execution_outbox WHERE is_global OR workspace_id=target_workspace_id;
  RETURN answer;
 ELSIF operation='recover' THEN
  IF NOT p.enabled THEN RETURN jsonb_build_object('enabled',false); END IF;
  PERFORM dation_private.maintain_execution_work();
  UPDATE dation_private.execution_dispatch_policy SET last_recovery_at=clock_timestamp() WHERE singleton;
  RETURN jsonb_build_object('enabled',true,'recovered_at',clock_timestamp());
 ELSIF operation='reserve' THEN
  IF NOT p.enabled THEN RETURN result; END IF;
  PERFORM pg_advisory_xact_lock(701921);
  UPDATE dation_private.execution_dispatch_policy SET
   deliveries_today=CASE WHEN delivery_day<CURRENT_DATE THEN 0 ELSE deliveries_today END,delivery_day=CURRENT_DATE
   WHERE singleton RETURNING * INTO p;
  stamp:=clock_timestamp();
  IF p.deliveries_today>=p.delivery_daily_limit THEN RETURN result; END IF;
  FOR o IN SELECT * FROM dation_private.execution_outbox
   WHERE state NOT IN('done','dead') AND available_at<=stamp AND deadline_at>stamp AND delivery_attempts<3
    AND (state='pending' OR lease_expires_at<=stamp)
    AND (is_global OR workspace_id=target_workspace_id)
    AND (kind_filter IS NULL OR kind=kind_filter)
    AND (arguments->>'entity_id' IS NULL OR entity_id=(arguments->>'entity_id')::uuid)
   ORDER BY CASE WHEN kind='reconciliation' THEN 1 ELSE 0 END,available_at,created_at
   FOR UPDATE SKIP LOCKED
  LOOP
   source:=dation_private.execution_source(o.kind,o.entity_id);
   IF source IS NULL OR source->>'state' IN('completed','error') THEN
    UPDATE dation_private.execution_outbox SET state='done',finished_at=stamp,lease_expires_at=NULL WHERE id=o.id;
    CONTINUE;
   END IF;
   IF source->>'state'='running' AND (source->>'lease_expires_at')::timestamptz>stamp THEN
    UPDATE dation_private.execution_outbox SET lease_expires_at=(source->>'lease_expires_at')::timestamptz WHERE id=o.id;
    CONTINUE;
   END IF;
   capacity:=CASE WHEN o.kind='reconciliation' THEN p.max_control ELSE p.max_compute END;
   SELECT count(*) INTO active FROM dation_private.execution_outbox
    WHERE state IN('dispatching','submitted','running') AND lease_expires_at>stamp
     AND ((kind='reconciliation')=(o.kind='reconciliation'));
   IF active>=capacity THEN CONTINUE; END IF;
   UPDATE dation_private.execution_outbox SET state='dispatching',delivery_token=gen_random_uuid(),
    lease_expires_at=least(deadline_at,stamp+interval '5 minutes'),reserved_at=stamp,delivery_attempts=delivery_attempts+1,
    updated_at=stamp,last_error=NULL WHERE id=o.id RETURNING * INTO selected;
   UPDATE dation_private.execution_dispatch_policy SET deliveries_today=deliveries_today+1 WHERE singleton RETURNING * INTO p;
   result:=result||jsonb_build_array(to_jsonb(selected));
   IF jsonb_array_length(result)>=greatest(1,least(coalesce((arguments->>'limit')::integer,1),3))
    OR p.deliveries_today>=p.delivery_daily_limit THEN EXIT; END IF;
  END LOOP;
  RETURN result;
 END IF;
 target:=(arguments->>'intent_id')::uuid;token:=(arguments->>'delivery_token')::uuid;
 SELECT * INTO o FROM dation_private.execution_outbox WHERE id=target;
 IF NOT FOUND THEN RETURN jsonb_build_object('outcome','missing'); END IF;
 IF NOT is_global AND o.workspace_id<>target_workspace_id THEN RAISE EXCEPTION 'Intent not found' USING ERRCODE='P0002'; END IF;
 IF operation='claim' THEN
  -- Source first, then outbox: same order as terminal/reconciliation triggers.
  IF o.kind='dispatch' THEN SELECT * INTO j FROM public.dispatch_run_jobs WHERE run_id=o.entity_id FOR UPDATE;
  ELSIF o.kind='comparative' THEN SELECT * INTO a FROM public.decision_comparative_analyses WHERE id=o.entity_id FOR UPDATE;
  ELSE SELECT * INTO c FROM public.decision_case_reconciliations WHERE case_id=o.entity_id FOR UPDATE;
  END IF;
  SELECT * INTO o FROM dation_private.execution_outbox WHERE id=target FOR UPDATE;
  stamp:=clock_timestamp();
  IF o.delivery_token IS DISTINCT FROM token OR o.state='dead' THEN RETURN jsonb_build_object('outcome','stale'); END IF;
  IF o.state='done' THEN RETURN jsonb_build_object('outcome','terminal'); END IF;
  IF o.state='running' AND o.lease_expires_at>stamp THEN RETURN jsonb_build_object('outcome','busy'); END IF;
  IF o.lease_expires_at<=stamp OR o.deadline_at<=stamp THEN RETURN jsonb_build_object('outcome','stale'); END IF;
  source:=dation_private.execution_source(o.kind,o.entity_id);
  IF source IS NULL OR source->>'state' IN('completed','error') THEN
   UPDATE dation_private.execution_outbox SET state='done',finished_at=stamp,lease_expires_at=NULL WHERE id=target;
   RETURN jsonb_build_object('outcome','terminal');
  END IF;
  IF source->>'state'='running' AND (source->>'lease_expires_at')::timestamptz>stamp THEN RETURN jsonb_build_object('outcome','busy'); END IF;
  IF o.kind<>'reconciliation' AND ((source->>'attempts')::integer >= (source->>'max_attempts')::integer
   OR (source->>'deadline_at')::timestamptz<=stamp) THEN RETURN jsonb_build_object('outcome','expired'); END IF;
  IF o.kind='dispatch' THEN
   UPDATE public.dispatch_run_jobs SET state='running',attempts=attempts+1,lease_token=token,heartbeat_at=stamp,
    lease_expires_at=least(deadline_at,stamp+interval '120 seconds') WHERE run_id=o.entity_id RETURNING * INTO j;
   UPDATE public.decision_runs SET status='running',started_at=coalesce(started_at,stamp),error_message=NULL,
    progress_json=jsonb_build_object('stage','validating','attempt',j.attempts) WHERE id=o.entity_id AND status IN('queued','running');
   answer:=to_jsonb(j);
  ELSIF o.kind='comparative' THEN
   UPDATE public.decision_comparative_analyses SET status='running',attempts=attempts+1,lease_token=token,heartbeat_at=stamp,
    started_at=coalesce(started_at,stamp),lease_expires_at=least(deadline_at,stamp+interval '120 seconds'),
    progress_json=jsonb_build_object('stage','validating','attempt',attempts+1)
    WHERE id=o.entity_id RETURNING * INTO a;
   answer:=to_jsonb(a);
  ELSE
   IF c.version IS DISTINCT FROM o.source_version THEN RETURN jsonb_build_object('outcome','stale'); END IF;
   answer:=to_jsonb(c);
  END IF;
  UPDATE dation_private.execution_outbox SET state='running',lease_expires_at=least(deadline_at,stamp+interval '120 seconds'),
   updated_at=stamp WHERE id=target RETURNING * INTO o;
  RETURN jsonb_build_object('outcome','claimed','intent',to_jsonb(o),'job',answer);
 ELSIF operation='ack_case' THEN
  SELECT * INTO c FROM public.decision_case_reconciliations WHERE case_id=o.entity_id FOR UPDATE;
  SELECT * INTO o FROM dation_private.execution_outbox WHERE id=target FOR UPDATE;
  stamp:=clock_timestamp();
  IF o.kind<>'reconciliation' OR o.delivery_token IS DISTINCT FROM token OR o.state<>'running' OR o.lease_expires_at<=stamp
   OR c.version IS DISTINCT FROM (arguments->>'source_version')::bigint
   OR c.updated_at IS DISTINCT FROM (arguments->>'source_updated_at')::timestamptz THEN RETURN 'false'; END IF;
  DELETE FROM public.decision_case_reconciliations WHERE case_id=o.entity_id AND version=c.version AND updated_at=c.updated_at;
  GET DIAGNOSTICS affected=ROW_COUNT;
  RETURN to_jsonb(affected=1);
 END IF;
 SELECT * INTO o FROM dation_private.execution_outbox WHERE id=target FOR UPDATE;
 stamp:=clock_timestamp();
 IF o.delivery_token IS DISTINCT FROM token THEN RETURN 'false'; END IF;
 IF operation='submitted' THEN
  IF length(coalesce(arguments->>'provider_operation',''))>512 THEN RAISE EXCEPTION 'Invalid provider reference'; END IF;
  UPDATE dation_private.execution_outbox SET provider_operation=arguments->>'provider_operation',
   submitted_at=coalesce(submitted_at,stamp),state=CASE WHEN state='dispatching' THEN 'submitted' ELSE state END
   WHERE id=target;
  RETURN 'true';
 ELSIF operation='defer' THEN
  UPDATE dation_private.execution_outbox SET last_error=CASE WHEN arguments->>'code' IN('provider_timeout','provider_unavailable','provider_rejected','not_configured')
   THEN arguments->>'code' ELSE 'provider_unavailable' END WHERE id=target AND state<>'done';
  -- Ambiguous provider ACK retains its token until the startup lease expires.
  RETURN 'true';
 ELSIF operation='heartbeat' THEN
  source:=dation_private.execution_source(o.kind,o.entity_id);
  IF o.state='done' THEN RETURN jsonb_build_object('alive',false,'terminal',true); END IF;
  IF o.state<>'running' OR o.lease_expires_at<=stamp OR o.deadline_at<=stamp THEN RETURN jsonb_build_object('alive',false,'terminal',false); END IF;
  IF o.kind<>'reconciliation' AND (source->>'state'<>'running' OR source->>'lease_token' IS DISTINCT FROM token::text
   OR (source->>'lease_expires_at')::timestamptz<=stamp) THEN RETURN jsonb_build_object('alive',false,'terminal',false); END IF;
  UPDATE dation_private.execution_outbox SET lease_expires_at=least(deadline_at,stamp+interval '120 seconds'),updated_at=stamp WHERE id=target;
  RETURN jsonb_build_object('alive',true,'terminal',false);
 ELSIF operation='ack' THEN
  source:=dation_private.execution_source(o.kind,o.entity_id);
  IF (o.kind='reconciliation' AND source IS NULL) OR (o.kind<>'reconciliation' AND source->>'state' IN('completed','error')) THEN
   UPDATE dation_private.execution_outbox SET state='done',finished_at=coalesce(finished_at,stamp),lease_expires_at=NULL WHERE id=target;
   RETURN 'true';
  END IF;
  RETURN 'false';
 END IF;
 RAISE EXCEPTION 'Unknown execution operation' USING ERRCODE='22023';
END; $fn$;
REVOKE ALL ON FUNCTION dation_private.execution_source(text,uuid),dation_private.maintain_execution_work(),
 public.execution_runtime(text,jsonb,uuid,uuid) FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.execution_runtime(text,jsonb,uuid,uuid) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
