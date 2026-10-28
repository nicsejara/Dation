"""Independent cross-projection checks. Never repairs or optimizes a result."""
from decimal import Decimal,ROUND_HALF_UP,localcontext
import json,hashlib
from . import contracts as c
from .canonical import canonical_bytes,artifact_bytes,content_sha256,core_result_fingerprint


def require(ok,message):
    if not ok:raise ValueError(message)


def rounded(n,d):return None if not d else (Decimal(n)/Decimal(d)).quantize(Decimal('.0001'),rounding=ROUND_HALF_UP)


def validate_certified_plan(plan):
    _validated_plan_output(plan)
    return True


def _validated_plan_output(plan):
    with localcontext() as ctx:
        ctx.prec=60
        return _validate_plan(plan)


def _validate_plan(plan):
    output=c.EngineOutput.model_validate(plan.output);core=output.core
    require(core.result_schema=='transport_plan_v1','Unsupported Core schema')
    original=plan.structural.output.core
    require(core.context==original.context,'Frozen context changed')
    trips=core.transport_plan.trips
    resource_facts={e.entity_id:e.facts for e in output.evidence.entities if e.entity_type=='RESOURCE'}
    require(len(trips)==len(original.transport_plan.trips),'Assembly input changed Trips')
    for a,b in zip(trips,original.transport_plan.trips):
        x=a.model_dump();y=b.model_dump()
        for key in ['estimated_cost','reason_codes']:x.pop(key);y.pop(key)
        require(x==y,'Assignments differ from the certified structural plan')
        f=resource_facts[a.resource_id]
        rate=f['operating_cost_per_km'] if a.resource_source=='OWN' else f['external_rate']
        amount=None if rate is None else Decimal(rate)
        if amount is not None:
            if a.resource_source=='OWN':amount*=a.distance_km*2
            elif f['external_cost_model']=='PER_KM':amount*=a.distance_km*(2 if f['billing_basis']=='ROUND_TRIP' else 1)
            amount=core.context.currency_policy.rounded(amount)
        require((a.estimated_cost.amount if a.estimated_cost else None)==amount,'Core price contradicts certified input cost facts')
    total=sum((t.estimated_cost.amount for t in trips if t.estimated_cost),Decimal(0))
    all_known=core.feasibility.solution_found and all(t.estimated_cost is not None for t in trips)
    require((core.metrics.total_cost.amount if core.metrics.total_cost else None)==(total if all_known else None),'Core total cost inconsistent')
    require(core.metrics.cost_completeness==('COMPLETE' if all_known else 'PARTIAL' if any(t.estimated_cost for t in trips) else 'UNKNOWN'),'Core cost completeness inconsistent')
    orders={r.order_id:r for r in plan.demand_resolution}
    require(len(orders)==len(plan.demand_resolution)==plan.input_summary.orders,'Demand cardinality differs')
    assigned={oid:{d:Decimal(0) for d in core.context.active_dimensions} for oid in orders}
    for trip in trips:
        for a in trip.orders:
            require(a.order_id in orders,'Unknown allocation Order')
            for d in core.context.active_dimensions:assigned[a.order_id][d]+=getattr(a.load,d)
    for oid,row in orders.items():
        for d in core.context.active_dimensions:
            require(getattr(row.assigned,d)==assigned[oid][d] and getattr(row.assigned,d)+getattr(plan.residuals[oid],d)==getattr(row.requested,d),'Demand conservation differs')
        require(tuple(sorted(t.trip_id for t in trips if any(a.order_id==oid for a in t.orders)))==row.trip_ids,'Demand Trip refs differ')
    primary=core.context.primary_dimension
    requested=sum((getattr(r.requested,primary) for r in orders.values()),Decimal(0))
    allocated=sum((getattr(r.assigned,primary) for r in orders.values()),Decimal(0))
    metric=core.metrics
    require(metric.trip_count==len(trips) and metric.resources_used==len({t.resource_id for t in trips}),'Core count metric inconsistent')
    require((metric.demand_coverage.requested,metric.demand_coverage.assigned,metric.demand_coverage.unassigned,metric.demand_coverage.ratio)==(requested,allocated,requested-allocated,rounded(allocated,requested)),'Core coverage inconsistent')
    require(metric.capacity_utilization.weighted_ratio==rounded(sum((getattr(t.total_load,primary) for t in trips),Decimal(0)),sum((getattr(t.guaranteed_capacity,primary) for t in trips),Decimal(0))),'Core weighted utilization inconsistent')
    for usage in plan.resource_usage:
        used=[t for t in trips if t.resource_id==usage.resource_id]
        amount=sum((t.estimated_cost.amount for t in used if t.estimated_cost),Decimal(0)) if core.feasibility.solution_found and all(t.estimated_cost for t in used) else None
        require((usage.total_cost.amount if usage.total_cost else None)==amount,'Resource cost inconsistent')
    if core.feasibility.solution_found:
        require(core.feasibility.policy_feasible is True,'Uncertified policy passed to assembler')
        for guard in core.context.node_policy.guardrails:
            if guard.kind=='MINIMUM_DEMAND_COVERAGE':n,d=allocated,requested
            elif guard.kind=='CRITICAL_DEMAND_COVERAGE':n=sum(getattr(r.assigned,primary) for r in orders.values() if r.priority=='HIGH');d=sum(getattr(r.requested,primary) for r in orders.values() if r.priority=='HIGH')
            elif guard.kind=='MAXIMUM_EXTERNAL_SHARE':n,d=sum(t.resource_source=='EXTERNAL' for t in trips),len(trips)
            else:n,d=sum(t.resource_source=='OWN' for t in trips),len(trips)
            require(d==0 or (n<=guard.limit*d if guard.kind=='MAXIMUM_EXTERNAL_SHARE' else n>=guard.limit*d),'Assembler input violates guardrail')
    require(output.evidence.core_result_fingerprint==core_result_fingerprint(core),'Core evidence hash mismatch')
    return output


def read_delivery(delivery,artifacts):
    lookup={a.reference.artifact_id:a for a in artifacts}
    def fetch(ref):
        require(ref.artifact_id in lookup,'Missing artifact')
        prepared=lookup[ref.artifact_id]
        require(prepared.reference==ref and content_sha256(prepared.content)==ref.content_sha256 and len(prepared.content)==ref.size_bytes,'Artifact integrity mismatch')
        body=json.loads(prepared.content)
        require(artifact_bytes(body)==prepared.content,'Noncanonical/unsafe artifact')
        return body
    return _bound_delivery_rows(delivery,fetch)


def _bound_delivery_rows(delivery,fetch):
    if isinstance(delivery,c.InlineDataset):return list(delivery.rows)
    rows=[]
    for index,ref in enumerate(delivery.artifacts):
        body=fetch(ref)
        require(body['dataset_id']==delivery.dataset_id and body['row_schema']==delivery.row_schema and body['scope']=='FULL','Wrong artifact dataset/schema/scope')
        require(body['row_semantics'] in ('TYPED_ROWS_V1','PARTITIONED_ENGINE_EVIDENCE_V1','DECISION_CONTEXT_BASE_V1'),'Unknown artifact row semantics')
        require(body['chunk_index']==index and body['chunk_count']==len(delivery.artifacts) and body['total_rows']==delivery.row_count,'Incomplete chunk set')
        require(body['core_binding']['core_result_fingerprint']==ref.core_fingerprint and body['core_binding']['run_id']==str(ref.run_id),'Wrong artifact binding')
        rows.extend(body['rows'])
    require(len(rows)==delivery.row_count,'Delivery cardinality differs')
    return rows


def reassemble_evidence(rows):
    """Explicit adapter for complete partitioned evidence; no missing-row fallback."""
    require(bool(rows),'Missing evidence partitions')
    return _reassemble_validated_evidence([c.EngineEvidence.model_validate(row) for row in rows])


def _reassemble_validated_evidence(parts):
    """Merge locally validated partitions, retaining whole-evidence validation."""
    require(bool(parts),'Missing evidence partitions')
    header=parts[0].model_dump(exclude={'constraints','entities','reasons'})
    collections={'constraints':{},'entities':{},'reasons':{}}
    for part in parts:
        require(canonical_bytes(part.model_dump(exclude=set(collections)))==canonical_bytes(header),'Evidence partition header mismatch')
        for kind in collections:
            for value in getattr(part,kind):
                key=(value.entity_type,value.entity_id) if kind=='entities' else value.evidence_id if kind=='constraints' else value.emission_id
                previous=collections[kind].get(key)
                require(previous is None or previous==value,'Conflicting evidence partition identity')
                collections[kind][key]=value
    return c.EngineEvidence(**header,**{k:tuple(v[key] for key in sorted(v)) for k,v in collections.items()})


def validate_bundle(bundle):
    if bundle.package.result_schema=='day_scheduling_v1':
        from .day_validation import validate_day_bundle
        return validate_day_bundle(bundle)
    with localcontext() as ctx:
        ctx.prec=60;_validate_bundle(bundle)
    return True


def _validate_bundle(bundle):
    package=c.DecisionResultPackageV1.model_validate(bundle.package)
    plan=bundle.result.recommended
    checked_output=_validated_plan_output(plan)
    core,evidence=checked_output.core,checked_output.evidence
    c.validate_result_binding(core,evidence,package)
    lookup={a.reference.artifact_id:a for a in bundle.artifacts}
    require(len(lookup)==len(bundle.artifacts),'Duplicate prepared artifact')
    require({a.artifact_id for a in package.artifact_manifest.artifacts}==set(lookup),'Manifest differs from prepared artifacts')
    verified_bodies={};datasets={};verified_evidence={}
    for ref in package.artifact_manifest.artifacts:
        a=lookup[ref.artifact_id]
        require(ref==a.reference and len(a.content)==ref.size_bytes and content_sha256(a.content)==ref.content_sha256,'Prepared bytes corrupt')
        require(len(a.content)<=c.EVIDENCE_CHUNK_MAX_BYTES,'Artifact exceeds budget')
        body=json.loads(a.content)
        require(artifact_bytes(body)==a.content,'Unsafe/noncanonical prepared bytes')
        semantics=body['row_semantics']
        require(semantics in ('TYPED_ROWS_V1','PARTITIONED_ENGINE_EVIDENCE_V1','DECISION_CONTEXT_BASE_V1'),'Unknown prepared row semantics')
        if semantics=='DECISION_CONTEXT_BASE_V1':
            require(ref.artifact_schema=='decision_context_v1' and ref.kind=='AI_BASE','Wrong base-context artifact schema/role')
            from .ai_context import DecisionContextBase
            row_type=DecisionContextBase
        else:
            if semantics=='PARTITIONED_ENGINE_EVIDENCE_V1':require(ref.artifact_schema=='engine_evidence_v1' and ref.kind=='EVIDENCE','Wrong evidence-partition schema/role')
            row_type=c._row_schema_type(ref.artifact_schema)
        if row_type is c.EngineEvidence:
            # Keep the typed result of the mandatory row validation. Repeating
            # that same conversion when reconstructing the proof dominated
            # large D1 bundles. These objects never leave this validation call.
            verified_evidence[ref.artifact_id]=tuple(row_type.model_validate(row) for row in body['rows'])
        else:
            for row in body['rows']:
                if row_type is not dict:row_type.model_validate(row)
        verified_bodies[ref.artifact_id]=body
        datasets.setdefault(body['dataset_id'],[]).append(a)
    def verified(ref):
        # Invocation-local: these immutable bytes were hash/schema checked above.
        # Recheck reference identity and delivery bindings for every use. No
        # authorization/cache state survives this single bundle validation.
        require(ref.artifact_id in verified_bodies and lookup[ref.artifact_id].reference==ref,'Artifact integrity mismatch')
        return verified_bodies[ref.artifact_id]
    def rows(delivery):return _bound_delivery_rows(delivery,verified)
    def evidence_rows(delivery):
        # Delivery cardinality/schema/chunk/core/Run binding checks still run.
        bound=rows(delivery)
        require(all(ref.artifact_id in verified_evidence for ref in delivery.artifacts),'Evidence row schema differs')
        parts=[part for ref in delivery.artifacts for part in verified_evidence.pop(ref.artifact_id)]
        require(len(parts)==len(bound),'Evidence partition cardinality differs')
        return _reassemble_validated_evidence(parts)
    def same(a,b,message):require(canonical_bytes(a)==canonical_bytes(b),message)
    def dataset(dataset_id):
        prepared=list(datasets.get(dataset_id,()))
        require(bool(prepared),'Missing named artifact dataset')
        prepared.sort(key=lambda p:verified_bodies[p.reference.artifact_id]['chunk_index'])
        head=verified_bodies[prepared[0].reference.artifact_id]
        return c.ReferenceDataset(dataset_id=dataset_id,row_schema=head['row_schema'],row_count=head['total_rows'],artifacts=tuple(p.reference for p in prepared))
    same(rows(dataset('core')),(core,),'Prepared Core differs')
    same(rows(package.transport_plan.trips),sorted(core.transport_plan.trips,key=lambda t:t.trip_id),'Published Trips differ')
    same(rows(package.transport_plan.unassigned_demand),core.transport_plan.unassigned_demand,'Published residual differs')
    details={d.dataset_id:d for d in package.details}
    require(set(details)=={'plan','demand','resources','alternatives','exceptions','evidence'},'Missing/unknown D1 detail dataset')
    same(rows(details['plan'].data),sorted(core.transport_plan.trips,key=lambda t:t.trip_id),'Plan detail differs')
    same(rows(details['resources'].data),plan.resource_usage,'Resource details differ')
    same(rows(details['demand'].data),[e for e in evidence.entities if e.entity_type=='ORDER'],'Demand details differ')
    same(rows(details['evidence'].data),sorted(evidence.entities,key=lambda e:(e.entity_type,e.entity_id)),'Entity evidence differs')
    same(rows(package.evidence.reason_emissions),evidence.reasons,'Reasons differ')
    proof=next(d for d in package.evidence.parts if d.dataset_id=='engine-evidence')
    # Compare semantic evidence sets independently of the partition/display order.
    restored=evidence_rows(proof)
    require(len(restored.constraints)==len(evidence.constraints) and len(restored.entities)==len(evidence.entities) and len(restored.reasons)==len(evidence.reasons),'Incomplete restored evidence')
    same({v.evidence_id:v for v in restored.constraints},{v.evidence_id:v for v in evidence.constraints},'Restored constraint facts differ')
    same({(v.entity_type+':'+v.entity_id):v for v in restored.entities},{(v.entity_type+':'+v.entity_id):v for v in evidence.entities},'Restored entity facts differ')
    same({v.emission_id:v for v in restored.reasons},{v.emission_id:v for v in evidence.reasons},'Restored reason facts differ')
    visual=package.primary_visual.projection
    if isinstance(visual,c.ReferenceDataset):visual=c.SankeyProjection.model_validate(rows(visual)[0])
    require(visual.value_dimension==core.context.primary_dimension,'Sankey dimension mismatch')
    nodes={n.id:n for n in visual.nodes};expected_nodes=set();expected_links={}
    def gid(kind,eid):return kind+'-'+hashlib.sha256(canonical_bytes(eid)).hexdigest()[:24]
    for trip in core.transport_plan.trips:
        keys=[gid('DESTINATION',trip.destination_id),gid('TRIP',trip.trip_id),gid('RESOURCE',trip.resource_id)]
        expected_nodes.update(keys)
        value=getattr(trip.total_load,core.context.primary_dimension)
        expected_links[keys[0],keys[1]]=value;expected_links[keys[1],keys[2]]=value
    require(set(nodes)==expected_nodes and len(visual.links)==len(expected_links),'Fictitious/missing Sankey entity')
    require({(l.source,l.target):l.value for l in visual.links}==expected_links,'Sankey flow differs')
    index=rows(next(d for d in package.evidence.parts if d.dataset_id=='sankey-entity-index'))
    require(len(index)==len(expected_nodes) and {r['facts']['graph_node_id'] for r in index}==expected_nodes,'Sankey entity index incomplete')
    for row in index:
        f=row['facts']
        if f['scope']=='DESTINATION_FILTER':require(row['entity_type']=='CASE' and row['entity_id']==str(core.context.case_id) and gid('DESTINATION',f['destination_id'])==f['graph_node_id'],'Wrong destination binding')
        else:require(row['entity_type'] in ('TRIP','RESOURCE') and gid(row['entity_type'],row['entity_id'])==f['graph_node_id'],'Wrong graph entity binding')
    for kind in ['DESTINATION','TRIP']:
        cut=sum((l.value for l in visual.links if nodes[l.source].type==kind),Decimal(0))
        require(cut==core.metrics.demand_coverage.assigned,'Sankey cut inconsistent')
    require(package.exports.csv.available==core.feasibility.solution_found,'Unusable result exposes a plan CSV')
    require(package.exports.csv.available or package.exports.csv.rows is None,'Unusable CSV has fake empty rows')
    export=rows(package.exports.csv.rows) if package.exports.csv.available else []
    allocations={(t.trip_id,a.order_id):(t,a) for t in core.transport_plan.trips for a in t.orders}
    require(len(export)==len(allocations) and {(r['trip_id'],r['order_id']) for r in export}==set(allocations),'Export allocation set differs')
    recognized=Decimal(0)
    for row in export:
        trip,a=allocations[row['trip_id'],row['order_id']]
        first=min(v.order_id for v in trip.orders)==a.order_id
        expected_cost=trip.estimated_cost.amount if first and trip.estimated_cost else None
        require((Decimal(row['estimated_cost']) if row['estimated_cost'] is not None else None)==expected_cost,'Export duplicates/changes Trip cost')
        if expected_cost is not None:recognized+=expected_cost
        require(row['resource_id']==trip.resource_id and Decimal(row['allocation_fraction'])==a.allocation_fraction,'Export resource/fraction differs')
        require((row['origin_id'],row['destination_id'],row['resource_source'],Decimal(row['distance_km']))==(trip.origin_id,trip.destination_id,trip.resource_source,trip.distance_km),'Export route differs')
        for d in core.context.active_dimensions:require(Decimal(row['load_'+d])==getattr(a.load,d),'Export load differs')
    if core.metrics.total_cost:require(recognized==core.metrics.total_cost.amount,'Export cost sum differs')
    same(package.metrics,core.metrics,'Package metrics changed')
    expected_summary={'trip_count':core.metrics.trip_count,'assigned':core.metrics.demand_coverage.assigned,
        'residual':core.metrics.demand_coverage.unassigned,'coverage_ratio':core.metrics.demand_coverage.ratio,
        'total_cost':core.metrics.total_cost.amount if core.metrics.total_cost else None,'currency':core.context.currency_policy.currency,
        'primary_dimension':core.context.primary_dimension,'policy_feasible':core.feasibility.policy_feasible,'solver_status':core.engine.solver_status}
    same(package.summary.facts,expected_summary,'Summary facts contradict Core')
    same(bundle.context.metrics,core.metrics,'AI metrics changed')
    same(bundle.context.approval_review,package.approval_review,'AI review changed')
    same(bundle.context.result_summary,package.summary,'AI summary changed')
    same(bundle.context.case,core.context,'AI Case changed')
    require(package.approval_review.exception_count==len(package.exceptions) and package.approval_review.assumption_count==len(package.assumptions),'Review counts differ')
    actual_reasons={r.emission_id:r for r in evidence.reasons}
    for item in (*package.exceptions,*package.assumptions):
        require(item.reason_ref in actual_reasons and actual_reasons[item.reason_ref].code==item.code,'Invented exception/assumption reason')
    same(rows(details['exceptions'].data),[c.EntityEvidence(entity_type=e.entity_type,entity_id=e.entity_ids[0],facts={'exception_id':e.exception_id,'code':e.code,'category':e.category,'severity':e.severity,**e.facts},reason_refs=(e.reason_ref,)) for e in package.exceptions],'Exception details differ')
    require(len(package.alternatives)==len(bundle.result.alternatives)<=3,'Alternative count differs')
    signatures=[]
    def physical(plan):return canonical_bytes(sorted([dict(resource=t.resource_id,source=t.resource_source,origin=t.origin_id,destination=t.destination_id,distance=t.distance_km,orders=t.orders) for t in plan.output.core.transport_plan.trips],key=canonical_bytes))
    signatures.append(physical(plan))
    for descriptor,candidate in zip(package.alternatives,bundle.result.alternatives):
        validate_certified_plan(candidate)
        signature=physical(candidate);require(signature not in signatures,'Duplicate alternative plan');signatures.append(signature)
        ac=candidate.output.core
        require(ac.context==core.context and ac.feasibility.policy_feasible is True,'Alternative uses another context or violates policy')
        same(rows(descriptor.plan),sorted(ac.transport_plan.trips,key=lambda t:t.trip_id),'Alternative plan lost')
        same(rows(descriptor.evidence),candidate.output.evidence.entities,'Alternative evidence lost')
        same(rows(dataset(descriptor.alternative_id+'-core')),(ac,),'Alternative Core bytes differ')
        restored_alt=evidence_rows(dataset(descriptor.alternative_id+'-proof'))
        same({v.evidence_id:v for v in restored_alt.constraints},{v.evidence_id:v for v in candidate.output.evidence.constraints},'Alternative constraint bytes differ')
        same({v.emission_id:v for v in restored_alt.reasons},{v.emission_id:v for v in candidate.output.evidence.reasons},'Alternative reason bytes differ')
        require(descriptor.metrics.trip_count==ac.metrics.trip_count and descriptor.metrics.total_cost==(ac.metrics.total_cost.amount if ac.metrics.total_cost else None),'Alternative metrics differ')
        if core.metrics.total_cost and ac.metrics.total_cost:require(descriptor.difference_vs_recommended.cost_delta==ac.metrics.total_cost.amount-core.metrics.total_cost.amount,'Alternative delta differs')
    from .ai_context import DecisionContextBase,bind_context
    base=DecisionContextBase.model_validate(rows(package.ai_context.base_context)[0])
    same(bind_context(base,package),bundle.context,'AI binding/base diverges')
    return True
