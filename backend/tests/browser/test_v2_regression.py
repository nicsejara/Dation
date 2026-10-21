"""Reloaded drawers restore the selected row, including native mobile dialogs."""
import unittest
import test_navigation as navigation


class SelectedDrawerRegressionTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):navigation.NavigationTests.setUpClass()
    @classmethod
    def tearDownClass(cls):navigation.NavigationTests.tearDownClass()
    async def asyncSetUp(self):
        self.b=navigation.NavigationTests();await self.b.asyncSetUp();self.page=self.b.page
    async def asyncTearDown(self):await self.b.asyncTearDown()

    async def test_data_hub_reload_closes_back_to_selected_second_dataset_without_refetch(self):
        for width in (1440,390):
            with self.subTest(width=width):
                await self.page.set_viewport_size({'width':width,'height':1000})
                await self.page.goto(f'http://127.0.0.1:{navigation.NavigationTests.port}/app/data')
                root=self.page.locator('[data-platform-data]');trigger=root.locator('[data-dataset-open]').nth(1)
                await trigger.wait_for();identifier=await trigger.get_attribute('data-dataset-open')
                await trigger.click();await root.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
                await self.page.reload();await root.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
                await self.page.wait_for_load_state('networkidle');before=self.b.requests.count(('GET','/api/platform/data/datasets'))
                await root.get_by_role('button',name='Cerrar detalle del dataset',exact=True).click()
                await self.page.wait_for_function('id=>document.activeElement?.dataset.datasetOpen===id',arg=identifier,timeout=1500)
                self.assertNotIn('dataset_id=',self.page.url)
                self.assertEqual(self.b.requests.count(('GET','/api/platform/data/datasets')),before)

    async def test_decision_center_reload_closes_back_to_selected_second_case_without_refetch(self):
        identifier=self.b.case['id'];other='00000000-0000-4000-8000-000000000099'
        async def listing(route):
            rows=[{'id':cid,'label':label,'friendly_id':'DC-'+cid[:8].upper(),'status':'active','dda':'logistics','progress':{'approved':0,'total':2}} for cid,label in ((other,'Otro caso'),(identifier,'Caso seleccionado'))]
            await route.fulfill(json={'items':rows,'total':2,'summary':{'active_cases':2}})
        await self.b.context.route('**/api/platform/decisions?**',listing)
        for width in (1440,390):
            with self.subTest(width=width):
                await self.page.set_viewport_size({'width':width,'height':1000})
                await self.page.goto(f'http://127.0.0.1:{navigation.NavigationTests.port}/app/decisions?center_case_id={identifier}')
                root=self.page.locator('[data-platform-decisions]');await root.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
                await self.page.reload();await root.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
                await self.page.wait_for_load_state('networkidle');before=self.b.requests.count(('GET','/api/platform/decisions'))
                await root.get_by_role('button',name='Cerrar detalle del caso',exact=True).click()
                await self.page.wait_for_function('id=>document.activeElement?.dataset.caseOpen===id',arg=identifier,timeout=1500)
                self.assertNotIn('center_case_id=',self.page.url)
                self.assertEqual(self.b.requests.count(('GET','/api/platform/decisions')),before)
