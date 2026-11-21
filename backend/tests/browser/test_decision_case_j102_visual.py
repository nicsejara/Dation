"""Executed J1.02 geometry, keyboard, pagination and exact-history evidence."""
import asyncio
import json
import time
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from uuid import uuid4
from playwright.async_api import expect
from r4_model_helpers import R4Browser
import test_decision_case_j102 as cases
import test_ultimate_case_setup as setup

OUT=cases.OUT


class DecisionCaseV2VisualTests(R4Browser):
    fixture_name='decision_case_j102_fixture.py'
    ready_case=cases.DecisionCaseV2BrowserTests.ready_case
    begin_case=cases.DecisionCaseV2BrowserTests.begin_case
    fill_case=cases.DecisionCaseV2BrowserTests.fill_case
    confirm_definition=cases.DecisionCaseV2BrowserTests.confirm_definition
    selected_definition=cases.DecisionCaseV2BrowserTests.selected_definition
    prepare_data=cases.DecisionCaseV2BrowserTests.prepare_data
    upload_entity=cases.DecisionCaseV2BrowserTests.upload_entity
    finish_case=cases.DecisionCaseV2BrowserTests.finish_case
    database_snapshot=cases.DecisionCaseV2BrowserTests.database_snapshot
    model=setup.UltimateCaseSetupTests.model

    async def capture(self,scene,full=True):
        geometry=[]
        for width in [1440,1280,768,375]:
            await self.page.set_viewport_size({'width':width,'height':960 if width>768 else 844})
            await self.page.mouse.move(0,0);await self.page.evaluate('document.activeElement?.blur();window.scrollTo(0,0)')
            await self.page.evaluate('document.fonts.ready');await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
            metrics=await self.page.evaluate('''()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,controls:[...document.querySelectorAll('.j102-shell button,.j102-shell input:not([type=checkbox]),.j102-shell select,.j102-shell textarea')].filter(n=>n.getClientRects().length&&!n.hidden&&getComputedStyle(n).visibility!=='hidden').map(n=>({label:n.name||n.textContent,disabled:n.disabled,rect:n.getBoundingClientRect().toJSON()}))})''')
            self.assertLessEqual(metrics['scroll'],metrics['client'],metrics)
            for control in metrics['controls']:
                self.assertGreaterEqual(control['rect']['height'],44,control);self.assertGreaterEqual(control['rect']['width'],44,control)
                self.assertGreaterEqual(control['rect']['left'],-1,control);self.assertLessEqual(control['rect']['right'],metrics['client']+1,control)
            audit=await self.page.evaluate((Path(__file__).parent/'theme_audit.js').read_text());self.assertEqual(audit['failures'],[],audit['failures'])
            metrics['contrast']={'minimum':audit['minimumContrast'],'count':audit['textCount'],'failures':audit['failures']};geometry.append(metrics)
            await self.page.screenshot(path=str(OUT/(scene+'-'+str(width)+'.png')),full_page=full,animations='disabled')
        (OUT/(scene+'-geometry.json')).write_text(json.dumps(geometry,indent=2))
        await self.page.set_viewport_size({'width':1440,'height':1000})

    async def test_11_wizard_confirmed_review_error_and_modal_geometry(self):
        self.m,self.v=await self.model('J102 Visual');await self.begin_case('J102 Distribución de vinos')
        await self.capture('wizard-empty');await self.fill_case(self.m,self.v);await self.capture('wizard-confirmed')
        await self.confirm_definition();await self.capture('review-draft')
        await self.page.get_by_role('button',name='Editar configuración',exact=True).click();await self.ready_case()
        await self.page.get_by_label('Nombre del Case',exact=True).fill('');await self.page.locator('[data-case-confirm="1"]').click()
        await expect(self.page.locator('[data-block-error="1"]')).to_contain_text('nombre');await self.capture('edit-error')
        header=self.page.locator('.j102-shell .d-page-header');await header.evaluate('n=>{n.tabIndex=-1;n.focus()}');self.assertEqual(await header.evaluate('n=>getComputedStyle(n).outlineStyle'),'none')
        await self.page.keyboard.press('Tab');self.assertNotEqual(await self.page.evaluate('document.activeElement?.tagName'),'HEADER')
        await self.page.locator('.j102-rail').get_by_role('button',name='02 · Decision Case',exact=True).click();await expect(self.page.get_by_role('dialog')).to_be_visible();await self.capture('dirty-modal')
        await self.page.keyboard.press('Escape');await expect(self.page.get_by_role('dialog')).to_have_count(0)

    async def test_12_server_library_pagination_error_exact_history_and_derive(self):
        await self.selected_definition('J102 Historial visual');await self.prepare_data()
        for entity in ['transport_demand','transport_resources']:await self.upload_entity(entity)
        cid=await self.finish_case();base='/api/platform/logistics-cases/'+cid
        await self.page.get_by_role('button',name='Resumen Core Config',exact=True).click()
        await expect(self.page.locator('[data-case-acceptance]')).to_have_attribute('data-acceptance-status','PENDING')
        await self.capture('graph-acceptance');await self.page.keyboard.press('Escape')
        context=await self.api('GET',base+'/context');snapshot=context['case_definition']['snapshot'];snapshot['identity']['name']='J102 Historial actualizado'
        updated=await self.api('PUT',base+'/definition',{'mutation_id':str(uuid4()),'expected_revision':1,'expected_updated_at':context['case']['updated_at'],'definition_v2':snapshot})
        for i in range(26):
            await self.api('POST','/api/platform/logistics-cases',{'id':str(uuid4()),'name':'J102 Biblioteca '+str(i).zfill(2),'logistics_model_version_id':self.v['version']['id'],'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':setup.ADMIN})
        started=time.monotonic();await self.page.goto(self.base+'/app/ddas/logistics/case?journey_version=v2');await self.ready_case();elapsed=time.monotonic()-started
        await self.page.get_by_label('Buscar Cases',exact=True).fill('J102 Biblioteca');await self.page.get_by_role('button',name='Buscar Cases',exact=True).click();await expect(self.page.locator('.j102-case-card')).to_have_count(25)
        await self.capture('library',full=False);await self.page.get_by_role('button',name='Más Cases',exact=True).click();await expect(self.page.locator('.j102-case-card')).to_have_count(1)
        before=await self.database_snapshot();writes=[];self.page.on('request',lambda r:writes.append(r.url) if r.method in ['POST','PUT','PATCH'] and '/api/platform/' in r.url else None)
        async def unavailable(route):await route.fulfill(status=503,json={'detail':'J102 listado temporalmente no disponible'})
        await self.page.route('**/api/platform/decisions?*',unavailable);await self.page.get_by_role('button',name='Buscar Cases',exact=True).click();await expect(self.page.get_by_role('button',name='Reintentar Cases',exact=True)).to_be_visible();await self.capture('library-error',full=False)
        await self.page.unroute('**/api/platform/decisions?*',unavailable);await self.page.get_by_role('button',name='Reintentar Cases',exact=True).click();await expect(self.page.locator('.j102-case-card')).to_have_count(25)
        await self.page.goto(self.base+'/app/ddas/logistics/case?journey_version=v2&case_id='+cid+'&case_view=history');await self.ready_case();await expect(self.page.locator('.j102-history-item')).to_have_count(2);await self.capture('definition-history')
        await self.page.get_by_role('button',name='Revisar definición 1',exact=True).click();await self.ready_case();await expect(self.page.locator('.j102-review')).to_contain_text('J102 Historial visual');await self.capture('review-history')
        await self.page.get_by_role('button',name='Crear Case derivado',exact=True).click();await expect(self.page.get_by_role('dialog')).to_be_visible();await self.capture('derive-modal')
        await self.page.keyboard.press('Escape');self.assertEqual(before,await self.database_snapshot());self.assertEqual(writes,[])
        (OUT/'library-benchmark.json').write_text(json.dumps({'initial_list_seconds':elapsed,'seeded_server_cases':27,'page_size':25,'second_page_filtered_rows':1,'batch_rpc_assertion':'test_decision_case_j102_gate.DecisionCaseV2GateTests.test_listing_adds_one_scoped_batch_not_one_rpc_per_case','same_case_history':[context['case_definition']['id'],updated['case_definition']['id']]},indent=2))

    async def test_13_late_selector_response_and_lock_never_change_final_manual_selection(self):
        a,av=await self.model('J102 Lento A');b,bv=await self.model('J102 Vigente B');await self.begin_case('J102 Selector protegido')
        seen=asyncio.Event();release=asyncio.Event()
        async def hold(route):response=await route.fetch();seen.set();await release.wait();await route.fulfill(response=response)
        path='**/api/platform/logistics-models/'+a['model']['id'];await self.page.route(path,hold)
        try:
            await self.page.get_by_label('Logistics Model',exact=True).select_option(a['model']['id']);await asyncio.wait_for(seen.wait(),10)
            await self.page.get_by_label('Logistics Model',exact=True).select_option(b['model']['id']);await expect(self.page.get_by_label('Versión publicada',exact=True)).to_be_enabled();await self.page.get_by_label('Versión publicada',exact=True).select_option(bv['version']['id']);release.set()
            await expect(self.page.get_by_label('Versión publicada',exact=True)).to_have_value(bv['version']['id']);await expect(self.page.locator('.j102-selected-model')).to_contain_text('J102 Vigente B')
            await self.page.get_by_role('button',name='Guardar borrador',exact=True).click();url=self.page.url;other=await self.context.new_page();await other.goto(url);await expect(other.locator('#ultimate-case-setup-root')).to_contain_text('Este borrador ya está abierto en otra pestaña');await expect(other.locator('.j102-form')).to_have_count(0);await other.close()
        finally:release.set();await self.page.unroute(path,hold)


class DecisionCaseV2DefaultGateTests(R4Browser):
    fixture_name='model_library_fixture.py'
    async def test_14_default_off_keeps_legacy_steps_and_blocks_v2_deep_link(self):
        await self.page.goto(self.base+'/app/ddas/logistics/case');await self.ready(1);await expect(self.page.locator('.core-wizard')).to_have_attribute('data-active-step','1')
        await self.page.goto(self.base+'/app/ddas/logistics/case?journey_version=v2');await expect(self.page.locator('#ultimate-case-setup-root')).to_contain_text('Decision Case V2 todavía no está activado');await expect(self.page.locator('.j102-form')).to_have_count(0)
