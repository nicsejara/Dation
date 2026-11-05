"""Saga 01: real setup/API/SQL and reused Data Pack UI on an owned sandbox."""
import unittest
from uuid import uuid4
from pathlib import Path
from playwright.async_api import expect
import test_ultimate_case_setup as t3
import test_ultimate_case_data as t4


class Saga01PlanningTests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(t4.UltimateCaseDataTests.setUpClass.__func__)
    tearDownClass=classmethod(t3.UltimateCaseSetupTests.tearDownClass.__func__)
    asyncSetUp=t3.UltimateCaseSetupTests.asyncSetUp
    asyncTearDown=t3.UltimateCaseSetupTests.asyncTearDown
    login=t3.UltimateCaseSetupTests.login
    request=t3.UltimateCaseSetupTests.request
    api=t3.UltimateCaseSetupTests.api
    model=t3.UltimateCaseSetupTests.model
    case=t3.UltimateCaseSetupTests.case
    open=t3.UltimateCaseSetupTests.open
    template=t4.UltimateCaseDataTests.template
    attach=t4.UltimateCaseDataTests.attach
    store_ui=t4.UltimateCaseDataTests.store_ui
    publish_ui=t4.UltimateCaseDataTests.publish_ui
    upload_api=t4.UltimateCaseDataTests.upload_api

    async def fill_case(self,name='Planificación Saga 01'):
        await self.page.get_by_label('Nombre del Case',exact=True).fill(name)
        await self.page.get_by_label('Inicio de planificación',exact=True).fill('2026-11-02')
        await self.page.get_by_label('Inicio de planificación',exact=True).press('Tab')
        await self.page.get_by_label('Fin de planificación',exact=True).fill('2026-11-08')
        await self.page.get_by_label('Decision Owner inicial (D1 y D2)',exact=True).select_option(t3.ADMIN)

    async def create(self):
        await self.page.get_by_role('button',name='Crear Decision Case',exact=True).click()
        await self.page.locator('[data-graph-ready=true]').wait_for(timeout=30000)
        return await self.page.evaluate('new URL(location.href).searchParams.get("case_id")')

    async def test_01_first_time_landing_model_contract_case_graph(self):
        self.assertEqual((await self.api('GET','/api/platform/logistics-models'))['total'],0)
        await self.page.goto(self.base+'/app/ddas/logistics')
        await self.page.get_by_role('button',name='Comenzar',exact=False).click()
        await self.page.locator('[data-ultimate-ready=true]').wait_for()
        self.assertEqual(await self.page.get_by_label('Logistics Model',exact=True).count(),0)
        await self.page.get_by_label('Nombre del Model',exact=True).fill('Operación inicial')
        await self.fill_case()
        self.assertEqual(await self.page.locator('input[type=file]').count(),0)
        await expect(self.page.get_by_role('heading',name='Órdenes / Demanda · Requerido',exact=True)).to_be_visible()
        cid=await self.create();context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context')
        self.assertEqual(context['model']['name'],'Operación inicial');self.assertEqual(context['model_version']['version'],1);self.assertEqual(context['entry_count'],0)
        await expect(self.page.locator('[data-graph-node=logistics_assignment]')).to_have_attribute('data-node-state','DATA_REQUIRED')
        await expect(self.page.locator('[data-graph-node=logistics_scheduling]')).to_have_attribute('data-node-state','LOCKED')

    async def test_02_recurrent_version_is_not_mutated_and_contract_templates_match(self):
        m,v=await self.model();mid=m['model']['id'];before=await self.api('GET','/api/platform/logistics-models/'+mid)
        await self.open('/app/ddas/logistics/case?model_id='+mid)
        await expect(self.page.get_by_label('Model Version',exact=True)).to_have_value(v['version']['id'])
        self.assertTrue(await self.page.get_by_label('Operating Role',exact=True).is_disabled())
        async with self.page.expect_download() as event:await self.page.get_by_role('button',name='Descargar template de Órdenes / Demanda',exact=True).click()
        download=await event.value;self.assertTrue(download.suggested_filename.endswith('.csv'))
        await self.fill_case();cid=await self.create()
        after=await self.api('GET','/api/platform/logistics-models/'+mid);self.assertEqual(before,after)
        context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context');self.assertEqual(context['case']['logistics_model_version_id'],v['version']['id'])
        self.assertEqual(await self.template(cid,'transport_demand'),Path(await download.path()).read_bytes())

    async def test_03_new_model_with_existing_models_and_required_validation(self):
        await self.model();await self.open('/app/ddas/logistics/case')
        await self.page.get_by_role('button',name='Crear nuevo Logistics Model',exact=True).click()
        await expect(self.page.get_by_role('button',name='Crear Decision Case',exact=True)).to_be_enabled()
        await self.page.get_by_role('button',name='Crear Decision Case',exact=True).click()
        await expect(self.page.locator('.ultimate-errors')).to_be_visible()
        await self.page.get_by_label('Nombre del Model',exact=True).fill('Otra operación '+str(uuid4())[:8]);await self.fill_case();cid=await self.create()
        context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context');self.assertTrue(context['model']['name'].startswith('Otra operación'))

    async def test_04_failed_case_creation_recovers_without_duplicate_model_or_version(self):
        await self.model()
        await self.open('/app/ddas/logistics/case');await self.page.get_by_role('button',name='Crear nuevo Logistics Model',exact=True).click()
        name='Intento recuperable '+str(uuid4())[:8]
        await self.page.get_by_label('Nombre del Model',exact=True).fill(name);await self.fill_case()
        async def fail(route):await route.fulfill(status=503,json={'detail':'Fallo sintético al guardar Case'})
        await self.page.route('**/api/platform/logistics-cases',fail)
        await self.page.get_by_role('button',name='Crear Decision Case',exact=True).click()
        await self.page.get_by_text('Crear Decision Case: Fallo sintético al guardar Case',exact=True).wait_for()
        self.assertNotIn('/decisions',self.page.url)
        await self.page.unroute('**/api/platform/logistics-cases',fail)
        self.page.on('dialog',lambda dialog:dialog.accept());await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for()
        cid=await self.create();models=await self.api('GET','/api/platform/logistics-models?q='+name)
        self.assertEqual(models['total'],1);self.assertEqual(len(models['items'][0]['versions']),1)
        context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context');self.assertEqual(context['model']['id'],models['items'][0]['id'])

    async def test_05_graph_data_upload_reuse_and_existing_case_navigation(self):
        _,_,c=await self.case();cid=c['case']['id']
        await self.page.goto(self.base+'/app/ddas/logistics/decisions?case_id='+cid);await self.page.locator('[data-graph-ready=true]').wait_for()
        await self.page.get_by_role('button',name='Cargar nuevos datos',exact=True).click();await self.page.locator('[data-ultimate-ready=true]').wait_for()
        self.assertEqual(await self.page.locator('input[type=file]').count(),2)
        await self.store_ui(cid);await self.publish_ui();await self.page.locator('[data-pack-current-version="2"]').wait_for()
        await self.page.get_by_role('button',name='Volver al Decision Map',exact=True).click();await self.page.locator('[data-graph-ready=true]').wait_for()
        await self.page.get_by_role('button',name='Reutilizar inputs compatibles',exact=True).click();await self.page.locator('[data-ultimate-ready=true]').wait_for()
        slot=self.page.locator('[data-t4-slot=transport_demand]');await slot.get_by_role('button',name='Reutilizar anterior',exact=False).click();await slot.get_by_role('button',name='Seleccionar input compatible',exact=True).first.click()
        self.assertTrue(await self.page.get_by_role('button',name='Publicar versión del Pack',exact=True).is_enabled())
        await self.page.go_back();await self.page.locator('[data-graph-ready=true]').wait_for();await self.page.go_forward();await self.page.locator('[data-ultimate-ready=true]').wait_for()
        await self.page.goto(self.base+'/app/ddas/logistics/decisions?case_id='+cid);await self.page.locator('[data-graph-ready=true]').wait_for();self.assertEqual(await self.page.get_by_role('heading',name='Planificación inicial',exact=True).count(),0)

    async def test_06_mobile_contract_preview_race_and_legacy_entry(self):
        await self.model()
        await self.page.set_viewport_size({'width':390,'height':844});await self.open('/app/ddas/logistics/data')
        self.assertIn('/case',self.page.url);await self.page.get_by_role('button',name='Crear nuevo Logistics Model',exact=True).click()
        await self.page.get_by_role('checkbox',name='Peso (kg)',exact=True).check()
        await expect(self.page.get_by_role('cell',name='demand_weight_kg',exact=True)).to_be_visible()
        await self.page.get_by_role('checkbox',name='Peso (kg)',exact=True).uncheck()
        await expect(self.page.get_by_role('cell',name='demand_weight_kg',exact=True)).to_have_count(0)
        self.assertLessEqual(await self.page.evaluate('document.documentElement.scrollWidth'),391)
        self.assertEqual(await self.page.locator('input[type=file]').count(),0)

    async def test_07_contract_failure_blocks_setup_and_can_be_retried(self):
        await self.model()
        async def unavailable(route):await route.fulfill(status=503,json={'detail':'Contrato temporalmente no disponible'})
        await self.page.route('**/api/platform/logistics-models/contract-preview',unavailable)
        await self.open('/app/ddas/logistics/case')
        self.assertTrue(await self.page.get_by_role('button',name='Crear Decision Case',exact=True).is_disabled())
        self.assertTrue(await self.page.get_by_label('Nombre del Case',exact=True).is_disabled())
        await self.page.get_by_text('Contrato temporalmente no disponible',exact=True).wait_for()
        await self.page.unroute('**/api/platform/logistics-models/contract-preview',unavailable)
        await self.page.get_by_role('button',name='Reintentar Data Contract',exact=True).click()
        await expect(self.page.get_by_role('button',name='Crear Decision Case',exact=True)).to_be_enabled()
        self.assertEqual(await self.page.locator('input[type=file]').count(),0)

    async def test_08_new_planning_from_data_hub_also_starts_with_context(self):
        await self.model();await self.open('/app/ddas/logistics/case')
        await self.page.evaluate("window.DationDispatch.reuseHubData([{id:'10000000-0000-4000-8000-000000000099',dataset_type:'orders'}])")
        await self.page.locator('[data-ultimate-ready=true]').wait_for()
        self.assertIn('/case',self.page.url)
        self.assertEqual(await self.page.locator('input[type=file]').count(),0)
