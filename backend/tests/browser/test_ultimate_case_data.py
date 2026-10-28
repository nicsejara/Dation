"""W4: Case Data over real API/SQL and owned private Storage-contract fixtures."""
import asyncio,csv,io,json,os,select,subprocess,unittest
from pathlib import Path
from uuid import uuid4
from playwright.async_api import async_playwright
import test_ultimate_case_setup as t3

ROOT=Path(__file__).resolve().parents[2];REPO=ROOT.parent
OUT=Path(os.environ.get('DATION_T4_BROWSER_ARTIFACTS','/tmp/dation-t4-browser'))


class UltimateCaseDataTests(unittest.IsolatedAsyncioTestCase):
    # Reuse auth/request/Model/Case helpers, not the nine T3 test methods.
    asyncSetUp=t3.UltimateCaseSetupTests.asyncSetUp
    asyncTearDown=t3.UltimateCaseSetupTests.asyncTearDown
    login=t3.UltimateCaseSetupTests.login
    request=t3.UltimateCaseSetupTests.request
    api=t3.UltimateCaseSetupTests.api
    model=t3.UltimateCaseSetupTests.model
    case=t3.UltimateCaseSetupTests.case
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True,exist_ok=True);t3.OUT=OUT;cls.fixture_log=(OUT/'fixture.log').open('w')
        env=os.environ.copy()
        for k in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:env[k]=''
        for k in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(k,None)
        env.update(PYTHONDONTWRITEBYTECODE='1',DOCKER_HOST='unix:///var/run/docker.sock')
        cls.fixture=subprocess.Popen([str(REPO/'.venv/bin/python'),'-B',str(ROOT/'tests/e2e/ultimate_data_fixture.py')],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=cls.fixture_log,text=True)
        if not select.select([cls.fixture.stdout],[],[],60)[0]:cls.fixture.terminate();cls.fixture.wait(10);raise RuntimeError('T4 fixture startup timeout')
        line=cls.fixture.stdout.readline()
        if not line:raise RuntimeError('T4 fixture failed: '+(OUT/'fixture.log').read_text()[-4000:])
        value=json.loads(line);cls.base=value['api_url'];cls.control=Path(value['control_dir'])
    tearDownClass=classmethod(t3.UltimateCaseSetupTests.tearDownClass.__func__)
    async def open_data(self,cid):
        await self.page.goto(self.base+'/app/ddas/logistics/case/data?case_id='+cid,wait_until='domcontentloaded');await self.page.locator('[data-ultimate-ready="true"]').wait_for(timeout=30000)
    async def template(self,cid,entity):
        r=await self.request('GET',f'/api/platform/logistics-cases/{cid}/data/templates/{entity}');self.assertTrue(r.ok,await r.text());return await r.body()
    async def upload_api(self,cid,entity='transport_demand'):
        data=await self.api('GET',f'/api/platform/logistics-cases/{cid}/data');raw=await self.template(cid,entity);session=await self.context.request.post(self.base+'/auth/session',headers={'Origin':self.base});token=(await session.json())['access_token']
        r=await self.context.request.post(self.base+f'/api/platform/logistics-cases/{cid}/data/uploads/{entity}?upload_id={uuid4()}&contract_hash='+data['contracts'][entity]['contract_hash'],headers={'Authorization':'Bearer '+token},multipart={'file':{'name':'operacion.csv','mimeType':'text/csv','buffer':raw}});self.assertTrue(r.ok,await r.text());return await r.json()
    async def attach(self,cid,entity='transport_demand',raw=None):
        raw=raw if raw is not None else await self.template(cid,entity)
        await self.page.locator(f'[data-t4-file="{entity}"]').set_input_files({'name':'operacion.csv','mimeType':'text/csv','buffer':raw})
        slot=self.page.locator(f'[data-t4-slot="{entity}"]');await slot.get_by_role('button',name='Guardar candidato de '+('Demanda' if entity=='transport_demand' else 'Recursos'),exact=True).wait_for();return slot
    async def store_ui(self,cid,entity='transport_demand'):
        slot=await self.attach(cid,entity);save=slot.get_by_role('button',name='Guardar candidato de '+('Demanda' if entity=='transport_demand' else 'Recursos'),exact=True);await save.wait_for();await self.page.wait_for_function('e=>!document.querySelector(`[data-t4-slot="${e}"] button[aria-busy]`)?.disabled',arg=entity)
        await save.click();await self.page.get_by_role('button',name='Seleccionar candidato',exact=True).first.wait_for()
    async def publish_ui(self):
        await self.page.get_by_role('button',name='Publicar versión del Pack',exact=True).click();dialog=self.page.get_by_role('dialog',name='Publicar Data Pack');await dialog.wait_for();await dialog.get_by_role('button',name='Publicar Pack',exact=True).click()
    async def test_01_upload_preview_publish_two_slots_and_reload(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.open_data(cid);await self.store_ui(cid)
        self.assertEqual(await self.page.locator('[data-pack-current-version]').get_attribute('data-pack-current-version'),'1')
        await self.publish_ui();await self.page.locator('[data-pack-current-version="2"]').wait_for();await self.store_ui(cid,'transport_resources');await self.publish_ui();await self.page.locator('[data-pack-current-version="3"]').wait_for()
        await self.page.reload();await self.page.locator('[data-ultimate-ready="true"]').wait_for();state=await self.api('GET',f'/api/platform/logistics-cases/{cid}/data');self.assertEqual(len(state['entries']),2);self.assertIsNone(state['decision_readiness']);self.assertFalse(state['runtime_execution_available'])
        await self.page.get_by_role('button',name='Ver manifest de versión 2',exact=True).click();await self.page.get_by_role('heading',name='Manifest de versión 2',exact=True).wait_for();(OUT/'published-case.json').write_text(json.dumps({'case_id':cid,'version':3,'entries':[e['slot_key'] for e in state['entries']],'graph_ready':None},indent=2))
    async def test_02_validation_drawer_exact_columns_and_keyboard_escape(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.open_data(cid);data=await self.api('GET',f'/api/platform/logistics-cases/{cid}/data');count=len(data['contracts']['transport_demand']['fields']);self.assertTrue(await self.page.locator('[data-t4-slot="transport_demand"]').get_by_text(str(count)+' columnas exactas',exact=True).is_visible());raw=(await self.template(cid,'transport_demand')).decode().splitlines();raw[0]+=',customer_name'
        for i in range(1,len(raw)):raw[i]+=',PRIVATE-COMMERCIAL'
        slot=await self.attach(cid,raw=('\n'.join(raw)+'\n').encode());review=slot.get_by_role('button',name='Revisar errores de Demanda',exact=True);await review.wait_for();await review.focus();await self.page.keyboard.press('Enter');drawer=self.page.get_by_role('dialog',name='Problemas de validación');await drawer.wait_for();self.assertNotIn('PRIVATE-COMMERCIAL',await drawer.inner_text());await self.page.keyboard.press('Escape');await drawer.wait_for(state='hidden');self.assertTrue(await slot.get_by_role('button',name='Elegir archivo',exact=True).evaluate('n=>n===document.activeElement'))
        columns=slot.get_by_role('button',name='Ver columnas',exact=True);await columns.click();spec=self.page.get_by_role('dialog',name='Columnas del contrato');await spec.wait_for();self.assertEqual(await spec.locator('tbody tr').count(),count);await self.page.keyboard.press('Escape');await spec.wait_for(state='hidden');self.assertTrue(await columns.evaluate('n=>n===document.activeElement'))
        await slot.get_by_role('button',name='Quitar selección',exact=True).click();self.assertEqual(await slot.locator('input[type=file]').evaluate('n=>n.files.length'),0);self.assertFalse(await review.is_visible());self.assertTrue(await slot.get_by_role('button',name='Guardar candidato de Demanda',exact=True).is_disabled())
        self.assertEqual(await self.page.locator('[data-pack-current-version]').get_attribute('data-pack-current-version'),'1');state=await self.api('GET',f'/api/platform/logistics-cases/{cid}/data');self.assertEqual(state['uploads'],[])
    async def test_03_interrupted_upload_reload_recovery_and_publish(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.open_data(cid);(self.control/'fail-t4-store').touch();slot=await self.attach(cid);await slot.get_by_role('button',name='Guardar candidato de Demanda',exact=True).click();await self.page.get_by_role('button',name='Consultar carga pendiente de Demanda',exact=True).wait_for()
        await self.page.get_by_role('button',name='Consultar carga pendiente de Demanda',exact=True).click();await self.page.get_by_role('button',name='Recuperar candidato',exact=True).wait_for();await self.page.get_by_role('button',name='Recuperar candidato',exact=True).click();await self.page.get_by_role('button',name='Seleccionar candidato',exact=True).wait_for();self.assertEqual(await self.page.locator('[data-pack-current-version]').get_attribute('data-pack-current-version'),'1');await self.publish_ui();await self.page.locator('[data-pack-current-version="2"]').wait_for()
    async def test_04_lost_publication_response_recovers_same_intent(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.open_data(cid);await self.store_ui(cid);(self.control/'lose-t4-publish-response').touch();await self.publish_ui();await self.page.get_by_text('No se confirmó la publicación. Recuperá la misma intención antes de publicar otra versión.',exact=True).wait_for()
        self.page.on('dialog',lambda d:d.accept());await self.page.reload();await self.page.get_by_role('button',name='Recuperar publicación',exact=True).wait_for();await self.page.get_by_role('button',name='Recuperar publicación',exact=True).click();await self.page.locator('[data-pack-current-version="2"]').wait_for();state=await self.api('GET',f'/api/platform/logistics-cases/{cid}/data');self.assertEqual(state['history_total'],2)
    async def test_05_compatible_reuse_and_cas_conflict_keep_selection(self):
        m,v,c=await self.case();cid=c['case']['id'];j=await self.upload_api(cid);await self.open_data(cid);await self.page.get_by_role('button',name='Seleccionar candidato',exact=True).click()
        await self.api('POST',f'/api/platform/logistics-cases/{cid}/data/publish',{'publication_id':str(uuid4()),'expected_revision':1,'selection':[{'slot_key':'transport_demand','upload_id':j['id']}]});await self.publish_ui();await self.page.get_by_role('button',name='Recargar Pack y revisar',exact=True).wait_for();await self.page.get_by_role('button',name='Recargar Pack y revisar',exact=True).click();await self.page.locator('[data-pack-current-version="2"]').wait_for()
        slot=self.page.locator('[data-t4-slot="transport_demand"]');await slot.get_by_role('button',name='Reutilizar anterior',exact=False).click();await slot.get_by_role('button',name='Seleccionar input compatible',exact=True).wait_for();await slot.get_by_role('button',name='Seleccionar input compatible',exact=True).first.click();self.assertTrue(await self.page.get_by_role('button',name='Publicar versión del Pack',exact=True).is_enabled())
    async def test_06_responsive_long_filename_zoom_touch_contrast_and_focus(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.open_data(cid);raw=await self.template(cid,'transport_demand');name=('Distribución Buenos Aires · planificación operativa semanal · centros de transferencia · '+('zona-sur-'*5))[:116]+'.csv';await self.page.locator('[data-t4-file="transport_demand"]').set_input_files({'name':name,'mimeType':'text/csv','buffer':raw});await self.page.get_by_text('Válido: 5 filas. 0 advertencias. Todavía no está publicado.',exact=True).wait_for()
        audit=(ROOT/'tests/browser/theme_audit.js').read_text();contrast=await self.page.evaluate(audit,'.ultimate-case-data');(OUT/'contrast.json').write_text(json.dumps(contrast,indent=2));self.assertEqual(contrast['failures'],[])
        metrics=[]
        for width in [1440,1280,1024,768,390,320]:
            await self.page.set_viewport_size({'width':width,'height':1000});await self.page.evaluate('scrollTo(0,0)');await self.page.screenshot(path=str(OUT/f'case-data-{width}.png'),full_page=True,animations='disabled');m=await self.page.evaluate('''()=>{const slot=document.querySelector('[data-t4-slot="transport_demand"]'),badge=slot.querySelector('.dispatch-pro-state-badge').getBoundingClientRect(),icon=getComputedStyle(slot.querySelector('.dispatch-pro-entity-icon svg')),choose=slot.querySelector('.dispatch-pro-choose').getBoundingClientRect(),th=slot.querySelector('th');return {width:innerWidth,scroll:document.documentElement.scrollWidth,badgeHeight:badge.height,badgeWidth:badge.width,iconFill:icon.fill,iconStroke:icon.stroke,iconWidth:parseFloat(icon.width),chooseHeight:choose.height,headerWhitespace:getComputedStyle(th).whiteSpace}}''');self.assertLessEqual(m['scroll'],width+1,m);self.assertLess(m['badgeHeight'],40,m);self.assertGreater(m['badgeWidth'],60,m);self.assertEqual(m['iconFill'],'none');self.assertNotEqual(m['iconStroke'],'none');self.assertEqual(m['iconWidth'],20);self.assertLess(m['chooseHeight'],50,m);self.assertEqual(m['headerWhitespace'],'nowrap');metrics.append(m)
        await self.page.set_viewport_size({'width':1440,'height':1000});await self.page.evaluate('document.documentElement.style.zoom="2"');self.assertLessEqual(await self.page.evaluate('document.documentElement.scrollWidth'),1441);await self.page.screenshot(path=str(OUT/'case-data-zoom200.png'),full_page=True);await self.page.evaluate('document.documentElement.style.zoom="1"');self.assertTrue(await self.page.evaluate('matchMedia("(prefers-reduced-motion:reduce)").matches'))
        await self.page.set_viewport_size({'width':390,'height':1000});await self.page.locator('.ultimate-case-data header button').focus();focus=[]
        for _ in range(45):
            await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');m=await self.page.evaluate('''()=>{const n=document.activeElement,b=n.getBoundingClientRect(),hit=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);return {inside:!!n.closest('.ultimate-case-data'),name:n.getAttribute('aria-label')||n.textContent.slice(0,50),top:b.top,bottom:b.bottom,hit:hit===n||n.contains(hit)}}''')
            if not m['inside']:break
            self.assertTrue(m['hit'] and m['top']>=0 and m['bottom']<=1000,m);focus.append(m);await self.page.keyboard.press('Tab')
        self.assertGreater(len(focus),10);(OUT/'responsive.json').write_text(json.dumps(metrics,indent=2));(OUT/'keyboard-focus.json').write_text(json.dumps(focus,indent=2))
    async def test_07_viewer_reads_and_setup_context_link_is_recoverable(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.page.goto(self.base+'/app/ddas/logistics/case?case_id='+cid,wait_until='domcontentloaded');await self.page.get_by_role('button',name='Administrar datos del Case',exact=True).wait_for();await self.page.get_by_role('button',name='Administrar datos del Case',exact=True).click();await self.page.locator('[data-ultimate-ready="true"]').wait_for()
        viewer=await self.browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);await self.login(viewer,3);page=await viewer.new_page();await page.goto(self.base+'/app/ddas/logistics/case/data?case_id='+cid,wait_until='domcontentloaded');await page.locator('[data-ultimate-ready="true"]').wait_for();self.assertTrue(await page.get_by_role('button',name='Guardar candidato de Demanda',exact=True).is_disabled());await page.get_by_role('button',name='Contexto del Case',exact=True).tap();await page.get_by_role('button',name='Administrar datos del Case',exact=True).wait_for();await viewer.close()
    async def test_08_saving_one_slot_keeps_the_other_selected_csv(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.open_data(cid);d=await self.attach(cid);r=await self.attach(cid,'transport_resources')
        await self.page.wait_for_function('!document.querySelector("[data-t4-slot=transport_resources] button[aria-busy]")?.disabled')
        await d.get_by_role('button',name='Guardar candidato de Demanda',exact=True).click();await self.page.get_by_text('Candidato de Demanda guardado. El otro CSV seleccionado se conserva hasta que lo guardes o quites.',exact=True).wait_for()
        self.assertEqual(await r.locator('input[type=file]').evaluate('n=>n.files.length'),1);self.assertTrue(await self.page.get_by_role('button',name='Publicar versión del Pack',exact=True).is_disabled())
        await r.get_by_role('button',name='Guardar candidato de Recursos',exact=True).click();await self.page.get_by_role('button',name='Seleccionar candidato',exact=True).first.wait_for();await self.publish_ui();await self.page.locator('[data-pack-current-version="2"]').wait_for();state=await self.api('GET',f'/api/platform/logistics-cases/{cid}/data');self.assertEqual(len(state['entries']),2);self.assertEqual(await self.page.get_by_text('operacion.csv · Publicado en el Pack vigente',exact=True).count(),2)


if __name__=='__main__':unittest.main()
