"""Fast classifier contract: unknown changes must never skip required FULL."""
import importlib.util
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('rapid_impact',ROOT/'scripts/ci/impact.py')
impact=importlib.util.module_from_spec(spec)
spec.loader.exec_module(impact)

class RapidImpactTests(unittest.TestCase):
    def check(self,paths,risk,full):
        r=impact.classify_files(paths)
        self.assertEqual(r['risk'],risk)
        self.assertEqual(r['requires_full'],full)
        return r
    def test_docs(self):
        self.check(['docs/notes.md'],'R0',False)
    def test_css(self):
        self.check(['backend/app/static/css/theme.css'],'R1',False)
    def test_core_ux_must_include_case_smoke(self):
        r=self.check(['backend/app/static/js/dispatch/models/planning-model.mjs'],'R2',False)
        self.assertTrue(any('test_01_first_time_landing' in v for v in r['browser_tests']))
        self.assertTrue(any('test_07_contract_failure' in v for v in r['browser_tests']))
    def test_graph_ux_must_include_dependency_smoke(self):
        r=self.check(['backend/app/static/js/dispatch/navigation/resource.mjs'],'R2',False)
        self.assertTrue(any('test_05_graph_data' in v for v in r['browser_tests']))
    def test_sql_and_auth_always_full(self):
        self.check(['supabase/migrations/some.sql'],'R3',True)
        self.check(['backend/app/auth.py'],'R3',True)
    def test_workflow_release_and_unknown_fail_closed(self):
        self.check(['.github/workflows/fast-check.yml'],'R4',True)
        self.check(['random/unknown.xyz'],'R3',True)
        self.check([],'R4',True)
    def test_mixed_risks_elevate(self):
        self.check(['docs/plan.md','backend/app/static/css/theme.css','backend/app/models.py'],'R3',True)

if __name__ == '__main__':unittest.main()
