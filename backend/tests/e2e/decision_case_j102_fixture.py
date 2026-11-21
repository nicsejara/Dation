"""J1.02 opt-in only in owned local Auth/API/PG17/private Storage infrastructure."""
import json
import sys
from model_library_fixture import ModelLibrarySandbox


class DecisionCaseSandbox(ModelLibrarySandbox):
    def start_process(self,name,args,**options):
        if name=='api':options['env']={**options.get('env',self.env),'DATION_J102_ENABLED':'true'}
        return super().start_process(name,args,**options)

    def start(self):
        super().start()
        self.sql('UPDATE dation_private.platform_release SET j102_enabled=true;')


if __name__=='__main__':
    with DecisionCaseSandbox() as s:
        print(json.dumps({'api_url':s.api_url,'control_dir':str(s.storage),'pg_container':s.pg,'database':s.database}),flush=True)
        sys.stdin.readline()
