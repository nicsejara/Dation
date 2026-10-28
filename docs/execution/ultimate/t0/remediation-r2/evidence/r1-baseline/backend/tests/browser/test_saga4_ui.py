"""Focused Saga 4 browser flows using the existing synthetic navigation fixture."""
import copy
import json
import os
from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlparse
import test_saga3_ui as saga3

class Saga4UITests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):saga3.Saga3UITests.setUpClass()
    @classmethod
    def tearDownClass(cls):saga3.Saga3UITests.tearDownClass()
    async def asyncSetUp(self):
        self.fixture=saga3.Saga3UITests();await self.fixture.asyncSetUp()
        self.b=self.fixture.b;self.page=self.fixture.page;self.workflow=self.fixture.workflow
    async def asyncTearDown(self):await self.fixture.asyncTearDown()

    async def test_shared_case_context_and_compact_map_milestones(self):
        node='logistics_assignment';original=copy.deepcopy(self.b.case)
        await self.b.open('logistics-config',node)
        context=self.page.locator('#dispatch-config-root [data-config-context]')
        await context.wait_for();self.assertEqual(await context.locator('summary').inner_text(),'Contexto del Case\n⌄')
        await context.locator('summary').click();await self.page.wait_for_function("document.querySelector('#dispatch-config-root summary').title==='Cerrar contexto del Case'")
        config_fields=await context.locator('dt').all_text_contents()
        for active in ('logistics_assignment','logistics_scheduling'):
            self.b.case=copy.deepcopy(original)
            if active=='logistics_assignment':
                for key in ('logistics_assignment','logistics_scheduling'):self.b.case['nodes'][key].update(status='available' if key==active else 'locked',run_id=None,approved_run_id=None,latest_run_id=None,run_count=0)
            await self.b.open('logistics-map')
            context=self.page.locator('#dispatch-map-root [data-config-context]')
            await context.locator('summary').click()
            self.assertEqual(await context.locator('dt').all_text_contents(),config_fields)
            self.assertEqual(await context.locator('summary').inner_text(),'Contexto del Case\n⌄')
            progress=self.page.locator('#dispatch-map-root .dispatch-case-progress__grid')
            self.assertEqual(await progress.locator('li').count(),3)
            self.assertEqual(await progress.locator('[aria-disabled=true]').count(),1)
            self.assertEqual(await progress.locator('.is-reached').count(),1 if active=='logistics_assignment' else 2)
            self.assertEqual(await progress.locator('.is-reached').last.locator('.dispatch-case-progress__segment').inner_text(),'1' if active=='logistics_assignment' else '2')
        self.assertEqual(await self.page.locator('[aria-label="Reabrir análisis"]').count(),0)
        for width in (1440,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            for card in await self.page.locator('#dispatch-map-root article[data-decision-node]').all():
                buttons=card.locator('.dispatch-decision-node__tracebar button')
                if await buttons.count()==2:
                    a,b=await buttons.nth(0).bounding_box(),await buttons.nth(1).bounding_box()
                    self.assertLess(abs(a['width']-b['width']),1);self.assertLess(abs(a['height']-b['height']),1)
                result=card.locator('.dispatch-decision-node__actions button')
                if await result.count():self.assertEqual(await result.count(),1)
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            directory=os.getenv('DATION_SAGA4_ARTIFACTS')
            if directory:
                Path(directory).mkdir(parents=True,exist_ok=True);await self.page.screenshot(path=str(Path(directory)/f'map-{width}.png'),full_page=True)
        self.assertEqual(self.b.execution_bodies,[])

    async def test_execution_uses_real_stages_and_indeterminate_feedback_then_success_or_error(self):
        original_case=copy.deepcopy(self.b.case);original_runs=copy.deepcopy(self.b.runs)
        for node,kind in [('logistics_assignment','assignment'),('logistics_scheduling','scheduling')]:
            self.b.case=copy.deepcopy(original_case);self.b.runs=copy.deepcopy(original_runs)
            run=self.b.runs[self.b.f['ids'][kind]];completed=copy.deepcopy(run)
            self.b.case['nodes'][node].update(status='running',approved_run_id=None)
            run.update(status='running',result_json=None,approved_at=None,progress_json={'stage':'validating'})
            await self.page.goto(f'http://127.0.0.1:{self.b.port}/app?view=decision-dashboard&case_id={self.b.case["id"]}&node_id={node}&run_id={run["id"]}')
            status=self.page.locator('[data-run-stage]');await status.get_by_text('VALIDANDO DATOS Y CONFIGURACIÓN',exact=True).wait_for()
            bar=self.page.locator('[data-execution-progress] .decision-engine-flow')
            self.assertIsNone(await bar.get_attribute('aria-valuenow'));self.assertIsNone(await bar.get_attribute('aria-valuemax'))
            self.assertNotIn('%',await self.page.locator('[data-execution-progress]').inner_text())
            self.assertNotEqual(await bar.locator('[data-state=active] .decision-engine-flow__marker').evaluate('n=>getComputedStyle(n,"::after").animationName'),'none')
            run['progress_json']['stage']='optimizing:service'
            await status.get_by_text('EJECUTANDO MOTOR',exact=True).wait_for()
            directory=os.getenv('DATION_SAGA4_ARTIFACTS')
            if directory:await self.page.screenshot(path=str(Path(directory)/f'execution-{kind}.png'))
            if kind=='assignment':
                run.clear();run.update(completed);run['approved_at']=None;self.b.case['nodes'][node].update(status='review')
                await self.page.locator('.d-decision-dashboard').wait_for()
                self.assertEqual(await self.page.locator('[data-approve-toolbar]').count(),1)
            else:
                run.update(status='error',error_message='Error sintético del motor')
                await self.page.locator('[data-run-terminal-error]').wait_for()
                self.assertEqual(await self.page.locator('[data-run-terminal-error] button').count(),1)
            self.assertEqual(await self.page.locator('[data-execution-progress]').count(),0)
        self.assertEqual(self.b.execution_bodies,[])

    async def test_approval_hero_routes_by_next_owner_and_rerun_keeps_case_and_decision(self):
        original_case=copy.deepcopy(self.b.case);original_runs=copy.deepcopy(self.b.runs)
        for has_owner in (True,False):
            self.b.case=copy.deepcopy(original_case);self.b.runs=copy.deepcopy(original_runs)
            node='logistics_assignment';run=self.b.runs[self.b.f['ids']['assignment']]
            run['approved_at']=None;self.b.case['nodes'][node].update(status='review',approved_run_id=None)
            self.b.case['nodes']['logistics_scheduling'].update(status='locked',run_id=None,approved_run_id=None,latest_run_id=None,run_count=0)
            if not has_owner:self.workflow['stages']['logistics_scheduling'].update(owner=None,owner_eligible=False)
            await self.b.open('decision-dashboard',node,run['id'])
            self.assertEqual(await self.page.locator('[data-approve-toolbar]').count(),1)
            self.assertEqual(await self.page.locator('[data-approve-final],.assignment-final-actions,[data-dashboard-map],[data-approved-map]').count(),0)
            self.assertEqual(await self.page.locator('#dispatch-hero [data-approve-toolbar]').count(),1)
            self.assertEqual(await self.page.locator('[data-more-menu] button').all_text_contents(),['Detalles de ejecuciónMotor, solver, archivos y huella'])
            # The shared fixture predates canonical downstream unlocking on approval.
            self.b.case['nodes']['logistics_scheduling']['status']='available'
            await self.page.locator('[data-approve-toolbar]').click()
            next_cta=self.page.locator('#dispatch-hero [data-after-approve]');await next_cta.wait_for(state='visible')
            self.assertEqual(await self.page.locator('[data-approve-toolbar]').count(),0)
            self.assertEqual(await next_cta.inner_text(),'Configurar D2 · Planificación de despachos' if has_owner else 'Asignar Decision Owner · D2 Planificación de despachos')
            for width in (1440,390):
                await self.page.set_viewport_size({'width':width,'height':1000})
                rect=await next_cta.bounding_box();self.assertGreater(rect['height'],40);self.assertLessEqual(rect['x']+rect['width'],width)
                directory=os.getenv('DATION_SAGA4_ARTIFACTS')
                if directory:await self.page.screenshot(path=str(Path(directory)/f'hero-owner-{has_owner}-{width}.png'),full_page=True)
            await next_cta.click()
            await self.page.locator('[data-scheduling-review]' if has_owner else '#dispatch-map-root [data-map-node=logistics_scheduling]').first.wait_for()
            query=parse_qs(urlparse(self.page.url).query);self.assertEqual(query['case_id'],[self.b.case['id']])
            if has_owner:self.assertEqual(query['node_id'],['logistics_scheduling'])
            self.assertNotIn('run_id',query)
            if not has_owner:
                card=self.page.locator('#dispatch-map-root article[data-decision-node=logistics_scheduling]')
                self.assertTrue(await card.locator('[data-map-action=configure]').is_disabled())
                self.assertIn('is-attention',await card.get_attribute('class'))
                async def assign_owner(route):
                    body=route.request.post_data_json;self.assertNotIn('approver_user_id',body)
                    stage=self.workflow['stages']['logistics_scheduling'];stage.update(owner=copy.deepcopy(self.workflow['stages']['data_owner']['owner']),owner_eligible=True,updated_at='2026-10-22T00:00:00Z')
                    await route.fulfill(json=self.workflow)
                await self.b.context.route('**/api/platform/decisions/*/responsibilities/logistics_scheduling',assign_owner)
                await card.get_by_role('button',name='Seleccionar responsable',exact=True).click()
                select=card.locator('select');await select.locator('option[value="10000000-0000-4000-8000-000000000001"]').wait_for(state='attached')
                await select.select_option('10000000-0000-4000-8000-000000000001')
                await card.get_by_role('button',name='Guardar',exact=True).click()
                await self.page.wait_for_function("!document.querySelector('#dispatch-map-root article[data-decision-node=logistics_scheduling] [data-map-action=configure]').disabled")
                await card.locator('[data-map-action=configure]').click();await self.page.locator('[data-scheduling-review]').wait_for()
            await self.b.open('decision-dashboard',node,run['id'])
            await self.page.get_by_role('button',name='Nueva corrida',exact=True).click();await self.b.confirm_rerun();await self.page.locator('[data-config-review]').wait_for()
            query=parse_qs(urlparse(self.page.url).query);self.assertEqual(query['case_id'],[self.b.case['id']]);self.assertEqual(query['node_id'],[node]);self.assertNotIn('run_id',query)
        self.assertEqual(self.b.execution_bodies,[])

    async def test_last_decision_completes_case_and_technical_menu_keeps_exports(self):
        node='logistics_scheduling';run=self.b.runs[self.b.f['ids']['scheduling']]
        await self.b.open('decision-dashboard',node,run['id'])
        self.assertEqual(await self.page.locator('[data-approve-toolbar]').count(),1)
        self.assertEqual(await self.page.locator('[data-approve-final],.scheduling-final-actions').count(),0)
        await self.page.locator('[data-approve-toolbar]').click()
        await self.page.locator('#dispatch-hero').get_by_text('✓ DECISIÓN APROBADA · ✓ CASE COMPLETADO',exact=True).wait_for()
        self.assertEqual(await self.page.locator('[data-approve-toolbar],[data-dashboard-map],[data-approved-map]').count(),0)
        self.assertNotIn('Configurar D',await self.page.locator('#dispatch-hero').inner_text())
        await self.page.locator('[data-more-menu] summary').click()
        self.assertEqual(await self.page.locator('[data-more-menu] button').count(),1)
        await self.page.get_by_role('button',name='Detalles de ejecución').click()
        drawer=self.page.locator('[data-run-drawer]');self.assertTrue(await drawer.is_visible())
        self.assertIn(run['id'],await drawer.inner_text());self.assertEqual(await drawer.locator('dt').get_by_text('Run ID',exact=True).count(),1)
        await self.page.keyboard.press('Escape');self.assertFalse(await drawer.is_visible())
        for form in ('csv','json'):
            await self.page.locator('[data-export-menu] summary').click()
            async with self.page.expect_download() as pending:await self.page.locator('[data-export-'+form+']').click()
            download=await pending.value;self.assertTrue(download.suggested_filename.endswith('.'+form))
        await self.page.get_by_role('button',name='Nueva corrida',exact=True).click();await self.b.confirm_rerun();await self.page.locator('[data-scheduling-review]').wait_for()
        query=parse_qs(urlparse(self.page.url).query);self.assertEqual(query['node_id'],[node]);self.assertEqual(query['case_id'],[self.b.case['id']]);self.assertNotIn('run_id',query)
        self.assertEqual(self.b.execution_bodies,[])
