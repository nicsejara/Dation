"""Discover every E2E module and save a synthetic, machine-readable result."""
import json
import os
from pathlib import Path
import sys
import unittest
import argparse

# Direct execution uses tests/e2e as sys.path[0]. Ultimate modules also import
# the actual app and shared typed fixtures from backend, just like -m runners.
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

parser=argparse.ArgumentParser()
parser.add_argument('--module',action='append',default=[],help='Focused recheck; omitted means the entire suite.')
args=parser.parse_args()
suite = (unittest.defaultTestLoader.loadTestsFromNames(args.module) if args.module else
         unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern='test_*.py'))
class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.passed_ids=[]
    def addSuccess(self,test):super().addSuccess(test);self.passed_ids.append(test.id())
result = unittest.TextTestRunner(verbosity=2,resultclass=RecordedResult).run(suite)
# Missing coverage and skipped infrastructure must fail this release gate.
passed = result.wasSuccessful() and result.testsRun > 0 and not result.skipped
report = {
    'passed': passed, 'tests': result.testsRun,
    'failures': [test.id() for test, _ in result.failures],
    'errors': [test.id() for test, _ in result.errors],
    'skipped': [test.id() for test, _ in result.skipped],
    'passed_ids':result.passed_ids,
    'scope':'FOCUSED_RECHECK' if args.module else 'FULL',
    'selected_modules':args.module,
    'failure_details': [{'test': test.id(), 'traceback': trace[-3000:]}
                        for test, trace in result.failures + result.errors],
}
print('DATION_E2E_RESULT=' + json.dumps(report))
if artifact := os.getenv('DATION_E2E_ARTIFACTS'):
    Path(artifact).mkdir(parents=True, exist_ok=True)
    (Path(artifact)/'suite-report.json').write_text(json.dumps(report, indent=2))
sys.exit(0 if passed else 1)
