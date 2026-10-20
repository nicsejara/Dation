"""Home uses canonical evidence for resume while preserving explicit candidates."""
import copy,json,unittest
from pathlib import Path
from app.platform.home import recent_case

FIXTURE=json.loads((Path(__file__).parent/'browser/fixtures.json').read_text())

class HomeResumeTests(unittest.TestCase):
 def bundle(self,assignment=None,scheduling=None,approval=None):
  summaries={key:{'latest':None,'approved':None,'run_count':0} for key in FIXTURE['case']['nodes']}
  for key,run in [('logistics_assignment',assignment),('logistics_scheduling',scheduling)]:
   if run:summaries[key].update(latest=run,approved=run if run.get('approved_at') else None,run_count=1)
  if approval:summaries['logistics_assignment'].update(approved=approval,run_count=2)
  return {'case':copy.deepcopy(FIXTURE['case_row']),'label':'Mi caso','summaries':summaries}
 def test_ordinary_resume_opens_official_approval_and_retains_candidate_id(self):
  approved=copy.deepcopy(FIXTURE['runs']['assignment']);candidate={**approved,'id':'00000000-0000-4000-8000-000000000006','approved_at':None,'created_at':'2026-10-20T00:00:00Z'}
  bundle=self.bundle(candidate,approval=approved);before=copy.deepcopy(bundle)
  for status in ['queued','running','completed','error']:
   bundle['summaries']['logistics_assignment']['latest']['status']=status
   result=recent_case(bundle)
   self.assertEqual(result['resume']['run_id'],approved['id']);self.assertEqual(result['run_id'],candidate['id']);self.assertTrue(result['approval_current'])
   self.assertEqual(result['context']['friendlyId'],'DC-00000000');self.assertEqual(result['node_label'],'Asignación de carga')
  bundle['summaries']['logistics_assignment']['latest']['status']='completed';self.assertEqual(bundle,before)
 def test_initial_case_opens_configuration_and_reads_do_not_repair_legacy_cache(self):
  bundle=self.bundle();bundle['case']['state_json']={'schema_version':'invalid'};before=copy.deepcopy(bundle)
  result=recent_case(bundle)
  self.assertEqual(result['resume'],{'view':'logistics-config','node_id':'logistics_assignment','run_id':None});self.assertEqual(bundle,before)
 def test_completed_cache_without_approvals_does_not_claim_completion(self):
  bundle=self.bundle();bundle['case']['status']='completed'
  result=recent_case(bundle);self.assertEqual(result['status'],'available')
 def test_stale_scheduling_does_not_navigate_as_an_official_approval(self):
  d1=copy.deepcopy(FIXTURE['runs']['assignment']);d1['id']='00000000-0000-4000-8000-000000000007'
  d2={**copy.deepcopy(FIXTURE['runs']['scheduling']),'approved_at':'2026-10-10T00:00:00Z'}
  result=recent_case(self.bundle(d1,d2))
  self.assertEqual(result['status'],'stale');self.assertFalse(result['approval_current']);self.assertEqual(result['resume']['run_id'],d2['id'])
 def test_real_two_step_approval_opens_latest_official_dashboard(self):
  d1=copy.deepcopy(FIXTURE['runs']['assignment']);d2={**copy.deepcopy(FIXTURE['runs']['scheduling']),'approved_at':'2026-10-10T00:00:00Z'}
  result=recent_case(self.bundle(d1,d2))
  self.assertEqual(result['status'],'completed');self.assertEqual(result['resume']['run_id'],d2['id'])
