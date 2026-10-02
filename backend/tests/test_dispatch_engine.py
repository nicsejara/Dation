import csv
import io
import unittest
from app.engines.dispatch import run_dispatch_engine
from app.validators.orders_schema import COLUMNS
from app.validators.fleet_schema import COLUMNS as FC


def csv_bytes(cols, rows):
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=cols,delimiter=';');w.writeheader();w.writerows(rows)
    return out.getvalue().encode()


def order(id='A', units=1, weight=400, day='2026-10-01', window=2):
    return dict(zip(COLUMNS,[id,'Producto',units,weight,'Origen','Destino',100,'Normal',window,day]))


def fleet(own=1, third=True, base='Origen'):
    rows=[{
        'fleet_pool_id':'OWN-S',
        'vehicle_type':'S',
        'ownership':'own',
        'base_location':base,
        'capacity_kg':1000,
        'cost_per_km':1,
        'fixed_trip_cost':10,
        'units_available':own,
        'avg_speed_kmh':100,
        'driving_hours_per_day':10,
        'fuel_l_per_100km':20,
        'co2_kg_per_km':.5,
    }]
    if third:
        rows.append({
            'fleet_pool_id':'TP-T',
            'vehicle_type':'T',
            'ownership':'third_party',
            'base_location':'*',
            'capacity_kg':1000,
            'cost_per_km':2,
            'fixed_trip_cost':20,
            'units_available':'',
            'avg_speed_kmh':100,
            'driving_hours_per_day':10,
            'fuel_l_per_100km':20,
            'co2_kg_per_km':.5,
        })
    return csv_bytes(FC,rows)


class DispatchEngineTests(unittest.TestCase):
    def run_case(self, rows, f=None, **kwargs):
        return run_dispatch_engine(csv_bytes(COLUMNS,rows),f or fleet(),options={'sensitivity':False,'deterministic_limit':.05},**kwargs)

    def test_consolidation_and_integer_capacity(self):
        result=self.run_case([order('A'),order('B')],configuration={'objective':'min_trips'})
        self.assertEqual(result['scenarios']['selected']['metrics']['total_trips'],1)
        r=self.run_case([order(units=3,weight=600)])
        self.assertEqual(r['scenarios']['min_trips']['metrics']['total_trips'],3)
        self.assertEqual(r['scenarios']['selected']['metrics']['units_delivered'],3)

    def test_limited_fleet_and_late(self):
        r=self.run_case([order(units=3,weight=600,window=1)],configuration={'objective':'min_cost'})
        self.assertAlmostEqual(r['scenarios']['selected']['metrics']['outsourced_trips_share'],2/3)
        o=order(window=1);o['distance_km']=2500
        r=self.run_case([o]);s=r['scenarios']['selected']
        self.assertEqual(s['metrics']['late_orders_unavoidable'],1)
        self.assertEqual(s['trips'][0]['dispatch_date'],'2026-10-01')
        self.assertEqual(s['order_outcomes'][0]['late_days'],2)

    def test_determinism_extremes(self):
        rows=[order('A'),order('B',day='2026-10-02')]
        a=self.run_case(rows);b=self.run_case(rows)
        self.assertEqual(a['result_fingerprint'],b['result_fingerprint'])
        for name in ('min_cost','min_trips','min_time'):
            r=self.run_case(rows,configuration={'objective':name})
            self.assertEqual(r['scenarios'][name]['metrics'],r['scenarios']['selected']['metrics'])

    def test_infeasible_not_partial(self):
        with self.assertRaises(ValueError):self.run_case([order(units=3,weight=600,window=1)],fleet(third=False))

    def test_outlier_requires_decision(self):
        with self.assertRaisesRegex(ValueError,'anomalía'):self.run_case([order(units=51)])

    def test_reprogramming(self):
        r=self.run_case([order(units=2,weight=600,window=2)],fleet(third=False))
        self.assertEqual(r['scenarios']['selected']['metrics']['units_delivered'],2)
        self.assertEqual(len(set(t['dispatch_date'] for t in r['scenarios']['selected']['trips'])),2)

    def test_conservation_and_weighted_reference(self):
        rows=[order('A',3,600),order('B',2,400)]
        r=self.run_case(rows,configuration={'mode':'custom','objective':'custom','weights':{'cost':.4,'trips':.3,'time':.3}})
        for scenario in r['scenarios'].values():
            if scenario.get('feasible'):
                self.assertEqual(scenario['metrics']['units_delivered'],5)
        def score(s):
            return sum(r['configuration']['weights'][k]*s['metrics'][metric]/r['normalization'][k]['scale']
                for k,metric in [('cost','total_cost'),('trips','total_trips'),('time','avg_lead_time_days')])
        self.assertLessEqual(score(r['scenarios']['selected']),score(r['scenarios']['baseline_direct'])+1e-8)

    def test_anomalies_include_and_exclude(self):
        data=csv_bytes(COLUMNS,[order('A',51),order('B')])
        for decision,units in [('include',52),('exclude',1)]:
            r=run_dispatch_engine(data,fleet(),options={'sensitivity':False,'anomaly_decisions':{'A':decision}})
            self.assertEqual(r['scenarios']['selected']['metrics']['units_delivered'],units)
            self.assertEqual(r['inputs']['anomalies'][0]['decision'],decision)

    def test_historical_vehicle_assignment_is_ignored(self):
        row={**order(),'current_vehicle_type':'missing'}
        data=csv_bytes(COLUMNS+['current_vehicle_type'],[row])
        r=run_dispatch_engine(data,fleet(),options={'sensitivity':False})
        self.assertNotIn('baseline_current',r['scenarios'])
        self.assertEqual(r['scenarios']['selected']['metrics']['units_delivered'],1)

        row['current_vehicle_type']='T'
        data=csv_bytes(COLUMNS+['current_vehicle_type'],[row])
        r=run_dispatch_engine(data,fleet(),options={'allow_third_party':False,'sensitivity':False})
        self.assertNotIn('baseline_current',r['scenarios'])
        self.assertEqual(r['scenarios']['selected']['metrics']['outsourced_trips_share'],0)

    def test_spatial_pool_cannot_serve_another_origin(self):
        with self.assertRaisesRegex(ValueError,'No hay flota habilitada'):
            self.run_case([order()],fleet(own=1,third=False,base='Otra Base'))

    def test_trip_exposes_pool_and_base(self):
        r=self.run_case([order()],fleet(own=1,third=False,base='Origen'))
        trip=r['scenarios']['selected']['trips'][0]
        self.assertEqual(trip['fleet_pool_id'],'OWN-S')
        self.assertEqual(trip['base_location'],'Origen')

    def test_multiday_cycle_blocks_own_fleet_until_return(self):
        first=order('A',weight=600,day='2026-10-01',window=3)
        second=order('B',weight=600,day='2026-10-02',window=2)
        first['distance_km']=600
        second['distance_km']=600
        r=self.run_case(
            [first,second],
            fleet(third=False),
            configuration={'objective':'min_cost'},
        )
        trips=r['scenarios']['selected']['trips']
        self.assertEqual(
            [trip['dispatch_date'] for trip in trips],
            ['2026-10-01','2026-10-03'],
        )
        self.assertEqual(trips[0]['cycle_days'],2)
        self.assertEqual(
            trips[0]['resource_available_again'],
            '2026-10-03',
        )
        self.assertEqual(
            r['scenarios']['selected']['metrics']['avg_cycle_days'],
            2,
        )

    def test_min_time_can_outsource_while_own_vehicle_is_busy(self):
        first=order('A',weight=600,day='2026-10-01',window=3)
        second=order('B',weight=600,day='2026-10-02',window=2)
        first['distance_km']=600
        second['distance_km']=600
        r=self.run_case(
            [first,second],
            fleet(third=True),
            configuration={'objective':'min_time'},
        )
        selected=r['scenarios']['selected']
        self.assertEqual(
            [trip['dispatch_date'] for trip in selected['trips']],
            ['2026-10-01','2026-10-02'],
        )
        self.assertAlmostEqual(
            selected['metrics']['outsourced_trips_share'],
            .5,
        )

    def test_validation_rejects_temporal_double_booking(self):
        import copy
        from app.engines.dispatch.plans import validate_plan
        from app.validators.orders_schema import validate_orders_csv
        from app.validators.fleet_schema import validate_fleet_csv

        first=order('A',weight=600,day='2026-10-01',window=3)
        second=order('B',weight=600,day='2026-10-02',window=2)
        first['distance_km']=600
        second['distance_km']=600
        orders_bytes=csv_bytes(COLUMNS,[first,second])
        fleet_bytes=fleet(third=False)
        result=run_dispatch_engine(
            orders_bytes,
            fleet_bytes,
            configuration={'objective':'min_cost'},
            options={'sensitivity':False},
        )
        plan=copy.deepcopy(result['scenarios']['selected']['trips'])
        plan[1]['dispatch_date']='2026-10-02'
        plan[1]['arrival_date']='2026-10-03'
        plan[1]['resource_available_again']='2026-10-04'
        with self.assertRaisesRegex(ValueError,'Disponibilidad temporal'):
            validate_plan(
                plan,
                validate_orders_csv(orders_bytes)['records'],
                validate_fleet_csv(fleet_bytes)['records'],
            )

    def test_sensitivity_reports_consecutive_changes(self):
        r=run_dispatch_engine(csv_bytes(COLUMNS,[order('A'),order('B')]),fleet())
        points=r['sensitivity']['weight_sweep']
        self.assertEqual(len(points),7)
        self.assertIsNone(points[0]['orders_changed_vs_previous'])
        self.assertTrue(all(0<=p['orders_changed_vs_previous']<=2 for p in points[1:]))

    def test_validation_rejects_corrupt_plan(self):
        from app.engines.dispatch.plans import validate_plan
        from app.validators.orders_schema import validate_orders_csv
        from app.validators.fleet_schema import validate_fleet_csv
        data=csv_bytes(COLUMNS,[order()]);r=run_dispatch_engine(data,fleet(),options={'sensitivity':False})
        plan=r['scenarios']['selected']['trips'];plan[0]['arrival_date']='2026-12-01'
        with self.assertRaisesRegex(ValueError,'Llegada'):validate_plan(plan,validate_orders_csv(data)['records'],validate_fleet_csv(fleet())['records'])
