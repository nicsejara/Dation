"""Focused browser checks for ownership, context switches and recovery UX."""
import asyncio
import copy
import json
import unittest
from urllib.parse import parse_qs,urlparse
import test_navigation as navigation


class WorkflowContextTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):navigation.NavigationTests.setUpClass()
    @classmethod
    def tearDownClass(cls):navigation.NavigationTests.tearDownClass()

    async def asyncSetUp(self):
        self.b=navigation.NavigationTests();await self.b.asyncSetUp();self.page=self.b.page
        self.person={'id':'10000000-0000-4000-8000-000000000001','name':'Persona elegible','active':True,'access_role':'admin'}
        self.snapshot={'case_id':self.b.case['id'],'gates_enforced':True,'attributes_applied':True,'can_assign':True,'policy_version':1,'stages':{
            'data_owner':{'owner':self.person,'owner_eligible':True,'approver':None,'approver_eligible':False,'updated_at':'2026-10-21T00:00:00Z'},
            'logistics_assignment':{'owner':None,'owner_eligible':False,'approver':None,'approver_eligible':False,'updated_at':None},
            'logistics_scheduling':{'owner':None,'owner_eligible':False,'approver':None,'approver_eligible':False,'updated_at':None}}}
        self.snapshot['stages']['data_preparation']=self.snapshot['stages']['data_owner']
        self.b.workflows[self.b.case['id']]=self.snapshot
        self.attribute_requests=[]
        self.b.context.on('request',lambda request:self.attribute_requests.append(request.post_data_json)
            if request.method=='PUT' and urlparse(request.url).path.endswith('/attributes') else None)
        original=self.b.hydrated
        self.b.hydrated=lambda:{**original(),'workflow_responsibilities':copy.deepcopy(self.snapshot)}
        self.writes=[];self.people_queries=[];self.candidate_gate=None;self.no_candidates=False;self.assignment_conflict=False;self.readiness_calls=0
        async def hydrated(route):
            if route.request.method!='GET':await route.fallback();return
            cid=urlparse(route.request.url).path.split('/')[-1]
            bundle=self.b.hydrated() if cid==self.b.case['id'] else self.b.other_cases.get(cid)
            if not bundle:await route.fallback();return
            data=copy.deepcopy(bundle);data['workflow_responsibilities']=copy.deepcopy(self.b.workflows[cid]);data['workflow_responsibilities']['case_id']=cid
            if data['case'].get('status')=='archived':data['workflow_responsibilities']['can_assign']=False
            await route.fulfill(json=data)
        async def workflow(route):
            request=route.request;parts=urlparse(request.url).path.split('/');cid=parts[4];target=self.b.workflows[cid]
            if request.method=='PUT':
                body=request.post_data_json;self.writes.append(body)
                key='data_owner' if parts[-1]=='data_preparation' else parts[-1]
                stage=target['stages'][key]
                if self.assignment_conflict or body['expected_updated_at']!=stage['updated_at']:await route.fulfill(status=409,json={'detail':'Assignment changed'});return
                stage.update(owner=copy.deepcopy(self.person) if body['owner_user_id'] else None,owner_eligible=bool(body['owner_user_id']))
                stage.update(approver=stage['owner'] if key!='data_owner' else None,approver_eligible=bool(stage['owner']) and key!='data_owner')
                stage['updated_at']='2026-10-21T01:00:00Z'
                if key=='data_owner':target['stages']['data_preparation']=stage
            if parts[-1]=='workflow-readiness':
                self.readiness_calls+=1
                ready=target['attributes_applied'] and target['stages']['data_owner']['owner_eligible']
                await route.fulfill(status=200 if ready else 409,json={'ready':True} if ready else {'detail':'Falta responsable de datos'});return
            result=copy.deepcopy(target);result['case_id']=cid;await route.fulfill(json=result)
        async def candidates(route):
            query=parse_qs(urlparse(route.request.url).query);self.people_queries.append(query)
            if self.candidate_gate:await self.candidate_gate.wait()
            members=[] if self.no_candidates else [{'user_id':self.person['id'],'name':self.person['name'],'email':'person@example.test'}]
            await route.fulfill(json={'members':members,'total':len(members),'limit':25,'offset':0})
        await self.b.context.route('**/api/platform/decisions/*/responsibilities**',workflow)
        await self.b.context.route('**/api/platform/decisions/*/workflow-readiness',workflow)
        await self.b.context.route('**/api/platform/team?**',candidates)
        await self.b.context.route('**/api/decision-cases/*',hydrated)

    async def asyncTearDown(self):await self.b.asyncTearDown()

    def decision_selector(self,node='logistics_assignment',field='owner'):
        return self.page.locator('[data-workflow-responsibility="'+node+'"][data-responsibility-field="'+field+'"]')

    async def select_person(self,node='logistics_assignment',field='owner'):
        root=self.decision_selector(node,field)
        await root.get_by_role('button',name='Seleccionar responsable',exact=True).click()
        await root.locator('select').select_option(self.person['id'])
        await root.get_by_role('button',name='Guardar',exact=True).click()
        await self.page.wait_for_function('(args)=>window.DationDispatch.getWorkspace().workflow.stages[args[0]][args[1]+"_eligible"]',arg=[node,field])

    async def test_map_assignment_is_consumed_readonly_by_config_and_review(self):
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app?view=logistics-config&case_id={self.b.case["id"]}&node_id=logistics_assignment')
        await self.page.locator('[data-map-node=logistics_assignment]').first.wait_for()
        self.assertEqual(await self.page.evaluate('window.dationGetCurrentView()'),'logistics-map')
        self.assertEqual(await self.page.locator('[data-config-review]').count(),0)
        await self.select_person()
        self.assertEqual(self.people_queries[0]['responsibility'],['decision_owner'])
        self.assertEqual(self.writes[0],{'expected_updated_at':None,'owner_user_id':self.person['id']})
        await self.b.open('logistics-config','logistics_assignment')
        review=self.page.locator('[data-config-review]');self.assertFalse(await review.is_disabled())
        self.assertEqual(await self.page.locator('[data-workflow-responsibility]').count(),0)
        await review.click();dialog=self.page.get_by_role('dialog',name='Revisar Assignment antes de ejecutar')
        await dialog.get_by_text('Persona elegible',exact=True).wait_for()
        self.assertIn('case_id='+self.b.case['id'],self.page.url);self.assertEqual(self.b.execution_bodies,[])

    async def test_empty_candidates_and_conflict_preserve_the_map_assignment(self):
        self.no_candidates=True;await self.b.open('logistics-map')
        root=self.decision_selector();await root.get_by_role('button',name='Seleccionar responsable').click()
        await root.get_by_text('No hay personas elegibles.',exact=False).wait_for()
        self.assertTrue(await root.get_by_role('button',name='Guardar',exact=True).is_disabled())
        self.assertEqual(await root.get_by_role('searchbox').count(),0)
        self.assertEqual(await root.get_by_role('button',name='Siguiente',exact=True).count(),0)
        await root.get_by_role('button',name='Cancelar',exact=True).click()
        self.no_candidates=False;self.assignment_conflict=True
        await root.get_by_role('button',name='Seleccionar responsable').click()
        await root.locator('select').select_option(self.person['id'])
        await root.get_by_role('button',name='Guardar',exact=True).click()
        await root.get_by_role('button',name='Actualizar etapa',exact=True).wait_for()
        self.assertFalse(self.snapshot['stages']['logistics_assignment']['owner_eligible'])

    async def test_case_context_is_fixed_and_keyboard_navigation_returns_to_its_map(self):
        await self.b.open('decision-dashboard','logistics_assignment',self.b.f['ids']['assignment'])
        self.assertEqual(await self.page.locator('[data-case-switcher],[data-select-case]').count(),0)
        before=len(self.b.requests)
        link=self.page.locator('.dda-navigation a').last
        await link.focus();await self.page.keyboard.press('Enter')
        await self.page.locator('[data-map-node=logistics_assignment]').first.wait_for()
        self.assertIn('case_id='+self.b.case['id'],self.page.url)
        self.assertNotIn('run_id=',self.page.url)
        self.assertFalse(any(path=='/api/platform/decisions' for _,path in self.b.requests[before:]))

    async def test_viewer_and_late_candidates_do_not_gain_mutation_controls(self):
        self.b.access_role='viewer';self.snapshot['can_assign']=False
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app?view=logistics-config&case_id={self.b.case["id"]}&node_id=logistics_assignment')
        await self.page.locator('[data-map-node=logistics_assignment]').first.wait_for()
        self.assertEqual(await self.page.evaluate('window.dationGetCurrentView()'),'logistics-map')
        self.assertEqual(await self.page.locator('[data-workflow-responsibility] button').count(),0)
        self.assertEqual(await self.page.locator('[data-config-review]').count(),0)
        self.b.access_role='admin';self.snapshot['can_assign']=True;self.candidate_gate=asyncio.Event()
        await self.b.open('logistics-map');await self.decision_selector().get_by_role('button',name='Seleccionar responsable').click()
        await self.page.locator('.nav [data-platform-view=platform-home]').click();self.candidate_gate.set()
        await self.page.locator('[data-platform-home] .platform-home__header').wait_for()
        self.assertEqual(await self.page.locator('[data-workflow-responsibility]').count(),0);self.assertEqual(self.writes,[])

    async def test_mobile_reflow_and_status_marker_are_independent_from_selection(self):
        await self.b.open('decision-dashboard','logistics_assignment',self.b.f['ids']['assignment'])
        for width in (1440,768,390,320):
            await self.page.set_viewport_size({'width':width,'height':1000})
            await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
            self.assertLessEqual(await self.page.evaluate('document.documentElement.scrollWidth'),width+1)
        rail=self.page.locator('.assignment-dashboard-v2 .dispatch-decision-tab[data-decision-node=logistics_assignment]').first
        self.assertEqual(await rail.get_attribute('aria-current'),'page')
        self.assertEqual(await rail.get_attribute('data-status-tone'),'success')
        colors=await rail.evaluate('n=>({border:getComputedStyle(n).borderColor,marker:getComputedStyle(n.querySelector("i")).color})')
        self.assertNotEqual(colors['border'],colors['marker'])

    async def test_recovery_and_new_password_finish_on_login_with_generic_confirmation(self):
        async def complete(route):await route.fulfill(json={'message':'Si la cuenta existe, recibirás un enlace.'})
        await self.b.context.route('**/auth/recover',complete);await self.b.context.route('**/auth/password',complete)
        origin=f'http://127.0.0.1:{navigation.NavigationTests.port}'
        await self.page.goto(origin+'/recover');await self.page.get_by_label('Email',exact=True).fill('unknown@example.test')
        await self.page.get_by_role('button',name='Enviar enlace',exact=True).click();await self.page.wait_for_url('**/login?recovery=sent')
        await self.page.get_by_role('status').get_by_text('Si la cuenta existe',exact=False).wait_for()
        await self.page.goto(origin+'/recover?step=password')
        await self.page.get_by_label('Contraseña',exact=True).fill('synthetic-new-password');await self.page.get_by_label('Confirmar contraseña',exact=True).fill('synthetic-new-password')
        await self.page.get_by_role('button',name='Guardar contraseña',exact=True).click();await self.page.wait_for_url('**/login?password=updated')
        await self.page.get_by_role('status').get_by_text('Tu contraseña fue actualizada.',exact=False).wait_for()

    async def test_data_gate_registers_only_on_assignment_and_opens_the_same_case_map(self):
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app?view=logistics-data');await self.b.wait_for_app()
        await self.page.evaluate('inputs=>window.DationDispatch.startNewDecision(inputs)',list(self.b.f['datasets'].values()))
        root=self.page.locator('#dispatch-data-root');await root.locator('[data-case-identity]').wait_for()
        next_button=root.get_by_role('button',name='Seleccioná tu decisión',exact=True)
        self.assertTrue(await next_button.is_disabled())
        self.assertEqual(sum(method=='POST' and path=='/api/decision-cases' for method,path in self.b.requests),0)
        await self.b.assign_data_responsible()
        await self.page.wait_for_function("!document.querySelector('#dispatch-data-root .d-workflow-action-bar button').disabled")
        self.assertEqual(self.people_queries[0]['responsibility'],['data_owner'])
        self.assertEqual(sum(method=='POST' and path=='/api/decision-cases' for method,path in self.b.requests),1)
        self.assertEqual(len(self.attribute_requests),1)
        cid=await self.page.evaluate('window.DationDispatch.getWorkspace().decisionCase.id')
        await next_button.click();await self.page.locator('[data-map-node=logistics_assignment]').first.wait_for()
        self.assertIn('case_id='+cid,self.page.url);self.assertNotIn('run_id=',self.page.url)

    async def test_team_keeps_one_invitation_entry_and_edits_multiple_roles_together(self):
        member={'user_id':self.person['id'],'name':'Persona elegible','email':'person@example.test','access_role':'admin','status':'active','business_role':'decision_owner','business_roles':['decision_owner'],'updated_at':'2026-10-21T00:00:00Z'}
        writes=[]
        async def team(route):
            if route.request.method=='PATCH':
                body=route.request.post_data_json;writes.append(body);member.update(body)
                await route.fulfill(json={'updated_at':member['updated_at']});return
            await route.fulfill(json={'members':[member],'invitations':[],'total':1,'invitation_total':0,'limit':25,'offset':0})
        await self.b.context.route('**/api/platform/team**',team)
        await self.page.goto(f'http://127.0.0.1:{navigation.NavigationTests.port}/app?view=platform-team')
        root=self.page.locator('[data-platform-team]');await root.get_by_role('button',name='Invitar',exact=True).wait_for()
        self.assertEqual(await root.get_by_role('button',name='Invitar',exact=True).count(),1)
        self.assertEqual(await root.get_by_role('button',name='Invitar a alguien',exact=True).count(),0)
        self.assertEqual(await root.get_by_role('link',name='Abrir registro',exact=True).count(),0)
        self.assertNotIn('/register',await root.inner_text())
        await root.get_by_role('button',name='Editar acceso',exact=True).click();dialog=self.page.get_by_role('dialog')
        self.assertEqual(await dialog.get_by_label('Approver',exact=True).count(),0);self.assertTrue(await dialog.get_by_label('Decision Owner',exact=True).is_checked())
        await dialog.get_by_label('Data Owner',exact=True).check();await dialog.get_by_role('button',name='Guardar',exact=True).click()
        await root.get_by_text('Equipo actualizado.',exact=True).wait_for()
        self.assertEqual(set(writes[0]['business_roles']),{'data_owner','decision_owner'})
        self.assertNotIn('business_role',writes[0]);self.assertEqual(writes[0]['expected_updated_at'],'2026-10-21T00:00:00Z')

    async def test_operator_registers_a_pending_data_case_and_refreshes_admin_assignment(self):
        self.b.access_role='operator';self.snapshot['can_assign']=False
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app?view=logistics-data');await self.b.wait_for_app()
        await self.page.evaluate('inputs=>window.DationDispatch.startNewDecision(inputs)',list(self.b.f['datasets'].values()))
        form=self.page.locator('[data-case-identity]');await form.wait_for()
        self.assertEqual(await form.get_by_label('Data Owner',exact=True).count(),0)
        await form.get_by_label('Nombre del Case',exact=True).fill('SEMANA 43')
        await form.get_by_label('Categoría',exact=True).select_option('weekly')
        await form.get_by_role('button',name='Aplicar',exact=True).click()
        await form.get_by_text('Atributos y Data Owner aplicados.',exact=True).wait_for()
        cid=await self.page.evaluate('window.DationDispatch.getWorkspace().decisionCase.id')
        self.assertEqual(sum(m=='POST' and p=='/api/decision-cases' for m,p in self.b.requests),1)
        self.assertTrue(await self.page.locator('.d-workflow-action-bar button').is_disabled())
        self.b.workflows[cid]['stages']['data_owner'].update(owner=self.person,owner_eligible=True)
        await self.page.reload();await self.b.wait_for_app();await form.wait_for()
        await self.page.wait_for_function("document.querySelector('#dispatch-data-root .d-workflow-action-bar button')?.disabled===false")
        self.assertEqual(await self.page.locator('[data-case-identity] select').count(),1)  # Category remains editable; assignment is read-only.
        self.assertEqual(self.writes,[])

    async def test_both_dashboards_keep_approval_blocked_until_an_eligible_approver_is_saved(self):
        original=copy.deepcopy(self.b.case)
        assignment=self.b.f['runs']['assignment'];original_run=copy.deepcopy(assignment)
        for node,kind in (('logistics_assignment','assignment'),('logistics_scheduling','scheduling')):
            with self.subTest(node=node):
                self.b.case=copy.deepcopy(original);assignment.clear();assignment.update(copy.deepcopy(original_run))
                if kind=='assignment':
                    self.b.case['nodes'][node].update(status='review',approved_run_id=None)
                    assignment['approved_at']=None;assignment['result_json']['decision_case'].update(status='review',approved_at=None)
                self.snapshot['stages'][node].update(owner=None,owner_eligible=False,approver=None,approver_eligible=False)
                await self.b.open('decision-dashboard',node,self.b.f['ids'][kind])
                self.assertEqual(await self.page.locator('[data-workflow-responsibility]').count(),0)
                self.assertEqual(await self.page.locator('[data-approve-toolbar]').count(),1)
                self.assertTrue(await self.page.locator('[data-approve-toolbar]').is_disabled())
                await self.b.open('logistics-map');await self.select_person(node,'owner')
                await self.b.open('decision-dashboard',node,self.b.f['ids'][kind])
                await self.page.wait_for_function("document.querySelector('[data-approve-toolbar]')?.disabled===false")
                self.assertEqual(await self.page.locator('[data-responsibility-field=approver]').count(),0)

    async def test_owner_revoked_at_admission_returns_to_config_without_polling_a_phantom_run(self):
        self.snapshot['stages']['logistics_assignment'].update(owner=self.person,owner_eligible=True)
        attempts=[]
        async def reject(route):
            if route.request.method!='POST' or urlparse(route.request.url).path!='/api/runs':await route.fallback();return
            attempts.append(parse_qs(urlparse(route.request.url).query)['run_id'][0])
            self.snapshot['stages']['logistics_assignment']['owner_eligible']=False
            await route.fulfill(status=409,headers={'X-Dation-Workflow-Gate':'decision_owner'},json={'detail':'Seleccioná un responsable de la decisión activo y elegible antes de ejecutar.'})
        await self.b.context.route('**/api/runs?**',reject)
        await self.b.open('logistics-config','logistics_assignment')
        objective=await self.page.evaluate('window.DationDispatch.getWorkspace().objective')
        await self.page.locator('[data-config-review]').click();await self.page.locator('[data-config-execute]').click()
        await self.page.locator('[data-map-node=logistics_assignment]').first.wait_for()
        self.assertEqual(await self.page.evaluate('window.dationGetCurrentView()'),'logistics-map')
        self.assertEqual(await self.page.locator('[data-config-review]').count(),0)
        self.assertEqual(len(attempts),1);self.assertNotIn('run_id=',self.page.url)
        self.assertIn('case_id='+self.b.case['id'],self.page.url)
        self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().objective'),objective)
        self.assertNotIn(('GET','/api/runs/'+attempts[0]),self.b.requests)

    async def test_history_and_archived_maps_remain_readable_after_data_owner_loses_eligibility(self):
        self.snapshot['stages']['data_preparation']['owner_eligible']=False
        for status in ('active','archived'):
            self.b.case['status']=status
            self.b.f['case_row']['status']=status
            await self.b.open('logistics-map')
            await self.page.locator('[data-map-node=logistics_assignment]').first.wait_for()
            self.assertEqual(self.readiness_calls,0)
        self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().decisionCase.status'),'archived')
        self.assertEqual(await self.page.locator('[data-workflow-responsibility] button').count(),0)
        await self.b.open('decision-dashboard','logistics_assignment',self.b.f['ids']['assignment'])
        self.assertTrue(await self.page.locator('.assignment-dashboard-v2').is_visible())
        self.assertEqual(self.b.execution_bodies,[])

    async def test_viewer_cannot_execute_even_when_all_business_responsibilities_are_eligible(self):
        self.b.access_role='viewer';self.snapshot['can_assign']=False
        for stage in self.snapshot['stages'].values():stage.update(owner=self.person,owner_eligible=True,approver=self.person,approver_eligible=True)
        for node in ('logistics_assignment','logistics_scheduling'):
            await self.b.open('logistics-config',node)
            self.assertTrue(await self.page.locator('[data-config-review],[data-scheduling-review]').is_disabled())
            await self.page.get_by_text('Tu rol permite consultar, pero no ejecutar decisiones.',exact=True).first.wait_for()
        self.assertEqual(self.b.execution_bodies,[])

    async def test_data_roles_exist_before_csv_and_stay_below_compatibility(self):
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app?view=logistics-data')
        form=self.page.locator('[data-case-identity]');owner=form.get_by_label('Data Owner',exact=True)
        await owner.locator('option[value="'+self.person['id']+'"]').wait_for(state='attached')
        self.assertEqual(await self.page.locator('[data-workflow-responsibility=data_owner]').count(),1)
        self.assertEqual(await self.page.locator('[data-workflow-responsibility=data_steward]').count(),0)
        self.assertTrue(await form.evaluate('el=>el.contains(document.querySelector("[data-workflow-responsibility=data_owner]"))'))
        self.assertTrue(await form.get_by_role('button',name='Aplicar',exact=True).is_disabled())
        await form.get_by_label('Nombre del Case',exact=True).fill('SEMANA 43')
        await form.get_by_label('Categoría',exact=True).select_option('weekly')
        await owner.select_option(self.person['id'])
        await form.get_by_role('button',name='Aplicar',exact=True).click()
        await form.get_by_text('Atributos y Data Owner aplicados.',exact=True).wait_for()
        self.assertEqual(sum(m=='POST' and p=='/api/decision-cases' for m,p in self.b.requests),0)
        self.assertTrue(await self.page.locator('.d-workflow-action-bar button').is_disabled())
        await self.b.upload_reuse_pair()
        await self.page.wait_for_function("document.querySelector('#dispatch-data-root .d-workflow-action-bar button')?.disabled===false")
        self.assertEqual(sum(m=='POST' and p=='/api/decision-cases' for m,p in self.b.requests),1)
        self.assertEqual(len(self.attribute_requests),1)

    async def test_dda_navigation_resolves_canonical_runs_without_losing_context(self):
        self.b.f['case_row']['label']='SEMANA 43'
        for key in ('logistics_assignment','logistics_scheduling'):self.snapshot['stages'][key].update(owner=self.person,owner_eligible=True)
        await self.b.open('logistics-map')
        nav=self.page.locator('.dda-navigation')
        await nav.get_by_role('link',name='SEMANA 43',exact=True).wait_for()
        self.assertEqual(await nav.locator('li').count(),3)
        self.assertEqual(await self.page.locator('[data-case-switcher],[data-select-case]').count(),0)
        self.assertEqual(await self.page.locator('#dispatch-map-root .dispatch-decision-rail').count(),0)
        await self.b.open('logistics-config','logistics_scheduling')
        await self.page.locator('.dispatch-decision-rail').wait_for()
        self.assertEqual(await self.page.locator('#dda-workspace-nav [aria-current=step]').get_attribute('data-step'),'3')
        self.assertEqual(await self.page.locator('.decision-view-tabs,[data-back-map]').count(),0)
        await self.page.locator('.dispatch-decision-tab[data-decision-node=logistics_assignment]').click()
        await self.page.locator('[data-config-review]').wait_for()
        self.assertNotIn('run_id=',self.page.url)
        await self.page.locator('.dispatch-decision-tab[data-decision-node=logistics_scheduling]').click()
        await self.page.locator('[data-scheduling-review]').wait_for()
        await self.page.locator('#dda-workspace-nav [data-step="4"]').click()
        await self.page.locator('.scheduling-dashboard-v2').wait_for()
        self.assertIn('run_id='+self.b.f['ids']['scheduling'],self.page.url)
        await self.page.locator('.dispatch-decision-tab[data-decision-node=logistics_assignment]').click()
        await self.page.locator('.assignment-dashboard-v2').wait_for()
        self.assertIn('case_id='+self.b.case['id'],self.page.url)
        self.assertIn('run_id='+self.b.f['ids']['assignment'],self.page.url)
        await self.page.wait_for_load_state('networkidle')
        self.assertEqual(await self.page.locator('.dda-navigation li').count(),3)
        self.assertEqual(await self.page.locator('#dda-workspace-nav [aria-current=step]').get_attribute('data-step'),'4')
        await self.page.locator('.dispatch-decision-tab[data-decision-node=logistics_scheduling]').click()
        await self.page.locator('.scheduling-dashboard-v2').wait_for()
        await self.page.locator('#dda-workspace-nav [data-step="3"]').click()
        await self.page.locator('[data-scheduling-review]').wait_for()
        self.assertIn('node_id=logistics_scheduling',self.page.url)
        self.assertEqual(await self.page.locator('.decision-view-tabs,[data-back-map]').count(),0)
        await self.page.locator('#dda-workspace-nav [data-step="1"]').click()
        await self.page.locator('[data-case-identity]').wait_for()
        self.assertIn('case_id='+self.b.case['id'],self.page.url)
        self.assertEqual(await self.page.get_by_label('Nombre del Case',exact=True).input_value(),'SEMANA 43')
        self.assertEqual(self.b.execution_bodies,[])

    async def test_dashboard_trace_shares_the_copy_row_and_context_pills_are_equal(self):
        self.b.f['case_row']['label']='Planning Semana 43 con un nombre largo'
        for node,kind in [('logistics_assignment','assignment'),('logistics_scheduling','scheduling')]:
            await self.b.open('decision-dashboard',node,self.b.f['ids'][kind])
            await self.page.locator('#dispatch-hero .dashboard-hero-trace').wait_for()
            for width in (1440,1024,768,390):
                await self.page.set_viewport_size({'width':width,'height':1000})
                await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
                geometry=await self.page.evaluate('''()=>{
                  const hero=document.querySelector('#dispatch-hero'),copy=hero.querySelector('[data-assignment-hero-copy],[data-scheduling-hero]');
                  const trace=hero.querySelector('.dashboard-hero-trace'),pills=[...document.querySelectorAll('.dda-navigation__step')].map(n=>n.getBoundingClientRect());
                  return {copy:copy.getBoundingClientRect().toJSON(),trace:trace.getBoundingClientRect().toJSON(),pills:pills.map(r=>({width:r.width,height:r.height})),overflow:document.documentElement.scrollWidth>innerWidth+1};
                }''')
                self.assertFalse(geometry['overflow'],(node,width,geometry))
                pills=geometry['pills'];self.assertEqual(len(pills),3)
                self.assertAlmostEqual(pills[0]['width'],pills[1]['width'],delta=.25)
                self.assertGreater(pills[2]['width'],pills[0]['width'])
                self.assertEqual({p['height'] for p in pills},{48})
                if width>900:
                    self.assertAlmostEqual(geometry['copy']['top'],geometry['trace']['top'],delta=1)
                    self.assertGreater(geometry['trace']['left'],geometry['copy']['right'])
                else:self.assertGreaterEqual(geometry['trace']['top'],geometry['copy']['bottom'])
            self.assertEqual(await self.page.locator('.decision-view-tabs,[data-back-map],[data-approval-handoff]').count(),0)

    async def test_data_save_does_not_overwrite_assignment_changed_while_editing(self):
        old={'id':'10000000-0000-4000-8000-000000000009','name':'Anterior'}
        stage=self.snapshot['stages']['data_owner'];stage.update(owner=old,owner_eligible=True,updated_at='2026-10-21T00:00:00Z')
        await self.b.open('logistics-data')
        form=self.page.locator('[data-case-identity]');select=form.get_by_label('Data Owner',exact=True)
        await select.locator('option[value="'+self.person['id']+'"]').wait_for(state='attached')
        await select.select_option(self.person['id'])
        before=copy.deepcopy(self.b.f['case_row'])
        stage['updated_at']='2026-10-21T02:00:00Z'
        await form.get_by_role('button',name='Aplicar',exact=True).click()
        await form.get_by_role('alert').filter(has_text='El Case o su Data Owner cambió').wait_for()
        self.assertEqual(self.attribute_requests[-1]['expected_owner_updated_at'],'2026-10-21T00:00:00Z')
        self.assertEqual(stage['owner'],old);self.assertEqual(self.b.f['case_row'],before)
        self.assertEqual(self.writes,[])
