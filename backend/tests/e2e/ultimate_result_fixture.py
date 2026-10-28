"""Owned T8 API + PostgreSQL/PostgREST + private Storage fixture + real worker."""
import json,sys
from ultimate_data_fixture import DataPackSandbox,Sandbox

class ResultSandbox(DataPackSandbox):
    def docker(self,*args):
        if args and args[0]=='run':args=(args[0],'--label','dation.qa.phase=T8','--label','dation.qa.owner=codex-dation',*args[1:])
        if args and args[0]=='run' and 'postgres:17-alpine' in args:args=(*args[:-1],'-p','127.0.0.1::5432',args[-1])
        return Sandbox.docker(self,*args)
    def start_process(self,name,args,**options):
        if name=='storage':args=[x.replace('storage_gateway:app','ultimate_result_gateway:app') for x in args]
        return Sandbox.start_process(self,name,args,**options)
    def start(self):
        super().start()
        self.sql('UPDATE dation_private.platform_release SET ultimate_admissions_enabled=true;')

if __name__=='__main__':
    with ResultSandbox() as s:
        print(json.dumps({'api_url':s.api_url,'control_dir':str(s.storage),'pg_container':s.pg}),flush=True)
        sys.stdin.readline()
