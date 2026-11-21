"""Explicit J1.01 preview only, on owned local Journey infrastructure."""
import json,sys
from journey_fixture import JourneySandbox

class ModelLibrarySandbox(JourneySandbox):
    def start_process(self,name,args,**options):
        if name=='api':options['env']={**options.get('env',self.env),'DATION_J101_LIBRARY_ENABLED':'true'}
        return super().start_process(name,args,**options)

if __name__=='__main__':
    with ModelLibrarySandbox() as s:
        print(json.dumps({'api_url':s.api_url,'control_dir':str(s.storage),'pg_container':s.pg,'database':s.database}),flush=True)
        sys.stdin.readline()
