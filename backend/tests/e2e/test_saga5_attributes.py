"""Joint attributes/Owner persistence through the actual API and PostgreSQL."""
import unittest
import httpx
from auth_fixture import USER_A,USER_B,VIEWER
import test_workflow_gates as gates

class Saga5AttributesTests(unittest.TestCase):
    setUpClass=classmethod(gates.WorkflowGateTests.setUpClass.__func__)
    setUp=gates.WorkflowGateTests.setUp
    checked=gates.WorkflowGateTests.checked
    upload=gates.WorkflowGateTests.upload
    case=gates.WorkflowGateTests.case
    roles=gates.WorkflowGateTests.roles
    snapshot=gates.WorkflowGateTests.snapshot
    assign=gates.WorkflowGateTests.assign

    def payload(self,cid,**changes):
        case=self.checked(self.a.get('/api/platform/decisions/'+cid));stage=self.snapshot(cid)['stages']['data_owner']
        return {'expected_updated_at':case['updated_at'],'expected_owner_updated_at':stage['updated_at'],'label':' SEMANA 43 ','category':'weekly','description':'Operación semanal.',**changes}

    def evidence(self,cid):
        case=self.checked(self.a.get('/api/platform/decisions/'+cid))
        return {key:case.get(key) for key in ('id','label','category','description','updated_at')},self.snapshot(cid)['stages']['data_owner'],self.s.sql(f"SELECT count(*) FROM audit_events WHERE decision_case_id='{cid}';")

    def test_joint_apply_and_metadata_or_owner_edits_keep_case_and_four_part_readiness(self):
        cid,orders,fleet=self.case();self.roles(USER_A,['data_owner'])
        saved=self.checked(self.a.put(f'/api/platform/decisions/{cid}/attributes',json=self.payload(cid,data_owner_user_id=USER_A)))
        self.assertEqual(saved['id'],cid);self.assertEqual(saved['label'],'SEMANA 43')
        self.assertEqual(saved['workflow_responsibilities']['stages']['data_owner']['owner']['id'],USER_A)
        self.assertEqual(self.a.get(f'/api/platform/decisions/{cid}/workflow-readiness').status_code,200)
        self.checked(self.a.put(f'/api/platform/decisions/{cid}/attributes',json=self.payload(cid,label='SEMANA 44',category='monthly',description=None,data_owner_user_id=None)))
        self.assertEqual(self.a.get(f'/api/platform/decisions/{cid}/workflow-readiness').status_code,409)
        case=self.checked(self.a.get('/api/decision-cases/'+cid))
        self.assertEqual(case['case']['id'],cid);self.assertEqual(case['orders']['id'],orders['id']);self.assertEqual(case['fleet']['id'],fleet['id']);self.assertIsNotNone(case['case']['attributes_applied_at'])
        self.checked(self.a.put(f'/api/platform/decisions/{cid}/attributes',json=self.payload(cid,data_owner_user_id=USER_A)))
        self.assertEqual(self.a.get(f'/api/platform/decisions/{cid}/workflow-readiness').status_code,200)
        self.assertEqual(self.s.sql('SELECT count(*) FROM decision_cases;'),'1')

    def test_owner_conflicts_and_ineligible_people_roll_back_all_attributes_and_audit(self):
        cid,_,_=self.case();self.roles(USER_A,['data_owner']);stale=self.payload(cid,data_owner_user_id=USER_A)
        self.assign(cid,'data_owner',USER_A);before=self.evidence(cid)
        self.assertEqual(self.a.put(f'/api/platform/decisions/{cid}/attributes',json=stale).status_code,409)
        self.assertEqual(self.evidence(cid),before)
        payload=self.payload(cid,label='No debe guardarse',data_owner_user_id=USER_B);before=self.evidence(cid)
        self.assertEqual(self.a.put(f'/api/platform/decisions/{cid}/attributes',json=payload).status_code,409)
        self.assertEqual(self.evidence(cid),before)
        current=self.payload(cid);self.checked(self.a.put(f'/api/platform/decisions/{cid}/attributes',json=current));before=self.evidence(cid)
        self.assertEqual(self.a.put(f'/api/platform/decisions/{cid}/attributes',json=current).status_code,409)
        self.assertEqual(self.evidence(cid),before)

    def test_joint_submit_preserves_tenant_viewer_and_admin_only_owner_permissions(self):
        cid,_,_=self.case();payload=self.payload(cid)
        for uid,status in ((USER_B,404),(VIEWER,403)):
            before=self.evidence(cid)
            with httpx.Client(base_url=self.s.api_url,trust_env=False,headers={'Authorization':'Bearer '+self.s.user_tokens[uid]}) as client:
                self.assertEqual(client.put(f'/api/platform/decisions/{cid}/attributes',json=payload).status_code,status)
            self.assertEqual(self.evidence(cid),before)
        self.roles(USER_A,['data_owner']);self.assign(cid,'data_owner',USER_A)
        payload=self.payload(cid,data_owner_user_id=None)
        self.s.sql(f"UPDATE workspace_members SET access_role='operator' WHERE user_id='{USER_A}';")
        before=self.evidence(cid)
        self.assertEqual(self.a.put(f'/api/platform/decisions/{cid}/attributes',json=payload).status_code,403)
        self.assertEqual(self.evidence(cid),before)
        payload.pop('data_owner_user_id');self.checked(self.a.put(f'/api/platform/decisions/{cid}/attributes',json=payload))
        self.assertEqual(self.snapshot(cid)['stages']['data_owner']['owner']['id'],USER_A)
        self.assertEqual(self.s.sql("SELECT has_function_privilege('authenticated','public.platform_apply_case_attributes(uuid,uuid,uuid,timestamptz,jsonb,timestamptz,boolean,uuid)','EXECUTE');"),'f')
