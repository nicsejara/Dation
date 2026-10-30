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
  assert await root.get_by_role('button',name='Data Packs',exact=True).count()==0
  assert await root.get_by_role('button',name='Cargar datos',exact=True).count()==0
  await root.locator('[data-dataset-open="'+os.environ['DATION_HUB_ORDERS']+'"]').click()
  await root.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
  await root.get_by_role('link',name='Ver Decision Case',exact=True).click()
  await page.locator('[data-platform-decisions] .center-drawer:visible').get_by_role('heading',name='Cadena de decisiones').wait_for()
  assert 'center_case_id='+os.environ['DATION_HUB_CASE'] in page.url
  await page.go_back();await root.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
  await page.evaluate("id=>window.DationDispatch.openCase(id,'logistics-data')",os.environ['DATION_HUB_CASE'])
  await page.locator('[data-kind=orders] input[type=file]').set_input_files(str(INPUT))
  await page.wait_for_function("window.DationDispatch.getWorkspace().orders?.original_filename==='datos ñ.csv'")
  dataset=await page.evaluate('window.DationDispatch.getWorkspace().orders.id')
  assert dataset!=os.environ['DATION_HUB_ORDERS']
  await page.locator('.nav [data-platform-view=platform-data]').click()
  await root.locator('[data-dataset-open="'+dataset+'"]').click()
  await root.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
  for width in (1440,1280,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
   probe=await page.evaluate(theme);assert not probe['overflow'] and not probe['failures'],probe
   if artifacts:await page.screenshot(path=str(artifacts/f'dataset-{width}.png'),full_page=True)
  await root.locator('summary',has_text='Vista previa').click()
  await root.get_by_text('<img src=x onerror=window.__bad=1>',exact=True).wait_for();assert await root.locator('img[src=x]').count()==0;assert await page.evaluate('window.__bad===undefined')
  drawer=root.locator('.hub-drawer:visible')
  async with page.expect_download() as pending:await drawer.get_by_role('link',name='Descargar',exact=True).click()
  saved=await pending.value;assert Path(await saved.path()).read_bytes()==INPUT.read_bytes()
  async def menu(label):
   await drawer.get_by_role('button',name='Acciones de ',exact=False).click()
   await drawer.get_by_role('menuitem',name=label,exact=True).click()
  await menu('Archivar');await page.get_by_role('dialog',name='Archivar dataset',exact=True).get_by_role('button',name='Archivar dataset',exact=True).click()
  await drawer.get_by_text('Archivado',exact=True).first.wait_for()
  await menu('Restaurar');await page.get_by_role('dialog',name='Restaurar dataset',exact=True).get_by_role('button',name='Restaurar dataset',exact=True).click()
  await drawer.get_by_text('Activo',exact=True).first.wait_for()
  await menu('Archivar');await page.get_by_role('dialog',name='Archivar dataset',exact=True).get_by_role('button',name='Archivar dataset',exact=True).click()
  await drawer.get_by_text('Archivado',exact=True).first.wait_for()
  await menu('Eliminar definitivamente');await page.get_by_role('dialog',name='Eliminar definitivamente',exact=True).get_by_role('button',name='Eliminar definitivamente',exact=True).click()
  await page.wait_for_function("!new URL(location.href).searchParams.has('dataset_id')")
  await page.reload();await root.get_by_role('table').wait_for();assert errors==[],errors
  await browser.close()
 print(json.dumps({'passed':True,'dda_upload':True,'preview':True,'download_bytes':True,'decision_center_lineage':True,'safe_delete':True,'restore':True,'viewports':[1440,1280,1024,768,390]}))
asyncio.run(main())
