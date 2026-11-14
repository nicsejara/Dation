"""UX 03: strategic setup using owned API/PostgREST/SQL, never decision engines."""
import asyncio
import json
import unittest
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
from playwright.async_api import expect
import test_ultimate_case_setup as setup
import test_ultimate_case_data as data
import test_saga01_planning as saga
from wizard_helpers import select_model,show_case

OUT=Path('/tmp/dation-ux03-browser')
GOALS=[('MINIMIZE_COST','Minimizar costo'),('MAXIMIZE_SERVICE','Maximizar servicio'),('MAXIMIZE_OWN_CAPACITY','Maximizar capacidad propia'),('MINIMIZE_TRIPS','Minimizar viajes'),('BALANCED','Balanceado'),('CUSTOM','Personalizado')]


class DecisionCaseWizardTests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(data.UltimateCaseDataTests.setUpClass.__func__)
    tearDownClass=classmethod(setup.UltimateCaseSetupTests.tearDownClass.__func__)
    login=setup.UltimateCaseSetupTests.login
    request=setup.UltimateCaseSetupTests.request
    api=setup.UltimateCaseSetupTests.api
    model=setup.UltimateCaseSetupTests.model
    case=setup.UltimateCaseSetupTests.case
    open=setup.UltimateCaseSetupTests.open
    fill_case=saga.Saga01PlanningTests.fill_case
    create=saga.Saga01PlanningTests.create

    async def asyncSetUp(self):
        await setup.UltimateCaseSetupTests.asyncSetUp(self)
        self.calls=[]
        self.page.on('request',lambda r:self.calls.append((r.method,urlparse(r.url).path,r.post_data_json if r.method in ['POST','PATCH'] and '/logistics-cases' in r.url else None)))

    async def asyncTearDown(self):
        await setup.UltimateCaseSetupTests.asyncTearDown(self)
        self.assertFalse(any(method=='POST' and (path.startswith('/api/runs') or '/execute' in path) for method,path,_ in self.calls),self.calls)

    async def selected(self,m=None,v=None):
        if m is None:m,v=await self.model('Modelo UX 03')
        await self.open('/app/ddas/logistics/case');await select_model(self.page,m['model']['id'],v['version']['id'])
        await self.page.get_by_role('button',name='Continuar a Decision Case',exact=True).click()
        return m,v

    def advanced(self):return self.page.locator('.ultimate-policy')
    def footer(self):return self.page.locator('.decision-case-footer')
    def writes(self):return [body for method,path,body in self.calls if method=='POST' and path=='/api/platform/logistics-cases']

    async def test_01_incomplete_progress_summary_and_informative_flow(self):
        await self.selected()
        self.assertEqual(await self.page.locator('[data-dation-test=core-case] .ultimate-disclosure__title').text_content(),'03. Decision Case')
        self.assertEqual(await self.page.locator('.decision-case-card').count(),5)
        self.assertEqual(await self.page.locator('[name=primary_goal]').count(),6)
        self.assertEqual(await self.page.get_by_role('radiogroup',name='Objetivo global',exact=True).get_by_role('radio').count(),6)
        await expect(self.page.get_by_role('radio',name='Minimizar costo',exact=True)).to_be_checked()
        self.assertEqual(await self.page.get_by_label('Inicio de planificación',exact=True).input_value(),'')
        self.assertEqual(await self.page.get_by_label('Fin de planificación',exact=True).input_value(),'')
        self.assertEqual(await self.page.get_by_label('Decision Owner inicial (D1 y D2)',exact=True).input_value(),'')
        await expect(self.footer()).to_have_attribute('data-case-ready','false')
        self.assertFalse(await self.advanced().evaluate('n=>n.open'))
        flow=self.page.locator('[data-dation-test=case-flow]');self.assertEqual(await flow.locator('button,input,a,[tabindex]').count(),0)
        before=len(self.calls);url=self.page.url
        await flow.get_by_text('D1 · Asignación',exact=True).click();await flow.get_by_text('D2 · Planificación',exact=True).click()
        self.assertEqual(len(self.calls),before);self.assertEqual(self.page.url,url)
        await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click()
        self.assertEqual(self.writes(),[])
        self.assertEqual(await self.page.evaluate('document.activeElement.name'),'case_name')
        await expect(self.page.locator('.ultimate-errors')).to_be_visible()
        await self.page.get_by_label('Nombre del Case',exact=True).fill('   ');await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click();self.assertEqual(self.writes(),[])
        self.assertEqual(await self.page.get_by_label('Nombre del Case',exact=True).get_attribute('maxlength'),'120')
        self.assertEqual(await self.page.get_by_label('Descripción (opcional)',exact=True).get_attribute('maxlength'),'1000')
        self.assertEqual(await self.page.locator('.ultimate-foundation form button[type=submit]').count(),1)
        await expect(self.page.locator('.decision-case-review')).to_contain_text('2 contratos generados')

    async def test_02_six_goals_reload_and_exact_policy_payloads(self):
        m,v=await self.model();before=await self.api('GET','/api/platform/logistics-models/'+m['model']['id'])
        for index,(goal,label) in enumerate(GOALS):
            with self.subTest(goal=goal):
                await self.selected(m,v);await self.fill_case('Estrategia '+label)
                await self.page.get_by_role('radio',name=label,exact=True).check()
                self.assertEqual(await self.page.locator('[name=primary_goal]:checked').count(),1)
                if not await self.advanced().evaluate('n=>n.open'):await self.advanced().locator('summary').click()
                await self.page.get_by_role('checkbox',name='Cobertura mínima de demanda',exact=True).check()
                await self.page.get_by_label('Cobertura mínima de demanda (%)',exact=True).fill('10.01')
                if goal=='CUSTOM':
                    for label,value in [('Costo','10.01'),('Viajes','19.99'),('Servicio','30'),('Capacidad propia','40')]:await self.page.get_by_label(label+' (%)',exact=True).fill(value)
                self.page.once('dialog',lambda d:d.accept());await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for();await show_case(self.page)
                await expect(self.page.get_by_role('radio',name=dict(GOALS)[goal],exact=True)).to_be_checked()
                await expect(self.footer()).to_have_attribute('data-case-ready','true')
                cid=await self.create();body=self.writes()[-1]
                expected={'version':1,'primary_goal':goal,'guardrails':[{'kind':'MINIMUM_DEMAND_COVERAGE','hard':True,'limit':'0.1001'}],'preferences':[{'kind':key,'weight':weight} for key,weight in [('COST','0.1001'),('TRIPS','0.1999'),('SERVICE','0.3'),('OWN_CAPACITY','0.4')]] if goal=='CUSTOM' else []}
                self.assertEqual(body['case_policy'],expected)
                context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context')
                self.assertEqual(context['case']['logistics_model_version_id'],v['version']['id']);self.assertEqual(context['planning_context']['case_policy'],expected)
                self.assertEqual(len(self.writes()),index+1)
        self.assertEqual(await self.api('GET','/api/platform/logistics-models/'+m['model']['id']),before)
        self.assertFalse(any(method=='POST' and path=='/api/platform/logistics-models' for method,path,_ in self.calls))

    async def test_03_custom_errors_reveal_focus_and_guard_values_survive_switch(self):
        await self.selected();await self.fill_case()
        await self.page.get_by_role('radio',name='Personalizado',exact=True).check()
        self.assertTrue(await self.advanced().evaluate('n=>n.open'))
        await self.page.get_by_label('Costo (%)',exact=True).fill('10')
        await expect(self.footer()).to_have_attribute('data-case-ready','false')
        await self.advanced().locator('summary').click()
        await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click()
        self.assertTrue(await self.advanced().evaluate('n=>n.open'))
        self.assertEqual(await self.page.evaluate('document.activeElement.name'),'weight_COST')
        await expect(self.page.get_by_label('Costo (%)',exact=True)).to_have_attribute('aria-invalid','true')
        await expect(self.page.get_by_role('link',name='Las preferencias deben sumar 100 %.')).to_be_visible()
        self.assertEqual(self.writes(),[])
        guard=self.page.get_by_label('Cobertura mínima de demanda (%)',exact=True);check=self.page.get_by_role('checkbox',name='Cobertura mínima de demanda',exact=True)
        await check.check();await guard.fill('100.01');await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click()
        self.assertEqual(await self.page.evaluate('document.activeElement.name'),'guard_MINIMUM_DEMAND_COVERAGE')
        await guard.fill('10.01');await check.uncheck();await expect(guard).to_be_disabled();self.assertEqual(await guard.input_value(),'10.01')
        await check.check();await expect(guard).to_be_enabled()
        await self.page.get_by_role('radio',name='Minimizar costo',exact=True).check();await expect(self.footer()).to_have_attribute('data-case-ready','true')
        await self.page.get_by_role('radio',name='Personalizado',exact=True).check();self.assertEqual(await self.page.get_by_label('Costo (%)',exact=True).input_value(),'10')
        for label,value in [('Costo','10.01'),('Viajes','19.99'),('Servicio','30'),('Capacidad propia','40')]:await self.page.get_by_label(label+' (%)',exact=True).fill(value)
        await expect(self.footer()).to_have_attribute('data-case-ready','true')

    async def test_04_mode_and_horizons_keep_utc_custom_dates_and_range_validation(self):
        await self.selected();await self.fill_case()
        start=self.page.get_by_label('Inicio de planificación',exact=True);end=self.page.get_by_label('Fin de planificación',exact=True);kind=self.page.get_by_label('Tipo de horizonte',exact=True)
        await start.fill('2028-02-28');await start.press('Tab')
        for value,expected in [('DAILY','2028-02-28'),('MONTHLY','2028-02-29'),('WEEKLY','2028-03-05')]:
            await kind.select_option(value);await expect(end).to_have_value(expected)
        await kind.select_option('CUSTOM');await end.fill('2028-03-03');await start.fill('2028-03-06');await start.press('Tab')
        self.assertEqual(await end.input_value(),'2028-03-03');await expect(self.footer()).to_have_attribute('data-case-ready','false')
        await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click()
        self.assertEqual(await self.page.evaluate('document.activeElement.name'),'planning_end');self.assertEqual(self.writes(),[])
        await end.fill('2028-03-09');before=len(self.calls);await self.page.get_by_role('radio',name='Simulación',exact=True).check()
        self.assertEqual(len(self.calls),before);await expect(self.page.locator('.decision-case-review')).to_contain_text('Simulación')
        cid=await self.create();context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context')
        self.assertEqual((context['case']['operating_mode'],context['case']['horizon_type'],context['case']['planning_start'],context['case']['planning_end']),('SIMULATION','CUSTOM','2028-03-06','2028-03-09'))

    async def test_05_no_assign_permission_allows_pending_owner_without_inventing_one(self):
        m,v=await self.model();uid='10000000-0000-4000-8000-000000000003'
        member=next(x for x in (await self.api('GET','/api/platform/team'))['members'] if x['user_id']==uid)
        await self.api('PATCH','/api/platform/team/members/'+uid,{'expected_updated_at':member['updated_at'],'access_role':'operator','status':'active','business_roles':[]})
        admin=await self.browser.new_context();await self.login(admin)
        try:
            await self.login(self.context,3);await self.selected(m,v)
            owner=self.page.get_by_label('Decision Owner inicial (D1 y D2)',exact=True);await expect(owner).to_be_disabled();self.assertEqual(await owner.input_value(),'')
            await self.page.get_by_label('Nombre del Case',exact=True).fill('Owner pendiente')
            await self.page.get_by_label('Inicio de planificación',exact=True).fill('2026-11-16');await self.page.get_by_label('Inicio de planificación',exact=True).press('Tab')
            await expect(self.footer()).to_have_attribute('data-case-ready','true')
            cid=await self.create();self.assertIsNone(self.writes()[-1]['decision_owner_user_id'])
            context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context')
            self.assertTrue(all(stage['owner'] is None for stage in context['responsibilities']['stages'].values()))
        finally:
            team=await self.request('GET','/api/platform/team',context=admin);self.assertEqual(team.status,200)
            member=next(x for x in (await team.json())['members'] if x['user_id']==uid)
            response=await self.request('PATCH','/api/platform/team/members/'+uid,{'expected_updated_at':member['updated_at'],'access_role':'viewer','status':'active','business_roles':[]},context=admin);self.assertEqual(response.status,200,await response.text())
            await admin.close()

    async def test_06_no_eligible_owner_blocks_readiness_and_submission(self):
        async def nobody(route):await route.fulfill(json={'members':[],'total':0})
        await self.page.route('**/api/platform/team?*',nobody);await self.selected()
        await self.page.get_by_label('Nombre del Case',exact=True).fill('Sin personas elegibles')
        await self.page.get_by_label('Inicio de planificación',exact=True).fill('2026-11-16');await self.page.get_by_label('Inicio de planificación',exact=True).press('Tab')
        await expect(self.footer()).to_have_attribute('data-case-ready','false')
        await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click()
        self.assertEqual(await self.page.evaluate('document.activeElement.name'),'decision_owner_user_id');self.assertEqual(self.writes(),[])
        await expect(self.page.get_by_text('No hay personas elegibles. Revisá las responsabilidades en Equipo antes de asignar.',exact=True)).to_be_visible()

    async def test_07_existing_case_patch_keeps_revision_version_and_stage_owners(self):
        m,v,c=await self.case();cid=c['case']['id']
        await self.api('PUT','/api/platform/decisions/'+cid+'/responsibilities/logistics_scheduling',{'expected_updated_at':c['responsibilities']['stages']['logistics_scheduling']['updated_at'],'owner_user_id':None})
        c=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context');await self.open('/app/ddas/logistics/case?case_id='+cid)
        await self.page.get_by_label('Nombre del Case',exact=True).fill('Contexto actualizado')
        await self.page.get_by_role('radio',name='Balanceado',exact=True).check();await self.page.get_by_role('radio',name='Simulación',exact=True).check()
        await self.page.get_by_label('Decision Owner · Planificación de despachos',exact=True).select_option(setup.ADMIN)
        await self.page.get_by_role('button',name='Guardar contexto',exact=True).click()
        await self.page.locator('[data-ultimate-ready=true]').wait_for()
        await self.page.wait_for_function('document.querySelector("[name=case_name]")?.value==="Contexto actualizado" && document.querySelector(".decision-case-footer [role=status]")?.textContent==="Sin cambios pendientes."')
        patches=[body for method,path,body in self.calls if method=='PATCH' and path.endswith('/context')];self.assertEqual(len(patches),1)
        body=patches[0];self.assertEqual(body['expected_updated_at'],c['case']['updated_at']);self.assertEqual(body['case_policy']['primary_goal'],'BALANCED');self.assertEqual(body['operating_mode'],'SIMULATION')
        self.assertEqual(body['owner_updates'],[{'node_id':'logistics_scheduling','owner_user_id':setup.ADMIN,'expected_updated_at':c['responsibilities']['stages']['logistics_scheduling']['updated_at']}])
        after=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context');self.assertEqual(after['case']['logistics_model_version_id'],v['version']['id']);self.assertEqual(after['responsibilities']['stages']['logistics_assignment']['owner']['id'],setup.ADMIN)
        self.assertEqual(self.writes(),[])

    async def test_08_frozen_and_viewer_contexts_keep_protected_fields_disabled(self):
        _,_,c=await self.case();cid=c['case']['id'];pattern='**/api/platform/logistics-cases/'+cid+'/context'
        async def frozen(route):
            if route.request.method!='GET':return await route.continue_()
            response=await route.fetch();body=await response.json();body['case']['context_frozen_at']='2026-11-14T12:00:00Z';await route.fulfill(json=body)
        await self.page.route(pattern,frozen);await self.open('/app/ddas/logistics/case?case_id='+cid)
        for n in await self.page.locator('[name=primary_goal],[name=operating_mode],[name=horizon_type],[name=planning_start],[name=planning_end]').all():await expect(n).to_be_disabled()
        await expect(self.page.get_by_label('Nombre del Case',exact=True)).to_be_enabled()
        await self.page.get_by_label('Nombre del Case',exact=True).fill('Identidad permitida congelada')
        await self.page.get_by_role('button',name='Guardar contexto',exact=True).click()
        await self.page.wait_for_function('document.querySelector("[name=case_name]")?.value==="Identidad permitida congelada" && document.querySelector(".decision-case-footer [role=status]")?.textContent==="Sin cambios pendientes."')
        body=[body for method,path,body in self.calls if method=='PATCH' and path.endswith('/context')][-1]
        for key in ['case_policy','planning_start','planning_end','horizon_type','operating_mode']:self.assertNotIn(key,body)
        viewer=await self.browser.new_context(viewport={'width':390,'height':844});await self.login(viewer,3);page=await viewer.new_page();await page.goto(self.base+'/app/ddas/logistics/case?case_id='+cid);await page.locator('[data-ultimate-ready=true]').wait_for()
        await expect(page.get_by_label('Nombre del Case',exact=True)).to_be_disabled();await expect(page.get_by_role('button',name='Guardar contexto',exact=True)).to_be_disabled()
        for n in await page.get_by_role('radio').all():await expect(n).to_be_disabled()
        await viewer.close()

    async def test_09_lost_create_ack_double_click_and_refresh_reuse_exact_intent(self):
        await self.selected();await self.fill_case('Recuperación del nuevo Case')
        entered=asyncio.Event();release=asyncio.Event()
        async def lost(route):
            response=await route.fetch();self.assertEqual(response.status,200);entered.set();await release.wait();await route.abort('timedout')
        pattern='**/api/platform/logistics-cases';await self.page.route(pattern,lost)
        submit=self.page.get_by_role('button',name='Finalizar configuración',exact=True);await submit.click();await asyncio.wait_for(entered.wait(),12)
        await expect(submit).to_be_disabled();self.assertEqual(await submit.get_attribute('aria-busy'),'true');await submit.evaluate('n=>{n.click();n.click();}')
        self.assertEqual(len(self.writes()),1);release.set()
        await expect(self.page.locator('.decision-case-footer [role=alert]')).to_contain_text('Crear Decision Case:')
        await self.page.unroute(pattern,lost);self.page.once('dialog',lambda d:d.accept());await self.page.reload();await self.page.locator('[data-ultimate-ready=true]').wait_for();await show_case(self.page)
        cid=await self.create();self.assertEqual(len(self.writes()),2);self.assertEqual(self.writes()[0],self.writes()[1]);self.assertEqual(cid,self.writes()[0]['id'])
        context=await self.api('GET','/api/platform/logistics-cases/'+cid+'/context');self.assertEqual(context['case']['label'],'Recuperación del nuevo Case')
        self.assertFalse(any(method=='POST' and path=='/api/platform/logistics-models' for method,path,_ in self.calls))

    async def test_10_visual_states_responsive_keyboard_and_draft_navigation(self):
        await self.selected();OUT.mkdir(exist_ok=True);measurements=[]
        async def capture(name):
            await self.page.mouse.move(0,0);await self.page.evaluate('scrollTo(0,0)');await self.page.screenshot(path=str(OUT/name),full_page=True,animations='disabled')
        for width,height in [(1536,1024),(1024,900),(768,1024),(390,844),(320,844)]:
            await self.page.set_viewport_size({'width':width,'height':height})
            result=await self.page.evaluate('''()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,controls:[...document.querySelectorAll('.decision-case-step input,.decision-case-step select,.decision-case-step textarea,.decision-case-footer button')].filter(n=>n.getClientRects().length).map(n=>({name:n.name,left:n.getBoundingClientRect().left,right:n.getBoundingClientRect().right}))})''')
            radios=await self.page.locator('.decision-case-radio').evaluate_all('nodes=>nodes.filter(n=>n.getClientRects().length).map(n=>({w:n.getBoundingClientRect().width,h:n.getBoundingClientRect().height,layout:getComputedStyle(n.parentElement).display}))');self.assertTrue(all(abs(n['w']-18)<1 and abs(n['h']-18)<1 and n['layout']=='flex' for n in radios),radios)
            self.assertLessEqual(result['scroll'],width+1,result);self.assertTrue(all(n['left']>=0 and n['right']<=width+1 for n in result['controls']),result);measurements.append(result)
            if width in [1536,1024,390]:await capture(f'decision-case-{width}.png')
        await self.page.set_viewport_size({'width':1536,'height':1024});await self.fill_case('Planificación región sur')
        await expect(self.footer()).to_have_attribute('data-case-ready','true');await capture('decision-case-1536-ready.png')
        await self.page.get_by_role('radio',name='Personalizado',exact=True).check()
        for label,value in [('Costo','10'),('Viajes','20'),('Servicio','30'),('Capacidad propia','40')]:await self.page.get_by_label(label+' (%)',exact=True).fill(value)
        await self.page.get_by_role('checkbox',name='Cobertura mínima de demanda',exact=True).check();await self.page.get_by_label('Cobertura mínima de demanda (%)',exact=True).fill('80')
        await capture('decision-case-1536-custom.png')
        await self.page.set_viewport_size({'width':390,'height':844});await capture('decision-case-390-custom.png')
        await self.page.set_viewport_size({'width':1536,'height':1024});await self.page.get_by_label('Costo (%)',exact=True).fill('11');await self.advanced().locator('summary').click();await self.page.get_by_role('button',name='Finalizar configuración',exact=True).click()
        self.assertEqual(await self.page.evaluate('document.activeElement.name'),'weight_COST');await capture('decision-case-validation.png')
        await self.page.get_by_label('Costo (%)',exact=True).fill('10')
        before=len(self.calls)
        for step in [1,2,3]:await self.page.locator('[data-dation-test=core-step-'+str(step)+']').click()
        self.assertEqual(len(self.calls),before);self.assertEqual(await self.page.get_by_label('Costo (%)',exact=True).input_value(),'10')
        self.assertEqual(await self.page.get_by_label('Nombre del Case',exact=True).input_value(),'Planificación región sur')
        radio=self.page.get_by_role('radio',name='Minimizar costo',exact=True);await radio.focus();await self.page.keyboard.press('ArrowRight')
        await expect(self.page.get_by_role('radio',name='Maximizar servicio',exact=True)).to_be_checked()
        audit=await self.page.evaluate((setup.ROOT/'tests/browser/theme_audit.js').read_text(),'.decision-case-step')
        self.assertEqual(audit['failures'],[],audit)
        (OUT/'contrast.json').write_text(json.dumps(audit,indent=2));(OUT/'responsive.json').write_text(json.dumps(measurements,indent=2))


if __name__=='__main__':unittest.main()
