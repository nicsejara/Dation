import importlib.util
import tempfile
import unittest
from pathlib import Path
from app.validators.orders_schema import validate_orders_csv
from app.validators.fleet_schema import validate_fleet_csv
from app.models.dispatch_config import DispatchConfig

ROOT = Path(__file__).resolve().parents[2]


class DispatchValidationTests(unittest.TestCase):
    def test_conversion_preserves_orders(self):
        spec = importlib.util.spec_from_file_location('convert', ROOT/'scripts/convert_legacy_csv.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'orders.csv'
            self.assertEqual(module.convert(ROOT/'sample_data/InputData-LogisticsDDA.csv',target),100)
            data=validate_orders_csv(target.read_bytes())
            self.assertEqual(data['profile']['total_units'],2682)
            self.assertEqual(data['profile']['total_weight_kg'],2384000)
            self.assertIn('current_vehicle_type',data['records'][0])

    def test_invalid_inputs(self):
        data=(ROOT/'sample_data/v1/orders.csv').read_bytes()
        for invalid in [data.replace(b'2026-10-09', b'10-09-26'),data.replace(b';11;',b';1.5;',1),data.replace(b';1400;',b';NaN;',1)]:
            with self.assertRaises(ValueError): validate_orders_csv(invalid)
        fleet=(ROOT/'sample_data/v1/fleet.csv').read_bytes()
        with self.assertRaises(ValueError):validate_fleet_csv(fleet.replace(b';4;70',b';;70',1))
        self.assertEqual(validate_fleet_csv(fleet)['rows'],4)

    def test_legacy_weights(self):
        config=DispatchConfig(mode='custom',objective='custom',weights={'cost':.7,'trips':.3})
        self.assertEqual(config.weights.time,0)
