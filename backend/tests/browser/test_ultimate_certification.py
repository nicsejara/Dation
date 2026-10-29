"""T11 real zero-kilometer UI journey plus the required five-size surface matrix."""
import asyncio
import json
import os
from pathlib import Path
import select
import subprocess
import unittest
from urllib.parse import urlparse,parse_qs

from playwright.async_api import async_playwright,expect
import test_ultimate_case_setup as setup
import test_ultimate_case_data as data

BACKEND=Path(__file__).resolve().parents[2];REPO=BACKEND.parent
OUT=Path(os.getenv('DATION_T11_BROWSER_ARTIFACTS','/tmp/dation-t11-browser'))
SIZES=[('desktop',1440,900),('laptop',1024,768),('tablet',768,1024),('phone',375,812),('small',320,640)]


class UltimateCertificationTests(unittest.IsolatedAsyncioTestCase):
    login=setup.UltimateCaseSetupTests.login
    request=setup.UltimateCaseSetupTests.request
    api=setup.UltimateCaseSetupTests.api
    template=data.UltimateCaseDataTests.template
    attach=data.UltimateCaseDataTests.attach
    store_ui=data.UltimateCaseDataTests.store_ui
    publish_ui=data.UltimateCaseDataTests.publish_ui
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True,exist_ok=True);cls.fixture_log=(OUT/'fixture.log').open('w')
        env=os.environ.copy()
        for name in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:env[name]=''
        for name in ['DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(name,None)
        env.update(DOCKER_HOST='unix:///var/run/docker.sock',PYTHONDONTWRITEBYTECODE='1')
        cls.fixture=subprocess.Popen([setup.RUNTIME_PYTHON,'-B',str(BACKEND/'tests/e2e/ultimate_certification_fixture.py')],
            cwd=BACKEND,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=cls.fixture_log,text=True)
        if not select.select([cls.fixture.stdout],[],[],60)[0]:raise RuntimeError('T11 owned browser fixture timeout')
        line=cls.fixture.stdout.readline()
        if not line:raise RuntimeError((OUT/'fixture.log').read_text()[-4000:])
        cls.f=json.loads(line);cls.base=cls.f['api_url'];(OUT/'owned-fixture.json').write_text(json.dumps(cls.f,indent=2)+'\n')
    tearDownClass=classmethod(setup.UltimateCaseSetupTests.tearDownClass.__func__)
    async def asyncSetUp(self):
        self.pw=await async_playwright().start();self.browser=await self.pw.chromium.launch(executable_path=setup.CHROMIUM_EXECUTABLE,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        self.context=await self.browser.new_context(viewport={'width':1440,'height':900},reduced_motion='reduce')
        await self.login(self.context);self.page=await self.context.new_page();self.page.set_default_timeout(20000)
        self.errors=[];self.requests=[];self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.page.on('request',lambda r:self.requests.append({'method':r.method,'path':urlparse(r.url).path}))
    async def asyncTearDown(self):
        try:await self.page.screenshot(path=str(OUT/(self._testMethodName+'.png')),full_page=True,animations='disabled')
        finally:
            (OUT/(self._testMethodName+'-requests.json')).write_text(json.dumps(self.requests,indent=2)+'\n')
            await self.browser.close();await self.pw.stop()
        self.assertEqual(self.errors,[])
    async def go(self,path,selector):
        await self.page.goto(self.base+path,wait_until='domcontentloaded')
        await self.page.locator(selector).wait_for(timeout=35000)
        await self.page.evaluate('document.fonts.ready')
    async def approve_current(self,rid):
        root=self.page.locator('.ultimate-results')
        await root.locator('[data-details]>summary').click();await root.locator('[data-table] table').wait_for()
        await root.locator('[data-details]>summary').click()
        await root.locator('[data-chat]').click();await root.get_by_label('Pregunta',exact=True).fill('¿Qué hechos publicados debo revisar antes de aprobar?')
        async with self.page.expect_response(lambda r:'/copilot?' in r.url and r.request.method=='POST') as pending:
            await root.locator('[data-assistant] [type=submit]').click()
        answer=await (await pending.value).json();self.assertEqual(answer['provenance']['run_id'],rid)
        await self.page.keyboard.press('Escape');await root.locator('[data-check-review]').click()
        await expect(root.locator('[data-approve-package]')).to_be_enabled(timeout=30000)
        async with self.page.expect_response(lambda r:'/api/runs/'+rid+'/approve' in r.url and r.request.method=='POST') as pending:
            await root.locator('[data-approve-package]').click()
        response=await pending.value;self.assertEqual(response.status,200,await response.text())

    async def test_01_empty_business_login_model_pack_execute_and_approve_d1_d2(self):
        self.assertFalse(any(self.f['business_counts'].values()))
        await self.go('/app/ddas/logistics/models?model_id=new','[data-ultimate-ready=true]')
        await self.page.get_by_label('Nombre del Model',exact=True).fill('T11 · Primera operación')
        await self.page.get_by_role('button',name='Crear Model',exact=True).click()
        await self.page.get_by_role('button',name='Publicar nueva versión',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Publicar versión',exact=True).click()
        await self.page.get_by_text('Versión 1',exact=True).wait_for()
        await self.page.get_by_role('button',name='Crear Case con este Model',exact=True).click()
        await self.page.locator('.ultimate-foundation[data-ultimate-ready=true] input[name=case_name]').wait_for()
        await self.page.get_by_label('Nombre del Case',exact=True).fill('T11 · Semana desde cero')
        version=self.page.get_by_label('Model Version',exact=True);await version.locator('option').first.wait_for(state='attached');await version.select_option(index=0)
        await self.page.get_by_label('Inicio de planificación',exact=True).fill('2026-11-02');await self.page.get_by_label('Inicio de planificación',exact=True).press('Tab')
        await self.page.get_by_label('Fin de planificación',exact=True).fill('2026-11-08')
        await self.page.get_by_label('Decision Owner inicial (D1 y D2)',exact=True).select_option(setup.ADMIN)
        await self.page.get_by_role('button',name='Crear Decision Case',exact=True).click();await self.page.locator('[data-graph-ready=true]').wait_for()
        cid=parse_qs(urlparse(self.page.url).query)['case_id'][0]
        await expect(self.page.locator('[data-graph-node=logistics_assignment]')).to_have_attribute('data-node-state','DATA_REQUIRED')
        await self.page.get_by_role('button',name='Seleccionar responsable',exact=True).click()
        await self.page.get_by_label('Data Owner',exact=True).select_option(setup.ADMIN)
        await self.page.get_by_role('button',name='Guardar',exact=True).click()
        await self.page.get_by_role('button',name='Completar datos del Case',exact=False).click()
        await self.page.locator('[data-ultimate-ready=true]').wait_for()
        for entity,number in [('transport_demand','2'),('transport_resources','3')]:
            await self.store_ui(cid,entity);await self.publish_ui();await self.page.locator('[data-pack-current-version="'+number+'"]').wait_for()
        await self.page.get_by_role('button',name='Volver al Decision Map',exact=True).click();await self.page.locator('[data-graph-ready=true]').wait_for()
        runs=[]
        for node,label in [('logistics_assignment','Transport Plan'),('logistics_scheduling','Day Scheduling')]:
            await expect(self.page.locator('[data-graph-node="'+node+'"]')).to_have_attribute('data-node-state','READY')
            await self.page.get_by_role('button',name='Configurar '+label,exact=False).click()
            await self.page.locator('[data-graph-config="'+node+'"]').wait_for()
            trigger=self.page.get_by_role('button',name='Ejecutar decisión',exact=True);await expect(trigger).to_be_enabled()
            self.requests.clear()
            if not runs:
                async def lose_admission_response(route):
                    response=await route.fetch()
                    self.assertEqual(response.status,202)
                    await route.abort('failed')
                await self.page.route('**/api/runs?run_id=*',lose_admission_response,times=1)
            async with self.page.expect_request(lambda r:urlparse(r.url).path=='/api/runs' and r.method=='POST') as pending:
                await trigger.focus();await self.page.keyboard.press('Enter')
            request=await pending.value;body=request.post_data_json
            if not runs:
                await self.page.locator('[data-graph-config] [role=alert]').wait_for()
                await expect(trigger).to_be_enabled()
                await expect(trigger).to_be_focused()
                async with self.page.expect_request(lambda r:urlparse(r.url).path=='/api/runs' and r.method=='POST') as repeated:
                    await self.page.keyboard.press('Enter')
                retry=await repeated.value
                self.assertEqual(retry.url,request.url);self.assertEqual(retry.post_data_json,body)
            self.assertEqual(body['node_id'],node);self.assertEqual(body['case_id'],cid)
            if runs:self.assertEqual(body['source_transport_plan'],{'run_id':runs[0]['id'],'result_fingerprint':runs[0]['result_fingerprint']})
            await self.page.locator('.ultimate-results [data-chart] svg').wait_for(timeout=60000)
            rid=await self.page.locator('.ultimate-results').get_attribute('data-run-id')
            self.assertFalse(any('/api/runs/'+rid+'/'+part in r['path'] for r in self.requests for part in ['details/','entities/','copilot','decision-context']))
            await self.approve_current(rid)
            run=await self.api('GET','/api/runs/'+rid);self.assertTrue(run['approved_at']);runs.append(run)
            history=await self.api('GET','/api/platform/logistics-cases/'+cid+'/graph/history/'+node)
            self.assertEqual(history['total'],1)
            await self.go('/app/ddas/logistics/decisions?case_id='+cid,'[data-graph-ready=true]')
        self.assertEqual([await n.get_attribute('data-node-state') for n in await self.page.locator('[data-graph-node]').all()],['APPROVED','APPROVED'])
        type(self).f.update(case_id=cid,d1=runs[0],d2=runs[1])
        (OUT/'first-user-ui-journey.json').write_text(json.dumps({'case_id':cid,'runs':runs,'initial_business_counts':self.f['business_counts'],
            'model_case_uploads_executions_ia_reviews_approvals':'real UI + API/SQL/worker','business_SQL_interventions':0},indent=2)+'\n')

    async def test_02_required_surface_responsive_accessibility_matrix(self):
        # The preceding single journey deliberately supplies this scenario's
        # exact approved chain; running this test alone must fail, never seed it.
        self.assertIn('case_id',self.f,'Run the complete T11 browser scenario, not only its second step')
        cid=self.f['case_id'];records=[]
        baseline_page=await self.context.new_page() if self.f.get('baseline_url') else None
        if baseline_page:
            baseline=self.f['baseline_url']
            response=await self.context.request.post(baseline+'/auth/login',headers={'Origin':baseline},data={'email':'user-1@example.test','password':'dispatch-e2e-private'})
            self.assertEqual(response.status,200)
        surfaces=[('case-setup','/app/ddas/logistics/case?case_id='+cid,'[data-ultimate-ready=true]'),
            ('decision-map','/app/ddas/logistics/decisions?case_id='+cid,'[data-graph-ready=true]'),
            ('case-data','/app/ddas/logistics/case/data?case_id='+cid,'[data-ultimate-ready=true]')]
        for key,node in [('d1','logistics_assignment'),('d2','logistics_scheduling')]:
            surfaces.append(('config-'+key,'/app?view=logistics-config&case_id='+cid+'&node_id='+node,'[data-graph-config="'+node+'"]'))
        for size,width,height in SIZES:
            # Release rendered charts/screenshots between independent viewport
            # samples while preserving the authenticated fixture context.
            await self.page.close();self.page=await self.context.new_page()
            self.page.set_default_timeout(20000)
            self.page.on('pageerror',lambda e:self.errors.append(str(e)))
            self.page.on('request',lambda r:self.requests.append({'method':r.method,'path':urlparse(r.url).path}))
            await self.page.set_viewport_size({'width':width,'height':height})
            for name,path,selector in surfaces:
                await self.go(path,selector);await self.capture(records,name,size,width,height)
                if baseline_page and name.startswith('config-'):
                    await baseline_page.set_viewport_size({'width':width,'height':height})
                    await baseline_page.goto(self.f['baseline_url']+path,wait_until='domcontentloaded')
                    await baseline_page.locator(selector).wait_for();await baseline_page.evaluate('document.fonts.ready')
                    await baseline_page.mouse.move(0,0)
                    self.assertTrue(await baseline_page.get_by_role('button',name='Ejecutar decisión',exact=True).is_disabled())
                    self.assertFalse(await self.page.get_by_role('button',name='Ejecutar decisión',exact=True).is_disabled())
                    await baseline_page.screenshot(path=str(OUT/(name+'-'+size+'-post-t10-before.png')),full_page=True,animations='disabled')
            for key,node in [('d1','logistics_assignment'),('d2','logistics_scheduling')]:
                run=self.f[key]
                await self.go('/app?view=decision-dashboard&case_id='+cid+'&node_id='+node+'&run_id='+run['id'],'.ultimate-results [data-chart] svg')
                await self.page.locator('.d-dashboard-hero img').evaluate_all('async imgs=>Promise.all(imgs.map(i=>i.decode()))')
                await self.capture(records,'dashboard-'+key,size,width,height)
                # Values shown in the DOM, not only an attached fingerprint.
                metrics=run['result_json']['metrics']
                field='trip_count' if key=='d1' else 'scheduled_trips'
                expected=str(metrics['trip_count'] if key=='d1' else metrics['scheduled_trips']['scheduled'])
                self.assertEqual(await self.page.locator('[data-executive-kpi="'+field+'"] strong').inner_text(),expected)
                self.assertEqual(await self.page.locator('.ultimate-results').get_attribute('data-result-fingerprint'),run['result_fingerprint'])
                await self.page.locator('[data-details]>summary').click();await self.page.locator('[data-table] table').wait_for()
                await self.capture(records,'detailed-analysis-'+key,size,width,height)
                await self.page.locator('[data-details]>summary').click();await self.page.locator('[data-chat]').click()
                await self.page.get_by_label('Pregunta',exact=True).wait_for();await self.capture(records,'dation-ia-'+key,size,width,height)
                await self.page.keyboard.press('Escape');await self.page.locator('[data-review]').scroll_into_view_if_needed()
                await self.capture(records,'approval-review-'+key,size,width,height)
        (OUT/'responsive-matrix.json').write_text(json.dumps(records,indent=2)+'\n')
        if baseline_page:await baseline_page.close()

    async def capture(self,records,surface,size,width,height):
        actual=await self.page.evaluate('document.body.scrollWidth')
        self.assertLessEqual(actual,width+1,(surface,size,actual))
        await self.page.mouse.move(0,0)
        await self.page.screenshot(path=str(OUT/(surface+'-'+size+'.png')),full_page=True,animations='disabled')
        records.append({'surface':surface,'viewport':[width,height],'body_width':actual,'result':'PASS','keyboard_and_focus':'full B-BROWSER/W10 and first-user controls'})


if __name__=='__main__':unittest.main()
