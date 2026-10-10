-- Phase 5: a bounded case page, datasets and live node summaries in one read.
-- Existing full-list consumers retain their payload; the selector opts into metadata.
BEGIN;
CREATE FUNCTION public.list_decision_cases(
 case_status text DEFAULT 'active', page_limit integer DEFAULT 50,
 page_offset integer DEFAULT 0, summary_only boolean DEFAULT false
) RETURNS TABLE(case_row jsonb, orders jsonb, fleet jsonb, summaries jsonb)
 LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path=public,pg_temp AS $$
BEGIN
 IF case_status IS NOT NULL AND case_status NOT IN ('active','completed','archived')
    OR page_limit IS NULL OR page_limit < 1 OR page_limit > 100
    OR page_offset IS NULL OR page_offset < 0 OR summary_only IS NULL THEN
   RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='Paginación de casos inválida';
 END IF;
 RETURN QUERY
 WITH page AS MATERIALIZED (
   SELECT c.* FROM public.decision_cases c
   WHERE case_status IS NULL OR c.status=case_status
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
$$;
REVOKE ALL ON FUNCTION public.list_decision_cases(text,integer,integer,boolean) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.list_decision_cases(text,integer,integer,boolean) TO service_role;
COMMIT;
NOTIFY pgrst, 'reload schema';
