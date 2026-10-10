"""Discover every E2E module and save a synthetic, machine-readable result."""
import json
import os
from pathlib import Path
import sys
import unittest


suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern='test_*.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
# Missing coverage and skipped infrastructure must fail this release gate.
passed = result.wasSuccessful() and result.testsRun > 0 and not result.skipped
if artifact := os.getenv('DATION_E2E_ARTIFACTS'):
    Path(artifact).mkdir(parents=True, exist_ok=True)
    (Path(artifact)/'suite-report.json').write_text(json.dumps({
        'passed': passed, 'tests': result.testsRun,
        'failures': [test.id() for test, _ in result.failures],
        'errors': [test.id() for test, _ in result.errors],
        'skipped': [test.id() for test, _ in result.skipped],
    }, indent=2))
sys.exit(0 if passed else 1)
