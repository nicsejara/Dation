import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from app.auth import require_upload_access
from app.services import dispatch_service
from app.engines.dispatch.normalization import preflight
from app.validators.fleet_schema import (
    validate_fleet_csv,
    validate_fleet_report,
)
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

    def test_sample_profiles_match_ux_acceptance(self):
        orders = validate_orders_report(
            (ROOT / "sample_data" / "v1" / "orders.csv").read_bytes()
        )
        fleet = validate_fleet_report(
            (ROOT / "sample_data" / "v1" / "fleet.csv").read_bytes()
        )

        profile = orders["profile"]
        self.assertEqual(orders["rows"], 100)
        self.assertEqual(profile["total_units"], 2682)
        self.assertEqual(profile["total_weight_kg"], 2384000)
        self.assertEqual(profile["routes"], 28)
        self.assertEqual(profile["origins"], 3)
        self.assertEqual(profile["destinations"], 10)
        self.assertEqual(profile["date_from"], "2026-10-01")
        self.assertEqual(profile["date_to"], "2026-10-10")
        self.assertEqual(profile["max_order_kg"], 61600)
        self.assertEqual(
            profile["priority_mix"],
            {"High": 27, "Normal": 62, "Low": 11},
        )
        self.assertEqual(
            orders["suggested_label"],
            "Órdenes 1–10 oct 2026",
        )
        self.assertEqual(len(orders["preview"]["rows"]), 5)
        self.assertEqual(orders["detected"]["delimiter"], ";")
        self.assertEqual(orders["detected"]["encoding"], "UTF-8")
        self.assertEqual(orders["detected"]["columns"], 11)

        fleet_profile = fleet["profile"]
        self.assertEqual(fleet_profile["types"], 4)
        self.assertEqual(fleet_profile["own_units_per_day"], 11)
        self.assertEqual(
            fleet_profile["own_capacity_kg_per_day"],
            167000,
        )
        self.assertTrue(fleet_profile["has_third_party"])
        self.assertEqual(fleet_profile["pools"], 4)
        self.assertFalse(fleet_profile["spatially_scoped"])
        self.assertEqual(fleet_profile["global_scope_pools"], 4)

    def test_sample_preflight_is_grouped_for_business(self):
        orders = validate_orders_csv(
            (ROOT / "sample_data" / "v1" / "orders.csv").read_bytes()
        )
        fleet = validate_fleet_csv(
            (ROOT / "sample_data" / "v1" / "fleet.csv").read_bytes()
        )
        result = preflight(
            orders["records"],
            fleet["records"],
            fleet["records"],
        )

        late = next(
            item
            for item in result["findings"]
            if item["id"] == "late_orders"
        )
        self.assertEqual(late["count"], 7)
        self.assertEqual(
            [item["order_id"] for item in late["items"]],
            [
                "SHP-0014",
                "SHP-0024",
                "SHP-0052",
                "SHP-0055",
                "SHP-0077",
                "SHP-0082",
                "SHP-0094",
            ],
        )

        capacity = result["capacity_check"]
        self.assertEqual(capacity["own_capacity_kg_per_day"], 167000)
        self.assertEqual(capacity["days_over"], 9)
        self.assertEqual(capacity["total_days"], 10)
        peak = max(capacity["days"], key=lambda item: item["kg"])
        self.assertEqual(peak["date"], "2026-10-09")
        self.assertEqual(peak["kg"], 351800)
        self.assertAlmostEqual(peak["ratio"], 2.1065868, places=5)
        zero_slack = next(
            item
            for item in result["findings"]
            if item["id"] == "zero_slack"
        )
        self.assertEqual(zero_slack["count"], 26)
        self.assertTrue(result["readiness"]["can_continue"])

    def test_v2_sample_is_spatially_scoped(self):
        orders = validate_orders_report(
            (ROOT / "sample_data" / "v2" / "orders.csv").read_bytes()
        )
        fleet = validate_fleet_report(
            (ROOT / "sample_data" / "v2" / "fleet.csv").read_bytes()
        )
        self.assertTrue(orders["valid"])
        self.assertEqual(orders["schema"], "orders_v2")
        self.assertTrue(fleet["valid"])
        self.assertEqual(fleet["schema"], "fleet_v2")
        self.assertTrue(fleet["profile"]["spatially_scoped"])
        self.assertEqual(
            fleet["profile"]["bases"],
            ["Buenos Aires", "Cordoba", "Rosario"],
        )
        self.assertEqual(fleet["profile"]["own_units_per_day"], 11)
        self.assertEqual(
            fleet["profile"]["own_capacity_kg_per_day"],
            167000,
        )
        self.assertEqual(fleet["profile"]["global_scope_pools"], 1)

    def test_report_caps_visible_problems_at_one_hundred(self):
        header = (
            "order_id;product;quantity_units;unit_weight_kg;origin;"
            "destination;distance_km;priority;max_delivery_days;"
            "dispatch_date\n"
        )
        rows = "".join(
            (
                f"X-{index};P;0;NaN;A;A;-1;Urgent;95;"
                "31/02/2026\n"
            )
            for index in range(40)
        )
        report = validate_orders_report(
            (header + rows).encode("utf-8")
        )
        self.assertFalse(report["valid"])
        self.assertTrue(report["truncated"])
        self.assertLessEqual(
            len(report["errors"]) + len(report["warnings"]),
            100,
        )

    def test_templates_and_sample_data_validate(self):
        from app.validators.contracts import template_csv

        for kind, validator in (
            ("orders", validate_orders_report),
            ("fleet", validate_fleet_report),
        ):
            template_text = template_csv(kind)
            template_report = validator(template_text.encode())
            self.assertTrue(template_report["valid"])
            self.assertEqual(template_report["rows"], 5)
            header = template_text.splitlines()[0]
            if kind == "orders":
                self.assertIn("ready_date", header)
                self.assertNotIn("current_vehicle_type", header)
                self.assertNotIn("dispatch_date", header)
            else:
                self.assertIn("fleet_pool_id", header)
                self.assertIn("base_location", header)
                self.assertEqual(template_report["schema"], "fleet_v2")
            sample = (ROOT / "sample_data" / "v1" / f"{kind}.csv").read_bytes()
            sample_report = validator(sample)
            self.assertTrue(sample_report["valid"])
            if kind == "fleet":
                self.assertEqual(sample_report["schema"], "fleet_v1")
                self.assertFalse(sample_report["profile"]["spatially_scoped"])
                self.assertTrue(any(
                    issue["code"] == "LEGACY_FLEET_GLOBAL_SCOPE"
                    for issue in sample_report["warnings"]
                ))


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
            "orders_v2",
        )
        self.assertEqual(
            response.json()["formats"]["fleet"]["schema"],
            "fleet_v2",
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
