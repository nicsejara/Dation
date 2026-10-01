import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from app.auth import require_upload_access
from app.services import dispatch_service
from app.validators.fleet_schema import validate_fleet_report
from app.validators.orders_schema import (
    validate_orders_csv,
    validate_orders_report,
)
from main import app


ROOT = Path(__file__).resolve().parents[2]


class DispatchIngestionValidationTests(unittest.TestCase):
    def test_report_accumulates_multiple_errors(self):
        data = (
            b"order_id;product;quantity_units;unit_weight_kg;origin;"
            b"destination;distance_km;priority;max_delivery_days;dispatch_date\n"
            b"A;P;1.5;NaN;X;X;100;Urgent;95;31/02/2026\n"
            b"A;P;0;100;X;Y;-2;Normal;2;2026-10-01\n"
        )
        report = validate_orders_report(data)
        self.assertFalse(report["valid"])
        self.assertGreaterEqual(report["counts"]["errors"], 7)
        self.assertTrue(
            all("code" in issue and "message" in issue for issue in report["errors"])
        )
        self.assertTrue(any(issue["row"] == 2 for issue in report["errors"]))

    def test_strict_wrapper_still_raises_first_error(self):
        data = (
            b"order_id;product;quantity_units;unit_weight_kg;origin;"
            b"destination;distance_km;priority;max_delivery_days;dispatch_date\n"
            b"A;P;1.5;400;X;Y;100;Normal;2;2026-10-01\n"
        )
        with self.assertRaises(ValueError):
            validate_orders_csv(data)

    def test_detects_legacy_mixed_format(self):
        legacy = (ROOT / "sample_data" / "InputData-LogisticsDDA.csv").read_bytes()
        report = validate_orders_report(legacy)
        self.assertEqual(report["detected_format"], "legacy_mixed")
        self.assertTrue(any(issue["code"] == "LEGACY_MIXED" for issue in report["errors"]))

    def test_templates_and_sample_data_validate(self):
        from app.validators.contracts import template_csv

        for kind, validator in (
            ("orders", validate_orders_report),
            ("fleet", validate_fleet_report),
        ):
            self.assertTrue(validator(template_csv(kind).encode())["valid"])
            sample = (ROOT / "sample_data" / "v1" / f"{kind}.csv").read_bytes()
            self.assertTrue(validator(sample)["valid"])


class DispatchIngestionHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )
        app.dependency_overrides[require_upload_access] = lambda: "dation"

    async def asyncTearDown(self):
        app.dependency_overrides.clear()
        await self.client.aclose()

    async def test_validate_does_not_require_supabase(self):
        contents = (ROOT / "sample_data" / "v1" / "orders.csv").read_bytes()
        response = await self.client.post(
            "/api/datasets/validate?dataset_type=orders",
            files={"file": ("orders.csv", contents, "text/csv")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertIn("sha256", response.json()["file"])

    async def test_contract_endpoint(self):
        response = await self.client.get("/api/dispatch/contracts")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["formats"]["orders"]["schema"],
            "orders_v1",
        )

    async def test_status_uses_detailed_service(self):
        expected = {
            "available": False,
            "engine_version": "1.0.0",
            "checks": [],
            "message": "Activación pendiente",
        }
        with patch.object(
            dispatch_service,
            "system_status",
            AsyncMock(return_value=expected),
        ):
            response = await self.client.get("/api/dispatch/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    async def test_archive_current_fleet_is_rejected(self):
        with patch(
            "app.services.dispatch_service.get_dataset",
            AsyncMock(
                return_value={
                    "id": "x",
                    "dataset_type": "fleet",
                    "is_default": True,
                }
            ),
        ):
            response = await self.client.post(
                "/api/datasets/00000000-0000-4000-8000-000000000002/archive"
            )
        self.assertEqual(response.status_code, 422)
