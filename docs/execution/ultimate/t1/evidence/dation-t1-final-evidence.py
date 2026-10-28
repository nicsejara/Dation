"""T1 final evidence only: no suite repetition or remote operations."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = Path('/workspace/Dation')
WORK = Path('/workspace/work/dation-t1')
OUT = ROOT / 'docs/execution/ultimate/t1'
EVIDENCE = OUT / 'evidence'
EVIDENCE.mkdir(parents=True, exist_ok=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

initial = read(WORK/'initial-state.json')
freeze = read(WORK/'source-freeze.json')
preserved = [{'path':name, 'sha256':expected, 'unchanged':(ROOT/name).is_file() and sha(ROOT/name)==expected}
             for name,expected in initial['preserve'].items()]
assert len(preserved)==248 and all(row['unchanged'] for row in preserved)
baseline_manifest = ROOT/'docs/execution/ultimate/t0/remediation-r2/artifact-integrity.json'
assert sha(baseline_manifest)==initial['t0_r2_manifest_sha256']
frozen = [{'path':name, 'sha256':expected, 'unchanged':sha(ROOT/name)==expected}
          for name,expected in freeze['files'].items()]
assert len(frozen)==17 and all(row['unchanged'] for row in frozen)
assert git('rev-parse', 'HEAD')==initial['head']
assert not git('diff', '--cached', '--name-only')
changed=git('diff','--name-only').splitlines()
assert sorted(changed)==sorted(initial['existing_changed_paths'])

def identities(path):
    found=[]
    for prefix, location in re.findall(r'^([^\n]+?) \(([^()\n]+)\) \.\.\.',path.read_text(),re.M):
        if prefix=='unittest.case.FunctionTestCase':
            found.append(location)
        elif prefix.startswith('test_'):
            found.append(location+'.'+prefix)
    return found

old_ids=identities(ROOT/'docs/execution/ultimate/t0/remediation-r2/evidence/B-PY.log')
new_ids=identities(WORK/'B-PY.log')
assert len(old_ids)==383 and len(new_ids)==444
assert not (Counter(old_ids)-Counter(new_ids))
baseline=read(ROOT/'docs/execution/ultimate/t0/remediation-r2/qa-summary.json')
old_node=next(row for row in baseline['tests'] if row['suite']=='B-NODE')
node=read(WORK/'B-NODE.result.json')
assert old_node['command']==node['command']

sys.path.insert(0,str(ROOT/'backend'))
for key in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:
    os.environ[key]=''
from main import app
from app.results.canonical import canonical_bytes
from app.results.registry import contract_metadata
from tests.ultimate_fixtures import package, ai_context
actual_api=app.openapi()
old_api=read(ROOT/'docs/execution/ultimate/t0/evidence/openapi.json')
assert actual_api==old_api
api={'exact_openapi_equal_to_T0':True,'paths':len(actual_api['paths']),
     'operations':sum(key.lower() in {'get','post','put','patch','delete','head','options','trace'}
                      for path in actual_api['paths'].values() for key in path),
     'no_endpoints_added':True,'baseline_sha256':sha(ROOT/'docs/execution/ultimate/t0/evidence/openapi.json'),
     'import_only_no_lifespan_or_request':True}
write(EVIDENCE/'api-preservation.json',api)
metadata=contract_metadata()
sizes={'fixture_kind':'hypothetical ABI fixtures, no engine or assembler producer',
       'budgets':metadata['budgets'],'measure':'canonical UTF-8 bytes',
       'D1_package':len(canonical_bytes(package())),
       'D2_package':len(canonical_bytes(package('d2'))),
       'D1_inline_visual':len(canonical_bytes(package().primary_visual.projection)),
       'D2_inline_visual':len(canonical_bytes(package('d2').primary_visual.projection)),
       'decision_context':len(canonical_bytes(ai_context())),
       'selection_fixture':None,
       'not_certified':['production performance','chunking','retrieval','payloads from real engines']}
assert sizes['D1_package']<=sizes['budgets']['package_bytes']
assert sizes['D2_package']<=sizes['budgets']['package_bytes']
assert sizes['D1_inline_visual']<=sizes['budgets']['visual_inline_bytes']
assert sizes['D2_inline_visual']<=sizes['budgets']['visual_inline_bytes']
write(EVIDENCE/'payload-budgets.json',sizes)
proof={'phase':'T1','captured_at':datetime.now(timezone.utc).isoformat(),
       'source_head':initial['head'],'baseline_artifacts_verified':len(preserved),
       'baseline_manifest_unchanged':True,'baseline_files':preserved,
       'candidate_files_match_final_test_freeze':frozen,
       'existing_tracked_changes_unchanged':changed,
       'baseline_python_tests':len(old_ids),'final_python_tests':len(new_ids),
       'baseline_python_test_ids_retained':old_ids,
       'missing_baseline_python_test_ids':[],
       'new_python_test_ids':sorted((Counter(new_ids)-Counter(old_ids)).elements()),
       'baseline_node_command_unchanged':True,'node_files':len(node['command'])-2,
       'no_stage_commit_push_or_remote_operations':True}
write(EVIDENCE/'legacy-preservation.json',proof)
print(json.dumps({'preserved':len(preserved),'frozen_source_files':len(frozen),'legacy_python_ids':len(old_ids),
                  'new_python_ids':len(new_ids)-len(old_ids),'node_files':len(node['command'])-2,
                  'api':api,'sizes':sizes},ensure_ascii=False))
