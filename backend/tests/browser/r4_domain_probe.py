"""Read JSON from stdin; finite local D1/DC proofs using the unchanged runtime."""
import json,sys
from copy import deepcopy
from decimal import Decimal as D
from app.domain.logistics.physical import normalize_catalog
from app.domain.logistics.data_contracts import compile_contract,entities_for,template_csv
from app.domain.logistics.normalizers import normalize_input
from app.domain.logistics.normalizers_v2 import combine_catalog
from tests.test_saga10_data_contracts import version,csv_bytes,sample_rows,normalized
from tests.saga10_fixtures import cargo_request
from tests.test_transport_plan_core import resource
from app.engines.assignment.cargo_inputs import run_cargo_policy

def check(cfg):
 cfg=deepcopy(cfg);cargo=cfg['cargo'];pids=[p['presentation_id'] for p in cargo['presentations']];groups=[p['compatibility_groups'][0] for p in cargo['products']]
 physical=normalize_catalog(cargo,cfg['active_dimensions']);assert [(p.coefficients.weight_kg,p.coefficients.volume_m3) for p in physical.values()]==[(D('745'),D('1.8')),(D('665'),D('1.8'))]
 v=version(cfg);assert set(entities_for(v))=={'transport_demand','order_lines','transport_resources'}
 contracts={e:compile_contract(v,e) for e in entities_for(v)}
 for c in contracts.values():assert normalize_input(template_csv(c),c)['report']['valid']
 dc=contracts['transport_demand'];orders=normalized(csv_bytes(dc,sample_rows(dc)[:1]),dc);oid=orders[0]['order_id']
 lc=contracts['order_lines'];lines=normalized(csv_bytes(lc,[{'order_id':oid,'presentation_id':pids[0],'quantity':'10'},{'order_id':oid,'presentation_id':pids[1],'quantity':'6'}]),lc)
 combined=combine_catalog({'transport_demand':orders,'order_lines':lines},dc);assert combined[0]['demand'].requested.weight_kg==11440;assert combined[0]['demand'].requested.volume_m3==D('28.8')
 def truck(count=2):return resource(services=count,guaranteed_capacity={'weight_kg':'4470','volume_m3':'10.8'},compatibility_groups=groups)
 def solve(configuration,spec,resources=None):return run_cargo_policy(cargo_request(configuration,spec,resources or [truck()]),alternative_budget=0).recommended.output.core
 cfg['split_permitted']=False;cargo['split_policy']='INDIVISIBLE';indiv=solve(cfg,[('TEN',[(pids[0],'10')],False)]);assert not indiv.transport_plan.trips
 cfg['split_permitted']=True;cargo['split_policy']='DISCRETE';discrete=solve(cfg,[('TEN',[(pids[0],'10')],True)]);assert sorted(a.quantity for a in discrete.transport_plan.cargo.allocations)==[4,6]
 forbidden=solve(cfg,[('TEN',[(pids[0],'10')],False)]);assert not forbidden.transport_plan.trips
 # Distinct stable groups are conservative: split can separate the two types;
 # an indivisible mixed order cannot be served without explicit compatibility.
 cargo['split_policy']='INDIVISIBLE';cfg['split_permitted']=False
 mixed=solve(cfg,[('MIX',[(pids[0],'1'),(pids[1],'1')],False)]);assert not mixed.transport_plan.trips
 cfg['split_permitted']=True;cargo['split_policy']='DISCRETE'
 mixed_split=solve(cfg,[('MIX',[(pids[0],'1'),(pids[1],'1')],True)]);assert len(mixed_split.transport_plan.trips)==2
 separate=solve(cfg,[('W',[(pids[0],'1')],False),('O',[(pids[1],'1')],False)]);assert len(separate.transport_plan.trips)==2
 allowed=deepcopy(cfg);allowed['cargo']['co_load_pairs']=[groups]
 explicit=solve(allowed,[('MIX',[(pids[0],'1'),(pids[1],'1')],False)]);assert len(explicit.transport_plan.trips)==1
 same=deepcopy(cfg);same['cargo']['products'][1]['compatibility_groups']=[groups[0]];assert len(solve(same,[('MIX',[(pids[0],'1'),(pids[1],'1')],False)]).transport_plan.trips)==1
 absent=deepcopy(cfg);absent['cargo']['products'][1]['compatibility_groups']=[]
 try:version(absent)
 except ValueError:pass
 else:raise AssertionError('Missing categorized group accepted')
 return {'physics':['745 kg / 1.8 m3','665 kg / 1.8 m3'],'csv':list(contracts),'mixed_aggregate':['11440 kg','28.8 m3'],'indivisible':'unserved','discrete_quantities':[str(a.quantity) for a in discrete.transport_plan.cargo.allocations],'order_split_false':'unserved','distinct_types_same_order_indivisible':'unserved','distinct_types_discrete':'two trips','separate_orders':'two trips','explicit_pair':'one trip','same_group':'one trip','missing_group':'rejected','production_execution':False}
if __name__=='__main__':print(json.dumps(check(json.load(sys.stdin)),indent=2))
