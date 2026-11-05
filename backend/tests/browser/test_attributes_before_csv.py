"""Saga 01 readiness: context and owners precede operational file upload."""
import unittest
from urllib.parse import urlparse
from playwright.async_api import expect
import test_saga01_planning as saga
import test_ultimate_case_setup as setup
import test_ultimate_case_data as data


class AttributesBeforeCSVTests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(data.UltimateCaseDataTests.setUpClass.__func__)
    tearDownClass=classmethod(setup.UltimateCaseSetupTests.tearDownClass.__func__)
    asyncSetUp=setup.UltimateCaseSetupTests.asyncSetUp
    asyncTearDown=setup.UltimateCaseSetupTests.asyncTearDown
    login=setup.UltimateCaseSetupTests.login
    request=setup.UltimateCaseSetupTests.request
    api=setup.UltimateCaseSetupTests.api
    model=setup.UltimateCaseSetupTests.model
    case=setup.UltimateCaseSetupTests.case
    open=setup.UltimateCaseSetupTests.open
    fill_case=saga.Saga01PlanningTests.fill_case
    create=saga.Saga01PlanningTests.create
    template=data.UltimateCaseDataTests.template
    attach=data.UltimateCaseDataTests.attach
    store_ui=data.UltimateCaseDataTests.store_ui
    publish_ui=data.UltimateCaseDataTests.publish_ui

    async def new_form(self):
        await self.open('/app/ddas/logistics/case')
        if await self.page.get_by_label('Logistics Model',exact=True).count():
            await self.page.get_by_role('button',name='Crear nuevo Logistics Model',exact=True).click()
        await expect(self.page.get_by_role('button',name='Crear Decision Case',exact=True)).to_be_enabled(timeout=30000)
        self.writes=[]
        self.page.on('request',lambda r:self.writes.append(r.post_data_json) if r.method=='POST' and urlparse(r.url).path in ('/api/platform/logistics-models','/api/platform/logistics-cases') else None)
        return self.page.locator('.ultimate-foundation form')

    async def test_1_context_is_validated_before_creation_without_operational_files(self):
        form=await self.new_form()
        await self.page.get_by_role('button',name='Crear Decision Case',exact=True).click()
        await expect(form.locator('.ultimate-errors')).to_be_visible()
        await self.page.get_by_label('Nombre del Model',exact=True).fill('Preparación antes de datos')
        await self.fill_case('SEMANA 43')
        await self.page.get_by_label('Descripción (opcional)',exact=True).fill('Contexto antes de los archivos.')
        self.assertEqual(await self.page.locator('input[type=file]').count(),0)
        self.assertEqual(await self.page.get_by_label('Decision Owner inicial (D1 y D2)',exact=True).input_value(),setup.ADMIN)
        self.assertEqual(self.writes,[])
        self.assertIsNone(await self.page.evaluate('window.DationDispatch.getWorkspace().decisionCase'))
        cid=await self.create();context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context')
        self.assertEqual(context['case']['label'],'SEMANA 43');self.assertEqual(context['entry_count'],0)
        self.assertEqual(len(self.writes),2)

    async def test_2_draft_context_and_owner_survive_reload_without_creating_objects(self):
        await self.new_form()
        await self.page.get_by_label('Nombre del Model',exact=True).fill('Borrador antes de datos')
        await self.fill_case('SEMANA 44')
        await self.page.get_by_label('Descripción (opcional)',exact=True).fill('Preparado antes de los CSV.')
        await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for()
        self.assertEqual(await self.page.get_by_label('Nombre del Model',exact=True).input_value(),'Borrador antes de datos')
        self.assertEqual(await self.page.get_by_label('Nombre del Case',exact=True).input_value(),'SEMANA 44')
        self.assertEqual(await self.page.get_by_label('Descripción (opcional)',exact=True).input_value(),'Preparado antes de los CSV.')
        self.assertEqual(await self.page.get_by_label('Decision Owner inicial (D1 y D2)',exact=True).input_value(),setup.ADMIN)
        self.assertEqual(self.writes,[]);self.assertEqual(await self.page.locator('input[type=file]').count(),0)
        await self.page.get_by_label('Decision Owner inicial (D1 y D2)',exact=True).select_option('')
        await self.page.get_by_role('button',name='Crear Decision Case',exact=True).click()
        await expect(self.page.locator('.ultimate-errors')).to_be_visible();self.assertEqual(self.writes,[])

    async def test_3_created_case_without_csv_keeps_d1_data_required_and_d2_locked(self):
        _,_,case=await self.case();cid=case['case']['id']
        await self.page.goto(self.base+'/app/ddas/logistics/decisions?case_id='+cid)
        await self.page.locator('[data-graph-ready=true]').wait_for()
        await expect(self.page.locator('[data-graph-node=logistics_assignment]')).to_have_attribute('data-node-state','DATA_REQUIRED')
        await expect(self.page.locator('[data-graph-node=logistics_scheduling]')).to_have_attribute('data-node-state','LOCKED')
        context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context')
        self.assertEqual(context['entry_count'],0);self.assertEqual(context['case']['id'],cid)
        self.assertEqual(await self.page.locator('input[type=file]').count(),0)
        self.assertEqual(await self.page.get_by_role('button',name='Ejecutar decisión',exact=True).count(),0)

    async def test_4_adding_csv_keeps_the_previously_created_case_and_model_version(self):
        _,_,case=await self.case();cid=case['case']['id']
        before=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context')
        await self.api('PUT','/api/platform/decisions/'+cid+'/responsibilities/data_owner',{'expected_updated_at':None,'owner_user_id':setup.ADMIN})
        writes=[];self.page.on('request',lambda r:writes.append(urlparse(r.url).path) if r.method=='POST' and urlparse(r.url).path in ('/api/platform/logistics-models','/api/platform/logistics-cases','/api/runs') else None)
        await self.page.goto(self.base+'/app/ddas/logistics/decisions?case_id='+cid)
        await self.page.locator('[data-graph-ready=true]').wait_for()
        await self.page.get_by_role('button',name='Cargar nuevos datos',exact=True).click()
        await self.page.locator('[data-ultimate-ready=true]').wait_for()
        for entity,version in [('transport_demand','2'),('transport_resources','3')]:
            await self.store_ui(cid,entity);await self.publish_ui()
            await self.page.locator('[data-pack-current-version="'+version+'"]').wait_for()
        await self.page.get_by_role('button',name='Volver al Decision Map',exact=True).click()
        await self.page.locator('[data-graph-ready=true]').wait_for()
        await expect(self.page.locator('[data-graph-node=logistics_assignment]')).to_have_attribute('data-node-state','READY')
        after=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context')
        for key in ('id','label','description','logistics_model_version_id','planning_start','planning_end','horizon_type','operating_mode'):
            self.assertEqual(after['case'][key],before['case'][key])
        self.assertEqual(after['planning_context']['case_policy'],before['planning_context']['case_policy'])
        self.assertEqual(after['model_version'],before['model_version'])
        self.assertEqual(after['entry_count'],2);self.assertEqual(writes,[])
