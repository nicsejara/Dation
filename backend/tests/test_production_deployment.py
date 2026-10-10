"""Deployment preserves service configuration and waits for the NEW revision."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('production_deployment',Path(__file__).resolve().parents[2]/'scripts/deploy_production_phase3.py')
deploy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


def service(observed=4,created='old',ready='old',condition='True'):
    return {'apiVersion':'serving.knative.dev/v1','kind':'Service',
        'metadata':{'name':'dation-core','generation':5,'resourceVersion':'17','namespace':'project','labels':{'existing':'label'},'uid':'output-only'},
        'spec':{'template':{'metadata':{'name':'old','labels':{'existing':'template'},'annotations':{'existing':'annotation'}},
            'spec':{'serviceAccountName':'runtime@example.invalid','containerConcurrency':4,'timeoutSeconds':300,
                'containers':[{'image':'old-image','env':[{'name':'SUPABASE_SECRET_KEY','valueFrom':{'secretKeyRef':{'name':'existing-secret','key':'1'}}},
                    {'name':'SUPABASE_INPUT_BUCKET','value':'qa-bucket'}],'resources':{'limits':{'memory':'512Mi','cpu':'1000m'}}}]}},
            'traffic':[{'revisionName':'old','percent':100}]},
        'status':{'observedGeneration':observed,'latestCreatedRevisionName':created,'latestReadyRevisionName':ready,
            'conditions':[{'type':'Ready','status':condition,'message':'QA readiness error'}]}}


class ProductionDeploymentTests(unittest.TestCase):
    def test_image_update_preserves_secrets_account_and_resource_limits(self):
        original=service();expected=copy.deepcopy(original)
        with patch.object(deploy,'run_request',side_effect=[original,service(5,'new','new')]) as request, \
             patch.object(deploy,'wait_ready',side_effect=lambda value,env:value):
            deploy.cloud_run(('run','services','update','dation-core','--image=new-image','--update-labels=dation-release=sha','--update-env-vars=DATION_RELEASE_SHA=sha'),{})
        body=request.call_args_list[1].args[3]
        self.assertEqual(body['metadata']['resourceVersion'],'17')
        self.assertNotIn('uid',body['metadata'])
        self.assertNotIn('name',body['spec']['template']['metadata'])
        self.assertEqual(body['spec']['template']['metadata']['annotations'],{'existing':'annotation'})
        actual=body['spec']['template']['spec'];before=expected['spec']['template']['spec']
        self.assertEqual(actual['serviceAccountName'],before['serviceAccountName'])
        self.assertEqual(actual['containerConcurrency'],before['containerConcurrency'])
        self.assertEqual(actual['containers'][0]['resources'],before['containers'][0]['resources'])
        self.assertEqual(actual['containers'][0]['env'][:2],before['containers'][0]['env'])
        self.assertEqual(actual['containers'][0]['image'],'new-image')
        self.assertEqual(body['spec']['traffic'],[{'latestRevision':True,'percent':100}])

    def test_ready_old_generation_or_old_revision_is_not_accepted(self):
        snapshots=[service(),service(5,'new','old'),service(5,'new','new')]
        with patch.object(deploy,'run_request',side_effect=snapshots) as request, \
             patch.object(deploy.time,'sleep'),patch.object(deploy.time,'monotonic',return_value=0):
            ready=deploy.wait_ready(service(),{})
        self.assertEqual(request.call_count,3)
        self.assertEqual(ready['status']['latestReadyRevisionName'],'new')

    def test_readiness_failure_is_reported(self):
        with patch.object(deploy,'run_request',return_value=service(5,'new','old','False')), \
             patch.object(deploy.time,'monotonic',return_value=0):
            with self.assertRaisesRegex(RuntimeError,'failed readiness'):
                deploy.wait_ready(service(),{})

    def test_worker_permission_error_never_attempts_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'worker.json';path.write_text(json.dumps({'metadata':{'name':'dation-core-worker'}}))
            with patch.object(deploy,'run_request',side_effect=RuntimeError('Cloud Run GET returned HTTP 403.')) as request:
                with self.assertRaisesRegex(RuntimeError,'403'):
                    deploy.cloud_run(('run','services','replace',str(path)),{})
            request.assert_called_once()

    def test_worker_create_requires_confirmed_404(self):
        body={'metadata':{'name':'dation-core-worker'}}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'worker.json';path.write_text(json.dumps(body))
            with patch.object(deploy,'run_request',side_effect=[RuntimeError('Cloud Run GET returned HTTP 404.'),body]) as request, \
                 patch.object(deploy,'wait_ready',return_value=body):
                deploy.cloud_run(('run','services','replace',str(path)),{})
            self.assertEqual(request.call_args_list[1].args[0],'POST')
            self.assertEqual(request.call_args_list[1].args[3],body)
