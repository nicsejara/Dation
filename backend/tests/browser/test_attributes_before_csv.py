"""Only the four requested readiness scenarios; reuse existing UI/API fixtures."""
import copy
import unittest
from urllib.parse import urlsplit
import test_saga3_ui as saga3

OWNER='10000000-0000-4000-8000-000000000001'
class AttributesBeforeCSVTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):saga3.Saga3UITests.setUpClass()
    @classmethod
    def tearDownClass(cls):saga3.Saga3UITests.tearDownClass()
    async def asyncSetUp(self):
        self.fixture=saga3.Saga3UITests();await self.fixture.asyncSetUp()
        self.b=self.fixture.b;self.page=self.fixture.page;await self.page.emulate_media(reduced_motion='reduce')
    async def asyncTearDown(self):await self.fixture.asyncTearDown()
    async def new_form(self):
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app?view=logistics-data')
        form=self.page.locator('[data-case-identity]');await form.wait_for()
        select=form.get_by_label('Data Owner',exact=True);await select.locator(f'option[value="{OWNER}"]').wait_for(state='attached')
        return form
    async def fill(self,form):
        await form.get_by_label('Nombre del Case',exact=True).fill('SEMANA 43')
        await form.get_by_label('Categoría',exact=True).select_option('weekly')
        await form.get_by_label('Descripción (opcional)',exact=True).fill('Preparado antes de los CSV.')
        await form.get_by_label('Data Owner',exact=True).select_option(OWNER)
    async def apply(self,form):
        await form.get_by_role('button',name='Aplicar',exact=True).click()
        await form.locator('[data-case-identity-feedback]').get_by_text('Atributos y Data Owner aplicados.',exact=True).wait_for()
    def bar(self):return self.page.locator('#dispatch-data-root .d-workflow-action-bar')

    async def test_1_no_csv_valid_and_dirty_can_apply_and_reverting_disables_it(self):
        form=await self.new_form();button=form.get_by_role('button',name='Aplicar',exact=True)
        self.assertTrue(await button.is_disabled());await self.fill(form)
        self.assertFalse(await button.is_disabled())
        self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().orders'),None)
        self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().fleet'),None)
        await self.apply(form);self.assertTrue(await button.is_disabled())
        for label,value in [('Nombre del Case','SEMANA 44'),('Descripción (opcional)','Otra descripción')]:
            field=form.get_by_label(label,exact=True);initial=await field.input_value();await field.fill(value);self.assertFalse(await button.is_disabled());await field.fill(initial);self.assertTrue(await button.is_disabled())
        category=form.get_by_label('Categoría',exact=True);await category.select_option('monthly');self.assertFalse(await button.is_disabled());await category.select_option('weekly');self.assertTrue(await button.is_disabled())
        owner=form.get_by_label('Data Owner',exact=True);await owner.locator(f'option[value="{OWNER}"]').wait_for(state='attached');await owner.select_option('');self.assertFalse(await button.is_disabled());await owner.select_option(OWNER);self.assertTrue(await button.is_disabled())

    async def test_2_no_csv_applied_attributes_and_owner_survive_reload_but_global_cta_is_disabled(self):
        form=await self.new_form();await self.fill(form);await self.apply(form)
        await self.page.reload();await form.wait_for();await form.get_by_label('Data Owner',exact=True).locator(f'option[value="{OWNER}"]').wait_for(state='attached')
        self.assertEqual(await form.get_by_label('Nombre del Case',exact=True).input_value(),'SEMANA 43')
        self.assertEqual(await form.get_by_label('Data Owner',exact=True).input_value(),OWNER)
        for label in ('Atributos: listo','Data Owner: listo'):self.assertTrue(await self.bar().get_by_text(label,exact=True).is_visible())
        for label in ('Órdenes: pendiente','Flota: pendiente'):self.assertTrue(await self.bar().get_by_text(label,exact=True).is_visible())
        self.assertTrue(await self.bar().locator('button').is_disabled());self.assertTrue(await form.get_by_role('button',name='Aplicar',exact=True).is_disabled())
        self.assertFalse(any(method=='POST' and path=='/api/decision-cases' for method,path in self.b.requests))

    async def test_3_csv_complete_without_applied_attributes_keeps_global_cta_disabled(self):
        await self.new_form()
        await self.page.evaluate('inputs=>window.DationDispatch.startNewDecision(inputs)',list(self.b.f['datasets'].values()))
        await self.page.wait_for_function('Boolean(window.DationDispatch.getWorkspace().preflight?.valid)')
        self.assertTrue(await self.bar().get_by_text('Órdenes: listo',exact=True).is_visible());self.assertTrue(await self.bar().get_by_text('Flota: listo',exact=True).is_visible())
        self.assertTrue(await self.bar().get_by_text('Atributos: pendiente',exact=True).is_visible());self.assertTrue(await self.bar().locator('button').is_disabled())

    async def test_4_adding_csv_promotes_applied_attributes_and_owner_once_without_another_apply(self):
        submissions=[];created=[]
        async def create(route):
            body=route.request.post_data_json;created.append(body)
            workflow={'case_id':body['id'],'gates_enforced':True,'can_assign':True,'stages':{'data_owner':{'owner':None,'owner_eligible':False,'updated_at':None}}}
            row={'id':body['id'],'status':'active','updated_at':'2026-10-22T00:00:00Z','label':None,'category':None,'attributes_applied_at':None}
            self.b.other_cases[body['id']]={'case':row,'decision_case':body['state'],'orders':self.b.f['datasets']['orders'],'fleet':self.b.f['datasets']['fleet'],'workflow_responsibilities':workflow}
            await route.fulfill(json={'case':row})
        async def apply(route):
            body=route.request.post_data_json;submissions.append(body);cid=urlsplit(route.request.url).path.split('/')[4]
            item=self.b.other_cases[cid];item['case'].update({key:body[key] for key in ('label','category','description')});item['case'].update(attributes_applied_at='2026-10-22T01:00:00Z',updated_at='2026-10-22T01:00:00Z')
            item['workflow_responsibilities']['stages']['data_owner'].update(owner={'id':body['data_owner_user_id'],'name':'Synthetic owner'},owner_eligible=True,updated_at='2026-10-22T01:00:00Z')
            await route.fulfill(json={'id':cid})
        await self.b.context.route('**/api/decision-cases',create)
        await self.b.context.route('**/api/platform/decisions/*/attributes',apply)
        form=await self.new_form();await self.fill(form);await self.apply(form);self.assertEqual(submissions,[])
        for kind in ('orders','fleet'):
            card=self.page.locator(f'[data-kind="{kind}"]')
            await card.get_by_role('button',name='Reutilizar anterior',exact=False).click()
            await card.get_by_role('button',name='Usar esta carga',exact=True).click()
        await self.page.wait_for_function('(()=>{const b=document.querySelector("#dispatch-data-root .d-workflow-action-bar button");return b&&!b.disabled})()')
        self.assertEqual(len(created),1);self.assertEqual(len(submissions),1)
        self.assertEqual(submissions[0]['label'],'SEMANA 43');self.assertEqual(submissions[0]['description'],'Preparado antes de los CSV.');self.assertEqual(submissions[0]['data_owner_user_id'],OWNER)
        self.assertEqual(await self.bar().locator('.is-success').count(),4)
        self.assertTrue(await form.get_by_role('button',name='Aplicar',exact=True).is_disabled())
        self.assertEqual(self.b.execution_bodies,[])
