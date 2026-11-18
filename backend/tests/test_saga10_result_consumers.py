"""Published cargo details/CSV exactness; legacy consumers remain unchanged."""
from decimal import Decimal as D
import json,unittest
from unittest.mock import patch
from app.engines.assignment.cargo_inputs import run_cargo_policy
from app.results.assembler import assemble,AssemblyError
from app.results.validation import read_delivery
from app.results.export_rows import transport_export_rows
from app.results.day_projections import day_export_rows
from app.engines.scheduling.day_scheduling import run_day_scheduling
from tests.saga10_fixtures import cargo_request
from tests.test_saga10_scheduling import make_request

class Saga10ResultConsumerTests(unittest.TestCase):
    def test_cargo_detail_has_requested_assigned_unserved_and_snapshot_labels(self):
        result=run_cargo_policy(cargo_request(),alternative_budget=0);bundle=assemble(result)
        detail=next(d for d in bundle.package.details if d.dataset_id=='cargo');rows=read_delivery(detail.data,bundle.artifacts)
        self.assertEqual(len(rows),3);self.assertEqual({r['facts']['presentation_label'] for r in rows},{'Jugo palletizado','Agua palletizado','Gaseosa palletizado'})
        self.assertEqual(sum(D(r['facts']['assigned']) for r in rows),12);self.assertTrue(all(D(r['facts']['unserved'])==0 for r in rows))
        export=read_delivery(bundle.package.exports.csv.rows,bundle.artifacts);self.assertEqual(bundle.package.exports.csv.granularity,'TRIP_ORDER_LINE')
        self.assertEqual(sum(D(row['estimated_cost']) for row in export if row['estimated_cost'] is not None),100)
        self.assertEqual(sum(D(row['load_weight_kg']) for row in export),13140);self.assertEqual(sum(D(row['quantity']) for row in export),12)
        self.assertEqual(sum(D(p['product_units']) for row in export for p in json.loads(row['products_json'])),11520)
        self.assertEqual({p['product_name'] for row in export for p in json.loads(row['products_json'])},{'Jugo','Agua','Gaseosa'})
    def test_rehashed_csv_cost_or_quantity_cannot_contradict_certificate(self):
        result=run_cargo_policy(cargo_request(),alternative_budget=0)
        for key in ['estimated_cost','quantity','load_weight_kg']:
            def changed(core):
                rows=[dict(r) for r in transport_export_rows(core)];rows[1][key]=D('1');return tuple(rows)
            with self.subTest(key=key),patch('app.results.assembler.transport_export_rows',changed),self.assertRaises(AssemblyError):assemble(result)
    def test_D2_line_csv_copies_same_quantities_with_source_and_dates(self):
        req=make_request();result=run_day_scheduling(req);bundle=assemble(result)
        rows=read_delivery(bundle.package.exports.csv.rows,bundle.artifacts)
        self.assertEqual(len(rows),len(req.source_core.transport_plan.cargo.allocations))
        self.assertEqual(sum(D(r['quantity']) for r in rows),12)
        self.assertTrue(all(r['source_run_id']==str(req.source_transport_plan.run_id) and r['upstream_result_fingerprint']==req.source_transport_plan.result_fingerprint for r in rows))
        self.assertEqual({(r['trip_id'],r['line_id'],D(r['quantity'])) for r in rows},{(a.trip_id,a.line_id,a.quantity) for a in req.source_core.transport_plan.cargo.allocations})
        self.assertIsNotNone(next(d for d in bundle.package.details if d.dataset_id=='cargo'))
