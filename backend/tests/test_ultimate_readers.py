"""Shared readers keep the empty Ultimate cohort visible without legacy writes."""
import copy
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException

from app.domain.decision_cases import (create_case_state, project_case_history,
    case_projection_options, case_workflow_version, NODE_IDS)
from app.platform.home import recent_case
from app.platform.decision_center import project
from app.services import decision_case_service as service


def fixture():
    row=dict(id='00000000-0000-4000-8000-000000000123',schema_version='decision_case_v2',
        workflow_version=2,orders_dataset_id=None,fleet_dataset_id=None,state_json={},
        created_at='2026-10-26T12:00:00Z',updated_at='2026-10-26T12:00:00Z',
        last_activity_at='2026-10-26T12:00:00Z',status='active',label='Semana 45')
    summaries={node:dict(run_count=0,latest=None,approved=None) for node in NODE_IDS}
    return dict(case=row,case_row=row,state_json={},summaries=summaries,status='active',
                in_review=False,orders=None,fleet=None)


class UltimateReaderTests(unittest.TestCase):
    def test_empty_case_has_null_references_and_requires_data(self):
        row=fixture()['case']
        result=project_case_history({},[],**case_projection_options(row))
        self.assertIsNone(result['signature'])
        self.assertEqual(result['inputs'],dict(orders_dataset_id=None,fleet_dataset_id=None))
        self.assertEqual(result['nodes']['logistics_assignment']['status'],'needs_data')
        self.assertTrue(all(node['run_count']==0 for node in result['nodes'].values()))

    def test_legacy_case_projection_does_not_gain_ultimate_fields(self):
        state=create_case_state('case','orders','fleet')
        self.assertEqual(state['signature'],'orders:fleet')
        self.assertEqual(state['nodes']['logistics_assignment']['status'],'available')
        self.assertNotIn('workflow_version',state)
        self.assertEqual(case_workflow_version({}),1)

    def test_unknown_or_bool_cohort_is_not_legacy(self):
        for value in (0,3,True,'2',None):
            with self.subTest(value=value),self.assertRaises(ValueError):
                case_workflow_version(dict(workflow_version=value))

    def test_cached_legacy_approval_cannot_open_empty_ultimate_config(self):
        b=fixture();b['case']['state_json']={'nodes':{'logistics_assignment':{'status':'approved'}}}
        home=recent_case(b)
        self.assertEqual(home['status'],'needs_data')
        self.assertIsNone(home['resume'])
        self.assertIsNone(home['run_id'])

    def test_home_and_center_keep_empty_case_without_fake_results(self):
        b=fixture();before=copy.deepcopy(b)
        home=recent_case(b);center=project(b,True)
        self.assertEqual(home['case_id'],center['id'])
        self.assertEqual(center['progress'],dict(approved=0,total=2))
        self.assertIsNone(center['orders']);self.assertIsNone(center['fleet'])
        self.assertTrue(all(node['target'] is None for node in center['nodes']))
        self.assertEqual(b,before)

    def test_cohort_mismatch_and_fake_pair_are_rejected(self):
        with self.assertRaises(ValueError):
            project_case_history({'workflow_version':1},[],**case_projection_options(fixture()['case']))
        with self.assertRaises(ValueError):
            create_case_state('case','orders','fleet',workflow_version=2)


class UltimateServiceReaderTests(unittest.IsolatedAsyncioTestCase):
    async def test_detail_does_not_fetch_null_dataset_ids(self):
        b=fixture()
        with patch.object(service,'get_case_row',AsyncMock(return_value=b['case'])), \
             patch.object(service,'history_snapshot',AsyncMock(return_value={'summaries':b['summaries']})), \
             patch.object(service,'get_dataset',AsyncMock()) as datasets:
            result=await service.get_case(b['case']['id'])
        datasets.assert_not_awaited()
        self.assertIsNone(result['orders']);self.assertIsNone(result['fleet'])

    async def test_list_keeps_empty_case_and_does_not_repair_rows(self):
        b=fixture()
        with patch.object(service,'_db',AsyncMock(return_value=[b])) as db:
            result=await service.list_cases()
        self.assertEqual(result[0]['case']['id'],b['case']['id'])
        self.assertEqual(result[0]['decision_case']['workflow_version'],2)
        self.assertEqual(db.await_args.args,('POST','rpc/list_decision_cases'))

    async def test_legacy_missing_pair_is_still_an_error(self):
        b=fixture();b['case']['workflow_version']=1
        with patch.object(service,'_db',AsyncMock(return_value=[b])):
            with self.assertRaises(LookupError):await service.list_cases()

    async def test_legacy_state_write_cannot_overwrite_ultimate_context(self):
        b=fixture()
        with patch.object(service,'get_case_row',AsyncMock(return_value=b['case'])), \
             patch.object(service,'_db',AsyncMock()) as db:
            with self.assertRaises(ValueError):await service.update_case(b['case']['id'],state={})
            with self.assertRaises(ValueError):await service.ensure_case(b['case']['id'],'orders','fleet')
            with self.assertRaises(ValueError):await service.sync_case_history(b['case']['id'])
        db.assert_not_awaited()

    async def test_archiving_retains_ultimate_schema_identity(self):
        b=fixture()
        with patch.object(service,'get_case_row',AsyncMock(return_value=b['case'])), \
             patch.object(service,'_db',AsyncMock(return_value=[b['case']])) as db:
            await service.update_case(b['case']['id'],status='archived')
        body=db.await_args.kwargs['body']
        self.assertEqual(body['schema_version'],b['case']['schema_version'])
        self.assertNotIn('state_json',body)

    async def test_progressive_relations_are_read_only_and_tenant_scoped(self):
        from app.platform.repository import TenantClient
        from app.platform import repository
        ctx=type('ReaderContext',(),dict(workspace_id='workspace',user_id='user',worker=False,access_role='admin'))()
        raw=AsyncMock();raw.request.return_value=httpx.Response(200,json=[])
        with patch.object(repository,'current',return_value=ctx),patch.object(repository,'is_infrastructure',return_value=False):
            client=TenantClient(raw)
            await client.get(repository.SUPABASE_URL+'/rest/v1/case_data_packs')
            self.assertEqual(raw.request.await_args.kwargs['params']['workspace_id'],'eq.workspace')
            with self.assertRaises(HTTPException):await client.post(repository.SUPABASE_URL+'/rest/v1/case_data_packs',json={})
            with self.assertRaises(HTTPException):await client.post(repository.SUPABASE_URL+'/rest/v1/decision_cases',json={'workflow_version':2})


if __name__=='__main__':unittest.main()
