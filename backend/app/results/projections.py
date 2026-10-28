"""Pure D1 joins and display projections of certified engine facts."""
import hashlib
from . import contracts as c
from .canonical import canonical_bytes


def graph_id(kind,entity_id):
    return kind+'-'+hashlib.sha256(canonical_bytes(entity_id)).hexdigest()[:24]


def sankey(core):
    nodes={};links=[];dimension=core.context.primary_dimension
    for trip in core.transport_plan.trips:
        destination=graph_id('DESTINATION',trip.destination_id)
        tid=graph_id('TRIP',trip.trip_id);resource=graph_id('RESOURCE',trip.resource_id)
        for identity,kind,label in [(destination,'DESTINATION',trip.destination_id),(tid,'TRIP',trip.trip_id),(resource,'RESOURCE',trip.resource_id)]:
            nodes[identity]=c.SankeyNode(id=identity,type=kind,label=label)
        value=getattr(trip.total_load,dimension)
        links.extend([c.SankeyLink(source=destination,target=tid,value=value,order_ids=tuple(a.order_id for a in trip.orders)),
            c.SankeyLink(source=tid,target=resource,value=value,order_ids=tuple(a.order_id for a in trip.orders))])
    return c.SankeyProjection(value_dimension=dimension,nodes=tuple(nodes[k] for k in sorted(nodes)),links=tuple(sorted(links,key=lambda l:(l.source,l.target))))


def exceptions_and_assumptions(evidence):
    exceptions=[];assumptions=[]
    categories={'CAPACITY_GAP':'BUSINESS','NO_COMPATIBLE_RESOURCE':'DATA','NON_SPLIT_EXCEEDS_GUARANTEED_CAPACITY':'FEASIBILITY','DATE_WINDOW_INCOMPATIBLE':'FEASIBILITY'}
    for reason in evidence.reasons:
        if reason.code in categories:
            exceptions.append(c.ExceptionDescriptor(exception_id='EX-'+reason.emission_id,category=categories[reason.code],severity='ATTENTION',
                code=reason.code,entity_type=reason.entity_type,entity_ids=(reason.entity_id,),message_key='ultimate.exception.'+reason.code.lower(),facts=reason.facts,reason_ref=reason.emission_id))
        if reason.code=='ASSUMED_EXTERNAL_AVAILABILITY':
            # DERIVED describes this projection of the supplied ASSUMED fact;
            # no actor/default provenance is invented from a services count.
            assumptions.append(c.AssumptionDescriptor(assumption_id='AS-'+reason.emission_id,code=reason.code,entity_type=reason.entity_type,
                entity_id=reason.entity_id,value=reason.facts['services_available'],unit='horizon_services',source='DERIVED',reason_ref=reason.emission_id))
    return tuple(sorted(exceptions,key=lambda e:e.exception_id)),tuple(sorted(assumptions,key=lambda a:a.assumption_id))


def summary(core):
    metric=core.metrics
    return c.ExecutiveSummary(template_id='ultimate.transport_plan.certified_v1',facts={
        'trip_count':metric.trip_count,'assigned':metric.demand_coverage.assigned,'residual':metric.demand_coverage.unassigned,
        'coverage_ratio':metric.demand_coverage.ratio,'total_cost':metric.total_cost.amount if metric.total_cost else None,
        'currency':core.context.currency_policy.currency,'primary_dimension':core.context.primary_dimension,
        'policy_feasible':core.feasibility.policy_feasible,'solver_status':core.engine.solver_status})


def descriptor(dataset_id,dataset_type,data,columns,key):
    return c.DetailDatasetDescriptor(dataset_id=dataset_id,dataset_type=dataset_type,data=data,
        columns=tuple(c.DetailColumn(key=k,format=f,unit=u) for k,f,u in columns),primary_key=key,stable_order=key)


def evidence_shards(evidence):
    """Typed PARTITIONED_ENGINE_EVIDENCE_V1 rows, reconstructed as a whole.

    Each row preserves the same header and valid reason links. Delivery metadata
    declares partition semantics; no row is advertised as the complete evidence.
    """
    header=evidence.model_dump(exclude={'constraints','reasons','entities'})
    rows=[];reason_map={r.emission_id:r for r in evidence.reasons}
    for index in range(0,len(evidence.constraints),100):
        rows.append(c.EngineEvidence(**header,constraints=evidence.constraints[index:index+100],reasons=(),entities=()))
    for index in range(0,len(evidence.entities),25):
        entities=evidence.entities[index:index+25]
        refs={ref for e in entities for ref in (*e.reason_refs,*(ref for candidate in e.candidate_summary for ref in candidate.reason_refs))}
        rows.append(c.EngineEvidence(**header,constraints=(),reasons=tuple(reason_map[ref] for ref in sorted(refs)),entities=entities))
    for index in range(0,len(evidence.reasons),100):
        rows.append(c.EngineEvidence(**header,constraints=(),reasons=evidence.reasons[index:index+100],entities=()))
    return tuple(rows) if rows else (evidence,)
