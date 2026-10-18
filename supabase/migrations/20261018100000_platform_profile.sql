-- Phase 3 profile: only personal display fields; email, roles and memberships are not editable here.
BEGIN;
CREATE FUNCTION public.platform_update_profile(actor_user_id uuid,first_name text,last_name text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE person profiles;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM auth.users WHERE id=actor_user_id AND email_confirmed_at IS NOT NULL)
  OR length(trim(first_name)) NOT BETWEEN 1 AND 100 OR length(trim(last_name)) NOT BETWEEN 1 AND 100 THEN
  RAISE EXCEPTION 'Invalid profile' USING ERRCODE='42501'; END IF;
 UPDATE profiles SET first_name=trim(platform_update_profile.first_name),last_name=trim(platform_update_profile.last_name),
  display_name=trim(platform_update_profile.first_name)||' '||trim(platform_update_profile.last_name),updated_at=now()
  WHERE id=actor_user_id RETURNING * INTO person;
 IF NOT FOUND THEN RAISE EXCEPTION 'Profile not found' USING ERRCODE='P0002'; END IF;
 RETURN to_jsonb(person);
END; $$;
REVOKE ALL ON FUNCTION public.platform_update_profile(uuid,text,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.platform_update_profile(uuid,text,text) TO service_role;
COMMIT;
NOTIFY pgrst,'reload schema';
