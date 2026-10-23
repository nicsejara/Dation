"""Behavioral checks for extracted dashboard lifecycle and old native module URLs."""
import unittest

import test_saga3_ui as saga3


class FoundationComponentTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        saga3.Saga3UITests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        saga3.Saga3UITests.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = saga3.Saga3UITests()
        await self.fixture.asyncSetUp()
        self.b, self.page = self.fixture.b, self.fixture.page
        await self.b.open('decision-dashboard', 'logistics_assignment', self.b.f['ids']['assignment'])
        await self.page.evaluate('''async runs=>{
          const {createScope}=await import('/static/js/dispatch/lifecycle.mjs');
          window.foundationMount=async(kind,id='shared-run')=>{
            const module=await import('/static/js/dispatch/'+kind+'/'+kind+'-dashboard-shell.mjs');
            const root=document.createElement('div');document.body.append(root);const scope=createScope(root);
            const run={...runs[kind],id};let opened=0;
            module['render'+(kind==='assignment'?'Assignment':'Scheduling')+'Shell'](root,run);
            const shell=module['bind'+(kind==='assignment'?'Assignment':'Scheduling')+'Shell'](root,run,{onAdvancedOpen:()=>opened++});
            return {root,scope,shell,kind,get opened(){return opened;},
              toggle:root.querySelector('[data-'+kind+'-advanced-toggle]'),
              content:root.querySelector('[data-'+kind+'-advanced-content]')};
          };
          window.foundationState=x=>({depth:x.root.dataset.visualDepth,expanded:x.toggle.getAttribute('aria-expanded'),
            hidden:x.content.hidden,opened:x.opened,label:x.toggle.querySelector('strong').textContent});
        }''', self.b.f['runs'])

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def test_real_shells_keep_disclosure_storage_isolated_and_restore_per_run(self):
        for kind in ('assignment', 'scheduling'):
            with self.subTest(decision=kind):
                probe = await self.page.evaluate('''async kind=>{
                  sessionStorage.removeItem('dation.'+kind+'.presentation.shared-run');
                  const x=await foundationMount(kind);const initial=foundationState(x);
                  x.toggle.click();const expanded=foundationState(x);x.shell.openAdvanced();const repeated=x.opened;
                  x.toggle.click();const closed=foundationState(x);x.toggle.click();
                  x.scope.dispose();x.root.remove();
                  const restored=await foundationMount(kind),sameRun=foundationState(restored);
                  const another=await foundationMount(kind,'another-run'),otherRun=foundationState(another);
                  restored.scope.dispose();restored.root.remove();another.scope.dispose();another.root.remove();
                  return {initial,expanded,repeated,closed,sameRun,otherRun};
                }''', kind)
                self.assertEqual(probe['initial'], {'depth':'essential','expanded':'false','hidden':True,'opened':0,'label':'Mostrar análisis avanzado'})
                self.assertEqual(probe['expanded'], {'depth':'advanced','expanded':'true','hidden':False,'opened':1,'label':'Ocultar análisis avanzado'})
                self.assertEqual(probe['repeated'], 1, 'Already-open analysis must not redraw on repeated commands')
                self.assertEqual(probe['closed']['depth'], 'essential')
                self.assertEqual(probe['closed']['opened'], 1)
                self.assertEqual(probe['sameRun'], probe['expanded'])
                self.assertEqual(probe['otherRun'], probe['initial'])
        self.assertEqual(await self.page.evaluate('''()=>[
          sessionStorage.getItem('dation.assignment.presentation.shared-run'),
          sessionStorage.getItem('dation.scheduling.presentation.shared-run')]'''), ['advanced','advanced'])

    async def test_real_shells_focus_the_requested_plan_and_dispose_queued_actions(self):
        for kind in ('assignment', 'scheduling'):
            with self.subTest(decision=kind):
                await self.page.evaluate('''async kind=>{
                  const x=await foundationMount(kind,'focus-run');window.foundationProbe=x;
                  const target=document.createElement('section');target.id='foundation-plan';target.tabIndex=-1;x.content.append(target);
                  x.shell.openAdvanced(kind==='assignment'?target:'#foundation-plan');
                }''', kind)
                await self.page.wait_for_function("document.activeElement.id==='foundation-plan'")
                state = await self.page.evaluate('''()=>{
                  const x=foundationProbe;x.scope.dispose();x.root.remove();
                  const opened=x.opened;x.toggle.click();return {opened,after:x.opened};
                }''')
                self.assertEqual(state['opened'], state['after'])
                cancelled = await self.page.evaluate('''async kind=>{
                  const x=await foundationMount(kind,'cancelled-run');
                  let scrolled=0;x.root.querySelector('[data-'+kind+'-advanced]').scrollIntoView=()=>scrolled++;
                  x.shell.openAdvanced();x.scope.dispose();
                  await new Promise(resolve=>setTimeout(resolve,30));x.root.remove();return scrolled;
                }''', kind)
                self.assertEqual(cancelled, 0)

    async def test_previous_urls_preserve_native_imports_exports_and_escaped_result_text(self):
        result = await self.page.evaluate('''async()=>{
          const previous=await import('/static/js/dispatch/navigation.mjs');
          const config=await import('/static/js/dispatch/assignment-config.mjs');
          const workflow=await import('/static/js/dispatch/workflow-context.mjs');
          const legacy=await import('/static/js/dispatch/decision-config-ui.mjs');
          const canonical=await import('/static/js/dispatch/result-summary.mjs');
          const host=document.createElement('div');host.innerHTML=legacy.decisionResultSummary({
            parts:['Mover ',{value:'<img src=x onerror=alert(1)>'},' en ',{value:'2 viajes'}],supportingText:'<script>unsafe</script>'});
          return {view:previous.readResource('/app').view,configuration:typeof config.mountAssignmentConfig,
            names:['mountWorkflowContext','mountCasePreparation','mountDashboardTrace','renderExecutionProgress'].map(k=>typeof workflow[k]),
            sameSummary:legacy.decisionResultSummary===canonical.decisionResultSummary,images:host.querySelectorAll('img,script').length,
            values:[...host.querySelectorAll('strong')].map(n=>n.textContent),support:host.querySelector('.decision-result-summary__support').textContent};
        }''')
        self.assertEqual(result, {'view':'platform-home','configuration':'function','names':['function']*4,
                                 'sameSummary':True,'images':0,'values':['<img src=x onerror=alert(1)>','2 viajes'],
                                 'support':'<script>unsafe</script>'})
        self.assertEqual(self.b.execution_bodies, [], 'Reading old module URLs must never admit a Run')
