"""Chromium regression suite. Every API request is intercepted with synthetic data."""
import asyncio
import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import shutil
import time
import unittest
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((Path(__file__).parent / "fixtures.json").read_text())
KEY = "dation.dispatch.workspace.v5"


class NavigationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        env = {**os.environ, "DATION_ACCESS_PASSWORD": "dispatch-qa",
               "SUPABASE_URL": "", "SUPABASE_SECRET_KEY": "", "LLM_API_KEY": ""}
        cls.server = subprocess.Popen(
            [os.getenv("DATION_RUNTIME_PYTHON") or (str(ROOT.parent / ".venv/bin/python") if (ROOT.parent / ".venv/bin/python").exists() else shutil.which("python")), "-m", "uvicorn", "main:app",
             "--host", "127.0.0.1", "--port", str(cls.port)],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", cls.port), timeout=.2):
                    break
            except OSError:
                if cls.server.poll() is not None:
                    raise RuntimeError("QA server did not start")
                time.sleep(.05)
        else:
            cls.server.terminate()
            raise RuntimeError("QA server startup timed out")

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait(timeout=10)

    async def asyncSetUp(self):
        self.f = copy.deepcopy(FIXTURE)
        self.case = self.f["case"]
        self.runs = {r["id"]: r for r in self.f["runs"].values()}
        self.requests = []
        self.errors = []
        self.delay = {}
        self.post_status = 202
        self.missing_run = False
        self.history_rows = None
        self.history_failure = False
        self.chat_calls = []
        self.chat_fail_once = False
        self.chat_history = None
        self.selector_size = 1
        self.selector_queries = []
        self.comparative=None
        self.comparative_posts=0
        self.comparative_fail_once=False
        self.saved_explanation=None
        self.approval_calls=0
        self.approval_fail_once=False
        self.other_cases={}
        self.execution_bodies=[]
        self.run_fetch_failures=0
        self.pw = await async_playwright().start()
        executable = os.getenv("CHROMIUM_EXECUTABLE")
        if not executable and Path("/usr/bin/chromium").exists():
            executable = "/usr/bin/chromium"
        self.browser = await self.pw.chromium.launch(executable_path=executable, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        self.context = await self.browser.new_context(viewport={"width":1440,"height":1000},
            http_credentials={"username":"dation","password":"dispatch-qa"})
        await self.context.route("**/api/**", self.route_api)
        self.page = await self.context.new_page()
        self.page.set_default_timeout(6000)
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))

    async def asyncTearDown(self):
        await self.browser.close()
        await self.pw.stop()
        self.assertEqual(self.errors, [], "Browser JavaScript errors")

    def hydrated(self):
        return {"case":{**self.f["case_row"],"state_json":self.case},"decision_case":self.case,
                "orders":self.f["datasets"]["orders"],"fleet":self.f["datasets"]["fleet"]}

    async def route_api(self, route):
        request = route.request
        u = urlparse(request.url)
        path, query, method = u.path, parse_qs(u.query), request.method
        self.requests.append((method, path))
        captured_evidence=self.comparative['id'] if self.comparative and self.comparative['status']=='completed' else None
        await asyncio.sleep(self.delay.get(path, .01))
        data, status = {}, 200
        if path == "/api/dispatch/status":
            data = {"available":True,"checks":[],"engine_version":"1.0.0"}
        elif path == "/api/dispatch/contracts": data = self.f["contracts"]
        elif path == "/api/system/llm-status": data = {"configured":False,"provider":"qa","model":"qa"}
        elif path == "/api/system/supabase-check": data = {"ok":True}
        elif path == "/api/workspace/summary": data = {"datasets":2,"runs":len(self.runs)}
        elif path == "/api/datasets":
            kind = query.get("type", [None])[0]
            data = {"items":[d for k,d in self.f["datasets"].items() if kind is None or k == kind]}
        elif path.endswith("/profile"):
            kind = "orders" if self.f["ids"]["orders"] in path else "fleet"
            data = {"dataset":self.f["datasets"][kind]}
            for item in self.other_cases.values():
                for name in ('orders','fleet'):
                    if item[name]['id'] in path:data={'dataset':item[name]}
        elif path in {"/api/runs/preflight", "/api/runs/assignment-preview"}:
            data = self.f["preflight" if path.endswith("preflight") else "preview"]
        elif path == "/api/decision-cases":
            self.selector_queries.append(query)
            items=[self.hydrated() for _ in range(self.selector_size)]
            if self.other_cases:items=[self.hydrated(),*copy.deepcopy(list(self.other_cases.values()))]
            for i,item in enumerate(items):
                if i and not self.other_cases:item['case']['id']=f'00000000-0000-4000-9000-{i:012d}'
                if query.get('summary') == ['true']:
                    for kind in ('orders','fleet'):
                        item[kind]={k:v for k,v in item[kind].items() if k in
                            ('id','dataset_type','canonical_filename','label','original_filename')}
            data = {"cases":items}
        elif path.startswith("/api/decision-cases/") and path.endswith("/runs"):
            node = query.get("node_id", ["logistics_assignment"])[0]
            runs = self.history_rows if self.history_rows is not None else [r for r in self.runs.values() if r.get("node_id") == node]
            offset,limit=int(query.get('offset',['0'])[0]),int(query.get('limit',['100'])[0])
            data = {"case_id":self.case["id"],"node_id":node,"total":len(runs),"summary":self.case["nodes"][node],
                    "offset":offset,"limit":limit,
                    "runs":[{**r,"result_json":None,"decision_state":"approved" if r.get("approved_at") else "candidate"} for r in runs[offset:offset+limit]]}
            if self.history_failure and offset:
                status,data=503,{'detail':'Historial temporalmente no disponible'}
        elif path.startswith("/api/decision-cases/"):
            if path.split("/")[-1] in self.other_cases:
                data=self.other_cases[path.split("/")[-1]]
            elif path.split("/")[-1] != self.case["id"]:
                status, data = 404, {"detail":"No se encontró el Decision Case."}
            else: data = self.hydrated()
        elif path == "/api/runs" and method == "POST":
            body = request.post_data_json
            self.execution_bodies.append(body)
            kind = "scheduling" if body.get("decision_case",{}).get("node_id") == "logistics_scheduling" else "assignment"
            rid = query["run_id"][0]
            row = copy.deepcopy(self.f["runs"][kind])
            row.update(id=rid,approved_at=None)
            row["result_json"]["decision_case"].update(status="review",approved_at=None)
            self.runs[rid] = row
            node = self.case["nodes"]["logistics_"+kind]
            node.update(latest_run_id=rid,run_count=node.get("run_count",0)+1)
            if not node.get("approved_run_id"): node.update(run_id=rid,status="review")
            status, data = self.post_status, {**row,"status":"queued","result_json":None}
            if status >= 400: data = {"detail":"Lost response after acceptance"}
        elif path == "/api/runs": data = {"items":list(self.runs.values())}
        elif path.endswith("/approve"):
            self.approval_calls+=1
            if self.approval_fail_once and self.approval_calls==1:
                status,data=503,{'detail':'Fallo sintético de aprobación'}
            else:
                rid = path.split("/")[3]
                row = self.runs[rid]
                row["approved_at"] = "2026-10-10T12:00:00+00:00"
                row["result_json"]["decision_case"].update(status="approved",approved_at=row["approved_at"])
                self.case["nodes"][row["node_id"]].update(status="approved",approved_run_id=rid,run_id=rid)
                data = row
        elif path.endswith("/interpretation"):
            data = {"explanation":None,"messages":[],"configured":False}
            if self.saved_explanation:data.update(explanation=self.saved_explanation,explanation_is_current=captured_evidence is None)
            data['current_evidence_analysis_id']=captured_evidence
            if self.chat_history:
                offset=int(query.get('offset',['0'])[0])
                rows=self.chat_history[offset:offset+2]
                data.update(messages=list(reversed(rows)),pagination={'has_more':len(self.chat_history)>offset+2,'next_offset':offset+2})
        elif path.endswith("/explain"): data = {"summary":"Synthetic explanation"}
        elif path.endswith("/chat"):
            self.chat_calls.append(request.post_data_json)
            data = {"answer":"Synthetic answer","evidence_analysis_id":captured_evidence}
            if self.chat_fail_once and len(self.chat_calls)==1:status,data=504,{'detail':'Synthetic timeout'}
        elif path.endswith('/comparative'):
            if method=='POST':
                self.comparative_posts+=1
                if self.comparative_fail_once and self.comparative_posts==1:
                    status,data=503,{'detail':'Análisis temporalmente no disponible'}
                else:
                    self.comparative={'id':'00000000-0000-4000-8000-000000000099','base_run_id':self.f['ids']['assignment'],
                        'status':'queued','source_mode':'computed','result_json':self.f['runs']['assignment']['result_json'],
                        'finished_at':'2026-10-13T12:00:00Z'}
                    status,data=202,self.comparative
            else:data=self.comparative or {'status':'available','id':None}
        elif path.startswith("/api/runs/"):
            data = self.runs.get(path.split("/")[3])
            if not data or self.missing_run: status, data = 404, {"detail":"No se encontró la corrida."}
            elif self.run_fetch_failures:
                self.run_fetch_failures-=1;status,data=503,{'detail':'Red temporalmente no disponible'}
        else:
            status, data = 501, {"detail":"Unmocked QA endpoint: "+path}
        await route.fulfill(status=status,content_type="application/json",body=json.dumps(data))

    async def open(self, view="logistics-map", node=None, run=None):
        query = f"view={view}&case_id={self.case['id']}"
        if node: query += "&node_id="+node
        if run: query += "&run_id="+run
        await self.page.goto(f"http://127.0.0.1:{self.port}/app?{query}")
        await self.page.wait_for_function("window.DationDispatch && window.DationDispatch.getWorkspace().decisionCase?.persisted")
        if view == "logistics-map": await self.page.wait_for_selector("[data-map-node=logistics_assignment]")
        if view == "logistics-config": await self.page.wait_for_selector("[data-scheduling-review]" if node == "logistics_scheduling" else "[data-config-review]")
        if view == "decision-dashboard": await self.page.wait_for_selector(".dispatch-scheduling-dashboard" if node == "logistics_scheduling" else ".assignment-dashboard-v2")

    async def nav(self, view):
        await self.page.evaluate("view=>window.dationNavigate(view)",view)

    async def test_cold_assignment_link(self):
        await self.open("decision-dashboard","logistics_assignment",self.f["ids"]["assignment"])
        self.assertEqual(await self.page.evaluate("window.DationDispatch.getWorkspace().orders.id"),self.f["ids"]["orders"])

    def essential(self):
        run=self.f['runs']['assignment']
        run['result_json']['analysis']['depth']='essential'
        run['result_json']['configuration']['options']['analysis_depth']='essential'

    async def dashboard(self):
        await self.open('decision-dashboard','logistics_assignment',self.f['ids']['assignment'])

    async def test_comparative_original_always_keeps_essential_before_comparative_and_ia(self):
        await self.dashboard()
        self.assertEqual(await self.page.locator('[data-generate-comparative]').count(),0)
        order=await self.page.evaluate("[...document.querySelectorAll('.assignment-dashboard-v2 section[id]')].map(x=>x.id)")
        self.assertLess(order.index('dispatch-assignment'),order.index('dispatch-comparative'))
        self.assertLess(order.index('dispatch-review'),order.index('dispatch-comparative'))
        self.assertEqual(await self.page.locator('[data-flow],[data-case-flow],.dispatch-dashboard-map-back').count(),0)
        self.assertFalse(await self.page.locator('#dda-workspace-nav-shell').is_visible())

    async def test_trip_detail_is_contextual_toggleable_and_escape_restores_focus(self):
        await self.dashboard()
        self.assertEqual(await self.page.locator('[data-trip-detail]').count(),0)
        controls=self.page.locator('[data-trip-detail-button]')
        await controls.first.click()
        self.assertEqual(await controls.first.get_attribute('aria-expanded'),'true')
        self.assertTrue(await self.page.locator('[data-close-trip]').evaluate('(x)=>x===document.activeElement'))
        self.assertEqual(await self.page.locator('[data-trip-detail]').count(),1)
        self.assertTrue(await self.page.locator('[data-trip-detail]').evaluate('(x)=>x.closest("tr").previousElementSibling.classList.contains("is-selected")'))
        await self.page.keyboard.press('Escape')
        self.assertEqual(await self.page.locator('[data-trip-detail]').count(),0)
        self.assertTrue(await controls.first.evaluate('(x)=>x===document.activeElement'))
        await controls.first.press('Enter');await controls.first.click()
        self.assertEqual(await self.page.locator('[data-trip-detail]').count(),0)
        if await controls.count()>1:
            await controls.first.click();await controls.nth(1).click()
            self.assertEqual(await self.page.locator('[data-trip-detail]').count(),1)
            self.assertEqual(await controls.first.get_attribute('aria-expanded'),'false')
        await self.page.locator('[data-evidence-tab=trips]').focus();await self.page.keyboard.press('ArrowRight')
        self.assertEqual(await self.page.locator('[data-evidence-tab=vehicles]').get_attribute('aria-selected'),'true')
        self.assertEqual(await self.page.locator('[data-trip-detail]').count(),0)

    async def test_progressive_analysis_is_local_and_restores_after_reload(self):
        self.essential();await self.dashboard();url=self.page.url
        await self.page.locator('[data-generate-comparative]').click()
        await self.page.wait_for_selector('[data-comparative-state=queued]')
        self.assertTrue(await self.page.locator('#dispatch-assignment').is_visible())
        self.assertEqual(self.page.url,url)
        self.comparative['status']='completed'
        await self.page.wait_for_selector('[data-comparative-state=completed]')
        await self.page.reload();await self.page.wait_for_selector('[data-comparative-state=completed]')
        self.assertEqual(self.comparative_posts,1)
        self.assertEqual(sum(m=='POST' and p=='/api/runs' for m,p in self.requests),0)
        self.assertEqual(self.page.url,url)

    async def test_comparative_error_retry_and_departure_cancels_polling(self):
        self.essential();self.comparative_fail_once=True;await self.dashboard()
        await self.page.locator('[data-generate-comparative]').click()
        await self.page.wait_for_selector('[data-comparative-state=error]')
        self.assertIn('temporalmente',await self.page.locator('#dispatch-comparative').inner_text())
        await self.page.locator('[data-generate-comparative]').click()
        await self.page.wait_for_selector('[data-comparative-state=queued]')
        self.assertEqual(self.comparative_posts,2)
        await self.nav('inicio');count=sum(p.endswith('/comparative') for _,p in self.requests)
        await self.page.wait_for_timeout(1800)
        self.assertEqual(sum(p.endswith('/comparative') for _,p in self.requests),count)
        self.assertEqual(await self.page.locator('[data-comparative-state]').count(),0)

    async def test_new_run_direct_configuration_preserves_business_context_and_history(self):
        await self.dashboard();before=copy.deepcopy(self.case)
        await self.page.locator('[data-more-menu] summary').click()
        await self.page.locator('[data-rerun]').click()
        await self.page.wait_for_selector('[data-config-review]')
        self.assertEqual(parse_qs(urlparse(self.page.url).query)['case_id'],[before['id']])
        self.assertNotIn('run_id=',self.page.url)
        self.assertEqual(self.case,before)
        self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))

    async def test_new_decision_goes_to_empty_data_without_losing_existing_case(self):
        await self.dashboard();before=copy.deepcopy(self.case)
        await self.page.locator('[data-more-menu] summary').click()
        await self.page.locator('[data-new-decision]').click()
        await self.page.wait_for_selector('[data-kind=orders] input[type=file]',state='attached')
        self.assertIn('view=logistics-data',self.page.url)
        self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().orders'),None)
        self.assertEqual(self.case,before)
        await self.page.go_back();await self.page.wait_for_selector('.assignment-dashboard-v2')
        self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().orders.id'),self.f['ids']['orders'])

    async def test_approved_assignment_continues_directly_to_scheduling_configuration(self):
        self.case['nodes']['logistics_scheduling'].update(status='locked',run_id=None,latest_run_id=None,run_count=0)
        await self.dashboard()
        await self.page.locator('[data-after-approve]').click()
        await self.page.wait_for_selector('[data-scheduling-review]')
        self.assertIn('view=logistics-config',self.page.url);self.assertIn('node_id=logistics_scheduling',self.page.url)
        self.assertNotIn('run_id=',self.page.url)
        await self.page.go_back();await self.page.wait_for_selector('.assignment-dashboard-v2')
        await self.page.go_forward();await self.page.wait_for_selector('[data-scheduling-review]')

    async def test_existing_review_does_not_offer_another_next_configuration(self):
        await self.dashboard()
        await self.page.wait_for_function("document.querySelector('[data-next-decision-status]')?.textContent.includes('para revisar')")
        self.assertFalse(await self.page.locator('[data-after-approve]').is_visible())
        await self.page.locator('.dispatch-decision-rail [data-decision-node=logistics_scheduling]').click()
        await self.page.wait_for_selector('.dispatch-scheduling-dashboard')

    async def test_mobile_trip_detail_has_no_document_overflow(self):
        await self.page.set_viewport_size({'width':390,'height':844});await self.dashboard()
        await self.page.locator('[data-trip-detail-button]').first.click()
        self.assertEqual(await self.page.locator('[data-trip-detail]').count(),1)
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        bounds=await self.page.locator('[data-trip-detail]').bounding_box()
        self.assertGreaterEqual(bounds['x'],0);self.assertLessEqual(bounds['x']+bounds['width'],390)
        await self.page.locator('[data-close-trip]').click()
        self.assertEqual(await self.page.locator('[data-trip-detail]').count(),0)

    def review_assignment(self):
        row=self.f['runs']['assignment'];row['approved_at']=None
        row['result_json']['decision_case'].update(status='review',approved_at=None)
        self.case['nodes']['logistics_assignment'].update(status='review',approved_run_id=None,approved_at=None)
        self.case['nodes']['logistics_scheduling'].update(status='locked',run_id=None,latest_run_id=None,run_count=0)

    def second_case(self):
        item=copy.deepcopy(self.hydrated());case=copy.deepcopy(self.f['initial_case'])
        cid='00000000-0000-4000-9000-000000000010'
        case['id']=cid
        for i,kind in enumerate(('orders','fleet'),11):
            item[kind]['id']=f'00000000-0000-4000-9000-{i:012d}'
            item[kind]['canonical_filename']='Caso-B-'+kind+'.csv'
            case['inputs'][kind+'_dataset_id']=item[kind]['id']
            item['case'][kind+'_dataset_id']=item[kind]['id']
        case['signature']=item['orders']['id']+':'+item['fleet']['id']
        item['decision_case']=case;item['case'].update(id=cid,state_json=case)
        self.other_cases[cid]=item
        return item

    def failed_run(self,kind):
        run=copy.deepcopy(self.f['runs'][kind]);node='logistics_'+kind
        run.update(status='error',result_json=None,approved_at=None,decision_case_id=self.case['id'],node_id=node,
            error_message='No existe una programación temporal factible dentro de la ventana configurada.')
        run['configuration_json']=copy.deepcopy(self.f['runs'][kind]['result_json']['configuration'])
        if kind=='scheduling':run['configuration_json'].update(strategy='service_first',planning_window_start='2026-10-01',planning_window_end='2026-10-02')
        self.runs[run['id']]=run
        self.case['nodes'][node].update(status='error',approved_run_id=None,approved_at=None,latest_execution_status='error')
        return run

    async def test_overview_has_two_hero_actions_and_disabled_visible_map_without_cases(self):
        self.selector_size=0
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=overview')
        await self.page.locator('[data-start-new-decision]').wait_for(state='visible')
        self.assertEqual(await self.page.locator('.dda-landing button').count(),2)
        self.assertFalse(await self.page.locator('[data-start-new-decision]').is_disabled())
        map_button=self.page.locator('[data-open-decision-map]')
        self.assertTrue(await map_button.is_visible());self.assertTrue(await map_button.is_disabled())
        self.assertEqual(await map_button.get_attribute('aria-disabled'),'true')
        self.assertEqual(await map_button.evaluate('(x)=>getComputedStyle(x).cursor'),'not-allowed')
        self.assertEqual(await map_button.evaluate('(x)=>getComputedStyle(x).opacity'),'1')
        bg=await map_button.evaluate('(x)=>getComputedStyle(x).backgroundColor')
        await map_button.hover(force=True)
        self.assertEqual(bg,await map_button.evaluate('(x)=>getComputedStyle(x).backgroundColor'))
        initial=self.page.url;await map_button.dispatch_event('click');self.assertEqual(self.page.url,initial)
        self.assertEqual(await self.page.locator('[data-go-data],[data-go-map],[data-go-home],.dda-landing__mobile-primary').count(),0)
        await self.page.set_viewport_size({'width':390,'height':844})
        self.assertTrue(await self.page.locator('[data-start-new-decision]').is_visible())
        self.assertTrue(await map_button.is_visible())
        await self.page.locator('[data-start-new-decision]').click()
        await self.page.locator('[data-kind=orders] input[type=file]').wait_for(state='attached')
        self.assertIn('view=logistics-data',self.page.url)

    async def test_overview_map_with_active_case_and_multiple_cases_uses_existing_selector(self):
        self.second_case();await self.open();await self.nav('logistics-overview')
        await self.page.locator('[data-open-decision-map]').click()
        await self.page.locator('[data-open-case="'+self.case['id']+'"]').click()
        await self.page.locator('[data-select-case]').wait_for(state='visible')
        self.assertIn('case_id='+self.case['id'],self.page.url)
        self.assertEqual(await self.page.locator('.dispatch-case-selector').count(),0)

    async def test_overview_multiple_cases_without_selection_uses_existing_selector(self):
        other=self.second_case()
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=overview')
        await self.page.wait_for_function("document.querySelector('[data-open-decision-map]')?.disabled===false")
        await self.page.locator('[data-open-decision-map]').click()
        await self.page.locator('[data-open-case="'+other['case']['id']+'"]').click()
        await self.page.locator('[data-select-case]').wait_for(state='visible')
        self.assertIn('case_id='+other['case']['id'],self.page.url)

    async def test_overview_single_case_map_opens_directly_and_new_decision_clears_active_context(self):
        await self.open();await self.nav('logistics-overview')
        self.assertFalse(await self.page.locator('[data-start-new-decision]').is_disabled())
        self.assertFalse(await self.page.locator('[data-open-decision-map]').is_disabled())
        await self.page.locator('[data-open-decision-map]').click()
        await self.page.locator('[data-select-case]').wait_for(state='visible')
        self.assertEqual(await self.page.locator('.dispatch-case-selector').count(),0)
        await self.nav('logistics-overview');before=copy.deepcopy(self.case)
        await self.page.evaluate('''()=>{const start=window.DationDispatch.startNewDecision;window.__starts=0;
          window.DationDispatch.startNewDecision=()=>{window.__starts++;return start();};}''')
        await self.page.locator('[data-start-new-decision]').click()
        await self.page.locator('[data-kind=orders] input[type=file]').wait_for(state='attached')
        state=await self.page.evaluate('window.DationDispatch.getWorkspace()')
        self.assertEqual(await self.page.evaluate('window.__starts'),1)
        for key in ('orders','decisionCase','run','activeNode'):self.assertIsNone(state[key])
        self.assertNotIn('case_id=',self.page.url);self.assertIn('view=logistics-data',self.page.url)
        self.assertEqual(self.case,before)
        self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))
        drafts=await self.page.evaluate("JSON.parse(sessionStorage.getItem('dation.dispatch.drafts.v1'))")
        self.assertIn(self.case['id'],drafts)
        await self.page.go_back();await self.page.locator('[data-open-decision-map]').click()
        await self.page.locator('[data-select-case]').wait_for(state='visible')
        self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().decisionCase.id'),self.case['id'])

    async def test_overview_availability_ignores_stale_responses_and_refreshes_on_bfcache(self):
        self.selector_size=0
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=overview')
        await self.page.locator('[data-start-new-decision]').wait_for(state='visible')
        await self.page.wait_for_timeout(100)
        await self.page.evaluate('''()=>{window.__caseResolvers=[];
          window.DationDispatch.listDecisionCases=()=>new Promise(resolve=>window.__caseResolvers.push(resolve));
          window.dispatchEvent(new CustomEvent('dation:cases-ready'));
          window.dispatchEvent(new CustomEvent('dation:cases-ready'));}''')
        await self.page.evaluate('window.__caseResolvers[1]([{}])')
        self.assertFalse(await self.page.locator('[data-open-decision-map]').is_disabled())
        await self.page.evaluate('window.__caseResolvers[0]([])')
        self.assertFalse(await self.page.locator('[data-open-decision-map]').is_disabled())
        await self.page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
        await self.page.evaluate('window.__caseResolvers[2]([])')
        self.assertTrue(await self.page.locator('[data-open-decision-map]').is_disabled())
        self.assertFalse(await self.page.locator('[data-start-new-decision]').is_disabled())

    async def check_context_layout(self,kind):
        details=self.page.locator('[data-config-context]');summary=details.locator('summary')
        self.assertFalse(await details.get_attribute('open'))
        before=await summary.bounding_box();root=await details.bounding_box()
        self.assertLess(abs(before['width']-(root['width']-2)),2)
        await summary.focus();await self.page.keyboard.press('Enter')
        self.assertTrue(await details.evaluate('(x)=>x.open'))
        after=await summary.bounding_box();self.assertAlmostEqual(before['height'],after['height'],delta=1)
        geometry=await details.evaluate('''el=>{const rect=x=>{const r=x.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};
          const body=el.querySelector('.decision-config-case__body'),files=el.querySelector('.decision-config-case__files');
          return {root:rect(el),body:rect(body),identity:rect(el.querySelector('.assignment-case-strip__identity')),
            header:rect(el.querySelector('.decision-config-case__pack-header')),button:rect(el.querySelector('.assignment-change-data')),
            columns:getComputedStyle(files).gridTemplateColumns.split(' ').length,
            cards:[...files.children].map(rect),wrapperDisplay:getComputedStyle(el).display,
            names:[...files.querySelectorAll('.dispatch-datapack-file__name')].map(x=>({title:x.title,overflow:getComputedStyle(x).textOverflow}))};}''')
        self.assertEqual(geometry['wrapperDisplay'],'block')
        self.assertLess(abs(geometry['body']['w']-(geometry['root']['w']-2)),2)
        self.assertEqual(geometry['columns'],1 if self.page.viewport_size['width']<=720 else 2)
        self.assertGreaterEqual(geometry['header']['y'],geometry['identity']['bottom']-1)
        self.assertGreaterEqual(min(card['y'] for card in geometry['cards']),geometry['header']['bottom']-1)
        for card in geometry['cards']:
            self.assertGreaterEqual(card['w'],180)
            self.assertGreaterEqual(card['x'],geometry['body']['x']);self.assertLessEqual(card['right'],geometry['body']['right']+1)
        self.assertTrue(all(name['title'].endswith('.csv') and name['overflow']=='ellipsis' for name in geometry['names']))
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        await summary.focus();await self.page.keyboard.press('Space')
        self.assertFalse(await details.evaluate('(x)=>x.open'))
        self.assertAlmostEqual((await details.bounding_box())['height'],root['height'],delta=1)

    async def test_shared_config_disclosures_are_full_width_without_overlap_at_all_five_breakpoints(self):
        for dataset in self.f['datasets'].values():dataset['canonical_filename']='Nombre_con_muchos_caracteres_'+('W'*180)+'.csv'
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000 if width>390 else 844})
            for kind in ('assignment','scheduling'):
                with self.subTest(width=width,kind=kind):
                    await self.open('logistics-config','logistics_'+kind)
                    await self.check_context_layout(kind)

    async def test_overview_two_actions_use_rows_on_desktop_and_stack_on_mobile(self):
        self.selector_size=0
        await self.page.emulate_media(reduced_motion='reduce')
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=overview')
        await self.page.locator('[data-start-new-decision]').wait_for(state='visible')
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            await self.page.wait_for_timeout(450)
            start=await self.page.locator('[data-start-new-decision]').bounding_box()
            map_box=await self.page.locator('[data-open-decision-map]').bounding_box()
            if width==390:
                self.assertGreaterEqual(map_box['y'],start['y']+start['height'])
                self.assertAlmostEqual(start['width'],map_box['width'],delta=1)
            elif width>=1280:self.assertAlmostEqual(start['y'],map_box['y'],delta=1)
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            self.assertEqual(await self.page.locator('.dda-landing button').count(),2)

    async def test_config_disclosure_preserves_copy_id_change_data_and_real_validation_labels(self):
        await self.context.grant_permissions(['clipboard-read','clipboard-write'])
        for kind in ('assignment','scheduling'):
            await self.open('logistics-config','logistics_'+kind)
            details=self.page.locator('[data-config-context]');await details.locator('summary').click()
            self.assertEqual(await details.locator('.decision-config-data-file__validated').count(),2)
            await details.locator('[data-'+('config' if kind=='assignment' else 'scheduling')+'-copy-case]').click()
            self.assertEqual(await self.page.evaluate('navigator.clipboard.readText()'),self.case['id'])
            self.assertTrue(await details.evaluate('(x)=>x.open'))
            await details.locator('.assignment-change-data').click()
            if kind=='assignment':await self.page.locator('[data-change-confirm]').click()
            await self.page.locator('[data-kind=orders] input[type=file]').wait_for(state='attached')

    async def test_config_disclosures_do_not_claim_validation_for_profiles_with_errors(self):
        for dataset in self.f['datasets'].values():dataset['profile_json']['counts']['errors']=1
        for kind in ('assignment','scheduling'):
            await self.open('logistics-config','logistics_'+kind)
            details=self.page.locator('[data-config-context]');await details.locator('summary').click()
            self.assertEqual(await details.locator('.decision-config-data-file__validated').count(),0)
            self.assertTrue(await details.locator('.assignment-case-file').evaluate_all(
                "cards=>cards.every(card=>getComputedStyle(card,'::after').content==='none')"))

    async def test_map_disclosure_layout_remains_readable_at_all_five_breakpoints(self):
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            await self.open();details=self.page.locator('[data-map-context]')
            await details.locator('summary').click()
            cards=await details.locator('.dispatch-datapack-file').all()
            rectangles=[await card.bounding_box() for card in cards]
            self.assertTrue(all(card['width']>=180 for card in rectangles))
            a,b=rectangles
            self.assertTrue(a['y']+a['height']<=b['y']+1 or a['x']+a['width']<=b['x']+1)
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))

    async def test_map_disclosure_keeps_progress_visible_and_preserves_columns_and_change_data(self):
        await self.open();details=self.page.locator('[data-map-context]')
        self.assertFalse(await details.get_attribute('open'))
        self.assertTrue(await self.page.locator('.dispatch-map-progress [role=progressbar]').is_visible())
        self.assertEqual(await details.locator('[role=progressbar]').count(),0)
        self.assertFalse(await details.locator('[data-map-columns]').first.is_visible())
        await details.locator('summary').click()
        self.assertTrue(await details.locator('[data-map-columns]').first.is_visible())
        await details.locator('[data-map-columns=orders]').click()
        await self.page.locator('.dispatch-guide [aria-label=Cerrar]').wait_for(state='visible')
        await self.page.locator('.dispatch-guide [aria-label=Cerrar]').click()
        await details.locator('[data-map-action=data]').click()
        await self.page.locator('[data-confirm-change]').click()
        await self.page.locator('[data-kind=orders] input[type=file]').wait_for(state='attached')

    async def test_both_configuration_contexts_are_closed_and_scheduling_source_stays_visible(self):
        for kind in ('assignment','scheduling'):
            await self.open('logistics-config','logistics_'+kind)
            details=self.page.locator('[data-config-context]')
            self.assertFalse(await details.get_attribute('open'))
            self.assertFalse(await details.locator('button').first.is_visible())
            if kind=='scheduling':self.assertTrue(await self.page.get_by_text('ASIGNACIÓN APROBADA',exact=True).is_visible())
            await details.locator('summary').click()
            self.assertTrue(await details.locator('button').first.is_visible())
            self.assertIn('Cambiar datos',await details.inner_text())

    async def test_comparative_can_close_reopen_reload_without_mutation_or_another_post(self):
        self.essential();await self.dashboard();before=copy.deepcopy(self.case)
        await self.page.locator('[data-generate-comparative]').click()
        await self.page.wait_for_function("document.querySelector('[data-comparative-state]')?.dataset.comparativeState==='queued'")
        self.comparative['status']='completed'
        await self.page.locator('[data-close-comparative]').wait_for(state='visible')
        artifact=copy.deepcopy(self.comparative)
        await self.page.locator('[data-close-comparative]').click()
        self.assertEqual(await self.page.locator('[data-comparison-kpi]').count(),0)
        await self.page.reload();await self.page.locator('[data-open-comparative]').wait_for(state='visible')
        await self.page.locator('[data-open-comparative]').click()
        self.assertEqual(await self.page.locator('[data-comparison-kpi]').count(),4)
        self.assertEqual(self.comparative_posts,1);self.assertEqual(self.comparative,artifact);self.assertEqual(self.case,before)
        self.assertEqual(await self.page.locator('[data-generate-comparative]').count(),0)

    async def test_terminal_scheduling_error_restores_window_and_executes_new_run(self):
        failed=self.failed_run('scheduling');before=copy.deepcopy(failed)
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=decision-dashboard&case_id={self.case["id"]}&node_id=logistics_scheduling&run_id={failed["id"]}')
        await self.page.locator('[data-reconfigure-run]').wait_for(state='visible')
        self.assertEqual(await self.page.locator('[data-error-map]').inner_text(),'Decision Map')
        self.assertNotIn('Reintentar',await self.page.locator('[data-run-terminal-error]').inner_text())
        await self.page.locator('[data-reconfigure-run]').click()
        await self.page.locator('[data-scheduling-review]').wait_for(state='visible')
        self.assertNotIn('run_id=',self.page.url)
        self.assertEqual(await self.page.locator('[data-scheduling-window-start]').input_value(),'2026-10-01')
        self.assertEqual(await self.page.locator('[data-scheduling-window-end]').input_value(),'2026-10-02')
        await self.page.locator('[data-scheduling-window-end]').fill('2026-12-31')
        await self.page.locator('[data-scheduling-window-end]').dispatch_event('change')
        await self.page.locator('[data-scheduling-review]').click();await self.page.locator('[data-scheduling-execute]').click()
        await self.page.locator('.dispatch-scheduling-dashboard').wait_for(state='visible')
        self.assertNotIn('run_id='+failed['id'],self.page.url)
        self.assertEqual(self.execution_bodies[-1]['source_run_id'],self.f['ids']['assignment'])
        self.assertEqual(self.execution_bodies[-1]['configuration']['planning_window_end'],'2026-12-31')
        self.assertEqual(self.runs[failed['id']],before)
        await self.page.locator('[data-dashboard-map]').click()
        await self.page.locator('[data-select-case]').wait_for(state='visible')
        await self.page.evaluate("window.DationDispatch.openRunHistory('logistics_scheduling')")
        await self.page.locator('[data-history-range]').wait_for(state='visible')
        self.assertIn('de 2',await self.page.locator('[data-history-range]').inner_text())

    async def test_terminal_assignment_error_restores_objective_and_retains_failed_run(self):
        failed=self.failed_run('assignment');failed['configuration_json'].update(objective='min_cost',dimensions=['trips','cost','own_fleet'])
        failed['configuration_json']['options'].update(analysis_depth='essential',resource_mode='own')
        before=copy.deepcopy(failed)
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=decision-dashboard&case_id={self.case["id"]}&node_id=logistics_assignment&run_id={failed["id"]}')
        await self.page.locator('[data-reconfigure-run]').click()
        await self.page.locator('[data-config-review]').wait_for(state='visible')
        state=await self.page.evaluate('window.DationDispatch.getWorkspace()')
        self.assertEqual((state['objective'],state['resourceMode']),('min_cost','own'))
        self.assertNotIn('analysisDepth',state)
        self.assertEqual(self.runs[failed['id']],before)

    async def test_transient_run_fetch_error_retries_without_showing_terminal_actions(self):
        self.run_fetch_failures=1
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=decision-dashboard&case_id={self.case["id"]}&node_id=logistics_assignment&run_id={self.f["ids"]["assignment"]}')
        await self.page.get_by_role('button',name='Reintentar',exact=True).click()
        await self.page.locator('.assignment-dashboard-v2').wait_for(state='visible')
        self.assertEqual(await self.page.locator('[data-reconfigure-run]').count(),0)
        self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))

    async def test_map_selector_switches_case_data_progress_url_and_restores_cancel_focus(self):
        other=self.second_case();await self.open()
        await self.page.locator('[data-select-case]').click();await self.page.locator('[data-open-case]').first.wait_for(state='visible')
        await self.page.keyboard.press('Escape')
        self.assertTrue(await self.page.locator('[data-select-case]').evaluate('(x)=>x===document.activeElement'))
        await self.page.locator('[data-select-case]').click()
        await self.page.locator('[data-open-case="'+other['case']['id']+'"]').click()
        await self.page.wait_for_function('id=>window.DationDispatch.getWorkspace().decisionCase.id===id',arg=other['case']['id'])
        await self.page.locator('[data-map-context]').wait_for(state='visible')
        state=await self.page.evaluate('window.DationDispatch.getWorkspace()')
        self.assertEqual(state['orders']['id'],other['orders']['id']);self.assertEqual(state['fleet']['id'],other['fleet']['id'])
        self.assertEqual(await self.page.locator('.dispatch-map-progress [role=progressbar]').get_attribute('aria-valuenow'),'0')
        self.assertIn('case_id='+other['case']['id'],self.page.url);self.assertNotIn('run_id=',self.page.url)
        await self.page.go_back();await self.page.wait_for_function('id=>window.DationDispatch.getWorkspace().decisionCase.id===id',arg=self.case['id'])

    async def test_both_toolbar_map_buttons_use_run_case_and_preserve_business_state(self):
        other=self.second_case();before=copy.deepcopy(self.case)
        for kind in ('assignment','scheduling'):
            await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=decision-dashboard&case_id={other["case"]["id"]}&node_id=logistics_{kind}&run_id={self.f["ids"][kind]}')
            await self.page.locator('[data-dashboard-map]').click()
            await self.page.locator('[data-select-case]').wait_for(state='visible')
            self.assertIn('case_id='+self.case['id'],self.page.url)
            self.assertNotIn('run_id=',self.page.url);self.assertNotIn('node_id=',self.page.url)
        self.assertEqual(self.case,before)
        self.assertFalse(any(m=='POST' and p.endswith('/approve') for m,p in self.requests))

    async def test_map_config_and_toolbar_fit_mobile_without_obsolete_kpi_or_calendar_actions(self):
        await self.page.set_viewport_size({'width':390,'height':844})
        await self.open();self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        await self.open('logistics-config','logistics_scheduling');self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        await self.dashboard()
        self.assertTrue(await self.page.locator('[data-dashboard-map]').is_visible())
        for text in ('KPI del resultado','Parte del objetivo'):
            self.assertNotIn(text,await self.page.locator('#dispatch-hero').inner_text())
        self.assertEqual(await self.page.locator('.assignment-essential__metric-note').count(),0)
        await self.open('decision-dashboard','logistics_scheduling',self.f['ids']['scheduling'])
        self.assertEqual(await self.page.locator('[data-export-schedule]').count(),0)
        self.assertEqual(await self.page.locator('[data-export-menu] button').count(),2)
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))

    async def test_four_kpis_and_comparator_use_independent_scenario_averages_and_pp(self):
        result=self.f['runs']['assignment']['result_json']
        result['scenarios']['selected']['metrics'].update(total_cost=1000,total_trips=4,load_utilization=.82,own_weight_share=.78)
        result['scenarios']['min_cost']['metrics'].update(total_cost=1200,total_trips=3,load_utilization=.75,own_weight_share=.64)
        await self.dashboard()
        self.assertEqual(await self.page.locator('[data-executive-kpi]').count(),4)
        self.assertIn('$ 250',await self.page.locator('[data-executive-kpi=avg_cost_per_trip]').inner_text())
        self.assertEqual(await self.page.locator('[data-comparison-kpi]').count(),4)
        await self.page.locator('[data-comparison-select]').select_option('min_cost')
        cost=await self.page.locator('[data-comparison-kpi=avg_cost_per_trip]').inner_text()
        self.assertIn('$ 250',cost);self.assertIn('$ 400',cost);self.assertIn('−$ 150 · −37,5 %',cost)
        self.assertIn('+7 pp',await self.page.locator('[data-comparison-kpi=load_utilization]').inner_text())
        self.assertIn('+14 pp',await self.page.locator('[data-comparison-kpi=own_weight_share]').inner_text())
        self.assertIn('peso',await self.page.locator('[data-executive-kpi=own_weight_share] span').first.get_attribute('aria-label'))
        advanced=await self.page.locator('#dispatch-comparative').inner_text()
        for forbidden in ('CO₂ estimado','Costo estimado','Lectura de la elección','Prioridades configuradas','Trazabilidad del análisis','corrida base','huella','Estado del solver','Objetivo original'):
            self.assertNotIn(forbidden,advanced)
        self.assertEqual(await self.page.locator('#dispatch-comparative h2').count(),1)

    async def test_validation_without_controls_is_one_simple_state_and_no_inline_actions(self):
        result=self.f['runs']['assignment']['result_json']
        result['exceptions']=[];result['inputs']['anomalies']=[]
        result['scenarios']['selected']['trips']=[];result['scenarios']['selected']['order_outcomes']=[]
        await self.dashboard()
        self.assertEqual(await self.page.locator('.assignment-validation__empty').count(),1)
        self.assertEqual(await self.page.locator('#dispatch-review button').count(),0)
        self.assertEqual(await self.page.locator('#dispatch-review article').count(),0)
        content=await self.page.locator('#dispatch-review').inner_text()
        self.assertIn('No se detectaron controles u observaciones pendientes',content)
        for forbidden in ('Evidencia del motor','Estado del solver','entrada para Planificación','Nueva corrida','Aprobar asignación'):
            self.assertNotIn(forbidden,content)

    async def test_validation_retains_real_operational_and_critical_controls(self):
        result=self.f['runs']['assignment']['result_json'];scenario=result['scenarios']['selected']
        scenario['trips'][0]['ownership']='third_party';scenario['order_outcomes'][0]['split']=True
        result['inputs']['anomalies']=[{'decision':'include'}];scenario['feasible']=False
        result['exceptions']=[{'title':'Carga incompatible','detail':'Revisar vehículo','trip_id':'T1'}]
        await self.dashboard()
        for key in ('infeasible','engine_exceptions','outsourced','anomalies','split_orders'):
            self.assertEqual(await self.page.locator('[data-approval-warning='+key+']').count(),1)
        self.assertEqual(await self.page.locator('.assignment-validation__empty').count(),0)
        self.assertIn('Carga incompatible',await self.page.locator('#dispatch-review').inner_text())
        self.assertEqual(await self.page.locator('#dispatch-review button').count(),0)

    async def test_toolbar_approval_is_unique_direct_and_preserves_continuation(self):
        self.review_assignment();path=f"/api/runs/{self.f['ids']['assignment']}/approve";self.delay[path]=.5
        await self.dashboard()
        self.assertEqual(await self.page.locator('[data-approve-toolbar]').count(),1)
        self.assertEqual(await self.page.locator('[data-approve]').count(),0)
        button=self.page.locator('[data-dashboard-toolbar] [data-approve-toolbar]')
        await button.click()
        self.assertTrue(await button.is_disabled());self.assertEqual(await button.inner_text(),'Aprobando…')
        await button.dispatch_event('click')
        await self.page.wait_for_function("document.querySelector('[data-status-badge]').textContent==='Aprobada'")
        self.assertEqual(self.approval_calls,1);self.assertFalse(await button.is_visible())
        await self.page.locator('[data-after-approve]').wait_for(state='visible')
        self.assertEqual(self.case['nodes']['logistics_assignment']['approved_run_id'],self.f['ids']['assignment'])

    async def test_toolbar_approval_error_restores_button_and_can_retry_once(self):
        self.review_assignment();self.approval_fail_once=True;await self.dashboard()
        button=self.page.locator('[data-approve-toolbar]');await button.click()
        await self.page.locator('[data-approval-error]').wait_for(state='visible')
        self.assertFalse(await button.is_disabled());self.assertEqual(await button.inner_text(),'Aprobar asignación')
        self.assertIn('Fallo sintético',await self.page.locator('[data-approval-error]').inner_text())
        self.assertIsNone(self.case['nodes']['logistics_assignment']['approved_run_id'])
        self.assertEqual(await self.page.locator('[data-status-badge]').inner_text(),'En revisión')
        await button.click();await self.page.wait_for_function("document.querySelector('[data-status-badge]').textContent==='Aprobada'")
        self.assertEqual(self.approval_calls,2);self.assertFalse(await self.page.locator('[data-approval-error]').is_visible())

    async def test_scheduling_uses_shared_menus_drawer_and_exports_without_format_changes(self):
        await self.open('decision-dashboard','logistics_scheduling',self.f['ids']['scheduling'])
        self.assertEqual(await self.page.locator('[data-more-menu] button').count(),3)
        self.assertEqual(await self.page.locator('[data-export-menu] button').count(),2)
        self.assertNotIn('Acciones ···',await self.page.locator('[data-dashboard-toolbar]').inner_text())
        self.assertFalse(await self.page.locator('[data-run-drawer]').is_visible())
        await self.page.locator('[data-more-menu] summary').click();await self.page.locator('[data-run-details]').click()
        drawer=self.page.locator('[data-run-drawer]');await drawer.wait_for(state='visible')
        content=await drawer.inner_text()
        for value in ('Assignment fuente',self.f['ids']['assignment'],'Inicio','Fin','Motor','Solver','Servicio de IA'):
            self.assertIn(value,content)
        await self.page.keyboard.press('Shift+Tab');self.assertTrue(await drawer.evaluate('(x)=>x.contains(document.activeElement)'))
        await self.page.keyboard.press('Escape');self.assertFalse(await drawer.is_visible())
        self.assertTrue(await self.page.locator('[data-more-menu] summary').evaluate('(x)=>x===document.activeElement'))
        await self.page.locator('[data-more-menu] summary').click();await self.page.locator('[data-run-details]').click()
        await self.page.locator('[data-run-drawer-backdrop]').click(position={'x':5,'y':5})
        self.assertFalse(await drawer.is_visible())
        await self.page.locator('[data-export-menu] summary').click()
        async with self.page.expect_download() as downloaded:await self.page.locator('[data-export-csv]').click()
        download=await downloaded.value;self.assertEqual(download.suggested_filename,'planificacion-recomendada.csv')
        self.assertIn('Salida',Path(await download.path()).read_text())
        await self.page.locator('[data-export-menu] summary').click()
        async with self.page.expect_download() as downloaded:await self.page.locator('[data-export-json]').click()
        download=await downloaded.value;self.assertEqual(download.suggested_filename,'planificacion-'+self.f['ids']['scheduling']+'.json')
        self.assertEqual(json.loads(Path(await download.path()).read_text()),self.f['runs']['scheduling']['result_json'])

    async def test_shared_drawer_cleans_up_on_navigation_and_scheduling_chat_has_one_listener(self):
        await self.dashboard()
        await self.page.locator('[data-more-menu] summary').click();await self.page.locator('[data-run-details]').click()
        await self.nav('logistics-map')
        self.assertFalse(await self.page.evaluate("document.body.classList.contains('dashboard-drawer-open')"))
        await self.page.evaluate("id=>window.DationDispatch.openRun(id,'logistics_scheduling')",self.f['ids']['scheduling'])
        await self.page.wait_for_selector('.dispatch-scheduling-dashboard')
        before=sum(p.endswith('/interpretation') for _,p in self.requests)
        await self.page.locator('#dispatch-explanation [data-question]').first.click()
        await self.page.wait_for_selector('.dispatch-chat textarea')
        await self.page.wait_for_timeout(150)
        self.assertEqual(sum(p.endswith('/interpretation') for _,p in self.requests)-before,1)

    async def test_refined_comparator_and_scheduling_drawer_fit_mobile_viewport(self):
        await self.page.set_viewport_size({'width':390,'height':844});await self.dashboard()
        cards=await self.page.locator('[data-comparison-kpi]').all()
        bounds=[await card.bounding_box() for card in cards]
        self.assertEqual(len(bounds),4);self.assertTrue(all(abs(b['x']-bounds[0]['x'])<1 for b in bounds))
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        await self.page.evaluate("id=>window.DationDispatch.openRun(id,'logistics_scheduling')",self.f['ids']['scheduling'])
        await self.page.wait_for_selector('.dispatch-scheduling-dashboard')
        await self.page.locator('[data-more-menu] summary').click();await self.page.locator('[data-run-details]').click()
        bounds=await self.page.locator('[data-run-drawer]').bounding_box()
        self.assertGreaterEqual(bounds['x'],0);self.assertLessEqual(bounds['x']+bounds['width'],390)
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))

    async def test_ia_retains_and_labels_original_turn_when_comparative_finishes_mid_response(self):
        self.essential();self.saved_explanation={'id':'saved','response_json':{'executive_summary':'Explicación original'}}
        await self.dashboard()
        await self.page.locator('[data-chat]').click()
        self.delay[f"/api/runs/{self.f['ids']['assignment']}/chat"]=3
        await self.page.locator('.dispatch-chat textarea').fill('¿Qué debería revisar?')
        await self.page.locator('.dispatch-chat button[type=submit]').click()
        await self.page.locator('[data-generate-comparative]').click()
        await self.page.wait_for_selector('[data-comparative-state=queued]')
        self.comparative['status']='completed'
        await self.page.wait_for_selector('[data-comparative-state=completed]')
        await self.page.get_by_text('Synthetic answer',exact=True).wait_for()
        self.assertIn('interpretación de la corrida original',(await self.page.locator('[data-messages]').inner_text()).lower())
        self.assertIn('Ya hay nueva evidencia comparativa',await self.page.locator('#dispatch-explanation').inner_text())

    async def test_case_selector_requests_one_compact_page_and_hydrates_only_selection(self):
        self.selector_size=100
        await self.open()
        before=len(self.requests)
        await self.page.evaluate('window.DationDispatch.openDecisionMap()')
        await self.page.wait_for_selector('[data-open-case]')
        self.assertEqual(await self.page.locator('[data-open-case]').count(),100)
        self.assertEqual(self.selector_queries[-1].get('summary'),['true'])
        self.assertEqual(self.requests[before:],[('GET','/api/decision-cases')])
        await self.page.locator('[data-open-case="'+self.case['id']+'"]').click()
        await self.page.wait_for_selector('[data-map-node=logistics_assignment]')
        self.assertEqual(await self.page.locator('[data-open-case]').count(),0)
        self.assertIn(('GET','/api/decision-cases/'+self.case['id']),self.requests[before:])

    async def test_cold_scheduling_link_and_refresh(self):
        await self.open("decision-dashboard","logistics_scheduling",self.f["ids"]["scheduling"])
        await self.page.reload()
        await self.page.wait_for_selector(".dispatch-scheduling-dashboard")
        self.assertIn("node_id=logistics_scheduling", self.page.url)

    async def test_config_d2_keeps_node(self):
        await self.open("logistics-config","logistics_scheduling")
        await self.page.reload()
        await self.page.wait_for_selector("[data-scheduling-review]")

    async def test_map_clears_run_from_url(self):
        await self.open("decision-dashboard","logistics_assignment",self.f["ids"]["assignment"])
        await self.nav("logistics-map")
        self.assertNotIn("run_id=",self.page.url)
        self.assertEqual(await self.page.locator(".assignment-dashboard-v2").count(),0)

    async def test_back_forward_restore_resource(self):
        await self.open()
        await self.page.locator('[data-trace-new="logistics_scheduling"]').click()
        await self.page.wait_for_selector("[data-scheduling-review]")
        await self.page.go_back()
        await self.page.wait_for_selector("[data-map-node=logistics_assignment]")
        await self.page.go_forward()
        await self.page.wait_for_selector("[data-scheduling-review]")

    async def test_unknown_resource_shows_error(self):
        await self.page.goto(f"http://127.0.0.1:{self.port}/app?view=unknown")
        await self.page.wait_for_selector("#dispatch-dashboard-root .dispatch-alert")
        self.assertIn("no existe",await self.page.locator("#dispatch-dashboard-root").inner_text())

    async def test_missing_run_stops_polling(self):
        self.missing_run = True
        await self.page.goto(f"http://127.0.0.1:{self.port}/app?view=decision-dashboard&run_id={self.f['ids']['assignment']}")
        await self.page.wait_for_selector("#dispatch-dashboard-root .dispatch-alert")
        count = sum(p.startswith('/api/runs/') for _,p in self.requests)
        await self.page.wait_for_timeout(1700)
        self.assertEqual(sum(p.startswith('/api/runs/') for _,p in self.requests),count)

    async def test_map_idle_makes_no_requests(self):
        await self.open()
        await self.page.wait_for_timeout(250)
        count = len(self.requests)
        await self.page.wait_for_timeout(1700)
        self.assertEqual(len(self.requests),count)

    async def test_phase5_toolbar_menus_are_exclusive_outside_escape_and_viewport_safe(self):
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':844});await self.page.wait_for_timeout(250)
            for kind in ('assignment','scheduling'):
                await self.open('decision-dashboard','logistics_'+kind,self.f['ids'][kind])
                export=self.page.locator('[data-export-menu] summary');more=self.page.locator('[data-more-menu] summary')
                for control in await self.page.locator('.dashboard-toolbar__tools>button:visible,.dashboard-toolbar__menu>summary').all():
                    self.assertGreater(await control.locator('svg[aria-hidden=true]').count(),0)
                await export.click();await more.click()
                await self.page.wait_for_function("document.querySelectorAll('.dashboard-toolbar__menu[open]').length===1")
                self.assertEqual(await more.get_attribute('aria-expanded'),'true')
                self.assertEqual(await export.get_attribute('aria-expanded'),'false')
                box=await self.page.locator('[data-more-menu] .dashboard-toolbar__menu-panel').bounding_box()
                self.assertGreaterEqual(box['x'],15);self.assertLessEqual(box['x']+box['width'],width-15)
                self.assertGreaterEqual(box['y'],0);self.assertLessEqual(box['y']+box['height'],845)
                await self.page.keyboard.press('Escape')
                self.assertTrue(await more.evaluate('el=>el===document.activeElement'))
                await export.click();await self.page.locator('.topbar').click(position={'x':5,'y':5})
                self.assertEqual(await self.page.locator('.dashboard-toolbar__menu[open]').count(),0)
                await more.focus();await self.page.keyboard.press('Enter')
                await self.page.locator('[data-run-details]').click()
                self.assertEqual(await self.page.locator('.dashboard-toolbar__menu[open]').count(),0)
                await self.page.keyboard.press('Escape')
                self.assertTrue(await more.evaluate('el=>el===document.activeElement'))
                self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))

    async def test_phase5_programmatic_menu_opening_is_exclusive_and_cleanup_survives_navigation(self):
        await self.dashboard()
        await self.page.locator('[data-export-menu]').evaluate('el=>el.open=true')
        await self.page.locator('[data-more-menu]').evaluate('el=>el.open=true')
        await self.page.wait_for_function("document.querySelectorAll('.dashboard-toolbar__menu[open]').length===1")
        await self.nav('logistics-map')
        await self.page.keyboard.press('Escape')
        await self.page.locator('[data-select-case]').wait_for(state='visible')
        await self.page.evaluate('window.DationDispatch.openRun('+json.dumps(self.f['ids']['assignment'])+',"logistics_assignment")')
        await self.page.locator('.assignment-dashboard-v2').wait_for(state='visible')
        await self.page.locator('[data-export-menu] summary').click()
        self.assertEqual(await self.page.locator('.dashboard-toolbar__menu[open]').count(),1)
        self.assertEqual(await self.page.locator('[data-dashboard-toolbar]').count(),1)

    async def test_phase5_dashboard_dark_roles_and_contrast_at_five_widths(self):
        audit=(Path(__file__).parent/'theme_audit.js').read_text()
        await self.page.emulate_media(reduced_motion='reduce',color_scheme='light')
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':844});await self.page.wait_for_timeout(250)
            for kind in ('assignment','scheduling'):
                await self.open('decision-dashboard','logistics_'+kind,self.f['ids'][kind])
                result=await self.page.evaluate(audit)
                self.assertEqual(result['scheme'],'dark');self.assertFalse(result['legacyBoundary']);self.assertFalse(result['overflow'])
                self.assertEqual(result['failures'],[],(kind,width,result['failures']))
                await self.page.locator('[data-more-menu] summary').click();await self.page.locator('[data-run-details]').click()
                drawer=await self.page.evaluate(audit,'[data-run-drawer]')
                self.assertEqual(drawer['failures'],[]);self.assertEqual(drawer['scheme'],'dark')
                await self.page.keyboard.press('Escape')
                await self.page.locator('[data-chat]').click()
                chat=await self.page.evaluate(audit,'.dispatch-chat')
                self.assertEqual(chat['failures'],[]);self.assertEqual(chat['scheme'],'dark')
                await self.page.keyboard.press('Escape')

    async def test_phase5_schedule_chart_preserves_data_dates_and_dark_tooltip(self):
        await self.page.set_viewport_size({'width':390,'height':844})
        before=copy.deepcopy(self.f['runs']['scheduling'])
        await self.open('decision-dashboard','logistics_scheduling',self.f['ids']['scheduling'])
        chart=self.page.locator('.dispatch-schedule-chart')
        actual=await chart.evaluate('''el=>{
            const instance=window.DationCharts.getInstanceByDom(el),o=instance.getOption();
            return {background:o.backgroundColor,text:o.textStyle.color,tooltip:o.tooltip[0],
                offsets:o.series[0].data,durations:o.series[1].data,hidden:o.series[0].itemStyle.opacity,
                axis:o.xAxis[0].axisLabel,labels:o.yAxis[0].axisLabel,
                height:el.clientHeight,rows:o.yAxis[0].data.length,
                detail:o.tooltip[0].formatter({dataIndex:0})};
        }''')
        self.assertEqual(actual['background'],'transparent');self.assertEqual(actual['text'],'#f3f8fa')
        self.assertEqual(actual['tooltip']['backgroundColor'],'#172731');self.assertEqual(actual['tooltip']['textStyle']['color'],'#f3f8fa')
        trips=before['result_json']['scenarios']['selected']['trips']
        self.assertEqual(len(actual['durations']),len(trips));self.assertEqual(actual['hidden'],0)
        self.assertIn('Salida:',actual['detail']);self.assertIn('Disponible:',actual['detail'])
        self.assertGreaterEqual(actual['height'],actual['rows']*28)
        viewport=self.page.locator('.dispatch-schedule-chart-scroll');await viewport.scroll_into_view_if_needed();await viewport.focus()
        await viewport.press('PageDown');await self.page.wait_for_timeout(200)
        self.assertGreater(await viewport.evaluate('el=>el.scrollTop'),0)
        await chart.evaluate("el=>window.DationCharts.getInstanceByDom(el).dispatchAction({type:'showTip',seriesIndex:1,dataIndex:0})")
        svg_audit=(Path(__file__).parent/'svg_chart_audit.js').read_text()
        result=await self.page.evaluate(svg_audit,'.dispatch-schedule-chart')
        self.assertGreater(result['count'],0);self.assertEqual(result['failures'],[])
        await self.page.set_viewport_size({'width':1440,'height':1000})
        await self.page.wait_for_function("window.DationCharts.getInstanceByDom(document.querySelector('.dispatch-schedule-chart')).getOption().grid[0].left===170")
        self.assertEqual(self.f['runs']['scheduling'],before)
        await self.nav('logistics-map')
        self.assertEqual(await self.page.locator('#dispatch-dashboard-root svg').count(),0)

    async def test_phase5_chat_escape_restores_focus_and_all_dashboard_state(self):
        for kind in ('assignment','scheduling'):
            await self.open('decision-dashboard','logistics_'+kind,self.f['ids'][kind])
            toggle=self.page.locator('[data-chat]');await toggle.click()
            self.assertEqual(await toggle.get_attribute('aria-expanded'),'true')
            self.assertTrue(await self.page.locator('.d-decision-dashboard').evaluate("el=>el.classList.contains('with-chat')"))
            await self.page.keyboard.press('Escape')
            self.assertTrue(await self.page.locator('.dispatch-chat').is_hidden())
            self.assertEqual(await toggle.get_attribute('aria-expanded'),'false')
            self.assertTrue(await toggle.evaluate('el=>el===document.activeElement'))
            self.assertFalse(await self.page.locator('.d-decision-dashboard').evaluate("el=>el.classList.contains('with-chat')"))
            before=sum(p.endswith('/interpretation') for _,p in self.requests)
            await toggle.click();await self.page.wait_for_timeout(150)
            self.assertEqual(sum(p.endswith('/interpretation') for _,p in self.requests)-before,1)
            await self.page.locator('.dispatch-chat [data-close]').click()
            self.assertEqual(await toggle.get_attribute('aria-expanded'),'false')

    async def test_phase5_comparative_states_stay_dark_and_do_not_change_the_base(self):
        self.essential();base=copy.deepcopy(self.f['runs']['assignment']);case=copy.deepcopy(self.case)
        await self.dashboard();audit=(Path(__file__).parent/'theme_audit.js').read_text()
        layer=self.page.locator('#dispatch-comparative')
        self.assertEqual((await self.page.evaluate(audit,'#dispatch-comparative'))['failures'],[])
        await self.page.locator('[data-generate-comparative]').click()
        await self.page.wait_for_function("document.querySelector('[data-comparative-state]')?.dataset.comparativeState==='queued'")
        self.assertEqual((await self.page.evaluate(audit,'#dispatch-comparative'))['failures'],[])
        self.comparative.update(status='error',error_message='Fallo sintético de referencia')
        await layer.get_by_role('button',name='Reintentar',exact=True).wait_for(state='visible')
        self.assertEqual((await self.page.evaluate(audit,'#dispatch-comparative'))['failures'],[])
        await layer.get_by_role('button',name='Reintentar',exact=True).click()
        await self.page.wait_for_function("document.querySelector('[data-comparative-state]')?.dataset.comparativeState==='queued'")
        self.comparative['status']='completed'
        await self.page.locator('[data-close-comparative]').wait_for(state='visible')
        self.assertEqual((await self.page.evaluate(audit,'#dispatch-comparative'))['failures'],[])
        artifact=copy.deepcopy(self.comparative)
        await self.page.locator('[data-close-comparative]').click();await self.page.locator('[data-open-comparative]').click()
        self.assertEqual(self.comparative_posts,2);self.assertEqual(self.comparative,artifact)
        self.assertEqual(self.f['runs']['assignment'],base);self.assertEqual(self.case,case)

    async def test_phase5_delayed_dashboard_styles_cannot_reopen_a_view_after_navigation(self):
        requested,release=asyncio.Event(),asyncio.Event()
        async def slow_style(route):requested.set();await release.wait();await route.continue_()
        await self.context.route('**/static/css/assignment-dashboard-v2.css*',slow_style)
        try:
            await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=decision-dashboard&case_id={self.case["id"]}&node_id=logistics_assignment&run_id={self.f["ids"]["assignment"]}',wait_until='domcontentloaded')
            await asyncio.wait_for(requested.wait(),6)
            await self.nav('logistics-overview')
        finally:release.set()
        await self.page.locator('[data-start-new-decision]').wait_for(state='visible');await self.page.wait_for_timeout(150)
        self.assertEqual(await self.page.locator('.view.is-active').get_attribute('data-view-panel'),'logistics-overview')
        await self.page.evaluate('window.DationDispatch.openRun('+json.dumps(self.f['ids']['assignment'])+',"logistics_assignment")')
        await self.page.locator('.assignment-dashboard-v2').wait_for(state='visible')
        count=await self.page.evaluate("[...document.querySelectorAll('link[rel=stylesheet]')].filter(x=>new URL(x.href).pathname==='/static/css/assignment-dashboard-v2.css').length")
        self.assertEqual(count,1)

    async def test_phase5_historical_dispatch_remains_dark_readable_and_exports_original_json(self):
        row=self.f['runs']['assignment'];row['schema_version']='dispatch_v2';row['result_json']['schema_version']='dispatch_v2'
        before=copy.deepcopy(row)
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=decision-dashboard&case_id={self.case["id"]}&run_id={row["id"]}')
        await self.page.locator('.dispatch-dashboard-focused').wait_for(state='visible')
        self.assertIn('CORRIDA HISTÓRICA',await self.page.locator('#dispatch-hero').inner_text())
        audit=(Path(__file__).parent/'theme_audit.js').read_text();result=await self.page.evaluate(audit)
        self.assertEqual(result['scheme'],'dark');self.assertEqual(result['failures'],[])
        self.assertNotIn('Profundidad',await self.page.locator('.dispatch-action-menu').inner_text())
        await self.page.locator('.dispatch-action-menu summary').click()
        async with self.page.expect_download() as downloaded:await self.page.locator('[data-json]').click()
        content=json.loads(Path(await (await downloaded.value).path()).read_text())
        self.assertEqual(content,before['result_json']);self.assertEqual(row,before)
        self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))

    async def test_phase4_config_waits_for_its_stylesheet_before_rendering(self):
        requested,release=asyncio.Event(),asyncio.Event()
        attempts=0
        async def slow_style(route):
            nonlocal attempts
            attempts+=1
            if attempts==1:
                requested.set();await release.wait();await route.abort()
            else:await route.continue_()
        await self.context.route('**/static/css/assignment-config-v2.css*',slow_style)
        try:
            await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=logistics-config&case_id={self.case["id"]}&node_id=logistics_assignment',wait_until='domcontentloaded')
            await asyncio.wait_for(requested.wait(),6)
            self.assertEqual(await self.page.locator('[data-config-review]').count(),0)
        finally:release.set()
        await self.page.get_by_role('button',name='Reintentar',exact=True).click()
        await self.page.locator('[data-config-review]').wait_for(state='visible')
        audit=(Path(__file__).parent/'theme_audit.js').read_text()
        self.assertEqual((await self.page.evaluate(audit))['failures'],[])
        await self.nav('logistics-map')
        await self.page.evaluate('window.DationDispatch.openCase('+json.dumps(self.case['id'])+',"logistics-config","logistics_assignment")')
        await self.page.locator('[data-config-review]').wait_for(state='visible')
        count=await self.page.evaluate("[...document.querySelectorAll('link[rel=stylesheet]')].filter(x=>new URL(x.href).pathname==='/static/css/assignment-config-v2.css').length")
        self.assertEqual(count,1)
        self.assertEqual(attempts,2)

    async def test_phase4_weight_edits_refresh_validation_and_review_without_losing_focus(self):
        await self.open('logistics-config','logistics_assignment')
        await self.page.locator('[data-objective=custom]').click()
        sliders=self.page.locator('[data-custom-weight]:not(:disabled)')
        for slider in await sliders.all():
            await slider.focus();await slider.press('Home')
        self.assertEqual(await self.page.locator('.d-workflow-action-bar').get_attribute('data-state'),'error')
        await self.page.locator('[data-config-review]').click()
        self.assertEqual(await self.page.locator('dialog[open]').count(),0)
        await sliders.first.focus();await sliders.first.press('End')
        self.assertTrue(await sliders.first.evaluate('el=>el===document.activeElement'))
        self.assertEqual(await self.page.locator('.d-workflow-action-bar').get_attribute('data-state'),'ready')
        await self.page.locator('[data-config-review]').click()
        self.assertIn('Cantidad de viajes 100 %',await self.page.locator('dialog[open]').inner_text())
        self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))

    async def test_phase4_filter_dialog_is_dark_accessible_and_preserves_escape_focus(self):
        await self.open('logistics-config','logistics_assignment')
        trigger=self.page.locator('[data-filter-dialog-open]');await trigger.click()
        audit=(Path(__file__).parent/'theme_audit.js').read_text()
        result=await self.page.evaluate(audit,'dialog[open]')
        self.assertEqual(result['failures'],[])
        self.assertEqual(result['scheme'],'dark')
        await self.page.locator('[data-filter-field-search]').fill('dest')
        self.assertTrue(await self.page.locator('[data-filter-add]:visible').count())
        await self.page.keyboard.press('Escape')
        await self.page.locator('dialog[open]').wait_for(state='detached')
        await self.page.wait_for_function("document.activeElement?.hasAttribute('data-filter-dialog-open')")
        self.assertTrue(await trigger.evaluate('el=>el===document.activeElement'))
        self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))

    async def test_phase4_old_assignment_drafts_keep_criteria_and_send_essential(self):
        draft={'objective':'custom','customWeights':{'trips':60,'cost':30,'own_fleet':10},'resourceMode':'own','configured':True,'dimensions':['trips','cost','own_fleet'],'analysisDepth':'comparative'}
        saved={'analysisDepth':'deep'}
        drafts={self.case['id']:draft,'another-case':{'objective':'min_cost','analysisDepth':'deep'}}
        await self.page.add_init_script('sessionStorage.setItem('+json.dumps(KEY)+','+json.dumps(json.dumps(saved))+');sessionStorage.setItem("dation.dispatch.drafts.v1",'+json.dumps(json.dumps(drafts))+');')
        await self.open('logistics-config','logistics_assignment')
        state=await self.page.evaluate('window.DationDispatch.getWorkspace()')
        self.assertNotIn('analysisDepth',state)
        self.assertEqual((state['objective'],state['resourceMode']),('custom','own'))
        self.assertEqual(state['customWeights']['trips'],60)
        stored=await self.page.evaluate('({workspace:JSON.parse(sessionStorage.getItem("'+KEY+'")),drafts:JSON.parse(sessionStorage.getItem("dation.dispatch.drafts.v1"))})')
        self.assertNotIn('analysisDepth',stored['workspace'])
        self.assertTrue(all('analysisDepth' not in value for value in stored['drafts'].values()))
        for select in await self.page.locator('[data-config-anomaly]').all():await select.select_option('include')
        await self.page.locator('[data-config-review]').click()
        await self.page.locator('[data-config-execute]').click()
        await self.page.wait_for_selector('.assignment-dashboard-v2')
        body=self.execution_bodies[-1]
        self.assertEqual(body['options']['analysis_depth'],'essential')
        self.assertEqual(body['options']['resource_mode'],'own')
        self.assertEqual(body['configuration']['objective'],'custom')
        self.assertEqual(body['configuration']['weights']['trips'],.6)

    async def test_phase4_scheduling_old_depth_and_unknown_options_are_not_reactivated(self):
        config={self.case['id']:{'strategy':'earliest_dispatch','windowMode':'custom','windowStart':'2026-01-01','windowEnd':'2026-12-31','analysisDepth':'deep','bufferBetweenTrips':123}}
        await self.page.add_init_script('sessionStorage.setItem("dation.scheduling.config.v1",'+json.dumps(json.dumps(config))+');')
        await self.open('logistics-config','logistics_scheduling')
        stored=await self.page.evaluate('JSON.parse(sessionStorage.getItem("dation.scheduling.config.v1"))')
        self.assertNotIn('analysisDepth',stored[self.case['id']]);self.assertNotIn('bufferBetweenTrips',stored[self.case['id']])
        self.assertEqual(await self.page.locator('[data-scheduling-window-start]').input_value(),'2026-01-01')
        await self.page.locator('[data-scheduling-review]').click()
        await self.page.locator('[data-scheduling-execute]').click()
        await self.page.wait_for_selector('.dispatch-scheduling-dashboard')
        body=self.execution_bodies[-1]
        self.assertEqual(body['source_run_id'],self.f['ids']['assignment'])
        self.assertEqual(body['configuration']['planning_window_start'],'2026-01-01')
        self.assertEqual(body['configuration']['planning_window_end'],'2026-12-31')
        self.assertEqual(body['configuration']['strategy'],'earliest_dispatch')
        self.assertNotIn('analysis_depth',body['options'])
        self.assertNotIn('bufferBetweenTrips',json.dumps(body))

    async def test_phase4_advanced_options_are_disabled_and_workflow_is_shared(self):
        for kind in ('assignment','scheduling'):
            await self.open('logistics-config','logistics_'+kind)
            self.assertEqual(await self.page.locator('.d-workflow-action-bar').count(),1)
            self.assertEqual(await self.page.locator('.d-workflow-action-bar__chip').count(),3)
            self.assertEqual(await self.page.locator('[data-depth]').count(),0)
            options=self.page.locator('.decision-advanced-option')
            self.assertEqual(await options.count(),3)
            for option in await options.all():
                self.assertTrue(await option.is_disabled())
                self.assertIn('Próximamente',await option.inner_text())
                self.assertEqual(await option.get_attribute('aria-disabled'),'true')
                self.assertIsNone(await option.get_attribute('name'))
            before=await self.page.evaluate('sessionStorage.getItem("'+KEY+'")')
            await options.first.dispatch_event('click')
            self.assertEqual(await self.page.evaluate('sessionStorage.getItem("'+KEY+'")'),before)
            await self.page.locator('.d-workflow-action-bar__chip').nth(1).click()
            self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))

    async def test_phase4_historical_depths_open_without_recalculation_or_depth_badge(self):
        for depth in ('essential','comparative','deep'):
            run=self.f['runs']['assignment'];run['result_json']['analysis']['depth']=depth
            run['result_json']['configuration']['options']['analysis_depth']=depth
            before=copy.deepcopy(run)
            await self.dashboard()
            self.assertEqual(await self.page.locator('[data-depth-badge]').count(),0)
            self.assertEqual(await self.page.locator('.assignment-dashboard-v2').get_attribute('data-analysis-depth'),depth)
            await self.page.locator('[data-more-menu] summary').click()
            await self.page.locator('[data-run-details]').click()
            self.assertNotIn('Profundidad',await self.page.locator('[data-run-drawer]').inner_text())
            self.assertEqual(run,before)
        self.assertFalse(any(m=='POST' and p in ('/api/runs',f'/api/runs/{self.f["ids"]["assignment"]}/comparative') for m,p in self.requests))

    async def test_phase4_dark_config_forms_review_and_footer_at_five_widths(self):
        audit=(Path(__file__).parent/'theme_audit.js').read_text()
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000});await self.page.wait_for_timeout(250)
            for kind in ('assignment','scheduling'):
                await self.open('logistics-config','logistics_'+kind)
                self.assertFalse(await self.page.locator('.view.is-active').get_attribute('data-dation-surface'))
                if kind=='assignment':await self.page.locator('[data-objective=custom]').click()
                else:await self.page.locator('[data-scheduling-focus-toggle]').click()
                result=await self.page.evaluate(audit)
                self.assertEqual(result['failures'],[],(width,kind,result['failures']))
                self.assertFalse(result['overflow'])
                await self.page.locator('.decision-advanced-option').last.scroll_into_view_if_needed()
                await self.page.evaluate('window.scrollTo(0,document.documentElement.scrollHeight)')
                geometry=await self.page.evaluate('''()=>{
                  const last=document.querySelector('.decision-advanced-option:last-child').getBoundingClientRect();
                  const bar=document.querySelector('.d-workflow-action-bar').getBoundingClientRect();
                  return {last:last.bottom,bar:bar.top,padding:parseFloat(getComputedStyle(document.querySelector('#dispatch-config-root')).paddingBottom),height:bar.height};
                }''')
                self.assertLessEqual(geometry['last'],geometry['bar']+1)
                self.assertGreater(geometry['padding'],geometry['height'])
                for select in await self.page.locator('[data-config-anomaly]').all():await select.select_option('include')
                await self.page.locator('[data-config-review]' if kind=='assignment' else '[data-scheduling-review]').click()
                dialog=self.page.locator('dialog[open]');await dialog.wait_for(state='visible')
                result=await self.page.evaluate(audit,'dialog[open]')
                self.assertEqual(result['failures'],[],(width,kind,result['failures']))
                self.assertEqual(result['scheme'],'dark')
                await self.page.keyboard.press('Escape')
                self.assertEqual(await self.page.locator('dialog[open]').count(),0)

    async def test_malformed_saved_state(self):
        await self.page.add_init_script(f"sessionStorage.setItem('{KEY}','null');sessionStorage.setItem('dation.scheduling.config.v1','[]');")
        await self.open("logistics-config","logistics_scheduling")

    async def test_new_assignment_preserves_approval(self):
        await self.open("logistics-config","logistics_assignment")
        for select in await self.page.locator("[data-config-anomaly]").all(): await select.select_option("include")
        await self.page.locator("[data-config-review]").click()
        await self.page.locator("[data-config-execute]").click()
        await self.page.wait_for_selector(".assignment-dashboard-v2")
        self.assertEqual(self.execution_bodies[-1]["options"]["analysis_depth"],"essential")
        approved = await self.page.evaluate("window.DationDispatch.getWorkspace().decisionCase.nodes.logistics_assignment.approved_run_id")
        self.assertEqual(approved,self.f["ids"]["assignment"])
        self.assertNotEqual(parse_qs(urlparse(self.page.url).query)["run_id"][0],approved)

    async def test_scheduling_executes_with_rules_contract(self):
        await self.open("logistics-config","logistics_scheduling")
        await self.page.locator("[data-scheduling-review]").click()
        await self.page.locator("[data-scheduling-execute]").click()
        await self.page.wait_for_selector(".dispatch-scheduling-dashboard")
        self.assertIn("node_id=logistics_scheduling",self.page.url)

    async def test_lost_post_response_recovers_same_run(self):
        self.post_status = 502
        await self.test_new_assignment_preserves_approval()
        self.assertEqual(sum(m=='POST' and p=='/api/runs' for m,p in self.requests),1)

    async def test_stale_result_has_no_approval(self):
        self.case["nodes"]["logistics_scheduling"]["status"] = "stale"
        self.case["nodes"]["logistics_scheduling"]["approved_run_id"] = self.f["ids"]["scheduling"]
        await self.open("decision-dashboard","logistics_scheduling",self.f["ids"]["scheduling"])
        self.assertEqual(await self.page.locator("[data-approve-toolbar]").count(),0)

    async def test_module_urls_have_single_identity(self):
        await self.open("logistics-config","logistics_scheduling")
        urls = await self.page.evaluate("performance.getEntriesByType('resource').map(x=>x.name).filter(x=>/\\.(mjs|js)(\\?|$)/.test(x))")
        module_urls = [url for url in urls if '/dispatch/' in url]
        self.assertTrue(module_urls)
        self.assertTrue(all('?v=' not in url for url in module_urls))
        self.assertEqual(len(module_urls),len(set(urlparse(url).path for url in module_urls)))

    async def test_explanation_aborts_on_navigation(self):
        await self.open("decision-dashboard","logistics_assignment",self.f["ids"]["assignment"])
        path=f"/api/runs/{self.f['ids']['assignment']}/explain"
        self.delay[path]=.8
        await self.page.locator("[data-explain]").click()
        await self.nav("logistics-map")
        await self.page.wait_for_timeout(950)
        self.assertEqual(await self.page.locator("#dispatch-dashboard-root").inner_text(),"")
        self.assertNotIn("Synthetic explanation",await self.page.locator("body").inner_text())

    async def test_history_modal_removed_when_leaving(self):
        await self.open()
        await self.page.evaluate("window.DationDispatch.openRunHistory('logistics_assignment')")
        await self.page.wait_for_selector(".dispatch-trace-dialog")
        await self.nav("logistics-data")
        self.assertEqual(await self.page.locator(".dispatch-trace-dialog").count(),0)

    def large_history(self):
        row=self.f['runs']['assignment']
        self.history_rows=[{**row,'id':f'00000000-0000-4000-8000-{index:012d}','approved_at':None} for index in range(205,0,-1)]
        self.history_rows[-1]=row

    async def test_history_paginates_and_preserves_approval_outside_page(self):
        self.large_history()
        await self.page.set_viewport_size({'width':390,'height':844})
        await self.open()
        await self.page.evaluate("window.DationDispatch.openRunHistory('logistics_assignment')")
        await self.page.wait_for_selector('[data-history-next]')
        self.assertEqual(await self.page.locator('[data-history-range]').inner_text(),'1–100 de 205')
        summary=await self.page.locator('.dispatch-run-history__summary').inner_text()
        self.assertIn('Aprobada vigente',summary)
        await self.page.locator('[data-history-next]').click()
        await self.page.wait_for_function("document.querySelector('[data-history-range]')?.textContent==='101–200 de 205'")
        self.assertEqual(await self.page.locator('.dispatch-run-history__summary').inner_text(),summary)
        await self.page.locator('[data-history-next]').click()
        await self.page.wait_for_function("document.querySelector('[data-history-range]')?.textContent==='201–205 de 205'")
        self.assertTrue(await self.page.locator('[data-history-next]').is_disabled())
        self.assertEqual(await self.page.locator('.dispatch-run-history__item').count(),5)
        self.assertIn('Aprobación histórica',await self.page.locator('.dispatch-run-history__list').inner_text())
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        await self.page.locator('[data-history-prev]').click()
        await self.page.wait_for_function("document.querySelector('[data-history-range]')?.textContent==='101–200 de 205'")

    async def test_history_page_error_retries_and_late_response_cannot_reopen_dialog(self):
        self.large_history();self.history_failure=True
        await self.open()
        await self.page.evaluate("window.DationDispatch.openRunHistory('logistics_assignment')")
        await self.page.wait_for_selector('[data-history-next]')
        await self.page.locator('[data-history-next]').click()
        await self.page.wait_for_function("document.querySelector('[data-history-error]')?.textContent.includes('no disponible')")
        self.assertEqual(await self.page.locator('[data-history-range]').inner_text(),'1–100 de 205')
        self.history_failure=False
        await self.page.locator('[data-history-next]').click()
        await self.page.wait_for_function("document.querySelector('[data-history-range]')?.textContent==='101–200 de 205'")
        self.delay[f"/api/decision-cases/{self.case['id']}/runs"]=.6
        await self.page.locator('[data-history-next]').click()
        await self.nav('logistics-data')
        await self.page.wait_for_timeout(750)
        self.assertEqual(await self.page.locator('.dispatch-trace-dialog').count(),0)

    async def test_mobile_config_stays_within_viewport(self):
        await self.page.set_viewport_size({"width":390,"height":844})
        await self.open("logistics-config","logistics_scheduling")
        self.assertFalse(await self.page.evaluate("document.documentElement.scrollWidth>innerWidth"))
        await self.page.locator("[data-scheduling-review]").click()
        bounds=await self.page.locator("dialog[open]").bounding_box()
        self.assertGreaterEqual(bounds['x'],0)
        self.assertLessEqual(bounds['x']+bounds['width'],391)

    async def test_dashboard_exports_csv(self):
        await self.open("decision-dashboard","logistics_assignment",self.f["ids"]["assignment"])
        await self.page.locator("[data-export-menu] summary").click()
        async with self.page.expect_download() as download:
            await self.page.locator("[data-export-csv]").click()
        self.assertTrue((await download.value).suggested_filename.endswith('.csv'))

    async def test_assignment_draft_is_restored_per_case(self):
        await self.open("logistics-config","logistics_assignment")
        await self.page.locator('[data-objective="min_cost"]').click()
        first=copy.deepcopy(self.case)
        self.case={**copy.deepcopy(first),"id":"00000000-0000-4000-8000-000000000006"}
        self.f["case_row"]["id"]=self.case["id"]
        await self.page.evaluate("id=>window.DationDispatch.openCase(id,'logistics-config','logistics_assignment')",self.case["id"])
        self.assertEqual(await self.page.evaluate("window.DationDispatch.getWorkspace().objective"),"balanced")
        self.case=first
        self.f["case_row"]["id"]=first["id"]
        await self.page.evaluate("id=>window.DationDispatch.openCase(id,'logistics-config','logistics_assignment')",first["id"])
        self.assertEqual(await self.page.evaluate("window.DationDispatch.getWorkspace().objective"),"min_cost")

    async def test_observers_are_disposed_after_repeated_routes(self):
        await self.page.add_init_script("""
          window.__qaObservers=new Set();
          for(const name of ['ResizeObserver','IntersectionObserver']){
            const Native=window[name];
            window[name]=class extends Native{
              constructor(callback){super(callback);this.application=String(new Error().stack).includes('/static/');this.targets=new Set();}
              observe(target,options){super.observe(target,options);this.targets.add(target);if(this.application)window.__qaObservers.add(this);}
              unobserve(target){super.unobserve(target);this.targets.delete(target);if(!this.targets.size)window.__qaObservers.delete(this);}
              disconnect(){super.disconnect();this.targets.clear();window.__qaObservers.delete(this);}
            };
          }
        """)
        await self.open()
        for _ in range(3):
            await self.nav("logistics-data")
            await self.page.wait_for_selector("#dispatch-data-root input[type=file]", state="attached")
            await self.page.evaluate("id=>window.DationDispatch.openRun(id,'logistics_scheduling')",self.f["ids"]["scheduling"])
            await self.page.wait_for_selector(".dispatch-scheduling-dashboard")
            await self.nav("logistics-map")
        await self.nav("settings")
        await self.page.wait_for_timeout(100)
        self.assertEqual(await self.page.evaluate("window.__qaObservers.size"),0)
        self.assertEqual(await self.page.locator(".dispatch-guide-overlay,.dispatch-previous-overlay,.dispatch-validation-overlay").count(),0)

    async def test_dashboard_drawer_traps_focus_and_escape_returns_to_menu(self):
        await self.open("decision-dashboard","logistics_assignment",self.f["ids"]["assignment"])
        await self.page.locator("[data-run-details]").evaluate("button=>{button.closest('details').open=true;}")
        await self.page.locator("[data-run-details]").click()
        drawer=self.page.locator("[data-run-drawer]")
        await drawer.wait_for(state="visible")
        await self.page.keyboard.press("Shift+Tab")
        self.assertTrue(await drawer.evaluate("node=>node.contains(document.activeElement)"))
        await self.page.keyboard.press("Escape")
        self.assertEqual(await drawer.is_visible(),False)
        self.assertEqual(await self.page.evaluate("document.activeElement.tagName"),"SUMMARY")

    async def test_chat_retry_reuses_turn_id_and_older_messages_prepend(self):
        self.chat_fail_once=True
        self.chat_history=[{'id':str(i),'role':'user' if i%2 else 'assistant','content':'Message '+str(i)} for i in range(4,0,-1)]
        await self.open("decision-dashboard","logistics_assignment",self.f["ids"]["assignment"])
        await self.page.locator('[data-chat]').click()
        await self.page.locator('[data-older]').wait_for(state='visible')
        await self.page.locator('[data-older]').click()
        await self.page.wait_for_function("document.querySelector('[data-older]').hidden")
        self.assertEqual(await self.page.locator('[data-messages] article div').all_text_contents(),['Message 1','Message 2','Message 3','Message 4'])
        field=self.page.locator('.dispatch-chat textarea')
        await field.fill('¿Qué debo revisar?')
        await self.page.locator('.dispatch-chat button[type=submit]').click()
        await self.page.wait_for_function("document.querySelector('.dispatch-chat textarea').value.length>0")
        await self.page.locator('.dispatch-chat button[type=submit]').click()
        await self.page.get_by_text('Synthetic answer',exact=True).wait_for()
        self.assertEqual(len(self.chat_calls),2)
        self.assertEqual(self.chat_calls[0]['turn_id'],self.chat_calls[1]['turn_id'])
        from uuid import UUID
        UUID(self.chat_calls[0]['turn_id'])

    async def test_chat_response_cannot_focus_a_departed_screen(self):
        await self.open("decision-dashboard","logistics_assignment",self.f["ids"]["assignment"])
        self.delay[f"/api/runs/{self.f['ids']['assignment']}/chat"]=.8
        await self.page.locator("[data-chat]").click()
        await self.page.locator(".dispatch-chat textarea").fill("¿Qué viajes requieren revisión?")
        await self.page.locator(".dispatch-chat button[type=submit]").click()
        await self.nav("logistics-map")
        await self.page.wait_for_timeout(950)
        self.assertEqual(await self.page.locator(".dispatch-chat").count(),0)
        self.assertNotIn("Synthetic answer",await self.page.locator("body").inner_text())

    async def test_scheduling_does_not_poll_before_admission_finishes(self):
        self.delay['/api/runs']=1
        await self.open('logistics-config','logistics_scheduling')
        await self.page.locator('[data-scheduling-review]').click()
        await self.page.locator('[data-scheduling-execute]').click()
        from urllib.parse import parse_qs,urlparse
        identifier=parse_qs(urlparse(self.page.url).query)['run_id'][0]
        await self.page.wait_for_timeout(650)
        self.assertNotIn(('GET','/api/runs/'+identifier),self.requests)
        await self.page.wait_for_selector('.dispatch-scheduling-dashboard')
        self.assertIn(('GET','/api/runs/'+identifier),self.requests)

    async def test_late_execution_response_does_not_reopen_dashboard(self):
        self.delay['/api/runs']=.8
        await self.open("logistics-config","logistics_scheduling")
        await self.page.locator("[data-scheduling-review]").click()
        await self.page.locator("[data-scheduling-execute]").click()
        await self.nav("logistics-map")
        await self.page.wait_for_timeout(1200)
        self.assertEqual(await self.page.evaluate("window.dationGetCurrentView()"),"logistics-map")
        self.assertEqual(await self.page.locator(".dispatch-scheduling-dashboard").count(),0)

    async def test_mobile_map_and_dashboard_do_not_overflow(self):
        await self.page.set_viewport_size({"width":390,"height":844})
        await self.open()
        self.assertFalse(await self.page.evaluate("document.documentElement.scrollWidth>innerWidth"))
        await self.page.evaluate("id=>window.DationDispatch.openRun(id,'logistics_assignment')",self.f["ids"]["assignment"])
        await self.page.wait_for_selector(".assignment-dashboard-v2")
        self.assertFalse(await self.page.evaluate("document.documentElement.scrollWidth>innerWidth"))


    async def test_dark_shell_and_heroes_survive_responsive_and_warm_navigation(self):
        await self.page.emulate_media(reduced_motion="reduce", color_scheme="light")
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({"width":width,"height":1000})
            for view,node in (("inicio",None),("logistics-overview",None),("logistics-data",None),
                              ("logistics-map",None),("logistics-config","logistics_scheduling"),
                              ("logistics-config","logistics_assignment")):
                if view in ("inicio","logistics-overview","logistics-data"):
                    await self.page.goto(f"http://127.0.0.1:{self.port}/app?view={view}")
                else:
                    await self.open(view,node)
                hero=self.page.locator(".view.is-active .d-page-hero")
                await hero.wait_for(state="visible")
                metrics=await hero.evaluate("""el=>{
                    const s=getComputedStyle(el), h=el.querySelector('h1'), r=el.getBoundingClientRect();
                    return {scheme:getComputedStyle(document.documentElement).colorScheme,
                        body:getComputedStyle(document.body).backgroundColor, topbar:getComputedStyle(document.querySelector('.topbar')).backgroundColor,
                        minHeight:parseFloat(s.minHeight),padding:parseFloat(s.paddingTop),radius:parseFloat(s.borderRadius),
                        title:parseFloat(getComputedStyle(h).fontSize),height:r.height,
                        overflow:document.documentElement.scrollWidth>innerWidth,
                        childrenFit:[...el.children].every(x=>x.getBoundingClientRect().right<=r.right+1),
                        workspace:document.querySelector('.dda-workspace-nav-shell[hidden]')?null:getComputedStyle(document.querySelector('.dda-workspace-nav')).backgroundColor,
                        current:document.querySelector('.dda-workspace-step.is-current')?getComputedStyle(document.querySelector('.dda-workspace-step.is-current')).color:null,
                        disabledCursors:[...document.querySelectorAll('.dda-workspace-step.is-disabled')].map(x=>getComputedStyle(x).cursor)};
                }""")
                with self.subTest(width=width,view=view,node=node):
                    self.assertEqual(metrics["scheme"],"dark")
                    self.assertEqual(metrics["body"],"rgb(7, 16, 21)")
                    self.assertEqual(metrics["topbar"],"rgba(10, 20, 27, 0.96)")
                    self.assertFalse(metrics["overflow"])
                    self.assertTrue(metrics["childrenFit"])
                    self.assertGreaterEqual(metrics["minHeight"],210)
                    self.assertTrue(20<=metrics["padding"]<=28)
                    self.assertEqual(metrics["radius"],24)
                    self.assertTrue(28<=metrics["title"]<=40)
                    if metrics["workspace"]:self.assertEqual(metrics["workspace"],"rgb(15, 27, 36)")
                    if metrics["current"]:self.assertEqual(metrics["current"],"rgb(243, 248, 250)")
                    self.assertTrue(all(cursor=="default" for cursor in metrics["disabledCursors"]))
            # The real SPA path retains dynamically loaded styles across decisions.
            await self.page.evaluate("id=>window.DationDispatch.openCase(id,'logistics-config','logistics_scheduling')",self.case["id"])
            await self.page.locator(".scheduling-config-v2 .d-page-hero").wait_for(state="visible")
            await self.page.evaluate("id=>window.DationDispatch.openCase(id,'logistics-config','logistics_assignment')",self.case["id"])
            await self.page.locator(".assignment-config-v2 .d-page-hero").wait_for(state="visible")
            self.assertFalse(await self.page.evaluate("document.documentElement.scrollWidth>innerWidth"))

    async def test_dark_buttons_have_keyboard_focus_contrast_and_stable_disabled_state(self):
        # Isolate control states from the decorative page entrance animation.
        await self.page.emulate_media(reduced_motion="reduce")
        await self.page.goto(f"http://127.0.0.1:{self.port}/app?view=logistics-overview")
        primary=self.page.locator("[data-start-new-decision]")
        await primary.wait_for(state="visible")
        await self.page.mouse.move(0,0)
        await primary.focus()
        self.assertTrue(await primary.evaluate("el=>el.matches(':focus-visible')"))
        self.assertEqual(await primary.evaluate("el=>getComputedStyle(el).outlineStyle"),"solid")
        self.assertEqual(await primary.evaluate("el=>parseFloat(getComputedStyle(el).outlineWidth)"),3)
        normal=await primary.evaluate("el=>getComputedStyle(el).backgroundImage")
        await primary.hover();await self.page.wait_for_timeout(180)
        hover=await primary.evaluate("el=>getComputedStyle(el).backgroundImage")
        self.assertNotEqual(normal,hover)
        # Actual computed colors, including every point of the action gradient.
        contrast=await primary.evaluate("""(el,gradients)=>{
            const rgb=s=>(s.match(/[\\d.]+/g)||[]).map(Number).slice(0,3);
            const lum=c=>c.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((a,x,i)=>a+x*[.2126,.7152,.0722][i],0);
            const ratio=(a,b)=>(Math.max(lum(a),lum(b))+.05)/(Math.min(lum(a),lum(b))+.05);
            const fg=rgb(getComputedStyle(el).color);
            return Math.min(...gradients.map(gradient=>{
            const stops=gradient.match(/rgb\\([^)]+\\)/g).map(rgb);
            return Math.min(...stops.slice(1).flatMap((b,i)=>Array.from({length:257},(_,k)=>ratio(fg,b.map((v,j)=>stops[i][j]+(v-stops[i][j])*k/256)))));
            }));
        }""",[normal,hover])
        self.assertGreaterEqual(contrast,4.5)
        await self.page.evaluate("""()=>{
            const region=document.createElement('div');region.id='theme-control-fixture';
            for(const variant of ['secondary','ghost','danger','icon','menu']) {
                const button=document.createElement('button');button.className='d-button d-button--'+variant;
                button.type='button';button.textContent=variant;button.dataset.variant=variant;region.append(button);
            }
            const disabled=document.createElement('button');disabled.className='d-button d-button--primary';disabled.disabled=true;
            disabled.textContent='Disabled';region.append(disabled);document.querySelector('.topbar').append(region);
        }""")
        disabled=self.page.locator("#theme-control-fixture button:disabled")
        before=await disabled.evaluate("el=>[getComputedStyle(el).backgroundImage,getComputedStyle(el).backgroundColor,getComputedStyle(el).transform]")
        await disabled.hover(force=True);await self.page.wait_for_timeout(180)
        self.assertEqual(before,await disabled.evaluate("el=>[getComputedStyle(el).backgroundImage,getComputedStyle(el).backgroundColor,getComputedStyle(el).transform]"))
        self.assertEqual(await disabled.evaluate("el=>getComputedStyle(el).opacity"),"1")
        await self.page.locator("#theme-control-fixture [data-variant=secondary]").focus()
        await self.page.keyboard.press("Tab")
        self.assertTrue(await self.page.locator("#theme-control-fixture [data-variant=ghost]").evaluate("el=>el===document.activeElement && el.matches(':focus-visible')"))
        await self.page.emulate_media(reduced_motion="reduce")
        await primary.hover()
        self.assertEqual(await primary.evaluate("el=>getComputedStyle(el).transform"),"none")

    async def test_config_controls_and_review_use_native_dark_roles(self):
        await self.open("logistics-config","logistics_assignment")
        panel=self.page.locator(".view.is-active")
        self.assertEqual(await panel.evaluate("el=>getComputedStyle(el).colorScheme"),"dark")
        self.assertEqual(await panel.locator(".d-page-hero").evaluate("el=>getComputedStyle(el).colorScheme"),"dark")
        await self.page.locator("[data-config-review]").click()
        dialog=self.page.locator("dialog[open]")
        await dialog.wait_for(state="visible")
        self.assertEqual(await dialog.evaluate("el=>getComputedStyle(el).colorScheme"),"dark")
        execute=self.page.locator("[data-config-execute]")
        await self.page.keyboard.press("Tab")
        await execute.focus()
        self.assertTrue(await execute.evaluate("el=>el.matches(':focus-visible')"))
        await self.page.keyboard.press("Escape")
        self.assertFalse(await dialog.is_visible())
        self.assertEqual(self.execution_bodies,[])


    async def test_home_overview_dark_contrast_compact_heroes_and_responsive_actions(self):
        audit = (Path(__file__).parent / "theme_audit.js").read_text()
        await self.page.emulate_media(reduced_motion="reduce", color_scheme="light")
        for width in (1440, 1280, 1024, 768, 390):
            await self.page.set_viewport_size({"width": width, "height": 844})
            heights = {}
            for view in ("inicio", "logistics-overview"):
                with self.subTest(width=width, view=view):
                    await self.page.goto(f"http://127.0.0.1:{self.port}/app?view={view}")
                    await self.page.locator(".view.is-active h1").wait_for(state="visible")
                    await self.page.locator(".view.is-active").evaluate("el=>el.scrollIntoView({block:'start',behavior:'instant'})")
                    metrics = await self.page.evaluate(audit)
                    self.assertEqual(metrics["scheme"], "dark")
                    self.assertFalse(metrics["legacyBoundary"])
                    self.assertFalse(metrics["overflow"])
                    self.assertGreater(metrics["textCount"], 15)
                    self.assertEqual(metrics["failures"], [], "Rendered text must meet AA, including muted informational content")
                    for card in metrics["cards"]:
                        # Transparent sections inherit the dark canvas; solid cards must stay dark.
                        channels = card["background"].removeprefix("rgba(").removeprefix("rgb(").rstrip(")").split(",")
                        self.assertLess(max(float(x) for x in channels[:3]), 80)
                    heights[view] = metrics["hero"]["height"]
                    if view == "logistics-overview":
                        self.assertEqual(await self.page.locator(".dda-landing__final").count(), 0)
                        actions = self.page.locator(".dda-landing__hero-actions button")
                        self.assertEqual(await actions.count(), 2)
                        if width == 390:
                            boxes = [await actions.nth(i).bounding_box() for i in range(2)]
                            self.assertLess(boxes[1]["y"] + boxes[1]["height"], 844)
                            self.assertGreaterEqual(boxes[1]["y"], boxes[0]["y"] + boxes[0]["height"])
                            self.assertAlmostEqual(boxes[0]["width"], boxes[1]["width"], delta=1)
            if width >= 1280:
                self.assertLessEqual(heights["inicio"], heights["logistics-overview"] * 1.1 + 1)
                self.assertLessEqual(heights["inicio"], 250)
        self.assertEqual(self.execution_bodies, [])

    async def test_home_card_keyboard_and_informational_overview_with_native_faq(self):
        await self.page.emulate_media(reduced_motion="reduce")
        await self.page.goto(f"http://127.0.0.1:{self.port}/app?view=inicio")
        active = self.page.locator("#home-open-logistics")
        await active.wait_for(state="visible")
        inactive = self.page.locator(".d-home__asset--disabled")
        self.assertEqual(await inactive.get_attribute("aria-disabled"), "true")
        self.assertEqual(await inactive.evaluate("el=>el.tagName"), "ARTICLE")
        self.assertEqual(await inactive.locator("button,a,[tabindex]").count(), 0)
        self.assertEqual(await inactive.evaluate("el=>getComputedStyle(el).opacity"), "1")
        await active.focus()
        self.assertTrue(await active.evaluate("el=>el.matches(':focus-visible')"))
        self.assertEqual(await active.evaluate("el=>getComputedStyle(el).outlineWidth"), "3px")
        await self.page.keyboard.press("Enter")
        await self.page.locator(".dda-landing__hero").wait_for(state="visible")
        self.assertEqual(await self.page.evaluate("window.dationGetCurrentView()"), "logistics-overview")
        for state, label in (("is-active", "Optimiza hoy"), ("is-inactive", "En consolidación")):
            pills = self.page.locator(".dda-landing__variable-pill." + state)
            self.assertEqual(await pills.count(), 3)
            self.assertEqual(await pills.locator(".dda-landing__variable-status").all_text_contents(), [label] * 3)
        chain = self.page.locator(".dda-landing__chain")
        self.assertEqual(await chain.locator(".is-conceptual").count(), 3)
        self.assertEqual(await chain.locator("button,[data-node-state],.dda-landing__node-footer").count(), 0)
        summaries = self.page.locator(".dda-landing__faq-grid summary")
        self.assertEqual(await summaries.count(), 4)
        for index in range(4):
            summary = summaries.nth(index)
            await summary.focus()
            self.assertTrue(await summary.evaluate("el=>el.matches(':focus-visible')"))
            self.assertEqual(await summary.evaluate("el=>getComputedStyle(el).outlineWidth"), "3px")
            await self.page.keyboard.press("Enter" if index % 2 == 0 else "Space")
            self.assertTrue(await summary.evaluate("el=>el.parentElement.open"))
        audit = await self.page.evaluate((Path(__file__).parent / "theme_audit.js").read_text())
        self.assertEqual(audit["failures"], [])
        self.assertEqual(self.execution_bodies, [])


    async def upload_reuse_pair(self):
        for kind in ("orders", "fleet"):
            card = self.page.locator(f"[data-kind={kind}]")
            await card.locator("[data-mode=reuse]").click()
            await card.get_by_role("button", name="Usar esta carga", exact=True).click()

    async def test_data_pack_has_one_stable_dark_bar_across_responsive_reuse(self):
        audit = (Path(__file__).parent / "theme_audit.js").read_text()
        await self.page.emulate_media(reduced_motion="reduce", color_scheme="light")
        await self.page.add_init_script("sessionStorage.clear()")
        for width in (1440, 1280, 1024, 768, 390):
            await self.page.set_viewport_size({"width": width, "height": 844})
            await self.page.goto(f"http://127.0.0.1:{self.port}/app?view=logistics-data")
            await self.page.locator("[data-kind=fleet] .dispatch-pro-dropzone").wait_for(state="visible")
            bar = self.page.locator(".d-workflow-action-bar")
            self.assertEqual(await bar.count(), 1)
            self.assertEqual(await bar.locator("button").count(), 1)
            self.assertTrue(await bar.locator("button").is_disabled())
            await bar.evaluate("el=>window.__originalActionBar=el")
            for ready in (False, True):
                if ready:
                    await self.upload_reuse_pair()
                    await self.page.locator(".d-workflow-action-bar[data-state=ready]").wait_for(state="visible")
                    self.assertFalse(await bar.locator("button").is_disabled())
                    self.assertTrue(await bar.evaluate("el=>el===window.__originalActionBar"))
                metrics = await self.page.evaluate(audit)
                self.assertEqual(metrics["scheme"], "dark")
                self.assertFalse(metrics["legacyBoundary"])
                self.assertFalse(metrics["overflow"])
                self.assertEqual(metrics["failures"], [])
                await self.page.evaluate("scrollTo({top:0,behavior:'instant'})")
                box = await bar.bounding_box()
                self.assertAlmostEqual(box["y"] + box["height"], 828, delta=1)
                if width >= 1280:
                    self.assertGreaterEqual(box["height"], 76)
                    self.assertLessEqual(box["height"], 88)
                await self.page.evaluate("scrollTo({top:document.documentElement.scrollHeight,behavior:'instant'})")
                if ready:
                    last = self.page.locator("[data-kind=fleet] .dispatch-pro-validation-success summary")
                    await last.focus()
                    control, footer = await last.bounding_box(), await bar.bounding_box()
                    self.assertLessEqual(control["y"] + control["height"], footer["y"])
            self.assertNotIn(("POST", "/api/decision-cases"), self.requests)
        self.assertEqual(self.execution_bodies, [])

    async def test_data_pack_invalid_file_focus_busy_cancel_and_service_unavailable(self):
        audit = (Path(__file__).parent / "theme_audit.js").read_text()
        await self.page.emulate_media(reduced_motion="reduce")
        await self.page.goto(f"http://127.0.0.1:{self.port}/app?view=logistics-data")
        file = self.page.locator("[data-kind=orders] input[type=file]")
        await file.wait_for(state="attached")
        await file.set_input_files({"name":"bad.txt", "mimeType":"text/plain", "buffer":b"bad"})
        bar = self.page.locator(".d-workflow-action-bar")
        await self.page.locator(".d-workflow-action-bar[data-state=error]").wait_for(state="visible")
        await bar.locator("button").click()
        self.assertEqual(await self.page.evaluate("document.activeElement.dataset.kind"), "orders")
        self.assertEqual(await self.page.evaluate("window.dationGetCurrentView()"), "logistics-data")
        await self.page.get_by_role("button", name="Ver detalle", exact=True).first.click()
        await self.page.locator(".dispatch-validation-drawer").wait_for(state="visible")
        self.assertEqual((await self.page.evaluate(audit, ".dispatch-validation-drawer"))["failures"], [])
        await self.page.keyboard.press("Escape")
        started, release = asyncio.Event(), asyncio.Event()
        async def validation(route):
            started.set()
            await release.wait()
            try:
                await route.fulfill(status=200, content_type="application/json", body=json.dumps({"valid":False,"errors":[],"counts":{"errors":1}}))
            except Exception:
                pass  # Cancellation aborts this owned synthetic request.
        await self.context.route("**/api/datasets/validate**", validation)
        await file.set_input_files({"name":"orders.csv", "mimeType":"text/csv", "buffer":b"order_id\n1"})
        await asyncio.wait_for(started.wait(), 5)
        await self.page.locator(".d-workflow-action-bar[data-state=validating]").wait_for(state="visible")
        self.assertTrue(await bar.locator("button").is_disabled())
        self.assertEqual(await bar.locator("button").get_attribute("aria-busy"), "true")
        await bar.locator("button").dispatch_event("click")
        await self.page.locator("[data-kind=orders] .dispatch-pro-progress button").click()
        release.set()
        await self.page.locator(".d-workflow-action-bar[data-state=pending]").wait_for(state="visible")
        async def unavailable(route):
            await route.fulfill(status=200, content_type="application/json", body=json.dumps({"available":False,"checks":[{"ok":False,"label":"Storage","detail":"No disponible"}]}))
        await self.context.route("**/api/dispatch/status", unavailable)
        await self.page.reload()
        await self.page.locator(".dispatch-system-banner").wait_for(state="visible")
        await self.page.locator(".dispatch-system-banner summary").click()
        self.assertTrue(await bar.locator("button").is_disabled())
        self.assertIn("Servicio no disponible", await bar.inner_text())
        self.assertEqual((await self.page.evaluate(audit))["failures"], [])
        self.assertNotIn(("POST", "/api/decision-cases"), self.requests)
        self.assertEqual(self.execution_bodies, [])

    async def test_data_pack_relation_error_recovers_to_ready_with_optional_warnings(self):
        audit = (Path(__file__).parent / "theme_audit.js").read_text()
        self.f["preflight"]["errors"] = [{"code":"UNKNOWN_CURRENT_VEHICLE", "detail":"Vehículo no encontrado"}]
        profile = self.f["datasets"]["orders"]["profile_json"]
        profile["counts"]["warnings"] = 1
        profile["warnings"] = [{"code":"EXTRA_COLUMN", "message":"Columna opcional adicional"}]
        await self.page.emulate_media(reduced_motion="reduce")
        await self.page.goto(f"http://127.0.0.1:{self.port}/app?view=logistics-data")
        await self.page.locator("[data-kind=fleet] input[type=file]").wait_for(state="attached")
        await self.upload_reuse_pair()
        await self.page.locator(".d-workflow-action-bar[data-state=error]").wait_for(state="visible")
        await self.page.locator(".dispatch-pro-compatibility button").click()
        await self.page.locator(".dispatch-validation-drawer").wait_for(state="visible")
        self.assertEqual((await self.page.evaluate(audit, ".dispatch-validation-drawer"))["failures"], [])
        await self.page.keyboard.press("Escape")
        self.f["preflight"]["errors"] = []
        await self.page.locator("[data-kind=fleet] .dispatch-pro-file-actions .is-danger").click()
        fleet = self.page.locator("[data-kind=fleet]")
        await fleet.locator("[data-mode=reuse]").click()
        await fleet.get_by_role("button", name="Usar esta carga", exact=True).click()
        await self.page.locator(".d-workflow-action-bar[data-state=ready]").wait_for(state="visible")
        self.assertFalse(await self.page.locator(".dispatch-pro-next-button").is_disabled())
        self.assertIn("con avisos", await self.page.locator(".d-workflow-action-bar").inner_text())
        self.assertEqual((await self.page.evaluate(audit))["failures"], [])
        await fleet.locator("[data-mode=reuse]").click()
        await fleet.locator(".dispatch-pro-view-all").click()
        drawer = self.page.locator(".dispatch-previous-drawer")
        await drawer.wait_for(state="visible")
        self.assertEqual((await self.page.evaluate(audit, ".dispatch-previous-drawer"))["failures"], [])
        self.assertEqual(await drawer.get_attribute("aria-labelledby"), "dispatch-previous-title")
        await self.page.keyboard.press("Escape")
        self.assertTrue(await fleet.locator(".dispatch-pro-view-all").evaluate("el=>el===document.activeElement"))
        self.assertNotIn(("POST", "/api/decision-cases"), self.requests)

    async def test_data_pack_context_is_dark_with_native_disclosure_in_map_and_configs(self):
        audit = (Path(__file__).parent / "theme_audit.js").read_text()
        await self.page.emulate_media(reduced_motion="reduce")
        for width in (1440, 1280, 1024, 768, 390):
            await self.page.set_viewport_size({"width":width,"height":1000})
            for view, node in (("logistics-map", None), ("logistics-config", "logistics_assignment"), ("logistics-config", "logistics_scheduling")):
                await self.open(view, node)
                context = self.page.locator(".d-data-context")
                self.assertFalse(await context.evaluate("el=>el.open"))
                summary = context.locator("summary")
                await summary.focus()
                await self.page.keyboard.press("Enter")
                metrics = await self.page.evaluate(audit, ".d-data-context")
                self.assertEqual(metrics["scheme"], "dark")
                self.assertEqual(metrics["failures"], [])
                self.assertFalse(metrics["overflow"])
                copy = context.locator('button[aria-label="Copiar ID completo del caso"]')
                await copy.focus()
                self.assertEqual(await copy.evaluate("el=>getComputedStyle(el).outlineColor"), "rgb(57, 188, 192)")
                if view == "logistics-map":
                    await context.locator("[data-map-columns=orders]").click()
                    await self.page.locator(".dispatch-guide").wait_for(state="visible")
                    self.assertEqual((await self.page.evaluate(audit, ".dispatch-guide"))["failures"], [])
                    await self.page.keyboard.press("Escape")
                await summary.focus()
                await self.page.keyboard.press("Space")
                self.assertFalse(await context.evaluate("el=>el.open"))
        self.assertEqual(self.execution_bodies, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
