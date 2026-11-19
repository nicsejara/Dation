"""Ultimate Pro: real API/owned SQL, no production, engines remain OFF."""
import asyncio,json,re,unittest,subprocess,os
from pathlib import Path
from playwright.async_api import expect
import test_saga10_5_guided as fixture
import guided_model_helpers as legacy

OUT=Path('/tmp/dation-saga10-5-r2-browser')
class UltimateProTests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(fixture.Saga10GuidedTests.setUpClass.__func__)
    tearDownClass=classmethod(fixture.Saga10GuidedTests.tearDownClass.__func__)
    sql=fixture.Saga10GuidedTests.sql;login=fixture.Saga10GuidedTests.login;request=fixture.Saga10GuidedTests.request;api=fixture.Saga10GuidedTests.api;ready=fixture.Saga10GuidedTests.ready
    asyncSetUp=fixture.Saga10GuidedTests.asyncSetUp;asyncTearDown=fixture.Saga10GuidedTests.asyncTearDown

    async def start(self):
        self.errors=[];self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await expect(self.page.locator('.model-wizard-pro')).to_be_visible()
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('QA Logistics Orange')
        await legacy.block(self.page,3)
        self.assertEqual(self.errors,[])

    async def fill(self,*,kind='PALLET',mass='8',quantity='80',product='Jugo de naranja'):
        first=self.page.locator('[data-pro-step="1"]');second=self.page.locator('[data-pro-step="2"]')
        await first.get_by_role('button',name='Agregar unidad logística',exact=True).click()
        await first.get_by_label('Nombre de la presentación *',exact=True).fill('Presentación naranja')
        await first.get_by_label('Nombre de la unidad *',exact=True).fill('Pallet estándar')
        await first.locator('[data-guided-field=support-tare]').fill('25')
        for label,value in [('Largo cargado','120'),('Ancho cargado','100'),('Alto cargado','150')]:await first.get_by_label(label,exact=True).fill(value)
        if kind!='PALLET':await self.kind(kind)
        await second.get_by_role('button',name='Agregar producto',exact=True).click()
        await second.get_by_label('Nombre del producto *',exact=True).fill(product)
        massbox=second.locator('fieldset').filter(has=self.page.get_by_text('Peso bruto por bulto *',exact=True))
        await massbox.get_by_label('Valor',exact=True).fill(mass)
        dims=second.locator('fieldset').filter(has=self.page.get_by_text('Dimensiones del bulto (informativas)',exact=True))
        for label,value in [('Largo del bulto','30'),('Ancho del bulto','20'),('Alto del bulto','30')]:await dims.get_by_label(label,exact=True).fill(value)
        await second.get_by_label('Bultos por unidad logística *',exact=True).fill(quantity)
        advanced=second.locator('details').filter(has=self.page.get_by_text('Datos avanzados del producto y la presentación',exact=True));await advanced.locator('>summary').click()
        await second.get_by_label('Categorías de compatibilidad (separadas por coma)',exact=True).fill('SECO')
        return first,second

    async def kind(self,value,*,cancel=False):
        await self.page.locator('label.guided-radio-card').filter(has=self.page.locator('[name=guided_unit_type][value="'+value+'"]')).click()
        dialog=self.page.get_by_role('dialog');await expect(dialog).to_be_visible()
        await dialog.get_by_role('button',name='Cancelar' if cancel else 'Cambiar tipo',exact=True).click()

    async def confirm(self):
        for i in [1,2,4,5,3]:
            node=await legacy.block(self.page,i);cta=node.locator('[data-confirm-block="'+str(i)+'"]')
            await expect(cta).to_be_enabled()
            if i==3:await expect(cta).to_have_attribute('data-preview-current','true')
            await cta.click()
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_enabled()

    async def publish(self):
        await self.confirm()
        async with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/versions')) as response:
            await self.page.locator('[data-dation-test=model-create]').click()
        result=await (await response.value).json();await self.ready(2);return result['version']['config_jsonb']

    async def test_01_homogeneous_physics_contract_and_explicit_confirmation(self):
        await self.start()
        await expect(self.page.locator('.guided-status[data-state=complete]')).to_have_count(0)
        await expect(self.page.locator('[data-pro-step]')).to_have_count(3)
        await expect(self.page.locator('[data-cargo-step]')).to_have_count(0)
        await expect(self.page.locator('[name=cargo_review]')).to_have_count(0)
        await expect(self.page.locator('[name=primary_dimension]')).to_have_count(0)
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        first,second=await self.fill()
        await expect(second).to_contain_text('0,018 m³')
        await expect(second.locator('[data-cargo-metric=gross]')).to_contain_text('665 kg')
        await expect(first).to_contain_text('1,8 m³')
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('665')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        cfg=await self.publish();c=cfg['cargo'];p=c['presentations'][0]
        self.assertEqual(cfg['active_dimensions'],['weight_kg','volume_m3']);self.assertEqual(cfg['primary_dimension'],'weight_kg')
        self.assertEqual(c['compatibility_policy'],'CATEGORIZED');self.assertEqual(c['co_load_pairs'],[])
        self.assertEqual(p['loaded_dimensions'],{'length':'120','width':'100','height':'150','unit':'cm'})
        self.assertIsNone(c['logistic_units'][0]['empty_dimensions']);self.assertEqual(c['logistic_units'][0]['tare_mass']['value'],'25')
        self.assertEqual(len(p['components']),1);self.assertEqual(p['components'][0]['quantity'],'80')
        self.assertEqual(c['products'][0]['units_per_package'],1);self.assertEqual(c['products'][0]['unit_label'],'caja')
        await expect(self.page.locator('[data-dation-test=contract-cards]>.data-contract-card')).to_have_count(3)
        OUT.mkdir(exist_ok=True);(OUT/'dto.json').write_text(json.dumps(cfg,indent=2))
        # Finite D1 boundary test using the exact browser-published DTO. Never
        # invokes /runs, changes release flags, or accesses production.
        check=subprocess.run([os.environ.get('DATION_RUNTIME_PYTHON',os.sys.executable),'-c',"""
import json,sys
from tests.saga10_fixtures import cargo_request
from tests.test_transport_plan_core import resource
from app.engines.assignment.cargo_inputs import run_cargo_policy
cfg=json.load(sys.stdin);cfg['split_permitted']=True;cfg['cargo']['split_policy']='DISCRETE'
pid=cfg['cargo']['presentations'][0]['presentation_id']
r=resource(services=1,guaranteed_capacity={'weight_kg':'1330','volume_m3':'3.6'},compatibility_groups=['SECO'])
req=cargo_request(cfg,[('QA',[(pid,'3')],True)],[r])
core=run_cargo_policy(req,alternative_budget=0).recommended.output.core
assert core.transport_plan.cargo.lines[0].assigned==2
assert core.transport_plan.cargo.lines[0].unserved==1
assert core.transport_plan.trips[0].total_load.weight_kg==1330
cfg['split_permitted']=False;cfg['cargo']['split_policy']='INDIVISIBLE'
core=run_cargo_policy(cargo_request(cfg,[('QA',[(pid,'3')],False)],[r]),alternative_budget=0).recommended.output.core
assert not core.transport_plan.trips
print('D1_WEIGHT_PRIMARY_NO_HIDDEN_PALLETS_AND_SPLIT_PASS')
"""],input=json.dumps(cfg),text=True,capture_output=True,cwd=Path(__file__).resolve().parents[2],env={**os.environ,'DATION_EXECUTION_MODE':'legacy'})
        self.assertEqual(check.returncode,0,check.stderr);(OUT/'d1-dry-run.txt').write_text(check.stdout)
        self.assertEqual(self.errors,[])

    async def test_02_roles_sources_cost_dependencies_and_currency(self):
        await self.start();await self.fill()
        node=await legacy.block(self.page,2)
        for value in ['LOGISTICS_PROVIDER','HYBRID','SHIPPER']:
            control=node.locator('[name=operating_role][value='+value+']');await control.focus();await self.page.keyboard.press('Space');await expect(control).to_be_checked()
        await node.locator('[name=consolidation_permitted][value=no]').focus();await self.page.keyboard.press('Space')
        await expect(node.locator('[name=transport_pattern]')).to_have_count(0)
        resources=await legacy.block(self.page,4);await resources.locator('label').filter(has=self.page.locator('[name=sources][value=OWN]')).click()
        costs=await legacy.block(self.page,5);await expect(costs.get_by_text('Costo operativo por kilómetro',exact=True)).to_be_hidden()
        await costs.locator('label').filter(has=self.page.locator('[name=currency][value=EUR]')).click()
        money=costs.locator('details').filter(has=self.page.get_by_text('Configuración monetaria avanzada',exact=True));await money.locator('>summary').click();await costs.get_by_label('Decimales monetarios',exact=True).select_option('4')
        await costs.locator('label').filter(has=self.page.locator('[name=external_costs][value=PER_KM]')).click()
        await expect(costs.locator('[name=billing]').first).to_be_hidden()
        await costs.locator('label').filter(has=self.page.locator('[name=external_costs][value=PER_TRIP]')).click()
        await costs.locator('[data-confirm-block="5"]').click();await expect(costs.locator('[data-model-error-for=costs]')).to_contain_text('tarifa externa')
        await costs.locator('label').filter(has=self.page.locator('[name=external_costs][value=PER_KM]')).click()
        cfg=await self.publish()
        self.assertFalse(cfg['consolidation_permitted']);self.assertEqual(cfg['allowed_sources'],['EXTERNAL'])
        self.assertEqual(cfg['currency_policy']['currency'],'EUR');self.assertEqual(cfg['currency_policy']['minor_units'],4)
        self.assertEqual(cfg['per_km_billing_bases'],['ONE_WAY','ROUND_TRIP']);self.assertEqual(cfg['external_cost_models'],['PER_KM'])

    async def test_03_five_types_cancel_and_big_bag_without_fake_geometry(self):
        await self.start();first,second=await self.fill()
        await self.kind('BOX',cancel=True);await expect(first.locator('[value=PALLET]')).to_be_checked()
        for value in ['BOX','CRATE','OTHER','PALLET']:
            await self.kind(value);await expect(first.locator('[data-support-art=empty]')).to_have_attribute('data-unit-type',value)
            await expect(first.get_by_label('Alto cargado',exact=True)).to_have_value('150')
        await self.kind('BIG_BAG')
        await expect(second.get_by_role('heading',name='Resumen de la composición',exact=True)).to_be_visible()
        await expect(self.page.locator('[data-dation-test=model-v2-summary]')).to_contain_text('Catálogo homogéneo')
        await expect(second.get_by_text('Resumen del pallet',exact=True)).to_have_count(0)
        # Existing dimensions are preserved explicitly; clear them deliberately.
        d=first.locator('details').filter(has=self.page.get_by_text('Dimensiones exteriores adicionales (opcionales)',exact=True));await d.locator('>summary').click()
        for label in ['Largo cargado','Ancho cargado','Alto cargado']:await first.get_by_label(label,exact=True).fill('')
        await first.get_by_label('Volumen exterior *',exact=True).fill('1')
        await first.locator('[data-guided-field=support-tare]').fill('2')
        mass=second.locator('fieldset').filter(has=self.page.get_by_text('Peso bruto por bulto *',exact=True));await mass.get_by_label('Valor',exact=True).fill('900')
        await second.get_by_label('Bultos por unidad logística *',exact=True).fill('1')
        await expect(second.locator('[data-cargo-metric=gross]')).to_contain_text('902 kg')
        cfg=await self.publish();p=cfg['cargo']['presentations'][0]
        self.assertEqual(p['quantity_kind'],'DISCRETE');self.assertIsNone(p['loaded_dimensions']);self.assertEqual(p['external_volume']['value'],'1');self.assertEqual(cfg['cargo']['logistic_units'][0]['type'],'BIG_BAG')

    async def test_04_shared_support_two_homogeneous_presentations_and_reload(self):
        await self.start();first,second=await self.fill()
        first_id=await first.get_by_label('Presentación activa',exact=True).input_value();unit=await first.get_by_label('Soporte compartido',exact=True).input_value()
        await first.get_by_role('button',name='Agregar presentación homogénea',exact=True).click()
        await first.get_by_label('Nombre de la presentación *',exact=True).fill('Manzana')
        for label,value in [('Largo cargado','120'),('Ancho cargado','100'),('Alto cargado','150')]:await first.get_by_label(label,exact=True).fill(value)
        await second.get_by_role('button',name='Agregar producto',exact=True).click();await second.get_by_label('Nombre del producto *',exact=True).fill('Jugo de manzana')
        await second.locator('fieldset').filter(has=self.page.get_by_text('Peso bruto por bulto *',exact=True)).get_by_label('Valor',exact=True).fill('10')
        await second.get_by_label('Bultos por unidad logística *',exact=True).fill('80')
        advanced=second.locator('details').filter(has=self.page.get_by_text('Datos avanzados del producto y la presentación',exact=True));await advanced.locator('>summary').click();await second.get_by_label('Categorías de compatibilidad (separadas por coma)',exact=True).fill('SECO')
        await expect(second.locator('[data-cargo-metric=gross]')).to_contain_text('825 kg')
        await self.page.reload();await self.ready(1);await legacy.block(self.page,3)
        await expect(first.get_by_label('Soporte compartido',exact=True)).to_have_value(unit)
        cfg=await self.publish();c=cfg['cargo'];self.assertEqual(len(c['products']),2);self.assertEqual(len(c['logistic_units']),1);self.assertEqual(len(c['presentations']),2)
        self.assertEqual({p['logistic_unit_id'] for p in c['presentations']},{unit});self.assertTrue(all(len(p['components'])==1 for p in c['presentations']))
        await self.page.locator('[data-dation-test=core-step-1]').click();await self.ready(1)
        await expect(self.page.locator('.model-wizard-v2 input:not(:disabled):not([data-guided-ui])')).to_have_count(0)
        self.assertEqual(await self.page.locator('.model-wizard-v2 input:not(:disabled)').evaluate_all('(ns)=>ns.map(n=>n.name)'),[])
        await expect(self.page.get_by_label('Soporte compartido',exact=True)).to_be_disabled()
        await expect(self.page.get_by_label('Producto de esta presentación',exact=True)).to_be_disabled()
        await expect(self.page.locator('[data-model-new]')).to_be_enabled()
        self.assertEqual(self.errors,[])

    async def test_05_real_geometry_a11y_and_screenshots(self):
        await self.start();await self.fill();await self.confirm()
        OUT.mkdir(exist_ok=True);geometry=[];audits=[]
        for width in [1536,1024,768,390,320]:
            await self.page.set_viewport_size({'width':width,'height':1100})
            for i in range(1,6):await legacy.block(self.page,i)
            metrics=await self.page.evaluate('''()=>{
              const rect=n=>{const r=n.getBoundingClientRect(),s=getComputedStyle(n);return {width:r.width,height:r.height,rightGap:n.closest('.ultimate-disclosure__content').getBoundingClientRect().right-r.right,padding:s.padding,border:s.borderWidth,radius:s.borderRadius,font:s.font,iconWidth:n.querySelector('svg').getBoundingClientRect().width}};
              return {width:innerWidth,scrollWidth:document.documentElement.scrollWidth,ctas:[...document.querySelectorAll('.guided-confirm-cta')].map(rect),toolbar:[...document.querySelectorAll('.model-wizard-top-actions>button')].map(n=>({width:n.getBoundingClientRect().width,height:n.getBoundingClientRect().height})),categoryTops:[...document.querySelectorAll('[name=resource_categories]')].map(n=>n.closest('label').getBoundingClientRect().top),typeTops:[...document.querySelectorAll('[name=guided_unit_type]')].map(n=>n.closest('label').getBoundingClientRect().top)};
            }''')
            self.assertLessEqual(metrics['scrollWidth'],width);self.assertEqual(len(metrics['ctas']),5)
            for key in ['width','height','rightGap','iconWidth']:self.assertLessEqual(max(c[key] for c in metrics['ctas'])-min(c[key] for c in metrics['ctas']),1,metrics)
            for key in ['padding','border','radius','font']:self.assertEqual(len({c[key] for c in metrics['ctas']}),1)
            for key in ['width','height']:self.assertLessEqual(abs(metrics['toolbar'][0][key]-metrics['toolbar'][1][key]),1)
            if width==1536:
                for key in ['categoryTops','typeTops']:self.assertLessEqual(max(metrics[key])-min(metrics[key]),1)
            self.assertGreaterEqual(min(c['height'] for c in metrics['toolbar']),44)
            heading=await self.page.locator('[name=model_name]').evaluate("n=>{const s=getComputedStyle(n.closest('.d-field').querySelector('label'),'::after');return {width:s.width,height:s.height}}")
            self.assertEqual(heading,{'width':'44px','height':'2px'})
            geometry.append(metrics)
            if width in [1536,390,320]:
                for i in range(1,6):
                    for j in range(1,6):
                        node=self.page.locator('[data-dation-test=model-v2-block-'+str(j)+']')
                        if (await node.get_attribute('open') is not None)!=(j==i):await node.locator('>summary').click()
                    await self.page.evaluate('scrollTo(0,0)')
                    await self.page.screenshot(path=str(OUT/f'actual-B0{i}-{width}.png'),full_page=True,animations='disabled')
            for i in range(1,6):await legacy.block(self.page,i)
            audits.append(await self.page.locator('[data-dation-test=core-model]').evaluate('''root=>[...root.querySelectorAll('button')].map((n,i)=>{const r=n.getBoundingClientRect();return {id:n.dataset.confirmBlock?'confirm-'+n.dataset.confirmBlock:n.dataset.dationTest||n.dataset.modelNew!==undefined&&'model-new'||'catalog-'+i,label:n.textContent.trim(),visible:!!n.getClientRects().length,disabled:n.disabled,role:n.getAttribute('role')||'button',type:n.type,component:n.closest('[data-pro-step]')?.dataset.proStep||n.closest('[data-dation-test]')?.dataset.dationTest,width:r.width,height:r.height,rightGap:n.parentElement.getBoundingClientRect().right-r.right,actionTest:'See CTA.md action-to-test mapping',pass:n.type==='button'}})'''))
        (OUT/'geometry.json').write_text(json.dumps(geometry,indent=2));(OUT/'cta-audit.json').write_text(json.dumps(audits,indent=2))
        await self.page.set_viewport_size({'width':1536,'height':1100})
        theme=await self.page.evaluate(Path(__file__).with_name('theme_audit.js').read_text(),'.model-wizard-v2')
        self.assertEqual(theme['failures'],[]);self.assertFalse(theme['overflow']);(OUT/'a11y.json').write_text(json.dumps(theme,indent=2))
        node=await legacy.block(self.page,2);radio=node.locator('[name=operating_role][value=SHIPPER]');await radio.focus();await self.page.keyboard.press('ArrowRight');await expect(node.locator('[value=LOGISTICS_PROVIDER]')).to_be_checked()
        focus=await node.locator('[value=LOGISTICS_PROVIDER]').evaluate("n=>({outline:getComputedStyle(n.closest('label')).outlineStyle,width:getComputedStyle(n.closest('label')).outlineWidth})")
        self.assertEqual(focus,{'outline':'solid','width':'2px'})
        await self.page.keyboard.press('Tab');self.assertTrue(await self.page.evaluate('document.activeElement!==document.body'))
        self.assertEqual(self.errors,[])

    async def test_06_stale_preview_retry_and_local_cta_never_publish(self):
        await self.start();first,second=await self.fill();await self.confirm()
        writes=[];previews=[]
        self.page.on('request',lambda r:writes.append(r.url) if r.method=='POST' and ('/versions' in r.url or r.url.endswith('/logistics-models')) else None)
        identity=await legacy.block(self.page,1);await identity.locator('>summary').click()
        await self.page.get_by_role('button',name='Crear nuevo modelo',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Cancelar',exact=True).click()
        name=self.page.get_by_label('Nombre del modelo *',exact=True);await legacy.block(self.page,1);await expect(name).to_have_value('QA Logistics Orange')
        await name.press('Enter');self.assertEqual(writes,[])
        entered=asyncio.Event();release=asyncio.Event()
        async def hold(route):
            body=route.request.post_data_json
            if body.get('configuration',{}).get('cargo',{}).get('presentations',[{}])[0].get('components',[{}])[0].get('quantity')=='81':
                entered.set();await release.wait()
            previews.append(body);await route.continue_()
        await self.page.route('**/logistics-models/contract-preview',hold)
        await second.get_by_label('Bultos por unidad logística *',exact=True).fill('81');await asyncio.wait_for(entered.wait(),10)
        await second.get_by_label('Bultos por unidad logística *',exact=True).fill('1.5');release.set()
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled();await expect(self.page.locator('[data-confirm-block="3"]')).to_have_attribute('data-preview-current','false')
        await second.get_by_label('Bultos por unidad logística *',exact=True).fill('80');await self.confirm()
        cta=self.page.locator('[data-confirm-block="3"]');before=len(previews);await cta.dblclick();self.assertEqual(len(previews),before);self.assertEqual(writes,[])
        await self.page.unroute('**/logistics-models/contract-preview',hold)
        async def unavailable(route):await route.fulfill(status=503,json={'detail':'QA unavailable'})
        await self.page.route('**/logistics-models/contract-preview',unavailable)
        await second.get_by_label('Bultos por unidad logística *',exact=True).fill('82')
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('QA unavailable')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await self.page.get_by_role('button',name='Reintentar Data Contract',exact=True).click()
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_be_focused()
        await self.page.unroute('**/logistics-models/contract-preview',unavailable)
        await self.page.get_by_role('button',name='Reintentar Data Contract',exact=True).click();await self.confirm()
        self.assertEqual(writes,[]);self.assertEqual(self.errors,[])


    async def test_07_dimensions_split_crud_and_confirmation_invalidation(self):
        await self.start();first,second=await self.fill();await self.confirm()
        third=self.page.locator('[data-pro-step="3"]')
        await third.locator('label').filter(has=self.page.locator('[name=dimensions][value=weight_kg]')).click()
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('1.8')
        await third.locator('label').filter(has=self.page.locator('[name=dimensions][value=volume_m3]')).click()
        await expect(self.page.locator('[data-confirm-block="3"]')).to_have_attribute('data-preview-current','false')
        await self.page.locator('[data-confirm-block="3"]').click()
        await expect(self.page.locator('[data-error-for=cargo_catalog]')).to_contain_text('dimensión principal')
        await third.locator('label').filter(has=self.page.locator('[name=dimensions][value=volume_m3]')).click()
        await third.locator('label').filter(has=self.page.locator('[name=cargo_split_policy][value=DISCRETE]')).click()
        old_id=await first.get_by_label('Presentación activa',exact=True).input_value()
        await first.get_by_role('button',name='Duplicar presentación',exact=True).click()
        clone_id=await first.get_by_label('Presentación activa',exact=True).input_value();self.assertNotEqual(old_id,clone_id)
        await expect(second.get_by_label('Nombre del producto *',exact=True)).to_be_disabled()
        await expect(second.get_by_label('Código (opcional)',exact=True)).to_be_disabled()
        await second.get_by_role('button',name='Duplicar producto',exact=True).click()
        await expect(second.get_by_label('Nombre del producto *',exact=True)).to_be_enabled()
        await second.get_by_label('Nombre del producto *',exact=True).fill('Producto copiado')
        await first.get_by_role('button',name='Eliminar presentación',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Cancelar',exact=True).click()
        await expect(first.get_by_label('Presentación activa',exact=True)).to_have_value(clone_id)
        await first.get_by_role('button',name='Eliminar presentación',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Eliminar',exact=True).click()
        await expect(first.get_by_label('Presentación activa',exact=True)).to_have_value(old_id)
        cfg=await self.publish();self.assertEqual(cfg['active_dimensions'],['volume_m3']);self.assertEqual(cfg['primary_dimension'],'volume_m3')
        self.assertEqual(cfg['cargo']['split_policy'],'DISCRETE');self.assertTrue(cfg['split_permitted'])
        self.assertEqual(len(cfg['cargo']['presentations']),1);self.assertEqual(len(cfg['cargo']['products']),2)

    async def test_08_legacy_mixed_currency_and_commercial_counts_are_not_converted(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        # Public component fixture: adversarial old draft marker, not a claimed
        # end-to-end publication. Published selection E2E is covered separately.
        data=await self.page.evaluate('''async()=>{
          const {mountModelFieldsV2}=await import('/static/js/dispatch/models/model-fields-v2.mjs');
          const configuration={version:2,operating_role:'SHIPPER',transport_pattern:'DIRECT',consolidation_permitted:false,allowed_sources:['OWN'],resource_categories:[],active_dimensions:['pallets','weight_kg'],primary_dimension:'pallets',split_permitted:false,homogeneous_loads_declared:false,currency_policy:{currency:'BRL',minor_units:5,rounding:'ROUND_HALF_UP'},own_cost_model:'OWN_OPERATING_CYCLE',external_cost_models:[],per_km_billing_bases:[],cargo:{profile:'MIXED',input_mode:'catalog',split_policy:'INDIVISIBLE',compatibility_policy:'CATEGORIZED',co_load_pairs:[['SECO','FRIO']],products:[{product_id:'A',name:'A',unit_label:'sobre',units_per_package:216,compatibility_groups:['SECO']},{product_id:'B',name:'B',unit_label:'caja',units_per_package:1,compatibility_groups:['FRIO']}],logistic_units:[{logistic_unit_id:'U',label:'Viejo',type:'PALLET',tare_mass:{value:'25',unit:'kg'}}],presentations:[{presentation_id:'MIX',label:'Mixta',quantity_kind:'DISCRETE',quantity_unit:'presentation',logistic_unit_id:'U',gross_mass:{value:'900',unit:'kg'},components:[{product_id:'A',quantity:'40'},{product_id:'B',quantity:'40'}],loaded_dimensions:{length:'120',width:'100',height:'150',unit:'cm'}}]}};
          const parent=document.querySelector('.model-wizard-v2').parentElement,form=document.createElement('form');parent.replaceChildren(form);
          const controller=new AbortController(),scope={signal:controller.signal,listen(n,t,fn){n.addEventListener(t,fn,{signal:controller.signal})},own(){}};
          window.legacyPro=mountModelFieldsV2(form,scope,{id:crypto.randomUUID(),name:'Histórico',configuration,guided_ux:{edition:'ultimate'}},{published:true});window.legacyPro.lock({published:true});return window.legacyPro.read().configuration;
        }''')
        self.assertEqual(data['currency_policy'],{'currency':'BRL','minor_units':5,'rounding':'ROUND_HALF_UP'})
        self.assertEqual(data['primary_dimension'],'pallets');self.assertEqual(data['active_dimensions'],['pallets','weight_kg'])
        self.assertEqual(data['cargo']['products'][0]['units_per_package'],216);self.assertEqual(data['cargo']['products'][0]['unit_label'],'sobre')
        self.assertEqual(data['cargo']['presentations'][0]['components'],[{'product_id':'A','quantity':'40'},{'product_id':'B','quantity':'40'}])
        self.assertEqual(data['cargo']['co_load_pairs'],[['SECO','FRIO']]);self.assertEqual(data['cargo']['presentations'][0]['gross_mass']['value'],'900')
        await expect(self.page.locator('.model-wizard-pro')).to_have_count(0)
        await expect(self.page.locator('[name=currency][value=BRL]')).to_be_checked()
        await expect(self.page.locator('.model-wizard-v2 :is(input,select,button):not(:disabled):not([data-guided-ui])')).to_have_count(0)
