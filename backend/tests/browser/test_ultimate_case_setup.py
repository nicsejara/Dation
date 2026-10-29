"""W3: new setup surfaces over actual auth/API and the full isolated SQL catalog."""
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import unittest
from uuid import uuid4

from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[2]
REPO=ROOT.parent
RUNTIME_PYTHON=os.getenv('DATION_RUNTIME_PYTHON') or (str(REPO/'.venv/bin/python') if (REPO/'.venv/bin/python').exists() else shutil.which('python'))
CHROMIUM_EXECUTABLE=os.getenv('CHROMIUM_EXECUTABLE') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None)
ADMIN='10000000-0000-4000-8000-000000000001'
OUT=Path(os.environ.get('DATION_T3_BROWSER_ARTIFACTS','/tmp/dation-t3-browser'))
CONFIG=dict(version=1,operating_role='SHIPPER',transport_pattern='DIRECT',allowed_sources=['OWN','EXTERNAL'],active_dimensions=['pallets'],primary_dimension='pallets',split_permitted=False,homogeneous_loads_declared=False,currency_policy=dict(currency='ARS',minor_units=2,rounding='ROUND_HALF_UP'),own_cost_model='OWN_OPERATING_CYCLE',external_cost_models=['PER_TRIP','PER_KM'],per_km_billing_bases=['ONE_WAY','ROUND_TRIP'])


class UltimateCaseSetupTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True,exist_ok=True)
        cls.fixture_log=(OUT/'fixture.log').open('w')
        env=os.environ.copy()
        for key in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:env[key]=''
        for key in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(key,None)
        env.update(PYTHONDONTWRITEBYTECODE='1',DOCKER_HOST='unix:///var/run/docker.sock')
        cls.fixture=subprocess.Popen([RUNTIME_PYTHON,'-B',str(ROOT/'tests/e2e/ultimate_setup_fixture.py')],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=cls.fixture_log,text=True)
        if not select.select([cls.fixture.stdout],[],[],60)[0]:
            cls.fixture.terminate();cls.fixture.wait(10);raise RuntimeError('Owned W3 API fixture did not become ready')
        line=cls.fixture.stdout.readline()
        if not line:
            cls.fixture.wait(10);raise RuntimeError('Owned W3 fixture failed: '+(OUT/'fixture.log').read_text()[-4000:])
        cls.base=json.loads(line)['api_url']
    @classmethod
    def tearDownClass(cls):
        cls.fixture.stdin.write('stop\n');cls.fixture.stdin.flush();cls.fixture.stdin.close()
        try:cls.fixture.wait(30)
        except subprocess.TimeoutExpired:cls.fixture.terminate();cls.fixture.wait(10)
        cls.fixture.stdout.close();cls.fixture_log.close()
        if cls.fixture.returncode:raise AssertionError('W3 fixture cleanup failed')
    async def asyncSetUp(self):
        self.pw=await async_playwright().start();self.browser=await self.pw.chromium.launch(executable_path=CHROMIUM_EXECUTABLE,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        self.context=await self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        await self.login(self.context)
        self.page=await self.context.new_page();self.page.set_default_timeout(12000)
        self.errors=[];self.page.on('pageerror',lambda error:self.errors.append(str(error)))
    async def asyncTearDown(self):
        if self.errors:(OUT/(self._testMethodName+'-errors.json')).write_text(json.dumps(self.errors,indent=2))
        await self.page.screenshot(path=str(OUT/(self._testMethodName+'.png')),full_page=True,animations='disabled')
        await self.browser.close();await self.pw.stop();self.assertEqual(self.errors,[])
    async def login(self,context,user=1):
        r=await context.request.post(self.base+'/auth/login',headers={'Origin':self.base},data={'email':f'user-{user}@example.test','password':'dispatch-e2e-private'})
        self.assertEqual(r.status,200,await r.text())
    async def request(self,method,path,body=None,context=None):
        context=context or self.context
        # Playwright retries only ECONNRESET here, never HTTP business failures.
        # This fixture-only read/refresh has no Model/Case write side effect.
        session=await context.request.post(self.base+'/auth/session',headers={'Origin':self.base},max_retries=1);self.assertEqual(session.status,200)
        token=(await session.json())['access_token'];response=await context.request.fetch(self.base+path,method=method,headers={'Authorization':'Bearer '+token},data=body)
        return response
    async def api(self,method,path,body=None):
        r=await self.request(method,path,body);self.assertTrue(r.ok,await r.text());return await r.json()
    async def model(self,name=None):
        m=await self.api('POST','/api/platform/logistics-models',{'id':str(uuid4()),'name':name or 'Operación '+str(uuid4())[:8],'configuration':CONFIG})
        v=await self.api('POST','/api/platform/logistics-models/'+m['model']['id']+'/versions',{'version_id':str(uuid4()),'expected_revision':m['model']['revision']})
        return m,v
    async def case(self):
        m,v=await self.model();c=await self.api('POST','/api/platform/logistics-cases',{'id':str(uuid4()),'name':'Case sin CSV','logistics_model_version_id':v['version']['id'],'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','operating_mode':'OPERATIONAL','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':ADMIN})
        return m,v,c
    async def open(self,path):
        await self.page.goto(self.base+path,wait_until='domcontentloaded',timeout=30000)
        await self.page.locator('.ultimate-foundation[data-ultimate-ready="true"]').wait_for(timeout=30000)
    async def test_01_ui_model_publish_case_without_csv_and_reload(self):
        await self.open('/app/ddas/logistics/models?model_id=new')
        await self.page.get_by_label('Nombre del Model',exact=True).fill('W3 · Distribución región sur')
        await self.page.get_by_role('button',name='Crear Model',exact=True).click()
        await self.page.get_by_role('button',name='Publicar nueva versión',exact=True).wait_for()
        trigger=self.page.get_by_role('button',name='Publicar nueva versión',exact=True);await trigger.focus();await self.page.keyboard.press('Enter')
        dialog=self.page.get_by_role('dialog');await dialog.wait_for();self.assertEqual(await self.page.evaluate('document.activeElement.textContent'),'Cancelar')
        await self.page.keyboard.press('Escape');await dialog.wait_for(state='detached');self.assertTrue(await trigger.evaluate('n=>n===document.activeElement'))
        await trigger.click();await dialog.get_by_role('button',name='Publicar versión',exact=True).click()
        await self.page.get_by_text('Versión 1',exact=True).wait_for()
        await self.page.get_by_role('button',name='Crear Case con este Model',exact=True).click()
        await self.page.locator('[data-ultimate-ready="true"] form').wait_for()
        await self.page.get_by_label('Nombre del Case',exact=True).fill('Semana 45 · Operación Buenos Aires')
        version=self.page.get_by_label('Model Version',exact=True);await version.locator('option').first.wait_for(state='attached');await version.select_option(index=0)
        await self.page.get_by_label('Inicio de planificación',exact=True).fill('2026-11-02');await self.page.get_by_label('Inicio de planificación',exact=True).press('Tab')
        await self.page.get_by_label('Fin de planificación',exact=True).fill('2026-11-08')
        await self.page.get_by_label('Decision Owner inicial (D1 y D2)',exact=True).select_option(ADMIN)
        await self.page.get_by_role('button',name='Crear Decision Case',exact=True).click()
        await self.page.locator('[data-graph-ready="true"]').wait_for();await self.page.get_by_role('button',name='Contexto del Case',exact=True).click()
        await self.page.get_by_role('button',name='Guardar contexto',exact=True).wait_for();await self.page.get_by_role('heading',name='Contexto guardado',exact=True).wait_for()
        cid=await self.page.evaluate('new URL(location.href).searchParams.get("case_id")');self.assertTrue(cid)
        self.assertEqual(await self.page.locator('input[type="file"]').count(),0)
        before=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context');self.assertEqual(before['entry_count'],0)
        await self.page.reload();await self.page.locator('[data-ultimate-ready="true"]').wait_for()
        self.assertEqual(await self.page.get_by_label('Nombre del Case',exact=True).input_value(),'Semana 45 · Operación Buenos Aires')
        after=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context');self.assertEqual(before['planning_context_hash'],after['planning_context_hash'])
        (OUT/'durable-context.json').write_text(json.dumps({'case_id':cid,'entry_count':after['entry_count'],'hash_stable':True,'no_csv':True},indent=2))
    async def test_02_validation_dirty_reload_and_cas_preserve_draft(self):
        _,_,c=await self.case();cid=c['case']['id'];await self.open('/app/ddas/logistics/case?case_id='+cid)
        await self.page.get_by_label('Objetivo global',exact=True).select_option('CUSTOM');await self.page.locator('.ultimate-policy summary').click()
        await self.page.get_by_label('Costo (%)',exact=True).fill('10');await self.page.get_by_role('button',name='Guardar contexto',exact=True).click()
        await self.page.get_by_role('link',name='Las preferencias deben sumar 100 %.').wait_for();self.assertTrue(await self.page.locator('.ultimate-errors').evaluate('n=>n===document.activeElement'))
        await self.page.get_by_role('link',name='Las preferencias deben sumar 100 %.').click();self.assertEqual(await self.page.evaluate('document.activeElement.name'),'weight_COST')
        await self.page.get_by_label('Objetivo global',exact=True).select_option('MINIMIZE_COST')
        await self.page.get_by_label('Nombre del Case',exact=True).fill('Mi borrador pendiente')
        self.page.on('dialog',lambda dialog:dialog.accept())
        await self.page.reload();await self.page.locator('[data-ultimate-ready="true"]').wait_for();self.assertEqual(await self.page.get_by_label('Nombre del Case',exact=True).input_value(),'Mi borrador pendiente')
        await self.api('PATCH','/api/platform/logistics-cases/'+cid+'/context',{'expected_updated_at':c['case']['updated_at'],'name':'Cambio concurrente'})
        await self.page.get_by_role('button',name='Guardar contexto',exact=True).click();await self.page.get_by_text('La versión guardada cambió. Tu borrador se conserva; revisá la versión actual antes de reintentar.',exact=True).wait_for()
        self.assertEqual(await self.page.get_by_label('Nombre del Case',exact=True).input_value(),'Mi borrador pendiente')
        await self.page.get_by_role('button',name='Descartar borrador y recargar',exact=True).click();dialog=self.page.get_by_role('dialog');await dialog.wait_for();await self.page.keyboard.press('Escape');await dialog.wait_for(state='detached')
        self.assertEqual(await self.page.get_by_label('Nombre del Case',exact=True).input_value(),'Mi borrador pendiente')
        await self.page.get_by_role('button',name='Descartar borrador y recargar',exact=True).click();await dialog.get_by_role('button',name='Descartar y recargar',exact=True).click()
        await self.page.get_by_label('Nombre del Case',exact=True).wait_for();await self.page.wait_for_function('document.querySelector("[name=case_name]")?.value==="Cambio concurrente"')
    async def test_03_viewer_reads_without_controls_or_write_authority(self):
        _,_,c=await self.case();viewer=await self.browser.new_context(viewport={'width':390,'height':844});await self.login(viewer,3)
        page=await viewer.new_page();await page.goto(self.base+'/app/ddas/logistics/case?case_id='+c['case']['id']);await page.locator('[data-ultimate-ready="true"]').wait_for()
        self.assertTrue(await page.get_by_label('Nombre del Case',exact=True).is_disabled());self.assertTrue(await page.get_by_role('button',name='Guardar contexto',exact=True).is_disabled())
        response=await self.request('PATCH','/api/platform/logistics-cases/'+c['case']['id']+'/context',{'expected_updated_at':c['case']['updated_at'],'name':'Forbidden'},context=viewer);self.assertEqual(response.status,403)
        await viewer.close()
    async def test_04_responsive_stress_zoom_touch_and_native_controls(self):
        long_name='Operación de distribución interregional · '+('área metropolitana y centros de consolidación · '*3)
        m,v=await self.model(long_name[:120]);await self.open('/app/ddas/logistics/case?model_id='+m['model']['id'])
        await self.page.get_by_label('Nombre del Case',exact=True).fill(long_name[:120]);await self.page.get_by_label('Descripción (opcional)',exact=True).fill(('Planificación operativa ñ · '*50)[:1000])
        await self.page.get_by_label('Model Version',exact=True).select_option(v['version']['id'])
        await self.page.get_by_label('Objetivo global',exact=True).select_option('CUSTOM');await self.page.locator('.ultimate-policy summary').click()
        measurements=[]
        for width in [1440,1280,1024,768,390,320]:
            await self.page.set_viewport_size({'width':width,'height':1000});await self.page.evaluate('scrollTo(0,0)');await self.page.screenshot(path=str(OUT/f'case-stress-{width}.png'),full_page=True,animations='disabled')
            data=await self.page.evaluate('''()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,root:document.querySelector('.ultimate-foundation').getBoundingClientRect().toJSON(),controls:[...document.querySelectorAll('.ultimate-foundation input,.ultimate-foundation select,.ultimate-foundation textarea,.ultimate-foundation button')].filter(n=>n.getClientRects().length).map(n=>({name:n.name||n.textContent,height:n.getBoundingClientRect().height,right:n.getBoundingClientRect().right,left:n.getBoundingClientRect().left}))})''')
            self.assertLessEqual(data['scroll'],width+1);self.assertTrue(all(x['right']<=width+1 and x['left']>=0 for x in data['controls']),data);measurements.append(data)
        await self.page.set_viewport_size({'width':1440,'height':1000});await self.page.evaluate('document.documentElement.style.zoom="2"')
        self.assertLessEqual(await self.page.evaluate('document.documentElement.scrollWidth'),1441);await self.page.screenshot(path=str(OUT/'case-zoom200.png'),full_page=True)
        self.assertTrue(await self.page.evaluate('matchMedia("(prefers-reduced-motion:reduce)").matches'))
        await self.page.evaluate('document.documentElement.style.zoom="1"')
        touch=await self.browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True,reduced_motion='reduce');await self.login(touch)
        page=await touch.new_page();await page.goto(self.base+'/app/ddas/logistics/case?case_id='+ (await self.case())[2]['case']['id']);await page.locator('[data-ultimate-ready="true"]').wait_for();await page.get_by_label('Nombre del Case',exact=True).tap();self.assertEqual(await page.evaluate('document.activeElement.name'),'case_name');await touch.close()
        (OUT/'responsive-measurements.json').write_text(json.dumps(measurements,indent=2))
    async def test_05_legacy_navigation_and_home_recover_empty_case(self):
        _,_,c=await self.case();cid=c['case']['id']
        # T5 implements the Map that T3 originally recovered through Setup.
        await self.page.goto(self.base+'/app/ddas/logistics/decisions?case_id='+cid)
        await self.page.locator('[data-graph-ready=true]').wait_for()
        self.assertIn('/app/ddas/logistics/decisions',self.page.url);self.assertIn('case_id='+cid,self.page.url)
        self.assertEqual(await self.page.locator('[data-graph-node=logistics_assignment]').get_attribute('data-node-state'),'DATA_REQUIRED')
        response=await self.request('PUT','/api/platform/decisions/'+cid+'/data-pack',{'expected_updated_at':c['case']['updated_at'],'orders_dataset_id':str(uuid4()),'fleet_dataset_id':str(uuid4())})
        self.assertEqual(response.status,409)
        readiness=await self.request('GET','/api/platform/decisions/'+cid+'/workflow-readiness');self.assertEqual(readiness.status,409)
        home=await self.api('GET','/api/platform/home');(OUT/'home-context-routing.json').write_text(json.dumps({'ultimate_case':cid,'legacy_link_recovers_context':True,'home_keys':list(home)},indent=2))
    async def test_06_keyboard_focus_contrast_and_labels(self):
        m,v=await self.model();await self.open('/app/ddas/logistics/case?model_id='+m['model']['id'])
        await self.page.get_by_label('Objetivo global',exact=True).select_option('CUSTOM');await self.page.locator('.ultimate-policy summary').click()
        audit=(ROOT/'tests/browser/theme_audit.js').read_text();contrast=await self.page.evaluate(audit,'.ultimate-foundation')
        (OUT/'case-contrast.json').write_text(json.dumps(contrast,indent=2));self.assertGreater(contrast['textCount'],20);self.assertEqual(contrast['failures'],[])
        measurements=[]
        for width in [1440,390]:
            await self.page.set_viewport_size({'width':width,'height':1000})
            first=self.page.locator('.ultimate-foundation header button');await first.focus();count=0
            while count<80:
                await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
                # Viewport scrolling rounds to whole pixels; DOM rectangles retain fractions.
                data=await self.page.evaluate('''()=>{const n=document.activeElement,b=n.getBoundingClientRect(),hit=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2),c=getComputedStyle(n);return {inForm:!!n.closest('.ultimate-foundation'),name:n.name||n.textContent.slice(0,60),tag:n.tagName,rect:b.toJSON(),scroll:scrollY,hit:hit?.className,visible:b.top>=-1&&b.bottom<=innerHeight+1,reachable:hit===n||n.contains(hit),outline:parseFloat(c.outlineWidth),label:n.labels?[...n.labels].map(x=>x.textContent).join(''):null}}''')
                if not data['inForm']:break
                (OUT/'keyboard-focus-latest.json').write_text(json.dumps({'width':width,**data},indent=2))
                self.assertTrue(data['visible'] and data['reachable'],data)
                if data['tag'] in ['INPUT','SELECT','TEXTAREA']:self.assertTrue(data['label'],data)
                measurements.append({'width':width,**data});count+=1;await self.page.keyboard.press('Tab')
            self.assertGreater(count,15);self.assertLess(count,80)
        (OUT/'keyboard-focus.json').write_text(json.dumps(measurements,indent=2))
    async def test_07_models_library_empty_search_and_versioned_edit(self):
        m,v=await self.model('W3 colección · '+str(uuid4())[:8]);mid=m['model']['id']
        await self.open('/app/ddas/logistics/models?model_id='+mid)
        await self.page.get_by_label('Operating Role',exact=True).select_option('HYBRID');await self.page.get_by_role('button',name='Guardar borrador',exact=True).click()
        await self.page.wait_for_function('document.querySelector("[name=operating_role]")?.value==="HYBRID" && document.querySelector(".ultimate-footer [role=status]")?.textContent==="Sin cambios pendientes."')
        await self.page.get_by_role('button',name='Publicar nueva versión',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Publicar versión',exact=True).click();await self.page.get_by_text('Versión 2',exact=True).wait_for()
        stored=await self.api('GET','/api/platform/logistics-models/'+mid);self.assertEqual(len(stored['versions']),2);self.assertEqual(stored['versions'][1]['id'],v['version']['id']);self.assertEqual(stored['versions'][1]['config_jsonb']['operating_role'],'SHIPPER')
        await self.page.get_by_role('button',name='Volver a Models',exact=True).click();await self.page.get_by_label('Buscar Models',exact=True).wait_for()
        await self.page.get_by_label('Buscar Models',exact=True).fill('No existe '+str(uuid4()));await self.page.get_by_role('button',name='Buscar',exact=True).click();await self.page.get_by_text('No hay Models que coincidan. Probá otro nombre.',exact=True).wait_for()
        await self.page.get_by_label('Buscar Models',exact=True).fill(stored['model']['name']);await self.page.get_by_role('button',name='Buscar',exact=True).click();await self.page.get_by_role('button',name='Abrir Model',exact=True).wait_for();self.assertEqual(await self.page.locator('.ultimate-model-card').count(),1)
    async def test_08_publish_cas_recovers_without_overwriting_a_published_version(self):
        m,v=await self.model();mid=m['model']['id'];await self.open('/app/ddas/logistics/models?model_id='+mid)
        await self.api('PUT','/api/platform/logistics-models/'+mid,{'expected_revision':2,'name':'Nombre concurrente','configuration':{**CONFIG,'operating_role':'HYBRID'}})
        await self.page.get_by_role('button',name='Publicar nueva versión',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Publicar versión',exact=True).click()
        await self.page.get_by_text('El Model cambió. Tu borrador se conserva. Recargá la versión guardada antes de publicar.',exact=True).wait_for()
        self.assertEqual(await self.page.get_by_label('Nombre del Model',exact=True).input_value(),m['model']['name'])
        await self.page.get_by_role('button',name='Descartar borrador y recargar',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Descartar y recargar',exact=True).click()
        await self.page.wait_for_function('document.querySelector("[name=model_name]")?.value==="Nombre concurrente"')
        await self.page.get_by_role('button',name='Publicar nueva versión',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Publicar versión',exact=True).click();await self.page.get_by_text('Versión 2',exact=True).wait_for()
        stored=await self.api('GET','/api/platform/logistics-models/'+mid);self.assertEqual(stored['versions'][1]['id'],v['version']['id']);self.assertEqual(stored['versions'][0]['config_jsonb']['operating_role'],'HYBRID')
    async def test_09_unchanged_values_do_not_restore_a_false_dirty_draft(self):
        _,_,c=await self.case();await self.open('/app/ddas/logistics/case?case_id='+c['case']['id'])
        await self.page.get_by_label('Nombre del Case',exact=True).fill(c['case']['label'])
        await self.page.reload();await self.page.locator('[data-ultimate-ready="true"]').wait_for()
        self.assertEqual(await self.page.locator('.ultimate-footer [role=status]').text_content(),'Sin cambios pendientes.')
        self.assertFalse(await self.page.evaluate('Object.keys(sessionStorage).filter(k=>k.startsWith("dation.ultimate.setup.v1")).length>0'))
        await self.page.get_by_label('Nombre del Case',exact=True).fill('Borrador que sí cambia')
        self.page.on('dialog',lambda dialog:dialog.accept());await self.page.reload();await self.page.locator('[data-ultimate-ready="true"]').wait_for()
        self.assertEqual(await self.page.get_by_label('Nombre del Case',exact=True).input_value(),'Borrador que sí cambia')


if __name__=='__main__':unittest.main()
