"""J1.02 append-only definitions against the full isolated PostgreSQL17 catalog."""
from copy import deepcopy
import json
import unittest
from uuid import uuid4
from app.models.decision_case_v2 import UltimateCaseCreateV2, CaseDefinitionUpdateV2
from app.services import logistics_model_service as models
from app.results.canonical import canonical_tree, canonical_bytes, content_sha256, policy_hash
from tests.test_decision_case_j102 import definition
from tests.integration import test_ultimate_case_models as baseline
from ultimate_sql_support import UltimateSQLSandbox


class DecisionCaseV2SQLTests(UltimateSQLSandbox,unittest.TestCase):
    verify_owner=classmethod(baseline.UltimateCaseSQLTests.verify_owner.__func__)
    sql=baseline.UltimateCaseSQLTests.sql
    reject=baseline.UltimateCaseSQLTests.reject
    rpc_sql=baseline.UltimateCaseSQLTests.rpc_sql
    rpc=baseline.UltimateCaseSQLTests.rpc
    invoke=baseline.UltimateCaseSQLTests.invoke
    model=baseline.UltimateCaseSQLTests.model
    publish=baseline.UltimateCaseSQLTests.publish

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.command('UPDATE dation_private.platform_release SET admissions_open=true,workflow_gates_enabled=true,ultimate_foundation_enabled=true,ultimate_pilot_enabled=true,unified_journey_enabled=true,ultimate_data_pack_enabled=true,j102_enabled=true;')
        for uid in [baseline.ADMIN,baseline.OTHER,baseline.VIEWER]:cls.command(f"INSERT INTO auth.users VALUES('{uid}','{uid}@example.test',now());")
        cls.wa=json.loads(cls.command(f"SELECT platform_create_workspace('{baseline.ADMIN}','J102 A','AR','UTC','ARS');").stdout)['workspace_id']
        cls.wb=json.loads(cls.command(f"SELECT platform_create_workspace('{baseline.OTHER}','J102 B','AR','UTC','ARS');").stdout)['workspace_id']
        for wid,uid in [(cls.wa,baseline.ADMIN),(cls.wb,baseline.OTHER)]:
            cls.command(f"SELECT platform_set_member_responsibilities('{wid}','{uid}','{uid}',(SELECT updated_at FROM workspace_members WHERE workspace_id='{wid}' AND user_id='{uid}'),ARRAY['decision_owner']); INSERT INTO dation_private.ultimate_pilot_workspaces(workspace_id,enabled) VALUES('{wid}',true);")
        cls.command(f"INSERT INTO profiles(id) VALUES('{baseline.VIEWER}'); INSERT INTO workspace_members(workspace_id,user_id,access_role,status) VALUES('{cls.wa}','{baseline.VIEWER}','viewer','active');")

    def v2sql(self,operation,arguments,user=baseline.ADMIN,workspace=None):
        return f"SET ROLE service_role; SELECT platform_decision_case_v2('{workspace or self.wa}','{user}','{operation}',{baseline.literal(arguments)});"

    def v2(self,operation,arguments,**options):return json.loads(self.sql(self.v2sql(operation,arguments,**options)))

    def new_case(self,**changes):
        m=self.model();v=self.publish(m)['version']
        d=definition(model_binding=dict(model_id=m['model']['id'],model_version_id=v['id'],configuration_hash=v['config_hash'],contract_hash=v['contract_hash']),**changes)
        body=UltimateCaseCreateV2(id=uuid4(),**d.identity.model_dump(),**d.decision_context.model_dump(),logistics_model_version_id=v['id'],case_policy=d.case_policy,decision_owner_user_id=baseline.ADMIN,definition_v2=d)
        args=canonical_tree(body);args.update(case_policy=canonical_tree(body.case_policy),case_policy_hash=policy_hash(body.case_policy),**models.empty_pack_snapshot(self.wa,body.id),creation_intent_hash=models.snapshot_hash('case_creation_intent_v1',{'actor':baseline.ADMIN,**body.model_dump(mode='json')}))
        # SQL-only staging facts, not a claim that files were normalized. The
        # browser and worker E2E below use real private bytes and normalizers.
        pid=str(uuid4());self.sql(f"INSERT INTO dation_private.journey_preparations(id,workspace_id,created_by,model_version_id,parent_case_id,status,creation_body) VALUES('{pid}','{self.wa}','{baseline.ADMIN}','{v['id']}',"+("'"+str(d.provenance.parent_case_id)+"'" if d.provenance else 'NULL')+",'FINALIZING',"+baseline.literal(canonical_tree(body))+");")
        for entity in ['transport_demand','transport_resources']:
            self.sql(f"INSERT INTO dation_private.journey_uploads(id,workspace_id,preparation_id,entity,intent_hash,metadata,ready,selected) VALUES('{uuid4()}','{self.wa}','{pid}','{entity}','{'a'*64}','{{}}',true,true);")
        return self.rpc('case_create',args),args

    def update_definition(self,context,definition_,**changes):
        revision=context['case_definition'];payload=CaseDefinitionUpdateV2(mutation_id=uuid4(),expected_revision=revision['revision'],expected_updated_at=context['case']['updated_at'],definition_v2=definition_)
        args=canonical_tree(payload);args.update(case_id=context['case']['id'],case_policy_hash=policy_hash(payload.definition_v2.case_policy));args.update(changes)
        return self.v2('update',args),args

    def test_01_atomic_initial_snapshot_and_replay_are_exact(self):
        c,args=self.new_case();row=c['case_definition'];self.assertEqual(row['revision'],1)
        self.assertEqual(content_sha256(canonical_bytes(row['snapshot'])),row['definition_hash'])
        self.assertEqual(self.rpc('case_create',args)['case_definition'],row)
        self.assertEqual(self.v2('history',{'case_id':c['case']['id']})['total'],1)
        changed=deepcopy(args);changed['definition_v2']['identity']['name']='Other'
        self.reject(self.rpc_sql('case_create',changed),'55006')

    def test_02_metadata_cas_history_and_mutation_recovery(self):
        c,_=self.new_case();old=deepcopy(c['case_definition']);d=deepcopy(old['snapshot']);d['identity']['name']='Revisión dos'
        updated,args=self.update_definition(c,d);self.assertEqual(updated['case_definition']['revision'],2)
        self.assertEqual(self.v2('revision',{'case_id':c['case']['id'],'revision_id':old['id']}),old)
        self.assertEqual(self.v2('update',args)['case_definition'],updated['case_definition'])
        args['mutation_id']=str(uuid4());self.reject(self.v2sql('update',args),'55006')
        self.assertEqual(self.v2('history',{'case_id':c['case']['id'],'limit':1})['total'],2)
        self.reject(f"UPDATE dation_private.case_definition_revisions SET snapshot='{{}}' WHERE id='{old['id']}';",'22023')
        self.reject(f"DELETE FROM dation_private.case_definition_revisions WHERE id='{old['id']}';",'22023')

    def test_03_model_is_pinned_and_frozen_math_requires_derivation(self):
        c,_=self.new_case();d=deepcopy(c['case_definition']['snapshot']);d['model_binding']['model_id']=str(uuid4())
        with self.assertRaises(AssertionError):self.update_definition(c,d)
        self.sql(f"UPDATE decision_cases SET context_frozen_at=now() WHERE id='{c['case']['id']}';")
        frozen=self.rpc('case_get',{'case_id':c['case']['id']});d=deepcopy(frozen['case_definition']['snapshot']);d['acceptance_policy']['threshold']='0.9'
        with self.assertRaises(AssertionError):self.update_definition(frozen,d)
        d=deepcopy(frozen['case_definition']['snapshot']);d['identity']['name']='Nombre permitido'
        updated,_=self.update_definition(frozen,d);self.assertEqual(updated['case_definition']['revision'],2)
        self.assertEqual(updated['model_version'],c['model_version'])

    def test_04_parent_revision_authorized_and_original_unchanged(self):
        c,_=self.new_case();source=c['case_definition']
        derived,_=self.new_case(provenance=dict(parent_case_id=c['case']['id'],parent_definition_revision_id=source['id'],reason='Nueva planificación'))
        self.assertNotEqual(derived['case']['id'],c['case']['id']);self.assertEqual(derived['case_definition']['snapshot']['provenance']['parent_definition_revision_id'],source['id'])
        self.assertEqual(self.rpc('case_get',{'case_id':c['case']['id']}),c)
        with self.assertRaises(AssertionError):self.new_case(provenance=dict(parent_case_id=c['case']['id'],parent_definition_revision_id=str(uuid4()),reason='Falso'))

    def test_05_tenants_viewers_and_private_privileges(self):
        c,args=self.new_case();cid=c['case']['id']
        self.reject(self.v2sql('history',{'case_id':cid},user=baseline.OTHER,workspace=self.wb),'P0002')
        self.reject(self.rpc_sql('case_create',args,user=baseline.VIEWER),'42501')
        self.reject("SET ROLE authenticated; SELECT * FROM dation_private.case_definition_revisions;",'42501')
        self.reject("SET ROLE service_role; SELECT * FROM dation_private.case_definition_revisions;",'42501')
        self.reject(self.v2sql('validate',{'definition_v2':args['definition_v2']},user=baseline.OTHER,workspace=self.wb),'P0002')
        self.assertEqual(self.v2('history',{'case_id':cid},user=baseline.VIEWER)['total'],1)

    def test_06_writers_off_history_still_readable_legacy_not_rewritten(self):
        c,_=self.new_case()
        self.sql('UPDATE dation_private.platform_release SET j102_enabled=false;')
        try:
            self.assertEqual(self.rpc('case_get',{'case_id':c['case']['id']})['case_definition'],c['case_definition'])
            self.assertEqual(self.v2('history',{'case_id':c['case']['id']})['total'],1)
            with self.assertRaises(AssertionError):self.update_definition(c,c['case_definition']['snapshot'])
            self.assertFalse(self.rpc('capabilities')['decision_case_v2_write_enabled'])
        finally:self.sql('UPDATE dation_private.platform_release SET j102_enabled=true;')

    def test_07_batched_projection_scopes_rows_and_preserves_legacy(self):
        c,_=self.new_case();data=self.v2('projection',{'case_ids':[c['case']['id'],str(uuid4())]})
        self.assertEqual(list(data),[c['case']['id']]);self.assertEqual(data[c['case']['id']]['model_version_id'],c['model_version']['id'])
        self.assertEqual(self.v2('projection',{'case_ids':[c['case']['id']]},user=baseline.OTHER,workspace=self.wb),{})

    def test_08_no_direct_v2_creation_without_exact_validated_preparation(self):
        _,args=self.new_case();args=deepcopy(args);args['id']=str(uuid4())
        before=self.sql('SELECT count(*) FROM decision_cases;')
        self.reject(self.rpc_sql('case_create',args),'55006')
        self.assertEqual(self.sql('SELECT count(*) FROM decision_cases;'),before)

    def test_09_python_sql_math_hash_matches_and_ignores_only_revision_identity(self):
        from tests.test_decision_case_j102 import bound
        from tests.test_transport_plan_policies import policy_request
        from app.engines.assignment.transport_plan import IDENTITY
        from app.results.canonical import input_context_hash
        req=bound(policy_request());ctx=canonical_tree(req.context)
        actual=self.sql('SELECT dation_private.t9_input_hash('+baseline.literal(ctx)+','+baseline.literal(canonical_tree(IDENTITY))+');')
        self.assertEqual(actual,input_context_hash(req.context,IDENTITY))
        ctx['decision_definition']['definition_revision_id']=str(uuid4());ctx['decision_definition']['definition_hash']='f'*64
        self.assertEqual(self.sql('SELECT dation_private.t9_input_hash('+baseline.literal(ctx)+','+baseline.literal(canonical_tree(IDENTITY))+');'),actual)
        ctx['decision_definition']['acceptance_policy']['threshold']='0.9'
        self.assertNotEqual(self.sql('SELECT dation_private.t9_input_hash('+baseline.literal(ctx)+','+baseline.literal(canonical_tree(IDENTITY))+');'),actual)

    def test_10_archived_model_keeps_committed_intent_and_case_history_readable(self):
        c,args=self.new_case();self.sql(f"UPDATE logistics_models SET status='archived',revision=revision+1 WHERE id='{c['model']['id']}';")
        self.assertEqual(self.rpc('case_create',args)['case_definition'],c['case_definition'])
        self.assertEqual(self.rpc('case_get',{'case_id':c['case']['id']})['model_version'],c['model_version'])

