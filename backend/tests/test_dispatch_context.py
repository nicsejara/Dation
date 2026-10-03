import unittest
from app.services.dispatch_context import verify_numbers

class DispatchContextTests(unittest.TestCase):
    def test_numeric_guard(self):
        context={'metrics':{'total_cost':1234567.5,'total_trips':12,'on_time_rate':.9}}
        self.assertTrue(verify_numbers('Costo $ 1.234.567,50 en 12 viajes; 90 % a tiempo.',context))
        self.assertFalse(verify_numbers('Costo $ 9.999.999.',context))

    def test_assignment_context_excludes_temporal_semantics(self):
        from app.engines.assignment import run_assignment_engine
        from app.services.dispatch_context import build_dispatch_context
        from test_assignment_engine import (
            FLEET_COLUMNS,
            ORDER_COLUMNS,
            csv_bytes,
            order,
            vehicle,
        )

        result = run_assignment_engine(
            csv_bytes(
                ORDER_COLUMNS,
                [order("A")],
            ),
            csv_bytes(
                FLEET_COLUMNS,
                [vehicle("VEH-001")],
            ),
            configuration={
                "objective": "min_trips",
                "dimensions": [
                    "trips",
                    "own_fleet",
                ],
            },
            options={
                "analysis_depth": "essential",
            },
        )
        context = build_dispatch_context(
            result
        )

        self.assertEqual(
            context["schema_version"],
            "assignment_v1",
        )
        self.assertFalse(
            context[
                "interpretation_boundary"
            ]["temporal"],
        )
        self.assertFalse(
            context[
                "interpretation_boundary"
            ]["sla_is_decided_here"],
        )
        self.assertIn(
            "assignment_by_vehicle",
            context,
        )
        self.assertIn(
            "key_events",
            context,
        )
        self.assertTrue(
            context["key_events"],
        )
        self.assertNotIn(
            "feasibility",
            context,
        )
        self.assertNotIn(
            "exceptions",
            context,
        )

    def test_scheduling_context_keeps_assignment_locked(self):
        from app.engines.assignment import run_assignment_engine
        from app.engines.scheduling import run_scheduling_engine
        from app.services.decision_context import build_decision_context
        from test_scheduling_engine import (
            FLEET_COLUMNS,
            ORDER_COLUMNS,
            csv_bytes,
            order,
            vehicle,
        )

        orders = [order("A", "Mendoza")]
        fleet = [vehicle()]
        assignment = run_assignment_engine(
            csv_bytes(
                ORDER_COLUMNS,
                orders,
            ),
            csv_bytes(
                FLEET_COLUMNS,
                fleet,
            ),
            configuration={
                "objective": "min_trips",
                "dimensions": [
                    "trips",
                    "own_fleet",
                ],
            },
            options={
                "analysis_depth": "essential",
            },
        )
        scheduling = run_scheduling_engine(
            csv_bytes(
                ORDER_COLUMNS,
                orders,
            ),
            csv_bytes(
                FLEET_COLUMNS,
                fleet,
            ),
            assignment,
        )
        context = build_decision_context(
            scheduling,
            scheduling["configuration"],
        )

        self.assertEqual(
            context["schema_version"],
            "scheduling_v1",
        )
        self.assertTrue(
            context[
                "interpretation_boundary"
            ]["assignment_locked"],
        )
        self.assertFalse(
            context[
                "interpretation_boundary"
            ]["can_change_vehicle"],
        )
        self.assertTrue(
            context[
                "interpretation_boundary"
            ]["temporal"],
        )
        self.assertIn(
            "sequence_by_vehicle",
            context,
        )
        self.assertTrue(
            context["sequence_by_vehicle"]
        )
        self.assertIn(
            "key_events",
            context,
        )

    def test_context_has_hard_size_bound(self):
        import json
        from app.services.dispatch_context import build_dispatch_context
        from test_dispatch_engine import order,fleet,csv_bytes,COLUMNS
        from app.engines.dispatch import run_dispatch_engine
        result=run_dispatch_engine(csv_bytes(COLUMNS,[order()]),fleet(),options={'sensitivity':False})
        result['fleet']=[{'vehicle_type':'X'*10000}]*100
        for scenario in result['scenarios'].values():
            if scenario.get('metrics'):scenario['metrics']['trips_by_vehicle_type']={'T'+str(i)+'x'*1000:i for i in range(100)}
        context=build_dispatch_context(result)
        self.assertEqual(context['schema_version'], 'dispatch_v2')
        self.assertIn('decision_drivers', context)
        self.assertIn('feasibility', context)
        self.assertIn('assignment_by_pool', context)
        self.assertTrue(context['assignment_by_pool'])
        self.assertIn(
            'products',
            context['assignment_by_pool'][0],
        )
        self.assertLessEqual(len(json.dumps(context,ensure_ascii=False)),18000)
