"""Actual runtime/SQL/cohort dependencies stay fail-closed for J1.02 writers."""
import os
import unittest
from unittest.mock import AsyncMock,patch
from fastapi import HTTPException
from app.services import logistics_model_service as models,decision_case_v2_service as definitions


class DecisionCaseV2GateTests(unittest.IsolatedAsyncioTestCase):
    async def capability(self,env,**changes):
        caps=dict(enabled=True,saga10_schema_enabled=True,saga10_ui_enabled=True,decision_case_v2_write_enabled=True,can_create_case=False)
        with patch.dict(os.environ,env,clear=True),patch.object(models,'call',AsyncMock(return_value={**caps,**changes})),patch('app.services.decision_journey_service.capabilities',AsyncMock(return_value=True)):
            return await models.capabilities(object())
    async def test_default_off_requires_exact_runtime_opt_in_and_all_existing_gates(self):
        self.assertFalse((await self.capability({}))['decision_case_v2_enabled'])
        env={'DATION_J101_LIBRARY_ENABLED':'true','DATION_J102_ENABLED':'true'}
        self.assertTrue((await self.capability(env))['decision_case_v2_enabled'])
        for gate in ['enabled','saga10_schema_enabled','saga10_ui_enabled','decision_case_v2_write_enabled']:
            self.assertFalse((await self.capability(env,**{gate:False}))['decision_case_v2_enabled'])
        self.assertFalse((await self.capability({**env,'DATION_J102_ENABLED':'1'}))['decision_case_v2_enabled'])
        self.assertFalse((await self.capability({'DATION_J102_ENABLED':'true'}))['decision_case_v2_enabled'])
    async def test_require_writes_does_not_call_new_rpc_when_disabled(self):
        with patch.object(models,'capabilities',AsyncMock(return_value={'decision_case_v2_enabled':False})),patch.object(definitions,'platform_call',AsyncMock()) as rpc:
            with self.assertRaises(HTTPException) as caught:await definitions.require_writes(object())
            self.assertEqual(caught.exception.status_code,409);rpc.assert_not_awaited()

    async def test_listing_adds_one_scoped_batch_not_one_rpc_per_case(self):
        rows=[{'id':str(__import__('uuid').uuid4()),'label':'Synthetic '+str(i)} for i in range(25)]
        projection={row['id']:{'model_name':'Pinned model'} for row in rows}
        with patch.object(definitions,'call',AsyncMock(return_value=projection)) as rpc:
            result=await definitions.enrich_listing(object(),rows)
            rpc.assert_awaited_once()
            self.assertEqual(rpc.await_args.args[1],'projection')
            self.assertEqual(len(rpc.await_args.kwargs['case_ids']),25)
        self.assertEqual([r['case_definition_context'] for r in result],list(projection.values()))
        with patch.object(definitions,'call',AsyncMock()) as rpc:
            self.assertEqual(await definitions.enrich_listing(object(),[]),[]);rpc.assert_not_awaited()
