"""Real J1.01 browser/API/PostgreSQL invariants, default-off production gate."""
import asyncio,json,re,unittest
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from uuid import uuid4
from playwright.async_api import expect
from r4_model_helpers import R4Browser
import guided_model_helpers as blocks
import test_ultimate_case_setup as setup

OUT=Path('/tmp/dation-j101-browser');OUT.mkdir(exist_ok=True)

class ModelLibraryTests(R4Browser):
 fixture_name='model_library_fixture.py'
 model=setup.UltimateCaseSetupTests.model
 async def library(self):
  await self.page.goto(self.base+'/app/ddas/logistics/models');await self.loaded()
 async def loaded(self):await expect(self.page.locator('#ultimate-models-root')).to_have_attribute('data-ultimate-ready','true')
 async def start(self,name='J101 Modelo QA'):
  await self.library();await self.page.get_by_role('button',name='Crear nuevo modelo',exact=True).click()
  await expect(self.page.locator('.model-wizard-pro')).to_be_visible();await self.loaded()
  await self.page.get_by_label('Nombre del modelo *',exact=True).fill(name);await blocks.block(self.page,3)
 async def confirm(self):
  for i in [1,2,4,5,3]:
   node=await blocks.block(self.page,i);cta=node.locator('[data-confirm-block="'+str(i)+'"]')
   if i==3:await expect(cta).to_have_attribute('data-preview-current','true')
   if not await cta.is_disabled():await cta.click()
   await expect(cta).to_be_disabled();await expect(node.locator('>summary .guided-status')).to_have_attribute('data-state','complete')
  await expect(self.page.locator('[data-library-publish]')).to_be_enabled()
 async def publish(self):
  await self.confirm();await self.page.locator('[data-library-publish]').click()
  async with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/versions')) as response:
   await self.page.get_by_role('dialog').get_by_role('button',name='Publicar esta versión',exact=True).click()
  data=await (await response.value).json();await expect(self.page.locator('[data-review-context=library]')).to_be_visible();return data
 async def snapshot(self):
  return json.loads(self.sql("SELECT jsonb_build_object('cases',(SELECT coalesce(jsonb_agg(to_jsonb(c) ORDER BY c.id),'[]') FROM decision_cases c),'runs',(SELECT coalesce(jsonb_agg(to_jsonb(r) ORDER BY r.id),'[]') FROM decision_runs r),'packs',(SELECT coalesce(jsonb_agg(to_jsonb(p) ORDER BY p.id),'[]') FROM case_data_packs p));"))
 async def test_01_incomplete_drafts_are_independent_durable_and_never_create_cases(self):
  before=await self.snapshot();await self.start('J101 Borrador A')
  a=self.page.url;await self.page.locator('[data-library-save]').click();await expect(self.page.locator('[data-library-feedback]')).to_contain_text('en este navegador')
  await self.page.reload();await self.loaded();await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('J101 Borrador A')
  await self.page.locator('.j101-back').click();await self.loaded();await self.page.get_by_role('button',name='Crear nuevo modelo',exact=True).click();await self.loaded()
  b=self.page.url;self.assertNotEqual(parse_qs(urlparse(a).query)['model_work_id'],parse_qs(urlparse(b).query)['model_work_id'])
  await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('');await self.page.get_by_label('Nombre del modelo *',exact=True).fill('J101 Borrador B')
  await self.page.locator('[data-library-save]').click();await self.page.goto(a);await self.loaded();await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('J101 Borrador A')
  second=await self.context.new_page();await second.goto(b);await expect(second.get_by_label('Nombre del modelo *',exact=True)).to_have_value('J101 Borrador B');await second.close()
  self.assertEqual(before,await self.snapshot());self.assertFalse(any(m in ['POST','PUT','PATCH'] and '/api/platform/logistics-models' in p for m,p in self.operations))
 async def test_02_publish_two_models_review_history_successor_and_pinned_case(self):
  before=await self.snapshot();await self.start('J101 A · Propia');await self.fill(two=True);a=await self.publish();self.assertEqual(a['version']['version'],1)
  self.assertEqual(before,await self.snapshot());mid=a['version']['model_id'];v1=a['version']['id'];h1=a['version']['config_hash']
  await expect(self.page.locator('[data-review-case]')).to_have_count(0);await expect(self.page.get_by_role('button',name='Crear Case con otra versión',exact=True)).to_have_count(0)
  await self.page.locator('.j101-back').click();await self.loaded();await self.page.get_by_role('button',name='Crear nuevo modelo',exact=True).click();await self.loaded()
  await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('');await self.page.get_by_label('Nombre del modelo *',exact=True).fill('J101 B · Tercerizada');await blocks.block(self.page,3);await self.fill();b=await self.publish()
  self.assertNotEqual(mid,b['version']['model_id']);self.assertNotEqual(h1,b['version']['config_hash']);self.assertEqual(before,await self.snapshot())
  case=await self.api('POST','/api/platform/logistics-cases',{'id':str(uuid4()),'name':'J101 Case pinned','logistics_model_version_id':v1,'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':setup.ADMIN})
  pinned_resources=await self.snapshot()
  pinned_before=await self.api('GET','/api/platform/logistics-cases/'+case['case']['id']+'/context')
  await self.page.goto(self.base+'/app/ddas/logistics/models?model_id='+mid+'&model_version_id='+v1+'&model_view=review');await self.loaded();await self.page.get_by_role('button',name='Preparar nueva versión',exact=True).click();await self.loaded()
  await self.page.get_by_label('Nombre del modelo *',exact=True).fill('J101 A · Sucesora');await self.page.locator('[data-dation-test=model-v2-block-5]>summary').click();await self.page.locator('[name=currency][value=USD]').check();v2=await self.publish();self.assertEqual(v2['version']['version'],2)
  data=await self.api('GET','/api/platform/logistics-models/'+mid);old=next(v for v in data['versions'] if v['id']==v1);self.assertEqual(old['config_hash'],h1);self.assertEqual(old['config_jsonb'],a['version']['config_jsonb'])
  pinned_after=await self.api('GET','/api/platform/logistics-cases/'+case['case']['id']+'/context');
  for key in ['case','model_version','pack','pack_version','responsibilities','entry_count']:self.assertEqual(pinned_before[key],pinned_after[key],key)
  self.assertEqual(pinned_resources,await self.snapshot())
  (OUT/'version-integrity.json').write_text(json.dumps({'model_a':mid,'a_v1':v1,'a_v1_hash':h1,'a_v2':v2['version']['id'],'a_v2_hash':v2['version']['config_hash'],'model_b':b['version']['model_id'],'b_v1':b['version']['id'],'case':case['case']['id'],'case_pinned_version':pinned_after['model_version']['id'],'case_pack_run_unchanged':pinned_resources==await self.snapshot(),'v1_snapshot_unchanged':old['config_jsonb']==a['version']['config_jsonb']},indent=2))
  await self.page.get_by_role('button',name='Ver historial',exact=True).click();await self.loaded();await expect(self.page.locator('[data-model-history] article')).to_have_count(2);await self.page.get_by_role('button',name='Revisar versión 1',exact=True).click();await self.loaded();await expect(self.page.locator('[data-model-review]')).to_have_attribute('data-review-version',v1)
  await self.page.locator('.j101-back').click();await self.loaded();await self.page.get_by_role('button',name='Continuar a Decision Case',exact=True).click();await self.ready(1);await expect(self.page.locator('[data-dation-test=core-model]')).to_have_attribute('data-model-state','NEW_EDITING');await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('');self.assertNotIn('model_id=',self.page.url);self.assertEqual(pinned_resources,await self.snapshot())
 async def test_03_dirty_back_cancel_discard_and_reload(self):
  await self.start('J101 Guardado');await self.page.locator('[data-library-save]').click();await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Cambio sin guardar')
  url=self.page.url;await self.page.go_back();dialog=self.page.get_by_role('dialog');await expect(dialog).to_be_visible();await dialog.get_by_role('button',name='Seguir editando',exact=True).click();await expect(self.page).to_have_url(url)
  await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('Cambio sin guardar');await self.page.locator('.j101-back').click();await self.page.get_by_role('dialog').get_by_role('button',name='Descartar cambios',exact=True).click();await self.loaded()
  await self.page.goto(url);await self.loaded();await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('J101 Guardado')
 async def test_04_get_error_is_not_empty_and_exact_version_never_falls_back(self):
  async def fail(route):await route.fulfill(status=503,json={'detail':'J101 fallo de consulta controlado'})
  await self.page.route('**/api/platform/logistics-models?*',fail);await self.library();await expect(self.page.locator('#ultimate-models-root')).to_contain_text('J101 fallo de consulta controlado');await expect(self.page.locator('.j101-empty')).to_have_count(0)
  await self.page.unroute('**/api/platform/logistics-models?*',fail);await self.page.get_by_role('button',name='Reintentar',exact=True).click();await expect(self.page.locator('.j101-model-card')).not_to_have_count(0)
  model=await self.api('POST','/api/platform/logistics-models',{'id':str(uuid4()),'name':'J101 Legacy','configuration':setup.CONFIG});mid=model['model']['id'];v=await self.api('POST','/api/platform/logistics-models/'+mid+'/versions',{'version_id':str(uuid4()),'expected_revision':1})
  writes=len([1 for m,p in self.operations if m in ['POST','PUT','PATCH'] and '/api/platform/' in p]);await self.page.goto(self.base+'/app/ddas/logistics/models?model_id='+mid+'&model_version_id='+v['version']['id']+'&model_view=review');await self.loaded();await expect(self.page.locator('[data-review-context=library]')).to_be_visible();self.assertEqual(writes,len([1 for m,p in self.operations if m in ['POST','PUT','PATCH'] and '/api/platform/' in p]))
  await self.page.goto(self.base+'/app/ddas/logistics/models?model_id='+mid+'&model_version_id='+str(uuid4())+'&model_view=review');await expect(self.page.locator('#ultimate-models-root')).to_contain_text('No se encontró la versión histórica solicitada');await expect(self.page.locator('[data-model-review]')).to_have_count(0)
 async def test_05_core_return_preserves_draft_candidate_graph_and_read_only_permissions(self):
  m,v=await setup.UltimateCaseSetupTests.model(self,'J101 Modelo candidato');mid=m['model']['id'];vid=v['version']['id']
  await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
  from wizard_helpers import show_case
  await self.page.get_by_role('button',name='Seleccionar modelo existente',exact=True).click();dialog=self.page.get_by_role('dialog');await dialog.get_by_label('Logistics Model',exact=True).select_option(mid);await expect(dialog.get_by_role('button',name='Seleccionar esta versión',exact=True)).to_be_enabled();await dialog.get_by_role('button',name='Seleccionar esta versión',exact=True).click();await self.ready(2);await show_case(self.page);await self.page.get_by_label('Nombre del Case',exact=True).fill('J101 nombre sin guardar')
  stored=await self.page.evaluate("()=>{const k=Object.keys(sessionStorage).find(k=>k.endsWith('.case.new'));return sessionStorage.getItem(k)}")
  self.page.once('dialog',lambda dialog:dialog.accept());await self.page.locator('[data-open-model-library]').click();await self.loaded();liburl=self.page.url
  await self.page.get_by_role('button',name='Crear nuevo modelo',exact=True).click();await self.loaded();await self.page.get_by_label('Nombre del modelo *',exact=True).fill('J101 Modelo no candidato');await self.page.locator('[data-library-save]').click();await self.page.locator('.j101-back').click();await self.loaded();await self.page.get_by_role('button',name='Volver al contexto de origen',exact=True).click();await self.ready(3)
  await expect(self.page.get_by_label('Nombre del Case',exact=True)).to_have_value('J101 nombre sin guardar');now=await self.page.evaluate("()=>{const k=Object.keys(sessionStorage).find(k=>k.endsWith('.case.new'));return sessionStorage.getItem(k)}")
  a,b=json.loads(stored),json.loads(now);self.assertEqual(a['id'],b['id']);self.assertEqual(a['planning_model']['version_id'],b['planning_model']['version_id']);self.assertEqual(a['planning_model']['version_id'],vid)
  viewer=await self.browser.new_context();await self.login(viewer,3);vp=await viewer.new_page();await vp.goto(self.base+'/app/ddas/logistics/models');await expect(vp.locator('#ultimate-models-root')).to_have_attribute('data-ultimate-ready','true');await expect(vp.get_by_role('button',name='Crear nuevo modelo',exact=True)).to_have_count(0)
  await vp.goto(self.base+'/app/ddas/logistics/models?model_id='+mid+'&model_version_id='+vid+'&model_view=review');await expect(vp.locator('[data-review-context=library]')).to_be_visible();await expect(vp.get_by_role('button',name='Preparar nueva versión',exact=True)).to_have_count(0)
  for method,path,body in [('POST','/api/platform/logistics-models',{'id':str(uuid4()),'name':'Forbidden','configuration':setup.CONFIG}),('PUT','/api/platform/logistics-models/'+mid,{'expected_revision':2,'name':'Forbidden','configuration':setup.CONFIG}),('POST','/api/platform/logistics-models/'+mid+'/versions',{'version_id':str(uuid4()),'expected_revision':2})]:self.assertEqual((await self.request(method,path,body,context=viewer)).status,403)
  other=await self.browser.new_context();await self.login(other,2);response=await self.request('GET','/api/platform/logistics-models/'+mid,context=other);self.assertIn(response.status,[403,404]);await other.close();await viewer.close()
 async def frame(self,scene):
  metrics=[]
  for width in [1440,1280,768,375]:
   await self.page.set_viewport_size({'width':width,'height':1000 if width>768 else 844});await self.page.evaluate('document.fonts.ready');await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
   data=await self.page.evaluate('''()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,buttons:[...document.querySelectorAll('.j101-library :is(.d-button,.d-recovery__actions button)')].filter(n=>n.getClientRects().length).map(n=>({text:n.textContent,width:n.getBoundingClientRect().width,height:n.getBoundingClientRect().height,left:n.getBoundingClientRect().left,right:n.getBoundingClientRect().right})),cards:[...document.querySelectorAll('.j101-model-card')].map(n=>({x:n.getBoundingClientRect().x,y:n.getBoundingClientRect().y,width:n.getBoundingClientRect().width}))})''')
   self.assertLessEqual(data['scroll'],data['client'],data);self.assertTrue(all(b['height']>=44 and b['left']>=0 and b['right']<=data['client']+1 for b in data['buttons']),data)
   if scene=='library' and width==1440:self.assertEqual(data['cards'][0]['y'],data['cards'][1]['y'])
   if scene=='library' and width==375:self.assertNotEqual(data['cards'][0]['y'],data['cards'][1]['y'])
   await self.page.mouse.move(0,0);await self.page.evaluate('document.activeElement?.blur();scrollTo(0,0)');await self.page.screenshot(path=str(OUT/(scene+'-'+str(width)+'.png')),full_page=True,animations='disabled');metrics.append(data)
  (OUT/(scene+'-geometry.json')).write_text(json.dumps(metrics,indent=2));await self.page.set_viewport_size({'width':1440,'height':1000})
 async def test_06_real_library_editor_review_history_errors_responsive_and_keyboard(self):
  await setup.UltimateCaseSetupTests.model(self,'J101 Histórico de prueba');await self.start('J101 Operación premium');await self.fill(two=True);await self.frame('editor')
  published=await self.publish();await self.frame('review');await self.page.get_by_role('button',name='Ver historial',exact=True).click();await self.loaded();await self.frame('history')
  await self.page.locator('.j101-back').click();await self.loaded();await self.frame('library')
  await self.page.get_by_label('Buscar por nombre',exact=True).fill('J101 Operación premium');await self.page.get_by_role('button',name='Buscar',exact=True).click();await expect(self.page.locator('.j101-model-card')).to_have_count(1)
  await self.page.get_by_label('Buscar por nombre',exact=True).fill('NONEXISTENT-J101');await self.page.get_by_role('button',name='Buscar',exact=True).click();await expect(self.page.locator('.j101-empty')).to_contain_text('No hay modelos que coincidan')
  async def fail(route):await route.fulfill(status=503,json={'detail':'J101 error de prueba'})
  await self.page.route('**/api/platform/logistics-models?*',fail);await self.page.get_by_role('button',name='Buscar',exact=True).click();await expect(self.page.locator('.d-recovery')).to_be_visible();await self.frame('error');await self.page.unroute('**/api/platform/logistics-models?*',fail)
  await self.page.get_by_role('button',name='Crear nuevo modelo',exact=True).click();await self.loaded();await self.page.get_by_label('Nombre del modelo *',exact=True).fill('Dirty teclado');await self.page.locator('.j101-back').click();dialog=self.page.get_by_role('dialog');await expect(dialog.get_by_role('button',name='Seguir editando',exact=True)).to_be_focused()
  await self.page.keyboard.press('Shift+Tab');await expect(dialog.get_by_role('button',name='Guardar borrador',exact=True)).to_be_focused();await self.page.keyboard.press('Escape');await expect(dialog).to_have_count(0)
  button=self.page.locator('[data-library-save]');await button.focus();self.assertEqual(await button.evaluate("n=>getComputedStyle(n).outlineStyle"),'solid')
 async def test_07_real_pagination_search_archive_and_non_mutating_history_back(self):
  ids=[]
  for i in range(51):
   model=await self.api('POST','/api/platform/logistics-models',{'id':str(uuid4()),'name':'J101 Pager '+str(i).zfill(2),'configuration':setup.CONFIG});ids.append(model['model']['id'])
  await self.library();await self.page.get_by_label('Buscar por nombre',exact=True).fill('J101 Pager');await self.page.get_by_role('button',name='Buscar',exact=True).click();await expect(self.page.locator('.j101-pager')).to_contain_text('51 modelos')
  observed=[]
  for page in range(3):
   await expect(self.page.locator('.j101-pager')).to_contain_text('Página '+str(page+1));observed+=await self.page.locator('.j101-model-card').evaluate_all('nodes=>nodes.map(n=>n.dataset.modelId)')
   if page<2:await self.page.get_by_role('navigation',name='Páginas de modelos').get_by_role('button',name='Siguiente',exact=True).click()
  self.assertEqual(len(observed),51);self.assertEqual(set(observed),set(ids));await expect(self.page.get_by_role('navigation',name='Páginas de modelos').get_by_role('button',name='Siguiente',exact=True)).to_be_disabled()
  model=await self.api('GET','/api/platform/logistics-models/'+ids[0]);version=await self.api('POST','/api/platform/logistics-models/'+ids[0]+'/versions',{'version_id':str(uuid4()),'expected_revision':model['model']['revision']})
  await self.api('PUT','/api/platform/logistics-models/'+ids[0],{'name':model['model']['name'],'status':'archived','expected_revision':(await self.api('GET','/api/platform/logistics-models/'+ids[0]))['model']['revision'],'configuration':setup.CONFIG})
  await self.library();await self.page.get_by_label('Estado',exact=True).select_option('archived');await expect(self.page.locator('.j101-model-card')).to_have_count(1);await self.page.get_by_role('button',name='Revisar modelo',exact=True).click();await self.loaded();await expect(self.page.locator('[data-review-context=library]')).to_have_attribute('data-review-version',version['version']['id']);await expect(self.page.get_by_role('button',name='Preparar nueva versión',exact=True)).to_have_count(0)
  before=await self.api('GET','/api/platform/logistics-models/'+ids[0]);writes=[];self.page.on('request',lambda r:writes.append(r.url) if r.method in ['POST','PUT','PATCH','DELETE'] and '/api/platform/' in r.url else None)
  await self.page.get_by_role('button',name='Ver historial',exact=True).click();await self.loaded();history_url=self.page.url;await self.page.go_back();await self.loaded();await self.page.go_forward();await expect(self.page).to_have_url(history_url);await self.loaded();self.assertEqual(writes,[]);self.assertEqual(before,await self.api('GET','/api/platform/logistics-models/'+ids[0]))
 async def test_08_two_tabs_server_cas_preserves_local_copy_and_requires_explicit_reload(self):
  await self.start('J101 CAS original');await self.fill();await self.page.locator('[data-library-save]').click();await expect(self.page).not_to_have_url(re.compile('model_id=new'));await self.loaded();mid=parse_qs(urlparse(self.page.url).query)['model_id'][0]
  second=await self.context.new_page();await second.goto(self.base+'/app/ddas/logistics/models?model_id='+mid+'&model_view=edit');await expect(second.locator('.model-wizard-pro')).to_be_visible();await second.get_by_label('Nombre del modelo *',exact=True).fill('J101 CAS otra pestaña');await second.locator('[data-library-save]').click();await expect(second.locator('[data-library-feedback]')).to_contain_text('servidor')
  await self.page.get_by_label('Nombre del modelo *',exact=True).fill('J101 CAS copia conservada');await self.page.locator('[data-library-save]').click();await expect(self.page.locator('[data-library-feedback]')).to_contain_text('Conflicto');await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('J101 CAS copia conservada');self.assertEqual((await self.api('GET','/api/platform/logistics-models/'+mid))['model']['name'],'J101 CAS otra pestaña')
  await self.page.get_by_role('button',name='Descartar copia local y recargar servidor',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Descartar y recargar',exact=True).click();await self.loaded();await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('J101 CAS otra pestaña');await second.close()
 async def test_09_lost_publish_response_recovers_same_intent_without_second_version(self):
  await self.start('J101 Respuesta perdida');await self.fill();await self.confirm();seen=[]
  async def lose(route):
   response=await route.fetch();seen.append(route.request.post_data_json);self.assertEqual(response.status,200);await route.abort('failed')
  await self.page.route('**/api/platform/logistics-models/*/versions',lose)
  await self.page.locator('[data-library-publish]').click();await self.page.get_by_role('dialog').get_by_role('button',name='Publicar esta versión',exact=True).click();await expect(self.page.locator('[data-library-feedback]')).to_have_attribute('role','alert');await expect(self.page.locator('[data-library-publish]')).to_have_text('Reintentar publicación pendiente');self.assertEqual(len(seen),1)
  intent=seen[0];work=parse_qs(urlparse(self.page.url).query)['model_work_id'][0];record=await self.page.evaluate("id=>JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k=>k.endsWith('.'+id))))",work);mid=record['modelId'];self.assertEqual(record['publishIntent'],intent)
  await self.page.unroute('**/api/platform/logistics-models/*/versions',lose);await self.page.locator('[data-library-publish]').click();await expect(self.page.locator('[data-review-context=library]')).to_have_attribute('data-review-version',intent['version_id']);data=await self.api('GET','/api/platform/logistics-models/'+mid);self.assertEqual(len(data['versions']),1);self.assertEqual(data['versions'][0]['id'],intent['version_id'])
 async def test_10_graph_pinned_review_library_v2_and_return_keep_original_resources(self):
  m,v,c=await setup.UltimateCaseSetupTests.case(self);mid=m['model']['id'];cid=c['case']['id'];vid=v['version']['id'];before=await self.snapshot()
  current=await self.api('GET','/api/platform/logistics-models/'+mid);cfg={**setup.CONFIG,'currency_policy':{**setup.CONFIG['currency_policy'],'currency':'USD'}}
  updated=await self.api('PUT','/api/platform/logistics-models/'+mid,{'name':'J101 Graph otra versión','expected_revision':current['model']['revision'],'configuration':cfg});v2=await self.api('POST','/api/platform/logistics-models/'+mid+'/versions',{'version_id':str(uuid4()),'expected_revision':updated['model']['revision']})
  await self.page.goto(self.base+'/app/ddas/logistics/decisions?case_id='+cid);await self.page.locator('[data-ux05-ready=true]').wait_for();await self.page.get_by_role('button',name='Editar Decision Case',exact=True).click();await self.ready(3);await self.page.locator('[data-dation-test=core-step-1]').click();await self.ready(1)
  await expect(self.page.locator('[data-review-context=case_pinned]')).to_have_attribute('data-review-version',vid)
  header=self.page.locator('[data-model-review]>header');await header.focus();self.assertEqual(await header.evaluate('n=>getComputedStyle(n).outlineStyle'),'none')
  await self.page.locator('[data-open-model-library]').click();await self.loaded();card=self.page.locator('.j101-model-card[data-model-id="'+mid+'"]');await card.get_by_role('button',name='Revisar modelo',exact=True).click();await self.loaded();await expect(self.page.locator('[data-review-context=library]')).to_have_attribute('data-review-version',v2['version']['id'])
  await self.page.locator('.j101-back').click();await self.loaded();await self.page.get_by_role('button',name='Volver al contexto de origen',exact=True).click();await self.ready(1);await expect(self.page.locator('[data-review-context=case_pinned]')).to_have_attribute('data-review-version',vid)
  await self.page.locator('.journey-return-link').click();await self.page.locator('[data-ux05-ready=true]').wait_for();self.assertIn('case_id='+cid,self.page.url);self.assertEqual(before,await self.snapshot())
 async def test_11_same_working_copy_is_locked_across_tabs_without_losing_recovery(self):
  await self.start('J101 Copia exclusiva');await self.page.locator('[data-library-save]').click();url=self.page.url
  second=await self.context.new_page();await second.goto(url);await expect(second.locator('#ultimate-models-root')).to_contain_text('Este borrador ya está abierto en otra pestaña');await expect(second.locator('.model-wizard-pro')).to_have_count(0)
  await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('J101 Copia exclusiva');await self.page.locator('.j101-back').click();await self.loaded();await second.reload();await expect(second.get_by_label('Nombre del modelo *',exact=True)).to_have_value('J101 Copia exclusiva');await second.close()
 async def test_12_dirty_dialog_touch_targets_at_every_viewport(self):
  await self.start('J101 Diálogo accesible');await self.page.locator('.j101-back').click();dialog=self.page.get_by_role('dialog');await expect(dialog).to_be_visible();metrics=[]
  for width in [1440,1280,768,375]:
   await self.page.set_viewport_size({'width':width,'height':844});await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
   data=await dialog.evaluate('''d=>({width:innerWidth,scroll:d.scrollWidth,client:d.clientWidth,buttons:[...d.querySelectorAll('button')].map(n=>({text:n.textContent,height:n.getBoundingClientRect().height,width:n.getBoundingClientRect().width}))})''');self.assertLessEqual(data['scroll'],data['client'],data);self.assertTrue(all(n['height']>=44 and n['width']>=44 for n in data['buttons']),data);metrics.append(data)
   await self.page.screenshot(path=str(OUT/('dialog-'+str(width)+'.png')),full_page=True,animations='disabled')
  (OUT/'dialog-geometry.json').write_text(json.dumps(metrics,indent=2));await self.page.keyboard.press('Escape');await expect(dialog).to_have_count(0);await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('J101 Diálogo accesible')
 async def test_13_late_preview_success_or_error_cannot_unlock_a_pending_save(self):
  observations=[]
  for preview_error in [False,True]:
   with self.subTest(preview_error=preview_error):
    preview_seen=asyncio.Event();preview_release=asyncio.Event();save_seen=asyncio.Event();save_release=asyncio.Event()
    async def hold_preview(route):
     response=await route.fetch();preview_seen.set();await preview_release.wait()
     if preview_error:await route.fulfill(status=503,json={'detail':'J101 preview tardío fallido'})
     else:await route.fulfill(response=response)
    async def hold_save(route):
     response=await route.fetch();save_seen.set();await save_release.wait();await route.fulfill(response=response)
    await self.page.route('**/api/platform/logistics-models/contract-preview',hold_preview);await self.page.route('**/api/platform/logistics-models',hold_save)
    try:
     name='J101 Guardado protegido '+str(preview_error);await self.start(name);await self.fill();await asyncio.wait_for(preview_seen.wait(),10)
     original=await self.page.get_by_label('Nombre del modelo *',exact=True).input_value();await self.page.locator('[data-library-save]').click();await asyncio.wait_for(save_seen.wait(),10)
     async with self.page.expect_response(lambda r:r.url.endswith('/contract-preview')):preview_release.set()
     await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
     enabled=await self.page.locator('.j101-editor input:not([disabled]),.j101-editor select:not([disabled]),.j101-editor textarea:not([disabled]),.j101-editor button:not([disabled])').evaluate_all('nodes=>nodes.map(n=>n.name||n.textContent)');self.assertEqual(enabled,[]);await expect(self.page.locator('[data-library-save]')).to_be_disabled();await expect(self.page.locator('[data-library-publish]')).to_be_disabled()
     observations.append({'preview_error':preview_error,'enabled_while_save_pending':enabled});save_release.set();await expect(self.page).not_to_have_url(re.compile('model_id=new'));await self.loaded();await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value(original)
     mid=parse_qs(urlparse(self.page.url).query)['model_id'][0];self.assertEqual((await self.api('GET','/api/platform/logistics-models/'+mid))['model']['name'],original)
    finally:
     preview_release.set();save_release.set();await self.page.unroute('**/api/platform/logistics-models/contract-preview',hold_preview);await self.page.unroute('**/api/platform/logistics-models',hold_save)
  (OUT/'pending-save-preview.json').write_text(json.dumps(observations,indent=2))

class DefaultLibraryGateTests(R4Browser):
 async def test_default_closed_retains_legacy_library_and_rejects_new_mode_links(self):
  await self.page.goto(self.base+'/app/ddas/logistics/models');await expect(self.page.locator('#ultimate-models-root')).to_have_attribute('data-ultimate-ready','true');await expect(self.page.get_by_role('button',name='Crear Model',exact=True)).to_be_visible();await expect(self.page.get_by_role('button',name='Crear nuevo modelo',exact=True)).to_have_count(0)
  await self.page.goto(self.base+'/app/ddas/logistics/models?model_id=new&model_view=edit&model_work_id='+str(uuid4()));await expect(self.page.locator('#ultimate-models-root')).to_contain_text('La biblioteca J1.01 todavía no está activada');await expect(self.page.locator('.model-wizard-pro')).to_have_count(0)
