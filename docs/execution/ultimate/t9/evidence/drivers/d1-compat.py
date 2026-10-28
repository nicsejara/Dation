"""Compare exact D1 bytes with the post-T8 modules in isolated processes."""
import json,os,subprocess,sys,unittest
from pathlib import Path
B=Path('/workspace/Dation/backend');W=Path('/workspace/work/dation-t9')
CODE=r'''
import json,sys
if sys.argv[1]=='post-t8':
 import app.results,app.engines.common,app.engines.assignment,app.domain.logistics
 for module,suffix in [(app.results,'results'),(app.engines.common,'engines/common'),(app.engines.assignment,'engines/assignment'),(app.domain.logistics,'domain/logistics')]:
  module.__path__.insert(0,'/workspace/work/dation-t9/post-t8/backend/app/'+suffix)
from tests.test_transport_plan_policies import policy_request
from tests.test_transport_plan_core import order,resource
from app.engines.assignment.transport_policy_result import run_transport_policy
from app.results.assembler import assemble
from app.results.canonical import canonical_bytes,content_sha256
cases=[policy_request([order(pallets='1')],[resource(cap='2',services=1)]),
       policy_request([order(pallets='70')],[resource(cap='26',services=2)]),
       policy_request([order(pallets='52')],[resource(cap='26',services=1,source='OWN',operating_cost_per_km='1')])]
results=[]
for request in cases:
 result=run_transport_policy(request,alternative_budget=0);b=assemble(result)
 results.append({'package':content_sha256(canonical_bytes(b.package)),'core':content_sha256(canonical_bytes(result.recommended.output.core)),
  'context':content_sha256(canonical_bytes(b.context)),'artifacts':[(str(a.reference.artifact_id),content_sha256(a.content)) for a in b.artifacts]})
print(json.dumps(results))
'''
def produce(version):
 r=subprocess.run(['/workspace/Dation/.venv/bin/python','-B','-c',CODE,version],cwd=B,env=os.environ.copy(),capture_output=True,text=True,timeout=45)
 if r.returncode:raise AssertionError(r.stderr)
 return json.loads(r.stdout)
old,new=produce('post-t8'),produce('current')
class D1Compatibility(unittest.TestCase):
 def test_external_and_full_publication_bytes(self):self.assertEqual(old[0],new[0])
 def test_partial_coverage_and_null_residual_bytes(self):self.assertEqual(old[1],new[1])
 def test_own_temporal_certificate_and_evidence_bytes(self):self.assertEqual(old[2],new[2])
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(D1Compatibility))
(W/'d1-compat-vectors.json').write_text(json.dumps({'post_t8':old,'current':new,'same_exact_bytes':old==new},indent=2)+'\n')
raise SystemExit(0 if result.wasSuccessful() else 1)
