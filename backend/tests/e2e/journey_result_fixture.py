"""Owned opt-in UX04 result fixture. Real finite tests; worker dies with sandbox."""
import json,sys
from ultimate_day_fixture import DaySandbox
class JourneyResultSandbox(DaySandbox):
    def start_process(self,name,args,**options):
        if name=='api':options['env']={**options.get('env',self.env),'DATION_UNIFIED_JOURNEY_ENABLED':'true'}
        return super().start_process(name,args,**options)
    def start(self):
        super().start();self.sql('UPDATE dation_private.platform_release SET unified_journey_enabled=true;')
if __name__=='__main__':
    with JourneyResultSandbox() as s:
        s.start_worker()
        print(json.dumps({'api_url':s.api_url,'control_dir':str(s.storage),'pg_container':s.pg,'database':s.database}),flush=True)
        sys.stdin.readline()
