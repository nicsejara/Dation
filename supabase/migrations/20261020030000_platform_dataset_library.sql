-- Data Hub V2 read projection. Existing upload, pack and lifecycle RPCs stay intact.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';

CREATE FUNCTION dation_private.dataset_case_usage(wid uuid,did uuid)
RETURNS SETOF public.decision_cases LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT c.* FROM decision_cases c WHERE c.workspace_id=wid AND
 (c.orders_dataset_id=did OR c.fleet_dataset_id=did OR EXISTS(
  SELECT 1 FROM decision_runs r WHERE r.workspace_id=wid AND r.decision_case_id=c.id
  AND did IN(r.dataset_id,r.orders_dataset_id,r.fleet_dataset_id)))
$$;

CREATE FUNCTION dation_private.library_dataset(d public.datasets)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT dation_private.hub_dataset(d)||jsonb_build_object('case_count',
 (SELECT count(*) FROM dation_private.dataset_case_usage(d.workspace_id,d.id)))
$$;

CREATE FUNCTION public.platform_dataset_library(target_workspace_id uuid,actor_user_id uuid,
 target_dataset_id uuid DEFAULT NULL,dataset_type text DEFAULT 'all',validation_state text DEFAULT 'all',
 lifecycle_state text DEFAULT 'active',search_text text DEFAULT '',page_limit integer DEFAULT 25,page_offset integer DEFAULT 0)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE answer jsonb; target datasets;
BEGIN
 PERFORM dation_private.data_actor(target_workspace_id,actor_user_id);
 IF dataset_type NOT IN('all','orders','fleet','logistics_legacy') OR validation_state NOT IN('all','validated','issues','unknown')
 OR lifecycle_state NOT IN('all','active','archived') OR length(search_text)>120
 OR page_limit NOT BETWEEN 1 AND 50 OR page_offset NOT BETWEEN 0 AND 1000000 THEN
 RAISE EXCEPTION 'Invalid dataset library query' USING ERRCODE='22023'; END IF;
 IF target_dataset_id IS NOT NULL THEN
  -- Keep the existing bounded validation report and conservative lifecycle permits.
  answer=public.platform_data_hub(target_workspace_id,actor_user_id,resource=>'dataset',
   target_dataset_id=>target_dataset_id,page_limit=>page_limit,page_offset=>page_offset);
  SELECT * INTO target FROM datasets WHERE workspace_id=target_workspace_id AND id=target_dataset_id;
  RETURN answer||jsonb_build_object('dataset',dation_private.library_dataset(target),
   'case_total',(SELECT count(*) FROM dation_private.dataset_case_usage(target_workspace_id,target_dataset_id)),
   'used_in',coalesce((SELECT jsonb_agg(to_jsonb(p) ORDER BY p.created_at DESC,p.id DESC) FROM
    (SELECT c.id,c.status,c.created_at,c.label,c.domain AS dda,'DC-'||upper(left(c.id::text,8)) AS friendly_id
     FROM dation_private.dataset_case_usage(target_workspace_id,target_dataset_id) c
     ORDER BY c.created_at DESC,c.id DESC LIMIT page_limit OFFSET page_offset) p),'[]'));
 END IF;
 WITH workspace AS MATERIALIZED (SELECT * FROM datasets WHERE workspace_id=target_workspace_id),
 matched AS (SELECT * FROM workspace d WHERE
  (platform_dataset_library.dataset_type='all' OR d.dataset_type=platform_dataset_library.dataset_type)
  AND (lifecycle_state='all' OR (lifecycle_state='active' AND d.archived_at IS NULL) OR (lifecycle_state='archived' AND d.archived_at IS NOT NULL))
  AND (validation_state='all' OR CASE WHEN d.profile_json->'valid'='true' THEN 'validated' WHEN d.profile_json->'valid'='false' THEN 'issues' ELSE 'unknown' END=validation_state)
  AND (search_text='' OR strpos(lower(concat_ws(' ',d.label,d.canonical_filename,d.original_filename)),lower(search_text))>0)),
 page AS (SELECT * FROM matched ORDER BY created_at DESC,id DESC LIMIT page_limit OFFSET page_offset)
 SELECT jsonb_build_object('items',coalesce((SELECT jsonb_agg(dation_private.library_dataset(p::public.datasets) ORDER BY p.created_at DESC,p.id DESC) FROM page p),'[]'),
  'total',(SELECT count(*) FROM matched),'limit',page_limit,'offset',page_offset,
  'summary',(SELECT jsonb_build_object('total',count(*),'validated',count(*) FILTER(WHERE profile_json->'valid'='true'),
   'issues',count(*) FILTER(WHERE profile_json->'valid'='false'),'archived',count(*) FILTER(WHERE archived_at IS NOT NULL)) FROM workspace),
  'incomplete_uploads',coalesce((SELECT jsonb_agg(to_jsonb(u) ORDER BY u.created_at DESC,u.id DESC) FROM
   (SELECT id,filename,created_at,status FROM dation_private.dataset_uploads u WHERE u.workspace_id=target_workspace_id
    AND (u.status IN('failed','discarding') OR (u.status='pending' AND u.created_at<now()-interval '15 minutes'))
    AND NOT EXISTS(SELECT 1 FROM datasets d WHERE d.workspace_id=target_workspace_id AND d.id=u.dataset_id)
    ORDER BY created_at DESC,id DESC LIMIT 10) u),'[]')) INTO answer;
 RETURN answer;
END; $$;

REVOKE ALL ON FUNCTION dation_private.dataset_case_usage(uuid,uuid) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION dation_private.library_dataset(public.datasets) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_dataset_library(uuid,uuid,uuid,text,text,text,text,integer,integer) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_dataset_library(uuid,uuid,uuid,text,text,text,text,integer,integer) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
