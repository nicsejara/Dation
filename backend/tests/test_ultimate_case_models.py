"""U3: T3 configuration, Case setup contracts and exact pre-admission snapshots."""
import copy
from datetime import datetime,timezone
import unittest
from unittest.mock import AsyncMock,patch
from uuid import UUID,uuid4

from pydantic import ValidationError
from app.models.ultimate_foundation import (LogisticsModelConfigurationV1,ModelCreate,ModelUpdate,ModelPublish,
    UltimateCaseCreate,UltimateCaseUpdate,PlanningContextV1)
from app.services import logistics_model_service as service
from app.domain.logistics.contracts import CasePolicy
from app.results.canonical import policy_hash


def config(**changes):
    values=dict(operating_role='SHIPPER',allowed_sources=['OWN','EXTERNAL'],
        active_dimensions=['pallets'],primary_dimension='pallets',currency_policy={'currency':'ARS','minor_units':2})
    values.update(changes)
    return LogisticsModelConfigurationV1.model_validate(values)


def case_request(**changes):
    values=dict(id=uuid4(),name='Semana 45',logistics_model_version_id=uuid4(),planning_start='2026-11-02',planning_end='2026-11-08',
        horizon_type='WEEKLY',case_policy={'primary_goal':'MINIMIZE_COST'})
    values.update(changes);return UltimateCaseCreate.model_validate(values)


def raw_context():
    ws,cid,mid,mvid=[str(uuid4()) for _ in range(4)];configuration,h=service.configuration_snapshot(config());descriptor,ch=service.contract_reference(h)
    p=service.empty_pack_snapshot(ws,cid);policy=CasePolicy(primary_goal='MINIMIZE_COST')
    return dict(case=dict(workspace_id=ws,id=cid,label='Semana 45',description=None,planning_start='2026-11-02',planning_end='2026-11-08',
        operating_mode='OPERATIONAL',horizon_type='WEEKLY',case_policy_jsonb=policy.model_dump(mode='json'),case_policy_hash=policy_hash(policy),
        graph_definition_version=service.GRAPH_VERSION,context_frozen_at=None),
        model=dict(id=mid,name='Operación'),model_version=dict(id=mvid,model_id=mid,version=1,config_jsonb=configuration,
            config_hash=h,contract_hash=ch,contract_registry_version=service.CONTRACT_REGISTRY_VERSION),
        pack=dict(id=p['pack_id']),pack_version=dict(id=p['pack_version_id'],version=1,manifest_hash=p['manifest_hash']),responsibilities={},entry_count=0)


class UltimateCaseModelsTests(unittest.TestCase):
    def test_three_operating_roles_preserve_the_same_domain_contract_and_no_runtime_selection(self):
        for role in ['SHIPPER','LOGISTICS_PROVIDER','HYBRID']:
            values=config(operating_role=role);self.assertEqual(values.transport_pattern,'DIRECT')
            self.assertNotIn('engine_name',values.model_dump());self.assertNotIn('access_role',values.model_dump())

    def test_dimensions_and_sources_are_explicit_and_unique(self):
        for change in [dict(active_dimensions=['weight_kg'],primary_dimension='pallets'),dict(active_dimensions=['pallets','pallets']),dict(allowed_sources=[]),dict(allowed_sources=['OWN','OWN'])]:
            with self.subTest(change=change),self.assertRaises(ValidationError):config(**change)

    def test_cost_and_billing_options_are_closed(self):
        for change in [dict(external_cost_models=[]),dict(external_cost_models=['PER_KM'],per_km_billing_bases=[]),dict(own_cost_model='FREE_OWN')]:
            with self.subTest(change=change),self.assertRaises(ValidationError):config(**change)

    def test_currency_precision_does_not_infer_live_workspace_or_fx(self):
        self.assertEqual(config().currency_policy.currency,'ARS')
        for policy in [{'currency':'usd','minor_units':2},{'currency':'USD','minor_units':True},{'currency':'USD','minor_units':7}]:
            with self.subTest(policy=policy),self.assertRaises(ValidationError):config(currency_policy=policy)

    def test_configuration_hash_is_exact_and_semantic(self):
        value,h=service.configuration_snapshot(config());again=service.configuration_snapshot(dict(reversed(list(value.items()))))
        self.assertEqual((value,h),again)
        self.assertNotEqual(h,service.configuration_snapshot(config(split_permitted=True))[1])
        descriptor,ch=service.contract_reference(h)
        self.assertEqual(descriptor['configuration_hash'],h);self.assertEqual(ch,service.contract_reference(h)[1])
        self.assertNotIn('csv',descriptor);self.assertNotIn('template',descriptor)

    def test_model_identity_text_is_normalized_and_not_part_of_configuration(self):
        payload=ModelCreate(id=uuid4(),name='  Operacio\u0301n  ',configuration=config())
        self.assertEqual(payload.name,'Operación')
        with self.assertRaises(ValidationError):ModelCreate(id=uuid4(),name='   ',configuration=config())
        with self.assertRaises(ValidationError):ModelPublish(version_id=uuid4(),expected_revision=True)

    def test_case_exists_without_any_dataset_or_execution_fields(self):
        request=case_request();self.assertNotIn('orders_dataset_id',request.model_dump());self.assertNotIn('fleet_dataset_id',request.model_dump())
        with self.assertRaises(ValidationError):case_request(orders_dataset_id=uuid4())

    def test_horizon_is_inclusive_ordered_and_date_only(self):
        self.assertEqual(case_request(planning_end='2026-11-02').planning_end.isoformat(),'2026-11-02')
        for change in [dict(planning_end='2026-11-01'),dict(planning_start='2026-11-02T00:00:00Z'),dict(planning_start=datetime.now(timezone.utc))]:
            with self.subTest(change=change),self.assertRaises(ValidationError):case_request(**change)

    def test_horizon_types_and_operating_modes_do_not_create_simulation_engine(self):
        for kind in ['DAILY','WEEKLY','MONTHLY','CUSTOM']:
            for mode in ['OPERATIONAL','SIMULATION']:
                self.assertEqual(case_request(horizon_type=kind,operating_mode=mode).operating_mode,mode)
        with self.assertRaises(ValidationError):case_request(engine_name='simulation_engine')

    def test_goals_guardrails_and_preferences_keep_t1_authority(self):
        for goal in ['MINIMIZE_COST','MAXIMIZE_SERVICE','MAXIMIZE_OWN_CAPACITY','MINIMIZE_TRIPS','BALANCED']:
            self.assertEqual(case_request(case_policy={'primary_goal':goal}).case_policy.primary_goal,goal)
        custom={'primary_goal':'CUSTOM','guardrails':[{'kind':'MINIMUM_DEMAND_COVERAGE','limit':'.9','hard':True}],
            'preferences':[{'kind':'COST','weight':'.5'},{'kind':'SERVICE','weight':'.5'}]}
        self.assertEqual(len(case_request(case_policy=custom).case_policy.preferences),2)
        with self.assertRaises(ValidationError):case_request(case_policy={'primary_goal':'CUSTOM'})

    def test_model_binding_is_not_an_editable_case_field(self):
        with self.assertRaises(ValidationError):UltimateCaseUpdate(expected_updated_at='2026-10-26T12:00:00Z',logistics_model_version_id=uuid4())

    def test_context_update_requires_changes_and_preserves_owner_cas(self):
        with self.assertRaises(ValidationError):UltimateCaseUpdate(expected_updated_at='2026-10-26T12:00:00Z')
        with self.assertRaises(ValidationError):UltimateCaseUpdate(expected_updated_at='2026-10-26T12:00:00Z',planning_start=None)
        change=UltimateCaseUpdate(expected_updated_at='2026-10-26T12:00:00Z',owner_updates=[{'node_id':'logistics_assignment','owner_user_id':uuid4(),'expected_updated_at':None}])
        self.assertIsNone(change.owner_updates[0].expected_updated_at)

    def test_initial_pack_identity_and_hash_are_reproducible_without_placeholders(self):
        cid=uuid4();a=service.empty_pack_snapshot(str(uuid4()),cid);self.assertEqual(a['pack_id'],service.empty_pack_snapshot('workspace',cid)['pack_id'])
        self.assertNotEqual(a['pack_id'],a['pack_version_id']);self.assertTrue(UUID(a['pack_id']))
        self.assertNotIn('dataset_id',a);self.assertNotEqual(a['manifest_hash'],service.empty_pack_snapshot('workspace',uuid4())['manifest_hash'])

    def test_pre_admission_context_is_typed_serializable_and_does_not_fake_a_read_set(self):
        result=service.enrich_context(raw_context());context=PlanningContextV1.model_validate(result['planning_context'])
        self.assertFalse(context.admission_available);self.assertNotIn('read_set',result['planning_context'])
        self.assertEqual(PlanningContextV1.model_validate_json(context.model_dump_json()),context)

    def test_metadata_owner_and_freeze_clock_do_not_change_mathematical_context(self):
        value=raw_context();before=service.enrich_context(value)['planning_context_hash'];changed=copy.deepcopy(value)
        changed['case'].update(label='Otro nombre',description='Metadata editable',context_frozen_at='2026-10-26T12:00:00Z');changed['responsibilities']={'owner':'another'}
        self.assertEqual(before,service.enrich_context(changed)['planning_context_hash'])
        changed['case']['planning_end']='2026-11-09';self.assertNotEqual(before,service.enrich_context(changed)['planning_context_hash'])


class UltimateCaseModelServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_derives_tenant_and_actor_instead_of_accepting_client_authority(self):
        ctx=type('Context',(),dict(workspace_id=str(uuid4()),user_id=str(uuid4())))()
        payload=ModelCreate(id=uuid4(),name='Operación',configuration=config())
        with patch.object(service,'platform_call',AsyncMock(return_value={})) as call:
            await service.create_model(ctx,payload)
        body=call.await_args.args[1];self.assertEqual(body['target_workspace_id'],ctx.workspace_id);self.assertEqual(body['actor_user_id'],ctx.user_id)
        self.assertEqual(body['operation'],'model_create');self.assertEqual(len(body['arguments']['configuration_hash']),64)

    async def test_publish_replay_uses_persisted_identity_before_mutable_draft(self):
        vid=uuid4();ctx=object();payload=ModelPublish(version_id=vid,expected_revision=1)
        with patch.object(service,'get_model',AsyncMock(return_value={'model':{'draft_config_jsonb':None},'versions':[{'id':str(vid)}]})),patch.object(service,'call',AsyncMock(return_value={'replayed':True})) as call:
            await service.publish_model(ctx,uuid4(),payload)
        self.assertNotIn('configuration_hash',call.await_args.args[2])


if __name__=='__main__':unittest.main()
