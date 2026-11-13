"""Targeted publication/WIF safety contracts. Never calls GCP or builds Dation."""
import ast
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace
import urllib.error
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('publication', ROOT / 'scripts/runtime_v2_publication.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
DIGEST = 'sha256:' + 'a' * 64
CONTEXT = {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'nicsejara/Dation',
    'GITHUB_REPOSITORY_ID': '1114679650', 'GITHUB_REPOSITORY_OWNER_ID': '249153366',
    'GITHUB_REF': 'refs/heads/main', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
    'GITHUB_WORKFLOW_REF': 'nicsejara/Dation/.github/workflows/runtime-v2-publish.yml@refs/heads/main',
    'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_RUN_ID': '100'}


def wif_block():
    document = (ROOT/'docs/runtime-v2/github-actions-go-live.md').read_text()
    return document.split("python3 - <<'PY'\n", 1)[1].split('\nPY\n', 1)[0]


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dation-publication-test-')
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)

    def test_only_trusted_manual_context(self):
        p.guard_context(CONTEXT)
        for key in CONTEXT:
            changed = dict(CONTEXT); changed[key] = 'untrusted'
            with self.subTest(claim=key), self.assertRaises(RuntimeError):p.guard_context(changed)

    def test_wif_numeric_subject_and_exact_claims(self):
        plan = p.wif_plan()
        self.assertEqual(plan['attribute_mapping'], {'google.subject': 'assertion.repository_id'})
        self.assertTrue(plan['principal'].endswith('/subject/1114679650'))
        self.assertNotIn('principalSet:', plan['principal'])
        self.assertEqual(plan['expected_claims']['event_name'], 'workflow_dispatch')
        self.assertEqual(plan['expected_claims']['ref'], 'refs/heads/main')
        for claim, value in plan['expected_claims'].items():
            self.assertIn("assertion." + claim + " == '" + value + "'", plan['attribute_condition'])

    def test_provider_matches_publisher_and_no_token_creator(self):
        plan = p.wif_plan()
        self.assertEqual(plan['provider'], p.PROVIDER)
        self.assertEqual(plan['service_account'], p.ACCOUNT)
        self.assertEqual(plan['audience'], 'https://iam.googleapis.com/' + p.PROVIDER)
        self.assertNotIn('TokenCreator', json.dumps(plan))

    def test_owner_block_contains_the_same_reviewed_trust(self):
        tree = ast.parse(wif_block())
        plan = next(n.value for n in tree.body if isinstance(n, ast.Assign) and
            any(isinstance(t, ast.Name) and t.id == 'PLAN' for t in n.targets))
        self.assertEqual(ast.literal_eval(plan), p.wif_plan())

    def test_owner_block_stops_before_any_io_without_specific_go(self):
        with mock.patch.dict(os.environ, {'DATION_WIF_GO':''}), mock.patch.object(p.subprocess, 'run') as run:
            with self.assertRaisesRegex(SystemExit, 'requires explicit owner GO'):
                exec(compile(wif_block(), '<reviewed-wif-block>', 'exec'), {})
        run.assert_not_called()

    def test_owner_block_configures_only_reviewed_identity_and_is_idempotent(self):
        plan = p.wif_plan(); calls = []; mutations = []
        state = {'apis': {'iam.googleapis.com'}, 'project_role': True,
            'writer': False, 'binding': False, 'pool': False, 'provider': False}
        member = 'serviceAccount:' + p.ACCOUNT
        def policy(role, who):return {'bindings':[{'role':role, 'members':[who]}]}
        def run(argv, **kwargs):
            self.assertEqual(argv[0], 'gcloud'); calls.append(argv)
            if argv[1:3] == ['auth','print-access-token']:
                return SimpleNamespace(returncode=0, stdout='fixture-token', stderr='')
            self.assertIn('--project=' + p.PROJECT, argv)
            self.assertIn('--billing-project=' + p.PROJECT, argv)
            args = argv[1:-4]
            if args[:2] == ['projects','describe']:
                value = {'projectId':p.PROJECT, 'projectNumber':p.PROJECT_NUMBER, 'lifecycleState':'ACTIVE'}
            elif args[:2] == ['services','list']:
                value = [{'config':{'name':a}} for a in state['apis']]
            elif args[:3] == ['iam','service-accounts','describe']:
                value = {'email':p.ACCOUNT}
            elif args[:4] == ['iam','service-accounts','keys','list']:value = []
            elif args[:2] == ['projects','get-iam-policy']:
                value = policy('roles/logging.logWriter',member) if state['project_role'] else {}
            elif args[:3] == ['artifacts','repositories','get-iam-policy']:
                value = policy('roles/artifactregistry.writer',member) if state['writer'] else {}
            elif args[:3] == ['iam','service-accounts','get-iam-policy']:
                value = policy('roles/iam.workloadIdentityUser',plan['principal']) if state['binding'] else {}
            elif args[:4] == ['iam','workload-identity-pools','providers','list']:
                value = [{'name':plan['provider']}] if state['provider'] else []
            else:
                mutations.append(args)
                if args[:2] == ['services','enable']:
                    self.assertEqual(set(args[2:]), {'sts.googleapis.com','iamcredentials.googleapis.com'})
                    state['apis'].update(args[2:])
                elif args[:3] == ['iam','workload-identity-pools','create']:state['pool'] = True
                elif args[:4] == ['iam','workload-identity-pools','providers','create-oidc']:
                    self.assertIn('--attribute-condition=' + plan['attribute_condition'], args)
                    self.assertIn('--allowed-audiences=' + plan['audience'], args)
                    state['provider'] = True
                elif args[:2] == ['projects','remove-iam-policy-binding']:
                    self.assertIn('--role=roles/logging.logWriter',args);state['project_role'] = False
                elif args[:3] == ['artifacts','repositories','add-iam-policy-binding']:
                    self.assertIn('--role=roles/artifactregistry.writer',args);state['writer'] = True
                elif args[:3] == ['iam','service-accounts','add-iam-policy-binding']:
                    self.assertIn('--member=' + plan['principal'], args)
                    self.assertIn('--role=roles/iam.workloadIdentityUser',args);state['binding'] = True
                else:self.fail('Unreviewed mutation: ' + repr(args))
                value = None
            return SimpleNamespace(returncode=0, stdout=json.dumps(value), stderr='')
        def read(request, **kwargs):
            url = request.full_url
            if url == 'https://artifactregistry.googleapis.com/v1/' + p.REPOSITORY:
                value = {'format':'DOCKER'}
            elif url.startswith('https://storage.googleapis.com/'):
                raise urllib.error.HTTPError(url,404,'',{},io.BytesIO(json.dumps(
                    {'error':{'code':404,'errors':[{'reason':'notFound'}]}}).encode()))
            elif url.endswith('/providers/github-main-manual') and state['provider']:
                value = {'state':'ACTIVE','attributeMapping':plan['attribute_mapping'],
                    'attributeCondition':plan['attribute_condition'],
                    'oidc':{'issuerUri':plan['issuer'],'allowedAudiences':[plan['audience']]}}
            elif url.endswith('/dation-github-publish') and state['pool']:
                value = {'state':'ACTIVE'}
            else:
                raise urllib.error.HTTPError(url,404,'',{},io.BytesIO(json.dumps(
                    {'error':{'code':404,'status':'NOT_FOUND'}}).encode()))
            return io.BytesIO(json.dumps(value).encode())
        with mock.patch.dict(os.environ,{'DATION_WIF_GO':'GO_RUNTIME_V2_GITHUB_OIDC'}), \
            mock.patch.object(p.subprocess,'run',side_effect=run), \
            mock.patch.object(p.urllib.request,'urlopen',side_effect=read), contextlib.redirect_stdout(io.StringIO()) as output:
            exec(compile(wif_block(), '<reviewed-wif-block>', 'exec'), {})
            self.assertEqual(json.loads(output.getvalue())['status'],'WIF_CONFIGURATION_VERIFIED_METADATA')
            self.assertEqual(len(mutations),6)
            mutations.clear();output.seek(0);output.truncate(0)
            exec(compile(wif_block(), '<reviewed-wif-block>', 'exec'), {})
        self.assertEqual(mutations, [])
        self.assertNotIn('fixture-token', output.getvalue())

    def test_http_denials_and_ambiguous_404_do_not_mean_absent(self):
        for code, body in [(401, {'error':{'code':401,'status':'UNAUTHENTICATED'}}),
            (403, {'error':{'code':403,'status':'PERMISSION_DENIED'}}),
            (404, {'error':{'code':403,'status':'PERMISSION_DENIED'}}),
            (404, {'error':'Image not found with extra explanatory text'}), (404, {})]:
            error = urllib.error.HTTPError('https://artifactregistry.googleapis.com',code,'',{},io.BytesIO(json.dumps(body).encode()))
            opener = mock.Mock(); opener.open.side_effect = error
            with self.subTest(code=code), mock.patch.dict(os.environ,{'DATION_PUBLISH_ACCESS_TOKEN':'fixture-only'}),mock.patch.object(p.urllib.request,'build_opener',return_value=opener):
                with self.assertRaises(RuntimeError):p.ar('GET',p.PACKAGE+'/tags/'+p.SOURCE_SHA,absent=True)

    def test_structured_absence_ignores_explanatory_text(self):
        error = urllib.error.HTTPError('https://artifactregistry.googleapis.com',404,'',{},io.BytesIO(json.dumps(
            {'error':{'code':404,'status':'NOT_FOUND','message':'Image not found.\nAdditional server explanation'}}).encode()))
        opener=mock.Mock();opener.open.side_effect=error
        with mock.patch.dict(os.environ,{'DATION_PUBLISH_ACCESS_TOKEN':'fixture-only'}),mock.patch.object(p.urllib.request,'build_opener',return_value=opener):
            self.assertIsNone(p.ar('GET',p.PACKAGE+'/tags/'+p.SOURCE_SHA,absent=True))

    def test_bearer_never_follows_redirects(self):
        self.assertIsNone(p.NoRedirect().redirect_request(None,None,302,'',{},'https://other.invalid'))

    def test_destination_cannot_be_another_repository(self):
        with self.assertRaisesRegex(RuntimeError,'destination'):
            p.api('GET','https://artifactregistry.googleapis.com/v1/'+p.REPOSITORY+'-other')

    def test_version_identity_and_known_numeric_alias(self):
        self.assertEqual(p.parse_version(p.PACKAGE+'/versions/'+DIGEST),DIGEST)
        self.assertEqual(p.parse_version((p.PACKAGE+'/versions/'+DIGEST).replace(p.PROJECT,p.PROJECT_NUMBER).replace('sha256:','sha256%3A')),DIGEST)
        for bad in [p.PACKAGE.replace('dation-core','other')+'/versions/'+DIGEST, p.PACKAGE+'/versions/not-a-digest']:
            with self.subTest(value=bad), self.assertRaises(RuntimeError):p.parse_version(bad)

    def test_wrong_exact_tag_is_rejected(self):
        with mock.patch.object(p,'ar',return_value={'name':p.PACKAGE+'/tags/other','version':p.PACKAGE+'/versions/'+DIGEST}):
            with self.assertRaisesRegex(RuntimeError,'exact tag'):p.tag_digest()

    def test_prior_images_do_not_block_new_exact_sha_release(self):
        with mock.patch.object(p,'source_check'),mock.patch.object(p,'tag_digest',return_value=None), \
             mock.patch.object(p,'require_no_previous_build') as history, \
             mock.patch.object(p,'digest_file',return_value='checksum'), \
             mock.patch.object(p,'outputs'),mock.patch.object(p,'ar',side_effect=[
                 {'name':p.REPOSITORY,'format':'DOCKER'},
                 {'permissions':sorted(p.PERMISSIONS)}]) as registry:
            p.preflight(ROOT,self.output)
        history.assert_called_once()
        self.assertEqual(registry.call_count,2)
        self.assertTrue(json.loads((self.output/'state.json').read_text())['build_required'])

    def history(self, step, *, previous_status='completed', total=1):
        runs={'workflow_runs':[{'id':99,'status':previous_status,'head_sha':'c'*40},{'id':100,'status':'in_progress','head_sha':'c'*40}]}
        jobs={'total_count':total,'jobs':[{'conclusion':'failure','steps':step}]}
        return mock.patch.object(p,'api',side_effect=[runs,jobs])

    def test_history_allows_auth_failure_before_build(self):
        with mock.patch.dict(os.environ,{**CONTEXT,'GITHUB_SHA':'c'*40}),self.history([{'name':p.TRUST['build_step_name'],'conclusion':'skipped'}]):p.require_no_previous_build()

    def test_any_previous_build_attempt_blocks_another_build(self):
        for conclusion in ('success','failure','cancelled',None):
            with self.subTest(conclusion=conclusion),mock.patch.dict(os.environ,{**CONTEXT,'GITHUB_SHA':'c'*40}),self.history([{'name':p.TRUST['build_step_name'],'conclusion':conclusion}]):
                with self.assertRaisesRegex(RuntimeError,'previous build'):p.require_no_previous_build()

    def test_unresolved_previous_run_blocks_build(self):
        with mock.patch.dict(os.environ,{**CONTEXT,'GITHUB_SHA':'c'*40}),mock.patch.object(p,'api',return_value={'workflow_runs':[{'id':99,'status':'in_progress','head_sha':'c'*40}]}):
            with self.assertRaisesRegex(RuntimeError,'unresolved'):p.require_no_previous_build()

    def test_previous_other_release_does_not_block_build(self):
        with mock.patch.dict(os.environ,{**CONTEXT,'GITHUB_SHA':'c'*40}), \
             mock.patch.object(p,'api',return_value={'workflow_runs':[{
                 'id':99,'status':'completed','head_sha':'d'*40}]}) as history:
            p.require_no_previous_build()
        history.assert_called_once()

    def test_missing_prior_control_identity_is_not_assumed_safe(self):
        with mock.patch.dict(os.environ,{**CONTEXT,'GITHUB_SHA':'c'*40}), \
             mock.patch.object(p,'api',return_value={'workflow_runs':[{
                 'id':99,'status':'completed'}]}),self.assertRaisesRegex(RuntimeError,'control SHA'):
            p.require_no_previous_build()

    def test_incomplete_history_cannot_clear_build_marker(self):
        with mock.patch.dict(os.environ,{**CONTEXT,'GITHUB_SHA':'c'*40}),self.history([],total=101):
            with self.assertRaisesRegex(RuntimeError,'history incomplete'):p.require_no_previous_build()

    def test_no_tag_overwrite_when_existing_digest_differs(self):
        with mock.patch.object(p,'tag_digest',return_value='sha256:'+'b'*64),mock.patch.object(p,'ar') as api:
            with self.assertRaisesRegex(RuntimeError,'never overwrite'):p.create_tag(DIGEST)
        api.assert_not_called()

    def test_atomic_tag_conflict_never_uses_patch(self):
        with mock.patch.object(p,'tag_digest',side_effect=[None,DIGEST]),mock.patch.object(p,'ar',return_value=None) as api:p.create_tag(DIGEST)
        self.assertEqual(api.call_count,1);self.assertEqual(api.call_args.args[0],'POST')
        with mock.patch.object(p,'tag_digest',side_effect=[None,'sha256:'+'b'*64]),mock.patch.object(p,'ar',return_value=None):
            with self.assertRaises(RuntimeError):p.create_tag(DIGEST)

    def test_build_once_marker_preserves_docker_ci_procedure(self):
        p.write(self.output/'state.json',{'build_required':True,'local_image':'fixture'})
        with mock.patch.object(p,'command') as command:p.build(Path('/fixture'),self.output)
        args=command.call_args.args
        self.assertEqual(args[:2],('docker','build'));self.assertIn('linux/amd64',args)
        self.assertEqual(command.call_args.kwargs['timeout'],1200)
        with mock.patch.object(p,'command') as command,self.assertRaisesRegex(RuntimeError,'claimed'):p.build(Path('/fixture'),self.output)
        command.assert_not_called()

    def test_verify_uses_no_network_and_does_not_run_engines(self):
        p.write(self.output/'state.json',{'build_required':True,'local_image':'fixture'})
        (self.output/'image-id.txt').write_text('sha256:fixture')
        with mock.patch.object(p,'command',side_effect=[f'sha256:fixture linux amd64 {p.SOURCE_SHA} 100','No broken requirements','imports_ok']) as command:
            p.verify_image(self.output)
        for call in command.call_args_list[1:]:
            self.assertIn('none',call.args);self.assertIn('--cpus=1',call.args);self.assertIn('--memory=512m',call.args)
        self.assertTrue(json.loads((self.output/'state.json').read_text())['imports_verified'])

    def test_manifest_generation_preserves_runtime_guards(self):
        source=Path(os.environ['DATION_TEST_VALIDATED_SOURCE'])
        p.manifests(source,self.output,p.IMAGE+'@'+DIGEST)
        plan=json.loads((self.output/'manifests/release.json').read_text())
        self.assertEqual(plan['release_sha'],p.SOURCE_SHA);self.assertEqual(plan['environment']['DATION_CLOUD_EXECUTION_ENABLED'],'false')
        self.assertFalse(plan['recovery_schedule']['enabled']);self.assertNotIn('DATION_ACCESS_PASSWORD',plan['secret_references'])
        api=json.loads((self.output/'manifests/api.json').read_text())
        self.assertEqual(api['scaling'],{'minInstanceCount':0,'maxInstanceCount':2})
        self.assertTrue(api['template']['containers'][0]['resources']['cpuIdle'])
        for name in ('executor','recovery'):
            job=json.loads((self.output/f'manifests/{name}.json').read_text());self.assertEqual(job['template']['template']['maxRetries'],0)

    def test_source_sha_and_credentials_outside_build_context(self):
        source=Path(os.environ['DATION_TEST_VALIDATED_SOURCE'])
        with mock.patch.dict(os.environ,{'DOCKER_CONFIG':str(self.output/'auth')}):p.source_check(source,self.output)
        with mock.patch.dict(os.environ,{'DOCKER_CONFIG':str(source/'unsafe-auth')}):
            with self.assertRaisesRegex(RuntimeError,'credentials'):p.source_check(source,self.output)

    def test_workflow_is_manual_only_and_credentials_are_ephemeral(self):
        w=yaml.load((ROOT/'.github/workflows/runtime-v2-publish.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(set(w['on']),{'workflow_dispatch'})
        self.assertEqual(w['concurrency']['cancel-in-progress'],'false')
        job=w['jobs']['publish'];self.assertEqual(job['permissions'],{'contents':'read','actions':'read','id-token':'write'})
        auth=next(s for s in job['steps'] if s.get('id')=='auth')
        self.assertEqual(auth['with']['create_credentials_file'],'false');self.assertEqual(auth['with']['access_token_lifetime'],'1800s')
        build=next(s for s in job['steps'] if s['name']==p.TRUST['build_step_name'])
        self.assertEqual(build['timeout-minutes'],'20');self.assertNotIn('DATION_PUBLISH_ACCESS_TOKEN',build.get('env',{}))
        app=next(s for s in job['steps'] if s.get('with',{}).get('path')=='application')
        self.assertEqual(app['with']['ref'],p.SOURCE_SHA)
        artifact=next(s for s in job['steps'] if s.get('uses','').startswith('actions/upload-artifact@'))
        self.assertNotIn('**',artifact['with']['path']);self.assertNotIn('auth',artifact['with']['path'])
        for step in job['steps']:
            if 'uses' in step:self.assertRegex(step['uses'],r'@[0-9a-f]{40}$')

    def test_publication_code_has_no_deploy_iam_or_cloud_build_commands(self):
        tree=ast.parse((ROOT/'scripts/runtime_v2_publication.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='command' and node.args and isinstance(node.args[0],ast.Constant):
                self.assertNotIn(node.args[0].value,('gcloud','supabase','terraform'))


if __name__ == '__main__':unittest.main(verbosity=2)
