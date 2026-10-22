-- Apply the existing Case identity and Data Owner contracts in one transaction.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';
CREATE FUNCTION public.platform_apply_case_attributes(target_workspace_id uuid,actor_user_id uuid,target_case_id uuid,
 expected_updated_at timestamptz,identity_changes jsonb,expected_owner_updated_at timestamptz,
 change_data_owner boolean DEFAULT false,new_data_owner_user_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE result jsonb; responsibilities jsonb; owner_version timestamptz;
BEGIN
 -- Same workspace -> Case lock order as admission and responsibility assignment.
 PERFORM 1 FROM workspaces WHERE id=target_workspace_id FOR UPDATE;
 result=public.platform_update_case_identity(target_workspace_id,actor_user_id,target_case_id,expected_updated_at,identity_changes);
 SELECT updated_at INTO owner_version FROM dation_private.workflow_stage_assignments
  WHERE workspace_id=target_workspace_id AND decision_case_id=target_case_id AND stage_key='data_owner';
 IF owner_version IS DISTINCT FROM expected_owner_updated_at THEN RAISE EXCEPTION 'Assignment changed' USING ERRCODE='55006'; END IF;
 IF change_data_owner THEN
  responsibilities=public.platform_workflow_responsibilities(target_workspace_id,actor_user_id,target_case_id,'write','data_owner',expected_owner_updated_at,new_data_owner_user_id,NULL);
 ELSE
  responsibilities=public.platform_workflow_responsibilities(target_workspace_id,actor_user_id,target_case_id);
 END IF;
 -- Any ownership/CAS/permission failure rolls back the identity update as well.
 RETURN result||jsonb_build_object('workflow_responsibilities',responsibilities);
END; $$;
REVOKE ALL ON FUNCTION public.platform_apply_case_attributes(uuid,uuid,uuid,timestamptz,jsonb,timestamptz,boolean,uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_apply_case_attributes(uuid,uuid,uuid,timestamptz,jsonb,timestamptz,boolean,uuid) TO service_role;
NOTIFY pgrst,'reload schema';
COMMIT;
