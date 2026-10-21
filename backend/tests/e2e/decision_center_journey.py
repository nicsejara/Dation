"""Real BFF login and Decision Center restore/navigation journey."""
import asyncio,json,os
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from playwright.async_api import async_playwright
BASE=os.environ['DATION_E2E_URL'];assert urlsplit(BASE).hostname=='127.0.0.1'
CASE=os.environ['DATION_CENTER_CASE'];D1=os.environ['DATION_CENTER_ASSIGNMENT'];D2=os.environ['DATION_CENTER_SCHEDULING']
async def main():
 errors=[];artifacts=Path(os.environ['DATION_E2E_ARTIFACTS'])/'decision-center' if os.getenv('DATION_E2E_ARTIFACTS') else None
 if artifacts:artifacts.mkdir(parents=True,exist_ok=True)
 theme=(Path(__file__).parents[1]/'browser/theme_audit.js').read_text()
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  page=await browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce');page.set_default_timeout(15000);page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(BASE+'/login');await page.get_by_label('Email',exact=True).fill('user-1@example.test');await page.get_by_label('Contraseña',exact=True).fill('dispatch-e2e-private');await page.get_by_role('button',name='Ingresar',exact=True).click();await page.locator('[data-platform-home] h1').wait_for()
  await page.locator('.nav [data-platform-view=platform-decisions]').click();root=page.locator('[data-platform-decisions]');await root.get_by_role('table').wait_for()
  assert await root.get_by_role('table').locator('tbody tr').count()==1
  for width in (1440,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');probe=await page.evaluate(theme);probe['width']=width
   if probe['overflow']:probe['outside']=await page.evaluate("[...document.querySelectorAll('body *')].filter(n=>n.getClientRects().length&&n.getBoundingClientRect().right>innerWidth+1).slice(0,20).map(n=>({tag:n.tagName,cls:n.className,right:n.getBoundingClientRect().right,width:n.getBoundingClientRect().width}))")
   assert not probe['overflow'] and not probe['failures'],probe
   if artifacts:await page.screenshot(path=str(artifacts/f'library-{width}.png'),full_page=True)
  await root.get_by_role('link',name='Abrir',exact=True).click();await root.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
  if D2=='available':
   await root.locator('[data-center-node=logistics_scheduling]').get_by_role('link',name='Configurar',exact=True).click()
   await page.locator('[data-scheduling-review]').wait_for()
   query=parse_qs(urlsplit(page.url).query);assert query['node_id']==['logistics_scheduling'] and query['case_id']==[CASE] and query['view']==['logistics-config']
   assert errors==[],errors;await browser.close();print(json.dumps({'passed':True,'available_d2_direct_config':True}));return
  await root.locator('.center-drawer:visible').get_by_role('button',name='Acciones de DC-'+CASE[:8].upper(),exact=True).click();await root.get_by_role('menuitem',name='Editar nombre',exact=True).click();dialog=page.get_by_role('dialog');label='Semana 43 · <img src=x onerror=window.__bad=1>'
  await dialog.get_by_label('Etiqueta opcional').fill(label);await dialog.get_by_role('button',name='Guardar',exact=True).click();await root.get_by_role('heading',name=label,exact=True).wait_for();assert await root.locator('img[src=x]').count()==0
  for width in (1440,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');probe=await page.evaluate(theme);probe['width']=width
   if probe['overflow']:probe['outside']=await page.evaluate("[...document.querySelectorAll('body *')].filter(n=>n.getClientRects().length&&n.getBoundingClientRect().right>innerWidth+1).slice(0,20).map(n=>({tag:n.tagName,cls:n.className,right:n.getBoundingClientRect().right,width:n.getBoundingClientRect().width}))")
   assert not probe['overflow'] and not probe['failures'],probe
   if artifacts:await page.screenshot(path=str(artifacts/f'detail-{width}.png'),full_page=True)
  # Approved D1 restores that exact dashboard without Data/Config intermediates.
  first=root.locator('[data-center-node=logistics_assignment]');await first.locator('summary',has_text='Responsables y aprobación').click();await first.get_by_role('link',name='Abrir dashboard aprobado',exact=True).click();await page.wait_for_url('**run_id='+D1);await page.locator('.assignment-dashboard-v2').wait_for()
  assert parse_qs(urlsplit(page.url).query)['node_id']==['logistics_assignment']
  await page.go_back();await root.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
  second=root.locator('[data-center-node=logistics_scheduling]');await second.get_by_role('link',name='Revisar',exact=True).click();await page.wait_for_url('**run_id='+D2);await page.locator('.scheduling-dashboard-v2').wait_for()
  await page.go_back();await root.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
  await first.locator('summary',has_text='Historial de corridas').click();await first.locator('.center-run-list').wait_for();assert 'center_node=logistics_assignment' in page.url
  await page.reload();await root.locator('[data-center-node=logistics_assignment] .center-run-list').wait_for()
  async with page.expect_download() as downloaded:await root.locator('.center-linked-file a[download]').first.click()
  download=await downloaded.value;assert Path(await download.path()).read_bytes();assert 'center_case_id='+CASE in page.url
  await root.locator('.center-drawer:visible').get_by_role('button',name='Acciones de DC-'+CASE[:8].upper(),exact=True).click();await root.get_by_role('menuitem',name='Archivar',exact=True).click();await page.get_by_role('dialog',name='Archivar caso').get_by_role('button',name='Archivar',exact=True).click();await page.wait_for_url('**center_filter=archived*');await page.reload();await root.get_by_role('link',name='Abrir',exact=True).click();await root.locator('.center-drawer:visible .center-status[data-state=archived]').wait_for()
  assert await root.locator('.center-drawer__ctas a').first.get_attribute('aria-disabled')=='true'
  await root.locator('.center-drawer:visible').get_by_role('button',name='Acciones de DC-'+CASE[:8].upper(),exact=True).click();await root.get_by_role('menuitem',name='Restaurar',exact=True).click();await page.get_by_role('dialog',name='Restaurar caso').get_by_role('button',name='Restaurar',exact=True).click();await page.wait_for_url('**center_filter=all*');await root.locator('.center-table .center-status:not([data-state=archived])').first.wait_for()
  assert await page.evaluate('window.__bad===undefined');assert errors==[],errors
  await browser.close()
 print(json.dumps({'passed':True,'approved_d1':True,'current_d2':True,'history_reload':True,'labels_archive':True,'viewports':[1440,1024,768,390]}))
asyncio.run(main())
