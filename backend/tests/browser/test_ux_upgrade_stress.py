"""break-ui regression fixtures; all API traffic is intercepted, no production access."""
import asyncio
import copy
import json
import os
from pathlib import Path
import unittest
from urllib.parse import urlsplit
import test_saga3_ui as saga3

FIXTURES = Path(__file__).parent / 'fixtures'
WORST = json.loads((FIXTURES / 'ux-upgrade-stress.json').read_text())


class UXStressTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls): saga3.Saga3UITests.setUpClass()
    @classmethod
    def tearDownClass(cls): saga3.Saga3UITests.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = saga3.Saga3UITests(); await self.fixture.asyncSetUp()
        self.b, self.page = self.fixture.b, self.fixture.page
        self.mode = 'demo'
        self.out = Path(os.getenv('DATION_UX_STRESS_ARTIFACTS', '/tmp/dation-ux-stress'))
        self.out.mkdir(exist_ok=True, parents=True)
        await self.page.expose_function('uxStressSetMode', self.mode_changed)
        await self.b.context.add_init_script((FIXTURES / 'ux-upgrade-stress-toggle.js').read_text())

    def mode_changed(self, mode):
        self.mode = mode
        self.b.center_label = WORST['case_label'] if mode == 'worst' else 'Jo' if mode == 'one' else None
        self.b.center_summary = dict(zip(('active_cases','in_review','pending_approval','approved'),
                                        [WORST['aggregate_count'],1284,0,1] if mode == 'worst' else [0,0,0,0] if mode == 'empty' else [1,0,0,0]))
        self.b.center_archived = mode == 'empty'

    async def asyncTearDown(self): await self.fixture.asyncTearDown()

    async def test_demo_worst_empty_one_toggle_preserves_readable_counts(self):
        await self.page.set_viewport_size({'width': 320, 'height': 640})
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app/decisions')
        for label, mode in [('Demo data','demo'),('Worst case','worst'),('Empty','empty'),('One','one')]:
            await self.page.get_by_role('button',name=label,exact=True).click()
            await self.page.wait_for_url('**ux_stress='+mode)
            await self.page.locator('.center-kpi').first.wait_for()
            await self.page.screenshot(path=str(self.out / (mode+'-320.png')),full_page=True)
            self.assertTrue(await self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            fits = await self.page.locator('.center-kpi__value').evaluate_all('''nodes=>nodes.every(e=>{
                const r=document.createRange();r.selectNodeContents(e);return r.getClientRects().length===1;
            })''')
            self.assertTrue(fits, mode)
            if mode == 'empty': self.assertTrue(await self.page.locator('.center-empty').is_visible())
        self.assertEqual(self.b.execution_bodies, [])

    async def test_multilingual_identity_and_large_paginated_team(self):
        async def identity(route):
            import time
            await route.fulfill(json={'access_token':'browser-layout-fixture','expires_at':int(time.time())+3600,
                'profile':{'id':'10000000-0000-4000-8000-000000000001','first_name':'👩🏽‍💻','last_name':'Priya','email':WORST['email']},
                'membership':{'workspace_id':self.b.workspace_settings['workspace']['id'],'access_role':'admin'},
                'workspace':{**self.b.workspace_settings['workspace'],'name':WORST['workspace_name']},'ddas':self.b.ddas})
        async def team(route):
            rows=[{'user_id':f'10000000-0000-4000-8000-{i+1:012d}','name':WORST['people'][i%len(WORST['people'])],
                   'email':WORST['email'] if i%3==0 else f'ops+regional-{i}@example.test','access_role':['admin','operator','viewer'][i%3],
                   'business_roles':[] if i%2 else ['data_owner','decision_owner'],'status':'active' if i%2 else 'disabled','updated_at':'2026-10-23T23:30:00-03:00'} for i in range(25)]
            await route.fulfill(json={'members':rows,'invitations':[],'total':1284,'invitation_total':0})
        await self.b.context.route('**/auth/session', identity)
        await self.b.context.route('**/api/platform/team?**', team)
        await self.b.context.route('**/auth/invitations',lambda r:r.fulfill(json={'items':[]}))
        for width in (320,375,1440):
            await self.page.set_viewport_size({'width':width,'height':900})
            await self.page.goto(f'http://127.0.0.1:{self.b.port}/app/team')
            await self.page.locator('.team-table').wait_for()
            await self.page.screenshot(path=str(self.out/f'team-worst-{width}.png'),full_page=True)
            self.assertTrue(await self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            self.assertEqual(await self.page.locator('.team-table tbody tr').count(),25)
            self.assertFalse(await self.page.locator('[data-user-avatar]').evaluate('e=>[...e.textContent].some(c=>{const n=c.codePointAt(0);return n>=0xd800&&n<=0xdfff})'))
            self.assertTrue(await self.page.get_by_role('button',name='Siguiente',exact=True).is_enabled())

    async def test_long_case_and_filenames_and_numeric_extremes(self):
        old = self.b.hydrated
        description = (WORST['description']*8)[:1000]
        self.b.hydrated = lambda: {**old(),'case':{**old()['case'],'label':WORST['case_label'],'description':description}}
        for row in self.b.hub_rows.values(): row['original_filename']=WORST['filename'];row['row_count']=1284
        for width in (320,1440):
            await self.page.set_viewport_size({'width':width,'height':900})
            await self.b.open('logistics-data')
            field = self.page.locator('[name=description]')
            await field.wait_for(state='visible')
            await self.page.wait_for_function("value=>document.querySelector('[name=description]')?.value===value",arg=description)
            self.assertEqual(len(await field.input_value()),1000)
            self.assertTrue(await self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            await self.page.screenshot(path=str(self.out/f'data-long-{width}.png'),full_page=True)
            await self.b.open('logistics-map')
            self.assertTrue(await self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            await self.page.screenshot(path=str(self.out/f'map-long-{width}.png'),full_page=True)
            await self.page.goto(f'http://127.0.0.1:{self.b.port}/app/data')
            await self.page.locator('.hub-table').wait_for()
            self.assertTrue(await self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        result=await self.page.evaluate('''async()=>{const {weight,money,num}=await import('/static/js/dispatch/shared.mjs');
            return [0,1,12345678.9,-42.5,.1+.2,null].map(v=>[weight(v),money(v),num(v,2)]);}''')
        self.assertNotIn('NaN',str(result));self.assertNotIn('undefined',str(result))
        self.assertEqual(result[0][0],'0 kg');self.assertEqual(result[-1][0],'—')

    async def test_route_change_during_loading_does_not_reopen_team(self):
        async def delayed(route):
            await asyncio.sleep(.4)
            try: await route.fulfill(json={'members':[],'invitations':[],'total':0,'invitation_total':0})
            except Exception: pass  # Request abort is the expected outcome after disposal.
        await self.b.context.route('**/api/platform/team?**', delayed)
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app/team')
        await self.page.locator('[data-platform-team] .d-loading').wait_for()
        await self.page.evaluate("window.dationNavigate('settings')")
        await self.page.locator('.workspace-settings__tabs').wait_for()
        await self.page.wait_for_timeout(500)
        self.assertEqual(await self.page.evaluate('window.dationGetCurrentView()'),'settings')
        self.assertEqual(await self.page.locator('dialog[open]').count(),0)
