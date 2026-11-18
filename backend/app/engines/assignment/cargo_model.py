"""Bounded v2 CP-SAT: integer physical quanta, unchanged business objectives."""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from math import gcd,lcm
import hashlib
import ortools
from ortools.sat.python import cp_model
from app.domain.logistics.base import Priority
from app.domain.logistics.units import scaled_integer,QUANTITY_SCALES
from app.domain.logistics.physical import normalize_catalog
from app.results.canonical import canonical_bytes
from app.engines.common.day_resource_feasibility import dispatch_window
from .transport_model import Slot,compatible,quantities

class CargoSearchLimit(ValueError):
    code='SAGA10_SEARCH_LIMIT'

@dataclass(frozen=True)
class Quantum:
    order_index: int
    line_id: str | None
    presentation_id: str | None
    count: int
    step: Decimal | None
    coefficients: dict
    groups: tuple


def quanta(request,orders):
    cfg=request.model.configuration;dims=request.model.active_dimensions
    catalog=normalize_catalog(cfg.cargo,dims);out={}
    for i,order in enumerate(orders):
        if cfg.cargo.input_mode=='catalog':
            for line in sorted(order.lines,key=lambda l:l.line_id):
                p=catalog[line.presentation_id];step=p.allocation_increment;coefs={}
                for d in dims:
                    value=Decimal(scaled_integer(getattr(p.coefficients,d),QUANTITY_SCALES[d]))*step
                    if value!=value.to_integral_value():raise ValueError('El incremento no conserva la precisión física.')
                    coefs[d]=int(value)
                out[i,line.line_id]=Quantum(i,line.line_id,line.presentation_id,int(line.quantity/step),step,coefs,line.compatibility_groups)
        else:
            denominator,unit=quantities(order,dims);factor=1
            for d in ('pallets','units'):
                if d in dims:factor=lcm(factor,1000//gcd(unit[d],1000))
            if denominator%factor:raise ValueError('El vector directo no admite objetos enteros a esta precisión.')
            out[i,'direct']=Quantum(i,None,None,denominator//factor,None,{d:v*factor for d,v in unit.items()},order.compatibility_groups)
    return out


def solve_cargo(request,policy_search=None):
    cfg=request.model.configuration;dims=request.model.active_dimensions;options=request.options
    orders=sorted(request.demands,key=lambda o:o.order_id);resources=sorted(request.resources,key=lambda r:r.resource_id)
    line_quanta=quanta(request,orders);model=cp_model.CpModel();groups=defaultdict(list)
    for i,o in enumerate(orders):groups[o.origin_id,o.destination_id,o.distance_km].append(i)
    denominator={i:(scaled_integer(getattr(o.requested,request.model.primary_dimension),QUANTITY_SCALES[request.model.primary_dimension]),
        {d:int(d==request.model.primary_dimension) for d in dims}) for i,o in enumerate(orders)}
    by_order=defaultdict(list);by_resource=defaultdict(list);intervals=defaultdict(list);slots=[]
    by_quantum=defaultdict(list);by_order_presence=defaultdict(list);canonical_limits=set()
    days=(request.context.planning_end-request.context.planning_start).days+1
    def within_budget():
        if len(model.proto.variables)>options.max_variables or len(model.proto.constraints)>options.max_variables*8:
            raise CargoSearchLimit('El modelo v2 supera el presupuesto de variables/restricciones; reducí órdenes, líneas, grupos o disponibilidades.')
    for resource in resources:
        if resource.source not in request.model.allowed_sources:continue
        available=resource.units_available if resource.source=='OWN' else resource.services_available
        if not available:continue
        for route,indices in sorted(groups.items()):
            eligible={};windows={}
            caps={d:scaled_integer(getattr(resource.guaranteed_capacity,d),QUANTITY_SCALES[d]) for d in dims}
            for i in indices:
                o=orders[i]
                if not compatible(o,resource,request.model):continue
                first,last,_=dispatch_window(o,resource,request.context)
                if first>last:continue
                split=o.split_allowed and request.model.split_permitted
                if not split and any(getattr(o.requested,d)>getattr(resource.guaranteed_capacity,d) for d in dims):continue
                choices={key:q for key,q in line_quanta.items() if key[0]==i and (set(q.groups).issubset(resource.compatibility_groups) if q.groups else request.model.homogeneous_loads_declared) and all(q.coefficients[d]<=caps[d] for d in dims)}
                all_lines=sum(key[0]==i for key in line_quanta)
                if not choices or not split and len(choices)!=all_lines:continue
                eligible.update(choices);windows[i]=(first,last)
            if not eligible:continue
            # Any nonempty Trip contains >=1 integral quantum; indivisible
            # orders need only one Trip each. This is a proved finite upper bound.
            bound=sum(q.count for key,q in eligible.items() if orders[key[0]].split_allowed and request.model.split_permitted)+sum(not(orders[i].split_allowed and request.model.split_permitted) for i in windows)
            count=min(available*(days if resource.source=='OWN' else 1),bound)
            if len(slots)+count>options.max_slots:raise CargoSearchLimit('El conjunto completo de candidatos v2 supera el límite de Trips; reducí disponibilidades o el horizonte del piloto.')
            for _ in range(count):
                index=len(slots);present=model.new_bool_var('cargo_trip_'+str(index));start=model.new_int_var(request.context.planning_start.toordinal(),request.context.planning_end.toordinal(),'cargo_start_'+str(index))
                variables={};has={};primary={};order_has={}
                for key,q in sorted(eligible.items()):
                    x=model.new_int_var(0,q.count,f'line_{index}_{key[0]}_{key[1]}');b=model.new_bool_var(f'has_{index}_{key[0]}_{key[1]}')
                    model.add(x>=b);model.add(x<=q.count*b);model.add(b<=present)
                    variables[key]=x;has[key]=b;by_quantum[key].append(x)
                for i in sorted(windows):
                    chosen=[has[key] for key in variables if key[0]==i]
                    b=model.new_bool_var(f'order_{index}_{i}');model.add_max_equality(b,chosen);order_has[i]=b;by_order_presence[i].append(b)
                    if not(orders[i].split_allowed and request.model.split_permitted):
                        for key,x in variables.items():
                            if key[0]==i:model.add(x==eligible[key].count*b)
                    first,last=windows[i];model.add(start>=first).only_enforce_if(b);model.add(start<=last).only_enforce_if(b)
                    x=model.new_int_var(0,denominator[i][0],f'primary_{index}_{i}')
                    model.add(x==sum(eligible[key].coefficients[request.model.primary_dimension]*v for key,v in variables.items() if key[0]==i))
                    minimum=max(1,(denominator[i][0]+1999999)//2000000)
                    model.add(x>=minimum*b)
                    if any(q.coefficients[request.model.primary_dimension]<minimum for key,q in eligible.items() if key[0]==i):canonical_limits.add('CARGO_FRACTION_DISPLAY_LIMIT')
                    primary[i]=x;by_order[i].append(x)
                model.add(sum(order_has.values())>=present)
                if not cfg.consolidation_permitted:model.add(sum(order_has.values())<=1)
                if cfg.cargo.compatibility_policy=='CATEGORIZED':
                    categories=defaultdict(list)
                    for key,b in has.items():categories[eligible[key].groups].append(b)
                    group_has={}
                    for n,(tags,items) in enumerate(sorted(categories.items())):
                        b=model.new_bool_var(f'category_{index}_{n}');model.add_max_equality(b,items);group_has[tags]=b
                    items=list(group_has.items())
                    for a,(left,lb) in enumerate(items):
                        for right,rb in items[a+1:]:
                            if not cfg.cargo.can_co_load(left,right):model.add(lb+rb<=1)
                for d in dims:model.add(sum(eligible[key].coefficients[d]*x for key,x in variables.items())<=caps[d]*present)
                slot=Slot(resource,tuple(sorted(windows)),present,start,primary,route[2],variables,dict(eligible),None);slots.append(slot)
                by_resource[resource.resource_id].append(present)
                if resource.source=='OWN':
                    cycle=dispatch_window(orders[min(windows)],resource,request.context)[2].cycle_days
                    intervals[resource.resource_id].append(model.new_optional_fixed_size_interval_var(start,cycle,present,'cycle_'+str(index)))
                within_budget()
    for key,q in line_quanta.items():model.add(sum(by_quantum[key])<=q.count)
    for i,order in enumerate(orders):
        model.add(sum(by_order[i])<=denominator[i][0])
        if not(order.split_allowed and request.model.split_permitted):model.add(sum(by_order_presence[i])<=1)
    for resource in resources:
        if resource.source=='EXTERNAL' and by_resource[resource.resource_id]:model.add(sum(by_resource[resource.resource_id])<=resource.services_available)
        elif intervals[resource.resource_id]:model.add_cumulative(intervals[resource.resource_id],[1]*len(intervals[resource.resource_id]),min(resource.units_available,len(intervals[resource.resource_id])))
    within_budget()
    if model.validate():raise ValueError('Modelo físico v2 inválido: '+model.validate())
    if policy_search is not None:
        selected,statuses,limits=policy_search.optimize(model,slots,orders,denominator,by_order)
    else:
        solver=cp_model.CpSolver();solver.parameters.num_search_workers=1;solver.parameters.random_seed=options.seed
        solver.parameters.max_deterministic_time=options.deterministic_budget/3;solver.parameters.max_time_in_seconds=10
        selected=None;statuses=[];limits=[]
        for priority in Priority:
            objective=sum(x for i,o in enumerate(orders) if o.priority==priority for x in by_order[i]);model.maximize(objective);status=solver.solve(model);native=solver.status_name(status);statuses.append(native)
            if status not in (cp_model.FEASIBLE,cp_model.OPTIMAL):break
            selected=[{i:solver.value(x) for i,x in slot.fractions.items()} if solver.value(slot.present) else {} for slot in slots]
            for slot in slots:slot.line_values={key:solver.value(x) for key,x in slot.line_variables.items()} if solver.value(slot.present) else {}
            if status!=cp_model.OPTIMAL:limits.append('CARGO_COVERAGE_UNPROVEN');break
            if not isinstance(objective,int):model.add(objective==solver.value(objective))
    limits=sorted(set(limits)|canonical_limits)
    return orders,denominator,slots,selected,{'version':'D1_CARGO_POLICY_V2' if policy_search else 'D1_CARGO_STRUCTURAL_V2','native_statuses':tuple(statuses),'solver_version':ortools.__version__,
        'seed':options.seed,'candidate_slots':len(slots),'variable_count':len(model.proto.variables),'candidate_set_complete':policy_search is not None and not limits,
        'limits':tuple(limits),'model_sha256':hashlib.sha256(str(model.proto).encode()).hexdigest(),'structural_input_sha256':hashlib.sha256(canonical_bytes({'model':request.model,'context':request.context,'demands':orders,'resources':resources,'options':options})).hexdigest(),'options':options}
