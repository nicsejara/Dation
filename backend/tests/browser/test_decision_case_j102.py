"""J1.02 real browser, Auth, API, Storage and PostgreSQL. Synthetic data only."""
import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from uuid import uuid4
from playwright.async_api import expect
from r4_model_helpers import R4Browser
import test_ultimate_case_setup as setup
import test_ultimate_navigation as legacy_navigation

OUT=Path('/tmp/dation-j102-browser');OUT.mkdir(exist_ok=True)


class DecisionCaseV2BrowserTests(R4Browser):
    fixture_name='decision_case_j102_fixture.py'
    model=setup.UltimateCaseSetupTests.model

    async def asyncTearDown(self):
        result=self._outcome.result
        if any(test is self for test,_ in result.errors+result.failures):
            (OUT/(self._testMethodName+'-diagnostic.json')).write_text(json.dumps(await self.page.evaluate("()=>({url:location.href,text:document.body.innerText,html:document.querySelector('#ultimate-case-setup-root')?.innerHTML})")))
            await self.page.screenshot(path=str(OUT/(self._testMethodName+'-failure.png')),full_page=True)
        await super().asyncTearDown()

    async def ready_case(self):
        try:await expect(self.page.locator('.j102-shell')).to_have_attribute('data-j102-ready','true')
        except AssertionError:
            text=await self.page.evaluate('document.body.innerText')
            (OUT/(self._testMethodName+'-ui-error.txt')).write_text(text or '')
            raise

    async def begin_case(self,name='J102 Distribución QA'):
        await self.page.goto(self.base+'/app/ddas/logistics/case?journey_version=v2')
        await self.ready_case();await self.page.get_by_role('button',name='Crear Decision Case',exact=True).click()
        await self.ready_case();await expect(self.page.get_by_label('Nombre del Case',exact=True)).to_be_visible()
        await self.page.get_by_label('Nombre del Case',exact=True).fill(name)

    async def fill_case(self,model,version):
        await expect(self.page.get_by_label('Logistics Model',exact=True)).to_have_value('')
        await self.page.get_by_label('Logistics Model',exact=True).select_option(model['model']['id'])
        await expect(self.page.get_by_label('Versión publicada',exact=True)).to_be_enabled()
        await expect(self.page.get_by_label('Versión publicada',exact=True)).to_have_value('')
        await self.page.get_by_label('Versión publicada',exact=True).select_option(version['version']['id'])
        await self.page.get_by_label('Inicio de planificación',exact=True).fill('2026-11-02')
        await self.page.get_by_label('Fin de planificación',exact=True).fill('2026-11-08')
        await self.page.get_by_label('Decision Owner',exact=True).select_option(setup.ADMIN)
        for i in range(1,7):
            b=self.page.locator('[data-case-confirm="'+str(i)+'"]');await b.click();await expect(b).to_be_disabled()

    async def confirm_definition(self):
        await self.page.get_by_role('button',name='Confirmar definición',exact=True).click()
        await expect(self.page.locator('[data-case-review=confirmed-draft]')).to_be_visible()
        await self.ready_case()

    async def database_snapshot(self):
        return json.loads(self.sql("SELECT jsonb_build_object('cases',(SELECT coalesce(jsonb_agg(to_jsonb(c) ORDER BY id),'[]') FROM decision_cases c),'runs',(SELECT coalesce(jsonb_agg(to_jsonb(r) ORDER BY id),'[]') FROM decision_runs r),'packs',(SELECT coalesce(jsonb_agg(to_jsonb(p) ORDER BY id),'[]') FROM case_data_packs p),'definitions',(SELECT coalesce(jsonb_agg(to_jsonb(d) ORDER BY id),'[]') FROM dation_private.case_definition_revisions d));"))

    async def selected_definition(self,name='J102 Preparación',catalog=False):
        if catalog:
            cfg=json.loads((Path(__file__).parent/'fixtures/j102/catalog-model.json').read_text())
            self.m=await self.api('POST','/api/platform/logistics-models',{'id':str(uuid4()),'name':'J102 Catálogo físico','configuration':cfg})
            self.v=await self.api('POST','/api/platform/logistics-models/'+self.m['model']['id']+'/versions',{'version_id':str(uuid4()),'expected_revision':1})
        else:self.m,self.v=await self.model('J102 Modelo de '+name)
        await self.begin_case(name);await self.fill_case(self.m,self.v);await self.confirm_definition()

    async def prepare_data(self):
        await self.page.get_by_role('button',name='Continuar a preparación de datos',exact=True).click()
        await self.ready_case();await expect(self.page.locator('[data-preparation-entity=transport_demand]')).to_be_visible()
        async with self.page.expect_response(lambda r:r.url.endswith('/owner') and r.request.method=='PUT') as response:
            await self.page.get_by_label('Data Owner',exact=True).select_option(setup.ADMIN)
        self.assertTrue((await response.value).ok)

    async def upload_entity(self,entity):
        response=await self.request('POST','/api/platform/logistics-models/contract-preview/templates/'+entity,{'model_id':self.m['model']['id'],'version_id':self.v['version']['id']})
        self.assertTrue(response.ok,await response.text());raw=await response.body()
        host=self.page.locator('[data-preparation-entity='+entity+']');await host.locator('input[type=file]').set_input_files({'name':entity+'.csv','mimeType':'text/csv','buffer':raw})
        save=host.get_by_role('button',name='Guardar candidato de ',exact=False);await expect(save).to_be_enabled();await save.click();await expect(host).to_contain_text('Candidato guardado · no publicado')

    async def finish_case(self):
        await expect(self.page.locator('[data-j102-finalize]')).to_be_enabled();await self.page.locator('[data-j102-finalize]').click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Crear Case',exact=True).click()
        await self.page.locator('[data-ux05-ready=true]').wait_for();return parse_qs(urlparse(self.page.url).query)['case_id'][0]

    async def test_01_manual_six_blocks_confirm_review_without_creating_case(self):
        model,version=await self.model('J102 Modelo publicado');before=await self.database_snapshot()
        await self.begin_case();await expect(self.page.locator('[data-case-block]')).to_have_count(6)
        await expect(self.page.get_by_role('button',name='Confirmar definición',exact=True)).to_be_disabled()
        await self.fill_case(model,version);await self.confirm_definition()
        await expect(self.page.locator('.j102-review input,.j102-review select')).to_have_count(0)
        self.assertEqual(before,await self.database_snapshot())

    async def test_02_two_contract_bridge_reload_finalize_and_graph_review(self):
        await self.selected_definition();before=await self.database_snapshot();await self.prepare_data()
        await self.upload_entity('transport_demand');await self.upload_entity('transport_resources')
        work_url=self.page.url;await self.page.reload();await self.ready_case();await expect(self.page.locator('[data-j102-finalize]')).to_be_enabled()
        cid=await self.finish_case();after=await self.database_snapshot();self.assertEqual(len(after['cases']),len(before['cases'])+1);self.assertEqual(len(after['runs']),len(before['runs']));self.assertEqual(len(after['definitions']),len(before['definitions'])+1)
        context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context');self.assertEqual(context['model_version']['id'],self.v['version']['id']);self.assertEqual(context['entry_count'],2)
        self.assertIn('definition_hash',context['case_definition']);self.assertNotIn('case_id=',work_url)
        await self.page.get_by_role('button',name='Editar Decision Case',exact=True).first.click();await self.ready_case()
        await expect(self.page.locator('[data-case-review=persisted]')).to_be_visible();await expect(self.page.get_by_label('Nombre del Case',exact=True)).to_have_count(0)
        self.assertIn('case_id='+cid,self.page.url);self.assertEqual(after,await self.database_snapshot())
        await self.page.locator('.j102-footer .j101-back').click();await self.page.locator('[data-ux05-ready=true]').wait_for();self.assertIn('case_id='+cid,self.page.url)

    async def test_03_catalog_three_contracts_use_exact_physical_version(self):
        await self.selected_definition('J102 Catálogo',catalog=True);await self.prepare_data()
        await expect(self.page.locator('[data-preparation-entity]')).to_have_count(3)
        for entity in ['transport_demand','order_lines','transport_resources']:await self.upload_entity(entity)
        cid=await self.finish_case();context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context')
        self.assertEqual(context['entry_count'],3);self.assertEqual(context['case_definition']['snapshot']['model_binding']['model_version_id'],self.v['version']['id'])
        state=await self.api('GET','/api/platform/logistics-cases/'+cid+'/data');self.assertEqual(set(state['contracts']),{'transport_demand','order_lines','transport_resources'})

    async def test_04_models_round_trip_preserves_work_and_selection(self):
        await self.selected_definition('J102 Retorno');url=self.page.url;before=await self.database_snapshot()
        await self.page.get_by_role('button',name='Revisar Model Version',exact=True).click()
        await expect(self.page.locator('[data-review-context=library]')).to_be_visible();await self.page.locator('.j101-back').click();await expect(self.page.locator('.j101-library')).to_have_attribute('data-ultimate-ready','true')
        await self.page.get_by_role('button',name='Volver al contexto de origen',exact=True).click();await self.ready_case()
        self.assertEqual(self.page.url,url);await expect(self.page.locator('.j102-review')).to_contain_text('J102 Retorno');await expect(self.page.locator('.j102-review')).to_contain_text('Versión 1');self.assertEqual(before,await self.database_snapshot())

    async def test_05_dirty_guard_cancel_and_recover_independent_copies(self):
        await self.begin_case('J102 Copia A');url=self.page.url
        await self.page.locator('.j102-rail').get_by_role('button',name='02 · Decision Case',exact=True).click()
        dialog=self.page.get_by_role('dialog');await expect(dialog).to_be_visible();await dialog.get_by_role('button',name='Seguir editando',exact=True).click();self.assertEqual(self.page.url,url)
        await self.page.get_by_role('button',name='Guardar borrador',exact=True).click();await self.page.locator('.j102-rail').get_by_role('button',name='02 · Decision Case',exact=True).click();await self.ready_case()
        await self.page.get_by_role('button',name='Crear Decision Case',exact=True).click();await self.ready_case();await expect(self.page.get_by_label('Nombre del Case',exact=True)).to_have_value('')
        b=self.page.url;self.assertNotEqual(url,b);await self.page.goto(url);await self.ready_case();await expect(self.page.get_by_label('Nombre del Case',exact=True)).to_have_value('J102 Copia A')

    async def test_06_cancel_edit_restores_confirmed_draft_and_reconfirmation_is_required(self):
        await self.selected_definition('J102 Cancelar');before=await self.database_snapshot();await self.page.get_by_role('button',name='Editar configuración',exact=True).click();await self.ready_case()
        await self.page.get_by_label('Nombre del Case',exact=True).fill('Cambio descartado');await expect(self.page.get_by_role('button',name='Confirmar definición',exact=True)).to_be_disabled()
        await self.page.get_by_role('button',name='Cancelar cambios',exact=True).click();await self.ready_case();await expect(self.page.locator('.j102-review')).to_contain_text('J102 Cancelar');await expect(self.page.locator('.j102-review')).not_to_contain_text('Cambio descartado');self.assertEqual(before,await self.database_snapshot())
        url=self.page.url;await self.page.reload();await self.ready_case();await expect(self.page.locator('[data-case-review=confirmed-draft]')).to_be_visible();self.assertEqual(url,self.page.url)
        self.assertEqual(before,await self.database_snapshot())

    async def test_07_lost_finalize_response_recovers_one_case_pack_and_fixed_intent(self):
        await self.selected_definition('J102 Respuesta perdida');await self.prepare_data()
        for entity in ['transport_demand','transport_resources']:await self.upload_entity(entity)
        before=await self.database_snapshot();bodies=[];lost=False
        async def drop_once(route):
            nonlocal lost
            bodies.append(route.request.post_data_json);response=await route.fetch()
            if not lost:
                lost=True;self.assertEqual(response.status,200);await route.fulfill(status=503,json={'detail':'J102 Respuesta perdida después del commit'})
            else:await route.fulfill(response=response)
        await self.page.route('**/data-preparations/*/finalize',drop_once)
        await self.page.locator('[data-j102-finalize]').click();await self.page.get_by_role('dialog').get_by_role('button',name='Crear Case',exact=True).click()
        await expect(self.page.locator('.j102-footer [role=alert]')).to_contain_text('perdida')
        self.assertTrue(await self.page.locator('.j102-content').evaluate('n=>n.inert'))
        await self.page.get_by_role('button',name='Recuperar creación pendiente',exact=True).click();await self.page.locator('[data-ux05-ready=true]').wait_for()
        self.assertEqual(len(bodies),2);self.assertEqual(bodies[0]['case'],bodies[1]['case']);after=await self.database_snapshot()
        self.assertEqual(len(after['cases']),len(before['cases'])+1);self.assertEqual(len(after['packs']),len(before['packs'])+1);self.assertEqual(len(after['definitions']),len(before['definitions'])+1)

    async def test_08_persisted_metadata_history_derive_and_original_integrity(self):
        await self.selected_definition('J102 Original');await self.prepare_data()
        for entity in ['transport_demand','transport_resources']:await self.upload_entity(entity)
        cid=await self.finish_case();base='/api/platform/logistics-cases/'+cid
        old=await self.api('GET',base+'/context');await self.page.goto(self.base+'/app/ddas/logistics/case?journey_version=v2&case_id='+cid);await self.ready_case()
        await self.page.get_by_role('button',name='Editar configuración',exact=True).click();await self.ready_case()
        await self.page.get_by_label('Nombre del Case',exact=True).fill('J102 Nombre editado');await self.page.locator('[data-case-confirm="1"]').click()
        await self.page.get_by_role('button',name='Guardar cambios',exact=True).click();await expect(self.page.locator('[data-case-review=persisted]')).to_contain_text('J102 Nombre editado')
        await self.page.get_by_role('button',name='Historial de definiciones',exact=True).click();await self.ready_case();await expect(self.page.locator('.j102-history-item')).to_have_count(2)
        await self.page.get_by_role('button',name='Revisar definición 1',exact=True).click();await self.ready_case();await expect(self.page.locator('.j102-review')).to_contain_text('J102 Original')
        await expect(self.page.get_by_role('button',name='Editar configuración',exact=True)).to_have_count(0)
        await self.page.get_by_role('button',name='Revisar definición vigente',exact=True).click();await self.ready_case()
        await expect(self.page.locator('.j102-review')).to_contain_text('J102 Nombre editado');await expect(self.page.get_by_role('button',name='Editar configuración',exact=True)).to_be_enabled()
        await self.page.get_by_role('button',name='Historial de definiciones',exact=True).click();await self.ready_case();await self.page.get_by_role('button',name='Revisar definición 1',exact=True).click();await self.ready_case();snapshot=await self.database_snapshot()
        await self.page.get_by_role('button',name='Crear Case derivado',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Preparar derivado',exact=True).click();await self.ready_case()
        await expect(self.page.locator('.j102-origin')).to_contain_text(cid);await expect(self.page.get_by_label('Nombre del Case',exact=True)).to_have_value('J102 Original')
        self.assertNotIn('case_id=',self.page.url);self.assertEqual(snapshot,await self.database_snapshot())
        latest=await self.api('GET',base+'/definitions/'+old['case_definition']['id']);self.assertEqual(latest,old['case_definition'])

    async def test_09_two_tab_cas_preserves_second_copy(self):
        await self.selected_definition('J102 CAS');await self.prepare_data()
        for entity in ['transport_demand','transport_resources']:await self.upload_entity(entity)
        cid=await self.finish_case();url=self.base+'/app/ddas/logistics/case?journey_version=v2&case_id='+cid
        await self.page.goto(url);await self.ready_case();await self.page.get_by_role('button',name='Editar configuración',exact=True).click();await self.ready_case()
        second=await self.context.new_page();await second.goto(url);await expect(second.locator('.j102-shell')).to_have_attribute('data-j102-ready','true');await second.get_by_role('button',name='Editar configuración',exact=True).click();await expect(second.get_by_label('Nombre del Case',exact=True)).to_be_visible()
        await self.page.get_by_label('Nombre del Case',exact=True).fill('J102 Primer cambio');await self.page.locator('[data-case-confirm="1"]').click();await self.page.get_by_role('button',name='Guardar cambios',exact=True).click();await expect(self.page.locator('.j102-review')).to_contain_text('J102 Primer cambio')
        await second.get_by_label('Nombre del Case',exact=True).fill('J102 Copia preservada');await second.locator('[data-case-confirm="1"]').click();await second.get_by_role('button',name='Guardar cambios',exact=True).click()
        await expect(second.locator('.j102-footer [role=alert]')).to_contain_text('Conflicto de revisión');await expect(second.get_by_label('Nombre del Case',exact=True)).to_have_value('J102 Copia preservada');await expect(second.get_by_label('Nombre del Case',exact=True)).to_be_disabled()
        data=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context');self.assertEqual(data['case']['label'],'J102 Primer cambio');self.assertEqual(data['case_definition']['revision'],2)
        await second.close()

    async def test_10_direct_empty_finalize_denied_and_viewer_cannot_create(self):
        await self.selected_definition('J102 Sin datos');before=await self.database_snapshot();await self.prepare_data()
        stored=await self.page.evaluate("()=>JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k=>k.startsWith('dation.cases.working.v2.')))).draft")
        d=stored['confirmedDefinition'];body={'id':stored['id'],**d['identity'],**d['decision_context'],'logistics_model_version_id':d['model_binding']['model_version_id'],'case_policy':d['case_policy'],'decision_owner_user_id':setup.ADMIN,'definition_v2':d}
        pid=stored['preparation']['id'];session=await self.api('GET','/api/platform/data-preparations/'+pid)
        response=await self.request('POST','/api/platform/data-preparations/'+pid+'/finalize',{'expected_revision':session['session']['revision'],'case':body});self.assertEqual(response.status,409)
        self.assertEqual((await self.api('GET','/api/platform/data-preparations/'+pid))['session']['status'],'DRAFT');self.assertEqual(before,await self.database_snapshot())
        viewer=await self.browser.new_context();await self.login(viewer,3);vp=await viewer.new_page();await vp.goto(self.base+'/app/ddas/logistics/case?journey_version=v2');await expect(vp.locator('.j102-shell')).to_have_attribute('data-j102-ready','true');await expect(vp.get_by_role('button',name='Crear Decision Case',exact=True)).to_have_count(0)
        response=await self.request('POST','/api/platform/decision-case-definitions/validate',d,context=viewer);self.assertEqual(response.status,403)
        await viewer.close()

    async def test_15_back_forward_is_read_only_and_model_change_preserves_old_candidates(self):
        await self.selected_definition('J102 Cambiar modelo');first=self.v['version']['id'];await self.prepare_data()
        for entity in ['transport_demand','transport_resources']:await self.upload_entity(entity)
        stored=await self.page.evaluate("()=>JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k=>k.startsWith('dation.cases.working.v2.')))).draft")
        pid=stored['preparation']['id'];url=self.page.url;before=await self.database_snapshot();writes=[]
        def track(r):
            if r.method in ['POST','PUT','PATCH'] and '/api/platform/' in r.url:writes.append(r.url)
        self.page.on('request',track)
        await self.page.go_back();await self.ready_case();await expect(self.page.locator('[data-case-review=confirmed-draft]')).to_be_visible()
        await self.page.go_forward();await self.ready_case();await expect(self.page.locator('[data-j102-finalize]')).to_be_enabled();self.assertEqual(self.page.url,url);self.assertEqual(writes,[]);self.assertEqual(before,await self.database_snapshot())
        self.page.remove_listener('request',track);other,version=await self.model('J102 Segunda familia')
        await self.page.go_back();await self.ready_case();await self.page.get_by_role('button',name='Editar configuración',exact=True).click();await self.ready_case()
        await self.page.get_by_label('Logistics Model',exact=True).select_option(other['model']['id']);await self.page.get_by_role('dialog').get_by_role('button',name='Cambiar modelo',exact=True).click();await expect(self.page.get_by_label('Versión publicada',exact=True)).to_be_enabled()
        await self.page.get_by_label('Versión publicada',exact=True).select_option(version['version']['id'])
        for i in [2,5,6]:await self.page.locator('[data-case-confirm="'+str(i)+'"]').click()
        await self.confirm_definition();await self.page.get_by_role('button',name='Continuar a preparación de datos',exact=True).click();await self.ready_case();await expect(self.page.locator('[data-preparation-entity=transport_demand]')).to_be_visible()
        after=await self.page.evaluate("()=>JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k=>k.startsWith('dation.cases.working.v2.')))).draft")
        self.assertNotEqual(after['preparation']['id'],pid);old=await self.api('GET','/api/platform/data-preparations/'+pid);self.assertEqual(old['session']['model_version_id'],first);self.assertEqual(len([u for u in old['uploads'] if u['selected'] and u['ready']]),2)
        self.assertEqual(before,await self.database_snapshot())

    async def test_16_flag_off_still_reads_persisted_and_archived_cases(self):
        await self.selected_definition('J102 Archivo');await self.prepare_data()
        for entity in ['transport_demand','transport_resources']:await self.upload_entity(entity)
        cid=await self.finish_case();context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context')
        await self.api('PATCH','/api/platform/decisions/'+cid,{'expected_updated_at':context['case']['updated_at'],'archived':True})
        self.sql('UPDATE dation_private.platform_release SET j102_enabled=false;')
        try:
            before=await self.database_snapshot();await self.page.goto(self.base+'/app/ddas/logistics/case?journey_version=v2&case_id='+cid);await self.ready_case()
            await expect(self.page.locator('.j102-footer')).to_contain_text('Case archivado');await expect(self.page.get_by_role('button',name='Editar configuración',exact=True)).to_have_count(0);await expect(self.page.get_by_role('button',name='Crear Case derivado',exact=True)).to_have_count(0)
            self.assertEqual(before,await self.database_snapshot());self.assertEqual((await self.api('GET','/api/platform/logistics-cases/'+cid+'/definitions'))['total'],1)
        finally:self.sql('UPDATE dation_private.platform_release SET j102_enabled=true;')

    async def test_17_graph_data_and_model_routes_keep_pinned_resources_and_origin(self):
        await self.selected_definition('J102 Origen Graph');await self.prepare_data()
        for entity in ['transport_demand','transport_resources']:await self.upload_entity(entity)
        cid=await self.finish_case();before=await self.database_snapshot()
        await self.page.get_by_role('button',name='Resumen Core Config',exact=True).click()
        await expect(self.page.locator('[data-case-acceptance]')).to_have_attribute('data-acceptance-status','PENDING')
        await expect(self.page.locator('[data-case-acceptance]')).to_contain_text('no aprueba corridas')
        await self.page.keyboard.press('Escape')
        await self.page.get_by_role('button',name='Editar datos de origen',exact=True).click();await self.ready_case()
        await expect(self.page.locator('[data-t4-slot]')).to_have_count(2)
        await expect(self.page.get_by_role('button',name='Publicar versión del Pack',exact=True)).to_be_disabled()
        self.assertIn('case_id='+cid,self.page.url)
        await self.page.locator('.j102-footer .j101-back').click();await self.page.locator('[data-ux05-ready=true]').wait_for()
        await self.page.goto(self.base+'/app/ddas/logistics/case?case_id='+cid+'&core_step=1&return_view=logistics-map');await self.ready_case()
        await expect(self.page.locator('[data-model-review]')).to_have_attribute('data-review-version',self.v['version']['id'])
        await expect(self.page.locator('[data-model-review]')).to_have_attribute('data-review-case',cid)
        self.assertEqual(before,await self.database_snapshot())
        await self.page.get_by_role('button',name='Crear Case con otra versión',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Preparar derivado',exact=True).click();await self.ready_case()
        await expect(self.page.locator('.j102-origin')).to_contain_text(cid);self.assertNotIn('case_id=',self.page.url)
        self.assertEqual(before,await self.database_snapshot())

    async def test_18_graph_frozen_data_derivation_preserves_revision_and_case(self):
        await self.selected_definition('J102 Origen congelado');await self.prepare_data()
        for entity in ['transport_demand','transport_resources']:await self.upload_entity(entity)
        cid=await self.finish_case()
        # Existing graph fixture installs a synthetic error run; real workers are
        # exercised separately by tests/e2e/test_decision_case_j102.py.
        rid=await legacy_navigation.UltimateNavigationTests.install(self,cid,status='error')
        before=await self.database_snapshot();revision=(await self.api('GET','/api/platform/logistics-cases/'+cid+'/context'))['case_definition']['id']
        await self.page.reload();await self.page.locator('[data-ux05-ready=true]').wait_for()
        await self.page.get_by_role('button',name='Editar datos de origen',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Preparar nuevo Decision Case',exact=True).click();await self.ready_case()
        await expect(self.page.get_by_label('Nombre del Case',exact=True)).to_have_value('J102 Origen congelado')
        stored=await self.page.evaluate("()=>JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k=>k.startsWith('dation.cases.working.v2.')))).draft")
        self.assertEqual(stored['provenance']['parent_case_id'],cid);self.assertEqual(stored['provenance']['parent_definition_revision_id'],revision)
        self.assertNotEqual(stored['id'],cid);self.assertIsNone(stored['confirmedDefinition']);self.assertEqual(before,await self.database_snapshot())
        self.assertIn(rid,[r['id'] for r in before['runs']])

    async def test_19_expired_stage_explicit_cleanup_creates_one_new_private_session(self):
        await self.selected_definition('J102 Preparación vencida');await self.prepare_data();await self.upload_entity('transport_demand')
        pid=self.sql("SELECT id FROM dation_private.journey_preparations WHERE status='DRAFT' ORDER BY created_at DESC LIMIT 1;")
        self.sql("UPDATE dation_private.journey_preparations SET expires_at=now()-interval '1 second' WHERE id='"+pid+"';")
        before=await self.database_snapshot();await self.page.reload();await self.ready_case()
        await expect(self.page.locator('.journey-preparation-status')).to_contain_text('venció')
        await self.page.get_by_role('button',name='Limpiar preparación expirada e iniciar otra',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Limpiar e iniciar',exact=True).click()
        await expect(self.page.locator('[data-preparation-entity]')).to_have_count(2)
        await expect(self.page.locator('[data-j102-finalize]')).to_be_disabled()
        self.assertEqual(self.sql("SELECT count(*) FROM dation_private.journey_uploads WHERE preparation_id='"+pid+"' AND NOT cleaned;"),'0')
        self.assertEqual(self.sql("SELECT count(*) FROM dation_private.journey_preparations WHERE status='DRAFT';"),'1')
        self.assertEqual(before,await self.database_snapshot())

    async def test_20_paged_manual_picker_presets_modes_and_custom_validation(self):
        published=[]
        for i in range(27):published.append(await self.model('J102 Paginado '+str(i).zfill(2)))
        before=await self.database_snapshot();await self.begin_case('J102 Opciones explícitas')
        await self.page.get_by_label('Buscar modelos publicados',exact=True).fill('J102 Paginado')
        await self.page.get_by_role('button',name='Buscar modelos',exact=True).click()
        await expect(self.page.get_by_label('Logistics Model',exact=True).locator('option')).to_have_count(26)
        await self.page.get_by_role('button',name='Más modelos',exact=True).click()
        await expect(self.page.get_by_label('Logistics Model',exact=True).locator('option')).to_have_count(3)
        model=self.page.get_by_label('Logistics Model',exact=True);await expect(model).to_have_value('')
        chosen=await model.locator('option').nth(1).get_attribute('value');await model.select_option(chosen)
        version=self.page.get_by_label('Versión publicada',exact=True);await expect(version).to_be_enabled();await expect(version).to_have_value('')
        await self.page.get_by_label('Inicio de planificación',exact=True).fill('2026-11-02')
        await self.page.get_by_role('button',name='Proponer fecha de fin',exact=True).click()
        await expect(self.page.get_by_label('Fin de planificación',exact=True)).to_have_value('2026-11-08')
        await self.page.get_by_label('Horizonte',exact=True).select_option('DAILY')
        await self.page.get_by_role('button',name='Proponer fecha de fin',exact=True).click();await self.page.keyboard.press('Escape')
        await expect(self.page.get_by_label('Fin de planificación',exact=True)).to_have_value('2026-11-08')
        await self.page.get_by_role('button',name='Proponer fecha de fin',exact=True).click();await self.page.get_by_role('dialog').get_by_role('button',name='Actualizar fin',exact=True).click()
        await expect(self.page.get_by_label('Fin de planificación',exact=True)).to_have_value('2026-11-02')
        await self.page.get_by_label('Modalidad',exact=True).select_option('SIMULATION')
        await expect(self.page.get_by_label('Objetivo global',exact=True).locator('option')).to_have_count(6)
        await self.page.get_by_label('Objetivo global',exact=True).select_option('CUSTOM')
        await self.page.get_by_label('Costo (%)',exact=True).fill('10');await self.page.locator('[data-case-confirm="4"]').click()
        await expect(self.page.locator('[data-block-error="4"]')).to_contain_text('100')
        await self.page.get_by_label('Costo (%)',exact=True).fill('25');await self.page.locator('[data-case-confirm="4"]').click();await expect(self.page.locator('[data-case-confirm="4"]')).to_be_disabled()
        await self.page.get_by_label('Cobertura mínima de demanda crítica (%)',exact=True).fill('101');await self.page.locator('[data-case-confirm="5"]').click()
        await expect(self.page.locator('[data-block-error="5"]')).to_contain_text('100')
        await expect(self.page.get_by_role('button',name='Confirmar definición',exact=True)).to_be_disabled();self.assertEqual(before,await self.database_snapshot())
