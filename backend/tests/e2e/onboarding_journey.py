"""Real first-run UI and controlled demo; faults only intercept owned local traffic."""
import asyncio,json,os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
BASE=os.environ['DATION_E2E_URL'];assert urlsplit(BASE).hostname=='127.0.0.1'

async def main():
 artifacts=Path(os.environ['DATION_E2E_ARTIFACTS'])/'onboarding' if os.getenv('DATION_E2E_ARTIFACTS') else None
 if artifacts:artifacts.mkdir(parents=True,exist_ok=True)
 theme=(Path(__file__).parents[1]/'browser/theme_audit.js').read_text();errors=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  context=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=await context.new_page();page.set_default_timeout(15000);page.on('pageerror',lambda error:errors.append(str(error)))
  await page.goto(BASE+'/login');await page.get_by_label('Email',exact=True).fill('user-2@example.test');await page.get_by_label('Contraseña',exact=True).fill('dispatch-e2e-private');await page.get_by_role('button',name='Ingresar',exact=True).click()
  home=page.locator('[data-platform-home]');await home.get_by_role('heading',name='Accesos rápidos').wait_for();assert await home.locator('[data-onboarding-step],.d-onboarding').count()==0;assert await home.locator('.platform-home__hero-actions a').count()==2;assert await home.get_by_role('button',name='Usar datos de ejemplo',exact=True).count()==0
  for width in (1440,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');audit=await page.evaluate(theme);assert not audit['overflow'] and not audit['failures'],audit
   if artifacts:await page.screenshot(path=str(artifacts/f'welcome-{width}.png'),full_page=True)
  await page.set_viewport_size({'width':1440,'height':1000});await page.locator('.nav [data-platform-view=platform-team]').click();await page.locator('[data-team-empty]').get_by_role('heading',name='Tu equipo empieza con vos',exact=True).wait_for();assert await page.locator('[data-platform-team]').get_by_role('button',name='Invitar',exact=True).count()==1;assert await page.locator('[data-team-empty] button').count()==0
  await page.locator('.nav [data-platform-view=platform-decisions]').click();center=page.locator('[data-platform-decisions]');await center.get_by_role('heading',name='Todavía no hay decisiones en este Workspace.',exact=True).wait_for()
  await center.locator('.center-empty').get_by_role('button',name='Explorar DDA',exact=True).click()
  await home.get_by_role('heading',name='Accesos rápidos',exact=True).wait_for();assert urlsplit(page.url).path=='/app'
  progress=await page.evaluate("async()=>{const {api}=await import('/static/js/dispatch/shared.mjs');return await api('/api/platform/onboarding');}");assert not progress['explored_at']
  await page.locator('.nav [data-platform-view=platform-data]').click()
  hub=page.locator('[data-platform-data]');await hub.get_by_role('heading',name='Todavía no hay datos en este Workspace.',exact=True).wait_for();assert await hub.get_by_role('button',name='Usar datos de ejemplo',exact=True).count()==0
  failed=False
  async def offline_once(route):
   nonlocal failed
   if not failed:failed=True;await route.abort('internetdisconnected')
   else:await route.continue_()
  await context.route('**/api/platform/data/datasets?**',offline_once)
  await page.locator('.nav [data-platform-view=platform-home]').click();await page.locator('.nav [data-platform-view=platform-data]').click();await hub.get_by_text('Revisá tu conexión y reintentá. Los datos ya guardados se conservan.',exact=True).wait_for();await hub.get_by_role('button',name='Reintentar',exact=True).click();await hub.get_by_role('heading',name='Todavía no hay datos en este Workspace.',exact=True).wait_for()
  await hub.get_by_role('button',name='Explorar DDA',exact=True).first.click()
  async with page.expect_response(lambda response:'/api/platform/onboarding/explore' in response.url and response.status==200):
   await page.locator('#home-open-logistics').click()
  progress=await page.evaluate("async()=>{const {api}=await import('/static/js/dispatch/shared.mjs');return await api('/api/platform/onboarding');}");explored_at=progress['explored_at'];assert explored_at
  caps=await page.evaluate("async()=>{const {api}=await import('/static/js/dispatch/shared.mjs');return await api('/api/platform/ultimate-foundation/capabilities');}")
  assert not caps['can_create_case']
  await page.locator('[data-start-new-decision][disabled]').wait_for()
  assert await page.locator('input[type=file]').count()==0
  # Seed the supported demo API as fixture data; new planning never opens
  # the retired upload-first surface or silently converts legacy CSV schemas.
  demo=await page.evaluate("async()=>{const {post}=await import('/static/js/dispatch/shared.mjs');return await post('/api/platform/onboarding/demo',{});}")
  assert demo['contains_demo_data']
  await page.locator('.nav [data-platform-view=platform-home]').click();await home.get_by_role('heading',name='Accesos rápidos').wait_for();assert await home.locator('[data-onboarding-step]').count()==0
  await home.get_by_role('link',name='Explorar DDA',exact=True).click();assert urlsplit(page.url).path=='/app';assert await page.evaluate('document.activeElement.id')=='dation-dda-title'
  await page.locator('.nav [data-platform-view=platform-home]').click();await page.reload();await home.get_by_role('heading',name='Accesos rápidos').wait_for();assert await home.locator('.d-onboarding').count()==0
  progress=await page.evaluate("async()=>{const {api}=await import('/static/js/dispatch/shared.mjs');return await api('/api/platform/onboarding');}");assert progress['explored_at']==explored_at and progress['data_ready'] and not progress['first_decision_completed']
  await page.locator('.nav [data-platform-view=platform-data]').click();await hub.locator('.d-demo-badge').first.wait_for();assert await hub.locator('.d-demo-badge').count()==2
  for width in (1440,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');audit=await page.evaluate(theme);assert not audit['overflow'] and not audit['failures'],audit
   if artifacts:await page.screenshot(path=str(artifacts/f'demo-library-{width}.png'),full_page=True)
  assert not errors,errors;await browser.close()
 print(json.dumps({'passed':True,'first_run':True,'personal_progress_persists':True,'real_demo_data':True,'empty_team':True,'offline_retry':True,'visual_states':8}))
asyncio.run(main())
