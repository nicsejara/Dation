"""Golden V2: real BFF sessions, distinct responsibilities, engines and persisted navigation."""
import asyncio
from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import parse_qs,urlsplit,urlencode

from playwright.async_api import async_playwright
from browser_auth import api_get

BASE=os.environ['DATION_E2E_URL']
assert urlsplit(BASE).hostname=='127.0.0.1','Never run synthetic workflows on production.'
INPUTS=Path(os.environ['DATION_E2E_INPUTS'])
ARTIFACT=Path(os.environ['DATION_E2E_ARTIFACTS']) if os.getenv('DATION_E2E_ARTIFACTS') else None
WIDTHS=[1440,1280,1024,768,390]
STEWARD='10000000-0000-4000-8000-000000000005'
OWNER='10000000-0000-4000-8000-000000000006'
APPROVER='10000000-0000-4000-8000-000000000007'
THEME=(Path(__file__).parents[1]/'browser/theme_audit.js').read_text()


async def main():
    errors=[];requests=[];surfaces=set();probes=[];runs={};evidence={};run_history=[];case=None
    if ARTIFACT:ARTIFACT.mkdir(parents=True,exist_ok=True)
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        pages={};contexts={}
        for actor,suffix in (('admin','1'),('steward','5'),('owner','6'),('approver','7'),('viewer','3')):
            context=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
            await context.tracing.start(screenshots=True,snapshots=True,sources=True)
            page=await context.new_page();page.set_default_timeout(20000)
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('request',lambda request,actor=actor:requests.append({'actor':actor,'method':request.method,'path':urlsplit(request.url).path,'query':parse_qs(urlsplit(request.url).query)}))
            await page.goto(BASE+'/login');await page.get_by_label('Email',exact=True).fill('user-'+suffix+'@example.test')
            await page.get_by_label('Contraseña',exact=True).fill('dispatch-e2e-private')
            await page.get_by_role('button',name='Ingresar',exact=True).click()
            await page.locator('[data-platform-home] h1').wait_for()
            pages[actor]=page;contexts[actor]=context
        admin,steward,owner,outsider,viewer=[pages[key] for key in ('admin','steward','owner','approver','viewer')];approver=owner

        def collections():
            return Counter((r['actor'],r['path']) for r in requests if r['method']=='GET' and r['path'] in ('/api/platform/home','/api/platform/decisions','/api/platform/data/datasets'))

        async def matrix(page,name,selector='.view.is-active'):
            await page.wait_for_load_state('networkidle');before=collections()
            for width in WIDTHS:
                await page.set_viewport_size({'width':width,'height':1000})
                await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
                audit=await page.evaluate(THEME,selector)
                assert not audit['overflow'] and not audit['failures'] and audit['scheme']=='dark' and not audit['legacyBoundary'],(name,width,audit)
                probes.append({'surface':name,'width':width,'minimum_contrast':audit['minimumContrast']})
                if ARTIFACT:await page.screenshot(path=str(ARTIFACT/f'{name}-{width}.png'))
            assert collections()==before,(name,'Resize must not refetch portfolios or summaries.')
            await page.set_viewport_size({'width':1440,'height':1000});surfaces.add(name)

        def target(view,node=None,run=None):
            value={'view':view,'case_id':case}
            if node:value['node_id']=node
            if run:value['run_id']=run
            return BASE+'/app?'+urlencode(value)

        async def open_stage(page,view,node=None,run=None):
            await page.goto(target(view,node,run))
            selector='[data-config-review],[data-scheduling-review]' if view=='logistics-config' else '.d-decision-dashboard' if view=='decision-dashboard' else '[data-map-node]'
            await page.locator(selector).first.wait_for()

        async def assign(stage,uid,field='owner',audit_editor=False):
            root=admin.locator('[data-workflow-responsibility="'+stage+'"][data-responsibility-field="'+field+'"]')
            await root.get_by_role('button',name=re.compile('^(Seleccionar responsable|Cambiar)$')).click()
            select=root.locator('select');await select.locator('option[value="'+uid+'"]').wait_for(state='attached')
            options=await select.locator('option').evaluate_all('nodes=>nodes.map(n=>n.value).filter(Boolean)')
            assert options==[uid],(stage,field,options)
            if audit_editor:await matrix(admin,'responsibility')
            await select.select_option(uid);await root.get_by_role('button',name='Guardar',exact=True).click()
            await admin.wait_for_function('(args)=>window.DationDispatch.getWorkspace().workflow.stages[args[0]][args[1]+"_eligible"]',arg=[stage,field])
            await root.get_by_role('button',name='Cambiar',exact=True).wait_for()

        async def execute(node):
            context=owner.locator('[data-config-context]')
            await context.locator('summary').click()
            context_text=await context.inner_text()
            assert 'Contexto del Case' in context_text and 'Golden DataOwner' in context_text
            assert 'Decision Owner' not in context_text and 'Data Steward' not in context_text
            assert 'DC-' not in await context.locator('summary').inner_text()
            await context.locator('summary').click()
            review='[data-config-review]' if node=='logistics_assignment' else '[data-scheduling-review]'
            confirm='[data-config-execute]' if node=='logistics_assignment' else '[data-scheduling-execute]'
            await owner.locator(review).click();dialog=owner.locator('dialog[open]')
            await dialog.get_by_text('Golden Owner',exact=True).wait_for()
            async with owner.expect_response(lambda r:urlsplit(r.url).path=='/api/runs' and r.request.method=='POST') as pending:
                await owner.locator(confirm).click()
            response=await pending.value;assert response.status==202,await response.text()
            run=(await response.json())['id'];runs[node]=run;run_history.append({'node':node,'id':run})
            await owner.locator('.d-decision-dashboard').wait_for()
            assert parse_qs(urlsplit(owner.url).query)['run_id']==[run]
            return run

        async def approve(node,run):
            await open_stage(admin,'decision-dashboard',node,run)
            assert await admin.locator('[data-workflow-responsibility]').count()==0
            await open_stage(outsider,'decision-dashboard',node,run)
            assert await outsider.locator('[data-approve-toolbar],[data-approve-final]').count()==0
            await open_stage(approver,'decision-dashboard',node,run)
            async with approver.expect_response(lambda r:urlsplit(r.url).path=='/api/runs/'+run+'/approve' and r.request.method=='POST') as pending:
                await approver.locator('[data-approve-toolbar]').click()
            response=await pending.value;assert response.status==200
            saved=await response.json()
            evidence[node]={key:saved[key] for key in ('id','result_fingerprint','configuration_json','created_by_user_id','approved_by_user_id','upstream_run_id')}
            await approver.wait_for_function('node=>window.DationDispatch.getWorkspace().decisionCase.nodes[node].status==="approved"',arg=node)
            await approver.locator('#dispatch-hero [data-run-trace] dd').get_by_text('Golden Owner',exact=True).wait_for()
            assert await approver.locator('#dispatch-hero').get_by_text('Configurado por',exact=True).count()==0
            await approver.locator('#dispatch-hero [data-run-trace] dt').get_by_text('Aprobado por',exact=True).wait_for()
            assert parse_qs(urlsplit(approver.url).query)['run_id']==[run]

        try:
            await matrix(steward,'home')
            await steward.locator('[data-platform-home] .platform-home__hero-actions a').first.click()
            await steward.locator('[data-dda-id=logistics]').wait_for()
            await steward.locator('#home-open-logistics').click()
            await steward.locator('[data-start-new-decision]').click()
            await steward.get_by_label('Nombre del Case',exact=True).fill('SEMANA 43')
            await steward.get_by_label('Categoría',exact=True).select_option('weekly')
            for kind in ('orders','fleet'):
                async with steward.expect_response(lambda r:urlsplit(r.url).path=='/api/datasets/upload' and r.request.method=='POST') as pending:
                    await steward.locator('[data-kind="'+kind+'"] input[type=file]').set_input_files(INPUTS/(kind+'.csv'))
                assert (await pending.value).status==200
            data=steward.locator('#dispatch-data-root');next_button=data.get_by_role('button',name='Seleccioná tu decisión',exact=True)
            assert await next_button.is_disabled()
            await data.get_by_role('button',name='Aplicar',exact=True).click()
            await data.locator('[data-case-identity-feedback]').get_by_text('Atributos aplicados.',exact=True).wait_for()
            await data.get_by_role('button',name='Actualizar responsabilidad',exact=True).wait_for()
            case=await steward.evaluate('window.DationDispatch.getWorkspace().decisionCase.id')
            await admin.goto(target('logistics-data'))
            await assign('data_owner',STEWARD)
            await data.get_by_role('button',name='Actualizar responsabilidad',exact=True).click()
            await steward.wait_for_function('!document.querySelector("#dispatch-data-root .d-workflow-action-bar button").disabled')
            await matrix(steward,'data')
            await next_button.click();await steward.locator('[data-map-node=logistics_assignment]').first.wait_for()
            await matrix(steward,'map')
            await open_stage(admin,'logistics-map')
            await assign('logistics_assignment',OWNER,audit_editor=True)
            await assign('logistics_scheduling',OWNER)
            await open_stage(owner,'logistics-config','logistics_assignment')
            await owner.locator('[data-objective=min_cost]').click()
            assert await owner.locator('.dda-navigation li').count()==3
            await owner.locator('#dda-workspace-nav [data-step="1"]').click()
            await owner.locator('[data-case-identity]').wait_for()
            assert parse_qs(urlsplit(owner.url).query)['case_id']==[case]
            await owner.locator('#dda-workspace-nav [data-step="2"]').click()
            await owner.locator('[data-map-action=configure][data-map-node=logistics_assignment]').click()
            await owner.locator('[data-config-review]').wait_for()
            await matrix(owner,'config')
            await execute('logistics_assignment')
            await owner.locator('#dda-workspace-nav [data-step="3"]').click()
            await owner.locator('[data-config-review]').wait_for()
            d1=await execute('logistics_assignment')
            await matrix(owner,'dashboard')
            await approve('logistics_assignment',d1)
            final=approver.locator('.assignment-final-actions')
            await final.get_by_role('button',name='Configurar siguiente decisión',exact=True).wait_for()
            assert await final.get_by_role('button',name='Ver mapa de decisiones',exact=True).is_visible()
            assert await approver.locator('[data-approval-handoff]').count()==0
            await final.get_by_role('button',name='Configurar siguiente decisión',exact=True).click()
            await approver.locator('[data-scheduling-review]').wait_for()
            assert 'run_id=' not in approver.url
            await open_stage(admin,'logistics-config','logistics_scheduling')
            assert await admin.locator('[data-workflow-responsibility]').count()==0
            await open_stage(owner,'logistics-config','logistics_scheduling')
            await execute('logistics_scheduling')
            await owner.locator('#dda-workspace-nav [data-step="3"]').click()
            await owner.locator('[data-scheduling-review]').wait_for()
            d2=await execute('logistics_scheduling')

            # Navigation is a matrix: horizontal changes the decision, vertical changes the level.
            await owner.locator('.dda-navigation a').last.click()
            await owner.locator('[data-map-action=open-result][data-map-node=logistics_scheduling]').click()
            await owner.locator('.scheduling-dashboard-v2').wait_for()
            await owner.locator('#dda-workspace-nav [data-step="3"]').click()
            await owner.locator('[data-scheduling-review]').wait_for()
            for node,selector in [('logistics_assignment','[data-config-review]'),('logistics_scheduling','[data-scheduling-review]')]:
                await owner.locator('.dispatch-decision-tab[data-decision-node="'+node+'"]').click()
                await owner.locator(selector).wait_for()
                query=parse_qs(urlsplit(owner.url).query)
                assert query['case_id']==[case] and query['node_id']==[node] and 'run_id' not in query
            await owner.locator('#dda-workspace-nav [data-step="4"]').click()
            await owner.locator('.scheduling-dashboard-v2').wait_for()
            for node,rid,selector in [('logistics_assignment',d1,'.assignment-dashboard-v2'),('logistics_scheduling',d2,'.scheduling-dashboard-v2')]:
                await owner.locator('.dispatch-decision-tab[data-decision-node="'+node+'"]').click()
                await owner.locator(selector).wait_for()
                query=parse_qs(urlsplit(owner.url).query)
                assert query['case_id']==[case] and query['node_id']==[node] and query['run_id']==[rid]
            await owner.locator('#dda-workspace-nav [data-step="3"]').click()
            await owner.locator('[data-scheduling-review]').wait_for()
            assert parse_qs(urlsplit(owner.url).query)['node_id']==['logistics_scheduling']
            await owner.locator('#dda-workspace-nav [data-step="4"]').click()
            await owner.locator('.scheduling-dashboard-v2').wait_for()
            assert await owner.locator('.decision-view-tabs,[data-back-map],[data-approval-handoff]').count()==0
            await approve('logistics_scheduling',d2)
            final=approver.locator('.scheduling-final-actions')
            await final.get_by_role('button',name='Volver a Decision Center',exact=True).wait_for()
            assert 'Case completado' in await final.inner_text()
            assert await final.get_by_role('button',name='Ver mapa del Case',exact=True).is_visible()
            assert await final.get_by_role('button',name='Configurar siguiente decisión',exact=True).count()==0

            await owner.locator('.dispatch-decision-tab[data-decision-node=logistics_assignment]').click()
            await owner.locator('.assignment-dashboard-v2').wait_for()
            await owner.locator('#dda-workspace-nav [data-step="3"]').click()
            await owner.locator('[data-config-review]').wait_for()
            d1=await execute('logistics_assignment')
            assert await owner.evaluate('window.DationDispatch.getWorkspace().decisionCase.nodes.logistics_scheduling.status')=='stale'
            await approve('logistics_assignment',d1)
            await owner.locator('.assignment-final-actions [data-approved-map]').click()
            await owner.locator('[data-map-action=configure][data-map-node=logistics_scheduling]').click()
            await owner.locator('[data-scheduling-review]').wait_for()
            d2=await execute('logistics_scheduling')
            await approve('logistics_scheduling',d2)

            # Both rails use their canonical run, with no configuration bounce.
            for node,run in (('logistics_assignment',d1),('logistics_scheduling',d2)):
                await approver.locator('.view.is-active .dispatch-decision-tab[data-decision-node="'+node+'"]').first.click()
                await approver.wait_for_url('**run_id='+run)
                await approver.locator('.d-decision-dashboard').wait_for()
                query=parse_qs(urlsplit(approver.url).query);assert query['case_id']==[case] and query['node_id']==[node]
            switch_start=len(requests)
            assert await approver.locator('[data-case-switcher],[data-select-case]').count()==0
            await approver.get_by_role('button',name='Volver a Decision Center',exact=True).click()
            await approver.locator('[data-center-case="'+case+'"]').wait_for()
            await matrix(approver,'completed')
            await approver.locator('[data-case-open="'+case+'"]').click()
            center=approver.locator('[data-platform-decisions]');await center.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
            assert parse_qs(urlsplit(approver.url).query)['center_case_id']==[case]
            assert await center.locator('[data-center-case="'+case+'"]').get_attribute('aria-selected')=='true'
            assert 'Golden DataOwner' in await center.locator('.center-linked-data').inner_text()
            for node in ('logistics_assignment','logistics_scheduling'):
                detail=center.locator('[data-center-node="'+node+'"]')
                await detail.locator('summary',has_text='Responsables y aprobación').click()
                text=await detail.inner_text();assert 'Golden Owner' in text and 'Aprobador asignado' not in text
                assert 'Aprobada por · Golden Owner' in text
                assert 'Objetivo · Por definir' not in text
            await center.locator('[data-case-activity] .platform-activity__event').first.wait_for()
            assert await center.locator('.center-linked-file').count()==2
            assert not any(r['path'].endswith('/runs') and '/api/platform/decisions/' in r['path'] and not (r['query'].get('run_id') and r['query'].get('limit')==['1']) for r in requests)
            await matrix(approver,'decision_center')
            await center.get_by_role('button',name='Cerrar detalle del caso',exact=True).click()

            await approver.locator('.nav [data-platform-view=platform-data]').click()
            hub=approver.locator('[data-platform-data]');await hub.get_by_role('table').wait_for()
            dataset=(await (await api_get(contexts['approver'],BASE+'/api/decision-cases/'+case)).json())['orders']['id']
            await hub.locator('[data-dataset-open="'+dataset+'"]').click()
            await hub.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
            assert not any(r['path'].endswith('/preview') for r in requests)
            await matrix(approver,'data_hub')
            await hub.get_by_role('link',name='Ver Decision Case',exact=True).click()
            await center.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
            await approver.go_back();await hub.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
            assert parse_qs(urlsplit(approver.url).query)['dataset_id']==[dataset]
            await approver.reload();await hub.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
            assert await hub.locator('[data-dataset="'+dataset+'"]').get_attribute('aria-selected')=='true'
            await hub.get_by_role('button',name='Cerrar detalle del dataset',exact=True).click()
            await approver.wait_for_function('id=>document.activeElement?.dataset.datasetOpen===id',arg=dataset)

            await open_stage(viewer,'logistics-config','logistics_assignment')
            assert await viewer.locator('[data-config-review]').is_disabled()
            assert await viewer.locator('[data-workflow-responsibility] button').count()==0
            await open_stage(viewer,'decision-dashboard','logistics_scheduling',d2)
            assert await viewer.locator('[data-approve-toolbar],[data-approve-final]').count()==0
            switch_queries=[r for r in requests if r['path']=='/api/platform/decisions' and r['query'].get('limit')==['8']]
            assert switch_queries==[], 'The Case flow must never query an internal Case picker.'
            assert not any(r['method']=='GET' and r['path']=='/api/decision-cases' for r in requests[switch_start:])
            assert sum(r['method']=='POST' and r['path']=='/api/runs' for r in requests)==6
            assert sum(r['method']=='POST' and r['path'].endswith('/approve') for r in requests)==4
            for node,rid in runs.items():
                final=await (await api_get(contexts['approver'],BASE+'/api/runs/'+rid)).json()
                assert all(final[key]==value for key,value in evidence[node].items()),(node,'Navigation changed persisted execution evidence.')
            # Attribute edits preserve the completed Case; a changed file creates another Case.
            await owner.goto(target('logistics-data'))
            await owner.locator('[data-case-identity]').wait_for()
            await owner.get_by_label('Nombre del Case',exact=True).fill('SEMANA 44')
            await owner.get_by_role('button',name='Aplicar',exact=True).click()
            await owner.locator('[data-case-identity-feedback]').get_by_text('Atributos aplicados.',exact=True).wait_for()
            assert await owner.evaluate('window.DationDispatch.getWorkspace().decisionCase.id')==case
            assert await owner.locator('.d-workflow-action-bar__item').count()==4
            assert 'Data Steward' not in await owner.locator('#dispatch-data-root').inner_text()
            await owner.locator('[data-kind="orders"] input[type=file]').set_input_files({'name':'next-pack-orders.csv','mimeType':'text/csv','buffer':(INPUTS/'orders.csv').read_bytes()+b'\n'})
            await owner.wait_for_function('id=>window.DationDispatch.getWorkspace().decisionCase?.persisted&&window.DationDispatch.getWorkspace().decisionCase.id!==id',arg=case)
            fork=await owner.evaluate('window.DationDispatch.getWorkspace().decisionCase.id')
            assert await owner.locator('.d-workflow-action-bar button').is_disabled()
            preserved=await (await api_get(contexts['owner'],BASE+'/api/decision-cases/'+case)).json()
            assert all(preserved['decision_case']['nodes'][node]['status']=='approved' for node in runs)
            assert errors==[],errors
            report={'passed':True,'case_id':case,'runs':runs,'run_history':run_history,'forked_case_id':fork,'viewports':WIDTHS,'surfaces':sorted(surfaces),'responsive_probes':probes,'distinct_actor_sessions':5,'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).parents[2],text=True).strip(),'javascript_errors':errors,'requests':requests}
            if ARTIFACT:(ARTIFACT/'report.json').write_text(json.dumps(report,indent=2))
            print(json.dumps(report))
        except BaseException:
            if ARTIFACT:
                (ARTIFACT/'failure.json').write_text(json.dumps({'requests':requests,'actor_urls':{actor:page.url for actor,page in pages.items()},'javascript_errors':errors},indent=2))
                for actor,page in pages.items():await page.screenshot(path=str(ARTIFACT/(actor+'-failure.png')))
            raise
        finally:
            for actor,context in contexts.items():
                await context.tracing.stop(path=str(ARTIFACT/(actor+'-trace.zip')) if ARTIFACT else None)
            await browser.close()


asyncio.run(main())
