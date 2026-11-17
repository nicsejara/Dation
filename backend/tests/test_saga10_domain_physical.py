"""G1/G2: references, precision and seeded conservation properties."""
from copy import deepcopy
from decimal import Decimal as D
import random,unittest
from pydantic import ValidationError
from app.domain.logistics.physical import normalize_catalog,line_load
from app.models.ultimate_foundation import parse_configuration,ModelCreate
from app.results.canonical import canonical_bytes
from app.services.logistics_model_service import configuration_snapshot,snapshot_hash
from tests.saga10_fixtures import direct_config,catalog_config,bulk_config
from tests.test_ultimate_case_models import config

class Saga10DomainPhysicalTests(unittest.TestCase):
    def normalized(self,value=None):
        c=parse_configuration(value or catalog_config());return normalize_catalog(c.cargo,c.active_dimensions)
    def test_legacy_hash_and_dto_are_byte_identical(self):
        old=config();wire,h=configuration_snapshot(old)
        self.assertEqual(canonical_bytes(parse_configuration(wire)),canonical_bytes(old));self.assertEqual(h,snapshot_hash('logistics_model_configuration_v1',wire));self.assertNotIn('cargo',wire)
    def test_v2_direct_has_no_dummy_product(self):
        c=parse_configuration(direct_config());self.assertEqual(c.version,2);self.assertEqual(c.cargo.products,());self.assertEqual(self.normalized(direct_config()),{})
        ModelCreate(id='00000000-0000-0000-0000-000000000001',name='Modelo',configuration=c)
    def test_numeric_examples_A_B(self):
        p=self.normalized();totals={key:D(0) for key in ['pallets','weight_kg','volume_m3','units']}
        for pid,n in [('PAL-JUICE',5),('PAL-WATER',4),('PAL-SODA',3)]:
            for key,v in line_load(p[pid],D(n)).model_dump().items():totals[key]+=v
        self.assertEqual((totals['pallets'],totals['weight_kg'],totals['volume_m3']),(12,13140,D('27.24')))
        juice=line_load(p['PAL-JUICE'],D(20));self.assertEqual((juice.weight_kg,juice.units,juice.volume_m3),(19700,19200,D('43.2')))
        self.assertEqual(p['PAL-JUICE'].composition[0]['units_per_package'],12)
    def test_shared_unit_new_snapshots_multiple_presentations(self):
        value=catalog_config();original=parse_configuration(value);first=canonical_bytes(original);value['cargo']['logistic_units'][0]['tare_mass']['value']='30'
        for p in value['cargo']['presentations']:p.pop('gross_mass')
        second=parse_configuration(value);self.assertEqual(self.normalized(value)['PAL-JUICE'].coefficients.weight_kg,990)
        self.assertEqual(canonical_bytes(original),first);self.assertNotEqual(configuration_snapshot(original)[1],configuration_snapshot(second)[1])
        value=catalog_config();value['cargo']['presentations'].append({**value['cargo']['presentations'][0],'presentation_id':'JUICE-OTHER','label':'Otra presentación'})
        self.assertEqual(len(self.normalized(value)),4)
    def test_unit_conversion_loaded_volume_not_empty_or_product_geometry(self):
        value=catalog_config();value['cargo']['presentations'][0]['gross_mass']={'value':'.985','unit':'t'};value['cargo']['presentations'][0]['external_volume']={'value':'2160','unit':'l'}
        p=self.normalized(value)['PAL-JUICE'];self.assertEqual((p.coefficients.weight_kg,p.coefficients.volume_m3),(985,D('2.16')))
        value=catalog_config();value['cargo']['presentations'][0].pop('loaded_dimensions');value['cargo']['products'][0]['dimensions']={'length':'1','width':'1','height':'1','unit':'m'}
        with self.assertRaisesRegex(ValueError,'Falta una propiedad'):self.normalized(value)
    def test_explicit_density_and_contradictions(self):
        p=self.normalized(bulk_config())['BULK'];load=line_load(p,D('.125'));self.assertEqual((load.weight_kg,load.volume_m3),(D('106.25'),D('.125')))
        with self.assertRaisesRegex(ValueError,'Falta una propiedad'):self.normalized(bulk_config(None))
        value=bulk_config();value['cargo']['presentations'][0]['gross_mass']={'value':'900','unit':'kg'}
        with self.assertRaisesRegex(ValueError,'contradictorios'):self.normalized(value)
        for key,declared in [('gross_mass',{'value':'986','unit':'kg'}),('external_volume',{'value':'2.17','unit':'m3'})]:
            value=catalog_config();value['cargo']['presentations'][0][key]=declared
            with self.assertRaisesRegex(ValueError,'contradice'):self.normalized(value)
    def test_duplicates_references_no_recursive_presentation(self):
        for mutate in [lambda c:c['cargo']['products'].append(deepcopy(c['cargo']['products'][0])),lambda c:c['cargo']['products'][1].update(name='JUGO'),lambda c:c['cargo']['logistic_units'].clear(),lambda c:c['cargo']['presentations'][0]['components'][0].update(product_id='PAL-JUICE')]:
            value=catalog_config();mutate(value)
            with self.assertRaises(ValidationError):parse_configuration(value)
        value=direct_config();value['cargo']['products']=catalog_config()['cargo']['products']
        with self.assertRaises(ValidationError):parse_configuration(value)
    def test_invalid_numeric_inputs_and_no_fractional_pallets(self):
        for invalid in ['NaN','Infinity','-1',1.2,'1000000000000000000000']:
            value=catalog_config();value['cargo']['products'][0]['gross_mass']['value']=invalid
            with self.assertRaises(ValidationError):parse_configuration(value)
        p=self.normalized()['PAL-JUICE']
        for q in [D('1.5'),D(0),D(-1)]:
            with self.assertRaises(ValueError):line_load(p,q)
    def test_split_compatibility_and_structural_limit(self):
        for mutate in [lambda c:c.update(split_permitted=False),lambda c:c.update(homogeneous_loads_declared=False),lambda c:c['cargo']['logistic_units'][0].update(structural_limit_kg='980')]:
            value=catalog_config();mutate(value)
            with self.assertRaises(ValidationError):parse_configuration(value)
    def test_mixed_requires_explicit_symmetric_coload(self):
        value=catalog_config();value['homogeneous_loads_declared']=False;value['cargo']['compatibility_policy']='CATEGORIZED'
        for i,p in enumerate(value['cargo']['products']):p['compatibility_groups']=['TAG-'+str(i)]
        mixed=deepcopy(value['cargo']['presentations'][0]);mixed.update(presentation_id='MIX',label='Mixta',components=[{'product_id':'JUICE','quantity':'40'},{'product_id':'WATER','quantity':'40'}]);mixed.pop('gross_mass');value['cargo']['presentations'].append(mixed)
        with self.assertRaisesRegex(ValidationError,'no autorizados'):parse_configuration(value)
        value['cargo']['co_load_pairs']=[['TAG-1','TAG-0']];c=parse_configuration(value)
        self.assertTrue(c.cargo.can_co_load(['TAG-0'],['TAG-1']));self.assertFalse(c.cargo.can_co_load(['TAG-0'],['TAG-2']))
        self.assertEqual(self.normalized(value)['MIX'].coefficients.weight_kg,1105)
    def test_seeded_scaling_and_permutation_conserve(self):
        rng=random.Random(10);presentations=self.normalized()
        for _ in range(100):
            pid=rng.choice(list(presentations));a,b=rng.randint(1,100),rng.randint(1,100);whole=line_load(presentations[pid],D(a+b));parts=[line_load(presentations[pid],D(a)),line_load(presentations[pid],D(b))]
            for dim,v in whole.model_dump().items():self.assertEqual(v,sum(getattr(p,dim) for p in parts))
        value=catalog_config();expected=self.normalized(value);value['cargo']['products'].reverse();value['cargo']['presentations'].reverse();self.assertEqual(self.normalized(value),expected)
    def test_continuous_increment_conserves_canonical_precision(self):
        p=self.normalized(bulk_config('1500',unit='kg'))['BULK'];self.assertEqual(p.allocation_increment,1)
        with self.assertRaisesRegex(ValueError,'incremento'):line_load(p,D('.5'))
        self.assertEqual(line_load(p,D(2)).weight_kg,2);self.assertIn('SCALAR_EXTERIOR_ONLY',p.provenance['geometry'])
