"""T12-R API/browser authority and kill-switch draining on owned infrastructure."""
import json,sys,unittest
from pathlib import Path
from uuid import uuid4
import httpx
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ultimate_result_fixture import ResultSandbox
from ultimate_result_helpers import setup_case,intention,submit,ok,wait_run,endpoint,approval,row
from auth_fixture import USER_A,USER_B,VIEWER
from tests.test_ultimate_data_contracts import model
from test_ultimate_d2_lineage import day_submit


class UltimatePilotCohortE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=ResultSandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)

    def setUp(self):
        self.s.sql(f"UPDATE dation_private.platform_release SET ultimate_pilot_enabled=true,ultimate_scheduling_admissions_enabled=true; UPDATE dation_private.ultimate_pilot_workspaces SET enabled=true WHERE workspace_id='{self.s.workspace_a}';")
    def tearDown(self):self.s.stop(self.s.worker,kill=True)
    def client(self,user):return httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[user]},trust_env=False,timeout=30)
    def model_body(self):return {'id':str(uuid4()),'name':'T12-R synthetic','configuration':model()['config_jsonb']}

    def test_01_authorized_workspace_and_legacy_default_no_payload_or_query_bypass(self):
        self.assertTrue(ok(self.s.api_client.get('/api/platform/ultimate-foundation/capabilities'))['enabled'])
        with self.client(USER_B) as b:
            self.assertFalse(ok(b.get('/api/platform/ultimate-foundation/capabilities',params={'ultimate_pilot_enabled':'true','workspace_id':self.s.workspace_a}))['enabled'])
            self.assertEqual(b.get('/api/platform/home').status_code,200)
            self.assertIn(b.post('/api/platform/logistics-models?ultimate_pilot_enabled=true',json=self.model_body()).status_code,[403,404])
            self.assertEqual(b.post('/api/platform/logistics-models',json={**self.model_body(),'ultimate_pilot_enabled':True}).status_code,422)
            self.assertEqual(b.get('/api/platform/ultimate-foundation/capabilities',headers={'X-Dation-Workspace-Id':self.s.workspace_a}).status_code,403)

    def test_02_kill_switch_blocks_new_admission_and_pack_write(self):
        cid=setup_case(self.s);body=intention(self.s,cid)
        base='/api/platform/logistics-cases/'+cid
        template=self.s.api_client.get(base+'/data/templates/transport_demand').content
        uploads=self.s.sql(f"SELECT count(*) FROM dation_private.ultimate_input_uploads WHERE case_id='{cid}';")
        for switch in ['UPDATE dation_private.platform_release SET ultimate_pilot_enabled=false;',
                       f"UPDATE dation_private.platform_release SET ultimate_pilot_enabled=true; UPDATE dation_private.ultimate_pilot_workspaces SET enabled=false WHERE workspace_id='{self.s.workspace_a}';"]:
            self.s.sql(switch)
            context=ok(self.s.api_client.get(base+'/run-context'))
            self.assertFalse(context['admission_available'])
            self.assertEqual(submit(self.s,cid,body=body)[2].status_code,403)
            self.assertIn(self.s.api_client.post('/api/platform/logistics-models',json=self.model_body()).status_code,[403,404])
            state=ok(self.s.api_client.get(base+'/data'))
            self.assertFalse(state['can_edit'])
            response=self.s.api_client.post(base+'/data/uploads/transport_demand',params={'upload_id':str(uuid4()),'contract_hash':state['contracts']['transport_demand']['contract_hash']},files={'file':('denied.csv',template,'text/csv')})
            # The existing T4 RPC reports a closed publication capability as
            # P0002 -> HTTP 404. Preserve that contract and prove no write.
            self.assertEqual(response.status_code,404,response.text)
            self.assertEqual(self.s.sql(f"SELECT count(*) FROM dation_private.ultimate_input_uploads WHERE case_id='{cid}';"),uploads)
        self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_runs WHERE decision_case_id='{cid}';"),'0')

    def test_03_owner_and_viewer_permissions_survive_cohort_gate(self):
        cid=setup_case(self.s);body=intention(self.s,cid)
        with self.client(VIEWER) as viewer:
            capabilities=ok(viewer.get('/api/platform/ultimate-foundation/capabilities'))
            self.assertTrue(capabilities['enabled']);self.assertFalse(capabilities['can_create_case'])
            self.assertEqual(viewer.post('/api/platform/logistics-models',json=self.model_body()).status_code,403)
            self.assertEqual(viewer.post('/api/runs',params={'run_id':str(uuid4())},json=body).status_code,403)
        self.s.sql(f"UPDATE workspace_members SET access_role='operator' WHERE workspace_id='{self.s.workspace_a}' AND user_id='{USER_A}';")
        try:
            rid,_,response=submit(self.s,cid,body=body);self.assertEqual(response.status_code,202,response.text)
            self.s.start_worker();wait_run(self.s,rid)
        finally:self.s.sql(f"UPDATE workspace_members SET access_role='admin' WHERE workspace_id='{self.s.workspace_a}' AND user_id='{USER_A}';")

    def test_04_kill_drains_admitted_job_preserves_history_replay_and_approval(self):
        cid=setup_case(self.s);rid,body,response=submit(self.s,cid);ok(response)
        self.s.sql('UPDATE dation_private.platform_release SET ultimate_pilot_enabled=false;')
        self.s.start_worker();completed=wait_run(self.s,rid)
        package=ok(endpoint(self.s,rid))['package'];fp=completed['result_fingerprint']
        self.assertEqual(package['fingerprints']['result_fingerprint'],fp)
        self.assertTrue(ok(endpoint(self.s,rid,'approval-review'))['approval_overlay']['approval_allowed'])
        ok(approval(self.s,cid,rid));snapshot=row(self.s,rid)
        self.assertEqual(submit(self.s,cid,rid=rid,body=body)[2].status_code,202)
        self.assertEqual(row(self.s,rid),snapshot)
        self.assertEqual(submit(self.s,cid,body=body)[2].status_code,403)
        self.assertEqual(day_submit(self.s,cid)[2].status_code,403)
        self.assertEqual(row(self.s,rid),snapshot)
        self.assertEqual(ok(endpoint(self.s,rid))['package'],package)

    def test_05_real_browser_localstorage_and_query_cannot_activate_unenrolled_workspace(self):
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            try:
                context=browser.new_context()
                login=context.request.post(self.s.api_url+'/auth/login',headers={'Origin':self.s.api_url},data={'email':'user-2@example.test','password':'dispatch-e2e-private'})
                self.assertEqual(login.status,200)
                page=context.new_page();page.goto(self.s.api_url+'/app',wait_until='domcontentloaded')
                page.evaluate("(wid)=>{localStorage.setItem('ultimate_pilot_enabled','true'); localStorage.setItem('ultimate_foundation_enabled','true'); localStorage.setItem('ultimate_workspace_ids',JSON.stringify([wid]));}",self.s.workspace_b)
                page.goto(self.s.api_url+'/app/ddas/logistics/models?model_id=new&ultimate_pilot_enabled=true',wait_until='domcontentloaded')
                observed=page.evaluate("""async (body)=>{
                    const session=await (await fetch('/auth/session',{method:'POST'})).json();
                    const headers={Authorization:'Bearer '+session.access_token,'Content-Type':'application/json'};
                    const capabilities=await (await fetch('/api/platform/ultimate-foundation/capabilities?ultimate_pilot_enabled=true',{headers})).json();
                    const write=await fetch('/api/platform/logistics-models?ultimate_pilot_enabled=true',{method:'POST',headers,body:JSON.stringify(body)});
                    return {capabilities,status:write.status};
                }""",self.model_body())
                self.assertFalse(observed['capabilities']['enabled']);self.assertIn(observed['status'],[403,404])
                context.close()
            finally:browser.close()


if __name__=='__main__':unittest.main()
