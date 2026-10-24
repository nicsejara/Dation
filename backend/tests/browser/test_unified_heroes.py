"""Scoped visual acceptance against real assets and isolated API fixtures."""
import os
import unittest
from pathlib import Path
from urllib.parse import urlsplit
import test_saga3_ui as fixture

WIDTHS=((1440,900),(1280,800),(1024,768),(768,1024),(375,812),(320,640))

class UnifiedHeroTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):fixture.Saga3UITests.setUpClass()
    @classmethod
    def tearDownClass(cls):fixture.Saga3UITests.tearDownClass()
    async def asyncSetUp(self):
        self.f=fixture.Saga3UITests();await self.f.asyncSetUp()
        self.b,self.page=self.f.b,self.f.page
        await self.page.emulate_media(reduced_motion='reduce')
    async def asyncTearDown(self):await self.f.asyncTearDown()

    async def test_shared_icons_have_transparent_edges_and_row_owns_all_sidebar_states(self):
        for width,height in WIDTHS:
            await self.page.set_viewport_size({'width':width,'height':height})
            await self.page.goto(f'http://127.0.0.1:{self.b.port}/app')
            card=self.page.locator('[data-dda-id=logistics]');await card.wait_for()
            row=self.page.locator('.sidebar .asset-item[data-view=logistics-overview]')
            source=await row.locator('img').get_attribute('src')
            self.assertEqual(urlsplit(source).path,urlsplit(await card.locator('img').get_attribute('src')).path)
            pixels=await row.evaluate('''async (e)=>{
                const image=e.querySelector('img');await image.decode();
                const canvas=document.createElement('canvas');canvas.width=canvas.height=25;
                const c=canvas.getContext('2d');c.drawImage(image,0,0,25,25);
                const alpha=(x,y)=>c.getImageData(x,y,1,1).data[3];
                return {corners:[[0,0],[24,0],[0,24],[24,24]].map(([x,y])=>alpha(x,y)),painted:[...c.getImageData(0,0,25,25).data].filter((v,i)=>i%4===3&&v>0).length};
            }''')
            self.assertEqual(pixels['corners'],[0,0,0,0]);self.assertGreater(pixels['painted'],50)
            async def check(state):
                for item in (row.locator('.asset-icon'),row.locator('img')):
                    self.assertEqual(await item.evaluate('e=>getComputedStyle(e).backgroundColor'),'rgba(0, 0, 0, 0)',(width,state))
                    self.assertEqual(await item.evaluate('e=>getComputedStyle(e).boxShadow'),'none',(width,state))
                self.assertEqual(await row.locator('.asset-icon').evaluate('e=>getComputedStyle(e).borderTopWidth'),'0px')
                target=os.getenv('DATION_VISUAL_QA_ROOT')
                if target and width in (1440,375):
                    p=Path(target);p.mkdir(parents=True,exist_ok=True)
                    await row.screenshot(path=str(p/f'sidebar-{width}-{state}.png'))
            await check('default');await row.hover();await check('hover')
            await self.page.mouse.down();await check('pressed');await self.page.mouse.up()
            await self.page.wait_for_function("window.dationGetCurrentView()==='logistics-overview'")
            self.assertIn('is-active',await row.get_attribute('class'));await check('active')
            await row.focus();await self.page.keyboard.press('Shift+Tab');await self.page.keyboard.press('Tab')
            self.assertTrue(await row.evaluate('e=>e===document.activeElement'))
            self.assertEqual(await row.evaluate('e=>getComputedStyle(e).outlineStyle'),'solid');await check('focus')
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        self.assertEqual(self.b.execution_bodies,[]);self.assertEqual(self.b.errors,[])

    async def test_dashboard_art_stays_clear_of_result_copy_and_mobile_controls(self):
        for kind in ('assignment','scheduling'):
            await self.b.open('decision-dashboard','logistics_'+kind,self.b.f['ids'][kind])
            hero=self.page.locator('#dispatch-hero')
            for width,height in WIDTHS:
                await self.page.set_viewport_size({'width':width,'height':height})
                metrics=await hero.evaluate('''(e,kind)=>{
                    const r=e.getBoundingClientRect(),copy=e.querySelector(kind==='assignment'?'.assignment-hero__content':'[data-scheduling-hero]').getBoundingClientRect();
                    const art=e.querySelector('.dashboard-hero__media'),a=art.getBoundingClientRect();
                    return {visible:getComputedStyle(art).display!=='none',left:a.left,right:a.right,top:a.top,copyBottom:copy.bottom,copyRight:copy.right,heroRight:r.right};
                }''',kind)
                self.assertTrue(metrics['visible'],(kind,width))
                if width>900:
                    self.assertGreaterEqual(metrics['left'],metrics['copyRight'],(kind,width,metrics))
                    self.assertLess(metrics['right'],metrics['heroRight'],(kind,width,metrics))
                else:self.assertGreaterEqual(metrics['top'],metrics['copyBottom'],(kind,width,metrics))
                self.assertTrue(await hero.locator('[data-rerun]').is_visible())
                self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        self.assertEqual(self.b.execution_bodies,[]);self.assertEqual(self.b.errors,[])

    async def test_overview_actions_keep_filtered_center_and_prepare_a_new_case_without_execution(self):
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app')
        await self.page.locator('[data-dda-id=logistics]').get_by_role('button',name='Abrir DDA Logística').click()
        await self.page.locator('[data-open-decision-map]:not([disabled])').click()
        await self.page.wait_for_function("window.dationGetCurrentView()==='platform-decisions'")
        self.assertEqual(await self.page.evaluate("new URL(location.href).searchParams.get('center_dda')"),'logistics')
        await self.page.locator('.sidebar .asset-item[data-view=logistics-overview]').click()
        await self.page.locator('[data-start-new-decision]').click()
        await self.page.locator('[data-kind=orders] input[type=file]').wait_for(state='attached')
        self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().decisionCase'),None)
        self.assertNotIn('case_id=',self.page.url)
        self.assertFalse(any(m=='POST' and p in ('/api/runs','/api/decision-cases') for m,p in self.b.requests))
        self.assertEqual(self.b.execution_bodies,[]);self.assertEqual(self.b.errors,[])
