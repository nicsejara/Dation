"""Owned T4 API/PostgREST/PostgreSQL + explicit private MIME fixture; no engines."""
import json
import sys
from sandbox import Sandbox
from auth_fixture import VIEWER,DISABLED

class DataPackSandbox(Sandbox):
    def docker(self,*args):
        if args and args[0]=='run':args=(args[0],'--label','dation.qa.phase=T4','--label','dation.qa.owner=codex-dation',*args[1:])
        return super().docker(*args)
    def start_process(self,name,args,**options):
        if name=='storage':args=[x.replace('storage_gateway:app','ultimate_storage_gateway:app') for x in args]
        return super().start_process(name,args,**options)
    def start(self):
        super().start()
        self.sql(f"INSERT INTO dation_private.ultimate_pilot_workspaces(workspace_id,enabled) VALUES('{self.workspace_a}',true); UPDATE dation_private.platform_release SET ultimate_pilot_enabled=true;")
        self.sql('UPDATE dation_private.platform_release SET ultimate_foundation_enabled=true,ultimate_data_pack_enabled=true;')
        (self.directory/'auth-fixture-users.json').write_text(json.dumps({'user-3@example.test':{'id':VIEWER,'refresh':'fixture-refresh-t4-viewer'}}))

if __name__=='__main__':
    with DataPackSandbox() as sandbox:
        print(json.dumps({'api_url':sandbox.api_url,'control_dir':str(sandbox.storage)}),flush=True)
        sys.stdin.readline()
