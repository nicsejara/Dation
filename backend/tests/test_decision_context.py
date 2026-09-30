import unittest

from app.engines.logistics.engine import (
    run_logistics_engine,
)
from app.services.decision_context import (
    build_decision_context,
)


CSV = """shipment_id,product,quantity_units,unit_weight_kg,origin,destination,distance_km,vehicle_type,vehicle_capacity_kg,cost_per_km,fixed_trip_cost,priority,max_delivery_days,dispatch_date
SHP-001,A,15,100,Cordoba,Rosario,100,Small,1000,1,0,Normal,3,2026-10-01
SHP-002,A,15,100,Cordoba,Rosario,100,Large,2000,3,0,High,2,2026-10-02
""".encode("utf-8")


class DecisionContextTests(
    unittest.TestCase
):
    def test_custom_run_keeps_custom_identity(
        self,
    ):
        result = run_logistics_engine(
            CSV,
            configuration={
                "mode": "custom",
                "objective": "custom",
                "weights": {
                    "cost": 0.7,
                    "trips": 0.3,
                },
            },
        )

        context = build_decision_context(
            result,
            result["configuration"],
        )

        semantics = context[
            "selection_semantics"
        ]

        self.assertEqual(
            context["recommended_scenario"],
            "custom",
        )
        self.assertEqual(
            semantics["requested_mode"],
            "custom",
        )
        self.assertEqual(
            semantics["selected_label"],
            "Configuración personalizada",
        )
        self.assertEqual(
            semantics["requested_weights"],
            {
                "cost": 0.7,
                "trips": 0.3,
            },
        )
        self.assertIn(
            "Nunca renombrarla",
            semantics["interpretation_rule"],
        )

    def test_equivalence_does_not_rename_custom(
        self,
    ):
        result = run_logistics_engine(
            CSV,
            configuration={
                "mode": "custom",
                "objective": "custom",
                "weights": {
                    "cost": 1.0,
                    "trips": 0.0,
                },
            },
        )

        context = build_decision_context(
            result,
            result["configuration"],
        )

        semantics = context[
            "selection_semantics"
        ]

        self.assertEqual(
            semantics["selected_label"],
            "Configuración personalizada",
        )
        self.assertIn(
            "min_cost",
            semantics[
                "equivalent_scenarios"
            ],
        )


    def test_context_exposes_reference_semantics(
        self,
    ):
        result = run_logistics_engine(
            CSV,
            objective="min_cost",
        )

        context = build_decision_context(
            result,
            result["configuration"],
        )

        reference = context[
            "reference_semantics"
        ]

        self.assertEqual(
            reference["label"],
            "Asignación de referencia",
        )
        self.assertIn(
            "vehicle_type",
            reference["source"],
        )
        self.assertIn(
            "No implica",
            reference["meaning"],
        )
        self.assertEqual(
            context["scenarios"][
                "baseline"
            ]["name"],
            "Asignación de referencia",
        )


if __name__ == "__main__":
    unittest.main()
