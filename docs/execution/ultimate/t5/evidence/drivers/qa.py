"""Freeze the incremental T5 candidate and run only authorized final suites."""
from datetime import datetime,timezone
from pathlib import Path
import difflib,glob,hashlib,json,os,re,subprocess,time
ROOT=Path('/workspace/Dation');B=ROOT/'backend';W=Path('/workspace/work/dation-t5')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
initial=json.loads((W/'initial-state.json').read_text());pending=subprocess.check_output(['git','ls-files','--modified','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
files={};patch=[]
for name in sorted(set(pending)-{''}):
 if not name.startswith(('backend/','supabase/')):continue
 path=ROOT/name
 if name in initial['files']:old=(W/'post-t4'/name).read_bytes();baseline='post-T4 checkpoint'
 else:
  result=subprocess.run(['git','show','HEAD:'+name],cwd=ROOT,capture_output=True);old=result.stdout if result.returncode==0 else None;baseline='HEAD' if old is not None else 'new T5 file'
 if old==path.read_bytes():continue
 files[name]={'bytes':path.stat().st_size,'sha256':sha(path),'baseline_sha256':hashlib.sha256(old).hexdigest() if old is not None else None,'baseline':baseline}
 patch.extend(difflib.unified_diff((old or b'').decode().splitlines(True),path.read_text().splitlines(True),fromfile='post-T4/'+name,tofile='T5/'+name))
(W/'candidate.json').write_text(json.dumps({'phase':'T5','head':initial['head'],'frozen_at':datetime.now(timezone.utc).isoformat(),'files':files},indent=2)+'\n');(W/'t5-changes.patch').write_text(''.join(patch))
env=os.environ.copy()
for k in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:env[k]=''
for k in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(k,None)
env.update(PYTHONDONTWRITEBYTECODE='1',DATION_T5_BROWSER_ARTIFACTS=str(W/'browser'),DATION_T3_BROWSER_ARTIFACTS=str(W/'setup-focal'))
P=str(ROOT/'.venv/bin/python');BR=str(B/'.browser-venv/bin/python')
commands={
 'B-PY':([P,'-B','-m','unittest','discover','-s','tests','-v'],None),
 'B-NODE':(['node','--test',*sorted(glob.glob('tests/test_*.js',root_dir=B)),*sorted(glob.glob('tests/test_*.mjs',root_dir=B))],None),
 'S5':([P,'-B','-m','unittest','test_ultimate_graph','-v'],'tests/integration'),
 'W5':([BR,'-B','-m','unittest','test_ultimate_navigation','-v'],'tests/browser'),
 'B-FOCUS':([BR,'-B','-m','unittest','test_run_lineage_polish','test_navigation.NavigationTests.test_foundation_dashboard_navigation_prefers_approved_over_later_candidate','-v'],'tests/browser'),
 'FOCAL-CASE-CREATE':([BR,'-B','-m','unittest','test_ultimate_case_setup.UltimateCaseSetupTests.test_01_ui_model_publish_case_without_csv_and_reload','-v'],'tests/browser'),
}
for suite,(command,pythonpath) in commands.items():
 if os.environ.get('DATION_T5_SUITES') and suite not in os.environ['DATION_T5_SUITES'].split(','):continue
 child=env.copy()
 if pythonpath:child['PYTHONPATH']=pythonpath
 else:child.pop('PYTHONPATH',None)
 start=datetime.now(timezone.utc).isoformat();begin=time.monotonic();print(json.dumps({'suite':suite,'state':'RUNNING','started_at':start}),flush=True)
 with (W/(suite+'.log')).open('w') as log:r=subprocess.run(command,cwd=B,env=child,stdout=log,stderr=subprocess.STDOUT,text=True)
 text=(W/(suite+'.log')).read_text();text=re.sub(r'(?im)^.*(?:cookie:|authorization:|apikey:).*$','[ephemeral fixture auth headers redacted]',text);(W/(suite+'.log')).write_text(text)
 if suite=='B-NODE':
  def count(k):
   m=re.search(r'^(?:# |ℹ )'+k+r' (\d+)$',text,re.M);return int(m[1]) if m else 0
  n=count('tests');fails=count('fail');errors=0;skips=count('skipped')
 else:
  m=re.findall(r'^Ran (\d+) tests? in ([\d.]+)s',text,re.M);n=int(m[-1][0]) if m else 0;fails=len(re.findall(r'^FAIL:',text,re.M));errors=len(re.findall(r'^ERROR:',text,re.M));skips=len(re.findall(r'^test_.* \.\.\. skipped',text,re.M))
 record={'suite':suite,'status':'PASS' if r.returncode==0 and n>0 and fails==errors==skips==0 else 'FAIL','tests':n,'failures':fails,'errors':errors,'skips':skips,'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'seconds':round(time.monotonic()-begin,3),'cwd':str(B),'command':command,'exit_code':r.returncode,'production_credentials_cleared':True,'PYTHONPATH':pythonpath,'log_sha256':sha(W/(suite+'.log'))}
 (W/(suite+'.result.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
 if record['status']!='PASS':raise SystemExit(1)
 assert all(sha(ROOT/n)==v['sha256'] for n,v in files.items()),'Candidate changed during QA'
print(json.dumps({'candidate_files':len(files),'frozen_candidate_verified':True,'T6_executed':False}),flush=True)
