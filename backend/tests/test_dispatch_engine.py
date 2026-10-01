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


def fleet(own=1, third=True):
    rows=[dict(zip(FC,['S','own',1000,1,10,own,100,10,20,.5]))]
    if third:rows.append(dict(zip(FC,['T','third_party',1000,2,20,'',100,10,20,.5])))
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
