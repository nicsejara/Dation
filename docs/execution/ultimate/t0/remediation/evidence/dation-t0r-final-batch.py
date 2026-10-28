import subprocess,json
from pathlib import Path
commands=['B-PY','B-NODE','B-FOCUS','B-BROWSER','B-E2E']
results=[]
for suite in commands:
 result=subprocess.run(['/workspace/Dation/.venv/bin/python','-B','/tmp/dation-t0r-run-suite.py',suite])
 results.append({'suite':suite,'exit_code':result.returncode})
Path('/workspace/work/dation-t0r/revalidation/batch-results.json').write_text(json.dumps(results,indent=2)+'\n')
