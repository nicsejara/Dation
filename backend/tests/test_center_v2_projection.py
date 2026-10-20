import unittest
from app.platform.decision_center import node_objective,project

class CenterObjectiveTests(unittest.TestCase):
 def test_official_objective_is_not_replaced_by_a_later_candidate(self):
  summary={'approved':{'id':'official','configuration_json':{'objective':'cost_min'}},'latest':{'id':'candidate','configuration_json':{'objective':'co2_min'}}}
  self.assertEqual(node_objective(summary,True),{'id':'min_cost','label':'Costo mínimo','source':'approved_run','run_id':'official'})
  self.assertEqual(node_objective(summary,False)['id'],'min_co2')
 def test_unknown_objective_is_preserved_and_missing_draft_is_not_invented(self):
  self.assertIsNone(node_objective({},False))
  self.assertEqual(node_objective({'latest':{'id':'run','configuration_json':{'strategy':'historic_strategy'}}},False)['label'],'historic_strategy')
