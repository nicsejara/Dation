"""Owned test databases must leave no anonymous volumes, even on startup failure."""
import json
import subprocess
import unittest
from unittest.mock import patch

from sandbox import Sandbox


class SandboxCleanupTests(unittest.TestCase):
    def test_owned_resources_are_released_after_success_and_startup_failure(self):
        for fail in (False, True):
            with self.subTest(startup_failure=fail):
                sandbox = Sandbox()
                volumes = []
                start_api = sandbox.start_api

                def capture_then_start():
                    metadata = json.loads(subprocess.check_output(['docker', 'inspect', sandbox.pg], text=True))[0]
                    volumes.extend(m['Name'] for m in metadata['Mounts'] if m['Type'] == 'volume')
                    if fail:
                        raise RuntimeError('synthetic fixture startup failure')
                    start_api()

                with patch.object(sandbox, 'start_api', capture_then_start):
                    if fail:
                        with self.assertRaisesRegex(RuntimeError, 'synthetic fixture startup failure'):
                            with sandbox:
                                self.fail('Startup must fail before yielding the fixture')
                    else:
                        with sandbox:
                            self.assertTrue(sandbox.reachable(sandbox.api_url + '/health'))
                self.assertTrue(volumes, 'PostgreSQL anonymous volume was not inspected')
                for volume in volumes:
                    self.assertNotEqual(subprocess.run(['docker', 'volume', 'inspect', volume], capture_output=True).returncode, 0,
                                        'Owned PostgreSQL data leaked after the fixture closed')
                self.assertNotEqual(subprocess.run(['docker', 'inspect', sandbox.pg], capture_output=True).returncode, 0)
                self.assertNotEqual(subprocess.run(['docker', 'network', 'inspect', sandbox.network], capture_output=True).returncode, 0)
                self.assertTrue(all(process.poll() is not None for process in sandbox.processes))
