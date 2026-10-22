"""Focused Saga 3 navigation guards and terminal-run recovery."""
import copy
import unittest
from urllib.parse import parse_qs,urlparse
import test_navigation as navigation

class Saga3UITests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):navigation.NavigationTests.setUpClass()
    @classmethod
    def tearDownClass(cls):navigation.NavigationTests.tearDownClass()

    async def asyncSetUp(self):
        self.b=navigation.NavigationTests();await self.b.asyncSetUp();self.page=self.b.page
        person={'id':'10000000-0000-4000-8000-000000000001','name':'Synthetic owner','active':True,'access_role':'admin'}
        self.workflow={'case_id':self.b.case['id'],'gates_enforced':True,'attributes_applied':True,'can_assign':True,'stages':{key:{'owner':person,'owner_eligible':True,'can_execute':True,'can_approve':True,'updated_at':None} for key in ('data_owner','data_preparation','logistics_assignment','logistics_scheduling')}}
        original=self.b.hydrated
        self.b.hydrated=lambda:{**original(),'case':{**original()['case'],'label':'SEMANA 43','category':'weekly','attributes_applied_at':'2026-10-22T00:00:00Z'},'workflow_responsibilities':copy.deepcopy(self.workflow)}
        self.b.workflows[self.b.case['id']]=self.workflow

    async def asyncTearDown(self):await self.b.asyncTearDown()

    async def test_both_terminal_runs_offer_one_same_case_same_decision_configuration_cta(self):
        original_runs=copy.deepcopy(self.b.runs);original_case=copy.deepcopy(self.b.case)
        for node,kind in [('logistics_assignment','assignment'),('logistics_scheduling','scheduling')]:
            self.b.runs=copy.deepcopy(original_runs);self.b.case=copy.deepcopy(original_case)
            run=self.b.runs[self.b.f['ids'][kind]];run.update(status='error',result_json=None,error_message='Error sintético de validación')
            self.b.case['nodes'][node].update(status='error',approved_run_id=None,run_id=run['id'],latest_run_id=run['id'])
            if node=='logistics_scheduling':self.b.case['nodes']['logistics_assignment'].update(status='approved',approved_run_id=self.b.f['ids']['assignment'])
            await self.page.goto(f'http://127.0.0.1:{self.b.port}/app?view=decision-dashboard&case_id={self.b.case["id"]}&node_id={node}&run_id={run["id"]}')
            error=self.page.locator('[data-run-terminal-error]');await error.wait_for()
            self.assertEqual(await error.get_by_role('button').count(),1)
            await error.get_by_role('button',name='Volver a configuración',exact=True).click()
            await self.page.locator('[data-config-review]' if kind=='assignment' else '[data-scheduling-review]').wait_for()
            query=parse_qs(urlparse(self.page.url).query)
            self.assertEqual(query['case_id'],[self.b.case['id']]);self.assertEqual(query['node_id'],[node]);self.assertNotIn('run_id',query)
        self.assertEqual(self.b.execution_bodies,[])

    async def test_missing_owner_blocks_map_configuration_and_direct_configuration_entry(self):
        self.workflow['stages']['logistics_scheduling'].update(owner=None,owner_eligible=False)
        self.b.case['nodes']['logistics_scheduling'].update(status='available',run_id=None,latest_run_id=None,run_count=0)
        await self.b.open('logistics-map')
        card=self.page.locator('#dispatch-map-root article[data-decision-node=logistics_scheduling]')
        self.assertTrue(await card.locator('[data-map-action=configure]').is_disabled())
        self.assertIn('Decision Owner',await card.inner_text());self.assertIn('Sin asignar',await card.inner_text())
        self.assertEqual(await card.locator('[data-responsibility-field=approver]').count(),0)
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app?view=logistics-config&case_id={self.b.case["id"]}&node_id=logistics_scheduling')
        await self.page.locator('[data-map-node=logistics_assignment]').first.wait_for()
        self.assertEqual(await self.page.evaluate('window.dationGetCurrentView()'),'logistics-map')
        self.assertEqual(self.b.execution_bodies,[])
