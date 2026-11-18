"""Twelve industrial challenges: exact supported outcomes or schema rejection."""
from copy import deepcopy
from decimal import Decimal as D
import unittest
from pydantic import ValidationError
from app.models.ultimate_foundation import parse_configuration
from app.engines.assignment.cargo_inputs import run_cargo_policy
from tests.saga10_fixtures import cargo_request,catalog_config,direct_config,bulk_config
from tests.test_saga10_assignment import truck
from tests.test_transport_plan_core import resource,order


def solve(req):return run_cargo_policy(req,alternative_budget=0).recommended.output.core

def boxed(name='Tornillos',mass='.01',pieces='100',tare='.1'):
    cfg=direct_config(active_dimensions=['units','weight_kg'],primary_dimension='units',split_permitted=True,homogeneous_loads_declared=True)
    cfg['cargo']={'input_mode':'catalog','profile':'PACKAGED','split_policy':'DISCRETE','compatibility_policy':'UNIFORM_DECLARED',
        'products':[{'product_id':'P','name':name,'unit_label':'pieza','gross_mass':{'value':mass,'unit':'kg'}}],
        'logistic_units':[{'logistic_unit_id':'BOX','label':'Caja reutilizable','type':'BOX','tare_mass':{'value':tare,'unit':'kg'}}],
        'presentations':[{'presentation_id':'BOX-P','label':name+' en caja','logistic_unit_id':'BOX','components':[{'product_id':'P','quantity':pieces}]}]}
    return cfg


class Saga10IndustryTests(unittest.TestCase):
    def test_01_juice_factory_shared_unit_distinct_loaded_height(self):
        cfg=catalog_config();self.assertEqual(len(cfg['cargo']['logistic_units']),1)
        core=solve(cargo_request(cfg));self.assertEqual(core.metrics.demand_coverage.assigned,12)
        self.assertEqual(sum(t.total_load.weight_kg for t in core.transport_plan.trips),13140)
        self.assertEqual({a.presentation_label for a in core.transport_plan.cargo.allocations},{'Jugo palletizado','Agua palletizado','Gaseosa palletizado'})
    def test_02_screws_integer_boxes_and_weight(self):
        core=solve(cargo_request(boxed(),[('O',[('BOX-P','3')],True)],[resource(guaranteed_capacity={'units':'250','weight_kg':'20'},services=1)]))
        self.assertEqual(core.metrics.demand_coverage.assigned,200);self.assertEqual(core.transport_plan.cargo.lines[0].unserved,1)
        self.assertEqual(core.transport_plan.trips[0].total_load.weight_kg,D('2.2'))
    def test_03_soda_prebuilt_mixed_crate_multiple_presentations(self):
        cfg=boxed('Gaseosa','1','6','2');cfg['active_dimensions']=['units','weight_kg','volume_m3']
        cargo=cfg['cargo'];cargo['logistic_units'][0]['type']='CRATE';cargo['products'].append({'product_id':'W','name':'Agua','unit_label':'botella','gross_mass':{'value':'1.5','unit':'kg'}})
        cargo['presentations'][0].update(external_volume={'value':'.05','unit':'m3'},components=[{'product_id':'P','quantity':'6'},{'product_id':'W','quantity':'6'}])
        cargo['presentations'].append({'presentation_id':'SMALL','label':'Gaseosa seis botellas','logistic_unit_id':'BOX','components':[{'product_id':'P','quantity':'6'}],'external_volume':{'value':'.03','unit':'m3'}})
        core=solve(cargo_request(cfg,[('O',[('BOX-P','2'),('SMALL','1')],True)],[resource(guaranteed_capacity={'units':'100','weight_kg':'100','volume_m3':'1'},services=1)]))
        self.assertEqual(core.metrics.demand_coverage.assigned,30);self.assertEqual(core.transport_plan.trips[0].total_load.weight_kg,42)
        self.assertEqual(len(core.transport_plan.cargo.allocations),2)
    def test_04_sand_continuous_density_and_three_trips(self):
        cfg=bulk_config('1600');cfg['cargo']['profile']='DRY_BULK'
        core=solve(cargo_request(cfg,[('SAND',[('BULK','25')],True)],[resource(guaranteed_capacity={'weight_kg':'16000','volume_m3':'10'},services=3)]))
        self.assertEqual(core.metrics.demand_coverage.assigned,25);self.assertEqual(core.metrics.trip_count,3)
        self.assertEqual(sum(t.total_load.weight_kg for t in core.transport_plan.trips),40000)
    def test_05_cement_weight_dominates_pallet_count(self):
        cfg=catalog_config();cfg['cargo']['products']=cfg['cargo']['products'][:1];p=cfg['cargo']['products'][0];p.update(name='Cemento',units_per_package=1,gross_mass={'value':'50','unit':'kg'})
        cfg['cargo']['presentations']=cfg['cargo']['presentations'][:1];p=cfg['cargo']['presentations'][0];p['components'][0]['quantity']='40';p.pop('gross_mass')
        core=solve(cargo_request(cfg,[('C',[('PAL-JUICE','6')],True)],[truck(weight='12000')]))
        self.assertEqual(core.metrics.demand_coverage.assigned,5);self.assertEqual(core.transport_plan.trips[0].total_load.weight_kg,10125)
    def test_06_oil_tanker_category_and_explicit_hazmat_limit(self):
        cfg=bulk_config();cfg['resource_categories']=['TANKER']
        fleet=resource(resource_category='TANKER',guaranteed_capacity={'weight_kg':'17000','volume_m3':'20'},services=1)
        self.assertEqual(solve(cargo_request(cfg,[('OIL',[('BULK','20')],True)],[fleet])).metrics.demand_coverage.assigned,20)
        invalid=deepcopy(cfg);invalid['cargo']['hazmat_certified']=True
        with self.assertRaises(ValidationError):parse_configuration(invalid)
        with self.assertRaises(ValidationError):cargo_request(cfg,[('OIL',[('BULK','20')],True)],[{**fleet,'resource_category':'GENERAL'}])
    def test_07_mining_lane_restriction_and_no_invented_cycle(self):
        cfg=bulk_config('1800');cfg['cargo']['profile']='DRY_BULK'
        core=solve(cargo_request(cfg,[('M',[('BULK','2')],True)],[resource(guaranteed_capacity={'weight_kg':'18000','volume_m3':'10'},services=1,lanes=[['A','C']])]))
        self.assertEqual(core.metrics.demand_coverage.assigned,0);self.assertFalse(core.transport_plan.trips)
        self.assertIn('NO_COMPATIBLE_RESOURCE',set(core.transport_plan.unassigned_demand[0].reason_codes))
        invalid=deepcopy(cfg);invalid['mining_cycle_hours']='3'
        with self.assertRaises(ValidationError):parse_configuration(invalid)
    def test_08_grain_explicit_commodity_coload(self):
        cfg=bulk_config('750');cfg['cargo'].update(profile='DRY_BULK',compatibility_policy='CATEGORIZED');cfg['homogeneous_loads_declared']=False
        cfg['cargo']['products'][0]['compatibility_groups']=['WHEAT'];other=deepcopy(cfg['cargo']['products'][0]);other.update(product_id='BARLEY',name='Cebada',compatibility_groups=['BARLEY']);cfg['cargo']['products'].append(other)
        other=deepcopy(cfg['cargo']['presentations'][0]);other.update(presentation_id='BULK-B',label='Cebada a granel',components=[{'product_id':'BARLEY','quantity':'1'}]);cfg['cargo']['presentations'].append(other)
        core=solve(cargo_request(cfg,[('W',[('BULK','5')],True),('B',[('BULK-B','5')],True)],[resource(guaranteed_capacity={'weight_kg':'15000','volume_m3':'20'},services=2,compatibility_groups=['WHEAT','BARLEY'])]))
        self.assertEqual(core.metrics.demand_coverage.assigned,10);self.assertEqual(core.metrics.trip_count,2)
    def test_09_cold_chain_declared_matching_without_temperature_claim(self):
        cfg=catalog_config();cfg['resource_categories']=['REFRIGERATED'];cfg['homogeneous_loads_declared']=False;cfg['cargo']['compatibility_policy']='CATEGORIZED'
        for p in cfg['cargo']['products']:p['compatibility_groups']=['COLD']
        core=solve(cargo_request(cfg,resources=[truck(resource_category='REFRIGERATED',compatibility_groups=['COLD'])]));self.assertEqual(core.metrics.demand_coverage.assigned,12)
        core=solve(cargo_request(cfg,resources=[truck(resource_category='REFRIGERATED',compatibility_groups=['DRY'])]));self.assertEqual(core.metrics.demand_coverage.assigned,0)
        invalid=deepcopy(cfg);invalid['cargo']['temperature_controlled']=True
        with self.assertRaises(ValidationError):parse_configuration(invalid)
    def test_10_steel_whole_order_no_geometry_claim(self):
        cfg=boxed('Acero','300','1','0');cfg['split_permitted']=False;cfg['cargo']['split_policy']='INDIVISIBLE'
        for cap,expected in [('2',0),('3',3)]:
            core=solve(cargo_request(cfg,[('STEEL',[('BOX-P','3')],False)],[resource(guaranteed_capacity={'units':cap,'weight_kg':'1000'},services=2)]));self.assertEqual(core.metrics.demand_coverage.assigned,expected)
        invalid=deepcopy(cfg);invalid['cargo']['securement_guarantee']=True
        with self.assertRaises(ValidationError):parse_configuration(invalid)
    def test_11_concrete_hourly_requirement_is_rejected_not_optimized(self):
        req=cargo_request(bulk_config('2400'),[('CONCRETE',[('BULK','1')],True)],[resource(guaranteed_capacity={'weight_kg':'24000','volume_m3':'10'},services=1)]).model_dump()
        req['demands'][0]['delivery_due_date']='2026-11-02T10:30:00Z'
        from app.engines.assignment.transport_contracts import TransportPlanInput
        with self.assertRaises(ValidationError):TransportPlanInput.model_validate(req)
    def test_12_ecommerce_direct_only_multistop_rejected(self):
        cfg=boxed('Paquetes','1','1','0');self.assertEqual(solve(cargo_request(cfg,[('E',[('BOX-P','5')],True)],[resource(guaranteed_capacity={'units':'5','weight_kg':'10'},services=1)])).metrics.demand_coverage.assigned,5)
        cfg['transport_pattern']='MULTI_STOP'
        with self.assertRaises(ValidationError):parse_configuration(cfg)
    def test_13_literal_26_pallet_12t_cannot_hold_indivisible_14t_order(self):
        cfg=direct_config(active_dimensions=['pallets','weight_kg'],homogeneous_loads_declared=True,cargo={'input_mode':'direct','split_policy':'INDIVISIBLE','compatibility_policy':'UNIFORM_DECLARED'})
        core=solve(cargo_request(cfg,[order('HEAVY',split=False,requested={'pallets':'12','weight_kg':'14000'})],[resource(guaranteed_capacity={'pallets':'26','weight_kg':'12000'},services=1)]))
        self.assertEqual(core.metrics.demand_coverage.assigned,0)
