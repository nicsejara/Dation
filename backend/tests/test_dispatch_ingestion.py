import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from app.auth import require_upload_access
from app.services import dispatch_service
from app.services.decision_readiness import build_decision_readiness
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


class DataPackValidationTests(unittest.TestCase):
    def test_report_accumulates_multiple_errors(self):
        data = (
            b"order_id;product;quantity_units;unit_weight_kg;origin;"
            b"destination;distance_km;estimated_dispatch_date;priority;"
            b"delivery_due_date\n"
            b"A;P;1.5;NaN;X;X;-2;31/02/2026;Urgent;2026-01-01\n"
            b"A;P;0;100;X;Y;-2;2026-10-01;Normal;2026-10-03\n"
        )
        report = validate_orders_report(data)
        self.assertFalse(report["valid"])
        self.assertGreaterEqual(report["counts"]["errors"], 6)
        self.assertTrue(
            all(
                "code" in issue and "message" in issue
                for issue in report["errors"]
            )
        )

    def test_strict_wrapper_still_raises_first_error(self):
        data = (
            b"order_id;product;quantity_units;unit_weight_kg;origin;"
            b"destination;distance_km\n"
            b"A;P;1.5;400;Cordoba;Mendoza;650\n"
        )
        with self.assertRaises(ValueError):
            validate_orders_csv(data)

    def test_detects_legacy_mixed_format(self):
        legacy = (
            ROOT / "sample_data" / "InputData-LogisticsDDA.csv"
        ).read_bytes()
        report = validate_orders_report(legacy)
        self.assertEqual(
            report["detected_format"],
            "legacy_mixed",
        )
        self.assertTrue(
            any(
                issue["code"] == "LEGACY_MIXED"
                for issue in report["errors"]
            )
        )

    def test_v3_sample_profiles_and_readiness(self):
        orders = validate_orders_report(
            (ROOT / "sample_data" / "v3" / "orders.csv").read_bytes()
        )
        fleet = validate_fleet_report(
            (ROOT / "sample_data" / "v3" / "fleet.csv").read_bytes()
        )

        self.assertTrue(orders["valid"])
        self.assertEqual(orders["schema"], "orders_v3")
        self.assertEqual(orders["rows"], 30)
        self.assertEqual(orders["profile"]["origins"], 1)
        self.assertEqual(
            orders["profile"]["origin_sites"],
            ["Cordoba"],
        )
        self.assertEqual(
            orders["profile"]["estimated_dispatch_date_range"],
            {"from": "2026-10-01", "to": "2026-10-10"},
        )

        self.assertTrue(fleet["valid"])
        self.assertEqual(fleet["schema"], "fleet_v3")
        self.assertEqual(fleet["profile"]["vehicles"], 8)
        self.assertEqual(fleet["profile"]["own_vehicles"], 5)
        self.assertEqual(fleet["profile"]["third_party_vehicles"], 3)
        self.assertEqual(fleet["profile"]["sites"], ["Cordoba"])

        readiness = build_decision_readiness(
            validate_orders_csv(
                (ROOT / "sample_data" / "v3" / "orders.csv").read_bytes()
            ),
            validate_fleet_csv(
                (ROOT / "sample_data" / "v3" / "fleet.csv").read_bytes()
            ),
        )
        self.assertEqual(
            readiness["decisions"][0]["state"],
            "available",
        )
        self.assertTrue(
            readiness["decisions"][1]["data_ready"],
        )
        self.assertTrue(
            readiness["decisions"][2]["data_ready"],
        )
        self.assertEqual(
            readiness["summary"]["data_ready"],
            3,
        )

    def test_minimal_data_pack_unlocks_only_assignment_data(self):
        orders = validate_orders_csv(
            (
                "order_id;product;quantity_units;unit_weight_kg;origin;"
                "destination;distance_km\n"
                "A;Producto A;10;800;Cordoba;Mendoza;650\n"
            ).encode()
        )
        fleet = validate_fleet_csv(
            (
                "vehicle_id;vehicle_type;ownership;base_site;capacity_kg\n"
                "VEH-001;Truck_L;own;Cordoba;25000\n"
            ).encode()
        )

        readiness = build_decision_readiness(orders, fleet)
        assignment, scheduling, final = readiness["decisions"]

        self.assertEqual(assignment["state"], "available")
        self.assertTrue(assignment["data_ready"])
        self.assertFalse(scheduling["data_ready"])
        self.assertFalse(final["data_ready"])
        self.assertEqual(scheduling["state"], "locked")
        self.assertEqual(final["state"], "locked")
        self.assertIn(
            "estimated_dispatch_date",
            {
                item["column"]
                for item in scheduling["missing"]
            },
        )
        self.assertIn(
            "license_plate",
            {
                item["column"]
                for item in final["missing"]
            },
        )

        capabilities = {
            item["id"]: item
            for item in assignment["capabilities"]
        }
        self.assertTrue(capabilities["trips"]["available"])
        self.assertTrue(capabilities["own_fleet"]["available"])
        self.assertFalse(capabilities["cost"]["available"])
        self.assertFalse(capabilities["co2"]["available"])

    def test_readiness_blocks_assignment_when_site_has_no_fleet(self):
        orders = validate_orders_csv(
            (
                "order_id;product;quantity_units;unit_weight_kg;origin;"
                "destination;distance_km\n"
                "A;Producto A;10;800;Cordoba;Mendoza;650\n"
            ).encode()
        )
        fleet = validate_fleet_csv(
            (
                "vehicle_id;vehicle_type;ownership;base_site;capacity_kg\n"
                "VEH-001;Truck_L;own;Rosario;25000\n"
            ).encode()
        )
        compatibility = preflight(
            orders["records"],
            fleet["records"],
            fleet["records"],
        )
        readiness = build_decision_readiness(
            orders,
            fleet,
            compatibility,
        )

        assignment = readiness["decisions"][0]
        self.assertEqual(
            assignment["state"],
            "needs_data",
        )
        self.assertFalse(assignment["data_ready"])
        self.assertTrue(assignment["blockers"])
        self.assertEqual(
            assignment["blockers"][0]["code"],
            "NO_FLEET_AT_ORIGIN",
        )

    def test_templates_are_complete_but_only_core_is_required(self):
        from app.validators.contracts import (
            public_contracts,
            template_csv,
        )

        contracts = public_contracts()
        self.assertEqual(
            contracts["orders"]["schema"],
            "orders_v3",
        )
        self.assertEqual(
            contracts["fleet"]["schema"],
            "fleet_v3",
        )

        order_required = {
            column["name"]
            for column in contracts["orders"]["columns"]
            if column["required"]
        }
        self.assertEqual(
            order_required,
            {
                "order_id",
                "product",
                "quantity_units",
                "unit_weight_kg",
                "origin",
                "destination",
                "distance_km",
            },
        )

        fleet_required = {
            column["name"]
            for column in contracts["fleet"]["columns"]
            if column["required"]
        }
        self.assertEqual(
            fleet_required,
            {
                "vehicle_id",
                "vehicle_type",
                "ownership",
                "base_site",
                "capacity_kg",
            },
        )

        orders_template = template_csv("orders")
        fleet_template = template_csv("fleet")
        self.assertIn(
            "estimated_dispatch_date",
            orders_template.splitlines()[0],
        )
        self.assertIn(
            "license_plate",
            fleet_template.splitlines()[0],
        )
        self.assertNotIn(
            "fleet_pool_id",
            fleet_template.splitlines()[0],
        )
        self.assertTrue(
            validate_orders_report(
                orders_template.encode()
            )["valid"]
        )
        self.assertTrue(
            validate_fleet_report(
                fleet_template.encode()
            )["valid"]
        )

    def test_report_caps_visible_problems_at_one_hundred(self):
        header = (
            "order_id;product;quantity_units;unit_weight_kg;origin;"
            "destination;distance_km\n"
        )
        rows = "".join(
            f"X-{index};P;0;NaN;A;A;-1\n"
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


class DataPackHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )
        app.dependency_overrides[
            require_upload_access
        ] = lambda: "dation"

    async def asyncTearDown(self):
        app.dependency_overrides.clear()
        await self.client.aclose()

    async def test_validate_does_not_require_supabase(self):
        contents = (
            ROOT / "sample_data" / "v3" / "orders.csv"
        ).read_bytes()
        response = await self.client.post(
            "/api/datasets/validate?dataset_type=orders",
            files={
                "file": (
                    "orders.csv",
                    contents,
                    "text/csv",
                )
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertIn(
            "completeness",
            response.json(),
        )
        self.assertIn(
            "sha256",
            response.json()["file"],
        )

    async def test_contract_endpoint_exposes_progressive_v3(self):
        response = await self.client.get(
            "/api/dispatch/contracts"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(
            payload["formats"]["orders"]["schema"],
            "orders_v3",
        )
        self.assertEqual(
            payload["formats"]["fleet"]["schema"],
            "fleet_v3",
        )
        fleet_names = [
            column["name"]
            for column in payload[
                "formats"
            ]["fleet"]["columns"]
        ]
        self.assertIn("vehicle_id", fleet_names)
        self.assertNotIn("fleet_pool_id", fleet_names)

    async def test_status_uses_detailed_service(self):
        expected = {
            "available": False,
            "engine_version": "2.2.0",
            "checks": [],
            "message": "Activación pendiente",
        }
        with patch.object(
            dispatch_service,
            "system_status",
            AsyncMock(return_value=expected),
        ):
            response = await self.client.get(
                "/api/dispatch/status"
            )
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
                "/api/datasets/"
                "00000000-0000-4000-8000-000000000002/archive"
            )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
