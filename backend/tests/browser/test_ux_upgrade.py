"""Product-level UX regressions, using the existing isolated API fixtures."""
import unittest
import copy
import json
from pathlib import Path
import test_saga3_ui as saga3


class UXUpgradeTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        saga3.Saga3UITests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        saga3.Saga3UITests.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = saga3.Saga3UITests()
        await self.fixture.asyncSetUp()
        self.b, self.page = self.fixture.b, self.fixture.page
        await self.page.emulate_media(reduced_motion='reduce')

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def test_focused_attributes_are_unobscured_at_every_breakpoint(self):
        for width, height in [(375, 812), (768, 1024), (1024, 768), (1440, 900)]:
            await self.page.set_viewport_size({'width': width, 'height': height})
            await self.b.open('logistics-data')
            for name in ('label', 'category', 'description'):
                field = self.page.locator(f'[name="{name}"]')
                await field.focus()
                await self.page.wait_for_timeout(450)
                visible = await field.evaluate('''e => {
                    const r=e.getBoundingClientRect();
                    return [.1,.5,.9].every(dx=>[.1,.5,.9].every(dy=>{
                        const hit=document.elementFromPoint(r.x+r.width*dx,r.y+r.height*dy);
                        return hit&&(hit===e||e.contains(hit));
                    }));
                }''')
                self.assertTrue(visible, (width, height, name))
            await self.page.locator('[name=label]').focus()
            await self.page.keyboard.press('Tab')
            self.assertEqual(await self.page.evaluate('document.activeElement.name'), 'category')
        self.assertEqual(self.b.execution_bodies, [])

    async def test_dashboard_launcher_and_exports_preserve_persisted_evidence(self):
        before = copy.deepcopy(self.b.runs)
        for kind in ('assignment', 'scheduling'):
            run_id = self.b.f['ids'][kind]
            await self.b.open('decision-dashboard', 'logistics_' + kind, run_id)
            for width, height in [(1440, 900), (1024, 768), (768, 1024), (375, 812)]:
                await self.page.set_viewport_size({'width': width, 'height': height})
                launcher = self.page.locator('.view.is-active [data-chat]')
                self.assertEqual(await launcher.count(), 1)
                self.assertTrue(await launcher.evaluate('e=>e.closest("[data-dashboard-toolbar]")!==null'))
                self.assertEqual(await launcher.evaluate('e=>getComputedStyle(e).position'), 'static')
                await launcher.click()
                await self.page.locator('.view.is-active .dispatch-chat:not([hidden])').wait_for()
                await self.page.keyboard.press('Escape')
                self.assertTrue(await launcher.evaluate('e=>e===document.activeElement'))
            await self.page.locator('[data-export-menu] summary').click()
            async with self.page.expect_download() as output:
                await self.page.locator('[data-export-json]').click()
            download = await output.value
            self.assertEqual(json.loads(Path(await download.path()).read_text()), before[run_id]['result_json'])
        self.assertEqual(self.b.runs, before)
        self.assertEqual(self.b.execution_bodies, [])

    async def test_human_approval_stays_run_specific_and_duplicate_clicks_are_guarded(self):
        self.b.review_assignment()
        run_id = self.b.f['ids']['assignment']
        self.b.delay[f'/api/runs/{run_id}/approve'] = .3
        await self.b.open('decision-dashboard', 'logistics_assignment', run_id)
        self.assertEqual(self.b.approval_calls, 0)
        button = self.page.locator('[data-approve-toolbar]')
        await button.click()
        await button.dispatch_event('click')
        await self.page.wait_for_function("document.querySelector('[data-status-badge]').textContent==='Aprobada'")
        self.assertEqual(self.b.approval_calls, 1)
        self.assertEqual(self.b.case['nodes']['logistics_assignment']['approved_run_id'], run_id)

    async def test_skip_and_keyboard_navigation_do_not_follow_workspace_updates(self):
        await self.b.open('logistics-map')
        skip = self.page.get_by_role('link', name='Saltar al contenido principal')
        await skip.focus()
        await self.page.keyboard.press('Enter')
        self.assertEqual(await self.page.evaluate('document.activeElement.id'), 'main-content')
        link = self.page.locator('.platform-global-nav [data-platform-view="platform-data"]')
        await link.focus()
        await self.page.keyboard.press('Enter')
        await self.page.wait_for_function('document.activeElement.id==="main-content"')
        await self.page.locator('.platform-global-nav [data-platform-view="platform-team"]').focus()
        await self.page.evaluate('window.dispatchEvent(new CustomEvent("dation:workspace"))')
        self.assertEqual(await self.page.evaluate('document.activeElement.dataset.platformView'), 'platform-team')

    async def test_current_case_flow_step_is_visible_on_entry_and_resize(self):
        for view, node in [('logistics-map', None), ('logistics-config', 'logistics_assignment'),
                           ('decision-dashboard', 'logistics_scheduling')]:
            await self.page.set_viewport_size({'width': 1440, 'height': 900})
            await self.b.open(view, node=node, run=self.b.f['ids']['scheduling'] if view == 'decision-dashboard' else None)
            for width, height in [(375, 812), (768, 1024), (1024, 768)]:
                await self.page.set_viewport_size({'width': width, 'height': height})
                await self.page.wait_for_timeout(100)
                self.assertTrue(await self.page.locator('#dda-workspace-nav').evaluate('''root=>{
                    const current=root.querySelector('[aria-current="step"]');
                    const r=current.getBoundingClientRect(), p=root.getBoundingClientRect();
                    return r.left>=p.left-1&&r.right<=p.right+1;
                }'''), (view, width))
        self.assertEqual(self.b.execution_bodies, [])

