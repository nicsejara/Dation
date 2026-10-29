-- T12-R only: server-owned rollout scope. No pilot is enrolled or activated.
-- Existing readers, approvals, idempotent replays and admitted worker jobs stay
-- readable/drainable; only new capabilities/writes/admissions are narrowed.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='60s';

ALTER TABLE dation_private.platform_release
 ADD COLUMN ultimate_pilot_enabled boolean NOT NULL DEFAULT false;

CREATE TABLE dation_private.ultimate_pilot_workspaces (
 workspace_id uuid PRIMARY KEY REFERENCES public.workspaces(id) ON DELETE RESTRICT,
 enabled boolean NOT NULL DEFAULT false
);
ALTER TABLE dation_private.ultimate_pilot_workspaces ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE dation_private.ultimate_pilot_workspaces FROM PUBLIC,anon,authenticated,service_role;
COMMENT ON TABLE dation_private.ultimate_pilot_workspaces IS
 'Release-operator allowlist only. Workspace Admin/Owner/Viewer and service-role API callers cannot enroll a pilot.';

CREATE FUNCTION dation_private.ultimate_pilot_allows(target_workspace_id uuid)
RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER SET search_path=pg_catalog AS $$
 SELECT coalesce((SELECT r.ultimate_pilot_enabled AND EXISTS(
   SELECT 1 FROM dation_private.ultimate_pilot_workspaces w
   WHERE w.workspace_id=target_workspace_id AND w.enabled)
  FROM dation_private.platform_release r WHERE r.singleton),false)
$$;
REVOKE ALL ON FUNCTION dation_private.ultimate_pilot_allows(uuid) FROM PUBLIC,anon,authenticated,service_role;

-- Patch only the certified release-flag expressions. Keep signatures, owners,
-- ACLs, membership/role checks, persisted results and mathematical code intact.
-- Refuse unknown definitions rather than applying an approximate replacement.
DO $$
DECLARE change record; source text; occurrences integer;
BEGIN
 FOR change IN SELECT * FROM (VALUES
  ('dation_private.t3_case_context(public.decision_cases,uuid)',
   'SELECT ultimate_foundation_enabled INTO enabled',
   'SELECT ultimate_foundation_enabled AND dation_private.ultimate_pilot_allows(c.workspace_id) INTO enabled',1),
  ('public.platform_ultimate_foundation(uuid,uuid,text,jsonb)',
   'SELECT ultimate_foundation_enabled INTO enabled',
   'SELECT ultimate_foundation_enabled AND dation_private.ultimate_pilot_allows(target_workspace_id) INTO enabled',2),
  ('public.platform_ultimate_data_pack(uuid,uuid,text,jsonb)',
   'SELECT ultimate_foundation_enabled AND ultimate_data_pack_enabled INTO enabled',
   'SELECT ultimate_foundation_enabled AND ultimate_data_pack_enabled AND dation_private.ultimate_pilot_allows(target_workspace_id) INTO enabled',2),
  ('public.platform_ultimate_execution(uuid,uuid,text,jsonb)',
   'SELECT ultimate_admissions_enabled,ultimate_scheduling_admissions_enabled INTO enabled,scheduling_enabled',
   'SELECT ultimate_admissions_enabled AND dation_private.ultimate_pilot_allows(wid),ultimate_scheduling_admissions_enabled AND dation_private.ultimate_pilot_allows(wid) INTO enabled,scheduling_enabled',1),
  ('public.platform_ultimate_graph(uuid,uuid,uuid,text,text,uuid,integer,integer)',
   'SELECT ultimate_scheduling_admissions_enabled FROM dation_private.platform_release WHERE singleton',
   'SELECT ultimate_admissions_enabled AND ultimate_scheduling_admissions_enabled AND dation_private.ultimate_pilot_allows(target_workspace_id) FROM dation_private.platform_release WHERE singleton',1)
 ) AS patches(signature,old_expression,new_expression,expected_occurrences)
 LOOP
  source=pg_get_functiondef(change.signature::regprocedure);
  occurrences=(length(source)-length(replace(source,change.old_expression,'')))/length(change.old_expression);
  IF occurrences<>change.expected_occurrences OR strpos(source,'ultimate_pilot_allows')>0 THEN
   RAISE EXCEPTION 'Unrecognized pre-cohort release definition: %',change.signature;
  END IF;
  EXECUTE replace(source,change.old_expression,change.new_expression);
 END LOOP;
END; $$;

COMMIT;
