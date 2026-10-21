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
        self.snapshot={'case_id':self.b.case['id'],'gates_enforced':True,'can_assign':True,'policy_version':1,'stages':{
            'data_preparation':{'owner':self.person,'owner_eligible':True,'approver':None,'approver_eligible':False,'updated_at':'2026-10-21T00:00:00Z'},
            'logistics_assignment':{'owner':None,'owner_eligible':False,'approver':None,'approver_eligible':False,'updated_at':None},
            'logistics_scheduling':{'owner':None,'owner_eligible':False,'approver':None,'approver_eligible':False,'updated_at':None}}}
        original=self.b.hydrated
        self.b.hydrated=lambda:{**original(),'workflow_responsibilities':copy.deepcopy(self.snapshot)}
        self.writes=[];self.people_queries=[];self.candidate_gate=None;self.no_candidates=False;self.assignment_conflict=False;self.readiness_calls=0
        async def hydrated(route):
            if route.request.method!='GET':await route.fallback();return
            cid=urlparse(route.request.url).path.split('/')[-1]
            bundle=self.b.hydrated() if cid==self.b.case['id'] else self.b.other_cases.get(cid)
            if not bundle:await route.fallback();return
            data=copy.deepcopy(bundle);data['workflow_responsibilities']=copy.deepcopy(self.snapshot);data['workflow_responsibilities']['case_id']=cid
            await route.fulfill(json=data)
        async def workflow(route):
            request=route.request;parts=urlparse(request.url).path.split('/');cid=parts[4]
            if request.method=='PUT':
                body=request.post_data_json;self.writes.append(body)
                if self.assignment_conflict:await route.fulfill(status=409,json={'detail':'Assignment changed'});return
                stage=self.snapshot['stages'][parts[-1]]
                for field in ('owner','approver'):
                    stage[field]=copy.deepcopy(self.person) if body[field+'_user_id'] else None;stage[field+'_eligible']=bool(stage[field])
                stage['updated_at']='2026-10-21T01:00:00Z'
            if parts[-1]=='workflow-readiness':
                self.readiness_calls+=1
                ready=self.snapshot['stages']['data_preparation']['owner_eligible']
                await route.fulfill(status=200 if ready else 409,json={'ready':True} if ready else {'detail':'Falta responsable de datos'});return
            result=copy.deepcopy(self.snapshot);result['case_id']=cid;await route.fulfill(json=result)
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

    async def select_person(self):
        root=self.page.locator('[data-workflow-responsibility]')
        await root.get_by_role('button',name='Seleccionar responsable',exact=True).click()
        await root.get_by_label('Responsable de la decisión',exact=True).select_option(self.person['id'])
        await root.get_by_role('button',name='Guardar',exact=True).click()
        await root.get_by_role('button',name='Cambiar',exact=True).wait_for()

    async def test_config_gate_inline_assignment_and_review_preserve_the_case(self):
        await self.b.open('logistics-config','logistics_assignment')
        review=self.page.locator('[data-config-review]');self.assertTrue(await review.is_disabled())
        await self.select_person();self.assertFalse(await review.is_disabled())
        self.assertEqual(self.people_queries[0]['responsibility'],['decision_owner'])
        self.assertEqual(self.writes[0],{'expected_updated_at':None,'owner_user_id':self.person['id'],'approver_user_id':None})
        await review.click();dialog=self.page.get_by_role('dialog',name='Revisar Assignment antes de ejecutar')
        await dialog.get_by_text('Persona elegible',exact=True).wait_for()
        self.assertIn('case_id='+self.b.case['id'],self.page.url)
        self.assertEqual(self.b.execution_bodies,[])

    async def test_empty_candidates_and_conflict_explain_the_block_and_keep_review_disabled(self):
        self.no_candidates=True;await self.b.open('logistics-config','logistics_assignment')
        root=self.page.locator('[data-workflow-responsibility]');await root.get_by_role('button',name='Seleccionar responsable').click()
        await root.get_by_text('No hay personas con responsabilidad',exact=False).wait_for()
        self.assertTrue(await root.get_by_role('button',name='Guardar',exact=True).is_disabled())
        await root.get_by_role('button',name='Ir a Equipo',exact=True).wait_for()
        await root.get_by_role('button',name='Cancelar',exact=True).click()
        self.no_candidates=False;self.assignment_conflict=True
        await root.get_by_role('button',name='Seleccionar responsable').click()
        await root.get_by_label('Responsable de la decisión',exact=True).select_option(self.person['id'])
        await root.get_by_role('button',name='Guardar',exact=True).click()
        await root.get_by_role('button',name='Actualizar etapa',exact=True).wait_for()
        self.assertTrue(await self.page.locator('[data-config-review]').is_disabled())

    async def test_case_switcher_is_bounded_keyboard_accessible_and_clears_foreign_run(self):
        other='00000000-0000-4000-8000-000000000088';bundle=copy.deepcopy(self.b.hydrated())
        bundle['case']['id']=other;bundle['decision_case']['id']=other
        for key,node in bundle['decision_case']['nodes'].items():
            node.update(status='available' if key=='logistics_assignment' else 'locked',run_id=None,latest_run_id=None,approved_run_id=None,run_count=0)
        bundle['workflow_responsibilities']=copy.deepcopy(self.snapshot);bundle['workflow_responsibilities']['case_id']=other
        self.b.other_cases[other]=bundle;queries=[]
        async def listing(route):
            queries.append(parse_qs(urlparse(route.request.url).query))
            await route.fulfill(json={'items':[{'id':self.b.case['id'],'status':'active','dda':'logistics'},{'id':other,'label':'Otro caso','status':'active','dda':'logistics'}],'total':2})
        await self.b.context.route('**/api/platform/decisions?**',listing)
        await self.b.open('decision-dashboard','logistics_assignment',self.b.f['ids']['assignment'])
        switcher=self.page.locator('[data-case-switcher]');trigger=switcher.locator('button').first
        await trigger.focus();await self.page.keyboard.press('Enter');await switcher.get_by_role('button',name='Otro caso',exact=False).wait_for()
        self.assertEqual(await trigger.get_attribute('aria-expanded'),'true');await self.page.keyboard.press('Escape')
        self.assertEqual(await trigger.get_attribute('aria-expanded'),'false');self.assertTrue(await trigger.evaluate('n=>n===document.activeElement'))
        await trigger.click();await switcher.get_by_role('button',name='Otro caso',exact=False).click()
        await self.page.locator('[data-map-node=logistics_assignment]').wait_for()
        self.assertIn('case_id='+other,self.page.url);self.assertNotIn('run_id=',self.page.url);self.assertNotIn('node_id=',self.page.url)
        self.assertEqual(queries,[{'dda':['logistics'],'limit':['8'],'offset':['0']}]*2)
        switcher=self.page.locator('[data-case-switcher]');await switcher.locator('button').first.click()
        await switcher.get_by_role('button',name='Abrir este caso en Decision Center',exact=True).click()
        self.assertIn('center_case_id='+other,self.page.url)

    async def test_viewer_and_late_candidates_do_not_gain_mutation_controls(self):
        self.b.access_role='viewer';self.snapshot['can_assign']=False
        await self.b.open('logistics-config','logistics_assignment')
        self.assertEqual(await self.page.locator('[data-workflow-responsibility] button').count(),0)
        self.assertTrue(await self.page.locator('[data-config-review]').is_disabled())
        self.b.access_role='admin';self.snapshot['can_assign']=True;self.candidate_gate=asyncio.Event()
        await self.page.reload();await self.page.locator('[data-workflow-responsibility]').get_by_role('button',name='Seleccionar responsable').click()
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
        self.snapshot['stages']['data_preparation'].update(owner=None,owner_eligible=False)
        await self.page.goto(f'http://127.0.0.1:{navigation.NavigationTests.port}/app?view=logistics-data')
        await self.page.wait_for_function('Boolean(window.DationDispatch)')
        await self.page.evaluate('inputs=>window.DationDispatch.startNewDecision(inputs)',list(self.b.f['datasets'].values()))
        root=self.page.locator('#dispatch-data-root');await root.locator('[data-workflow-responsibility]').wait_for()
        next_button=root.get_by_role('button',name='Seleccioná tu decisión',exact=True)
        self.assertTrue(await next_button.is_disabled())
        self.assertEqual(sum(method=='POST' and path=='/api/decision-cases' for method,path in self.b.requests),0)
        selector=root.locator('[data-workflow-responsibility]');await selector.get_by_role('button',name='Seleccionar responsable').click()
        await selector.get_by_label('Responsable de datos',exact=True).select_option(self.person['id'])
        await selector.get_by_role('button',name='Guardar',exact=True).click();await selector.get_by_role('button',name='Cambiar',exact=True).wait_for()
        self.assertFalse(await next_button.is_disabled());self.assertEqual(self.people_queries[0]['responsibility'],['data'])
        self.assertEqual(sum(method=='POST' and path=='/api/decision-cases' for method,path in self.b.requests),1)
        cid=await self.page.evaluate('window.DationDispatch.getWorkspace().decisionCase.id')
        await next_button.click();await self.page.locator('[data-map-node=logistics_assignment]').wait_for()
        self.assertIn('case_id='+cid,self.page.url);self.assertNotIn('run_id=',self.page.url)

    async def test_team_keeps_one_invitation_entry_and_edits_multiple_roles_together(self):
        member={'user_id':self.person['id'],'name':'Persona elegible','email':'person@example.test','access_role':'admin','status':'active','business_role':'approver','business_roles':['approver','decision_owner'],'updated_at':'2026-10-21T00:00:00Z'}
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
        self.assertTrue(await dialog.get_by_label('Approver',exact=True).is_checked());self.assertTrue(await dialog.get_by_label('Decision Owner',exact=True).is_checked())
        await dialog.get_by_label('Data Steward',exact=True).check();await dialog.get_by_role('button',name='Guardar',exact=True).click()
        await root.get_by_text('Equipo actualizado.',exact=True).wait_for()
        self.assertEqual(set(writes[0]['business_roles']),{'approver','decision_owner','data_steward'})
        self.assertNotIn('business_role',writes[0]);self.assertEqual(writes[0]['expected_updated_at'],'2026-10-21T00:00:00Z')

    async def test_operator_registers_a_pending_data_case_and_refreshes_admin_assignment(self):
        self.b.access_role='operator';self.snapshot['can_assign']=False
        self.snapshot['stages']['data_preparation'].update(owner=None,owner_eligible=False)
        await self.page.goto(f'http://127.0.0.1:{navigation.NavigationTests.port}/app?view=logistics-data')
        await self.page.wait_for_function('Boolean(window.DationDispatch)')
        await self.page.evaluate('inputs=>window.DationDispatch.startNewDecision(inputs)',list(self.b.f['datasets'].values()))
        root=self.page.locator('#dispatch-data-root');selector=root.locator('[data-workflow-responsibility]')
        await selector.get_by_role('button',name='Registrar caso para asignar responsable',exact=True).click()
        await selector.get_by_role('button',name='Actualizar responsabilidad',exact=True).wait_for()
        self.assertEqual(await selector.get_by_role('button',name='Seleccionar responsable',exact=True).count(),0)
        self.assertTrue(await root.get_by_role('button',name='Seleccioná tu decisión',exact=True).is_disabled())
        self.snapshot['stages']['data_preparation'].update(owner=self.person,owner_eligible=True)
        await selector.get_by_role('button',name='Actualizar responsabilidad',exact=True).click()
        await self.page.wait_for_function("!document.querySelector('#dispatch-data-root .d-workflow-action-bar button').disabled")
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
                self.snapshot['stages'][node].update(owner=self.person,owner_eligible=True,approver=None,approver_eligible=False)
                await self.b.open('decision-dashboard',node,self.b.f['ids'][kind])
                root=self.page.locator('[data-workflow-responsibility]');await root.get_by_role('button',name='Seleccionar responsable').wait_for()
                for button in await self.page.locator('[data-approve-toolbar],[data-approve-final]').all():self.assertTrue(await button.is_disabled())
                await root.get_by_role('button',name='Seleccionar responsable').click()
                await root.get_by_label('Aprobador asignado',exact=True).select_option(self.person['id'])
                await root.get_by_role('button',name='Guardar',exact=True).click()
                await self.page.wait_for_function("[...document.querySelectorAll('[data-approve-toolbar],[data-approve-final]')].length>0&&[...document.querySelectorAll('[data-approve-toolbar],[data-approve-final]')].every(b=>!b.disabled)")

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
        await self.page.locator('[data-config-review]:disabled').wait_for()
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
        await self.page.locator('[data-case-switcher]').get_by_text('Archivado',exact=False).wait_for()

    async def test_viewer_cannot_execute_even_when_all_business_responsibilities_are_eligible(self):
        self.b.access_role='viewer';self.snapshot['can_assign']=False
        for stage in self.snapshot['stages'].values():stage.update(owner=self.person,owner_eligible=True,approver=self.person,approver_eligible=True)
        for node in ('logistics_assignment','logistics_scheduling'):
            await self.b.open('logistics-config',node)
            self.assertTrue(await self.page.locator('[data-config-review],[data-scheduling-review]').is_disabled())
            await self.page.get_by_text('Tu rol permite consultar, pero no ejecutar decisiones.',exact=True).first.wait_for()
        self.assertEqual(self.b.execution_bodies,[])
