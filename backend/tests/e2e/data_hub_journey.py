"""Real isolated Data Hub: BFF login, CSV bytes, derived pack and deletion."""
import asyncio,json,os
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from playwright.async_api import async_playwright
BASE=os.environ['DATION_E2E_URL'];assert urlsplit(BASE).hostname=='127.0.0.1'
INPUT=Path(os.environ['DATION_HUB_INPUT'])

async def main():
 errors=[]
 artifacts=Path(os.environ['DATION_E2E_ARTIFACTS'])/'data-hub' if os.getenv('DATION_E2E_ARTIFACTS') else None
 if artifacts:artifacts.mkdir(parents=True,exist_ok=True)
 theme=(Path(__file__).parents[1]/'browser/theme_audit.js').read_text()
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  page=await browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce');page.set_default_timeout(15000);page.on('pageerror',lambda error:errors.append(str(error)))
  await page.goto(BASE+'/login');await page.get_by_label('Email',exact=True).fill('user-1@example.test');await page.get_by_label('Contraseña',exact=True).fill('dispatch-e2e-private');await page.get_by_role('button',name='Ingresar',exact=True).click()
  await page.locator('[data-platform-home] h1').wait_for()
  await page.locator('.nav [data-platform-view=platform-data]').click();root=page.locator('[data-platform-data]');await root.get_by_role('table').wait_for()
  for width in (1440,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});probe=await page.evaluate(theme);assert not probe['overflow'] and not probe['failures'],probe
   if artifacts:await page.screenshot(path=str(artifacts/f'library-{width}.png'),full_page=True)
  await root.get_by_role('button',name='Data Packs',exact=True).click();await root.locator('a[href*="pack_orders_id="]').first.click();await root.get_by_role('heading',name='Datasets del Data Pack').wait_for()
  await root.get_by_role('link',name='DC-'+os.environ['DATION_HUB_CASE'][:8]).click();await page.wait_for_function('window.DationDispatch?.getWorkspace().decisionCase?.persisted')
  assert os.environ['DATION_HUB_CASE'] in page.url
  await page.go_back();await root.get_by_role('heading',name='Datasets del Data Pack').wait_for()
  await root.get_by_role('button',name='Reutilizar Data Pack',exact=True).click();await page.locator('.dispatch-upload-screen').wait_for()
  state=await page.evaluate('window.DationDispatch.getWorkspace()');assert state['orders']['id']==os.environ['DATION_HUB_ORDERS'];assert not (state.get('decisionCase') or {}).get('persisted')
  await page.locator('.nav [data-platform-view=platform-data]').click();await root.get_by_role('table').wait_for()
  await root.get_by_role('button',name='Cargar datos',exact=True).first.click();dialog=page.get_by_role('dialog',name='Cargar datos',exact=True)
  await dialog.locator('input[type=file]').set_input_files(str(INPUT))
  await page.wait_for_url('**dataset_id=*');await root.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
  dataset=parse_qs(urlsplit(page.url).query)['dataset_id'][0];assert dataset!=os.environ['DATION_HUB_ORDERS']
  await root.get_by_text('<img src=x onerror=window.__bad=1>',exact=True).wait_for();assert await root.locator('img').count()==0;assert await page.evaluate('window.__bad===undefined')
  for width in (1440,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});probe=await page.evaluate(theme);assert not probe['overflow'] and not probe['failures'],probe
   if artifacts:await page.screenshot(path=str(artifacts/f'dataset-{width}.png'),full_page=True)
  async with page.expect_download() as pending:await root.get_by_role('link',name='Descargar CSV',exact=True).click()
  saved=await pending.value;assert Path(await saved.path()).read_bytes()==INPUT.read_bytes()
  await root.get_by_role('button',name='Archivar',exact=True).click();await page.get_by_role('dialog').get_by_role('button',name='Archivar dataset',exact=True).click();await root.get_by_role('button',name='Restaurar',exact=True).wait_for()
  await root.get_by_role('button',name='Eliminar definitivamente',exact=True).click();await page.get_by_role('dialog').get_by_role('button',name='Eliminar definitivamente',exact=True).click();await root.get_by_role('heading',name='No encontramos resultados').wait_for()
  await page.reload();await root.get_by_role('heading',name='No encontramos resultados').wait_for();assert errors==[],errors
  await browser.close()
 print(json.dumps({'passed':True,'upload':True,'preview':True,'download_bytes':True,'pack_reuse':True,'safe_delete':True,'viewports':[1440,1024,768,390]}))
asyncio.run(main())
