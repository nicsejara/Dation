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
