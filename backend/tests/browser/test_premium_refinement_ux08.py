"""UX08 visual contracts over existing synthetic and functional Journey fixtures."""
import json,unittest
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from playwright.async_api import expect
import test_navigation as synthetic
import test_journey_navigation_ux06 as ux06
import test_unified_decision_journey as journey
from wizard_helpers import publish_model

OUT=Path('/tmp/dation-ux08-browser');OUT.mkdir(exist_ok=True)
WIDTHS=[1536,1280,1024,768,390,320]
HEIGHTS={1536:900,1280:800,1024:768,768:900,390:844,320:740}
GEOMETRY=[]
AUDIT=(Path(__file__).parent/'theme_audit.js').read_text()
async def settled(page):
    await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
async def capture(page,name):
    await page.mouse.move(0,0);await page.evaluate('document.activeElement?.blur();scrollTo(0,0)')
    await page.screenshot(path=str(OUT/(name+'.png')),full_page=True,animations='disabled')
async def document_geometry(case,page,tag):
    await settled(page)
    d=await page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})')
    if d['scroll']>d['client']:d['overflowNodes']=await page.evaluate("[...document.querySelectorAll('body *')].filter(n=>n.getBoundingClientRect().right>innerWidth+1&&n.getClientRects().length).slice(-12).map(n=>({tag:n.tagName,class:n.className,rect:n.getBoundingClientRect().toJSON()}))")
    case.assertLessEqual(d['scroll'],d['client'],(tag,d));d['scenario']=tag
    audit=await page.evaluate(AUDIT)
    case.assertEqual(audit['failures'],[],(tag,audit['failures']))
    d['contrast']={key:audit[key] for key in ['textCount','minimumContrast','failures']}
    GEOMETRY.append(d);(OUT/'geometry.json').write_text(json.dumps(GEOMETRY,indent=2))
    return d

class HeroRefinementTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):synthetic.NavigationTests.setUpClass()
    @classmethod
    def tearDownClass(cls):synthetic.NavigationTests.tearDownClass()
    async def asyncSetUp(self):
        self.b=synthetic.NavigationTests();await self.b.asyncSetUp();self.page=self.b.page
        await self.page.emulate_media(reduced_motion='reduce')
    async def asyncTearDown(self):await self.b.asyncTearDown()
    async def test_01_common_hero_geometry_and_real_identity(self):
        hero_metrics=[]
        for width in WIDTHS:
            await self.page.set_viewport_size({'width':width,'height':HEIGHTS[width]});measured=[]
            for path,selector in [('/app','.platform-home__header'),('/app/ddas/logistics','.dda-landing__hero')]:
                await self.page.goto(f'http://127.0.0.1:{self.b.port}'+path)
                hero=self.page.locator(selector);await hero.locator('.product-hero-topline').wait_for();await self.page.evaluate('document.fonts.ready')
                await document_geometry(self,self.page,selector+'-'+str(width))
                d=await hero.evaluate("""n=>{const r=x=>x.getBoundingClientRect().toJSON();return {outer:r(n),top:r(n.querySelector('.product-hero-topline')),title:r(n.querySelector('h1')),font:getComputedStyle(n.querySelector('h1')).fontSize,subtitle:r(n.querySelector('.d-page-description,.dda-landing__hero-lead')),actions:r(n.querySelector('.platform-home__hero-actions,.dda-landing__hero-actions')),panel:r(n.querySelector('.d-product-hero__panel')),art:r(n.querySelector('.d-product-hero__art'))}}""")
                measured.append(d)
                if width in [1536,390]:await capture(self.page,('home' if path=='/app' else 'landing')+'-'+str(width))
            hero_metrics.append({'width':width,'home':measured[0],'landing':measured[1]})
            home,landing=measured
            self.assertEqual(home['font'],landing['font'])
            if width>700:
                self.assertEqual(home['outer']['height'],480 if width>=1280 else 560)
                self.assertEqual(home['outer']['height'],landing['outer']['height'])
                for key in ['title','subtitle','actions']:
                    self.assertAlmostEqual(home[key]['y']-home['outer']['y'],landing[key]['y']-landing['outer']['y'],delta=1,msg=(width,key,measured))
                if width>=1024:self.assertAlmostEqual(home['panel']['height'],landing['panel']['height'],delta=1)
        (OUT/'hero-metrics.json').write_text(json.dumps(hero_metrics,indent=2))
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app')
        await expect(self.page.locator('.platform-home__greeting')).to_have_text('Bienvenido, Synthetic')
        await self.page.evaluate("window.dationSession.identity.profile.first_name='María';dispatchEvent(new Event('dation:identity'))")
        await expect(self.page.locator('.platform-home__greeting')).to_have_text('Bienvenido, María')
        self.assertEqual(self.b.execution_bodies,[])

class JourneyRefinementTests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(ux06.JourneyNavigationTests.setUpClass.__func__)
    tearDownClass=classmethod(ux06.JourneyNavigationTests.tearDownClass.__func__)
    asyncSetUp=ux06.JourneyNavigationTests.asyncSetUp
    asyncTearDown=ux06.JourneyNavigationTests.asyncTearDown
    sql=ux06.JourneyNavigationTests.sql
    login=ux06.JourneyNavigationTests.login
    request=ux06.JourneyNavigationTests.request
    api=ux06.JourneyNavigationTests.api
    attach=journey.UnifiedDecisionJourneyTests.attach
    fill_case=journey.UnifiedDecisionJourneyTests.fill_case
    ready=ux06.JourneyNavigationTests.ready
    async def test_03_real_publish_prepare_finalize_geometry_and_local_toggle(self):
        await self.page.set_viewport_size({'width':1536,'height':900})
        await self.page.goto(self.base+'/app/ddas/logistics');await expect(self.page.locator('#journey-nav li')).to_have_count(2)
        nav=await self.page.locator('#journey-nav li').evaluate_all('ns=>ns.map(n=>n.getBoundingClientRect().toJSON())')
        await self.page.get_by_role('button',name='Comenzar',exact=True).click();await self.ready(1)
        nav4=await self.page.locator('#journey-nav li').evaluate_all('ns=>ns.map(n=>n.getBoundingClientRect().toJSON())')
        self.assertEqual(len(nav4),4)
        for a,b in zip(nav,nav4):self.assertAlmostEqual(a['width'],b['width'],delta=1);self.assertAlmostEqual(a['x'],b['x'],delta=1)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Modelo UX08')
        await expect(self.page.get_by_role('button',name='Guardar y continuar',exact=True)).to_be_enabled()
        metrics=[];owner_metrics=[]
        async def measure_core(step):
            previous=self.page.locator('[data-journey-previous]:visible')
            await expect(previous).to_have_accessible_name({1:'Volver a DDA Logística',2:'Volver a Logistics Model',3:'Volver a Data Contract & Preparation'}[step])
            self.assertEqual(await previous.inner_text(),'')
            await previous.focus()
            self.assertEqual(await previous.evaluate('n=>getComputedStyle(n).outlineWidth'),'3px')
            for width in WIDTHS:
                await self.page.set_viewport_size({'width':width,'height':HEIGHTS[width]});await document_geometry(self,self.page,'core'+str(step)+'-'+str(width))
                d=await self.page.evaluate('''()=>{const rect=n=>n.getBoundingClientRect().toJSON(),panel=document.querySelector('[data-dation-test=core-'+({1:'model',2:'contract',3:'case'})[document.querySelector('.core-wizard').dataset.activeStep]+']'),footer=[...document.querySelectorAll('.journey-step-footer')].find(n=>n.getClientRects().length);return {width:innerWidth,step:Number(document.querySelector('.core-wizard').dataset.activeStep),header:rect(panel.querySelector('.journey-step-header')),title:getComputedStyle(panel.querySelector('.ultimate-disclosure__title')).fontSize,footer:rect(footer),previous:rect(footer.querySelector('[data-journey-previous]')),ring:rect(footer.querySelector('.model-wizard-ring,.data-contract-ring,.decision-case-ring')),cards:[...document.querySelectorAll('.core-wizard-steps>button')].map(rect)}}''')
                badge=self.page.locator('[data-dation-test=core-'+{1:'model',2:'contract',3:'case'}[step]+'] .ultimate-disclosure__status').first
                b=await badge.bounding_box();self.assertGreaterEqual(b['height'],36)
                if width==1536:
                    original=await badge.text_content();state=await badge.get_attribute('data-state')
                    box=await badge.locator('xpath=..').bounding_box()
                    for label,tone in [('En configuración','pending'),('Estructura lista','complete'),('Revisar estructura','warning'),('Reintentar Data Contract','error')]:
                        await badge.evaluate('(n,v)=>{n.textContent=v.label;n.dataset.state=v.tone}',{'label':label,'tone':tone})
                        self.assertEqual(await badge.locator('xpath=..').bounding_box(),box)
                        self.assertEqual(round((await badge.bounding_box())['height']),36)
                    await badge.evaluate('(n,v)=>{n.textContent=v.label;n.dataset.state=v.tone}',{'label':original,'tone':state})
                if width>=390:self.assertEqual(round(b['width']),180)
                else:self.assertLessEqual(b['width'],180)
                if step==2 and width>=1280:
                    buttons=await self.page.locator('.journey-step-actions:visible>button:visible').evaluate_all('ns=>ns.map(n=>n.getBoundingClientRect().toJSON())')
                    self.assertEqual(len(buttons),2);self.assertAlmostEqual(buttons[0]['y'],buttons[1]['y'],delta=1)
                self.assertEqual(d['step'],step);self.assertEqual(round(d['previous']['width']),44);self.assertEqual(round(d['previous']['height']),44)
                self.assertEqual(round(d['ring']['width']),44);self.assertEqual(round(d['ring']['height']),44)
                self.assertLess(max(c['height'] for c in d['cards'])-min(c['height'] for c in d['cards']),2,d)
                if step in [2,3]:
                    owner=self.page.locator('[data-dation-test=preparation-owner-card]' if step==2 else '[data-dation-test=core-case] .core-owner-card')
                    owner_metrics.append(await owner.evaluate("""(n,meta)=>{const r=x=>x.getBoundingClientRect().toJSON();return {...meta,card:r(n),rail:r(n.querySelector('.decision-case-rail')),select:r(n.querySelector('select')),label:getComputedStyle(n.querySelector('label')).fontSize}}""",{'step':step,'width':width}))
                metrics.append(d)
                if width in [1536,390]:await capture(self.page,'core'+str(step)+'-'+str(width))
            await self.page.set_viewport_size({'width':1536,'height':900})
        await measure_core(1)
        async with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/versions')) as response:
            await publish_model(self.page)
        published=await (await response.value).json();model_id=published['version']['model_id'];version_id=published['version']['id']
        self.m={'model':{'id':model_id}};self.v={'version':{'id':version_id}}
        await self.ready(2)
        async with self.page.expect_response(lambda r:r.request.method=='PUT' and r.url.endswith('/owner')) as owner_response:
            await self.page.get_by_label('Data Owner',exact=True).select_option(ux06.setup.ADMIN)
        self.assertTrue((await owner_response.value).ok)
        await expect(self.page.locator('[data-journey-next]')).to_have_text('Continuar con datos')
        await expect(self.page.locator('[data-journey-next]')).to_be_disabled();await expect(self.page.locator('[data-journey-skip]')).to_have_text('Continuar sin datos')
        await self.attach('transport_demand');await self.attach('transport_resources');await expect(self.page.locator('[data-journey-next]')).to_be_enabled()
        await expect(self.page.locator('[data-dation-test=preparation-owner-card]')).to_contain_text('Responsable de datos')
        await expect(self.page.get_by_role('button',name='Ver sesiones',exact=True)).to_be_visible()
        await expect(self.page.locator('.data-contract-info,.data-contract-technical')).to_have_count(0)
        await self.page.locator('[data-dation-test=contract-fields-transport_resources] > summary').click()
        table_metrics=[]
        for width in [1536,1280,390]:
            await self.page.set_viewport_size({'width':width,'height':HEIGHTS[width]});await settled(self.page)
            table=self.page.locator('[data-dation-test=contract-fields-transport_resources] table')
            heights=await table.locator('tbody tr').evaluate_all('ns=>ns.map(n=>n.getBoundingClientRect().height)')
            if width>700:self.assertLess(max(heights)-min(heights),1)
            table_metrics.append({'width':width,'rowHeights':heights,'headers':await table.get_by_role('columnheader').all_text_contents()})
            await expect(table.get_by_role('columnheader')).to_have_count(3)
            if width in [1536,390]:await capture(self.page,'contract-fields-'+str(width))
        (OUT/'table-metrics.json').write_text(json.dumps(table_metrics,indent=2))
        await self.page.locator('[data-dation-test=contract-fields-transport_resources] > summary').click()
        await measure_core(2)
        await self.page.locator('[data-journey-next]').click();await self.ready(3);await self.fill_case('Case UX08');await measure_core(3)
        for width in [1536,1280]:
            owners=[o for o in owner_metrics if o['width']==width]
            self.assertEqual(len(owners),2)
            # UX09 narrows Data Owner to 2/3; the control/type family is preserved.
            self.assertAlmostEqual(owners[0]['card']['width'],(owners[1]['card']['width']-16)*2/3,delta=1,msg=owners)
            self.assertAlmostEqual(owners[0]['select']['height'],owners[1]['select']['height'],delta=1,msg=owners)
            self.assertEqual(owners[0]['label'],owners[1]['label'])
            ds=[m for m in metrics if m['width']==width]
            self.assertLess(max(m['header']['height'] for m in ds)-min(m['header']['height'] for m in ds),2,ds)
            self.assertEqual(len(set(m['title'] for m in ds)),1,ds)
            self.assertLess(max(m['footer']['width'] for m in ds)-min(m['footer']['width'] for m in ds),2,ds)
            self.assertLess(max(m['footer']['height'] for m in ds)-min(m['footer']['height'] for m in ds),2,ds)
        for step in [3,2,1]:
            await self.page.evaluate('document.documentElement.style.zoom="2"');await document_geometry(self,self.page,'core'+str(step)+'-zoom200')
            if step>1:await self.page.locator('[data-journey-previous]:visible').click();await self.ready(step-1)
        await self.page.evaluate('document.documentElement.style.zoom="1"');await settled(self.page)
        await self.page.locator('[data-dation-test=core-step-3]').click();await self.ready(3)
        await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click();await self.page.wait_for_url('**/decisions?**');await self.page.locator('[data-ux05-ready=true]').wait_for()
        graph_url=self.page.url;nodes=self.page.locator('[data-ux05-node]');await expect(nodes).to_have_count(2)
        states=await nodes.evaluate_all('ns=>ns.map(n=>({id:n.dataset.ux05Node,tone:n.dataset.tone,label:n.getAttribute("aria-label")}))')
        requests=[];graph_metrics=[];self.page.on('request',lambda r:requests.append(r.url) if '/api/' in r.url else None)
        for width in WIDTHS:
            await self.page.set_viewport_size({'width':width,'height':HEIGHTS[width]});await document_geometry(self,self.page,'graph-'+str(width))
            d=await self.page.evaluate('''()=>({circles:[...document.querySelectorAll('.ux05-node-button,.ux05-future-circle')].map(n=>n.getBoundingClientRect().toJSON()),edges:[...document.querySelectorAll('.ux05-edge,.ux05-future-edge')].map(n=>({text:n.textContent,rect:n.getBoundingClientRect().toJSON()})),rail:[...document.querySelectorAll('.journey-studio-rail>button')].map(n=>n.getBoundingClientRect().toJSON())})''')
            await expect(self.page.locator('.ux05-future :is(button,a,[tabindex])')).to_have_count(0)
            self.assertEqual(len(d['circles']),3);self.assertLess(max(c['width'] for c in d['circles'])-min(c['width'] for c in d['circles']),1,d)
            for c in d['circles']:self.assertAlmostEqual(c['width'],c['height'],delta=1)
            a,b,c=d['circles'];axis='x' if abs(a['y']-b['y'])<2 else 'y'
            self.assertAlmostEqual(b[axis]-a[axis],c[axis]-b[axis],delta=2,msg=d)
            self.assertTrue(all(not e['text'].strip() for e in d['edges']),d)
            graph_metrics.append({'width':width,**d});(OUT/'graph-metrics.json').write_text(json.dumps(graph_metrics,indent=2))
            if width>=1280:
                core=next(x for x in metrics if x['width']==width and x['step']==1)['cards']
                for a,b in zip(core,d['rail']):self.assertAlmostEqual(a['width'],b['width'],delta=1);self.assertAlmostEqual(a['height'],b['height'],delta=1)
            if width in [1536,390]:await capture(self.page,'graph-closed-'+str(width))
            first=nodes.nth(0);second=nodes.nth(1)
            await first.click();await expect(self.page.locator('#ux05-decision-panel')).to_be_visible()
            if width in [1536,390]:await capture(self.page,'graph-d1-'+str(width))
            before=len(requests);await first.click();await expect(self.page.locator('#ux05-decision-panel')).to_have_count(0);self.assertEqual(len(requests),before)
            await first.press('Enter');await expect(self.page.locator('#ux05-decision-panel')).to_be_visible();await second.click();await expect(second).to_have_attribute('aria-expanded','true');await expect(first).to_have_attribute('aria-expanded','false')
            await expect(self.page.locator('.ux05-case-facts>div')).to_have_count(4)
            await expect(self.page.locator('.ux05-toolbar-actions button')).to_have_count(5)
            await expect(self.page.locator('.ux08-node-header h2')).to_contain_text('D2')
            await expect(self.page.locator('.ux08-node-meta dt')).to_have_text(['Estado','Salida'])
            self.assertTrue(all('✓' not in x for x in await self.page.locator('.ux05-requirements li').all_text_contents()))
            await document_geometry(self,self.page,'graph-open-'+str(width))
            if width in [1536,390]:await capture(self.page,'graph-open-'+str(width))
            close=self.page.get_by_role('button',name='Cerrar panel',exact=True);r=await close.bounding_box();self.assertGreaterEqual(r['width'],44);self.assertGreaterEqual(r['height'],44)
            svg=await close.locator('svg').bounding_box();self.assertAlmostEqual(svg['x']+svg['width']/2,r['x']+r['width']/2,delta=1);self.assertAlmostEqual(svg['y']+svg['height']/2,r['y']+r['height']/2,delta=1)
            await close.click();await second.press('Space');await expect(self.page.locator('#ux05-decision-panel')).to_be_visible();await self.page.keyboard.press('Escape');await expect(second).to_be_focused()
            await second.click();await second.click();await expect(self.page.locator('#ux05-decision-panel')).to_have_count(0)
            await first.click();await self.page.get_by_role('heading',name='Decision Studio',exact=True).click();await expect(self.page.locator('#ux05-decision-panel')).to_have_count(0)
            self.assertEqual(self.page.url,graph_url);self.assertEqual(await nodes.evaluate_all('ns=>ns.map(n=>({id:n.dataset.ux05Node,tone:n.dataset.tone,label:n.getAttribute("aria-label")}))'),states)
        await self.page.set_viewport_size({'width':1440,'height':1000});await self.page.evaluate('document.documentElement.style.zoom="2"');await document_geometry(self,self.page,'graph-zoom200')
        (OUT/'core-metrics.json').write_text(json.dumps(metrics,indent=2))
        (OUT/'owner-metrics.json').write_text(json.dumps(owner_metrics,indent=2))

    model=ux06.JourneyNavigationTests.model
    case=ux06.JourneyNavigationTests.case
    async def test_04_contextual_loading_and_safe_human_preparation_picker(self):
        import asyncio
        from uuid import uuid4
        from wizard_helpers import select_model
        m,v,c=await self.case();cid=c['case']['id']
        pattern='**/api/platform/ultimate-foundation/capabilities'
        for suffix,copy in [('', 'Inicializando Core Configuration…'),('?parent_case_id='+cid,'Inicializando Core Configuration…'),('?case_id='+cid,'Recuperando contexto del Case…')]:
            entered=asyncio.Event();release=asyncio.Event()
            async def hold(route):
                response=await route.fetch();entered.set();await release.wait();await route.fulfill(response=response)
            await self.page.route(pattern,hold)
            try:
                await self.page.goto(self.base+'/app/ddas/logistics/case'+suffix,wait_until='domcontentloaded')
                await asyncio.wait_for(entered.wait(),12)
                await expect(self.page.locator('.ultimate-core-setup')).to_contain_text(copy)
            finally:release.set()
            await self.page.locator('[data-ultimate-ready=true]').wait_for();await self.page.unroute(pattern,hold)
        await self.page.evaluate("async()=>{const {draftStore}=await import('/static/js/dispatch/models/forms.mjs');draftStore('case').clear();}")
        await self.page.goto(self.base+'/app/ddas/logistics/case',wait_until='domcontentloaded')
        await self.ready(1);await select_model(self.page,m['model']['id'],v['version']['id']);await self.ready(2)
        await expect(self.page.locator('[data-journey-skip]')).to_be_enabled()
        picker=self.page.get_by_role('button',name='Ver sesiones',exact=True)
        await expect(self.page.locator('#journey-session-availability')).to_contain_text('No hay otras sesiones')
        await expect(picker).to_be_disabled()
        alternate=str(uuid4());await self.api('POST','/api/platform/data-preparations',{'id':alternate,'model_version_id':v['version']['id']})
        await self.page.evaluate("dispatchEvent(new Event('focus'))");await expect(self.page.locator('#journey-session-availability')).to_have_text('1 sesión disponible')
        await picker.click();await expect(self.page.locator('.journey-resume-list button')).to_have_count(1)
        for parent in [None]:
            await self.api('POST','/api/platform/data-preparations',{'id':str(uuid4()),'model_version_id':v['version']['id'],'parent_case_id':parent})
        other,other_version=await self.model('Versión incompatible UX08')
        await self.api('POST','/api/platform/data-preparations',{'id':str(uuid4()),'model_version_id':other_version['version']['id']})
        await self.page.evaluate("dispatchEvent(new Event('focus'))");await expect(self.page.locator('#journey-session-availability')).to_have_text('2 sesiones disponibles')
        await picker.click();await expect(self.page.locator('.journey-resume-list button')).to_have_count(2)
        labels=await self.page.locator('.journey-resume-list button').all_text_contents()
        self.assertTrue(all('Borrador' in label and '2026-' not in label for label in labels),labels)
        self.assertNotIn(alternate,await self.page.locator('.journey-resume-list').inner_text())
        await self.page.locator('[data-preparation-id="'+alternate+'"]').click()
        await expect(self.page.get_by_label('Data Owner',exact=True)).to_be_enabled()
        async with self.page.expect_response(lambda r:r.request.method=='PUT' and '/'+alternate+'/owner' in r.url) as response:
            await self.page.get_by_label('Data Owner',exact=True).select_option(ux06.setup.ADMIN)
        self.assertTrue((await response.value).ok)
        await expect(self.page.locator('#journey-session-availability')).not_to_contain_text('Consultando')
        raw=await self.request('POST','/api/platform/logistics-models/contract-preview/templates/transport_demand',{'model_id':m['model']['id'],'version_id':v['version']['id']})
        host=self.page.locator('[data-preparation-entity=transport_demand]')
        await host.locator('input[type=file]').set_input_files({'name':'pending.csv','mimeType':'text/csv','buffer':await raw.body()})
        await expect(host.get_by_role('button',name='Guardar candidato de Órdenes / Demanda',exact=True)).to_be_enabled()
        calls=[];self.page.on('request',lambda r:calls.append(r.url) if r.url.endswith('/api/platform/data-preparations') and r.method=='GET' else None)
        await picker.click();await expect(self.page.locator('.journey-preparation-status')).to_contain_text('Guardá o quitá los archivos locales')
        self.assertEqual(calls,[])
        self.page.on('dialog',lambda d:d.accept())
