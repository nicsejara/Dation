"""Product-level UX regressions, using the existing isolated API fixtures."""
import unittest
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

