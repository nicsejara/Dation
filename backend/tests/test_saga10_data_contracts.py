"""G3: compiled CSV source of truth, strict references and legacy parity."""
import csv,io,json,unittest
from copy import deepcopy
from decimal import Decimal as D
from uuid import uuid4
from app.domain.logistics.data_contracts import compile_contract,template_csv,entities_for,ENTITIES
from app.domain.logistics.normalizers import normalize_input,InputValidationError
from app.domain.logistics.normalizers_v2 import combine_catalog
from app.services.logistics_model_service import configuration_snapshot
from tests.saga10_fixtures import catalog_config,direct_config,bulk_config
from tests.test_ultimate_data_contracts import model as legacy_model


def version(config=None,mid=None):
    cfg,h=configuration_snapshot(config or catalog_config())
    return {'id':str(mid or uuid4()),'config_jsonb':cfg,'config_hash':h,'contract_registry_version':'SAGA10_DOMAIN_V2'}

def csv_bytes(contract,rows):
    s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=[f.public_header for f in contract.fields],lineterminator='\n');w.writeheader();w.writerows(rows);return s.getvalue().encode()

def sample_rows(contract):return list(csv.DictReader(io.StringIO(template_csv(contract).decode())))
def normalized(raw,contract):return json.loads(normalize_input(raw,contract)['bytes'])['records']

class Saga10ContractTests(unittest.TestCase):
    def setUp(self):self.v=version();self.contracts={e:compile_contract(self.v,e) for e in entities_for(self.v)}
    def single_order(self):
        c=self.contracts['transport_demand'];return normalized(csv_bytes(c,sample_rows(c)[:1]),c)
    def lines(self,items=None):
        c=self.contracts['order_lines'];rows=items or [{'order_id':'ORD-001','presentation_id':p,'quantity':q} for p,q in [('PAL-JUICE','5'),('PAL-WATER','4'),('PAL-SODA','3')]]
        return normalized(csv_bytes(c,rows),c)
    def rejected(self,contract,rows,code=None):
        with self.assertRaises(InputValidationError) as cm:normalize_input(csv_bytes(contract,rows),contract)
        if code:self.assertEqual(cm.exception.report['errors'][0]['code'],code)
    def test_legacy_compiler_and_normalizer_keep_two_entities(self):
        v=legacy_model();self.assertEqual(entities_for(v),ENTITIES)
        with self.assertRaises(ValueError):compile_contract(v,'transport_demand',registry_version='')
        for e in ENTITIES:
            c=compile_contract(v,e);n=normalize_input(template_csv(c),c);self.assertEqual(n['record_count'],5)
            self.assertEqual(json.loads(n['bytes'])['normalizer_version'],'DATION_INPUT_NORMALIZER_V1');self.assertNotIn('catalog_hash',json.loads(n['bytes']))
    def test_direct_v2_same_headers_and_no_product_file(self):
        v=version(direct_config());self.assertEqual(entities_for(v),ENTITIES)
        for e in ENTITIES:
            c=compile_contract(v,e);old=compile_contract(legacy_model(),e)
            self.assertEqual([f.public_header for f in c.fields],[f.public_header for f in old.fields]);self.assertEqual(normalize_input(template_csv(c),c)['record_count'],5)
        with self.assertRaises(ValueError):compile_contract(v,'order_lines')
    def test_catalog_exact_three_files_and_templates_roundtrip(self):
        self.assertEqual(set(self.contracts),{'transport_demand','order_lines','transport_resources'})
        self.assertEqual([f.public_header for f in self.contracts['order_lines'].fields],['order_id','presentation_id','quantity'])
        self.assertFalse(any(f.public_header.startswith('demand_') for f in self.contracts['transport_demand'].fields))
        records={}
        for e,c in self.contracts.items():
            raw=template_csv(c);n=normalize_input(raw,c);records[e]=json.loads(n['bytes'])['records'];self.assertEqual(n['record_count'],5);self.assertTrue(n['report']['valid'])
        self.assertEqual(len(combine_catalog(records,self.contracts['transport_demand'])),5)
    def test_example_A_line_identity_quantity_provenance(self):
        orders=self.single_order();lines=self.lines();items=combine_catalog({'transport_demand':orders,'order_lines':lines},self.contracts['transport_demand'])
        self.assertEqual(len(items),1);d=items[0]['demand'];self.assertEqual((d.requested.pallets,d.requested.weight_kg,d.requested.volume_m3),(12,13140,D('27.24')))
        self.assertEqual(len({l['line_id'] for l in items[0]['lines']}),3);self.assertEqual({l['quantity'] for l in items[0]['lines']},{D(3),D(4),D(5)})
    def test_duplicate_pairs_ids_missing_orders_and_lines(self):
        c=self.contracts['order_lines'];rows=sample_rows(c)[:1];self.rejected(c,rows*2,'DUPLICATE_LINE')
        c=self.contracts['transport_demand'];rows=sample_rows(c)[:1];self.rejected(c,rows*2,'DUPLICATE_ID')
        for data,code in [({'transport_demand':self.single_order()},'INCOMPLETE_ORDER_LINES'),({'order_lines':self.lines()},'INCOMPLETE_ORDER_LINES'),({'transport_demand':self.single_order(),'order_lines':[]},'ORDER_WITHOUT_LINES')]:
            with self.assertRaises(InputValidationError) as cm:combine_catalog(data,self.contracts['transport_demand'])
            self.assertEqual(cm.exception.report['errors'][0]['code'],code)
        lines=self.lines([{'order_id':'OTHER','presentation_id':'PAL-JUICE','quantity':'1'}])
        with self.assertRaises(InputValidationError) as cm:combine_catalog({'transport_demand':self.single_order(),'order_lines':lines},self.contracts['transport_demand'])
        self.assertEqual(cm.exception.report['errors'][0]['code'],'ORPHAN_LINE')
    def test_unknown_catalog_and_fractional_discrete_quantities(self):
        c=self.contracts['order_lines']
        for pid,q,code in [('UNKNOWN','1','UNKNOWN_PRESENTATION'),('PAL-JUICE','1.5','INVALID_VALUE'),('PAL-JUICE','NaN','INVALID_VALUE'),('PAL-JUICE','-1','INVALID_VALUE'),('PAL-JUICE','0','INVALID_VALUE')]:
            self.rejected(c,[{'order_id':'ORD-001','presentation_id':pid,'quantity':q}],code)
    def test_schema_and_numeric_types_are_exact(self):
        c=self.contracts['order_lines']
        for raw in [b'order_id,presentation_id,quantity,demand_weight_kg\nORD-001,PAL-JUICE,1,100\n',b'order_id,order_id,quantity\nORD-001,PAL-JUICE,1\n',b'order_id,presentation_id,quantity\n',b'order_id,presentation_id,quantity\nORD-001,PAL-JUICE,1,extra\n',b'\xff\xff']:
            with self.assertRaises(InputValidationError):normalize_input(raw,c)
        self.rejected(c,[{'order_id':'=FORMULA','presentation_id':'PAL-JUICE','quantity':'1'}],'INVALID_VALUE')
    def test_permutation_canonical_hash_and_cross_snapshot_reference(self):
        c=self.contracts['order_lines'];rows=[{'order_id':'ORD-001','presentation_id':p,'quantity':'1'} for p in ['PAL-JUICE','PAL-WATER','PAL-SODA']]
        a=normalize_input(csv_bytes(c,rows),c);b=normalize_input(csv_bytes(c,list(reversed(rows))),c)
        self.assertEqual(a['canonical_sha256'],b['canonical_sha256']);self.assertNotEqual(a['raw_sha256'],b['raw_sha256'])
        other=compile_contract(version(),'transport_demand')
        with self.assertRaises(InputValidationError) as cm:combine_catalog({'transport_demand':self.single_order(),'order_lines':json.loads(a['bytes'])['records']},other)
        self.assertEqual(cm.exception.report['errors'][0]['code'],'LINE_IDENTITY')
    def test_direct_counts_are_integral_and_model_split_is_not_overridden(self):
        v=version(direct_config());c=compile_contract(v,'transport_demand');rows=sample_rows(c)[:1];rows[0]['demand_pallets']='1.5';self.rejected(c,rows,'DISCRETE_QUANTITY')
        c=self.contracts['transport_demand'];rows=sample_rows(c)[:1];rows[0]['delivery_due_date']='2020-01-01';self.rejected(c,rows,'INVALID_VALUE')
        c=compile_contract(version(direct_config()),'transport_demand');rows=sample_rows(c)[:1];rows[0]['split_allowed']='true';self.rejected(c,rows,'DOMAIN_CONTRACT')
    def test_bulk_quantity_unit_and_explicit_increment(self):
        v=version(bulk_config());c=compile_contract(v,'order_lines');rows=[{'order_id':'ORD-001','presentation_id':'BULK','quantity':'.125'}]
        line=normalized(csv_bytes(c,rows),c)[0];self.assertEqual(line['quantity'],'0.125')
        c=compile_contract(version(bulk_config('1500','kg')),'order_lines');self.rejected(c,[{'order_id':'ORD-001','presentation_id':'BULK','quantity':'.5'}],'INVALID_VALUE')
    def test_resource_category_is_compiled_validated_and_preserved(self):
        cfg=catalog_config();cfg['resource_categories']=['REFRIGERATED'];c=compile_contract(version(cfg),'transport_resources')
        rows=sample_rows(c);result=normalized(csv_bytes(c,rows),c);self.assertTrue(all(r['resource_category']=='REFRIGERATED' for r in result))
        rows[0]['resource_category']='OPEN';self.rejected(c,rows,'INVALID_VALUE')
    def test_solver_limits_are_separate_from_csv_validity(self):
        dc=self.contracts['transport_demand'];lc=self.contracts['order_lines'];orders=[];lines=[];sample=sample_rows(dc)[0]
        for i in range(501):
            oid='ORDER-'+str(i);orders.append({**sample,'order_id':oid});lines.append({'order_id':oid,'presentation_id':'PAL-JUICE','quantity':'1'})
        records={'transport_demand':normalized(csv_bytes(dc,orders),dc),'order_lines':normalized(csv_bytes(lc,lines),lc)}
        self.assertEqual(len(combine_catalog(records,dc)),501)
        with self.assertRaises(InputValidationError) as cm:combine_catalog(records,dc,solver_limits=True)
        self.assertEqual(cm.exception.report['errors'][0]['code'],'SOLVER_ROW_LIMIT')
    def test_csv_limit_stops_incrementally_without_materializing_unbounded_rows(self):
        c=self.contracts['order_lines'];raw=b'order_id,presentation_id,quantity\n'+b'ORD-001,PAL-JUICE,1\n'*10001
        with self.assertRaises(InputValidationError) as cm:normalize_input(raw,c)
        self.assertEqual(cm.exception.report['errors'][0]['code'],'ROW_LIMIT')
        with self.assertRaises(InputValidationError):normalize_input(b'order_id,presentation_id,quantity\n"unterminated',c)
