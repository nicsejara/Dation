"""Data Hub against actual tenant SQL/REST, Storage bytes and authenticated API."""
import json
import csv
import io
import os
from pathlib import Path
import subprocess
import time
import unittest
from uuid import uuid4
import httpx
from sandbox import Sandbox,wait_for
from fixtures import csv_input
from auth_fixture import USER_A,USER_B,VIEWER

class DataHubTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.s=Sandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
 def setUp(self):
  self.s.stop(self.s.worker)
  self.s.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events,dation_private.dataset_deletions,dation_private.dataset_uploads CASCADE;')
  self.s.sql("UPDATE workspace_ddas SET status='enabled' WHERE dda_id='logistics';")
  self.a=self.s.api_client
  self.b=httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False,timeout=30);self.addCleanup(self.b.close)
 def checked(self,response,status=200):
  self.assertEqual(response.status_code,status,response.text[:1500]);return response.json()
 def upload(self,kind='orders',client=None):
  result=self.checked((client or self.a).post('/api/platform/data/datasets/upload',params={'dataset_type':kind},files={'file':(kind+'.csv',csv_input(kind),'text/csv')}))
  return result.get('dataset') or result['existing_dataset']
 def case(self,orders,fleet,client=None):
  case=str(uuid4());self.checked((client or self.a).post('/api/decision-cases',json={'id':case,'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id']}));return case
 def detail(self,row):return self.checked(self.a.get('/api/platform/data/datasets/'+row['id']))
 def file(self,row):return self.s.storage/row['storage_bucket']/row['storage_path']

 def test_01_library_attribution_pagination_literal_search_and_workspace_boundary(self):
  orders=self.upload();fleet=self.upload('fleet');other=self.upload(client=self.b)
  self.assertNotEqual(orders['id'],other['id'])
  listing=self.checked(self.a.get('/api/platform/data/datasets',params={'limit':1}))
  self.assertEqual((listing['total'],len(listing['items'])),(2,1))
  second=self.checked(self.a.get('/api/platform/data/datasets',params={'limit':1,'offset':1}))
  self.assertNotEqual(listing['items'][0]['id'],second['items'][0]['id'])
  self.assertEqual(self.detail(orders)['dataset']['uploaded_by']['id'],USER_A)
  self.assertNotIn('storage_path',json.dumps(listing));self.assertNotIn('storage_bucket',json.dumps(listing))
  for query in ["' OR true --",'%',other['id']]:
   self.assertEqual(self.checked(self.a.get('/api/platform/data/datasets',params={'q':query}))['total'],0)
  self.assertEqual(self.checked(self.a.get('/api/platform/data/datasets',params={'q':orders['canonical_filename'],'workspace_id':self.s.workspace_b}))['items'][0]['id'],orders['id'])
  self.assertEqual(self.checked(self.a.get('/api/platform/data/datasets',params={'filter':'orders'}))['total'],1)
  for method,suffix in [('GET',''),('GET','/preview'),('GET','/download'),('POST','/archive'),('POST','/unarchive'),('DELETE','')]:
   self.assertEqual(self.b.request(method,'/api/platform/data/datasets/'+orders['id']+suffix,timeout=3).status_code,404)
  for body in [{'target_workspace_id':self.s.workspace_a,'actor_user_id':USER_B}]:
   self.assertEqual(self.s.db.post('rpc/platform_data_hub',json=body).status_code,403)
  for credential in (self.s.anon_token,self.s.user_tokens[USER_A]):
   for function,extra in [('platform_dataset_library',{}),('platform_data_hub',{}),('platform_dataset_delete',{'target_dataset_id':orders['id']}),('platform_dataset_upload',{'operation':'discard','operation_id':str(uuid4())})]:
    self.assertIn(self.s.http.post(self.s.rest_url+'/rpc/'+function,headers={'Authorization':'Bearer '+credential},json={'target_workspace_id':self.s.workspace_a,'actor_user_id':USER_A,**extra}).status_code,(401,403))
  self.assertEqual(self.a.get('/api/platform/data/datasets?limit=51').status_code,422)
  immutable=self.s.db.patch('datasets',params={'id':'eq.'+orders['id']},json={'uploaded_by_user_id':USER_B})
  self.assertGreaterEqual(immutable.status_code,400)

 def test_02_detail_preview_filters_and_derived_packs_preserve_case_history(self):
  orders,fleet=self.upload(),self.upload('fleet');cases=[self.case(orders,fleet) for _ in range(2)]
  self.checked(self.a.patch('/api/decision-cases/'+cases[0],json={'status':'archived'}))
  before=self.s.sql('SELECT md5(string_agg(to_jsonb(c)::text,\'\' ORDER BY id)) FROM decision_cases c;')
  detail=self.detail(orders);self.assertEqual(detail['dataset']['case_count'],2);self.assertEqual(len(detail['used_in']),2);self.assertFalse(detail['can_delete'])
  first=self.checked(self.a.get('/api/platform/data/datasets/'+orders['id']+'/preview',params={'limit':1}))
  second=self.checked(self.a.get('/api/platform/data/datasets/'+orders['id']+'/preview',params={'limit':1,'offset':1}))
  self.assertEqual(len(first['rows']),1);self.assertTrue(first['has_more']);self.assertNotEqual(first['rows'][0],second['rows'][0])
  packs=self.checked(self.a.get('/api/platform/data/packs'));self.assertEqual(packs['total'],1);self.assertEqual(packs['items'][0]['case_count'],2)
  pack=self.checked(self.a.get('/api/platform/data/pack',params={'orders_id':orders['id'],'fleet_id':fleet['id'],'limit':1,'offset':1}))
  self.assertEqual(pack['pack']['case_count'],2);self.assertEqual(len(pack['used_in']),1)
  self.assertEqual(self.s.sql('SELECT md5(string_agg(to_jsonb(c)::text,\'\' ORDER BY id)) FROM decision_cases c;'),before)
  self.checked(self.a.post('/api/platform/data/datasets/'+orders['id']+'/archive'))
  self.assertEqual(self.checked(self.a.get('/api/platform/data/datasets'))['total'],1)
  self.assertEqual(self.checked(self.a.get('/api/platform/data/datasets?filter=archived'))['items'][0]['id'],orders['id'])
  self.checked(self.a.delete('/api/platform/data/datasets/'+orders['id']),409);self.assertTrue(self.file(orders).is_file())
  self.checked(self.a.post('/api/platform/data/datasets/'+orders['id']+'/unarchive'))
  self.s.sql(f"UPDATE datasets SET profile_json=jsonb_set(profile_json,'{{valid}}','false') WHERE id='{orders['id']}';")
  self.assertEqual(self.checked(self.a.get('/api/platform/data/datasets?filter=issues'))['items'][0]['id'],orders['id'])
  self.assertEqual(self.checked(self.a.get('/api/platform/data/datasets?filter=validated'))['items'][0]['id'],fleet['id'])

 def test_03_data_hub_survives_disabled_dda_but_reuse_and_viewer_writes_are_denied(self):
  orders,fleet=self.upload(),self.upload('fleet');self.case(orders,fleet)
  self.s.sql(f"UPDATE workspace_ddas SET status='disabled' WHERE workspace_id='{self.s.workspace_a}' AND dda_id='logistics';")
  self.assertEqual(self.a.get('/api/decision-cases').status_code,403)
  for path in ['/api/platform/data/datasets','/api/platform/data/datasets/'+orders['id'],'/api/platform/data/packs','/api/platform/data/datasets/'+orders['id']+'/preview']:
   self.assertEqual(self.a.get(path).status_code,200,path)
  self.assertEqual(self.a.post('/api/platform/data/datasets/'+orders['id']+'/reuse').status_code,403)
  self.assertEqual(self.a.post('/api/platform/data/pack/reuse',json={'orders_id':orders['id'],'fleet_id':fleet['id']}).status_code,403)
  # Upload still belongs to the workspace library, independent of using a DDA.
  self.assertEqual(self.a.post('/api/platform/data/datasets/upload',params={'dataset_type':'orders'},files={'file':('orders.csv',csv_input('orders'),'text/csv')}).status_code,200)
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as viewer:
   self.assertEqual(viewer.get('/api/platform/data/datasets').status_code,200)
   for suffix in ['', '/preview','/download']:
    self.assertEqual(viewer.get('/api/platform/data/datasets/'+orders['id']+suffix).status_code,200)
   self.assertFalse(self.checked(viewer.get('/api/platform/data/datasets/'+orders['id']))['can_archive'])
   for method,path in [('POST','/archive'),('POST','/unarchive'),('POST','/reuse'),('DELETE','')]:
    self.assertEqual(viewer.request(method,'/api/platform/data/datasets/'+orders['id']+path).status_code,403)
   for operation in ('upload','validate'):
    self.assertEqual(viewer.post('/api/platform/data/datasets/'+operation,params={'dataset_type':'orders'},files={'file':('orders.csv',csv_input('orders'),'text/csv')}).status_code,403)

 def test_04_deletion_is_recoverable_and_prevents_new_references(self):
  orders,fleet=self.upload(),self.upload('fleet')
  self.checked(self.a.delete('/api/platform/data/datasets/'+orders['id']),409)
  self.checked(self.a.post('/api/platform/data/datasets/'+orders['id']+'/archive'))
  (self.s.storage/'fail-next-delete').touch()
  self.checked(self.a.delete('/api/platform/data/datasets/'+orders['id']),503)
  detail=self.detail(orders);self.assertTrue(detail['dataset']['deletion_pending']);self.assertTrue(detail['can_delete']);self.assertTrue(self.file(orders).is_file())
  for suffix in ['/preview','/download','/reuse']:
   result=self.a.post('/api/platform/data/datasets/'+orders['id']+suffix) if suffix=='/reuse' else self.a.get('/api/platform/data/datasets/'+orders['id']+suffix)
   self.assertEqual(result.status_code,404)
  self.assertEqual(self.a.post('/api/decision-cases',json={'id':str(uuid4()),'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id']}).status_code,404)
  bypass=self.s.db.post('decision_cases',json={'id':str(uuid4()),'workspace_id':self.s.workspace_a,'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id'],'input_signature':'synthetic'})
  self.assertGreaterEqual(bypass.status_code,400)
  self.assertIn('pending',bypass.text.lower())
  self.assertTrue(self.checked(self.a.delete('/api/platform/data/datasets/'+orders['id']))['deleted'])
  self.assertFalse(self.file(orders).exists());self.assertEqual(self.s.sql(f"SELECT count(*) FROM datasets WHERE id='{orders['id']}';"),'0')
  self.assertTrue(self.checked(self.a.delete('/api/platform/data/datasets/'+orders['id']))['deleted'])
  self.assertEqual(self.b.delete('/api/platform/data/datasets/'+orders['id']).status_code,404)
  self.assertEqual(self.s.sql("SELECT count(*) FROM dation_private.dataset_deletions WHERE status='pending';"),'0')

 def test_05_row_lock_conflict_returns_retryable_error_without_deleting_storage(self):
  orders=self.upload();self.checked(self.a.post('/api/platform/data/datasets/'+orders['id']+'/archive'))
  command=['docker','exec','-i',self.s.pg,'psql','-U','postgres','-d',self.s.database,'-v','ON_ERROR_STOP=1']
  process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
  try:
   process.stdin.write(f"SET application_name='dation-hub-lock-test'; BEGIN; SELECT id FROM datasets WHERE id='{orders['id']}' FOR UPDATE; SELECT pg_sleep(5); COMMIT;\n");process.stdin.close()
   wait_for(lambda:self.s.sql("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE application_name='dation-hub-lock-test' AND wait_event='PgSleep');")=='t','dataset row lock',timeout=3)
   start=time.monotonic();response=self.a.delete('/api/platform/data/datasets/'+orders['id'],timeout=3)
   self.assertEqual(response.status_code,409,response.text);self.assertEqual(response.headers.get('X-Dation-Retryable'),'true');self.assertLess(time.monotonic()-start,3)
   self.assertTrue(self.file(orders).is_file());self.assertFalse(self.detail(orders)['dataset']['deletion_pending'])
  finally:process.wait(timeout=10);process.stderr.close()

 def test_06_real_browser_dda_upload_library_lineage_download_and_safe_delete(self):
  orders,fleet=self.upload(),self.upload('fleet');case=self.case(orders,fleet);self.s.start_worker()
  reader=csv.DictReader(io.StringIO(csv_input('orders').decode()),delimiter=';');rows=list(reader)
  rows[0]['order_id']='HUB-UPLOAD-'+str(uuid4());rows[0]['product']='<img src=x onerror=window.__bad=1>'
  stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=reader.fieldnames,delimiter=';',lineterminator='\n');writer.writeheader();writer.writerows(rows)
  path=self.s.directory/'datos ñ.csv';path.write_text(stream.getvalue())
  before=self.s.sql('SELECT md5(string_agg(to_jsonb(c)::text,\'\' ORDER BY id)) FROM decision_cases c;')
  root=Path(__file__).resolve().parents[2]
  result=subprocess.run([os.getenv('DATION_BROWSER_PYTHON',str(root/'.browser-venv/bin/python')),str(root/'tests/e2e/data_hub_journey.py')],cwd=root,
   env={**self.s.env,'DATION_E2E_URL':self.s.api_url,'DATION_HUB_CASE':case,'DATION_HUB_ORDERS':orders['id'],'DATION_HUB_INPUT':str(path)},capture_output=True,text=True,timeout=150)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  self.assertEqual(self.s.sql('SELECT md5(string_agg(to_jsonb(c)::text,\'\' ORDER BY id)) FROM decision_cases c;'),before)
  self.assertEqual(self.s.sql('SELECT count(*) FROM datasets;'),'2')
  self.assertTrue(self.file(orders).is_file());self.assertTrue(self.file(fleet).is_file())
  self.assertEqual(self.s.sql("SELECT count(*) FROM dation_private.dataset_deletions WHERE status='completed';"),'1')

 def test_07_failed_upload_cleanup_is_tracked_and_workspace_authorized(self):
  (self.s.storage/'fail-next-dataset-insert').touch();(self.s.storage/'fail-next-delete').touch()
  self.checked(self.a.post('/api/platform/data/datasets/upload',params={'dataset_type':'orders'},files={'file':('interrumpida.csv',csv_input('orders'),'text/csv')}),503)
  listing=self.checked(self.a.get('/api/platform/data/datasets'))
  self.assertEqual(listing['total'],0);self.assertEqual(len(listing['incomplete_uploads']),1)
  operation=listing['incomplete_uploads'][0];self.assertNotIn('storage_path',json.dumps(operation))
  stored=json.loads(self.s.sql("SELECT row_to_json(u) FROM dation_private.dataset_uploads u WHERE status='discarding';"))
  path=self.s.storage/stored['storage_bucket']/stored['storage_path'];self.assertTrue(path.exists())
  self.assertEqual(self.b.post('/api/platform/data/uploads/'+operation['id']+'/discard').status_code,404);self.assertTrue(path.exists())
  self.checked(self.a.post('/api/platform/data/uploads/'+operation['id']+'/discard'))
  self.assertFalse(path.exists());self.assertEqual(self.checked(self.a.get('/api/platform/data/datasets'))['incomplete_uploads'],[])
  self.checked(self.a.post('/api/platform/data/uploads/'+operation['id']+'/discard'))

 def test_08_historical_unknown_attribution_and_validation_are_not_invented(self):
  identifier=str(uuid4());path=self.s.workspace_a+'/'+identifier+'/input.csv'
  row={'id':identifier,'workspace_id':self.s.workspace_a,'original_filename':'historico.csv',
   'storage_bucket':'dda-inputs','storage_path':path,'dataset_type':'logistics_legacy',
   'status':'error','row_count':2,'profile_json':['historical format']}
  self.checked(self.s.db.post('datasets',headers={'Prefer':'return=representation'},json=row),201)
  file=self.s.storage/'dda-inputs'/path;file.parent.mkdir(parents=True);file.write_bytes(csv_input('orders'))
  detail=self.checked(self.a.get('/api/platform/data/datasets/'+identifier))
  self.assertIsNone(detail['dataset']['uploaded_by']);self.assertEqual(detail['dataset']['validation'],'unknown')
  self.assertFalse(detail['can_archive']);self.assertEqual(detail['validation_report']['errors'],[])
  self.assertEqual(self.checked(self.a.get('/api/platform/data/datasets?filter=issues'))['total'],0)
  self.assertEqual(len(self.checked(self.a.get('/api/platform/data/datasets/'+identifier+'/preview'))['rows']),2)

 def test_09_v2_summary_composed_filters_historical_lineage_and_read_purity(self):
  orders,fleet=self.upload(),self.upload('fleet');other=self.upload(client=self.b)
  case=self.case(orders,fleet)
  self.s.sql(f"UPDATE decision_cases SET label='Semana 43' WHERE id='{case}';")
  before=self.s.sql("SELECT md5(string_agg(to_jsonb(d)::text,'' ORDER BY id)) FROM datasets d;")
  response=self.checked(self.a.get('/api/platform/data/datasets?limit=1&type=orders&validation=validated&state=all'))
  self.assertEqual(response['summary'],{'total':2,'validated':2,'issues':0,'archived':0});self.assertEqual(response['total'],1)
  detail=self.detail(orders);self.assertEqual(detail['case_total'],1);self.assertEqual(detail['used_in'][0]['label'],'Semana 43');self.assertEqual(detail['used_in'][0]['dda'],'logistics')
  self.assertEqual(self.s.sql("SELECT md5(string_agg(to_jsonb(d)::text,'' ORDER BY id)) FROM datasets d;"),before)
  self.checked(self.a.post('/api/platform/data/datasets/'+orders['id']+'/archive'))
  result=self.checked(self.a.get('/api/platform/data/datasets?state=active&type=fleet&limit=1&offset=1'))
  self.assertEqual(result['summary'],{'total':2,'validated':2,'issues':0,'archived':1});self.assertEqual(result['items'],[])
  self.assertEqual(self.checked(self.a.get('/api/platform/data/datasets?state=all'))['total'],2)
  self.assertEqual(self.checked(self.a.get('/api/platform/data/datasets?type=fleet&state=archived'))['total'],0)
  for query in ['type=bad','validation=bad','state=bad']:
   self.assertEqual(self.a.get('/api/platform/data/datasets?'+query).status_code,422)

  replacement=self.checked(self.a.post('/api/platform/data/datasets/upload',params={'dataset_type':'orders'},files={'file':('version.csv',csv_input('orders')+b'\n','text/csv')}))['dataset']
  self.s.sql(f"INSERT INTO decision_runs(id,workspace_id,dataset_id,orders_dataset_id,fleet_dataset_id,decision_case_id,node_id,status,engine_name,engine_version,result_json) VALUES('{uuid4()}','{self.s.workspace_a}','{orders['id']}','{orders['id']}','{fleet['id']}','{case}','logistics_assignment','completed','historical-test','1','{{}}'); UPDATE decision_cases SET orders_dataset_id='{replacement['id']}' WHERE id='{case}';")
  self.assertEqual(self.detail(orders)['case_total'],1)
  self.assertEqual(self.detail(orders)['used_in'][0]['id'],case)
  page=self.checked(self.a.get('/api/platform/data/datasets?state=all&type=orders'))
  self.assertEqual(next(d for d in page['items'] if d['id']==orders['id'])['case_count'],1)

 def test_10_lost_committed_upload_response_preserves_metadata_and_bytes(self):
  (self.s.storage/'fail-next-dataset-response').touch()
  self.checked(self.a.post('/api/platform/data/datasets/upload',params={'dataset_type':'orders'},files={'file':('confirmada.csv',csv_input('orders'),'text/csv')}),503)
  listing=self.checked(self.a.get('/api/platform/data/datasets'))
  self.assertEqual(listing['total'],1);self.assertEqual(listing['incomplete_uploads'],[])
  result=self.checked(self.a.post('/api/platform/data/datasets/upload',params={'dataset_type':'orders'},files={'file':('confirmada.csv',csv_input('orders'),'text/csv')}))
  self.assertTrue(result['duplicate']);row=result['existing_dataset']
  self.assertEqual(self.file(row).read_bytes(),csv_input('orders'))
  self.assertEqual(self.a.get('/api/platform/data/datasets/'+row['id']+'/download').content,csv_input('orders'))
  self.assertEqual(self.s.sql("SELECT count(*) FROM dation_private.dataset_uploads WHERE status='stored';"),'1')
