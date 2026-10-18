"""All five D1 objectives from actual API/worker results, without API interception."""
import asyncio,json,os
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from browser_auth import authenticate
A=Path(os.environ['DATION_E2E_MATRIX']);matrix=json.loads(A.read_text());BASE=os.environ['DATION_E2E_URL']
assert urlparse(BASE).hostname=='127.0.0.1'
async def main():
 errors=[];writes=[];results=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  context=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
  await authenticate(context,BASE)
  page=await context.new_page();page.set_default_timeout(30000)
  page.on('pageerror',lambda error:errors.append(str(error)))
  page.on('request',lambda request:writes.append((request.method,urlparse(request.url).path)) if request.method!='GET' and '/api/' in request.url else None)
  for run in matrix['runs']:
   await page.goto(BASE+'/app?view=decision-dashboard&case_id='+matrix['case_id']+'&node_id=logistics_assignment&run_id='+run['id'])
   await page.locator('#dispatch-hero h1').wait_for()
   assert await page.locator('#dispatch-hero h1').inner_text()=='Asignación recomendada'
   assert not await page.locator('#dispatch-assignment').is_visible()
   assert not await page.locator('[data-ai-summary-body]').is_visible()
   current=await page.evaluate('window.DationDispatch.getWorkspace().run')
   assert current['id']==run['id'] and current['result_json']['scenarios']['selected']['plan_fingerprint']==run['plan_fingerprint']
   assert current['result_json']['scenarios']['selected']['metrics']==run['metrics']
   selected=page.locator('#assignment-scenarios [aria-current=true]');assert await selected.count()==1
   assert await selected.get_attribute('data-scenario-row')==run['objective']
   assert await page.locator('#assignment-preview tbody tr').count()==min(5,len(run['trips']))
   expected=await page.evaluate('()=>{const m=window.DationDispatch.getWorkspace().run.result_json.scenarios.selected.metrics;return {cost:"$ "+new Intl.NumberFormat("es-AR",{maximumFractionDigits:2}).format(m.total_cost),own:new Intl.NumberFormat("es-AR",{maximumFractionDigits:1}).format(m.own_weight_share*100)+" %"};}')
   assert await page.locator('[data-executive-kpi=total_cost]>strong').inner_text()==expected['cost']
   actual_own=await page.locator('[data-executive-kpi=own_weight_share]>strong').inner_text()
   assert actual_own==expected['own'],(run['objective'],actual_own,expected['own'],run['metrics'])
   url=page.url;await page.locator('[data-assignment-advanced-toggle]').click()
   await page.locator('.assignment-frontier__chart svg').wait_for()
   assert await page.locator('[data-comparison-kpi]').count()==6
   assert await page.locator('[data-assignment-corridors] tbody tr').count()>0
   assert page.url==url
   await page.locator('[data-assignment-advanced-toggle]').click()
   assert not await page.locator('#dispatch-assignment').is_visible()
   assert await page.evaluate('window.DationDispatch.getWorkspace().run.result_json.scenarios.selected.plan_fingerprint')==run['plan_fingerprint']
   assert not await page.evaluate('document.documentElement.scrollWidth>innerWidth')
   results.append({'objective':run['objective'],'run_id':run['id'],'selected_fingerprint':run['plan_fingerprint'],'own_weight_share':run['metrics']['own_weight_share'],'passed':True})
  assert not errors and not writes,(errors,writes)
  await browser.close()
 report={'passed':True,'objectives':results,'errors':errors,'writes_from_browser':writes,'dataset':'reproducible V3 QA: 4 orders, 3 resources; not Golden Pallets v2'}
 A.with_name('assignment-matrix-browser-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
asyncio.run(main())
