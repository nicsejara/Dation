"""T8 owned scenarios. All inputs enter through the real T3/T4 APIs."""
import csv,io,json,time
from uuid import uuid4
from auth_fixture import USER_A
from tests.test_ultimate_data_contracts import model

D1='logistics_assignment';D2='logistics_scheduling'
def ok(response):
    assert response.is_success,(response.status_code,response.text)
    return response.json()

def setup_case(s):
    a=s.api_client
    m=ok(a.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'T8 owned','configuration':model()['config_jsonb']}))
    v=ok(a.post('/api/platform/logistics-models/'+m['model']['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':1}))
    c=ok(a.post('/api/platform/logistics-cases',json={'id':str(uuid4()),'name':'T8 frozen','logistics_model_version_id':v['version']['id'],'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':USER_A}))
    cid=c['case']['id']
    ok(a.put('/api/platform/decisions/'+cid+'/responsibilities/data_owner',json={'expected_updated_at':None,'owner_user_id':USER_A}))
    for entity in ['transport_demand','transport_resources']:publish(s,cid,entity)
    return cid

def publish(s,cid,entity='transport_demand',change=None):
    a=s.api_client;base='/api/platform/logistics-cases/'+cid
    state=ok(a.get(base+'/data'))
    raw=a.get(base+'/data/templates/'+entity).content
    reader=csv.DictReader(io.StringIO(raw.decode()));rows=list(reader)
    # One feasible row keeps these lifecycle tests independent of search budgets.
    row=rows[0];row.update(change or {})
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=reader.fieldnames,lineterminator='\n');w.writeheader();w.writerow(row)
    j=ok(a.post(base+'/data/uploads/'+entity,params={'upload_id':str(uuid4()),'contract_hash':state['contracts'][entity]['contract_hash']},files={'file':('T8.csv',out.getvalue().encode(),'text/csv')}))
    return ok(a.post(base+'/data/publish',json={'publication_id':str(uuid4()),'expected_revision':state['pack']['revision'],'selection':[{'slot_key':entity,'upload_id':j['id']}]}))

def intention(s,cid):
    ctx=ok(s.api_client.get('/api/platform/logistics-cases/'+cid+'/run-context'))
    return {'request_schema':'ultimate_run_request_v1','workflow_version':2,'case_id':cid,'node_id':D1,**{k:ctx[k] for k in ['expected_context_hash','model_version_id','data_pack_version_id','node_policy']}}

def submit(s,cid,rid=None,body=None):
    rid=rid or str(uuid4());body=body or intention(s,cid)
    return rid,body,s.api_client.post('/api/runs',params={'run_id':rid},json=body)

def row(s,rid):return json.loads(s.sql(f"SELECT to_jsonb(r) FROM decision_runs r WHERE id='{rid}';"))
def wait_run(s,rid,status='completed',timeout=35):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        r=row(s,rid)
        if r['status']==status:return r
        if r['status']=='error':raise AssertionError(r['error_message'])
        time.sleep(.1)
    raise AssertionError('Run did not reach '+status+': '+r['status'])
def endpoint(s,rid,suffix='result',fingerprint=None):
    fp=fingerprint or row(s,rid)['result_fingerprint']
    return s.api_client.get('/api/runs/'+rid+'/'+suffix,params={'expected_result_fingerprint':fp})
def approval(s,cid,rid,fp=None,client=None):
    return (client or s.api_client).post('/api/runs/'+rid+'/approve',json={'case_id':cid,'node_id':D1,'expected_result_fingerprint':fp or row(s,rid)['result_fingerprint']})
