"""UX 02: data preparation over the existing owned API/PostgREST/SQL sandbox."""
import asyncio
import csv
import io
import json
import unittest
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
from playwright.async_api import expect
import test_ultimate_case_setup as setup
import test_ultimate_case_data as data
import test_saga01_planning as saga
from wizard_helpers import publish_model,select_model

OUT=Path('/tmp/dation-ux02-browser')
DEMAND='transport_demand'
RESOURCES='transport_resources'


class DataContractWizardTests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(data.UltimateCaseDataTests.setUpClass.__func__)
    tearDownClass=classmethod(setup.UltimateCaseSetupTests.tearDownClass.__func__)
    login=setup.UltimateCaseSetupTests.login
    request=setup.UltimateCaseSetupTests.request
    api=setup.UltimateCaseSetupTests.api
    model=setup.UltimateCaseSetupTests.model
    case=setup.UltimateCaseSetupTests.case
    open=setup.UltimateCaseSetupTests.open
    fill_case=saga.Saga01PlanningTests.fill_case
    create=saga.Saga01PlanningTests.create

    async def asyncSetUp(self):
        await setup.UltimateCaseSetupTests.asyncSetUp(self)
        self.calls=[]
        self.page.on('request',lambda r:self.calls.append((r.method,urlparse(r.url).path,r.post_data_json if r.method=='POST' and '/logistics-models' in r.url else None)))

    async def asyncTearDown(self):
        await setup.UltimateCaseSetupTests.asyncTearDown(self)
        self.assertFalse(any(method=='POST' and (path.startswith('/api/runs') or '/execute' in path) for method,path,_ in self.calls),self.calls)

    def card(self,entity):return self.page.locator('[data-dation-test=contract-card-'+entity+']')
    def fields(self,entity):return self.page.locator('[data-dation-test=contract-fields-'+entity+']')
    def action(self,entity):return self.card(entity).get_by_role('button',name='Descargar template de '+('Órdenes / Demanda' if entity==DEMAND else 'Flota / Recursos'),exact=True)
    def next(self):return self.page.get_by_role('button',name='Continuar a Decision Case',exact=True)

    async def selected(self):
        m,v=await self.model();await self.open('/app/ddas/logistics/case')
        await select_model(self.page,m['model']['id'],v['version']['id'])
        await expect(self.next()).to_be_enabled()
        return m,v,{'model_id':m['model']['id'],'version_id':v['version']['id']}

    async def download(self,entity):
        async with self.page.expect_download() as event:await self.action(entity).click()
        result=await event.value
        self.assertEqual(result.suggested_filename,entity+'.csv')
        return Path(await result.path()).read_bytes()

    async def test_01_create_publish_contract_continue_and_case_without_download(self):
        await self.open('/app/ddas/logistics/case')
        await expect(self.page.locator('[data-dation-test=contract-continue]')).to_be_disabled()
        await publish_model(self.page,'Data Contract UX 02')
        self.assertEqual(await self.page.locator('.data-contract-card').count(),2)
        await expect(self.page.locator('[data-dation-test=core-contract]')).to_have_attribute('data-contract-state','READY')
        await expect(self.page.get_by_text('2 contratos generados para el modelo seleccionado',exact=True)).to_be_visible()
        await expect(self.page.locator('.ultimate-footer')).to_be_hidden()
        self.assertFalse(any('/templates/' in path for _,path,_ in self.calls))
        self.assertFalse(any(method=='POST' and path=='/api/platform/logistics-cases' for method,path,_ in self.calls))
        self.assertEqual(await self.next().get_attribute('type'),'button')
        before=len(self.calls);await self.next().click()
        await expect(self.page.locator('[data-dation-test=core-step-3]')).to_have_attribute('aria-current','step')
        self.assertEqual(len(self.calls),before)
        await expect(self.page.get_by_role('button',name='Finalizar configuración',exact=True)).to_be_visible()
        await self.fill_case('Preparado sin descargar CSV');cid=await self.create()
        context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context')
        self.assertEqual(context['model']['name'],'Data Contract UX 02');self.assertEqual(context['entry_count'],0)
        self.assertEqual(sum(method=='POST' and path=='/api/platform/logistics-models' for method,path,_ in self.calls),1)
        self.assertEqual(sum(method=='POST' and path.endswith('/versions') for method,path,_ in self.calls),1)
        self.assertEqual(sum(method=='POST' and path=='/api/platform/logistics-cases' for method,path,_ in self.calls),1)

    async def test_02_both_csvs_preserve_bytes_headers_source_and_immutable_version(self):
        m,_,source=await self.selected()
        before=await self.api('GET','/api/platform/logistics-models/'+m['model']['id'])
        preview=await self.api('POST','/api/platform/logistics-models/contract-preview',source)
        for entity in [DEMAND,RESOURCES]:
            expected=await self.request('POST','/api/platform/logistics-models/contract-preview/templates/'+entity,source)
            self.assertEqual(expected.status,200)
            downloaded=await self.download(entity)
            self.assertEqual(downloaded,await expected.body())
            self.assertEqual(next(csv.reader(io.StringIO(downloaded.decode()))),[f['public_header'] for f in preview['contracts'][entity]['fields']])
            calls=[body for method,path,body in self.calls if '/templates/'+entity in path]
            self.assertEqual(calls,[source])
        self.assertEqual(await self.api('GET','/api/platform/logistics-models/'+m['model']['id']),before)
        await expect(self.next()).to_be_enabled()

    async def test_03_single_independent_toggles_human_conditions_and_lossless_technical(self):
        _,_,source=await self.selected();contracts=(await self.api('POST','/api/platform/logistics-models/contract-preview',source))['contracts']
        count=len(self.calls);other=await self.card(RESOURCES).bounding_box()
        for entity in [DEMAND,RESOURCES]:
            self.assertFalse(await self.fields(entity).evaluate('n=>n.open'))
            self.assertEqual(await self.card(entity).locator('header :is(button,summary)').count(),0)
            self.assertEqual(await self.card(entity).locator('details.data-contract-fields > summary').count(),1)
        await self.fields(DEMAND).locator('> summary').focus();await self.page.keyboard.press('Enter')
        self.assertFalse(await self.fields(RESOURCES).evaluate('n=>n.open'))
        self.assertAlmostEqual((await self.card(RESOURCES).bounding_box())['height'],other['height'],delta=1)
        self.assertEqual(await self.fields(DEMAND).locator('thead th').all_text_contents(),['Campo','Descripción','Condición'])
        self.assertEqual(await self.fields(DEMAND).locator('tbody td:first-child').all_text_contents(),[f['public_header'] for f in contracts[DEMAND]['fields']])
        await self.fields(RESOURCES).locator('> summary').click()
        for key,condition in [('resource_id','Requerido'),('base_origin_id','Requerido cuando el recurso es propio'),('maximum_pallets','Opcional'),('trip_rate','Opcional · Aplica cuando el recurso es externo y la tarifa es por viaje')]:
            row=self.fields(RESOURCES).get_by_role('row').filter(has=self.page.get_by_role('cell',name=key,exact=True))
            self.assertEqual(await row.locator('td').nth(2).text_content(),condition)
        for entity in [DEMAND,RESOURCES]:
            technical=self.fields(entity).locator('.data-contract-technical')
            self.assertFalse(await technical.evaluate('n=>n.open'))
            await technical.locator('> summary').click()
            self.assertEqual(json.loads(await technical.locator('pre').text_content()),contracts[entity])
        self.assertEqual(len(self.calls),count)

    async def test_04_download_error_is_local_and_double_click_does_not_duplicate(self):
        await self.selected()
        pattern='**/contract-preview/templates/'+DEMAND
        for failure in ['503','timeout']:
            async def fail(route):
                if failure=='timeout':return await route.abort('timedout')
                await route.fulfill(status=503,json={'detail':'Fixture download unavailable'})
            await self.page.route(pattern,fail);await self.action(DEMAND).click()
            await expect(self.card(DEMAND).get_by_role('alert')).to_have_text('No se pudo descargar el template. Volvé a intentarlo.')
            await expect(self.action(RESOURCES)).to_be_enabled();await expect(self.next()).to_be_enabled()
            self.assertEqual(await self.card(RESOURCES).get_by_role('alert').count(),0)
            await self.page.unroute(pattern,fail)
        entered=asyncio.Event();release=asyncio.Event()
        async def slow(route):entered.set();await release.wait();await route.continue_()
        await self.page.route(pattern,slow)
        requests_before=len([path for _,path,_ in self.calls if '/templates/'+DEMAND in path])
        await self.action(DEMAND).click();await asyncio.wait_for(entered.wait(),12)
        await expect(self.action(DEMAND)).to_be_disabled()
        await self.action(DEMAND).evaluate('n=>{n.click();n.click();}')
        async with self.page.expect_download():release.set()
        self.assertEqual(len([path for _,path,_ in self.calls if '/templates/'+DEMAND in path]),requests_before+1)
        await expect(self.card(DEMAND).get_by_role('alert')).to_have_count(0)

    async def test_05_partial_mismatched_timeout_and_503_never_mark_ready(self):
        await self.selected();pattern='**/api/platform/logistics-models/contract-preview'
        for failure in ['partial','mismatched','timeout','503']:
            with self.subTest(failure=failure):
                async def fail(route):
                    if failure=='timeout':return await route.abort('timedout')
                    if failure=='503':return await route.fulfill(status=503,json={'detail':'Contrato no disponible'})
                    response=await route.fetch();body=await response.json()
                    if failure=='partial':body['contracts'].pop(RESOURCES)
                    else:body['contracts'][RESOURCES]['model_version_id']=str(uuid4())
                    await route.fulfill(json=body)
                await self.page.route(pattern,fail)
                self.page.on('dialog',lambda d:d.accept()) if failure=='partial' else None
                await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for()
                await self.page.locator('[data-dation-test=core-step-2]').click()
                await expect(self.page.locator('[data-dation-test=core-contract]')).to_have_attribute('data-contract-state','ERROR')
                self.assertEqual(await self.page.locator('.data-contract-card').count(),0)
                await expect(self.next()).to_be_disabled();await expect(self.page.locator('[data-dation-test=core-step-3]')).to_be_disabled()
                await self.page.unroute(pattern,fail)
                await self.page.locator('[data-dation-test=core-contract]').get_by_role('button',name='Reintentar Data Contract',exact=True).click()
                await expect(self.next()).to_be_enabled()
                self.assertEqual(await self.page.locator('.data-contract-card').count(),2)

    async def test_06_unknown_metadata_is_literal_safe_and_preserved(self):
        m,v=await self.model();pattern='**/api/platform/logistics-models/contract-preview'
        unknown='<img src=x onerror="window.contractInjected=true">'
        async def future(route):
            response=await route.fetch();body=await response.json();f=dict(body['contracts'][DEMAND]['fields'][0])
            f.update(public_header=unknown,semantic_key='future_field',nullable=False,applies_when={'future_condition':{'any':['x','y']}},validation={'future_rule':{'minimum':0,'pattern':'<script>exact</script>'}})
            body['contracts'][DEMAND]['fields'].append(f);await route.fulfill(json=body)
        await self.page.route(pattern,future);await self.open('/app/ddas/logistics/case');await select_model(self.page,m['model']['id'],v['version']['id'])
        await self.fields(DEMAND).locator('> summary').click()
        row=self.fields(DEMAND).get_by_role('row').filter(has=self.page.get_by_role('cell',name=unknown,exact=True))
        self.assertEqual(await row.locator('td').nth(1).text_content(),'Campo «'+unknown+'» del contrato seleccionado')
        self.assertEqual(await row.locator('td').nth(2).text_content(),'Requerido según condición técnica')
        self.assertFalse(await self.page.evaluate('!!window.contractInjected'));self.assertEqual(await self.card(DEMAND).locator('img,script').count(),0)
        await self.fields(DEMAND).locator('.data-contract-technical > summary').click()
        spec=json.loads(await self.fields(DEMAND).locator('pre').text_content())
        self.assertEqual(spec['fields'][-1]['applies_when'],{'future_condition':{'any':['x','y']}})
        self.assertEqual(spec['fields'][-1]['validation'],{'future_rule':{'minimum':0,'pattern':'<script>exact</script>'}})
        result=await self.page.evaluate("""async()=>{const m=await import('/static/js/dispatch/models/data-contract-view.mjs');return [m.fieldDescription({public_header:'__proto__'}),m.fieldCondition({nullable:true,applies_when:{source:'UNKNOWN'}}),m.fieldCondition({nullable:false,applies_when:{cost_model:'PER_KM'}})];}""")
        self.assertEqual(result,['Campo «__proto__» del contrato seleccionado','Opcional según condición técnica','Requerido cuando la tarifa es por kilómetro'])

    async def test_07_existing_case_uses_unchanged_contracts_and_downloads(self):
        _,_,case=await self.case();cid=case['case']['id'];before=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context')
        await self.open('/app/ddas/logistics/case?case_id='+cid);await self.page.locator('[data-dation-test=core-step-2]').click()
        self.assertEqual(await self.page.locator('.data-contract-step').count(),0)
        self.assertEqual(await self.page.locator('[data-dation-test=contract-continue]').count(),0)
        for entity,label in [(DEMAND,'Órdenes / Demanda'),(RESOURCES,'Flota / Recursos')]:
            expected=await self.request('GET','/api/platform/logistics-cases/'+cid+'/data/templates/'+entity)
            async with self.page.expect_download() as event:await self.page.get_by_role('button',name='Descargar template de '+label,exact=True).click()
            result=await event.value;self.assertEqual(Path(await result.path()).read_bytes(),await expected.body())
        await self.page.locator('[data-dation-test=core-step-3]').click()
        await expect(self.page.get_by_role('button',name='Guardar contexto',exact=True)).to_be_visible()
        self.assertEqual(await self.api('GET','/api/platform/logistics-cases/'+cid+'/context'),before)

    async def test_08_visual_responsive_focus_and_contrast(self):
        await self.selected();OUT.mkdir(exist_ok=True);measurements=[]
        for width,height in [(1536,1024),(1024,900),(768,1024),(390,844),(320,844)]:
            await self.page.set_viewport_size({'width':width,'height':height})
            for expanded in [False,True]:
                toggle=self.fields(DEMAND).locator('> summary')
                if await self.fields(DEMAND).evaluate('n=>n.open')!=expanded:await toggle.click()
                if expanded:
                    await toggle.focus();self.assertTrue(await toggle.evaluate('n=>document.activeElement===n'))
                await self.page.evaluate('scrollTo(0,0)')
                data=await self.page.evaluate('''()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,cards:[...document.querySelectorAll('.data-contract-card')].map(n=>{const b=n.getBoundingClientRect(),a=n.querySelector('button').getBoundingClientRect(),s=getComputedStyle(n);return {width:b.width,height:b.height,action:a.width,expected:b.width-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight)-2,left:a.left,right:a.right};})})''')
                self.assertLessEqual(data['scroll'],width+1,data)
                self.assertTrue(all(abs(c['action']-c['expected'])<=1 and c['left']>=0 and c['right']<=width+1 for c in data['cards']),data)
                if width>=1280 and not expanded:self.assertAlmostEqual(data['cards'][0]['height'],data['cards'][1]['height'],delta=1)
                if width>=1280:self.assertAlmostEqual(data['cards'][0]['width'],data['cards'][1]['width'],delta=1)
                self.assertFalse(await self.fields(RESOURCES).evaluate('n=>n.open'))
                if width in [1536,1024,390]:await self.page.screenshot(path=str(OUT/(f'data-contract-{width}-'+('open' if expanded else 'closed')+'.png')),full_page=True,animations='disabled')
                measurements.append({'expanded':expanded,**data})
            if await self.fields(DEMAND).evaluate('n=>n.open'):await self.fields(DEMAND).locator('> summary').click()
        await self.page.set_viewport_size({'width':1536,'height':1024})
        contrast=await self.page.evaluate((setup.ROOT/'tests/browser/theme_audit.js').read_text(),'.data-contract-step')
        self.assertEqual(contrast['failures'],[],contrast)
        (OUT/'responsive.json').write_text(json.dumps(measurements,indent=2));(OUT/'contrast.json').write_text(json.dumps(contrast,indent=2))
        self.assertTrue(await self.page.evaluate('matchMedia("(prefers-reduced-motion:reduce)").matches'))
        await self.next().focus();await self.page.keyboard.press('Enter')
        await expect(self.page.locator('[data-dation-test=core-step-3]')).to_have_attribute('aria-current','step')
        self.assertEqual(await self.page.evaluate('document.activeElement.parentElement.dataset.dationTest'),'core-case')


    async def weight_model(self):
        config=json.loads(json.dumps(setup.CONFIG));config['active_dimensions'].append('weight_kg')
        m=await self.api('POST','/api/platform/logistics-models',{'id':str(uuid4()),'name':'Con peso '+str(uuid4())[:8],'configuration':config})
        v=await self.api('POST','/api/platform/logistics-models/'+m['model']['id']+'/versions',{'version_id':str(uuid4()),'expected_revision':m['model']['revision']})
        return m,v

    async def test_09_late_preview_never_replaces_the_current_version(self):
        a,av,source=await self.selected();b,bv=await self.weight_model()
        # Reload only to include the second real model in the existing picker.
        self.page.on('dialog',lambda d:d.accept());await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for()
        entered=asyncio.Event();release=asyncio.Event();done=asyncio.Event()
        async def slow(route):
            if route.request.post_data_json.get('version_id')!=bv['version']['id']:return await route.continue_()
            response=await route.fetch();entered.set();await release.wait();await route.fulfill(response=response);done.set()
        await self.page.route('**/api/platform/logistics-models/contract-preview',slow)
        await self.page.get_by_role('button',name='Seleccionar modelo existente',exact=True).click()
        dialog=self.page.get_by_role('dialog');await dialog.get_by_label('Logistics Model',exact=True).select_option(b['model']['id'])
        await expect(dialog.get_by_role('button',name='Seleccionar esta versión',exact=True)).to_be_enabled()
        await dialog.get_by_label('Model Version',exact=True).select_option(bv['version']['id'])
        await dialog.get_by_role('button',name='Seleccionar esta versión',exact=True).click();await asyncio.wait_for(entered.wait(),12)
        self.assertEqual(await self.page.locator('.data-contract-card').count(),0)
        await expect(self.page.locator('[data-dation-test=contract-continue]')).to_be_disabled()
        await select_model(self.page,a['model']['id'],av['version']['id'])
        release.set();await asyncio.wait_for(done.wait(),12)
        await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
        await expect(self.next()).to_be_enabled();await self.fields(DEMAND).locator('> summary').click()
        self.assertNotIn('demand_weight_kg',await self.fields(DEMAND).locator('tbody td:first-child').all_text_contents())
        await self.fields(DEMAND).locator('.data-contract-technical > summary').click()
        self.assertEqual(json.loads(await self.fields(DEMAND).locator('pre').text_content())['model_version_id'],source['version_id'])

    async def test_10_download_from_previous_version_is_discarded_after_switch(self):
        a,av=await self.model();b,bv=await self.weight_model();await self.open('/app/ddas/logistics/case')
        await select_model(self.page,a['model']['id'],av['version']['id'])
        downloads=[];self.page.on('download',lambda d:downloads.append(d))
        entered=asyncio.Event();release=asyncio.Event();done=asyncio.Event()
        async def slow(route):
            response=await route.fetch();entered.set();await release.wait();await route.fulfill(response=response);done.set()
        pattern='**/contract-preview/templates/'+DEMAND
        await self.page.route(pattern,slow);await self.action(DEMAND).click();await asyncio.wait_for(entered.wait(),12)
        await self.page.locator('[data-dation-test=core-step-1]').click()
        await select_model(self.page,b['model']['id'],bv['version']['id'])
        release.set();await asyncio.wait_for(done.wait(),12)
        await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
        self.assertEqual(downloads,[])
        await self.page.unroute(pattern,slow)
        content=await self.download(DEMAND)
        self.assertIn('demand_weight_kg',next(csv.reader(io.StringIO(content.decode()))))
        self.assertEqual(len(downloads),1)
        bodies=[body for _,path,body in self.calls if path.endswith('/templates/'+DEMAND)]
        self.assertEqual([body['version_id'] for body in bodies],[av['version']['id'],bv['version']['id']])


if __name__=='__main__':unittest.main()
