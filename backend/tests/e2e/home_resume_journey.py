"""Home stays exploratory; Center preserves official and explicit candidate results."""
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
  home=page.locator('[data-platform-home]');await home.get_by_role('heading',name='Accesos rápidos',exact=True).wait_for()
  assert await home.locator('.platform-home__case,.platform-home__attention,.platform-activity').count()==0
  assert await home.locator('.platform-home__quick-link').count()==4
  assert await home.locator('[data-onboarding-step],.d-onboarding').count()==0
  for width in (1440,1280,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');audit=await page.evaluate(theme);assert not audit['overflow'] and not audit['failures'],audit
   if artifact:await page.screenshot(path=str(artifact/f'home-{width}.png'),full_page=True)
  await page.set_viewport_size({'width':1440,'height':1000})
  await home.get_by_role('link',name='Ir a Decision Center',exact=True).click()
  center=page.locator('[data-platform-decisions]');await center.locator('[data-case-open="'+CASE+'"]').click()
  node=center.locator('[data-center-node=logistics_assignment]')
  await node.locator('summary',has_text='Responsables y aprobación').click()
  assert await node.get_by_role('link',name='Abrir dashboard aprobado',exact=True).count()==0
  await node.locator('summary',has_text='Historial de corridas').click()
  previous=node.locator('.center-run').filter(has=page.get_by_role('link',name='RUN-'+OFFICIAL[:8],exact=True))
  await previous.wait_for();assert 'Reemplazada' in await previous.inner_text()
  await previous.get_by_role('link',name='RUN-'+OFFICIAL[:8],exact=True).click()
  await page.locator('.assignment-dashboard-v2').wait_for();assert parse_qs(urlsplit(page.url).query)['run_id']==[OFFICIAL]
  await page.go_back();await node.locator('summary',has_text='Responsables y aprobación').click()
  await node.get_by_role('link',name='Abrir último dashboard',exact=True).click()
  await page.locator('.assignment-dashboard-v2').wait_for();query=parse_qs(urlsplit(page.url).query)
  assert query['run_id']==[CANDIDATE] and query['case_id']==[CASE] and query['node_id']==['logistics_assignment']
  await page.go_back();await center.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
  await center.get_by_role('button',name='Cerrar detalle del caso',exact=True).click()
  await center.locator('.center-hero').get_by_role('button',name='Explorar DDA',exact=True).click()
  await home.get_by_role('heading',name='Accesos rápidos',exact=True).wait_for()
  assert await page.evaluate('document.activeElement.id')=='dation-dda-title'
  await page.reload();await home.get_by_role('heading',name='Accesos rápidos',exact=True).wait_for()
  assert 'run_id=' not in page.url and await home.locator('.platform-home__case').count()==0
  assert not errors,errors;await browser.close()
 print(json.dumps({'passed':True,'official_resume':True,'exact_candidate_review':True,'history_reload':True,'responsive_viewports':5,'no_global_demo':True}))
asyncio.run(main())
