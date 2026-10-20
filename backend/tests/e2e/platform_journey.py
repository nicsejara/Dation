"""Phase 3 browser gate: real login/Bearer, global navigation, profile and logout."""
import asyncio,json,os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
BASE=os.environ['DATION_E2E_URL'];assert urlsplit(BASE).hostname=='127.0.0.1'
async def main():
 errors=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  context=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
  page=await context.new_page();page.set_default_timeout(20000);page.on('pageerror',lambda error:errors.append(str(error)))
  await page.goto(BASE+'/login');await page.get_by_label('Email',exact=True).fill('user-1@example.test');await page.get_by_label('Contraseña',exact=True).fill('dispatch-e2e-private');await page.get_by_role('button',name='Ingresar',exact=True).click()
  await page.locator('[data-platform-home] h1').wait_for();assert '/login' not in page.url
  home=page.locator('[data-platform-home]');await home.locator('.platform-home__case').wait_for()
  assert await home.locator('.platform-home__attention').count()==1
  assert await home.locator('.platform-home__quick-link').count()==3
  await home.get_by_role('link',name='Revisar Asignación de carga · DC-'+os.environ['DATION_HOME_CASE'][:8].upper(),exact=True).click();await page.locator('.assignment-dashboard-v2').wait_for()
  assert os.environ['DATION_HOME_CASE'] in page.url and os.environ['DATION_HOME_RUN'] in page.url
  await page.go_back();await home.locator('.platform-home__case').wait_for()
  await home.get_by_role('link',name='Continuar DC-'+os.environ['DATION_HOME_CASE'][:8].upper(),exact=True).click();await page.locator('.assignment-dashboard-v2').wait_for()
  await page.locator('.nav [data-platform-view="platform-home"]').click();await home.locator('.platform-home__case').wait_for()
  assert not await page.locator('.sidebar').get_by_text('Cloud Run',exact=True).count()
  await page.locator('.nav [data-platform-view="inicio"]').click();await page.locator('[data-dda-id]').first.wait_for();assert urlsplit(page.url).path=='/app/ddas'
  before=await page.evaluate('history.length');await page.locator('.nav [data-platform-view="settings"]').click();await page.locator('[data-workspace-settings] .d-card').first.wait_for();assert await page.evaluate('history.length')==before+1
  assert not await page.locator('[data-platform-diagnostics]').evaluate('n=>n.open')
  await page.go_back();await page.locator('[data-home-dda-catalog]').wait_for(state='visible');await page.go_forward();await page.locator('[data-workspace-settings]').wait_for(state='visible')
  await context.clear_cookies(name='dation_access')
  await page.reload();await page.locator('[data-workspace-settings]').wait_for(state='visible');assert urlsplit(page.url).path=='/app/settings'
  await page.evaluate("dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
  await page.wait_for_function("!document.documentElement.classList.contains('d-session-loading')")
  for width in [1440,1024,768,390]:
   await page.set_viewport_size({'width':width,'height':1000});assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   menu=page.get_by_role('button',name='Abrir menú de usuario');await menu.focus();await page.keyboard.press('ArrowDown');assert await page.locator('[data-user-menu-panel]').is_visible();await page.keyboard.press('Escape');assert not await page.locator('[data-user-menu-panel]').is_visible();assert await menu.evaluate('n=>n===document.activeElement')
  await page.evaluate("window.dationNavigate('logistics-data')")
  async with page.expect_download() as download:
   await page.locator('a[download="orders.csv"]').first.click()
  saved=await download.value;assert saved.suggested_filename=='orders.csv'
  assert 'order_id' in Path(await saved.path()).read_text().splitlines()[0]
  await page.get_by_role('button',name='Abrir menú de usuario').click();await page.get_by_role('menuitem',name='Mi perfil').click();await page.get_by_label('Nombre',exact=True).fill('Perfil actualizado');await page.get_by_label('Apellido',exact=True).fill('User');await page.get_by_role('button',name='Guardar perfil').click();await page.get_by_text('Perfil actualizado.',exact=True).wait_for()
  assert await page.get_by_label('Email',exact=True).get_attribute('readonly') is not None
  assert await page.locator('[data-user-name]').inner_text()=='Perfil actualizado User'
  await page.reload();await page.get_by_label('Nombre',exact=True).wait_for();assert await page.get_by_label('Nombre',exact=True).input_value()=='Perfil actualizado'
  await page.locator('.nav [data-platform-view="platform-team"]').click();await page.get_by_role('heading',name='Equipo',exact=True).wait_for();assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  await page.get_by_role('button',name='Abrir menú de usuario').click();await page.get_by_role('menuitem',name='Cerrar sesión').click();await page.wait_for_url('**/login*');await page.goto(BASE+'/app/profile');await page.wait_for_url('**/login*')
  assert errors==[],errors
  await browser.close()
 print(json.dumps({'passed':True,'login':True,'history':True,'profile':True,'keyboard':True,'viewports':[1440,1024,768,390],'logout':True}))
asyncio.run(main())
