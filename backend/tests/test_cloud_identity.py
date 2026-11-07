"""Runtime V2 cannot fall back to, emit manifests for, or contact another project."""
import copy
import importlib.util
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from app import cloud_identity as identity
from app.observability import JSONFormatter

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import zero_idle_release as release


class CloudIdentityTests(unittest.TestCase):
    def setUp(self):self.plan=json.loads(release.DEFAULT.read_text())

    def test_missing_mixed_and_retired_identity_are_rejected(self):
        valid=identity.environment()
        identity.validate_environment(valid)
        changes={**dict.fromkeys(valid,''), 'DATION_CLOUD_PROJECT':'dation-510100',
                 'DATION_CLOUD_PROJECT_NUMBER':'469052310590',
                 'DATION_CLOUD_REGION':'us-central1',
                 'DATION_CONTROL_JOB':'projects/other-project/locations/us-west1/jobs/dation-recovery',
                 'GOOGLE_CLOUD_PROJECT':'other-project'}
        for key in valid:
            missing=dict(valid);missing.pop(key)
            with self.subTest(missing=key),self.assertRaises(ValueError):identity.validate_environment(missing)
        for key,value in changes.items():
            with self.subTest(key=key),self.assertRaises(ValueError):identity.validate_environment({**valid,key:value})

    def test_release_rejects_cross_project_accounts_images_resources_and_schedule(self):
        changes=[('project','dation-510100'),('project_number','469052310590'),
                 ('region','us-central1'),('service_account','runtime@dation-510100.iam.gserviceaccount.com'),
                 ('scheduler_service_account',self.plan['service_account']),
                 ('image','us-west1-docker.pkg.dev/dation-510100/repo/runtime@sha256:'+'a'*64)]
        changes.append(('image',f'us-west1-docker.pkg.dev/{identity.PROJECT}/repo/../runtime@sha256:'+'a'*64))
        for key,value in changes:
            with self.subTest(key=key):
                plan=copy.deepcopy(self.plan);plan[key]=value
                with self.assertRaises(ValueError):release.manifest(plan)
        for key in identity.environment():
            with self.subTest(missing=key):
                plan=copy.deepcopy(self.plan);plan['environment'].pop(key)
                with self.assertRaises(ValueError):release.manifest(plan)
        for key,value in [('target','dation-executor'),('enabled',True),('create_by_default',True),('time_zone','America/Los_Angeles')]:
            with self.subTest(schedule=key):
                plan=copy.deepcopy(self.plan);plan['recovery_schedule'][key]=value
                with self.assertRaises(ValueError):release.manifest(plan)

    def test_iam_and_secret_proposals_are_resource_scoped_and_scheduler_closed(self):
        proposal=release.manifest(self.plan)
        self.assertFalse(proposal['mutation_performed']);self.assertFalse(proposal['scheduler_created'])
        iam=proposal['iam'];runtime=self.plan['service_account'];scheduler=self.plan['scheduler_service_account']
        role=f'projects/{identity.PROJECT}/roles/dationFiniteJobDispatcher'
        runtime_bindings=[b for b in iam['bindings'] if b['role']==role]
        self.assertEqual({b['resource'] for b in runtime_bindings},set(identity.JOBS.values()))
        self.assertTrue(all(b['members']==['serviceAccount:'+runtime] for b in runtime_bindings))
        scheduler_bindings=[b for b in iam['bindings'] if 'serviceAccount:'+scheduler in b['members']]
        self.assertEqual(scheduler_bindings,[{'resource':identity.JOBS['control'],'role':'roles/run.invoker','members':['serviceAccount:'+scheduler]}])
        self.assertEqual(set(iam['custom_role']['role']['includedPermissions']),{'run.jobs.get','run.jobs.run','run.jobs.runWithOverrides'})
        self.assertFalse(proposal['secret_manager']['values_included'])
        for binding in iam['bindings']:
            self.assertNotIn('allUsers',binding['members'])
            self.assertTrue(binding['resource'].startswith(f'projects/{identity.PROJECT}/'))
            self.assertNotEqual(binding['resource'],f'projects/{identity.PROJECT}')
        schedule=proposal['scheduler']
        self.assertFalse(schedule['enabled']);self.assertFalse(schedule['create_by_default'])
        self.assertTrue(schedule['creation_requires_explicit_go'])
        target=schedule['request']['httpTarget']
        self.assertEqual(target['uri'],'https://run.googleapis.com/v2/'+identity.JOBS['control']+':run')
        self.assertEqual(target['oauthToken']['serviceAccountEmail'],scheduler)

    def test_operational_sources_contain_no_retired_project_target(self):
        paths=[ROOT/'.env.example']
        for directory in ['backend/app','scripts','infra']:
            paths += [p for p in (ROOT/directory).rglob('*') if p.suffix in {'.py','.json','.md'}]
        for path in paths:
            source=path.read_text()
            for retired in ['dation-510100','469052310590']:
                with self.subTest(file=str(path.relative_to(ROOT)),retired=retired):self.assertNotIn(retired,source)

    def test_legacy_cloud_helpers_refuse_other_project_before_credentials_or_network(self):
        import deploy_production_phase3 as legacy
        with patch.object(legacy,'urlopen') as network:
            with self.assertRaises(RuntimeError):legacy.run_request('GET','projects/dation-510100/locations/us-west1/services/dation-core',{})
            with self.assertRaises(RuntimeError):legacy.run_request('POST',f'projects/{identity.PROJECT}/locations/us-west1/services',{})
            network.assert_not_called()
        import release_platform_identity as auth_legacy
        with patch.object(auth_legacy,'urlopen') as network:
            with self.assertRaises(RuntimeError):auth_legacy.auth_config()
            network.assert_not_called()

    def test_apply_cli_stays_blocked_with_old_or_new_authorization_flags(self):
        for flag in ['AUTHORIZE_SAGA02_INFRASTRUCTURE','AUTHORIZE_RUNTIME_V2']:
            result=subprocess.run([sys.executable,str(ROOT/'scripts/zero_idle_release.py'),'apply','--authorize',flag],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('no production action permitted',result.stderr)

    def test_trace_formatter_never_emits_retired_or_unexpected_cloud_project(self):
        record=logging.LogRecord('test',logging.INFO,'',1,'',(),None)
        record.telemetry={'trace_id':'a'*32}
        for project in ['dation-510100','other-project',identity.PROJECT]:
            with patch.dict(os.environ,{'GOOGLE_CLOUD_PROJECT':project}):data=json.loads(JSONFormatter().format(record))
            if project==identity.PROJECT:self.assertEqual(data['logging.googleapis.com/trace'],f'projects/{identity.PROJECT}/traces/'+'a'*32)
            else:self.assertNotIn('logging.googleapis.com/trace',data)

    def test_cloud_shell_inventory_stops_on_unverified_project_and_rejects_other_urls(self):
        import runtime_v2_readonly as inventory
        reader=unittest.mock.Mock(return_value={'http_status':401,'verified':False})
        value=inventory.collect('synthetic',reader)
        reader.assert_called_once_with(inventory.endpoints()['project'],'synthetic')
        self.assertIn('NOT_ATTEMPTED',value['remaining_reads'])
        with patch.object(inventory,'urlopen') as network:
            with self.assertRaises(ValueError):inventory.fetch('https://run.googleapis.com/v2/projects/dation-510100/locations/us-west1/services','synthetic')
            network.assert_not_called()

    def test_cloud_shell_inventory_uses_only_get_and_drops_credentials_and_env_values(self):
        import runtime_v2_readonly as inventory
        response=unittest.mock.MagicMock()
        response.status=200;response.read.return_value=b'{"services":[{"name":"owned","template":{"containers":[{"env":[{"value":"private"}]}]}}],"access_token":"private"}'
        response.__enter__.return_value=response
        with patch.object(inventory,'urlopen',return_value=response) as network:
            result=inventory.fetch(inventory.endpoints()['services'],'synthetic')
        self.assertEqual(network.call_args.args[0].get_method(),'GET')
        self.assertTrue(result['verified']);self.assertNotIn('private',json.dumps(result))
