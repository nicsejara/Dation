"""Case identity and input replacement through the actual API and PostgreSQL."""
import unittest
from uuid import uuid4
import httpx
from auth_fixture import USER_A,USER_B,VIEWER
import test_workflow_gates as gates
from fixtures import csv_input

class CasePreparationTests(unittest.TestCase):
    setUpClass=classmethod(gates.WorkflowGateTests.setUpClass.__func__)
    setUp=gates.WorkflowGateTests.setUp
    checked=gates.WorkflowGateTests.checked
    upload=gates.WorkflowGateTests.upload
    case=gates.WorkflowGateTests.case
    roles=gates.WorkflowGateTests.roles
    assign=gates.WorkflowGateTests.assign
    snapshot=gates.WorkflowGateTests.snapshot
    body=gates.WorkflowGateTests.body
    admit=gates.WorkflowGateTests.admit

    def test_identity_survives_reload_and_respects_cas_and_workspace_access(self):
        cid,orders,fleet=self.case()
        case=self.checked(self.a.get('/api/platform/decisions/'+cid))
        payload={'expected_updated_at':case['updated_at'],'label':' SEMANA 43 ','category':'weekly','description':'Planificación semanal.'}
        saved=self.checked(self.a.patch('/api/platform/decisions/'+cid,json=payload))
        self.assertEqual(saved['label'],'SEMANA 43')
        self.assertEqual(self.a.patch('/api/platform/decisions/'+cid,json=payload).status_code,409)
        current=self.checked(self.a.get('/api/platform/decisions/'+cid))
        self.assertEqual((current['label'],current['category'],current['description']),('SEMANA 43','weekly','Planificación semanal.'))
        self.assertEqual(current['friendly_id'],'DC-'+cid[:8].upper())
        self.assertEqual(self.checked(self.a.get('/api/decision-cases/'+cid))['case']['category'],'weekly')
        payload['expected_updated_at']=current['updated_at'];payload['category']='arbitrary'
        self.assertEqual(self.a.patch('/api/platform/decisions/'+cid,json=payload).status_code,422)
        payload['category']='monthly'
        for uid,status in ((USER_B,404),(VIEWER,403)):
            with httpx.Client(base_url=self.s.api_url,trust_env=False,headers={'Authorization':'Bearer '+self.s.user_tokens[uid]}) as other:
                self.assertEqual(other.patch('/api/platform/decisions/'+cid,json=payload).status_code,status)
        # Old create payloads still work, new payloads persist identity immediately.
        new=self.checked(self.a.post('/api/decision-cases',json={'id':str(uuid4()),'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id'],'label':'SEMANA 44','category':'weekly'}))['case']
        self.assertEqual(new['label'],'SEMANA 44');self.assertEqual(new['category'],'weekly')

    def test_data_pack_changes_fork_while_preserving_original_people_and_runs(self):
        cid,orders,fleet=self.case();self.roles(USER_A,['data_owner','decision_owner'])
        before=self.checked(self.a.get('/api/platform/decisions/'+cid))
        self.checked(self.a.patch('/api/platform/decisions/'+cid,json={'expected_updated_at':before['updated_at'],'label':'Case original','category':'weekly'}))
        self.assign(cid,'data_owner',USER_A);self.assign(cid,'logistics_assignment',USER_A)
        people=self.snapshot(cid)['stages']
        replacement=self.checked(self.a.post('/api/datasets/upload',params={'dataset_type':'orders'},data={'is_sample':'true'},files={'file':('replacement.csv',csv_input('orders')+b'\n','text/csv')}))['dataset']
        before=self.checked(self.a.get('/api/platform/decisions/'+cid))
        body={'expected_updated_at':before['updated_at'],'orders_dataset_id':replacement['id'],'fleet_dataset_id':fleet['id']}
        fork=self.checked(self.a.put('/api/platform/decisions/'+cid+'/data-pack',json=body))
        self.assertNotEqual(fork['id'],cid)
        self.assertEqual(self.checked(self.a.put('/api/platform/decisions/'+cid+'/data-pack',json=body))['id'],fork['id'])
        hydrated=self.checked(self.a.get('/api/decision-cases/'+cid))
        self.assertEqual(hydrated['orders']['id'],orders['id'])
        self.assertEqual(hydrated['workflow_responsibilities']['stages'],people)
        run=self.admit(self.body(cid,orders,fleet))
        current=self.checked(self.a.get('/api/platform/decisions/'+cid));body['expected_updated_at']=current['updated_at']
        self.assertEqual(self.checked(self.a.put('/api/platform/decisions/'+cid+'/data-pack',json=body))['id'],fork['id'])
        self.assertEqual(self.checked(self.a.get('/api/runs/'+run))['id'],run)
        self.assertEqual(self.checked(self.a.get('/api/decision-cases/'+cid))['orders']['id'],orders['id'])
