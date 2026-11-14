"""UX 01: browser + owned API/PostgREST/SQL; no engines or production data."""
import asyncio
import json
import unittest
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
from playwright.async_api import expect
import test_ultimate_case_setup as setup
import test_ultimate_case_data as data
from wizard_helpers import publish_model,select_model,show_case

OUT=Path('/tmp/dation-ux01-browser')


class LogisticsModelWizardTests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(data.UltimateCaseDataTests.setUpClass.__func__)
    tearDownClass=classmethod(setup.UltimateCaseSetupTests.tearDownClass.__func__)
    async def asyncSetUp(self):
        await setup.UltimateCaseSetupTests.asyncSetUp(self)
        self.operations=[]
        self.page.on('request',lambda r:self.operations.append((r.method,urlparse(r.url).path)))

    async def asyncTearDown(self):
        await setup.UltimateCaseSetupTests.asyncTearDown(self)
        self.assertFalse(any(method=='POST' and (path.startswith('/api/runs') or '/execute' in path) for method,path in self.operations),self.operations)
    login=setup.UltimateCaseSetupTests.login
    request=setup.UltimateCaseSetupTests.request
    api=setup.UltimateCaseSetupTests.api
    model=setup.UltimateCaseSetupTests.model
    case=setup.UltimateCaseSetupTests.case
    open=setup.UltimateCaseSetupTests.open

    def track_writes(self):
        writes=[]
        self.page.on('request',lambda r:writes.append((urlparse(r.url).path,r.post_data_json)) if r.method=='POST' and (urlparse(r.url).path in ['/api/platform/logistics-models','/api/platform/logistics-cases'] or urlparse(r.url).path.endswith('/versions')) else None)
        return writes

    async def test_01_real_progress_validation_and_responsive_mockup(self):
        await self.api('POST','/api/platform/logistics-models',{'id':str(uuid4()),'name':'Sólo borrador','configuration':setup.CONFIG})
        await self.open('/app/ddas/logistics/case')
        writes=self.track_writes();progress=self.page.locator('[data-dation-test=model-progress]')
        await expect(self.page.get_by_role('button',name='Seleccionar modelo existente',exact=True)).to_be_disabled()
        await expect(self.page.get_by_text('Todavía no hay modelos publicados para reutilizar.',exact=True)).to_be_visible()
        await expect(progress).to_contain_text('2 de 3 secciones completas')
        await self.page.get_by_role('checkbox',name='Propios',exact=True).uncheck()
        await self.page.get_by_role('checkbox',name='Externos',exact=True).uncheck()
        await self.page.get_by_label('Moneda',exact=True).fill('X')
        await expect(progress).to_contain_text('0 de 3 secciones completas')
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('DATION LOGISTICS')
        await expect(progress).to_contain_text('1 de 3 secciones completas')
        await self.page.get_by_role('checkbox',name='Propios',exact=True).check()
        await expect(progress).to_contain_text('2 de 3 secciones completas')
        await self.page.get_by_label('Moneda',exact=True).fill('ARS')
        await expect(progress).to_contain_text('3 de 3 secciones completas')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_enabled()
        self.assertEqual(writes,[])
        for kind in ['identity','resources','costs']:self.assertEqual(await self.page.locator('[data-dation-test=model-card-'+kind+']').count(),1)
        self.assertEqual(await self.page.locator('[name=transport_pattern]').input_value(),'Directo · origen a destino')
        self.assertEqual(await self.page.locator('[name=billing]:checked').count(),2)
        self.assertEqual(await self.page.locator('[data-dation-test=model-version] select').count(),0)
        OUT.mkdir(exist_ok=True);measurements=[]
        for width,height in [(1536,1024),(1024,900),(768,1000),(390,844),(320,844)]:
            await self.page.set_viewport_size({'width':width,'height':height});await self.page.evaluate('scrollTo(0,0)')
            result=await self.page.evaluate('''()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,controls:[...document.querySelectorAll('.model-wizard input,.model-wizard select,.model-wizard textarea,.model-wizard button')].filter(n=>n.getClientRects().length).map(n=>({name:n.name||n.textContent,left:n.getBoundingClientRect().left,right:n.getBoundingClientRect().right}))})''')
            self.assertLessEqual(result['scroll'],width+1,result)
            self.assertTrue(all(c['left']>=0 and c['right']<=width+1 for c in result['controls']),result)
            await self.page.locator('[data-dation-test=core-model] > summary').focus()
            # Blurring the last edited field may start its contract validation.
            # Capture the actual ready state, rather than an in-flight preview.
            await expect(self.page.locator('[data-dation-test=model-create]')).to_be_enabled()
            await self.page.screenshot(path=str(OUT/f'logistics-model-{width}.png'),full_page=True,animations='disabled');measurements.append(result)
        (OUT/'responsive.json').write_text(json.dumps(measurements,indent=2))
        await self.page.set_viewport_size({'width':1536,'height':1024})
        contrast=await self.page.evaluate((setup.ROOT/'tests/browser/theme_audit.js').read_text(),'.model-wizard')
        self.assertEqual(contrast['failures'],[],contrast)
        (OUT/'contrast.json').write_text(json.dumps(contrast,indent=2))

    async def test_02_reuse_cancel_keeps_draft_and_defaults_to_new(self):
        m,v=await self.model();await self.open('/app/ddas/logistics/case?model_id='+m['model']['id']);writes=self.track_writes()
        await expect(self.page.locator('[data-dation-test=core-model]')).to_have_attribute('data-model-state','NEW_EDITING')
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Mi borrador')
        await self.page.get_by_label('Rol operativo',exact=True).select_option('HYBRID')
        await self.page.get_by_label('Descripción del modelo (opcional)',exact=True).fill('Contexto que no se pierde')
        trigger=self.page.get_by_role('button',name='Seleccionar modelo existente',exact=True)
        await trigger.click();await self.page.get_by_role('dialog').get_by_label('Logistics Model',exact=True).select_option(m['model']['id'])
        await self.page.keyboard.press('Escape');await expect(self.page.get_by_role('dialog')).to_have_count(0)
        self.assertTrue(await trigger.evaluate('n=>document.activeElement===n'))
        self.assertEqual(await self.page.get_by_label('Nombre del modelo *',exact=True).input_value(),'Mi borrador')
        self.assertEqual(await self.page.get_by_label('Rol operativo',exact=True).input_value(),'HYBRID')
        self.assertEqual(await self.page.get_by_label('Descripción del modelo (opcional)',exact=True).input_value(),'Contexto que no se pierde')
        before=await self.api('GET','/api/platform/logistics-models/'+m['model']['id'])
        await select_model(self.page,m['model']['id'],v['version']['id'])
        await self.page.locator('[data-dation-test=core-step-1]').click()
        await expect(self.page.get_by_text('Modelo seleccionado · Versión 1',exact=True)).to_be_visible()
        self.assertTrue(await self.page.get_by_label('Rol operativo',exact=True).is_disabled())
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_hidden()
        await self.page.get_by_role('button',name='Crear otro modelo',exact=True).click()
        self.assertEqual(await self.page.get_by_label('Nombre del modelo *',exact=True).input_value(),'Mi borrador')
        self.assertEqual(await self.api('GET','/api/platform/logistics-models/'+m['model']['id']),before);self.assertEqual(writes,[])

    async def test_03_double_submit_is_one_model_and_version_no_case(self):
        await self.open('/app/ddas/logistics/case');writes=self.track_writes()
        previews=[]
        self.page.on('request',lambda r:previews.append(r.post_data_json) if urlparse(r.url).path.endswith('/contract-preview') else None)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Una publicación '+str(uuid4())[:8])
        entered=asyncio.Event();release=asyncio.Event()
        async def slow(route):entered.set();await release.wait();await route.continue_()
        await self.page.route('**/api/platform/logistics-models/*/versions',slow)
        await self.page.locator('[data-dation-test=model-create]').click();await asyncio.wait_for(entered.wait(),12)
        await expect(self.page.get_by_role('button',name='Creando modelo…',exact=True)).to_be_disabled()
        await self.page.locator('[data-dation-test=model-create]').evaluate('n=>{n.click();n.click();}')
        release.set();await expect(self.page.locator('[data-dation-test=core-step-2]')).to_have_attribute('aria-current','step')
        self.assertEqual(len(writes),2,writes);self.assertTrue(writes[1][0].endswith('/versions'))
        detail=await self.api('GET','/api/platform/logistics-models/'+writes[0][1]['id'])
        self.assertEqual(len(detail['versions']),1);self.assertEqual(detail['versions'][0]['id'],writes[1][1]['version_id'])
        self.assertEqual(previews[-1],{'model_id':writes[0][1]['id'],'version_id':writes[1][1]['version_id']})
        await self.page.locator('[data-dation-test=core-step-1]').click()
        await expect(self.page.locator('[data-dation-test=model-feedback]')).to_have_text('Modelo creado y seleccionado correctamente')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_hidden()

    async def test_04_version_failure_refresh_and_same_intent_recovery(self):
        await self.open('/app/ddas/logistics/case')
        self.page.on('dialog',lambda d:d.accept())
        for status in [503,409]:
            with self.subTest(status=status):
                await self.page.evaluate('sessionStorage.clear()');await self.open('/app/ddas/logistics/case');writes=self.track_writes()
                name='Recuperable '+str(uuid4())[:8];await self.page.get_by_label('Nombre del modelo *',exact=True).fill(name)
                async def fail(route):await route.fulfill(status=status,json={'detail':'Publicación interrumpida'})
                await self.page.route('**/api/platform/logistics-models/*/versions',fail)
                await self.page.locator('[data-dation-test=model-create]').click()
                await expect(self.page.locator('[data-dation-test=model-feedback]')).to_contain_text('Publicación interrumpida')
                self.assertEqual(len(writes),2)
                await self.page.unroute('**/api/platform/logistics-models/*/versions',fail)
                if status==409:
                    # Older setup drafts locked the model before publication.
                    await self.page.evaluate('''()=>{for(const key of Object.keys(sessionStorage).filter(k=>k.startsWith('dation.ultimate.setup.v1'))){const d=JSON.parse(sessionStorage.getItem(key));d.planning_model.locked=true;sessionStorage.setItem(key,JSON.stringify(d));}}''')
                await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for()
                self.assertTrue(await self.page.get_by_label('Nombre del modelo *',exact=True).is_disabled())
                await self.page.get_by_role('button',name='Reintentar publicación pendiente',exact=True).click()
                await expect(self.page.locator('[data-dation-test=core-step-2]')).to_have_attribute('aria-current','step')
                self.assertEqual(len(writes),3,writes);self.assertEqual(writes[1],writes[2])
                models=await self.api('GET','/api/platform/logistics-models?q='+name)
                self.assertEqual(models['total'],1);self.assertEqual(len(models['items'][0]['versions']),1)

    async def test_05_lost_publication_ack_replays_exact_version(self):
        await self.open('/app/ddas/logistics/case');writes=self.track_writes()
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Respuesta perdida '+str(uuid4())[:8])
        async def lost(route):
            response=await route.fetch();self.assertEqual(response.status,200);await route.abort('timedout')
        await self.page.route('**/api/platform/logistics-models/*/versions',lost)
        await self.page.locator('[data-dation-test=model-create]').click()
        await expect(self.page.locator('[data-dation-test=model-feedback]')).to_contain_text('Publicar Logistics Model:')
        await self.page.unroute('**/api/platform/logistics-models/*/versions',lost)
        await self.page.get_by_role('button',name='Reintentar publicación pendiente',exact=True).click()
        await expect(self.page.locator('[data-dation-test=core-step-2]')).to_have_attribute('aria-current','step')
        self.assertEqual(len(writes),3);self.assertEqual(writes[1],writes[2])
        detail=await self.api('GET','/api/platform/logistics-models/'+writes[0][1]['id']);self.assertEqual(len(detail['versions']),1)

    async def test_06_stale_preview_cannot_enable_publication_or_leak_contract(self):
        await self.open('/app/ddas/logistics/case');await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Última configuración')
        entered=asyncio.Event();release=asyncio.Event();completed=asyncio.Event()
        async def slow(route):
            body=route.request.post_data_json;response=await route.fetch()
            if 'weight_kg' in body['configuration']['active_dimensions']:entered.set();await release.wait()
            await route.fulfill(response=response)
            if 'weight_kg' in body['configuration']['active_dimensions']:completed.set()
        await self.page.route('**/api/platform/logistics-models/contract-preview',slow)
        await self.page.get_by_role('checkbox',name='Peso (kg)',exact=True).check();await asyncio.wait_for(entered.wait(),12)
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await self.page.get_by_role('checkbox',name='Peso (kg)',exact=True).uncheck()
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_enabled()
        release.set();await asyncio.wait_for(completed.wait(),12);await self.page.unroute('**/api/platform/logistics-models/contract-preview',slow)
        await publish_model(self.page)
        await expect(self.page.get_by_role('cell',name='demand_weight_kg',exact=True)).to_have_count(0)
        self.assertEqual(await self.page.locator('[data-dation-test=core-contract] .ultimate-disclosure__status').text_content(),'Validado')

    async def test_07_no_model_permissions_cannot_publish_but_can_reuse(self):
        m,v=await self.model();writes=self.track_writes()
        async def limited(route):
            response=await route.fetch();caps=await response.json();caps['can_manage_models']=False;await route.fulfill(json=caps)
        await self.page.route('**/api/platform/ultimate-foundation/capabilities',limited)
        await self.open('/app/ddas/logistics/case')
        await expect(self.page.locator('[data-dation-test=core-model]')).to_have_attribute('data-model-state','READ_ONLY')
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_hidden()
        self.assertTrue(await self.page.get_by_label('Nombre del modelo *',exact=True).is_disabled())
        await select_model(self.page,m['model']['id'],v['version']['id']);await show_case(self.page)
        self.assertTrue(await self.page.get_by_label('Nombre del Case',exact=True).is_enabled());self.assertEqual(writes,[])

    async def test_08_new_model_after_publication_keeps_old_version_immutable(self):
        await self.open('/app/ddas/logistics/case');writes=self.track_writes();await publish_model(self.page,'Primero '+str(uuid4())[:8])
        first=await self.api('GET','/api/platform/logistics-models/'+writes[0][1]['id'])
        await self.page.locator('[data-dation-test=core-step-1]').click();await self.page.get_by_role('button',name='Crear otro modelo',exact=True).click()
        await self.page.get_by_label('Rol operativo',exact=True).select_option('HYBRID');await publish_model(self.page,'Segundo '+str(uuid4())[:8])
        self.assertEqual(len(writes),4);self.assertNotEqual(writes[0][1]['id'],writes[2][1]['id'])
        self.assertEqual(await self.api('GET','/api/platform/logistics-models/'+first['model']['id']),first)


    async def test_09_lost_create_ack_recovers_same_model_identity(self):
        await self.open('/app/ddas/logistics/case');writes=self.track_writes()
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Creación confirmada sin respuesta '+str(uuid4())[:8])
        async def lost(route):
            if route.request.method!='POST':return await route.continue_()
            response=await route.fetch();self.assertEqual(response.status,200);await route.abort('timedout')
        await self.page.route('**/api/platform/logistics-models',lost)
        await self.page.locator('[data-dation-test=model-create]').click()
        await expect(self.page.locator('[data-dation-test=model-feedback]')).to_contain_text('Publicar Logistics Model:')
        await self.page.unroute('**/api/platform/logistics-models',lost)
        await self.page.get_by_role('button',name='Reintentar publicación pendiente',exact=True).click()
        await expect(self.page.locator('[data-dation-test=core-step-2]')).to_have_attribute('aria-current','step')
        self.assertEqual(len(writes),3);self.assertEqual(writes[0],writes[1])
        detail=await self.api('GET','/api/platform/logistics-models/'+writes[0][1]['id']);self.assertEqual(len(detail['versions']),1)

    async def test_10_confirmed_publication_failed_selection_can_be_recovered(self):
        await self.open('/app/ddas/logistics/case');writes=self.track_writes()
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Selección recuperable '+str(uuid4())[:8])
        async def fail(route):
            if route.request.method!='GET':return await route.continue_()
            await route.fulfill(status=503,json={'detail':'Lectura temporalmente no disponible'})
        await self.page.route('**/api/platform/logistics-models/*',fail)
        await self.page.locator('[data-dation-test=model-create]').click()
        await expect(self.page.locator('[data-dation-test=model-feedback]')).to_contain_text('Lectura temporalmente no disponible')
        await self.page.unroute('**/api/platform/logistics-models/*',fail)
        await self.page.get_by_role('button',name='Reintentar selección del modelo',exact=True).click()
        await expect(self.page.locator('[data-dation-test=core-step-2]')).to_have_attribute('aria-current','step')
        self.assertEqual(len(writes),2)
        self.assertEqual(writes[1][0],'/api/platform/logistics-models/'+writes[0][1]['id']+'/versions')

    async def test_11_sidebar_keeps_case_inputs_and_keyboard_picker_focus(self):
        m,v=await self.model();await self.open('/app/ddas/logistics/case')
        trigger=self.page.get_by_role('button',name='Seleccionar modelo existente',exact=True)
        await trigger.focus();await self.page.keyboard.press('Enter')
        dialog=self.page.get_by_role('dialog');await expect(dialog).to_be_visible()
        self.assertEqual(await self.page.evaluate('document.activeElement.name'),'reuse_model')
        for _ in range(8):
            await self.page.keyboard.press('Tab')
            self.assertTrue(await self.page.evaluate('!!document.activeElement.closest("dialog")'))
        await self.page.keyboard.press('Escape');self.assertTrue(await trigger.evaluate('n=>document.activeElement===n'))
        await select_model(self.page,m['model']['id'],v['version']['id']);await show_case(self.page)
        await self.page.get_by_label('Nombre del Case',exact=True).fill('Conservado entre etapas')
        await self.page.get_by_label('Inicio de planificación',exact=True).fill('2026-11-02')
        for step in [1,2,3]:
            control=self.page.locator('[data-dation-test=core-step-'+str(step)+']')
            await control.focus();await self.page.keyboard.press('Enter')
            await expect(control).to_have_attribute('aria-current','step')
            self.assertEqual(await self.page.evaluate('document.activeElement.parentElement.dataset.dationTest'),['core-model','core-contract','core-case'][step-1])
        self.assertEqual(await self.page.get_by_label('Nombre del Case',exact=True).input_value(),'Conservado entre etapas')
        self.assertEqual(await self.page.get_by_label('Inicio de planificación',exact=True).input_value(),'2026-11-02')
        self.assertEqual(await self.page.locator('.ultimate-foundation form').count(),1)

    async def test_12_unavailable_version_never_selects_another_by_default(self):
        m,v=await self.model();await self.model('Alternativa que no se elige automáticamente')
        await self.open('/app/ddas/logistics/case');writes=self.track_writes()
        await select_model(self.page,m['model']['id'],v['version']['id'])
        async def missing(route):await route.fulfill(status=404,json={'detail':'Versión temporalmente no disponible'})
        path='**/api/platform/logistics-models/'+m['model']['id']
        await self.page.route(path,missing)
        self.page.on('dialog',lambda d:d.accept());await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for()
        await expect(self.page.locator('[data-dation-test=model-feedback]')).to_have_text('Versión temporalmente no disponible')
        await expect(self.page.locator('[data-dation-test=core-step-3]')).to_be_disabled()
        await self.page.unroute(path,missing)
        await self.page.get_by_role('button',name='Reintentar selección del modelo',exact=True).click()
        await expect(self.page.locator('[data-dation-test=core-step-2]')).to_have_attribute('aria-current','step')
        await self.page.locator('[data-dation-test=core-step-1]').click()
        await expect(self.page.locator('.model-wizard-selection h3')).to_have_text(m['model']['name'])
        self.assertEqual(writes,[])


if __name__=='__main__':unittest.main()
