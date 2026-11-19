"""R4 owned SQL/API fixture, never production or engine activation."""
import asyncio,json,os,subprocess,unittest
from pathlib import Path
from playwright.async_api import expect
import test_ultimate_case_setup as setup
import r4_model_helpers as fixture
import guided_model_helpers as blocks
OUT=Path('/tmp/dation-saga10-5-r4-browser');OUT.mkdir(exist_ok=True)
class R4Tests(fixture.R4Browser):
 async def test_01_progressive_one_two_edit_and_shared_physics(self):
  await self.start();await self.fill_unit();two=self.page.locator('[data-pro-step="2"]')
  await expect(two.locator('[data-load-type]')).to_have_count(0);await self.fill_product()
  await expect(two).to_contain_text('0,0225 m³');await expect(two.locator('[data-cargo-metric=gross]')).to_contain_text('745 kg')
  await self.save();await expect(two.locator('[name=product_name]')).to_have_value('');await expect(two.locator('[data-load-type]')).to_have_count(1)
  await self.fill_product('Aceite de oliva','8','80','20','30');await expect(two).to_contain_text('0,018 m³');await expect(two.locator('[data-cargo-metric=gross]')).to_contain_text('665 kg');await self.save()
  await expect(two.locator('[data-load-type]')).to_have_count(2);await expect(two.locator('[data-save-load-type]')).to_be_disabled();await expect(two.locator('[name=product_name]')).to_have_value('')
  before=(await self.draft())['configuration']['cargo'];self.assertEqual(len(before['products']),2);self.assertEqual(len(before['logistic_units']),1)
  await two.locator('[data-load-type]').first.click();await expect(two.locator('[data-save-load-type]')).to_have_text('Actualizar tipo de carga');await expect(two.locator('[data-save-load-type]')).to_be_disabled()
  await two.locator('[name=product_mass]').fill('13');await self.save();after=(await self.draft())['configuration']['cargo']
  self.assertEqual([p['presentation_id'] for p in after['presentations']],[p['presentation_id'] for p in before['presentations']]);self.assertEqual([p['product_id'] for p in after['products']],[p['product_id'] for p in before['products']]);self.assertEqual(after['products'][1],before['products'][1]);await expect(two.locator('[data-load-type]').first).to_contain_text('805 kg')
  await two.locator('[data-load-type]').first.click();await two.locator('[name=product_mass]').fill('12');await self.save()
  await self.page.locator('[name=unit_height]').fill('160');await expect(two.locator('[data-load-type]').first).to_contain_text('1,92 m³');await expect(two.locator('[data-load-type]').last).to_contain_text('1,92 m³')
  await self.page.locator('[name=unit_tare]').fill('30');await expect(two.locator('[data-load-type]').first).to_contain_text('750 kg');await expect(two.locator('[data-load-type]').last).to_contain_text('670 kg')
  await self.page.locator('[name=unit_height]').fill('150');await self.page.locator('[name=unit_tare]').fill('25')
  await self.page.reload();await self.ready(1);await blocks.block(self.page,3);await expect(self.page.locator('[data-load-type]')).to_have_count(2)
  cfg=await self.publish();(OUT/'published-dto.json').write_text(json.dumps(cfg,indent=2));await self.page.locator('[data-dation-test=core-step-1]').click();await self.ready(1);await blocks.block(self.page,3)
  await expect(self.page.locator('[data-pro-step]')).to_have_count(3);await expect(self.page.locator('.model-wizard-v2 input:enabled,.model-wizard-v2 select:enabled')).to_have_count(0)
  self.assertEqual(self.errors,[])
 async def test_02_errors_unsaved_buffer_discard_and_double_click(self):
  await self.start();two=self.page.locator('[data-pro-step="2"]');await self.fill_unit();await self.fill_product(q='1.5')
  await self.save();await expect(two.locator('[name=product_quantity]')).to_have_attribute('aria-invalid','true');await expect(two.locator('[data-load-type]')).to_have_count(0);await expect(two.locator('[name=product_name]')).to_have_value('Vino Malbec')
  for key,value in [('product_mass','0'),('product_width',''),('product_quantity','0')]:
   await two.locator('[name='+key+']').fill(value);await self.save();await expect(two.locator('[name='+key+']')).to_have_attribute('aria-invalid','true');await expect(two.locator('[data-load-type]')).to_have_count(0)
  await self.fill_product();await two.locator('[data-save-load-type]').dblclick();await expect(two.locator('[data-load-type]')).to_have_count(1)
  await self.fill_product();await self.save();await expect(two.locator('[name=product_name]')).to_have_attribute('aria-invalid','true');await expect(two.locator('[data-load-type]')).to_have_count(1)
  await self.fill_product('Aceite de oliva','8','80','20','30');pending=await self.stored();await self.page.reload();await self.ready(1);await blocks.block(self.page,3)
  await expect(two.locator('[name=product_name]')).to_have_value('Aceite de oliva');self.assertEqual((await self.draft())['configuration']['cargo']['products'],pending['value']['planning_model']['new_model']['configuration']['cargo']['products'])
  cta=self.page.locator('[data-confirm-block="3"]');await cta.click();await expect(self.page.locator('[data-error-for=cargo_catalog]')).to_contain_text('Guardá los cambios');await expect(cta).to_be_enabled()
  await two.locator('[data-load-type]').first.click();dialog=self.page.get_by_role('dialog');await dialog.get_by_role('button',name='Cancelar',exact=True).click();await expect(two.locator('[name=product_name]')).to_have_value('Aceite de oliva')
  await two.locator('[data-load-type]').first.click();await self.page.get_by_role('dialog').get_by_role('button',name='Descartar cambios',exact=True).click();await expect(two.locator('[name=product_name]')).to_have_value('Vino Malbec');await expect(two.locator('[data-save-load-type]')).to_be_disabled()
  await two.locator('[name=product_mass]').fill('13');await self.page.reload();await self.ready(1);await blocks.block(self.page,3);await expect(two.locator('[name=product_mass]')).to_have_value('13');self.assertEqual((await self.draft())['configuration']['cargo']['products'][0]['gross_mass']['value'],'12')
  self.assertFalse(any(m=='POST' and (u.endswith('/versions') or u.endswith('/logistics-models')) for m,u in self.operations))
 async def test_03_all_five_confirmation_cycles_and_dependencies(self):
  await self.start();await self.fill();await self.confirm();records=[]
  await self.page.evaluate("()=>{window.r4Reviewed=0;document.querySelector('.model-wizard-v2').addEventListener('model-review',()=>window.r4Reviewed++)}")
  for i in range(1,6):
   node=await blocks.block(self.page,i);cta=node.locator('[data-confirm-block="'+str(i)+'"]');before=len(self.operations)
   await cta.dispatch_event('click');self.assertEqual(len(self.operations),before)
   records.append(await cta.evaluate("n=>({block:n.dataset.confirmBlock,disabled:n.disabled,state:n.dataset.confirmationState,bg:getComputedStyle(n).backgroundColor,border:getComputedStyle(n).borderColor})"))
  self.assertEqual(await self.page.evaluate('window.r4Reviewed'),0)
  # Every material block edit invalidates its own signature, not UI focus.
  changes=[(1,'[name=model_name]','Renombrado'),(2,'[name=operating_role][value=HYBRID]',None),(3,'[name=unit_tare]','30'),(4,'[name=resource_categories][value=GENERAL]',None),(5,'[name=currency][value=EUR]',None)]
  for i,selector,value in changes:
   node=await blocks.block(self.page,i);control=node.locator(selector);cta=node.locator('[data-confirm-block="'+str(i)+'"]')
   if value is None:await control.focus();await self.page.keyboard.press('Space')
   else:await control.fill(value)
   await expect(cta).to_be_enabled();await expect(node.locator('>summary .guided-status')).to_have_attribute('data-state','pending')
   if i==3:await expect(cta).to_have_attribute('data-preview-current','true')
   await cta.click();await expect(cta).to_be_disabled()
  # A change in sources must invalidate B05, while B05 does not invalidate B04.
  four=await blocks.block(self.page,4);await four.locator('[name=sources][value=OWN]').focus();await self.page.keyboard.press('Space')
  await expect(self.page.locator('[data-confirm-block="5"]')).to_be_enabled()
  await four.locator('[data-confirm-block="4"]').click();await blocks.block(self.page,5);await self.page.locator('[data-confirm-block="5"]').click();await expect(four.locator('[data-confirm-block="4"]')).to_be_disabled()
  await self.page.reload();await self.ready(1);await expect(self.page.locator('[data-confirm-block="3"]')).to_have_attribute('data-preview-current','true')
  for i in range(1,6):await expect(self.page.locator('[data-confirm-block="'+str(i)+'"]')).to_be_disabled()
  stale=await self.stored();stale['value']['planning_model']['new_model']['guided_ux']['confirmed']['0']='FOREIGN_DRAFT'
  await self.page.evaluate('v=>sessionStorage.setItem(v.key,JSON.stringify(v.value))',stale);await self.page.reload();await self.ready(1);await expect(self.page.locator('[data-confirm-block="1"]')).to_be_enabled()
  for i in [2,4,5]:await expect(self.page.locator('[data-confirm-block="'+str(i)+'"]')).to_be_disabled()
  await self.confirm();self.assertEqual(self.errors,[])
  (OUT/'cta-states.json').write_text(json.dumps(records,indent=2))
 async def test_04_five_units_metre_volume_and_cancel_safe(self):
  await self.start();await self.fill(two=True);first=self.page.locator('[data-pro-step="1"]');initial=(await self.draft())['configuration']['cargo'];ids=[p['presentation_id'] for p in initial['presentations']]
  for kind in ['BOX','CRATE','BIG_BAG','OTHER','PALLET']:
   radio=first.locator('[name=guided_unit_type][value='+kind+']');await radio.focus();await self.page.keyboard.press('Space');await self.page.get_by_role('dialog').get_by_role('button',name='Cancelar',exact=True).click()
   self.assertEqual((await self.draft())['configuration']['cargo']['logistic_units'][0]['type'],'PALLET' if kind=='BOX' else previous)
   await radio.focus();await self.page.keyboard.press('Space');await self.page.get_by_role('dialog').get_by_role('button',name='Cambiar unidad',exact=True).click();previous=kind
   await expect(first.locator('[data-support-art=empty]')).to_have_attribute('data-unit-type',kind)
   self.assertNotEqual(await first.locator('[data-support-art=empty]').inner_html(),await self.page.locator('[data-support-art=loaded]').first.inner_html())
   if kind in ['BIG_BAG','OTHER']:
    await first.locator('[name=unit_volume]').fill('');await self.page.locator('[data-confirm-block="3"]').click();await expect(self.page.locator('[data-error-for=cargo_catalog]')).to_contain_text('Completá')
    await first.locator('[name=unit_volume]').fill('1.8');c=(await self.draft())['configuration']['cargo'];self.assertTrue(all(p['loaded_dimensions'] is None and p['external_volume']['value']=='1.8' for p in c['presentations']))
   self.assertEqual([p['presentation_id'] for p in (await self.draft())['configuration']['cargo']['presentations']],ids)
  await first.locator('[name=unit_measure]').select_option('m')
  for key,value in [('unit_length','1.2'),('unit_width','1'),('unit_height','1.5')]:await first.locator('[name='+key+']').fill(value)
  await expect(first.locator('[data-cargo-metric=volume]')).to_contain_text('1,8 m³');self.assertEqual(self.errors,[])
 async def test_05_reset_discard_refresh_and_pending_publication(self):
  await self.start();await self.fill(two=True);await self.confirm();before=await self.stored()
  await self.page.get_by_role('button',name='Crear nuevo modelo',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Cancelar',exact=True).click();self.assertEqual((await self.stored())['value'],before['value'])
  await self.page.get_by_role('button',name='Crear nuevo modelo',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Crear nuevo modelo',exact=True).click()
  await expect(self.page.locator('[data-load-type]')).to_have_count(0);await expect(self.page.locator('.guided-status[data-state=complete]')).to_have_count(0);await expect(self.page.locator('[name=product_name]')).to_have_value('');self.assertNotEqual((await self.draft())['id'],before['value']['planning_model']['new_model']['id'])
  await self.page.reload();await self.ready(1);await expect(self.page.locator('[name=model_name]')).to_have_value('');self.assertEqual((await self.draft())['configuration']['cargo']['products'],[])
  await self.page.locator('[name=model_name]').fill('Nuevo aislado');await blocks.block(self.page,3);await self.fill();await self.confirm()
  await self.page.route('**/api/platform/logistics-models/*/versions',lambda route:route.fulfill(status=503,json={'detail':'QA retry publication'}),times=1)
  await self.page.locator('[data-dation-test=model-create]').click();await expect(self.page.locator('[data-dation-test=model-feedback]')).to_contain_text('QA retry publication');await expect(self.page.locator('[data-model-new]')).to_be_disabled()
  intent=(await self.stored())['value']['planning_model']['intent'];await self.page.reload();await self.ready(1);await expect(self.page.locator('[data-model-new]')).to_be_disabled();await self.page.locator('[data-dation-test=model-create]').click();await self.ready(2)
  after=(await self.stored())['value']['planning_model'];self.assertEqual(after['model_id'],intent['model_id']);self.assertEqual(after['version_id'],intent['version_id']);self.assertEqual(sum(m=='POST' and u.endswith('/logistics-models') for m,u in self.operations),1);self.assertEqual(sum(m=='POST' and u.endswith('/versions') for m,u in self.operations),2)
 async def test_06_stale_preview_error_retry_no_local_publication(self):
  await self.start();await self.fill();await self.confirm();await blocks.block(self.page,3);entered=asyncio.Event();release=asyncio.Event()
  async def hold(route):
   if route.request.post_data_json.get('configuration',{}).get('cargo',{}).get('logistic_units',[{}])[0].get('tare_mass',{}).get('value')=='26':entered.set();await release.wait()
   await route.continue_()
  await self.page.route('**/logistics-models/contract-preview',hold);await self.page.locator('[name=unit_tare]').fill('26');await asyncio.wait_for(entered.wait(),10)
  await self.page.locator('[name=unit_tare]').fill('-1');release.set();await expect(self.page.locator('[data-confirm-block="3"]')).to_have_attribute('data-preview-current','false');await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
  await self.page.unroute('**/logistics-models/contract-preview',hold)
  async def unavailable(route):await route.fulfill(status=503,json={'detail':'QA unavailable'})
  await self.page.route('**/logistics-models/contract-preview',unavailable);await self.page.locator('[name=unit_tare]').fill('27');await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('QA unavailable')
  await self.page.get_by_role('button',name='Reintentar Data Contract',exact=True).click();await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_be_focused()
  await self.page.unroute('**/logistics-models/contract-preview',unavailable);await self.page.get_by_role('button',name='Reintentar Data Contract',exact=True).click();await self.confirm()
  self.assertFalse(any(m=='POST' and (u.endswith('/versions') or u.endswith('/logistics-models')) for m,u in self.operations));self.assertEqual(self.errors,[])
 async def test_07_three_csv_case_graph_review_three_returns_and_new(self):
  import test_saga10_wizard as saga
  import test_unified_decision_journey as journey
  from urllib.parse import urlparse,parse_qs
  await self.start();await self.fill(two=True);cfg=await self.publish();state=(await self.stored())['value']['planning_model'];mid=state['model_id'];vid=state['version_id']
  self.m={'model':{'id':mid}};self.v={'version':{'id':vid}}
  for entity in ['transport_demand','order_lines','transport_resources']:await saga.Saga10WizardTests.upload(self,entity)
  await expect(self.page.locator('[data-journey-next]')).to_be_enabled();await self.page.locator('[data-journey-next]').click();await self.ready(3)
  await journey.UnifiedDecisionJourneyTests.fill_case(self,'R4 recorrido publicado')
  await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click();await self.page.locator('[data-ux05-ready=true]').wait_for();cid=parse_qs(urlparse(self.page.url).query)['case_id'][0]
  original=await self.api('GET','/api/platform/logistics-models/'+mid);writes=[];self.page.on('request',lambda r:writes.append(r.url) if r.method=='POST' and (r.url.endswith('/versions') or r.url.endswith('/logistics-models')) else None)
  for i in range(3):
   await self.page.get_by_role('button',name='Editar datos de origen',exact=True).click();await self.ready(2);await self.page.locator('[data-dation-test=core-step-1]').click();await self.ready(1);await blocks.block(self.page,3)
   await expect(self.page.locator('[data-pro-step]')).to_have_count(3);await expect(self.page.locator('[data-cargo-step]')).to_have_count(0);await expect(self.page.locator('.model-wizard-v2 input:enabled,.model-wizard-v2 select:enabled,.model-wizard-v2 [data-save-load-type]:enabled')).to_have_count(0)
   await expect(self.page.locator('[data-pro-step="2"]')).to_contain_text('Configuración de solo lectura. Los tipos de carga se conservan sin cambios.');self.assertNotIn('Seleccioná una tarjeta inferior',await self.page.locator('[data-pro-step="2"]').text_content())
   await self.page.screenshot(path=str(OUT/f'published-review-return-{i}.png'),full_page=True,animations='disabled')
   current=await self.api('GET','/api/platform/logistics-models/'+mid);self.assertEqual(current,original)
   await self.page.locator('.journey-return-link').click();await self.page.locator('[data-ux05-ready=true]').wait_for();self.assertEqual(parse_qs(urlparse(self.page.url).query)['case_id'],[cid])
  self.assertEqual(writes,[])
  await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1);await self.page.locator('[data-model-new]').click()
  if await self.page.get_by_role('dialog').count():await self.page.get_by_role('dialog').get_by_role('button',name='Crear nuevo modelo',exact=True).click()
  await expect(self.page.locator('[data-load-type]')).to_have_count(0);await expect(self.page.locator('[name=model_name]')).to_have_value('');await expect(self.page.locator('.guided-status[data-state=complete]')).to_have_count(0)
  self.assertEqual(await self.api('GET','/api/platform/logistics-models/'+mid),original)
  result=subprocess.run([setup.RUNTIME_PYTHON,str(Path(__file__).with_name('r4_domain_probe.py'))],cwd=Path(__file__).resolve().parents[2],input=json.dumps(cfg),text=True,capture_output=True,env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[2]),'DATION_EXECUTION_MODE':'legacy'})
  self.assertEqual(result.returncode,0,result.stderr);(OUT/'d1-and-contract.txt').write_text(result.stdout)
 async def test_08_legacy_contracts_preserved_without_catalog_manager(self):
  import hashlib
  from uuid import uuid4
  code="from tests.saga10_fixtures import catalog_config,direct_config,bulk_config;import json;print(json.dumps([direct_config(),catalog_config(),bulk_config()]))"
  result=subprocess.run([setup.RUNTIME_PYTHON,'-c',code],cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
  records=[]
  for i,cfg in enumerate(json.loads(result.stdout)):
   if i:
    await self.page.goto(self.base+'/app');await self.page.evaluate("()=>{for(const k of Object.keys(sessionStorage))if(k.startsWith('dation.ultimate.setup.v1.')&&k.endsWith('.case.new'))sessionStorage.removeItem(k)}")
   m=await self.api('POST','/api/platform/logistics-models',{'id':str(uuid4()),'name':'Histórico R4 '+str(i),'configuration':cfg});v=await self.api('POST','/api/platform/logistics-models/'+m['model']['id']+'/versions',{'version_id':str(uuid4()),'expected_revision':1})
   await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1);await self.page.get_by_role('button',name='Seleccionar modelo existente',exact=True).click();dialog=self.page.get_by_role('dialog');await dialog.get_by_label('Logistics Model',exact=True).select_option(m['model']['id']);await expect(dialog.get_by_role('button',name='Seleccionar esta versión',exact=True)).to_be_enabled();await dialog.get_by_role('button',name='Seleccionar esta versión',exact=True).click();await self.ready(2)
   await self.page.locator('[data-dation-test=core-step-1]').click();await self.ready(1);await blocks.block(self.page,3)
   await expect(self.page.locator('[data-historical-review]')).to_be_visible();await expect(self.page.locator('[data-cargo-step]')).to_have_count(0);await expect(self.page.locator('[data-editor-choice]')).to_have_count(0);await expect(self.page.locator('[data-historical-review] input,[data-historical-review] select,[data-historical-review] button')).to_have_count(0)
   current=await self.api('GET','/api/platform/logistics-models/'+m['model']['id']);published=current['versions'][0]['config_jsonb'];self.assertEqual(published,v['version']['config_jsonb']);records.append({'case':i,'sha256':hashlib.sha256(json.dumps(published,sort_keys=True).encode()).hexdigest(),'products':len(published['cargo']['products']),'presentations':len(published['cargo']['presentations'])})
   await self.page.screenshot(path=str(OUT/f'legacy-readonly-{i}.png'),full_page=True,animations='disabled')
  (OUT/'legacy-integrity.json').write_text(json.dumps(records,indent=2))
 async def test_09_dom_inventory_responsive_geometry_accessibility_and_screenshots(self):
  await self.start();await self.fill(two=True);await self.confirm();await blocks.block(self.page,3)
  deny=['Presentación activa','Soporte compartido','Agregar presentación','Agregar unidad logística','Agregar producto','Duplicar','Eliminar presentación','Eliminar producto','Eliminar unidad','Nombre de la presentación','Perfil de carga','Configuración avanzada compatible','Compatibilidad y co-carga avanzadas','Dimensión principal de reporte','Aplicar sugerencia','Continuar']
  cargo=self.page.locator('[data-dation-test=model-v2-block-3]');text=await cargo.text_content()
  for label in deny:self.assertNotIn(label,text)
  await expect(cargo.locator('[data-pro-step]')).to_have_count(3);await expect(cargo.locator('[data-cargo-step],details')).to_have_count(0);await expect(cargo.locator('[name=guided_unit_type]')).to_have_count(5);await expect(cargo.locator('[name=dimensions]')).to_have_count(2)
  await expect(cargo.locator('[data-pro-step="3"] > .guided-pro-step-body > .guided-note')).to_have_count(3)
  self.assertEqual(await cargo.locator('button').count(),4) # two saved-card selection controls + exactly two CTAs
  geometry=[];audits=[]
  for width in [1536,1024,768,390,320]:
   await self.page.set_viewport_size({'width':width,'height':1000});await self.page.evaluate('document.fonts.ready');await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
   metrics=await self.page.evaluate('''()=>({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,ctas:[...document.querySelectorAll('[data-confirm-block]')].map(n=>{const r=n.getBoundingClientRect();return {w:r.width,h:r.height,gap:n.parentElement.getBoundingClientRect().right-r.right}}),historyBelow:(()=>{const h=document.querySelector('[data-load-history]'),s=document.querySelector('[data-save-load-type]');return h.getBoundingClientRect().top>=s.getBoundingClientRect().bottom})(),units:[...document.querySelectorAll('[name=guided_unit_type]')].map(n=>n.closest('label').getBoundingClientRect().top)})''')
   self.assertFalse(metrics['overflow'],metrics);self.assertTrue(metrics['historyBelow'],metrics);self.assertLessEqual(max(c['w'] for c in metrics['ctas'])-min(c['w'] for c in metrics['ctas']),1);self.assertLessEqual(max(c['h'] for c in metrics['ctas'])-min(c['h'] for c in metrics['ctas']),1)
   if width==1536:self.assertLessEqual(max(metrics['units'])-min(metrics['units']),1)
   geometry.append(metrics)
   audit=await self.page.evaluate(Path(__file__).with_name('theme_audit.js').read_text(),'.model-wizard-v2');self.assertEqual(audit['failures'],[],audit['failures']);self.assertFalse(audit['overflow']);audits.append({'width':width,**audit})
   for i in range(1,6):
    for j in range(1,6):
     node=self.page.locator('[data-dation-test=model-v2-block-'+str(j)+']')
     if (await node.get_attribute('open') is not None)!=(i==j):await node.locator('>summary').click()
    await self.page.evaluate('scrollTo(0,0)');await self.page.screenshot(path=str(OUT/f'actual-B0{i}-{width}.png'),full_page=True,animations='disabled')
   for i in range(1,6):await blocks.block(self.page,i)
  (OUT/'geometry.json').write_text(json.dumps(geometry,indent=2));(OUT/'a11y.json').write_text(json.dumps(audits,indent=2))
  await blocks.block(self.page,3);card=cargo.locator('[data-load-type]').first;await card.focus();await self.page.keyboard.press('Enter');await expect(self.page.locator('[name=product_name]')).to_be_focused();await expect(self.page.locator('[name=product_name]')).to_have_value('Vino Malbec')
  await cargo.locator('[data-load-type]').last.focus();await self.page.keyboard.press('Space');await expect(self.page.locator('[name=product_name]')).to_have_value('Aceite de oliva')
  await self.page.emulate_media(reduced_motion='reduce');self.assertEqual(await cargo.locator('.guided-radio-card').first.evaluate('n=>getComputedStyle(n).transitionDuration'),'0s')
  (OUT/'dom-audit.json').write_text(json.dumps({'deny':deny,'absent':True,'steps':3,'unit_radios':5,'capacity_checks':2,'internal_cta':1,'footer_cta':1,'history_cards':2},indent=2));self.assertEqual(self.errors,[])
 async def test_10_dimensions_primary_split_and_independent_publication(self):
  await self.start();await self.fill();three=self.page.locator('[data-pro-step="3"]')
  for key in ['weight_kg','volume_m3']:await three.locator('[name=dimensions][value='+key+']').uncheck()
  await self.page.locator('[data-confirm-block="3"]').click();await expect(self.page.locator('[data-error-for=cargo_catalog]')).to_contain_text('dimensión principal');await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
  await three.locator('[name=dimensions][value=volume_m3]').check();await three.locator('[name=cargo_split_policy][value=DISCRETE]').focus();await self.page.keyboard.press('Space')
  cfg=await self.publish();self.assertEqual(cfg['active_dimensions'],['volume_m3']);self.assertEqual(cfg['primary_dimension'],'volume_m3');self.assertTrue(cfg['split_permitted']);self.assertEqual(cfg['cargo']['split_policy'],'DISCRETE');self.assertNotIn('pallets',cfg['active_dimensions'])
  self.assertEqual(len(cfg['cargo']['presentations']),1);self.assertEqual(len(cfg['cargo']['products']),1)
 async def test_11_incompatible_draft_and_recovery_checkpoint(self):
  await self.start();original=await self.stored();fresh=json.loads(json.dumps(original['value']['planning_model']['new_model']));value=original['value'];d=value['planning_model']['new_model'];d['name']='Histórico directo';c=d['configuration'];c['active_dimensions']=['pallets'];c['primary_dimension']='pallets';c['cargo']['input_mode']='direct';d['guided_ux']={'edition':'compatible','confirmed':{}}
  before=json.loads(json.dumps(d));await self.page.evaluate('v=>sessionStorage.setItem(v.key,JSON.stringify(v.value))',original);await self.page.reload();await self.ready(1)
  await expect(self.page.locator('[data-historical-review]')).to_be_visible();await expect(self.page.locator('[data-cargo-step],[data-continue-compatible]')).to_have_count(0);self.assertEqual((await self.draft())['configuration'],before['configuration'])
  await self.page.locator('[data-model-new]').click();await self.page.get_by_role('dialog').get_by_role('button',name='Cancelar',exact=True).click();self.assertEqual((await self.draft())['configuration'],before['configuration'])
  # Read an existing R3 recovery checkpoint, without inventing a conversion.
  value['planning_model']['recovery']=before;value['planning_model']['new_model']=fresh;await self.page.evaluate('v=>sessionStorage.setItem(v.key,JSON.stringify(v.value))',original);await self.page.reload();await self.ready(1)
  await self.page.get_by_role('button',name='Restaurar borrador anterior',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Restaurar borrador',exact=True).click();await expect(self.page.locator('[data-historical-review]')).to_be_visible();self.assertEqual((await self.draft())['configuration'],before['configuration'])
  await self.page.locator('[data-model-new]').click();await self.page.get_by_role('dialog').get_by_role('button',name='Crear nuevo modelo',exact=True).click();await expect(self.page.locator('[data-pro-step]')).to_have_count(3);await expect(self.page.locator('[data-load-type]')).to_have_count(0)
  await self.page.reload();await self.ready(1);await expect(self.page.locator('[data-historical-review]')).to_have_count(0);self.assertEqual((await self.draft())['configuration']['cargo']['products'],[])
 async def test_12_new_from_published_preserves_identity(self):
  await self.start();await self.fill(two=True);await self.publish();old=(await self.stored())['value']['planning_model'];mid=old['model_id'];original=await self.api('GET','/api/platform/logistics-models/'+mid)
  await self.page.locator('[data-dation-test=core-step-1]').click();await self.ready(1);await expect(self.page.locator('.model-wizard-v2 input:enabled,.model-wizard-v2 select:enabled,[data-confirm-block]:enabled')).to_have_count(0)
  await self.page.locator('[data-model-new]').click();await expect(self.page.locator('[name=model_name]')).to_have_value('');await expect(self.page.locator('[data-load-type]')).to_have_count(0);await expect(self.page.locator('.guided-status[data-state=complete]')).to_have_count(0)
  new=await self.draft();self.assertNotEqual(new['id'],mid);self.assertEqual(new['configuration']['cargo']['products'],[]);self.assertEqual(new['guided_ux']['confirmed'],{})
  await self.page.reload();await self.ready(1);self.assertEqual((await self.draft())['id'],new['id']);self.assertEqual(await self.api('GET','/api/platform/logistics-models/'+mid),original)
 async def test_13_legacy_direct_uses_two_csv_without_dummy_catalog(self):
  from uuid import uuid4
  code="from tests.saga10_fixtures import direct_config;import json;print(json.dumps(direct_config()))"
  result=subprocess.run([setup.RUNTIME_PYTHON,'-c',code],cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr);cfg=json.loads(result.stdout)
  m=await self.api('POST','/api/platform/logistics-models',{'id':str(uuid4()),'name':'Directo preservado','configuration':cfg});v=await self.api('POST','/api/platform/logistics-models/'+m['model']['id']+'/versions',{'version_id':str(uuid4()),'expected_revision':1})
  await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1);await self.page.get_by_role('button',name='Seleccionar modelo existente',exact=True).click();dialog=self.page.get_by_role('dialog');await dialog.get_by_label('Logistics Model',exact=True).select_option(m['model']['id']);await expect(dialog.get_by_role('button',name='Seleccionar esta versión',exact=True)).to_be_enabled();await dialog.get_by_role('button',name='Seleccionar esta versión',exact=True).click();await self.ready(2)
  await expect(self.page.locator('[data-dation-test=contract-cards]>.data-contract-card')).to_have_count(2);self.assertEqual(v['version']['config_jsonb']['cargo']['products'],[]);self.assertEqual(v['version']['config_jsonb']['cargo']['presentations'],[])
  await self.page.locator('[data-dation-test=core-step-1]').click();await self.ready(1);await expect(self.page.locator('[data-historical-review]')).to_be_visible();await expect(self.page.locator('[data-cargo-step]')).to_have_count(0)
 async def test_14_real_progressive_visual_states(self):
  await self.start();await self.fill_unit();cargo=self.page.locator('[data-dation-test=model-v2-block-3]')
  async def capture(state):
   for width in [1536,390]:
    await self.page.set_viewport_size({'width':width,'height':1000});await self.page.evaluate('document.fonts.ready');await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');await self.page.evaluate('document.activeElement?.blur();scrollTo(0,0)');await self.page.mouse.move(0,0);await self.page.screenshot(path=str(OUT/f'progressive-{state}-{width}.png'),full_page=True,animations='disabled')
   await self.page.set_viewport_size({'width':1536,'height':1000})
  await capture('0-empty');await self.fill_product();await self.save();await expect(self.page.locator('[name=product_name]')).to_have_value('');await capture('1-saved')
  await self.fill_product('Aceite de oliva','8','80','20','30');await self.save();await expect(self.page.locator('[data-save-load-type]')).to_be_disabled();await capture('2-full')
  await self.page.locator('[data-load-type]').first.click();await expect(self.page.locator('[data-save-load-type]')).to_have_text('Actualizar tipo de carga');await capture('3-editing')
  self.assertEqual(self.errors,[])
