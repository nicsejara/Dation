"""W10: actual app/API/SQL/worker. Only explicit fault cases intercept APIs."""
import asyncio,csv,io,json,os,select,subprocess,unittest
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import test_ultimate_case_setup as t3

ROOT=Path(__file__).resolve().parents[2];REPO=ROOT.parent
OUT=Path(os.getenv('DATION_T10_BROWSER_ARTIFACTS','/tmp/dation-t10-browser'))

class UltimateResultConsumerTests(unittest.IsolatedAsyncioTestCase):
    login=t3.UltimateCaseSetupTests.login
    request=t3.UltimateCaseSetupTests.request
    api=t3.UltimateCaseSetupTests.api
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True,exist_ok=True);cls.fixture_log=(OUT/'fixture.log').open('w')
        env=os.environ.copy()
        for key in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:env[key]=''
        for key in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(key,None)
        env.update(PYTHONDONTWRITEBYTECODE='1',DOCKER_HOST='unix:///var/run/docker.sock',PYTHONPATH=str(ROOT))
        cls.fixture=subprocess.Popen([t3.RUNTIME_PYTHON,'-B',str(ROOT/'tests/e2e/ultimate_consumer_fixture.py')],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=cls.fixture_log,text=True)
        if not select.select([cls.fixture.stdout],[],[],60)[0]:cls.fixture.terminate();cls.fixture.wait(10);raise RuntimeError('Owned T10 fixture timeout')
        line=cls.fixture.stdout.readline()
        if not line:raise RuntimeError('Owned T10 fixture failed: '+(OUT/'fixture.log').read_text()[-4000:])
        cls.f=json.loads(line);cls.base=cls.f['api_url'];(OUT/'fixture-runs.json').write_text(json.dumps({k:cls.f[k] for k in ['case_id','d1','d2']},indent=2))
        (OUT/'owned-fixture.json').write_text(json.dumps({k:cls.f[k] for k in ['api_url','baseline_url','control_dir','pg_container','database']},indent=2))
    tearDownClass=classmethod(t3.UltimateCaseSetupTests.tearDownClass.__func__)
    async def asyncSetUp(self):
        self.pw=await async_playwright().start();self.browser=await self.pw.chromium.launch(executable_path=t3.CHROMIUM_EXECUTABLE,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        self.context=await self.browser.new_context(viewport={'width':1440,'height':900},reduced_motion='reduce');await self.login(self.context)
        self.page=await self.context.new_page();self.page.set_default_timeout(15000);self.errors=[];self.requests=[]
        self.page.on('pageerror',lambda e:self.errors.append(str(e)));self.page.on('request',lambda r:self.requests.append(urlparse(r.url).path))
    async def asyncTearDown(self):
        try:
            if not self.page.is_closed():await self.page.screenshot(path=str(OUT/(self._testMethodName+'.png')),full_page=True,animations='disabled')
        finally:
            (OUT/(self._testMethodName+'-requests.json')).write_text(json.dumps(self.requests,indent=2));await self.browser.close();await self.pw.stop()
        self.assertEqual(self.errors,[])
    async def open(self,key='d1'):
        run=self.f[key];node='logistics_assignment' if key=='d1' else 'logistics_scheduling'
        await self.page.goto(self.base+'/app?view=decision-dashboard&case_id='+self.f['case_id']+'&node_id='+node+'&run_id='+run['id'],wait_until='domcontentloaded')
        await self.page.locator('.ultimate-results[data-run-id="'+run['id']+'"] [data-chart] svg').wait_for(timeout=30000)
        media=await self.page.locator('.d-dashboard-hero img').evaluate_all("async images=>{await Promise.all(images.map(img=>img.decode()));return images.map(img=>({src:img.src,width:img.naturalWidth,height:img.naturalHeight,hidden:img.hidden}));}")
        self.assertTrue(media)
        for image in media:self.assertGreater(image['width'],0,image);self.assertFalse(image['hidden'],image)
        return run
    async def test_01_actual_dashboard_details_exports_ia_review_same_run_and_lazy(self):
        matrix=[]
        for key in ['d1','d2']:
            self.requests.clear();run=await self.open(key);rid=run['id'];fp=run['result_fingerprint'];root=self.page.locator('.ultimate-results')
            self.assertEqual(await root.locator('[data-executive-kpi]').count(),5);self.assertEqual(await root.get_attribute('data-result-fingerprint'),fp)
            self.assertFalse(await root.locator('[data-details]').evaluate('e=>e.open'))
            self.assertFalse(any('/api/runs/'+rid+'/'+part in path for path in self.requests for part in ['details/','entities/','decision-context','copilot','artifacts/','approval-review']))
            await root.locator('[data-details]>summary').click();await root.locator('[data-table] table').wait_for()
            for name in (['demand','resources','alternatives','exceptions','evidence'] if key=='d1' else ['trips','resources','service','exceptions','evidence']):
                await root.locator('[data-tab="'+name+'"]').click();await self.page.wait_for_function("name=>{const p=document.querySelector('[data-detail-panel]');return p?.getAttribute('aria-labelledby')==='tab-'+name&&!p.innerText.includes('Cargando datos publicados')}",arg=name)
                self.assertEqual(await root.locator('[data-detail-panel] [role=alert]').count(),0)
            await root.locator('[data-details]>summary').click()
            trip=root.locator('svg [data-entity-type=TRIP]').first;trip_id=await trip.get_attribute('data-entity-id');await trip.click()
            drawer=root.locator('[data-entity-drawer]');await drawer.locator('[data-entity-ai]:not([disabled])').wait_for();self.assertIn(trip_id,await drawer.inner_text())
            self.assertIn(self.f['d1']['result_fingerprint'],await drawer.text_content());await self.page.keyboard.press('Escape');self.assertFalse(await drawer.is_visible());self.assertEqual(await self.page.evaluate('document.activeElement.dataset.entityId'),trip_id)
            await root.locator('[data-chat]').click();await root.get_by_label('Pregunta',exact=True).fill('Explicá los hechos para revisar esta decisión')
            async with self.page.expect_response(lambda r:'/copilot?' in r.url) as pending:await root.locator('[data-assistant] [type=submit]').click()
            answer=await (await pending.value).json();self.assertEqual(answer['provenance'],{'run_id':rid,'result_fingerprint':fp})
            await self.page.wait_for_function("()=>document.querySelector('[data-ai-answer]')?.textContent.includes('Hechos publicados')")
            self.assertIn('Decisión aprobada.' if key=='d1' else 'Recomendación actual.',await root.locator('[data-ai-answer]').inner_text());await self.page.keyboard.press('Escape')
            async with self.page.expect_response(lambda r:'/approval-review?' in r.url) as pending:await root.locator('[data-check-review]').click()
            authority=await (await pending.value).json();await self.page.wait_for_function("()=>document.querySelector('[data-review-feedback]')?.textContent.includes('Integridad verificada')")
            self.assertEqual(await root.locator('[data-approve-package]').is_enabled(),authority['approval_overlay']['approval_allowed'])
            downloads={}
            for format in ['csv','json']:
                await root.locator('[data-export-menu]>summary').click()
                async with self.page.expect_download() as pending:await root.locator('[data-export-'+format+']').click()
                download=await pending.value;path=await download.path();body=Path(path).read_bytes();downloads[format]=body
            full=json.loads(downloads['json']);self.assertTrue(full['complete']);self.assertEqual(full['provenance'],answer['provenance']);self.assertEqual(full['package'],run['result_json'])
            self.assertTrue(list(csv.DictReader(io.StringIO(downloads['csv'].decode('utf-8-sig')))))
            matrix.append({'run_id':rid,'result_fingerprint':fp,'surfaces':['visible dashboard','all six details tabs','CSV UI download','complete JSON UI download','IA response','review UI'],'status':'PASS'})
        (OUT/'browser-consistency.json').write_text(json.dumps(matrix,indent=2))
    async def test_02_five_viewports_preserve_shell_tokens_and_controlled_overflow(self):
        measurements=[]
        first=True
        for key in ['d1','d2']:
            for label,size in [('desktop',(1440,900)),('laptop',(1024,768)),('tablet',(768,1024)),('phone',(375,812)),('small',(320,640))]:
                if not first:
                    await self.page.close();self.page=await self.context.new_page();self.page.set_default_timeout(15000)
                    self.page.on('pageerror',lambda e:self.errors.append(str(e)));self.page.on('request',lambda r:self.requests.append(urlparse(r.url).path))
                first=False
                await self.page.set_viewport_size(dict(zip(['width','height'],size)))
                if self.f.get('baseline_url'):
                    run=self.f[key];node='logistics_assignment' if key=='d1' else 'logistics_scheduling'
                    await self.page.goto(self.f['baseline_url']+'/app?view=decision-dashboard&case_id='+self.f['case_id']+'&node_id='+node+'&run_id='+run['id'],wait_until='domcontentloaded')
                    await self.page.locator('[data-graph-historical-run="'+run['id']+'"]').wait_for(timeout=30000);await self.page.evaluate('document.fonts.ready')
                    await self.page.evaluate('scrollTo(0,0)')
                    await self.page.screenshot(path=str(OUT/(key+'-'+label+'-before-t10.png')),full_page=True,animations='disabled')
                run=await self.open(key);await self.page.evaluate('document.fonts.ready')
                await self.page.evaluate('scrollTo(0,0)')
                measured=await self.page.evaluate("""()=>{const hero=getComputedStyle(document.querySelector('.d-dashboard-hero')),card=getComputedStyle(document.querySelector('[data-executive-kpi]')),body=getComputedStyle(document.body);return {viewport:innerWidth,width:document.body.scrollWidth,font:hero.fontFamily,radius:hero.borderRadius,border:hero.borderColor,background:hero.backgroundColor,padding:hero.padding,cardRadius:card.borderRadius,color:body.color,surface:body.backgroundColor}}""")
                self.assertLessEqual(measured['width'],size[0]+1,measured);measurements.append({'kind':key,'size':size,**measured})
                blocked=await self.page.evaluate("""()=>{const fab=document.querySelector('[data-chat]').getBoundingClientRect();return [...document.querySelectorAll('[data-dashboard-toolbar] .dashboard-toolbar__tools > .d-button,[data-dashboard-toolbar] .dashboard-toolbar__tools > details > summary')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.height&&r.top<innerHeight&&r.bottom>0&&r.right>fab.left&&r.left<fab.right&&r.bottom>fab.top&&r.top<fab.bottom;}).map(e=>e.textContent);}""")
                self.assertEqual(blocked,[])
                await self.page.screenshot(path=str(OUT/(key+'-'+label+'.png')),full_page=True,animations='disabled')
                await self.page.locator('[data-details]>summary').click();await self.page.locator('[data-table] table').wait_for();self.assertLessEqual(await self.page.evaluate('document.body.scrollWidth'),size[0]+1)
        (OUT/'measurements.json').write_text(json.dumps(measurements,indent=2))
    async def test_03_keyboard_chart_alternative_tabs_drawer_and_assistant_return_focus(self):
        await self.open();root=self.page.locator('.ultimate-results');summary=root.locator('[data-chart] details>summary');await summary.focus();await self.page.keyboard.press('Enter')
        trip=root.locator('[data-chart] li [data-entity-type=TRIP]').first;await trip.focus();await self.page.keyboard.press('Enter');await root.locator('[data-entity-ai]:not([disabled])').wait_for()
        await self.page.keyboard.press('Shift+Tab');self.assertTrue(await root.locator('[data-entity-drawer]').evaluate('e=>e.contains(document.activeElement)'))
        await self.page.keyboard.press('Escape');self.assertTrue(await trip.evaluate('e=>e===document.activeElement'))
        summary=root.locator('[data-details]>summary');await summary.focus();await self.page.keyboard.press('Enter');await root.locator('[data-tab=plan]').focus();await self.page.keyboard.press('ArrowRight');self.assertEqual(await root.locator('[role=tab][aria-selected=true]').get_attribute('data-tab'),'demand')
        await root.locator('[data-chat]').click();await root.locator('[data-assistant] [type=submit]').focus();await self.page.keyboard.press('Tab')
        self.assertTrue(await root.locator('[data-assistant] summary').first.evaluate('e=>e===document.activeElement'))
        await self.page.keyboard.press('Escape');self.assertTrue(await root.locator('[data-chat]').evaluate('e=>e===document.activeElement'))
    async def test_04_unknown_schema_and_recovery_are_safe(self):
        rid=self.f['d1']['id']
        async def unknown(route):
            response=await route.fetch();body=await response.json();body['result_json']['result_schema']='unknown_future_schema';await route.fulfill(response=response,json=body)
        await self.page.route('**/api/runs/'+rid,unknown)
        await self.page.goto(self.base+'/app?view=decision-dashboard&case_id='+self.f['case_id']+'&node_id=logistics_assignment&run_id='+rid)
        await self.page.locator('.d-recovery').wait_for();self.assertIn('UNSUPPORTED_RESULT_SCHEMA',await self.page.locator('.d-recovery').text_content());self.assertEqual(await self.page.locator('.assignment-dashboard-v2 svg').count(),0)
        await self.page.unroute('**/api/runs/'+rid,unknown)
        await self.open()
        async def failure(route):await route.fulfill(status=503,json={'detail':'Fallo temporal sintético'})
        await self.page.route('**/api/runs/'+rid+'/details/plan?*',failure);await self.page.locator('[data-details]>summary').click();await self.page.get_by_role('button',name='Reintentar',exact=True).wait_for()
        await self.page.unroute('**/api/runs/'+rid+'/details/plan?*',failure);await self.page.get_by_role('button',name='Reintentar',exact=True).click();await self.page.locator('[data-table] table').wait_for()
    async def test_05_late_entity_after_run_change_never_opens_wrong_drawer(self):
        await self.open();rid=self.f['d1']['id'];gate=asyncio.Event();started=asyncio.Event()
        async def delayed(route):
            response=await route.fetch();started.set();await gate.wait()
            try:await route.fulfill(response=response)
            except Exception:pass # navigation deliberately canceled this document
        await self.page.route('**/api/runs/'+rid+'/entities/TRIP/*',delayed)
        await self.page.locator('svg [data-entity-type=TRIP]').first.click();await asyncio.wait_for(started.wait(),5)
        navigating=asyncio.create_task(self.page.evaluate("args=>window.DationDispatch.openDashboard(args.caseId,'logistics_scheduling',args.runId)",{'caseId':self.f['case_id'],'runId':self.f['d2']['id']}))
        await asyncio.sleep(.15);gate.set();await navigating
        await self.page.locator('.ultimate-results[data-run-id="'+self.f['d2']['id']+'"]').wait_for();await self.page.wait_for_timeout(150)
        self.assertFalse(await self.page.locator('[data-entity-drawer]').is_visible());self.assertEqual(await self.page.locator('.ultimate-results').get_attribute('data-run-id'),self.f['d2']['id'])
    async def test_06_zoom_reduced_motion_focus_and_long_fields(self):
        await self.page.set_viewport_size({'width':768,'height':1024});await self.open();await self.page.evaluate("document.documentElement.style.zoom='2'")
        self.assertLessEqual(await self.page.evaluate('document.body.scrollWidth'),769)
        await self.page.locator('[data-details]>summary').click();await self.page.locator('[data-table] table').wait_for();self.assertLessEqual(await self.page.evaluate('document.body.scrollWidth'),769)
        await self.page.locator('[data-search]').fill('NO_MATCH');await self.page.get_by_text('Sin filas para esta selección.',exact=True).wait_for()
        await self.page.locator('[data-search]').fill('');await self.page.locator('[data-tab=exceptions]').click();await self.page.get_by_text('Sin filas para esta selección.',exact=True).wait_for()
        focus=self.page.locator('[data-tab=exceptions]');await self.page.keyboard.press('Tab');await focus.focus();style=await focus.evaluate('e=>({style:getComputedStyle(e).outlineStyle,width:getComputedStyle(e).outlineWidth})');self.assertNotEqual(style['style'],'none');self.assertNotEqual(style['width'],'0px')
        self.assertTrue(await self.page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"))
    async def test_07_contrast_focus_visibility_and_native_tokens(self):
        await self.open();measurements=await self.page.evaluate("""()=>{
          const rgb=s=>{const p=s.match(/[\\d.]+/g)?.map(Number)||[0,0,0,0];return [p[0],p[1],p[2],p[3]??1]};
          const over=(a,b)=>[...a.slice(0,3).map((v,i)=>v*a[3]+b[i]*(1-a[3])),1];
          const background=e=>{const ancestors=[];for(let p=e;p;p=p.parentElement)ancestors.unshift(p);return ancestors.reduce((b,p)=>over(rgb(getComputedStyle(p).backgroundColor),b),[0,0,0,1]);};
          const lum=c=>c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
          const ratio=(a,b)=>(Math.max(lum(a),lum(b))+.05)/(Math.min(lum(a),lum(b))+.05);
          const measure=e=>{const s=getComputedStyle(e),bg=background(e),graphic=e.matches('path,rect'),paint=graphic?(e.matches('path,.is-external')?s.stroke:s.fill):e instanceof SVGElement?s.fill:s.color,color=rgb(paint);color[3]*=Number(s.opacity);const fg=over(color,bg),large=parseFloat(s.fontSize)>=24||(parseFloat(s.fontSize)>=18.66&&Number(s.fontWeight)>=700);return {tag:e.tagName,text:e.textContent.slice(0,64),foreground:fg,background:bg,ratio:ratio(fg,bg),required:graphic?3:large?3:4.5};};const result=[...document.querySelectorAll('.ultimate-results h1,.ultimate-results h2,.ultimate-results [data-executive-kpi] span,.ultimate-results [data-executive-kpi]>p,.ultimate-results [data-executive-kpi]>strong,.ultimate-results [data-review] button:not([disabled]),.ultimate-results svg text,.ultimate-results svg path,.ultimate-results svg rect')].map(measure);for(const edge of document.querySelectorAll('.ultimate-results svg path')){edge.classList.add('is-muted');result.push({...measure(edge),state:'deemphasized'});edge.classList.remove('is-muted');}return result;
        }""")
        self.assertTrue(measurements)
        for row in measurements:self.assertGreaterEqual(row['ratio']+.01,row['required'],row)
        await self.page.set_viewport_size({'width':375,'height':812});await self.page.keyboard.press('Tab');button=self.page.locator('[data-check-review]');await button.focus();await self.page.wait_for_timeout(50)
        focus=await button.evaluate("""e=>{const r=e.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2),s=getComputedStyle(e);return {top:r.top,bottom:r.bottom,viewport:innerHeight,obscured:!(hit===e||e.contains(hit)),outline:s.outlineStyle,color:s.outlineColor,width:s.outlineWidth,background:getComputedStyle(e.closest('[data-review]')).backgroundColor}}""")
        self.assertGreaterEqual(focus['top'],0);self.assertLessEqual(focus['bottom'],focus['viewport']);self.assertFalse(focus['obscured']);self.assertNotEqual(focus['outline'],'none')
        (OUT/'contrast-focus.json').write_text(json.dumps({'text':measurements,'focus':focus},indent=2))
    async def test_08_saved_conversation_is_lazy_and_keeps_original_context(self):
        await self.open();await self.page.locator('[data-chat]').click();await self.page.get_by_label('Pregunta',exact=True).fill('Consulta propia de historial')
        async with self.page.expect_response(lambda r:'/copilot?' in r.url):await self.page.locator('[data-assistant] [type=submit]').click()
        await self.page.wait_for_function("()=>document.querySelector('[data-ai-answer]')?.textContent.includes('Hechos publicados')");await self.page.keyboard.press('Escape')
        self.requests.clear();await self.page.locator('[data-chat]').click();summary=self.page.locator('[data-assistant]').get_by_text('Conversaciones guardadas de esta corrida',exact=True)
        self.assertFalse(any('/copilot-history' in p for p in self.requests));await summary.click()
        await self.page.locator('[data-copilot-history] h3').first.wait_for();self.assertNotIn('/copilot', '\n'.join(p for p in self.requests if p.endswith('/copilot')))
        self.assertIn('Consulta propia de historial',await self.page.locator('[data-copilot-history]').inner_text())
    async def test_09_waits_for_atomic_publication_without_prefetching_details(self):
        from uuid import uuid4
        rid=str(uuid4());marker=Path(self.f['control_dir'])/'block-t8-finish';marker.touch()
        try:
            config=await self.api('GET','/api/platform/logistics-cases/'+self.f['case_id']+'/run-context');body={k:config[k] for k in ['expected_context_hash','model_version_id','data_pack_version_id','node_policy']}
            body.update(request_schema='ultimate_run_request_v1',workflow_version=2,case_id=self.f['case_id'],node_id='logistics_assignment')
            await self.api('POST','/api/runs?run_id='+rid,body)
            await self.page.goto(self.base+'/app?view=decision-dashboard&case_id='+self.f['case_id']+'&node_id=logistics_assignment&run_id='+rid,wait_until='domcontentloaded')
            await self.page.locator('[data-result-pending]').wait_for();self.assertFalse(any('/api/runs/'+rid+'/details/' in p for p in self.requests))
            marker.unlink();await self.page.locator('.ultimate-results[data-run-id="'+rid+'"] [data-chart] svg').wait_for(timeout=20000)
        finally:marker.unlink(missing_ok=True)
    async def test_10_copilot_keeps_mode_and_question_bound_while_waiting(self):
        await self.open();gate=asyncio.Event();started=asyncio.Event()
        async def delayed(route):
            response=await route.fetch();started.set();await gate.wait();await route.fulfill(response=response)
        await self.page.route('**/api/runs/'+self.f['d1']['id']+'/copilot?*',delayed)
        await self.page.locator('[data-chat]').click();form=self.page.locator('[data-assistant] form');await form.get_by_label('Pregunta',exact=True).fill('Explicá esta recomendación')
        await form.locator('[type=submit]').click()
        try:
            await asyncio.wait_for(started.wait(),5);self.assertTrue(await form.locator('[name=mode]').is_disabled());self.assertTrue(await form.locator('[name=question]').is_disabled())
        finally:gate.set()
        await self.page.wait_for_function("()=>document.querySelector('[data-ai-answer]')?.textContent.includes('Hechos publicados')");self.assertFalse(await form.locator('[name=mode]').is_disabled())
        await form.locator('[name=mode]').select_option('REVIEW');self.assertEqual(await self.page.locator('[data-ai-answer]').inner_text(),'')

if __name__=='__main__':unittest.main()
