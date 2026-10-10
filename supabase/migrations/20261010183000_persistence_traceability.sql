-- Phase 4: full history, serialized approvals and immutable evidence.
-- Upgrade the captured Phase 3 schema. No historical approvals are rewritten.
BEGIN;

ALTER TABLE public.decision_runs ADD COLUMN approved_by text;
ALTER TABLE public.decision_runs ADD CONSTRAINT decision_runs_approved_by_check
 CHECK (approved_by IS NULL OR (approved_by='shared_workspace:dation' AND approved_at IS NOT NULL));
CREATE INDEX decision_runs_history_page_idx
 ON public.decision_runs(decision_case_id, node_id, created_at DESC, id DESC)
 WHERE decision_case_id IS NOT NULL;
CREATE INDEX decision_runs_case_page_idx
 ON public.decision_runs(decision_case_id, created_at DESC, id DESC)
 WHERE decision_case_id IS NOT NULL;

CREATE TABLE public.decision_approval_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 run_id uuid NOT NULL REFERENCES public.decision_runs(id) ON DELETE RESTRICT,
 case_id uuid NOT NULL REFERENCES public.decision_cases(id) ON DELETE RESTRICT,
 node_id text NOT NULL,
 action text NOT NULL CHECK (action IN ('approved','superseded')),
 actor text NOT NULL CHECK (actor = 'shared_workspace:dation'),
 occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 replacement_run_id uuid REFERENCES public.decision_runs(id) ON DELETE RESTRICT,
 UNIQUE (run_id, action)
);
ALTER TABLE public.decision_approval_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.decision_approval_events FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT ON public.decision_approval_events TO service_role;

-- One SQL snapshot supplies all node summaries independently of the requested page.
-- Heavy result_json is deliberately excluded from both summaries and history.
CREATE FUNCTION public.decision_case_history(
 target_case_id uuid, target_node_id text DEFAULT NULL,
 page_limit integer DEFAULT 50, page_offset integer DEFAULT 0
) RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public, pg_temp AS $$
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
$$;

CREATE FUNCTION public.reject_approval_event_mutation() RETURNS trigger
 LANGUAGE plpgsql SECURITY INVOKER SET search_path=public,pg_temp AS $$
BEGIN
 RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Los eventos de aprobación son inmutables';
END;
$$;
CREATE TRIGGER approval_events_immutable BEFORE UPDATE OR DELETE ON public.decision_approval_events
 FOR EACH ROW EXECUTE FUNCTION public.reject_approval_event_mutation();

CREATE FUNCTION public.protect_persistence_identity() RETURNS trigger
 LANGUAGE plpgsql SECURITY INVOKER SET search_path=public,pg_temp AS $$
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
$$;
CREATE TRIGGER datasets_persistence_identity BEFORE UPDATE ON public.datasets
 FOR EACH ROW EXECUTE FUNCTION public.protect_persistence_identity();
CREATE TRIGGER cases_persistence_identity BEFORE UPDATE ON public.decision_cases
 FOR EACH ROW EXECUTE FUNCTION public.protect_persistence_identity();
CREATE TRIGGER runs_persistence_identity BEFORE UPDATE ON public.decision_runs
 FOR EACH ROW EXECUTE FUNCTION public.protect_persistence_identity();

-- Admission and approval share the case lock. Historical child results remain readable
-- and can finish after their parent was superseded; only new admissions require current lineage.
CREATE FUNCTION public.validate_current_run_admission() RETURNS trigger
 LANGUAGE plpgsql SECURITY INVOKER SET search_path=public,pg_temp AS $$
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
$$;
CREATE TRIGGER decision_runs_current_admission BEFORE INSERT ON public.decision_runs
 FOR EACH ROW EXECUTE FUNCTION public.validate_current_run_admission();

CREATE OR REPLACE FUNCTION public.approve_decision_run_version(
 target_run_id uuid,target_case_id uuid,target_node_id text
) RETURNS SETOF public.decision_runs LANGUAGE plpgsql SECURITY INVOKER SET search_path=public,pg_temp AS $$
DECLARE target public.decision_runs%rowtype; source public.decision_runs%rowtype;
 approval_time timestamptz := clock_timestamp();
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
 INSERT INTO public.decision_approval_events(run_id,case_id,node_id,action,actor,occurred_at,replacement_run_id)
   SELECT id,target_case_id,target_node_id,'superseded','shared_workspace:dation',approval_time,target_run_id
   FROM public.decision_runs WHERE decision_case_id=target_case_id AND node_id=target_node_id
     AND approved_at IS NOT NULL AND superseded_at IS NULL;
 UPDATE public.decision_runs SET superseded_at=approval_time,superseded_by_run_id=target_run_id
   WHERE decision_case_id=target_case_id AND node_id=target_node_id AND id<>target_run_id
     AND approved_at IS NOT NULL AND superseded_at IS NULL;
 UPDATE public.decision_runs SET approved_at=approval_time,approved_by='shared_workspace:dation',
   configuration_json=jsonb_set(configuration_json,'{decision_case}',
     coalesce(configuration_json->'decision_case','{}'::jsonb)||jsonb_build_object(
       'case_id',target_case_id::text,'node_id',target_node_id,'status','approved','approved_at',approval_time)),
   result_json=jsonb_set(result_json,'{decision_case}',
     coalesce(result_json->'decision_case','{}'::jsonb)||jsonb_build_object(
       'case_id',target_case_id::text,'node_id',target_node_id,'status','approved','approved_at',approval_time))
   WHERE id=target_run_id;
 INSERT INTO public.decision_approval_events(run_id,case_id,node_id,action,actor,occurred_at)
   VALUES(target_run_id,target_case_id,target_node_id,'approved','shared_workspace:dation',approval_time);
 RETURN QUERY SELECT * FROM public.decision_runs WHERE id=target_run_id;
END;
$$;

REVOKE ALL ON FUNCTION public.decision_case_history(uuid,text,integer,integer),
 public.reject_approval_event_mutation(),public.protect_persistence_identity(),public.validate_current_run_admission(),
 public.approve_decision_run_version(uuid,uuid,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.decision_case_history(uuid,text,integer,integer),
 public.reject_approval_event_mutation(),public.protect_persistence_identity(),public.validate_current_run_admission(),
 public.approve_decision_run_version(uuid,uuid,text) TO service_role;
COMMIT;
NOTIFY pgrst, 'reload schema';
