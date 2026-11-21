"""J1.02 real D1/D2 worker, SQL, private artifacts, KPI and human workflow."""
import json
import os
import sys
import unittest
import httpx
from copy import deepcopy
from uuid import uuid4
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ultimate_day_fixture import DaySandbox
from ultimate_result_helpers import ok,publish,submit,wait_run,row,approval,endpoint
from test_ultimate_d2_lineage import day_submit,day_approve
from auth_fixture import USER_A,USER_B,VIEWER
from tests.test_ultimate_data_contracts import model
from tests.test_decision_case_j102 import definition
from app.models.decision_case_v2 import UltimateCaseCreateV2
from app.results.canonical import canonical_tree
from sandbox import wait_for


class CaseV2Sandbox(DaySandbox):
    def start_process(self,name,args,**options):
        if name=='api':options['env']={**options.get('env',self.env),'DATION_J101_LIBRARY_ENABLED':'true','DATION_J102_ENABLED':'true','DATION_UNIFIED_JOURNEY_ENABLED':'true'}
        return super().start_process(name,args,**options)
    def start(self):
        super().start()
        self.sql('UPDATE dation_private.platform_release SET j102_enabled=true,unified_journey_enabled=true,saga10_schema_enabled=true,saga10_ui_enabled=true;')


class DecisionCaseV2ExecutionE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.s=CaseV2Sandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
    def setUp(self):
        s=self.s;a=s.api_client
        m=ok(a.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'J102 Engine QA','configuration':model()['config_jsonb']}))
        v=ok(a.post('/api/platform/logistics-models/'+m['model']['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':1}))['version']
        d=definition(model_binding=dict(model_id=m['model']['id'],model_version_id=v['id'],configuration_hash=v['config_hash'],contract_hash=v['contract_hash']))
        body=UltimateCaseCreateV2(id=uuid4(),**d.identity.model_dump(),**d.decision_context.model_dump(),logistics_model_version_id=v['id'],case_policy=d.case_policy,decision_owner_user_id=USER_A,definition_v2=d)
        data=ok(a.post('/api/platform/data-preparations',json={'id':str(uuid4()),'model_version_id':v['id']}));pid=data['session']['id']
        data=ok(a.put('/api/platform/data-preparations/'+pid+'/owner',json={'expected_revision':data['session']['revision'],'data_owner_user_id':USER_A}))
        for entity in ['transport_demand','transport_resources']:
            raw=a.post('/api/platform/logistics-models/contract-preview/templates/'+entity,json={'model_id':m['model']['id'],'version_id':v['id']}).content
            data=ok(a.post('/api/platform/data-preparations/'+pid+'/uploads/'+entity,params={'upload_id':str(uuid4()),'expected_revision':data['session']['revision'],'contract_hash':data['contracts'][entity]['contract_hash']},files={'file':('J102.csv',raw,'text/csv')}))
        self.c=ok(a.post('/api/platform/data-preparations/'+pid+'/finalize',json={'expected_revision':data['session']['revision'],'case':canonical_tree(body)}))['context'];self.cid=self.c['case']['id']
    def tearDown(self):self.s.stop(self.s.worker,kill=True)

    def completed(self):
        rid,body,response=submit(self.s,self.cid);ok(response);self.s.start_worker();return rid,wait_run(self.s,rid)

    def test_01_real_d1_result_kpi_and_manual_approval_are_separate(self):
        rid,run=self.completed();self.assertIsNone(run['approved_at'])
        kpi=ok(self.s.api_client.get('/api/platform/logistics-cases/'+self.cid+'/acceptance',params={'run_id':rid}))
        self.assertEqual(kpi['status'],'MEETS');self.assertEqual(kpi['run_id'],rid);self.assertEqual(kpi['definition_revision_id'],self.c['case_definition']['id'])
        self.assertEqual(kpi['unit'],self.c['planning_context']['model']['primary_dimension']);self.assertEqual(kpi['human_approval'],'SEPARATE_WORKFLOW')
        for uid in [VIEWER,USER_B]:
            with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[uid]},trust_env=False,timeout=30) as client:
                self.assertIn(approval(self.s,self.cid,rid,client=client).status_code,[403,404])
                self.assertIn(client.get('/api/platform/logistics-cases/'+self.cid+'/acceptance',params={'run_id':rid}).status_code,[200] if uid==VIEWER else [403,404])
        self.assertIsNone(row(self.s,rid)['approved_at']);ok(approval(self.s,self.cid,rid));self.assertIsNotNone(row(self.s,rid)['approved_at'])
        self.assertEqual(row(self.s,rid)['result_json'],run['result_json'])
        origin=ok(self.s.api_client.get('/api/platform/logistics-cases/'+self.cid+'/definitions/from-run/'+rid));self.assertEqual(origin['revision'],self.c['case_definition'])

    def test_02_metadata_revision_does_not_rebind_approved_d1_or_d2(self):
        rid,run=self.completed();ok(approval(self.s,self.cid,rid));before=row(self.s,rid)
        base='/api/platform/logistics-cases/'+self.cid;c=ok(self.s.api_client.get(base+'/context'));d=deepcopy(c['case_definition']['snapshot']);d['identity']['name']='Nombre administrativo nuevo'
        newer=ok(self.s.api_client.put(base+'/definition',json={'mutation_id':str(uuid4()),'expected_revision':c['case_definition']['revision'],'expected_updated_at':c['case']['updated_at'],'definition_v2':d}))
        self.assertEqual(newer['case_definition']['revision'],2)
        child,_,response=day_submit(self.s,self.cid);ok(response);wait_run(self.s,child)
        self.assertEqual(row(self.s,rid),before);self.assertEqual(row(self.s,child)['configuration_json']['frozen_context']['decision_definition']['definition_revision_id'],self.c['case_definition']['id'])
        evaluated=ok(self.s.api_client.get(base+'/acceptance',params={'run_id':child}));self.assertEqual(evaluated['run_id'],rid);self.assertEqual(evaluated['referenced_by_d2_run_id'],child)
        source=ok(self.s.api_client.get(base+'/definitions/from-run/'+child));self.assertEqual(source['revision']['id'],self.c['case_definition']['id'])
        ok(day_approve(self.s,self.cid,child));self.assertIsNotNone(row(self.s,child)['approved_at'])

    def test_03_legacy_approval_reconciliation_drains_without_exposing_v2_history(self):
        from unittest.mock import patch
        # Reuse the exact restore scenario without changing suite import order.
        with patch.object(sys,'path',[str(Path(__file__).resolve().parents[1]/'integration'),*sys.path]):
            from tests.integration.test_ultimate_restore import legacy_case
        self.s.start_worker();before=self.c['case_definition']
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False,timeout=45) as other:
            legacy=legacy_case(self.s,other)
        wait_for(lambda:self.s.sql("SELECT count(*) FROM decision_case_reconciliations WHERE workspace_id='"+self.s.workspace_b+"';")=='0',
            'legacy tenant reconciliation before restore snapshot')
        self.assertIsNotNone(row(self.s,legacy['run_id'])['approved_at'])
        self.assertEqual(ok(self.s.api_client.get('/api/platform/logistics-cases/'+self.cid+'/context'))['case_definition'],before)

