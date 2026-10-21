"""Platform V2 acceptance: distinct people, actual engines and cross-surface evidence."""
import json
import os
from pathlib import Path
import subprocess
import unittest
from uuid import uuid4

import httpx
from auth_fixture import USER_A,USER_B,VIEWER,token
from fixtures import csv_input
from sandbox import Sandbox,ROOT
from workflow_fixture import set_roles

STEWARD='10000000-0000-4000-8000-000000000005'
OWNER='10000000-0000-4000-8000-000000000006'
APPROVER='10000000-0000-4000-8000-000000000007'


class GoldenWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=Sandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
        assert cls.s.api_url.startswith('http://127.0.0.1:')
        cls.clients={USER_A:cls.s.api_client}
        for uid in (USER_B,VIEWER,STEWARD,OWNER,APPROVER):
            if uid not in cls.s.user_tokens:
                cls.s.sql(f"INSERT INTO auth.users VALUES('{uid}','user-{uid[-1]}@example.test',now());")
                cls.s.user_tokens[uid]=token(cls.s.auth_key,cls.s.env['SUPABASE_URL'],uid)
            client=httpx.Client(base_url=cls.s.api_url,headers={'Authorization':'Bearer '+cls.s.user_tokens[uid]},trust_env=False,timeout=30)
            cls.clients[uid]=client;cls.addClassCleanup(client.close)
        identities={'user-3@example.test':{'id':VIEWER,'refresh':'fixture-refresh-viewer'}}
        for uid,role,name in ((STEWARD,'data_steward','Steward'),(OWNER,'decision_owner','Owner'),(APPROVER,'approver','Approver')):
            email='user-'+uid[-1]+'@example.test'
            identities[email]={'id':uid,'refresh':'fixture-refresh-'+uid[-1]}
            invitation=cls.s.api_client.post('/api/platform/team/invitations',json={'email':email,'access_role':'operator','business_role':role})
            assert invitation.status_code==201,invitation.text
            with httpx.Client(base_url=cls.s.api_url,trust_env=False,headers={'Origin':cls.s.api_url},timeout=30) as bff:
                bff.cookies.set('dation_access',cls.s.user_tokens[uid])
                accepted=bff.post('/auth/invitations/'+invitation.json()['id']+'/accept')
                assert accepted.status_code==200,accepted.text
            result=cls.clients[uid].patch('/api/platform/profile',json={'first_name':'Golden','last_name':name})
            assert result.status_code==200,result.text
        (cls.s.directory/'auth-fixture-users.json').write_text(json.dumps(identities))
        set_roles(cls.s.api_client,USER_A,[])
        set_roles(cls.s.api_client,VIEWER,['data_owner','data_steward','decision_owner','approver'])

    def setUp(self):
        self.s.stop(self.s.worker)
        self.s.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events,audit_events CASCADE;')

    def checked(self,response,status=200):
        self.assertEqual(response.status_code,status,response.text[:1500]);return response.json()

    def create_case(self,uid):
        client=self.clients[uid];datasets={}
        for kind in ('orders','fleet'):
            datasets[kind]=self.checked(client.post('/api/datasets/upload',params={'dataset_type':kind},files={'file':(kind+'.csv',csv_input(kind),'text/csv')}))['dataset']
        cid=str(uuid4());self.checked(client.post('/api/decision-cases',json={'id':cid,'orders_dataset_id':datasets['orders']['id'],'fleet_dataset_id':datasets['fleet']['id']}))
        return cid,datasets

    def test_distinct_people_complete_the_golden_workflow_and_cross_surface_matrix(self):
        inputs=self.s.directory/'golden-inputs';inputs.mkdir()
        for kind in ('orders','fleet'):(inputs/(kind+'.csv')).write_bytes(csv_input(kind))
        self.s.start_worker()
        environment={**self.s.env,'DATION_E2E_URL':self.s.api_url,'DATION_E2E_INPUTS':str(inputs)}
        artifact=os.getenv('DATION_E2E_ARTIFACTS')
        if artifact:environment['DATION_E2E_ARTIFACTS']=str(Path(artifact)/'golden-v2')
        result=subprocess.run([os.getenv('DATION_BROWSER_PYTHON',str(ROOT/'.browser-venv/bin/python')),str(ROOT/'tests/e2e/golden_journey.py')],cwd=ROOT,env=environment,text=True,capture_output=True,timeout=300)
        if result.returncode:self.s.diagnostics('golden-v2')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(result.stdout.strip().splitlines()[-1]);self.assertTrue(report['passed'])
        case=report['case_id'];ids=report['runs']
        snapshot=self.checked(self.s.api_client.get(f'/api/platform/decisions/{case}/responsibilities'))
        self.assertEqual(snapshot['stages']['data_preparation']['owner']['id'],STEWARD)
        detail=self.checked(self.s.api_client.get(f'/api/platform/decisions/{case}'))
        self.assertEqual(detail['display_status'],'completed')
        for node,rid in ids.items():
            self.assertEqual(snapshot['stages'][node]['owner']['id'],OWNER)
            self.assertEqual(snapshot['stages'][node]['approver']['id'],APPROVER)
            run=self.checked(self.s.api_client.get('/api/runs/'+rid))
            self.assertEqual(run['created_by_user_id'],OWNER);self.assertEqual(run['approved_by_user_id'],APPROVER)
            if node=='logistics_scheduling':self.assertEqual(run['upstream_run_id'],ids['logistics_assignment'])
            projected=next(value for value in detail['nodes'] if value['id']==node)
            self.assertEqual(projected['status'],'approved');self.assertIsNotNone(projected['objective'])
            self.assertEqual(projected['approved_run']['approved_by']['id'],APPROVER)
            metadata=json.loads(self.s.sql(f"SELECT metadata_json FROM audit_events WHERE event_type='run.queued' AND object_id='{rid}';"))
            self.assertEqual(metadata['data_responsible_user_id'],STEWARD);self.assertEqual(metadata['decision_owner_user_id'],OWNER)
        self.assertEqual(self.s.sql('SELECT count(*) FROM decision_runs;'),'2')
        self.assertEqual(self.s.sql("SELECT count(*) FROM decision_approval_events WHERE action='approved';"),'2')
        self.assertEqual(report['source_sha'],subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
        self.assertEqual(report['viewports'],[1440,1280,1024,768,390])
        self.assertEqual(set(report['surfaces']),{'home','data','map','config','dashboard','responsibility','switcher','decision_center','data_hub'})

    def test_workspace_boundaries_and_viewer_responsibilities_do_not_grant_writes(self):
        ca,da=self.create_case(STEWARD);cb,db=self.create_case(USER_B)
        admin=self.s.api_client;other=self.clients[USER_B];viewer=self.clients[VIEWER]
        before=self.s.sql("SELECT md5(string_agg(to_jsonb(c)::text,'' ORDER BY id)) FROM decision_cases c;")
        for client,cid,datasets,foreign_member in ((admin,cb,db,USER_B),(other,ca,da,OWNER)):
            dataset=datasets['orders']['id']
            for path in (f'/api/platform/decisions/{cid}',f'/api/platform/decisions/{cid}/responsibilities',f'/api/platform/data/datasets/{dataset}',f'/api/platform/data/datasets/{dataset}/download'):
                self.assertEqual(client.get(path).status_code,404,path)
            self.assertEqual(client.post(f'/api/platform/data/datasets/{dataset}/archive').status_code,404)
            self.assertEqual(client.delete(f'/api/platform/data/datasets/{dataset}').status_code,404)
            self.assertEqual(client.patch(f'/api/platform/decisions/{cid}',json={'expected_updated_at':'2026-10-21T00:00:00Z','archived':True}).status_code,404)
            self.assertEqual(client.put(f'/api/platform/decisions/{cid}/responsibilities/data_preparation',json={'expected_updated_at':None,'owner_user_id':foreign_member}).status_code,404)
        for group,expected in (('data',STEWARD),('decision_owner',OWNER),('approver',APPROVER)):
            candidates=self.checked(admin.get('/api/platform/team',params={'candidates':'true','responsibility':group}))
            self.assertEqual([m['user_id'] for m in candidates['members']],[expected])
        self.assertEqual(admin.put(f'/api/platform/decisions/{ca}/responsibilities/logistics_assignment',json={'expected_updated_at':None,'owner_user_id':USER_B}).status_code,409)
        self.assertEqual(viewer.get(f'/api/platform/decisions/{ca}').status_code,200)
        for response in (viewer.post('/api/decision-cases',json={'id':str(uuid4()),'orders_dataset_id':da['orders']['id'],'fleet_dataset_id':da['fleet']['id']}),viewer.post('/api/runs',params={'run_id':str(uuid4())},json={'orders_dataset_id':da['orders']['id'],'fleet_dataset_id':da['fleet']['id'],'decision_case':{'case_id':ca,'node_id':'logistics_assignment'},'configuration':{'objective':'balanced'}}),viewer.put(f'/api/platform/decisions/{ca}/responsibilities/data_preparation',json={'expected_updated_at':None,'owner_user_id':VIEWER}),viewer.patch('/api/platform/team/members/'+VIEWER+'/responsibilities',json={'expected_updated_at':'2026-10-21T00:00:00Z','business_roles':[]})):
            self.assertEqual(response.status_code,403,response.text)
        self.assertEqual(before,self.s.sql("SELECT md5(string_agg(to_jsonb(c)::text,'' ORDER BY id)) FROM decision_cases c;"))
