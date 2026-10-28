"""Owned T5 API/SQL/Storage-contract fixture. No Ultimate engine is started."""
import json,sys
from ultimate_data_fixture import DataPackSandbox, Sandbox

class GraphSandbox(DataPackSandbox):
    def docker(self,*args):
        if args and args[0]=='run':args=(args[0],'--label','dation.qa.phase=T5','--label','dation.qa.owner=codex-dation',*args[1:])
        return Sandbox.docker(self,*args)

if __name__=='__main__':
    with GraphSandbox() as sandbox:
        print(json.dumps({'api_url':sandbox.api_url,'control_dir':str(sandbox.storage),'pg_container':sandbox.pg,'database':sandbox.database}),flush=True)
        sys.stdin.readline()
