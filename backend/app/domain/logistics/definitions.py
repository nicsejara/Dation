"""Release-controlled Ultimate Decision Definitions. No browser-supplied graph."""
from typing import Literal
from pydantic import StrictBool
from .base import ContractModel
from app.results.canonical import canonical_bytes, content_sha256

GRAPH_VERSION = 'ULTIMATE_DECISION_GRAPH_V1'
BINDINGS = ('ULTIMATE_FOUNDATION_V1', GRAPH_VERSION)

class DecisionDefinition(ContractModel):
    id: str
    version: str = '1'
    label: str
    question: str
    implemented: StrictBool
    applicability: Literal['ALWAYS', 'UPSTREAM_HAS_TRIPS']
    dependencies: tuple[str, ...]
    required_approvals: tuple[str, ...]
    required_inputs: tuple[str, ...]
    read_set: tuple[str, ...]
    decision_variables: tuple[str, ...]
    hard_constraints: tuple[str, ...]
    soft_constraints: tuple[str, ...]
    objectives: tuple[str, ...]
    outputs: tuple[str, ...]
    evidence: tuple[str, ...]
    downstream_contract: str | None

DEFINITIONS = (
    DecisionDefinition(id='logistics_assignment', label='Transport Plan',
        question='¿Cómo asignar la demanda a recursos y viajes?', implemented=True,
        applicability='ALWAYS', dependencies=(), required_approvals=(),
        required_inputs=('transport_demand','transport_resources'),
        read_set=('transport_demand','transport_resources','model','horizon','case_policy','node_policy'),
        decision_variables=('assignments','trips','consolidation','fractions'),
        hard_constraints=('guaranteed_capacity','finite_availability','compatibility','split_policy','case_guardrails'),
        soft_constraints=('case_preferences',), objectives=('case_primary_goal',),
        outputs=('transport_plan_v1',), evidence=('engine_core_v1','decision_evidence_v1'),
        downstream_contract='approved_transport_plan_v1'),
    DecisionDefinition(id='logistics_scheduling', label='Day Scheduling',
        question='¿Qué día debe despacharse cada viaje aprobado?', implemented=True,
        applicability='UPSTREAM_HAS_TRIPS', dependencies=('logistics_assignment',),
        required_approvals=('logistics_assignment',), required_inputs=(),
        read_set=('approved:logistics_assignment','horizon','node_policy'),
        decision_variables=('dispatch_day',),
        hard_constraints=('fixed_upstream_trips','inclusive_horizon','resource_cycle'),
        soft_constraints=('service_dates',), objectives=('case_primary_goal',),
        outputs=('day_scheduling_v1',), evidence=('engine_core_v1','decision_evidence_v1'),
        downstream_contract=None),
)

def validate_definitions(definitions):
    nodes={d.id:d for d in definitions}
    if len(nodes)!=len(definitions): raise ValueError('Duplicate Definition')
    closure={}
    def visit(key, stack=()):
        if key in stack: raise ValueError('Cyclic Definitions')
        if key not in nodes: raise ValueError('Unknown dependency')
        if key not in closure:
            d=nodes[key]
            if not set(d.required_approvals)<=set(d.dependencies): raise ValueError('Approval outside dependencies')
            closure[key]=tuple(sorted(set(d.dependencies).union(*(set(visit(p,(*stack,key))) for p in d.dependencies))))
        return closure[key]
    for key in nodes: visit(key)
    return closure

def definition_snapshot():
    return {'schema_version':'decision_graph_definition_v1','version':GRAPH_VERSION,
        'supported_bindings':list(BINDINGS), 'nodes':[d.model_dump(mode='json') for d in DEFINITIONS],
        'dependency_closure':{k:list(v) for k,v in validate_definitions(DEFINITIONS).items()}}

def definition_hash(): return content_sha256(canonical_bytes(definition_snapshot()))
