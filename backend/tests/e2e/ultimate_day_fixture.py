"""Owned T9 capability on the unchanged T8 Storage/lease fault harness."""
from ultimate_result_fixture import ResultSandbox
from sandbox import Sandbox

class DaySandbox(ResultSandbox):
    def docker(self,*args):
        if args and args[0]=='run':args=(args[0],'--label','dation.qa.phase=T9','--label','dation.qa.owner=codex-dation',*args[1:])
        if args and args[0]=='run' and 'postgres:17-alpine' in args:args=(*args[:-1],'-p','127.0.0.1::5432',args[-1])
        return Sandbox.docker(self,*args)
    def start(self):
        super().start()
        self.sql('UPDATE dation_private.platform_release SET ultimate_scheduling_admissions_enabled=true;')
