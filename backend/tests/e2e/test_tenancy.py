"""Release gate: actual API + PostgreSQL/RLS + RPC + private Storage + worker."""
import copy
import json
from uuid import uuid4
import unittest
import httpx
import jwt
from sandbox import Sandbox, wait_for
from fixtures import csv_input
from auth_fixture import USER_A, USER_B, VIEWER, DISABLED, token


class TenancyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=Sandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)

    def setUp(self):
        self.s.stop(self.s.worker)
        self.s.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events CASCADE;')
        self.a=self.s.api_client
        self.b=httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False,timeout=30)
        self.addCleanup(self.b.close)

    def checked(self,response,status=200):
        self.assertEqual(response.status_code,status,response.text[:1200]);return response.json()

    def upload(self,client,kind):
        return self.checked(client.post('/api/datasets/upload',params={'dataset_type':kind},files={'file':(kind+'.csv',csv_input(kind),'text/csv')}))['dataset']

    def case(self,client):
        orders,fleet=self.upload(client,'orders'),self.upload(client,'fleet');case=str(uuid4())
        self.checked(client.post('/api/decision-cases',json={'id':case,'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id']}))
        return case,orders,fleet

    def body(self,case,orders,fleet):
        return {'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id'],
            'decision_case':{'case_id':case,'node_id':'logistics_assignment'},'configuration':{'objective':'balanced'},
            'options':{'analysis_depth':'essential','total_time_limit_s':10,'solve_time_limit_s':2,'deterministic_limit':.05}}

    def test_01_identical_bytes_are_separate_and_all_cross_object_reads_fail(self):
        ca,oa,fa=self.case(self.a);cb,ob,fb=self.case(self.b)
        self.assertNotEqual(oa['id'],ob['id']);self.assertEqual(oa['sha256'],ob['sha256'])
        self.assertTrue(oa['storage_path'].startswith(self.s.workspace_a+'/'))
        self.assertTrue(ob['storage_path'].startswith(self.s.workspace_b+'/'))
        for client,other_case,other_data in ((self.a,cb,ob),(self.b,ca,oa)):
            for path in [f'/api/datasets/{other_data["id"]}/download',f'/api/datasets/{other_data["id"]}/profile',f'/api/decision-cases/{other_case}',f'/api/decision-cases/{other_case}/runs']:
                self.assertEqual(client.get(path).status_code,404,path)
            cases=self.checked(client.get('/api/decision-cases'))['cases']
            self.assertNotIn(other_case,[item['case']['id'] for item in cases])
            datasets=self.checked(client.get('/api/datasets',params={'type':'orders'}))['items']
            self.assertNotIn(other_data['id'],[item['id'] for item in datasets])
        self.assertEqual(self.a.get(f'/api/datasets/{oa["id"]}/download').content,csv_input('orders'))

    def test_02_defaults_and_parent_case_injections_cannot_cross_workspaces(self):
        ca,oa,fa=self.case(self.a);cb,ob,fb=self.case(self.b)
        for client,fleet in ((self.a,fa),(self.b,fb)):self.checked(client.post(f'/api/datasets/{fleet["id"]}/default'))
        rows=self.checked(self.s.db.get('datasets',params={'dataset_type':'eq.fleet'}))
        self.assertEqual(sum(bool(row['is_default']) for row in rows),2)
        for suffix in ['default','archive','unarchive','refresh-profile']:
            self.assertEqual(self.a.post(f'/api/datasets/{fb["id"]}/{suffix}').status_code,404,suffix)
        self.assertEqual(self.a.patch(f'/api/datasets/{fb["id"]}',json={'label':'intrusion'}).status_code,404)
        for payload in [dict(id=str(uuid4()),orders_dataset_id=ob['id'],fleet_dataset_id=fa['id']),dict(id=cb,orders_dataset_id=oa['id'],fleet_dataset_id=fa['id'])]:
            self.assertEqual(self.a.post('/api/decision-cases',json=payload).status_code,404)
        # FK ownership is enforced even for the bypass-RLS service key.
        response=self.s.db.patch('datasets',params={'id':'eq.'+fa['id']},json={'parent_dataset_id':fb['id']})
        self.assertEqual(response.status_code,409)
        self.assertEqual(self.checked(self.s.db.get('datasets',params={'id':'eq.'+fb['id']}))[0]['label'],fb['label'])

    def test_03_roles_disabled_members_and_identity_forgery(self):
        case,orders,fleet=self.case(self.a)
        for user in (VIEWER,DISABLED):
            with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[user]},trust_env=False) as client:
                self.assertEqual(client.get('/api/decision-cases').status_code,200 if user==VIEWER else 403)
                for path,body in [('/api/decision-cases',{'id':str(uuid4()),'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id']}),('/api/runs',self.body(case,orders,fleet)),(f'/api/datasets/{fleet["id"]}/default',{}),(f'/api/runs/{uuid4()}/explain',{}),(f'/api/runs/{uuid4()}/comparative',{})]:
                    self.assertEqual(client.post(path,json=body).status_code,403,path)
        self.assertEqual(self.a.get('/api/decision-cases',headers={'X-Dation-Workspace-ID':self.s.workspace_b}).status_code,403)
        self.assertEqual(self.a.post('/api/decision-cases',json={**self.body(case,orders,fleet),'workspace_id':self.s.workspace_b}).status_code,422)

    def test_04_invalid_and_expired_jwt_and_basic_are_rejected(self):
        expired=token(self.s.auth_key,self.s.env['SUPABASE_URL'],expires=-60)
        valid=self.s.user_tokens[USER_A];claims=jwt.decode(valid,options={'verify_signature':False})
        wrong_aud=jwt.encode({**claims,'aud':'other'},self.s.auth_key,algorithm='ES256',headers={'kid':'dation-local-test'})
        wrong_issuer=jwt.encode({**claims,'iss':'https://other.invalid/auth/v1'},self.s.auth_key,algorithm='ES256',headers={'kid':'dation-local-test'})
        forged=jwt.encode(claims,'untrusted-key',algorithm='HS256',headers={'kid':'dation-local-test'})
        for header in ['', 'Basic ZGF0aW9uOmRpc3BhdGNoLWUyZS1wcml2YXRl',*['Bearer '+v for v in (expired,wrong_aud,wrong_issuer,forged,'not-a-jwt')]]:
            self.assertEqual(self.s.http.get(self.s.api_url+'/api/decision-cases',headers={'Authorization':header}).status_code,401)

    def test_05_direct_rest_rls_rpc_and_storage_deny_cross_access(self):
        ca,oa,fa=self.case(self.a);cb,ob,fb=self.case(self.b)
        for user,own,other in ((USER_A,oa,ob),(USER_B,ob,oa)):
            headers={'Authorization':'Bearer '+self.s.user_tokens[user]}
            rows=self.checked(self.s.http.get(self.s.rest_url+'/datasets',headers=headers))
            self.assertIn(own['id'],[row['id'] for row in rows]);self.assertNotIn(other['id'],[row['id'] for row in rows])
            update=self.s.http.patch(self.s.rest_url+'/datasets?id=eq.'+other['id'],headers=headers,json={'label':'forbidden'})
            self.assertIn(update.status_code,(401,403))
            rpc=self.s.http.post(self.s.rest_url+'/rpc/platform_rpc',headers=headers,json={'target_workspace_id':self.s.workspace_b,'actor_user_id':USER_B,'operation':'list_decision_cases'})
            self.assertIn(rpc.status_code,(401,403))
            raw=self.s.http.get(self.s.env['SUPABASE_URL']+'/storage/v1/object/authenticated/dda-inputs/'+other['storage_path'],headers=headers)
            self.assertIn(raw.status_code,(401,403))
        # Retired privileged RPCs are absent from the public REST schema.
        for name in ['set_default_fleet','enqueue_dispatch_run','approve_decision_run_version','list_decision_cases']:
            self.assertEqual(self.s.db.post('rpc/'+name,json={}).status_code,404)

    def test_06_worker_preserves_tenant_and_cross_runs_evidence_are_blocked(self):
        ca,oa,fa=self.case(self.a);cb,ob,fb=self.case(self.b)
        ids=[]
        for client,case,orders,fleet in ((self.a,ca,oa,fa),(self.b,cb,ob,fb)):
            run=self.checked(client.post('/api/runs',json=self.body(case,orders,fleet)),202);ids.append(run['id'])
        self.s.start_worker()
        for client,rid,wid in ((self.a,ids[0],self.s.workspace_a),(self.b,ids[1],self.s.workspace_b)):
            result=[]
            def complete():
                row=self.checked(client.get('/api/runs/'+rid))
                if row['status'] not in ('completed','error'):return False
                self.assertEqual(row['status'],'completed',row.get('error_message'));self.assertEqual(row['workspace_id'],wid);result.append(row);return True
            wait_for(complete,'tenant worker result',timeout=60)
        for suffix in ['', '/interpretation','/comparative']:
            self.assertEqual(self.a.get('/api/runs/'+ids[1]+suffix).status_code,404,suffix)
        for suffix in ['cancel','approve','comparative','explain','chat']:
            body={'case_id':ca,'node_id':'logistics_assignment'} if suffix=='approve' else {'question':'¿Qué pasó?'} if suffix=='chat' else {}
            self.assertEqual(self.a.post('/api/runs/'+ids[1]+'/'+suffix,json=body).status_code,404,suffix)
        current=self.checked(self.a.get('/api/decision-cases/'+ca))['decision_case'];current['nodes']['logistics_assignment']['run_id']=ids[1]
        self.assertEqual(self.a.patch('/api/decision-cases/'+ca,json={'state':current}).status_code,404)
        approved=self.checked(self.a.post('/api/runs/'+ids[0]+'/approve',json={'case_id':ca,'node_id':'logistics_assignment'}))
        self.assertEqual(approved['approved_by'],'user:'+USER_A);self.assertEqual(approved['approved_by_user_id'],USER_A)

    def test_07_login_refresh_logout_cookie_security_and_csrf(self):
        with httpx.Client(base_url=self.s.api_url,trust_env=False) as client:
            body={'email':'user-1@example.test','password':'dispatch-e2e-private'}
            self.assertEqual(client.post('/auth/login',headers={'Origin':'https://evil.invalid'},json=body).status_code,403)
            login=client.post('/auth/login',headers={'Origin':self.s.api_url},json=body);self.checked(login)
            self.assertTrue(all('HttpOnly' in value for value in login.headers.get_list('set-cookie')))
            self.assertNotIn('refresh_token',login.text);self.assertEqual(client.get('/app').status_code,200)
            client.cookies.delete('dation_access')
            session=self.checked(client.post('/auth/session',headers={'Origin':self.s.api_url}))
            self.assertEqual(session['membership']['workspace_id'],self.s.workspace_a);self.assertIn('access_token',session);self.assertNotIn('refresh_token',session)
            self.checked(client.post('/auth/logout',headers={'Origin':self.s.api_url}));self.assertEqual(client.get('/app').status_code,303)
