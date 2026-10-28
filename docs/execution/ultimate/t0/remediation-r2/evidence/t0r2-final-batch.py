import json,subprocess
from pathlib import Path
import sys
w=Path('/workspace/work/dation-t0r2')
for suite in ['B-PY','B-NODE','B-BROWSER','B-E2E','B-FOCUS']:
 result=subprocess.run([sys.executable,'/tmp/dation-t0r2-run-suite.py',suite])
 if result.returncode:raise SystemExit(result.returncode)
result=subprocess.run([sys.executable,'/tmp/t0r2-sql-suite.py'])
raise SystemExit(result.returncode)
