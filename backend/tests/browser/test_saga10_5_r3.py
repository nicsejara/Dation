"""R3 regressions retained against the R4 flow; legacy editing is now read-only."""
import asyncio,json,unittest,os
from pathlib import Path
from playwright.async_api import expect
import r4_model_helpers as r4
import guided_model_helpers as legacy
OUT=Path('/tmp/dation-saga10-5-r3-browser');OUT.mkdir(exist_ok=True)
class R3Tests(r4.R4Browser):
    async def stored(self):
        return await self.page.evaluate("()=>{const k=Object.keys(sessionStorage).find(k=>k.startsWith('dation.ultimate.setup.v1.')&&k.endsWith('.case.new'));return {key:k,value:JSON.parse(sessionStorage.getItem(k))}}")
    async def snapshot(self):
        return await self.page.evaluate('''()=>({scrollY,open:[...document.querySelectorAll('.model-v2-block')].map(n=>n.open),focus:{name:document.activeElement.name,tag:document.activeElement.tagName,block:document.activeElement.closest('.model-v2-block')?.dataset.dationTest},invalid:[...document.querySelectorAll('[aria-invalid=true]')].map(n=>n.name),steps:document.querySelectorAll('[data-pro-step]').length,legacy:document.querySelectorAll('[data-cargo-step]').length})''')
    async def test_01_navigation_does_not_expand_incomplete_cargo(self):
        await self.start();first=self.page.locator('[data-pro-step="1"]')
        await self.fill_unit()
        await legacy.block(self.page,3);await self.page.locator('[data-dation-test=model-v2-block-3]>summary').click()
        records=[]
        controls=[(4,'sources',v) for v in ['OWN','OWN','EXTERNAL','EXTERNAL']]+[(4,'resource_categories',v) for v in ['GENERAL','REFRIGERATED','TANKER','BULK','FLATBED']]+[(5,'currency',v) for v in ['USD','EUR','ARS']]+[(5,'external_costs',v) for v in ['PER_KM','PER_KM','PER_TRIP','PER_TRIP']]+[(5,'billing',v) for v in ['ONE_WAY','ONE_WAY','ROUND_TRIP','ROUND_TRIP']]+[(2,'operating_role','HYBRID'),(2,'consolidation_permitted','no')]
        for recovered in [False,True]:
            if recovered:
                stored=await self.stored();ui=stored['value']['planning_model']['new_model']['guided_ux'];ui['edition']='compatible';ui.pop('editorChoice',None);ui.pop('origin',None)
                await self.page.evaluate('v=>sessionStorage.setItem(v.key,JSON.stringify(v.value))',stored);await self.page.reload();await self.ready(1);await expect(self.page.locator('[data-pro-step]')).to_have_count(3)
                await self.page.locator('[data-dation-test=model-v2-block-3]>summary').click()
            for width in [1536,390]:
                await self.page.set_viewport_size({'width':width,'height':1000})
                for index,name,value in controls:
                    node=await legacy.block(self.page,index);control=node.locator('label').filter(has=self.page.locator('[name='+name+'][value='+value+']'))
                    await control.scroll_into_view_if_needed();before=await self.snapshot()
                    await control.click();after=await self.snapshot();records.append({'recovered':recovered,'width':width,'control':name,'value':value,'before':before,'after':after})
                    (OUT/'navigation.json').write_text(json.dumps(records,indent=2))
                    if name=='currency' and value=='EUR' or name=='sources' and value=='OWN':await self.page.screenshot(path=str(OUT/f'fixed-nav-{recovered}-{width}-{name}.png'),full_page=True)
                    self.assertEqual(after['open'],before['open'],records[-1])
                    self.assertEqual(after['focus']['block'],'model-v2-block-'+str(index),records[-1])
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
            value=json.loads(json.dumps(stored['value']));ui=value['planning_model']['new_model']['guided_ux'];ui.pop('edition',None);ui.pop('editorChoice',None)
            if marker:ui['edition']=marker
            await self.page.evaluate('v=>sessionStorage.setItem(v.key,JSON.stringify(v.value))',{'key':stored['key'],'value':value})
            await self.page.reload();await self.ready(1);await legacy.block(self.page,3)
            if await self.page.locator('[data-use-guided]').is_visible():await self.page.locator('[data-use-guided]').click()
            await expect(self.page.locator('[data-pro-step]')).to_have_count(3);await expect(self.page.locator('[data-cargo-step]')).to_have_count(0)
            await expect(self.page.locator('[data-pro-step="1"] [name=guided_unit_type]')).to_have_count(5)
            self.assertEqual((await self.stored())['value']['planning_model']['new_model']['configuration'],initial)
    async def test_04_direct_choice_and_recoverable_checkpoint(self):
        await r4.scenario(self,'test_11_incompatible_draft_and_recovery_checkpoint')
    async def test_05_local_errors_stay_local_and_global_errors_are_deliberate(self):
        await self.start();await self.page.locator('[data-dation-test=model-v2-block-3]>summary').click()
        node=await legacy.block(self.page,4)
        for value in ['OWN','EXTERNAL']:await node.locator('label').filter(has=self.page.locator('[name=sources][value='+value+']')).click()
        await node.locator('[data-confirm-block="4"]').click();await expect(node.locator('[data-model-error-for=sources]')).to_contain_text('al menos una fuente');self.assertFalse((await self.snapshot())['open'][2])
        await node.locator('label').filter(has=self.page.locator('[name=sources][value=EXTERNAL]')).click()
        costs=await legacy.block(self.page,5)
        for value in ['PER_KM','PER_TRIP']:await costs.locator('label').filter(has=self.page.locator('[name=external_costs][value='+value+']')).click()
        await costs.locator('[data-confirm-block="5"]').click();await expect(costs.locator('[data-model-error-for=costs]')).to_contain_text('tarifa externa');self.assertFalse((await self.snapshot())['open'][2])
        self.assertEqual((await self.snapshot())['focus']['block'],'model-v2-block-5')
        writes=[];self.page.on('request',lambda r:writes.append(r.url) if r.method=='POST' and (r.url.endswith('/logistics-models') or r.url.endswith('/versions')) else None)
        await expect(self.page.locator('[data-dation-test=model-create]')).to_be_disabled()
        await self.page.locator('[data-dation-test=model-create]').dispatch_event('click')
        self.assertTrue((await self.snapshot())['open'][2]);self.assertEqual((await self.snapshot())['focus']['block'],'model-v2-block-3');self.assertEqual(writes,[])
    async def test_06_profiles_are_selectable_and_bulk_profile_stays_discrete(self):
        await r4.scenario(self,'test_04_five_units_metre_volume_and_cancel_safe')
    async def test_07_new_from_published_is_independent_and_empty(self):
        await r4.scenario(self,'test_12_new_from_published_preserves_identity')
    async def test_08_visual_contract_and_model_only_helpers(self):
        await r4.scenario(self,'test_09_dom_inventory_responsive_geometry_accessibility_and_screenshots')
    async def test_09_pending_publication_blocks_reset_and_reuses_intent(self):
        await self.start();await self.fill();await self.confirm()
        await self.page.route('**/api/platform/logistics-models/*/versions',lambda route:route.fulfill(status=503,json={'detail':'QA retry publication'}),times=1)
        await self.page.locator('[data-dation-test=model-create]').click()
        await expect(self.page.locator('[data-dation-test=model-feedback]')).to_contain_text('QA retry publication')
        await expect(self.page.get_by_role('button',name='Crear nuevo modelo',exact=True)).to_be_disabled()
        before=(await self.stored())['value']['planning_model']['intent'];await self.page.reload();await self.ready(1)
        await expect(self.page.get_by_role('button',name='Crear nuevo modelo',exact=True)).to_be_disabled()
        await self.page.locator('[data-dation-test=model-create]').click();await self.ready(2)
        requests=[(m,u) for m,u in self.operations if m=='POST' and (u.endswith('/logistics-models') or u.endswith('/versions'))]
        self.assertEqual(sum(u.endswith('/logistics-models') for _,u in requests),1)
        self.assertEqual(sum(u.endswith('/versions') for _,u in requests),2)
        after=(await self.stored())['value']['planning_model'];self.assertEqual(after['model_id'],before['model_id']);self.assertEqual(after['version_id'],before['version_id'])
