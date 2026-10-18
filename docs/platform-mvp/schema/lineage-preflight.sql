-- Platform MVP Fase 0: aggregate-only preflight for the current schema.
-- No DDL, business RPC, customer rows, emails, tokens or filenames returned.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SELECT jsonb_build_object(
  'dataset_storage_missing', (
    SELECT count(*) FROM public.datasets d
    WHERE NOT EXISTS (
      SELECT 1 FROM storage.objects o
      WHERE o.bucket_id = d.storage_bucket AND o.name = d.storage_path
    )
  ),
  'storage_unreferenced', (
    SELECT count(*) FROM storage.objects o
    WHERE o.bucket_id = 'dda-inputs'
      AND NOT EXISTS (
        SELECT 1 FROM public.datasets d
        WHERE d.storage_bucket = o.bucket_id AND d.storage_path = o.name
      )
  ),
  'case_missing_dataset', (
    SELECT count(*) FROM public.decision_cases c
    WHERE NOT EXISTS (SELECT 1 FROM public.datasets d WHERE d.id = c.orders_dataset_id)
       OR NOT EXISTS (SELECT 1 FROM public.datasets d WHERE d.id = c.fleet_dataset_id)
  ),
  'run_pack_differs_from_case', (
    SELECT count(*) FROM public.decision_runs r
    JOIN public.decision_cases c ON c.id = r.decision_case_id
    WHERE r.orders_dataset_id IS DISTINCT FROM c.orders_dataset_id
       OR r.fleet_dataset_id IS DISTINCT FROM c.fleet_dataset_id
  ),
  'upstream_cross_case', (
    SELECT count(*) FROM public.decision_runs r
    JOIN public.decision_runs u ON u.id = r.upstream_run_id
    WHERE r.decision_case_id IS DISTINCT FROM u.decision_case_id
  ),
  'case_state_invalid_run_refs', (
    SELECT count(*) FROM public.decision_cases c
    CROSS JOIN LATERAL jsonb_each(coalesce(c.state_json->'nodes', '{}'::jsonb)) n
    CROSS JOIN (VALUES ('run_id'), ('approved_run_id')) k(name)
    WHERE n.value->>k.name IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM public.decision_runs r
        WHERE r.id::text = n.value->>k.name
          AND r.decision_case_id = c.id AND r.node_id = n.key
      )
  ),
  'runs_without_case', (
    SELECT count(*) FROM public.decision_runs WHERE decision_case_id IS NULL
  ),
  'pending_jobs', (
    SELECT count(*) FROM public.dispatch_run_jobs WHERE state IN ('queued', 'running')
  ),
  'pending_reconciliations', (SELECT count(*) FROM public.decision_case_reconciliations),
  'public_workspace_columns', (
    SELECT count(*) FROM information_schema.columns
    WHERE table_schema = 'public' AND column_name = 'workspace_id'
  )
) AS checks;
COMMIT;
