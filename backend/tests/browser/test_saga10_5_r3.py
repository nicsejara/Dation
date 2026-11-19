"""R3 real recovered-draft/scroll/reset regressions; isolated SQL/API fixture."""
import asyncio,json,unittest,os
from pathlib import Path
from playwright.async_api import expect
import test_saga10_5_ultimate as pro
import guided_model_helpers as legacy

OUT=Path('/tmp/dation-saga10-5-r3-browser');OUT.mkdir(exist_ok=True)
class R3Tests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(pro.UltimateProTests.setUpClass.__func__);tearDownClass=classmethod(pro.UltimateProTests.tearDownClass.__func__)
    sql=pro.UltimateProTests.sql;login=pro.UltimateProTests.login;request=pro.UltimateProTests.request;api=pro.UltimateProTests.api;ready=pro.UltimateProTests.ready
    asyncSetUp=pro.UltimateProTests.asyncSetUp;asyncTearDown=pro.UltimateProTests.asyncTearDown
    start=pro.UltimateProTests.start;fill=pro.UltimateProTests.fill;kind=pro.UltimateProTests.kind;confirm=pro.UltimateProTests.confirm;publish=pro.UltimateProTests.publish
    async def stored(self):
        return await self.page.evaluate("()=>{const k=Object.keys(sessionStorage).find(k=>k.startsWith('dation.ultimate.setup.v1.')&&k.endsWith('.case.new'));return {key:k,value:JSON.parse(sessionStorage.getItem(k))}}")
    async def snapshot(self):
        return await self.page.evaluate('''()=>({scrollY,open:[...document.querySelectorAll('.model-v2-block')].map(n=>n.open),focus:{name:document.activeElement.name,tag:document.activeElement.tagName,block:document.activeElement.closest('.model-v2-block')?.dataset.dationTest},invalid:[...document.querySelectorAll('[aria-invalid=true]')].map(n=>n.name),steps:document.querySelectorAll('[data-pro-step]').length,legacy:document.querySelectorAll('[data-cargo-step]').length})''')
    async def test_01_navigation_does_not_expand_incomplete_cargo(self):
        await self.start();first=self.page.locator('[data-pro-step="1"]')
        await first.get_by_role('button',name='Agregar unidad logística',exact=True).click()
        await legacy.block(self.page,3);await self.page.locator('[data-dation-test=model-v2-block-3]>summary').click()
        records=[]
        for index,name,value in [(4,'sources','OWN'),(4,'resource_categories','GENERAL'),(5,'currency','USD')]:
            node=await legacy.block(self.page,index);control=node.locator('label').filter(has=self.page.locator('[name='+name+'][value='+value+']'))
            await control.scroll_into_view_if_needed();before=await self.snapshot()
            await self.page.screenshot(path=str(OUT/f'before-{name}.png'),full_page=True)
            await control.click();after=await self.snapshot();records.append({'control':name,'before':before,'after':after})
            (OUT/'navigation.json').write_text(json.dumps(records,indent=2))
            await self.page.screenshot(path=str(OUT/f'after-{name}.png'),full_page=True)
            if after['open'][2]:await self.page.locator('[data-dation-test=model-v2-block-3]>summary').click()
        self.assertTrue(all(v['after']['open'][2]==v['before']['open'][2] for v in records),records)
        self.assertTrue(all(v['after']['focus']['block']=='model-v2-block-'+str(i) for v,i in zip(records,[4,4,5])),records)
    async def test_02_new_model_resets_real_draft_and_cancel_preserves_it(self):
        await self.start();await self.fill();await self.confirm();before=await self.stored()
        await self.page.get_by_role('button',name='Crear nuevo modelo',exact=True).click()
        dialog=self.page.get_by_role('dialog');await expect(dialog).to_be_visible()
        await dialog.get_by_role('button',name='Cancelar',exact=True).click();self.assertEqual((await self.stored())['value'],before['value'])
        await self.page.get_by_role('button',name='Crear nuevo modelo',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Crear nuevo modelo',exact=True).click()
        await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('')
        after=await self.stored();a=after['value']['planning_model']['new_model'];b=before['value']['planning_model']['new_model']
        self.assertNotEqual(a['id'],b['id']);self.assertEqual(a['configuration']['cargo']['products'],[]);self.assertEqual(a['guided_ux']['confirmed'],{})
        await expect(self.page.locator('.guided-status[data-state=complete]')).to_have_count(0)
        await self.page.reload();await self.ready(1);await expect(self.page.get_by_label('Nombre del modelo *',exact=True)).to_have_value('')
        self.assertEqual((await self.stored())['value']['planning_model']['new_model']['id'],a['id'])
    async def test_03_recovered_homogeneous_draft_is_not_trapped_by_edition(self):
        await self.start();await self.fill();stored=await self.stored();initial=stored['value']['planning_model']['new_model']['configuration']
        for marker in [None,'compatible']:
            value=json.loads(json.dumps(stored['value']));ui=value['planning_model']['new_model']['guided_ux'];ui.pop('edition',None)
            if marker:ui['edition']=marker
            await self.page.evaluate('v=>sessionStorage.setItem(v.key,JSON.stringify(v.value))',{'key':stored['key'],'value':value})
            await self.page.reload();await self.ready(1);await legacy.block(self.page,3)
            if await self.page.locator('[data-use-guided]').is_visible():await self.page.locator('[data-use-guided]').click()
            await expect(self.page.locator('[data-pro-step]')).to_have_count(3);await expect(self.page.locator('[data-cargo-step]')).to_have_count(0)
            await expect(self.page.locator('[data-pro-step="1"] [name=cargo_profile]')).to_have_count(6)
            self.assertEqual((await self.stored())['value']['planning_model']['new_model']['configuration'],initial)
