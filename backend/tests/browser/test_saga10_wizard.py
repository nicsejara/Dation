"""Saga10 actual five-card UI and cross-file validation, no engines enabled."""
import asyncio,json,unittest
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
from playwright.async_api import expect
import test_journey_navigation_ux06 as nav
import test_unified_decision_journey as journey
import test_ultimate_case_setup as setup
from wizard_helpers import publish_model,select_model

OUT=Path('/tmp/dation-saga10-browser');OUT.mkdir(exist_ok=True)
class Saga10WizardTests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(nav.JourneyNavigationTests.setUpClass.__func__)
    tearDownClass=classmethod(nav.JourneyNavigationTests.tearDownClass.__func__)
    sql=nav.JourneyNavigationTests.sql
    login=nav.JourneyNavigationTests.login
    request=nav.JourneyNavigationTests.request
    api=nav.JourneyNavigationTests.api
    ready=nav.JourneyNavigationTests.ready
    attach=journey.UnifiedDecisionJourneyTests.attach
    template=journey.UnifiedDecisionJourneyTests.template
    async def asyncSetUp(self):
        await setup.UltimateCaseSetupTests.asyncSetUp(self)
        self.sql('UPDATE dation_private.platform_release SET saga10_schema_enabled=true,saga10_ui_enabled=true,saga10_optimization_enabled=false;')
        self.operations=[];self.responses=[];self.page.on('request',lambda r:self.operations.append((r.method,r.url)));self.page.on('response',lambda r:self.responses.append((r.status,r.url)));self.page.on('requestfailed',lambda r:self.responses.append((r.failure,r.url)))
    async def asyncTearDown(self):
        (OUT/(self._testMethodName+'-network.json')).write_text(json.dumps({'requests':self.operations,'responses':self.responses},indent=2))
        await self.page.screenshot(path=str(OUT/(self._testMethodName+'-last.png')),full_page=True,animations='disabled')
        self.sql('UPDATE dation_private.platform_release SET saga10_ui_enabled=false;')
        await journey.UnifiedDecisionJourneyTests.asyncTearDown(self)
        self.assertFalse(any(m=='POST' and '/api/runs' in p for m,p in self.operations))
    async def sizes(self,scene):
        geometry=[]
        for width in [1536,1024,768,390,320]:
            await self.page.set_viewport_size({'width':width,'height':960 if width>390 else 844})
            await self.page.evaluate('document.fonts.ready');await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
            data=await self.page.evaluate('''()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,controls:[...document.querySelectorAll('.model-wizard-v2 input,.model-wizard-v2 select,.model-wizard-v2 button')].filter(n=>n.getClientRects().length).map(n=>({name:n.name||n.textContent,left:n.getBoundingClientRect().left,right:n.getBoundingClientRect().right}))})''')
            self.assertLessEqual(data['scroll'],data['client'],data)
            self.assertTrue(all(n['left']>=0 and n['right']<=data['client']+1 for n in data['controls']),data)
            audit=await self.page.evaluate((Path(__file__).parent/'theme_audit.js').read_text());self.assertEqual(audit['failures'],[],audit['failures'])
            if width in [1536,390]:
                await self.page.mouse.move(0,0);await self.page.evaluate('document.activeElement?.blur();scrollTo(0,0)');await self.page.screenshot(path=str(OUT/(scene+'-'+str(width)+'.png')),full_page=True,animations='disabled')
            geometry.append(data)
        (OUT/(scene+'-geometry.json')).write_text(json.dumps(geometry,indent=2))
        await self.page.set_viewport_size({'width':1536,'height':960})
    async def test_01_real_catalog_editor_physics_publish_and_responsive(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        wizard=self.page.locator('[data-dation-test=model-wizard-v2]');await expect(wizard.locator('.model-v2-block')).to_have_count(5)
        await expect(wizard.locator('[data-dation-test=model-version]')).to_have_count(0)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Distribución de bebidas 2.0')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_enabled()
        summary=wizard.locator('.model-v2-block').nth(2).locator('>summary');await summary.focus();await self.page.keyboard.press('Enter')
        await self.page.get_by_label('Modo de ingreso',exact=True).select_option('catalog')
        await expect(wizard.locator('.cargo-group').nth(0).locator('.cargo-entry')).to_have_count(1)
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        product=wizard.locator('.cargo-group').nth(0).locator('.cargo-entry')
        await product.get_by_label('Nombre del producto *',exact=True).fill('Jugo de naranja');await product.get_by_label('Unidad del producto *',exact=True).fill('caja')
        await product.get_by_label('Unidades por bulto *',exact=True).fill('12')
        mass=product.locator('details').filter(has=self.page.get_by_text('Peso bruto por bulto (opcional)',exact=True));await mass.locator('summary').click();await mass.get_by_label('Valor',exact=True).fill('12')
        await wizard.get_by_role('button',name='Agregar unidad logística',exact=True).click()
        unit=wizard.locator('.cargo-group').nth(1).locator('.cargo-entry');await unit.get_by_label('Nombre de la unidad *',exact=True).fill('Pallet estándar compartido')
        tare=unit.locator('details').filter(has=self.page.get_by_text('Tara explícita',exact=True));await tare.locator('summary').click();await tare.get_by_label('Valor',exact=True).fill('25')
        await wizard.get_by_role('button',name='Agregar presentación',exact=True).click()
        presentation=wizard.locator('.cargo-group').nth(2).locator('.cargo-entry');await presentation.get_by_label('Nombre de la presentación *',exact=True).fill('Pallet de jugo · 80 cajas')
        select=presentation.get_by_label('Unidad logística compartida',exact=True);key=await select.locator('option').nth(1).get_attribute('value');await select.select_option(key)
        await presentation.get_by_label('Bultos por presentación *',exact=True).fill('80')
        dimensions=presentation.locator('details').filter(has=self.page.get_by_text('Dimensiones exteriores cargadas',exact=True));await dimensions.locator('summary').click()
        for label,value in [('Largo','120'),('Ancho','100'),('Alto','180')]:await dimensions.get_by_label(label,exact=True).fill(value)
        for value in ['weight_kg','volume_m3','units']:await wizard.locator('[name=dimensions][value='+value+']').check()
        await wizard.get_by_label('Compatibilidad de carga',exact=True).select_option('UNIFORM_DECLARED');await wizard.get_by_label('Fraccionamiento',exact=True).select_option('DISCRETE')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_enabled()
        preview=wizard.locator('[data-dation-test=cargo-physical-preview]');await expect(preview).to_contain_text('985');await expect(preview).to_contain_text('2.16');await expect(preview).to_contain_text('960')
        await expect(unit.get_by_role('button',name='Eliminar',exact=True)).to_be_disabled();await expect(product.get_by_role('button',name='Eliminar',exact=True)).to_be_disabled()
        # A product may have several presentations, and one presentation may
        # contain several products; the shared unit keeps the same stable ID.
        await wizard.get_by_role('button',name='Agregar otro producto',exact=True).click()
        second=wizard.locator('.cargo-group').nth(0).locator('.cargo-entry').nth(1)
        await second.get_by_label('Nombre del producto *',exact=True).fill('Agua mineral');await second.get_by_label('Unidad del producto *',exact=True).fill('caja');await second.get_by_label('Unidades por bulto *',exact=True).fill('12')
        mass=second.locator('details').filter(has=self.page.get_by_text('Peso bruto por bulto (opcional)',exact=True));await mass.locator('summary').click();await mass.get_by_label('Valor',exact=True).fill('15')
        await presentation.get_by_role('button',name='Agregar componente para presentación mixta',exact=True).click()
        component=presentation.locator('.cargo-composition > .ultimate-grid').nth(1);choose=component.get_by_label('Producto *',exact=True)
        await choose.select_option(await choose.locator('option').nth(2).get_attribute('value'));await component.get_by_label('Bultos por presentación *',exact=True).fill('20')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_enabled();await expect(preview).to_contain_text('1285');await expect(preview).to_contain_text('1200')
        await wizard.get_by_role('button',name='Agregar presentación',exact=True).click()
        second_presentation=wizard.locator('.cargo-group').nth(2).locator('.cargo-entry').nth(1)
        await second_presentation.get_by_label('Nombre de la presentación *',exact=True).fill('Pallet de jugo · 40 cajas')
        await second_presentation.get_by_label('Unidad logística compartida',exact=True).select_option(key);await second_presentation.get_by_label('Bultos por presentación *',exact=True).fill('40')
        loaded=second_presentation.locator('details').filter(has=self.page.get_by_text('Dimensiones exteriores cargadas',exact=True));await loaded.locator('summary').click()
        for label,value in [('Largo','120'),('Ancho','100'),('Alto','100')]:await loaded.get_by_label(label,exact=True).fill(value)
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_enabled();await expect(preview).to_contain_text('505')
        await self.page.evaluate("document.querySelectorAll('.model-v2-block').forEach(n=>n.open=true)")
        await self.sizes('five-card-catalog')
        await self.page.evaluate("document.querySelectorAll('.model-v2-block').forEach((n,i)=>n.open=i===0)")
        await self.sizes('five-card-overview')
        async with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/versions')) as response:await publish_model(self.page)
        published=await (await response.value).json();self.assertEqual(published['version']['config_jsonb']['version'],2)
        self.assertEqual(len(published['version']['config_jsonb']['cargo']['products']),2)
        self.assertEqual(len(published['version']['config_jsonb']['cargo']['logistic_units']),1)
        self.assertEqual(len(published['version']['config_jsonb']['cargo']['presentations']),2)
        await self.ready(2);await expect(self.page.locator('[data-dation-test=contract-cards]>.data-contract-card')).to_have_count(3)
        await self.sizes('three-file-contract')
        self.assertEqual(self.sql('SELECT saga10_optimization_enabled FROM dation_private.platform_release;'),'f')

    async def v2_model(self):
        cfg=deepcopy(setup.CONFIG);cfg.update(version=2,split_permitted=True,homogeneous_loads_declared=True,consolidation_permitted=True,resource_categories=[],active_dimensions=['pallets','weight_kg','volume_m3'])
        cfg['cargo']={'input_mode':'catalog','profile':'PALLETIZED','split_policy':'DISCRETE','compatibility_policy':'UNIFORM_DECLARED',
            'products':[{'product_id':'JUICE','name':'Jugo','unit_label':'caja','units_per_package':12,'gross_mass':{'value':'12','unit':'kg'}}],
            'logistic_units':[{'logistic_unit_id':'STD','label':'Pallet compartido','type':'PALLET','tare_mass':{'value':'25','unit':'kg'}}],
            'presentations':[{'presentation_id':'PAL-JUICE','label':'Pallet de jugo','logistic_unit_id':'STD','components':[{'product_id':'JUICE','quantity':'80'}],'loaded_dimensions':{'length':'120','width':'100','height':'180','unit':'cm'}}]}
        m=await self.api('POST','/api/platform/logistics-models',{'id':str(uuid4()),'name':'Sesión catálogo 2.0','configuration':cfg})
        v=await self.api('POST','/api/platform/logistics-models/'+m['model']['id']+'/versions',{'version_id':str(uuid4()),'expected_revision':1});return m,v
    async def upload(self,entity,raw=None):
        if raw is None:
            response=await self.request('POST','/api/platform/logistics-models/contract-preview/templates/'+entity,{'model_id':self.m['model']['id'],'version_id':self.v['version']['id']});self.assertTrue(response.ok,await response.text());raw=await response.body()
        host=self.page.locator('[data-preparation-entity='+entity+']');await host.locator('input[type=file]').set_input_files({'name':entity+'.csv','mimeType':'text/csv','buffer':raw})
        save=host.get_by_role('button',name='Guardar candidato de '+{'transport_demand':'Órdenes / Demanda','order_lines':'Líneas de órdenes','transport_resources':'Flota / Recursos'}[entity],exact=True)
        await expect(save).to_be_enabled();await save.click();await expect(host).to_contain_text('Candidato guardado · no publicado')
    async def select_v2(self):
        self.m,self.v=await self.v2_model();await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await self.page.get_by_role('button',name='Seleccionar modelo existente',exact=True).click();dialog=self.page.get_by_role('dialog');await dialog.get_by_label('Logistics Model',exact=True).select_option(self.m['model']['id'])
        await expect(dialog.get_by_label('Model Version',exact=True)).to_be_hidden();await expect(dialog.get_by_role('button',name='Seleccionar esta versión',exact=True)).to_be_enabled();await dialog.get_by_role('button',name='Seleccionar esta versión',exact=True).click();await self.ready(2)
        await expect(self.page.locator('[data-preparation-entity]')).to_have_count(3)
    async def test_02_three_csv_cross_file_error_repair_reload_and_case(self):
        before=int(self.sql('SELECT count(*) FROM decision_cases;'))
        await self.select_v2();await self.upload('transport_demand');await self.upload('transport_resources')
        self.assertEqual(int(self.sql('SELECT count(*) FROM decision_cases;')),before)
        await expect(self.page.locator('[data-journey-next]')).to_be_disabled()
        raw=b'order_id,presentation_id,quantity\nUNKNOWN,PAL-JUICE,1\n';await self.upload('order_lines',raw)
        await expect(self.page.locator('.journey-preparation-status')).to_contain_text('orden ausente')
        await expect(self.page.locator('[data-journey-next]')).to_be_disabled()
        await expect(self.page.get_by_role('button',name='Revalidar relaciones entre archivos',exact=True)).to_be_visible()
        await self.upload('order_lines');await expect(self.page.locator('[data-journey-next]')).to_be_enabled()
        await expect(self.page.locator('.journey-step-context:visible')).to_contain_text('3 archivos validados')
        await self.page.reload();await self.ready(2)
        await expect(self.page.locator('[data-journey-next]')).to_be_enabled();await self.sizes('three-csv-validated')
        await self.page.get_by_label('Data Owner',exact=True).select_option(setup.ADMIN)
        await expect(self.page.locator('[data-journey-next]')).to_be_enabled();await self.page.locator('[data-journey-next]').click();await self.ready(3)
        await journey.UnifiedDecisionJourneyTests.fill_case(self,'Case con líneas físicas')
        await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click();await self.page.locator('[data-ux05-ready=true]').wait_for()
        cases=json.loads(self.sql("SELECT jsonb_agg(id) FROM decision_cases WHERE logistics_model_version_id='"+self.v['version']['id']+"';"));self.assertEqual(len(cases),1)
        self.assertEqual(int(self.sql('SELECT count(*) FROM decision_cases;')),before+1)
        state=await self.api('GET','/api/platform/logistics-cases/'+cases[0]+'/data');self.assertEqual(len(state['entries']),3)
        await self.page.get_by_role('button',name='Editar datos de origen',exact=True).click();await self.ready(2)
        await expect(self.page.locator('[data-t4-slot=order_lines]')).to_be_visible()
        self.assertEqual(self.sql('SELECT saga10_optimization_enabled FROM dation_private.platform_release;'),'f')

    async def test_03_direct_mode_has_no_dummy_catalog_and_conditional_costs(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1);wizard=self.page.locator('[data-dation-test=model-wizard-v2]')
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Directo sin catálogo')
        await self.page.evaluate("document.querySelectorAll('.model-v2-block').forEach(n=>n.open=true)")
        await wizard.get_by_label('Modo de ingreso',exact=True).select_option('catalog')
        await expect(wizard.locator('.cargo-group').nth(0).locator('.cargo-entry')).to_have_count(1)
        await wizard.get_by_role('button',name='Agregar otro producto',exact=True).click();await expect(wizard.locator('.cargo-group').nth(0).locator('.cargo-entry')).to_have_count(2)
        await wizard.get_by_label('Modo de ingreso',exact=True).select_option('direct');await expect(wizard.locator('.model-v2-catalogue')).to_be_hidden()
        await wizard.locator('[name=sources][value=EXTERNAL]').uncheck();await expect(wizard.locator('[name=external_costs][value=PER_KM]')).to_be_hidden()
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_enabled()
        async with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/versions')) as response:await publish_model(self.page)
        published=await (await response.value).json();cargo=published['version']['config_jsonb']['cargo']
        self.assertEqual(cargo['input_mode'],'direct');self.assertEqual(cargo['products'],[]);self.assertEqual(cargo['presentations'],[])
        await expect(self.page.locator('[data-dation-test=contract-cards]>.data-contract-card')).to_have_count(2)

    async def test_04_stale_or_mismatched_bundle_proof_never_unlocks_data(self):
        await self.select_v2();await self.upload('transport_demand');await self.upload('transport_resources')
        entered,release,finished=asyncio.Event(),asyncio.Event(),asyncio.Event();pattern='**/validate-bundle'
        async def delayed(route):
            response=await route.fetch();body=await response.json();entered.set();await release.wait();await route.fulfill(response=response,json=body);finished.set()
        await self.page.route(pattern,delayed,times=1)
        try:
            await self.upload('order_lines');await asyncio.wait_for(entered.wait(),10)
            await expect(self.page.locator('[data-journey-next]')).to_be_disabled()
            # The owner change produces another revision and a new authoritative
            # proof while the old revision's successful response is still held.
            await self.page.get_by_label('Data Owner',exact=True).select_option(setup.ADMIN)
            await expect(self.page.locator('[data-journey-next]')).to_be_enabled()
            release.set()
            await asyncio.wait_for(finished.wait(),10)
            async def malformed(route):
                response=await route.fetch();body=await response.json();body['normalized_hashes']['order_lines']='0'*64;await route.fulfill(response=response,json=body)
            await self.page.route(pattern,malformed,times=1)
            await self.page.get_by_label('Data Owner',exact=True).select_option('')
            await expect(self.page.locator('.journey-preparation-status')).to_contain_text('no corresponde a esta preparación')
            await expect(self.page.locator('[data-journey-next]')).to_be_disabled()
            await self.page.get_by_role('button',name='Revalidar relaciones entre archivos',exact=True).click()
            await expect(self.page.locator('[data-journey-next]')).to_be_enabled()
            self.assertEqual(self.sql('SELECT count(*) FROM decision_runs;'),'0')
        finally:release.set()
