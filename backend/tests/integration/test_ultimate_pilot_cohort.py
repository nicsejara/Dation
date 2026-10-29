"""T12-R: real SQL rollout authority; no math, no production configuration."""
import json
import unittest
import test_ultimate_case_models as cases
from test_ultimate_case_models import ADMIN,OTHER,OPERATOR,VIEWER


class UltimatePilotCohortSQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cases.UltimateCaseSQLTests.setUpClass()
        cls.addClassCleanup(cases.UltimateCaseSQLTests.tearDownClass)
        cls.db=cases.UltimateCaseSQLTests()

    def setUp(self):
        self.db.sql('UPDATE dation_private.platform_release SET ultimate_pilot_enabled=true,ultimate_foundation_enabled=true;')
        self.db.sql(f"UPDATE dation_private.ultimate_pilot_workspaces SET enabled=true WHERE workspace_id='{self.db.wa}';")

    def test_default_is_closed_and_no_workspace_is_enrolled_by_migration(self):
        # The same certified chain on a fresh owned DB, before fixture enrollment.
        name=cases.UltimateCaseSQLTests.create_database()
        try:
            row=json.loads(cases.UltimateCaseSQLTests.command("SELECT jsonb_build_object('enabled',(SELECT ultimate_pilot_enabled FROM dation_private.platform_release),'members',(SELECT count(*) FROM dation_private.ultimate_pilot_workspaces));",database=name).stdout)
            self.assertEqual(row,{'enabled':False,'members':0})
        finally:cases.UltimateCaseSQLTests.drop_database(name)

    def test_one_workspace_only_and_payload_cannot_override(self):
        self.assertTrue(self.db.rpc('capabilities')['can_create_case'])
        b=self.db.rpc('capabilities',{'ultimate_pilot_enabled':True,'workspace_id':self.db.wa},user=OTHER,workspace=self.db.wb)
        self.assertFalse(b['enabled']);self.assertFalse(b['can_manage_models'])
        self.db.reject(self.db.rpc_sql('model_create',{'ultimate_pilot_enabled':True,'authorized_workspace_ids':[self.db.wb]},user=OTHER,workspace=self.db.wb),'P0002')
        self.assertEqual(self.db.sql(f"SELECT dation_private.ultimate_pilot_allows('{self.db.wb}');"),'f')

    def test_release_authority_cannot_be_written_or_read_by_app_or_browser_roles(self):
        for role in ['anon','authenticated','service_role']:
            for sql in [
                'SELECT * FROM dation_private.ultimate_pilot_workspaces;',
                f"INSERT INTO dation_private.ultimate_pilot_workspaces VALUES('{self.db.wb}',true);",
                'UPDATE dation_private.platform_release SET ultimate_pilot_enabled=true;',
                f"SELECT dation_private.ultimate_pilot_allows('{self.db.wa}');"]:
                with self.subTest(role=role,sql=sql):self.db.reject('SET ROLE '+role+'; '+sql,'42501')
        self.assertEqual(self.db.sql("SELECT relrowsecurity FROM pg_class WHERE oid='dation_private.ultimate_pilot_workspaces'::regclass;"),'t')

    def test_kill_switch_and_removal_keep_historical_context_readable(self):
        c=self.db.case()
        for change in ['UPDATE dation_private.platform_release SET ultimate_pilot_enabled=false;',
                       f"UPDATE dation_private.platform_release SET ultimate_pilot_enabled=true; UPDATE dation_private.ultimate_pilot_workspaces SET enabled=false WHERE workspace_id='{self.db.wa}';"]:
            self.db.sql(change)
            self.assertFalse(self.db.rpc('capabilities')['enabled'])
            data=self.db.rpc('case_get',{'case_id':c['case']['id']})
            self.assertEqual(data['case'],c['case']);self.assertFalse(data['permissions']['can_edit'])
            self.db.reject(self.db.rpc_sql('case_update',{}),'P0002')

    def test_workspace_roles_never_expand_allowlist(self):
        admin=self.db.rpc('capabilities',user=ADMIN)
        operator=self.db.rpc('capabilities',user=OPERATOR)
        viewer=self.db.rpc('capabilities',user=VIEWER)
        self.assertTrue(admin['can_manage_models']);self.assertTrue(operator['can_create_case'])
        self.assertFalse(operator['can_manage_models']);self.assertFalse(viewer['can_create_case'])
        self.db.sql('UPDATE dation_private.platform_release SET ultimate_pilot_enabled=false;')
        for actor in [ADMIN,OPERATOR,VIEWER]:self.assertFalse(self.db.rpc('capabilities',user=actor)['enabled'])

    def test_no_role_or_workspace_claim_bypass(self):
        self.db.reject(self.db.rpc_sql('capabilities',{'role':'admin','workspace_id':self.db.wa},user=OTHER),'42501')
        self.db.reject('SET ROLE authenticated; '+self.db.rpc_sql('capabilities').split('; ',1)[1],'42501')


if __name__=='__main__':unittest.main()
