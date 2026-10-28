"""T3 additive catalog/default/legacy-row check in the labelled local sandbox."""
from pathlib import Path
import json,sys
from uuid import uuid4
sys.path.insert(0,'/workspace/Dation/backend/tests/integration')
from ultimate_sql_support import UltimateSQLSandbox as S,REPO
out=Path('/workspace/work/dation-t3')
db=S.create_database(ultimate=False)
try:
 for m in sorted((REPO/'supabase/migrations').glob('*.sql')):
  if '20261026010000'<m.name[:14]<'20261026161050':S.command(m.read_text(),database=db)
 S.database=db
 w='00000000-0000-4000-8000-00000000da71';o,f,c,r=[str(uuid4()) for _ in range(4)]
 S.command(f"""INSERT INTO datasets(id,workspace_id,dataset_type,original_filename,storage_path) VALUES('{o}','{w}','orders','o.csv','{w}/{o}/o.csv'),('{f}','{w}','fleet','f.csv','{w}/{f}/f.csv');
 INSERT INTO decision_cases(id,workspace_id,orders_dataset_id,fleet_dataset_id,input_signature,label) VALUES('{c}','{w}','{o}','{f}','{o}:{f}','T3 preservation fixture');
 INSERT INTO decision_runs(id,workspace_id,dataset_id,orders_dataset_id,fleet_dataset_id,decision_case_id,node_id,engine_name,engine_version,schema_version,status,result_json,approved_at,approved_by) VALUES('{r}','{w}','{o}','{o}','{f}','{c}','logistics_assignment','logistics-assignment-engine','1.0.0','assignment_v1','completed','{{"schema_version":"assignment_v1","unchanged_fixture":[1,2]}}',now(),'shared_workspace:dation');
 INSERT INTO decision_approval_events(workspace_id,run_id,case_id,node_id,action,actor) VALUES('{w}','{r}','{c}','logistics_assignment','approved','shared_workspace:dation');""")
 before=S.catalog()
 tables=['datasets','decision_cases','decision_runs','decision_approval_events']
 columns={t:[x['column_name'] for x in before['columns'] if x['table_schema']=='public' and x['table_name']==t] for t in tables}
 def rows():return {t:json.loads(S.command('SELECT coalesce(jsonb_agg(to_jsonb(t)),\'[]\') FROM (SELECT '+','.join(columns[t])+' FROM '+t+' ORDER BY id) t;').stdout) for t in tables}
 old=rows();S.command((REPO/'supabase/migrations/20261026161050_ultimate_case_models.sql').read_text())
 after=S.catalog();assert rows()==old;assert before['defaults']==after['defaults'];assert before['policies']==after['policies']
 old_rel={ (x['schema_name'],x['name']):x for x in before['relations']};new_rel={ (x['schema_name'],x['name']):x for x in after['relations']};assert old_rel==new_rel
 old_fn={(x['schema_name'],x['name'],x['args']):x for x in before['functions']};new_fn={(x['schema_name'],x['name'],x['args']):x for x in after['functions']}
 changed=[]
 for key,value in old_fn.items():
  assert new_fn[key]['acl']==value['acl'],key
  if value['definition']!=new_fn[key]['definition']:changed.append('.'.join(key[:2]))
 assert changed==['public.platform_home'],changed
 flag=S.command('SELECT ultimate_foundation_enabled FROM dation_private.platform_release;').stdout.strip();assert flag=='f'
 added_columns=[x for x in after['columns'] if not any((x['table_schema'],x['table_name'],x['column_name'])==(y['table_schema'],y['table_name'],y['column_name']) for y in before['columns'])]
 report=dict(migration='20261026161050_ultimate_case_models.sql',environment='owned T3 local PostgreSQL 17',default_flag_closed=True,legacy_rows_unchanged=True,legacy_tables=tables,legacy_rows=sum(map(len,old.values())),table_acls_unchanged=True,existing_function_acls_unchanged=True,default_acls_unchanged=True,rls_policies_unchanged=True,existing_function_definition_changes=changed,added_columns=added_columns,new_functions=[v for k,v in new_fn.items() if k not in old_fn],new_triggers=[x for x in after['triggers'] if x not in before['triggers']])
 (out/'schema-boundary.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS: T3 default closed; prior rows, relation/function/default ACLs and RLS unchanged; only Home existing definition extended.')
finally:S.drop_database(db)
