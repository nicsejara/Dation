import json
import unittest
from pathlib import Path
from app.engines.dispatch import run_dispatch_engine

ROOT = Path(__file__).resolve().parents[2] / 'sample_data/v1/cases'


class DownloadableFixtureTests(unittest.TestCase):
    def test_expected_results(self):
        for case in json.loads((ROOT/'expected.json').read_text()):
            with self.subTest(case=case['case']):
                folder = ROOT / case['case']
                args = ((folder/'orders.csv').read_bytes(), (folder/'fleet.csv').read_bytes())
                kwargs = {'configuration': case['configuration'], 'options': {**case['options'], 'sensitivity': False}}
                expected = case['expected']
                if 'error_contains' in expected:
                    with self.assertRaisesRegex(ValueError, expected['error_contains']):
                        run_dispatch_engine(*args, **kwargs)
                else:
                    result = run_dispatch_engine(*args, **kwargs)
                    for key, value in expected.items():
                        self.assertAlmostEqual(result['scenarios']['selected']['metrics'][key], value)
