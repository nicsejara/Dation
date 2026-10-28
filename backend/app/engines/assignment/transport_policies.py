"""T7 policy CP extension. Hard bounds precede lexicographic coverage/goals.

Versioned source-share guardrails use the T1 trip-based resource_mix. Coverage
uses the primary quantity, critical=HIGH; zero denominators are vacuous bounds
and remain NULL in metrics. No epsilon money or hidden OWN preference.
"""
from dataclasses import dataclass,field
from decimal import Decimal
from fractions import Fraction
import hashlib

from ortools.sat.python import cp_model
from app.domain.logistics.base import Priority
from app.domain.logistics.costs import trip_cost
from app.domain.logistics.units import scaled_integer,QUANTITY_SCALES


class PolicyRequirementsError(ValueError):
    code='POLICY_COST_REQUIRED'


@dataclass
class PolicySearch:
    request: object
    goal: str | None = None
    model_budget: float | None = None
    kernel_budget: float = 1.0
    stages: list = field(default_factory=list)
    costs: list = field(default_factory=list)
    native_statuses: list = field(default_factory=list)
    all_optimal: bool = False
    model_sha256: str = ''
    final_value: int | None = None
    normalization: dict = field(default_factory=dict)

    def optimize(self,model,slots,orders,denominators,by_order):
        request=self.request;policy=request.context.node_policy
        goal=self.goal or policy.primary_goal
        primary=request.model.primary_dimension
        total_requested=sum(scaled_integer(getattr(o.requested,primary),QUANTITY_SCALES[primary]) for o in orders)
        assigned=sum(denominators[i][1][primary]*x for i in range(len(orders)) for x in by_order[i])
        priority={p:sum(denominators[i][1][primary]*x for i,o in enumerate(orders) if o.priority==p for x in by_order[i]) for p in Priority}
        requested_priority={p:sum(scaled_integer(getattr(o.requested,primary),QUANTITY_SCALES[primary]) for o in orders if o.priority==p) for p in Priority}
        own_load=sum(denominators[i][1][primary]*x for s in slots if s.resource.source=='OWN' for i,x in s.fractions.items())
        trips=sum(s.present for s in slots)
        own_trips=sum(s.present for s in slots if s.resource.source=='OWN')
        external_trips=trips-own_trips
        for guard in policy.guardrails:
            limit=Fraction(guard.limit)
            if guard.kind in ('MINIMUM_DEMAND_COVERAGE','CRITICAL_DEMAND_COVERAGE'):
                numerator,denominator=(assigned,total_requested) if guard.kind=='MINIMUM_DEMAND_COVERAGE' else (priority[Priority.HIGH],requested_priority[Priority.HIGH])
                if denominator*limit.denominator>2**60:raise ValueError('Guardrail numeric budget exceeded')
                model.add(limit.denominator*numerator>=limit.numerator*denominator)
            elif guard.kind=='MAXIMUM_EXTERNAL_SHARE':
                model.add(limit.denominator*external_trips<=limit.numerator*trips)
            else:
                model.add(limit.denominator*own_trips>=limit.numerator*trips)
        self.costs=[trip_cost(s.resource,s.distance,request.context.currency_policy) for s in slots]
        weights={p.kind:p.weight for p in policy.preferences if p.weight>0}
        if goal=='BALANCED' and not weights:weights={key:Decimal('.25') for key in ['COST','TRIPS','SERVICE','OWN_CAPACITY']}
        economic=goal=='MINIMIZE_COST' or (goal in ('BALANCED','CUSTOM') or weights) and weights.get('COST',0)>0
        if economic and any(c is None for c in self.costs):
            raise PolicyRequirementsError('A feasible candidate has unknown cost required by this policy')
        money=[scaled_integer(c.amount,request.context.currency_policy.minor_units) if c else 0 for c in self.costs]
        if sum(money)>2**55:raise ValueError('Cost objective integer budget exceeded')
        cost=sum(c*s.present for c,s in zip(money,slots))
        stages=[]
        for p in Priority:
            if requested_priority[p]:stages.append(('COVERAGE_'+p,priority[p],True))
        # Zero-primary vectors still have real capacity requirements. A separate
        # whole-order completion stage cannot trade off any primary coverage.
        zero=[]
        for i,o in enumerate(orders):
            if getattr(o.requested,primary)==0 and by_order[i]:
                covered=model.new_bool_var('zero_primary_'+str(i));model.add(sum(by_order[i])==denominators[i][0]).only_enforce_if(covered);zero.append(covered)
        if zero:stages.append(('ZERO_PRIMARY_COVERAGE',sum(zero),True))
        terms={'COST':(cost,sum(money)), 'TRIPS':(trips,len(slots)),
            'SERVICE':(total_requested-assigned,total_requested),'OWN_CAPACITY':(total_requested-own_load,total_requested)}
        self.normalization={**{'bound_'+k:v[1] for k,v in terms.items()},**{'weight_'+k:v for k,v in weights.items()},'normalized_scale':10000}
        def normalized(combination,label):
            losses=[]
            for kind,weight in sorted(combination.items()):
                if not weight:continue
                expression,bound=terms[kind]
                if not bound:continue
                if bound*20000>2**60:raise ValueError('Normalized objective integer budget exceeded')
                number=model.new_int_var(0,bound*10000+bound//2,label+'_'+kind+'_n')
                loss=model.new_int_var(0,10000,label+'_'+kind+'_loss')
                model.add(number==expression*10000+bound//2)
                model.add_division_equality(loss,number,bound)
                losses.append(loss*scaled_integer(weight,4))
            return sum(losses)
        if goal=='MINIMIZE_COST':stages.append((goal,cost,False))
        elif goal=='MINIMIZE_TRIPS':stages.append((goal,trips,False))
        elif goal=='MAXIMIZE_OWN_CAPACITY':stages.append((goal,own_load,True))
        elif goal in ('BALANCED','CUSTOM'):stages.append((goal,normalized(weights,'goal'),False))
        elif goal=='MAXIMIZE_SERVICE':stages.append((goal,assigned,True))
        else:raise ValueError('Unknown policy goal')
        if weights and goal not in ('BALANCED','CUSTOM'):stages.append(('PREFERENCES',normalized(weights,'pref'),False))
        stages.append(('STABLE_RESOURCE_TIE',sum((i+1)*s.present for i,s in enumerate(slots)),False))
        if len(model.proto.variables)>request.options.max_variables:return None,['UNKNOWN'],['POLICY_VARIABLE_BUDGET']
        if model.validate():raise ValueError('Invalid policy model: '+model.validate())
        solver=cp_model.CpSolver();solver.parameters.num_search_workers=1
        solver.parameters.random_seed=request.options.seed
        solver.parameters.max_deterministic_time=(self.model_budget if self.model_budget is not None else request.options.deterministic_budget)/max(len(stages),1)
        solver.parameters.max_time_in_seconds=10
        selected=None;limits=[]
        for label,objective,maximize in stages:
            if maximize:model.maximize(objective)
            else:model.minimize(objective)
            status=solver.solve(model);native=solver.status_name(status);self.native_statuses.append(native)
            if status==cp_model.MODEL_INVALID:raise RuntimeError('Invalid policy CP-SAT model')
            if status not in (cp_model.FEASIBLE,cp_model.OPTIMAL):
                self.stages.append((label,native,None,None))
                if selected is not None:limits.append('POLICY_LATER_STAGE_UNPROVEN')
                break
            value=solver.value(objective)
            # For OPTIMAL integer objective the exact optimum is certified by
            # the native response; never round a floating best bound into proof.
            self.stages.append((label,native,value,value if status==cp_model.OPTIMAL else None))
            self.final_value=value
            selected=[{i:solver.value(x) for i,x in s.fractions.items()} if solver.value(s.present) else {} for s in slots]
            if status!=cp_model.OPTIMAL:
                limits.append('POLICY_STAGE_UNPROVEN');break
            if not isinstance(objective,int):model.add(objective==value)
        self.all_optimal=len(self.stages)==len(stages) and all(s[1]=='OPTIMAL' for s in self.stages)
        self.model_sha256=hashlib.sha256(str(model.proto).encode()).hexdigest()
        return selected,self.native_statuses,limits
