from pathlib import Path
import hashlib,json,os,subprocess,sys
sys.path.insert(0,'/workspace/Dation/backend/tests/e2e')
from sandbox import Sandbox
out=Path('/workspace/work/dation-t3/dda-parity');out.mkdir(exist_ok=True)
env=os.environ.copy()
for key in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:env[key]=''
for key in ['DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(key,None)
env['DOCKER_HOST']='unix:///var/run/docker.sock';os.environ.update(env)
with Sandbox() as sandbox:
 for state in ['before','after']:
  sandbox.sql('UPDATE dation_private.platform_release SET ultimate_foundation_enabled='+('false' if state=='before' else 'true')+';')
  subprocess.run(['/workspace/Dation/backend/.browser-venv/bin/python','-B','/tmp/dation-t3-dda-parity-browser.py'],env={**env,'DATION_T3_PARITY_URL':sandbox.api_url,'DATION_T3_PARITY_STATE':state},check=True)
results=[]
for width in [1440,390]:
 hashes={state:hashlib.sha256((out/f'{state}-{width}.png').read_bytes()).hexdigest() for state in ['before','after']}
 before=json.loads((out/f'before-{width}.json').read_text());after=json.loads((out/f'after-{width}.json').read_text())
 assert before==after,'Hero geometry/computed styles changed'
 results.append(dict(width=width,png_bytes_equal=hashes['before']==hashes['after'],geometry_and_computed_styles_equal=True,sha256=hashes))
(out/'parity.json').write_text(json.dumps({'real_dda_hero':True,'only_difference': 'closed flag vs enabled T3 entry below the unchanged Hero','viewports':results},indent=2)+'\n')
print('PASS: actual DDA Hero geometry/computed styles unchanged at desktop/mobile; raw PNG hashes recorded for pixel assessment.')
