"""Bounded structural CP-SAT model. No monetary goal or public schedule.

One x quantum transports an exact proportional vector. The denominator is the
GCD of the T1 scaled quantities, not a primary-dimension capacity shortcut.
"""
from collections import defaultdict
from dataclasses import dataclass
from functools import reduce
from math import gcd, lcm
import hashlib

from ortools.sat.python import cp_model
import ortools

from app.domain.logistics.base import Priority
from app.domain.logistics.units import QUANTITY_SCALES, scaled_integer
from app.results.canonical import canonical_bytes
from app.engines.common.day_resource_feasibility import dispatch_window


def compatible(order, resource, model):
    if resource.source not in model.allowed_sources:
        return False
    if (order.origin_id, order.destination_id) not in resource.lanes:
        return False
    if resource.source == 'OWN' and resource.base_origin_id != order.origin_id:
        return False
    if order.compatibility_groups:
        return set(order.compatibility_groups).issubset(resource.compatibility_groups)
    return model.homogeneous_loads_declared


def quantities(order, dimensions):
    values = {d:scaled_integer(getattr(order.requested,d), QUANTITY_SCALES[d]) for d in dimensions}
    denominator = reduce(gcd, values.values())
    return denominator, {d:v//denominator for d,v in values.items()}


@dataclass
class Slot:
    resource: object
    indices: tuple
    present: object
    start: object
    fractions: dict
    distance: object


def solve_structural(request, policy_search=None):
    orders = sorted(request.demands, key=lambda o:o.order_id)
    resources = sorted(request.resources, key=lambda r:r.resource_id)
    dims, options = request.model.active_dimensions, request.options
    model = cp_model.CpModel()
    groups = defaultdict(list)
    for i,o in enumerate(orders):
        groups[(o.origin_id,o.destination_id,o.distance_km,tuple(sorted(o.compatibility_groups)))].append(i)
    denominators = {i:quantities(o,dims) for i,o in enumerate(orders)}
    slots, by_order, by_resource, intervals = [], defaultdict(list), defaultdict(list), defaultdict(list)
    limits = set()
    variables = 0
    days = (request.context.planning_end-request.context.planning_start).days+1
    for resource in resources:
        if resource.source not in request.model.allowed_sources:
            continue
        available = resource.units_available if resource.source == 'OWN' else resource.services_available
        if not available:
            continue
        for key, group in sorted(groups.items()):
            eligible = []
            bound = 0
            for i in group:
                order = orders[i]
                if not compatible(order,resource,request.model):
                    continue
                first,last,_ = dispatch_window(order,resource,request.context)
                if first > last:
                    continue
                ratios = [(getattr(order.requested,d),getattr(resource.guaranteed_capacity,d)) for d in dims]
                non_split = not (order.split_allowed and request.model.split_permitted)
                if non_split and any(q>c for q,c in ratios):
                    continue
                eligible.append(i)
                # Exact integer ceil of the largest vector load/capacity ratio.
                bound += max((scaled_integer(q,QUANTITY_SCALES[d])+scaled_integer(c,QUANTITY_SCALES[d])-1)//scaled_integer(c,QUANTITY_SCALES[d]) for d,(q,c) in zip(dims,ratios))
            if not eligible:
                continue
            count = available*(days if resource.source == 'OWN' else 1)
            if policy_search is None:
                count = min(bound,count)
            for _ in range(count):
                needed = 2 + 2*len(eligible)
                if len(slots) >= options.max_slots or variables+needed > options.max_variables:
                    limits.add('CANDIDATE_MODEL_BUDGET')
                    break
                index = len(slots)
                y = model.new_bool_var('trip_'+str(index))
                start = model.new_int_var(request.context.planning_start.toordinal(), request.context.planning_end.toordinal(),'start_'+str(index))
                fractions, selected = {}, []
                for i in eligible:
                    order = orders[i]
                    denominator, unit = denominators[i]
                    x = model.new_int_var(0,denominator,f'x_{index}_{i}')
                    b = model.new_bool_var(f'has_{index}_{i}')
                    if order.split_allowed and request.model.split_permitted:
                        # A positive allocation must survive six-decimal DTO display.
                        minimum = max(1,(denominator+1999999)//2000000)
                        model.add(x >= minimum*b)
                        model.add(x <= denominator*b)
                    else:
                        model.add(x == denominator*b)
                    model.add(b <= y)
                    first,last,_ = dispatch_window(order,resource,request.context)
                    model.add(start >= first).only_enforce_if(b)
                    model.add(start <= last).only_enforce_if(b)
                    fractions[i] = x
                    by_order[i].append(x)
                    selected.append(b)
                model.add(sum(selected) >= y)
                for d in dims:
                    cap = scaled_integer(getattr(resource.guaranteed_capacity,d),QUANTITY_SCALES[d])
                    model.add(sum(denominators[i][1][d]*fractions[i] for i in eligible) <= cap*y)
                slot = Slot(resource,tuple(eligible),y,start,fractions,key[2])
                slots.append(slot)
                by_resource[resource.resource_id].append(y)
                if resource.source == 'OWN':
                    estimate = dispatch_window(orders[eligible[0]],resource,request.context)[2]
                    intervals[resource.resource_id].append(model.new_optional_fixed_size_interval_var(start,estimate.cycle_days,y,'cycle_'+str(index)))
                variables += needed
    scores = defaultdict(list)
    objective_budget_exceeded = False
    common = {}
    for priority in Priority:
        common[priority] = 1
        for i,o in enumerate(orders):
            if o.priority == priority:
                common[priority] = lcm(common[priority],denominators[i][0])
                if common[priority]*len(orders) > 2**60:
                    objective_budget_exceeded = True
                    break
    for i, order in enumerate(orders):
        denominator = denominators[i][0]
        if by_order[i]:
            model.add(sum(by_order[i]) <= denominator)
        if not objective_budget_exceeded:
            scores[order.priority].extend(x*(common[order.priority]//denominator) for x in by_order[i])
    for resource in resources:
        ys = by_resource[resource.resource_id]
        if resource.source == 'EXTERNAL' and ys:
            model.add(sum(ys) <= resource.services_available)
        if resource.source == 'OWN' and ys:
            model.add_cumulative(intervals[resource.resource_id],[1]*len(ys),min(resource.units_available,len(ys)))
    if model.validate():
        raise RuntimeError('D1 structural model invalid: '+model.validate())
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = options.seed
    solver.parameters.max_deterministic_time = options.deterministic_budget/3
    solver.parameters.max_time_in_seconds = 10
    statuses, selected_values = [], None
    # Only structural priority/coverage. No cost/own/trip/preference objective.
    # T7 must certify the complete business-policy hierarchy separately.
    if objective_budget_exceeded:
        limits.add('RATIONAL_COVERAGE_INTEGER_BUDGET')
        statuses.append('UNKNOWN')
    if policy_search is not None and not objective_budget_exceeded:
        selected_values,statuses,policy_limits=policy_search.optimize(model,slots,orders,denominators,by_order)
        limits.update(policy_limits)
    for priority in (() if objective_budget_exceeded or policy_search is not None else Priority):
        objective = sum(scores[priority])
        model.maximize(objective)
        status = solver.solve(model)
        statuses.append(solver.status_name(status))
        if status == cp_model.MODEL_INVALID:
            raise RuntimeError('Invalid D1 CP-SAT response')
        if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
            if selected_values is None:
                break
            limits.add('LATER_COVERAGE_STAGE_UNPROVEN')
            break
        selected_values = [{i:solver.value(x) for i,x in s.fractions.items()} if solver.value(s.present) else {} for s in slots]
        if status != cp_model.OPTIMAL:
            limits.add('COVERAGE_STAGE_UNPROVEN')
            break
        if scores[priority]:
            model.add(objective == sum(solver.value(s) for s in scores[priority]))
    input_projection = {'model':request.model,'context':request.context,
        'demands':orders,'resources':resources,'options':options}
    return orders, denominators, slots, selected_values, {
        'version':'D1_POLICY_V1' if policy_search is not None else 'D1_STRUCTURAL_FRACTION_COVERAGE_V1',
        'native_statuses':tuple(statuses),'solver_version':ortools.__version__,'seed':options.seed,
        'candidate_slots':len(slots),'variable_count':len(model.proto.variables),
        # Conservative equal compatibility-group partition is deliberately not
        # an exhaustive global candidate-set certificate.
        'candidate_set_complete':policy_search is not None and not limits,'limits':tuple(sorted(limits)),
        'model_sha256':hashlib.sha256(str(model.proto).encode()).hexdigest(),
        'structural_input_sha256':hashlib.sha256(canonical_bytes(input_projection)).hexdigest(),
        'options':options,
    }
