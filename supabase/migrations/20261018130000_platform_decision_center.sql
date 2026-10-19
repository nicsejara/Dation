-- Phase 7: read-only case memory, optional labels and authenticated provenance.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='90s';
ALTER TABLE public.decision_cases ADD COLUMN label text CHECK(label IS NULL OR (length(label) BETWEEN 1 AND 120 AND label=trim(label)));
ALTER TABLE public.decision_cases ADD COLUMN created_by_user_id uuid REFERENCES auth.users(id);
ALTER TABLE public.decision_runs ADD COLUMN created_by_user_id uuid REFERENCES auth.users(id);

CREATE FUNCTION dation_private.center_provenance() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE actor uuid;
BEGIN
 IF TG_OP='UPDATE' AND NEW.created_by_user_id IS DISTINCT FROM OLD.created_by_user_id THEN
  RAISE EXCEPTION 'Creator is immutable' USING ERRCODE='22023'; END IF;
 IF TG_OP='INSERT' THEN
  actor=nullif(current_setting('dation.actor_user_id',true),'')::uuid;
  IF actor IS NOT NULL THEN NEW.created_by_user_id=actor; END IF;
  IF NEW.created_by_user_id IS NOT NULL THEN
   PERFORM dation_private.data_actor(NEW.workspace_id,NEW.created_by_user_id,true);
  END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER center_provenance_guard BEFORE INSERT OR UPDATE ON public.decision_cases FOR EACH ROW EXECUTE FUNCTION dation_private.center_provenance();
CREATE TRIGGER center_provenance_guard BEFORE INSERT OR UPDATE ON public.decision_runs FOR EACH ROW EXECUTE FUNCTION dation_private.center_provenance();

CREATE FUNCTION dation_private.center_person(wid uuid,uid uuid) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT jsonb_build_object('id',p.id,'name',coalesce(nullif(trim(concat_ws(' ',p.first_name,p.last_name)),''),'Usuario del workspace'))
 FROM profiles p JOIN workspace_members m ON m.user_id=p.id WHERE m.workspace_id=wid AND p.id=uid
$$;

CREATE FUNCTION dation_private.center_bundle(c public.decision_cases) RETURNS jsonb
LANGUAGE plpgsql STABLE SET search_path=public,pg_temp AS $$
DECLARE summaries jsonb; a jsonb; s jsonb; n jsonb; latest jsonb; pending boolean=false; reviewing boolean=false; finished boolean; life text;
BEGIN
 summaries=dation_private.decision_case_history(c.id,NULL,0,0)->'summaries';
 a=summaries->'logistics_assignment'->'approved';s=summaries->'logistics_scheduling'->'approved';
 FOR n IN SELECT value FROM jsonb_each(summaries-'logistics_final_assignment') LOOP
  latest=n->'latest';
  IF latest->>'id' IS NOT NULL AND latest->>'approved_at' IS NULL AND latest->>'superseded_at' IS NULL THEN
   pending=true;
   IF latest->>'status'='completed' AND (latest->>'node_id'='logistics_assignment' OR latest->>'upstream_run_id'=a->>'id') THEN reviewing=true; END IF;
  END IF;
 END LOOP;
 finished=coalesce(a->>'id' IS NOT NULL AND s->>'id' IS NOT NULL AND s->>'upstream_run_id'=a->>'id' AND NOT pending,false);
 life=CASE WHEN c.status='archived' THEN 'archived' WHEN finished THEN 'completed' ELSE 'active' END;
 RETURN jsonb_build_object('case',to_jsonb(c)-'state_json','state_json',c.state_json,'summaries',summaries,
  'status',life,'in_review',life='active' AND reviewing,'created_by',dation_private.center_person(c.workspace_id,c.created_by_user_id));
END; $$;

CREATE FUNCTION dation_private.center_run(r public.decision_runs) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT jsonb_build_object('id',r.id,'node_id',r.node_id,'created_at',r.created_at,'status',r.status,
  'duration_ms',r.duration_ms,'approved_at',r.approved_at,'superseded_at',r.superseded_at,
  'upstream_run_id',r.upstream_run_id,'created_by',dation_private.center_person(r.workspace_id,r.created_by_user_id),
  'approved_by',dation_private.center_person(r.workspace_id,r.approved_by_user_id),
  'legacy_approval',r.approved_by='shared_workspace:dation',
  'objective',coalesce(r.configuration_json->>'objective',r.configuration_json->>'strategy'),
  'engine_name',r.engine_name,'engine_version',r.engine_version,'schema_version',r.schema_version,
  'input_fingerprint',r.input_fingerprint,'result_fingerprint',r.result_fingerprint)
$$;

CREATE FUNCTION public.platform_decision_center(target_workspace_id uuid,actor_user_id uuid,
 target_case_id uuid DEFAULT NULL,filter_name text DEFAULT 'all',search_text text DEFAULT '',dda text DEFAULT 'all',
 target_node_id text DEFAULT NULL,page_limit integer DEFAULT 25,page_offset integer DEFAULT 0)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE current_case decision_cases; answer jsonb; history jsonb;
BEGIN
 PERFORM dation_private.data_actor(target_workspace_id,actor_user_id);
 PERFORM set_config('dation.workspace_id',target_workspace_id::text,true);
 IF filter_name NOT IN('all','in_progress','review','completed','archived') OR dda NOT IN('all','logistics')
 OR length(search_text)>120 OR page_limit NOT BETWEEN 1 AND 50 OR page_offset NOT BETWEEN 0 AND 1000000
 OR (target_node_id IS NOT NULL AND target_node_id NOT IN('logistics_assignment','logistics_scheduling','logistics_final_assignment')) THEN
  RAISE EXCEPTION 'Invalid center query' USING ERRCODE='22023'; END IF;
 IF target_case_id IS NOT NULL THEN
  SELECT * INTO current_case FROM decision_cases WHERE id=target_case_id AND workspace_id=target_workspace_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
  answer=dation_private.center_bundle(current_case);
  IF target_node_id IS NOT NULL THEN
   SELECT coalesce(jsonb_agg(dation_private.center_run(r) ORDER BY r.created_at DESC,r.id DESC),'[]') INTO history
   FROM (SELECT * FROM decision_runs WHERE workspace_id=target_workspace_id AND decision_case_id=current_case.id AND node_id=target_node_id
     ORDER BY created_at DESC,id DESC LIMIT page_limit OFFSET page_offset) r;
   RETURN answer||jsonb_build_object('runs',history,'node_id',target_node_id,'limit',page_limit,'offset',page_offset);
  END IF;
  RETURN answer||jsonb_build_object('orders',(SELECT dation_private.hub_dataset(d) FROM datasets d WHERE id=current_case.orders_dataset_id AND workspace_id=target_workspace_id),
   'fleet',(SELECT dation_private.hub_dataset(d) FROM datasets d WHERE id=current_case.fleet_dataset_id AND workspace_id=target_workspace_id),
   'run_people',coalesce((SELECT jsonb_object_agg(r.id::text,dation_private.center_run(r)) FROM decision_runs r
    WHERE r.workspace_id=target_workspace_id AND r.decision_case_id=current_case.id AND r.id IN
     (SELECT (value->k->>'id')::uuid FROM jsonb_each(answer->'summaries') CROSS JOIN (VALUES('latest'),('approved')) v(k))),'{}'));
 END IF;
 WITH base AS MATERIALIZED (SELECT c.*,dation_private.center_bundle(c) bundle FROM decision_cases c WHERE c.workspace_id=target_workspace_id
  AND (dda='all' OR c.domain=dda) AND (search_text='' OR strpos(lower(concat_ws(' ',c.id::text,'DC-'||substr(c.id::text,1,8),c.label)),lower(search_text))>0)),
 matched AS (SELECT * FROM base WHERE CASE filter_name
  WHEN 'all' THEN bundle->>'status'<>'archived'
  WHEN 'archived' THEN bundle->>'status'='archived'
  WHEN 'completed' THEN bundle->>'status'='completed'
  WHEN 'review' THEN (bundle->>'in_review')::boolean
  ELSE bundle->>'status'='active' AND NOT (bundle->>'in_review')::boolean END),
 page AS (SELECT * FROM matched ORDER BY last_activity_at DESC,id DESC LIMIT page_limit OFFSET page_offset)
 SELECT jsonb_build_object('items',coalesce((SELECT jsonb_agg(bundle ORDER BY last_activity_at DESC,id DESC) FROM page),'[]'),
  'total',(SELECT count(*) FROM matched),'limit',page_limit,'offset',page_offset) INTO answer;
 RETURN answer;
END; $$;

CREATE FUNCTION public.platform_update_case(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid,
 expected_updated_at timestamptz,change_label boolean DEFAULT false,new_label text DEFAULT NULL,archive boolean DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE c decision_cases;
BEGIN
 PERFORM dation_private.data_actor(target_workspace_id,actor_user_id,true);
 SELECT * INTO c FROM decision_cases WHERE workspace_id=target_workspace_id AND id=target_case_id FOR UPDATE NOWAIT;
 IF NOT FOUND THEN RAISE EXCEPTION 'Case not found' USING ERRCODE='P0002'; END IF;
 IF expected_updated_at IS DISTINCT FROM c.updated_at THEN RAISE EXCEPTION 'Case changed; refresh' USING ERRCODE='55006'; END IF;
 IF change_label AND new_label IS NOT NULL AND (length(trim(new_label)) NOT BETWEEN 1 AND 120) THEN RAISE EXCEPTION 'Invalid label' USING ERRCODE='22023'; END IF;
 UPDATE decision_cases SET label=CASE WHEN change_label THEN nullif(trim(new_label),'') ELSE label END,
  status=CASE WHEN archive THEN 'archived' WHEN archive=false THEN 'active' ELSE status END,
  archived_at=CASE WHEN archive THEN now() WHEN archive=false THEN NULL ELSE archived_at END,
  updated_at=clock_timestamp(),last_activity_at=clock_timestamp() WHERE id=c.id AND workspace_id=target_workspace_id RETURNING * INTO c;
 RETURN jsonb_build_object('id',c.id,'label',c.label,'updated_at',c.updated_at,'status',c.status);
EXCEPTION WHEN lock_not_available THEN RAISE EXCEPTION 'Case is busy; retry' USING ERRCODE='55006';
END; $$;

REVOKE ALL ON FUNCTION dation_private.center_provenance(),dation_private.center_person(uuid,uuid),dation_private.center_bundle(public.decision_cases),dation_private.center_run(public.decision_runs) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.platform_decision_center(uuid,uuid,uuid,text,text,text,text,integer,integer),public.platform_update_case(uuid,uuid,uuid,timestamptz,boolean,text,boolean) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_decision_center(uuid,uuid,uuid,text,text,text,text,integer,integer),public.platform_update_case(uuid,uuid,uuid,timestamptz,boolean,text,boolean) TO service_role;
-- Keep the same Home contract while honoring the optional case label.
CREATE OR REPLACE FUNCTION public.platform_home(target_workspace_id uuid, actor_user_id uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE member_role text; recent jsonb; attention jsonb; attention_total bigint;
BEGIN
 SELECT m.access_role INTO member_role
 FROM workspace_members m JOIN workspaces w ON w.id=m.workspace_id
 JOIN profiles p ON p.id=m.user_id
 JOIN auth.users u ON u.id=m.user_id AND u.email_confirmed_at IS NOT NULL
 WHERE m.workspace_id=target_workspace_id AND m.user_id=actor_user_id
   AND m.status='active' AND w.status='active';
 IF NOT FOUND THEN RAISE EXCEPTION 'Membership denied' USING ERRCODE='42501'; END IF;
 PERFORM set_config('dation.workspace_id',target_workspace_id::text,true);

 -- Three recent, non-archived cases. Run summaries are read in this same snapshot;
 -- cached state alone must never determine an approval or the current version.
 SELECT coalesce(jsonb_agg(jsonb_build_object(
   'case',jsonb_build_object('id',c.id,'status',c.status,'state_json',c.state_json,
     'orders_dataset_id',c.orders_dataset_id,'fleet_dataset_id',c.fleet_dataset_id,
     'last_activity_at',c.last_activity_at),
   'label',coalesce(nullif(c.label,''),nullif(o.label,''),o.canonical_filename,o.original_filename),
   'summaries',dation_private.decision_case_history(c.id,NULL,0,0)->'summaries'
 ) ORDER BY c.last_activity_at DESC,c.id DESC),'[]') INTO recent
 FROM (SELECT * FROM decision_cases WHERE workspace_id=target_workspace_id
   AND status IN('active','completed') ORDER BY last_activity_at DESC,id DESC LIMIT 3) c
 JOIN datasets o ON o.id=c.orders_dataset_id AND o.workspace_id=target_workspace_id;

 attention='[]'; attention_total=0;
 -- Approval is currently workspace-wide for admins/operators, not a personal
 -- assignment. Do not infer owners or invent reviewer responsibilities.
 IF member_role IN('admin','operator') THEN
  WITH candidates AS (
   SELECT c.id AS case_id,c.last_activity_at,r.id AS run_id,r.node_id,
     count(*) OVER() AS total
   FROM decision_cases c
   CROSS JOIN (VALUES ('logistics_assignment'::text),('logistics_scheduling')) n(node_id)
   JOIN LATERAL (SELECT id,node_id,status,approved_at,superseded_at,upstream_run_id
     FROM decision_runs WHERE workspace_id=target_workspace_id
       AND decision_case_id=c.id AND node_id=n.node_id
     ORDER BY created_at DESC,id DESC LIMIT 1) r ON true
   WHERE c.workspace_id=target_workspace_id AND c.status='active'
     AND r.status='completed' AND r.approved_at IS NULL AND r.superseded_at IS NULL
     AND (r.node_id='logistics_assignment' OR EXISTS(
       SELECT 1 FROM decision_runs source WHERE source.id=r.upstream_run_id
         AND source.workspace_id=target_workspace_id AND source.decision_case_id=c.id
         AND source.node_id='logistics_assignment' AND source.status='completed'
         AND source.approved_at IS NOT NULL AND source.superseded_at IS NULL))
   ORDER BY c.last_activity_at DESC,c.id DESC,r.node_id LIMIT 5
  ) SELECT coalesce(jsonb_agg(to_jsonb(candidates)-'total'
      ORDER BY last_activity_at DESC,case_id DESC,node_id),'[]'),coalesce(max(total),0)
    INTO attention,attention_total FROM candidates;
 END IF;
 RETURN jsonb_build_object('recent_cases',recent,
   'attention',jsonb_build_object('items',attention,'total',attention_total));
END; $$;
NOTIFY pgrst,'reload schema';
COMMIT;
