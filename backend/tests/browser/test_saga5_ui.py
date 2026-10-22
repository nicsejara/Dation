"""Saga 5: joint form/readiness, shared disclosure/CTA and result typography."""
import copy
import os
from pathlib import Path
import unittest
import test_saga3_ui as saga3

class Saga5UITests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):saga3.Saga3UITests.setUpClass()
    @classmethod
    def tearDownClass(cls):saga3.Saga3UITests.tearDownClass()
    async def asyncSetUp(self):
        self.fixture=saga3.Saga3UITests();await self.fixture.asyncSetUp()
        self.b=self.fixture.b;self.page=self.fixture.page;self.workflow=self.fixture.workflow
        await self.page.emulate_media(reduced_motion='reduce')
    async def asyncTearDown(self):await self.fixture.asyncTearDown()

    async def capture(self,name):
        if directory:=os.getenv('DATION_SAGA5_ARTIFACTS'):
            Path(directory).mkdir(parents=True,exist_ok=True);await self.page.screenshot(path=str(Path(directory)/f'{name}.png'),full_page=True)

    async def test_one_attributes_apply_saves_owner_and_keeps_four_independent_checks(self):
        self.workflow['stages']['data_owner'].update(owner=None,owner_eligible=False,updated_at=None)
        identity={'label':'SEMANA 43','category':'weekly','description':None,'attributes_applied_at':'2026-10-22T00:00:00Z'}
        original=self.b.hydrated;self.b.hydrated=lambda:{**original(),'case':{**original()['case'],**identity}}
        submissions=[]
        async def apply(route):
            body=route.request.post_data_json;submissions.append(body)
            identity.update({key:body[key] for key in ('label','category','description')})
            stage=self.workflow['stages']['data_owner'];uid=body.get('data_owner_user_id')
            if 'data_owner_user_id' in body:stage.update(owner={'id':uid,'name':'Synthetic owner','access_role':'admin'} if uid else None,owner_eligible=bool(uid),updated_at='2026-10-22T01:00:00Z')
            await route.fulfill(json={'id':self.b.case['id'],'workflow_responsibilities':self.workflow})
        await self.b.context.route('**/api/platform/decisions/*/attributes',apply)
        await self.b.open('logistics-data');form=self.page.locator('[data-case-identity]');select=form.get_by_label('Data Owner',exact=True)
        await select.locator('option[value="10000000-0000-4000-8000-000000000001"]').wait_for(state='attached')
        self.assertEqual(await self.page.locator('[data-workflow-responsibility=data_owner]').count(),1)
        self.assertEqual(await form.locator('[data-workflow-responsibility=data_owner]').count(),1)
        self.assertEqual(await form.get_by_role('button',name='Guardar',exact=True).count(),0)
        self.assertEqual(await self.page.locator('.dispatch-pro-hero-file-chips,.dispatch-pro-hero-visual').count(),0)
        self.assertEqual(await self.page.locator('#dispatch-data-root .d-page-hero').get_by_text('Vas a cargar',exact=True).count(),0)
        bar=self.page.locator('#dispatch-data-root .d-workflow-action-bar');next_button=bar.get_by_role('button',name='Seleccioná tu decisión',exact=True)
        self.assertTrue(await next_button.is_disabled())
        await form.get_by_label('Nombre del Case',exact=True).fill('SEMANA 44');await form.get_by_label('Descripción (opcional)',exact=True).fill('Datos verificados.')
        await select.select_option('10000000-0000-4000-8000-000000000001')
        self.assertTrue(await next_button.is_disabled());self.assertEqual(submissions,[])
        await form.get_by_role('button',name='Aplicar',exact=True).click()
        await form.locator('[data-case-identity-feedback]').get_by_text('Atributos y Data Owner aplicados.',exact=True).wait_for()
        self.assertEqual(len(submissions),1);self.assertEqual(submissions[0]['label'],'SEMANA 44');self.assertEqual(submissions[0]['description'],'Datos verificados.');self.assertEqual(submissions[0]['data_owner_user_id'],'10000000-0000-4000-8000-000000000001')
        self.assertEqual(await bar.locator('.d-workflow-action-bar__item').count(),4)
        await self.page.wait_for_function("!document.querySelector('#dispatch-data-root .d-workflow-action-bar button').disabled")
        await self.capture('attributes-1440')
        # A new selection has not been applied; persisted ownership alone is insufficient.
        select=form.get_by_label('Data Owner',exact=True);await select.locator('option[value=""]').wait_for(state='attached');await select.select_option('')
        self.assertTrue(await next_button.is_disabled());self.assertEqual(len(submissions),1)
        await self.page.set_viewport_size({'width':390,'height':1000});await self.capture('attributes-390')
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        self.assertFalse(any(method=='PUT' and '/responsibilities/' in path for method,path in self.b.requests))

    async def test_map_and_config_keep_the_same_rounded_hover_and_error_cta_is_primary(self):
        styles=[]
        for view in ('logistics-map','logistics-config'):
            await self.b.open(view,'logistics_assignment' if view=='logistics-config' else None)
            context=self.page.locator(('#dispatch-map-root' if view=='logistics-map' else '#dispatch-config-root')+' [data-config-context]')
            summary=context.locator('summary');before=await summary.bounding_box();await summary.hover()
            result=await summary.evaluate('(n)=>({radius:getComputedStyle(n).borderTopLeftRadius,background:getComputedStyle(n).backgroundColor,parentRadius:getComputedStyle(n.parentElement).borderTopLeftRadius})')
            self.assertEqual(result['radius'],result['parentRadius']);self.assertNotEqual(result['radius'],'0px');after=await summary.bounding_box();self.assertLess(abs(before['width']-after['width']),1);self.assertLess(abs(before['height']-after['height']),1);styles.append(result)
            await summary.focus();self.assertNotEqual(await summary.evaluate('n=>getComputedStyle(n).outlineStyle'),'none')
            await self.capture(view+'-hover')
        self.assertEqual(styles[0],styles[1])
        for node,kind in [('logistics_assignment','assignment'),('logistics_scheduling','scheduling')]:
            run=self.b.runs[self.b.f['ids'][kind]];run.update(status='error',result_json=None,error_message='Causa real conservada');self.b.case['nodes'][node].update(status='error',approved_run_id=None)
            await self.page.goto(f'http://127.0.0.1:{self.b.port}/app?view=decision-dashboard&case_id={self.b.case["id"]}&node_id={node}&run_id={run["id"]}')
            error=self.page.locator('[data-run-terminal-error]');await error.wait_for();button=error.get_by_role('button',name='Volver a configuración',exact=True)
            self.assertEqual(await error.get_by_role('button').count(),1);self.assertIn('Causa real conservada',await error.inner_text())
            self.assertIn('d-button--primary',await button.get_attribute('class'))
            self.assertNotEqual(await button.evaluate('n=>getComputedStyle(n).borderColor'),await button.evaluate('n=>getComputedStyle(n).getPropertyValue("--color-danger-border").trim()'))
        self.assertEqual(await self.page.locator('.sidebar .asset-item small').count(),0)
        self.assertEqual(await self.page.locator('.sidebar .asset-item strong').inner_text(),'DDA Logística')

    async def test_d1_and_d2_share_result_geometry_highlights_and_support_without_clipping(self):
        measurements=[]
        for node,kind in [('logistics_assignment','assignment'),('logistics_scheduling','scheduling')]:
            await self.b.open('decision-dashboard',node,self.b.f['ids'][kind])
            headline=self.page.locator('#dispatch-hero .decision-result-summary__headline');support=self.page.locator('#dispatch-hero .decision-result-summary__support')
            self.assertGreaterEqual(await headline.locator('strong').count(),2);self.assertEqual(await support.count(),1)
            measurements.append(await headline.evaluate('n=>{const s=getComputedStyle(n);return {font:s.fontSize,weight:s.fontWeight,line:s.lineHeight,max:s.maxWidth,margin:s.margin,overflow:s.overflow,clamp:s.webkitLineClamp}}'))
            self.assertNotEqual(measurements[-1]['weight'],await headline.locator('strong').first.evaluate('n=>getComputedStyle(n).fontWeight'))
            for width in (1440,1024,390):
                await self.page.set_viewport_size({'width':width,'height':1000})
                await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
                self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                self.assertEqual(await headline.evaluate('n=>n.scrollHeight<=n.clientHeight+1'),True)
                rect=await headline.bounding_box();self.assertLessEqual(rect['x']+rect['width'],width)
                if width==1440:self.assertLessEqual(await headline.evaluate('n=>n.getBoundingClientRect().height/parseFloat(getComputedStyle(n).lineHeight)'),3.05)
                await self.capture(kind+'-'+str(width))
            await self.page.set_viewport_size({'width':1440,'height':1000})
        self.assertEqual(measurements[0],measurements[1])
        self.assertEqual(self.b.execution_bodies,[])

    async def test_failed_apply_preserves_drafts_and_viewer_has_no_save_or_owner_editor(self):
        submissions=[]
        async def conflict(route):
            submissions.append(route.request.post_data_json);await route.fulfill(status=409,json={'detail':'El recurso cambió.'})
        await self.b.context.route('**/api/platform/decisions/*/attributes',conflict)
        await self.b.open('logistics-data');form=self.page.locator('[data-case-identity]');await form.get_by_role('button',name='Aplicar',exact=True).wait_for()
        await form.get_by_label('Nombre del Case',exact=True).fill('Cambios pendientes')
        await form.get_by_role('button',name='Aplicar',exact=True).click()
        feedback=form.locator('[data-case-identity-feedback]');await feedback.get_by_text('El Case o su Data Owner cambió. Recargá la página, revisá los cambios y volvé a aplicar.',exact=True).wait_for()
        self.assertEqual(await form.get_by_label('Nombre del Case',exact=True).input_value(),'Cambios pendientes')
        self.assertEqual(len(submissions),1);self.assertFalse(await form.get_by_role('button',name='Aplicar',exact=True).is_disabled())
        self.assertTrue(await self.page.locator('#dispatch-data-root .d-workflow-action-bar button').is_disabled())
        self.b.access_role='viewer';self.workflow['can_assign']=False
        await self.page.reload();await form.get_by_role('button',name='Aplicar',exact=True).wait_for()
        self.assertTrue(await form.get_by_role('button',name='Aplicar',exact=True).is_disabled())
        self.assertTrue(await form.get_by_label('Nombre del Case',exact=True).is_disabled())
        self.assertEqual(await form.locator('[data-workflow-responsibility=data_owner] select').count(),0)
        self.assertEqual(len(submissions),1)
