"""W5 scoped UI/navigation over real API/SQL and explicit lifecycle metadata."""
import asyncio,json,os,select,subprocess,unittest
from pathlib import Path
from playwright.async_api import expect
import test_ultimate_case_setup as t3
import test_ultimate_case_data as t4

ROOT=Path(__file__).resolve().parents[2];REPO=ROOT.parent
OUT=Path(os.environ.get('DATION_T5_BROWSER_ARTIFACTS','/workspace/work/dation-t5/browser'))
D1='logistics_assignment';D2='logistics_scheduling'

class UltimateNavigationTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=t3.UltimateCaseSetupTests.asyncSetUp
    asyncTearDown=t3.UltimateCaseSetupTests.asyncTearDown
    login=t3.UltimateCaseSetupTests.login
    request=t3.UltimateCaseSetupTests.request
    api=t3.UltimateCaseSetupTests.api
    model=t3.UltimateCaseSetupTests.model
    case=t3.UltimateCaseSetupTests.case
    template=t4.UltimateCaseDataTests.template
    upload_api=t4.UltimateCaseDataTests.upload_api
    attach=t4.UltimateCaseDataTests.attach
    publish_ui=t4.UltimateCaseDataTests.publish_ui
    store_ui=t4.UltimateCaseDataTests.store_ui
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True,exist_ok=True);t3.OUT=OUT;cls.fixture_log=(OUT/'fixture.log').open('w')
        env=os.environ.copy()
        for k in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:env[k]=''
        for k in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(k,None)
        env.update(PYTHONDONTWRITEBYTECODE='1',DOCKER_HOST='unix:///var/run/docker.sock')
        cls.fixture=subprocess.Popen([str(REPO/'.venv/bin/python'),'-B',str(ROOT/'tests/e2e/ultimate_graph_fixture.py')],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=cls.fixture_log,text=True)
        if not select.select([cls.fixture.stdout],[],[],60)[0]:cls.fixture.terminate();cls.fixture.wait(10);raise RuntimeError('T5 fixture startup timeout')
        line=cls.fixture.stdout.readline()
        if not line:raise RuntimeError('T5 fixture failed: '+(OUT/'fixture.log').read_text()[-3000:])
        value=json.loads(line);cls.base=value['api_url'];cls.pg=value['pg_container'];cls.database=value['database']
    tearDownClass=classmethod(t3.UltimateCaseSetupTests.tearDownClass.__func__)
    async def open_map(self,cid):
        await self.page.goto(self.base+'/app/ddas/logistics/decisions?case_id='+cid,wait_until='domcontentloaded');await self.page.locator('[data-graph-ready="true"]').wait_for(timeout=30000)
    async def owner(self,cid):await self.api('PUT','/api/platform/decisions/'+cid+'/responsibilities/data_owner',{'expected_updated_at':None,'owner_user_id':t3.ADMIN})
    async def full(self,cid):
        for entity in ['transport_demand','transport_resources']:
            j=await self.upload_api(cid,entity);state=await self.api('GET',f'/api/platform/logistics-cases/{cid}/data')
            from uuid import uuid4
            await self.api('POST',f'/api/platform/logistics-cases/{cid}/data/publish',{'publication_id':str(uuid4()),'expected_revision':state['pack']['revision'],'selection':[{'slot_key':entity,'upload_id':j['id']}]})
        await self.owner(cid)
    async def install(self,cid,node=D1,**options):
        session=await self.context.request.post(self.base+'/auth/session',headers={'Origin':self.base});token=(await session.json())['access_token']
        env=os.environ.copy();env['PYTHONPATH']=str(ROOT)
        child=await asyncio.create_subprocess_exec(str(REPO/'.venv/bin/python'),'-B',str(ROOT/'tests/e2e/ultimate_graph_state.py'),cwd=ROOT,env=env,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        out,error=await child.communicate(json.dumps({'base':self.base,'token':token,'pg':self.pg,'database':self.database,'case_id':cid,'node_id':node,'options':options}).encode())
        self.assertEqual(child.returncode,0,error.decode());return json.loads(out)['run_id']
    async def test_01_empty_map_data_publish_ready_and_config_d1(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.owner(cid);await self.open_map(cid)
        await expect(self.page.locator('[data-graph-node="'+D1+'"]')).to_have_attribute('data-node-state','DATA_REQUIRED');await expect(self.page.locator('[data-graph-node="'+D2+'"]')).to_have_attribute('data-node-state','LOCKED')
        self.assertEqual(await self.page.locator('[data-graph-node]').count(),2);self.assertEqual(await self.page.get_by_text('Nuevo Decision Case por cambio de datos',exact=True).count(),0)
        await self.page.screenshot(path=str(OUT/'empty-map.png'),full_page=True,animations='disabled')
        await self.page.get_by_role('button',name='Completar datos del Case',exact=False).click();await self.page.locator('[data-ultimate-ready="true"]').wait_for();await self.store_ui(cid);await self.publish_ui();await self.page.locator('[data-pack-current-version="2"]').wait_for()
        await self.page.get_by_role('button',name='Volver al Decision Map',exact=True).click();await self.page.locator('[data-graph-ready="true"]').wait_for();await expect(self.page.locator('[data-graph-node="'+D1+'"]')).to_have_attribute('data-node-state','DATA_REQUIRED')
        await self.page.get_by_role('button',name='Completar datos del Case',exact=False).click();await self.page.locator('[data-ultimate-ready="true"]').wait_for();await self.store_ui(cid,'transport_resources');await self.publish_ui();await self.page.locator('[data-pack-current-version="3"]').wait_for();await self.page.get_by_role('button',name='Volver al Decision Map',exact=True).click();await self.page.locator('[data-graph-ready="true"]').wait_for()
        await expect(self.page.locator('[data-graph-node="'+D1+'"]')).to_have_attribute('data-node-state','READY');await self.page.get_by_role('button',name='Configurar Transport Plan',exact=False).click();await self.page.locator('[data-graph-config="'+D1+'"]').wait_for();self.assertTrue(await self.page.get_by_role('button',name='Ejecutar decisión',exact=True).is_disabled());self.assertEqual(await self.page.locator('input[type=file]').count(),0)
        await self.page.reload();await self.page.locator('[data-graph-config="'+D1+'"]').wait_for();self.assertEqual(await self.page.evaluate('new URL(location.href).searchParams.get("case_id")'),cid)
    async def test_02_approved_d1_opens_d2_config_with_exact_upstream(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.full(cid);rid=await self.install(cid,approved=True);await self.open_map(cid)
        await expect(self.page.locator('[data-graph-node="'+D2+'"]')).to_have_attribute('data-node-state','READY');await self.page.get_by_role('button',name='Configurar Day Scheduling',exact=False).click();await self.page.locator('[data-graph-config="'+D2+'"]').wait_for();await self.page.get_by_text('Upstream aprobado: '+rid,exact=True).wait_for();self.assertEqual(await self.page.locator('input[type=file]').count(),0)
        await self.page.reload();await self.page.locator('[data-graph-config="'+D2+'"]').wait_for();self.assertIn('node_id='+D2,self.page.url)
    async def test_03_history_new_run_back_forward_reload_keep_case_node_and_run(self):
        # T10 renders real published packages; T5's two-byte metadata artifacts
        # intentionally are not valid Dashboard inputs. Keep these navigation
        # assertions, now over the actual API/SQL/worker publication fixture.
        previous_base=self.base;env=os.environ.copy()
        for k in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:env[k]=''
        for k in ['DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(k,None)
        env.update(DOCKER_HOST='unix:///var/run/docker.sock',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(ROOT))
        log=(OUT/'history-published-fixture.log').open('w')
        fixture=subprocess.Popen([str(REPO/'.venv/bin/python'),'-B',str(ROOT/'tests/e2e/ultimate_consumer_fixture.py')],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
        try:
            if not await asyncio.to_thread(lambda:select.select([fixture.stdout],[],[],60)[0]):raise RuntimeError('Published history fixture timeout')
            value=json.loads(fixture.stdout.readline());self.base=value['api_url'];await self.login(self.context)
            cid=value['case_id'];up=value['d1']['id'];child=value['d2']['id']
            await self.api('POST','/api/runs/'+child+'/approve',{'case_id':cid,'node_id':D2,'expected_result_fingerprint':value['d2']['result_fingerprint']})
            await self.open_map(cid)
            self.assertEqual(await self.page.locator('.ultimate-graph-view .dispatch-decision-node__next').count(),0)
            dashboard=lambda rid:self.page.locator('.ultimate-results[data-run-id="'+rid+'"] [data-chart] svg')
            await self.page.get_by_role('button',name='Historial de Day Scheduling',exact=True).click()
            await self.page.get_by_role('button',name='Abrir corrida '+child[:8],exact=True).click();await dashboard(child).wait_for()
            await self.page.get_by_role('button',name='Nueva corrida',exact=True).click();await self.page.locator('[data-graph-config="'+D2+'"]').wait_for()
            await self.page.get_by_text('Upstream aprobado: '+up,exact=True).wait_for()
            await self.page.go_back();await dashboard(child).wait_for();await self.page.reload();await dashboard(child).wait_for()
            await self.page.go_forward();await self.page.locator('[data-graph-config="'+D2+'"]').wait_for()
            await self.page.goto(self.base+'/app/ddas/logistics/dashboard?case_id='+cid+'&node_id='+D1+'&run_id='+up);await dashboard(up).wait_for()
            await self.page.get_by_role('button',name='Nueva corrida',exact=True).click();await self.page.locator('[data-graph-config="'+D1+'"]').wait_for()
            self.assertEqual(await self.page.locator('input[type=file]').count(),0)
            source=await self.api('GET','/api/runs/'+child)
            self.assertEqual(source['upstream_run_id'],up);self.assertEqual(source['result_fingerprint'],value['d2']['result_fingerprint'])
            await self.page.screenshot(path=str(OUT/'history-real-publications.png'),full_page=True,animations='disabled')
        finally:
            self.base=previous_base
            if fixture.poll() is None:
                fixture.stdin.write('stop\n');fixture.stdin.flush();fixture.stdin.close()
                await asyncio.to_thread(fixture.wait,45)
            fixture.stdout.close();log.close()
    async def test_04_case_selector_escape_switch_and_history_navigation(self):
        _,_,a=await self.case();_,_,b=await self.case();ca=a['case']['id'];cb=b['case']['id'];await self.open_map(ca)
        trigger=self.page.get_by_role('button',name='Seleccionar Decision Case',exact=True);await trigger.click();dialog=self.page.get_by_role('dialog',name='Seleccionar Decision Case');await dialog.wait_for();await self.page.keyboard.press('Escape');await dialog.wait_for(state='hidden');self.assertTrue(await trigger.evaluate('n=>n===document.activeElement'))
        await trigger.click();await self.page.locator('[data-open-case="'+cb+'"]').click();await self.page.locator('[data-graph-ready="true"]').wait_for();self.assertIn('case_id='+cb,self.page.url)
        await self.page.go_back();await self.page.locator('[data-graph-ready="true"]').wait_for();self.assertIn('case_id='+ca,self.page.url);await self.page.go_forward();await self.page.locator('[data-graph-ready="true"]').wait_for();self.assertIn('case_id='+cb,self.page.url)
        await self.page.reload();await self.page.locator('[data-graph-ready="true"]').wait_for();self.assertEqual((await self.api('GET','/api/platform/logistics-cases/'+cb+'/data'))['version']['version'],1)
    async def test_05_viewer_touch_and_archived_preserve_read_only_state(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.full(cid)
        viewer=await self.browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);await self.login(viewer,3);page=await viewer.new_page();await page.goto(self.base+'/app/ddas/logistics/decisions?case_id='+cid);await page.locator('[data-graph-ready="true"]').wait_for();await expect(page.locator('[data-graph-node="'+D1+'"]')).to_have_attribute('data-node-state','READY');self.assertEqual(await page.get_by_role('button',name='Configurar Transport Plan',exact=False).count(),0);await page.get_by_role('button',name='Datos del Case',exact=True).tap();await page.locator('[data-ultimate-ready="true"]').wait_for();self.assertTrue(await page.get_by_role('button',name='Guardar candidato de Demanda',exact=True).is_disabled());await viewer.close()
        row=(await self.api('GET','/api/platform/logistics-cases/'+cid+'/context'))['case'];await self.api('PATCH','/api/platform/decisions/'+cid,{'expected_updated_at':row['updated_at'],'archived':True});await self.open_map(cid);await self.page.get_by_text('Case archivado. El historial permanece disponible en modo de lectura.',exact=True).wait_for();self.assertEqual(await self.page.get_by_role('button',name='Configurar Transport Plan',exact=False).count(),0)
    async def test_06_responsive_native_states_keyboard_zoom_and_contrast(self):
        _,_,c=await self.case();cid=c['case']['id'];row=(await self.api('GET','/api/platform/logistics-cases/'+cid+'/context'))['case']
        await self.api('PATCH','/api/platform/logistics-cases/'+cid+'/context',{'expected_updated_at':row['updated_at'],'name':('Distribución Buenos Aires · café · operación semanal · '*4)[:120]})
        await self.full(cid);await self.open_map(cid)
        audit=(ROOT/'tests/browser/theme_audit.js').read_text();contrast=await self.page.evaluate(audit,'.ultimate-graph-view');(OUT/'contrast.json').write_text(json.dumps(contrast,indent=2));self.assertEqual(contrast['failures'],[])
        metrics=[]
        for width in [1440,1280,1024,768,390,320]:
            await self.page.set_viewport_size({'width':width,'height':1000});await self.page.screenshot(path=str(OUT/f'map-{width}.png'),full_page=True,animations='disabled');m=await self.page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})');self.assertLessEqual(m['scroll'],width+1,m);metrics.append(m)
        await self.page.set_viewport_size({'width':1440,'height':1000});await self.page.evaluate('document.documentElement.style.zoom="2"');self.assertLessEqual(await self.page.evaluate('document.documentElement.scrollWidth'),1441);await self.page.screenshot(path=str(OUT/'map-zoom200.png'),full_page=True);await self.page.evaluate('document.documentElement.style.zoom="1"');self.assertTrue(await self.page.evaluate('matchMedia("(prefers-reduced-motion:reduce)").matches'))
        await self.page.set_viewport_size({'width':390,'height':1000});await self.page.get_by_role('button',name='Mapa de decisiones',exact=True).focus();focus=[]
        for _ in range(35):
            await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');m=await self.page.evaluate('''()=>{const n=document.activeElement,b=n.getBoundingClientRect(),hit=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);return {inside:!!n.closest('.ultimate-graph-view'),name:n.textContent.slice(0,60),hit:hit===n||n.contains(hit),top:b.top,bottom:b.bottom}}''')
            if not m['inside']:break
            self.assertTrue(m['hit'] and m['top']>=0 and m['bottom']<=1000,m);focus.append(m);await self.page.keyboard.press('Tab')
        self.assertGreaterEqual(len(focus),7);(OUT/'responsive.json').write_text(json.dumps(metrics,indent=2));(OUT/'focus.json').write_text(json.dumps(focus,indent=2))
    async def test_07_navigation_race_disposes_old_case_projection(self):
        _,_,a=await self.case();_,_,b=await self.case();ca=a['case']['id'];cb=b['case']['id'];await self.open_map(cb)
        async def delay(route):await asyncio.sleep(.4);await route.continue_()
        await self.page.route('**/logistics-cases/'+ca+'/graph*',delay)
        await self.page.evaluate('(id)=>{window.DationDispatch.openCase(id,"logistics-map",null)}',ca);await asyncio.sleep(.1);await self.page.evaluate('(id)=>{window.DationDispatch.openCase(id,"logistics-map",null)}',cb)
        await self.page.locator('[data-graph-ready="true"]').wait_for();await asyncio.sleep(.6);self.assertIn('case_id='+cb,self.page.url);self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().ultimateGraph.case_id'),cb);self.assertEqual(await self.page.locator('[data-graph-ready="true"]').count(),1)
        async def delay_picker(route):await asyncio.sleep(.2);await route.continue_()
        await self.page.route('**/api/platform/decisions?*',delay_picker);choose=self.page.get_by_role('button',name='Seleccionar Decision Case',exact=True);await choose.click();await choose.click();await self.page.get_by_role('dialog',name='Seleccionar Decision Case').first.wait_for();await asyncio.sleep(.4);self.assertEqual(await self.page.get_by_role('dialog',name='Seleccionar Decision Case').count(),1);await self.page.keyboard.press('Escape')
    async def test_08_cross_document_return_and_persisted_pageshow_restore_context(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.open_map(cid);await self.page.goto('about:blank');await self.page.go_back();await self.page.locator('[data-graph-ready="true"]').wait_for();self.assertIn('case_id='+cid,self.page.url)
        await self.page.evaluate('dispatchEvent(new PageTransitionEvent("pageshow",{persisted:true}))');await self.page.locator('[data-graph-ready="true"]').wait_for();self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().ultimateGraph.case_id'),cid)
    async def test_09_native_owner_selector_unlocks_configuration_without_changing_pack(self):
        _,_,c=await self.case();cid=c['case']['id']
        for entity in ['transport_demand','transport_resources']:
            j=await self.upload_api(cid,entity);state=await self.api('GET',f'/api/platform/logistics-cases/{cid}/data')
            from uuid import uuid4
            await self.api('POST',f'/api/platform/logistics-cases/{cid}/data/publish',{'publication_id':str(uuid4()),'expected_revision':state['pack']['revision'],'selection':[{'slot_key':entity,'upload_id':j['id']}]})
        await self.open_map(cid);self.assertEqual(await self.page.get_by_role('button',name='Configurar Transport Plan',exact=False).count(),0)
        owner=self.page.locator('[data-workflow-responsibility="data_owner"]');await owner.get_by_role('button',name='Seleccionar responsable',exact=True).click();select=owner.locator('select');await select.locator('option[value="'+t3.ADMIN+'"]').wait_for(state='attached');await select.select_option(t3.ADMIN);await owner.get_by_role('button',name='Guardar',exact=True).click();await self.page.get_by_role('button',name='Configurar Transport Plan',exact=False).wait_for()
        current=await self.api('GET',f'/api/platform/logistics-cases/{cid}/data');self.assertEqual(current['version']['version'],3);self.assertEqual(current['pack']['revision'],3)
    async def test_10_center_renders_shared_graph_and_routes_to_case_data_and_config(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.page.goto(self.base+'/app/decisions?center_case_id='+cid,wait_until='domcontentloaded')
        node=self.page.locator('[data-center-node="'+D1+'"]');await node.get_by_role('heading',name='Transport Plan',exact=True).wait_for();await node.get_by_text('Requiere datos',exact=True).wait_for()
        await node.get_by_role('link',name='Completar datos del Case',exact=True).click();await self.page.locator('[data-ultimate-ready="true"]').wait_for();self.assertIn('case_id='+cid,self.page.url)
        await self.full(cid);await self.page.goto(self.base+'/app/decisions?center_case_id='+cid,wait_until='domcontentloaded');node=self.page.locator('[data-center-node="'+D1+'"]');await node.get_by_text('Lista para configurar',exact=True).wait_for();await node.get_by_role('link',name='Configurar Transport Plan',exact=True).click();await self.page.locator('[data-graph-config="'+D1+'"]').wait_for();self.assertIn('case_id='+cid,self.page.url)

if __name__=='__main__':unittest.main()
