-- Platform MVP Phase 2. Additive identity, ownership and fail-closed RPC boundary.
-- Apply only after backup/restore and draining the queue. New Auth admissions remain
-- closed until BOTH API and worker revisions are deployed; see the release runbook.
BEGIN;
CREATE SCHEMA dation_private;
REVOKE ALL ON SCHEMA dation_private FROM PUBLIC,anon,authenticated,service_role;
CREATE TABLE public.workspaces (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL CHECK(length(trim(name)) BETWEEN 2 AND 120),
 country text NOT NULL DEFAULT 'AR' CHECK(country ~ '^[A-Z]{2}$'),
 timezone text NOT NULL DEFAULT 'America/Argentina/Buenos_Aires', language text NOT NULL DEFAULT 'es',
 currency text NOT NULL DEFAULT 'ARS' CHECK(currency ~ '^[A-Z]{3}$'), weight_unit text NOT NULL DEFAULT 'kg',
 distance_unit text NOT NULL DEFAULT 'km', logistics_unit text NOT NULL DEFAULT 'units',
 status text NOT NULL DEFAULT 'active' CHECK(status IN('active','disabled')),
 created_by uuid REFERENCES auth.users(id), created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.profiles (
 id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
 first_name text NOT NULL DEFAULT '' CHECK(length(first_name)<=100), last_name text NOT NULL DEFAULT '' CHECK(length(last_name)<=100),
 display_name text NOT NULL DEFAULT '', avatar_url text, active_workspace_id uuid REFERENCES public.workspaces(id),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.workspace_members (
 workspace_id uuid NOT NULL REFERENCES public.workspaces(id), user_id uuid NOT NULL REFERENCES auth.users(id),
 access_role text NOT NULL CHECK(access_role IN('admin','operator','viewer')), business_role text,
 status text NOT NULL DEFAULT 'active' CHECK(status IN('invited','active','disabled')),
 invited_by uuid REFERENCES auth.users(id), joined_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(workspace_id,user_id)
);
CREATE INDEX workspace_members_user_idx ON public.workspace_members(user_id,status,workspace_id);
CREATE TABLE public.workspace_ddas (
 workspace_id uuid NOT NULL REFERENCES public.workspaces(id), dda_id text NOT NULL,
 status text NOT NULL CHECK(status IN('enabled','disabled','coming_soon')),
 configuration_json jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(workspace_id,dda_id), CHECK(dda_id IN('logistics','production','inventory','demand','purchasing','maintenance','pricing'))
);
CREATE TABLE public.audit_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES public.workspaces(id),
 actor_user_id uuid REFERENCES auth.users(id), event_type text NOT NULL, metadata_json jsonb NOT NULL DEFAULT '{}',
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX audit_events_workspace_time_idx ON public.audit_events(workspace_id,created_at DESC,id DESC);
CREATE TABLE dation_private.platform_release (singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), admissions_open boolean NOT NULL DEFAULT false);
INSERT INTO dation_private.platform_release VALUES(true,false);
CREATE TABLE dation_private.legacy_owners (email text PRIMARY KEY,workspace_id uuid NOT NULL REFERENCES public.workspaces(id),claimed_by uuid REFERENCES auth.users(id));
INSERT INTO public.workspaces(id,name) VALUES('00000000-0000-4000-8000-00000000da71','Dation');
-- The authorized email is bound by the release script, never by the first signup.
INSERT INTO public.workspace_ddas(workspace_id,dda_id,status)
 SELECT '00000000-0000-4000-8000-00000000da71',id,CASE WHEN id='logistics' THEN 'enabled' ELSE 'coming_soon' END
 FROM unnest(ARRAY['logistics','production','inventory','demand','purchasing','maintenance','pricing']) id;
CREATE FUNCTION dation_private.workspace_id() RETURNS uuid LANGUAGE sql STABLE AS $$
 SELECT nullif(current_setting('dation.workspace_id',true),'')::uuid;
$$;
-- Only the newly added ownership field is backfilled; immutable evidence is unchanged.
CREATE OR REPLACE FUNCTION public.reject_approval_event_mutation() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 IF TG_OP='UPDATE' AND OLD.workspace_id IS NULL AND NEW.workspace_id='00000000-0000-4000-8000-00000000da71'
    AND (to_jsonb(NEW)-'workspace_id')=(to_jsonb(OLD)-'workspace_id')
    AND current_setting('dation.ownership_backfill',true)='enabled' AND current_user='postgres' THEN RETURN NEW; END IF;
 RAISE EXCEPTION USING ERRCODE='22023',MESSAGE='Los eventos de aprobación son inmutables';
END; $$;
SELECT set_config('dation.ownership_backfill','enabled',true);
CREATE OR REPLACE FUNCTION public.protect_comparative_analysis()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
 IF OLD.workspace_id IS NULL AND NEW.workspace_id='00000000-0000-4000-8000-00000000da71' AND (to_jsonb(NEW)-'workspace_id')=(to_jsonb(OLD)-'workspace_id') AND current_setting('dation.ownership_backfill',true)='enabled' AND current_user='postgres' THEN RETURN NEW; END IF;

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
END; $function$
;
ALTER TABLE public.datasets ADD COLUMN workspace_id uuid REFERENCES public.workspaces(id);
UPDATE public.datasets SET workspace_id='00000000-0000-4000-8000-00000000da71';
ALTER TABLE public.datasets ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE public.datasets ALTER COLUMN workspace_id SET DEFAULT dation_private.workspace_id();
CREATE UNIQUE INDEX datasets_workspace_identity ON public.datasets(workspace_id,id);
ALTER TABLE public.decision_cases ADD COLUMN workspace_id uuid REFERENCES public.workspaces(id);
UPDATE public.decision_cases SET workspace_id='00000000-0000-4000-8000-00000000da71';
ALTER TABLE public.decision_cases ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE public.decision_cases ALTER COLUMN workspace_id SET DEFAULT dation_private.workspace_id();
CREATE UNIQUE INDEX decision_cases_workspace_identity ON public.decision_cases(workspace_id,id);
ALTER TABLE public.decision_runs ADD COLUMN workspace_id uuid REFERENCES public.workspaces(id);
UPDATE public.decision_runs SET workspace_id='00000000-0000-4000-8000-00000000da71';
ALTER TABLE public.decision_runs ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE public.decision_runs ALTER COLUMN workspace_id SET DEFAULT dation_private.workspace_id();
CREATE UNIQUE INDEX decision_runs_workspace_identity ON public.decision_runs(workspace_id,id);
ALTER TABLE public.dispatch_run_jobs ADD COLUMN workspace_id uuid REFERENCES public.workspaces(id);
UPDATE public.dispatch_run_jobs SET workspace_id='00000000-0000-4000-8000-00000000da71';
ALTER TABLE public.dispatch_run_jobs ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE public.dispatch_run_jobs ALTER COLUMN workspace_id SET DEFAULT dation_private.workspace_id();
CREATE UNIQUE INDEX dispatch_run_jobs_workspace_identity ON public.dispatch_run_jobs(workspace_id,run_id);
ALTER TABLE public.decision_case_reconciliations ADD COLUMN workspace_id uuid REFERENCES public.workspaces(id);
UPDATE public.decision_case_reconciliations SET workspace_id='00000000-0000-4000-8000-00000000da71';
ALTER TABLE public.decision_case_reconciliations ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE public.decision_case_reconciliations ALTER COLUMN workspace_id SET DEFAULT dation_private.workspace_id();
CREATE UNIQUE INDEX decision_case_reconciliations_workspace_identity ON public.decision_case_reconciliations(workspace_id,case_id);
ALTER TABLE public.decision_approval_events ADD COLUMN workspace_id uuid REFERENCES public.workspaces(id);
UPDATE public.decision_approval_events SET workspace_id='00000000-0000-4000-8000-00000000da71';
ALTER TABLE public.decision_approval_events ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE public.decision_approval_events ALTER COLUMN workspace_id SET DEFAULT dation_private.workspace_id();
CREATE UNIQUE INDEX decision_approval_events_workspace_identity ON public.decision_approval_events(workspace_id,id);
ALTER TABLE public.decision_comparative_analyses ADD COLUMN workspace_id uuid REFERENCES public.workspaces(id);
UPDATE public.decision_comparative_analyses SET workspace_id='00000000-0000-4000-8000-00000000da71';
ALTER TABLE public.decision_comparative_analyses ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE public.decision_comparative_analyses ALTER COLUMN workspace_id SET DEFAULT dation_private.workspace_id();
CREATE UNIQUE INDEX decision_comparative_analyses_workspace_identity ON public.decision_comparative_analyses(workspace_id,id);
ALTER TABLE public.decision_explanations ADD COLUMN workspace_id uuid REFERENCES public.workspaces(id);
UPDATE public.decision_explanations SET workspace_id='00000000-0000-4000-8000-00000000da71';
ALTER TABLE public.decision_explanations ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE public.decision_explanations ALTER COLUMN workspace_id SET DEFAULT dation_private.workspace_id();
CREATE UNIQUE INDEX decision_explanations_workspace_identity ON public.decision_explanations(workspace_id,id);
ALTER TABLE public.decision_messages ADD COLUMN workspace_id uuid REFERENCES public.workspaces(id);
UPDATE public.decision_messages SET workspace_id='00000000-0000-4000-8000-00000000da71';
ALTER TABLE public.decision_messages ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE public.decision_messages ALTER COLUMN workspace_id SET DEFAULT dation_private.workspace_id();
CREATE UNIQUE INDEX decision_messages_workspace_identity ON public.decision_messages(workspace_id,id);
ALTER TABLE public.decision_chat_turns ADD COLUMN workspace_id uuid REFERENCES public.workspaces(id);
UPDATE public.decision_chat_turns SET workspace_id='00000000-0000-4000-8000-00000000da71';
ALTER TABLE public.decision_chat_turns ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE public.decision_chat_turns ALTER COLUMN workspace_id SET DEFAULT dation_private.workspace_id();
CREATE UNIQUE INDEX decision_chat_turns_workspace_identity ON public.decision_chat_turns(workspace_id,turn_id);
ALTER TABLE public.decision_interpretation_sources ADD COLUMN workspace_id uuid REFERENCES public.workspaces(id);
UPDATE public.decision_interpretation_sources SET workspace_id='00000000-0000-4000-8000-00000000da71';
ALTER TABLE public.decision_interpretation_sources ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE public.decision_interpretation_sources ALTER COLUMN workspace_id SET DEFAULT dation_private.workspace_id();
CREATE UNIQUE INDEX decision_interpretation_sources_workspace_identity ON public.decision_interpretation_sources(workspace_id,id);
SELECT set_config('dation.ownership_backfill','',true);
CREATE OR REPLACE FUNCTION public.reject_approval_event_mutation() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN RAISE EXCEPTION USING ERRCODE='22023',MESSAGE='Los eventos de aprobación son inmutables'; END; $$;
CREATE OR REPLACE FUNCTION public.protect_comparative_analysis()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
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
END; $function$
;
ALTER TABLE public.datasets ADD CONSTRAINT tenant_datasets_parent_dataset_id FOREIGN KEY(workspace_id,parent_dataset_id) REFERENCES public.datasets(workspace_id,id);
ALTER TABLE public.decision_cases ADD CONSTRAINT tenant_decision_cases_orders_dataset_id FOREIGN KEY(workspace_id,orders_dataset_id) REFERENCES public.datasets(workspace_id,id);
ALTER TABLE public.decision_cases ADD CONSTRAINT tenant_decision_cases_fleet_dataset_id FOREIGN KEY(workspace_id,fleet_dataset_id) REFERENCES public.datasets(workspace_id,id);
ALTER TABLE public.decision_runs ADD CONSTRAINT tenant_decision_runs_dataset_id FOREIGN KEY(workspace_id,dataset_id) REFERENCES public.datasets(workspace_id,id);
ALTER TABLE public.decision_runs ADD CONSTRAINT tenant_decision_runs_orders_dataset_id FOREIGN KEY(workspace_id,orders_dataset_id) REFERENCES public.datasets(workspace_id,id);
ALTER TABLE public.decision_runs ADD CONSTRAINT tenant_decision_runs_fleet_dataset_id FOREIGN KEY(workspace_id,fleet_dataset_id) REFERENCES public.datasets(workspace_id,id);
ALTER TABLE public.decision_runs ADD CONSTRAINT tenant_decision_runs_decision_case_id FOREIGN KEY(workspace_id,decision_case_id) REFERENCES public.decision_cases(workspace_id,id);
ALTER TABLE public.decision_runs ADD CONSTRAINT tenant_decision_runs_upstream_run_id FOREIGN KEY(workspace_id,upstream_run_id) REFERENCES public.decision_runs(workspace_id,id);
ALTER TABLE public.decision_runs ADD CONSTRAINT tenant_decision_runs_superseded_by_run_id FOREIGN KEY(workspace_id,superseded_by_run_id) REFERENCES public.decision_runs(workspace_id,id);
ALTER TABLE public.dispatch_run_jobs ADD CONSTRAINT tenant_dispatch_run_jobs_run_id FOREIGN KEY(workspace_id,run_id) REFERENCES public.decision_runs(workspace_id,id);
ALTER TABLE public.decision_case_reconciliations ADD CONSTRAINT tenant_decision_case_reconciliations_case_id FOREIGN KEY(workspace_id,case_id) REFERENCES public.decision_cases(workspace_id,id);
ALTER TABLE public.decision_approval_events ADD CONSTRAINT tenant_decision_approval_events_run_id FOREIGN KEY(workspace_id,run_id) REFERENCES public.decision_runs(workspace_id,id);
ALTER TABLE public.decision_approval_events ADD CONSTRAINT tenant_decision_approval_events_case_id FOREIGN KEY(workspace_id,case_id) REFERENCES public.decision_cases(workspace_id,id);
ALTER TABLE public.decision_approval_events ADD CONSTRAINT tenant_decision_approval_events_replacement_run_id FOREIGN KEY(workspace_id,replacement_run_id) REFERENCES public.decision_runs(workspace_id,id);
ALTER TABLE public.decision_comparative_analyses ADD CONSTRAINT tenant_decision_comparative_analyses_base_run_id FOREIGN KEY(workspace_id,base_run_id) REFERENCES public.decision_runs(workspace_id,id);
ALTER TABLE public.decision_explanations ADD CONSTRAINT tenant_decision_explanations_run_id FOREIGN KEY(workspace_id,run_id) REFERENCES public.decision_runs(workspace_id,id);
ALTER TABLE public.decision_messages ADD CONSTRAINT tenant_decision_messages_run_id FOREIGN KEY(workspace_id,run_id) REFERENCES public.decision_runs(workspace_id,id);
ALTER TABLE public.decision_messages ADD CONSTRAINT tenant_decision_messages_turn_id FOREIGN KEY(workspace_id,turn_id) REFERENCES public.decision_chat_turns(workspace_id,turn_id);
ALTER TABLE public.decision_chat_turns ADD CONSTRAINT tenant_decision_chat_turns_run_id FOREIGN KEY(workspace_id,run_id) REFERENCES public.decision_runs(workspace_id,id);
ALTER TABLE public.decision_interpretation_sources ADD CONSTRAINT tenant_decision_interpretation_sources_run_id FOREIGN KEY(workspace_id,run_id) REFERENCES public.decision_runs(workspace_id,id);
ALTER TABLE public.decision_interpretation_sources ADD CONSTRAINT tenant_decision_interpretation_sources_analysis_id FOREIGN KEY(workspace_id,analysis_id) REFERENCES public.decision_comparative_analyses(workspace_id,id);
ALTER TABLE public.decision_interpretation_sources ADD CONSTRAINT tenant_decision_interpretation_sources_explanation_id FOREIGN KEY(workspace_id,explanation_id) REFERENCES public.decision_explanations(workspace_id,id);
ALTER TABLE public.decision_interpretation_sources ADD CONSTRAINT tenant_decision_interpretation_sources_chat_turn_id FOREIGN KEY(workspace_id,chat_turn_id) REFERENCES public.decision_chat_turns(workspace_id,turn_id);
DROP INDEX public.datasets_dispatch_hash_key;
CREATE UNIQUE INDEX datasets_dispatch_hash_key ON public.datasets(workspace_id,dataset_type,sha256)
 WHERE dataset_type IN('orders','fleet') AND sha256 IS NOT NULL;
DROP INDEX public.datasets_one_default_per_type;
CREATE UNIQUE INDEX datasets_one_default_per_type ON public.datasets(workspace_id,dataset_type) WHERE is_default;
CREATE INDEX datasets_workspace_created ON public.datasets(workspace_id,created_at DESC,id DESC);
CREATE INDEX cases_workspace_activity ON public.decision_cases(workspace_id,status,last_activity_at DESC,id DESC);
CREATE INDEX runs_workspace_created ON public.decision_runs(workspace_id,created_at DESC,id DESC);
ALTER TABLE public.decision_runs DROP CONSTRAINT decision_runs_approved_by_check;
ALTER TABLE public.decision_runs ADD CONSTRAINT decision_runs_approved_by_check CHECK(approved_by IS NULL OR
 (approved_at IS NOT NULL AND (approved_by='shared_workspace:dation' OR approved_by ~ '^user:[0-9a-f-]{36}$')));
ALTER TABLE public.decision_approval_events DROP CONSTRAINT decision_approval_events_actor_check;
ALTER TABLE public.decision_approval_events ADD CONSTRAINT decision_approval_events_actor_check CHECK(
 actor='shared_workspace:dation' OR actor ~ '^user:[0-9a-f-]{36}$');
ALTER TABLE public.decision_runs ADD COLUMN approved_by_user_id uuid REFERENCES auth.users(id);
ALTER TABLE public.decision_approval_events ADD COLUMN actor_user_id uuid REFERENCES auth.users(id);
CREATE FUNCTION dation_private.protect_workspace() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 IF NEW.workspace_id IS DISTINCT FROM OLD.workspace_id THEN RAISE EXCEPTION 'Workspace ownership is immutable' USING ERRCODE='22023'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER datasets_workspace_immutable BEFORE UPDATE ON public.datasets FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workspace();
CREATE TRIGGER decision_cases_workspace_immutable BEFORE UPDATE ON public.decision_cases FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workspace();
CREATE TRIGGER decision_runs_workspace_immutable BEFORE UPDATE ON public.decision_runs FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workspace();
CREATE TRIGGER dispatch_run_jobs_workspace_immutable BEFORE UPDATE ON public.dispatch_run_jobs FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workspace();
CREATE TRIGGER decision_case_reconciliations_workspace_immutable BEFORE UPDATE ON public.decision_case_reconciliations FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workspace();
CREATE TRIGGER decision_approval_events_workspace_immutable BEFORE UPDATE ON public.decision_approval_events FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workspace();
CREATE TRIGGER decision_comparative_analyses_workspace_immutable BEFORE UPDATE ON public.decision_comparative_analyses FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workspace();
CREATE TRIGGER decision_explanations_workspace_immutable BEFORE UPDATE ON public.decision_explanations FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workspace();
CREATE TRIGGER decision_messages_workspace_immutable BEFORE UPDATE ON public.decision_messages FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workspace();
CREATE TRIGGER decision_chat_turns_workspace_immutable BEFORE UPDATE ON public.decision_chat_turns FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workspace();
CREATE TRIGGER decision_interpretation_sources_workspace_immutable BEFORE UPDATE ON public.decision_interpretation_sources FOR EACH ROW EXECUTE FUNCTION dation_private.protect_workspace();
ALTER FUNCTION public.ack_case_reconciliation(target_case_id uuid, observed_version bigint) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.ack_case_reconciliation(target_case_id uuid, observed_version bigint)
 RETURNS void
 LANGUAGE sql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
    delete from public.decision_case_reconciliations
    where case_id=target_case_id and version=observed_version;
$function$
;
ALTER FUNCTION public.approve_decision_run_version(target_run_id uuid, target_case_id uuid, target_node_id text) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.approve_decision_run_version(target_run_id uuid, target_case_id uuid, target_node_id text)
 RETURNS SETOF decision_runs
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
DECLARE target public.decision_runs%rowtype; source public.decision_runs%rowtype;
 approval_time timestamptz;
BEGIN
 -- Lock the shared case first, before any candidate. This also serializes parent/child approvals.
 PERFORM 1 FROM public.decision_cases WHERE id=target_case_id FOR UPDATE;
 SELECT * INTO target FROM public.decision_runs WHERE id=target_run_id FOR UPDATE;
 IF NOT FOUND OR target.status<>'completed' OR target.decision_case_id IS DISTINCT FROM target_case_id
    OR target.node_id IS DISTINCT FROM target_node_id OR NOT (
      target_node_id='logistics_assignment' AND target.schema_version='assignment_v1'
      OR target_node_id='logistics_scheduling' AND target.schema_version='scheduling_v1') THEN
   RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='La corrida no puede aprobarse para ese Decision Case';
 END IF;
 IF target.superseded_at IS NOT NULL THEN
   RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Una aprobación anterior no puede reactivarse; ejecutá una nueva alternativa';
 END IF;
 IF target.upstream_run_id IS NOT NULL THEN
   SELECT * INTO source FROM public.decision_runs WHERE id=target.upstream_run_id;
   IF NOT FOUND OR source.decision_case_id IS DISTINCT FROM target_case_id
     OR source.status<>'completed' OR source.approved_at IS NULL OR source.superseded_at IS NOT NULL THEN
     RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='La corrida upstream ya no es la decisión aprobada vigente';
   END IF;
 END IF;
 IF target.approved_at IS NOT NULL THEN
   RETURN NEXT target; RETURN; -- A retry preserves actor/time and emits no second event.
 END IF;
 -- Date the approval after acquiring the case lock, not when the waiting request began.
 approval_time := clock_timestamp();
 INSERT INTO public.decision_approval_events(run_id,case_id,node_id,action,actor,actor_user_id,occurred_at,replacement_run_id)
   SELECT id,target_case_id,target_node_id,'superseded',('user:'||current_setting('dation.actor_user_id')),current_setting('dation.actor_user_id')::uuid,approval_time,target_run_id
   FROM public.decision_runs WHERE decision_case_id=target_case_id AND node_id=target_node_id
     AND approved_at IS NOT NULL AND superseded_at IS NULL;
 UPDATE public.decision_runs SET superseded_at=approval_time,superseded_by_run_id=target_run_id
   WHERE decision_case_id=target_case_id AND node_id=target_node_id AND id<>target_run_id
     AND approved_at IS NOT NULL AND superseded_at IS NULL;
 UPDATE public.decision_runs SET approved_at=approval_time,approved_by=('user:'||current_setting('dation.actor_user_id')),approved_by_user_id=current_setting('dation.actor_user_id')::uuid,
   configuration_json=jsonb_set(configuration_json,'{decision_case}',
     coalesce(configuration_json->'decision_case','{}'::jsonb)||jsonb_build_object(
       'case_id',target_case_id::text,'node_id',target_node_id,'status','approved','approved_at',approval_time)),
   result_json=jsonb_set(result_json,'{decision_case}',
     coalesce(result_json->'decision_case','{}'::jsonb)||jsonb_build_object(
       'case_id',target_case_id::text,'node_id',target_node_id,'status','approved','approved_at',approval_time))
   WHERE id=target_run_id;
 INSERT INTO public.decision_approval_events(run_id,case_id,node_id,action,actor,actor_user_id,occurred_at)
   VALUES(target_run_id,target_case_id,target_node_id,'approved',('user:'||current_setting('dation.actor_user_id')),current_setting('dation.actor_user_id')::uuid,approval_time);
 RETURN QUERY SELECT * FROM public.decision_runs WHERE id=target_run_id;
END;
$function$
;
ALTER FUNCTION public.cancel_dispatch_job(target_run_id uuid) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.cancel_dispatch_job(target_run_id uuid)
 RETURNS SETOF decision_runs
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
begin
    perform 1 from public.dispatch_run_jobs where run_id=target_run_id for update;
    if not found then return; end if;
    update public.dispatch_run_jobs set state='error', lease_token=null, lease_expires_at=null
    where run_id=target_run_id and state in ('queued','running');
    if found then
        update public.decision_runs set status='error',finished_at=now(),
          error_message='La ejecución fue cancelada.',
          progress_json=jsonb_build_object('stage','cancelled')
        where id=target_run_id and status in ('queued','running');
    end if;
    return query select * from public.decision_runs where id=target_run_id;
end;
$function$
;
CREATE OR REPLACE FUNCTION public.claim_comparative_analysis(worker_token uuid, lease_seconds integer DEFAULT 120)
 RETURNS SETOF decision_comparative_analyses
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
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
END; $function$
;
CREATE OR REPLACE FUNCTION public.claim_dispatch_job(worker_token uuid, lease_seconds integer DEFAULT 120)
 RETURNS SETOF dispatch_run_jobs
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
declare target public.dispatch_run_jobs%rowtype;
begin
    perform dation_private.maintain_dispatch_jobs();
    select * into target from public.dispatch_run_jobs
    where ((state='queued' and available_at <= now()) or (state='running' and lease_expires_at <= now()))
      and attempts < max_attempts and deadline_at > now()
    order by available_at, created_at for update skip locked limit 1;
    if not found then return; end if;
    update public.dispatch_run_jobs set state='running', attempts=attempts+1,
        lease_token=worker_token, heartbeat_at=now(),
        lease_expires_at=least(deadline_at,now()+make_interval(secs=>greatest(30,least(lease_seconds,300))))
    where run_id=target.run_id;
    update public.decision_runs set status='running', started_at=coalesce(started_at,now()),
        progress_json=jsonb_build_object('stage','validating','attempt',target.attempts+1), error_message=null
    where id=target.run_id and status in ('queued','running');
    return query select * from public.dispatch_run_jobs where run_id=target.run_id;
end;
$function$
;
ALTER FUNCTION public.comparative_operational_snapshot() SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.comparative_operational_snapshot()
 RETURNS jsonb
 LANGUAGE sql
 STABLE
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
 SELECT jsonb_build_object('queued',count(*) FILTER(WHERE status='queued'),'running',count(*) FILTER(WHERE status='running'),
  'expired_leases',count(*) FILTER(WHERE status='running' AND lease_expires_at<statement_timestamp()),
  'retried_active',count(*) FILTER(WHERE status IN('queued','running') AND attempts>1),
  'oldest_queued_seconds',coalesce(max(extract(epoch FROM statement_timestamp()-created_at)) FILTER(WHERE status='queued'),0))
 FROM decision_comparative_analyses WHERE workspace_id=dation_private.workspace_id() AND status IN('queued','running');
$function$
;
ALTER FUNCTION public.current_decision_explanation(target_run_id uuid) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.current_decision_explanation(target_run_id uuid)
 RETURNS SETOF decision_explanations
 LANGUAGE sql
 STABLE
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
 SELECT e.* FROM decision_explanations e
 LEFT JOIN decision_interpretation_sources source ON source.explanation_id=e.id
 LEFT JOIN decision_comparative_analyses a ON a.base_run_id=e.run_id AND a.status='completed'
 WHERE e.run_id=target_run_id
 ORDER BY ((source.analysis_id IS NOT DISTINCT FROM a.id) OR (a.source_mode='existing' AND source.analysis_id IS NULL)) DESC,
  e.created_at DESC,e.id DESC LIMIT 1;
$function$
;
ALTER FUNCTION public.decision_case_history(target_case_id uuid, target_node_id text, page_limit integer, page_offset integer) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.decision_case_history(target_case_id uuid, target_node_id text DEFAULT NULL::text, page_limit integer DEFAULT 50, page_offset integer DEFAULT 0)
 RETURNS jsonb
 LANGUAGE sql
 STABLE
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
 WITH nodes(node_id) AS (VALUES
   ('logistics_assignment'::text),('logistics_scheduling'),('logistics_final_assignment')),
 summaries AS (
   SELECT n.node_id, jsonb_build_object(
     'run_count',(SELECT count(*) FROM decision_runs r WHERE r.decision_case_id=target_case_id AND r.node_id=n.node_id),
     'latest',(SELECT to_jsonb(r)-'result_json' FROM decision_runs r
       WHERE r.decision_case_id=target_case_id AND r.node_id=n.node_id ORDER BY r.created_at DESC,r.id DESC LIMIT 1),
     'approved',(SELECT to_jsonb(r)-'result_json' FROM decision_runs r
       WHERE r.decision_case_id=target_case_id AND r.node_id=n.node_id AND r.approved_at IS NOT NULL AND r.superseded_at IS NULL LIMIT 1)
   ) AS value FROM nodes n
 ), page AS (
   SELECT r.* FROM decision_runs r WHERE r.decision_case_id=target_case_id
     AND (target_node_id IS NULL OR r.node_id=target_node_id)
   ORDER BY r.created_at DESC,r.id DESC
   LIMIT greatest(0,least(page_limit,200)) OFFSET greatest(0,page_offset)
 )
 SELECT jsonb_build_object(
   'summaries',(SELECT jsonb_object_agg(node_id,value) FROM summaries),
   'runs',(SELECT coalesce(jsonb_agg(to_jsonb(p)-'result_json' ORDER BY p.created_at DESC,p.id DESC),'[]'::jsonb) FROM page p)
 );
$function$
;
ALTER FUNCTION public.dispatch_operational_snapshot() SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.dispatch_operational_snapshot()
 RETURNS jsonb
 LANGUAGE sql
 STABLE
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
 SELECT jsonb_build_object(
 'sampled_at',statement_timestamp(),
 'queue',(SELECT jsonb_build_object(
  'queued',count(*) FILTER(WHERE state='queued'),
  'running',count(*) FILTER(WHERE state='running'),
  'retried_active',count(*) FILTER(WHERE state IN('queued','running') AND attempts>1),
  'expired_leases',count(*) FILTER(WHERE state='running' AND lease_expires_at<statement_timestamp()),
  'past_deadline',count(*) FILTER(WHERE state IN('queued','running') AND deadline_at<statement_timestamp()),
  'oldest_queued_seconds',coalesce(max(extract(epoch FROM statement_timestamp()-created_at)) FILTER(WHERE state='queued'),0)
 ) FROM dispatch_run_jobs WHERE workspace_id=dation_private.workspace_id() AND state IN('queued','running')),
 'workers',(SELECT jsonb_build_object('healthy',count(*) FILTER(WHERE ready), 'reporting',count(*))
  FROM dispatch_worker_instances WHERE seen_at>statement_timestamp()-interval '90 seconds'),
 'reconciliation',(SELECT jsonb_build_object('pending',count(*),'retrying',count(*) FILTER(WHERE attempts>0),
  'oldest_pending_seconds',coalesce(max(extract(epoch FROM statement_timestamp()-available_at)) FILTER(WHERE available_at<=statement_timestamp()),0))
  FROM decision_case_reconciliations WHERE workspace_id=dation_private.workspace_id()),
 'runs_24h',(SELECT jsonb_build_object('completed',count(*) FILTER(WHERE status='completed'),
  'errors',count(*) FILTER(WHERE status='error'),'duration_p95_ms',
  percentile_cont(0.95) WITHIN GROUP(ORDER BY duration_ms) FILTER(WHERE status='completed' AND duration_ms IS NOT NULL))
  FROM decision_runs WHERE workspace_id=dation_private.workspace_id() AND created_at>statement_timestamp()-interval '24 hours'),
 'chat_24h',(SELECT jsonb_build_object('turns',count(*),
  'total_tokens',coalesce(sum((usage_json->>'total_tokens')::bigint),0))
  FROM decision_chat_turns WHERE workspace_id=dation_private.workspace_id() AND created_at>statement_timestamp()-interval '24 hours')
 );
$function$
;
CREATE OR REPLACE FUNCTION public.enqueue_case_reconciliation()
 RETURNS trigger
 LANGUAGE plpgsql SECURITY DEFINER
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
begin
    if new.decision_case_id is not null then
        perform dation_private.request_case_reconciliation(new.decision_case_id);
    end if;
    return new;
end;
$function$
;
ALTER FUNCTION public.enqueue_comparative_analysis(target_base_id uuid, job_request jsonb, existing_result jsonb, retry_failed boolean) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.enqueue_comparative_analysis(target_base_id uuid, job_request jsonb, existing_result jsonb DEFAULT NULL::jsonb, retry_failed boolean DEFAULT false)
 RETURNS SETOF decision_comparative_analyses
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
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
END; $function$
;
ALTER FUNCTION public.enqueue_dispatch_run(run_payload jsonb, job_request jsonb, intent_fingerprint text, queue_limit integer) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.enqueue_dispatch_run(run_payload jsonb, job_request jsonb, intent_fingerprint text, queue_limit integer DEFAULT 32)
 RETURNS SETOF decision_runs
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
declare
    existing_job public.dispatch_run_jobs%rowtype;
    target_id uuid := (run_payload ->> 'id')::uuid;
begin
    -- Serialize admission, but never calculation. Replays do not consume capacity.
    perform pg_advisory_xact_lock(701003);
    select * into existing_job from public.dispatch_run_jobs where run_id = target_id;
    if found then
        if existing_job.request_fingerprint is distinct from intent_fingerprint then
            raise exception using errcode = '22023', message = 'run_id ya pertenece a otra intención';
        end if;
        return query select * from public.decision_runs where id = target_id;
        return;
    end if;
    if exists(select 1 from public.decision_runs where id = target_id) then
        raise exception using errcode = '22023', message = 'run_id ya existe';
    end if;
    if (select count(*) from public.dispatch_run_jobs where state in ('queued','running'))
       >= greatest(1, least(queue_limit, 256)) then
        raise exception using errcode = '53300', message = 'La cola de ejecución está llena';
    end if;
    insert into public.decision_runs(
        id, dataset_id, orders_dataset_id, fleet_dataset_id, schema_version,
        engine_name, engine_version, configuration_json, decision_case_id, node_id,
        upstream_run_id, status, progress_json
    ) values (
        target_id, (run_payload ->> 'dataset_id')::uuid,
        (run_payload ->> 'orders_dataset_id')::uuid, (run_payload ->> 'fleet_dataset_id')::uuid,
        run_payload ->> 'schema_version', run_payload ->> 'engine_name', run_payload ->> 'engine_version',
        run_payload -> 'configuration_json', (run_payload ->> 'decision_case_id')::uuid,
        run_payload ->> 'node_id', (run_payload ->> 'upstream_run_id')::uuid,
        'queued', jsonb_build_object('stage','queued')
    );
    insert into public.dispatch_run_jobs(run_id, request_json, request_fingerprint)
    values (target_id, job_request, intent_fingerprint);
    return query select * from public.decision_runs where id = target_id;
end;
$function$
;
ALTER FUNCTION public.finish_comparative_analysis(target_analysis_id uuid, worker_token uuid, terminal_values jsonb) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.finish_comparative_analysis(target_analysis_id uuid, worker_token uuid, terminal_values jsonb)
 RETURNS SETOF decision_comparative_analyses
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
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
END; $function$
;
ALTER FUNCTION public.finish_dispatch_job(target_run_id uuid, worker_token uuid, terminal_values jsonb) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.finish_dispatch_job(target_run_id uuid, worker_token uuid, terminal_values jsonb)
 RETURNS SETOF decision_runs
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
declare target public.dispatch_run_jobs%rowtype; outcome text := terminal_values ->> 'status';
begin
    if outcome not in ('completed','error') then raise exception 'Estado terminal inválido'; end if;
    select * into target from public.dispatch_run_jobs where run_id=target_run_id for update;
    if not found or target.state <> 'running' or target.lease_token is distinct from worker_token
       or target.lease_expires_at <= now() or target.deadline_at <= now() then return; end if;
    if outcome='completed' and (terminal_values -> 'result_json' is null
       or jsonb_typeof(terminal_values -> 'result_json') <> 'object') then
        raise exception 'Falta el resultado completado';
    end if;
    update public.decision_runs set status=outcome, finished_at=now(),
        duration_ms=(terminal_values ->> 'duration_ms')::integer,
        result_json=terminal_values -> 'result_json',
        result_fingerprint=terminal_values ->> 'result_fingerprint',
        input_fingerprint=coalesce(terminal_values ->> 'input_fingerprint',input_fingerprint),
        summary_json=terminal_values -> 'summary_json',
        progress_json=coalesce(terminal_values -> 'progress_json',jsonb_build_object('stage',outcome)),
        error_message=terminal_values ->> 'error_message'
    where id=target_run_id and status='running';
    if not found then return; end if;
    update public.dispatch_run_jobs set state=outcome, lease_token=null, lease_expires_at=null
    where run_id=target_run_id;
    return query select * from public.decision_runs where id=target_run_id;
end;
$function$
;
ALTER FUNCTION public.heartbeat_comparative_analysis(target_analysis_id uuid, worker_token uuid, lease_seconds integer, progress jsonb) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.heartbeat_comparative_analysis(target_analysis_id uuid, worker_token uuid, lease_seconds integer DEFAULT 120, progress jsonb DEFAULT NULL::jsonb)
 RETURNS boolean
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
BEGIN
 UPDATE decision_comparative_analyses SET heartbeat_at=clock_timestamp(),
  lease_expires_at=least(deadline_at,clock_timestamp()+make_interval(secs=>greatest(30,least(lease_seconds,300)))),
  progress_json=coalesce(progress,progress_json)
 WHERE id=target_analysis_id AND status='running' AND lease_token=worker_token AND
  lease_expires_at>clock_timestamp() AND deadline_at>clock_timestamp();
 RETURN FOUND;
END; $function$
;
ALTER FUNCTION public.heartbeat_dispatch_job(target_run_id uuid, worker_token uuid, lease_seconds integer, progress jsonb) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.heartbeat_dispatch_job(target_run_id uuid, worker_token uuid, lease_seconds integer DEFAULT 120, progress jsonb DEFAULT NULL::jsonb)
 RETURNS boolean
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
begin
    update public.dispatch_run_jobs set heartbeat_at=now(),
        lease_expires_at=least(deadline_at,now()+make_interval(secs=>greatest(30,least(lease_seconds,300))))
    where run_id=target_run_id and state='running' and lease_token=worker_token
      and lease_expires_at > now() and deadline_at > now();
    if not found then return false; end if;
    if progress is not null then
        update public.decision_runs set progress_json=progress
        where id=target_run_id and status='running';
    end if;
    return true;
end;
$function$
;
ALTER FUNCTION public.list_decision_cases(case_status text, page_limit integer, page_offset integer, summary_only boolean) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.list_decision_cases(case_status text DEFAULT 'active'::text, page_limit integer DEFAULT 50, page_offset integer DEFAULT 0, summary_only boolean DEFAULT false)
 RETURNS TABLE(case_row jsonb, orders jsonb, fleet jsonb, summaries jsonb)
 LANGUAGE plpgsql
 STABLE
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
BEGIN
 IF case_status IS NOT NULL AND case_status NOT IN ('active','completed','archived')
    OR page_limit IS NULL OR page_limit < 1 OR page_limit > 100
    OR page_offset IS NULL OR page_offset < 0 OR summary_only IS NULL THEN
   RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Paginación de casos inválida';
 END IF;
 RETURN QUERY
 WITH page AS MATERIALIZED (
   SELECT c.* FROM public.decision_cases c
   WHERE c.workspace_id=dation_private.workspace_id() AND (case_status IS NULL OR c.status=case_status)
   ORDER BY c.last_activity_at DESC,c.id DESC LIMIT page_limit OFFSET page_offset
 ), nodes(node_id) AS (VALUES
   ('logistics_assignment'::text),('logistics_scheduling'),('logistics_final_assignment'))
 SELECT to_jsonb(c),
   CASE WHEN summary_only THEN jsonb_build_object(
     'id',o.id,'dataset_type',o.dataset_type,'canonical_filename',o.canonical_filename,
     'label',o.label,'original_filename',o.original_filename)
     ELSE to_jsonb(o) END,
   CASE WHEN summary_only THEN jsonb_build_object(
     'id',f.id,'dataset_type',f.dataset_type,'canonical_filename',f.canonical_filename,
     'label',f.label,'original_filename',f.original_filename)
     ELSE to_jsonb(f) END,
   (SELECT jsonb_object_agg(n.node_id,jsonb_build_object(
     'run_count',(SELECT count(*) FROM public.decision_runs r
       WHERE r.decision_case_id=c.id AND r.node_id=n.node_id),
     'latest',(SELECT to_jsonb(compact) FROM (
       SELECT r.id,r.node_id,r.upstream_run_id,r.status,r.error_message,
              r.approved_at,r.superseded_at
       FROM public.decision_runs r WHERE r.decision_case_id=c.id AND r.node_id=n.node_id
       ORDER BY r.created_at DESC,r.id DESC LIMIT 1) compact),
     'approved',(SELECT to_jsonb(compact) FROM (
       SELECT r.id,r.node_id,r.upstream_run_id,r.status,r.error_message,
              r.approved_at,r.superseded_at
       FROM public.decision_runs r WHERE r.decision_case_id=c.id AND r.node_id=n.node_id
       AND r.approved_at IS NOT NULL AND r.superseded_at IS NULL LIMIT 1) compact)
   )) FROM nodes n)
 FROM page c JOIN public.datasets o ON o.id=c.orders_dataset_id
             JOIN public.datasets f ON f.id=c.fleet_dataset_id
 ORDER BY c.last_activity_at DESC,c.id DESC;
END;
$function$
;
ALTER FUNCTION public.maintain_dispatch_jobs() SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.maintain_dispatch_jobs()
 RETURNS integer
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
declare changed integer;
begin
    with expired as (
        update public.dispatch_run_jobs set state='error', lease_token=null, lease_expires_at=null
        where (dation_private.workspace_id() IS NULL OR workspace_id=dation_private.workspace_id()) and state in ('queued','running') and (
            deadline_at <= now()
            or (state='running' and lease_expires_at <= now() and attempts >= max_attempts)
        ) returning run_id
    )
    update public.decision_runs set status='error', finished_at=now(),
        error_message='La ejecución agotó su plazo o sus intentos de recuperación.',
        progress_json=jsonb_build_object('stage','error','reason','recovery_exhausted')
    where id in (select run_id from expired) and status in ('queued','running');
    get diagnostics changed = row_count;
    return changed;
end;
$function$
;
CREATE OR REPLACE FUNCTION public.protect_comparative_analysis()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
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
END; $function$
;
CREATE OR REPLACE FUNCTION public.protect_persistence_identity()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
BEGIN
 IF TG_TABLE_NAME='datasets' THEN
   IF ROW(NEW.id,NEW.created_at,NEW.storage_bucket,NEW.storage_path,NEW.sha256,NEW.size_bytes,NEW.original_filename,NEW.dataset_type)
      IS DISTINCT FROM ROW(OLD.id,OLD.created_at,OLD.storage_bucket,OLD.storage_path,OLD.sha256,OLD.size_bytes,OLD.original_filename,OLD.dataset_type) THEN
     RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='La identidad del archivo persistido es inmutable';
   END IF;
 ELSIF TG_TABLE_NAME='decision_cases' THEN
   IF ROW(NEW.id,NEW.created_at,NEW.orders_dataset_id,NEW.fleet_dataset_id,NEW.input_signature,NEW.domain)
      IS DISTINCT FROM ROW(OLD.id,OLD.created_at,OLD.orders_dataset_id,OLD.fleet_dataset_id,OLD.input_signature,OLD.domain) THEN
     RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='El Data Pack del Decision Case es inmutable';
   END IF;
 ELSE
   IF ROW(NEW.id,NEW.created_at,NEW.dataset_id,NEW.orders_dataset_id,NEW.fleet_dataset_id,NEW.engine_name,NEW.engine_version,NEW.schema_version)
      IS DISTINCT FROM ROW(OLD.id,OLD.created_at,OLD.dataset_id,OLD.orders_dataset_id,OLD.fleet_dataset_id,OLD.engine_name,OLD.engine_version,OLD.schema_version)
      OR (NEW.configuration_json #- '{decision_case,status}' #- '{decision_case,approved_at}')
        IS DISTINCT FROM (OLD.configuration_json #- '{decision_case,status}' #- '{decision_case,approved_at}') THEN
     RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='La identidad y configuración de la corrida son inmutables';
   END IF;
   IF OLD.status IN ('completed','error') AND (
     ROW(NEW.status,NEW.started_at,NEW.finished_at,NEW.duration_ms,NEW.input_fingerprint,NEW.result_fingerprint,NEW.summary_json,NEW.error_message)
       IS DISTINCT FROM ROW(OLD.status,OLD.started_at,OLD.finished_at,OLD.duration_ms,OLD.input_fingerprint,OLD.result_fingerprint,OLD.summary_json,OLD.error_message)
     OR (NEW.result_json #- '{decision_case,status}' #- '{decision_case,approved_at}')
       IS DISTINCT FROM (OLD.result_json #- '{decision_case,status}' #- '{decision_case,approved_at}')) THEN
     RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='El resultado terminal de la corrida es inmutable';
   END IF;
   IF OLD.approved_at IS NOT NULL AND ROW(NEW.approved_at,NEW.approved_by) IS DISTINCT FROM ROW(OLD.approved_at,OLD.approved_by)
      OR OLD.superseded_at IS NOT NULL AND ROW(NEW.superseded_at,NEW.superseded_by_run_id) IS DISTINCT FROM ROW(OLD.superseded_at,OLD.superseded_by_run_id) THEN
     RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Una aprobación histórica no puede reactivarse ni reescribirse';
   END IF;
 END IF;
 RETURN NEW;
END;
$function$
;
ALTER FUNCTION public.read_decision_chat_turn(target_turn_id uuid, target_run_id uuid, intent_hash text) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.read_decision_chat_turn(target_turn_id uuid, target_run_id uuid, intent_hash text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
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
END; $function$
;
ALTER FUNCTION public.read_decision_chat_turn_with_evidence(target_turn_id uuid, target_run_id uuid, intent_hash text) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.read_decision_chat_turn_with_evidence(target_turn_id uuid, target_run_id uuid, intent_hash text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
DECLARE answer jsonb; evidence uuid;
BEGIN
 answer=read_decision_chat_turn(target_turn_id,target_run_id,intent_hash);
 IF answer IS NULL THEN RETURN NULL; END IF;
 SELECT analysis_id INTO evidence FROM decision_interpretation_sources WHERE chat_turn_id=target_turn_id;
 RETURN answer||jsonb_build_object('evidence_analysis_id',evidence);
END; $function$
;
ALTER FUNCTION public.record_decision_chat_turn(target_turn_id uuid, target_run_id uuid, intent_hash text, question_text text, answer_text text, metadata jsonb) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.record_decision_chat_turn(target_turn_id uuid, target_run_id uuid, intent_hash text, question_text text, answer_text text, metadata jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
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
END; $function$
;
ALTER FUNCTION public.record_decision_chat_turn_with_evidence(target_turn_id uuid, target_run_id uuid, intent_hash text, question_text text, answer_text text, metadata jsonb, evidence_analysis_id uuid) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.record_decision_chat_turn_with_evidence(target_turn_id uuid, target_run_id uuid, intent_hash text, question_text text, answer_text text, metadata jsonb, evidence_analysis_id uuid DEFAULT NULL::uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
DECLARE answer jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended(target_turn_id::text,0));
 answer=read_decision_chat_turn_with_evidence(target_turn_id,target_run_id,intent_hash);
 IF answer IS NOT NULL THEN RETURN answer; END IF;
 answer=record_decision_chat_turn(target_turn_id,target_run_id,intent_hash,question_text,answer_text,metadata);
 INSERT INTO decision_interpretation_sources(run_id,analysis_id,chat_turn_id) VALUES(target_run_id,evidence_analysis_id,target_turn_id);
 RETURN answer||jsonb_build_object('evidence_analysis_id',evidence_analysis_id);
END; $function$
;
ALTER FUNCTION public.record_decision_explanation_with_evidence(explanation jsonb, evidence_analysis_id uuid) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.record_decision_explanation_with_evidence(explanation jsonb, evidence_analysis_id uuid DEFAULT NULL::uuid)
 RETURNS SETOF decision_explanations
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
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
END; $function$
;
CREATE OR REPLACE FUNCTION public.reject_approval_event_mutation()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
BEGIN
 RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Los eventos de aprobación son inmutables';
END;
$function$
;
CREATE OR REPLACE FUNCTION public.report_dispatch_worker(target_worker_id uuid, worker_revision text, is_ready boolean)
 RETURNS boolean
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
BEGIN
 IF target_worker_id IS NULL OR worker_revision IS NULL OR is_ready IS NULL THEN
  RAISE EXCEPTION 'Invalid worker report' USING ERRCODE='22023';
 END IF;
 INSERT INTO dispatch_worker_instances VALUES(target_worker_id,worker_revision,clock_timestamp(),is_ready)
 ON CONFLICT(worker_id) DO UPDATE SET revision=excluded.revision,seen_at=excluded.seen_at,ready=excluded.ready;
 DELETE FROM dispatch_worker_instances WHERE seen_at < clock_timestamp()-interval '24 hours';
 RETURN true;
END; $function$
;
ALTER FUNCTION public.request_case_reconciliation(target_case_id uuid) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.request_case_reconciliation(target_case_id uuid)
 RETURNS void
 LANGUAGE sql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
    insert into public.decision_case_reconciliations(case_id,workspace_id)
    select id,workspace_id from public.decision_cases where id=target_case_id
    on conflict (case_id) do update set version = decision_case_reconciliations.version + 1,
      available_at = now(), updated_at = now();
$function$
;
ALTER FUNCTION public.set_default_fleet(target_id uuid) SET SCHEMA dation_private;
CREATE OR REPLACE FUNCTION dation_private.set_default_fleet(target_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
begin
 perform pg_advisory_xact_lock(701001);
 if not exists(select 1 from public.datasets where workspace_id=dation_private.workspace_id() and id=target_id and dataset_type='fleet') then
  raise exception 'La flota solicitada no existe';
 end if;
 update public.datasets set is_default=false where workspace_id=dation_private.workspace_id() and dataset_type='fleet' and is_default;
 update public.datasets set is_default=true where workspace_id=dation_private.workspace_id() and id=target_id;
end;
$function$
;
CREATE OR REPLACE FUNCTION public.validate_current_run_admission()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
DECLARE source public.decision_runs%rowtype;
BEGIN
 IF NEW.decision_case_id IS NULL THEN RETURN NEW; END IF;
 PERFORM 1 FROM public.decision_cases WHERE id=NEW.decision_case_id FOR UPDATE;
 IF NEW.upstream_run_id IS NOT NULL THEN
   SELECT * INTO source FROM public.decision_runs WHERE id=NEW.upstream_run_id;
   IF NOT FOUND OR source.status<>'completed' OR source.approved_at IS NULL OR source.superseded_at IS NOT NULL THEN
     RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='La corrida upstream ya no es la decisión aprobada vigente';
   END IF;
   IF source.upstream_run_id IS NOT NULL AND NOT EXISTS (
     SELECT 1 FROM public.decision_runs r WHERE r.id=source.upstream_run_id
     AND r.decision_case_id=NEW.decision_case_id AND r.status='completed' AND r.approved_at IS NOT NULL AND r.superseded_at IS NULL) THEN
     RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='La cadena de decisiones upstream está desactualizada';
   END IF;
 END IF;
 RETURN NEW;
END;
$function$
;
CREATE OR REPLACE FUNCTION public.validate_decision_run_history()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
declare
    case_orders uuid;
    case_fleet uuid;
    source_case uuid;
    source_node text;
    source_approved_at timestamptz;
    expected_source_node text;
begin
    if tg_op = 'UPDATE' then
        if new.decision_case_id is distinct from old.decision_case_id
           or new.node_id is distinct from old.node_id
           or new.upstream_run_id is distinct from old.upstream_run_id then
            raise exception 'La identidad y el lineage de una Decision Run son inmutables';
        end if;
    end if;

    if new.decision_case_id is null then
        if new.node_id is not null or new.upstream_run_id is not null then
            raise exception 'Una corrida sin Decision Case no puede declarar nodo o dependencia';
        end if;
        return new;
    end if;

    select orders_dataset_id, fleet_dataset_id
      into case_orders, case_fleet
      from public.decision_cases
     where id = new.decision_case_id;

    if not found then
        raise exception 'El Decision Case de la corrida no existe';
    end if;

    if new.orders_dataset_id is distinct from case_orders
       or new.fleet_dataset_id is distinct from case_fleet then
        raise exception 'La Decision Run usa un Data Pack distinto al Decision Case';
    end if;

    expected_source_node := case new.node_id
        when 'logistics_assignment' then null
        when 'logistics_scheduling' then 'logistics_assignment'
        when 'logistics_final_assignment' then 'logistics_scheduling'
        else null
    end;

    if expected_source_node is null then
        if new.upstream_run_id is not null then
            raise exception 'Assignment no admite una corrida upstream';
        end if;
    else
        if new.upstream_run_id is null then
            raise exception 'La decisión requiere una corrida upstream aprobada';
        end if;

        select decision_case_id, node_id, approved_at
          into source_case, source_node, source_approved_at
          from public.decision_runs
         where id = new.upstream_run_id;

        if not found
           or source_case is distinct from new.decision_case_id
           or source_node is distinct from expected_source_node
           or source_approved_at is null then
            raise exception 'El lineage de la Decision Run no corresponde al Decision Case';
        end if;
    end if;

    if new.approved_at is not null and new.status <> 'completed' then
        raise exception 'Sólo una corrida completada puede aprobarse';
    end if;

    return new;
end;
$function$
;
CREATE OR REPLACE FUNCTION public.validate_dispatch_run()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
begin
  if new.schema_version in ('dispatch_v1', 'dispatch_v2') then
    if new.orders_dataset_id is null
       or new.fleet_dataset_id is null
       or new.dataset_id <> new.orders_dataset_id then
      raise exception 'Una corrida dispatch requiere órdenes y flota';
    end if;

    if not exists (
      select 1
      from public.datasets
      where id = new.orders_dataset_id
        and dataset_type = 'orders'
    )
    or not exists (
      select 1
      from public.datasets
      where id = new.fleet_dataset_id
        and dataset_type = 'fleet'
    ) then
      raise exception 'Tipos de datasets incorrectos';
    end if;

    if new.status = 'completed'
       and new.result_json is not null
       and coalesce(new.result_json ->> 'schema_version', '') <> new.schema_version then
      raise exception 'La versión del resultado no coincide con la corrida';
    end if;
  end if;

  return new;
end;
$function$
;
CREATE OR REPLACE FUNCTION public.validate_interpretation_source()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'dation_private', 'public', 'pg_temp'
AS $function$
DECLARE actual uuid;
BEGIN
 IF NEW.analysis_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM decision_comparative_analyses WHERE id=NEW.analysis_id AND base_run_id=NEW.run_id AND status='completed') THEN
  RAISE EXCEPTION 'Comparative evidence unavailable' USING ERRCODE='22023';
 END IF;
 IF NEW.chat_turn_id IS NOT NULL THEN SELECT run_id INTO actual FROM decision_chat_turns WHERE turn_id=NEW.chat_turn_id;
 ELSE SELECT run_id INTO actual FROM decision_explanations WHERE id=NEW.explanation_id; END IF;
 IF actual IS DISTINCT FROM NEW.run_id THEN RAISE EXCEPTION 'Interpreter source mismatch' USING ERRCODE='22023'; END IF;
 RETURN NEW;
END; $function$
;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA dation_private FROM PUBLIC,anon,authenticated,service_role;

-- Object guards run inside the dispatcher transaction, before any legacy RPC.
CREATE FUNCTION dation_private.assert_owned(relation_name text, object_id uuid, tenant_id uuid, allow_missing boolean DEFAULT false)
RETURNS void LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE key_name text; owned boolean; present boolean;
BEGIN
 IF object_id IS NULL THEN RETURN; END IF;
 IF relation_name NOT IN('datasets','decision_cases','decision_runs','decision_chat_turns','decision_explanations','decision_comparative_analyses') THEN
  RAISE EXCEPTION 'Unregistered object type';
 END IF;
 key_name=CASE WHEN relation_name='decision_chat_turns' THEN 'turn_id' ELSE 'id' END;
 EXECUTE format('SELECT EXISTS(SELECT 1 FROM public.%I WHERE %I=$1 AND workspace_id=$2), EXISTS(SELECT 1 FROM public.%I WHERE %I=$1)',
  relation_name,key_name,relation_name,key_name) INTO owned,present USING object_id,tenant_id;
 IF NOT owned AND (present OR NOT allow_missing) THEN RAISE EXCEPTION 'Resource not found' USING ERRCODE='P0002'; END IF;
END; $$;

CREATE FUNCTION dation_private.check_json_references(value jsonb, tenant_id uuid) RETURNS void
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE item record; relation_name text;
BEGIN
 IF jsonb_typeof(value)='object' THEN
  FOR item IN SELECT * FROM jsonb_each(value) LOOP
   relation_name=CASE WHEN item.key IN('dataset_id','orders_dataset_id','fleet_dataset_id','parent_dataset_id','orders_id','fleet_id') THEN 'datasets'
    WHEN item.key IN('run_id','latest_run_id','approved_run_id','upstream_run_id','source_run_id','source_assignment_run_id','base_run_id','superseded_by_run_id') THEN 'decision_runs'
    WHEN item.key IN('case_id','decision_case_id') THEN 'decision_cases'
    WHEN item.key IN('analysis_id','evidence_analysis_id','comparative_analysis_id') THEN 'decision_comparative_analyses' ELSE NULL END;
   IF item.key='stale_predecessor' AND jsonb_typeof(item.value)='object' THEN
    PERFORM dation_private.assert_owned('decision_cases',(item.value->>'id')::uuid,tenant_id);
   END IF;
   IF relation_name IS NOT NULL AND item.value<>'null'::jsonb THEN
    PERFORM dation_private.assert_owned(relation_name,(item.value#>>'{}')::uuid,tenant_id);
   ELSIF jsonb_typeof(item.value) IN('array','object') THEN
    PERFORM dation_private.check_json_references(item.value,tenant_id);
   END IF;
  END LOOP;
 ELSIF jsonb_typeof(value)='array' THEN
  FOR item IN SELECT v FROM jsonb_array_elements(value) v LOOP
   PERFORM dation_private.check_json_references(item.v,tenant_id);
  END LOOP;
 END IF;
END; $$;
CREATE FUNCTION dation_private.validate_case_state_tenancy() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
BEGIN
 -- A new case may reference itself before its INSERT; omit its root ID only.
 PERFORM dation_private.check_json_references(NEW.state_json-'id',NEW.workspace_id);
 RETURN NEW;
END; $$;
CREATE TRIGGER case_state_tenant_references BEFORE INSERT OR UPDATE OF state_json ON public.decision_cases
 FOR EACH ROW EXECUTE FUNCTION dation_private.validate_case_state_tenancy();

CREATE FUNCTION public.platform_rpc(target_workspace_id uuid, actor_user_id uuid, operation text, arguments jsonb DEFAULT '{}',worker_call boolean DEFAULT false)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE member_role text; answer jsonb; payload jsonb; is_read boolean;
BEGIN
 IF target_workspace_id IS NULL OR jsonb_typeof(arguments) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'Invalid context' USING ERRCODE='42501'; END IF;
 PERFORM set_config('dation.workspace_id',target_workspace_id::text,true);
 PERFORM set_config('dation.actor_user_id',coalesce(actor_user_id::text,''),true);
 is_read=operation IN('list_decision_cases','decision_case_history','read_decision_chat_turn','read_decision_chat_turn_with_evidence','current_decision_explanation',
  'dispatch_operational_snapshot','comparative_operational_snapshot');
 IF worker_call THEN
  IF actor_user_id IS NOT NULL OR operation NOT IN('heartbeat_dispatch_job','finish_dispatch_job','heartbeat_comparative_analysis','finish_comparative_analysis','ack_case_reconciliation','decision_case_history') THEN
   RAISE EXCEPTION 'Worker operation denied' USING ERRCODE='42501'; END IF;
 ELSE
  SELECT m.access_role INTO member_role FROM workspace_members m JOIN workspaces w ON w.id=m.workspace_id
   WHERE m.workspace_id=target_workspace_id AND m.user_id=actor_user_id AND m.status='active' AND w.status='active';
  IF NOT FOUND OR (member_role='viewer' AND NOT is_read) THEN RAISE EXCEPTION 'Membership denied' USING ERRCODE='42501'; END IF;
  IF operation IN('dispatch_operational_snapshot','comparative_operational_snapshot') AND member_role<>'admin' THEN RAISE EXCEPTION 'Admin required' USING ERRCODE='42501'; END IF;
 END IF;
 PERFORM dation_private.assert_owned('decision_runs',(arguments->>'target_run_id')::uuid,target_workspace_id);
 PERFORM dation_private.assert_owned('decision_cases',(arguments->>'target_case_id')::uuid,target_workspace_id);
 PERFORM dation_private.assert_owned('decision_runs',(arguments->>'target_base_id')::uuid,target_workspace_id);
 PERFORM dation_private.assert_owned('decision_comparative_analyses',(arguments->>'target_analysis_id')::uuid,target_workspace_id);
 PERFORM dation_private.assert_owned('datasets',(arguments->>'target_id')::uuid,target_workspace_id);
 PERFORM dation_private.assert_owned('decision_chat_turns',(arguments->>'target_turn_id')::uuid,target_workspace_id,true);
 PERFORM dation_private.assert_owned('decision_comparative_analyses',(arguments->>'evidence_analysis_id')::uuid,target_workspace_id);
 IF arguments ? 'explanation' THEN
  PERFORM dation_private.assert_owned('decision_runs',(arguments->'explanation'->>'run_id')::uuid,target_workspace_id);
  PERFORM dation_private.assert_owned('decision_explanations',(arguments->'explanation'->>'id')::uuid,target_workspace_id,true);
 END IF;
 IF operation='enqueue_dispatch_run' THEN
  payload=arguments->'run_payload';
  PERFORM dation_private.assert_owned('decision_runs',(payload->>'id')::uuid,target_workspace_id,true);
  PERFORM dation_private.check_json_references(payload-'id',target_workspace_id);
  IF arguments->'job_request'->>'workspace_id' IS DISTINCT FROM target_workspace_id::text THEN RAISE EXCEPTION 'Invalid job workspace' USING ERRCODE='42501'; END IF;
 END IF;
 CASE operation
 WHEN 'list_decision_cases' THEN SELECT coalesce(jsonb_agg(to_jsonb(result)),'[]') INTO answer FROM dation_private.list_decision_cases(coalesce((arguments->>'case_status')::text,'active'),coalesce((arguments->>'page_limit')::integer,50),coalesce((arguments->>'page_offset')::integer,0),coalesce((arguments->>'summary_only')::boolean,false)) result;
 WHEN 'decision_case_history' THEN SELECT to_jsonb(dation_private.decision_case_history((arguments->>'target_case_id')::uuid,(arguments->>'target_node_id')::text,coalesce((arguments->>'page_limit')::integer,50),coalesce((arguments->>'page_offset')::integer,0))) INTO answer;
 WHEN 'approve_decision_run_version' THEN SELECT coalesce(jsonb_agg(to_jsonb(result)),'[]') INTO answer FROM dation_private.approve_decision_run_version((arguments->>'target_run_id')::uuid,(arguments->>'target_case_id')::uuid,(arguments->>'target_node_id')::text) result;
 WHEN 'enqueue_dispatch_run' THEN SELECT coalesce(jsonb_agg(to_jsonb(result)),'[]') INTO answer FROM dation_private.enqueue_dispatch_run(nullif(arguments->'run_payload','null'::jsonb),nullif(arguments->'job_request','null'::jsonb),(arguments->>'intent_fingerprint')::text,coalesce((arguments->>'queue_limit')::integer,32)) result;
 WHEN 'cancel_dispatch_job' THEN SELECT coalesce(jsonb_agg(to_jsonb(result)),'[]') INTO answer FROM dation_private.cancel_dispatch_job((arguments->>'target_run_id')::uuid) result;
 WHEN 'heartbeat_dispatch_job' THEN SELECT to_jsonb(dation_private.heartbeat_dispatch_job((arguments->>'target_run_id')::uuid,(arguments->>'worker_token')::uuid,coalesce((arguments->>'lease_seconds')::integer,120),nullif(arguments->'progress','null'::jsonb))) INTO answer;
 WHEN 'finish_dispatch_job' THEN SELECT coalesce(jsonb_agg(to_jsonb(result)),'[]') INTO answer FROM dation_private.finish_dispatch_job((arguments->>'target_run_id')::uuid,(arguments->>'worker_token')::uuid,nullif(arguments->'terminal_values','null'::jsonb)) result;
 WHEN 'ack_case_reconciliation' THEN PERFORM dation_private.ack_case_reconciliation((arguments->>'target_case_id')::uuid,(arguments->>'observed_version')::bigint); answer='null'::jsonb;
 WHEN 'request_case_reconciliation' THEN PERFORM dation_private.request_case_reconciliation((arguments->>'target_case_id')::uuid); answer='null'::jsonb;
 WHEN 'set_default_fleet' THEN PERFORM dation_private.set_default_fleet((arguments->>'target_id')::uuid); answer='null'::jsonb;
 WHEN 'enqueue_comparative_analysis' THEN SELECT coalesce(jsonb_agg(to_jsonb(result)),'[]') INTO answer FROM dation_private.enqueue_comparative_analysis((arguments->>'target_base_id')::uuid,nullif(arguments->'job_request','null'::jsonb),nullif(arguments->'existing_result','null'::jsonb),coalesce((arguments->>'retry_failed')::boolean,false)) result;
 WHEN 'heartbeat_comparative_analysis' THEN SELECT to_jsonb(dation_private.heartbeat_comparative_analysis((arguments->>'target_analysis_id')::uuid,(arguments->>'worker_token')::uuid,coalesce((arguments->>'lease_seconds')::integer,120),nullif(arguments->'progress','null'::jsonb))) INTO answer;
 WHEN 'finish_comparative_analysis' THEN SELECT coalesce(jsonb_agg(to_jsonb(result)),'[]') INTO answer FROM dation_private.finish_comparative_analysis((arguments->>'target_analysis_id')::uuid,(arguments->>'worker_token')::uuid,nullif(arguments->'terminal_values','null'::jsonb)) result;
 WHEN 'read_decision_chat_turn' THEN SELECT to_jsonb(dation_private.read_decision_chat_turn((arguments->>'target_turn_id')::uuid,(arguments->>'target_run_id')::uuid,(arguments->>'intent_hash')::text)) INTO answer;
 WHEN 'read_decision_chat_turn_with_evidence' THEN SELECT to_jsonb(dation_private.read_decision_chat_turn_with_evidence((arguments->>'target_turn_id')::uuid,(arguments->>'target_run_id')::uuid,(arguments->>'intent_hash')::text)) INTO answer;
 WHEN 'record_decision_chat_turn' THEN SELECT to_jsonb(dation_private.record_decision_chat_turn((arguments->>'target_turn_id')::uuid,(arguments->>'target_run_id')::uuid,(arguments->>'intent_hash')::text,(arguments->>'question_text')::text,(arguments->>'answer_text')::text,nullif(arguments->'metadata','null'::jsonb))) INTO answer;
 WHEN 'record_decision_chat_turn_with_evidence' THEN SELECT to_jsonb(dation_private.record_decision_chat_turn_with_evidence((arguments->>'target_turn_id')::uuid,(arguments->>'target_run_id')::uuid,(arguments->>'intent_hash')::text,(arguments->>'question_text')::text,(arguments->>'answer_text')::text,nullif(arguments->'metadata','null'::jsonb),(arguments->>'evidence_analysis_id')::uuid)) INTO answer;
 WHEN 'record_decision_explanation_with_evidence' THEN SELECT coalesce(jsonb_agg(to_jsonb(result)),'[]') INTO answer FROM dation_private.record_decision_explanation_with_evidence(nullif(arguments->'explanation','null'::jsonb),(arguments->>'evidence_analysis_id')::uuid) result;
 WHEN 'current_decision_explanation' THEN SELECT coalesce(jsonb_agg(to_jsonb(result)),'[]') INTO answer FROM dation_private.current_decision_explanation((arguments->>'target_run_id')::uuid) result;
 WHEN 'dispatch_operational_snapshot' THEN SELECT to_jsonb(dation_private.dispatch_operational_snapshot()) INTO answer;
 WHEN 'comparative_operational_snapshot' THEN SELECT to_jsonb(dation_private.comparative_operational_snapshot()) INTO answer;
 ELSE RAISE EXCEPTION 'Operation denied' USING ERRCODE='42501';
 END CASE;
 RETURN answer;
END; $$;

CREATE FUNCTION public.platform_identity(actor_user_id uuid,first_name text DEFAULT '',last_name text DEFAULT '')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE account auth.users; person profiles; membership workspace_members; workspace workspaces; legacy record; membership_count integer;
BEGIN
 IF NOT (SELECT admissions_open FROM dation_private.platform_release WHERE singleton) THEN RAISE EXCEPTION 'Platform access is being upgraded' USING ERRCODE='55000'; END IF;
 SELECT * INTO account FROM auth.users WHERE id=actor_user_id AND email_confirmed_at IS NOT NULL;
 IF NOT FOUND THEN RAISE EXCEPTION 'Confirmed identity required' USING ERRCODE='42501'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(actor_user_id::text,0));
 INSERT INTO profiles(id,first_name,last_name,display_name) VALUES(actor_user_id,left(first_name,100),left(last_name,100),trim(left(first_name,100)||' '||left(last_name,100)))
 ON CONFLICT(id) DO NOTHING;
 -- Only a confirmed, explicitly authorized email can claim the preserved workspace.
 FOR legacy IN SELECT * FROM dation_private.legacy_owners WHERE email=lower(account.email) AND claimed_by IS NULL FOR UPDATE LOOP
  INSERT INTO workspace_members(workspace_id,user_id,access_role,status,joined_at)
   VALUES(legacy.workspace_id,actor_user_id,'admin','active',now()) ON CONFLICT DO NOTHING;
  UPDATE dation_private.legacy_owners SET claimed_by=actor_user_id WHERE email=legacy.email;
  UPDATE workspaces SET created_by=actor_user_id,updated_at=now() WHERE id=legacy.workspace_id AND created_by IS NULL;
  UPDATE profiles SET active_workspace_id=legacy.workspace_id WHERE id=actor_user_id;
  INSERT INTO audit_events(workspace_id,actor_user_id,event_type) VALUES(legacy.workspace_id,actor_user_id,'workspace.legacy_claimed');
 END LOOP;
 SELECT * INTO person FROM profiles WHERE id=actor_user_id;
 SELECT count(*) INTO membership_count FROM workspace_members m JOIN workspaces w ON w.id=m.workspace_id
  WHERE m.user_id=actor_user_id AND m.status='active' AND w.status='active';
 IF membership_count=1 THEN
  SELECT m.* INTO membership FROM workspace_members m JOIN workspaces w ON w.id=m.workspace_id
   WHERE m.user_id=actor_user_id AND m.status='active' AND w.status='active';
 ELSIF membership_count>1 THEN
  SELECT m.* INTO membership FROM workspace_members m JOIN workspaces w ON w.id=m.workspace_id
   WHERE m.user_id=actor_user_id AND m.workspace_id=person.active_workspace_id AND m.status='active' AND w.status='active';
  IF NOT FOUND THEN RAISE EXCEPTION 'Multiple memberships require an administrator-selected active workspace' USING ERRCODE='42501'; END IF;
 ELSIF EXISTS(SELECT 1 FROM workspace_members WHERE user_id=actor_user_id) THEN
  RAISE EXCEPTION 'No active membership' USING ERRCODE='42501';
 END IF;
 IF membership.workspace_id IS NOT NULL THEN
  SELECT * INTO workspace FROM workspaces WHERE id=membership.workspace_id;
 END IF;
 RETURN jsonb_build_object('profile',to_jsonb(person)||jsonb_build_object('email',account.email),
   'membership',CASE WHEN membership.workspace_id IS NULL THEN NULL ELSE to_jsonb(membership) END,
   'workspace',CASE WHEN workspace.id IS NULL THEN NULL ELSE to_jsonb(workspace) END,
   'ddas',coalesce((SELECT jsonb_agg(to_jsonb(d)) FROM workspace_ddas d WHERE d.workspace_id=membership.workspace_id),'[]'));
END; $$;

CREATE FUNCTION public.platform_create_workspace(actor_user_id uuid,workspace_name text,workspace_country text,workspace_timezone text,workspace_currency text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE target uuid;
BEGIN
 IF NOT (SELECT admissions_open FROM dation_private.platform_release WHERE singleton) OR NOT EXISTS(
  SELECT 1 FROM auth.users WHERE id=actor_user_id AND email_confirmed_at IS NOT NULL) THEN RAISE EXCEPTION 'Identity denied' USING ERRCODE='42501'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(actor_user_id::text,0));
 IF EXISTS(SELECT 1 FROM workspace_members WHERE user_id=actor_user_id) OR EXISTS(
  SELECT 1 FROM dation_private.legacy_owners o JOIN auth.users u ON lower(u.email)=o.email WHERE u.id=actor_user_id) THEN
  RAISE EXCEPTION 'Existing membership must be resolved first' USING ERRCODE='22023'; END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name=workspace_timezone) THEN RAISE EXCEPTION 'Invalid timezone' USING ERRCODE='22023'; END IF;
 INSERT INTO profiles(id) VALUES(actor_user_id) ON CONFLICT DO NOTHING;
 INSERT INTO workspaces(name,country,timezone,currency,created_by) VALUES(trim(workspace_name),workspace_country,workspace_timezone,workspace_currency,actor_user_id) RETURNING id INTO target;
 INSERT INTO workspace_members(workspace_id,user_id,access_role,joined_at) VALUES(target,actor_user_id,'admin',now());
 INSERT INTO workspace_ddas(workspace_id,dda_id,status)
  SELECT target,id,CASE WHEN id='logistics' THEN 'enabled' ELSE 'coming_soon' END
  FROM unnest(ARRAY['logistics','production','inventory','demand','purchasing','maintenance','pricing']) id;
 INSERT INTO audit_events(workspace_id,actor_user_id,event_type) VALUES(target,actor_user_id,'workspace.created');
 UPDATE profiles SET active_workspace_id=target,updated_at=now() WHERE id=actor_user_id;
 RETURN jsonb_build_object('workspace_id',target);
END; $$;

-- RLS defense in depth. Direct business mutations and RPC execution are withheld.
CREATE FUNCTION dation_private.is_member(target uuid,admin_only boolean DEFAULT false) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
 SELECT EXISTS(SELECT 1 FROM workspace_members m JOIN workspaces w ON w.id=m.workspace_id
 WHERE m.workspace_id=target AND m.user_id=auth.uid() AND m.status='active' AND w.status='active'
 AND (NOT admin_only OR m.access_role='admin'));
$$;
GRANT USAGE ON SCHEMA dation_private TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION dation_private.is_member(uuid,boolean) TO authenticated;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.profiles FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.profiles TO authenticated;
CREATE POLICY tenant_read ON public.profiles FOR SELECT TO authenticated USING(id=auth.uid());
ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.workspaces FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.workspaces TO authenticated;
CREATE POLICY tenant_read ON public.workspaces FOR SELECT TO authenticated USING(dation_private.is_member(id));
ALTER TABLE public.workspace_members ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.workspace_members FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.workspace_members TO authenticated;
CREATE POLICY tenant_read ON public.workspace_members FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
ALTER TABLE public.workspace_ddas ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.workspace_ddas FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.workspace_ddas TO authenticated;
CREATE POLICY tenant_read ON public.workspace_ddas FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.audit_events FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.audit_events TO authenticated;
CREATE POLICY tenant_read ON public.audit_events FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id,true));
ALTER TABLE public.datasets ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.datasets FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.datasets TO authenticated;
CREATE POLICY tenant_read ON public.datasets FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
ALTER TABLE public.decision_cases ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_cases FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.decision_cases TO authenticated;
CREATE POLICY tenant_read ON public.decision_cases FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
ALTER TABLE public.decision_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_runs FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.decision_runs TO authenticated;
CREATE POLICY tenant_read ON public.decision_runs FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
ALTER TABLE public.dispatch_run_jobs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.dispatch_run_jobs FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.dispatch_run_jobs TO authenticated;
CREATE POLICY tenant_read ON public.dispatch_run_jobs FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
ALTER TABLE public.decision_case_reconciliations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_case_reconciliations FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.decision_case_reconciliations TO authenticated;
CREATE POLICY tenant_read ON public.decision_case_reconciliations FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
ALTER TABLE public.decision_approval_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_approval_events FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.decision_approval_events TO authenticated;
CREATE POLICY tenant_read ON public.decision_approval_events FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
ALTER TABLE public.decision_comparative_analyses ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_comparative_analyses FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.decision_comparative_analyses TO authenticated;
CREATE POLICY tenant_read ON public.decision_comparative_analyses FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
ALTER TABLE public.decision_explanations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_explanations FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.decision_explanations TO authenticated;
CREATE POLICY tenant_read ON public.decision_explanations FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
ALTER TABLE public.decision_messages ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_messages FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.decision_messages TO authenticated;
CREATE POLICY tenant_read ON public.decision_messages FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
ALTER TABLE public.decision_chat_turns ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_chat_turns FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.decision_chat_turns TO authenticated;
CREATE POLICY tenant_read ON public.decision_chat_turns FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
ALTER TABLE public.decision_interpretation_sources ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_interpretation_sources FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.decision_interpretation_sources TO authenticated;
CREATE POLICY tenant_read ON public.decision_interpretation_sources FOR SELECT TO authenticated USING(dation_private.is_member(workspace_id));
GRANT SELECT,INSERT,UPDATE ON public.profiles,public.workspaces,public.workspace_members,public.workspace_ddas TO service_role;
GRANT SELECT,INSERT ON public.audit_events TO service_role;
CREATE TRIGGER audit_events_immutable BEFORE UPDATE OR DELETE ON public.audit_events FOR EACH ROW EXECUTE FUNCTION public.reject_approval_event_mutation();
REVOKE ALL ON FUNCTION public.platform_rpc(uuid,uuid,text,jsonb,boolean) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_rpc(uuid,uuid,text,jsonb,boolean) TO service_role;
REVOKE ALL ON FUNCTION public.platform_identity(uuid,text,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_identity(uuid,text,text) TO service_role;
REVOKE ALL ON FUNCTION public.platform_create_workspace(uuid,text,text,text,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_create_workspace(uuid,text,text,text,text) TO service_role;
ALTER FUNCTION public.claim_dispatch_job(uuid,integer) SECURITY DEFINER;
REVOKE ALL ON FUNCTION public.claim_dispatch_job(uuid,integer) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.claim_dispatch_job(uuid,integer) TO service_role;
ALTER FUNCTION public.claim_comparative_analysis(uuid,integer) SECURITY DEFINER;
REVOKE ALL ON FUNCTION public.claim_comparative_analysis(uuid,integer) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.claim_comparative_analysis(uuid,integer) TO service_role;
ALTER FUNCTION public.report_dispatch_worker(uuid,text,boolean) SECURITY DEFINER;
REVOKE ALL ON FUNCTION public.report_dispatch_worker(uuid,text,boolean) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.report_dispatch_worker(uuid,text,boolean) TO service_role;
REVOKE ALL ON FUNCTION dation_private.assert_owned(text,uuid,uuid,boolean),dation_private.check_json_references(jsonb,uuid),dation_private.validate_case_state_tenancy(),dation_private.is_member(uuid,boolean) FROM PUBLIC;
-- New objects must use a server-generated tenant namespace; legacy rows stay intact.
CREATE FUNCTION dation_private.validate_new_storage_namespace() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 IF split_part(NEW.storage_path,'/',1) IS DISTINCT FROM NEW.workspace_id::text
  OR split_part(NEW.storage_path,'/',2) IS DISTINCT FROM NEW.id::text
  OR array_length(string_to_array(NEW.storage_path,'/'),1)<>3
  OR split_part(NEW.storage_path,'/',3) IN('','..','.') THEN
  RAISE EXCEPTION 'Invalid dataset object namespace' USING ERRCODE='22023'; END IF;
 RETURN NEW;
END; $$;
REVOKE ALL ON FUNCTION dation_private.validate_new_storage_namespace() FROM PUBLIC,anon,authenticated,service_role;
CREATE TRIGGER dataset_storage_namespace BEFORE INSERT ON public.datasets FOR EACH ROW EXECUTE FUNCTION dation_private.validate_new_storage_namespace();
ALTER TABLE public.decision_runs ADD CONSTRAINT authenticated_approval_actor CHECK(
 (approved_by IS NULL AND approved_by_user_id IS NULL) OR
 (approved_by='shared_workspace:dation' AND approved_by_user_id IS NULL) OR
 (approved_by_user_id IS NOT NULL AND approved_by='user:'||approved_by_user_id::text));
ALTER TABLE public.decision_approval_events ADD CONSTRAINT authenticated_event_actor CHECK(
 (actor='shared_workspace:dation' AND actor_user_id IS NULL) OR
 (actor_user_id IS NOT NULL AND actor='user:'||actor_user_id::text));
-- Lease tokens and recovery intentions are internal; product reads use bounded API projections.
REVOKE SELECT ON public.dispatch_run_jobs,public.decision_case_reconciliations,public.decision_comparative_analyses FROM authenticated;
COMMIT;
NOTIFY pgrst,'reload schema';
