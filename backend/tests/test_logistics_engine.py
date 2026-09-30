import unittest

from pydantic import ValidationError

from app.engines.logistics.engine import (
    run_logistics_engine,
)
from app.models.decision_config import (
    DecisionRunConfig,
    normalize_stored_configuration,
)


CSV = """shipment_id,product,quantity_units,unit_weight_kg,origin,destination,distance_km,vehicle_type,vehicle_capacity_kg,cost_per_km,fixed_trip_cost,priority,max_delivery_days,dispatch_date
SHP-001,A,15,100,Cordoba,Rosario,100,Small,1000,1,0,Normal,3,2026-10-01
SHP-002,A,15,100,Cordoba,Rosario,100,Large,2000,3,0,High,2,2026-10-02
""".encode("utf-8")


def signature(result: dict, scenario: str):
    return [
        (
            item["shipment_id"],
            item["vehicle_type"],
        )
        for item in result[
            "scenarios"
        ][scenario]["assignments"]
    ]


class LogisticsEngineV02Tests(
    unittest.TestCase
):
    def test_custom_cost_extreme_matches_min_cost(
        self,
    ):
        preset = run_logistics_engine(
            CSV,
            objective="min_cost",
        )
        custom = run_logistics_engine(
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

        self.assertEqual(
            signature(
                preset,
                "min_cost",
            ),
            signature(
                custom,
                "custom",
            ),
        )
        self.assertEqual(
            preset["scenarios"][
                "min_cost"
            ]["metrics"],
            custom["scenarios"][
                "custom"
            ]["metrics"],
        )
        self.assertEqual(
            custom["sensitivity"][
                "matches_scenario"
            ],
            "min_cost",
        )

    def test_custom_trips_extreme_matches_min_trips(
        self,
    ):
        preset = run_logistics_engine(
            CSV,
            objective="min_trips",
        )
        custom = run_logistics_engine(
            CSV,
            configuration={
                "mode": "custom",
                "objective": "custom",
                "weights": {
                    "cost": 0.0,
                    "trips": 1.0,
                },
            },
        )

        self.assertEqual(
            signature(
                preset,
                "min_trips",
            ),
            signature(
                custom,
                "custom",
            ),
        )
        self.assertEqual(
            preset["scenarios"][
                "min_trips"
            ]["metrics"],
            custom["scenarios"][
                "custom"
            ]["metrics"],
        )
        self.assertEqual(
            custom["sensitivity"][
                "matches_scenario"
            ],
            "min_trips",
        )

    def test_custom_70_30_is_deterministic(
        self,
    ):
        configuration = {
            "mode": "custom",
            "objective": "custom",
            "weights": {
                "cost": 0.7,
                "trips": 0.3,
            },
        }

        first = run_logistics_engine(
            CSV,
            configuration=configuration,
        )
        second = run_logistics_engine(
            CSV,
            configuration=configuration,
        )

        self.assertEqual(
            signature(
                first,
                "custom",
            ),
            signature(
                second,
                "custom",
            ),
        )
        self.assertEqual(
            first["scenarios"][
                "custom"
            ]["metrics"],
            second["scenarios"][
                "custom"
            ]["metrics"],
        )
        self.assertEqual(
            first[
                "recommended_scenario"
            ],
            "custom",
        )
        self.assertEqual(
            first["configuration"][
                "weights"
            ],
            {
                "cost": 0.7,
                "trips": 0.3,
            },
        )

    def test_custom_result_keeps_baseline_and_scores(
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

        self.assertIn(
            "baseline",
            result["scenarios"],
        )
        self.assertIn(
            "min_cost",
            result["scenarios"],
        )
        self.assertIn(
            "min_trips",
            result["scenarios"],
        )
        self.assertIn(
            "custom",
            result["scenarios"],
        )

        assignment = result[
            "scenarios"
        ]["custom"]["assignments"][0]

        self.assertIn(
            "decision_score",
            assignment,
        )
        self.assertIn(
            "normalized_cost",
            assignment,
        )
        self.assertIn(
            "normalized_trips",
            assignment,
        )
        self.assertIn(
            "score_components",
            assignment,
        )

    def test_weights_must_sum_to_one(
        self,
    ):
        with self.assertRaises(
            ValidationError
        ):
            DecisionRunConfig(
                mode="custom",
                objective="custom",
                weights={
                    "cost": 0.7,
                    "trips": 0.4,
                },
            )

    def test_weights_must_be_in_range(
        self,
    ):
        with self.assertRaises(
            ValidationError
        ):
            DecisionRunConfig(
                mode="custom",
                objective="custom",
                weights={
                    "cost": 1.1,
                    "trips": -0.1,
                },
            )

    def test_legacy_min_cost_run_is_reconstructable(
        self,
    ):
        configuration = (
            normalize_stored_configuration(
                {
                    "objective": (
                        "min_cost"
                    )
                }
            )
        )

        self.assertEqual(
            configuration["mode"],
            "preset",
        )
        self.assertEqual(
            configuration["objective"],
            "min_cost",
        )
        self.assertEqual(
            configuration["weights"],
            {
                "cost": 1.0,
                "trips": 0.0,
            },
        )


if __name__ == "__main__":
    unittest.main()
