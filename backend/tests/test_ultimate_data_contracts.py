"""U4: descriptor/template/parser/normalizer coherence and O/P/Q/R boundaries."""
import copy,csv,io,json
from itertools import product
import unittest
from uuid import uuid4

from app.domain.logistics.data_contracts import compile_contract,template_csv,NORMALIZER_VERSION,REGISTRY_VERSION
from app.domain.logistics.normalizers import normalize_input,InputValidationError
from app.services.logistics_model_service import configuration_snapshot
from tests.test_ultimate_case_models import config

MID='10000000-0000-4000-8000-000000000099'
def model(**changes):
    c,h=configuration_snapshot(config(**changes));return {'id':MID,'config_jsonb':c,'config_hash':h}
def contract(entity='transport_demand',**changes):return compile_contract(model(**changes),entity)
def rows(c):return list(csv.DictReader(io.StringIO(template_csv(c).decode())))
def emit(c,data):
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=[f.public_header for f in c.fields],lineterminator='\n');w.writeheader();w.writerows(data);return out.getvalue().encode()
def one(c,**changes):
    row=rows(c)[0];row.update(changes);return emit(c,[row])


class UltimateDataContractTests(unittest.TestCase):
    def reject(self,c,body,code=None):
        with self.assertRaises(InputValidationError) as raised:normalize_input(body,c)
        self.assertFalse(raised.exception.report['valid'])
        if code:self.assertTrue(any(x['code']==code for x in raised.exception.report['errors']),raised.exception.report)
        return raised.exception.report
    def test_descriptor_serializes_and_hash_is_deterministic(self):
        a=contract();b=contract();self.assertEqual(a,b);self.assertEqual(a.contract_hash,b.contract_hash)
        self.assertEqual(a.model_validate_json(a.model_dump_json()),a)
        self.assertEqual(a.registry_version,REGISTRY_VERSION);self.assertEqual(a.normalizer_version,NORMALIZER_VERSION)
        for f in a.fields:
            self.assertTrue(f.semantic_key and f.engine_role and f.required_for and f.used_by and f.examples)
        self.assertEqual(a.rules['extra_columns'],'REJECT')
    def test_unknown_entity_or_registry_fails_closed(self):
        for entity,registry in [('orders',REGISTRY_VERSION),('transport_demand','UNKNOWN')]:
            with self.assertRaises(ValueError):compile_contract(model(),entity,registry)
    def test_pallet_only_needs_no_kg_and_template_has_five_valid_rows(self):
        for entity in ['transport_demand','transport_resources']:
            c=contract(entity);self.assertFalse(any('weight_kg' in f.public_header for f in c.fields));self.assertEqual(normalize_input(template_csv(c),c)['record_count'],5)
    def test_Q_role_source_and_dimension_matrix_uses_same_semantics(self):
        for role,sources,dim in product(['SHIPPER','LOGISTICS_PROVIDER','HYBRID'],[['OWN'],['EXTERNAL'],['OWN','EXTERNAL']],['pallets','weight_kg','volume_m3','units']):
            with self.subTest(role=role,sources=sources,dim=dim):
                for entity in ['transport_demand','transport_resources']:
                    c=contract(entity,operating_role=role,allowed_sources=sources,active_dimensions=[dim],primary_dimension=dim)
                    self.assertEqual(normalize_input(template_csv(c),c)['record_count'],5)
                    self.assertNotIn('engine_name',c.model_dump())
    def test_only_own_or_external_fields_are_compiled(self):
        own={f.public_header for f in contract('transport_resources',allowed_sources=['OWN']).fields};external={f.public_header for f in contract('transport_resources',allowed_sources=['EXTERNAL']).fields}
        self.assertNotIn('services_available',own);self.assertNotIn('units_available',external)
    def test_conditional_fields_are_checked_per_row(self):
        c=contract('transport_resources');self.reject(c,one(c,services_available='1'),'SOURCE_CONDITIONAL')
        ex=rows(c)[1];ex['units_available']='1';self.reject(c,emit(c,[ex]),'SOURCE_CONDITIONAL')
    def test_contract_hash_pins_configuration_and_published_version(self):
        c=contract();self.assertNotEqual(c.contract_hash,contract(split_permitted=True).contract_hash)
        v=model();v['id']=str(uuid4());self.assertNotEqual(c.contract_hash,compile_contract(v,'transport_demand').contract_hash)
    def test_missing_header_is_guided_and_not_inferred(self):
        c=contract();self.reject(c,template_csv(c).replace(b'demand_pallets',b'Peso'),'EXTRA_COLUMN')
        text=template_csv(c).decode().splitlines();text[0]=text[0].replace(',demand_pallets','');self.reject(c,('\n'.join(text)+'\n').encode(),'MISSING_COLUMN')
    def test_P_forbidden_commercial_extras_are_rejected_without_echoing_values(self):
        c=contract()
        for extra in ['customer_name','CUIT','SKU','invoice','revenue','margin','dispatch_date']:
            body=template_csv(c).decode().splitlines();body[0]+=','+extra
            for i in range(1,len(body)):body[i]+=',PRIVATE-COMMERCIAL'
            result=self.reject(c,('\n'.join(body)+'\n').encode(),'EXTRA_COLUMN');self.assertNotIn('PRIVATE-COMMERCIAL',json.dumps(result))
    def test_R_duplicate_ids_enum_dates_and_ready_due(self):
        c=contract();r=rows(c);r[1]['order_id']=r[0]['order_id'];self.reject(c,emit(c,r),'DUPLICATE_ID')
        for values in [dict(priority='Normal'),dict(ready_date='02/11/2026'),dict(ready_date='2026-02-30'),dict(ready_date='2026-11-08',delivery_due_date='2026-11-02'),dict(split_allowed='yes')]:
            with self.subTest(values=values):self.reject(c,one(c,**values))
    def test_R_negative_or_zero_physical_capacity_and_guarantee_above_max(self):
        c=contract('transport_resources')
        for values in [dict(guaranteed_pallets='0'),dict(guaranteed_pallets='-1'),dict(maximum_pallets='1')]:
            with self.subTest(values=values):self.reject(c,one(c,**values))
    def test_availability_zero_is_valid_own_and_external(self):
        c=contract('transport_resources');a=rows(c)[0];a['units_available']='0';b=rows(c)[1];b['services_available']='0'
        n=json.loads(normalize_input(emit(c,[a,b]),c)['bytes']);self.assertEqual(n['records'][0]['units_available'],0);self.assertEqual(n['records'][1]['services_available'],0)
    def test_unknown_external_capacity_is_not_assumed_or_unlimited(self):
        c=contract('transport_resources',allowed_sources=['EXTERNAL']);n=normalize_input(one(c,services_available='',availability_source='UNKNOWN'),c)
        row=json.loads(n['bytes'])['records'][0];self.assertIsNone(row['services_available']);self.assertEqual(row['availability_source'],'UNKNOWN');self.assertEqual(n['report']['summary']['unknown_availability_count'],1)
        self.reject(c,one(c,services_available='',availability_source='CONFIRMED'))
        self.reject(c,one(c,services_available='1',availability_source='UNKNOWN'))
    def test_O_explicit_assumption_defaults_one_with_frozen_provenance(self):
        c=contract('transport_resources',allowed_sources=['EXTERNAL']);n=normalize_input(one(c,services_available='',availability_source='ASSUMED'),c);snapshot=json.loads(n['bytes'])
        self.assertEqual(snapshot['records'][0]['services_available'],1);self.assertEqual(snapshot['records'][0]['availability_source'],'ASSUMED');self.assertEqual(snapshot['assumptions'][0]['source'],'DATION_DEFAULT')
        self.assertEqual(n['report']['warnings'][0]['code'],'ASSUMED_EXTERNAL_AVAILABILITY')
    def test_unknown_cost_is_null_and_known_zero_remains_zero(self):
        c=contract('transport_resources',allowed_sources=['EXTERNAL'],external_cost_models=['PER_TRIP']);a=normalize_input(one(c,trip_rate=''),c);b=normalize_input(one(c,trip_rate='0'),c)
        self.assertIsNone(json.loads(a['bytes'])['records'][0]['external_cost']['rate']);self.assertEqual(json.loads(b['bytes'])['records'][0]['external_cost']['rate'],'0');self.assertNotEqual(a['canonical_sha256'],b['canonical_sha256'])
    def test_per_km_basis_and_disallowed_rate_are_checked(self):
        c=contract('transport_resources',allowed_sources=['EXTERNAL'],external_cost_models=['PER_KM'],per_km_billing_bases=['ROUND_TRIP'])
        self.assertEqual(json.loads(normalize_input(template_csv(c),c)['bytes'])['records'][0]['external_cost']['billing_basis'],'ROUND_TRIP')
        self.reject(c,one(c,billing_basis='ONE_WAY'));self.reject(c,one(c,billing_basis=''))
    def test_multidimensional_units_precision_and_fraction_coherence_not_inferred(self):
        c=contract(active_dimensions=['pallets','weight_kg','volume_m3'],primary_dimension='pallets')
        n=normalize_input(one(c,demand_pallets='1.001',demand_weight_kg='10.123',demand_volume_m3='.123456'),c)
        self.assertEqual(json.loads(n['bytes'])['records'][0]['requested']['volume_m3'],'0.123456')
        self.reject(c,one(c,demand_pallets='1.0001'));self.reject(c,one(c,demand_weight_kg=''))
    def test_no_fuzzy_numeric_date_or_boolean_mapping(self):
        c=contract()
        for values in [dict(distance_km='1,5'),dict(distance_km='NaN'),dict(distance_km='Infinity'),dict(split_allowed='1'),dict(priority='medium')]:self.reject(c,one(c,**values))
    def test_compatibility_is_explicit_unless_model_declares_homogeneous(self):
        c=contract();self.reject(c,one(c,compatibility_groups=''),'REQUIRED_VALUE')
        homogeneous=contract(homogeneous_loads_declared=True);self.assertEqual(json.loads(normalize_input(one(homogeneous,compatibility_groups=''),homogeneous)['bytes'])['records'][0]['compatibility_groups'],[])
    def test_no_arbitrary_lanes_or_source_inference(self):
        c=contract('transport_resources')
        for values in [dict(lanes='all'),dict(lanes='[]'),dict(lanes='[["A"]]'),dict(source='THIRD_PARTY'),dict(lanes='[["A","B"],["A","B"]]')]:self.reject(c,one(c,**values))
    def test_canonical_reproduction_and_raw_hash_distinction(self):
        c=contract();a=normalize_input(template_csv(c),c);b=normalize_input(template_csv(c),c);self.assertEqual(a,b)
        r=rows(c);r.reverse();changed=normalize_input(emit(c,r),c);self.assertNotEqual(a['raw_sha256'],changed['raw_sha256']);self.assertEqual(a['canonical_sha256'],changed['canonical_sha256'])
        self.assertNotEqual(a['raw_sha256'],a['canonical_sha256'])
    def test_blank_invalid_utf8_duplicate_header_and_csv_syntax(self):
        c=contract()
        for body in [b'',b'\xff\xfe',b'order_id,order_id\nA,B\n',template_csv(c).split(b'\n',1)[0]+b'\n',template_csv(c).split(b'\n',1)[0]+b'\n"unterminated']:
            self.reject(c,body)
    def test_descriptor_maps_are_immutable(self):
        c=contract()
        with self.assertRaises(TypeError):c.rules['extra_columns']='ALLOW'
        with self.assertRaises(TypeError):c.fields[0].validation['max_length']=10000
    def test_unsupported_pinned_versions_fail_closed(self):
        c=contract();self.reject(c.model_copy(update={'normalizer_version':'UNKNOWN'}),template_csv(c),'UNSUPPORTED_VERSION')
        value=model();value['contract_registry_version']='UNKNOWN'
        with self.assertRaises(ValueError):compile_contract(value,'transport_demand')
    def test_assumption_summary_is_bounded_without_losing_total_provenance(self):
        c=contract('transport_resources',allowed_sources=['EXTERNAL']);base=rows(c)[0];data=[]
        for i in range(101):data.append({**base,'resource_id':'RES-'+str(i),'services_available':'','availability_source':'ASSUMED'})
        n=normalize_input(emit(c,data),c);summary=n['report']['summary'];self.assertEqual(summary['assumptions_total'],101);self.assertEqual(len(summary['assumptions']),20);self.assertTrue(summary['assumptions_truncated']);self.assertEqual(len(json.loads(n['bytes'])['assumptions']),101)


if __name__=='__main__':unittest.main()
