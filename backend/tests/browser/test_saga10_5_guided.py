"""Guided UX: real owned API/SQL fixtures, no production or engines."""
import asyncio,json,re,unittest
from pathlib import Path
from playwright.async_api import expect
import test_saga10_wizard as saga
import guided_model_helpers as guided

OUT=Path('/tmp/dation-saga10-5-browser')
class Saga10GuidedTests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(saga.Saga10WizardTests.setUpClass.__func__)
    tearDownClass=classmethod(saga.Saga10WizardTests.tearDownClass.__func__)
    sql=saga.Saga10WizardTests.sql
    login=saga.Saga10WizardTests.login
    request=saga.Saga10WizardTests.request
    api=saga.Saga10WizardTests.api
    ready=saga.Saga10WizardTests.ready
    asyncSetUp=saga.Saga10WizardTests.asyncSetUp
    asyncTearDown=saga.Saga10WizardTests.asyncTearDown

    async def test_01_direct_review_is_explicit_and_resets(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        wizard=self.page.locator('.model-wizard-v2')
        await expect(wizard.locator('.model-v2-block')).to_have_count(5)
        await expect(wizard.locator('.model-v2-block > summary .ultimate-disclosure__status')).to_have_count(0)
        await expect(wizard.locator('.model-v2-block > summary .guided-status[data-state=complete]')).to_have_count(0)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Modelo guiado directo')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await guided.confirm(self.page)
        await expect(wizard.locator('.model-v2-block > summary .guided-status[data-state=complete]')).to_have_count(5)
        node=await guided.step(self.page,6);await node.locator('[name=dimensions][value=weight_kg]').check()
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await expect(wizard.locator('[data-dation-test=model-v2-block-3] > summary .guided-status')).to_have_attribute('data-state','pending')
        await guided.confirm(self.page)
        OUT.mkdir(exist_ok=True);await self.page.screenshot(path=str(OUT/'direct-review.png'),full_page=True,animations='disabled')
        await self.page.locator('[data-dation-test=model-create]').click();await self.ready(2)
        await expect(self.page.locator('[data-dation-test=contract-cards]>.data-contract-card')).to_have_count(2)
        self.assertEqual(self.sql('SELECT saga10_optimization_enabled FROM dation_private.platform_release;'),'f')

    async def test_02_mixed_catalog_correct_physics_and_shared_unit(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Composición declarada de jugos')
        await guided.mode(self.page,'catalog')
        node=await guided.step(self.page,4)
        await expect(node.locator('.guided-product-row')).to_have_count(0)
        orange=await guided.product(self.page,'Jugo naranja','8',code='JUG-NAR',unit='sobres',units='216')
        apple=await guided.product(self.page,'Jugo manzana','10',code='JUG-MAN',unit='sobres',units='216')
        peach=await guided.product(self.page,'Jugo durazno','6',code='JUG-DUR',unit='sobres',units='216')
        unit=await guided.support(self.page)
        presentation=await guided.presentation(self.page,'Pallet mixto de jugos',unit,[(orange,32),(apple,24),(peach,24)])
        node=await guided.step(self.page,6)
        await node.locator('[name=dimensions][value=weight_kg]').check()
        await node.locator('[name=dimensions][value=volume_m3]').check()
        await guided.confirm(self.page)
        preview=self.page.locator('[data-dation-test=cargo-physical-preview]')
        await expect(preview).to_contain_text('665');await expect(preview).to_contain_text('1.8')
        node=await guided.step(self.page,5)
        await expect(node.locator('.guided-composition-total')).to_contain_text('640 kg')
        rows=node.locator('.guided-composition-row[role=row]').filter(has=self.page.locator('select'))
        for i,(percent,mass) in enumerate([('40 %','256 kg'),('30 %','240 kg'),('30 %','144 kg')]):
            await expect(rows.nth(i).locator('.guided-cell').nth(0)).to_have_text(percent)
            await expect(rows.nth(i).locator('.guided-cell').nth(1)).to_have_text(mass)
        await expect(node.locator('[data-cargo-metric=gross]')).to_contain_text('665 kg')
        await expect(node).not_to_contain_text('Peso neto de productos')
        # Removing a component changes the real presentation and invalidates
        # consent; restoring it uses the existing product ID, never a clone.
        await rows.nth(2).get_by_role('button',name='Quitar componente',exact=True).click()
        await expect(node.locator('.guided-composition-row[role=row]').filter(has=self.page.locator('select'))).to_have_count(2)
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await guided.confirm(self.page)
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('521')
        node=await guided.step(self.page,5)
        await node.get_by_role('button',name='Agregar producto a la composición',exact=True).click()
        restored=node.locator('.guided-composition-row[role=row]').filter(has=self.page.locator('select')).nth(2)
        await restored.get_by_label('Producto *',exact=True).select_option(peach)
        await restored.get_by_label('Bultos por presentación *',exact=True).fill('24')
        await guided.confirm(self.page)
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('665')
        await self.capture_scenes()
        # Another presentation shares the existing support without copying it.
        second=await guided.presentation(self.page,'Pallet homogéneo',unit,[(orange,80)])
        self.assertNotEqual(presentation,second)
        await guided.confirm(self.page)
        async with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/versions')) as response:
            await self.page.locator('[data-dation-test=model-create]').click()
        result=await (await response.value).json();c=result['version']['config_jsonb']['cargo']
        self.assertEqual(len(c['products']),3);self.assertEqual(len(c['logistic_units']),1);self.assertEqual(len(c['presentations']),2)
        self.assertEqual({p['logistic_unit_id'] for p in c['presentations']},{unit})
        self.assertEqual(c['presentations'][0]['loaded_dimensions'],{'length':'120','width':'100','height':'150','unit':'cm'})
        self.assertIsNone(c['logistic_units'][0]['empty_dimensions'])
        self.assertNotIn('guided_ux',result['version']['config_jsonb'])
        await self.ready(2)
        await expect(self.page.locator('[data-dation-test=contract-cards]>.data-contract-card')).to_have_count(3)

    async def test_03_profiles_and_reversible_mode_draft_survive_reload(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Borrador reversible')
        node=await guided.step(self.page,1)
        self.assertEqual(await node.locator('[name=cargo_profile]').evaluate_all('(nodes)=>nodes.map(n=>n.value)'),['PALLETIZED','PACKAGED','DRY_BULK','LIQUID_BULK','SPECIALIZED','MIXED'])
        radio=node.locator('[value=PALLETIZED]');await radio.focus();await self.page.keyboard.press('ArrowRight')
        await expect(node.locator('[value=PACKAGED]')).to_be_checked()
        self.assertEqual(await self.page.locator('[name=dimensions]:checked').evaluate_all('(nodes)=>nodes.map(n=>n.value)'),['pallets'])
        await guided.mode(self.page,'catalog')
        product=await guided.product(self.page,'Mercadería real','8',code='REAL')
        unit=await guided.support(self.page,'Soporte conservado','25')
        profile=await guided.step(self.page,1)
        await profile.locator('label.guided-radio-card').filter(has=self.page.locator('[name=cargo_profile][value=MIXED]')).click()
        await expect(self.page.locator('[data-product-id="'+product+'"]')).to_have_count(1)
        await expect(self.page.locator('[name=dimensions]:checked')).to_have_count(1)
        await profile.locator('label.guided-radio-card').filter(has=self.page.locator('[name=cargo_profile][value=PACKAGED]')).click()
        await guided.mode(self.page,'direct');dialog=self.page.get_by_role('dialog')
        await expect(dialog).to_contain_text('catálogo no se publicará')
        await dialog.get_by_role('button',name='Cancelar',exact=True).click()
        await expect(self.page.locator('[name=cargo_input_mode][value=catalog]')).to_be_checked()
        await guided.mode(self.page,'direct')
        await self.page.get_by_role('dialog').get_by_role('button',name='Conservar y continuar',exact=True).click()
        await expect(self.page.locator('[data-cargo-step="4"]')).to_be_hidden()
        await expect(self.page.locator('[data-cargo-step="5"]')).to_be_hidden()
        await self.page.reload();await self.ready(1)
        await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('Borrador reversible')
        await expect(self.page.locator('[name=cargo_profile][value=PACKAGED]')).to_be_checked()
        await guided.mode(self.page,'catalog')
        await expect(self.page.locator('[data-product-id="'+product+'"]')).to_have_count(1)
        node=await guided.step(self.page,2);await expect(node.get_by_label('Soporte activo',exact=True)).to_have_value(unit)
        await expect(node.get_by_label('Nombre de la unidad *',exact=True)).to_have_value('Soporte conservado')
        await guided.mode(self.page,'direct');await self.page.keyboard.press('Escape')
        await expect(self.page.locator('[name=cargo_input_mode][value=catalog]')).to_be_checked()
        await guided.mode(self.page,'direct')
        await self.page.get_by_role('dialog').get_by_role('button',name='Conservar y continuar',exact=True).click()
        await guided.confirm(self.page)
        async with self.page.expect_request(lambda r:r.method=='POST' and r.url.endswith('/api/platform/logistics-models')) as request:
            await self.page.locator('[data-dation-test=model-create]').click()
        payload=(await request.value).post_data_json
        self.assertNotIn('guided_ux',payload);self.assertNotIn('guided_ux',payload['configuration'])
        for key in ['products','logistic_units','presentations']:self.assertEqual(payload['configuration']['cargo'][key],[])
        await self.ready(2);await self.page.locator('[data-dation-test=core-step-1]').click();await self.ready(1)
        await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_be_disabled()
        await expect(self.page.locator('.model-v2-block > summary .guided-status[data-state=complete]')).to_have_count(5)

    async def test_04_products_filter_clone_and_reference_protection(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Catálogo editable sin pérdida')
        await guided.mode(self.page,'catalog')
        first=await guided.product(self.page,'Jugo naranja','8',code='JUG-NAR')
        second=await guided.product(self.page,'Agua mineral','10',code='AGUA')
        node=await guided.step(self.page,4)
        for key,category in [(first,'Bebidas'),(second,'Agua')]:
            row=node.locator('[data-product-id="'+key+'"]');await row.locator('[data-product-edit]').click()
            more=row.locator('details').filter(has=self.page.get_by_text('Datos avanzados del producto',exact=True))
            if await more.get_attribute('open') is None:await more.locator('>summary').click()
            await row.get_by_label('Categoría descriptiva (opcional)',exact=True).fill(category)
        await node.get_by_label('Buscar entre los productos de este modelo',exact=True).fill('JUG-NAR')
        await expect(node.locator('.guided-product-row:visible')).to_have_count(1)
        await expect(node.locator('.guided-product-row:visible')).to_have_attribute('data-product-id',first)
        await node.get_by_label('Buscar entre los productos de este modelo',exact=True).fill('')
        await node.get_by_label('Filtrar productos',exact=True).select_option('Agua')
        await expect(node.locator('.guided-product-row:visible')).to_have_attribute('data-product-id',second)
        await node.get_by_label('Filtrar productos',exact=True).select_option('')
        row=node.locator('[data-product-id="'+first+'"]');await row.locator('.guided-actions button').nth(1).click()
        await expect(node.locator('.guided-product-row')).to_have_count(3)
        copied=node.locator('.guided-product-row').filter(has=self.page.locator('.guided-product-editor:not([hidden])'))
        copy_id=await copied.get_attribute('data-product-id');self.assertNotEqual(copy_id,first)
        self.assertNotEqual(await copied.get_by_label('Nombre del producto *',exact=True).input_value(),'Jugo naranja')
        self.assertNotEqual(await copied.get_by_label('Código (opcional)',exact=True).input_value(),'JUG-NAR')
        await expect(copied.locator('fieldset').get_by_label('Valor',exact=True)).to_have_value('8')
        await copied.locator('.guided-actions button').nth(2).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Eliminar',exact=True).click()
        await expect(node.locator('.guided-product-row')).to_have_count(2)
        unit=await guided.support(self.page)
        await guided.presentation(self.page,'Presentación con referencias',unit,[(first,80)],loaded=None)
        await guided.confirm(self.page)
        node=await guided.step(self.page,4);row=node.locator('[data-product-id="'+first+'"]')
        await expect(row.locator('.guided-actions button').nth(2)).to_be_disabled()
        await expect(row).to_contain_text('reasigná')
        node=await guided.step(self.page,2)
        await expect(node.get_by_role('button',name='Eliminar unidad',exact=False)).to_be_disabled()
        # Filtering is a real view action: it cannot invalidate a valid snapshot.
        node=await guided.step(self.page,4)
        await node.get_by_label('Buscar entre los productos de este modelo',exact=True).fill('Agua')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_enabled()

    async def make_physical(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Física verificada')
        await guided.mode(self.page,'catalog');p=await guided.product(self.page,'Jugo','12')
        u=await guided.support(self.page);await guided.presentation(self.page,'Pallet de jugo',u,[(p,80)],loaded=('120','100','180'))
        node=await guided.step(self.page,6)
        for value in ['weight_kg','volume_m3','units']:await node.locator('[name=dimensions][value='+value+']').check()
        await guided.confirm(self.page);return p,u

    async def test_05_partial_dimensions_unknown_mass_and_contradiction(self):
        product,unit=await self.make_physical()
        node=await guided.step(self.page,2)
        dimensions=node.locator('details').filter(has=self.page.get_by_text('Dimensiones del soporte vacío',exact=True))
        await dimensions.locator('>summary').click()
        await dimensions.get_by_label('Largo',exact=True).fill('120');await dimensions.get_by_label('Ancho',exact=True).fill('100')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await self.page.reload();await self.ready(1);node=await guided.step(self.page,2)
        dimensions=node.locator('details').filter(has=self.page.get_by_text('Dimensiones del soporte vacío',exact=True))
        if await dimensions.get_attribute('open') is None:await dimensions.locator('>summary').click()
        await expect(dimensions.get_by_label('Largo',exact=True)).to_have_value('120')
        await expect(dimensions.get_by_label('Alto',exact=True)).to_have_value('')
        await dimensions.get_by_label('Alto',exact=True).fill('15')
        loaded=node.locator('details').filter(has=self.page.get_by_text('Dimensiones exteriores cargadas',exact=True))
        if await loaded.get_attribute('open') is None:await loaded.locator('>summary').click()
        await expect(loaded.get_by_label('Alto',exact=True)).to_have_value('180')
        await guided.confirm(self.page)
        node=await guided.step(self.page,2)
        gross=node.locator('details').filter(has=self.page.get_by_text('Peso bruto cargado declarado (opcional si se deriva)',exact=True));await gross.locator('>summary').click()
        await gross.get_by_label('Valor',exact=True).fill('500')
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('contradice')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await gross.get_by_label('Valor',exact=True).fill('')
        node=await guided.step(self.page,4);row=node.locator('[data-product-id="'+product+'"]')
        if not await row.get_by_label('Nombre del producto *',exact=True).is_visible():await row.locator('[data-product-edit]').click()
        mass=row.locator('fieldset').filter(has=self.page.get_by_text('Peso bruto por bulto (opcional)',exact=True)).get_by_label('Valor',exact=True)
        await mass.fill('')
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('Falta una propiedad física')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await mass.fill('12');await guided.confirm(self.page)
        async with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/versions')) as response:
            await self.page.locator('[data-dation-test=model-create]').click()
        data=await (await response.value).json();c=data['version']['config_jsonb']['cargo']
        self.assertEqual(c['logistic_units'][0]['logistic_unit_id'],unit)
        self.assertEqual(c['logistic_units'][0]['empty_dimensions']['height'],'15')
        self.assertEqual(c['presentations'][0]['loaded_dimensions']['height'],'180')

    async def test_06_stale_preview_never_reenables_publish(self):
        await self.make_physical();node=await guided.step(self.page,5)
        qty=node.get_by_label('Bultos por presentación *',exact=True)
        entered,release,finished=asyncio.Event(),asyncio.Event(),asyncio.Event()
        async def delayed(route):
            response=await route.fetch();data=await response.json();entered.set();await release.wait()
            await route.fulfill(response=response,json=data);finished.set()
        pattern='**/api/platform/logistics-models/contract-preview'
        await self.page.route(pattern,delayed,times=1)
        try:
            await qty.fill('40');await asyncio.wait_for(entered.wait(),10)
            await qty.fill('0.5')
            await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
            release.set();await asyncio.wait_for(finished.wait(),10)
            await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
            await expect(self.page.locator('[name=cargo_review]')).to_be_disabled()
            await qty.fill('60');await guided.confirm(self.page)
            await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('745')
            await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).not_to_contain_text('505.000')
        finally:release.set()

    async def test_07_bulk_uses_explicit_density_without_required_pallet(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Granel por kg')
        node=await guided.step(self.page,1)
        await node.locator('label.guided-radio-card').filter(has=self.page.locator('[value=LIQUID_BULK]')).click()
        await guided.mode(self.page,'catalog')
        material=await guided.product(self.page,'Aceite',None,unit='kg')
        node=await guided.step(self.page,4);row=node.locator('[data-product-id="'+material+'"]')
        advanced=row.locator('details').filter(has=self.page.get_by_text('Datos avanzados del producto',exact=True))
        if await advanced.get_attribute('open') is None:await advanced.locator('>summary').click()
        await row.get_by_label('Densidad explícita (kg/m³, opcional)',exact=True).fill('800')
        node=await guided.step(self.page,5);await node.get_by_role('button',name='Agregar presentación',exact=True).click()
        await node.get_by_label('Nombre de la presentación *',exact=True).fill('Aceite por kg')
        await expect(node.get_by_label('Naturaleza de la cantidad',exact=True)).to_have_value('CONTINUOUS')
        await expect(node.get_by_label('Unidad logística compartida',exact=True)).to_have_count(0)
        await node.get_by_label('Producto *',exact=True).select_option(material)
        await expect(node.get_by_label('Factor de material (1)',exact=True)).to_have_value('1')
        node=await guided.step(self.page,6)
        await node.get_by_role('button',name='Aplicar sugerencia de dimensiones del perfil',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Aplicar sugerencia',exact=True).click()
        await node.get_by_label('Fraccionamiento',exact=True).select_option('CONTINUOUS')
        await guided.confirm(self.page)
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('0.00125')
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('0.004 kg')
        await expect(self.page.locator('[data-cargo-step="5"] .guided-pallet-art')).to_have_count(0)
        async with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/versions')) as response:
            await self.page.locator('[data-dation-test=model-create]').click()
        data=await (await response.value).json();c=data['version']['config_jsonb']
        self.assertEqual(c['cargo']['profile'],'LIQUID_BULK');self.assertEqual(c['cargo']['logistic_units'],[])
        self.assertEqual(c['active_dimensions'],['weight_kg','volume_m3']);self.assertEqual(c['primary_dimension'],'weight_kg')
        self.assertEqual(c['cargo']['presentations'][0]['quantity_kind'],'CONTINUOUS')
        self.assertEqual(self.sql('SELECT saga10_optimization_enabled FROM dation_private.platform_release;'),'f')

    async def test_08_preview_failure_preserves_values_and_retries(self):
        await self.make_physical();node=await guided.step(self.page,5)
        pattern='**/api/platform/logistics-models/contract-preview'
        await self.page.route(pattern,lambda route:route.fulfill(status=503,json={'detail':'Verificación temporalmente no disponible'}),times=1)
        await node.get_by_label('Bultos por presentación *',exact=True).fill('60')
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('temporalmente')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await expect(node.get_by_label('Bultos por presentación *',exact=True)).to_have_value('60')
        await expect(node.locator('.guided-physical-summary [role=alert]')).to_contain_text('temporalmente')
        await self.page.get_by_role('button',name='Reintentar Data Contract',exact=True).click()
        await guided.confirm(self.page)
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('745')
        await expect(self.page.locator('[name=cargo_review]')).to_be_checked()

    async def test_09_component_limits_with_public_initial_dto(self):
        # Component boundary fixture, not a fabricated end-to-end publication.
        # Mount the public renderer with a synthetic draft near each real limit.
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        cfg=json.loads(json.dumps(saga.setup.CONFIG));cfg.update(version=2,consolidation_permitted=True,resource_categories=[])
        products=[{'product_id':'P'+str(i),'name':'Producto '+str(i),'unit_label':'caja','units_per_package':1,'gross_mass':{'value':'1','unit':'kg'},'compatibility_groups':['SECO']} for i in range(99)]
        units=[{'logistic_unit_id':'U'+str(i),'label':'Soporte '+str(i),'type':'PALLET','tare_mass':{'value':'1','unit':'kg'}} for i in range(49)]
        presentations=[{'presentation_id':'L'+str(i),'label':'Presentación '+str(i),'quantity_kind':'DISCRETE','quantity_unit':'presentation','logistic_unit_id':'U0','components':[{'product_id':'P0','quantity':'1'}]} for i in range(199)]
        presentations[0]['components']=[{'product_id':'P'+str(i),'quantity':'1'} for i in range(29)]
        cfg['cargo']={'profile':'PALLETIZED','input_mode':'catalog','split_policy':'INDIVISIBLE','compatibility_policy':'UNIFORM_DECLARED','co_load_pairs':[],'products':products,'logistic_units':units,'presentations':presentations}
        await self.page.evaluate('''async configuration=>{
          const {mountModelFieldsV2}=await import('/static/js/dispatch/models/model-fields-v2.mjs');
          const original=document.querySelector('.model-wizard-v2').closest('form'),form=document.createElement('form');form.className=original.className;original.replaceWith(form);
          const cleanups=[],controller=new AbortController(),scope={listen(n,event,run){n.addEventListener(event,run,{signal:controller.signal});},own(fn){cleanups.push(fn);},signal:controller.signal};
          window.guidedBoundary=mountModelFieldsV2(form,scope,{id:crypto.randomUUID(),expected_revision:1,name:'Límites del componente',configuration});
        }''',cfg)
        node=await guided.step(self.page,4)
        await node.get_by_role('button',name='Agregar producto',exact=True).click()
        await expect(node.get_by_role('button',name='Agregar producto',exact=True)).to_be_disabled()
        await expect(node.locator('[data-product-edit]').first).to_be_enabled()
        node=await guided.step(self.page,2)
        await node.get_by_role('button',name='Agregar unidad logística',exact=True).click()
        await expect(node.get_by_role('button',name='Agregar unidad logística',exact=True)).to_be_disabled()
        node=await guided.step(self.page,5)
        await node.get_by_role('button',name='Agregar presentación',exact=True).click()
        await expect(node.get_by_role('button',name='Agregar presentación',exact=True)).to_be_disabled()
        await node.get_by_label('Presentación activa',exact=True).select_option('L0')
        await node.get_by_role('button',name='Agregar producto a la composición',exact=True).click()
        await expect(node.get_by_role('button',name='Agregar producto a la composición',exact=True)).to_be_disabled()
        result=await self.page.evaluate('window.guidedBoundary.read().configuration.cargo')
        self.assertEqual(len(result['products']),100);self.assertEqual(len(result['logistic_units']),50);self.assertEqual(len(result['presentations']),200)
        self.assertEqual(len(result['presentations'][0]['components']),30)
        self.assertEqual(result['products'][0]['product_id'],'P0');self.assertEqual(result['presentations'][0]['logistic_unit_id'],'U0')
        await expect(self.page.locator('.model-v2-block > summary .guided-status[data-state=complete]')).to_have_count(0)

    async def capture_scenes(self):
        OUT.mkdir(exist_ok=True)
        # Confirm the real local substeps using their public navigation.
        for i in range(1,7):
            node=await guided.step(self.page,i);await node.locator('>summary').focus()
            actions=self.page.locator('.guided-flow-actions')
            await expect(actions).to_have_attribute('data-active-cargo-step',str(i))
            await actions.get_by_role('button').nth(1).click()
        await guided.step(self.page,4)
        for row in await self.page.locator('.guided-product-row').all():
            if await row.locator('.guided-product-editor').is_visible():await row.locator('[data-product-edit]').click()
        for i in [1,2,4,5]:
            node=self.page.locator('[data-dation-test=model-v2-block-'+str(i)+']')
            if await node.get_attribute('open') is not None:await node.locator('>summary').click()
        results=[]
        scenes=[('profile-support',{1,2}),('mode-products-composition',{3,4,5}),('review',{7})]
        for scene,opened in scenes:
            for i in range(1,8):
                node=self.page.locator('[data-cargo-step="'+str(i)+'"]')
                is_open=await node.get_attribute('open') is not None
                if is_open!=(i in opened):await node.locator('>summary').click()
            for width in [1536,1024,768,390,320]:
                await self.page.set_viewport_size({'width':width,'height':960 if width>=768 else 844})
                await self.page.evaluate('document.fonts.ready');await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
                geometry=await self.page.evaluate('''()=>({
                    width:innerWidth,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,
                    profileColumns:getComputedStyle(document.querySelector('[data-cargo-step="1"] .guided-radio-grid')).gridTemplateColumns,
                    outside:[...document.querySelectorAll('.model-wizard-v2 input,.model-wizard-v2 select,.model-wizard-v2 button,.model-wizard-v2 textarea')].filter(n=>n.getClientRects().length).filter(n=>{const r=n.getBoundingClientRect();return r.left<-.5||r.right>document.documentElement.clientWidth+1}).map(n=>({name:n.name||n.textContent,html:n.outerHTML.slice(0,180)}))
                })''')
                self.assertLessEqual(geometry['scroll'],geometry['client'],geometry)
                self.assertEqual(geometry['outside'],[],geometry)
                if scene=='profile-support':self.assertEqual(len(geometry['profileColumns'].split()),3 if width>=1200 else 2 if width>=768 else 1)
                audit=await self.page.evaluate((Path(__file__).parent/'theme_audit.js').read_text(),'.model-wizard-v2')
                self.assertEqual(audit['failures'],[],audit['failures'])
                geometry.update(scene=scene,minimumContrast=audit['minimumContrast'],textCount=audit['textCount'])
                results.append(geometry)
                if width in [1536,390,320]:
                    await self.page.mouse.move(0,0);await self.page.evaluate('document.activeElement?.blur();scrollTo(0,0)')
                    await self.page.screenshot(path=str(OUT/('actual-'+scene+'-'+str(width)+'.png')),full_page=True,animations='disabled')
        (OUT/'geometry-and-contrast.json').write_text(json.dumps(results,indent=2))
        await self.page.set_viewport_size({'width':1536,'height':960})
        for i in range(1,6):
            node=self.page.locator('[data-dation-test=model-v2-block-'+str(i)+']')
            if await node.get_attribute('open') is not None:await node.locator('>summary').click()
        await self.page.evaluate('scrollTo(0,0)');await self.page.screenshot(path=str(OUT/'actual-five-headers-1536.png'),full_page=True,animations='disabled')
        for index in [1,2,3]:
            header=self.page.locator('[data-dation-test=model-v2-block-'+str(index)+'] > summary')
            await header.focus()
            was_open=await header.evaluate('(n)=>n.parentElement.open')
            await self.page.keyboard.press('Space')
            await expect(header.locator('..')).to_have_attribute('open','') if not was_open else await expect(header.locator('..')).not_to_have_attribute('open','')
            await self.page.keyboard.press('Enter')
            self.assertEqual(await header.evaluate('(n)=>n.parentElement.open'),was_open)
        await guided.step(self.page,1)
        radio=self.page.locator('[name=cargo_profile]:checked');await radio.focus();await self.page.keyboard.press('Tab');await self.page.keyboard.press('Shift+Tab')
        focused=await radio.evaluate("(n)=>({checked:n.checked,cardOutline:getComputedStyle(n.closest('label')).outlineStyle,width:getComputedStyle(n.closest('label')).outlineWidth})")
        self.assertTrue(focused['checked']);self.assertNotEqual(focused['cardOutline'],'none');self.assertNotEqual(focused['width'],'0px')
        summary=self.page.locator('[data-dation-test=model-v2-block-3] > summary');await summary.focus()
        focus=await self.page.evaluate((Path(__file__).parent/'focus_audit.js').read_text())
        self.assertTrue(focus['visibleFocus'],focus);self.assertFalse(focus['outside'],focus)
        await self.page.emulate_media(reduced_motion='reduce')
        self.assertEqual(await self.page.locator('.guided-radio-card').first.evaluate('(n)=>getComputedStyle(n).transitionDuration'),'0s')
        await self.page.emulate_media(reduced_motion='no-preference')
        await guided.confirm(self.page)

    async def test_10_primary_coload_incomparable_units_and_safe_duplicates(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Reglas físicas explícitas')
        await guided.mode(self.page,'catalog')
        first=await guided.product(self.page,'Cajas secas','8',unit='caja',groups='SECO')
        second=await guided.product(self.page,'Bolsas frías','10',unit='bolsa',groups='FRIO')
        unit=await guided.support(self.page)
        original=await guided.presentation(self.page,'Mixto autorizado',unit,[(first,80),(second,20)],loaded=None)
        node=await guided.step(self.page,6);await node.locator('[name=dimensions][value=weight_kg]').check()
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('no autorizados')
        await expect(node.get_by_label('Compatibilidad de carga',exact=True)).to_have_value('CATEGORIZED')
        await node.get_by_role('button',name='Agregar pareja de co-carga',exact=True).click()
        await node.get_by_label('Categoría A',exact=True).fill('SECO');await node.get_by_label('Categoría B',exact=True).fill('FRIO')
        await node.locator('[name=dimensions][value=pallets]').uncheck()
        await expect(node.get_by_label('Dimensión principal de reporte',exact=True)).to_have_attribute('aria-invalid','true')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await node.get_by_label('Dimensión principal de reporte',exact=True).select_option('weight_kg')
        await node.get_by_label('Fraccionamiento',exact=True).select_option('DISCRETE')
        resources=await guided.block(self.page,4)
        for value in ['GENERAL','REFRIGERATED']:await resources.locator('[name=resource_categories][value='+value+']').check()
        await guided.confirm(self.page)
        node=await guided.step(self.page,5)
        await expect(node.locator('.guided-cell').first).to_have_text('No comparable')
        await expect(node.locator('.guided-composition-total')).to_contain_text('bultos no comparables')
        # Shared support and presentation clones get new IDs, never rebinding originals.
        node=await guided.step(self.page,2);await node.get_by_role('button',name='Duplicar unidad',exact=True).click()
        copied_unit=await node.get_by_label('Soporte activo',exact=True).input_value();self.assertNotEqual(copied_unit,unit)
        node=await guided.step(self.page,5)
        await expect(node.get_by_label('Unidad logística compartida',exact=True)).to_have_value(unit)
        node=await guided.step(self.page,2);await node.get_by_role('button',name='Eliminar unidad',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Eliminar',exact=True).click()
        self.assertEqual(await node.get_by_label('Soporte activo',exact=True).locator('option').count(),2)
        node=await guided.step(self.page,5);await node.get_by_role('button',name='Duplicar presentación',exact=True).click()
        self.assertNotEqual(await node.get_by_label('Presentación activa',exact=True).input_value(),original)
        await expect(node.get_by_label('Unidad logística compartida',exact=True)).to_have_value(unit)
        await node.get_by_role('button',name='Eliminar presentación',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Eliminar',exact=True).click()
        await expect(node.get_by_label('Presentación activa',exact=True)).to_have_value(original)
        node=await guided.step(self.page,6)
        await node.get_by_role('button',name='Agregar pareja de co-carga',exact=True).click()
        await node.get_by_label('Categoría A',exact=True).nth(1).fill('FRIO');await node.get_by_label('Categoría B',exact=True).nth(1).fill('SECO')
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('simétricos')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await node.get_by_role('button',name='Quitar pareja',exact=True).nth(1).click()
        await guided.confirm(self.page)
        async with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/versions')) as response:
            await self.page.locator('[data-dation-test=model-create]').click()
        data=await (await response.value).json();c=data['version']['config_jsonb']
        self.assertEqual(c['cargo']['co_load_pairs'],[['SECO','FRIO']])
        self.assertEqual(c['resource_categories'],['GENERAL','REFRIGERATED'])
        self.assertEqual(c['active_dimensions'],['weight_kg']);self.assertEqual(c['primary_dimension'],'weight_kg')
        self.assertTrue(c['split_permitted']);self.assertFalse(c['homogeneous_loads_declared'])
        self.assertEqual(len(c['cargo']['logistic_units']),1);self.assertEqual(len(c['cargo']['presentations']),1)
        self.assertEqual(c['cargo']['presentations'][0]['presentation_id'],original)
        self.assertEqual(c['cargo']['presentations'][0]['logistic_unit_id'],unit)

    async def test_11_missing_sources_has_inline_accessible_error(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Fuentes reales')
        node=await guided.block(self.page,4)
        for value in ['OWN','EXTERNAL']:await node.locator('[name=sources][value='+value+']').uncheck()
        await node.locator('[data-confirm-block="4"]').click()
        error=node.locator('[data-model-error-for=sources]')
        await expect(error).to_be_visible();await expect(error).to_contain_text('al menos una fuente')
        await expect(node.locator('[name=sources]').first).to_have_attribute('aria-describedby',await error.get_attribute('id'))
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await node.locator('[name=sources][value=OWN]').check();await guided.confirm(self.page)
        await expect(error).to_be_empty()
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_enabled()

    async def test_12_declared_physics_is_not_labelled_as_calculated(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Bruto declarado, composición sin peso')
        await guided.mode(self.page,'catalog')
        product=await guided.product(self.page,'Mercadería',None)
        unit=await guided.support(self.page)
        await guided.presentation(self.page,'Presentación declarada',unit,[(product,80)],loaded=None)
        node=await guided.step(self.page,2)
        for title,value in [('Peso bruto cargado declarado (opcional si se deriva)','900'),('Volumen exterior declarado','1.8')]:
            group=node.locator('details').filter(has=self.page.get_by_text(title,exact=True))
            await group.locator('>summary').click();await group.get_by_label('Valor',exact=True).fill(value)
        node=await guided.step(self.page,6)
        for value in ['weight_kg','volume_m3']:await node.locator('[name=dimensions][value='+value+']').check()
        await guided.confirm(self.page);node=await guided.step(self.page,5)
        panel=node.locator('.guided-physical-summary')
        for label,value in [('Peso bruto total','900 kg'),('Volumen exterior cargado','1,8 m³')]:
            row=panel.locator('.guided-readout').filter(has=self.page.get_by_text(label,exact=True))
            await expect(row).to_contain_text(value);await expect(row.locator('small')).to_have_text('Declarado · validado por Dation')
        await expect(panel).to_contain_text('Peso pendiente de declarar')
        async with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/versions')) as response:
            await self.page.locator('[data-dation-test=model-create]').click()
        data=await (await response.value).json();p=data['version']['config_jsonb']['cargo']['presentations'][0]
        self.assertIsNone(p['loaded_dimensions']);self.assertEqual(p['gross_mass']['value'],'900');self.assertEqual(p['external_volume']['value'],'1.8')
