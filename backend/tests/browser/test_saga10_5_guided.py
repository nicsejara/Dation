"""Historical contract regressions: R4 deliberately replaces legacy editing with
faithful read-only review. Business validation still uses the actual API/domain.
See docs/development/saga10-5-r4/TEST_MIGRATION.md.
"""
import asyncio,json,os,subprocess,unittest
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
from playwright.async_api import expect
import test_ultimate_case_setup as setup
import r4_model_helpers as r4
import guided_model_helpers as guided
OUT=Path('/tmp/dation-saga10-5-browser');OUT.mkdir(exist_ok=True)
class Saga10GuidedTests(r4.R4Browser):
 async def config(self,kind='catalog'):
  code="import json;from tests.saga10_fixtures import catalog_config,direct_config,bulk_config;print(json.dumps("+kind+"_config()))"
  result=subprocess.run([setup.RUNTIME_PYTHON,'-c',code],cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr);return json.loads(result.stdout)
 async def historical(self,cfg):
  m=await self.api('POST','/api/platform/logistics-models',{'id':str(uuid4()),'name':'Contrato histórico QA','configuration':cfg});v=await self.api('POST','/api/platform/logistics-models/'+m['model']['id']+'/versions',{'version_id':str(uuid4()),'expected_revision':1})
  await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1);await self.page.get_by_role('button',name='Seleccionar modelo existente',exact=True).click();dialog=self.page.get_by_role('dialog');await dialog.get_by_label('Logistics Model',exact=True).select_option(m['model']['id']);await expect(dialog.get_by_role('button',name='Seleccionar esta versión',exact=True)).to_be_enabled();await dialog.get_by_role('button',name='Seleccionar esta versión',exact=True).click();await self.ready(2)
  await self.page.locator('[data-dation-test=core-step-1]').click();await self.ready(1);await guided.block(self.page,3)
  await expect(self.page.locator('[data-historical-review]')).to_be_visible();await expect(self.page.locator('[data-cargo-step],[data-continue-compatible]')).to_have_count(0);await expect(self.page.locator('[data-historical-review] input,[data-historical-review] select,[data-historical-review] button')).to_have_count(0)
  self.assertEqual((await self.api('GET','/api/platform/logistics-models/'+m['model']['id']))['versions'][0]['config_jsonb'],v['version']['config_jsonb']);return m,v
 async def component(self,cfg):
  await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
  result=await self.page.evaluate('''async configuration=>{const {mountModelFieldsV2}=await import('/static/js/dispatch/models/model-fields-v2.mjs');const root=document.querySelector('.model-wizard-v2').parentElement;root.replaceChildren();const controller=new AbortController(),scope={signal:controller.signal,listen(n,k,f){n.addEventListener(k,f,{signal:controller.signal});},own(){}};const original={id:'historical',name:'Histórico íntegro',configuration,guided_ux:{edition:'compatible'}};const view=mountModelFieldsV2(root,scope,original,{published:true});view.lock({published:true});return view.read();}''',cfg)
  self.assertEqual(result['configuration'],cfg);await expect(self.page.locator('[data-cargo-step]')).to_have_count(0);await expect(self.page.locator('[data-historical-review] input,[data-historical-review] select,[data-historical-review] button')).to_have_count(0);return result
 async def test_01_direct_review_is_explicit_and_resets(self):
  await r4.scenario(self,'test_13_legacy_direct_uses_two_csv_without_dummy_catalog')
 async def test_02_mixed_catalog_correct_physics_and_shared_unit(self):
  c=await self.config();g=c['cargo'];g['products']=[{'product_id':k,'name':k,'unit_label':'sobre','units_per_package':216,'gross_mass':{'value':mass,'unit':'kg'}} for k,mass in [('NAR','8'),('MAN','10'),('DUR','6')]];g['presentations']=g['presentations'][:1];p=g['presentations'][0];p.pop('gross_mass',None);p['components']=[{'product_id':k,'quantity':q} for k,q in [('NAR','32'),('MAN','24'),('DUR','24')]];p['loaded_dimensions']['height']='150'
  m,v=await self.historical(c);preview=await self.api('POST','/api/platform/logistics-models/contract-preview',{'model_id':m['model']['id'],'version_id':v['version']['id']});physical=preview['contracts']['transport_demand']['rules']['catalog_snapshot'][p['presentation_id']];self.assertEqual(physical['coefficients']['weight_kg'],'665');self.assertEqual(physical['coefficients']['volume_m3'],'1.8');self.assertEqual(len(v['version']['config_jsonb']['cargo']['presentations'][0]['components']),3)
 async def test_03_profiles_and_legacy_draft_survive_reload(self):
  c=await self.config();c['cargo']['profile']='MIXED';await self.component(c);await expect(self.page.locator('[data-historical-review]')).to_contain_text('MIXED')
  for profile in ['PALLETIZED','PACKAGED','DRY_BULK','LIQUID_BULK','SPECIALIZED','MIXED']:
   value=deepcopy(c);value['cargo']['profile']=profile;result=await self.component(value);self.assertEqual(result['configuration']['cargo']['profile'],profile)
 async def test_04_products_codes_and_reference_integrity(self):
  c=await self.config();g=c['cargo'];g['products'][0]['code']='QA-UNIQUE';g['products'][0]['category']='Bebidas';m,v=await self.historical(c)
  published=v['version']['config_jsonb']['cargo'];self.assertEqual(published['products'][0]['code'],'QA-UNIQUE');self.assertEqual(published['products'][0]['units_per_package'],12);self.assertTrue(all(p['logistic_unit_id']==published['logistic_units'][0]['logistic_unit_id'] for p in published['presentations']))
 async def test_05_partial_dimensions_unknown_mass_and_contradiction(self):
  c=await self.config()
  for mutation in ['partial','missing','contradiction']:
   value=deepcopy(c);p=value['cargo']['presentations'][0]
   if mutation=='partial':p['loaded_dimensions'].pop('height')
   elif mutation=='missing':p.pop('gross_mass',None);value['cargo']['products'][0].pop('gross_mass')
   else:p['gross_mass']['value']='1'
   response=await self.request('POST','/api/platform/logistics-models/contract-preview',{'configuration':value});self.assertEqual(response.status,422,await response.text())
 async def test_06_stale_preview_never_reenables_publish(self):
  await r4.scenario(self,'test_06_stale_preview_error_retry_no_local_publication')
 async def test_07_bulk_uses_explicit_density_without_required_pallet(self):
  c=await self.config('bulk');m,v=await self.historical(c);preview=await self.api('POST','/api/platform/logistics-models/contract-preview',{'model_id':m['model']['id'],'version_id':v['version']['id']});physical=preview['contracts']['transport_demand']['rules']['catalog_snapshot']['BULK'];self.assertEqual(physical['coefficients']['weight_kg'],'850');self.assertEqual(physical['coefficients']['volume_m3'],'1');self.assertEqual(v['version']['config_jsonb']['cargo']['logistic_units'],[]);self.assertEqual(v['version']['config_jsonb']['cargo']['split_policy'],'CONTINUOUS')
 async def test_08_preview_failure_preserves_values_and_retries(self):
  await self.start();await self.fill();before=(await self.draft())['configuration'];await self.page.route('**/logistics-models/contract-preview',lambda r:r.fulfill(status=503,json={'detail':'QA preview unavailable'}))
  await self.page.locator('[name=unit_tare]').fill('26');await expect(self.page.locator('[data-dation-test=cargo-physical-preview]')).to_contain_text('QA preview unavailable');self.assertEqual((await self.draft())['configuration']['cargo']['products'],before['cargo']['products']);await self.page.unroute('**/logistics-models/contract-preview');await self.page.get_by_role('button',name='Reintentar Data Contract',exact=True).click();await self.confirm()
 async def test_09_component_limits_with_public_initial_dto(self):
  c=await self.config();g=c['cargo'];base=deepcopy(g['products'][0]);g['products']=[{**deepcopy(base),'product_id':'P'+str(i),'name':'Producto '+str(i)} for i in range(100)];u=deepcopy(g['logistic_units'][0]);g['logistic_units']=[{**deepcopy(u),'logistic_unit_id':'U'+str(i)} for i in range(50)];p=deepcopy(g['presentations'][0]);p.pop('gross_mass',None);g['presentations']=[{**deepcopy(p),'presentation_id':'L'+str(i),'label':'Carga '+str(i),'logistic_unit_id':'U'+str(i%50),'components':[{'product_id':'P'+str(k),'quantity':'1'} for k in range(30)]} for i in range(200)]
  result=await self.component(c);out=result['configuration']['cargo'];self.assertEqual((len(out['products']),len(out['logistic_units']),len(out['presentations']),len(out['presentations'][0]['components'])),(100,50,200,30));self.assertEqual(out,g)
  # Actual contract rejects exceeding a limit, independently of the reader.
  g['products'].append({**base,'product_id':'OVER','name':'Excedente'});response=await self.request('POST','/api/platform/logistics-models/contract-preview',{'configuration':c});self.assertEqual(response.status,422)
 async def test_10_primary_coload_currency_and_commercial_counts_preserved(self):
  c=await self.config();c['currency_policy']['currency']='BRL';c['currency_policy']['minor_units']=5;c['cargo']['co_load_pairs']=[['SECO','FRIO']];c['cargo']['products'][0]['units_per_package']=216;c['primary_dimension']='volume_m3'
  result=await self.component(c);self.assertEqual(result['configuration'],c);await expect(self.page.locator('[data-historical-review]')).to_contain_text('BRL');await expect(self.page.locator('[data-historical-review]')).to_contain_text('216')
 async def test_11_missing_sources_has_inline_accessible_error(self):
  await self.start();await self.page.locator('[data-dation-test=model-v2-block-3]>summary').click();node=await guided.block(self.page,4)
  for value in ['OWN','EXTERNAL']:await node.locator('[name=sources][value='+value+']').uncheck()
  await node.locator('[data-confirm-block="4"]').click();await expect(node.locator('[data-model-error-for=sources]')).to_contain_text('al menos una fuente');await expect(node.locator('[name=sources]').first).to_have_attribute('aria-invalid','true');self.assertFalse(await self.page.locator('[data-dation-test=model-v2-block-3]').evaluate('n=>n.open'))
 async def test_12_declared_physics_is_not_labelled_as_calculated(self):
  c=await self.config();c['cargo']['products'][0].pop('gross_mass');m,v=await self.historical(c);preview=await self.api('POST','/api/platform/logistics-models/contract-preview',{'model_id':m['model']['id'],'version_id':v['version']['id']});p=preview['contracts']['transport_demand']['rules']['catalog_snapshot']['PAL-JUICE'];self.assertEqual(p['provenance']['sources']['weight_kg'],'DECLARED_GROSS_MASS');self.assertEqual(p['coefficients']['weight_kg'],'985');self.assertEqual(v['version']['config_jsonb']['cargo']['presentations'][0]['gross_mass']['value'],'985')
