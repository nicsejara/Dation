"""Real Chromium journey. No API responses, runs or SQL are mocked."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright
from workflow_ui_audit import WorkflowUIAudit


async def journey():
    base=os.environ['DATION_E2E_URL']
    assert urlparse(base).hostname=='127.0.0.1', 'E2E must use its owned loopback API.'
    inputs=Path(os.environ['DATION_E2E_INPUTS'])
    gate=Path(os.environ['DATION_E2E_STORAGE'])/'block-downloads'
    errors,requests,failed,expected_draft_misses=[],[],[],[]
    admitted=False
    artifact=os.getenv('DATION_E2E_ARTIFACTS')
    viewport=json.loads(os.getenv('DATION_E2E_VIEWPORT','{"width":1440,"height":1000}'))
    assert 320<=viewport['width']<=1920 and 250<=viewport['height']<=1200
    async with async_playwright() as pw:
        executable=os.getenv('CHROMIUM_EXECUTABLE')
        if not executable and Path('/usr/bin/chromium').exists():executable='/usr/bin/chromium'
        browser=await pw.chromium.launch(executable_path=executable,headless=True,
            args=['--no-sandbox','--disable-dev-shm-usage'])
        context=await browser.new_context(http_credentials={'username':'dation','password':os.environ['DATION_ACCESS_PASSWORD'],
            'origin':base,'send':'always'},
            viewport=viewport,accept_downloads=True,reduced_motion='reduce')
        await context.tracing.start(screenshots=True,snapshots=True,sources=True)
        page=await context.new_page();page.set_default_timeout(30000)
        def response_seen(response):
            path=urlparse(response.url).path
            if path.startswith('/api/') and response.status>=400:
                # URL hydration may race the initial case registration on Map.
                # Only that draft's hydration misses are expected; later 404s fail.
                route_case=parse_qs(urlparse(response.request.frame.url).query).get('case_id',[None])[0]
                if not admitted and response.status==404 and path=='/api/decision-cases/'+str(route_case):
                    expected_draft_misses.append(path)
                    return
                failed.append((response.status,path))
        def watch(tab):
            tab.on('pageerror',lambda error:errors.append(str(error)))
            tab.on('request',lambda request:requests.append((request.method,urlparse(request.url).path)))
            tab.on('response',response_seen)
        watch(page)
        context.on('page',watch)
        ui=WorkflowUIAudit(page,Path(artifact) if artifact else None,viewport)
        try:
            await page.goto(base+'/app?view=inicio',wait_until='domcontentloaded')
            await page.locator('#home-open-logistics').wait_for(state='visible')
            await page.locator('[data-dda-filter=all]').wait_for()
            assert await page.locator('[data-dda-id]').count()==7
            assert await page.locator('[data-dda-status=coming-soon] button,[data-dda-status=coming-soon] a').count()==0
            await page.locator('[data-dda-filter=supply-chain]').click()
            assert await page.locator('[data-dda-id]:not([hidden])').count()==2
            await page.locator('[data-dda-filter=all]').click()
            await ui.checkpoint('inicio')
            await page.locator('#home-open-logistics').click()
            await page.wait_for_selector('[data-start-new-decision]')
            assert await page.locator('.dda-landing button').count()==2
            assert not await page.locator('[data-start-new-decision]').is_disabled()
            assert await page.locator('[data-open-decision-map]').is_disabled()
            await ui.checkpoint('overview')
            await page.locator('[data-start-new-decision]').click()
            await page.wait_for_selector('[data-kind="orders"] input[type=file]',state='attached')
            next_button=page.locator('.dispatch-pro-next-button')
            await next_button.wait_for(state='visible')
            assert await next_button.is_disabled()
            disabled_style=await next_button.evaluate('el=>[getComputedStyle(el).backgroundImage,getComputedStyle(el).backgroundColor,getComputedStyle(el).transform]')
            await next_button.hover(force=True)
            assert await next_button.evaluate('el=>[getComputedStyle(el).backgroundImage,getComputedStyle(el).backgroundColor,getComputedStyle(el).transform]')==disabled_style
            await page.mouse.move(0,0)
            await ui.hero('data-pending')
            await ui.checkpoint('data-pending')
            for kind in ('orders','fleet'):
                async with page.expect_response(lambda response:
                    urlparse(response.url).path=='/api/datasets/upload' and response.request.method=='POST') as upload:
                    await page.locator('[data-kind="'+kind+'"] input[type=file]').set_input_files(inputs/(kind+'.csv'))
                assert (await upload.value).status==200
                if kind=='orders':assert await next_button.is_disabled()
            await page.locator('.d-workflow-action-bar[data-state=ready]').wait_for()
            await ui.hero('data-ready')
            await ui.bar('data',2)
            await ui.action('data',next_button)
            await ui.checkpoint('data-ready')
            await next_button.click()
            await page.wait_for_selector('[data-map-node="logistics_assignment"][data-map-action]')
            await ui.hero('map-ready')
            await ui.action('map-assignment',page.locator('[data-map-node="logistics_assignment"][data-map-action]').first)
            await ui.checkpoint('map-ready')
            assert not await page.locator('[data-map-context]').get_attribute('open')
            assert await page.locator('.dispatch-map-progress [role=progressbar]').is_visible()
            # A validated case is durable and selectable before its first run.
            initial=await page.evaluate('window.DationDispatch.getWorkspace().decisionCase')
            assert initial['persisted']
            persisted=await context.request.get(base+'/api/decision-cases/'+initial['id'])
            assert persisted.status==200,{'status':persisted.status,'body':(await persisted.text())[:2000],'case_id':initial['id']}
            assert (await persisted.json())['decision_case']['inputs']==initial['inputs']
            map_url=page.url
            await page.locator('[data-select-case]').click()
            await page.get_by_role('dialog',name='Seleccionar Decision Case').wait_for()
            assert await page.get_by_role('button',name='Caso actual',exact=True).is_disabled()
            assert await page.get_by_text('No hay otros Decision Cases disponibles todavía.').is_visible()
            await page.keyboard.press('Escape')
            assert page.url==map_url
            assert await page.locator('[data-select-case]').evaluate('el=>el===document.activeElement')
            assert await page.locator('[data-case-transition]').count()==0
            await page.locator('[data-map-node="logistics_assignment"][data-map-action]').first.click()
            await page.wait_for_selector('[data-config-review]')
            await ui.hero('assignment','DECISIÓN 01 DE 3')
            assert not await page.locator('[data-config-context]').get_attribute('open')
            assert await page.locator("[data-depth]").count()==0
            assert await page.locator(".decision-advanced-option:disabled").count()==3
            for select in await page.locator('[data-config-anomaly]').all():await select.select_option('include')
            await ui.bar('assignment',3)
            await ui.action('assignment-review',page.locator('[data-config-review]'))
            await ui.checkpoint('assignment-config')
            config_url=page.url
            before_review=sum(method=='POST' and path=='/api/runs' for method,path in requests)
            await page.locator('[data-config-review]').click()
            assert page.url==config_url
            assert await page.evaluate('window.dationGetCurrentView()')=='logistics-config'
            assert await page.locator('[data-assignment-review-dialog]').evaluate("el=>el.matches(':modal')")
            assert sum(method=='POST' and path=='/api/runs' for method,path in requests)==before_review
            await ui.review('assignment')
            assert initial['id'][:8].lower() in (await page.locator('dialog[open]').inner_text()).lower()
            await page.keyboard.press('Escape')
            assert await page.locator('[data-config-review]').evaluate('el=>el===document.activeElement')
            await page.locator('[data-config-review]').click()
            await page.locator('[data-assignment-review-dialog]').get_by_role('button',name='Volver',exact=True).click()
            assert page.url==config_url
            assert sum(method=='POST' and path=='/api/runs' for method,path in requests)==before_review
            await page.locator('[data-config-review]').click()
            gate.touch()
            async with page.expect_response(lambda response:
                urlparse(response.url).path=='/api/runs' and response.request.method=='POST') as accepted:
                await page.locator('[data-config-execute]').click()
            response=await accepted.value
            assert response.status==202
            assert response.request.post_data_json["options"]["analysis_depth"]=="essential"
            admitted=True
            assignment=(await response.json())['id']
            case=(await response.json())['decision_case_id']
            await page.reload(wait_until='domcontentloaded')
            assert parse_qs(urlparse(page.url).query)['run_id']==[assignment]
            pending=await context.request.get(base+'/api/runs/'+assignment)
            assert (await pending.json())['status'] in ('queued','running')
            await page.get_by_role('heading',name='Preparando tu decisión',exact=True).wait_for()
            await ui.checkpoint('assignment-pending')
            gate.unlink()
            await page.wait_for_selector('.assignment-dashboard-v2')
            await ui.toolbar('assignment')
            await ui.checkpoint('assignment-dashboard')
            assert sum(method=='POST' and path=='/api/runs' for method,path in requests)==before_review+1
            assert await page.locator('[data-trip-detail]').count()==0
            assert not await page.locator('#dispatch-assignment').is_visible()
            assert not await page.locator('[data-ai-summary-body]').is_visible()
            await page.locator('[data-assignment-full-plan]').click()
            await page.locator('[data-trip-detail-button]').first.click()
            assert await page.locator('[data-trip-detail]').count()==1
            await page.keyboard.press('Escape')
            assert await page.locator('[data-trip-detail]').count()==0
            await page.locator('[data-generate-comparative]').click()
            await page.wait_for_selector('[data-comparative-state=completed]')
            comparative_posts=sum(method=='POST' and path.endswith('/comparative') for method,path in requests)
            await page.locator('[data-assignment-view=essential]').click()
            await page.reload(wait_until='domcontentloaded')
            await page.locator('[data-assignment-view=essential]').wait_for(state='visible')
            assert not await page.locator('#dispatch-assignment').is_visible()
            await page.locator('[data-assignment-view=advanced]').click()
            assert sum(method=='POST' and path.endswith('/comparative') for method,path in requests)==comparative_posts
            await page.reload(wait_until='domcontentloaded')
            await page.wait_for_selector('[data-comparative-state=completed]')
            assert await page.locator('[data-generate-comparative]').count()==0
            await page.locator('[data-approve-toolbar]').click()
            await page.wait_for_function("window.DationDispatch.getWorkspace().decisionCase.nodes.logistics_assignment.status==='approved'")
            await page.locator('[data-after-approve]').wait_for(state='visible')
            await ui.action('assignment-continue',page.locator('[data-after-approve]'))
            await ui.checkpoint('assignment-approved')
            await page.locator('[data-more-menu] summary').click()
            await page.locator('[data-dashboard-map]').click()
            await page.wait_for_selector('[data-map-node="logistics_scheduling"][data-map-action="configure"]')
            assert await page.get_by_role('progressbar',name='Decisiones aprobadas',exact=True).get_attribute('aria-valuenow')=='1'
            await ui.hero('map-after-assignment')
            await ui.action('map-scheduling',page.locator('[data-map-node="logistics_scheduling"][data-map-action="configure"]'))
            await ui.checkpoint('map-after-assignment')
            await page.locator('[data-map-node="logistics_scheduling"][data-map-action="configure"]').click()
            await page.wait_for_selector('[data-scheduling-review]')
            await page.go_back();await page.wait_for_selector('[data-map-node="logistics_scheduling"][data-map-action="configure"]')
            await page.go_back();await page.wait_for_selector('.assignment-dashboard-v2')
            # Preserve the direct continuation route as well as the full Map route.
            await page.locator('[data-after-approve]').click()
            await page.wait_for_selector('[data-scheduling-review]')
            assert 'run_id=' not in page.url
            await page.go_back();await page.wait_for_selector('.assignment-dashboard-v2')
            await page.go_forward();await page.wait_for_selector('[data-scheduling-review]')
            await page.reload(wait_until='domcontentloaded');await page.wait_for_selector('[data-scheduling-review]')
            assert not await page.locator('[data-config-context]').get_attribute('open')
            assert await page.get_by_text('ASIGNACIÓN APROBADA',exact=True).is_visible()
            await ui.hero('scheduling','DECISIÓN 02 DE 3')
            await ui.bar('scheduling',3)
            await ui.action('scheduling-review',page.locator('[data-scheduling-review]'))
            await ui.checkpoint('scheduling-config')
            config_url=page.url
            before_review=sum(method=='POST' and path=='/api/runs' for method,path in requests)
            await page.locator('[data-scheduling-review]').click()
            assert page.url==config_url
            assert await page.evaluate('window.dationGetCurrentView()')=='logistics-config'
            dialog=page.locator('[data-scheduling-review-dialog]')
            assert await dialog.evaluate("el=>el.matches(':modal')")
            assert await dialog.evaluate("el=>getComputedStyle(el,'::backdrop').backgroundColor")=='rgba(0, 0, 0, 0.64)'
            assert sum(method=='POST' and path=='/api/runs' for method,path in requests)==before_review
            await ui.review('scheduling')
            assert assignment[:8].lower() in (await dialog.inner_text()).lower()
            await page.keyboard.press('Escape')
            assert page.url==config_url
            assert await page.locator('[data-scheduling-review]').evaluate('el=>el===document.activeElement')
            await page.locator('[data-scheduling-review]').click()
            await dialog.get_by_role('button',name='Volver',exact=True).click()
            assert sum(method=='POST' and path=='/api/runs' for method,path in requests)==before_review
            await page.locator('[data-scheduling-window-mode=custom]').click()
            await page.locator('[data-scheduling-window-start]').fill('2026-09-01')
            await page.locator('[data-scheduling-window-start]').dispatch_event('change')
            await page.locator('[data-scheduling-window-end]').fill('2026-09-02')
            await page.locator('[data-scheduling-window-end]').dispatch_event('change')
            await page.locator('[data-scheduling-review]').click()
            async with page.expect_response(lambda response:
                urlparse(response.url).path=='/api/runs' and response.request.method=='POST') as failed_admission:
                await page.locator('[data-scheduling-execute]').click()
            assert (await failed_admission.value).status==202
            failed_scheduling=(await (await failed_admission.value).json())['id']
            await page.locator('[data-run-terminal-error]').wait_for(state='visible')
            await ui.checkpoint('scheduling-error')
            failed_snapshot=await (await context.request.get(base+'/api/runs/'+failed_scheduling)).json()
            assert failed_snapshot['status']=='error' and failed_snapshot['upstream_run_id']==assignment
            await page.locator('[data-reconfigure-run]').click()
            await page.locator('[data-scheduling-review]').wait_for(state='visible')
            assert await page.locator('[data-scheduling-window-start]').input_value()=='2026-09-01'
            assert await page.locator('[data-scheduling-window-end]').input_value()=='2026-09-02'
            assert 'run_id=' not in page.url and 'case_id='+case in page.url
            await page.locator('[data-scheduling-window-mode=auto]').click()
            await ui.checkpoint('scheduling-reconfigured')
            await page.locator('[data-scheduling-review]').click()
            async with page.expect_response(lambda response:
                urlparse(response.url).path=='/api/runs' and response.request.method=='POST') as accepted:
                await page.locator('[data-scheduling-execute]').click()
            assert (await accepted.value).status==202
            scheduling=(await (await accepted.value).json())['id']
            assert scheduling!=failed_scheduling
            await page.wait_for_selector('.dispatch-scheduling-dashboard')
            await ui.toolbar('scheduling')
            await ui.checkpoint('scheduling-dashboard')
            await page.locator('[data-approve-toolbar]').click()
            await page.wait_for_function("window.DationDispatch.getWorkspace().decisionCase.nodes.logistics_scheduling.status==='approved'")
            await ui.checkpoint('scheduling-approved')
            # Cold access in a new tab has no workspace sessionStorage.
            cold=await context.new_page()
            await cold.goto(base+'/app?view=decision-dashboard&case_id='+case+
                '&node_id=logistics_scheduling&run_id='+scheduling,wait_until='domcontentloaded')
            await cold.wait_for_selector('.dispatch-scheduling-dashboard')
            assert await cold.evaluate("window.DationDispatch.getWorkspace().decisionCase.nodes.logistics_assignment.approved_run_id")==assignment
            await cold.close()
            assert await (await context.request.get(base+'/api/runs/'+failed_scheduling)).json()==failed_snapshot
            await page.locator('[data-dashboard-map]').click()
            await page.wait_for_selector('[data-map-node="logistics_assignment"]')
            assert await page.get_by_role('progressbar',name='Decisiones aprobadas',exact=True).get_attribute('aria-valuenow')=='2'
            await ui.checkpoint('map-completed')
            await page.wait_for_timeout(500)
            before=sum(path.startswith('/api/') for _,path in requests)
            await page.wait_for_timeout(1200)
            assert sum(path.startswith('/api/') for _,path in requests)==before, 'Idle map keeps fetching.'
            await page.set_viewport_size({'width':390,'height':844})
            await page.evaluate("window.DationDispatch.openRunHistory('logistics_scheduling')")
            await page.wait_for_selector('[data-history-range]')
            assert await page.locator('[data-history-range]').inner_text()=='1–2 de 2'
            assert 'Aprobación · acceso compartido' in await page.locator('.dispatch-run-history__list').inner_text()
            assert not await page.evaluate('document.documentElement.scrollWidth>innerWidth')
            await page.locator('[data-close]').click()
            await page.evaluate("id=>window.DationDispatch.openRun(id,'logistics_assignment')",assignment)
            await page.wait_for_selector('.assignment-dashboard-v2')
            await page.locator('[data-export-menu] summary').click()
            async with page.expect_download() as downloaded:await page.locator('[data-export-csv]').click()
            download=await downloaded.value
            contents=Path(await download.path()).read_text()
            assert contents and len(contents.splitlines())>=2
            retained_case=await (await context.request.get(base+'/api/decision-cases/'+case)).json()
            runs_before=sum(method=='POST' and path=='/api/runs' for method,path in requests)
            await page.evaluate("window.dationNavigate('logistics-overview')")
            await page.wait_for_selector('[data-start-new-decision]')
            assert not await page.locator('[data-open-decision-map]').is_disabled()
            await page.locator('[data-open-decision-map]').click()
            await page.wait_for_selector('[data-map-node="logistics_assignment"]')
            assert await page.locator('.dispatch-case-selector').count()==0
            await page.evaluate("window.dationNavigate('logistics-overview')")
            await page.locator('[data-start-new-decision]').click()
            await page.wait_for_selector('[data-kind="orders"] input[type=file]',state='attached')
            workspace=await page.evaluate('window.DationDispatch.getWorkspace()')
            assert all(workspace[key] is None for key in ('orders','decisionCase','run','activeNode'))
            assert 'case_id=' not in page.url
            assert sum(method=='POST' and path=='/api/runs' for method,path in requests)==runs_before
            assert await (await context.request.get(base+'/api/decision-cases/'+case)).json()==retained_case
            assert case in await page.evaluate("JSON.parse(sessionStorage.getItem('dation.dispatch.drafts.v1'))")
            await ui.checkpoint('new-decision-after-mobile-history')
            assert not errors
            assert not failed,failed
            report={'passed':True,'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[3],text=True).strip(),
                'ui':ui.report(),'inicio_to_overview':True,'approval_map_scheduling_configuration':True,
                'disabled_upload_action_and_hover':True,'shared_workflow_visual_contract':True,
                'review_keyboard_cancel_and_confirmation':True,'creation_from_files':True,'refresh_during_queue':True,
                'assignment_and_scheduling_approved':True,'cold_link':True,'back_forward_refresh':True,
                'idle_request_budget':True,'mobile_history':True,'export_has_records':True,
                'comparative_reused_and_restored':True,'trip_detail_keyboard':True,'direct_next_configuration':True,
                'comparative_close_reopen_without_post':True,'terminal_scheduling_reconfigured_as_new_run':True,
                'failed_run_retained_unchanged':True,'map_toolbar_and_closed_contexts':True,
                'overview_dual_cta_without_cases':True,'overview_single_case_direct_map':True,
                'new_decision_clears_context_and_preserves_history':True,
                'javascript_errors':errors,'unexpected_http_errors':failed,
                'expected_draft_hydration_misses':len(expected_draft_misses),'requests':len(requests)}
            if artifact:
                Path(artifact).mkdir(parents=True,exist_ok=True)
                (Path(artifact)/'browser-report.json').write_text(json.dumps(report,indent=2))
            print(json.dumps(report))
        except BaseException:
            if artifact:
                Path(artifact).mkdir(parents=True,exist_ok=True)
                await page.screenshot(path=str(Path(artifact)/'browser-failure.png'),full_page=True)
                (Path(artifact)/'browser-failure.json').write_text(json.dumps({'errors':errors,'failed_requests':failed,'url':page.url},indent=2))
            raise
        finally:
            gate.unlink(missing_ok=True)
            await context.tracing.stop(path=str(Path(artifact)/'browser-trace.zip') if artifact else None)
            await browser.close()


asyncio.run(journey())
