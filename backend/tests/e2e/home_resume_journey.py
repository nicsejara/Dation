"""Home opens the official result; explicit review retains the replacement run."""
import asyncio,json,os
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from playwright.async_api import async_playwright
BASE=os.environ['DATION_E2E_URL'];assert urlsplit(BASE).hostname=='127.0.0.1'
CASE=os.environ['DATION_HOME_CASE'];OFFICIAL=os.environ['DATION_HOME_OFFICIAL'];CANDIDATE=os.environ['DATION_HOME_CANDIDATE']
async def main():
 errors=[];theme=(Path(__file__).parents[1]/'browser/theme_audit.js').read_text();artifact=Path(os.environ['DATION_E2E_ARTIFACTS'])/'home-v2' if os.getenv('DATION_E2E_ARTIFACTS') else None
 if artifact:artifact.mkdir(parents=True,exist_ok=True)
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  context=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=await context.new_page();page.set_default_timeout(15000);page.on('pageerror',lambda error:errors.append(str(error)))
  await page.goto(BASE+'/login');await page.get_by_label('Email',exact=True).fill('user-1@example.test');await page.get_by_label('Contraseña',exact=True).fill('dispatch-e2e-private');await page.get_by_role('button',name='Ingresar',exact=True).click()
  home=page.locator('[data-platform-home]');await home.locator('.platform-home__case').first.wait_for()
  assert await home.locator('.platform-home__case').count()==3;assert await home.locator('.platform-home__hero-actions a').count()==2
  assert await home.locator('[data-onboarding-step],.d-onboarding').count()==0
  assert await home.locator('.platform-activity__event').count()<=5
  for width in (1440,1280,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');audit=await page.evaluate(theme);assert not audit['overflow'] and not audit['failures'],audit
   if artifact:await page.screenshot(path=str(artifact/f'home-{width}.png'),full_page=True)
  await page.set_viewport_size({'width':1440,'height':1000})
  await home.get_by_role('link',name='Continuar DC-'+CASE[:8].upper(),exact=True).click();await page.locator('.assignment-dashboard-v2').wait_for();assert parse_qs(urlsplit(page.url).query)['run_id']==[OFFICIAL]
  await page.go_back();await home.get_by_role('link',name='Revisar Asignación de carga · DC-'+CASE[:8].upper(),exact=True).click();await page.locator('.assignment-dashboard-v2').wait_for();query=parse_qs(urlsplit(page.url).query);assert query['run_id']==[CANDIDATE] and query['case_id']==[CASE] and query['node_id']==['logistics_assignment']
  await page.go_back();await page.reload();await home.locator('.platform-home__case').first.wait_for();assert 'run_id=' not in page.url
  await home.get_by_role('link',name='Ir a Decision Center',exact=True).click();await page.locator('[data-platform-decisions]').get_by_role('heading',name='Decision Center',exact=True).wait_for();assert urlsplit(page.url).path=='/app/decisions'
  assert not errors,errors;await browser.close()
 print(json.dumps({'passed':True,'official_resume':True,'exact_candidate_review':True,'history_reload':True,'responsive_viewports':5,'no_global_demo':True}))
asyncio.run(main())
