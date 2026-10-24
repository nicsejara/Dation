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
import importlib.util
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((Path(__file__).parent / "fixtures.json").read_text())
KEY = "dation.dispatch.workspace.v5"
_export_spec=importlib.util.spec_from_file_location('synthetic_export_format',ROOT/'app/platform/exports.py')
_export_module=importlib.util.module_from_spec(_export_spec);_export_spec.loader.exec_module(_export_module)
generate_export=_export_module.generate


class NavigationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        env = {**os.environ, "DATION_ACCESS_PASSWORD": "dispatch-qa",
               "PYTHONPATH": str(ROOT / "tests/browser"), "SUPABASE_URL": "", "SUPABASE_SECRET_KEY": "", "LLM_API_KEY": ""}
        cls.server = subprocess.Popen(
            [os.getenv("DATION_RUNTIME_PYTHON") or (str(ROOT.parent / ".venv/bin/python") if (ROOT.parent / ".venv/bin/python").exists() else shutil.which("python")), "-m", "uvicorn", "fixture_server:app",
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
        self.selector_failure = False
        self.comparative=None
        self.comparative_posts=0
        self.comparative_fail_once=False
        self.saved_explanation=None
        self.saved_explanation_evidence=None
        self.explain_calls=0
        self.explain_fail_once=False
        self.explain_response={"executive_summary":"Synthetic explanation","key_drivers":["Evidencia publicada"],"caveats":["La planificación temporal corresponde a D2."]}
        self.approval_calls=0
        self.approval_fail_once=False
        self.other_cases={}
        self.workflows={}
        self.execution_bodies=[]
        self.run_fetch_failures=0
        self.home_data={'recent_cases':[],'attention':{'items':[],'total':0},'activity':{'available':False,'items':[]}}
        self.home_failure=False
        self.onboarding_data=None
        self.ddas=[{'workspace_id':'00000000-0000-4000-8000-00000000da71','dda_id':'logistics','status':'enabled'}]
        self.access_role='admin'
        self.hub_rows={row['id']:copy.deepcopy(row) for row in self.f['datasets'].values()}
        self.hub_cases=[]
        self.hub_failure=False
        self.hub_validation_fail=False
        self.hub_delete_failure=False
        self.hub_incomplete=[]
        self.center_failure=False
        self.center_conflict=False
        self.center_label=None
        self.center_archived=False
        self.center_edits=0
        self.settings_failure=False
        self.settings_conflict=False
        self.workspace_settings={'workspace':{'id':'00000000-0000-4000-8000-00000000da71','name':'Synthetic workspace','country':'AR','language':'es','timezone':'UTC','currency':'ARS','weight_unit':'kg','distance_unit':'km','logistics_unit':'units','updated_at':'2026-10-19T00:00:00Z'},'ddas':self.ddas,
            'plan':{'code':'free','name':'Free','status':'active','price_amount':0,'billing_mode':'free','requires_payment_method':False,'trial_ends_at':None,'member_limit':None},'members':{'active':2,'total':3},
            'options':{'countries':['AR','CL','US'],'languages':{'es':'Español','en':'English','pt':'Português'},'timezones':['UTC','America/Santiago'],'currencies':{'ARS':'Peso argentino','CLP':'Peso chileno','USD':'Dólar estadounidense'},'weight_units':{'kg':'Kilogramos (kg)','t':'Toneladas (t)'},'distance_units':{'km':'Kilómetros (km)','mi':'Millas (mi)'},'logistics_units':{'units':'Unidades','pallets':'Pallets','cases':'Cajas'}}}
        self.pw = await async_playwright().start()
        executable = os.getenv("CHROMIUM_EXECUTABLE")
        if not executable and Path("/usr/bin/chromium").exists():
            executable = "/usr/bin/chromium"
        self.browser = await self.pw.chromium.launch(executable_path=executable, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        self.context = await self.browser.new_context(viewport={"width":1440,"height":1000},
            http_credentials={"username":"dation","password":"dispatch-qa"})
        await self.context.add_cookies([{"name":"dation_access","value":"browser-layout-fixture","url":f"http://127.0.0.1:{self.port}"}])
        async def session_fixture(route):
            import time
            await route.fulfill(content_type="application/json",body=json.dumps({
                "access_token":"browser-layout-fixture","expires_at":int(time.time())+3600,
                "profile":{"id":"10000000-0000-4000-8000-000000000001","first_name":"Synthetic","last_name":"User","email":"fixture@example.test"},
                "membership":{"workspace_id":"00000000-0000-4000-8000-00000000da71","access_role":self.access_role},
                "workspace":self.workspace_settings['workspace'],"ddas":self.ddas}))
        await self.context.route("**/auth/session",session_fixture)
        await self.context.add_init_script("sessionStorage.setItem('_dation_identity','10000000-0000-4000-8000-000000000001:00000000-0000-4000-8000-00000000da71');")
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
        if path=='/api/platform/team' and query.get('candidates')==['true']:
            await route.fulfill(json={'members':[{'user_id':'10000000-0000-4000-8000-000000000001','name':'Synthetic owner','email':'fixture@example.test'}],'total':1,'limit':25,'offset':0});return
        if '/responsibilities' in path and path.startswith('/api/platform/decisions/'):
            cid=path.split('/')[4];snapshot=self.workflows[cid]
            if method=='PUT':
                stage=snapshot['stages'][path.split('/')[-1]]
                for field in ('owner','approver'):
                    uid=request.post_data_json[field+'_user_id'];stage[field]={'id':uid,'name':'Synthetic owner','active':True,'access_role':'admin'} if uid else None;stage[field+'_eligible']=bool(uid)
                stage['updated_at']='2026-10-21T01:00:00Z'
            await route.fulfill(json=snapshot);return
        if path.endswith('/workflow-readiness'):
            await route.fulfill(json={'ready':True});return
        if path=='/api/platform/activity/exports':
            body=json.loads(request.post_data);run=self.runs.get(body['run_id'])
            name,content,media=generate_export(run,body['format'])
            await route.fulfill(status=200,headers={'Content-Disposition':'attachment; filename="'+name+'"'},content_type=media,body=content)
            return
        if path=='/api/platform/activity':
            if getattr(self,'activity_gate',None):await self.activity_gate.wait()
            await asyncio.sleep(self.delay.get(path,.01))
            await route.fulfill(status=200,content_type='application/json',body=json.dumps({'available':True,'items':[],'next_cursor':None}))
            return
        if path.startswith('/api/platform/onboarding'):
            if path.endswith('/demo'):
                if getattr(self,'onboarding_gate',None):await self.onboarding_gate.wait()
                data={'contains_demo_data':True,**{kind:{**copy.deepcopy(row),'is_sample':True} for kind,row in self.f['datasets'].items()}}
            elif path.endswith('/explore'):
                self.onboarding_data['explored_at']='2026-10-19T12:00:00Z'
                self.home_data['onboarding']=copy.deepcopy(self.onboarding_data);data=self.onboarding_data
            else:data=self.onboarding_data or {'available':False}
            await route.fulfill(status=200,content_type='application/json',body=json.dumps(data));return
        if path.startswith('/api/platform/decisions'):
            await self.route_center(route,path,query,method)
            return
        captured_evidence=self.comparative['id'] if self.comparative and self.comparative['status']=='completed' else None
        await asyncio.sleep(self.delay.get(path, .01))
        data, status = {}, 200
        if path.startswith('/api/platform/data/'):
            await self.route_hub(route,path,query,method)
            return
        if path == '/api/platform/settings':
            if method=='PATCH':status,data=(409,{'detail':'Settings changed'}) if self.settings_conflict else (403,{'detail':'Admin required'})
            else:status,data=(503,{'detail':'Settings unavailable'}) if self.settings_failure else (200,copy.deepcopy(self.workspace_settings))
        elif path == "/api/platform/home":
            status,data=(503,{'detail':'Home unavailable'}) if self.home_failure else (200,copy.deepcopy(self.home_data))
        elif path == "/api/dispatch/status":
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
            if method == 'POST':
                body=request.post_data_json
                datasets={d['id']:d for d in self.f['datasets'].values()}
                for item in self.other_cases.values():
                    datasets.update({item[k]['id']:item[k] for k in ('orders','fleet')})
                row={'id':body['id'],'status':'active','state_json':body['state'],
                     'orders_dataset_id':body['orders_dataset_id'],'fleet_dataset_id':body['fleet_dataset_id']}
                self.other_cases[body['id']]={'case':row,'decision_case':body['state'],
                    'orders':datasets[body['orders_dataset_id']],'fleet':datasets[body['fleet_dataset_id']]}
                self.workflows[body['id']]={'case_id':body['id'],'can_assign':True,'gates_enforced':True,'policy_version':1,'stages':{stage:{'owner':None,'approver':None,'owner_eligible':False,'approver_eligible':False,'updated_at':None} for stage in ('data_preparation','logistics_assignment','logistics_scheduling')}}
                self.other_cases[body['id']]['workflow_responsibilities']=self.workflows[body['id']]
                data={'case':row}
            else:
                self.selector_queries.append(query)
                items=[copy.deepcopy(self.hydrated()) for _ in range(self.selector_size)]
                for i,item in enumerate(items):
                    if i:item['case']['id']=f'00000000-0000-4000-9000-{i:012d}'
                if self.other_cases:items=([copy.deepcopy(self.hydrated())] if self.selector_size else [])+copy.deepcopy(list(self.other_cases.values()))
                items=[item for item in items if item['case'].get('status','active')==query.get('status',['active'])[0]]
                offset,limit=int(query.get('offset',['0'])[0]),int(query.get('limit',['100'])[0])
                items=items[offset:offset+limit]
                for item in items:
                    if query.get('summary') == ['true']:
                        for kind in ('orders','fleet'):
                            item[kind]={k:v for k,v in item[kind].items() if k in
                                ('id','dataset_type','canonical_filename','label','original_filename')}
                data = {"cases":items}
                if self.selector_failure:status,data=503,{'detail':'Synthetic case list unavailable'}
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
            if self.saved_explanation:data.update(explanation=self.saved_explanation,explanation_is_current=self.saved_explanation_evidence==captured_evidence)
            data['current_evidence_analysis_id']=captured_evidence
            if self.chat_history:
                offset=int(query.get('offset',['0'])[0])
                rows=self.chat_history[offset:offset+2]
                data.update(messages=list(reversed(rows)),pagination={'has_more':len(self.chat_history)>offset+2,'next_offset':offset+2})
        elif path.endswith("/explain"):
            self.explain_calls+=1
            if self.explain_fail_once and self.explain_calls==1:status,data=503,{'detail':'Fallo sintético de IA'}
            else:
                data={'explanation':copy.deepcopy(self.explain_response),'evidence_analysis_id':captured_evidence}
                self.saved_explanation={'id':'saved-summary','response_json':copy.deepcopy(self.explain_response)}
                self.saved_explanation_evidence=captured_evidence
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

    async def route_center(self,route,path,query,method):
        await asyncio.sleep(self.delay.get(path,.01))
        prefix='/api/platform/decisions';status=200
        row={'id':self.case['id'],'friendly_id':'DC-'+self.case['id'][:8].upper(),'label':self.center_label,'dda':'logistics','status':'archived' if self.center_archived else 'active','in_review':False,'current_step':'logistics_assignment','current_step_label':'Asignación de carga','progress':{'approved':0,'total':2},'owner':None,'created_by':None,'created_at':'2026-10-18T12:00:00Z','updated_at':f'2026-10-18T12:00:{self.center_edits:02d}Z','last_activity_at':'2026-10-18T12:00:00Z','resume':{'view':'logistics-config','node_id':'logistics_assignment','run_id':None}}
        nodes=[]
        for key,label,flag in [('logistics_assignment','Asignación de carga','available'),('logistics_scheduling','Planificación de despachos','locked'),('logistics_final_assignment','Asignación de vehículos','coming_soon')]:
            nodes.append({'id':key,'label':label,'status':flag,'owner':None,'approver':None,'run_count':1 if key=='logistics_assignment' else 0,'latest_run':None,'approved_run':None,'approval_current':False,'target':None if key=='logistics_final_assignment' else {'view':'logistics-config' if flag=='available' else 'logistics-map','node_id':key,'run_id':None}})
        row.update(current_objective=None,display_status=row['status'])
        detail={**row,'orders':self.f['datasets']['orders'],'fleet':self.f['datasets']['fleet'],'nodes':nodes}
        if self.center_failure:status,data=503,{'detail':'Decision Center no está disponible.'}
        elif method=='PATCH':
            if self.center_conflict:self.center_conflict=False;status,data=409,{'detail':'El caso cambió.'}
            else:
                body=json.loads(route.request.post_data);self.center_edits+=1
                if 'label' in body:self.center_label=body['label']
                if 'archived' in body:self.center_archived=body['archived']
                data={**row,'label':self.center_label,'status':'archived' if self.center_archived else 'active'}
        elif path.endswith('/runs'):
            run=self.f['runs']['assignment'];data={'items':[{**run,'created_by':None,'approved_by':None,'objective':'balanced','decision_state':'candidate'}],'total':1,'limit':25,'offset':0}
        elif path==prefix:
            term=query.get('q',[''])[0].lower();kind=query.get('filter',['all'])[0]
            match=bool(self.center_archived)==(kind=='archived') and kind not in ('completed','review') and (not term or term in (self.center_label or '').lower() or term in row['id'].lower())
            data={'items':[row] if match else [],'total':int(match),'limit':25,'offset':0,'summary':getattr(self,'center_summary',{'active_cases':int(not self.center_archived),'in_review':0,'pending_approval':0,'approved':0}),'dda_options':['logistics'],'owner_options':[]}
        else:data=detail
        await route.fulfill(status=status,content_type='application/json',body=json.dumps(data))

    async def route_hub(self,route,path,query,method):
        await asyncio.sleep(self.delay.get(path,.01))
        prefix='/api/platform/data';status=200;data={}
        def public(row):
            result={k:copy.deepcopy(v) for k,v in row.items() if k not in ('profile_json','storage_path','storage_bucket')}
            result.update(validation='validated' if (row.get('profile_json') or {}).get('valid') else 'unknown',uploaded_by=row.get('uploaded_by'),case_count=len(self.hub_cases),run_count=0,deletion_pending=row.get('deletion_pending',False))
            return result
        rows=list(self.hub_rows.values());limit=int(query.get('limit',['25'])[0]);offset=int(query.get('offset',['0'])[0])
        if self.hub_failure:status,data=503,{'detail':'La biblioteca no está disponible.'}
        elif path==prefix+'/contracts':data=self.f['contracts']
        elif path==prefix+'/datasets':
            term=query.get('q',[''])[0].lower();kind=query.get('type',['all'])[0];state=query.get('state',['active'])[0];validation=query.get('validation',['all'])[0]
            summary={'total':len(rows),'validated':sum(public(r)['validation']=='validated' for r in rows),'issues':sum(public(r)['validation']=='issues' for r in rows),'archived':sum(bool(r.get('archived_at')) for r in rows)}
            rows=[r for r in rows if (state=='all' or bool(r.get('archived_at'))==(state=='archived')) and (kind=='all' or r['dataset_type']==kind) and (validation=='all' or public(r)['validation']==validation) and (not term or term in ' '.join(str(r.get(k,'')) for k in ('label','canonical_filename','original_filename')).lower())]
            data={'items':[public(r) for r in rows[offset:offset+limit]],'total':len(rows),'summary':summary,'limit':limit,'offset':offset,'incomplete_uploads':copy.deepcopy(self.hub_incomplete)}
        elif path==prefix+'/datasets/validate':
            data={'valid':not self.hub_validation_fail,'errors':[{'message':'Revisá las columnas obligatorias.'}] if self.hub_validation_fail else [],'counts':{'errors':int(self.hub_validation_fail)}}
        elif path==prefix+'/datasets/upload':
            row=rows[0];data={'dataset':row,'duplicate':False}
        elif path.startswith(prefix+'/uploads/') and path.endswith('/discard'):
            self.hub_incomplete=[];data={'cleared':True}
        elif path.startswith(prefix+'/datasets/'):
            parts=path.removeprefix(prefix+'/datasets/').split('/');row=self.hub_rows.get(parts[0]);action=parts[1] if len(parts)>1 else None
            if not row:status,data=404,{'detail':'No se encontró el dataset.'}
            elif action=='preview':data={'columns':['order_id','product'],'rows':[[str(i),'Synthetic '+str(i)] for i in range(offset,min(offset+limit,30))],'has_more':offset+limit<30,'limit':limit,'offset':offset}
            elif action=='reuse':data={'datasets':[row]}
            elif action in ('archive','unarchive'):
                row['archived_at']='2026-10-18T12:00:00Z' if action=='archive' else None;data={'archived':action=='archive'}
            elif method=='DELETE':
                if self.hub_delete_failure:
                    self.hub_delete_failure=False;row['deletion_pending']=True;status,data=503,{'detail':'La eliminación quedó pendiente. Reintentá para completarla.'}
                else:self.hub_rows.pop(row['id']);data={'deleted':True}
            else:data={'dataset':public(row),'validation_report':row.get('profile_json') or {},'used_in':copy.deepcopy(self.hub_cases[offset:offset+limit]),'case_total':len(self.hub_cases),'can_archive':self.access_role!='viewer' and not row.get('is_default') and not row.get('deletion_pending'),'can_delete':self.access_role!='viewer' and bool(row.get('archived_at')) and not self.hub_cases,'referenced':bool(self.hub_cases)}
        elif path in (prefix+'/packs',prefix+'/pack',prefix+'/pack/reuse') and rows:
            orders=next(r for r in rows if r['dataset_type']=='orders');fleet=next(r for r in rows if r['dataset_type']=='fleet')
            pack={'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id'],'orders':public(orders),'fleet':public(fleet),'label':'Data Pack sintético','validated':True,'case_count':len(self.hub_cases),'created_at':orders['created_at']}
            data={'datasets':[orders,fleet]} if path.endswith('/reuse') else {'pack':pack,'used_in':self.hub_cases} if path.endswith('/pack') else {'items':[pack] if self.hub_cases else [],'total':int(bool(self.hub_cases))}
        elif path==prefix+'/packs':data={'items':[],'total':0}
        else:status,data=501,{'detail':'Unmocked Data Hub endpoint: '+path}
        await route.fulfill(status=status,content_type='application/json',body=json.dumps(data))

    async def open(self, view="logistics-map", node=None, run=None):
        query = f"view={view}&case_id={self.case['id']}"
        if node: query += "&node_id="+node
        if run: query += "&run_id="+run
        await self.page.goto(f"http://127.0.0.1:{self.port}/app?{query}")
        try:
            await self.page.wait_for_function("window.DationDispatch && window.DationDispatch.getWorkspace().decisionCase?.persisted")
        except Exception:
            print("UI_BOOT_DIAGNOSTIC="+json.dumps({"url":self.page.url,"errors":self.errors,"requests":self.requests,"state":await self.page.evaluate("({loading:document.documentElement.classList.contains('d-session-loading'),workspace:window.DationDispatch?.getWorkspace(),text:document.body.innerText.slice(-500)})")}))
            raise
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
        self.assertLess(order.index('dispatch-explanation'),order.index('dispatch-comparative'))
        self.assertLess(order.index('dispatch-comparative'),order.index('dispatch-review'))
        self.assertFalse(await self.page.locator('#dispatch-assignment').is_visible())
        self.assertEqual(await self.page.locator('[data-assignment-advanced-toggle]').get_attribute('aria-expanded'),'false')
        self.assertEqual(await self.page.locator('[data-flow],[data-case-flow],.dispatch-dashboard-map-back').count(),0)
        self.assertFalse(await self.page.locator('#dda-workspace-nav-shell').is_visible())

    async def test_trip_detail_is_contextual_toggleable_and_escape_restores_focus(self):
        await self.dashboard();await self.open_advanced()
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
        self.essential();await self.dashboard();await self.open_advanced();url=self.page.url
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
        self.essential();self.comparative_fail_once=True;await self.dashboard();await self.open_advanced()
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

    async def test_existing_review_continues_to_its_dashboard_without_another_configuration(self):
        await self.dashboard()
        await self.page.locator('[data-after-approve]').wait_for(state='visible')
        await self.page.locator('[data-after-approve]').click()
        await self.page.wait_for_selector('.dispatch-scheduling-dashboard')
        self.assertIn('run_id='+self.f['ids']['scheduling'],self.page.url)
        self.assertEqual(self.execution_bodies,[])

    async def test_mobile_trip_detail_has_no_document_overflow(self):
        await self.page.set_viewport_size({'width':390,'height':844});await self.dashboard();await self.open_advanced()
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
        other=self.second_case();await self.open();await self.nav('logistics-overview')
        await self.page.locator('[data-open-decision-map]').click()
        await self.page.locator('.is-current').get_by_role('button',name='Caso actual').wait_for()
        await self.page.locator('[data-open-case="'+other['case']['id']+'"]').click()
        await self.page.locator('[data-select-case]').wait_for(state='visible')
        self.assertIn('case_id='+other['case']['id'],self.page.url)
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
        self.essential();await self.dashboard();await self.open_advanced();before=copy.deepcopy(self.case)
        await self.page.locator('[data-generate-comparative]').click()
        await self.page.wait_for_function("document.querySelector('[data-comparative-state]')?.dataset.comparativeState==='queued'")
        self.comparative['status']='completed'
        await self.page.wait_for_selector('[data-comparative-state=completed]')
        artifact=copy.deepcopy(self.comparative)
        await self.page.locator('[data-assignment-advanced-toggle]').click()
        self.assertFalse(await self.page.locator('[data-comparison-kpi]').first.is_visible())
        await self.page.reload();await self.page.locator('[data-assignment-advanced-toggle]').wait_for(state='visible')
        await self.open_advanced()
        self.assertEqual(await self.page.locator('[data-comparison-kpi]').count(),6)
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
        await self.page.locator('[data-more-menu] summary').click()
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
        await self.mock_recent_case_switcher()
        other=self.second_case();await self.open()
        await self.page.locator('[data-select-case]').click();await self.page.locator('[data-case-switcher] nav').get_by_role('button',name=other['case']['id'],exact=False).wait_for(state='visible')
        await self.page.keyboard.press('Escape')
        self.assertTrue(await self.page.locator('[data-case-switcher] button').first.evaluate('(x)=>x===document.activeElement'))
        await self.page.locator('[data-select-case]').click()
        await self.page.locator('[data-case-switcher] nav').get_by_role('button',name=other['case']['id'],exact=False).click()
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
            await self.page.locator('[data-more-menu] summary').click()
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
        await self.page.locator('[data-more-menu] summary').click()
        self.assertTrue(await self.page.locator('[data-dashboard-map]').is_visible())
        await self.page.keyboard.press('Escape')
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
        await self.dashboard();await self.open_advanced()
        self.assertEqual(await self.page.locator('[data-executive-kpi]').count(),4)
        self.assertIn('$ 1.000',await self.page.locator('[data-executive-kpi=total_cost]').inner_text())
        self.assertEqual(await self.page.locator('[data-executive-kpi=avg_cost_per_trip]').count(),0)
        self.assertEqual(await self.page.locator('[data-comparison-kpi]').count(),6)
        await self.page.locator('[data-comparison-select]').select_option('min_cost')
        cost=await self.page.locator('[data-comparison-kpi=avg_cost_per_trip]').inner_text()
        self.assertIn('$ 250',cost);self.assertIn('$ 400',cost);self.assertIn('−$ 150 · −37,5 %',cost)
        self.assertIn('+7 pp',await self.page.locator('[data-comparison-kpi=load_utilization]').inner_text())
        self.assertIn('+14 pp',await self.page.locator('[data-comparison-kpi=own_weight_share]').inner_text())
        self.assertIn('peso',await self.page.locator('[data-executive-kpi=own_weight_share] p').inner_text())
        advanced=await self.page.locator('#dispatch-comparative').inner_text()
        for forbidden in ('Costo estimado','Lectura de la elección','Prioridades configuradas','Trazabilidad del análisis','corrida base','huella','Estado del solver','Objetivo original'):
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
        self.assertIn('Sin observaciones adicionales',content)
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
        self.assertEqual(await button.get_attribute('aria-busy'),'true')
        self.assertEqual(await button.evaluate("el=>getComputedStyle(el,'::after').animationName"),'d-workflow-spin')
        await button.dispatch_event('click');await self.page.locator('[data-approve-final]').dispatch_event('click')
        await self.page.wait_for_function("document.querySelector('[data-status-badge]').textContent==='Aprobada'")
        self.assertEqual(self.approval_calls,1);self.assertTrue(await button.is_visible());self.assertTrue(await button.is_disabled())
        self.assertTrue(await self.page.locator('[data-approve-final]').is_disabled())
        await self.page.locator('[data-after-approve]').wait_for(state='visible')
        self.assertEqual(self.case['nodes']['logistics_assignment']['approved_run_id'],self.f['ids']['assignment'])

    async def test_toolbar_approval_error_restores_button_and_can_retry_once(self):
        self.review_assignment();self.approval_fail_once=True;await self.dashboard()
        button=self.page.locator('[data-approve-toolbar]');await button.click()
        await self.page.locator('[data-approval-error]').wait_for(state='visible')
        self.assertFalse(await button.is_disabled());self.assertEqual(await button.inner_text(),'Aprobar decisión')
        self.assertIsNone(await button.get_attribute('aria-busy'))
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
        await self.page.locator('[data-chat]').click()
        await self.page.locator('.dispatch-chat [data-starter]').first.click()
        await self.page.wait_for_selector('.dispatch-chat textarea')
        await self.page.wait_for_timeout(150)
        self.assertEqual(sum(p.endswith('/interpretation') for _,p in self.requests)-before,1)

    async def test_refined_comparator_and_scheduling_drawer_fit_mobile_viewport(self):
        await self.page.set_viewport_size({'width':390,'height':844});await self.dashboard();await self.open_advanced()
        cards=await self.page.locator('[data-comparison-kpi]').all()
        bounds=[await card.bounding_box() for card in cards]
        self.assertEqual(len(bounds),6);self.assertTrue(all(abs(b['x']-bounds[0]['x'])<1 for b in bounds))
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        await self.page.evaluate("id=>window.DationDispatch.openRun(id,'logistics_scheduling')",self.f['ids']['scheduling'])
        await self.page.wait_for_selector('.dispatch-scheduling-dashboard')
        await self.page.locator('[data-more-menu] summary').click();await self.page.locator('[data-run-details]').click()
        bounds=await self.page.locator('[data-run-drawer]').bounding_box()
        self.assertGreaterEqual(bounds['x'],0);self.assertLessEqual(bounds['x']+bounds['width'],390)
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))

    async def test_ia_retains_and_labels_original_turn_when_comparative_finishes_mid_response(self):
        self.essential();self.saved_explanation={'id':'saved','response_json':{'executive_summary':'Explicación original'}}
        await self.dashboard();await self.open_advanced()
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
        self.assertIn('Hay nueva evidencia disponible',await self.page.locator('#dispatch-explanation').inner_text())

    async def test_case_selector_paginates_compact_active_and_completed_and_hydrates_only_selection(self):
        self.selector_size=100
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=overview')
        await self.page.wait_for_function("document.querySelector('[data-open-decision-map]')?.disabled===false")
        before=len(self.requests)
        await self.page.evaluate('window.DationDispatch.openDecisionMap()')
        await self.page.wait_for_selector('[data-open-case]')
        self.assertEqual(await self.page.locator('[data-open-case]').count(),100)
        self.assertEqual(self.selector_queries[-1].get('summary'),['true'])
        self.assertEqual(self.requests[before:],[('GET','/api/decision-cases')]*3)
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

    async def phase6_open(self,view,node=None):
        if view in ('inicio','logistics-overview','logistics-data'):
            await self.page.goto(f'http://127.0.0.1:{self.port}/app?view={view}')
            await self.page.locator('.view.is-active').wait_for()
        else:
            run=self.f['ids']['scheduling' if node=='logistics_scheduling' else 'assignment'] if view=='decision-dashboard' else None
            await self.open(view,node,run)
        # Auth now gates asynchronous module mounting. Inspect the committed AX tree
        # after the browser has painted the resolved shell and its controls.
        await self.page.wait_for_function("!document.documentElement.classList.contains('d-session-loading')")
        await self.page.evaluate("new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))")

    async def test_phase6_all_pages_have_dark_contrast_accessible_names_and_no_overflow(self):
        audit=(Path(__file__).parent/'theme_audit.js').read_text()
        await self.page.emulate_media(reduced_motion='reduce',color_scheme='light')
        session=await self.context.new_cdp_session(self.page)
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':900})
            for view,node in [('inicio',None),('logistics-overview',None),('logistics-data',None),('logistics-map',None),('logistics-config','logistics_assignment'),('logistics-config','logistics_scheduling'),('decision-dashboard','logistics_assignment'),('decision-dashboard','logistics_scheduling')]:
                await self.phase6_open(view,node)
                result=await self.page.evaluate(audit)
                self.assertEqual(result['failures'],[],(view,node,width,result['failures']))
                self.assertFalse(result['overflow']);self.assertEqual(result['scheme'],'dark');self.assertFalse(result['legacyBoundary'])
                tree=await session.send('Accessibility.getFullAXTree')
                controls=[item for item in tree['nodes'] if not item.get('ignored') and item.get('role',{}).get('value') in ('button','link','textbox','searchbox','combobox','slider','checkbox','radio','tab','progressbar')]
                self.assertTrue(controls)
                missing=[item.get('role') for item in controls if not item.get('name',{}).get('value','').strip()]
                self.assertEqual(missing,[],(view,node,width,missing,await self.page.evaluate("[...document.querySelectorAll('button,[role=button]')].filter(n=>n.getClientRects().length&&!n.textContent.trim()&&!n.getAttribute('aria-label')).map(n=>n.outerHTML.slice(0,400))")))
        self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))

    async def test_phase6_tab_and_reverse_tab_keep_focus_visible_below_sticky_layers(self):
        audit=(Path(__file__).parent/'focus_audit.js').read_text()
        await self.page.emulate_media(reduced_motion='reduce')
        for width in (1440,390):
            await self.page.set_viewport_size({'width':width,'height':900})
            for view,node in [('inicio',None),('logistics-overview',None),('logistics-data',None),('logistics-map',None),('logistics-config','logistics_assignment'),('logistics-config','logistics_scheduling'),('decision-dashboard','logistics_assignment'),('decision-dashboard','logistics_scheduling')]:
                await self.phase6_open(view,node);seen=set()
                for index in range(120):
                    await self.page.keyboard.press('Tab');state=await self.page.evaluate(audit)
                    if state.get('skip'):continue
                    if state['identity'] in seen:break
                    seen.add(state['identity'])
                    self.assertTrue(state['visibleFocus'] and state['outline']=='solid' and state['width']>=2,(view,node,width,state))
                    self.assertFalse(state['occluded'] or state['outside'],(view,node,width,state))
                self.assertTrue(seen)
                for _ in range(5):
                    await self.page.keyboard.press('Shift+Tab');state=await self.page.evaluate(audit)
                    if not state.get('skip'):self.assertFalse(state['occluded'] or state['outside'],(view,node,width,state))

    async def test_phase6_mobile_footer_grid_keeps_keyboard_focus_visible_without_scroll_or_state_changes(self):
        audit=(Path(__file__).parent/'focus_audit.js').read_text()
        await self.page.emulate_media(reduced_motion='reduce')
        for width in (360,390):
            await self.page.set_viewport_size({'width':width,'height':844})
            for node in ('logistics_assignment','logistics_scheduling'):
                await self.open('logistics-config',node)
                await self.page.keyboard.press('Tab')
                chips=self.page.locator('.d-workflow-action-bar__chip');self.assertEqual(await chips.count(),3)
                await chips.first.focus()
                for index,key in ((0,None),(1,'Tab'),(2,'Tab'),(1,'Shift+Tab'),(0,'Shift+Tab')):
                    if key:await self.page.keyboard.press(key)
                    self.assertTrue(await chips.nth(index).evaluate('el=>el===document.activeElement'))
                    focus=await self.page.evaluate(audit)
                    self.assertTrue(focus['visibleFocus'] and focus['outline']=='solid' and focus['width']>=2,(width,node,focus))
                    self.assertFalse(focus['outside'] or focus['occluded'],(width,node,focus))
                    fit=await chips.nth(index).evaluate('''el=>{
                      const r=el.getBoundingClientRect(),bar=el.closest('.d-workflow-action-bar').getBoundingClientRect();
                      const style=getComputedStyle(el),ring=parseFloat(style.outlineWidth)+parseFloat(style.outlineOffset);
                      const grid=el.parentElement;
                      return r.left-ring>=bar.left&&r.right+ring<=bar.right&&r.top-ring>=bar.top&&r.bottom+ring<=bar.bottom
                        &&grid.scrollLeft===0&&grid.scrollWidth<=grid.clientWidth
                        &&document.documentElement.scrollWidth<=innerWidth;
                    }''')
                    self.assertTrue(fit,(width,node,index))
                state=await self.page.evaluate('window.DationDispatch.getWorkspace()')
                await chips.first.press('Enter');await chips.nth(2).press('Space')
                self.assertEqual((await self.page.evaluate('window.DationDispatch.getWorkspace()'))['resourceMode'],state['resourceMode'])
        self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))

    async def test_phase6_native_search_number_checkbox_range_and_autofill_keep_dark_roles(self):
        await self.page.emulate_media(reduced_motion='reduce')
        await self.open('logistics-config','logistics_assignment')
        await self.page.locator('[data-objective=custom]').click()
        slider=self.page.locator('[data-custom-weight]:not(:disabled)').first
        await slider.focus();before=await slider.input_value();await slider.press('ArrowRight')
        self.assertNotEqual(await slider.input_value(),before)
        await self.page.locator('[data-filter-dialog-open]').click()
        search=self.page.locator('[data-filter-field-search]');await search.fill('dest')
        session=await self.context.new_cdp_session(self.page);await session.send('DOM.enable');await session.send('CSS.enable')
        document=await session.send('DOM.getDocument');node=await session.send('DOM.querySelector',{'nodeId':document['root']['nodeId'],'selector':'[data-filter-field-search]'})
        await session.send('CSS.forcePseudoState',{'nodeId':node['nodeId'],'forcedPseudoClasses':['autofill']})
        style=await search.evaluate('el=>({autofill:el.matches(":autofill"),fill:getComputedStyle(el).webkitTextFillColor,shadow:getComputedStyle(el).boxShadow,scheme:getComputedStyle(el).colorScheme,value:el.value})')
        self.assertTrue(style['autofill']);self.assertEqual(style['fill'],'rgb(243, 248, 250)');self.assertIn('inset',style['shadow']);self.assertEqual(style['scheme'],'dark');self.assertEqual(style['value'],'dest')
        await session.send('CSS.forcePseudoState',{'nodeId':node['nodeId'],'forcedPseudoClasses':[]})
        await self.page.locator('[data-filter-add=destination]').click()
        checkbox=self.page.locator('[data-filter-category]').first;await checkbox.focus();before=await checkbox.is_checked();await checkbox.press('Space')
        self.assertNotEqual(await self.page.locator('[data-filter-category]').first.is_checked(),before)
        await self.page.locator('[data-filter-dialog-open]').click();await self.page.locator('[data-filter-add=quantity_units]').click()
        number=self.page.locator('[data-filter-number-min]');await number.fill('-1')
        self.assertFalse(await number.evaluate('el=>el.checkValidity()'))
        await number.hover();await number.focus()
        audit=await self.page.evaluate((Path(__file__).parent/'theme_audit.js').read_text())
        self.assertEqual(audit['failures'],[])
        self.assertEqual(await self.page.locator('.decision-advanced-option:disabled').count(),3)
        self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))

    async def test_phase6_native_date_picker_and_select_preserve_the_scheduling_contract(self):
        await self.page.emulate_media(reduced_motion='reduce')
        await self.open('logistics-config','logistics_scheduling')
        await self.page.locator('[data-scheduling-window-mode=custom]').click()
        field=self.page.locator('[data-scheduling-window-start]');await field.fill('2026-10-01');await field.focus()
        result=await field.evaluate('el=>{el.showPicker();return {scheme:getComputedStyle(el).colorScheme,indicator:getComputedStyle(el,"::-webkit-calendar-picker-indicator").opacity,value:el.value};}')
        self.assertEqual(result['scheme'],'dark');self.assertNotEqual(result['indicator'],'0');self.assertEqual(result['value'],'2026-10-01')
        await self.page.keyboard.press('Escape')
        await self.page.locator('[data-scheduling-window-end]').fill('2026-09-30')
        await self.page.locator('[data-scheduling-window-end]').blur()
        await self.page.locator('[data-scheduling-review]').click()
        self.assertIn('anterior',await self.page.locator('.view.is-active').inner_text())
        await self.page.locator('[data-scheduling-window-end]').fill('2026-10-10')
        await self.page.locator('[data-scheduling-window-end]').blur()
        selects=self.page.locator('select[data-config-anomaly]')
        for el in await selects.all():await el.select_option('include')
        await self.page.locator('[data-scheduling-review]').click();await self.page.locator('dialog[open]').wait_for()
        self.assertNotIn('Profundidad',await self.page.locator('dialog[open]').inner_text())
        await self.page.keyboard.press('Escape')
        self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))

    async def test_phase6_reduced_motion_updates_real_chart_and_cleans_up_on_departure(self):
        await self.page.emulate_media(reduced_motion='reduce')
        await self.open('decision-dashboard','logistics_scheduling',self.f['ids']['scheduling'])
        await self.page.locator('[data-scheduling-advanced-toggle]').click()
        await self.page.evaluate('window.__qaChart=window.DationCharts.getInstanceByDom(document.querySelector(".dispatch-schedule-chart"))')
        self.assertFalse(await self.page.evaluate('window.__qaChart.getOption().animation'))
        self.assertEqual(await self.page.evaluate('getComputedStyle(document.documentElement).scrollBehavior'),'auto')
        await self.page.emulate_media(reduced_motion='no-preference')
        await self.page.wait_for_function('window.__qaChart.getOption().animation===true')
        await self.page.emulate_media(reduced_motion='reduce')
        await self.page.wait_for_function('window.__qaChart.getOption().animation===false')
        await self.nav('logistics-map');await self.page.locator('[data-map-node=logistics_assignment]').first.wait_for()
        self.assertTrue(await self.page.evaluate('window.__qaChart.isDisposed()'))
        await self.page.emulate_media(reduced_motion='no-preference')
        self.assertEqual(self.errors,[])

    async def test_phase6_reflow_at_200_and_400_percent_keeps_pages_dialog_and_chat_reachable(self):
        audit=(Path(__file__).parent/'theme_audit.js').read_text();focus=(Path(__file__).parent/'focus_audit.js').read_text()
        await self.page.emulate_media(reduced_motion='reduce')
        session=await self.context.new_cdp_session(self.page)
        for zoom in (2,4):
            await session.send('Emulation.setDeviceMetricsOverride',{'width':1440//zoom,'height':1000//zoom,'deviceScaleFactor':zoom,'mobile':False})
            self.assertEqual(await self.page.evaluate('devicePixelRatio'),zoom)
            for view,node in [('inicio',None),('logistics-overview',None),('logistics-data',None),('logistics-map',None),('logistics-config','logistics_assignment'),('logistics-config','logistics_scheduling'),('decision-dashboard','logistics_assignment'),('decision-dashboard','logistics_scheduling')]:
                await self.phase6_open(view,node);result=await self.page.evaluate(audit)
                self.assertFalse(result['overflow'],(zoom,view,node));self.assertEqual(result['failures'],[],(zoom,view,node,result['failures']))
                if view=='logistics-config':
                    await self.page.locator('[data-scheduling-review]' if node=='logistics_scheduling' else '[data-config-review]').focus()
                    self.assertFalse((await self.page.evaluate(focus))['occluded'])
                if view=='decision-dashboard':
                    await self.page.locator('[data-chat]').click()
                    field=self.page.locator('.dispatch-chat textarea');await field.focus();await self.page.keyboard.press('Tab')
                    result=await self.page.evaluate(focus);self.assertFalse(result['occluded'] or result['outside'],(zoom,node,result))
                    await self.page.keyboard.press('Escape')
        await session.send('Emulation.clearDeviceMetricsOverride')

    async def test_phase6_chat_composer_and_modal_keyboard_remain_visible_on_mobile(self):
        await self.page.emulate_media(reduced_motion='reduce');await self.page.set_viewport_size({'width':390,'height':844})
        focus=(Path(__file__).parent/'focus_audit.js').read_text()
        for kind in ('assignment','scheduling'):
            await self.open('decision-dashboard','logistics_'+kind,self.f['ids'][kind]);await self.page.locator('[data-chat]').click()
            await self.page.locator('.dispatch-chat textarea').focus()
            state=await self.page.evaluate(focus);self.assertFalse(state['occluded'] or state['outside'],(kind,state))
            await self.page.keyboard.press('Tab');state=await self.page.evaluate(focus);self.assertFalse(state['occluded'] or state['outside'],(kind,state))
            await self.page.keyboard.press('Escape');self.assertTrue(await self.page.locator('[data-chat]').evaluate('el=>el===document.activeElement'))
            more=self.page.locator('[data-more-menu] summary');await more.focus();await more.press('Space');await self.page.locator('[data-run-details]').click()
            drawer=self.page.locator('[data-run-drawer]');await self.page.keyboard.press('Shift+Tab');self.assertTrue(await drawer.evaluate('el=>el.contains(document.activeElement)'))
            await self.page.keyboard.press('Tab');self.assertTrue(await drawer.evaluate('el=>el.contains(document.activeElement)'))
            await self.page.keyboard.press('Escape');self.assertTrue(await more.evaluate('el=>el===document.activeElement'))
        await self.open('logistics-config','logistics_assignment');trigger=self.page.locator('[data-filter-dialog-open]');await trigger.focus();await trigger.press('Enter')
        dialog=self.page.locator('dialog[open]');await self.page.keyboard.press('Shift+Tab');self.assertTrue(await dialog.evaluate('el=>el.contains(document.activeElement)'))
        await self.page.keyboard.press('Escape');await self.page.wait_for_function("document.activeElement?.hasAttribute('data-filter-dialog-open')")

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
                await export.click();await more.click()
                self.assertEqual(await more.get_attribute('aria-expanded'),'true')
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
        await self.page.locator('.dispatch-decision-node').first.wait_for(state='visible')
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
        await self.page.locator('[data-scheduling-advanced-toggle]').click()
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
        await self.dashboard();await self.open_advanced();audit=(Path(__file__).parent/'theme_audit.js').read_text()
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
        await self.page.wait_for_selector('[data-comparative-state=completed]')
        self.assertEqual((await self.page.evaluate(audit,'#dispatch-comparative'))['failures'],[])
        artifact=copy.deepcopy(self.comparative)
        await self.page.locator('[data-assignment-advanced-toggle]').click();await self.open_advanced()
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
                  return {last:last.bottom,bar:bar.top,barBottom:bar.bottom,viewport:innerHeight};
                }''')
                self.assertLessEqual(geometry['last'],geometry['bar']+1)
                self.assertLessEqual(geometry['barBottom'],geometry['viewport']+1)
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

    async def test_bfcache_denied_session_hides_private_content_and_offers_recovery(self):
        await self.open()
        async def denied(route):
            await route.fulfill(status=403,content_type="application/json",body=json.dumps({"detail":"Tu acceso al workspace fue deshabilitado."}))
        await self.context.route("**/auth/session",denied)
        await self.page.evaluate("dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
        await self.page.get_by_role('heading',name='No se pudo abrir el workspace').wait_for()
        self.assertTrue(await self.page.locator('.app-shell').evaluate('node=>node.hidden'))
        self.assertFalse(await self.page.evaluate("document.documentElement.classList.contains('d-session-loading')"))
        self.assertTrue(await self.page.get_by_role('button',name='Reintentar',exact=True).is_visible())
        self.assertTrue(await self.page.get_by_role('button',name='Cerrar sesión',exact=True).is_visible())
        self.assertEqual(await self.page.locator('[data-session-error]').count(),1)

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


    async def test_home_overview_dark_contrast_and_responsive_actions(self):
        audit = (Path(__file__).parent / "theme_audit.js").read_text()
        await self.page.emulate_media(reduced_motion="reduce", color_scheme="light")
        for width in (1440, 1280, 1024, 768, 390):
            await self.page.set_viewport_size({"width": width, "height": 844})
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
                    if view == "logistics-overview":
                        self.assertEqual(await self.page.locator(".dda-landing__final").count(), 0)
                        actions = self.page.locator(".dda-landing__hero-actions button")
                        self.assertEqual(await actions.count(), 2)
                        if width == 390:
                            boxes = [await actions.nth(i).bounding_box() for i in range(2)]
                            self.assertLess(boxes[1]["y"] + boxes[1]["height"], 844)
                            self.assertGreaterEqual(boxes[1]["y"], boxes[0]["y"] + boxes[0]["height"])
                            self.assertAlmostEqual(boxes[0]["width"], boxes[1]["width"], delta=1)
        self.assertEqual(self.execution_bodies, [])

    async def test_home_catalog_filters_preserve_navigation_and_workspace(self):
        await self.open('logistics-map')
        await self.nav('inicio')
        await self.page.locator('[data-dda-filter=all]').wait_for()
        await self.page.wait_for_load_state('networkidle')
        root=self.page.locator('[data-home-dda-catalog]')
        self.assertEqual(await root.locator('[data-dda-id]').count(),7)
        self.assertEqual(await root.locator('[data-dda-status=available]').count(),1)
        self.assertEqual(await root.locator('[data-dda-status=coming-soon]').count(),6)
        self.assertEqual(await root.locator('[data-dda-counts]').inner_text(),'1 disponible · 6 próximos')
        before=await self.page.evaluate('JSON.stringify(window.DationDispatch.getWorkspace())')
        await self.page.evaluate("window.__homeButton=document.getElementById('home-open-logistics')")
        requests=len(self.requests)
        expected={'all':['logistics','production','inventory','demand','procurement','maintenance','pricing'],
            'supply-chain':['logistics','inventory'],'production':['production'],'operations':['procurement'],
            'commercial':['demand','pricing'],'assets':['maintenance']}
        for category,ids in expected.items():
            button=root.locator('[data-dda-filter="'+category+'"]')
            await button.focus();await self.page.keyboard.press('Enter')
            self.assertEqual(await button.get_attribute('aria-pressed'),'true')
            self.assertEqual(await root.locator('[data-dda-filter][aria-pressed=true]').count(),1)
            self.assertEqual(await root.locator('[data-dda-id]:not([hidden])').evaluate_all('els=>els.map(el=>el.dataset.ddaId)'),ids)
            self.assertIn(str(len(ids)),await root.locator('[data-dda-filter-status]').inner_text())
        await root.locator('[data-dda-filter=all]').click()
        await self.page.evaluate('''async()=>{
            const {mountHomeCatalog}=await import('/static/js/home-dda-catalog.mjs');
            const root=document.querySelector('[data-home-dda-catalog]');mountHomeCatalog(root);mountHomeCatalog(root);
        }''')
        self.assertTrue(await self.page.evaluate("window.__homeButton===document.getElementById('home-open-logistics')"))
        self.assertEqual(await root.locator('[data-dda-filter]').count(),6)
        for card in await root.locator('[data-dda-status=coming-soon]').all():
            self.assertEqual(await card.locator('button,a,[tabindex]').count(),0)
            url=self.page.url;await card.click()
            self.assertEqual(self.page.url,url)
        self.assertEqual(await self.page.evaluate('JSON.stringify(window.DationDispatch.getWorkspace())'),before)
        self.assertEqual(self.requests[requests:],[],'Filtering the catalog must not call APIs')
        await self.page.evaluate('''()=>{
            window.__homeNavigation=[];const navigate=window.dationNavigate;
            window.dationNavigate=(...args)=>{window.__homeNavigation.push(args.slice(0,2));return navigate(...args);};
        }''')
        # The stretched semantic button makes the entire available card actionable.
        await root.locator('[data-dda-id=logistics]').click(position={'x':16,'y':16})
        await self.page.locator('.dda-landing__hero').wait_for()
        self.assertEqual(await self.page.evaluate('window.__homeNavigation'),[['logistics-overview','dda']])
        self.assertEqual(self.execution_bodies,[])

    async def test_home_catalog_responsive_accessible_and_honest_states(self):
        theme=(Path(__file__).parent/'theme_audit.js').read_text()
        focus=(Path(__file__).parent/'focus_audit.js').read_text()
        await self.page.emulate_media(reduced_motion='reduce')
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=inicio')
        await self.page.locator('[data-dda-filter=all]').wait_for()
        root=self.page.locator('[data-home-dda-catalog]')
        for width,height in ((1680,1050),(1440,1000),(1280,1000),(1024,1000),(768,1000),(699,1000),(390,844),(360,250),(320,568),(320,256),(568,320)):
            await self.page.set_viewport_size({'width':width,'height':height})
            # Every selection keeps complete labels, stable target heights and local reflow.
            pill_height=None
            for category in ('all','supply-chain','operations','production','commercial','assets'):
                await root.locator('[data-dda-filter='+category+']').evaluate('el=>el.click()')
                pills=await root.locator('[data-dda-filter]').evaluate_all('''els=>els.map(el=>{
                    const r=el.getBoundingClientRect(),s=getComputedStyle(el),p=el.parentElement.getBoundingClientRect();
                    return {x:r.x,right:r.right,y:r.y,width:r.width,height:r.height,left:p.x,end:p.right,
                        overflow:el.scrollWidth>el.clientWidth+1,radius:parseFloat(s.borderRadius)};})''')
                self.assertLess(max(p['height'] for p in pills)-min(p['height'] for p in pills),1,(width,category,pills))
                if pill_height is None:pill_height=pills[0]['height']
                self.assertAlmostEqual(pills[0]['height'],pill_height,delta=1,msg=(width,category,pills))
                for pill in pills:
                    peers=[p for p in pills if abs(p['y']-pill['y'])<1]
                    self.assertGreaterEqual(pill['x'],pill['left']-1)
                    self.assertLessEqual(pill['right'],pill['end']+1)
                    self.assertGreaterEqual(pill['height'],40)
                    self.assertFalse(pill['overflow'],(width,category,pills))
            await root.locator('[data-dda-filter=all]').evaluate('el=>el.click()')
            audit=await self.page.evaluate(theme)
            self.assertFalse(audit['overflow'],(width,audit));self.assertEqual(audit['failures'],[],width)
            rows=await root.locator('.d-home__asset').evaluate_all('''els=>els.map(el=>{
                const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};})''')
            for row in rows:
                peers=[peer for peer in rows if abs(peer['y']-row['y'])<1]
                self.assertLess(max(peer['height'] for peer in peers)-min(peer['height'] for peer in peers),1)
            columns=await root.locator('.d-home__asset-grid').evaluate('el=>getComputedStyle(el).gridTemplateColumns.split(" ").length')
            self.assertEqual(columns,1 if width<=620 else 2 if width<=1100 else 3)
            production=root.locator('.d-home__production-icon')
            icon=await production.evaluate('el=>({color:getComputedStyle(el).backgroundColor,mask:getComputedStyle(el).maskImage,filter:getComputedStyle(el).filter})')
            self.assertIn('/static/assets/dda-production.svg',icon['mask'])
            self.assertEqual(icon['filter'],'none')
            for other in await root.locator('.d-home__asset--coming-soon .d-home__asset-icon svg').all():
                self.assertEqual(icon['color'],await other.evaluate('el=>getComputedStyle(el).stroke'))
            for button in await root.locator('[data-dda-filter],#home-open-logistics').all():
                await button.focus()
                self.assertEqual(await button.evaluate('el=>getComputedStyle(el).outlineWidth'),'3px')
            await root.locator('[data-dda-filter=all]').focus()
            for key in ['Tab']*15+['Shift+Tab']*15:
                await self.page.keyboard.press(key)
                probe=await self.page.evaluate(focus)
                if not probe.get('skip'):
                    self.assertTrue(probe['visibleFocus'],(width,height,probe))
                    self.assertFalse(probe['occluded'] or probe['outside'],(width,height,probe))
        await self.page.set_viewport_size({'width':1440,'height':1000})
        await self.page.emulate_media(reduced_motion='no-preference')
        await self.page.mouse.move(0,0)
        available=root.locator('[data-dda-id=logistics]');upcoming=root.locator('[data-dda-id=production]')
        initial=await available.evaluate('el=>getComputedStyle(el).borderColor')
        await available.hover();await self.page.wait_for_timeout(250)
        hover=await available.evaluate('el=>({border:getComputedStyle(el).borderColor,transform:getComputedStyle(el).transform})')
        self.assertNotEqual(hover['border'],initial);self.assertEqual(hover['transform'],'none')
        await upcoming.hover()
        self.assertEqual(await upcoming.evaluate('el=>getComputedStyle(el).transform'),'none')
        self.assertEqual(await upcoming.evaluate('el=>getComputedStyle(el).cursor'),'default')
        self.assertEqual(await upcoming.evaluate('el=>getComputedStyle(el).opacity'),'1')
        await self.page.emulate_media(reduced_motion='reduce');await available.hover()
        self.assertEqual(await available.evaluate('el=>getComputedStyle(el).transform'),'none')

        # Normal motion may animate native scrolling; verify the settled target too.
        await self.page.emulate_media(reduced_motion='no-preference')
        await self.page.set_viewport_size({'width':390,'height':844})
        await root.locator('[data-dda-filter=all]').focus()
        settled='()=>{const p=('+focus+')();return p.skip||(!p.occluded&&!p.outside);}'
        await self.page.wait_for_function(settled)
        for key in ['Tab']*8+['Shift+Tab']*8:
            await self.page.keyboard.press(key)
            await self.page.wait_for_function(settled)

    async def test_home_catalog_keeps_a_usable_fallback_without_its_module(self):
        await self.context.route('**/home-dda-catalog.mjs',lambda route:route.abort())
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=inicio')
        fallback=self.page.locator('#home-open-logistics');await fallback.wait_for()
        self.assertEqual(await self.page.locator('.d-home__asset--available').count(),1)
        self.assertEqual(await self.page.locator('[data-dda-filters]').is_visible(),False)
        await fallback.click()
        await self.page.locator('.dda-landing__hero').wait_for()
        self.assertEqual(await self.page.evaluate('window.dationGetCurrentView()'),'logistics-overview')
        await self.nav('settings')
        settings=self.page.locator('[data-workspace-settings]')
        await settings.get_by_label('Nombre del workspace').wait_for()
        await settings.get_by_role('tab',name='Decision Data Assets',exact=True).click()
        await settings.get_by_role('heading',name='Decision Data Assets',exact=True).wait_for()
        self.assertEqual(await settings.locator('dt').count(),7)
        self.assertEqual(await settings.get_by_text('Próximamente',exact=True).count(),6)
        await settings.get_by_role('tab',name='Plan y facturación',exact=True).click()
        await settings.get_by_role('heading',name='Plan Free',exact=True).wait_for()
        self.assertTrue(await self.page.locator('.app-shell').is_visible())

    async def test_dashboard_toolbars_share_controls_and_symmetric_bleed(self):
        theme=(Path(__file__).parent/'theme_audit.js').read_text()
        for width,height in ((1680,1050),(1440,1000),(1280,1000),(1024,1000),(768,1000),(390,844),(320,568),(568,320)):
            await self.page.set_viewport_size({'width':width,'height':height})
            reference=None
            for kind in ('assignment','scheduling'):
                await self.open('decision-dashboard','logistics_'+kind,self.f['ids'][kind])
                toolbar=self.page.locator('[data-dashboard-toolbar]')
                sizes=await toolbar.evaluate('''el=>{
                    const root=el.closest('.d-decision-dashboard'),main=root.querySelector('main'),r=el.getBoundingClientRect(),m=main.getBoundingClientRect(),h=el.closest('#dispatch-hero')?.getBoundingClientRect();
                    const tools=[...el.querySelectorAll(el.dataset.toolbarPlacement==='hero'?'.dashboard-toolbar__menu>summary':'[data-dashboard-map],.dashboard-toolbar__menu>summary')].filter(button=>button.getClientRects().length).map(button=>{
                        const b=button.getBoundingClientRect(),s=getComputedStyle(button);
                        return {width:b.width,height:b.height,padding:s.padding,radius:s.borderRadius,fontSize:s.fontSize,
                            fontWeight:s.fontWeight,lineHeight:s.lineHeight,gap:s.gap,icon:button.querySelector('svg').getBoundingClientRect().width};});
                    return {width:r.width,content:m.width,left:m.x-r.x,right:r.right-m.right,tools,insideHero:h?r.left>=h.left&&r.right<=h.right:false,position:getComputedStyle(el).position};
                }''')
                expected=24 if width>1100 else 12 if width>760 else 0
                self.assertTrue(sizes['insideHero']);self.assertEqual(sizes['position'],'relative')
                self.assertEqual(len(sizes['tools']),2)
                for tool in sizes['tools'][1:]:
                    for key in ('width','height'):self.assertAlmostEqual(tool[key],sizes['tools'][0][key],delta=.25)
                    self.assertEqual({k:v for k,v in tool.items() if k not in ('width','height')},
                        {k:v for k,v in sizes['tools'][0].items() if k not in ('width','height')})
                audit=await self.page.evaluate(theme)
                self.assertFalse(audit['overflow']);self.assertEqual(audit['failures'],[])
                for menu in ('export','more'):
                    summary=toolbar.locator('[data-'+menu+'-menu]>summary')
                    await summary.click()
                    panel=toolbar.locator('[data-'+menu+'-menu] .dashboard-toolbar__menu-panel')
                    box=await panel.bounding_box()
                    self.assertGreaterEqual(box['x'],15.5);self.assertLessEqual(box['x']+box['width'],width-15.5)
                    self.assertGreaterEqual(box['y'],0);self.assertLessEqual(box['y']+box['height'],height)
                    self.assertEqual(await summary.get_attribute('aria-expanded'),'true')
                    await self.page.keyboard.press('Escape')
                    self.assertEqual(await summary.get_attribute('aria-expanded'),'false')
                    self.assertTrue(await summary.evaluate('el=>el===document.activeElement'))
        self.assertEqual(self.execution_bodies,[])


    async def test_home_card_keyboard_and_informational_overview_with_native_faq(self):
        await self.page.emulate_media(reduced_motion="reduce")
        await self.page.goto(f"http://127.0.0.1:{self.port}/app?view=inicio")
        active = self.page.locator("#home-open-logistics")
        await active.wait_for(state="visible")
        inactive = self.page.locator(".d-home__asset--coming-soon")
        self.assertEqual(await inactive.count(), 6)
        for card in await inactive.all():
            self.assertEqual(await card.get_attribute("aria-disabled"), "true")
            self.assertEqual(await card.evaluate("el=>el.tagName"), "ARTICLE")
            self.assertEqual(await card.locator("button,a,[tabindex]").count(), 0)
            self.assertEqual(await card.evaluate("el=>getComputedStyle(el).opacity"), "1")
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

    async def assign_data_responsible(self):
        root=self.page.locator('[data-workflow-responsibility=data_preparation]')
        await root.get_by_role('button',name='Seleccionar responsable',exact=True).click()
        await root.get_by_label('Responsable de datos',exact=True).select_option('10000000-0000-4000-8000-000000000001')
        await root.get_by_role('button',name='Guardar',exact=True).click()
        await root.get_by_role('button',name='Cambiar',exact=True).wait_for()

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
                    await self.page.locator('[data-workflow-responsibility]').wait_for()
                    self.assertTrue(await bar.locator('button').is_disabled())
                    await self.assign_data_responsible()
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
            self.assertGreaterEqual(self.requests.count(("POST", "/api/decision-cases")),1)
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
        await self.assign_data_responsible()
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
        self.assertEqual(self.requests.count(("POST", "/api/decision-cases")),1)

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


    async def test_phase7_library_and_settings_share_the_dark_roles(self):
        audit=(Path(__file__).parent/'theme_audit.js').read_text()
        await self.page.emulate_media(reduced_motion='reduce',color_scheme='light')
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            for view in ('traceability','settings'):
                await self.page.goto(f'http://127.0.0.1:{self.port}/app?view={view}',wait_until='networkidle')
                if view=='traceability':
                    await self.page.locator('#datasets-table-body tr').first.wait_for(state='visible')
                    for tab in ('datasets','history','evidence'):
                        button=self.page.locator('[data-trace-tab='+tab+']')
                        await button.focus();await self.page.keyboard.press('Enter')
                        self.assertTrue(await self.page.locator('[data-trace-panel='+tab+']').evaluate("el=>el.classList.contains('is-active')"))
                        await self.page.locator('[data-trace-panel='+tab+']').wait_for(state='visible')
                        self.assertEqual(await self.page.locator('[data-trace-panel='+tab+']').evaluate('el=>getComputedStyle(el).animationName'),'none')
                        result=await self.page.evaluate(audit)
                        self.assertEqual(result['failures'],[],(width,tab,result))
                    await self.page.evaluate("async run=>{const ui=await import('/static/js/ui.js');ui.renderTechnicalEvidence(run);}",self.f['runs']['assignment'])
                    self.assertTrue(await self.page.locator('#configuration-json').inner_text())
                    self.assertEqual(await self.page.locator('#runs-table-body [data-open-run]').count(),2)
                else:
                    self.assertNotEqual(await self.page.locator('#settings-ai-status').inner_text(),'Verificando…')
                result=await self.page.evaluate(audit)
                self.assertEqual(result['failures'],[],(width,view,result))
                self.assertFalse(result['overflow']);self.assertFalse(result['legacyBoundary'])
                self.assertEqual(result['scheme'],'dark')
            await self.page.evaluate("window.dationNavigate('library')")
            await self.page.locator('[data-view-panel=traceability].is-active').wait_for(state='visible')
        self.assertEqual(await self.page.locator('link[href*=dation-legacy-surfaces]').count(),0)
        self.assertEqual(self.execution_bodies,[])

    async def test_phase7_map_styles_retry_and_remain_shared_with_config_and_filters(self):
        calls=[]
        async def sheet(route):
            calls.append(route.request.url)
            if len(calls)==1:await route.abort('failed')
            else:await route.continue_()
        await self.context.route('**/static/css/decision-map-case-v2.css*',sheet)
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=logistics-map&case_id={self.case["id"]}',wait_until='domcontentloaded')
        await self.page.get_by_role('button',name='Reintentar',exact=True).click()
        await self.page.locator('[data-select-case]').wait_for(state='visible')
        for view,node in [('logistics-config','logistics_scheduling'),('logistics-config','logistics_assignment'),('logistics-map',None),('logistics-config','logistics_assignment')]:
            await self.page.evaluate('args=>window.DationDispatch.openCase(...args)',[self.case['id'],view,node])
            ready='[data-select-case]' if view=='logistics-map' else '[data-scheduling-review]' if node=='logistics_scheduling' else '[data-config-review]'
            await self.page.locator(ready).wait_for(state='visible')
        await self.page.locator('[data-filter-dialog-open]').click()
        await self.page.locator('[data-filter-add=destination]').click()
        await self.page.locator('[data-filter-category]').first.check()
        row=self.page.locator('.assignment-filter-row.is-collapsible').first
        toggle=row.locator('[data-filter-collapse-toggle]')
        await toggle.click()
        self.assertEqual(await toggle.get_attribute('aria-expanded'),'false')
        self.assertTrue(await row.locator('.assignment-filter-row__summary').is_visible())
        self.assertFalse(await row.locator('.assignment-filter-options').is_visible())
        await toggle.focus();await self.page.keyboard.press('Enter')
        self.assertTrue(await row.locator('.assignment-filter-options').is_visible())
        self.assertEqual(len(calls),2,'Only failed load and successful retry; warm routes reuse the sheet')
        self.assertEqual(await self.page.locator('link[href*="/static/css/decision-map-case-v2.css"]').count(),1)
        self.assertEqual(await self.page.locator('#assignment-filter-collapse-styles').count(),0)
        result=await self.page.evaluate((Path(__file__).parent/'theme_audit.js').read_text())
        self.assertEqual(result['failures'],[]);self.assertFalse(result['overflow'])
        self.assertEqual(self.execution_bodies,[])

    async def test_phase7_delayed_map_styles_do_not_restore_an_abandoned_route(self):
        requested,release=asyncio.Event(),asyncio.Event()
        async def slow_sheet(route):
            requested.set();await release.wait();await route.continue_()
        await self.context.route('**/static/css/decision-map-case-v2.css*',slow_sheet)
        try:
            await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=logistics-map&case_id={self.case["id"]}',wait_until='domcontentloaded')
            await asyncio.wait_for(requested.wait(),6)
            await self.nav('logistics-overview')
        finally:release.set()
        await self.page.locator('[data-start-new-decision]').wait_for(state='visible')
        await self.page.wait_for_load_state('networkidle')
        self.assertEqual(await self.page.locator('.view.is-active').get_attribute('data-view-panel'),'logistics-overview')
        self.assertEqual(await self.page.locator('#dispatch-map-root [data-select-case]').count(),0)
        self.assertEqual(self.execution_bodies,[])


    async def mock_recent_case_switcher(self):
        async def recent(route):
            if self.selector_failure:
                await route.fulfill(status=503,json={'detail':'No pudimos cargar los casos.'});return
            bundles=[self.hydrated(),*self.other_cases.values()]
            rows=[{'id':item['case']['id'],'label':'Caso '+item['case']['id'],'dda':'logistics','status':item['case'].get('status','active')} for item in bundles]
            await route.fulfill(json={'items':rows[:8],'total':len(rows)})
        await self.context.route('**/api/platform/decisions?**',recent)

    async def test_case_ux_single_current_picker_never_navigates_and_restores_keyboard_focus(self):
        await self.mock_recent_case_switcher()
        await self.open()
        url=self.page.url
        before=len(self.requests)
        await self.page.evaluate('''()=>{window.__caseCalls=[];const original=window.DationDispatch.openCase;
          window.DationDispatch.openCase=(...args)=>{window.__caseCalls.push(args);return original(...args);};}''')
        trigger=self.page.locator('[data-select-case]')
        await trigger.focus();await self.page.keyboard.press('Enter')
        dialog=self.page.locator('[data-case-switcher] nav')
        await dialog.get_by_role('button',name='Abrir este caso en Decision Center').wait_for()
        self.assertEqual(await dialog.locator('[aria-current=true]').count(),1)
        await dialog.locator('[aria-current=true]').click()
        self.assertTrue(await dialog.is_hidden())
        await self.page.locator('[data-case-switcher] button').first.click()
        await dialog.get_by_role('button',name='Abrir este caso en Decision Center').wait_for()
        self.assertEqual(self.page.url,url)
        self.assertEqual(await self.page.evaluate('window.__caseCalls'),[])
        self.assertFalse(any(p.startswith('/api/decision-cases/') for _,p in self.requests[before:]))
        await self.page.keyboard.press('Escape')
        self.assertTrue(await self.page.locator('[data-case-switcher] button').first.evaluate('(el)=>el===document.activeElement'))
        self.assertEqual(self.page.url,url)

    async def test_case_ux_completed_picker_switches_once_without_reload_and_preserves_drafts(self):
        await self.mock_recent_case_switcher()
        other=self.second_case();other['case']['status']='completed'
        await self.open('logistics-config','logistics_assignment')
        await self.page.locator('[data-objective=min_cost]').click()
        await self.nav('logistics-map')
        await self.page.evaluate('''()=>{window.__documentIdentity='kept';window.__caseCalls=[];
          const original=window.DationDispatch.openCase;
          window.DationDispatch.openCase=(...args)=>{window.__caseCalls.push(args);return original(...args);};}''')
        await self.page.locator('[data-select-case]').click()
        await self.page.locator('[data-case-switcher] nav').get_by_role('button',name='Abrir este caso en Decision Center').wait_for()
        self.assertTrue(await self.page.get_by_text('Completado',exact=True).is_visible())
        await self.page.locator('[data-case-switcher] nav').get_by_role('button',name=other['case']['id'],exact=False).click()
        await self.page.wait_for_function('id=>window.DationDispatch.getWorkspace().decisionCase.id===id',arg=other['case']['id'])
        await self.page.locator('[data-select-case]').wait_for()
        self.assertEqual(await self.page.evaluate('window.__caseCalls'),[[other['case']['id'],'logistics-map',None]])
        self.assertEqual(await self.page.evaluate('window.__documentIdentity'),'kept')
        self.assertEqual(await self.page.locator('dialog[open]').count(),0)
        self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().orders.id'),other['orders']['id'])
        await self.page.go_back()
        await self.page.wait_for_function('id=>window.DationDispatch.getWorkspace().decisionCase.id===id',arg=self.case['id'])
        await self.page.go_forward()
        await self.page.wait_for_function('id=>window.DationDispatch.getWorkspace().decisionCase.id===id',arg=other['case']['id'])
        await self.page.evaluate("id=>window.DationDispatch.openCase(id,'logistics-config','logistics_assignment')",self.case['id'])
        self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().objective'),'min_cost')

    async def test_case_ux_picker_load_error_keeps_map_and_archived_cases_are_excluded(self):
        await self.mock_recent_case_switcher()
        other=self.second_case();other['case']['status']='archived'
        await self.open();url=self.page.url
        await self.page.locator('[data-select-case]').click()
        await self.page.locator('[data-case-switcher] nav').get_by_role('button',name='Abrir este caso en Decision Center').wait_for()
        self.assertEqual(await self.page.locator('[data-case-switcher] [aria-current=true]').count(),1)
        self.assertEqual(await self.page.locator('[data-case-switcher] nav').get_by_role('button',name=other['case']['id'],exact=False).count(),0)
        await self.page.keyboard.press('Escape')
        self.selector_failure=True
        await self.page.locator('[data-select-case]').click()
        await self.page.get_by_text('No pudimos cargar los casos.',exact=False).wait_for()
        self.assertEqual(self.page.url,url)
        await self.page.keyboard.press('Escape')
        self.assertTrue(await self.page.locator('[data-case-switcher] button').first.evaluate('(el)=>el===document.activeElement'))

    async def test_case_ux_first_pack_is_persisted_before_execution_without_transition_notice(self):
        await self.mock_recent_case_switcher()
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=logistics-data')
        await self.page.wait_for_function('Boolean(window.DationDispatch)')
        await self.page.evaluate('inputs=>window.DationDispatch.startNewDecision(inputs)',list(self.f['datasets'].values()))
        root=self.page.locator('#dispatch-data-root')
        await root.locator('[data-workflow-responsibility]').wait_for()
        self.assertEqual(self.requests.count(('POST','/api/decision-cases')),0)
        await self.assign_data_responsible()
        cid=await self.page.evaluate('window.DationDispatch.getWorkspace().decisionCase.id')
        await root.get_by_role('button',name='Seleccioná tu decisión',exact=True).click()
        await self.page.locator('[data-select-case]').wait_for()
        state=await self.page.evaluate('window.DationDispatch.getWorkspace()')
        self.assertTrue(state['decisionCase']['persisted'])
        self.assertEqual(state['decisionCase']['id'],cid)
        self.assertIn('case_id='+cid,self.page.url)
        self.assertEqual(await self.page.locator('[data-case-transition]').count(),0)
        self.assertEqual(self.requests.count(('POST','/api/decision-cases')),1)
        self.assertEqual(self.execution_bodies,[])
        await self.page.locator('[data-select-case]').click()
        await self.page.locator('[data-case-switcher] nav').get_by_role('button',name='Abrir este caso en Decision Center').wait_for()
        self.assertEqual(await self.page.locator('[data-case-switcher] [aria-current=true]').count(),1)

    async def test_case_ux_real_data_change_retains_lineage_but_reopening_history_has_no_new_notice(self):
        other=self.second_case()
        saved={'decisionCase':{**self.case,'persisted':True},'orders':other['orders'],'fleet':other['fleet']}
        await self.page.add_init_script('sessionStorage.setItem('+json.dumps(KEY)+','+json.dumps(json.dumps(saved))+');')
        await self.page.goto(f'http://127.0.0.1:{self.port}/app?view=logistics-map')
        notice=self.page.locator('[data-case-transition]');await notice.wait_for()
        state=await self.page.evaluate('window.DationDispatch.getWorkspace()');cid=state['decisionCase']['id']
        copy_text=await notice.inner_text()
        self.assertIn('Nuevo Decision Case por cambio de datos',copy_text)
        self.assertIn('DC-'+cid[:8].upper(),copy_text)
        self.assertIn('DC-'+self.case['id'][:8].upper(),copy_text)
        audit=(Path(__file__).parent/'theme_audit.js').read_text()
        self.assertEqual((await self.page.evaluate(audit,'[data-case-transition]'))['failures'],[])
        self.assertEqual(self.other_cases[cid]['decision_case']['stale_predecessor']['id'],self.case['id'])
        await self.page.evaluate("id=>window.DationDispatch.openCase(id)",self.case['id'])
        await self.page.locator('[data-select-case]').wait_for()
        self.assertEqual(await self.page.locator('[data-case-transition]').count(),0)
        await self.page.evaluate("id=>window.DationDispatch.openCase(id)",cid)
        await self.page.locator('[data-select-case]').wait_for()
        self.assertEqual(await self.page.locator('[data-case-transition]').count(),0)
        self.assertEqual(await self.page.evaluate('window.DationDispatch.getWorkspace().orders.id'),other['orders']['id'])

    async def test_case_ux_stale_local_lineage_cannot_show_a_transition_notice(self):
        self.case['stale_predecessor']={'id':'00000000-0000-4000-9000-000000000099','signature':'missing:pack'}
        await self.open()
        self.assertEqual(await self.page.locator('[data-case-transition]').count(),0)

    async def test_case_ux_hero_contract_and_attention_contours_at_desktop_mobile_and_reflow(self):
        style="""el=>{const s=getComputedStyle(el),h=getComputedStyle(el.querySelector('h1')),l=getComputedStyle(el.querySelector('.dispatch-pro-hero-lead'));return {minHeight:s.minHeight,padding:s.padding,gap:s.gap,radius:s.borderRadius,heading:h.fontSize,lead:l.fontSize,line:l.lineHeight}}"""
        for width,height in ((1440,1000),(390,844),(360,250)):
            await self.page.set_viewport_size({'width':width,'height':height})
            await self.open('logistics-data');await self.page.locator('#dispatch-data-root .d-page-hero').wait_for()
            data=await self.page.locator('#dispatch-data-root .d-page-hero').evaluate(style)
            data_height=(await self.page.locator('#dispatch-data-root .d-page-hero').bounding_box())['height']
            await self.open();map_style=await self.page.locator('#dispatch-map-root .d-page-hero').evaluate(style)
            self.assertEqual(data,map_style)
            if width==1440:self.assertLess(abs((await self.page.locator('#dispatch-map-root .d-page-hero').bounding_box())['height']-data_height),32)
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        for reduced in ('no-preference','reduce'):
            await self.page.emulate_media(reduced_motion=reduced)
            for kind in ('assignment','scheduling'):
                await self.open('logistics-config','logistics_'+kind)
                context=self.page.locator('[data-config-context]')
                geometry=await context.evaluate("el=>({outer:getComputedStyle(el).borderRadius,inner:getComputedStyle(el.querySelector('summary')).borderRadius})")
                self.assertEqual(geometry['outer'],geometry['inner'])
                chip=self.page.locator('[data-summary-target]').first
                target='#'+await chip.get_attribute('data-summary-target')
                initial=await self.page.locator(target).bounding_box()
                await chip.click()
                result=await self.page.locator(target).evaluate("el=>({radius:getComputedStyle(el).borderRadius,overlay:getComputedStyle(el,'::after').borderRadius,animation:getComputedStyle(el,'::after').animationName,pointer:getComputedStyle(el,'::after').pointerEvents,transform:getComputedStyle(el).transform,width:el.getBoundingClientRect().width})")
                self.assertEqual(result['radius'],result['overlay'])
                self.assertEqual(result['pointer'],'none');self.assertEqual(result['transform'],'none')
                self.assertEqual(result['width'],initial['width'])
                if reduced=='reduce':self.assertEqual(result['animation'],'none')

    async def test_case_ux_both_reviews_keep_config_and_only_confirm_executes_once(self):
        for width,height in ((1440,1000),(390,844)):
            await self.page.set_viewport_size({'width':width,'height':height})
            for kind in ('assignment','scheduling'):
                await self.open('logistics-config','logistics_'+kind)
                trigger=self.page.locator('[data-config-review]' if kind=='assignment' else '[data-scheduling-review]')
                confirm='[data-config-execute]' if kind=='assignment' else '[data-scheduling-execute]'
                url=self.page.url;before=len(self.execution_bodies)
                await trigger.focus();await self.page.keyboard.press('Enter')
                dialog=self.page.locator('dialog[open]');await dialog.wait_for()
                self.assertEqual(self.page.url,url)
                self.assertEqual(await self.page.evaluate('window.dationGetCurrentView()'),'logistics-config')
                self.assertEqual(len(self.execution_bodies),before)
                self.assertTrue(await dialog.evaluate("el=>el.matches(':modal')"))
                self.assertIn('Decision Case',await dialog.inner_text())
                backdrop=await dialog.evaluate("el=>getComputedStyle(el,'::backdrop').backgroundColor")
                self.assertEqual(backdrop,'rgba(0, 0, 0, 0.64)')
                self.assertFalse(await dialog.evaluate('el=>el.scrollWidth>el.clientWidth'))
                await self.page.keyboard.press('Escape')
                self.assertTrue(await trigger.evaluate('(el)=>el===document.activeElement'))
                self.assertEqual(self.page.url,url)
                await trigger.click();await dialog.get_by_role('button',name='Volver',exact=True).click()
                self.assertEqual(len(self.execution_bodies),before)
                await trigger.click()
                await self.page.locator(confirm).evaluate("el=>{el.click();el.dispatchEvent(new MouseEvent('click',{bubbles:true}));}")
                await self.page.locator('.assignment-dashboard-v2' if kind=='assignment' else '.dispatch-scheduling-dashboard').wait_for()
                self.assertEqual(len(self.execution_bodies),before+1)
                self.assertIn('view=decision-dashboard',self.page.url)
                self.assertEqual(await self.page.locator('dialog[open]').count(),0)

    async def test_workflow_keyboard_and_text_spacing_at_320_and_landscape(self):
        focus=(Path(__file__).parent/'focus_audit.js').read_text()
        theme=(Path(__file__).parent/'theme_audit.js').read_text()
        await self.page.emulate_media(reduced_motion='reduce')
        async def check_focus():
            probe=await self.page.evaluate(focus)
            if probe.get('skip'):return probe
            self.assertTrue(probe['visibleFocus']);self.assertGreaterEqual(probe['width'],2)
            if probe['tag']=='ARTICLE' and probe['rect']['height']>self.page.viewport_size['height']-160:
                # A read-only card can exceed the viewport. Its visible focus segment must be clear.
                visible=await self.page.evaluate('''()=>{
                    const el=document.activeElement,r=el.getBoundingClientRect(),top=Math.max(0,r.top),bottom=Math.min(innerHeight,r.bottom);
                    return bottom-top>=24&&[.1,.5,.9].every(t=>el.contains(document.elementFromPoint(r.x+r.width*.5,top+(bottom-top)*t)));
                }''')
                self.assertTrue(visible,probe)
            else:
                self.assertFalse(probe['outside'] or probe['occluded'],probe)
            if 'dda-workspace-step' in probe['identity']:
                self.assertTrue(await self.page.evaluate('''()=>{
                    const el=document.activeElement,r=el.getBoundingClientRect(),nav=el.closest('nav').getBoundingClientRect();
                    return r.left-5>=nav.left&&r.right+5<=nav.right;
                }'''),probe)
            return probe
        for width,height in ((320,568),(320,256),(568,320)):
            await self.page.set_viewport_size({'width':width,'height':height})
            for kind,view,node in (('data','logistics-data',None),('map','logistics-map',None),
                                  ('assignment','logistics-config','logistics_assignment'),('scheduling','logistics-config','logistics_scheduling')):
                with self.subTest(width=width,height=height,screen=kind):
                    saved=copy.deepcopy(self.case)
                    if kind=='map':self.case['nodes']=copy.deepcopy(self.f['initial_case']['nodes'])
                    await self.open(view,node)
                    if kind=='data':await self.page.locator('.d-workflow-action-bar[data-state=ready]').wait_for()
                    if kind=='map':
                        progress=self.page.get_by_role('progressbar',name='Decisiones aprobadas',exact=True)
                        self.assertEqual(await progress.get_attribute('aria-valuenow'),'0')
                        self.assertEqual(await progress.get_attribute('aria-valuetext'),'0 de 3 decisiones aprobadas')
                    if kind=='assignment':
                        for name in ('Órdenes en el análisis','Flota habilitada'):
                            progress=self.page.get_by_role('progressbar',name=name,exact=True)
                            self.assertTrue(await progress.get_attribute('aria-valuetext'))
                    layers=await self.page.locator('.topbar,.dda-workspace-nav-shell,.d-workflow-action-bar').evaluate_all('els=>els.map(el=>getComputedStyle(el).position)')
                    self.assertTrue(all(value=='static' for value in layers),layers)
                    seen=set()
                    for _ in range(120):
                        await self.page.keyboard.press('Tab');probe=await check_focus()
                        if probe.get('skip'):continue
                        if probe['identity'] in seen:break
                        seen.add(probe['identity'])
                    self.assertTrue(seen)
                    for _ in range(len(seen)):
                        await self.page.keyboard.press('Shift+Tab');await check_focus()
                    await self.page.locator('.view.is-active').evaluate('''root=>{
                        for(const el of [root,...root.querySelectorAll('*')]){
                            if(el.closest('svg,script,style,[aria-hidden=true]'))continue;
                            el.style.lineHeight='1.5';el.style.letterSpacing='.12em';el.style.wordSpacing='.16em';
                            if(el.tagName==='P')el.style.marginBottom='2em';
                        }
                    }''')
                    result=await self.page.evaluate(theme)
                    self.assertFalse(result['overflow']);self.assertEqual(result['failures'],[])
                    badges=await self.page.locator('.decision-config-section__current').evaluate_all('''els=>els.map(el=>{
                        const r=el.getBoundingClientRect(),parent=el.parentElement.getBoundingClientRect();
                        return r.right<=parent.right+.5&&el.scrollWidth<=el.clientWidth;
                    })''')
                    self.assertTrue(all(badges),badges)
                    if kind=='map':self.case.clear();self.case.update(saved)
                    if kind in ('assignment','scheduling'):
                        await self.open(view,node)
                        trigger=self.page.locator('[data-config-review]' if kind=='assignment' else '[data-scheduling-review]')
                        url=self.page.url;before=len(self.requests)
                        await trigger.focus();await self.page.keyboard.press('Enter')
                        dialog=self.page.locator('dialog[open]');await dialog.wait_for()
                        buttons=dialog.get_by_role('button')
                        await buttons.last.focus();await self.page.keyboard.press('Tab');await check_focus()
                        self.assertTrue(await buttons.first.evaluate('el=>el===document.activeElement'))
                        await self.page.keyboard.press('Shift+Tab');await check_focus()
                        self.assertTrue(await buttons.last.evaluate('el=>el===document.activeElement'))
                        await self.page.keyboard.press('Escape')
                        self.assertTrue(await trigger.evaluate('el=>el===document.activeElement'))
                        self.assertEqual(self.page.url,url);self.assertEqual(self.requests[before:],[])
        self.assertEqual(self.execution_bodies,[]);self.assertEqual(self.approval_calls,0)

    async def test_workflow_review_respects_motion_preference_changes_while_open(self):
        await self.page.set_viewport_size({'width':390,'height':568})
        for kind in ('assignment','scheduling'):
            await self.page.emulate_media(reduced_motion='no-preference')
            await self.open('logistics-config','logistics_'+kind)
            trigger=self.page.locator('[data-config-review]' if kind=='assignment' else '[data-scheduling-review]')
            url=self.page.url;before=len(self.requests)
            await trigger.focus();await self.page.keyboard.press('Enter')
            dialog=self.page.locator('dialog[open]');await dialog.wait_for()
            self.assertEqual(await dialog.evaluate('el=>getComputedStyle(el).animationName'),'none')
            await self.page.emulate_media(reduced_motion='reduce')
            self.assertEqual(await dialog.evaluate('el=>getComputedStyle(el).animationName'),'none')
            self.assertEqual(await dialog.evaluate('el=>el.getAnimations().filter(a=>a.playState==="running").length'),0)
            await self.page.keyboard.press('Escape')
            self.assertTrue(await trigger.evaluate('el=>el===document.activeElement'))
            await trigger.press('Enter');await dialog.wait_for()
            self.assertEqual(await dialog.evaluate('el=>getComputedStyle(el).animationName'),'none')
            await dialog.get_by_role('button',name='Volver',exact=True).press('Space')
            self.assertTrue(await trigger.evaluate('el=>el===document.activeElement'))
            self.assertEqual(self.page.url,url);self.assertEqual(self.requests[before:],[])
        self.assertEqual(self.execution_bodies,[])

    async def test_workflow_reviews_share_shell_and_accessible_controls_at_six_viewports(self):
        theme=(Path(__file__).parent/'theme_audit.js').read_text()
        focus=(Path(__file__).parent/'focus_audit.js').read_text()
        await self.page.emulate_media(reduced_motion='reduce')
        for width,height in ((1440,1000),(1280,1000),(1024,1000),(768,1000),(390,844),(360,250)):
            await self.page.set_viewport_size({'width':width,'height':height})
            reference=None
            for kind in ('assignment','scheduling'):
                with self.subTest(width=width,height=height,kind=kind):
                    await self.open('logistics-config','logistics_'+kind)
                    trigger=self.page.locator('[data-config-review]' if kind=='assignment' else '[data-scheduling-review]')
                    before=len(self.requests);url=self.page.url
                    await trigger.focus();await self.page.keyboard.press('Enter')
                    dialog=self.page.locator('dialog.d-execution-review[open]');await dialog.wait_for()
                    labels=await dialog.locator('.d-execution-review__row strong').all_text_contents()
                    self.assertEqual(labels,['Decision Case','Responsable','Alcance','Objetivo','Prioridades','Recursos'] if kind=='assignment'
                        else ['Decision Case','Responsable','Entrada','Ventana','Reglas por foco','Objetivo','Recursos'])
                    self.assertEqual(await dialog.locator('.d-execution-review__note').count(),1)
                    self.assertEqual(await dialog.locator('form').get_attribute('method'),'dialog')
                    self.assertTrue(await dialog.evaluate("el=>el.matches(':modal')"))
                    self.assertEqual(await dialog.locator('[data-config-review-error]').inner_text(),'')
                    styles=await dialog.evaluate('''el=>{
                        const style=node=>{const s=getComputedStyle(node);return Object.fromEntries(
                            ['padding','borderRadius','borderColor','boxShadow','background','color','font','gap','display',
                             'maxWidth','maxHeight','gridTemplateColumns','animationName','minHeight'].map(k=>[k,s[k]]));};
                        return {shell:style(el),width:el.getBoundingClientRect().width,
                            header:style(el.querySelector('header')),heading:style(el.querySelector('h2')),
                            eyebrow:style(el.querySelector('.d-execution-review__eyebrow')),
                            rows:style(el.querySelector('.d-execution-review__rows')),
                            row:style(el.querySelector('.d-execution-review__row')),
                            label:style(el.querySelector('.d-execution-review__row strong')),
                            value:style(el.querySelector('.d-execution-review__row span')),
                            footer:style(el.querySelector('footer')),
                            buttons:[...el.querySelectorAll('button')].map(style)};
                    }''')
                    if reference is None:reference=styles
                    self.assertEqual(styles,reference)
                    self.assertEqual(styles['width'],min(650,width-32))
                    if width>=1024:
                        box=await dialog.bounding_box()
                        self.assertGreaterEqual(box['height'],544)
                        self.assertLessEqual(box['height'],height-32)
                        footer=await dialog.locator('footer').bounding_box()
                        execute=await dialog.get_by_role('button',name='Ejecutar decisión',exact=True).bounding_box()
                        self.assertAlmostEqual(execute['x']+execute['width'],footer['x']+footer['width'],delta=.25)
                        self.assertAlmostEqual(execute['y']+execute['height'],box['y']+box['height']-25,delta=.25)
                    self.assertEqual(styles['shell']['animationName'],'none')
                    audit=await self.page.evaluate(theme,'dialog[open]')
                    self.assertFalse(audit['overflow']);self.assertEqual(audit['failures'],[])
                    buttons=dialog.get_by_role('button')
                    await buttons.last.focus();await self.page.keyboard.press('Tab')
                    self.assertTrue(await buttons.first.evaluate('el=>el===document.activeElement'))
                    await self.page.keyboard.press('Shift+Tab')
                    self.assertTrue(await buttons.last.evaluate('el=>el===document.activeElement'))
                    for button in await buttons.all():
                        await button.focus()
                        probe=await self.page.evaluate(focus)
                        self.assertTrue(probe['visibleFocus']);self.assertGreaterEqual(probe['width'],3)
                        self.assertFalse(probe['outside']);self.assertFalse(probe['occluded'])
                    await self.page.keyboard.press('Escape')
                    self.assertEqual(await self.page.locator('dialog[open]').count(),0)
                    self.assertTrue(await trigger.evaluate('el=>el===document.activeElement'))
                    self.assertEqual(self.page.url,url)
                    self.assertEqual(self.requests[before:],[])
        self.assertEqual(self.execution_bodies,[])

    async def test_workflow_review_escapes_content_and_wraps_long_values(self):
        await self.open('logistics-config','logistics_assignment')
        for width,height in ((1440,1000),(390,844),(360,250)):
            await self.page.set_viewport_size({'width':width,'height':height})
            result=await self.page.evaluate('''async()=>{
                const {executionReviewDialog}=await import('/static/js/dispatch/decision-config-ui.mjs');
                const owner=document.createElement('div'),text='<img src=x onerror=alert(1)>',long='Prioridad'.repeat(80);
                owner.innerHTML=executionReviewDialog({title:text,accessibleLabel:'Revisar "prueba"',
                    dialogAttributes:{'data-owner':'<unsafe>"'},executeAttributes:{'data-test-confirm':true},
                    rows:[{label:text,value:long},{label:'Cero',value:0},{label:'Sin valor',value:null}],note:text});
                document.body.append(owner);const dialog=owner.querySelector('dialog');dialog.showModal();
                const result={title:dialog.querySelector('h2').textContent,label:dialog.getAttribute('aria-label'),
                    hook:dialog.dataset.owner,images:dialog.querySelectorAll('img').length,
                    values:[...dialog.querySelectorAll('.d-execution-review__row span')].map(el=>el.textContent),
                    note:dialog.querySelector('.d-execution-review__note').textContent,
                    overflow:[dialog,...dialog.querySelectorAll('p,h2,span,strong')].some(el=>el.scrollWidth>el.clientWidth),
                    bounded:dialog.getBoundingClientRect().height<=innerHeight-32,
                    execute:dialog.querySelector('[data-test-confirm]').type};
                dialog.close();owner.remove();return result;
            }''')
            self.assertEqual(result['title'],'<img src=x onerror=alert(1)>')
            self.assertEqual(result['label'],'Revisar "prueba"');self.assertEqual(result['hook'],'<unsafe>"')
            self.assertEqual(result['images'],0);self.assertEqual(result['note'],result['title'])
            self.assertEqual(result['values'],['Prioridad'*80,'0','—'])
            self.assertFalse(result['overflow']);self.assertTrue(result['bounded']);self.assertEqual(result['execute'],'button')

    async def test_workflow_review_retry_preserves_feedback_and_guards_execution(self):
        await self.open('logistics-config','logistics_assignment')
        await self.page.evaluate('''async()=>{
            const {executionReviewDialog,bindConfigReview,mountConfigActionBar}=await import('/static/js/dispatch/decision-config-ui.mjs');
            const {createScope}=await import('/static/js/dispatch/lifecycle.mjs');
            const owner=document.createElement('div');owner.id='review-retry-fixture';
            owner.style.cssText='position:fixed;top:16px;right:16px;z-index:10000';
            owner.innerHTML='<button data-retry-trigger>Revisar prueba</button>'+executionReviewDialog({title:'Reintento',
                rows:[{label:'Objetivo',value:'Balanceado'}],executeAttributes:{'data-retry-execute':true}});
            document.body.append(owner);const scope=createScope(owner);mountConfigActionBar(owner);
            window.__reviewRetry={calls:0,scope,owner};
            bindConfigReview({dialog:owner.querySelector('dialog'),trigger:owner.querySelector('[data-retry-trigger]'),
                executeSelector:'[data-retry-execute]',onExecute:()=>{
                    window.__reviewRetry.calls++;
                    return new Promise((resolve,reject)=>Object.assign(window.__reviewRetry,{resolve,reject}));
                }});
        }''')
        trigger=self.page.locator('[data-retry-trigger]');dialog=self.page.locator('#review-retry-fixture dialog')
        execute=self.page.locator('[data-retry-execute]')
        await trigger.click();await execute.click()
        self.assertFalse(await dialog.is_visible());self.assertTrue(await execute.is_disabled())
        self.assertEqual(await execute.get_attribute('aria-busy'),'true')
        await self.page.evaluate("document.querySelector('[data-retry-trigger]').click();document.querySelector('[data-retry-execute]').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
        self.assertEqual(await self.page.evaluate('window.__reviewRetry.calls'),1)
        await self.page.evaluate("window.__reviewRetry.reject(new Error('No se pudo iniciar. Volvé a intentar.'))")
        await dialog.wait_for(state='visible')
        self.assertIn('Volvé a intentar',await dialog.locator('[role=alert]').inner_text())
        self.assertFalse(await execute.is_disabled());self.assertIsNone(await execute.get_attribute('aria-busy'))
        await self.page.keyboard.press('Escape')
        self.assertTrue(await trigger.evaluate('el=>el===document.activeElement'))
        await trigger.click();self.assertEqual(await dialog.locator('[role=alert]').inner_text(),'')
        self.assertIn('Balanceado',await dialog.inner_text())
        await execute.click();self.assertEqual(await self.page.evaluate('window.__reviewRetry.calls'),2)
        await self.page.evaluate('window.__reviewRetry.scope.dispose();window.__reviewRetry.reject(new Error("Respuesta tardía"))')
        self.assertFalse(await dialog.is_visible())
        await self.page.evaluate('window.__reviewRetry.owner.remove();delete window.__reviewRetry')
        self.assertEqual(self.execution_bodies,[])

    async def test_workflow_primitives_preserve_action_identity_states_and_token_overrides(self):
        await self.open('logistics-data')
        await self.page.locator('.d-workflow-action-bar').wait_for()
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            await self.page.emulate_media(reduced_motion='reduce' if width==390 else 'no-preference')
            result=await self.page.evaluate('''async()=>{
                const {createWorkflowActionBar}=await import('/static/js/dispatch/workflow-action-bar.mjs');
                let continued=0,corrected=0;
                const {bar,button,update}=createWorkflowActionBar({label:'Prueba',
                    onContinue:()=>continued++,onProblem:()=>corrected++});
                bar.style.setProperty('--workflow-action-height','58px');
                bar.style.setProperty('--workflow-action-radius','18px');
                bar.style.setProperty('--workflow-action-padding-x','24px');
                bar.style.setProperty('--workflow-context-control-min-width','160px');
                document.querySelector('#dispatch-data-root').append(bar);
                const snapshots=[];
                for(const [kind,enabled,options] of [
                    ['pending',false,{missingCount:2}],['ready',true,{}],
                    ['ready',true,{busy:true}],['error',false,{}],['ready',true,{}]]){
                    update({kind,enabled,message:'Estado de prueba'},options);
                    const s=getComputedStyle(button);
                    snapshots.push({sameNode:bar.querySelector('.d-button')===button,
                        height:button.getBoundingClientRect().height,radius:s.borderRadius,
                        padding:s.paddingInlineStart,minWidth:s.minWidth,
                        disabled:button.disabled,busy:button.getAttribute('aria-busy'),
                        spinner:getComputedStyle(button,'::after').animationName,
                        iconDisplay:getComputedStyle(button.querySelector('svg')).display,
                        primary:s.backgroundImage!=='none',
                        described:document.getElementById(button.getAttribute('aria-describedby'))?.textContent});
                    button.click();
                }
                button.querySelector('span').textContent='Continuar con la revisión de esta decisión y sus recursos disponibles';
                const wrapsWithoutClipping=button.scrollWidth<=button.clientWidth&&button.scrollHeight<=button.clientHeight;
                button.focus();
                const focused=document.activeElement===button;
                const fits=bar.getBoundingClientRect().right<=innerWidth;
                bar.remove();
                return {snapshots,continued,corrected,wrapsWithoutClipping,focused,fits};
            }''')
            self.assertEqual(result['continued'],2)
            self.assertEqual(result['corrected'],1)
            self.assertTrue(result['wrapsWithoutClipping'])
            self.assertTrue(result['focused'])
            self.assertTrue(result['fits'])
            self.assertEqual([s['disabled'] for s in result['snapshots']],[True,False,True,False,False])
            self.assertEqual([s['busy'] for s in result['snapshots']],['false','false','true','false','false'])
            self.assertFalse(result['snapshots'][3]['primary'],'Corrective actions keep their secondary role')
            self.assertTrue(result['snapshots'][1]['primary'])
            self.assertEqual(result['snapshots'][2]['spinner'],'none' if width==390 else 'd-workflow-spin')
            self.assertEqual(result['snapshots'][2]['iconDisplay'],'none')
            for snapshot in result['snapshots']:
                self.assertTrue(snapshot['sameNode'])
                self.assertEqual(snapshot['height'],58)
                self.assertEqual(snapshot['radius'],'18px')
                self.assertEqual(snapshot['padding'],'24px')
                self.assertEqual(snapshot['described'],'Estado de prueba')
        self.assertEqual(self.execution_bodies,[])

    async def test_workflow_bars_equalize_context_and_keep_a_wider_primary_action(self):
        geometry='''bar=>{
            const items=[...bar.querySelectorAll('.d-workflow-action-bar__item')];
            const action=bar.querySelector('.d-button'),r=action.getBoundingClientRect();
            return {items:items.map(el=>{const r=el.getBoundingClientRect();return {
                width:r.width,height:r.height,clipped:el.scrollWidth>el.clientWidth||el.scrollHeight>el.clientHeight};}),
                actionWidth:r.width,primary:getComputedStyle(action).backgroundImage!=='none',
                overflow:document.documentElement.scrollWidth>innerWidth};
        }'''
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            for view,node in (('logistics-data',None),('logistics-config','logistics_assignment'),
                              ('logistics-config','logistics_scheduling')):
                await self.open(view,node)
                bar=self.page.locator('.d-workflow-action-bar');await bar.wait_for()
                if node is None:
                    await self.page.locator('.d-workflow-action-bar[data-state="ready"]').wait_for()
                for long_copy in (False,True):
                    if long_copy:
                        await bar.locator('.d-workflow-action-bar__item strong,.d-workflow-action-bar__item span').first.evaluate(
                            "el=>el.textContent='Recursos disponibles para todas las operaciones seleccionadas y sus prioridades'")
                    sizes=await bar.evaluate(geometry)
                    self.assertEqual(len(sizes['items']),2 if node is None else 3)
                    self.assertLess(max(x['width'] for x in sizes['items'])-min(x['width'] for x in sizes['items']),.25)
                    self.assertLess(max(x['height'] for x in sizes['items'])-min(x['height'] for x in sizes['items']),.25)
                    self.assertGreater(sizes['actionWidth'],max(x['width'] for x in sizes['items']))
                    self.assertFalse(sizes['overflow'])
                    self.assertTrue(sizes['primary'],(width,node,long_copy,sizes))
                    self.assertTrue(all(not x['clipped'] for x in sizes['items']))
        self.assertEqual(self.execution_bodies,[])

    async def test_workflow_progressive_actions_share_styles_arrow_and_keyboard_focus(self):
        original_case=copy.deepcopy(self.case)
        original_run=copy.deepcopy(self.f['runs']['assignment'])
        await self.page.emulate_media(reduced_motion='reduce')
        reference=None
        async def check(button,label):
            nonlocal reference
            await button.wait_for(state='visible')
            await self.page.mouse.move(0,0)
            await self.page.keyboard.press('Tab')
            await button.focus()
            actual=await button.evaluate('''el=>{
                const s=getComputedStyle(el),icon=el.querySelector('svg'),i=getComputedStyle(icon);
                return {minHeight:s.minHeight,padding:s.padding,radius:s.borderRadius,
                    font:s.font,fontWeight:s.fontWeight,gap:s.gap,background:s.backgroundImage,color:s.color,
                    outline:s.outline,offset:s.outlineOffset,iconWidth:i.width,iconHeight:i.height,
                    iconCount:el.querySelectorAll('svg').length,decorative:icon.getAttribute('aria-hidden'),
                    textArrow:el.textContent.includes('→'),focused:document.activeElement===el,
                    clipped:el.scrollWidth>el.clientWidth||el.scrollHeight>el.clientHeight,
                    workflow:el.classList.contains('d-button--workflow')};
            }''')
            self.assertTrue(actual.pop('focused'),label)
            self.assertFalse(actual.pop('clipped'),label)
            self.assertTrue(actual.pop('workflow'),label)
            self.assertEqual(actual['iconCount'],1,label)
            self.assertEqual(actual['decorative'],'true',label)
            self.assertFalse(actual['textArrow'],label)
            self.assertIn('linear-gradient',actual['background'],label)
            if reference is None:reference=actual
            self.assertEqual(actual,reference,label)
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            self.case.clear();self.case.update(copy.deepcopy(original_case))
            self.f['runs']['assignment'].clear();self.f['runs']['assignment'].update(copy.deepcopy(original_run))
            await self.open('logistics-data')
            await self.page.locator('.d-workflow-action-bar[data-state="ready"]').wait_for()
            await check(self.page.locator('.d-workflow-action-bar .d-button'),'data')
            self.case['nodes']=copy.deepcopy(self.f['initial_case']['nodes'])
            await self.open('logistics-map')
            await check(self.page.locator('[data-map-action="configure"]'),'map')
            self.case.clear();self.case.update(copy.deepcopy(original_case))
            for kind in ('assignment','scheduling'):
                await self.open('logistics-config','logistics_'+kind)
                trigger=self.page.locator('[data-config-review]' if kind=='assignment' else '[data-scheduling-review]')
                await check(trigger,kind+'-review')
                await trigger.click()
                await check(self.page.locator('[data-config-execute]' if kind=='assignment' else '[data-scheduling-execute]'),kind+'-execute')
                self.assertFalse(await self.page.locator('dialog[open] button[value="cancel"]').evaluate("el=>el.classList.contains('d-button--primary')"))
                await self.page.keyboard.press('Escape')
            await self.open('decision-dashboard','logistics_scheduling',self.f['ids']['scheduling'])
            await check(self.page.locator('[data-approve-toolbar]'),'scheduling-approve')
            self.review_assignment();await self.dashboard()
            await check(self.page.locator('[data-approve-toolbar]'),'assignment-approve')
            await self.page.locator('[data-approve-toolbar]').click()
            await check(self.page.locator('[data-after-approve]'),'continue')
            self.assertFalse(await self.page.locator('[data-dashboard-map]').evaluate("el=>el.classList.contains('d-button--primary')"))
        self.assertEqual(self.approval_calls,5)
        self.assertEqual(self.execution_bodies,[])

    async def test_workflow_heroes_share_metadata_panel_and_stable_desktop_height(self):
        await self.page.emulate_media(reduced_motion='reduce')
        for width,height in ((1440,1000),(1280,1000),(1024,1000),(768,1000),(390,1000),(360,1000),(360,250)):
            await self.page.set_viewport_size({'width':width,'height':height})
            records=[]
            for view,node in (('logistics-data',None),('logistics-map',None),
                              ('logistics-config','logistics_assignment'),('logistics-config','logistics_scheduling')):
                await self.open(view,node)
                hero=self.page.locator('.view.is-active .d-page-hero--workflow');await hero.wait_for()
                if node=='logistics_scheduling':
                    self.assertEqual(await hero.locator('.dispatch-pro-how-node strong').nth(1).inner_text(),'Calendario operativo + secuencia')
                metrics=await hero.evaluate('''el=>{
                    const rect=x=>{const r=x.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,height:r.height,width:r.width};};
                    const style=x=>{const s=getComputedStyle(x);return {size:parseFloat(s.fontSize),weight:parseFloat(s.fontWeight),border:s.borderColor,color:s.color};};
                    const s=getComputedStyle(el),copy=el.querySelector('.dispatch-pro-hero-copy'),panel=el.querySelector('.dispatch-pro-hero-visual');
                    const step=el.querySelector('.d-hero-meta__step'),decision=el.querySelector('.d-hero-meta__decision');
                    const items=[...panel.querySelectorAll('.dispatch-pro-how-node')];
                    return {hero:rect(el),copy:rect(copy),panel:rect(panel),columns:s.gridTemplateColumns,
                        padding:s.padding,gap:parseFloat(s.gap),animation:s.animationName,metaTop:rect(step).top-rect(el).top,
                        step:{...rect(step),...style(step)},decision:decision?{...rect(decision),...style(decision)}:null,
                        items:items.map(x=>{const text=x.querySelector('strong'),range=document.createRange();range.selectNodeContents(text);
                            return {...rect(x),lines:new Set([...range.getClientRects()].map(r=>Math.round(r.y))).size,font:style(text).size,
                                clipped:x.scrollWidth>x.clientWidth||text.scrollWidth>text.clientWidth};}),
                        overflow:el.scrollWidth>el.clientWidth||document.documentElement.scrollWidth>innerWidth};
                }''')
                with self.subTest(width=width,height=height,view=view,node=node):
                    self.assertFalse(metrics['overflow']);self.assertEqual(metrics['animation'],'none')
                    self.assertEqual(len(metrics['items']),3)
                    self.assertAlmostEqual(metrics['metaTop'],float(metrics['padding'].split()[0].removesuffix('px'))+1,delta=.25)
                    for item in metrics['items']:
                        self.assertFalse(item['clipped']);self.assertGreater(item['height'],0)
                        self.assertGreaterEqual(item['font'],12)
                        self.assertGreaterEqual(item['left'],metrics['hero']['left'])
                        self.assertLessEqual(item['right'],metrics['hero']['right'])
                    if node:
                        step,decision=metrics['step'],metrics['decision']
                        self.assertIsNotNone(decision)
                        self.assertGreaterEqual(decision['top'],step['bottom']+3.5)
                        self.assertAlmostEqual(step['left'],decision['left'],delta=.25)
                        self.assertGreater(step['size'],decision['size']);self.assertGreater(step['weight'],decision['weight'])
                        self.assertNotEqual(step['border'],decision['border']);self.assertNotEqual(step['color'],decision['color'])
                    else:self.assertIsNone(metrics['decision'])
                    if width>=1280:
                        self.assertGreaterEqual(metrics['panel']['width'],320)
                        self.assertTrue(all(item['lines']==1 for item in metrics['items']))
                    else:self.assertGreaterEqual(metrics['panel']['top'],metrics['copy']['bottom']+metrics['gap']-.5)
                    if height==250:
                        positions=await self.page.locator('.topbar,.dda-workspace-nav-shell,.d-workflow-action-bar').evaluate_all('els=>els.map(el=>getComputedStyle(el).position)')
                        self.assertTrue(all(position=='static' for position in positions),positions)
                        if node:
                            await self.page.keyboard.press('Tab')
                            await self.page.locator('[data-config-review]' if node=='logistics_assignment' else '[data-scheduling-review]').focus()
                            await self.page.locator('[data-config-context] summary').focus()
                            focus=await self.page.evaluate((Path(__file__).parent/'focus_audit.js').read_text())
                            self.assertTrue(focus['visibleFocus'],focus)
                            self.assertFalse(focus['occluded'] or focus['outside'],focus)
                records.append(metrics)
            if width>=1280:
                self.assertLessEqual(max(r['hero']['height'] for r in records)-min(r['hero']['height'] for r in records),1)
                self.assertEqual(len({r['columns'] for r in records}),1)
                self.assertTrue(all(r['hero']['height']<=266 for r in records))
        self.assertFalse(any(m=='POST' and p=='/api/runs' for m,p in self.requests))

    async def test_workflow_hero_future_content_wraps_without_clipping_or_html_injection(self):
        await self.open('logistics-config','logistics_assignment')
        for width in (1440,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            result=await self.page.evaluate('''async()=>{
                const {decisionHero}=await import('/static/js/dispatch/decision-config-ui.mjs');
                const owner=document.createElement('div');document.querySelector('#dispatch-config-root').append(owner);
                owner.style.setProperty('--hero-meta-gap','10px');
                owner.innerHTML=decisionHero({step:{number:7,label:'Nueva decisión '+ 'Contenido'.repeat(35)},decisionIndex:4,totalDecisions:20,
                    title:'Título'+ 'Largo'.repeat(60),description:'Descripción'+ 'Extendida'.repeat(90),
                    panelTitle:'<img src=x onerror=alert(1)>',panelFootnote:'Nota '+ 'Prolongada'.repeat(60),
                    panelItems:Array.from({length:5},()=>({icon:'truck',label:'Campo'+ 'Extendido'.repeat(30),description:'Valor'+ 'Largo'.repeat(90)}))});
                const hero=owner.firstElementChild,texts=[...hero.querySelectorAll('h1,p,small,strong,.d-hero-meta>span,.dispatch-pro-how-history>span')];
                const result={overflow:hero.scrollWidth>hero.clientWidth||document.documentElement.scrollWidth>innerWidth,
                    clipped:texts.some(el=>el.scrollWidth>el.clientWidth+1||el.scrollHeight>el.clientHeight+1),
                    decision:hero.querySelector('.d-hero-meta__decision').textContent,
                    panelItems:hero.querySelectorAll('.dispatch-pro-how-node').length,
                    images:hero.querySelectorAll('img:not(.dispatch-pro-hero-watermark)').length,
                    title:hero.querySelector('.dispatch-pro-how-title').textContent,gap:getComputedStyle(hero.querySelector('.d-hero-meta')).gap};
                owner.remove();return result;
            }''')
            self.assertFalse(result['overflow'],result);self.assertFalse(result['clipped'],result)
            self.assertEqual(result['decision'],'DECISIÓN 04 DE 20');self.assertEqual(result['panelItems'],5)
            self.assertEqual(result['images'],0);self.assertEqual(result['title'],'<img src=x onerror=alert(1)>')
            self.assertEqual(result['gap'],'10px')

    async def test_workflow_primitives_hero_supports_optional_metadata_and_panel(self):
        await self.open('logistics-config','logistics_assignment')
        await self.page.locator('.assignment-config-hero').wait_for()
        for width in (1440,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            result=await self.page.evaluate('''async()=>{
                const {decisionHero}=await import('/static/js/dispatch/decision-config-ui.mjs');
                const owner=document.createElement('div');
                document.querySelector('#dispatch-config-root').append(owner);
                const variants=[];
                for(const decisionIndex of [undefined,null,'',1,'02']){
                    owner.innerHTML=decisionHero({title:'<img src=x onerror=alert(1)>',
                        description:'Descripción',step:{number:3,label:'Configurar decisión'},decisionIndex});
                    const hero=owner.firstElementChild;
                    variants.push({decision:hero.querySelector('.assignment-decision-chip')?.textContent??null,
                        panel:!!hero.querySelector('.dispatch-pro-hero-visual'),
                        columns:getComputedStyle(hero).gridTemplateColumns.split(' ').length,
                        title:hero.querySelector('h1').textContent,images:hero.querySelectorAll('img').length,
                        overflow:hero.scrollWidth>hero.clientWidth});
                }
                owner.innerHTML=decisionHero({title:'Decisión',description:'Descripción',decisionIndex:1,
                    panelItems:[{icon:'truck',label:'Recursos',description:'Flota disponible'}]});
                const hasPanel=owner.querySelectorAll('.dispatch-pro-hero-visual .dispatch-pro-how-node').length===1;
                owner.remove();return {variants,hasPanel};
            }''')
            self.assertEqual([v['decision'] for v in result['variants']],
                             [None,None,None,'DECISIÓN 01 DE 3','DECISIÓN 02 DE 3'])
            self.assertTrue(result['hasPanel'])
            for variant in result['variants']:
                self.assertFalse(variant['panel'])
                self.assertEqual(variant['columns'],1)
                self.assertEqual(variant['title'],'<img src=x onerror=alert(1)>')
                self.assertEqual(variant['images'],0)
                self.assertFalse(variant['overflow'])
        self.assertEqual(self.execution_bodies,[])

    async def open_advanced(self):
        toggle=self.page.locator('[data-assignment-advanced-toggle]')
        if await toggle.get_attribute('aria-expanded')=='false':await toggle.click()
        await self.page.locator('#dispatch-assignment').wait_for(state='visible')

    async def test_d1_v2_view_modes_preserve_evidence_and_restore_without_reexecution(self):
        self.essential();before=copy.deepcopy(self.f['runs']['assignment']);await self.dashboard();url=self.page.url
        self.assertEqual(await self.page.locator('.assignment-view-control,[data-assignment-view]').count(),0)
        main=self.page.locator('main.assignment-dashboard-v2__main')
        self.assertIsNone(await main.get_attribute('role'));self.assertIsNone(await main.get_attribute('aria-labelledby'))
        self.assertTrue(await main.evaluate('el=>el.previousElementSibling.classList.contains("assignment-dashboard-v2__rail")'))
        self.assertEqual(await self.page.locator('[data-assignment-advanced-toggle]').get_attribute('aria-expanded'),'false')
        self.assertFalse(await self.page.locator('#dispatch-assignment').is_visible())
        self.assertFalse(await self.page.locator('[data-ai-summary-body]').is_visible())
        self.assertEqual(await self.page.locator('#assignment-preview tbody tr').count(),5)
        await self.page.locator('[data-assignment-full-plan]').click()
        self.assertTrue(await self.page.locator('#dispatch-assignment').is_visible())
        self.assertTrue(await self.page.locator('#dispatch-assignment').evaluate('el=>el===document.activeElement'))
        await self.page.locator('#dispatch-assignment').evaluate('el=>{window.savedEvidence=el;window.savedFrontier=document.querySelector(".assignment-frontier__chart svg");}')
        await self.page.locator('[data-assignment-advanced-toggle]').click()
        self.assertFalse(await self.page.locator('#dispatch-assignment').is_visible())
        await self.open_advanced()
        self.assertTrue(await self.page.locator('#dispatch-assignment').evaluate('el=>el===window.savedEvidence'))
        self.assertTrue(await self.page.evaluate('window.savedFrontier===document.querySelector(".assignment-frontier__chart svg")'))
        await self.page.reload();await self.page.locator('#dispatch-assignment').wait_for(state='visible')
        self.assertEqual(await self.page.locator('[data-assignment-advanced-label]').inner_text(),'Ocultar análisis avanzado')
        self.assertEqual(await self.page.locator('[data-assignment-advanced-toggle]').get_attribute('aria-expanded'),'true')
        self.assertEqual(await self.page.evaluate('sessionStorage.getItem("dation.assignment.presentation."+window.DationDispatch.getWorkspace().run.id)'),'advanced')
        self.assertEqual(await self.page.locator('.assignment-dashboard-v2').get_attribute('data-analysis-depth'),'essential')
        self.assertEqual(self.page.url,url);self.assertEqual(self.f['runs']['assignment'],before)
        self.assertEqual(self.comparative_posts,0);self.assertEqual(self.explain_calls,0);self.assertEqual(self.execution_bodies,[])

    async def test_d1_v2_disclosure_keyboard_feedback_and_manual_scroll(self):
        await self.page.emulate_media(reduced_motion='reduce');await self.dashboard();url=self.page.url
        toggle=self.page.locator('[data-assignment-advanced-toggle]')
        content=self.page.locator('[data-assignment-advanced-content]')
        self.assertEqual(await toggle.get_attribute('type'),'button')
        self.assertEqual(await toggle.get_attribute('aria-controls'),await content.get_attribute('id'))
        self.assertEqual(await content.get_attribute('id'),'assignment-presentation-'+self.f['ids']['assignment']+'-advanced-content')
        self.assertEqual(await self.page.locator('[data-assignment-advanced-chevron]').get_attribute('aria-hidden'),'true')
        self.assertEqual(await self.page.locator('.assignment-view-control,[data-assignment-view]').count(),0)
        for width,height in ((1440,1000),(768,1024),(390,844),(320,568)):
            await self.page.set_viewport_size({'width':width,'height':height})
            await toggle.evaluate('el=>el.scrollIntoView({block:"center"})');await toggle.focus()
            before=await toggle.evaluate('''el=>({y:scrollY,background:getComputedStyle(el).backgroundColor,
                border:getComputedStyle(el).borderColor,leading:getComputedStyle(el.querySelector('.assignment-advanced__copy svg')).transform})''')
            self.assertEqual(await toggle.get_attribute('aria-expanded'),'false');self.assertTrue(await content.evaluate('el=>el.hidden'))
            self.assertEqual(await self.page.locator('[data-assignment-advanced-label]').inner_text(),'Mostrar análisis avanzado')
            await self.page.keyboard.press('Enter')
            self.assertEqual(await toggle.get_attribute('aria-expanded'),'true');self.assertFalse(await content.evaluate('el=>el.hidden'))
            self.assertTrue(await self.page.locator('[data-assignment-advanced]').evaluate('el=>el.classList.contains("is-open")'))
            self.assertEqual(await self.page.locator('[data-assignment-advanced-label]').inner_text(),'Ocultar análisis avanzado')
            after=await toggle.evaluate('''el=>{const s=getComputedStyle(el),c=el.querySelector('[data-assignment-advanced-chevron]'),a=el.querySelector('.assignment-advanced__copy'),r=el.getBoundingClientRect(),cr=c.getBoundingClientRect();return {
                y:scrollY,background:s.backgroundColor,border:s.borderColor,rotation:getComputedStyle(c).transform,
                leading:getComputedStyle(a.querySelector('svg')).transform,transition:getComputedStyle(c).transitionDuration,
                fits:cr.right<=r.right&&a.getBoundingClientRect().right<=cr.left&&el.scrollWidth<=el.clientWidth,
                focus:el===document.activeElement&&el.matches(':focus-visible'),outline:parseFloat(s.outlineWidth)};}''')
            self.assertEqual(after['y'],before['y']);self.assertNotEqual(after['background'],before['background'])
            self.assertNotEqual(after['border'],before['border']);self.assertEqual(after['leading'],before['leading'])
            self.assertEqual(after['rotation'],'matrix(-1, 0, 0, -1, 0, 0)');self.assertEqual(after['transition'],'0s')
            self.assertTrue(after['fits']);self.assertTrue(after['focus']);self.assertGreaterEqual(after['outline'],2)
            await self.page.keyboard.press('Space')
            self.assertEqual(await toggle.get_attribute('aria-expanded'),'false');self.assertTrue(await content.evaluate('el=>el.hidden'))
            self.assertFalse(await self.page.locator('[data-assignment-advanced]').evaluate('el=>el.classList.contains("is-open")'))
            self.assertEqual(await self.page.locator('[data-assignment-advanced-label]').inner_text(),'Mostrar análisis avanzado')
            self.assertEqual(await self.page.evaluate('scrollY'),before['y']);self.assertEqual(self.page.url,url)
            self.assertEqual(await self.page.locator('[data-assignment-advanced-chevron]').evaluate('el=>getComputedStyle(el).transform'),'none')
            self.assertTrue(await toggle.evaluate('el=>el===document.activeElement'))
        self.assertEqual(self.explain_calls,0);self.assertEqual(self.comparative_posts,0);self.assertEqual(self.execution_bodies,[])

    async def test_d1_v2_all_objectives_highlight_the_actual_selected_scenario(self):
        original=copy.deepcopy(self.f['runs']['assignment']['result_json']);copy_values=[]
        for objective in ('min_trips','min_cost','max_own_fleet','balanced','min_co2'):
            result=copy.deepcopy(original);reference=result['scenarios'][objective]
            result['configuration']['objective']=objective
            result['scenarios']['selected'].update(metrics=copy.deepcopy(reference['metrics']),plan_fingerprint=reference['plan_fingerprint'],name=reference['name'])
            self.f['runs']['assignment']['result_json']=result
            await self.dashboard()
            selected=self.page.locator('#assignment-scenarios [aria-current=true]')
            self.assertEqual(await selected.count(),1);self.assertEqual(await selected.get_attribute('data-scenario-row'),objective)
            self.assertEqual(await self.page.locator('#assignment-scenarios input').count(),0)
            copy_values.append(await self.page.locator('.assignment-hero__lead').inner_text())
        self.assertEqual(len(set(copy_values)),5)
        self.assertEqual(self.comparative_posts,0);self.assertEqual(self.explain_calls,0)

    async def test_d1_v2_ai_cached_brief_copy_chat_and_collapse_without_inference(self):
        self.saved_explanation={'id':'cached','response_json':{'executive_summary':'Resumen ejecutivo persistido <script>malicioso()</script>','key_drivers':['Evidencia persistida'],'caveats':['Assignment no define fechas.']}}
        await self.dashboard()
        await self.page.get_by_text('Resumen disponible',exact=True).wait_for()
        self.assertFalse(await self.page.locator('[data-ai-summary-body]').is_visible())
        await self.page.locator('[data-explain]').click()
        await self.page.locator('[data-ai-summary-controls]').wait_for(state='visible')
        self.assertEqual(self.explain_calls,0)
        self.assertEqual(await self.page.locator('[data-response] script,[data-response] img,.dispatch-ai-evidence-grid').count(),0)
        self.assertIn('<script>',await self.page.locator('[data-response]').inner_text())
        await self.page.evaluate("navigator.clipboard.writeText=async value=>{window.copiedSummary=value}")
        await self.page.locator('[data-ai-copy]').click()
        self.assertIn('Resumen ejecutivo persistido',await self.page.evaluate('window.copiedSummary'))
        await self.page.locator('[data-ai-ask]').click()
        await self.page.locator('.dispatch-chat textarea').wait_for(state='visible')
        self.assertEqual(self.chat_calls,[])
        self.assertIn(self.f['ids']['assignment'][:8],await self.page.locator('.dispatch-chat-context').inner_text())
        await self.page.keyboard.press('Escape');self.assertFalse(await self.page.locator('.dispatch-chat').is_visible())
        await self.page.locator('[data-ai-collapse]').click();self.assertFalse(await self.page.locator('[data-ai-summary-body]').is_visible())
        await self.page.locator('[data-explain]').click();self.assertEqual(self.explain_calls,0)

    async def test_d1_v2_ai_loading_error_retry_regeneration_are_explicit_and_coalesced(self):
        self.explain_fail_once=True;self.delay[f"/api/runs/{self.f['ids']['assignment']}/explain"]=.4
        await self.dashboard();self.assertEqual(self.explain_calls,0)
        button=self.page.locator('[data-explain]');await button.click()
        self.assertTrue(await button.is_disabled());self.assertEqual(await button.get_attribute('aria-busy'),'true')
        await button.dispatch_event('click')
        await self.page.get_by_role('alert').filter(has_text='Fallo sintético de IA').wait_for()
        self.assertEqual(self.explain_calls,1);self.assertEqual(await self.page.locator('[data-executive-kpi]').count(),4)
        await self.page.get_by_role('button',name='Reintentar resumen',exact=True).click()
        await self.page.locator('[data-ai-summary-controls]').wait_for(state='visible')
        self.assertEqual(self.explain_calls,2)
        await self.page.locator('[data-ai-regenerate]').click()
        await self.page.wait_for_function("document.querySelector('[data-ai-summary-state]').dataset.aiSummaryState==='completed'")
        self.assertEqual(self.explain_calls,3);self.assertEqual(self.execution_bodies,[])

    async def test_d1_v2_new_comparative_evidence_marks_summary_stale_without_automatic_ai(self):
        self.essential();self.saved_explanation={'id':'original','response_json':{'executive_summary':'Resumen original'}}
        await self.dashboard();await self.page.get_by_text('Resumen disponible',exact=True).wait_for()
        await self.page.locator('[data-explain]').click();await self.page.get_by_text('Resumen original',exact=True).wait_for()
        await self.open_advanced();await self.page.locator('[data-generate-comparative]').click()
        await self.page.wait_for_selector('[data-comparative-state=queued]');self.comparative['status']='completed'
        await self.page.locator('[data-ai-summary-availability]').filter(has_text='Hay nueva evidencia disponible').wait_for()
        self.assertEqual(self.explain_calls,0);self.assertIn('Resumen original',await self.page.locator('[data-response]').inner_text())
        await self.page.locator('[data-explain]').click()
        await self.page.get_by_text('Synthetic explanation',exact=True).wait_for()
        self.assertEqual(self.explain_calls,1)
        self.assertEqual(self.saved_explanation_evidence,self.comparative['id'])
        self.assertFalse(await self.page.locator('[data-ai-summary-freshness]').is_visible())

    async def test_d1_v2_infeasible_and_missing_metrics_remain_explicit(self):
        self.review_assignment();result=self.f['runs']['assignment']['result_json']
        result['scenarios']['selected']['feasible']=False;result['scenarios']['selected']['metrics']['total_cost']=None
        result['scenarios']['min_cost']['feasible']=False
        await self.dashboard()
        self.assertIn('Escenario no factible',await self.page.locator('[data-assignment-hero-status]').inner_text())
        self.assertIn('—',await self.page.locator('[data-executive-kpi=total_cost]').inner_text())
        self.assertTrue(await self.page.locator('[data-approve-toolbar]').is_disabled())
        self.assertTrue(await self.page.locator('[data-approve-final]').is_disabled())
        self.assertIn('No factible',await self.page.locator('#assignment-scenarios').inner_text())
        await self.open_advanced();await self.page.locator('[data-comparison-select]').select_option('min_cost')
        self.assertIn('Referencia no factible',await self.page.locator('#dispatch-comparative').inner_text())
        self.assertEqual(await self.page.locator('.assignment-comparison__metric.is-improvement').count(),0)

    async def test_d1_v2_final_approval_updates_hero_and_continues_to_scheduling(self):
        self.review_assignment();await self.dashboard()
        await self.page.locator('[data-approve-final]').click()
        await self.page.wait_for_function("document.querySelector('[data-status-badge]').textContent==='Aprobada'")
        self.assertEqual(self.approval_calls,1);self.assertTrue(await self.page.locator('[data-approve-toolbar]').is_disabled())
        self.assertIn('Decisión aprobada',await self.page.locator('[data-assignment-hero-status]').inner_text())
        await self.page.locator('[data-after-approve]').wait_for(state='visible')
        await self.page.locator('[data-after-approve]').click()
        await self.page.locator('[data-scheduling-review]').wait_for(state='visible')
        self.assertEqual(self.execution_bodies,[])

    async def test_d1_v2_local_hero_has_a_readable_svg_fallback(self):
        await self.context.route('**/assignment-hero-truck.webp',lambda route:route.abort())
        await self.page.set_viewport_size({'width':390,'height':844});await self.dashboard()
        await self.page.locator('.assignment-hero__art[data-fallback=true]').wait_for()
        self.assertTrue(await self.page.locator('#dispatch-hero h1').is_visible())
        self.assertTrue(await self.page.locator('[data-rerun]').is_visible())
        background=await self.page.locator('.assignment-hero__art').evaluate('el=>getComputedStyle(el).backgroundImage')
        self.assertIn('/static/assets/dda-logistics.svg',background)
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))

    async def test_d1_v2_essential_and_advanced_fit_low_viewports_and_keyboard(self):
        theme=(Path(__file__).parent/'theme_audit.js').read_text();focus=(Path(__file__).parent/'focus_audit.js').read_text()
        await self.page.emulate_media(reduced_motion='reduce');await self.dashboard()
        for width,height in ((1440,1000),(1280,1000),(1024,1000),(768,1000),(390,844),(360,250),(320,568),(320,256),(568,320)):
            await self.page.set_viewport_size({'width':width,'height':height})
            for mode in ('essential','advanced'):
                toggle=self.page.locator('[data-assignment-advanced-toggle]')
                if (await toggle.get_attribute('aria-expanded')=='true')!=(mode=='advanced'):await toggle.click()
                audit=await self.page.evaluate(theme);self.assertFalse(audit['overflow'],(width,height,mode));self.assertEqual(audit['failures'],[],(width,height,mode))
                await self.page.locator('#dispatch-hero .assignment-essential__objective>summary').focus()
                for key in ['Tab']*14+['Shift+Tab']*14:
                    await self.page.keyboard.press(key);probe=await self.page.evaluate(focus)
                    if not probe.get('skip'):
                        self.assertTrue(probe['visibleFocus'],(width,height,mode,probe))
                        self.assertFalse(probe['occluded'] or probe['outside'],(width,height,mode,probe))
        self.assertEqual(self.explain_calls,0);self.assertEqual(self.comparative_posts,0)

    async def test_d1_v2_table_focus_reveals_partially_clipped_trip_control(self):
        reproduced=0
        await self.dashboard();await self.open_advanced()
        clipped_rows=0
        for width,height in ((1280,800),(800,800),(390,844),(390,300)):
            await self.page.set_viewport_size({'width':width,'height':height})
            button=self.page.locator('[data-trip-detail-button]').first
            await button.scroll_into_view_if_needed()
            result=await button.evaluate('''button=>{
                const wrap=button.closest('.assignment-evidence__table-wrap');
                button.blur();wrap.scrollLeft=0;
                const initial=button.getBoundingClientRect(),bounds=wrap.getBoundingClientRect();
                wrap.scrollLeft=Math.max(0,initial.right-bounds.right-10);
                const clipped=button.getBoundingClientRect().right>bounds.right+1;
                const before={top:wrap.scrollTop,pageY:scrollY,left:wrap.scrollLeft};
                button.focus({preventScroll:true});
                const rect=button.getBoundingClientRect(),after=wrap.getBoundingClientRect();
                return {clipped,before,focused:document.activeElement===button,
                    right:rect.right,edge:after.right,left:wrap.scrollLeft,top:wrap.scrollTop,pageY:scrollY};
            }''')
            reproduced+=int(result['clipped'])
            self.assertTrue(result['focused']);self.assertLessEqual(result['right'],result['edge']-5,result)
            self.assertEqual(result['top'],result['before']['top']);self.assertEqual(result['pageY'],result['before']['pageY'])
            if result['clipped']:self.assertGreater(result['left'],result['before']['left'])
            later=self.page.locator('[data-trip-detail-button]').nth(3)
            await later.scroll_into_view_if_needed()
            vertical=await later.evaluate('''button=>{
                button.blur();const wrap=button.closest('.assignment-evidence__table-wrap');wrap.scrollTop=0;
                const before=button.getBoundingClientRect(),edge=wrap.getBoundingClientRect(),pageY=scrollY;
                const clipped=before.bottom>edge.bottom;
                button.focus({preventScroll:true});const rect=button.getBoundingClientRect();
                return {clipped,pageY,afterY:scrollY,top:rect.top,bottom:rect.bottom,edgeTop:edge.top,edgeBottom:edge.bottom,
                    visible:[[.2,.2],[.5,.5],[.8,.8]].every(([x,y])=>button.contains(document.elementFromPoint(rect.x+rect.width*x,rect.y+rect.height*y)))};
            }''')
            clipped_rows+=int(vertical['clipped'])
            self.assertTrue(vertical['visible'],vertical);self.assertGreaterEqual(vertical['top'],vertical['edgeTop'])
            self.assertLessEqual(vertical['bottom'],vertical['edgeBottom']);self.assertEqual(vertical['afterY'],vertical['pageY'])
        self.assertGreater(reproduced,0)
        self.assertGreater(clipped_rows,0)
        self.assertEqual(self.explain_calls,0);self.assertEqual(self.comparative_posts,0);self.assertEqual(self.execution_bodies,[])

    async def test_d2_v21_disclosure_keyboard_persistence_preview_and_evidence(self):
        original=copy.deepcopy(self.f['runs']['scheduling'])
        await self.open('decision-dashboard','logistics_scheduling',self.f['ids']['scheduling'])
        root=self.page.locator('.scheduling-dashboard-v2')
        self.assertEqual(await root.locator('[role=tablist],[role=tab],[role=tabpanel],.scheduling-view-control').count(),0)
        self.assertEqual(await self.page.locator('[data-scheduling-kpi]').count(),4)
        self.assertLessEqual(await self.page.locator('#scheduling-preview tbody tr').count(),5)
        self.assertEqual(await self.page.locator('.dispatch-schedule-chart').count(),0)
        self.assertIn('Asignación aprobada · viajes y vehículos fijos',await root.inner_text())
        self.assertIn('Plan con excepciones',await self.page.locator('#dispatch-hero').inner_text())
        button=self.page.locator('[data-scheduling-advanced-toggle]')
        for width,height in [(1440,1000),(768,1024),(390,844),(320,568)]:
            await self.page.set_viewport_size({'width':width,'height':height})
            await self.page.emulate_media(reduced_motion='reduce')
            await button.scroll_into_view_if_needed();await button.focus()
            before=await self.page.evaluate('({url:location.href,y:scrollY})')
            await button.press('Enter')
            self.assertEqual(await button.get_attribute('aria-expanded'),'true')
            self.assertIn('Ocultar análisis avanzado',await button.inner_text())
            state=await self.page.evaluate('''()=>{const a=document.querySelector('[data-scheduling-advanced]'),b=a.querySelector('button'),c=a.querySelector('[data-scheduling-advanced-content]'),s=getComputedStyle(a.querySelector('.scheduling-advanced__chevron'));return {hidden:c.hidden,active:a.classList.contains('is-open'),controls:b.getAttribute('aria-controls')===c.id,rotation:s.transform,transition:s.transitionDuration,width:document.documentElement.scrollWidth,viewport:innerWidth,y:scrollY,url:location.href};}''')
            self.assertFalse(state['hidden']);self.assertTrue(state['active']);self.assertTrue(state['controls'])
            self.assertNotEqual(state['rotation'],'none');self.assertEqual(state['transition'],'0s')
            self.assertLessEqual(state['width'],state['viewport']+1)
            self.assertEqual(state['url'],before['url']);self.assertLessEqual(abs(state['y']-before['y']),2)
            await button.press('Space')
            self.assertEqual(await button.get_attribute('aria-expanded'),'false')
            self.assertIn('Mostrar análisis avanzado',await button.inner_text())
        await self.page.locator('[data-scheduling-full-plan]').click()
        await self.page.wait_for_function("document.activeElement?.id==='scheduling-full-plan'")
        self.assertEqual(await self.page.locator('#scheduling-full-plan tbody tr').count(),len(original['result_json']['scenarios']['selected']['trips']))
        await self.page.reload();await button.wait_for()
        self.assertEqual(await button.get_attribute('aria-expanded'),'true')
        self.assertIn('Ocultar análisis avanzado',await button.inner_text())
        self.assertEqual(self.f['runs']['scheduling'],original)
        self.assertEqual(self.execution_bodies,[]);self.assertEqual(self.comparative_posts,0);self.assertEqual(self.explain_calls,0)

    async def test_d2_v21_timeline_vehicle_rows_sla_and_release_dates(self):
        await self.open('decision-dashboard','logistics_scheduling',self.f['ids']['scheduling'])
        option=await self.page.locator('.scheduling-timeline-chart').evaluate('''el=>{const o=window.DationCharts.getInstanceByDom(el).getOption();return {rows:o.yAxis[0].data,data:o.series.filter((_,i)=>i%2).flatMap(s=>s.data).filter(d=>d.trip_id),detail:o.tooltip[0].formatter({data:o.series[1].data[0]}),type:o.series[1].type};}''')
        trips=self.f['runs']['scheduling']['result_json']['scenarios']['selected']['trips']
        self.assertEqual(set(option['rows']),{t['vehicle_id'] for t in trips});self.assertEqual(len(option['data']),len(trips));self.assertEqual(option['type'],'bar')
        self.assertIn('Disponible:',option['detail']);self.assertIn('Llegada:',option['detail']);self.assertIn('Espera:',option['detail'])
        await self.page.locator('[data-scheduling-advanced-toggle]').click()
        self.assertEqual(await self.page.locator('#scheduling-service tbody tr').count(),len(self.f['runs']['scheduling']['result_json']['scenarios']['selected']['order_outcomes']))
        await self.page.locator('[data-scheduling-wait-sort]').select_option('resource')
        ids=await self.page.locator('#scheduling-waits tbody tr td:first-of-type').all_text_contents()
        self.assertEqual(ids,sorted(ids));self.assertEqual(await self.page.locator('#scheduling-rules').count(),0)
        await self.page.locator('#scheduling-full-plan summary').first.click()
        self.assertIn(trips[0]['loads'][0]['order_id'],await self.page.locator('#scheduling-full-plan').inner_text())
        self.assertEqual(self.execution_bodies,[])

    async def test_d2_v21_no_sla_null_dates_custom_window_and_rules(self):
        r=self.f['runs']['scheduling']['result_json'];r['analysis']['sla_enabled']=False
        r['scenarios']['selected']['metrics']['on_time_rate']=None
        r['analysis']['planning_window'].update(start='2026-10-01',end='2026-12-31')
        r['analysis']['focus_rules']=[{'id':'R1','field':'vehicle_id','values':['VEH-005'],'action':'prioritize','planning_window_start':'2026-10-01','planning_window_end':None,'matched_trip_count':1,'matched_trip_ids':['A-00018']}]
        r['analysis']['focused_trip_count']=1
        r['scenarios']['selected']['order_outcomes'][0]['delivery_due_date']=None
        await self.open('decision-dashboard','logistics_scheduling',self.f['ids']['scheduling'])
        self.assertIn('Sin SLA',await self.page.locator('[data-scheduling-kpi="0"]').inner_text())
        self.assertNotIn('100%',await self.page.locator('#dispatch-hero').inner_text())
        self.assertIn('1 viajes',await self.page.locator('#dispatch-hero').inner_text())
        await self.page.locator('[data-scheduling-advanced-toggle]').click()
        self.assertIn('Sin SLA',await self.page.locator('#scheduling-service').inner_text())
        self.assertIn('VEH-005',await self.page.locator('#scheduling-rules').inner_text())
        self.assertIn('1 de oct de 2026',await self.page.locator('#scheduling-rules').inner_text())
        self.assertEqual(await self.page.locator('#scheduling-validation .is-warning').count(),0)

    async def test_d2_v21_ai_cache_generation_freshness_and_chat(self):
        self.saved_explanation={'id':'cached-D2','response_json':{'executive_summary':'Plan temporal cacheado','key_drivers':['Assignment bloqueada'],'caveats':['Revisar márgenes']}}
        await self.open('decision-dashboard','logistics_scheduling',self.f['ids']['scheduling'])
        button=self.page.locator('[data-explain]');self.assertEqual(self.explain_calls,0)
        await button.click();await self.page.get_by_text('Plan temporal cacheado',exact=True).wait_for()
        self.assertEqual(self.explain_calls,0)
        await self.page.locator('[data-ai-collapse]').click()
        self.assertEqual(await button.get_attribute('aria-expanded'),'false')
        self.saved_explanation_evidence='previous-evidence'
        await self.page.reload();await button.wait_for();await self.page.get_by_text('Hay evidencia más reciente',exact=True).wait_for()
        await button.click();await self.page.get_by_text('Synthetic explanation',exact=True).wait_for()
        self.assertEqual(self.explain_calls,1)
        await self.page.locator('[data-ai-ask]').click();await self.page.locator('.dispatch-chat:not([hidden])').wait_for()
        await self.page.keyboard.press('Escape');self.assertEqual(await self.page.locator('[data-chat]').get_attribute('aria-expanded'),'false')
        self.assertEqual(self.execution_bodies,[]);self.assertEqual(self.comparative_posts,0)

    async def test_d2_v21_ai_retry_approval_and_approved_state(self):
        self.explain_fail_once=True;self.approval_fail_once=True
        self.case['nodes']['logistics_scheduling']['status']='review'
        self.case['nodes']['logistics_scheduling']['approved_run_id']=None
        r=self.f['runs']['scheduling'];r['approved_at']=None;r['result_json']['decision_case']['status']='review'
        await self.open('decision-dashboard','logistics_scheduling',self.f['ids']['scheduling'])
        await self.page.locator('[data-explain]').click();await self.page.get_by_role('button',name='Reintentar resumen',exact=True).click()
        await self.page.get_by_text('Synthetic explanation',exact=True).wait_for();self.assertEqual(self.explain_calls,2)
        approve=self.page.locator('[data-approve-final]');await approve.click();await self.page.locator('[data-approval-error]:not([hidden])').wait_for()
        self.assertFalse(await approve.is_disabled());await approve.click()
        await self.page.wait_for_function("document.querySelector('[data-approve-final]').disabled")
        await self.page.locator('[data-scheduling-hero-status]').filter(has_text='Planificación aprobada').wait_for()
        self.assertEqual(self.approval_calls,2);self.assertTrue(await self.page.locator('[data-approve-toolbar]').is_disabled())
        await self.page.reload();await self.page.locator('.scheduling-dashboard-v2').wait_for()
        self.assertTrue(await self.page.locator('[data-approve-final]').is_disabled());self.assertEqual(self.execution_bodies,[])

    async def test_d2_v21_stale_assignment_preserves_evidence_and_blocks_approval(self):
        self.case['nodes']['logistics_scheduling']['status']='stale'
        await self.open('decision-dashboard','logistics_scheduling',self.f['ids']['scheduling'])
        self.assertIn('Evidencia desactualizada',await self.page.locator('[data-scheduling-hero-status]').inner_text())
        for selector in ('[data-approve-toolbar]','[data-approve-final]'):
            button=self.page.locator(selector)
            self.assertTrue(await button.count()==0 or await button.is_disabled())
        self.assertTrue(await self.page.locator('#scheduling-kpis').is_visible())
        await self.page.locator('[data-scheduling-advanced-toggle]').click()
        self.assertTrue(await self.page.locator('#scheduling-full-plan').is_visible())
        self.assertEqual(self.approval_calls,0)

    async def test_d2_v21_infeasible_never_recommends_or_approves(self):
        r=self.f['runs']['scheduling']['result_json'];r['scenarios']['selected']['feasible']=False
        r['engine']['solver']['status']='infeasible';r['scenarios']['selected']['solver']['status']='infeasible'
        await self.open('decision-dashboard','logistics_scheduling',self.f['ids']['scheduling'])
        await self.page.get_by_role('heading',level=1,name='No existe una planificación factible',exact=True).wait_for()
        self.assertTrue(await self.page.locator('[data-approve-toolbar]').is_disabled());self.assertTrue(await self.page.locator('[data-approve-final]').is_disabled())
        self.assertFalse(await self.page.locator('[data-scheduling-advanced]').is_visible())
        self.assertFalse(await self.page.locator('#scheduling-kpis').is_visible())
        self.assertEqual(await self.page.locator('.dispatch-chart').count(),0)
        self.assertEqual(self.approval_calls,0);self.assertEqual(self.execution_bodies,[]);self.assertEqual(self.explain_calls,0)


    async def test_d1_d2_upper_geometry_and_visible_headings_are_normalized(self):
        original_case=copy.deepcopy(self.case);original_runs=copy.deepcopy(self.f['runs'])
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            for state in ('review','approved'):
                reference=None
                for kind in ('assignment','scheduling'):
                    self.case.clear();self.case.update(copy.deepcopy(original_case))
                    for key in self.f['runs']:
                        self.f['runs'][key].clear();self.f['runs'][key].update(copy.deepcopy(original_runs[key]))
                    run=self.f['runs'][kind];node=self.case['nodes']['logistics_'+kind]
                    node.update(status=state,approved_run_id=run['id'] if state=='approved' else None)
                    run['approved_at']='2026-10-10T12:00:00Z' if state=='approved' else None
                    run['result_json']['decision_case']['status']=state
                    metrics=copy.deepcopy(run['result_json']['scenarios']['selected']['metrics'])
                    await self.open('decision-dashboard','logistics_'+kind,run['id'])
                    await self.page.locator('#'+kind+'-context').get_by_role('heading',name='Contexto',exact=True).wait_for()
                    await self.page.get_by_role('heading',name='Indicadores de la '+('asignación' if kind=='assignment' else 'planificación'),exact=True).wait_for()
                    self.assertEqual(await self.page.locator('.'+('assignment-context__grid' if kind=='assignment' else 'scheduling-context__grid')+' article').count(),4)
                    self.assertEqual(await self.page.locator('[data-executive-kpi]' if kind=='assignment' else '[data-scheduling-kpi]').count(),4)
                    if kind=='scheduling':
                        context=await self.page.locator('#scheduling-context').inner_text()
                        for redundant in ('Contexto heredado','Heredados de Assignment','Órdenes heredadas'):self.assertNotIn(redundant,context)
                        self.assertIn('Assignment bloqueada',context)
                    else:self.assertIn('Objetivo de la corrida',await self.page.locator('#dispatch-hero').inner_text())
                    geometry=await self.page.evaluate('''()=>{
                      const hero=document.querySelector('#dispatch-hero'),h=hero.getBoundingClientRect(),toolbar=hero.querySelector('[data-toolbar-placement="hero"]'),t=toolbar.getBoundingClientRect();
                      const style=(n,keys)=>Object.fromEntries(keys.map(k=>[k,getComputedStyle(n)[k]]));
                      const type=n=>style(n,['fontSize','fontWeight','lineHeight','letterSpacing','marginTop','marginBottom']);
                      const card=q=>{const n=document.querySelector(q),r=n.getBoundingClientRect();return {width:r.width,height:r.height,...style(n,['minHeight','padding','border','borderRadius','backgroundColor'])};};
                      const control=q=>{const n=toolbar.querySelector(q),r=n.getBoundingClientRect(),i=n.querySelector('svg').getBoundingClientRect();return {width:r.width,height:r.height,padding:getComputedStyle(n).padding,border:getComputedStyle(n).border,radius:getComputedStyle(n).borderRadius,font:type(n),gap:getComputedStyle(n).gap,icon:[i.width,i.height]};};
                      const grid=document.querySelector('.assignment-context__grid,.scheduling-context__grid'),kpi=document.querySelector('.assignment-essential__kpi-strip,.scheduling-kpis');
                      const status=hero.querySelector('[data-assignment-hero-status],[data-scheduling-hero-status]'),sr=status.getBoundingClientRect();
                      const primary=toolbar.querySelector('[data-approve-toolbar]'),pr=primary?.getBoundingClientRect(),rerun=toolbar.querySelector('[data-rerun]').getBoundingClientRect(),last=toolbar.querySelector('[data-more-menu]').getBoundingClientRect();
                      return {heroHeight:h.height,heroMin:getComputedStyle(hero).minHeight,padding:getComputedStyle(hero).padding,toolbarY:t.y-h.y,toolbarHeight:t.height,divider:getComputedStyle(toolbar).borderTopWidth,
                        title:type(hero.querySelector('h1')),headline:type(hero.querySelector('.assignment-hero__headline,.scheduling-hero__headline')),
                        status:{height:sr.height,...style(status,['padding','borderRadius','fontSize','fontWeight','lineHeight','gap'])},copy:hero.querySelector('.assignment-hero__content,[data-scheduling-hero]').getBoundingClientRect().width,
                        controls:['[data-rerun]','[data-export-menu]>summary','[data-more-menu]>summary'].map(control),primaryHeight:pr?.height,
                        primaryLeft:pr?pr.left-t.left:null,toolsRight:t.right-last.right,grouped:rerun.right<=last.left+1,
                        context:card('.assignment-context__grid article,.scheduling-context__grid article'),kpi:card('[data-executive-kpi],[data-scheduling-kpi]'),
                        columns:getComputedStyle(grid).gridTemplateColumns.split(' ').length,kpiColumns:getComputedStyle(kpi).gridTemplateColumns.split(' ').length,
                        overflow:document.documentElement.scrollWidth>innerWidth};
                    }''')
                    self.assertFalse(geometry['overflow'],(width,state,kind,geometry))
                    expected_columns=4 if width>1100 else 1 if width<=600 else 2
                    self.assertEqual(geometry['columns'],expected_columns);self.assertEqual(geometry['kpiColumns'],expected_columns)
                    self.assertEqual(geometry['divider'],'1px')
                    if width>1100:
                        self.assertAlmostEqual(geometry['primaryLeft'],0,delta=1);self.assertAlmostEqual(geometry['toolsRight'],0,delta=1);self.assertTrue(geometry['grouped'])
                    if width<=760:self.assertTrue(all(abs(c['height']-geometry['primaryHeight'])<.25 for c in geometry['controls']))
                    if reference:
                        for key in ('heroMin','padding','title','headline','status','controls','context','kpi'):
                            self.assertEqual(geometry[key],reference[key],(width,state,key,geometry[key],reference[key]))
                        self.assertAlmostEqual(geometry['copy'],reference['copy'],delta=.25)
                        if width>=768:
                            self.assertAlmostEqual(geometry['heroHeight'],reference['heroHeight'],delta=.5)
                            self.assertAlmostEqual(geometry['toolbarY'],reference['toolbarY'],delta=.5)
                    reference=geometry
                    actual=await self.page.evaluate('window.DationDispatch.getWorkspace().run.result_json.scenarios.selected.metrics')
                    self.assertEqual(actual,metrics)
        self.assertEqual(self.execution_bodies,[]);self.assertEqual(self.explain_calls,0);self.assertEqual(self.comparative_posts,0);self.assertEqual(self.approval_calls,0)

    async def test_d1_d2_hero_grows_for_objective_and_tools_align_without_approval(self):
        await self.page.set_viewport_size({'width':1440,'height':1000});await self.dashboard()
        hero=self.page.locator('#dispatch-hero');original=await hero.bounding_box()
        details=hero.locator('.assignment-essential__objective');await details.locator('summary').click()
        self.assertTrue(await details.evaluate('el=>el.open'))
        await details.evaluate('''el=>{const p=document.createElement('p');p.textContent=('Detalle de las prioridades publicadas de esta corrida. ').repeat(40);el.append(p)}''')
        expanded=await hero.bounding_box();self.assertGreater(expanded['height'],original['height'])
        self.assertTrue(await details.evaluate('el=>el.getBoundingClientRect().bottom<=el.closest("#dispatch-hero").getBoundingClientRect().bottom'))
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        for kind in ('assignment','scheduling'):
            self.case['nodes']['logistics_'+kind]['status']='stale'
            await self.open('decision-dashboard','logistics_'+kind,self.f['ids'][kind])
            toolbar=self.page.locator('[data-toolbar-placement=hero]')
            self.assertEqual(await toolbar.locator('[data-approve-toolbar]').count(),0)
            aligned=await toolbar.evaluate('''el=>Math.abs(el.getBoundingClientRect().right-el.querySelector('[data-more-menu]').getBoundingClientRect().right)<1''')
            self.assertTrue(aligned)
        self.assertEqual(self.approval_calls,0);self.assertEqual(self.execution_bodies,[])


    async def test_d1_d2_normalized_hero_keeps_approval_reconfigure_export_and_details(self):
        original_case=copy.deepcopy(self.case);original_runs=copy.deepcopy(self.f['runs'])
        for kind in ('assignment','scheduling'):
            self.case.clear();self.case.update(copy.deepcopy(original_case))
            for key in self.f['runs']:
                self.f['runs'][key].clear();self.f['runs'][key].update(copy.deepcopy(original_runs[key]))
            run=self.f['runs'][kind];node=self.case['nodes']['logistics_'+kind]
            node.update(status='review',approved_run_id=None);run['approved_at']=None;run['result_json']['decision_case']['status']='review'
            selected=copy.deepcopy(run['result_json']['scenarios']['selected'])
            await self.open('decision-dashboard','logistics_'+kind,run['id'])
            await self.page.locator('[data-export-menu] summary').click()
            async with self.page.expect_download() as output:await self.page.locator('[data-export-csv]').click()
            download=await output.value;self.assertIn('planificacion' if kind=='scheduling' else 'assignment',download.suggested_filename)
            csv=Path(await download.path()).read_text();self.assertIn(selected['trips'][0]['trip_id'],csv)
            await self.page.locator('[data-export-menu] summary').click()
            async with self.page.expect_download() as output:await self.page.locator('[data-export-json]').click()
            self.assertEqual(json.loads(Path(await (await output.value).path()).read_text())['scenarios']['selected'],selected)
            more=self.page.locator('[data-more-menu] summary');await more.click();await self.page.locator('[data-run-details]').click()
            drawer=self.page.locator('[data-run-drawer]');await drawer.wait_for(state='visible')
            self.assertIn(run['id'],await drawer.inner_text());await self.page.keyboard.press('Escape')
            self.assertFalse(await drawer.is_visible());self.assertTrue(await more.evaluate('el=>el===document.activeElement'))
            await self.page.locator('[data-rerun]').click()
            await self.page.locator('[data-scheduling-review]' if kind=='scheduling' else '[data-config-review]').wait_for(state='visible')
            self.assertEqual(self.execution_bodies,[])
            await self.open('decision-dashboard','logistics_'+kind,run['id'])
            approve=self.page.locator('[data-approve-toolbar]');await approve.click()
            await self.page.wait_for_function("label=>{const b=document.querySelector('[data-approve-toolbar]');return b?.disabled&&b.textContent.includes(label)}",arg='Planificación aprobada' if kind=='scheduling' else 'Decisión aprobada')
            self.assertIn('Planificación aprobada' if kind=='scheduling' else 'Decisión aprobada',await approve.inner_text())
            actual=await self.page.evaluate('window.DationDispatch.getWorkspace().run.result_json.scenarios.selected')
            self.assertEqual(actual,selected)
        self.assertEqual(self.approval_calls,2);self.assertEqual(self.execution_bodies,[]);self.assertEqual(self.explain_calls,0);self.assertEqual(self.comparative_posts,0)


    async def test_workspace_settings_retry_conflict_readonly_and_tab_history(self):
        self.settings_failure=True
        await self.open('logistics-map')
        await self.nav('settings')
        root=self.page.locator('[data-workspace-settings]')
        await root.get_by_text('Settings unavailable',exact=True).wait_for()
        self.settings_failure=False
        await root.get_by_role('button',name='Reintentar',exact=True).click()
        await root.get_by_label('Nombre del workspace').fill('Cambio sin aplicar')
        self.settings_conflict=True
        await root.get_by_role('button',name='Guardar datos generales',exact=True).click()
        await root.get_by_role('button',name='Actualizar configuración',exact=True).wait_for()
        self.assertTrue(await root.get_by_role('button',name='Guardar datos generales',exact=True).is_disabled())
        self.assertEqual(len([r for r in self.requests if r==('PATCH','/api/platform/settings')]),1)
        await root.get_by_role('button',name='Actualizar configuración',exact=True).click()
        await root.get_by_label('Nombre del workspace').wait_for()
        self.assertEqual(await root.get_by_label('Nombre del workspace').input_value(),'Synthetic workspace')
        self.access_role='viewer'
        await self.page.evaluate('window.dationSession.refresh()')
        await self.page.wait_for_function("document.querySelector('#workspace-name')?.disabled===true")
        self.assertEqual(await root.get_by_role('button',name='Guardar datos generales',exact=True).count(),0)
        await root.get_by_role('tab',name='Plan y facturación',exact=True).click()
        await root.get_by_role('heading',name='Plan Free',exact=True).wait_for()
        self.assertIn('No hay cobros',await root.inner_text())
        await self.page.reload()
        await root.get_by_role('heading',name='Plan Free',exact=True).wait_for()
        self.assertIn('settings_tab=plan',self.page.url)

    async def test_workspace_home_empty_state_and_catalog_access(self):
        await self.page.goto(f'http://127.0.0.1:{self.port}/app')
        root=self.page.locator('[data-platform-home]')
        await root.get_by_role('heading',name='Accesos rápidos',exact=True).wait_for()
        self.assertEqual(await root.evaluate("el=>[...el.children].map(n=>n.tagName)"),['HEADER','SECTION','SECTION'])
        self.assertEqual(await root.locator('.platform-home__quick-link').count(),4)
        self.assertEqual(await root.locator('.platform-home__attention,.platform-home__case,.platform-activity').count(),0)
        self.assertIn('Synthetic',await root.locator('.platform-home__greeting').inner_text())
        await root.get_by_role('link',name='Explorar DDA',exact=True).click()
        await self.page.locator('[data-home-dda-catalog]').wait_for(state='visible')
        self.assertEqual(await self.page.evaluate('document.activeElement.id'),'dation-dda-title')
        self.assertEqual(urlparse(self.page.url).path,'/app')
        self.assertEqual(sum(path=='/api/platform/home' for _,path in self.requests),0)

    async def test_workspace_home_quick_access_routes_preserve_history(self):
        await self.page.goto(f'http://127.0.0.1:{self.port}/app')
        root=self.page.locator('[data-platform-home]')
        for label,view,path in [('Decision Center','platform-decisions','/app/decisions'),('Datos / Data Hub','platform-data','/app/data'),('Equipo','platform-team','/app/team'),('Configuración','settings','/app/settings')]:
            await root.get_by_role('heading',name='Accesos rápidos',exact=True).wait_for()
            await root.locator('.platform-home__quick').get_by_role('link',name=label,exact=True).click()
            await self.page.wait_for_function('(view)=>window.dationGetCurrentView()===view',arg=view)
            self.assertEqual(urlparse(self.page.url).path,path)
            await self.page.go_back()
        await root.get_by_role('heading',name='Accesos rápidos',exact=True).wait_for()
        self.assertFalse(any(method=='POST' and path in ('/api/runs','/api/decision-cases') for method,path in self.requests))

    async def test_home_center_keep_readable_headers_and_catalog_cta(self):
        await self.page.goto(f'http://127.0.0.1:{self.port}/app')
        root=self.page.locator('[data-platform-home]')
        await root.get_by_role('heading',name='Accesos rápidos',exact=True).wait_for()
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
            home_cta=await root.locator('.platform-hero-cta').first.bounding_box()
            if width>=1024:
                self.assertLessEqual(await root.locator('.d-page-description').evaluate('el=>{const range=document.createRange();range.selectNodeContents(el);return range.getClientRects().length}'),3)
            self.assertGreaterEqual(home_cta['height'],40 if width>=768 else 44)
            self.assertLessEqual(home_cta['x']+home_cta['width'],width)
            self.assertTrue(await self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
            await root.locator('.platform-home__quick').get_by_role('link',name='Decision Center',exact=True).click()
            center=self.page.locator('[data-platform-decisions]');await center.locator('.center-hero').wait_for()
            center_cta=await center.locator('.center-hero .platform-hero-cta').bounding_box()
            self.assertGreaterEqual(center_cta['height'],40 if width>=768 else 44)
            self.assertLessEqual(center_cta['x']+center_cta['width'],width)
            self.assertTrue(await self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
            await center.locator('.center-hero').get_by_role('button',name='Explorar DDA',exact=True).click()
            await root.get_by_role('heading',name='Accesos rápidos',exact=True).wait_for()
            self.assertEqual(await self.page.evaluate('document.activeElement.id'),'dation-dda-title')
        self.assertEqual(sum(path=='/api/platform/home' for _,path in self.requests),0)

    async def test_catalog_entitlements_cover_deep_links_revocation_and_reenable(self):
        self.ddas=[]
        await self.page.goto(f'http://127.0.0.1:{self.port}/app/ddas/logistics/dashboard?run_id={self.f["runs"]["assignment"]["id"]}')
        root=self.page.locator('[data-home-dda-catalog]')
        await root.locator('[data-dda-id=logistics][data-dda-entitlement=disabled]').wait_for()
        self.assertEqual(urlparse(self.page.url).path,'/app/ddas')
        self.assertEqual(await root.locator('[data-dda-id=logistics] button,a').count(),0)
        self.assertTrue(await self.page.locator('.asset-item').is_disabled())
        self.assertFalse(await self.page.locator('.asset-item .status-dot').is_visible())
        self.assertTrue(all(method=='GET' and path=='/api/platform/onboarding' for method,path in self.requests),self.requests)
        for width in (1440,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            self.assertTrue(await self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
        await root.locator('[data-dda-filter=supply-chain]').click()
        self.ddas=[{'workspace_id':'00000000-0000-4000-8000-00000000da71','dda_id':'logistics','status':'enabled'}]
        await self.page.evaluate('window.dationSession.refresh()')
        await root.locator('#home-open-logistics').wait_for()
        self.assertEqual(await root.locator('[data-dda-filter=supply-chain]').get_attribute('aria-pressed'),'true')
        await root.locator('#home-open-logistics').click();await self.page.locator('.dda-landing__hero').wait_for()
        self.ddas[0]['status']='disabled'
        await self.page.evaluate('window.dationSession.refresh()')
        await root.locator('[data-dda-id=logistics][data-dda-entitlement=disabled]').wait_for()
        await self.page.go_back();await root.wait_for(state='visible')
        await self.page.reload();await root.locator('[data-dda-entitlement=disabled]').wait_for()
        await self.page.locator('.nav [data-platform-view="platform-home"]').click()
        await self.page.locator('[data-platform-home] .platform-home__quick-link').first.wait_for()
        home=self.page.locator('[data-platform-home]')
        await home.get_by_role('link',name='Explorar DDA',exact=True).wait_for()
        self.assertTrue(await self.page.locator('.asset-item').is_disabled())
        self.ddas[0]['status']='enabled'
        await self.page.evaluate('window.dationSession.refresh()')
        await self.page.wait_for_function("document.querySelector('.asset-item')?.disabled===false")
        await home.get_by_role('link',name='Explorar DDA',exact=True).click()
        await root.locator('#home-open-logistics').wait_for()
        self.ddas[0]['status']='disabled'
        await self.page.evaluate('window.dationSession.refresh()')
        await root.locator('[data-dda-id=logistics][data-dda-entitlement=disabled]').wait_for()
        self.assertTrue(await self.page.locator('.asset-item').is_disabled())
        await self.nav('platform-home');await home.get_by_role('link',name='Explorar DDA',exact=True).wait_for()
        self.assertEqual(self.errors,[])

    async def test_catalog_fallback_keeps_disabled_entitlement_closed(self):
        self.ddas=[]
        await self.context.route('**/home-dda-catalog.mjs',lambda route:route.abort())
        await self.page.goto(f'http://127.0.0.1:{self.port}/app/ddas')
        await self.page.wait_for_function("!document.documentElement.classList.contains('d-session-loading')")
        self.assertTrue(await self.page.locator('#home-open-logistics').is_disabled())
        self.assertTrue(await self.page.locator('.asset-item').is_disabled())
        await self.page.evaluate("window.dationNavigate('logistics-data')")
        self.assertEqual(await self.page.evaluate('window.dationGetCurrentView()'),'inicio')
        self.assertTrue(all(method=='GET' and path=='/api/platform/onboarding' for method,path in self.requests),self.requests)

    async def test_data_hub_library_details_preview_history_and_responsive(self):
        self.hub_cases=[{'id':self.case['id'],'status':'active','created_at':'2026-10-18T12:00:00Z','label':'Semana 43','dda':'logistics'}]
        await self.page.goto(f'http://127.0.0.1:{self.port}/app/data')
        root=self.page.locator('[data-platform-data]');await root.get_by_role('table').wait_for()
        self.assertEqual(await root.get_by_role('heading',name='Data Hub',exact=True).count(),1)
        self.assertEqual(await root.get_by_role('columnheader').count(),9)
        self.assertEqual(await root.get_by_role('button',name='Data Packs',exact=True).count(),0)
        for text in ('Cargar datos','Reutilizar','Probar demo'):
            self.assertEqual(await root.get_by_role('button',name=text,exact=True).count(),0)
        await root.get_by_label('Tipo',exact=True).select_option('fleet');await self.page.wait_for_url('**data_type=fleet*')
        await self.page.wait_for_function("document.querySelector('[data-platform-data] tbody')?.children.length===1")
        self.assertEqual(await root.locator('[data-kpi=total] strong').inner_text(),'2')
        await root.get_by_label('Buscar por nombre de dataset o archivo').fill('missing-file')
        await root.get_by_role('button',name='Buscar',exact=True).click()
        await root.get_by_role('heading',name='No encontramos datasets con estos filtros.').wait_for()
        await root.get_by_role('button',name='Limpiar filtros',exact=True).first.click()
        await root.get_by_role('link',name=self.f['datasets']['orders']['label'],exact=True).click()
        await root.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
        self.assertFalse(any(path.endswith('/preview') for _,path in self.requests))
        await self.page.evaluate("async()=>{const {readHubResource}=await import('/static/js/platform/data-resource.mjs');window.DationDispatch.openDataHub({...readHubResource(location.href),casesOffset:25});}")
        await root.get_by_text('No hay Decision Cases en esta página.',exact=True).wait_for()
        await root.get_by_role('navigation',name='Paginación de Decision Cases vinculados').get_by_role('button',name='Anterior',exact=True).click()
        await root.get_by_role('link',name='Ver Decision Case',exact=True).wait_for()
        count=sum(path=='/api/platform/data/datasets' for _,path in self.requests)
        self.assertEqual(await root.locator('tr[aria-selected=true]').count(),1)
        icons=await root.locator('.hub-icon svg').evaluate_all('els=>els.map(el=>({stroke:getComputedStyle(el).stroke,fill:getComputedStyle(el).fill}))')
        self.assertTrue(icons);self.assertTrue(all(i['stroke']!='none' and i['fill']=='none' for i in icons),icons)
        theme=(Path(__file__).parent/'theme_audit.js').read_text()
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000});await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
            probe=await self.page.evaluate(theme);self.assertFalse(probe['overflow'],probe);self.assertEqual(probe['failures'],[],probe)
        await root.locator('summary',has_text='Vista previa').click()
        await root.get_by_text('Filas 1–5',exact=True).wait_for()
        await root.get_by_role('button',name='Más filas',exact=True).click();await root.get_by_text('Filas 6–10',exact=True).wait_for()
        self.assertEqual(sum(path=='/api/platform/data/datasets' for _,path in self.requests),count)
        await root.get_by_role('link',name='Ver Decision Case',exact=True).click()
        await self.page.locator('[data-platform-decisions] .center-drawer:visible').get_by_role('heading',name='Cadena de decisiones').wait_for()
        self.assertIn('center_case_id='+self.case['id'],self.page.url)
        await self.page.go_back();await root.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
        await self.page.reload();await root.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
        await self.page.keyboard.press('Escape');await self.page.wait_for_function("!new URL(location.href).searchParams.has('dataset_id')")
        await self.page.go_back();await root.get_by_role('heading',name='Información del dataset',exact=True).wait_for()
        self.assertEqual(self.errors,[])

    async def test_data_hub_empty_failure_readonly_and_legacy_links(self):
        self.hub_failure=True
        await self.page.goto(f'http://127.0.0.1:{self.port}/app/data')
        root=self.page.locator('[data-platform-data]');await root.get_by_role('heading',name='No se pudo abrir Data Hub').wait_for()
        self.hub_failure=False;self.hub_rows={}
        await root.get_by_role('button',name='Reintentar',exact=True).click()
        await root.get_by_role('heading',name='Todavía no hay datos en este Workspace.').wait_for()
        self.access_role='viewer';self.ddas=[];await self.page.evaluate('window.dationSession.refresh()')
        self.assertEqual(await root.get_by_role('button',name='Cargar datos',exact=True).count(),0)
        for suffix in ('data_tab=packs','pack_orders_id='+self.f['ids']['orders']+'&pack_fleet_id='+self.f['ids']['fleet']):
            await self.page.goto(f'http://127.0.0.1:{self.port}/app/data?'+suffix)
            await root.get_by_role('heading',name='Todavía no hay datos en este Workspace.').wait_for()
            self.assertNotIn('pack_',self.page.url);self.assertNotIn('data_tab',self.page.url)
        await root.get_by_role('button',name='Ir a Decision Center',exact=True).click()
        await self.page.locator('[data-platform-decisions] h1').wait_for()
        self.assertFalse(any(method!='GET' and '/api/platform/data/' in path for method,path in self.requests))

    async def test_data_hub_archive_delete_retry_and_text_safety(self):
        orders=self.f['ids']['orders'];self.hub_rows[orders]['label']='<img src=x onerror=alert(1)>'
        await self.page.goto(f'http://127.0.0.1:{self.port}/app/data?dataset_id={orders}')
        root=self.page.locator('[data-platform-data]');drawer=root.locator('.hub-drawer:visible')
        await drawer.get_by_role('heading',name='<img src=x onerror=alert(1)>',exact=True).wait_for()
        self.assertEqual(await root.locator('img[src=x]').count(),0)
        async def menu(label):
            await drawer.get_by_role('button',name='Acciones de <img src=x onerror=alert(1)>',exact=True).click()
            await drawer.get_by_role('menuitem',name=label,exact=True).click()
        await menu('Archivar');await self.page.get_by_role('dialog').get_by_role('button',name='Archivar dataset',exact=True).click()
        await drawer.get_by_text('Archivado',exact=True).first.wait_for()
        self.hub_delete_failure=True
        await menu('Eliminar definitivamente');await self.page.get_by_role('dialog').get_by_role('button',name='Eliminar definitivamente',exact=True).click()
        await drawer.get_by_text('Eliminación pendiente',exact=True).first.wait_for()
        await menu('Completar eliminación');await self.page.get_by_role('dialog').get_by_role('button',name='Completar eliminación',exact=True).click()
        await self.page.wait_for_function("!new URL(location.href).searchParams.has('dataset_id')")
        self.assertEqual(sum(method=='DELETE' for method,path in self.requests if path.startswith('/api/platform/data/')),2)
        self.assertEqual(self.errors,[])

    async def test_data_hub_incomplete_upload_cleanup_is_explicit_and_text_safe(self):
        self.hub_incomplete=[{'id':'00000000-0000-4000-8000-000000000089','filename':'<img src=x onerror=alert(1)>.csv','created_at':'2026-10-18T12:00:00Z','status':'failed'}]
        await self.page.goto(f'http://127.0.0.1:{self.port}/app/data');root=self.page.locator('[data-platform-data]')
        await root.locator('.hub-recovery summary').wait_for()
        self.assertFalse(any(method=='POST' and '/uploads/' in path for method,path in self.requests))
        await root.locator('.hub-recovery summary').click()
        self.assertEqual(await root.locator('img[src=x]').count(),0)
        await root.get_by_role('button',name='Descartar archivo incompleto',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Descartar archivo incompleto',exact=True).click()
        await root.locator('.hub-recovery').wait_for(state='hidden')
        self.assertEqual(len(self.hub_rows),2)
        self.assertEqual(sum(method=='POST' and '/uploads/' in path for method,path in self.requests),1)

    async def test_data_hub_stale_detail_cannot_replace_new_selection_or_navigate_after_leave(self):
        orders=self.f['ids']['orders'];fleet=self.f['ids']['fleet'];path='/api/platform/data/datasets/'+orders
        self.delay[path]=1
        await self.page.goto(f'http://127.0.0.1:{self.port}/app/data');root=self.page.locator('[data-platform-data]')
        await root.get_by_role('table').wait_for()
        await root.locator(f'[data-dataset-open="{orders}"]').click()
        await root.locator(f'[data-dataset-open="{fleet}"]').click()
        await root.get_by_role('heading',name=self.f['datasets']['fleet']['label'],exact=True).wait_for()
        await self.page.wait_for_timeout(1100)
        self.assertIn('dataset_id='+fleet,self.page.url)
        await self.nav('platform-home');await self.nav('platform-data')
        await root.get_by_role('table').wait_for()
        self.assertEqual(urlparse(self.page.url).path,'/app/data')
        self.assertFalse(any(method=='POST' and path.endswith('/reuse') for method,path in self.requests))

    async def test_data_hub_summary_filters_and_viewer_preserve_download(self):
        orders=self.f['ids']['orders'];self.hub_rows[orders]['archived_at']='2026-10-20T12:00:00Z'
        self.access_role='viewer'
        await self.page.goto(f'http://127.0.0.1:{self.port}/app/data');root=self.page.locator('[data-platform-data]')
        await root.get_by_role('table').wait_for()
        self.assertEqual(await root.locator('[data-kpi=total] strong').inner_text(),'2')
        await root.locator('[data-kpi=archived]').click();await self.page.wait_for_url('**data_state=archived*')
        await root.locator(f'[data-dataset-open="{orders}"]').click()
        drawer=root.locator('.hub-drawer:visible');await drawer.get_by_role('heading',name='Información del dataset').wait_for()
        self.assertEqual(await drawer.get_by_role('link',name='Descargar',exact=True).count(),1)
        await drawer.get_by_role('button',name='Acciones de ',exact=False).click()
        self.assertEqual(await drawer.get_by_role('menuitem',name='Restaurar',exact=True).count(),0)
        self.assertEqual(await drawer.get_by_role('menuitem',name='Eliminar definitivamente',exact=True).count(),0)
        await self.page.keyboard.press('Escape')
        await root.get_by_role('button',name='Cerrar detalle del dataset').click()
        await root.locator('[data-kpi=total]').click();await self.page.wait_for_url('**data_state=all*')
        await self.page.wait_for_function("document.querySelector('[data-platform-data] tbody')?.children.length===2")
        await root.get_by_label('Validación',exact=True).select_option('unknown')
        await root.get_by_role('heading',name='No encontramos datasets con estos filtros.').wait_for()
        self.assertEqual(await root.locator('[data-kpi=total] strong').inner_text(),'2')

    async def test_data_hub_drawer_keyboard_focus_and_no_list_refetch(self):
        await self.page.set_viewport_size({'width':390,'height':844})
        await self.page.goto(f'http://127.0.0.1:{self.port}/app/data');root=self.page.locator('[data-platform-data]')
        trigger=root.locator('[data-dataset-open]').first;await trigger.wait_for();await trigger.focus();await self.page.keyboard.press('Enter')
        drawer=root.get_by_role('dialog');await drawer.get_by_role('heading',name='Información del dataset').wait_for()
        self.assertEqual(await drawer.get_attribute('aria-labelledby'),'hub-drawer-title')
        count=sum(path=='/api/platform/data/datasets' for _,path in self.requests)
        close=drawer.get_by_role('button',name='Cerrar detalle del dataset');await close.focus();await self.page.keyboard.press('Shift+Tab')
        self.assertTrue(await drawer.evaluate('el=>el.contains(document.activeElement)'))
        await self.page.keyboard.press('Escape');await drawer.wait_for(state='hidden')
        self.assertTrue(await trigger.evaluate('el=>el===document.activeElement'))
        self.assertEqual(sum(path=='/api/platform/data/datasets' for _,path in self.requests),count)
        await self.page.go_back();await drawer.get_by_role('heading',name='Información del dataset').wait_for()
        await self.page.go_forward();await drawer.wait_for(state='hidden')

    async def test_decision_center_search_detail_disclosure_label_and_archive(self):
        self.center_label='Semana 43 · <img src=x onerror=window.__bad=1>'
        await self.open('logistics-map');await self.nav('platform-decisions')
        root=self.page.locator('[data-platform-decisions]')
        await root.get_by_role('table').wait_for()
        for width in (1440,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            self.assertFalse((await self.page.evaluate((ROOT/'tests/browser/theme_audit.js').read_text()))['overflow'])
        await root.get_by_label('Buscar por ID o etiqueta').fill('Semana 43')
        await root.get_by_role('button',name='Buscar',exact=True).click()
        await self.page.wait_for_url('**center_q=Semana+43*')
        await root.get_by_role('link',name='Abrir',exact=True).click()
        await root.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
        self.assertEqual(await root.locator('img[src=x]').count(),0)
        self.assertTrue(await self.page.evaluate('window.__bad===undefined'))
        node=root.locator('[data-center-node=logistics_assignment]')
        await node.locator('summary',has_text='Historial de corridas').click()
        await node.locator('.center-run-list').wait_for()
        await self.page.reload();await node.locator('.center-run-list').wait_for()
        await root.locator('.center-drawer:visible').get_by_role('button',name='Acciones de '+('DC-'+self.case['id'][:8].upper()),exact=True).click()
        await root.get_by_role('menuitem',name='Editar nombre',exact=True).click()
        dialog=self.page.get_by_role('dialog');await dialog.get_by_label('Etiqueta opcional').fill('Semana 44')
        await dialog.get_by_role('button',name='Guardar',exact=True).click()
        await root.get_by_role('heading',name='Semana 44',exact=True).wait_for()
        await root.locator('.center-drawer:visible').get_by_role('button',name='Acciones de '+('DC-'+self.case['id'][:8].upper()),exact=True).click()
        await root.get_by_role('menuitem',name='Archivar',exact=True).click()
        await self.page.get_by_role('dialog').get_by_role('button',name='Archivar',exact=True).click()
        await self.page.wait_for_url('**center_filter=archived*')
        self.assertEqual(await root.locator('dialog[open]').count(),0)
        await self.page.reload();await root.get_by_role('link',name='Abrir',exact=True).click()
        await root.locator('.center-drawer:visible .center-status[data-state=archived]').wait_for()
        self.assertEqual(await root.get_by_role('link',name='Continuar',exact=True).get_attribute('aria-disabled'),'true')
        await root.locator('.center-drawer:visible').get_by_role('button',name='Acciones de '+('DC-'+self.case['id'][:8].upper()),exact=True).click()
        await root.get_by_role('menuitem',name='Restaurar',exact=True).click()
        await self.page.get_by_role('dialog',name='Restaurar caso').get_by_role('button',name='Restaurar',exact=True).click()
        await self.page.wait_for_url('**center_filter=all*')
        self.assertNotIn('center_q=',self.page.url)
        await root.get_by_role('table').wait_for()
        self.assertEqual(self.center_edits,3)

    async def test_decision_center_failures_readonly_conflict_and_global_recovery(self):
        self.center_failure=True
        await self.open('logistics-map');await self.nav('platform-decisions')
        root=self.page.locator('[data-platform-decisions]')
        await root.get_by_role('heading',name='No pudimos cargar Decision Center.',exact=True).wait_for()
        self.center_failure=False;await root.get_by_role('button',name='Reintentar',exact=True).click()
        await root.get_by_role('link',name='Abrir',exact=True).click()
        await root.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
        self.center_conflict=True
        await root.locator('.center-drawer:visible').get_by_role('button',name='Acciones de '+('DC-'+self.case['id'][:8].upper()),exact=True).click()
        await root.get_by_role('menuitem',name='Editar nombre',exact=True).click()
        dialog=self.page.get_by_role('dialog');await dialog.get_by_label('Etiqueta opcional').fill('Nuevo')
        await dialog.get_by_role('button',name='Guardar',exact=True).click()
        await dialog.get_by_role('alert').filter(has_text='El caso cambió').wait_for()
        self.assertEqual(self.center_edits,0)
        await self.page.keyboard.press('Escape')
        await root.get_by_role('button',name='Cerrar detalle del caso',exact=True).focus()
        await self.nav('platform-home');self.access_role='viewer';self.ddas[0]['status']='disabled'
        await self.page.reload();await self.page.locator('[data-platform-home] h1').wait_for()
        await self.nav('platform-decisions');await root.get_by_role('link',name='Abrir',exact=True).click()
        await root.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
        self.assertEqual(await root.get_by_role('button',name='Editar nombre',exact=True).count(),0)
        self.assertEqual(await root.get_by_role('link',name='Continuar',exact=True).get_attribute('aria-disabled'),'true')
        await self.page.goto(f'http://127.0.0.1:{self.port}/app/decisions?center_case_id=broken')
        await root.get_by_role('heading',name='No pudimos cargar Decision Center.',exact=True).wait_for()
        await root.get_by_role('button',name='Reintentar',exact=True).click()
        await root.get_by_role('table').wait_for()
        self.assertEqual(sum(method=='PATCH' and path.startswith('/api/platform/decisions') for method,path in self.requests),1)



    async def test_activity_case_late_response_is_disposed_after_navigation(self):
        self.activity_gate=asyncio.Event()
        await self.page.goto(f"http://127.0.0.1:{self.port}/app/decisions?center_case_id={self.case['id']}")
        root=self.page.locator('[data-platform-decisions]');panel=root.locator('[data-case-activity]')
        await self.page.wait_for_function("document.querySelector('[data-case-activity] .platform-activity')?.getAttribute('aria-busy')==='true'")
        for _ in range(100):
            if ('GET','/api/platform/activity') in self.requests:break
            await asyncio.sleep(.01)
        self.assertIn(('GET','/api/platform/activity'),self.requests)
        await self.nav('settings');await self.page.locator('[data-workspace-settings]').get_by_label('Nombre del workspace').wait_for()
        self.activity_gate.set();self.activity_gate=None;await self.page.wait_for_timeout(100)
        self.assertEqual(await self.page.evaluate('window.dationGetCurrentView()'),'settings')
        self.assertEqual(await panel.locator('.platform-activity [role=status]').inner_text(),'Cargando actividad…')
        self.delay['/api/platform/activity']=.01
        await self.page.evaluate("id=>window.DationDispatch.openDecisionCenter({caseId:id})",self.case['id'])
        await panel.get_by_text('Todavía no hay eventos registrados. Las nuevas acciones aparecerán acá.',exact=True).wait_for()
        # One workspace feed and one selected-Case feed on each entry.
        self.assertEqual(len([r for r in self.requests if r==('GET','/api/platform/activity')]),4)

    async def test_center_v2_kpis_and_docked_or_modal_drawer_preserve_portfolio(self):
        self.center_label='Semana 43 · Centro'
        self.center_summary={'active_cases':42,'in_review':8,'pending_approval':3,'approved':17}
        await self.open('logistics-map');await self.nav('platform-decisions')
        root=self.page.locator('[data-platform-decisions]')
        await root.get_by_role('table').wait_for()
        self.assertEqual(await root.get_by_role('heading',name='Decision Center',exact=True).count(),1)
        self.assertEqual(await root.locator('[data-kpi=active_cases] strong').inner_text(),'42')
        await root.get_by_role('button',name='Ver pendientes',exact=True).click()
        await self.page.wait_for_url('**center_filter=pending_approval*')
        await root.get_by_role('button',name='Limpiar filtros',exact=True).click()
        await self.page.wait_for_url('**center_filter=all*')
        before=await root.locator('.center-table-scroll').bounding_box()
        await root.get_by_role('link',name='Abrir',exact=True).click()
        await root.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
        self.assertEqual(await root.locator('tr[aria-selected=true]').count(),1)
        self.assertEqual(await root.locator('.center-table-scroll').bounding_box(),before)
        requests_before=sum(r==('GET','/api/platform/decisions') for r in self.requests)
        artifacts=Path('/workspace/dation-audit/platform-v2-phase2/visual') if Path('/workspace/dation-audit/platform-v2-phase2').exists() else None
        if artifacts:artifacts.mkdir(exist_ok=True)
        for width in (1440,1280,1024,768,390):
            await self.page.set_viewport_size({'width':width,'height':1000})
            await self.page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
            panel=root.locator('[data-center-sheet]')
            await panel.wait_for()
            audit=await self.page.evaluate((ROOT/'tests/browser/theme_audit.js').read_text())
            self.assertFalse(audit['overflow']);self.assertEqual(audit['failures'],[])
            self.assertEqual(await root.get_by_role('table').count(),1)
            self.assertTrue(await panel.evaluate('n=>n.open'))
            await panel.get_by_role('button',name='Cerrar detalle del caso').focus()
            await self.page.keyboard.press('Shift+Tab')
            self.assertTrue(await panel.evaluate('n=>n.contains(document.activeElement)'))
            if artifacts:
                await panel.get_by_role('button',name='Cerrar detalle del caso').focus()
                await panel.evaluate('n=>n.scrollTop=0')
                await self.page.screenshot(path=str(artifacts/f'drawer-{width}.png'),full_page=True)
        await self.page.keyboard.press('Escape')
        await self.page.wait_for_function("!new URL(location.href).searchParams.has('center_case_id')")
        await self.page.go_back()
        await root.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
        await self.page.reload()
        await root.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for()
        self.assertIn('center_case_id='+self.case['id'],self.page.url)
        self.assertGreaterEqual(sum(r==('GET','/api/platform/decisions') for r in self.requests),requests_before)
        self.assertFalse(any(method in ('POST','PUT','PATCH','DELETE') and path.startswith('/api/platform/decisions') for method,path in self.requests))

    async def test_center_assignment_search_preserves_both_selections_and_explicit_clear(self):
        alice='10000000-0000-4000-8000-000000000011'
        bruno='10000000-0000-4000-8000-000000000012'
        people=[{'user_id':alice,'name':'Alice','active':True},{'user_id':bruno,'name':'Bruno','active':True}]
        writes=[]
        async def candidates(route):
            q=parse_qs(urlparse(route.request.url).query).get('q',[''])[0].lower()
            await route.fulfill(content_type='application/json',body=json.dumps({'members':[p for p in people if q in p['name'].lower()]}))
        async def assign(route):
            writes.append(json.loads(route.request.post_data))
            await route.fulfill(content_type='application/json',body='{}')
        await self.context.route('**/api/platform/team?**',candidates)
        await self.context.route('**/api/platform/decisions/*/responsibilities/logistics_assignment',assign)
        await self.open('logistics-map');await self.nav('platform-decisions')
        root=self.page.locator('[data-platform-decisions]')
        await root.get_by_role('link',name='Abrir',exact=True).click()
        await root.locator('.center-drawer:visible .center-drawer__content>.center-responsibilities').get_by_role('button',name='Asignar responsable · Asignación de carga',exact=True).click()
        dialog=self.page.get_by_role('dialog');owner=dialog.get_by_label('Responsable',exact=True);approver=dialog.get_by_label('Aprobador asignado',exact=True)
        async def ready():
            await self.page.wait_for_function("!document.querySelector('#center-owner_user_id').closest('form').querySelector('button[type=submit]').disabled")
        async def search(q):
            await dialog.get_by_label('Buscar personas por nombre o email').fill(q)
            await dialog.get_by_role('button',name='Buscar personas',exact=True).click();await ready()
        await ready();await owner.select_option(alice);await approver.select_option(bruno)
        await search('Bruno');self.assertEqual(await owner.input_value(),alice);self.assertEqual(await approver.input_value(),bruno)
        await search('Alice');self.assertEqual(await owner.input_value(),alice);self.assertEqual(await approver.input_value(),bruno)
        await owner.select_option('');await search('Bruno');self.assertEqual(await owner.input_value(),'')
        await search('Alice');await owner.select_option(alice)
        await dialog.get_by_role('button',name='Guardar responsables',exact=True).click()
        await root.get_by_text('Responsables actualizados.',exact=True).wait_for()
        self.assertEqual(writes,[{'expected_updated_at':None,'owner_user_id':alice,'approver_user_id':bruno}])

    async def test_center_v2_late_detail_does_not_reopen_closed_drawer(self):
        await self.open('logistics-map');await self.nav('platform-decisions')
        root=self.page.locator('[data-platform-decisions]');await root.get_by_role('table').wait_for()
        self.delay['/api/platform/decisions/'+self.case['id']]=.5
        await root.get_by_role('link',name='Abrir',exact=True).click()
        await root.get_by_role('button',name='Cerrar detalle del caso').click()
        await self.page.wait_for_timeout(700)
        self.assertNotIn('center_case_id',self.page.url)
        self.assertFalse(await root.locator('[data-center-drawer]').is_visible())
        self.assertEqual(await root.get_by_role('heading',name='Cadena de decisiones',exact=True).count(),0)
        self.assertEqual(await root.get_by_role('table').count(),1)

    async def test_home_v2_has_no_global_guide_or_demo_and_viewer_explores_catalog(self):
        self.access_role='viewer'
        self.onboarding_data={'available':True,'workspace_created':True,'explored_at':None,'data_ready':False,'first_decision_completed':False,'logistics_enabled':True}
        self.home_data['onboarding']=copy.deepcopy(self.onboarding_data)
        await self.page.goto(f'http://127.0.0.1:{self.port}/app')
        root=self.page.locator('[data-platform-home]');await root.get_by_role('heading',name='Accesos rápidos').wait_for()
        self.assertEqual(await root.locator('[data-onboarding-step],.d-onboarding').count(),0)
        self.assertEqual(await root.get_by_role('button',name='Usar datos de ejemplo',exact=True).count(),0)
        self.assertEqual(await root.locator('.platform-home__hero-actions a').count(),2)
        await root.get_by_role('link',name='Explorar DDA',exact=True).click()
        await self.page.locator('#home-open-logistics').click()
        for _ in range(100):
            if self.onboarding_data['explored_at']:break
            await asyncio.sleep(.01)
        self.assertIsNotNone(self.onboarding_data['explored_at'])
        await self.nav('platform-home');await root.get_by_role('heading',name='Accesos rápidos').wait_for()
        await self.page.reload();await root.get_by_role('heading',name='Accesos rápidos').wait_for()
        self.assertEqual(await root.locator('[data-onboarding-step]').count(),0)
        self.assertEqual(sum(path.endswith('/onboarding/explore') and method=='POST' for method,path in self.requests),1)
        self.assertFalse(any(path.endswith('/onboarding/demo') for _,path in self.requests))

    async def test_onboarding_demo_late_response_does_not_leave_settings(self):
        self.onboarding_data={'available':True,'workspace_created':True,'explored_at':None,'data_ready':False,'first_decision_completed':False,'logistics_enabled':True}
        self.home_data['onboarding']=copy.deepcopy(self.onboarding_data);self.onboarding_gate=asyncio.Event()
        await self.open('logistics-data')
        root=self.page.locator('#dispatch-data-root');await root.get_by_role('button',name='Usar datos de ejemplo',exact=True).click()
        for _ in range(100):
            if ('POST','/api/platform/onboarding/demo') in self.requests:break
            await asyncio.sleep(.01)
        self.assertIn(('POST','/api/platform/onboarding/demo'),self.requests)
        await self.nav('settings');await self.page.locator('[data-workspace-settings]').get_by_label('Nombre del workspace').wait_for()
        self.onboarding_gate.set();self.onboarding_gate=None;await self.page.wait_for_timeout(100)
        self.assertEqual(await self.page.evaluate('window.dationGetCurrentView()'),'settings')
        await self.nav('logistics-data');await root.get_by_role('button',name='Usar datos de ejemplo',exact=True).wait_for()
        self.assertFalse(await root.get_by_role('button',name='Usar datos de ejemplo',exact=True).is_disabled())
        self.assertEqual(sum(method=='POST' and path.endswith('/onboarding/demo') for method,path in self.requests),1)

    async def test_foundation_dashboard_navigation_prefers_approved_over_later_candidate(self):
        from uuid import uuid4
        official=self.f['runs']['assignment'];candidate=copy.deepcopy(official);candidate['id']=str(uuid4());candidate['approved_at']=None
        candidate['result_json']['decision_case']['status']='review';self.runs[candidate['id']]=candidate
        node=self.case['nodes']['logistics_assignment']
        node.update(status='approved',approved_run_id=official['id'],latest_run_id=candidate['id'],run_id=candidate['id'])
        await self.open('decision-dashboard','logistics_scheduling',self.f['runs']['scheduling']['id'])
        await self.page.locator('button[data-decision-node=logistics_assignment]').click()
        await self.page.locator('.assignment-dashboard-v2').wait_for()
        self.assertEqual(parse_qs(urlparse(self.page.url).query)['run_id'],[official['id']])
        selected=self.page.locator('button[data-decision-node=logistics_assignment]')
        self.assertEqual(await selected.get_attribute('aria-current'),'page')
        self.assertEqual(await selected.get_attribute('data-status-tone'),'success')
        self.assertEqual(self.execution_bodies,[])

if __name__ == "__main__":
    unittest.main(verbosity=2)
