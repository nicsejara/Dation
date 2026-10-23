from unittest.mock import AsyncMock
from platform_fixtures import CONTEXT
from pathlib import Path
import unittest
from unittest.mock import patch

import httpx

from main import app
from app import auth


class RuntimeCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://qa")
        patch.object(auth,"verify",AsyncMock(return_value={"sub":CONTEXT.user_id})).start()
        patch.object(auth,"resolve",AsyncMock(return_value=CONTEXT)).start()
        self.headers = {"Authorization":"Bearer fixture-signed-token"}

    async def asyncTearDown(self):
        patch.stopall()
        await self.client.aclose()

    async def test_protected_html_and_multipart_auth(self):
        self.assertEqual((await self.client.get("/app")).status_code,303)
        for path in ["/api/dispatch/status"]:
            response=await self.client.get(path)
            self.assertEqual(response.status_code,401)
            self.assertEqual(response.headers["cache-control"],"no-store")
        response = await self.client.post("/api/datasets/validate?dataset_type=orders",
            files={"file":("orders.csv",b"wrong", "text/csv")})
        self.assertEqual(response.status_code,401)

    async def test_orders_and_fleet_csv_bom(self):
        samples = Path(__file__).resolve().parents[2] / "sample_data/v3"
        for kind, count in [("orders",30),("fleet",8)]:
            data = b"\xef\xbb\xbf"+(samples/(kind+".csv")).read_bytes()
            response = await self.client.post("/api/datasets/validate?dataset_type="+kind,
                headers=self.headers, files={"file":(kind+".csv",data,"text/csv")})
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.json()["valid"])
            self.assertEqual(response.json()["rows"],count)

    async def test_invalid_dataset_type_remains_422(self):
        response = await self.client.post("/api/datasets/validate?dataset_type=other",headers=self.headers,
            files={"file":("bad.csv",b"x,y\n1,2","text/csv")})
        self.assertEqual(response.status_code,422)

    async def test_static_byte_ranges_and_unsatisfiable_range(self):
        path = "/static/js/dispatch/workspace.mjs"
        response = await self.client.get(path,headers={"Range":"bytes=0-15"})
        self.assertEqual(response.status_code,206)
        self.assertEqual(len(response.content),16)
        self.assertEqual((await self.client.get(path,headers={"Range":"bytes=9999999-"})).status_code,416)

    async def test_module_assets_revalidate_without_losing_etags(self):
        path = "/static/js/dispatch/navigation/resource.mjs"
        response = await self.client.get(path)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers["cache-control"],"no-cache")
        cached = await self.client.get(path,headers={"If-None-Match":response.headers["etag"]})
        self.assertEqual(cached.status_code,304)


if __name__ == "__main__":
    unittest.main()
