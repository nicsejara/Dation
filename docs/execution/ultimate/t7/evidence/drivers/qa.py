"""Freeze the post-T6 delta and run authorized T7 suites locally."""
from pathlib import Path
from datetime import datetime,timezone
import difflib,glob,hashlib,json,os,re,subprocess,time,sys
R=Path('/workspace/Dation');B=R/'backend';W=Path('/workspace/work/dation-t7')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
initial=json.loads((W/'initial-state.json').read_text())
pending=subprocess.check_output(['git','ls-files','--modified','--others','--exclude-standard','-z'],cwd=R).decode().split('\0')
files={};patch=[]
for name in sorted(set(pending)-{''}):
 if not name.startswith(('backend/','supabase/')):continue
 p=R/name
 if name in initial['files']:old=(W/'post-t6'/name).read_bytes();baseline='post-T6 checkpoint'
 else:
  got=subprocess.run(['git','show','HEAD:'+name],cwd=R,capture_output=True)
  old=got.stdout if got.returncode==0 else None;baseline='HEAD' if old is not None else 'new T7 file'
 if old==p.read_bytes():continue
 files[name]={'bytes':p.stat().st_size,'sha256':sha(p),'baseline_sha256':hashlib.sha256(old).hexdigest() if old is not None else None,'baseline':baseline}
 patch.extend(difflib.unified_diff((old or b'').decode().splitlines(True),p.read_text().splitlines(True),fromfile='post-T6/'+name,tofile='T7/'+name))
assert len(files)==16,list(files)
assert sum(v['baseline']=='new T7 file' for v in files.values())==12
(W/'candidate.json').write_text(json.dumps({'phase':'T7','head':initial['head'],'frozen_at':datetime.now(timezone.utc).isoformat(),'files':files},indent=2)+'\n')
(W/'t7-changes.patch').write_text(''.join(patch))
env=os.environ.copy()
for k in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:env[k]=''
env['PYTHONDONTWRITEBYTECODE']='1';env.pop('PYTHONPATH',None)
P=str(R/'.venv/bin/python')
commands={'B-PY':[P,'-B','-m','unittest','discover','-s','tests','-v'],
 'B-NODE':['node','--test',*sorted(glob.glob('tests/test_*.js',root_dir=B)),*sorted(glob.glob('tests/test_*.mjs',root_dir=B))],
 'U7':[P,'-B','-m','unittest','tests.test_transport_plan_policies','tests.test_transport_result_package','-v']}
for suite,command in commands.items():
 if len(sys.argv)>1 and suite not in sys.argv[1:]:continue
 start=datetime.now(timezone.utc).isoformat();begin=time.monotonic()
 print(json.dumps({'suite':suite,'state':'RUNNING','started_at':start}),flush=True)
 with (W/(suite+'.log')).open('w') as log:result=subprocess.run(command,cwd=B,env=env,stdout=log,stderr=subprocess.STDOUT,text=True)
 text=(W/(suite+'.log')).read_text();text=re.sub(r'(?im)^.*(?:cookie:|authorization:|apikey:).*$','[ephemeral fixture auth headers redacted]',text);(W/(suite+'.log')).write_text(text)
 if suite=='B-NODE':
  def count(k):
   found=re.search(r'^(?:# |ℹ )'+k+r' (\d+)$',text,re.M);return int(found[1]) if found else 0
  tests=count('tests');failures=count('fail');errors=0;skips=count('skipped')
 else:
  found=re.findall(r'^Ran (\d+) tests? in ([\d.]+)s',text,re.M);tests=int(found[-1][0]) if found else 0
  failures=len(re.findall(r'^FAIL:',text,re.M));errors=len(re.findall(r'^ERROR:',text,re.M));skips=len(re.findall(r'^test_.* \.\.\. skipped',text,re.M))
 record={'suite':suite,'status':'PASS' if result.returncode==0 and tests>0 and failures==errors==skips==0 else 'FAIL',
  'tests':tests,'failures':failures,'errors':errors,'skips':skips,'exit_code':result.returncode,
  'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'seconds':round(time.monotonic()-begin,3),
  'cwd':str(B),'command':command,'production_credentials_cleared':True,'log_sha256':sha(W/(suite+'.log'))}
 (W/(suite+'.result.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
 if record['status']!='PASS':raise SystemExit(1)
 assert all(sha(R/n)==v['sha256'] for n,v in files.items()),'Frozen candidate changed during QA'
print(json.dumps({'source_files':len(files),'frozen_candidate_verified':True,'T8_executed':False}),flush=True)
