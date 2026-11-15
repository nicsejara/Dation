"""UX04 real Core/Studio browser integration in opt-in private local fixture."""
import asyncio,json,os,select,subprocess,unittest
from pathlib import Path
from uuid import uuid4
from playwright.async_api import expect
import test_ultimate_case_setup as setup
import test_ultimate_case_data as pack
import test_saga01_planning as saga
import test_ultimate_navigation as nav
from wizard_helpers import select_model
OUT=Path('/tmp/dation-ux04-browser')
class UnifiedDecisionJourneyTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True,exist_ok=True);setup.OUT=OUT;cls.fixture_log=(OUT/'fixture.log').open('w')
        env=os.environ.copy()
        for k in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:env[k]=''
        for k in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(k,None)
        env.update(PYTHONDONTWRITEBYTECODE='1',DOCKER_HOST='unix:///var/run/docker.sock')
        cls.fixture=subprocess.Popen([setup.RUNTIME_PYTHON,'-B',str(setup.ROOT/'tests/e2e'/getattr(cls,'fixture_name','journey_fixture.py'))],cwd=setup.ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=cls.fixture_log,text=True)
        if not select.select([cls.fixture.stdout],[],[],60)[0]:raise RuntimeError('UX04 startup timeout')
        line=cls.fixture.stdout.readline()
        if not line:raise RuntimeError((OUT/'fixture.log').read_text()[-4000:])
        v=json.loads(line);cls.base=v['api_url'];cls.control=Path(v['control_dir']);cls.pg=v['pg_container'];cls.database=v['database']
    tearDownClass=classmethod(setup.UltimateCaseSetupTests.tearDownClass.__func__)
    asyncSetUp=setup.UltimateCaseSetupTests.asyncSetUp
    async def asyncTearDown(self):
        try:
            self.sql("UPDATE dation_private.journey_preparations SET status='EXPIRED' WHERE status IN('DRAFT','VALIDATED','FINALIZING');")
            ids=json.loads(self.sql("SELECT coalesce(jsonb_agg(id),'[]') FROM dation_private.journey_preparations;"))
            for pid in ids:await self.request('POST','/api/platform/data-preparations/'+pid+'/cleanup',{})
        finally:await setup.UltimateCaseSetupTests.asyncTearDown(self)
    def sql(self,sql):
        env={**os.environ,'DOCKER_HOST':'unix:///var/run/docker.sock'}
        check=subprocess.run(['docker','inspect','--format','{{index .Config.Labels "dation.qa.phase"}}',self.pg],env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(check.stdout.strip(),'T5')
        r=subprocess.run(['docker','exec','-i',self.pg,'psql','-U','postgres','-d',self.database,'-X','-A','-t','-v','ON_ERROR_STOP=1'],input=sql,env=env,capture_output=True,text=True,timeout=30);self.assertEqual(r.returncode,0,r.stderr);return r.stdout.strip()
    install=nav.UltimateNavigationTests.install
    full=nav.UltimateNavigationTests.full
    owner=nav.UltimateNavigationTests.owner
    upload_api=pack.UltimateCaseDataTests.upload_api
    template=pack.UltimateCaseDataTests.template
    login=setup.UltimateCaseSetupTests.login
    request=setup.UltimateCaseSetupTests.request
    api=setup.UltimateCaseSetupTests.api
    model=setup.UltimateCaseSetupTests.model
    case=setup.UltimateCaseSetupTests.case
    open=setup.UltimateCaseSetupTests.open
    fill_case=saga.Saga01PlanningTests.fill_case
    async def capture(self,**options):
        await self.page.mouse.move(0,0);await self.page.evaluate('document.activeElement?.blur();window.scrollTo(0,0)');await self.page.evaluate('new Promise(requestAnimationFrame)');return await self.page.screenshot(**options)
    async def selected(self):
        m,v=await self.model('Operación UX04');await self.page.goto(self.base+'/app/ddas/logistics',wait_until='domcontentloaded');await self.page.get_by_role('button',name='Comenzar',exact=True).click();await self.page.locator('.ultimate-foundation[data-ultimate-ready=true]').wait_for();await select_model(self.page,m['model']['id'],v['version']['id']);await expect(self.page.locator('[data-journey-skip]')).to_be_enabled();return m,v
    async def attach(self,entity):
        r=await self.request('POST','/api/platform/logistics-models/contract-preview/templates/'+entity,{'model_id':self.m['model']['id'],'version_id':self.v['version']['id']});self.assertTrue(r.ok,await r.text());raw=await r.body()
        host=self.page.locator('[data-preparation-entity='+entity+']');await host.locator('input[type=file]').set_input_files({'name':entity+'.csv','mimeType':'text/csv','buffer':raw});b=host.get_by_role('button',name='Guardar candidato de '+('Órdenes / Demanda' if entity=='transport_demand' else 'Flota / Recursos'),exact=True);await expect(b).to_be_enabled();await b.click();await expect(host).to_contain_text('Candidato guardado · no publicado');return host
    async def test_01_pre_case_two_uploads_refresh_and_finalize(self):
        self.m,self.v=await self.selected();
        async with self.page.expect_response(lambda r:r.url.endswith('/owner') and r.request.method=='PUT') as response:await self.page.get_by_label('Data Owner',exact=True).select_option(setup.ADMIN)
        self.assertTrue((await response.value).ok)
        self.assertEqual(await self.page.locator('[data-dation-test=core-model]').evaluate('n=>n.tagName'),'SECTION');self.assertEqual(await self.page.locator('[data-dation-test=core-contract] > summary').count(),0)
        await self.attach('transport_demand');await self.attach('transport_resources');await expect(self.page.locator('[data-journey-next]')).to_be_enabled()
        await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for();await self.page.locator('[data-dation-test=core-step-2]').click();await expect(self.page.locator('[data-journey-next]')).to_be_enabled()
        await self.page.locator('[data-journey-next]').click();await self.fill_case('Journey con datos');await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click();await self.page.wait_for_url('**/decisions?**',timeout=30000);await self.page.locator('[data-graph-ready=true]').wait_for();await expect(self.page.locator('.journey-studio-rail')).to_contain_text('Decision Studio');await expect(self.page.locator('.journey-studio-content')).to_contain_text('Demanda: 5 filas');await expect(self.page.locator('.journey-studio-content')).to_contain_text('Data Owner: Miembro del equipo')
    async def test_02_skip_empty_graph_prepare_same_case_and_edit_return(self):
        self.m,self.v=await self.selected();await self.page.locator('[data-journey-skip]').click();await self.fill_case('Journey pendiente');await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click();await self.page.wait_for_url('**/decisions?**');await self.page.locator('[data-graph-ready=true]').wait_for();url=self.page.url
        await self.page.get_by_role('button',name='Editar Decision Case',exact=True).first.click();await self.page.locator('[data-ultimate-ready=true]').wait_for();await expect(self.page.locator('.core-wizard')).to_have_attribute('data-active-step','3');await self.page.get_by_label('Nombre del Case',exact=True).fill('Journey editado');await self.page.get_by_role('button',name='Guardar contexto',exact=True).click();await self.page.locator('[data-graph-ready=true]').wait_for();self.assertEqual(self.page.url,url)
        await self.page.get_by_role('button',name='Preparar datos',exact=True).first.click();await self.page.locator('[data-ultimate-ready=true]').first.wait_for();await expect(self.page.locator('.core-wizard')).to_have_attribute('data-active-step','2');self.assertIn('case_id=',self.page.url)
        from urllib.parse import parse_qs,urlparse
        cid=parse_qs(urlparse(self.page.url).query)['case_id'][0];raw=await self.template(cid,'transport_demand');host=self.page.locator('[data-t4-slot=transport_demand]');await host.locator('input[type=file]').set_input_files({'name':'same-case.csv','mimeType':'text/csv','buffer':raw});save=host.get_by_role('button',name='Guardar candidato de Demanda',exact=True);await expect(save).to_be_enabled();await save.click();await self.page.locator('[data-pack-ready=true]').wait_for();await self.page.get_by_role('button',name='Publicar versión del Pack',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Publicar Pack',exact=True).click();await self.page.locator('[data-pack-current-version="2"]').wait_for();state=await self.api('GET','/api/platform/logistics-cases/'+cid+'/data');self.assertEqual(state['pack']['case_id'],cid);self.assertEqual(state['history_total'],2)

    async def open_map(self,cid):
        await self.page.goto(self.base+'/app/ddas/logistics/decisions?case_id='+cid,wait_until='domcontentloaded');await self.page.locator('[data-graph-ready=true]').wait_for()
    async def test_03_derivation_cancel_confirm_and_original_immutable(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.full(cid);rid=await self.install(cid,approved=True);before=await self.api('GET','/api/platform/logistics-cases/'+cid+'/data');await self.open_map(cid);url=self.page.url
        await self.page.get_by_role('button',name='Editar datos de origen',exact=True).first.click();dialog=self.page.get_by_role('dialog');await expect(dialog).to_contain_text('Crear una nueva planificación');await dialog.get_by_role('button',name='Cancelar',exact=True).click();self.assertEqual(self.page.url,url)
        await self.page.get_by_role('button',name='Editar datos de origen',exact=True).first.click();await dialog.get_by_role('button',name='Preparar nuevo Decision Case',exact=True).click();await self.page.locator('[data-ultimate-ready=true]').wait_for();await expect(self.page.locator('.core-wizard')).to_have_attribute('data-active-step','2');self.assertNotIn('case_id',__import__('urllib.parse',fromlist=['urlparse','parse_qs']).parse_qs(__import__('urllib.parse',fromlist=['urlparse']).urlparse(self.page.url).query))
        await self.capture(path=str(OUT/'derivation.png'),full_page=True,animations='disabled');await self.page.locator('[data-journey-skip]').click();await self.fill_case('Derivado UX04');await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click();await self.page.locator('[data-graph-ready=true]').wait_for();from urllib.parse import parse_qs,urlparse
        new=parse_qs(urlparse(self.page.url).query)['case_id'][0];self.assertNotEqual(new,cid);after=await self.api('GET','/api/platform/logistics-cases/'+cid+'/data');self.assertEqual(before['pack'],after['pack']);g=await self.api('GET','/api/platform/logistics-cases/'+cid+'/graph');self.assertEqual(g['graph']['nodes'][0]['approved_run_id'],rid);self.assertEqual(self.sql("SELECT parent_case_id FROM dation_private.journey_case_events WHERE case_id='"+new+"';"),cid)
    async def test_04_frozen_context_and_historical_return_survive_reload(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.full(cid);rid=await self.install(cid,approved=True);await self.open_map(cid)
        await self.page.get_by_role('button',name='Editar Decision Case',exact=True).first.click();await self.page.locator('[data-ultimate-ready=true]').wait_for();await expect(self.page.get_by_label('Inicio de planificación',exact=True)).to_be_disabled();await expect(self.page.get_by_role('button',name='Crear nuevo Case a partir de este',exact=True)).to_be_visible();await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for();await self.page.get_by_label('Nombre del Case',exact=True).fill('Administración conservada');await self.page.get_by_role('button',name='Guardar contexto',exact=True).click();await self.page.locator('[data-graph-ready=true]').wait_for();self.assertIn('case_id='+cid,self.page.url);g=await self.api('GET','/api/platform/logistics-cases/'+cid+'/graph');self.assertEqual(g['graph']['nodes'][0]['approved_run_id'],rid)
    async def test_05_close_not_applicable_revalidates_and_returns_center(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.full(cid);await self.install(cid,approved=True,trip_count=0);await self.open_map(cid);close=self.page.get_by_role('button',name='Cerrar Decision Case',exact=True);await expect(close).to_be_enabled();await close.click();dialog=self.page.get_by_role('dialog');await dialog.get_by_role('button',name='Cerrar Decision Case',exact=True).click();await self.page.wait_for_url('**/app/decisions?**');row=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context');self.assertEqual(row['case']['status'],'archived');state=await self.api('GET','/api/platform/logistics-cases/'+cid+'/journey');self.assertIsNotNone(state['lifecycle']['closed_at'])
    async def test_06_invalid_csv_has_real_report_and_no_false_candidate(self):
        self.m,self.v=await self.selected();host=self.page.locator('[data-preparation-entity=transport_demand]');await host.locator('input[type=file]').set_input_files({'name':'bad.csv','mimeType':'text/csv','buffer':b'wrong\nnot-a-row\n'});await expect(host).to_contain_text('Con errores');await expect(host.get_by_role('button',name='Guardar candidato de Órdenes / Demanda',exact=True)).to_be_disabled();await expect(self.page.locator('[data-journey-next]')).to_be_disabled();await host.get_by_role('button',name='Ver detalle de Órdenes / Demanda',exact=True).click();await expect(self.page.get_by_role('dialog')).to_be_visible()
    async def test_07_screenshots_core_studio_responsive_and_pending_closure(self):
        self.m,self.v=await self.selected();await self.page.set_viewport_size({'width':1536,'height':960});await self.capture(path=str(OUT/'core02-empty-1536.png'),full_page=True,animations='disabled');await self.attach('transport_demand');await self.attach('transport_resources');await self.capture(path=str(OUT/'core02-valid-1536.png'),full_page=True,animations='disabled')
        measurements=[]
        for width in [1536,1024,768,390,320]:
            await self.page.set_viewport_size({'width':width,'height':960});await self.page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');measurements.append(await self.page.evaluate("""()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth})"""));self.assertFalse(measurements[-1]['overflow'],measurements[-1])
            if width==390:await self.capture(path=str(OUT/'core02-valid-390.png'),full_page=True,animations='disabled')
        (OUT/'responsive.json').write_text(json.dumps(measurements,indent=2));await self.page.set_viewport_size({'width':1536,'height':960});await self.page.locator('[data-dation-test=core-step-1]').click();await self.capture(path=str(OUT/'core01-1536.png'),full_page=True,animations='disabled');await self.page.locator('[data-dation-test=core-step-3]').click();await self.fill_case('Visual UX04');await self.capture(path=str(OUT/'core03-1536.png'),full_page=True,animations='disabled');await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click();await self.page.locator('[data-graph-ready=true]').wait_for();await self.capture(path=str(OUT/'studio-graph-1536.png'),full_page=True,animations='disabled');await expect(self.page.get_by_role('button',name='Cerrar Decision Case',exact=True)).to_be_disabled();await self.page.set_viewport_size({'width':390,'height':960});await self.page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');overflow=await self.page.evaluate("""()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,nodes:[...document.querySelectorAll('body *')].filter(n=>n.getBoundingClientRect().right>innerWidth+1).slice(0,30).map(n=>({tag:n.tagName,class:n.className,width:n.getBoundingClientRect().width,right:n.getBoundingClientRect().right,display:getComputedStyle(n).display,parent:n.parentElement?.outerHTML.slice(0,800),ancestors:[n.parentElement,n.parentElement?.parentElement,n.parentElement?.parentElement?.parentElement,n.parentElement?.parentElement?.parentElement?.parentElement,n.parentElement?.parentElement?.parentElement?.parentElement?.parentElement,n.parentElement?.parentElement?.parentElement?.parentElement?.parentElement?.parentElement].filter(Boolean).map(p=>({tag:p.tagName,class:p.className,display:getComputedStyle(p).display,columns:getComputedStyle(p).gridTemplateColumns,x:p.getBoundingClientRect().x,width:p.getBoundingClientRect().width}))}))})""");(OUT/'studio-overflow.json').write_text(json.dumps(overflow,indent=2));self.assertFalse(overflow['scroll']>overflow['width'],overflow);await self.capture(path=str(OUT/'studio-graph-390.png'),full_page=True,animations='disabled')

    async def test_09_finalize_storage_failure_reload_recovers_same_case(self):
        self.m,self.v=await self.selected();await self.attach('transport_demand');await self.attach('transport_resources');await self.page.locator('[data-journey-next]').click();await self.fill_case('Reintento durable UX04');(self.control/'fail-t4-publish').touch();await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click();await expect(self.page.locator('.ultimate-footer [role=alert]')).to_be_visible();self.assertIn('/case?',self.page.url);rows=json.loads(self.sql("SELECT jsonb_agg(creation_body->>'id') FROM dation_private.journey_preparations WHERE status='FINALIZING';"));self.assertEqual(len(rows),1);cid=rows[0]
        await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for();await self.page.locator('[data-dation-test=core-step-2]').click();await self.page.get_by_role('button',name='Recuperar creación del Case',exact=True).click();await self.page.locator('[data-graph-ready=true]').wait_for();self.assertIn('case_id='+cid,self.page.url);self.assertEqual(self.sql("SELECT count(*) FROM case_data_pack_versions WHERE case_id='"+cid+"';"),'2')
    async def test_10_expired_preparation_cleanup_starts_new_stage_without_case(self):
        self.m,self.v=await self.selected();await self.attach('transport_demand');pid=self.sql("SELECT id FROM dation_private.journey_preparations WHERE status='DRAFT' ORDER BY created_at DESC LIMIT 1;");self.sql("UPDATE dation_private.journey_preparations SET expires_at=now()-interval '1 second' WHERE id='"+pid+"';");await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for();await self.page.locator('[data-dation-test=core-step-2]').click();await expect(self.page.locator('.journey-preparation-status')).to_contain_text('venció');await self.page.get_by_role('button',name='Limpiar preparación expirada e iniciar otra',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Limpiar e iniciar',exact=True).click();await expect(self.page.locator('[data-journey-skip]')).to_be_enabled();self.assertEqual(self.sql("SELECT count(*) FROM dation_private.journey_uploads WHERE preparation_id='"+pid+"' AND NOT cleaned;"),'0')

    async def test_11_model_change_requires_derivation_without_mutating_existing_binding(self):
        _,v,c=await self.case();cid=c['case']['id'];await self.open('/app/ddas/logistics/case?case_id='+cid+'&core_step=1');await expect(self.page.locator('.core-wizard')).to_have_attribute('data-active-step','1');await self.page.get_by_role('button',name='Crear un Case con otra Model Version',exact=True).click();dialog=self.page.get_by_role('dialog');await expect(dialog).to_contain_text('Model Version vinculada es inmutable');await dialog.get_by_role('button',name='Preparar nuevo Decision Case',exact=True).click();await self.page.locator('[data-ultimate-ready=true]').wait_for();await expect(self.page.locator('.core-wizard')).to_have_attribute('data-active-step','2');current=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context');self.assertEqual(current['case']['logistics_model_version_id'],v['version']['id']);self.assertEqual(self.sql("SELECT count(*) FROM decision_cases WHERE id='"+cid+"';"),'1')

    async def test_12_real_warning_stays_candidate_not_published(self):
        import csv,io
        self.m,self.v=await self.selected();response=await self.request('POST','/api/platform/logistics-models/contract-preview/templates/transport_resources',{'model_id':self.m['model']['id'],'version_id':self.v['version']['id']});raw=await response.body();reader=csv.DictReader(io.StringIO(raw.decode()));row=next(reader);row['operating_cost_per_km']='';out=io.StringIO();writer=csv.DictWriter(out,fieldnames=reader.fieldnames,lineterminator='\n');writer.writeheader();writer.writerow(row)
        before=self.sql('SELECT count(*) FROM decision_cases;');host=self.page.locator('[data-preparation-entity=transport_resources]');await host.locator('input[type=file]').set_input_files({'name':'warning.csv','mimeType':'text/csv','buffer':out.getvalue().encode()});await expect(host).to_contain_text('1 advertencias');await host.get_by_role('button',name='Ver detalle de Flota / Recursos',exact=True).click();await expect(self.page.get_by_role('dialog')).to_contain_text('Costo desconocido');await self.page.keyboard.press('Escape');await host.get_by_role('button',name='Guardar candidato de Flota / Recursos',exact=True).click();await expect(host).to_contain_text('Candidato guardado · no publicado');self.assertEqual(self.sql('SELECT count(*) FROM decision_cases;'),before);await self.capture(path=str(OUT/'core02-warning-1536.png'),full_page=True,animations='disabled')

    async def test_13_late_validation_cannot_mix_model_versions(self):
        second,version=await self.model('Segunda versión UX04');self.m,self.v=await self.selected();response=await self.request('POST','/api/platform/logistics-models/contract-preview/templates/transport_demand',{'model_id':self.m['model']['id'],'version_id':self.v['version']['id']});raw=await response.body();entered=asyncio.Event();release=asyncio.Event();self.addCleanup(release.set)
        async def hold(route):
            r=await route.fetch();entered.set();await release.wait();await route.fulfill(response=r)
        await self.page.route('**/api/platform/data-preparations/*/validate/transport_demand?**',hold,times=1);await self.page.locator('[data-journey-file=transport_demand]').set_input_files({'name':'old.csv','mimeType':'text/csv','buffer':raw});await entered.wait();await self.page.locator('[data-dation-test=core-step-1]').click();
        # Select the next Model; the explicit confirmation explains the discarded local selection.
        selecting=asyncio.create_task(select_model(self.page,second['model']['id'],version['version']['id']));dialog=self.page.get_by_role('dialog').filter(has_text='Cambió la Model Version');await dialog.get_by_role('button',name='Preparar esta versión',exact=True).click();await selecting;release.set();await expect(self.page.locator('[data-journey-skip]')).to_be_enabled();await expect(self.page.locator('[data-journey-next]')).to_be_disabled();await expect(self.page.locator('.journey-preparation-status')).to_contain_text('0 de 2');self.assertEqual(await self.page.locator('[data-preparation-entity=transport_demand] .dispatch-pro-file-panel:visible').count(),0)


class JourneyEngineTests(unittest.IsolatedAsyncioTestCase):
    capture=UnifiedDecisionJourneyTests.capture
    fixture_name='journey_result_fixture.py'
    setUpClass=classmethod(UnifiedDecisionJourneyTests.setUpClass.__func__)
    tearDownClass=classmethod(setup.UltimateCaseSetupTests.tearDownClass.__func__)
    asyncSetUp=setup.UltimateCaseSetupTests.asyncSetUp
    asyncTearDown=setup.UltimateCaseSetupTests.asyncTearDown
    login=setup.UltimateCaseSetupTests.login
    request=setup.UltimateCaseSetupTests.request
    api=setup.UltimateCaseSetupTests.api
    model=setup.UltimateCaseSetupTests.model
    case=setup.UltimateCaseSetupTests.case
    template=pack.UltimateCaseDataTests.template
    owner=nav.UltimateNavigationTests.owner
    async def test_08_real_d1_d2_approval_returns_graph_and_exact_dashboard_origin(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.owner(cid)
        session=await self.context.request.post(self.base+'/auth/session',headers={'Origin':self.base});token=(await session.json())['access_token']
        for entity in ['transport_demand','transport_resources']:
            raw=await self.template(cid,entity);raw=b'\n'.join(raw.splitlines()[:2])+b'\n';state=await self.api('GET','/api/platform/logistics-cases/'+cid+'/data')
            r=await self.context.request.post(self.base+'/api/platform/logistics-cases/'+cid+'/data/uploads/'+entity+'?'+__import__('urllib.parse',fromlist=['urlencode']).urlencode({'upload_id':str(uuid4()),'contract_hash':state['contracts'][entity]['contract_hash']}),headers={'Authorization':'Bearer '+token},multipart={'file':{'name':'feasible.csv','mimeType':'text/csv','buffer':raw}});self.assertTrue(r.ok,await r.text());j=await r.json();await self.api('POST','/api/platform/logistics-cases/'+cid+'/data/publish',{'publication_id':str(uuid4()),'expected_revision':state['pack']['revision'],'selection':[{'slot_key':entity,'upload_id':j['id']}]})
        await self.page.goto(self.base+'/app/ddas/logistics/decisions?case_id='+cid,wait_until='domcontentloaded');await self.page.locator('[data-graph-ready=true]').wait_for()
        approved=[]
        for node in ['logistics_assignment','logistics_scheduling']:
            await self.page.locator('[data-graph-node='+node+'] [data-map-action]').first.click();await self.page.locator('[data-graph-config='+node+']').wait_for();await expect(self.page.get_by_role('button',name='Ejecutar decisión',exact=True)).to_be_enabled();await self.capture(path=str(OUT/(node+'-configuration-1536.png')),full_page=True,animations='disabled');await self.page.get_by_role('button',name='Ejecutar decisión',exact=True).click();await self.page.locator('.ultimate-results [data-chart] svg').wait_for(timeout=45000);await self.page.locator('.journey-studio-rail').wait_for();dashboard_url=self.page.url
            if node=='logistics_assignment':
                await self.page.get_by_role('button',name='Editar Decision Case',exact=True).click();await self.page.locator('[data-ultimate-ready=true]').wait_for();await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for();await self.page.get_by_label('Nombre del Case',exact=True).fill('Origen histórico exacto');await self.page.get_by_role('button',name='Guardar contexto',exact=True).click();await self.page.locator('.ultimate-results [data-chart] svg').wait_for();self.assertEqual(self.page.url,dashboard_url)
            await self.capture(path=str(OUT/(node+'-dashboard-1536.png')),full_page=True,animations='disabled');
            for width in [1024,768,390,320]:
                await self.page.set_viewport_size({'width':width,'height':960});await self.page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'),{'node':node,'width':width})
                if width==390:await self.capture(path=str(OUT/(node+'-dashboard-390.png')),full_page=True,animations='disabled')
            await self.page.set_viewport_size({'width':1536,'height':960});await self.page.locator('[data-check-review]').click();await expect(self.page.locator('[data-approve-package]')).to_be_enabled();if_lost=node=='logistics_assignment'
            if if_lost:
                async def lost(route):
                    response=await route.fetch();self.assertTrue(response.ok);await route.abort('failed')
                await self.page.route('**/api/runs/*/approve',lost,times=1)
            await self.page.locator('[data-approve-package]').click();await self.page.wait_for_url('**/decisions?**',timeout=30000);await self.page.locator('[data-graph-ready=true]').wait_for();g=await self.api('GET','/api/platform/logistics-cases/'+cid+'/graph');n=next(n for n in g['graph']['nodes'] if n['id']==node);self.assertEqual(n['node_state'],'APPROVED');approved.append(n['approved_run_id'])
            if node=='logistics_assignment':self.assertEqual(g['graph']['nodes'][1]['node_state'],'READY')
        self.assertNotEqual(*approved);await expect(self.page.get_by_role('button',name='Cerrar Decision Case',exact=True)).to_be_enabled();await self.capture(path=str(OUT/'studio-closure-ready-1536.png'),full_page=True,animations='disabled');await self.page.get_by_role('button',name='Cerrar Decision Case',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Cerrar Decision Case',exact=True).click();await self.page.wait_for_url('**/app/decisions?**');state=await self.api('GET','/api/platform/logistics-cases/'+cid+'/journey');self.assertIsNotNone(state['lifecycle']['closed_at'])
