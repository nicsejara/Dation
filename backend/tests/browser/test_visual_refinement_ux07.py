"""UX07 visual contracts over existing synthetic and functional Journey fixtures."""
import json,unittest
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from playwright.async_api import expect
import test_navigation as synthetic
import test_journey_navigation_ux06 as ux06
import test_unified_decision_journey as journey
from wizard_helpers import publish_model

OUT=Path('/tmp/dation-ux07-browser');OUT.mkdir(exist_ok=True)
WIDTHS=[1536,1280,1024,768,390,320]
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
    case.assertLessEqual(d['scroll'],d['client'],(tag,d));d['scenario']=tag
    audit=await page.evaluate(AUDIT)
    case.assertEqual(audit['failures'],[],(tag,audit['failures']))
    d['contrast']={key:audit[key] for key in ['textCount','minimumContrast','failures']}
    GEOMETRY.append(d);(OUT/'geometry.json').write_text(json.dumps(GEOMETRY,indent=2))
    return d

class HomeRefinementTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):synthetic.NavigationTests.setUpClass()
    @classmethod
    def tearDownClass(cls):synthetic.NavigationTests.tearDownClass()
    async def asyncSetUp(self):
        self.b=synthetic.NavigationTests();await self.b.asyncSetUp();self.page=self.b.page
        await self.page.emulate_media(reduced_motion='reduce')
    async def asyncTearDown(self):await self.b.asyncTearDown()
    async def test_01_six_visible_cards_filters_entitlement_and_home_bar(self):
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app')
        root=self.page.locator('[data-home-dda-catalog]');await root.locator('[data-dda-id=logistics]').wait_for()
        await expect(root.locator('[data-dda-id]')).to_have_count(6)
        await expect(root.locator('[data-dda-counts]')).to_have_text('1 disponible · 5 próximos')
        await expect(self.page.locator('.topbar--journey')).to_be_hidden()
        self.assertEqual(await root.locator('[data-dda-id]').evaluate_all('ns=>ns.map(n=>n.dataset.ddaId)'),['logistics','production','inventory','procurement','maintenance','pricing'])
        expected={'all':6,'supply-chain':2,'operations':1,'production':1,'commercial':1,'assets':1}
        for category,count in expected.items():
            await root.locator('[data-dda-filter='+category+']').click()
            await expect(root.locator('[data-dda-id]:visible')).to_have_count(count)
            await expect(root.locator('[aria-pressed=true]')).to_have_count(1)
            await expect(root.locator('[data-dda-filter-status]')).to_contain_text(str(count)+' '+('capacidad' if count==1 else 'capacidades'))
        await root.locator('[data-dda-filter=all]').click()
        for width in WIDTHS:
            await self.page.set_viewport_size({'width':width,'height':1000});await document_geometry(self,self.page,'home-'+str(width))
            d=await root.evaluate('''n=>({cards:[...n.querySelectorAll('[data-dda-id]')].map(x=>x.getBoundingClientRect().toJSON()),filters:[...n.querySelectorAll('[data-dda-filter]')].map(x=>x.getBoundingClientRect().toJSON())})''')
            self.assertLess(max(x['width'] for x in d['cards'])-min(x['width'] for x in d['cards']),2,d)
            self.assertLess(max(x['height'] for x in d['cards'])-min(x['height'] for x in d['cards']),2,d)
            self.assertLess(max(x['width'] for x in d['filters'])-min(x['width'] for x in d['filters']),2,d)
            self.assertTrue(all(x['height']>=44 for x in d['filters']),d)
            columns=len(set(round(x['x']) for x in d['cards']));self.assertEqual(columns,3 if width>=1280 else 2 if width>=768 else 1,d)
            if width in [1536,390]:await capture(self.page,'home-'+str(width))
        self.b.ddas=[];await self.page.reload();await expect(root.locator('[data-dda-entitlement=disabled]')).to_have_count(1)
        await expect(root.locator('[data-dda-counts]')).to_have_text('0 disponibles · 5 próximos · 1 no habilitado')
        await expect(root.locator('[data-dda-id=logistics] button')).to_have_count(0)
        self.assertEqual(self.b.execution_bodies,[])
    async def test_02_landing_equivalent_actions_preserve_filtered_center(self):
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app/ddas/logistics')
        await expect(self.page.locator('[data-open-decision-map]')).to_have_text('Ir al Decision Center →')
        await expect(self.page.locator('.topbar--journey')).to_be_visible()
        await expect(self.page.locator('#journey-nav li')).to_have_count(2)
        for width in WIDTHS:
            await self.page.set_viewport_size({'width':width,'height':1000});await document_geometry(self,self.page,'landing-'+str(width))
            title=await self.page.locator('.dda-landing__hero h1').evaluate('n=>parseFloat(getComputedStyle(n).fontSize)')
            self.assertAlmostEqual(title,max(28,min(width*.026,38)),delta=.1)
            buttons=await self.page.locator('.dda-landing__hero-actions button').evaluate_all('ns=>ns.map(n=>n.getBoundingClientRect().toJSON())')
            self.assertEqual(len(buttons),2);self.assertAlmostEqual(buttons[0]['width'],buttons[1]['width'],delta=1);self.assertAlmostEqual(buttons[0]['height'],buttons[1]['height'],delta=1)
            if width in [1536,390]:await capture(self.page,'landing-'+str(width))
        await self.page.get_by_role('button',name='Ir al Decision Center',exact=False).click()
        await self.page.wait_for_function("window.dationGetCurrentView()==='platform-decisions'")
        self.assertEqual(parse_qs(urlparse(self.page.url).query)['center_dda'],['logistics'])
        await self.page.locator('.nav [data-platform-view=platform-home]').click()
        await expect(self.page.locator('.topbar--journey')).to_be_hidden()
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
        await self.page.set_viewport_size({'width':1536,'height':1000})
        await self.page.goto(self.base+'/app/ddas/logistics');await expect(self.page.locator('#journey-nav li')).to_have_count(2)
        nav=await self.page.locator('#journey-nav li').evaluate_all('ns=>ns.map(n=>n.getBoundingClientRect().toJSON())')
        await self.page.get_by_role('button',name='Comenzar',exact=True).click();await self.ready(1)
        nav4=await self.page.locator('#journey-nav li').evaluate_all('ns=>ns.map(n=>n.getBoundingClientRect().toJSON())')
        self.assertEqual(len(nav4),4)
        for a,b in zip(nav,nav4):self.assertAlmostEqual(a['width'],b['width'],delta=1);self.assertAlmostEqual(a['x'],b['x'],delta=1)
        await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Modelo UX07')
        await expect(self.page.get_by_role('button',name='Guardar y continuar',exact=True)).to_be_enabled()
        metrics=[]
        async def measure_core(step):
            previous=self.page.locator('[data-journey-previous]:visible')
            await expect(previous).to_have_accessible_name({1:'Volver a DDA Logística',2:'Volver a Logistics Model',3:'Volver a Data Contract & Preparation'}[step])
            self.assertEqual(await previous.inner_text(),'')
            await previous.focus()
            self.assertEqual(await previous.evaluate('n=>getComputedStyle(n).outlineWidth'),'3px')
            for width in WIDTHS:
                await self.page.set_viewport_size({'width':width,'height':1000});await document_geometry(self,self.page,'core'+str(step)+'-'+str(width))
                d=await self.page.evaluate('''()=>{const rect=n=>n.getBoundingClientRect().toJSON(),panel=document.querySelector('[data-dation-test=core-'+({1:'model',2:'contract',3:'case'})[document.querySelector('.core-wizard').dataset.activeStep]+']'),footer=[...document.querySelectorAll('.journey-step-footer')].find(n=>n.getClientRects().length);return {width:innerWidth,step:Number(document.querySelector('.core-wizard').dataset.activeStep),header:rect(panel.querySelector('.journey-step-header')),title:getComputedStyle(panel.querySelector('.ultimate-disclosure__title')).fontSize,footer:rect(footer),previous:rect(footer.querySelector('[data-journey-previous]')),ring:rect(footer.querySelector('.model-wizard-ring,.data-contract-ring,.decision-case-ring')),cards:[...document.querySelectorAll('.core-wizard-steps>button')].map(rect)}}''')
                self.assertEqual(d['step'],step);self.assertEqual(round(d['previous']['width']),44);self.assertEqual(round(d['previous']['height']),44)
                self.assertEqual(round(d['ring']['width']),44);self.assertEqual(round(d['ring']['height']),44)
                self.assertLess(max(c['height'] for c in d['cards'])-min(c['height'] for c in d['cards']),2,d)
                metrics.append(d)
                if width in [1536,390]:await capture(self.page,'core'+str(step)+'-'+str(width))
            await self.page.set_viewport_size({'width':1536,'height':1000})
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
        await measure_core(2)
        await self.page.locator('[data-journey-next]').click();await self.ready(3);await self.fill_case('Case UX07');await measure_core(3)
        for width in [1536,1280]:
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
            await self.page.set_viewport_size({'width':width,'height':1000});await document_geometry(self,self.page,'graph-'+str(width))
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
            before=len(requests);await first.click();await expect(self.page.locator('#ux05-decision-panel')).to_have_count(0);self.assertEqual(len(requests),before)
            await first.press('Enter');await expect(self.page.locator('#ux05-decision-panel')).to_be_visible();await second.click();await expect(second).to_have_attribute('aria-expanded','true');await expect(first).to_have_attribute('aria-expanded','false')
            if width in [1536,390]:await capture(self.page,'graph-open-'+str(width))
            close=self.page.get_by_role('button',name='Cerrar panel',exact=True);r=await close.bounding_box();self.assertGreaterEqual(r['width'],44);self.assertGreaterEqual(r['height'],44)
            svg=await close.locator('svg').bounding_box();self.assertAlmostEqual(svg['x']+svg['width']/2,r['x']+r['width']/2,delta=1);self.assertAlmostEqual(svg['y']+svg['height']/2,r['y']+r['height']/2,delta=1)
            await close.click();await second.press('Space');await expect(self.page.locator('#ux05-decision-panel')).to_be_visible();await self.page.keyboard.press('Escape');await expect(second).to_be_focused()
            await second.click();await second.click();await expect(self.page.locator('#ux05-decision-panel')).to_have_count(0)
            await first.click();await self.page.get_by_role('heading',name='Decision Studio',exact=True).click();await expect(self.page.locator('#ux05-decision-panel')).to_have_count(0)
            self.assertEqual(self.page.url,graph_url);self.assertEqual(await nodes.evaluate_all('ns=>ns.map(n=>({id:n.dataset.ux05Node,tone:n.dataset.tone,label:n.getAttribute("aria-label")}))'),states)
        await self.page.set_viewport_size({'width':1440,'height':1000});await self.page.evaluate('document.documentElement.style.zoom="2"');await document_geometry(self,self.page,'graph-zoom200')
        (OUT/'core-metrics.json').write_text(json.dumps(metrics,indent=2))
