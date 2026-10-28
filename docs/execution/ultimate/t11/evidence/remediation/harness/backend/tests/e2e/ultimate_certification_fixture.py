"""Empty business state for the T11 real browser first-user journey."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from ultimate_certification_support import CertificationSandbox
from sandbox import port,wait_for

with CertificationSandbox() as s:
    counts=json.loads(s.sql("SELECT jsonb_build_object('models',(SELECT count(*) FROM logistics_models),'cases',(SELECT count(*) FROM decision_cases),'datasets',(SELECT count(*) FROM datasets),'runs',(SELECT count(*) FROM decision_runs));"))
    assert not any(counts.values()),counts
    s.start_worker()
    baseline=Path('/workspace/work/dation-t11/post-t10-src/backend');baseline_url=None
    if baseline.exists():
        number=port();baseline_url='http://127.0.0.1:'+str(number)
        process=s.start_process('post-t10-baseline-api',['-m','uvicorn','main:app','--host','127.0.0.1','--port',str(number)],cwd=baseline,env={**s.env,'PYTHONPATH':str(baseline)})
        wait_for(lambda:process.poll() is None and s.reachable(baseline_url+'/health'),'frozen post-T10 API')
    print(json.dumps({'api_url':s.api_url,'baseline_url':baseline_url,'pg_container':s.pg,'workspace_id':s.workspace_a,'business_counts':counts}),flush=True)
    sys.stdin.readline()
