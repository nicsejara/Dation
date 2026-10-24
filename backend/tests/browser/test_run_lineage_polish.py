"""Final controls, dashboard media and contextual reruns using isolated API fixtures."""
import unittest
from pathlib import Path
from playwright.async_api import expect
import test_saga3_ui as fixture

WIDTHS=((1440,900),(1024,768),(768,1024),(375,812),(320,640))

class RunLineagePolishTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):fixture.Saga3UITests.setUpClass()
    @classmethod
    def tearDownClass(cls):fixture.Saga3UITests.tearDownClass()
    async def asyncSetUp(self):
        self.f=fixture.Saga3UITests();await self.f.asyncSetUp();self.b,self.page=self.f.b,self.f.page
        await self.page.emulate_media(reduced_motion='reduce')
    async def asyncTearDown(self):await self.f.asyncTearDown()

    async def test_f2_owners_share_native_select_geometry_and_interaction_states(self):
        style='''e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return {height:r.height,padding:s.padding,border:s.border,background:s.backgroundColor,radius:s.borderRadius,font:s.fontFamily,size:s.fontSize,weight:s.fontWeight,line:s.lineHeight,appearance:s.appearance,outline:s.outline}}'''
        for w,h in WIDTHS:
            await self.page.set_viewport_size({'width':w,'height':h});observations=[]
            for data in (True,False):
                await self.b.open('logistics-data' if data else 'logistics-map')
                await self.page.wait_for_load_state('networkidle')
                if data:select=self.page.locator('[data-case-identity] [data-workflow-responsibility] select')
                else:
                    owner=self.page.locator('[data-workflow-responsibility=logistics_assignment]')
                    await owner.get_by_role('button',name='Cambiar',exact=True).click();select=owner.locator('select')
                    await self.page.wait_for_load_state('networkidle')
                await select.locator('option[value="10000000-0000-4000-8000-000000000001"]').wait_for(state='attached')
                await expect(select).to_be_enabled()
                self.assertFalse(await select.is_disabled());self.assertEqual(await select.input_value(),'10000000-0000-4000-8000-000000000001')
                states={}
                await self.page.mouse.move(0,0);await select.evaluate('e=>e.blur()');states['default']=await select.evaluate(style)
                await select.hover();states['hover']=await select.evaluate(style)
                await self.page.mouse.move(0,0);await select.focus();states['focus']=await select.evaluate(style)
                await select.evaluate('e=>{e.blur();e.disabled=true}');states['disabled']=await select.evaluate(style)
                self.assertGreater(states['default']['height'],40)
                self.assertNotEqual(states['default']['border'],states['hover']['border'])
                self.assertIn('solid',states['focus']['outline']);observations.append(states)
            self.assertEqual(observations[0],observations[1],w)
        self.assertEqual(self.b.execution_bodies,[])

    async def test_f3_case_flow_keeps_steps_without_decorative_truck(self):
        await self.b.open('logistics-map');panel=self.page.locator('.dispatch-map-premium__hero .dispatch-pro-hero-visual')
        await panel.locator('summary').click()
        self.assertEqual(await panel.locator('img').count(),0)
        self.assertEqual(await panel.locator('.dispatch-pro-how-node small').all_inner_texts(),['1 · ELEGÍ','2 · CONFIGURÁ','3 · APROBÁ'])
        for w,h in WIDTHS:
            await self.page.set_viewport_size({'width':w,'height':h})
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))

    async def test_f4_warning_has_equal_canonical_actions_keyboard_and_cleanup(self):
        await self.b.open('decision-dashboard','logistics_assignment',self.b.f['ids']['assignment'])
        for w,h in WIDTHS:
            await self.page.set_viewport_size({'width':w,'height':h});trigger=self.page.locator('[data-rerun]');await trigger.focus()
            await self.page.evaluate('''async()=>{window.__warningResult=null;const {confirmNewRun}=await import('/static/js/dispatch/runs/new-run-warning.mjs');confirmNewRun(document.querySelector('#dispatch-hero')).then(v=>window.__warningResult=v)}''')
            dialog=self.page.locator('[data-new-run-warning][open]');await dialog.wait_for()
            cancel=dialog.get_by_role('button',name='Cancelar',exact=True);confirm=dialog.get_by_role('button',name='Confirmar nueva corrida',exact=True)
            self.assertTrue(await cancel.evaluate('e=>e===document.activeElement'))
            buttons=await dialog.locator('button').evaluate_all('''nodes=>nodes.map(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {width:r.width,height:r.height,padding:s.padding,radius:s.borderRadius,font:s.font}})''')
            self.assertEqual(buttons[0],buttons[1],w);self.assertGreaterEqual(buttons[0]['height'],44)
            self.assertTrue(await confirm.evaluate('e=>e.classList.contains("d-button--primary")'))
            await confirm.focus();await self.page.keyboard.press('Tab');self.assertTrue(await cancel.evaluate('e=>e===document.activeElement'))
            await self.page.keyboard.press('Escape');await dialog.wait_for(state='detached')
            self.assertFalse(await self.page.evaluate('window.__warningResult'));self.assertTrue(await trigger.evaluate('e=>e===document.activeElement'))
        self.assertEqual(self.b.execution_bodies,[]);self.assertEqual(self.b.errors,[])

    async def test_f5_shared_media_slot_is_stable_when_narrative_grows(self):
        for w,h in WIDTHS:
            await self.page.set_viewport_size({'width':w,'height':h});snapshots=[]
            for kind in ('assignment','scheduling'):
                await self.b.open('decision-dashboard','logistics_'+kind,self.b.f['ids'][kind])
                hero=self.page.locator('#dispatch-hero');await self.page.evaluate('document.fonts.ready')
                measure='''e=>{const r=e.getBoundingClientRect(),m=e.querySelector('.dashboard-hero__media').getBoundingClientRect(),i=e.querySelector('.dashboard-hero__media img'),s=getComputedStyle(e),v=getComputedStyle(i);return {x:m.x-r.x,y:m.y-r.y,width:m.width,height:m.height,padding:s.padding,minHeight:s.minHeight,fit:v.objectFit,position:v.objectPosition,maxWidth:getComputedStyle(i.parentElement).maxWidth,font:getComputedStyle(e.querySelector('h1')).fontSize}}'''
                baseline=await hero.evaluate(measure);snapshots.append(baseline)
                self.assertTrue(await hero.locator('.dashboard-hero__media img').is_visible())
                self.assertEqual(await hero.locator('.dashboard-hero__media').get_attribute('aria-hidden'),'true')
                for text in ('48 viajes con recursos aprobados.','Ejecutar 48 viajes entre las fechas aprobadas y conservar todos los recursos y cargas del plan.',' '.join(['El resultado publicado conserva recursos, cargas, evidencia y trazabilidad de esta corrida.']*5)):
                    await hero.locator('.decision-result-summary__headline').evaluate('(e,text)=>e.textContent=text',text)
                    actual=await hero.evaluate(measure)
                    for key in ('width','height','x','fit','position','maxWidth','font'):self.assertEqual(actual[key],baseline[key],(kind,w,key))
                    if w>900:self.assertEqual(actual['y'],baseline['y'],(kind,w))
                    self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            for key in ('width','height','x'):
                self.assertAlmostEqual(snapshots[0][key],snapshots[1][key],delta=.5,msg=(w,key))
            if w>900:self.assertAlmostEqual(snapshots[0]['y'],snapshots[1]['y'],delta=.5)
            for key in ('padding','minHeight','fit','position','maxWidth','font'):self.assertEqual(snapshots[0][key],snapshots[1][key],(w,key))
