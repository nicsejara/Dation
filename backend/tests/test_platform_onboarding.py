"""The controlled sample must fail before persistence if its bytes drift."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import AsyncMock,patch
from fastapi import HTTPException
from app.services import dispatch_service as service

class OnboardingPackTests(unittest.IsolatedAsyncioTestCase):
 async def test_corrupted_golden_pack_is_rejected_before_any_upload(self):
  source=Path(__file__).resolve().parents[2]/'sample_data/onboarding-v1'
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);pack=root/'sample_data/onboarding-v1';pack.mkdir(parents=True)
   for name in ['orders.csv','fleet.csv','manifest.json']:(pack/name).write_bytes((source/name).read_bytes())
   (pack/'orders.csv').write_bytes((pack/'orders.csv').read_bytes()+b'\nchanged')
   with patch.object(service,'Path') as paths,patch.object(service,'store_input',AsyncMock()) as store:
    paths.return_value.resolve.return_value.parents.__getitem__.return_value=root
    with self.assertRaises(HTTPException) as result:await service.load_sample_inputs()
    self.assertEqual(result.exception.status_code,503);store.assert_not_awaited()
