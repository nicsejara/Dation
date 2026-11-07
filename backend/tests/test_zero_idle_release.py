"""Negative release controls must fail before any cloud/SQL operation."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('zero_idle_release',ROOT/'scripts/zero_idle_release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

class ZeroIdleReleaseTests(unittest.TestCase):
    def setUp(self):self.plan=json.loads(release.DEFAULT.read_text())
    def test_plan_has_no_mutation_and_pins_zero_idle(self):
        result=release.manifest(self.plan)
        self.assertFalse(result['mutation_performed']);self.assertFalse(result['scheduler_created'])
        self.assertEqual(result['service']['template']['scaling']['minInstanceCount'],0)
        self.assertTrue(result['service']['template']['containers'][0]['resources']['cpuIdle'])
    def test_negative_always_on_secret_and_test_transport_configs(self):
        changes=[('api','min_instances',1),('api','cpu_idle',False),('compute','command',['python','worker.py']),
            ('environment','SUPABASE_SECRET_KEY','embedded'),('environment','DATION_TEST_RUNTIME','1'),
            ('environment','DATION_EXECUTION_MODE','legacy'),('environment','DATION_CLOUD_EXECUTION_ENABLED','true')]
        for group,key,value in changes:
            with self.subTest(key=key):
                p=copy.deepcopy(self.plan);p[group][key]=value
                with self.assertRaises(ValueError):release.validate(p)
    def test_every_script_scan_rejects_unsafe_generated_payload(self):
        release.scan_deploy_scripts()
        for code in ["payload={'autoscaling.knative.dev/minScale':'1'}", "args=['--no-cpu-throttling']", "args=['python','worker.py']", "resource={'cpuIdle':False}", "env={'SUPABASE_SECRET_KEY':'embedded'}"]:
            with tempfile.TemporaryDirectory() as d:
                (Path(d)/'successor.py').write_text(code)
                with self.assertRaises(ValueError):release.scan_deploy_scripts(Path(d))
    def test_apply_refuses_unverified_remote_trigger_even_with_authorize_flag(self):
        for flag in [None,'AUTHORIZE_SAGA02_INFRASTRUCTURE']:
            with self.assertRaises(ValueError):release.apply_gate(self.plan,flag)
    def test_rollback_never_chooses_historical_resident_revision(self):
        result=release.rollback_plan(self.plan)
        self.assertFalse(result['mutation_performed']);self.assertIn('zero-idle',result['target'])
        self.assertIn('retain accepted',result['admissions'])
