"""Characterization captured from a8ebde9 before extracting the Case domain."""
import ast
import copy
import json
from pathlib import Path
import unittest

from app.domain import decision_cases as domain


VECTORS = json.loads((Path(__file__).parent / 'fixtures/case_projection_vectors.json').read_text())


class CaseDomainTests(unittest.TestCase):
    def test_projection_preserves_baseline_outputs_and_input_evidence(self):
        for vector in VECTORS['scenarios']:
            with self.subTest(scenario=vector['name']):
                state, runs = copy.deepcopy(VECTORS['state']), copy.deepcopy(vector['runs'])
                before = copy.deepcopy((state, runs))
                options = {'summaries': copy.deepcopy(vector['summaries'])} if 'summaries' in vector else {}
                projected = domain.project_case_history(state, runs, **VECTORS['context'], **options)
                self.assertEqual(projected, {**VECTORS['state'], 'nodes': vector['expected_nodes']})
                self.assertEqual((state, runs), before, 'Projection must not mutate persisted input evidence')

    def test_cached_approval_cannot_survive_absent_authoritative_runs(self):
        state = copy.deepcopy(VECTORS['state'])
        for node in state['nodes'].values():
            node.update(status='approved', run_id='old', approved_run_id='old', approved_at='old', run_count=99)
        projected = domain.project_case_history(state, [], **VECTORS['context'])
        self.assertEqual(projected['nodes'], VECTORS['state']['nodes'])

    def test_case_identity_and_run_counts_are_validated(self):
        state = copy.deepcopy(VECTORS['state'])
        state['id'] = 'another-case'
        with self.assertRaisesRegex(ValueError, 'otro Decision Case'):
            domain.validate_case_state(state, **VECTORS['context'])
        state = copy.deepcopy(VECTORS['state'])
        state['nodes']['logistics_assignment']['run_count'] = 'not-a-number'
        with self.assertRaisesRegex(ValueError, 'Conteo de corridas inválido'):
            domain.validate_case_state(state, **VECTORS['context'])

    def test_domain_has_no_infrastructure_dependency(self):
        tree = ast.parse(Path(domain.__file__).read_text())
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        self.assertEqual(set(imports), {'__future__', 'datetime'})
