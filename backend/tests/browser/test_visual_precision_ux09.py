"""UX09 precision over the existing isolated Journey API/SQL/browser fixtures."""
import asyncio,json,unittest
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit
from playwright.async_api import expect,Error as PlaywrightError
import test_journey_navigation_ux06 as nav
import test_unified_decision_journey as journey
from wizard_helpers import publish_model,select_model

OUT=Path('/tmp/dation-ux09-browser');OUT.mkdir(exist_ok=True)
VIEWS={1536:900,1280:800,1024:768,768:900,390:844,320:740}
METRICS=[]
AUDIT=(Path(__file__).parent/'theme_audit.js').read_text()
RECTS="""()=>{const r=n=>n?.getBoundingClientRect().toJSON(),v=n=>n.getClientRects().length;const footer=[...document.querySelectorAll('.journey-step-footer')].find(v),context=footer?.querySelector('.journey-step-context'),row=document.querySelector('.journey-session-row'),cards=row?[...row.children]:[],meta=document.querySelector('.ux08-node-meta');return {viewport:{width:innerWidth,height:innerHeight},footer:r(footer),footerRows:footer&&getComputedStyle(footer).gridTemplateRows,context:r(context),contextBorders:context&&[getComputedStyle(context).borderLeftWidth,getComputedStyle(context).borderRightWidth],feedback:context?.textContent,previous:r(footer?.querySelector('[data-journey-previous]')),ring:r(footer?.querySelector('.model-wizard-ring,.data-contract-ring,.decision-case-ring')),actions:footer?[...footer.querySelectorAll('.journey-step-actions>button')].filter(v).map(n=>({text:n.textContent,rect:r(n)})):[],cards:cards.map(n=>({rect:r(n),icon:r(n.querySelector('.decision-case-tile')),title:r(n.querySelector('h3')),font:getComputedStyle(n.querySelector('h3')).font,copyFont:getComputedStyle(n.querySelector('.decision-case-rail p')).font,padding:getComputedStyle(n).padding,radius:getComputedStyle(n).borderRadius,border:getComputedStyle(n).borderTop,select:r(n.querySelector('select'))})),row:r(row),caseStatus:r(document.querySelector('.ux08-case-status')),caseColumn:r(document.querySelector('.ux08-case-status')?.parentElement),header:r(document.querySelector('.ux08-node-header')),state:r(meta?.children[0]),output:r(meta?.children[1]),badge:r(document.querySelector('.ux08-panel-state')),outputBox:r(document.querySelector('.ux09-output-box')),close:r(document.querySelector('.ux05-panel-close')),circles:[...document.querySelectorAll('.ux05-node-button,.ux05-future-circle')].map(r),scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth}}"""

class VisualPrecisionTests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(nav.JourneyNavigationTests.setUpClass.__func__)
    tearDownClass=classmethod(nav.JourneyNavigationTests.tearDownClass.__func__)
    asyncSetUp=nav.JourneyNavigationTests.asyncSetUp
    sql=nav.JourneyNavigationTests.sql
    login=nav.JourneyNavigationTests.login
    request=nav.JourneyNavigationTests.request
    api=nav.JourneyNavigationTests.api
    model=nav.JourneyNavigationTests.model
    case=nav.JourneyNavigationTests.case
    graph=nav.JourneyNavigationTests.graph
    ready=nav.JourneyNavigationTests.ready
    fill_case=journey.UnifiedDecisionJourneyTests.fill_case
    attach=journey.UnifiedDecisionJourneyTests.attach
    async def asyncTearDown(self):
        result=self._outcome.result
        if any(test is self for test,_ in result.failures+result.errors):
            await self.page.screenshot(path=str(OUT/(self._testMethodName+'-failure.png')),full_page=True)
        await nav.JourneyNavigationTests.asyncTearDown(self)
    async def measure(self,scene,shot=False):
        await self.page.evaluate('document.fonts.ready');await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
        d=await self.page.evaluate(RECTS);d['scene']=scene;d['path']=urlsplit(self.page.url).path;d['test']=self._testMethodName
        METRICS.append(d);(OUT/'geometry-after.json').write_text(json.dumps(METRICS,indent=2))
        (OUT/(self._testMethodName+'-geometry.json')).write_text(json.dumps([item for item in METRICS if item['test']==self._testMethodName],indent=2))
        self.assertLessEqual(d['scroll'],d['client'],d)
        audit=await self.page.evaluate(AUDIT);self.assertEqual(audit['failures'],[],(scene,audit['failures']))
        if shot:
            await self.page.mouse.move(0,0);await self.page.evaluate('document.activeElement?.blur();scrollTo(0,0)')
            await self.page.screenshot(path=str(OUT/(scene+'.png')),full_page=True,animations='disabled')
        return d
    async def focus_sessions(self):
        async with self.page.expect_request(lambda r:r.method=='GET' and r.url.endswith('/api/platform/data-preparations')):
            await self.page.evaluate("dispatchEvent(new Event('focus'))")
        await expect(self.page.locator('#journey-session-availability')).not_to_contain_text('Consultando')
    async def test_01_complete_journey_precision_and_stable_node_tracks(self):
        await self.page.set_viewport_size({'width':1536,'height':900});await self.page.emulate_media(reduced_motion='reduce')
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await self.page.locator('[name=currency]').fill('')
        for value in ['OWN','EXTERNAL']:await self.page.locator('[name=sources][value='+value+']').uncheck()
        await expect(self.page.locator('.model-wizard-progress')).to_contain_text('0 de 3')
        await expect(self.page.get_by_role('button',name='Guardar y continuar',exact=True)).to_be_disabled();await self.measure('core01-zero-1536',True)
        await self.page.locator('[name=currency]').fill('ARS')
        await expect(self.page.locator('.model-wizard-progress')).to_contain_text('1 de 3');await self.measure('core01-partial-1536',True)
        for value in ['OWN','EXTERNAL']:await self.page.locator('[name=sources][value='+value+']').check()
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Modelo de precisión UX09')
        await expect(self.page.locator('.model-wizard-progress')).to_contain_text('3 de 3')
        metrics=[]
        async def footer(step,tag):
            for width,height in VIEWS.items():
                await self.page.set_viewport_size({'width':width,'height':height});d=await self.measure('core0'+str(step)+'-'+tag+'-'+str(width),width in [1536,390]);metrics.append((step,tag,width,d))
                for key in ['previous','ring']:
                    self.assertAlmostEqual(d[key]['width'],44,delta=.1);self.assertAlmostEqual(d[key]['height'],44,delta=.1)
                self.assertTrue(all(x['rect']['height']>=44 for x in d['actions']),d)
                if width<=390 and step==1 and not d['feedback']:
                    self.assertLessEqual(len(d['footerRows'].split()),2,d)
                if width>=1280:
                    self.assertAlmostEqual(d['footer']['height'],96,delta=8,msg=d)
                    self.assertEqual(len(d['footerRows'].split()),1,d)
                    self.assertEqual(d['contextBorders'],['1px','1px'])
                    if step==2:self.assertEqual(len(d['actions']),2);self.assertAlmostEqual(d['actions'][0]['rect']['y'],d['actions'][1]['rect']['y'],delta=1)
            await self.page.set_viewport_size({'width':1536,'height':900})
        await footer(1,'ready')
        async with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/versions')) as published:await publish_model(self.page)
        v=await (await published.value).json();self.m={'model':{'id':v['version']['model_id']}};self.v={'version':{'id':v['version']['id']}}
        await self.ready(2);await expect(self.page.locator('#journey-session-availability')).to_contain_text('No hay otras sesiones')
        await expect(self.page.get_by_role('button',name='Ver sesiones',exact=True)).to_be_disabled()
        await footer(2,'empty');await expect(self.page.locator('[data-journey-next]')).to_be_disabled()
        await self.attach('transport_demand');await expect(self.page.locator('.journey-step-context:visible')).to_contain_text('Falta Flota')
        await expect(self.page.locator('[data-journey-next]')).to_be_disabled();await self.measure('core02-one-candidate-1536',True)
        await self.attach('transport_resources');await expect(self.page.locator('[data-journey-next]')).to_be_enabled()
        await footer(2,'validated')
        for _,_,width,d in [x for x in metrics if x[0]==2]:
            if width>=1280:
                a,b=d['cards'];self.assertAlmostEqual(a['rect']['height'],b['rect']['height'],delta=1)
                ratio=a['rect']['width']/(a['rect']['width']+b['rect']['width']);self.assertTrue(.65<=ratio<=.70,(width,ratio))
                for key in ['font','copyFont','padding','radius','border']:self.assertEqual(a[key],b[key],(key,d))
                for card in [a,b]:self.assertEqual(round(card['icon']['width']),48);self.assertEqual(round(card['icon']['height']),48)
                self.assertAlmostEqual(d['footer']['top']-d['row']['bottom'],22,delta=1)
                self.assertEqual(round(a['select']['height']),40)
        await self.page.locator('[data-journey-next]').click();await self.ready(3)
        await expect(self.page.locator('[data-dation-test=case-progress]')).to_contain_text('2 de 5');await self.measure('core03-partial-1536',True)
        await self.fill_case('Case de precisión UX09');await expect(self.page.locator('[data-dation-test=case-progress]')).to_contain_text('5 de 5');await footer(3,'ready')
        for width in [1536,1280]:
            heights=[d['footer']['height'] for step,tag,w,d in metrics if w==width];self.assertLess(max(heights)-min(heights),2,heights)
        await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click();await self.page.locator('[data-ux05-ready=true]').wait_for()
        await expect(self.page.locator('.ux05-case-facts>div')).to_have_count(4);await expect(self.page.locator('.ux05-toolbar-actions button')).to_have_count(5)
        for width,height in VIEWS.items():
            await self.page.set_viewport_size({'width':width,'height':height});d=await self.measure('case-header-'+str(width),width in [1536,390]);self.assertAlmostEqual(d['caseStatus']['width'],d['caseColumn']['width'],delta=1);self.assertGreaterEqual(d['caseStatus']['height'],36)
            node_metrics=[]
            for node,short in [('logistics_assignment','d1'),('logistics_scheduling','d2')]:
                trigger=self.page.locator('[data-ux05-node='+node+']');await trigger.click();await expect(self.page.locator('.ux08-node-header')).to_be_visible()
                m=await self.measure('graph-'+short+'-'+str(width),width in [1536,390]);node_metrics.append(m)
                await expect(self.page.locator('.ux09-output-box :is(button,a)')).to_have_count(0)
                for h in await self.page.locator('.ux05-panel-grid>section>h3').all():
                    svg=h.locator('svg');await expect(svg).to_have_attribute('aria-hidden','true');icon=await svg.bounding_box()
                    for size in ['width','height']:self.assertAlmostEqual(icon[size],22,delta=.1)
                header_styles=await self.page.locator('.ux05-panel-grid>section>h3').evaluate_all('(nodes)=>nodes.map(n=>{const s=getComputedStyle(n);return {font:s.font,gap:s.gap}})')
                self.assertEqual(len(header_styles),3);self.assertTrue(all(style==header_styles[0] for style in header_styles),header_styles)
                await expect(self.page.locator('.ux08-state-detail')).to_have_count(1)
                if width>=1280:
                    for key in ['badge','outputBox']:self.assertAlmostEqual(m[key]['height'],40,delta=.1)
                if short=='d2':await expect(self.page.locator('.ux08-panel-state')).to_have_text('Bloqueada');await expect(self.page.locator('.ux05-panel [data-ux05-action=configure]')).to_have_count(0)
                await self.page.keyboard.press('Escape');await expect(trigger).to_be_focused()
            for key in ['state','output','badge','outputBox','close']:
                self.assertAlmostEqual(node_metrics[0][key]['x'],node_metrics[1][key]['x'],delta=1,msg=(width,key,node_metrics))
                self.assertAlmostEqual(node_metrics[0][key]['width'],node_metrics[1][key]['width'],delta=1)
            self.assertAlmostEqual(node_metrics[0]['outputBox']['height'],node_metrics[1]['outputBox']['height'],delta=1)
        await self.page.set_viewport_size({'width':1440,'height':900});await self.page.evaluate('document.documentElement.style.zoom="2"')
        await self.page.locator('[data-ux05-node=logistics_scheduling]').click();await self.measure('graph-zoom200',True)

    async def selected(self):
        self.m,self.v=await self.model('Sesiones de precisión UX09')
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await select_model(self.page,self.m['model']['id'],self.v['version']['id']);await self.ready(2)
        await expect(self.page.locator('#journey-session-availability')).to_contain_text('No hay otras sesiones')
        return self.m,self.v
    async def test_02_sessions_availability_errors_recovery_and_pending_files(self):
        m,v=await self.selected();picker=self.page.get_by_role('button',name='Ver sesiones',exact=True);note=self.page.locator('#journey-session-availability')
        await expect(picker).to_be_disabled();original=(await self.api('GET','/api/platform/data-preparations'))['items'][0]['id']
        for width in [1536,390]:
            await self.page.set_viewport_size({'width':width,'height':VIEWS[width]});await self.measure('data-sessions-empty-'+str(width),True)
        alt=str(uuid4());await self.api('POST','/api/platform/data-preparations',{'id':alt,'model_version_id':v['version']['id']})
        await self.focus_sessions();await expect(note).to_have_text('1 sesión disponible');await expect(picker).to_be_enabled()
        for width in [1536,390]:
            await self.page.set_viewport_size({'width':width,'height':VIEWS[width]});await picker.click();await expect(self.page.locator('.journey-resume-list button')).to_have_count(1);await self.measure('data-sessions-available-'+str(width),True)
        await self.page.locator('[data-preparation-id="'+alt+'"]').click()
        await expect(note).to_have_text('1 sesión disponible');await expect(self.page.get_by_label('Data Owner',exact=True)).to_be_enabled()
        async with self.page.expect_response(lambda r:r.request.method=='PUT' and '/'+alt+'/owner' in r.url) as response:
            await self.page.get_by_label('Data Owner',exact=True).select_option(nav.setup.ADMIN)
        body=(await response.value).request.post_data_json;self.assertEqual(body['data_owner_user_id'],nav.setup.ADMIN);self.assertIn('expected_revision',body)
        self.assertTrue((await response.value).ok);await expect(note).not_to_contain_text('Consultando')
        second=str(uuid4());await self.api('POST','/api/platform/data-preparations',{'id':second,'model_version_id':v['version']['id']})
        items=(await self.api('GET','/api/platform/data-preparations'))['items']
        extra=[]
        for status in ['EXPIRED','CONSUMED','UNKNOWN']:
            extra.append(dict(items[0],id=str(uuid4()),status=status))
        extra.extend([dict(items[0],id=str(uuid4()),expires_at='2020-01-01T00:00:00Z'),dict(items[0],id=str(uuid4()),model_version_id=str(uuid4())),dict(items[0],id=str(uuid4()),parent_case_id=str(uuid4()))])
        pattern='**/api/platform/data-preparations'
        async def mixed(route):await route.fulfill(json={'items':items+extra})
        await self.page.route(pattern,mixed);await self.focus_sessions();await expect(note).to_have_text('2 sesiones disponibles');await picker.click()
        choices=self.page.locator('.journey-resume-list button');await expect(choices).to_have_count(2)
        self.assertEqual(set(await choices.evaluate_all('ns=>ns.map(n=>n.dataset.preparationId)')),{original,second})
        text=await self.page.locator('.journey-resume-list').inner_text();self.assertNotRegex(text,r'[0-9a-f]{8}-[0-9a-f-]{27,}');self.assertNotIn('2026-',text);self.assertIn('Borrador',text)
        await self.page.unroute(pattern,mixed)
        for kind in ['403','503','timeout','partial','duplicate']:
            async def fail(route):
                if kind=='timeout':return await route.abort('timedout')
                if kind=='partial':return await route.fulfill(json={'items':[{'id':alt}]})
                if kind=='duplicate':return await route.fulfill(json={'items':[items[0],items[0]]})
                await route.fulfill(status=int(kind),json={'detail':'Consulta de sesiones no disponible'})
            await self.page.route(pattern,fail,times=1);await self.focus_sessions()
            await expect(note).to_have_attribute('role','alert');await expect(note).to_contain_text('No se pudieron verificar sesiones');await expect(picker).to_be_disabled();self.assertFalse(await picker.evaluate('n=>n.hasAttribute("aria-controls")'))
            await expect(self.page.locator('[data-journey-skip]')).to_be_enabled();await expect(self.page.get_by_label('Data Owner',exact=True)).to_be_enabled()
            if kind in ['403','503']:
                width=390 if kind=='403' else 1536;await self.page.set_viewport_size({'width':width,'height':VIEWS[width]})
                d=await self.measure('data-sessions-error-'+kind+'-'+str(width),True);self.assertAlmostEqual(d['footer']['top']-d['row']['bottom'],22,delta=1)
            await self.page.get_by_role('button',name='Reintentar sesiones',exact=True).click();await expect(note).to_have_text('2 sesiones disponibles');await expect(note).to_have_attribute('role','status')
        # A failed/mismatched selected-resource read must not change the draft.
        for failure in ['503','identity']:
            async def bad_selected(route):
                if failure=='503':return await route.fulfill(status=503,json={'detail':'No se pudo verificar la sesión seleccionada'})
                response=await route.fetch();body=await response.json();body['session']['id']=second;await route.fulfill(json=body)
            await self.page.route('**/api/platform/data-preparations/'+original,bad_selected,times=1)
            await picker.click();await expect(choices).to_have_count(2)
            posts=[]
            def track(request):
                if request.method=='POST' and request.url.endswith('/api/platform/data-preparations'):posts.append(request.url)
            self.page.on('request',track)
            await self.page.locator('[data-preparation-id="'+original+'"]').click();await expect(note).to_have_attribute('role','alert')
            self.assertEqual(posts,[]);self.page.remove_listener('request',track)
            await expect(self.page.get_by_label('Data Owner',exact=True)).to_have_value(nav.setup.ADMIN)
            await self.page.get_by_role('button',name='Reintentar sesiones',exact=True).click();await expect(note).to_have_text('2 sesiones disponibles')
        self.page.on('dialog',lambda d:d.accept())
        async with self.page.expect_request(lambda request:request.method=='POST' and request.url.endswith('/api/platform/data-preparations') and request.post_data_json['id']==alt):await self.page.reload()
        await self.ready(2);await expect(self.page.get_by_label('Data Owner',exact=True)).to_have_value(nav.setup.ADMIN)
        await expect(note).to_have_text('2 sesiones disponibles');await picker.click();await expect(choices).to_have_count(2)
        raw=await self.request('POST','/api/platform/logistics-models/contract-preview/templates/transport_demand',{'model_id':m['model']['id'],'version_id':v['version']['id']})
        host=self.page.locator('[data-preparation-entity=transport_demand]');await host.locator('input[type=file]').set_input_files({'name':'pending.csv','mimeType':'text/csv','buffer':await raw.body()})
        await expect(host.get_by_role('button',name='Guardar candidato de Órdenes / Demanda',exact=True)).to_be_enabled()
        calls=[];self.page.on('request',lambda r:calls.append((r.method,r.url)) if '/api/platform/data-preparations' in r.url else None)
        await picker.click();await choices.first.click();await expect(self.page.locator('.journey-preparation-status')).to_contain_text('Guardá o quitá los archivos locales')
        self.assertEqual(calls,[]);self.assertTrue(await host.locator('input[type=file]').evaluate('n=>n.files[0].name==="pending.csv"'))
    async def test_03_stale_lookup_cancellation_and_version_switch(self):
        a,av=await self.model('Versión A UX09');b,bv=await self.model('Versión B UX09')
        alt_a=str(uuid4());alt_b=str(uuid4())
        for pid,version in [(alt_a,av),(alt_b,bv)]:await self.api('POST','/api/platform/data-preparations',{'id':pid,'model_version_id':version['version']['id']})
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1);await select_model(self.page,a['model']['id'],av['version']['id']);await self.ready(2)
        note=self.page.locator('#journey-session-availability');await expect(note).to_have_text('1 sesión disponible')
        entered=asyncio.Event();release=asyncio.Event();done=asyncio.Event()
        async def old(route):
            response=await route.fetch();entered.set();await release.wait()
            try:await route.fulfill(response=response)
            except PlaywrightError:pass # The model switch deliberately aborts this exact lookup.
            finally:done.set()
        await self.page.route('**/api/platform/data-preparations',old,times=1)
        await self.page.evaluate("dispatchEvent(new Event('focus'))");await asyncio.wait_for(entered.wait(),12)
        await self.page.locator('[data-dation-test=core-step-1]').click();await select_model(self.page,b['model']['id'],bv['version']['id'])
        await self.page.get_by_role('dialog').get_by_role('button',name='Preparar esta versión',exact=True).click()
        await expect(note).to_have_text('1 sesión disponible');release.set();await asyncio.wait_for(done.wait(),12)
        await self.page.get_by_role('button',name='Ver sesiones',exact=True).click();choices=self.page.locator('.journey-resume-list button');await expect(choices).to_have_count(1)
        self.assertEqual(await choices.first.get_attribute('data-preparation-id'),alt_b)
        await self.page.locator('[data-journey-skip]').click();await self.ready(3);calls=[]
        self.page.on('request',lambda r:calls.append(r.url) if r.method=='GET' and r.url.endswith('/api/platform/data-preparations') else None)
        for value in ['A','AB','ABC','ABCD']:await self.page.get_by_label('Nombre del Case',exact=True).fill(value)
        self.assertEqual(calls,[])
        # A late lookup also cannot repaint the next SPA view after disposal.
        entered.clear();release.clear();done.clear();await self.page.route('**/api/platform/data-preparations',old,times=1)
        await self.page.evaluate("dispatchEvent(new Event('focus'))");await asyncio.wait_for(entered.wait(),12)
        self.page.on('dialog',lambda d:d.accept());await self.page.locator('.nav [data-platform-view=platform-home]').click()
        await self.page.locator('.platform-home__greeting').wait_for();release.set();await asyncio.wait_for(done.wait(),12)
        await expect(self.page.locator('[data-dation-test=preparation-sessions-card]')).to_have_count(0);self.assertEqual(await self.page.evaluate('window.dationGetCurrentView()'),'platform-home')

    async def test_04_live_save_error_conflict_and_recovery_stay_accessible(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.page.goto(self.base+'/app/ddas/logistics/case?case_id='+cid);await self.ready(3)
        context=self.page.locator('.journey-step-context:visible');status=context.locator('p[aria-live=polite]')
        await expect(status).to_have_text('Sin cambios pendientes.');await expect(status).to_have_attribute('role','status')
        await self.page.get_by_label('Nombre del Case',exact=True).fill('Cambios UX09 guardados')
        await expect(status).to_have_text('Cambios sin guardar. El borrador se conserva en este navegador.')
        entered=asyncio.Event();release=asyncio.Event()
        pattern='**/api/platform/logistics-cases/'+cid+'/context'
        async def hold(route):
            if route.request.method!='PATCH':return await route.continue_()
            response=await route.fetch();entered.set();await release.wait();await route.fulfill(response=response)
        await self.page.route(pattern,hold)
        await self.page.get_by_role('button',name='Guardar contexto',exact=True).click();await asyncio.wait_for(entered.wait(),12)
        await expect(status).to_have_text('Guardando…');await self.measure('footer-saving-1536',True);release.set()
        await self.page.locator('[data-ux05-ready=true]').wait_for();await self.page.unroute(pattern,hold)
        await self.page.get_by_role('button',name='Editar Decision Case',exact=True).click();await self.ready(3)
        await expect(status).to_have_text('Sin cambios pendientes.')
        self.assertEqual((await self.api('GET','/api/platform/logistics-cases/'+cid+'/context'))['case']['label'],'Cambios UX09 guardados')
        for code,message in [(503,'La operación no pudo confirmarse. '+('El borrador se conserva y puede revisarse antes de reintentar. '*8)),(409,'La versión cambió')]:
            async def fail(route):
                if route.request.method=='PATCH':return await route.fulfill(status=code,json={'detail':message})
                await route.continue_()
            await self.page.route(pattern,fail)
            await self.page.get_by_label('Nombre del Case',exact=True).fill('Borrador UX09 '+str(code));await self.page.get_by_role('button',name='Guardar contexto',exact=True).click()
            await expect(status).to_have_attribute('role','alert')
            if code==503:await expect(status).to_have_text(message)
            else:await expect(context.get_by_role('button',name='Descartar borrador y recargar',exact=True)).to_be_visible()
            for width in [1536,1280,390,320]:
                await self.page.set_viewport_size({'width':width,'height':VIEWS[width]});await self.measure('footer-error-'+str(code)+'-'+str(width),width in [1536,390])
                self.assertGreater(await status.evaluate('n=>n.getBoundingClientRect().height'),0)
            await self.page.unroute(pattern,fail)
        reload=context.get_by_role('button',name='Descartar borrador y recargar',exact=True);await reload.focus();self.assertEqual(await reload.evaluate('n=>getComputedStyle(n).outlineWidth'),'3px')
        await reload.click();await self.page.get_by_role('dialog').get_by_role('button',name='Cancelar',exact=True).click()
        await expect(self.page.get_by_label('Nombre del Case',exact=True)).to_have_value('Borrador UX09 409')
        await reload.click();await self.page.get_by_role('dialog').get_by_role('button',name='Descartar y recargar',exact=True).click()
        await expect(self.page.get_by_label('Nombre del Case',exact=True)).to_have_value('Cambios UX09 guardados')
        await expect(self.page.locator('.journey-step-context:visible [role=status]')).to_have_text('Sin cambios pendientes.')
        await self.page.set_viewport_size({'width':1440,'height':900});await self.page.evaluate('document.documentElement.style.zoom="2"');await self.measure('footer-zoom200',True)
    async def test_05_graph_stress_labels_output_and_frozen_session_guard(self):
        m,v,c=await self.case();cid=c['case']['id'];await self.graph(cid)
        for width,height in VIEWS.items():
            await self.page.set_viewport_size({'width':width,'height':height})
            await self.page.evaluate('document.fonts.ready');await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
            badge=self.page.locator('.ux08-case-status');initial=await badge.text_content();rect=await badge.bounding_box()
            # Presentation-only long-label fixture: source state derivation remains tested by UX05.
            for label in ['En progreso','Listo para cerrar','Archivado','Cerrado']:
                await badge.evaluate('(n,text)=>n.textContent=text',label);current=await badge.bounding_box();self.assertAlmostEqual(current['width'],rect['width'],delta=.1,msg=(width,label,rect,current));self.assertGreaterEqual(current['height'],36)
                if width>=768:self.assertAlmostEqual(current['height'],36,delta=.1)
            await badge.evaluate('(n,text)=>n.textContent=text',initial)
            await self.page.locator('[data-ux05-node=logistics_assignment]').click();await expect(self.page.locator('.ux08-state-detail')).to_have_text('Requiere completar datos')
            before=await self.page.evaluate(RECTS)
            long='Resultado desactualizado. '+('El contexto consumido cambió; se conserva el historial. '*5)
            await self.page.locator('.ux08-state-detail').evaluate('(n,text)=>n.textContent=text',long)
            await self.page.locator('.ux08-node-identity h2').evaluate('(n)=>n.textContent+=" · Identidad extensa para comprobar geometría sin mover las zonas"')
            after=await self.measure('graph-long-label-'+str(width),width in [1536,390])
            for key in ['state','output','close']:
                self.assertAlmostEqual(before[key]['x'],after[key]['x'],delta=.1);self.assertAlmostEqual(before[key]['width'],after[key]['width'],delta=.1)
            await expect(self.page.locator('.ux08-state-detail')).to_have_text(long)
            await self.page.get_by_role('button',name='Cerrar panel',exact=True).click()
            trigger=self.page.locator('[data-ux05-node=logistics_scheduling]');await trigger.click();await trigger.click();await expect(self.page.locator('.ux05-panel')).to_have_count(0)
            await trigger.press('Enter');await self.page.get_by_role('heading',name='Decision Studio',exact=True).click();await expect(self.page.locator('.ux05-panel')).to_have_count(0)
        # A frozen current session keeps the pre-existing creation-intent guard.
        other=str(uuid4());await self.api('POST','/api/platform/data-preparations',{'id':other,'model_version_id':v['version']['id']})
        async def frozen(route):
            if route.request.method!='POST':return await route.continue_()
            response=await route.fetch();body=await response.json();body['session']['status']='FINALIZING';body['session']['creation_intent']={'id':str(uuid4())};await route.fulfill(json=body)
        await self.page.route('**/api/platform/data-preparations',frozen)
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1);await select_model(self.page,m['model']['id'],v['version']['id']);await self.ready(2)
        await expect(self.page.locator('#journey-session-availability')).to_have_text('1 sesión disponible')
        calls=[];self.page.on('request',lambda r:calls.append(r.url) if '/api/platform/data-preparations' in r.url else None)
        await self.page.get_by_role('button',name='Ver sesiones',exact=True).click();await expect(self.page.locator('.journey-preparation-status')).to_contain_text('Recuperá la creación congelada')
        self.assertEqual(calls,[]);await expect(self.page.get_by_role('button',name='Recuperar creación del Case',exact=True)).to_be_visible()

    async def test_06_finalizing_session_recovers_the_same_case_and_pack(self):
        await self.selected();await self.attach('transport_demand');await self.attach('transport_resources')
        await self.page.locator('[data-journey-next]').click();await self.fill_case('Creación recuperada por Data Sessions UX09')
        (self.control/'fail-t4-publish').touch();await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click()
        await expect(self.page.locator('.ultimate-footer [role=alert]')).to_be_visible()
        row=json.loads(self.sql("SELECT row_to_json(s) FROM (SELECT id,creation_body->>'id' AS case_id FROM dation_private.journey_preparations WHERE status='FINALIZING') s;"));pid=row['id'];cid=row['case_id']
        self.sql("UPDATE dation_private.journey_preparations SET expires_at=now()-interval '1 second' WHERE id='"+pid+"';")
        original=self.page;self.page=await self.context.new_page()
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        await self.page.set_viewport_size({'width':1536,'height':900});await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
        await select_model(self.page,self.m['model']['id'],self.v['version']['id']);await self.ready(2)
        await expect(self.page.locator('#journey-session-availability')).to_have_text('1 sesión disponible');await self.page.get_by_role('button',name='Ver sesiones',exact=True).click()
        selected=self.page.locator('[data-preparation-id="'+pid+'"]');await expect(selected).to_contain_text('Creación pendiente')
        for width in [1536,390]:
            await self.page.set_viewport_size({'width':width,'height':VIEWS[width]});await self.measure('data-sessions-frozen-recovery-'+str(width),True)
        await selected.click();recover=self.page.get_by_role('button',name='Recuperar creación del Case',exact=True);await expect(recover).to_be_visible()
        await expect(self.page.locator('[data-preparation-entity=transport_demand] input[type=file]')).to_be_disabled()
        await recover.click();await self.page.locator('[data-ux05-ready=true]').wait_for();self.assertIn('case_id='+cid,self.page.url)
        self.assertEqual(self.sql("SELECT count(*) FROM case_data_pack_versions WHERE case_id='"+cid+"';"),'2')
        self.assertEqual(self.sql("SELECT status FROM dation_private.journey_preparations WHERE id='"+pid+"';"),'CONSUMED')
        await original.close()

    async def test_07_case_creation_waits_for_the_selected_session(self):
        for failure in [False,'read','resolve']:
            previous=self.page;self.page=await self.context.new_page();self.page.set_default_timeout(12000);self.page.on('pageerror',lambda error:self.errors.append(str(error)));await previous.close()
            await self.selected();alt=str(uuid4());await self.api('POST','/api/platform/data-preparations',{'id':alt,'model_version_id':self.v['version']['id']})
            await self.focus_sessions();await self.page.get_by_role('button',name='Ver sesiones',exact=True).click()
            selected=self.page.locator('[data-preparation-id="'+alt+'"]');await expect(selected).to_be_visible()
            entered=asyncio.Event();release=asyncio.Event()
            async def hold(route):
                response=None if failure=='read' else await route.fetch();entered.set();await release.wait()
                if failure=='read':await route.fulfill(status=503,json={'detail':'No se confirmó la sesión elegida'})
                else:await route.fulfill(response=response)
            async def resolve_failure(route):
                if route.request.method=='POST' and route.request.post_data_json['id']==alt:return await route.fulfill(status=503,json={'detail':'No se confirmó la sesión elegida'})
                await route.continue_()
            if failure=='resolve':await self.page.route('**/api/platform/data-preparations',resolve_failure)
            pattern='**/api/platform/data-preparations/'+alt;await self.page.route(pattern,hold,times=1)
            await selected.click();await asyncio.wait_for(entered.wait(),12)
            await expect(self.page.locator('[data-journey-next]')).to_be_disabled();await expect(self.page.locator('[data-journey-skip]')).to_be_disabled()
            # The rail remains navigable; the existing readiness promise must
            # serialize submit behind the resource check and its recovery.
            await self.page.locator('[data-dation-test=core-step-3]').click();await self.ready(3);await self.fill_case('Creación coordinada UX09 '+str(failure))
            count_before=self.sql('SELECT count(*) FROM decision_cases;');finalizes=[]
            def track(request):
                if request.method=='POST' and request.url.endswith('/finalize'):finalizes.append(request.url)
            self.page.on('request',track)
            await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click();await expect(self.page.locator('.ultimate-footer [role=status]')).to_have_text('Guardando…')
            await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');self.assertEqual(finalizes,[])
            release.set()
            if failure:
                await expect(self.page.locator('.ultimate-footer [role=alert]')).to_contain_text('No se confirmó la sesión elegida')
                self.assertEqual(self.sql('SELECT count(*) FROM decision_cases;'),count_before);self.assertEqual(finalizes,[])
                if failure=='resolve':
                    await self.page.unroute('**/api/platform/data-preparations',resolve_failure)
                    await self.page.locator('[data-dation-test=core-step-2]').click();await self.ready(2)
                    await expect(self.page.get_by_role('button',name='Ver sesiones',exact=True)).to_be_enabled();await self.page.get_by_role('button',name='Ver sesiones',exact=True).click();await self.page.locator('[data-preparation-id="'+alt+'"]').click()
                    await expect(self.page.get_by_label('Data Owner',exact=True)).to_be_enabled()
                    await self.page.locator('[data-dation-test=core-step-3]').click();await self.ready(3)
                    await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click();await self.page.locator('[data-ux05-ready=true]').wait_for()
                    self.assertEqual(len(finalizes),1);self.assertIn('/'+alt+'/finalize',finalizes[0])
            else:
                await self.page.locator('[data-ux05-ready=true]').wait_for();self.assertEqual(len(finalizes),1);self.assertIn('/'+alt+'/finalize',finalizes[0])
                cid=self.sql("SELECT case_id FROM dation_private.journey_preparations WHERE id='"+alt+"';");self.assertIn('case_id='+cid,self.page.url)
            self.page.remove_listener('request',track)
