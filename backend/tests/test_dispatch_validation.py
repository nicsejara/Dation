import csv
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

from app.models.dispatch_config import DispatchConfig
from app.validators.fleet_schema import (
    validate_fleet_csv,
    validate_fleet_report,
)
from app.validators.orders_schema import (
    validate_orders_csv,
    validate_orders_report,
)

ROOT = Path(__file__).resolve().parents[2]


def csv_bytes(columns, rows):
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=columns,
        delimiter=";",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


MINIMAL_ORDER_COLUMNS = [
    "order_id",
    "product",
    "quantity_units",
    "unit_weight_kg",
    "origin",
    "destination",
    "distance_km",
]

MINIMAL_FLEET_COLUMNS = [
    "vehicle_id",
    "vehicle_type",
    "ownership",
    "base_site",
    "capacity_kg",
]


class DispatchValidationTests(unittest.TestCase):
    def test_minimal_v3_data_pack_is_valid(self):
        orders = validate_orders_report(
            csv_bytes(
                MINIMAL_ORDER_COLUMNS,
                [
                    {
                        "order_id": "SHP-001",
                        "product": "Producto A",
                        "quantity_units": 10,
                        "unit_weight_kg": 800,
                        "origin": "Cordoba",
                        "destination": "Mendoza",
                        "distance_km": 650,
                    }
                ],
            )
        )
        fleet = validate_fleet_report(
            csv_bytes(
                MINIMAL_FLEET_COLUMNS,
                [
                    {
                        "vehicle_id": "VEH-001",
                        "vehicle_type": "Truck_L",
                        "ownership": "own",
                        "base_site": "Cordoba",
                        "capacity_kg": 25000,
                    }
                ],
            )
        )

        self.assertTrue(orders["valid"])
        self.assertEqual(orders["schema"], "orders_v3")
        self.assertEqual(orders["detected_format"], "orders_v3")
        self.assertFalse(
            orders["completeness"]["estimated_dispatch_date"]["complete"]
        )

        self.assertTrue(fleet["valid"])
        self.assertEqual(fleet["schema"], "fleet_v3")
        self.assertEqual(fleet["detected_format"], "fleet_v3")
        self.assertFalse(
            fleet["completeness"]["license_plate"]["complete"]
        )
        self.assertFalse(
            fleet["completeness"]["cost_per_km"]["complete"]
        )

    def test_fleet_v3_uses_real_vehicle_identity(self):
        columns = [
            "vehicle_id",
            "license_plate",
            "vehicle_type",
            "ownership",
            "base_site",
            "capacity_kg",
        ]
        rows = [
            {
                "vehicle_id": "VEH-001",
                "license_plate": "AE123XX",
                "vehicle_type": "Truck_L",
                "ownership": "own",
                "base_site": "Cordoba",
                "capacity_kg": 25000,
            },
            {
                "vehicle_id": "VEH-002",
                "license_plate": "AF456YY",
                "vehicle_type": "Truck_L",
                "ownership": "own",
                "base_site": "Cordoba",
                "capacity_kg": 25000,
            },
        ]
        report = validate_fleet_csv(csv_bytes(columns, rows))
        self.assertEqual(report["rows"], 2)
        self.assertEqual(
            {row["vehicle_id"] for row in report["records"]},
            {"VEH-001", "VEH-002"},
        )
        self.assertEqual(
            {row["vehicle_type"] for row in report["records"]},
            {"Truck_L"},
        )
        self.assertTrue(
            all(
                row["fleet_pool_id"] == row["vehicle_id"]
                for row in report["records"]
            )
        )

        with self.assertRaisesRegex(ValueError, "repetido"):
            validate_fleet_csv(
                csv_bytes(
                    columns,
                    [
                        rows[0],
                        {**rows[1], "vehicle_id": "VEH-001"},
                    ],
                )
            )

        with self.assertRaisesRegex(ValueError, "patente"):
            validate_fleet_csv(
                csv_bytes(
                    columns,
                    [
                        rows[0],
                        {**rows[1], "license_plate": "AE123XX"},
                    ],
                )
            )

    def test_own_vehicle_requires_concrete_site(self):
        with self.assertRaisesRegex(ValueError, "site concreto"):
            validate_fleet_csv(
                csv_bytes(
                    MINIMAL_FLEET_COLUMNS,
                    [
                        {
                            "vehicle_id": "VEH-001",
                            "vehicle_type": "Truck_L",
                            "ownership": "own",
                            "base_site": "*",
                            "capacity_kg": 25000,
                        }
                    ],
                )
            )

    def test_optional_values_are_validated_when_present(self):
        order_columns = MINIMAL_ORDER_COLUMNS + [
            "estimated_dispatch_date",
            "delivery_due_date",
        ]
        with self.assertRaisesRegex(ValueError, "anterior"):
            validate_orders_csv(
                csv_bytes(
                    order_columns,
                    [
                        {
                            "order_id": "A",
                            "product": "P",
                            "quantity_units": 1,
                            "unit_weight_kg": 400,
                            "origin": "Cordoba",
                            "destination": "Mendoza",
                            "distance_km": 650,
                            "estimated_dispatch_date": "2026-10-10",
                            "delivery_due_date": "2026-10-09",
                        }
                    ],
                )
            )

        fleet_columns = MINIMAL_FLEET_COLUMNS + ["status"]
        with self.assertRaisesRegex(ValueError, "estado válido"):
            validate_fleet_csv(
                csv_bytes(
                    fleet_columns,
                    [
                        {
                            "vehicle_id": "VEH-001",
                            "vehicle_type": "Truck_L",
                            "ownership": "own",
                            "base_site": "Cordoba",
                            "capacity_kg": 25000,
                            "status": "broken",
                        }
                    ],
                )
            )

    def test_legacy_orders_converter_remains_readable(self):
        spec = importlib.util.spec_from_file_location(
            "convert",
            ROOT / "scripts" / "convert_legacy_csv.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "orders.csv"
            self.assertEqual(
                module.convert(
                    ROOT / "sample_data" / "InputData-LogisticsDDA.csv",
                    target,
                ),
                100,
            )
            data = validate_orders_csv(target.read_bytes())
            self.assertEqual(data["profile"]["total_units"], 2682)
            self.assertEqual(
                data["profile"]["total_weight_kg"],
                2384000,
            )
            self.assertIn(
                "estimated_dispatch_date",
                data["records"][0],
            )
            self.assertNotIn(
                "current_vehicle_type",
                data["records"][0],
            )

    def test_legacy_fleet_v1_and_v2_are_adapted(self):
        v1 = validate_fleet_report(
            (ROOT / "sample_data" / "v1" / "fleet.csv").read_bytes()
        )
        v2 = validate_fleet_report(
            (ROOT / "sample_data" / "v2" / "fleet.csv").read_bytes()
        )

        self.assertTrue(v1["valid"])
        self.assertTrue(v2["valid"])
        self.assertTrue(
            any(
                issue["code"] == "LEGACY_FLEET_POOL_FORMAT"
                for issue in v1["warnings"]
            )
        )
        self.assertTrue(
            any(
                issue["code"] == "LEGACY_FLEET_POOL_FORMAT"
                for issue in v2["warnings"]
            )
        )
        self.assertGreater(v1["profile"]["vehicles"], 4)
        self.assertGreater(v2["profile"]["vehicles"], 10)

    def test_phase4_weights_require_four_business_dimensions(self):
        with self.assertRaises(ValueError):
            DispatchConfig(
                mode="custom",
                objective="custom",
                weights={"cost": .7, "trips": .3},
            )

        config = DispatchConfig(
            mode="custom",
            objective="custom",
            weights={
                "cost": .4,
                "time": .2,
                "utilization": .2,
                "co2": .2,
            },
        )
        self.assertAlmostEqual(config.weights.cost, .4)
        self.assertAlmostEqual(config.weights.time, .2)
        self.assertAlmostEqual(config.weights.utilization, .2)
        self.assertAlmostEqual(config.weights.co2, .2)

    def test_dimension_contract_and_dynamic_balanced_weights(self):
        config = DispatchConfig(
            objective="balanced",
            dimensions=["cost", "time"],
        )
        self.assertEqual(
            config.dimensions,
            ["cost", "time"],
        )
        self.assertAlmostEqual(config.weights.cost, .5)
        self.assertAlmostEqual(config.weights.time, .5)
        self.assertEqual(config.weights.utilization, 0)
        self.assertEqual(config.weights.co2, 0)

        with self.assertRaisesRegex(ValueError, "requiere activar"):
            DispatchConfig(
                objective="min_co2",
                dimensions=["cost", "time"],
            )

        with self.assertRaisesRegex(ValueError, "inactiva"):
            DispatchConfig(
                mode="custom",
                objective="custom",
                dimensions=["cost", "time"],
                weights={
                    "cost": .4,
                    "time": .4,
                    "utilization": .2,
                    "co2": 0,
                },
            )

    def test_inconsistent_route_distances(self):
        rows = [
            {
                "order_id": "A",
                "product": "P",
                "quantity_units": 1,
                "unit_weight_kg": 400,
                "origin": "Cordoba",
                "destination": "Mendoza",
                "distance_km": 650,
            },
            {
                "order_id": "B",
                "product": "P",
                "quantity_units": 1,
                "unit_weight_kg": 400,
                "origin": "Cordoba",
                "destination": "Mendoza",
                "distance_km": 700,
            },
        ]
        with self.assertRaisesRegex(ValueError, "distancia"):
            validate_orders_csv(
                csv_bytes(
                    MINIMAL_ORDER_COLUMNS,
                    rows,
                )
            )


if __name__ == "__main__":
    unittest.main()
