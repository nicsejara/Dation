"""Real Chromium journey. No API responses, runs or SQL are mocked."""
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright


async def journey():
    base=os.environ['DATION_E2E_URL']
    assert urlparse(base).hostname=='127.0.0.1', 'E2E must use its owned loopback API.'
    inputs=Path(os.environ['DATION_E2E_INPUTS'])
    gate=Path(os.environ['DATION_E2E_STORAGE'])/'block-downloads'
    errors,requests,failed,expected_draft_misses=[],[],[],[]
    admitted=False
    artifact=os.getenv('DATION_E2E_ARTIFACTS')
    async with async_playwright() as pw:
        executable=os.getenv('CHROMIUM_EXECUTABLE')
        if not executable and Path('/usr/bin/chromium').exists():executable='/usr/bin/chromium'
        browser=await pw.chromium.launch(executable_path=executable,headless=True,
            args=['--no-sandbox','--disable-dev-shm-usage'])
        context=await browser.new_context(http_credentials={'username':'dation','password':os.environ['DATION_ACCESS_PASSWORD']},
            viewport={'width':1440,'height':1000},accept_downloads=True)
        await context.tracing.start(screenshots=True,snapshots=True,sources=True)
        page=await context.new_page();page.set_default_timeout(30000)
        def response_seen(response):
            path=urlparse(response.url).path
            if path.startswith('/api/') and response.status>=400:
                # The case remains a session draft until its first run is admitted.
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
        try:
            await page.goto(base+'/app?view=logistics-data',wait_until='domcontentloaded')
            await page.wait_for_selector('[data-kind="orders"] input[type=file]',state='attached')
            for kind in ('orders','fleet'):
                async with page.expect_response(lambda response:
                    urlparse(response.url).path=='/api/datasets/upload' and response.request.method=='POST') as upload:
                    await page.locator('[data-kind="'+kind+'"] input[type=file]').set_input_files(inputs/(kind+'.csv'))
                assert (await upload.value).status==200
            await page.locator('.dispatch-pro-next-button').click()
            await page.wait_for_selector('[data-map-node="logistics_assignment"][data-map-action]')
            await page.locator('[data-map-node="logistics_assignment"][data-map-action]').first.click()
            await page.wait_for_selector('[data-config-review]')
            await page.locator('[data-depth="essential"]').click()
            for select in await page.locator('[data-config-anomaly]').all():await select.select_option('include')
            await page.locator('[data-config-review]').click()
            gate.touch()
            async with page.expect_response(lambda response:
                urlparse(response.url).path=='/api/runs' and response.request.method=='POST') as accepted:
                await page.locator('[data-config-execute]').click()
            response=await accepted.value
            assert response.status==202
            admitted=True
            assignment=(await response.json())['id']
            case=(await response.json())['decision_case_id']
            await page.reload(wait_until='domcontentloaded')
            assert parse_qs(urlparse(page.url).query)['run_id']==[assignment]
            pending=await context.request.get(base+'/api/runs/'+assignment)
            assert (await pending.json())['status'] in ('queued','running')
            gate.unlink()
            await page.wait_for_selector('.assignment-dashboard-v2')
            assert await page.locator('[data-trip-detail]').count()==0
            await page.locator('[data-trip-detail-button]').first.click()
            assert await page.locator('[data-trip-detail]').count()==1
            await page.keyboard.press('Escape')
            assert await page.locator('[data-trip-detail]').count()==0
            await page.locator('[data-generate-comparative]').click()
            await page.wait_for_selector('[data-comparative-state=completed]')
            await page.reload(wait_until='domcontentloaded')
            await page.wait_for_selector('[data-comparative-state=completed]')
            assert await page.locator('[data-generate-comparative]').count()==0
            await page.locator('[data-approve]').click()
            await page.wait_for_function("window.DationDispatch.getWorkspace().decisionCase.nodes.logistics_assignment.status==='approved'")
            await page.locator('[data-after-approve]').click()
            await page.wait_for_selector('[data-scheduling-review]')
            assert 'run_id=' not in page.url
            await page.go_back();await page.wait_for_selector('.assignment-dashboard-v2')
            await page.go_forward();await page.wait_for_selector('[data-scheduling-review]')
            await page.reload(wait_until='domcontentloaded');await page.wait_for_selector('[data-scheduling-review]')
            await page.locator('[data-scheduling-review]').click()
            async with page.expect_response(lambda response:
                urlparse(response.url).path=='/api/runs' and response.request.method=='POST') as accepted:
                await page.locator('[data-scheduling-execute]').click()
            assert (await accepted.value).status==202
            scheduling=(await (await accepted.value).json())['id']
            await page.wait_for_selector('.dispatch-scheduling-dashboard')
            await page.locator('[data-approve]').click()
            await page.wait_for_function("window.DationDispatch.getWorkspace().decisionCase.nodes.logistics_scheduling.status==='approved'")
            # Cold access in a new tab has no workspace sessionStorage.
            cold=await context.new_page()
            await cold.goto(base+'/app?view=decision-dashboard&case_id='+case+
                '&node_id=logistics_scheduling&run_id='+scheduling,wait_until='domcontentloaded')
            await cold.wait_for_selector('.dispatch-scheduling-dashboard')
            assert await cold.evaluate("window.DationDispatch.getWorkspace().decisionCase.nodes.logistics_assignment.approved_run_id")==assignment
            await cold.close()
            await page.evaluate("window.dationNavigate('logistics-map')")
            await page.wait_for_selector('[data-map-node="logistics_assignment"]')
            await page.wait_for_timeout(500)
            before=sum(path.startswith('/api/') for _,path in requests)
            await page.wait_for_timeout(1200)
            assert sum(path.startswith('/api/') for _,path in requests)==before, 'Idle map keeps fetching.'
            await page.set_viewport_size({'width':390,'height':844})
            await page.evaluate("window.DationDispatch.openRunHistory('logistics_scheduling')")
            await page.wait_for_selector('[data-history-range]')
            assert await page.locator('[data-history-range]').inner_text()=='1–1 de 1'
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
            assert not errors
            assert not failed,failed
            report={'passed':True,'creation_from_files':True,'refresh_during_queue':True,
                'assignment_and_scheduling_approved':True,'cold_link':True,'back_forward_refresh':True,
                'idle_request_budget':True,'mobile_history':True,'export_has_records':True,
                'comparative_reused_and_restored':True,'trip_detail_keyboard':True,'direct_next_configuration':True,
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
