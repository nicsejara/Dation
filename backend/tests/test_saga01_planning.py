import unittest
from unittest.mock import AsyncMock,patch
from uuid import uuid4
from fastapi import HTTPException
from pydantic import ValidationError
from app.models.ultimate_foundation import ModelContractPreview
from app.services import logistics_model_service as service
from app.domain.logistics.data_contracts import compile_contract,template_csv
from test_ultimate_case_models import config


class PlanningContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_model_preview_uses_ingestion_compiler_without_published_identity(self):
        payload=ModelContractPreview(configuration=config())
        with patch.object(service,'capabilities',AsyncMock(return_value={'enabled':True,'can_create_case':True})),patch.object(service,'call',AsyncMock()) as writes:
            provisional,contracts=await service.preview_contracts(object(),payload)
        self.assertTrue(provisional);writes.assert_not_awaited()
        for entity,contract in contracts.items():
            version={'id':contract.model_version_id,'config_jsonb':payload.configuration.model_dump(mode='json'),'config_hash':contract.configuration_hash}
            self.assertEqual(contract,compile_contract(version,entity))
            self.assertEqual(template_csv(contract).decode().splitlines()[0],','.join(f.public_header for f in contract.fields))

    async def test_existing_model_uses_exact_published_version_and_never_updates_draft(self):
        mid,vid=uuid4(),uuid4();configuration,hash_=service.configuration_snapshot(config())
        version={'id':str(vid),'config_jsonb':configuration,'config_hash':hash_}
        ctx=object()
        with patch.object(service,'capabilities',AsyncMock(return_value={'enabled':True,'can_create_case':True})),patch.object(service,'get_model',AsyncMock(return_value={'model':{'status':'active'},'versions':[version]})) as get:
            provisional,contracts=await service.preview_contracts(ctx,ModelContractPreview(model_id=mid,version_id=vid))
        get.assert_awaited_once_with(ctx,mid);self.assertFalse(provisional)
        self.assertEqual(contracts['transport_demand'].model_version_id,vid)

    async def test_absent_or_foreign_version_does_not_fall_back_to_draft(self):
        with patch.object(service,'capabilities',AsyncMock(return_value={'enabled':True,'can_create_case':True})),patch.object(service,'get_model',AsyncMock(return_value={'model':{'status':'active'},'versions':[]})):
            with self.assertRaises(HTTPException) as error:await service.preview_contracts(object(),ModelContractPreview(model_id=uuid4(),version_id=uuid4()))
        self.assertEqual(error.exception.status_code,404)

    async def test_disabled_creation_cannot_preview_a_model(self):
        with patch.object(service,'capabilities',AsyncMock(return_value={'enabled':False,'can_create_case':False})),patch.object(service,'get_model',AsyncMock()) as get:
            with self.assertRaises(HTTPException) as error:await service.preview_contracts(object(),ModelContractPreview(configuration=config()))
        self.assertEqual(error.exception.status_code,403);get.assert_not_awaited()

    def test_preview_has_one_typed_source(self):
        for body in [{},{'model_id':uuid4()},{'configuration':config(),'model_id':uuid4(),'version_id':uuid4()}]:
            with self.assertRaises(ValidationError):ModelContractPreview(**body)
