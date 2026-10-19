"""D2 presentation against actual API/worker evidence; no API interception."""
import asyncio,csv,io,json,os
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from browser_auth import authenticate, api_get

MANIFEST=Path(os.environ['DATION_E2E_SCHEDULING']);DATA=json.loads(MANIFEST.read_text());BASE=os.environ['DATION_E2E_URL']
assert urlparse(BASE).hostname=='127.0.0.1'
async def main():
    errors=[];writes=[];states=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        context=await browser.new_context(reduced_motion='reduce')
        await authenticate(context,BASE)
        page=await context.new_page();page.set_default_timeout(20000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:writes.append((r.method,urlparse(r.url).path)) if r.method!='GET' and '/api/' in r.url else None)
        url=BASE+'/app?view=decision-dashboard&case_id='+DATA['case_id']+'&node_id=logistics_scheduling&run_id='+DATA['run']['id']
        for width,height in [(1440,1000),(768,1024),(390,844)]:
            await page.set_viewport_size({'width':width,'height':height});await page.goto(url)
            await page.locator('.scheduling-timeline-chart svg').wait_for()
            current=await page.evaluate('window.DationDispatch.getWorkspace().run')
            assert current['result_fingerprint']==DATA['run']['result_fingerprint']
            metrics=DATA['run']['result_json']['scenarios']['selected']['metrics']
            kpis=await page.locator('[data-scheduling-kpi]>strong').all_text_contents()
            expected=await page.evaluate('''m=>{const n=x=>new Intl.NumberFormat('es-AR',{maximumFractionDigits:2}).format(x);return [n(m.on_time_rate*100)+' %',n(m.makespan_days)+' días',n(m.avg_wait_days)+' días'];}''',metrics)
            assert kpis[:3]==expected,(kpis,expected)
            assert kpis[3]==DATA['critical_resource']
            assert await page.locator('#scheduling-preview tbody tr').count()==min(5,metrics['total_trips'])
            toggle=page.locator('[data-scheduling-advanced-toggle]')
            for opened in (False,True):
                if await toggle.get_attribute('aria-expanded')!=str(opened).lower():await toggle.click()
                assert not await page.evaluate('document.documentElement.scrollWidth>innerWidth')
                if opened:
                    assert await page.locator('#scheduling-full-plan tbody tr').count()==metrics['total_trips']
                    outcomes=DATA['run']['result_json']['scenarios']['selected']['order_outcomes']
                    assert await page.locator('#scheduling-service tbody tr').count()==len(outcomes)
                    for order in outcomes:
                        row=page.locator('#scheduling-service tbody tr').filter(has=page.get_by_role('rowheader',name=order['order_id'],exact=True))
                        assert await row.count()==1
                        text=await row.inner_text()
                        assert ('Fuera de fecha' in text)==(order['on_time'] is False)
                if artifacts:=os.getenv('DATION_E2E_ARTIFACTS'):
                    folder=Path(artifacts);folder.mkdir(parents=True,exist_ok=True)
                    await page.screenshot(path=str(folder/f'd2-{width}-{"open" if opened else "closed"}.png'),full_page=True)
                states.append({'width':width,'advanced':opened,'passed':True})
            await page.locator('[data-scheduling-full-plan]').click()
            await page.wait_for_function("document.activeElement?.id==='scheduling-full-plan'")
            await page.reload();await toggle.wait_for();assert await toggle.get_attribute('aria-expanded')=='true'
        await page.locator('[data-export-menu] summary').click()
        async with page.expect_download() as downloaded:await page.locator('[data-export-csv]').click()
        download=await downloaded.value;path=MANIFEST.with_name('d2-export.csv');await download.save_as(path)
        rows=list(csv.reader(io.StringIO(path.read_text(encoding='utf-8-sig')),delimiter=';'))
        assert 'Recurso disponible' in rows[0] and {t['trip_id'] for t in DATA['run']['result_json']['scenarios']['selected']['trips']}=={r[0] for r in rows[1:]}
        assert all(path=='/api/platform/activity/exports' for _,path in writes) and not errors,(writes,errors)
        await page.locator('[data-approve-final]').click()
        await page.wait_for_function("window.DationDispatch.getWorkspace().decisionCase.nodes.logistics_scheduling.status==='approved'")
        assert await page.locator('[data-approve-final]').is_disabled()
        assert all(path.endswith('/approve') or path in ('/api/runs/preflight','/api/platform/activity/exports') for _,path in writes),writes
        assert sum(path.endswith('/approve') for _,path in writes)==1,writes
        persisted=await (await api_get(context,BASE+'/api/runs/'+DATA['run']['id'])).json()
        assert persisted['approved_at'] and persisted['result_fingerprint']==DATA['run']['result_fingerprint']
        await page.locator('[data-more-menu] summary').click();await page.locator('[data-dashboard-map]').click()
        await page.locator('[data-map-node=logistics_scheduling][data-map-action=open-result]').first.wait_for()
        await browser.close()
    report={'passed':True,'states':states,'javascript_errors':errors,'writes':writes,'dataset':'QA temporal reproducible (no Golden Pallets v2)','assignment_frozen':True,'source_sha':DATA['source_sha']}
    MANIFEST.with_name('scheduling-dashboard-browser-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
asyncio.run(main())
