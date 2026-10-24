"""Actual contextual reruns and history across seven real engine executions."""
import asyncio,copy,json,os
from pathlib import Path
from urllib.parse import urlsplit,urlencode,parse_qs
from playwright.async_api import async_playwright
from browser_auth import api_get

BASE=os.environ['DATION_E2E_URL'];CASE=os.environ['DATION_E2E_CASE']
assert urlsplit(BASE).hostname=='127.0.0.1','Synthetic lineage is local only.'
ARTIFACT=Path(os.environ['DATION_E2E_ARTIFACTS']) if os.getenv('DATION_E2E_ARTIFACTS') else None
async def main():
    runs={};requests=[];errors=[];scenarios={};snapshots={}
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        context=await browser.new_context(viewport={'width':1440,'height':900},reduced_motion='reduce');page=await context.new_page();page.set_default_timeout(20000)
        await context.tracing.start(screenshots=True,snapshots=True,sources=True)
        page.on('pageerror',lambda error:errors.append(str(error)))
        def record(request):
            u=urlsplit(request.url)
            if u.path=='/api/runs' and request.method=='POST':requests.append({'id':parse_qs(u.query)['run_id'][0],'body':request.post_data_json})
        page.on('request',record)
        async def get(path):
            response=await api_get(context,BASE+path);assert response.status==200,await response.text();return await response.json()
        def target(node,run=None):
            return BASE+'/app?'+urlencode({'view':'decision-dashboard' if run else 'logistics-config','case_id':CASE,'node_id':'logistics_'+node,**({'run_id':run} if run else {})})
        async def open_dashboard(node,run):
            await page.goto(target(node,run));await page.locator('.d-decision-dashboard').wait_for()
            await page.wait_for_function('id=>window.DationDispatch?.getWorkspace().run?.id===id',arg=run)
        async def execute(node):
            review='[data-config-review]' if node=='assignment' else '[data-scheduling-review]'
            confirm='[data-config-execute]' if node=='assignment' else '[data-scheduling-execute]'
            await page.locator(review).click()
            async with page.expect_response(lambda r:urlsplit(r.url).path=='/api/runs' and r.request.method=='POST') as admitted:await page.locator(confirm).click()
            response=await admitted.value;assert response.status==202,await response.text();rid=(await response.json())['id']
            await page.locator('.d-decision-dashboard').wait_for();await page.wait_for_function('id=>window.DationDispatch?.getWorkspace().run?.id===id',arg=rid)
            assert parse_qs(urlsplit(page.url).query)['node_id']==['logistics_'+node]
            if ARTIFACT:await page.screenshot(path=str(ARTIFACT/f'run-{node}-{len(requests)}.png'),full_page=True)
            return rid
        async def approve(rid):
            await page.locator('[data-approve-toolbar]').click()
            await page.wait_for_function('document.querySelector("[data-approve-toolbar]")?.disabled===true&&document.querySelector("[data-status-badge]")?.textContent==="Aprobada"')
            saved=await get('/api/runs/'+rid);assert saved['approved_at'];snapshots[rid]=saved
        async def rerun(node,warning):
            before=len(requests);await page.locator('[data-rerun]').click()
            if warning:
                modal=page.locator('[data-new-run-warning][open]');await modal.wait_for()
                await modal.get_by_role('button',name='Confirmar nueva corrida',exact=True).click()
            await page.locator('[data-config-review]' if node=='assignment' else '[data-scheduling-review]').wait_for()
            q=parse_qs(urlsplit(page.url).query);assert q['view']==['logistics-config'] and q['case_id']==[CASE] and q['node_id']==['logistics_'+node] and 'run_id' not in q
            assert len(requests)==before,'Opening configuration never admits or invalidates a Run.'
            await page.reload();await page.locator('[data-config-review]' if node=='assignment' else '[data-scheduling-review]').wait_for()
            await page.go_back();await page.locator('.d-decision-dashboard').wait_for()
            await page.go_forward();await page.locator('[data-config-review]' if node=='assignment' else '[data-scheduling-review]').wait_for()
        try:
            await page.goto(BASE+'/login');await page.get_by_label('Email',exact=True).fill('user-6@example.test');await page.get_by_label('Contraseña',exact=True).fill('dispatch-e2e-private');await page.get_by_role('button',name='Ingresar',exact=True).click();await page.locator('[data-platform-home] h1').wait_for()
            await page.goto(target('assignment'));await page.locator('[data-config-review]').wait_for()
            runs['D1_01']=await execute('assignment')
            await rerun('assignment',False);scenarios['A']='PASS';runs['D1_02']=await execute('assignment')
            await rerun('assignment',False);runs['D1_A']=await execute('assignment');scenarios['D']='PASS';await approve(runs['D1_A'])
            await page.goto(target('scheduling'));await page.locator('[data-scheduling-review]').wait_for();runs['D2_A']=await execute('scheduling');await approve(runs['D2_A'])
            await rerun('scheduling',True);scenarios['B']='PASS'
            assert (await get('/api/runs/'+runs['D1_A']))['superseded_at'] is None
            assert (await get('/api/runs/'+runs['D2_A']))['superseded_at'] is None
            runs['D2_B']=await execute('scheduling')
            for key in ('D2_A','D2_B'):assert (await get('/api/runs/'+runs[key]))['upstream_run_id']==runs['D1_A']
            assert (await get('/api/runs/'+runs['D1_A']))['superseded_at'] is None
            scenarios['E']='PASS';await approve(runs['D2_B'])
            await open_dashboard('assignment',runs['D1_A']);await rerun('assignment',True)
            assert (await get('/api/runs/'+runs['D1_A']))['superseded_at'] is None
            runs['D1_B']=await execute('assignment')
            for key in ('D1_A','D2_A','D2_B'):assert (await get('/api/runs/'+runs[key]))['superseded_at']
            assert not (await get('/api/runs/'+runs['D1_B']))['approved_at'];scenarios['C']='PASS'
            await approve(runs['D1_B'])
            await page.goto(target('scheduling'));await page.locator('[data-scheduling-review]').wait_for();runs['D2_C']=await execute('scheduling')
            assert (await get('/api/runs/'+runs['D2_C']))['upstream_run_id']==runs['D1_B'];scenarios['F']='PASS'
            for rid,before in snapshots.items():
                saved=await get('/api/runs/'+rid)
                for key in ('result_json','result_fingerprint','input_fingerprint','configuration_json','approved_at','approved_by_user_id','upstream_run_id'):assert saved[key]==before[key],(rid,key)
            history=[]
            for node in ('logistics_assignment','logistics_scheduling'):
                history.extend((await get(f'/api/platform/decisions/{CASE}/runs?node_id={node}&limit=50'))['items'])
            assert set(runs.values()).issubset({r['id'] for r in history})
            await open_dashboard('scheduling',runs['D2_A']);await page.reload();await page.wait_for_function('id=>window.DationDispatch?.getWorkspace().run?.id===id',arg=runs['D2_A'])
            await page.go_back();await page.wait_for_function('id=>window.DationDispatch?.getWorkspace().run?.id===id',arg=runs['D2_C'])
            await page.go_forward();await page.wait_for_function('id=>window.DationDispatch?.getWorkspace().run?.id===id',arg=runs['D2_A'])
            assert not errors,errors
            print(json.dumps({'scenarios':scenarios,'runs':runs,'requests':requests,'errors':errors}),flush=True)
        finally:
            if ARTIFACT:await context.tracing.stop(path=str(ARTIFACT/'lineage-trace.zip'))
            await browser.close()
asyncio.run(main())
