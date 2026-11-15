"""UX05 over the real local API, private Storage contract and PostgreSQL.
Lifecycle metadata fixtures are explicit; the UX04 Engine test covers real D1/D2.
"""
import asyncio,json,unittest
from pathlib import Path
from uuid import uuid4
from playwright.async_api import expect, Error as PlaywrightError
import test_unified_decision_journey as journey
import test_ultimate_case_setup as setup
import test_ultimate_navigation as legacy

OUT=Path('/tmp/dation-ux05-browser');OUT.mkdir(exist_ok=True)
MEASUREMENTS=[]
CONTRAST=[]
class CommandCenterTests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(journey.UnifiedDecisionJourneyTests.setUpClass.__func__)
    tearDownClass=classmethod(journey.UnifiedDecisionJourneyTests.tearDownClass.__func__)
    asyncSetUp=setup.UltimateCaseSetupTests.asyncSetUp
    asyncTearDown=journey.UnifiedDecisionJourneyTests.asyncTearDown
    sql=journey.UnifiedDecisionJourneyTests.sql
    login=setup.UltimateCaseSetupTests.login
    request=setup.UltimateCaseSetupTests.request
    api=setup.UltimateCaseSetupTests.api
    model=setup.UltimateCaseSetupTests.model
    case=setup.UltimateCaseSetupTests.case
    owner=legacy.UltimateNavigationTests.owner
    full=legacy.UltimateNavigationTests.full
    upload_api=journey.UnifiedDecisionJourneyTests.upload_api
    template=journey.UnifiedDecisionJourneyTests.template
    install=legacy.UltimateNavigationTests.install
    async def graph(self,cid):
        await self.page.goto(self.base+'/app/ddas/logistics/decisions?case_id='+cid,wait_until='domcontentloaded');await self.page.locator('[data-ux05-ready=true]').wait_for()
    async def shot(self,name):
        await self.page.mouse.move(0,0);await self.page.evaluate('document.activeElement?.blur();scrollTo(0,0)');await self.page.evaluate('new Promise(requestAnimationFrame)');await self.page.screenshot(path=str(OUT/(name+'.png')),full_page=True,animations='disabled')
    async def geometry(self,tag):
        await self.page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        r=await self.page.evaluate('''()=>{const rect=s=>document.querySelector(s)?.getBoundingClientRect().toJSON();return {width:innerWidth,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,content:rect('.ux05-command-center .journey-studio-content'),graph:rect('.ux05-graph'),rail:rect('.ux05-command-center .journey-studio-rail'),panel:rect('.ux05-panel'),columns:getComputedStyle(document.querySelector('.ux05-command-center .journey-studio-layout')).gridTemplateColumns,gap:getComputedStyle(document.querySelector('.ux05-command-center .journey-studio-layout')).gap,items:[...document.querySelectorAll('.ux05-node-button,.ux05-edge,.ux05-future-circle,.ux05-future-edge')].map(n=>({class:n.className,rect:n.getBoundingClientRect().toJSON(),radius:getComputedStyle(n).borderTopLeftRadius}))}}''')
        self.assertLessEqual(r['scroll'],r['client']+1,r)
        for item in r['items']:
            self.assertGreaterEqual(item['rect']['left'],r['content']['left']-1,r);self.assertLessEqual(item['rect']['right'],r['content']['right']+1,r)
            if item['class']=='ux05-node-button':self.assertEqual(item['radius'],'50%');self.assertAlmostEqual(item['rect']['width'],item['rect']['height'],delta=1)
        for key in ['graph','panel']:
            b=r[key]
            if not b:continue
            self.assertGreaterEqual(b['left'],r['content']['left']-1,r);self.assertLessEqual(b['right'],r['content']['right']+1,r)
            a=r['rail'];intersects=b['left']<a['right']-1 and b['right']>a['left']+1 and b['top']<a['bottom']-1 and b['bottom']>a['top']+1
            self.assertFalse(intersects,r)
        if r['width']>=1200:self.assertAlmostEqual(r['rail']['width'],216,delta=1);self.assertEqual(r['gap'],'20px')
        self.assertFalse(await self.page.locator('#dda-workspace-nav-shell').is_visible());await expect(self.page.locator('#journey-nav li')).to_have_count(4)
        r['scenario']=tag;MEASUREMENTS.append(r);(OUT/'geometry.json').write_text(json.dumps(MEASUREMENTS,indent=2));return r
    async def test_01_default_panel_summary_and_six_width_containment(self):
        m,v,c=await self.case();cid=c['case']['id'];await self.graph(cid)
        await expect(self.page.locator('.ux05-node-button')).to_have_count(2);await expect(self.page.locator('.ux05-panel')).to_have_count(0);await expect(self.page.locator('.ux05-future button,.ux05-future a')).to_have_count(0)
        await expect(self.page.locator('[data-graph-node=logistics_assignment] .ux05-status')).to_have_text('Pendiente');await expect(self.page.locator('[data-graph-node=logistics_scheduling] .ux05-status')).to_have_text('Bloqueada')
        self.assertEqual(await self.page.get_by_role('button',name='Mapa de decisiones',exact=True).count(),0);self.assertEqual(await self.page.get_by_role('button',name='Editar Decision Case',exact=True).count(),1)
        for width in [1536,1280,1024,768,390,320]:
            await self.page.set_viewport_size({'width':width,'height':1000});await self.geometry('default');await self.shot('default-'+str(width))
            before=self.page.url;node=self.page.locator('[data-ux05-node=logistics_scheduling]');await node.focus();await self.page.keyboard.press('Enter');await expect(self.page.locator('.ux05-panel')).to_contain_text('Requiere aprobación vigente de D1');self.assertEqual(self.page.url,before);await self.geometry('d2-locked-open');await self.shot('locked-'+str(width));await self.page.keyboard.press('Escape');await expect(node).to_be_focused();await expect(node).to_have_attribute('aria-expanded','false')
        await self.page.set_viewport_size({'width':1536,'height':1000});await self.page.get_by_role('button',name='Resumen Core Config',exact=True).click();await expect(self.page.locator('#ux05-core-summary')).to_contain_text(m['model']['name']);await expect(self.page.locator('#ux05-core-summary')).to_contain_text('MINIMIZE_COST');await self.geometry('summary');await self.shot('core-summary');self.assertEqual(await self.page.locator('#ux05-core-summary input,#ux05-core-summary select,#ux05-core-summary textarea').count(),0);await self.page.keyboard.press('Escape')
    async def test_02_owner_reconciles_locked_and_ready_actions_without_execution(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.full(cid);responsibilities=await self.api('GET','/api/platform/decisions/'+cid+'/responsibilities');admin_name=responsibilities['stages']['logistics_assignment']['owner']['name']
        for node in ['logistics_assignment','logistics_scheduling']:await self.api('PUT','/api/platform/decisions/'+cid+'/responsibilities/'+node,{'expected_updated_at':responsibilities['stages'][node]['updated_at'],'owner_user_id':None})
        await self.graph(cid);posts=[];self.page.on('request',lambda r:posts.append(r.url) if r.method=='POST' and ('/api/runs' in r.url or '/approve' in r.url) else None)
        for node in ['logistics_scheduling','logistics_assignment']:
            await self.page.locator('[data-ux05-node='+node+']').click();panel=self.page.locator('.ux05-panel');await panel.get_by_role('button',name='Seleccionar responsable',exact=True).click();await expect(panel.locator('select')).to_be_enabled();await panel.locator('select').select_option(setup.ADMIN);await self.shot('owner-selector-'+node);await panel.get_by_role('button',name='Guardar',exact=True).click();await expect(self.page.locator('.ux05-panel .ux05-owner')).to_contain_text(admin_name);await expect(self.page.locator('[data-ux05-node='+node+']')).to_have_attribute('aria-expanded','true')
            if node=='logistics_scheduling':await expect(self.page.locator('.ux05-panel').get_by_role('button',name='Configurar y ejecutar',exact=True)).to_have_count(0)
        await self.page.locator('.ux05-panel').get_by_role('button',name='Configurar y ejecutar',exact=True).click();await self.page.locator('[data-graph-config=logistics_assignment]').wait_for();self.assertIn('case_id='+cid,self.page.url);self.assertIn('node_id=logistics_assignment',self.page.url);self.assertEqual(posts,[])
    async def test_03_approved_not_applicable_close_and_archived_readonly(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.full(cid);await self.install(cid,approved=True,trip_count=0);await self.graph(cid)
        await expect(self.page.locator('[data-graph-node=logistics_assignment] .ux05-status')).to_have_text('Aprobada');await expect(self.page.locator('[data-graph-node=logistics_scheduling] .ux05-status')).to_have_text('Bloqueada');await expect(self.page.get_by_role('button',name='Cerrar Decision Case',exact=True)).to_be_enabled();await self.page.locator('[data-ux05-node=logistics_assignment]').click();await self.shot('approved-open-1536');await self.page.locator('[data-ux05-node=logistics_scheduling]').click();await expect(self.page.locator('.ux05-panel')).to_contain_text('No requiere planificación en este Case');await self.shot('not-applicable-close-ready');await self.page.keyboard.press('Escape');await self.page.get_by_role('button',name='Cerrar Decision Case',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Cerrar Decision Case',exact=True).click();await self.page.wait_for_url('**/app/decisions?**');await self.graph(cid)
        for label in ['Cerrar Decision Case','Editar datos de origen','Editar Decision Case']:await expect(self.page.get_by_role('button',name=label,exact=True)).to_be_disabled()
        await self.page.locator('[data-ux05-node=logistics_assignment]').click();await expect(self.page.locator('.ux05-panel .ux05-owner select')).to_have_count(0);await expect(self.page.locator('.ux05-panel').get_by_role('button',name='Seleccionar responsable',exact=True)).to_have_count(0);await self.shot('archived-readonly')

    async def test_04_history_pages_and_case_selector_keep_exact_identities(self):
        _,v,c=await self.case();cid=c['case']['id'];await self.full(cid);ids=[]
        for _ in range(26):
            ids.append(await self.install(cid,status='error'))
        await self.graph(cid);await self.page.locator('[data-ux05-node=logistics_assignment]').click();await self.page.get_by_role('button',name='Ver historial',exact=True).click();await expect(self.page.locator('.ux05-history-row')).to_have_count(25);await self.shot('history-page-one');await self.page.get_by_role('button',name='Corridas anteriores',exact=True).click();await expect(self.page.locator('.ux05-history-row')).to_have_count(1);await self.page.get_by_role('button',name='Abrir corrida '+ids[0][:8],exact=True).click();await self.page.locator('[data-result-pending]').wait_for();self.assertIn('case_id='+cid,self.page.url);self.assertIn('run_id='+ids[0],self.page.url);self.assertIn('node_id=logistics_assignment',self.page.url)
        for i in range(26):await self.api('POST','/api/platform/logistics-cases',{'id':str(uuid4()),'name':'Selector UX05 '+str(i),'logistics_model_version_id':v['version']['id'],'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','operating_mode':'OPERATIONAL','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':setup.ADMIN})
        await self.graph(cid);await self.page.get_by_role('button',name='Seleccionar Decision Case',exact=True).click();dialog=self.page.locator('.dispatch-case-selector');await expect(dialog.get_by_role('button',name='Página siguiente',exact=True)).to_be_enabled();await dialog.get_by_role('button',name='Página siguiente',exact=True).click();dialog=self.page.locator('.dispatch-case-selector');await expect(dialog).to_contain_text('página 2');other=dialog.locator('[data-open-case]').first;target=await other.get_attribute('data-open-case');await other.click();await self.page.locator('[data-ux05-ready=true]').wait_for();self.assertIn('case_id='+target,self.page.url);self.assertNotEqual(target,cid);await expect(self.page.locator('.ux05-panel')).to_have_count(0)

    async def test_05_viewer_keeps_approved_visual_state_and_readonly_owner(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.full(cid);await self.install(cid,approved=True)
        viewer=await self.browser.new_context(viewport={'width':390,'height':1000});await self.login(viewer,3);page=await viewer.new_page();page.on('pageerror',lambda error:self.errors.append(str(error)));previous=self.page;self.page=page
        try:
            await self.graph(cid);await expect(page.locator('[data-graph-node=logistics_assignment] .ux05-status')).to_have_text('Aprobada');await page.locator('[data-ux05-node=logistics_assignment]').click();await expect(page.locator('.ux05-owner select')).to_have_count(0);await expect(page.locator('.ux05-owner').get_by_role('button',name='Cambiar',exact=True)).to_have_count(0);await expect(page.get_by_role('button',name='Editar datos de origen',exact=True)).to_be_disabled();await expect(page.get_by_role('button',name='Editar Decision Case',exact=True)).to_be_disabled();await expect(page.locator('.ux05-panel').get_by_role('button',name='Nueva corrida',exact=True)).to_have_count(0);await self.geometry('viewer-approved');await self.shot('viewer-approved-390')
        finally:self.page=previous;await viewer.close()

    async def test_06_keyboard_switch_outside_close_and_cancel_late_action(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.full(cid);await self.graph(cid);url=self.page.url
        d1=self.page.locator('[data-ux05-node=logistics_assignment]');d2=self.page.locator('[data-ux05-node=logistics_scheduling]');await d1.focus();await self.page.keyboard.press('Space');await expect(self.page.locator('.ux05-panel')).to_have_count(1);await d2.click();await expect(d1).to_have_attribute('aria-expanded','false');await expect(d2).to_have_attribute('aria-expanded','true');await expect(self.page.locator('.ux05-panel')).to_have_count(1);await self.page.get_by_role('button',name='Cerrar panel',exact=True).click();await expect(d2).to_be_focused();await d1.click();await self.page.get_by_role('heading',name='Decision Studio',exact=True).click();await expect(self.page.locator('.ux05-panel')).to_have_count(0)
        entered=asyncio.Event();release=asyncio.Event();finished=asyncio.Event()
        async def hold(route):
            response=await route.fetch();entered.set();await release.wait()
            try:await route.fulfill(response=response)
            except PlaywrightError:pass # The panel cancellation has already aborted this exact request.
            finally:finished.set()
        await self.page.route('**/api/platform/logistics-cases/'+cid+'/graph',hold,times=1);await d1.click();await self.page.get_by_role('button',name='Configurar y ejecutar',exact=True).click();await asyncio.wait_for(entered.wait(),15);await self.page.keyboard.press('Escape');release.set();await asyncio.wait_for(finished.wait(),15);await self.page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');self.assertEqual(self.page.url,url);await expect(self.page.locator('.ux05-panel')).to_have_count(0)

    async def test_07_strict_contrast_accessible_names_and_retry(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.full(cid);await self.graph(cid)
        for width in [1536,1280,1024,768,390,320]:
            await self.page.set_viewport_size({'width':width,'height':1000});await self.page.locator('[data-ux05-node=logistics_assignment]').click();await self.geometry('ready-open');await self.shot('ready-open-'+str(width));audit=await self.page.evaluate((Path(__file__).parent/'theme_audit.js').read_text());self.assertEqual(audit['failures'],[],audit['failures']);CONTRAST.append({'width':width,'textCount':audit['textCount'],'minimumContrast':audit['minimumContrast'],'failures':audit['failures']});(OUT/'contrast.json').write_text(json.dumps(CONTRAST,indent=2));await self.page.keyboard.press('Escape')
        await self.page.route('**/api/platform/logistics-cases/'+cid+'/context',lambda r:r.fulfill(status=503,json={'detail':'Temporalmente no disponible'}),times=1);await self.page.get_by_role('button',name='Resumen Core Config',exact=True).click();await expect(self.page.locator('.ux05-panel')).to_contain_text('Temporalmente no disponible');await self.page.get_by_role('button',name='Reintentar resumen',exact=True).click();await expect(self.page.locator('.ux05-panel')).to_contain_text('Logistics Model');await self.page.keyboard.press('Escape')

    async def test_08_current_approved_upstream_and_stale_error_queued_presentations(self):
        # Explicit metadata fixtures exercise the real server projection, not mathematical output.
        _,_,c=await self.case();cid=c['case']['id'];await self.full(cid);rid=await self.install(cid,approved=True);await self.graph(cid)
        await expect(self.page.locator('.ux05-edge')).to_have_attribute('data-active','true');await expect(self.page.locator('[data-graph-node=logistics_scheduling]')).to_have_attribute('data-node-state','READY');await expect(self.page.locator('[data-graph-node=logistics_scheduling] .ux05-status')).to_have_text('Pendiente')
        for width in [1536,1280,390]:
            await self.page.set_viewport_size({'width':width,'height':1000});await self.page.locator('[data-ux05-node=logistics_assignment]').click();await expect(self.page.locator('.ux05-panel').get_by_role('button',name='Ver dashboard',exact=True)).to_be_enabled();await self.geometry('approved-upstream-open');await self.shot('approved-d1-d2-ready-'+str(width));await self.page.keyboard.press('Escape')
        await self.page.locator('[data-ux05-node=logistics_scheduling]').click();await expect(self.page.locator('.ux05-panel').get_by_role('button',name='Configurar y ejecutar',exact=True)).to_be_enabled();await self.page.keyboard.press('Escape')
        self.sql("UPDATE decision_runs SET superseded_at=clock_timestamp() WHERE id='"+rid+"';");await self.install(cid,approved=True,stale_definition=True);await self.graph(cid);await expect(self.page.locator('[data-graph-node=logistics_assignment] .ux05-status')).to_have_text('Pendiente');await expect(self.page.locator('.ux05-edge')).to_have_attribute('data-active','false');await self.page.locator('[data-ux05-node=logistics_assignment]').click();await expect(self.page.locator('.ux05-panel')).to_contain_text('Resultado desactualizado');await self.shot('stale-result')
        for status,label in [('completed','Ver resultados y aprobar'),('queued','Ver ejecución'),('error','Ver dashboard histórico')]:
            _,_,case=await self.case();current=case['case']['id'];await self.full(current);await self.install(current,status=status)
            await self.graph(current);await expect(self.page.locator('[data-graph-node=logistics_assignment] .ux05-status')).to_have_text('Pendiente');await self.page.locator('[data-ux05-node=logistics_assignment]').click();await expect(self.page.locator('.ux05-panel').get_by_role('button',name=label,exact=True)).to_be_enabled();await self.geometry(status);await self.shot(status+'-open')

    async def test_09_pack_read_failure_is_explicit_and_case_switch_cancels_late_picker(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.page.route('**/api/platform/logistics-cases/'+cid+'/data',lambda r:r.fulfill(status=403,json={'detail':'Sin permiso de lectura del Pack'}),times=1);await self.graph(cid);await expect(self.page.locator('.ux05-case-toolbar')).to_contain_text('Información no disponible');await self.page.get_by_role('button',name='Resumen Core Config',exact=True).click();await expect(self.page.locator('#ux05-core-summary')).to_contain_text('Decision Case');await self.page.keyboard.press('Escape')
        entered=asyncio.Event();release=asyncio.Event();finished=asyncio.Event();self.addCleanup(release.set)
        async def hold(route):
            response=await route.fetch();entered.set();await release.wait()
            try:await route.fulfill(response=response)
            except PlaywrightError:pass
            finally:finished.set()
        await self.page.route('**/api/platform/decisions?dda=logistics*',hold,times=1);await self.page.get_by_role('button',name='Seleccionar Decision Case',exact=True).click();await asyncio.wait_for(entered.wait(),15);await self.page.locator('[data-ux05-node=logistics_scheduling]').click();release.set();await asyncio.wait_for(finished.wait(),15);await expect(self.page.locator('.ux05-panel')).to_contain_text('D2');await expect(self.page.locator('.dispatch-case-selector')).to_have_count(0);self.assertIn('case_id='+cid,self.page.url)
