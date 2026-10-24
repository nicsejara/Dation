"""A–F against the real API, SQL authority, worker and browser; no production writes."""
import json
import os
from pathlib import Path
import subprocess
import unittest
from auth_fixture import USER_A,VIEWER
import test_v2_golden as golden
from sandbox import ROOT

class FinalPolishLineageTests(unittest.TestCase):
    setUpClass=classmethod(golden.GoldenWorkflowTests.setUpClass.__func__)
    setUp=golden.GoldenWorkflowTests.setUp
    checked=golden.GoldenWorkflowTests.checked
    create_case=golden.GoldenWorkflowTests.create_case

    def test_actual_rerun_routing_and_lineage_scenarios_a_through_f(self):
        case,datasets=self.create_case(USER_A);admin=self.clients[USER_A]
        detail=self.checked(admin.get('/api/platform/decisions/'+case))
        self.checked(admin.put(f'/api/platform/decisions/{case}/attributes',json={
            'expected_updated_at':detail['updated_at'],'expected_owner_updated_at':None,
            'label':'Lineage A–F','category':'simulation','description':'Isolated acceptance',
            'data_owner_user_id':golden.STEWARD}))
        for stage in ('logistics_assignment','logistics_scheduling'):
            self.checked(admin.put(f'/api/platform/decisions/{case}/responsibilities/{stage}',json={'expected_updated_at':None,'owner_user_id':golden.OWNER}))
        before=self.checked(admin.get(f'/api/platform/decisions/{case}/responsibilities'))['stages']
        self.s.start_worker()
        environment={**self.s.env,'DATION_E2E_URL':self.s.api_url,'DATION_E2E_CASE':case}
        result=subprocess.run([os.getenv('DATION_BROWSER_PYTHON',str(ROOT/'.browser-venv/bin/python')),str(ROOT/'tests/e2e/run_lineage_journey.py')],cwd=ROOT,env=environment,text=True,capture_output=True,timeout=360)
        if result.returncode:self.s.diagnostics('final-polish-lineage')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(result.stdout.strip().splitlines()[-1]);self.assertEqual(report['scenarios'],dict.fromkeys('ABCDEF','PASS'))
        ids=report['runs'];self.assertEqual(len(set(ids.values())),7)
        self.assertEqual(self.s.sql('SELECT count(*) FROM decision_cases;'),'1')
        self.assertEqual(self.s.sql('SELECT count(*) FROM decision_runs;'),'7')
        owner=self.clients[golden.OWNER]
        for run,source in ((ids['D2_A'],ids['D1_A']),(ids['D2_B'],ids['D1_A']),(ids['D2_C'],ids['D1_B'])):
            saved=self.checked(owner.get('/api/runs/'+run));self.assertEqual(saved['upstream_run_id'],source)
            self.assertEqual(saved['decision_case_id'],case)
            self.assertEqual(saved['created_by_user_id'],golden.OWNER)
        for key in ('D1_A','D2_A','D2_B'):
            saved=self.checked(owner.get('/api/runs/'+ids[key]));self.assertIsNotNone(saved['approved_at']);self.assertIsNotNone(saved['superseded_at'])
            self.assertEqual(saved['approved_by_user_id'],golden.OWNER)
        current=self.checked(owner.get('/api/runs/'+ids['D1_B']));self.assertIsNotNone(current['approved_at']);self.assertIsNone(current['superseded_at'])
        self.assertEqual(self.checked(admin.get(f'/api/platform/decisions/{case}/responsibilities'))['stages'],before)
        # Replay an old admitted intention after the active lineage changed.
        request=next(r for r in report['requests'] if r['id']==ids['D1_02'])
        self.checked(owner.post('/api/runs',params={'run_id':request['id']},json=request['body']),202)
        self.assertEqual(self.s.sql('SELECT count(*) FROM decision_runs;'),'7')
        self.assertIsNone(self.checked(owner.get('/api/runs/'+ids['D1_B']))['superseded_at'])
        # A new D2 intention cannot use the retired D1, and a Viewer cannot admit it.
        body=next(r['body'] for r in report['requests'] if r['id']==ids['D2_A'])
        from uuid import uuid4
        self.assertEqual(owner.post('/api/runs',params={'run_id':str(uuid4())},json=body).status_code,409)
        self.assertEqual(self.clients[VIEWER].post('/api/runs',params={'run_id':str(uuid4())},json=body).status_code,403)
        self.assertEqual(self.s.sql('SELECT count(*) FROM decision_runs;'),'7')
        self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_approval_events WHERE case_id='{case}' AND action='approved';"),'4')
        case_row=self.checked(admin.get('/api/decision-cases/'+case))
        self.assertEqual(case_row['orders']['id'],datasets['orders']['id']);self.assertEqual(case_row['fleet']['id'],datasets['fleet']['id'])
        artifact=os.getenv('DATION_E2E_ARTIFACTS')
        if artifact:Path(artifact,'lineage-report.json').write_text(json.dumps(report,indent=2))
