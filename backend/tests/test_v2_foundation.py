import json
from pathlib import Path
import unittest
from app.platform.foundation import resolve_node_destination,objective_presentation,case_context

class FoundationTests(unittest.TestCase):
    def test_backend_obeys_the_same_destination_contract_as_browser(self):
        for vector in json.loads(Path(__file__).with_name('foundation_vectors.json').read_text()):
            with self.subTest(vector=vector['name']):
                self.assertEqual(resolve_node_destination(vector['node_id'],vector['node']),vector['expected'])

    def test_objective_and_context_labels_do_not_rewrite_engine_configuration(self):
        self.assertEqual(objective_presentation('min_cost'),{'id':'min_cost','label':'Costo mínimo'})
        self.assertEqual(objective_presentation('cost_min'),objective_presentation('min_cost'))
        self.assertEqual(case_context({'id':'abcdef12','label':'Caso','status':'archived'})['friendlyId'],'DC-ABCDEF12')
