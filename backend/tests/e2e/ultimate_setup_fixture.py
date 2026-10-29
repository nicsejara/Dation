"""Owned backend for W3. No worker, real auth/API/PostgREST/SQL, no production."""
import json
import sys
from sandbox import Sandbox
from auth_fixture import VIEWER

with Sandbox() as sandbox:
    sandbox.sql(f"INSERT INTO dation_private.ultimate_pilot_workspaces(workspace_id,enabled) VALUES('{sandbox.workspace_a}',true); UPDATE dation_private.platform_release SET ultimate_pilot_enabled=true;")
    sandbox.sql('UPDATE dation_private.platform_release SET ultimate_foundation_enabled=true;')
    (sandbox.directory/'auth-fixture-users.json').write_text(json.dumps({'user-3@example.test':{'id':VIEWER,'refresh':'fixture-refresh-t3-viewer'}}))
    print(json.dumps({'api_url':sandbox.api_url}),flush=True)
    sys.stdin.readline()
