-- Saga 10 G7: only extend the existing normalized-input archive projection.
BEGIN;
SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='90s';
DO $$ DECLARE source text; BEGIN
 source=pg_get_functiondef('public.platform_data_hub(uuid,uuid,text,text,text,uuid,uuid,uuid,integer,integer)'::regprocedure);
 IF strpos(source,'''order_lines''')=0 THEN
  IF strpos(source,'target.dataset_type IN(''orders'',''fleet'',''transport_demand'',''transport_resources'')')=0 THEN RAISE EXCEPTION 'Unexpected Data Hub archive projection'; END IF;
  EXECUTE replace(source,'target.dataset_type IN(''orders'',''fleet'',''transport_demand'',''transport_resources'')',
   'target.dataset_type IN(''orders'',''fleet'',''transport_demand'',''transport_resources'',''order_lines'')');
 END IF;
END $$;
NOTIFY pgrst,'reload schema';
COMMIT;
