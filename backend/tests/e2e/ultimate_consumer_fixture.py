"""Owned real T10 browser fixture; no production credentials or data."""
import json,sys
from pathlib import Path
from sandbox import port,wait_for
from ultimate_day_fixture import DaySandbox
from ultimate_result_helpers import setup_case,submit,wait_run,approval,ok,row,publish
from test_ultimate_d2_lineage import day_submit

if __name__=='__main__':
    with DaySandbox() as s:
        cid=setup_case(s)
        state=ok(s.api_client.get('/api/platform/logistics-cases/'+cid+'/context'))
        name=('Distribución metropolitana — Córdoba / São Paulo · Reposición de inventario y demanda regional ' * 2)[:120]
        ok(s.api_client.patch('/api/platform/logistics-cases/'+cid+'/context',json={'expected_updated_at':state['case']['updated_at'],'name':name}))
        publish(s,cid,'transport_demand',{'order_id':'ORDER-'+('A'*122)})
        publish(s,cid,'transport_resources',{'resource_id':'RESOURCE-'+('B'*119)})
        s.start_worker();parent,_,response=submit(s,cid);ok(response);wait_run(s,parent);ok(approval(s,cid,parent))
        child,_,response=day_submit(s,cid);ok(response);wait_run(s,child)
        baseline=Path('/workspace/work/dation-t10/baseline-src/backend');baseline_url=None
        if baseline.exists():
            baseline_port=port();baseline_url='http://127.0.0.1:'+str(baseline_port)
            process=s.start_process('post-t9-baseline-api',['-m','uvicorn','main:app','--host','127.0.0.1','--port',str(baseline_port)],cwd=baseline,env={**s.env,'PYTHONPATH':str(baseline)})
            wait_for(lambda:process.poll() is None and s.reachable(baseline_url+'/health'),'post-T9 baseline API')
        print(json.dumps({'api_url':s.api_url,'baseline_url':baseline_url,'control_dir':str(s.storage),'pg_container':s.pg,'database':'dation_e2e','case_id':cid,'d1':row(s,parent),'d2':row(s,child)}),flush=True)
        sys.stdin.readline()
