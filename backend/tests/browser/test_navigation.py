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
        elif path in {"/api/runs/preflight", "/api/runs/assignment-preview"}:
            data = self.f["preflight" if path.endswith("preflight") else "preview"]
        elif path == "/api/decision-cases": data = {"cases":[self.hydrated()]}
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
            if path.split("/")[-1] != self.case["id"]:
                status, data = 404, {"detail":"No se encontró el Decision Case."}
            else: data = self.hydrated()
        elif path == "/api/runs" and method == "POST":
            body = request.post_data_json
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
            rid = path.split("/")[3]
            row = self.runs[rid]
            row["approved_at"] = "2026-10-10T12:00:00+00:00"
            row["result_json"]["decision_case"].update(status="approved",approved_at=row["approved_at"])
            self.case["nodes"][row["node_id"]].update(status="approved",approved_run_id=rid,run_id=rid)
            data = row
        elif path.endswith("/interpretation"): data = {"explanation":None,"messages":[],"configured":False}
        elif path.endswith("/explain"): data = {"summary":"Synthetic explanation"}
        elif path.endswith("/chat"): data = {"answer":"Synthetic answer"}
        elif path.startswith("/api/runs/"):
            data = self.runs.get(path.split("/")[3])
            if not data or self.missing_run: status, data = 404, {"detail":"No se encontró la corrida."}
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

    async def test_malformed_saved_state(self):
        await self.page.add_init_script(f"sessionStorage.setItem('{KEY}','null');sessionStorage.setItem('dation.scheduling.config.v1','[]');")
        await self.open("logistics-config","logistics_scheduling")

    async def test_new_assignment_preserves_approval(self):
        await self.open("logistics-config","logistics_assignment")
        for select in await self.page.locator("[data-config-anomaly]").all(): await select.select_option("include")
        await self.page.locator("[data-config-review]").click()
        await self.page.locator("[data-config-execute]").click()
        await self.page.wait_for_selector(".assignment-dashboard-v2")
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
        self.assertEqual(await self.page.locator("[data-approve]").count(),0)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
