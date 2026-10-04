import unittest

from pydantic import ValidationError

from app.engines.assignment.scope import apply_order_scope, scope_preview
from app.models.assignment_config import AssignmentConfig, AssignmentOptions


ORDERS = [
    {
        "order_id": "A",
        "destination": "Cordoba",
        "origin": "Planta",
        "product": "A",
        "priority": "Normal",
        "quantity_units": 2,
        "unit_weight_kg": 100,
        "distance_km": 50,
        "estimated_dispatch_date": "2026-09-21",
        "delivery_due_date": "2026-09-24",
    },
    {
        "order_id": "B",
        "destination": "Mendoza",
        "origin": "Planta",
        "product": "B",
        "priority": "High",
        "quantity_units": 8,
        "unit_weight_kg": 200,
        "distance_km": 650,
        "estimated_dispatch_date": "2026-10-01",
        "delivery_due_date": "2026-10-04",
    },
    {
        "order_id": "C",
        "destination": "Cordoba",
        "origin": "Deposito",
        "product": "C",
        "priority": "Low",
        "quantity_units": 4,
        "unit_weight_kg": 150,
        "distance_km": 80,
        "estimated_dispatch_date": "2026-10-04",
        "delivery_due_date": "2026-10-07",
    },
]


class AssignmentScopeTests(unittest.TestCase):
    def test_category_filter(self):
        result = apply_order_scope(
            ORDERS,
            [
                {
                    "column": "destination",
                    "type": "category",
                    "operator": "in",
                    "value": ["Cordoba"],
                    "resolved": None,
                }
            ],
        )
        self.assertEqual([row["order_id"] for row in result], ["A", "C"])

    def test_date_filter_uses_resolved_absolute_range(self):
        result = apply_order_scope(
            ORDERS,
            [
                {
                    "column": "estimated_dispatch_date",
                    "type": "date",
                    "operator": "between",
                    "value": ["last14"],
                    "resolved": ["2026-09-21", "2026-10-04"],
                }
            ],
        )
        self.assertEqual(len(result), 3)

    def test_numeric_filter(self):
        result = apply_order_scope(
            ORDERS,
            [
                {
                    "column": "distance_km",
                    "type": "number",
                    "operator": "between",
                    "value": [60, 100],
                    "resolved": None,
                }
            ],
        )
        self.assertEqual([row["order_id"] for row in result], ["C"])

    def test_preview_only_exposes_present_filterable_columns(self):
        completeness = {
            key: {"present": True}
            for key in ORDERS[0]
        }
        preview = scope_preview(
            {"records": ORDERS, "completeness": completeness},
            {
                "records": [
                    {"ownership": "own"},
                    {"ownership": "third_party"},
                ]
            },
            [],
        )
        fields = {item["column"]: item for item in preview["fields"]}
        self.assertEqual(fields["destination"]["type"], "category")
        self.assertEqual(fields["estimated_dispatch_date"]["max"], "2026-10-04")
        self.assertEqual(preview["fleet"]["own"], 1)
        self.assertEqual(preview["fleet"]["third_party"], 1)

    def test_resource_mode_is_backward_compatible(self):
        self.assertEqual(
            AssignmentOptions.model_validate({"allow_third_party": False}).resource_mode,
            "own",
        )
        self.assertEqual(
            AssignmentOptions.model_validate({"allow_third_party": True}).resource_mode,
            "mixed",
        )
        self.assertTrue(
            AssignmentOptions.model_validate({"resource_mode": "outsourced"}).allow_third_party
        )

    def test_scope_contract_rejects_wrong_type(self):
        with self.assertRaises(ValidationError):
            AssignmentConfig.model_validate(
                {
                    "scope": {
                        "filters": [
                            {
                                "column": "destination",
                                "type": "number",
                                "operator": "between",
                                "value": [1, 2],
                            }
                        ]
                    }
                }
            )


if __name__ == "__main__":
    unittest.main()
