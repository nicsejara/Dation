"""Shared R4 public browser actions; no internal state mutation."""
import json,unittest
from playwright.async_api import expect
import test_saga10_wizard as fixture
import guided_model_helpers as blocks
class R4Browser(unittest.IsolatedAsyncioTestCase):
 setUpClass=classmethod(fixture.Saga10WizardTests.setUpClass.__func__);tearDownClass=classmethod(fixture.Saga10WizardTests.tearDownClass.__func__)
 sql=fixture.Saga10WizardTests.sql;login=fixture.Saga10WizardTests.login;request=fixture.Saga10WizardTests.request;api=fixture.Saga10WizardTests.api;ready=fixture.Saga10WizardTests.ready
 asyncSetUp=fixture.Saga10WizardTests.asyncSetUp;asyncTearDown=fixture.Saga10WizardTests.asyncTearDown
 async def start(self):
  self.errors=[];self.page.on('pageerror',lambda e:self.errors.append(str(e)))
  await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1)
  await expect(self.page.locator('.model-wizard-pro')).to_be_visible()
  await self.page.get_by_label('Nombre del modelo *',exact=True).fill('QA Logistics Orange')
  await blocks.block(self.page,3)
 async def stored(self):
  return await self.page.evaluate("()=>{const key=Object.keys(sessionStorage).find(k=>k.startsWith('dation.ultimate.setup.v1.')&&k.endsWith('.case.new'));return {key,value:JSON.parse(sessionStorage.getItem(key))}}")
 async def draft(self):return (await self.stored())['value']['planning_model']['new_model']
 async def fill_unit(self):
  for name,value in [('unit_name','Pallet estándar'),('unit_tare','25'),('unit_length','120'),('unit_width','100'),('unit_height','150')]:await self.page.locator('[data-pro-step="1"] [name='+name+']').fill(value)
 async def fill_product(self,name='Vino Malbec',mass='12',q='60',width='30',height='25'):
  for key,value in [('product_name',name),('product_mass',mass),('product_quantity',q),('product_length','30'),('product_width',width),('product_height',height)]:await self.page.locator('[data-pro-step="2"] [name='+key+']').fill(value)
 async def save(self):await self.page.locator('[data-save-load-type]').click()
 async def fill(self,two=False):
  await self.fill_unit();await self.fill_product();await self.save()
  if two:await self.fill_product('Aceite de oliva','8','80','20','30');await self.save()
 async def confirm(self):
  for i in [1,2,4,5,3]:
   node=await blocks.block(self.page,i);cta=node.locator('[data-confirm-block="'+str(i)+'"]')
   if i==3:await expect(cta).to_have_attribute('data-preview-current','true')
   if not await cta.is_disabled():await cta.click()
   await expect(cta).to_be_disabled();await expect(node.locator('>summary .guided-status')).to_have_attribute('data-state','complete')
  await expect(self.page.locator('[data-dation-test=model-create]')).to_be_enabled()
 async def publish(self):
  await self.confirm()
  async with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/versions')) as response:await self.page.locator('[data-dation-test=model-create]').click()
  data=await (await response.value).json();await self.ready(2);return data['version']['config_jsonb']

async def scenario(test,name):
 # Older suites retain their public scenario entry points; actions now follow
 # the normative R4 transaction flow, never the removed catalog administration.
 from types import MethodType
 import test_saga10_5_r4 as r4
 for key in ['start','stored','draft','fill_unit','fill_product','save','fill','confirm','publish']:
  setattr(test,key,MethodType(getattr(R4Browser,key),test))
 await getattr(r4.R4Tests,name)(test)
