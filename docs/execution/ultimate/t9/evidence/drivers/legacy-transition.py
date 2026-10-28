"""One existing legacy lineage/worker regression on the owned T8 schema."""
import json,os,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,'tests/e2e')
from ultimate_day_fixture import DaySandbox
import test_saga3

W=Path('/workspace/work/dation-t9')
class TransitionSandbox(DaySandbox):
    def start(self):
        super().start()
        binding=self.docker('port',self.pg,'5432/tcp');assert binding.startswith('127.0.0.1:')
        command=['/home/agent/.npm/_npx/91eb58246759989d/node_modules/@supabase/cli-linux-x64/bin/supabase','db','advisors','--db-url',
                 'postgresql://postgres@'+binding+'/dation_e2e?sslmode=disable','--type','all','--output','json']
        with (W/'advisors.json').open('w') as out,(W/'advisors.stderr').open('w') as err:r=subprocess.run(command,stdout=out,stderr=err,timeout=50)
        (W/'advisors-command.json').write_text(json.dumps({'scope':'owned loopback T8 final schema only','command':command,'exit_code':r.returncode},indent=2)+'\n')
        if r.returncode:raise AssertionError('Owned Advisors failed; see separate diagnostic')
test_saga3.Sandbox=TransitionSandbox
suite=unittest.defaultTestLoader.loadTestsFromName('Saga3Tests.test_multiple_runs_reopen_current_and_downstream_without_destroying_evidence',test_saga3)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
