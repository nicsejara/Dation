import unittest
from app.services.dispatch_context import verify_numbers

class DispatchContextTests(unittest.TestCase):
    def test_numeric_guard(self):
        context={'metrics':{'total_cost':1234567.5,'total_trips':12,'on_time_rate':.9}}
        self.assertTrue(verify_numbers('Costo $ 1.234.567,50 en 12 viajes; 90 % a tiempo.',context))
        self.assertFalse(verify_numbers('Costo $ 9.999.999.',context))

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
