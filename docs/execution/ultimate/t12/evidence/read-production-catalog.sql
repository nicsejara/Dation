SELECT jsonb_build_object(
 'columns',(SELECT jsonb_agg(to_jsonb(x) ORDER BY table_schema,table_name,ordinal_position)
  FROM (SELECT table_schema,table_name,ordinal_position,column_name,data_type,udt_name,is_nullable,column_default
   FROM information_schema.columns WHERE table_schema IN('public','dation_private')) x),
 'constraints',(SELECT jsonb_agg(to_jsonb(x) ORDER BY schema_name,table_name,name)
  FROM (SELECT n.nspname schema_name,t.relname table_name,c.conname name,c.contype,
    c.condeferrable,c.condeferred,pg_get_constraintdef(c.oid) definition
   FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace
   WHERE n.nspname IN('public','dation_private')) x),
 'indexes',(SELECT jsonb_agg(to_jsonb(x) ORDER BY schemaname,tablename,indexname)
  FROM (SELECT schemaname,tablename,indexname,indexdef FROM pg_indexes
   WHERE schemaname IN('public','dation_private')) x),
 'policies',(SELECT jsonb_agg(to_jsonb(x) ORDER BY schemaname,tablename,policyname)
  FROM (SELECT * FROM pg_policies WHERE schemaname IN('public','dation_private')) x),
 'relations',(SELECT jsonb_agg(to_jsonb(x) ORDER BY schema_name,name)
  FROM (SELECT n.nspname schema_name,c.relname name,c.relkind,c.relrowsecurity,c.relforcerowsecurity,c.relacl::text acl
   FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname IN('public','dation_private') AND c.relkind IN('r','p','v')) x),
 'functions',(SELECT jsonb_agg(to_jsonb(x) ORDER BY schema_name,name,args)
  FROM (SELECT n.nspname schema_name,p.proname name,pg_get_function_identity_arguments(p.oid) args,
    p.prosecdef,p.proconfig,p.proacl::text acl,pg_get_functiondef(p.oid) definition
   FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
   WHERE n.nspname IN('public','dation_private') AND p.prokind='f') x),
 'triggers',(SELECT jsonb_agg(to_jsonb(x) ORDER BY schema_name,table_name,name)
  FROM (SELECT n.nspname schema_name,c.relname table_name,t.tgname name,t.tgenabled,pg_get_triggerdef(t.oid) definition
   FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE NOT t.tgisinternal AND n.nspname IN('public','dation_private')) x),
 'defaults',(SELECT jsonb_agg(to_jsonb(x) ORDER BY owner_name,schema_name,kind)
  FROM (SELECT pg_get_userbyid(d.defaclrole) owner_name,n.nspname schema_name,d.defaclobjtype kind,d.defaclacl::text acl
   FROM pg_default_acl d JOIN pg_namespace n ON n.oid=d.defaclnamespace
   WHERE n.nspname IN('public','dation_private')) x));
