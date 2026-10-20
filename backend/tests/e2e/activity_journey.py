"""Actual BFF/DB activity, scoped case pagination, export and responsive disclosure."""
import asyncio,json,os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
BASE=os.environ['DATION_E2E_URL'];assert urlsplit(BASE).hostname=='127.0.0.1'
CASE=os.environ['DATION_ACTIVITY_CASE'];RUN=os.environ['DATION_ACTIVITY_RUN']
async def main():
 artifacts=Path(os.environ['DATION_E2E_ARTIFACTS'])/'activity' if os.getenv('DATION_E2E_ARTIFACTS') else None
 if artifacts:artifacts.mkdir(parents=True,exist_ok=True)
 theme=(Path(__file__).parents[1]/'browser/theme_audit.js').read_text();errors=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  context=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=await context.new_page();page.set_default_timeout(15000);page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(BASE+'/login');await page.get_by_label('Email',exact=True).fill('user-1@example.test');await page.get_by_label('Contraseña',exact=True).fill('dispatch-e2e-private');await page.get_by_role('button',name='Ingresar',exact=True).click()
  home=page.locator('[data-platform-home]');await home.locator('.platform-activity__event').first.wait_for();assert await home.locator('.platform-activity__event').count()==5
  assert await home.locator('.platform-activity__event img').count()==0;assert '<img' in await home.locator('.platform-activity__event').first.inner_text();assert await page.evaluate('window.__bad===undefined')
  for width in (1440,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');audit=await page.evaluate(theme);audit['width']=width
   if audit['overflow']:audit['outside']=await page.evaluate("[...document.querySelectorAll('body *')].filter(n=>n.getClientRects().length&&n.getBoundingClientRect().right>innerWidth+1).slice(0,20).map(n=>({tag:n.tagName,cls:n.className,right:n.getBoundingClientRect().right,width:n.getBoundingClientRect().width}))")
   assert not audit['overflow'] and not audit['failures'],audit
   if artifacts:await page.screenshot(path=str(artifacts/f'home-{width}.png'),full_page=True)
  await home.get_by_role('link',name='Ver caso',exact=True).first.click();root=page.locator('[data-platform-decisions]');await root.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for();assert 'center_case_id='+CASE in page.url
  panel=root.locator('[data-case-activity]');await panel.locator('.platform-activity__event').first.wait_for();assert await panel.locator('.platform-activity__event').count()==5;await panel.get_by_role('button',name='Ver toda la actividad',exact=True).click();await page.wait_for_function("document.querySelectorAll('[data-case-activity] [data-activity-id]').length===10")
  await panel.get_by_role('button',name='Ver más actividad',exact=True).click();await page.wait_for_function("document.querySelectorAll('[data-case-activity] [data-activity-id]').length>10")
  ids=await panel.locator('[data-activity-id]').evaluate_all('nodes=>nodes.map(n=>n.dataset.activityId)');assert len(ids)==len(set(ids))
  await panel.get_by_text('Detalles del evento',exact=True).first.click();assert await panel.locator('pre').first.is_visible()
  for width in (1440,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');audit=await page.evaluate(theme);audit['width']=width
   if audit['overflow']:audit['outside']=await page.evaluate("[...document.querySelectorAll('body *')].filter(n=>n.getClientRects().length&&n.getBoundingClientRect().right>innerWidth+1).slice(0,20).map(n=>({tag:n.tagName,cls:n.className,right:n.getBoundingClientRect().right,width:n.getBoundingClientRect().width}))")
   assert not audit['overflow'] and not audit['failures'],audit
   if artifacts:await page.screenshot(path=str(artifacts/f'case-{width}.png'),full_page=True)
  failed=False
  async def fail_once(route):
   nonlocal failed
   if not failed:failed=True;await route.fulfill(status=503,content_type='application/json',body='{"detail":"Network fault"}')
   else:await route.continue_()
  await context.route('**/api/platform/activity?**',fail_once)
  await panel.get_by_role('button',name='Ver toda la actividad',exact=True).click();await panel.get_by_role('button',name='Reintentar actividad',exact=True).click();await panel.locator('.platform-activity__event').first.wait_for();assert failed
  await page.evaluate("p=>window.DationDispatch.openRun(p.run,'logistics_assignment',p.case)",{'run':RUN,'case':CASE});await page.locator('.assignment-dashboard-v2').wait_for()
  for format in ('csv','json'):
   await page.locator('[data-export-menu] summary').click()
   async with page.expect_download() as output:await page.locator('[data-export-'+format+']').click()
   download=await output.value;data=Path(await download.path()).read_bytes();assert data
   assert download.suggested_filename==('assignment-recomendada.csv' if format=='csv' else 'dation-'+RUN[:8]+'.json')
  await page.locator('.nav [data-platform-view=platform-home]').click();await home.locator('.platform-activity__event').first.wait_for();assert 'generó una exportación de Assignment' in await home.locator('.platform-activity__event').first.inner_text()
  assert errors==[],errors;await browser.close()
 print(json.dumps({'passed':True,'real_activity':True,'keyset_pagination':True,'retry':True,'csv_json_audited':True,'xss_safe':True,'visual_states':8}))
asyncio.run(main())
