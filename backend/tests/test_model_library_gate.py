"""J1.01 capability is default closed and cannot grant model mutation rights."""
import os
import unittest
from unittest.mock import AsyncMock,patch
from app.services import logistics_model_service as service

class ModelLibraryGateTests(unittest.IsolatedAsyncioTestCase):
    async def caps(self,env,**overrides):
        base=dict(enabled=True,saga10_schema_enabled=True,saga10_ui_enabled=True,can_manage_models=False)
        with patch.dict(os.environ,env,clear=True),patch.object(service,'call',AsyncMock(return_value={**base,**overrides})),patch('app.services.decision_journey_service.capabilities',AsyncMock(return_value=True)):
            return await service.capabilities(object())

    async def test_default_closed_and_explicit_opt_in_preserves_read_only_actor(self):
        self.assertFalse((await self.caps({}))['models_library_enabled'])
        caps=await self.caps({'DATION_J101_LIBRARY_ENABLED':'true'})
        self.assertTrue(caps['models_library_enabled']);self.assertFalse(caps['can_manage_models'])

    async def test_existing_gates_cannot_be_bypassed(self):
        for gate in ['enabled','saga10_schema_enabled','saga10_ui_enabled']:
            self.assertFalse((await self.caps({'DATION_J101_LIBRARY_ENABLED':'true'},**{gate:False}))['models_library_enabled'])
        self.assertFalse((await self.caps({'DATION_J101_LIBRARY_ENABLED':'1'}))['models_library_enabled'])
