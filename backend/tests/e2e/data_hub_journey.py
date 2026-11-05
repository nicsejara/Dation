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
  async def read_api(path):
   return await page.evaluate("async path=>{const {api}=await import('/static/js/dispatch/shared.mjs');return api(path);}",path)
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
  await page.wait_for_function('''original=>{
   const s=window.DationDispatch.getWorkspace();
   return s.decisionCase?.persisted&&s.decisionCase.id!==original&&!s.forkedFrom
    &&new URL(location.href).searchParams.get('case_id')===s.decisionCase.id;
  }''',arg=os.environ['DATION_HUB_CASE'])
  fork=await page.evaluate('window.DationDispatch.getWorkspace().decisionCase.id')
  dda_dataset=dataset
  case_rows={cid:(await read_api('/api/decision-cases/'+cid))['case'] for cid in [os.environ['DATION_HUB_CASE'],fork]}
  detail=await read_api('/api/platform/data/datasets/'+dataset)
  assert detail['referenced'] and not detail['can_delete'],detail
  assert fork in [item['id'] for item in detail['used_in']],detail
  await page.locator('.nav [data-platform-view=platform-data]').click()
  await root.locator('[data-dataset-open="'+dataset+'"]').click()
  await root.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
  for width in (1440,1280,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
   probe=await page.evaluate(theme)
   if (probe['overflow'] or probe['failures']) and artifacts:
    geometry=await page.evaluate('''() => {
     const rect=el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return {
      tag:el.tagName,classes:typeof el.className==='string'?el.className:'',
      x:r.x,right:r.right,width:r.width,scrollWidth:el.scrollWidth,clientWidth:el.clientWidth,
      overflowX:s.overflowX,position:s.position,minWidth:s.minWidth,display:s.display};};
     return {innerWidth,documentWidth:document.documentElement.scrollWidth,
      activeElement:document.activeElement?.outerHTML.slice(0,300),
      hub:[...document.querySelectorAll('.hub-layout,.hub-portfolio,.hub-drawer,.hub-drawer__body,.hub-table-scroll,.hub-table,.hub-kpis,.hub-search')].map(rect),
      outside:[...document.querySelectorAll('body *')].filter(el=>{
       const r=el.getBoundingClientRect();return r.width&&r.height&&(r.right>innerWidth||r.left<0);
      }).slice(0,80).map(el=>({...rect(el),text:el.textContent.slice(0,100),
       parents:[...function*(node){for(let n=node.parentElement;n;n=n.parentElement)yield rect(n);}(el)]}))};
    }''')
    (artifacts/f'dataset-failure-{width}.json').write_text(json.dumps({'probe':probe,'geometry':geometry},indent=2))
    await page.screenshot(path=str(artifacts/f'dataset-failure-{width}.png'),full_page=True)
   assert not probe['overflow'] and not probe['failures'],(width,probe)
   if artifacts:await page.screenshot(path=str(artifacts/f'dataset-{width}.png'),full_page=True)
  await root.locator('summary',has_text='Vista previa').click()
  await root.get_by_text('<img src=x onerror=window.__bad=1>',exact=True).wait_for();assert await root.locator('img[src=x]').count()==0;assert await page.evaluate('window.__bad===undefined')
  drawer=root.locator('.hub-drawer:visible')
  async with page.expect_download() as pending:await drawer.get_by_role('link',name='Descargar',exact=True).click()
  saved=await pending.value;assert Path(await saved.path()).read_bytes()==INPUT.read_bytes()
  async def menu(label):
   await drawer.get_by_role('button',name='Acciones de ',exact=False).click()
   try:await drawer.get_by_role('menuitem',name=label,exact=True).click()
   except Exception:
    detail=await read_api('/api/platform/data/datasets/'+dataset)
    print('HUB_ACTION_FAILURE='+json.dumps({'label':label,
     'can_delete':detail.get('can_delete'),'referenced':detail.get('referenced'),'used_in':detail.get('used_in'),
     'dataset':{k:detail.get('dataset',{}).get(k) for k in ['id','archived_at','is_default','case_count','run_count']},
     'drawer':await drawer.inner_text()}),flush=True)
    raise
  async def mutate(label,title,operation,state=None):
   await menu(label)
   dialog=page.get_by_role('dialog',name=title,exact=True)
   # Native dialog close/focus events may run after its DOM is removed.
   await dialog.evaluate("dialog=>{window.__hubMutationClosed=new Promise(resolve=>dialog.addEventListener('close',()=>resolve(true),{once:true}));}")
   path='/api/platform/data/datasets/'+dataset+('' if operation=='delete' else '/'+operation)
   method='DELETE' if operation=='delete' else 'POST'
   async with page.expect_response(lambda response:response.request.method==method and urlsplit(response.url).path==path) as pending:
    await dialog.get_by_role('button',name=title,exact=True).click()
   response=await pending.value;assert response.ok,(response.status,await response.text())
   await page.evaluate('window.__hubMutationClosed')
   await dialog.wait_for(state='detached')
   if state:await drawer.locator('.hub-drawer__body:not([aria-busy])').get_by_text(state,exact=True).first.wait_for()
  await mutate('Archivar','Archivar dataset','archive','Archivado')
  await mutate('Restaurar','Restaurar dataset','unarchive','Activo')
  await mutate('Archivar','Archivar dataset','archive','Archivado')
  trigger=drawer.get_by_role('button',name='Acciones de ',exact=False)
  await trigger.click();await drawer.get_by_role('menuitem',name='Restaurar',exact=True).wait_for()
  assert await drawer.get_by_role('menuitem',name='Eliminar definitivamente',exact=True).count()==0
  assert 'center_case_id='+fork in await drawer.get_by_role('link',name='Ver Decision Case',exact=True).get_attribute('href')
  await trigger.click()
  await mutate('Restaurar','Restaurar dataset','unarchive','Activo')
  await drawer.get_by_role('button',name='Cerrar detalle del dataset',exact=True).click();await drawer.wait_for(state='hidden')
  dataset=os.environ['DATION_HUB_UNUSED']
  await root.locator('[data-dataset-open="'+dataset+'"]').click()
  await drawer.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
  detail=await read_api('/api/platform/data/datasets/'+dataset)
  assert not detail['referenced'],detail
  await mutate('Archivar','Archivar dataset','archive','Archivado')
  assert (await read_api('/api/platform/data/datasets/'+dataset))['can_delete']
  await mutate('Eliminar definitivamente','Eliminar definitivamente','delete')
  await page.wait_for_function("!new URL(location.href).searchParams.has('dataset_id')")
  assert case_rows=={cid:(await read_api('/api/decision-cases/'+cid))['case'] for cid in case_rows}
  await page.reload();await root.get_by_role('table').wait_for();assert errors==[],errors
  await browser.close()
 print(json.dumps({'passed':True,'dda_upload':True,'dda_dataset_id':dda_dataset,'fork_case_id':fork,'referenced_delete_blocked':True,
  'case_rows_unchanged':True,'preview':True,'download_bytes':True,'decision_center_lineage':True,'safe_delete':True,'restore':True,'viewports':[1440,1280,1024,768,390]}))
asyncio.run(main())
