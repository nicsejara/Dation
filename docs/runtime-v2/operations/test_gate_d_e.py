import copy, importlib.util, io, json, os, tempfile, unittest, urllib.error
from pathlib import Path
from unittest import mock
spec=importlib.util.spec_from_file_location('go_web',Path(__file__).with_name('gate_d_e_cloud_shell.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.patch=mock.patch.object(p,'STATE',Path(self.temp.name));self.patch.start();self.addCleanup(self.patch.stop)
  self.m=p.artifact()
 def test_official_zip_and_historical_labels_are_preserved(self):
  self.assertEqual(self.m['release']['billing_policy'],'OFF_UNTIL_EXPLICIT_OWNER_GO')
  self.assertEqual(self.m['release']['merge_gate'],'MERGE_BLOCKED_DEPLOY_TRIGGER')
  for k in ('api','executor','recovery'):p.check_spec(copy.deepcopy(self.m[k]),self.m[k],k=='api')
 def test_secret_reference_known_project_alias_preserves_exact_version(self):
  value=copy.deepcopy(self.m['api']);ref=value['template']['containers'][0]['env'][-1]['valueSource']['secretKeyRef']
  ref['secret']='projects/'+p.NUMBER+'/secrets/dation-supabase-secret'
  p.check_spec(value,self.m['api'],True)
  ref['secret']='projects/unapproved/secrets/dation-supabase-secret'
  with self.assertRaises(RuntimeError):p.check_spec(value,self.m['api'],True)
 def test_changed_official_zip_stops(self):
  with mock.patch.object(p,'ZIP_SHA','0'*64),self.assertRaisesRegex(RuntimeError,'checksum'):p.artifact()
 def test_api_unsafe_scaling_cpu_secret_image_and_cloudflag_stop(self):
  for change in ('min','max','cpu','secret','image','flag','sidecar','iam'):
   value=copy.deepcopy(self.m['api']);c=value['template']['containers'][0]
   if change=='min':value['scaling']['minInstanceCount']=1
   if change=='max':value['template']['scaling']['maxInstanceCount']=3
   if change=='cpu':c['resources']['cpuIdle']=False
   if change=='secret':c['env'][-1]['valueSource']['secretKeyRef']['version']='latest'
   if change=='image':c['image']='us-west1-docker.pkg.dev/other/image:latest'
   if change=='flag':next(e for e in c['env'] if e['name']=='DATION_CLOUD_EXECUTION_ENABLED')['value']='true'
   if change=='sidecar':value['template']['containers'].append(copy.deepcopy(c))
   if change=='iam':value['invokerIamDisabled']=True
   with self.subTest(change=change),self.assertRaises(RuntimeError):p.check_spec(value,self.m['api'],True)
 def test_finite_jobs_reject_retries_memory_executions(self):
  for k in ('executor','recovery'):
   for change in ('retry','memory','execution'):
    value=copy.deepcopy(self.m[k])
    if change=='retry':value['template']['template']['maxRetries']=1
    if change=='memory':value['template']['template']['containers'][0]['resources']['limits']['memory']='2Gi'
    if change=='execution':value['executionCount']=1
    with self.subTest(kind=k,change=change),self.assertRaises(RuntimeError):p.check_spec(value,self.m[k])
 def test_public_jobs_forbidden(self):
  for member in ('allUsers','allAuthenticatedUsers'):
   with self.assertRaises(RuntimeError):p.no_public_jobs({'bindings':[{'role':'roles/run.invoker','members':[member]}]})
 def test_iam_delta_cannot_be_project_or_public_job(self):
  for resource,role,member in [(p.JOBS[0],'roles/run.invoker','allUsers'),('projects/'+p.PROJECT,p.ROLE,p.MEMBER),(p.SERVICE,'roles/owner',p.MEMBER)]:
   with self.assertRaisesRegex(RuntimeError,'delta'):p.bind(resource,role,member)
 def test_iam_merge_preserves_etag_and_unrelated_binding(self):
  existing={'version':3,'etag':'fixture-etag','bindings':[{'role':'roles/run.viewer','members':['user:operator@example.invalid']}]}
  merged=copy.deepcopy(existing);merged['bindings'].append({'role':p.ROLE,'members':[p.MEMBER]})
  with mock.patch.object(p,'policy',side_effect=[existing,merged]),mock.patch.object(p,'run_api',return_value={}) as api:
   self.assertTrue(p.bind(p.JOBS[0],p.ROLE,p.MEMBER))
  self.assertEqual(api.call_args.kwargs['body']['policy'],merged)
 def test_no_old_project_or_job_execution_network_request(self):
  for url in ['https://run.googleapis.com/v2/projects/other/locations/us-west1/services','https://run.googleapis.com/v2/'+p.JOBS[0]+':run']:
   with mock.patch.object(p,'gc') as gc,self.assertRaisesRegex(RuntimeError,'Unapproved'):p.api('POST',url,{})
   gc.assert_not_called()
 def test_http401_403_ambiguous404_never_mean_absent(self):
  for code in (401,403,404):
   err=urllib.error.HTTPError('https://run.googleapis.com',code,'',{},io.BytesIO(json.dumps({'error':{'code':code,'status':'PERMISSION_DENIED'}}).encode()))
   opener=mock.Mock();opener.open.side_effect=err
   with mock.patch.object(p,'gc',return_value='fixture'),mock.patch.object(p.urllib.request,'build_opener',return_value=opener),self.assertRaises(p.ApiFailure):p.run_api('GET',p.SERVICE,absent=True)
 def test_structured404_can_mean_absent(self):
  err=urllib.error.HTTPError('https://run.googleapis.com',404,'',{},io.BytesIO(b'{"error":{"code":404,"status":"NOT_FOUND"}}'))
  opener=mock.Mock();opener.open.side_effect=err
  with mock.patch.object(p,'gc',return_value='fixture'),mock.patch.object(p.urllib.request,'build_opener',return_value=opener):self.assertIsNone(p.run_api('GET',p.SERVICE,absent=True))
 def test_existing_resource_is_verified_without_patch_or_create(self):
  with mock.patch.object(p,'run_api',return_value=self.m['executor']) as api:p.ensure_resource(self.m['executor'])
  self.assertEqual(api.call_count,1);self.assertEqual(api.call_args.args[0],'GET')
 def test_create_uses_original_artifact_body(self):
  op={'name':p.BASE+'/operations/example','done':True}
  with mock.patch.object(p,'run_api',side_effect=[None,op,self.m['recovery']]) as api:p.ensure_resource(self.m['recovery'])
  self.assertEqual(api.call_args_list[1].kwargs['body'],self.m['recovery'])
  self.assertTrue((p.STATE/'dation-recovery-operation.json').exists())
 def test_ambiguous_creation_does_not_get_retried(self):
  p.save('dation-core-creation-started.json',{'attempt':True})
  with mock.patch.object(p,'run_api',return_value=None) as api,self.assertRaisesRegex(RuntimeError,'Previous creation'):p.ensure_resource(self.m['api'],True)
  self.assertEqual(api.call_count,1)
 def budget(self,state='CONFIGURED'):
  return {'budgets':[{'budgetFilter':{'projects':['projects/'+p.NUMBER],'services':['services/152E-C115-5142']},'amount':{'specifiedAmount':{'currencyCode':'USD','units':'5'}},'spendCap':{'outputState':state}}]}
 def test_budget_state_and_coverage(self):
  with mock.patch.object(p,'api',return_value=self.budget()):result=p.finops({'billingAccountName':'billingAccounts/ABC-DEF-GHI'})
  self.assertIn('not a total or guaranteed cap',result['scope'])
  for state in ('ENFORCED','AWAITING_NEXT_PERIOD','STATE_UNSPECIFIED'):
   with mock.patch.object(p,'api',return_value=self.budget(state)),self.assertRaisesRegex(RuntimeError,'Spend cap'):p.finops({'billingAccountName':'billingAccounts/ABC-DEF-GHI'})
 def test_budget_read_denial_requires_real_console_confirmation(self):
  with mock.patch.object(p,'api',side_effect=p.ApiFailure(403,{'status':'PERMISSION_DENIED'})),mock.patch('builtins.open',return_value=io.StringIO('\n')),self.assertRaisesRegex(RuntimeError,'not verified'):p.finops({'billingAccountName':'billingAccounts/ABC-DEF-GHI'})
 def test_private_auth_checks_reject_platform403_or_html401(self):
  for code,headers,body in [(403,{},b'platform denied'),(401,{'Content-Type':'text/html'},b'401')]:
   with mock.patch.object(p,'web_request',side_effect=[(200,{},b'{"status":"healthy"}'),(code,headers,body)]),self.assertRaisesRegex(RuntimeError,'Business authentication'):p.verify_web('https://example.run.app','fixture')
 def test_api_is_not_published_without_gate_d(self):
  with mock.patch.object(p,'bind') as bind,self.assertRaisesRegex(RuntimeError,'Gate D'):p.public_api('https://example.run.app')
  bind.assert_not_called()
 def test_failed_public_probe_rolls_back_only_its_new_public_binding(self):
  p.save('GATE_D_RECEIPT.json',{'status':'PASS'})
  with mock.patch.object(p,'bind',return_value=True) as bind,mock.patch.object(p,'wait_public_access'),mock.patch.object(p,'verify_web',side_effect=RuntimeError('probe failed')),self.assertRaises(RuntimeError):p.public_api('https://example.run.app')
  self.assertEqual(bind.call_args_list,[mock.call(p.SERVICE,'roles/run.invoker','allUsers'),mock.call(p.SERVICE,'roles/run.invoker','allUsers',remove=True)])
 def test_only_verified_platform403_propagation_can_be_retried(self):
  public={'bindings':[{'role':'roles/run.invoker','members':['allUsers']}]}
  with mock.patch.object(p,'web_request',side_effect=[(403,{'Content-Type':'text/html'},b'Google platform denied'),(200,{},b'{"status":"healthy"}')]) as request,mock.patch.object(p,'policy',return_value=public),mock.patch.object(p.time,'sleep') as sleep:
   p.wait_public_access('https://example.run.app')
  self.assertEqual(request.call_count,2);sleep.assert_called_once_with(5)
  with mock.patch.object(p,'web_request',return_value=(401,{'Content-Type':'application/json'},b'{}')),mock.patch.object(p.time,'sleep') as sleep,self.assertRaises(RuntimeError):p.wait_public_access('https://example.run.app')
  sleep.assert_not_called()
 def test_missing_go_does_nothing(self):
  with mock.patch.dict(os.environ,{'DATION_GO_WEB':''}),mock.patch.object(p,'gc') as gc,self.assertRaisesRegex(RuntimeError,'GO WEB'):p.main()
  gc.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
