"""Bounded reproduction of the newly unblocked Home assignment discrepancy."""
import json
import httpx
from auth_fixture import USER_B,VIEWER
from workflow_fixture import prepare_stage,set_roles
from test_collaboration import CollaborationTests
C=CollaborationTests
C.setUpClass();test=C('test_02_assigned_approval_handoff_attribution_override_and_retry')
try:
 test.setUp();test.join();test.checked(test.update(VIEWER,'operator'));set_roles(test.a,VIEWER,[])
 cid,orders,fleet=test.case();prepare_stage(test.a,cid,'data_preparation');test.checked(test.assign(cid))
 test.s.start_worker();rid=test.admit(test.body(cid,orders,fleet));test.finish(rid)
 detail=test.checked(test.a.get('/api/platform/decisions/'+cid))
 with httpx.Client(base_url=test.s.api_url,headers={'Authorization':'Bearer '+test.s.user_tokens[VIEWER]},trust_env=False) as operator:
  attention=test.checked(operator.get('/api/platform/home'))['attention']
  collab=test.checked(operator.get('/api/decision-cases/'+cid))['collaboration']['logistics_assignment']
  denied=operator.post('/api/runs/'+rid+'/approve',json={'case_id':cid,'node_id':'logistics_assignment'})
  run=test.checked(operator.get('/api/runs/'+rid))
 raw=test.s.sql(f"SELECT jsonb_build_object('owner_user_id',owner_user_id,'approver_user_id',approver_user_id) FROM decision_assignments WHERE decision_case_id='{cid}' AND node_id='logistics_assignment';")
 legacy=test.s.sql("SELECT strpos(pg_get_functiondef('public.platform_home(uuid,uuid)'::regprocedure),'a.approver_user_id')>0;")
 evidence={'scope':'owned disposable stack only','case_id':cid,'run_id':rid,'assigned_owner':detail['nodes'][0]['owner']['id'],'unassigned_operator':VIEWER,'raw_assignment':json.loads(raw),'home_attention':attention,'collaboration_can_approve':collab['can_approve'],'approval_status':denied.status_code,'approval_body':denied.json(),'approved_at_after_denial':run['approved_at'],'home_sql_uses_retired_column':legacy}
 assert evidence['assigned_owner']==USER_B and attention['total']==1 and not collab['can_approve'] and denied.status_code==403 and run['approved_at'] is None,evidence
 print(json.dumps(evidence,ensure_ascii=False,indent=2))
finally:
 test.doCleanups();C.doClassCleanups()
