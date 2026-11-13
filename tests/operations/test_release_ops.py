"""Pure mocked Runtime V2 release tests. No Google Cloud calls are allowed."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('dation_release',ROOT/'scripts/release/dation_release.py')
release=importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
SHA='a'*40
DIGEST='sha256:'+'b'*64
IMAGE=release.REGISTRY+'@'+DIGEST
OLD='dation-core-00001-12g'
NEW='dation-core-00002-m4z'

def example_service(active_rev=OLD):
    return {'spec':{'template':{'metadata':{'annotations':{
        'autoscaling.knative.dev/minScale':'0','autoscaling.knative.dev/maxScale':'2',
        'run.googleapis.com/cpu-throttling':'true'}},
        'spec':{'serviceAccountName':'pilot@example.iam.gserviceaccount.com','containerConcurrency':12,
            'containers':[{'image':IMAGE,'env':[{'name':'IS_DATION','value':'yes'}],
               'resources':{'limits':{'cpu':'1','memory':'512Mi'}}}]}}},
        'status':{'traffic':[{'revisionName':active_rev,'percent':100}],
          'latestCreatedRevisionName':NEW}}
def example_revision(image=IMAGE,ready=True):
    return {'spec':{'containers':[{'image':image}]},
      'status':{'conditions':[{'type':'Ready','status':'True' if ready else 'False'}]}}

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir=Path(tmp.name)
        self.patch=mock.patch.object(release,'STATE',self.dir)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.sample={'sha':SHA,'project':release.PROJECT,'region':release.REGION,
                     'service':release.SERVICE,'image':IMAGE,'settings':release.settings(example_service()),
                     'old_revision':OLD,'new_revision':NEW,'promoted':False}
    def test_wrong_sha_and_bad_autoscaling_fail_closed(self):
        with self.assertRaisesRegex(RuntimeError,'40 hexadecimal'):release.state_file('short')
        s=example_service()
        s['spec']['template']['metadata']['annotations']['autoscaling.knative.dev/minScale']='1'
        with self.assertRaisesRegex(RuntimeError,'min instances'):release.settings(s)
    def test_prepare_uses_exact_digest_and_no_traffic(self):
        with mock.patch.object(release,'service',return_value=example_service()), \
             mock.patch.object(release,'registry_image',return_value=IMAGE), \
             mock.patch.object(release,'revision',return_value=example_revision()), \
             mock.patch.object(release,'time') as timer, \
             mock.patch.object(release,'command') as command:
            release.prepare(SHA)
            self.assertTrue(any('--no-traffic' in c.args for c in command.call_args_list))
            self.assertEqual(release.load(SHA)['image'],IMAGE)
            self.assertEqual(release.load(SHA)['new_revision'],NEW)
            command.reset_mock()
            release.prepare(SHA)
            command.assert_not_called()
    def test_promote_requires_confirmation_and_pinned_revision(self):
        release.save(self.sample)
        with self.assertRaisesRegex(RuntimeError,'explicit confirmation'):
            release.promote(SHA,'')
        with mock.patch.object(release,'service',side_effect=[
             example_service(),example_service(NEW)]), \
             mock.patch.object(release,'revision',return_value=example_revision()), \
             mock.patch.object(release,'command') as command:
            release.promote(SHA,'PROMOTE_100')
            self.assertIn('--to-revisions='+NEW+'=100',command.call_args.args)
            self.assertTrue(release.load(SHA)['promoted'])
    def test_promote_refuses_changed_service_config(self):
        release.save(self.sample)
        s=example_service()
        s['spec']['template']['spec']['serviceAccountName']='intruder@example.iam.gserviceaccount.com'
        with mock.patch.object(release,'service',return_value=s), \
             mock.patch.object(release,'revision',return_value=example_revision()), \
             mock.patch.object(release,'command') as command, \
             self.assertRaisesRegex(RuntimeError,'configuration changed'):
            release.promote(SHA,'PROMOTE_100')
        command.assert_not_called()
    def test_smoke_does_not_send_http_or_change_traffic(self):
        release.save(self.sample)
        with mock.patch.object(release,'service',return_value=example_service()), \
             mock.patch.object(release,'revision',return_value=example_revision()), \
             mock.patch.object(release,'command') as command:
            release.smoke(SHA)
        command.assert_not_called()
    def test_rollback_only_to_saved_revision(self):
        release.save(self.sample)
        with mock.patch.object(release,'service',side_effect=[
              example_service(NEW),example_service(OLD)]), \
             mock.patch.object(release,'revision',return_value=example_revision()), \
             mock.patch.object(release,'command') as command:
            release.rollback(SHA,'ROLLBACK_100')
            self.assertIn('--to-revisions='+OLD+'=100',command.call_args.args)
    def test_interrupted_prepare_does_not_redeploy(self):
        release.save({**self.sample,'new_revision':None})
        with mock.patch.object(release,'service',return_value=example_service()), \
             mock.patch.object(release,'revision',return_value=example_revision()), \
             mock.patch.object(release,'command') as command:
            release.prepare(SHA)
            command.assert_not_called()
            self.assertEqual(release.load(SHA)['new_revision'],NEW)

if __name__=='__main__':unittest.main()
