"""Final polish acceptance checks against real assets and isolated API fixtures."""
import unittest
import test_saga3_ui as saga3

WIDTHS = ((1440,900),(1280,800),(1024,768),(768,1024),(375,812),(320,640))

class FinalPolishTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls): saga3.Saga3UITests.setUpClass()
    @classmethod
    def tearDownClass(cls): saga3.Saga3UITests.tearDownClass()
    async def asyncSetUp(self):
        self.fixture=saga3.Saga3UITests();await self.fixture.asyncSetUp()
        self.b,self.page=self.fixture.b,self.fixture.page
        await self.page.emulate_media(reduced_motion='reduce')
    async def asyncTearDown(self): await self.fixture.asyncTearDown()

    async def test_c4_metadata_has_independent_unpadded_decision_label(self):
        for width,height in WIDTHS:
            await self.page.set_viewport_size({'width':width,'height':height})
            for kind,index in [('assignment',1),('scheduling',2)]:
                await self.b.open('logistics-config','logistics_'+kind)
                meta=self.page.locator('.d-hero-meta')
                self.assertEqual(await meta.locator('.d-hero-meta__step').inner_text(),'PASO 3 · CONFIGURAR DECISIÓN')
                self.assertEqual(await meta.locator('.d-hero-meta__decision').inner_text(),f'DECISIÓN {index} DE 3')
                self.assertTrue(await meta.evaluate('''e=>{
                    const a=e.firstElementChild.getBoundingClientRect(),b=e.lastElementChild.getBoundingClientRect();
                    return (b.left>=a.right+10||b.top>=a.bottom+6)&&b.right<=innerWidth;
                }'''), (kind,width))

    async def test_c5_command_bars_remain_visible_without_obscuring_controls(self):
        for width,height in WIDTHS:
            await self.page.set_viewport_size({'width':width,'height':height})
            for view,node in [('logistics-data',None),('logistics-config','logistics_assignment'),('logistics-config','logistics_scheduling')]:
                await self.b.open(view,node)
                bar=self.page.locator('.view.is-active .d-workflow-action-bar')
                await bar.wait_for()
                self.assertEqual(await bar.evaluate('e=>getComputedStyle(e).position'),'fixed')
                self.assertTrue(await bar.evaluate('e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&r.bottom<=innerHeight&&r.top>=0}'),(view,node,width))
                self.assertTrue(await bar.evaluate('e=>e.closest(".main").getBoundingClientRect().bottom<=e.getBoundingClientRect().top-12'),(view,node,width,'reserved command zone'))
                controls=self.page.locator('.view.is-active input:visible:not([type=file]),.view.is-active textarea:visible,.view.is-active select:visible')
                for field in [controls.first,controls.last]:
                    if not await field.count() or await field.is_disabled():continue
                    await field.focus();await self.page.wait_for_timeout(80)
                    self.assertTrue(await field.evaluate('''e=>{
                        const r=e.getBoundingClientRect();return [.1,.5,.9].every(x=>[.1,.5,.9].every(y=>e.contains(document.elementFromPoint(r.x+r.width*x,r.y+r.height*y))));
                    }'''),(view,node,width,await field.get_attribute('name')))
                self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        self.assertEqual(self.b.execution_bodies,[])

    async def test_c1_overview_hero_has_local_art_process_and_unchanged_actions(self):
        for width,height in WIDTHS:
            await self.page.set_viewport_size({'width':width,'height':height})
            await self.page.goto(f'http://127.0.0.1:{self.b.port}/app/ddas/logistics')
            hero=self.page.locator('.dda-landing__hero');await hero.wait_for()
            self.assertEqual(await hero.locator('.dda-landing__emblem').count(),0)
            self.assertEqual(await hero.locator('h1>span').inner_text(),'con mejor análisis.')
            self.assertEqual(await hero.locator('.dda-landing__flow-node small').all_inner_texts(),['ENTRADA','INTELIGENCIA','DECISIÓN'])
            self.assertEqual(await hero.get_by_role('button').count(),2)
            self.assertTrue(await hero.get_by_role('button',name='Iniciar nuevo Decision Case',exact=False).is_visible())
            self.assertTrue(await hero.get_by_role('button',name='Ver mis casos de Logística',exact=False).is_visible())
            if width>700:
                await self.page.wait_for_function('document.querySelector(".dda-landing__hero-art")?.naturalWidth>0')
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))

    async def test_c2_demo_tracks_actual_pack_provenance_across_case_surfaces(self):
        for sample in (False,True):
            for dataset in self.b.f['datasets'].values():dataset['is_sample']=sample
            for view,node,run in [('logistics-data',None,None),('logistics-map',None,None),('logistics-config','logistics_assignment',None),('decision-dashboard','logistics_assignment',self.b.f['ids']['assignment'])]:
                await self.b.open(view,node,run)
                await self.page.locator('.view.is-active h1:visible').first.wait_for()
                await self.page.wait_for_function('window.DationDispatch.getWorkspace().caseContext?.caseId===window.DationDispatch.getWorkspace().decisionCase?.id')
                self.assertEqual(await self.page.locator('[data-demo-context]').is_visible(),sample,(sample,view))
                self.assertEqual(await self.page.locator('[data-demo-context]').inner_text(),'Modo demo · Estás trabajando con datos de ejemplo.')
        self.assertEqual(self.b.execution_bodies,[])

    async def test_c3_contextual_launcher_sheet_busy_and_keyboard_preserve_chat(self):
        for kind in ('assignment','scheduling'):
            run=self.b.f['ids'][kind]
            await self.b.open('decision-dashboard','logistics_'+kind,run)
            launcher=self.page.locator('.view.is-active [data-chat]')
            for width,height in WIDTHS:
                await self.page.set_viewport_size({'width':width,'height':height})
                await launcher.click()
                panel=self.page.locator('.dispatch-chat:not([hidden])')
                self.assertIn(run[:8],await panel.locator('.dispatch-chat-context').inner_text())
                self.assertTrue(await panel.evaluate('e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight}'),(kind,width))
                if width<=700:
                    self.assertEqual(await panel.get_attribute('aria-modal'),'true')
                    await panel.locator('button[type=submit]').focus();await self.page.keyboard.press('Tab')
                    self.assertTrue(await panel.locator('[data-close]').evaluate('e=>e===document.activeElement'))
                await self.page.keyboard.press('Escape')
                self.assertTrue(await launcher.evaluate('e=>e===document.activeElement'))
                self.assertEqual(await launcher.get_attribute('aria-expanded'),'false')
            await self.page.set_viewport_size({'width':375,'height':812})
            self.b.delay[f'/api/runs/{run}/chat']=.5
            await launcher.click()
            await self.page.locator('.dispatch-chat textarea').fill('¿Qué debo revisar?')
            await self.page.locator('.dispatch-chat button[type=submit]').click()
            await self.page.get_by_text('Analizando…',exact=True).wait_for()
            await self.page.get_by_text('Synthetic answer',exact=True).wait_for()
            self.assertEqual(await launcher.inner_text(),'Dation IA')
            await self.page.keyboard.press('Escape')
        self.assertEqual(self.b.execution_bodies,[])
