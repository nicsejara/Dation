"""Real settings save, history, Free policy and readonly access across four widths."""
import asyncio,json,os
from pathlib import Path
from urllib.parse import urlsplit,urlencode
from playwright.async_api import async_playwright
BASE=os.environ['DATION_E2E_URL'];assert urlsplit(BASE).hostname=='127.0.0.1'
async def main():
 artifacts=Path(os.environ['DATION_E2E_ARTIFACTS'])/'workspace-settings' if os.getenv('DATION_E2E_ARTIFACTS') else None
 if artifacts:artifacts.mkdir(parents=True,exist_ok=True)
 theme=(Path(__file__).parents[1]/'browser/theme_audit.js').read_text();errors=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  context=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=await context.new_page();page.set_default_timeout(15000);page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(BASE+'/login');await page.get_by_label('Email',exact=True).fill('user-1@example.test');await page.get_by_label('Contraseña',exact=True).fill('dispatch-e2e-private');await page.get_by_role('button',name='Ingresar',exact=True).click();await page.locator('[data-platform-home] h1').wait_for()
  target=BASE+'/app?'+urlencode({'view':'decision-dashboard','case_id':os.environ['DATION_SETTINGS_CASE'],'node_id':'logistics_assignment','run_id':os.environ['DATION_SETTINGS_RUN']})
  await page.goto(target);await page.locator('.assignment-dashboard-v2').wait_for();await page.locator('.nav [data-platform-view=settings]').click();root=page.locator('[data-workspace-settings]');await root.get_by_label('Nombre del workspace').wait_for();assert await root.get_by_role('tab').count()==4
  name='Equipo Chile · <img src=x onerror=window.__bad=1>';await root.get_by_label('Nombre del workspace').fill(name);await root.get_by_label('País',exact=True).select_option('CL');await root.get_by_label('Idioma de formatos').select_option('en');await root.get_by_label('Zona horaria').select_option('America/Santiago');await root.get_by_role('button',name='Guardar datos generales').click();await root.get_by_text('Configuración guardada.',exact=True).wait_for();assert await page.locator('[data-workspace-name]').inner_text()==name;assert await page.evaluate('window.__bad===undefined')
  await root.get_by_role('tab',name='General',exact=True).focus();before=await page.evaluate('history.length');await page.keyboard.press('ArrowRight');assert await root.get_by_role('tab',name='Operación',exact=True).evaluate('n=>n===document.activeElement');assert await page.evaluate('history.length')==before;await page.keyboard.press('Enter');await root.get_by_label('Moneda',exact=True).wait_for();assert 'settings_tab=operation' in page.url
  for label,value in [('Moneda','CLP'),('Unidad de peso','t'),('Unidad de distancia','mi'),('Unidad logística','pallets')]:await root.get_by_label(label,exact=True).select_option(value)
  await root.get_by_role('button',name='Guardar preferencias').click();await root.get_by_text('Configuración guardada.',exact=True).wait_for()
  for width in (1440,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000})
   for tab,label in [('general','General'),('operation','Operación'),('ddas','Decision Data Assets'),('plan','Plan y facturación')]:
    await root.get_by_role('tab',name=label,exact=True).click();await root.locator('[role=tabpanel]:not([hidden]) .d-card').wait_for();probe=await page.evaluate(theme);assert not probe['overflow'] and not probe['failures'],probe
    geometry=await root.evaluate("n=>{const tabs=n.querySelector('[role=tablist]').getBoundingClientRect(),card=n.querySelector('[role=tabpanel]:not([hidden])').getBoundingClientRect();return {below:card.top>=tabs.bottom+19,width:Math.abs(card.width-n.getBoundingClientRect().width),heights:[...n.querySelectorAll('[role=tab]')].map(t=>t.getBoundingClientRect().height)}}");assert geometry['below'] and geometry['width']<2 and max(geometry['heights'])<75,geometry
    selected=await root.evaluate("n=>{const selected=getComputedStyle(n.querySelector('[aria-selected=true]')),other=getComputedStyle(n.querySelector('[aria-selected=false]'));return selected.borderBottomWidth==='2px'&&selected.borderBottomColor!==other.borderBottomColor;}");assert selected
    if artifacts:await page.screenshot(path=str(artifacts/f'{tab}-{width}.png'),full_page=True)
  assert await root.get_by_role('heading',name='Plan Free',exact=True).count()==1;assert await root.get_by_role('button').count()==0;assert 'No hay cobros' in await root.inner_text();assert 'Tarjeta' not in await root.inner_text()
  await page.reload();await root.get_by_role('heading',name='Plan Free',exact=True).wait_for();await page.go_back()
  try:await root.get_by_role('heading',name='Decision Data Assets',exact=True).wait_for()
  except Exception:raise AssertionError({'url':page.url,'root':await root.inner_text(),'errors':errors}) from None
  await page.go_forward();await root.get_by_role('heading',name='Plan Free',exact=True).wait_for();await root.get_by_role('tab',name='Operación',exact=True).click();await root.get_by_label('Moneda',exact=True).wait_for();assert await root.get_by_label('Moneda',exact=True).input_value()=='CLP'
  await page.goto(target);await page.locator('.assignment-dashboard-v2').wait_for();assert os.environ['DATION_SETTINGS_RUN'] in page.url
  assert errors==[],errors;await browser.close()
 print(json.dumps({'passed':True,'general_operation_persisted':True,'free_no_payments':True,'keyboard_history_reload':True,'original_run_restored':True,'viewports':[1440,1024,768,390]}))
asyncio.run(main())
