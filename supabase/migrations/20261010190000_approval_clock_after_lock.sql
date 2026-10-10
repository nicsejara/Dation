-- Phase 4 follow-up: record the effective approval time after serialization.
-- No historical dates or actors are rewritten.
BEGIN;

CREATE OR REPLACE FUNCTION public.approve_decision_run_version(
 target_run_id uuid,target_case_id uuid,target_node_id text
) RETURNS SETOF public.decision_runs LANGUAGE plpgsql SECURITY INVOKER SET search_path=public,pg_temp AS $$
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

COMMIT;
