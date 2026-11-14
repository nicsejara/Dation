"""G6 security contracts and controlled end-to-end simulations: zero GCP calls."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import urllib.error
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/release'))
import g6_common as common
import g6_orchestrator as orchestrator
import g6_release as release
import g6_bootstrap as bootstrap
import yaml
scope=orchestrator.scope
APP='a'*40;BASE='b'*40;RUN='501'
IMAGE=common.REGISTRY+'@sha256:'+'c'*64
OLD_IMAGE=common.REGISTRY+'@sha256:'+'d'*64
OLD=common.RESOURCE+'/revisions/dation-core-00002-old'
UI='backend/app/static/js/dispatch/cases/ultimate-case-setup.mjs'
CSS='backend/app/static/css/decision-map-case-v2.css'
TEST='backend/tests/browser/test_ultimate_case_setup.py'

def plan():
 return {'status':'ELIGIBLE','application_sha':APP,'control_sha':APP,'release_id':'g6-'+RUN,'release_run_id':RUN,
  'repository_id':1114679650,'policy_sha256':scope.policy_hash(),'gate_run_id':100,'risk':'R2','pr_number':9}

def publication():
 return {'status':'PUBLISH_PASS','release_id':'g6-'+RUN,'application_sha':APP,'image_digest':IMAGE,'publish_run_id':200}

def template():
 spec=importlib.util.spec_from_file_location('g6_manifest',ROOT/'scripts/zero_idle_release.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 config=json.loads((ROOT/'infra/zero-idle/release.json').read_text());config.update(image=OLD_IMAGE,release_sha=BASE)
 result=module.manifest(config)['service']['template']
 result['containers'][0]['resources']['startupCpuBoost']=False
 return result

class FakeGitHub:
 def __init__(self):self.head=APP;self.protection=True;self.gates=[]
 def main(self):return self.head
 def protected(self):common.require(self.protection,'unprotected main')
 def gate(self,*args):self.gates.append(args)

class FakeCloud:
 def __init__(self):
  self.service={'name':common.RESOURCE,'generation':'10','etag':'e10','reconciling':False,
   'template':template(),'scaling':{'minInstanceCount':0,'maxInstanceCount':2},'uri':common.POLICY['service_url'],
   'traffic':[{'type':'TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION','revision':'dation-core-00002-old','percent':100}],
   'trafficStatuses':[{'revision':OLD,'percent':100}],'latestCreatedRevision':OLD,'latestReadyRevision':OLD}
  self.revisions={OLD:{**copy.deepcopy(self.service['template']),'name':OLD,'conditions':[{'type':'Ready','state':'CONDITION_SUCCEEDED'}]}}
  self.iam_policy={'version':3,'etag':'iam1','bindings':[{'role':'roles/run.invoker','members':['allUsers']}]}
  self.writes=[];self.registry_calls=[]
 def iam(self):return copy.deepcopy(self.iam_policy)
 def registry(self,*args):self.registry_calls.append(args)
 def application_sha(self,image):return BASE
 def api(self,resource=common.RESOURCE,method='GET',body=None,query='',missing=False):
  if method=='GET':
   if resource==common.RESOURCE:return copy.deepcopy(self.service)
   if resource in self.revisions:return copy.deepcopy(self.revisions[resource])
   if missing:return None
   raise RuntimeError('missing fake revision')
  common.require(method=='PATCH' and resource==common.RESOURCE,'fake forbids all but service patch')
  common.require(body['etag']==self.service['etag'],'fake CAS conflict')
  self.writes.append(copy.deepcopy({'body':body,'query':query}))
  generation=int(self.service['generation'])+1;self.service.update(generation=str(generation),etag='e'+str(generation))
  if 'template' in body:
   t=copy.deepcopy(body['template']);self.service['template']=t
   name=common.RESOURCE+'/revisions/'+t['revision']
   self.revisions[name]={**copy.deepcopy(t),'name':name,'conditions':[{'type':'Ready','state':'CONDITION_SUCCEEDED'}]}
   self.service.update(latestCreatedRevision=name,latestReadyRevision=name)
  self.service['traffic']=copy.deepcopy(body['traffic']);statuses=[]
  for row in body['traffic']:
   target={'revision':common.RESOURCE+'/revisions/'+row['revision'],'percent':row.get('percent',0)}
   if row.get('tag'):target.update(tag=row['tag'],uri='https://'+row['tag']+'---dation-core-example-uw.a.run.app')
   statuses.append(target)
  self.service['trafficStatuses']=statuses
  return {'name':'unused-operation-not-polled'}

class ScopeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.repo=Path(self.temp.name)
  self.patch=mock.patch.object(scope,'ROOT',self.repo);self.patch.start();self.addCleanup(self.patch.stop)
  self.git('init','-q','--initial-branch=main');self.git('config','user.email','fixture@example.invalid');self.git('config','user.name','Fixture')
  self.put(UI,"export const label='Before';\n");self.put(CSS,'.ultimate-graph-view { color: red; }\n')
  self.put(TEST,"def test_contract(self):\n self.assertEqual(button('Before'), 1)\n")
  self.git('add','.');self.git('commit','-qm','baseline');self.base=self.git('rev-parse','HEAD')
 def git(self,*args):return subprocess.check_output(['git',*args],cwd=self.repo,text=True,stderr=subprocess.DEVNULL).strip()
 def put(self,path,text):
  p=self.repo/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
 def commit(self):self.git('add','.');self.git('commit','-qm','UX');return self.git('rev-parse','HEAD')
 def pull(self,sha):return {'merged':True,'merge_commit_sha':sha,'number':9,'base':{'ref':'main','repo':{'id':1114679650}},'head':{'sha':sha,'repo':{'id':1114679650}},'user':{'id':249153366},'merged_by':{'id':249153366}}
 def test_r1_real_squash_diff(self):
  self.put(CSS,'.ultimate-graph-view { color: blue; }\n');sha=self.commit()
  self.assertEqual(scope.eligible_commit(sha,self.pull(sha),self.base)['risk'],'R1')
 def test_r2_real_diff_preserves_selector_assertions(self):
  self.put(UI,"export const label='After';\n");self.put(TEST,"def test_contract(self):\n self.assertEqual(button('After'), 1)\n")
  sha=self.commit();self.assertEqual(scope.eligible_commit(sha,self.pull(sha),self.base)['risk'],'R2')
 def test_sensitive_unknown_test_only_and_mixed_denied(self):
  for paths in [['backend/main.py'],['.github/workflows/x.yml'],['supabase/new.sql'],['unknown.js'],[TEST],[UI,'scripts/ci/impact.py']]:
   with self.subTest(paths=paths),self.assertRaises(RuntimeError):scope.classify(paths)
 def test_pr_head_fork_or_unmerged_is_denied(self):
  self.put(UI,"export const label='After';\n");sha=self.commit()
  for field in ('merged','fork','other_sha','author'):
   p=self.pull(sha)
   if field=='merged':p['merged']=False
   if field=='fork':p['head']['repo']['id']=999
   if field=='other_sha':p['merge_commit_sha']=BASE
   if field=='author':p['user']['id']=999
   with self.subTest(field=field),self.assertRaises(RuntimeError):scope.eligible_commit(sha,p,self.base)
 def test_cumulative_backend_then_ux_cannot_launder_r3(self):
  self.put('backend/new.py','backend_change = True\n');self.commit()
  self.put(UI,"export const label='After';\n");sha=self.commit()
  with self.assertRaisesRegex(RuntimeError,'runtime delta'):scope.eligible_commit(sha,self.pull(sha),self.base)
 def test_parent_pair_is_verified_for_merge_commit(self):
  self.git('checkout','-qb','ux');self.put(UI,"export const label='After';\n");head=self.commit()
  self.git('checkout','-q','main');self.git('merge','--no-ff','-qm','merge','ux');sha=self.git('rev-parse','HEAD')
  p=self.pull(sha);p['head']['sha']=head
  self.assertEqual(scope.eligible_commit(sha,p,self.base)['risk'],'R2')
  p['head']['sha']=BASE
  with self.assertRaises(RuntimeError):scope.eligible_commit(sha,p,self.base)
 def test_deletion_or_symlink_cannot_be_ux(self):
  self.git('rm','-q',CSS);sha=self.commit()
  with self.assertRaises(RuntimeError):scope.eligible_commit(sha,self.pull(sha),self.base)
 def test_api_import_or_auth_surface_change_is_denied(self):
  for code in ["export const label='Before';fetch('/api/runs');\n","import x from './new-auth.mjs';\n","document.cookie='value';\n"]:
   self.git('reset','--hard',self.base);self.put(UI,code);sha=self.commit()
   with self.subTest(code=code),self.assertRaisesRegex(RuntimeError,'surface'):scope.eligible_commit(sha,self.pull(sha),self.base)
 def test_removed_assertion_is_denied(self):
  self.put(UI,"export const label='After';\n");self.put(TEST,'def test_contract(self):\n pass\n');sha=self.commit()
  with self.assertRaisesRegex(RuntimeError,'assertions'):scope.eligible_commit(sha,self.pull(sha),self.base)

class TransportAndWorkflowTests(unittest.TestCase):
 def test_cloud_transport_cannot_mutate_iam_jobs_other_project_or_fields(self):
  c=common.CloudRun('fixture')
  for resource,method,body,query in [(common.RESOURCE+':setIamPolicy','POST',{},''),('projects/other/locations/us-west1/services/dation-core','GET',None,''),
   (common.RESOURCE.replace('/services/dation-core','/jobs/dation-executor')+':run','POST',{},''),(common.RESOURCE,'PATCH',{'name':common.RESOURCE,'etag':'x','traffic':[],'scaling':{}},'traffic')]:
   with self.subTest(resource=resource),mock.patch.object(common,'request') as request,self.assertRaises(RuntimeError):c.api(resource,method=method,body=body,query=query)
   request.assert_not_called()
 def test_readonly_identity_job_never_patches(self):
  with mock.patch.object(common,'request') as request,self.assertRaises(RuntimeError):common.CloudRun('fixture',read_only=True).api(method='PATCH',body={'name':common.RESOURCE,'etag':'x','traffic':[]},query='traffic')
  request.assert_not_called()
 def test_revision_paths_cannot_escape_service_or_inject_queries(self):
  for suffix in ('../other','dation-core-test/../../jobs/other','dation-core-test?fields=other','dation-core-test:run'):
   with self.subTest(suffix=suffix),mock.patch.object(common,'request') as request,self.assertRaises(RuntimeError):
    common.CloudRun('fixture').api(common.RESOURCE+'/revisions/'+suffix)
   request.assert_not_called()
   with self.assertRaises(RuntimeError):release.revision_id(common.RESOURCE+'/revisions/'+suffix)
 def test_codeowners_protects_the_shared_publisher_project_identity(self):
  self.assertIn('/backend/app/cloud_identity.py',common.POLICY['required_codeowner_paths'])
  self.assertIn('/backend/app/cloud_identity.py @nicsejara',(ROOT/'.github/CODEOWNERS').read_text())
 def test_registry_conflicting_digest_is_denied(self):
  value={'version':'projects/'+common.PROJECT+'/locations/us-west1/repositories/dation-runtime/packages/dation-core/versions/sha256:'+'f'*64}
  with mock.patch.object(common,'request',return_value=value),self.assertRaisesRegex(RuntimeError,'tag differs'):common.CloudRun('fixture').registry(APP,IMAGE)
 def test_http401_403_and_ambiguous404_are_not_missing(self):
  for code in (401,403,404):
   err=urllib.error.HTTPError('https://run.googleapis.com',code,'',{},io.BytesIO(json.dumps({'error':{'code':code,'status':'PERMISSION_DENIED'}}).encode()))
   opener=mock.Mock();opener.open.side_effect=err
   with mock.patch.object(common.urllib.request,'build_opener',return_value=opener),self.assertRaises(common.HttpError):common.request('GET','https://run.googleapis.com','fixture',missing=True)
 def test_workflow_tokens_and_checkpoints_are_separated(self):
  w=yaml.load((ROOT/'.github/workflows/dation-ux-autorelease.yml').read_text(),Loader=yaml.BaseLoader)
  self.assertEqual(set(w['on']),{'workflow_run'});self.assertEqual(w['on']['workflow_run']['branches'],['main'])
  self.assertEqual(w['concurrency'],{'group':'dation-core-ux-release','cancel-in-progress':'false'})
  self.assertNotIn('id-token',w['jobs']['eligibility']['permissions']);self.assertNotIn('id-token',w['jobs']['publication']['permissions'])
  self.assertEqual(w['jobs']['publication']['permissions']['actions'],'write')
  self.assertNotIn('actions: write',str(w['jobs']['deployment']))
  self.assertEqual(w['jobs']['deployment']['permissions']['id-token'],'write')
  steps=w['jobs']['deployment']['steps'];names=[s.get('name','') for s in steps]
  self.assertLess(names.index('Persist snapshot before preparing a revision'),names.index('Prepare exact revision with zero default traffic'))
  self.assertLess(names.index('Persist promotion intent before moving traffic'),names.index('Promote exact revision, post-health and conditional rollback'))
  for job in w['jobs'].values():
   for step in job['steps']:
    if 'uses' in step:self.assertRegex(step['uses'],r'@[a-f0-9]{40}$')
    if step.get('uses','').startswith('google-github-actions/auth@'):
     self.assertEqual(step['with']['create_credentials_file'],'false');self.assertNotIn('credentials_json',step['with'])
 def test_wif_exact_workflow_event_pairs_numeric_ids_and_environment(self):
  p=bootstrap.plan();condition=p['attribute_condition']
  for value in ['1114679650','249153366',"assertion.ref == 'refs/heads/main'",'environment:ux-mvp-auto',common.AUTO_PATH+'@refs/heads/main',common.OPS_PATH+'@refs/heads/main',"assertion.event_name == 'workflow_run'","assertion.event_name == 'workflow_dispatch'"]:self.assertIn(value,condition)
  self.assertEqual(p['attribute_mapping'],{'google.subject':'assertion.repository_id'})
  self.assertTrue(p['federated_principal'].endswith('/subject/1114679650'))
  self.assertEqual(set(p['custom_role']['includedPermissions']),{'run.services.get','run.services.update','run.services.getIamPolicy','run.revisions.get'})
  self.assertEqual(p['project_roles_granted'],[]);self.assertFalse(p['keys_created']);self.assertFalse(p['auto_deploy_enabled'])
 def test_bootstrap_default_preview_has_no_side_effect(self):
  with mock.patch.object(sys,'argv',['g6_bootstrap.py']),mock.patch.object(bootstrap.subprocess,'run') as command,mock.patch('sys.stdout',new_callable=io.StringIO) as out:bootstrap.main()
  command.assert_not_called();self.assertEqual(json.loads(out.getvalue())['status'],'PREVIEW_ONLY')
 def test_bootstrap_wrong_confirmation_or_hash_stops_before_io(self):
  for confirmation,sha in [('',common.fingerprint(bootstrap.plan())),('GO_G6_BOOTSTRAP_IDENTITY','wrong')]:
   with mock.patch.object(bootstrap.subprocess,'run') as command,self.assertRaises(RuntimeError):bootstrap.apply(bootstrap.plan(),confirmation,sha)
   command.assert_not_called()
 def test_unprotected_main_cannot_pass(self):
  gh=common.GitHub('fixture')
  with mock.patch.object(gh,'api',return_value={'protected':False}),self.assertRaisesRegex(RuntimeError,'protection'):gh.protected()
 def test_wrong_wif_execution_claims_are_rejected(self):
  env={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':'nicsejara/Dation','GITHUB_REPOSITORY_ID':'1114679650','GITHUB_REPOSITORY_OWNER_ID':'249153366',
   'GITHUB_REF':'refs/heads/main','GITHUB_EVENT_NAME':'workflow_run','GITHUB_RUN_ATTEMPT':'1','GITHUB_RUN_ID':RUN,'GITHUB_SHA':APP,'GITHUB_WORKFLOW_REF':'nicsejara/Dation/'+common.AUTO_PATH+'@refs/heads/main'}
  common.context(env=env)
  for key in env:
   bad=dict(env);bad[key]='wrong'
   with self.subTest(key=key),self.assertRaises(RuntimeError):common.context(env=bad)

class OrchestrationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name)
  self.env={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':'nicsejara/Dation','GITHUB_REPOSITORY_ID':'1114679650','GITHUB_REPOSITORY_OWNER_ID':'249153366',
   'GITHUB_REF':'refs/heads/main','GITHUB_EVENT_NAME':'workflow_run','GITHUB_RUN_ATTEMPT':'1','GITHUB_RUN_ID':RUN,'GITHUB_SHA':APP,
   'GITHUB_WORKFLOW_REF':'nicsejara/Dation/'+common.AUTO_PATH+'@refs/heads/main','DATION_UX_AUTODEPLOY_ENABLED':'true',
   'DATION_UX_BOOTSTRAP_APPROVED':'true','DATION_UX_POLICY_SHA256':scope.policy_hash(),'DATION_UX_BASELINE_SHA':BASE}
  self.event={'workflow_run':{'id':100,'event':'push','conclusion':'success','head_branch':'main','head_sha':APP,'head_repository':{'id':1114679650}}}
  self.gh=mock.Mock();self.gh.main.return_value=APP
  self.gh.pages.return_value=[{'merged_at':'2026-11-13','merge_commit_sha':APP,'number':9,'base':{'ref':'main'}}]
  self.gh.api.return_value={'number':9}
 def test_disabled_switch_stops_before_any_github_or_cloud_call(self):
  for value in ('','false','TRUE'):
   env={**self.env,'DATION_UX_AUTODEPLOY_ENABLED':value}
   result=orchestrator.preflight(self.gh,self.event,env)
   self.assertEqual(result['status'],'SKIPPED');self.gh.assert_not_called();self.assertEqual(self.gh.mock_calls,[])
 def test_bootstrap_policy_and_wrong_green_sha_fail_before_publish(self):
  for change in ({'DATION_UX_BOOTSTRAP_APPROVED':''},{'DATION_UX_POLICY_SHA256':'wrong'},{'GITHUB_SHA':BASE}):
   with self.subTest(change=change),self.assertRaises(RuntimeError):orchestrator.preflight(self.gh,self.event,{**self.env,**change})
  self.assertEqual(self.gh.mock_calls,[])
 def test_red_pending_and_other_repository_events_are_denied(self):
  for change in ({'conclusion':'failure'},{'conclusion':None},{'head_repository':{'id':999}},{'event':'pull_request'}):
   event={'workflow_run':{**self.event['workflow_run'],**change}}
   with self.subTest(change=change),self.assertRaises(RuntimeError):orchestrator.preflight(self.gh,event,self.env)
  self.assertEqual(self.gh.mock_calls,[])
 def test_verified_merged_ux_plan_uses_exact_upstream_gate(self):
  with mock.patch.object(scope,'eligible_commit',return_value={'risk':'R2','pr_number':9}):
   result=orchestrator.preflight(self.gh,self.event,self.env)
  self.assertEqual(result['status'],'ELIGIBLE');self.gh.gate.assert_called_once_with(100,APP,'R2')
 def test_older_green_cannot_override_new_pending_gate(self):
  gh=common.GitHub('fixture')
  run={'id':100,'event':'push','name':'Dation FAST gate'}
  with mock.patch.object(gh,'run',return_value=run),mock.patch.object(gh,'pages',return_value=[{'id':100},{'id':101,'status':'queued'}]),self.assertRaisesRegex(RuntimeError,'newer pending'):
   gh.gate(100,APP,'R2')
 def publisher(self,receipt_change=None):
  gh=mock.Mock();gh.main.return_value=APP
  run={'id':200,'display_title':orchestrator.title(plan()),'head_sha':APP,'head_branch':'main',
   'repository':{'id':1114679650},'head_repository':{'id':1114679650},'event':'workflow_dispatch','status':'completed','conclusion':'success'}
  receipt={'status':'PASS','sha':APP,'request_id':'g6-'+RUN,'workflow_sha':APP,'run_id':'200','project':common.PROJECT,
   'architecture':'amd64','dependencies_verified':True,'imports_verified':True,'image_digest':IMAGE,**(receipt_change or {})}
  claim={'publish-claim.json':{'release_id':'g6-'+RUN,'application_sha':APP}}
  def artifact(run_id,name,**kwargs):
   return claim if name.startswith('g6-publish-claim-') else {'GATE_C_RECEIPT.json':receipt}
  gh.artifact.side_effect=artifact;gh.run.return_value=run;gh.pages.return_value=[run]
  return gh,run
 def test_single_dispatch_correlates_exact_publisher_receipt(self):
  gh,run=self.publisher();gh.pages.side_effect=[[],[run]]
  with mock.patch.dict(os.environ,self.env),mock.patch.object(orchestrator.time,'sleep'):
   result=orchestrator.dispatch_collect(gh,plan(),self.out)
   self.assertEqual(result['status'],'PUBLISH_PASS')
   gh.api.assert_called_once_with('/actions/workflows/runtime-v2-publish.yml/dispatches',method='POST',
    body={'ref':'main','inputs':{'application_sha':APP,'confirm_publish':True,'request_id':'g6-'+RUN}})
   gh.pages.return_value=[];gh.pages.side_effect=None
   with self.assertRaises(FileExistsError):orchestrator.dispatch_collect(gh,plan(),self.out)
   self.assertEqual(gh.api.call_count,1)
 def test_recovery_missing_child_never_dispatches_again(self):
  gh,run=self.publisher();gh.pages.return_value=[]
  with mock.patch.dict(os.environ,self.env),self.assertRaisesRegex(RuntimeError,'never submit again'):
   orchestrator.dispatch_collect(gh,plan(),self.out,allow_dispatch=False)
  gh.api.assert_not_called()
 def test_existing_child_is_collected_without_post(self):
  gh,run=self.publisher()
  with mock.patch.dict(os.environ,self.env):orchestrator.dispatch_collect(gh,plan(),self.out,allow_dispatch=False)
  gh.api.assert_not_called()
 def test_early_failure_receipt_never_claims_publication_or_deployment(self):
  common.write(self.out/'plan.json',plan())
  result=orchestrator.finalize(self.out,'failure')
  self.assertEqual(result['status'],'FAILED');self.assertFalse(result['PUBLISH_PASS']);self.assertFalse(result['HEALTH_PASS'])
  self.assertEqual(result['TRAFFIC'],0)
 def test_interrupted_write_receipt_marks_live_traffic_unverified(self):
  common.write(self.out/'plan.json',plan());common.write(self.out/'publication.json',publication())
  common.write(self.out/'snapshot.json',{'old_revision':OLD})
  result=orchestrator.finalize(self.out,'cancelled')
  self.assertTrue(result['PUBLISH_PASS']);self.assertEqual(result['TRAFFIC'],'UNVERIFIED_CHECK_LIVE')
  self.assertFalse(result['HEALTH_PASS'])
 def test_finalization_preserves_verified_activation_or_safe_rollback(self):
  for status in ('ACTIVATED','FAILED_ROLLED_BACK','FAILED_PREPARED_CLEANED','READ_ONLY_IDENTITY_VERIFIED'):
   prior={'status':status,'evidence':'immutable'};common.write(self.out/'G6_RELEASE_RECEIPT.json',prior)
   self.assertEqual(orchestrator.finalize(self.out,'failure'),prior)
 def test_ambiguous_child_or_wrong_receipt_never_authorizes_deploy(self):
  for key,value in [('sha',BASE),('request_id','g6-other'),('image_digest',common.REGISTRY+':mutable'),('imports_verified',False)]:
   gh,run=self.publisher({key:value})
   with self.subTest(key=key),self.assertRaises(RuntimeError):orchestrator.dispatch_collect(gh,plan(),self.out,allow_dispatch=False)
   gh.api.assert_not_called()
  gh,run=self.publisher();gh.pages.return_value=[run,run]
  with self.assertRaisesRegex(RuntimeError,'ambiguous'):orchestrator.correlated(gh,plan())
 def test_missing_or_tampered_artifact_is_denied(self):
  gh=common.GitHub('fixture');metadata={'id':7,'name':'checkpoint','digest':'sha256:'+'0'*64,'size_in_bytes':4}
  opener=mock.Mock();response=mock.MagicMock();response.__enter__.return_value.read.return_value=b'fake';opener.open.return_value=response
  with mock.patch.object(common.urllib.request,'build_opener',return_value=opener),self.assertRaisesRegex(RuntimeError,'digest mismatch'):gh.archive(metadata)
  with mock.patch.object(gh,'pages',return_value=[]),self.assertRaisesRegex(RuntimeError,'missing'):gh.artifact(100,'checkpoint')
 def test_storage_redirect_does_not_receive_github_token(self):
  gh=common.GitHub('fixture');raw=b'verified-archive'
  metadata={'id':7,'digest':'sha256:'+common.hashlib.sha256(raw).hexdigest(),'size_in_bytes':len(raw)}
  opener=mock.Mock();response=mock.MagicMock();response.__enter__.return_value.read.return_value=raw
  opener.open.side_effect=[urllib.error.HTTPError('https://api.github.com',302,'',{'Location':'https://results.blob.core.windows.net/file?sig=temporary'},None),response]
  with mock.patch.object(common.urllib.request,'build_opener',return_value=opener):self.assertEqual(gh.archive(metadata),raw)
  self.assertIsInstance(opener.open.call_args_list[1].args[0],str)
  self.assertNotIn('fixture',opener.open.call_args_list[1].args[0])
 def test_registry_source_read_reuses_pinned_client_and_restores_token(self):
  publisher=mock.Mock();publisher.install_crane.return_value=Path('/fixture/crane')
  publisher.command.return_value=json.dumps({'architecture':'amd64','os':'linux','config':{'Labels':{'org.opencontainers.image.revision':BASE}}})
  with (mock.patch('importlib.util.module_from_spec',return_value=publisher),mock.patch('importlib.util.spec_from_file_location') as spec,
   mock.patch.dict(os.environ,{'DOCKER_CONFIG':str(self.out/'auth'),'DATION_PUBLISH_ACCESS_TOKEN':'previous'})):
   spec.return_value.loader.exec_module.return_value=None
   cloud=common.CloudRun('ephemeral-fixture',tools=self.out/'tools')
   with mock.patch.object(cloud,'registry') as tag:
    self.assertEqual(cloud.application_sha(OLD_IMAGE),BASE);tag.assert_called_once_with(BASE,OLD_IMAGE)
   self.assertEqual(os.environ['DATION_PUBLISH_ACCESS_TOKEN'],'previous')
  publisher.command.assert_called_once_with(Path('/fixture/crane'),'config',OLD_IMAGE)

class BootstrapSimulationTests(unittest.TestCase):
 def test_exact_scoped_delta_preserves_existing_members_and_is_idempotent(self):
  value=bootstrap.plan();state={'account':False,'pool':False,'provider':False,'role':False,'bound':set()};mutations=[]
  policies={b['resource']:{'etag':'initial','bindings':[{'role':b['role'],'members':['serviceAccount:existing@fixture.invalid']}]} for b in value['bindings']}
  provider={'name':common.PROVIDER,'state':'ACTIVE','attributeMapping':value['attribute_mapping'],
   'attributeCondition':value['attribute_condition'],'oidc':{'issuerUri':value['issuer'],'allowedAudiences':[value['audience']]}}
  def command(argv,**kwargs):
   self.assertEqual(argv[0],'gcloud');self.assertIn('--project='+common.PROJECT,argv);self.assertIn('--billing-project='+common.PROJECT,argv)
   args=argv[1:];result=None
   if args[:2]==['auth','print-access-token']:return SimpleNamespace(returncode=0,stdout='fixture',stderr='')
   if args[:2]==['projects','describe']:result={'projectId':common.PROJECT,'projectNumber':common.POLICY['project_number'],'lifecycleState':'ACTIVE'}
   elif args[:2]==['services','list']:result=[{'config':{'name':n}} for n in ('iam.googleapis.com','iamcredentials.googleapis.com','sts.googleapis.com','run.googleapis.com','artifactregistry.googleapis.com')]
   elif args[:2]==['projects','get-iam-policy']:result={'bindings':[]}
   elif args[:3]==['run','services','describe']:result={'metadata':{'name':'dation-core'}}
   elif args[:4]==['iam','service-accounts','keys','list']:result=[]
   elif args[:4]==['iam','workload-identity-pools','providers','list']:result=[provider] if state['provider'] else []
   elif 'get-iam-policy' in args:
    if args[:2]==['run','services']:index=0
    elif args[:2]==['artifacts','repositories']:index=1
    elif args[3].startswith('dation-runtime@'):index=2
    else:index=3
    result=policies[value['bindings'][index]['resource']]
   else:
    mutations.append(args)
    if args[:3]==['iam','service-accounts','create']:state['account']=True
    elif args[:3]==['iam','workload-identity-pools','create']:state['pool']=True
    elif args[:4]==['iam','workload-identity-pools','providers','create-oidc']:state['provider']=True
    elif args[:3]==['iam','roles','create']:state['role']=True
    elif 'add-iam-policy-binding' in args:
     role=next(a.split('=',1)[1] for a in args if a.startswith('--role='));member=next(a.split('=',1)[1] for a in args if a.startswith('--member='))
     binding=next(b for b in value['bindings'] if b['role']==role)
     policies[binding['resource']]['bindings'][0]['members'].append(member);state['bound'].add(binding['resource'])
    else:self.fail('unexpected mutation '+repr(args))
   return SimpleNamespace(returncode=0,stdout=json.dumps(result),stderr='')
  class Response:
   def __init__(self,result):self.result=result
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self):return json.dumps(self.result).encode()
  def read(req,**kwargs):
   url=req.full_url
   if '/serviceAccounts/' in url:result={'email':common.DEPLOYER} if state['account'] else None
   elif '/providers/' in url:result=provider if state['provider'] else None
   elif '/workloadIdentityPools/' in url:result={'state':'ACTIVE'} if state['pool'] else None
   elif '/roles/' in url:result={'stage':'GA','includedPermissions':value['custom_role']['includedPermissions']} if state['role'] else None
   else:self.fail('unexpected read '+url)
   if result is None:raise urllib.error.HTTPError(url,404,'',{},io.BytesIO(b'{"error":{"code":404,"status":"NOT_FOUND"}}'))
   return Response(result)
  # The deployer IAM itself may have only the reviewed federation principal.
  policies[value['bindings'][3]['resource']]['bindings']=[]
  original_command=command
  def command_with_deployer(argv,**kwargs):
   args=argv[1:]
   if args[:3]==['iam','service-accounts','add-iam-policy-binding'] and args[3]==common.DEPLOYER:
    mutations.append(args);b=value['bindings'][3];policies[b['resource']]['bindings']=[{'role':b['role'],'members':[b['member']]}]
    return SimpleNamespace(returncode=0,stdout='null',stderr='')
   return original_command(argv,**kwargs)
  opener=mock.Mock();opener.open.side_effect=read
  with mock.patch.object(bootstrap.subprocess,'run',side_effect=command_with_deployer),mock.patch.object(common.urllib.request,'build_opener',return_value=opener),mock.patch('sys.stdout',new_callable=io.StringIO):
   bootstrap.apply(value,'GO_G6_BOOTSTRAP_IDENTITY',common.fingerprint(value));first=len(mutations)
   bootstrap.apply(value,'GO_G6_BOOTSTRAP_IDENTITY',common.fingerprint(value))
  self.assertEqual(first,8);self.assertEqual(len(mutations),first)
  for binding in value['bindings'][:3]:self.assertIn('serviceAccount:existing@fixture.invalid',policies[binding['resource']]['bindings'][0]['members'])
  self.assertFalse(any('enable' in call or 'deploy' in call or 'set-iam-policy' in call for call in mutations))

class ReleaseSimulationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name)
  self.gh=FakeGitHub();self.cloud=FakeCloud();self.release=release.Release(self.gh,self.cloud,plan(),publication(),self.out)
  self.scope_git=mock.patch.object(scope,'git',return_value='');self.scope_git.start();self.addCleanup(self.scope_git.stop)
  self.changed_patch=mock.patch.object(scope,'changed',return_value=[UI]);self.changed=self.changed_patch.start();self.addCleanup(self.changed_patch.stop)
  self.client_check=mock.patch.object(scope,'validate_client_changes');self.client_check.start();self.addCleanup(self.client_check.stop)
  self.health_patch=mock.patch.object(release,'health',return_value={'status':200,'body':{'status':'healthy'}});self.health=self.health_patch.start();self.addCleanup(self.health_patch.stop)
 def prepared(self):self.release.snapshot();self.release.prepare()
 def intent(self):self.prepared();self.release.smoke();self.release.promotion_intent()
 def test_end_to_end_zero_traffic_smoke_then_exact_promotion(self):
  self.prepared();self.assertEqual(release.active(self.cloud.service),OLD)
  self.assertEqual(self.cloud.writes[0]['body']['traffic'][0]['revision'],'dation-core-00002-old')
  self.assertEqual(self.cloud.writes[0]['body']['traffic'][1]['percent'],0)
  self.release.smoke();candidate=self.health.call_args.args[0];self.assertIn('ux-'+RUN,candidate)
  self.release.promotion_intent();receipt=self.release.promote()
  self.assertEqual(receipt['status'],'ACTIVATED');self.assertEqual(receipt['TRAFFIC'],100)
  self.assertEqual(release.active(self.cloud.service),self.release.new);self.assertEqual(len(self.cloud.writes),2)
  self.assertNotIn('tag',self.cloud.writes[1]['body']['traffic'][0]);self.assertEqual(receipt['ROLLBACK_REVISION'],OLD)
 def test_newer_main_stops_before_mutation(self):
  self.gh.head='f'*40
  with self.assertRaisesRegex(RuntimeError,'advanced'):self.release.snapshot()
  self.assertEqual(self.cloud.writes,[])
 def test_stale_environment_marker_does_not_replace_actual_oci_source(self):
  for target in [self.cloud.service['template'],self.cloud.revisions[OLD]]:
   next(e for e in target['containers'][0]['env'] if e['name']=='DATION_RELEASE_SHA')['value']='e'*40
  snap=self.release.snapshot()
  self.assertEqual(snap['old_application_sha'],BASE);self.assertEqual(snap['old_environment_sha'],'e'*40)
 def test_r3_live_runtime_delta_is_denied(self):
  self.changed.return_value=['backend/main.py']
  with self.assertRaisesRegex(RuntimeError,'non-UX'):self.release.snapshot()
  self.assertEqual(self.cloud.writes,[])
 def test_config_iam_or_etag_drift_denies_prepare(self):
  for kind in ('config','iam','etag'):
   with self.subTest(kind=kind):
    self.cloud=FakeCloud();self.release=release.Release(self.gh,self.cloud,plan(),publication(),self.out);self.release.snapshot()
    if kind=='config':self.cloud.service['template']['containers'][0]['resources']['limits']['memory']='1Gi'
    if kind=='iam':self.cloud.iam_policy['bindings'][0]['members'].append('allAuthenticatedUsers')
    if kind=='etag':self.cloud.service['etag']='external'
    with self.assertRaises(RuntimeError):self.release.prepare()
    self.assertEqual(self.cloud.writes,[])
 def test_missing_receipt_or_snapshot_cannot_prepare(self):
  with self.assertRaises(FileNotFoundError):self.release.prepare()
  self.assertEqual(self.cloud.writes,[])
 def test_interrupted_before_prepare_never_redeploys_on_recovery(self):
  self.release.snapshot();self.release.recovering=True
  with self.assertRaisesRegex(RuntimeError,'never redeploy'):self.release.prepare()
  self.assertEqual(self.cloud.writes,[])
 def test_interrupted_after_prepare_recovers_same_revision_without_write(self):
  self.prepared();self.cloud.writes.clear();self.release.recovering=True
  self.release.prepare();self.assertEqual(self.cloud.writes,[])
 def test_two_merges_or_deploys_cannot_promote_stale_revision(self):
  self.intent();self.gh.head='f'*40
  with self.assertRaises(RuntimeError):self.release.promote()
  self.assertEqual(len(self.cloud.writes),1)
  self.gh.head=APP;self.cloud.service['latestCreatedRevision']=common.RESOURCE+'/revisions/dation-core-newer';self.cloud.service['etag']='newer'
  with self.assertRaises(RuntimeError):self.release.promote()
  self.assertEqual(len(self.cloud.writes),1)
 def test_candidate_503_cleans_only_temporary_tag_keeps_old100(self):
  self.prepared();self.health.side_effect=RuntimeError('HTTP503')
  with self.assertRaisesRegex(RuntimeError,'503'):self.release.smoke()
  self.assertEqual(release.active(self.cloud.service),OLD);self.assertEqual(len(self.cloud.writes),2)
  self.assertEqual(set(self.cloud.writes[-1]['body']),{'name','etag','traffic'})
  receipt=json.loads((self.out/'G6_RELEASE_RECEIPT.json').read_text());self.assertEqual(receipt['status'],'FAILED_PREPARED_CLEANED')
 def test_post_promotion_503_rolls_back_only_owned_revision(self):
  self.intent();self.health.side_effect=[RuntimeError('HTTP503'),{'status':200}]
  with self.assertRaisesRegex(RuntimeError,'safe rollback'):self.release.promote()
  self.assertEqual(release.active(self.cloud.service),OLD);self.assertEqual(len(self.cloud.writes),3)
  self.assertEqual(json.loads((self.out/'G6_RELEASE_RECEIPT.json').read_text())['status'],'FAILED_ROLLED_BACK')
 def test_later_deploy_prevents_automatic_rollback(self):
  self.intent()
  def fail_after_newer(url):
   self.cloud.service.update(etag='later',generation='99',latestCreatedRevision=common.RESOURCE+'/revisions/dation-core-later')
   raise RuntimeError('HTTP503')
  self.health.side_effect=fail_after_newer
  with self.assertRaisesRegex(RuntimeError,'later deploy'):self.release.promote()
  self.assertEqual(len(self.cloud.writes),2)
 def test_old_revision_not_ready_blocks_rollback(self):
  self.intent();self.release.promote();self.cloud.revisions[OLD]['conditions']=[]
  with self.assertRaisesRegex(RuntimeError,'not READY'):self.release.rollback()
  self.assertEqual(len(self.cloud.writes),2)
 def test_interrupted_after_promotion_recovers_without_traffic_write(self):
  self.intent();self.release.promote();self.cloud.writes.clear()
  self.assertEqual(self.release.recover_promoted()['status'],'ACTIVATED');self.assertEqual(self.cloud.writes,[])
 def test_rollback_requires_same_generation_and_preserves_config(self):
  self.intent();self.release.promote();self.cloud.service['etag']='other'
  with self.assertRaises(RuntimeError):self.release.rollback()
  self.assertEqual(len(self.cloud.writes),2)
 def test_unsafe_runtime_configuration_never_reaches_snapshot_artifact(self):
  for mode in ('min','max','cpu','flag','secret'):
   cloud=FakeCloud()
   if mode=='min':cloud.service['scaling']['minInstanceCount']=1
   if mode=='max':cloud.service['scaling']['maxInstanceCount']=3
   if mode=='cpu':cloud.service['template']['containers'][0]['resources']['cpuIdle']=False
   if mode=='flag':next(e for e in cloud.service['template']['containers'][0]['env'] if e['name']=='DATION_CLOUD_EXECUTION_ENABLED')['value']='true'
   if mode=='secret':next(e for e in cloud.service['template']['containers'][0]['env'] if e['name']=='SUPABASE_SECRET_KEY').update(value='fixture-secret')
   with self.subTest(mode=mode),self.assertRaises(RuntimeError):release.Release(self.gh,cloud,plan(),publication(),self.out).snapshot()
   self.assertEqual(cloud.writes,[])

if __name__=='__main__':unittest.main(verbosity=2)
