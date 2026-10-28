"""Pure T7 assembly of one certified D1 result, prepared bytes only."""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID,uuid5

from . import contracts as c
from .canonical import artifact_bytes,content_sha256,core_result_fingerprint,result_fingerprint,policy_hash,canonical_tree
from .registry import resolve_schema
from .projections import sankey,summary,descriptor,exceptions_and_assumptions,graph_id,evidence_shards
from .export_rows import transport_export_rows
from .approval_review import build_review
from .ai_context import build_base,bind_context

ASSEMBLER_VERSION='RESULT_ASSEMBLER_D1_V1'


@dataclass(frozen=True)
class PreparedArtifact:
    reference: c.ResultArtifactReference
    content: bytes


@dataclass(frozen=True)
class AssemblyBundle:
    package: c.DecisionResultPackageV1
    artifacts: tuple[PreparedArtifact,...]
    context: c.DecisionContextV1
    result: object


class AssemblyError(ValueError):pass


class ArtifactBuilder:
    def __init__(self,core,assembler_version=ASSEMBLER_VERSION):
        self.core=core;self.fingerprint=core_result_fingerprint(core);self.parts=[];self.assembler_version=assembler_version

    def dataset(self,dataset_id,schema,rows,kind='DETAIL_DATASET',row_semantics='TYPED_ROWS_V1'):
        # Every descriptor is FULL and every chunk is numbered. No top-N or
        # empty substitute for unavailable rows. T8 may publish these bytes later.
        chunks=[];current=[]
        def payload(items,index):return {'delivery_version':1,'dataset_id':dataset_id,'row_schema':schema,'row_semantics':row_semantics,'scope':'FULL',
            'chunk_index':index,'core_binding':{'run_id':self.core.decision.run_id,'core_result_fingerprint':self.fingerprint},'rows':items}
        for row in rows:
            prospective=artifact_bytes(payload([*current,row],len(chunks)))
            if current and (len(current)>=100 or len(prospective)>c.EVIDENCE_CHUNK_MAX_BYTES):chunks.append(current);current=[]
            current.append(row)
            if len(artifact_bytes(payload(current,len(chunks))))>c.EVIDENCE_CHUNK_MAX_BYTES:
                raise AssemblyError('A single typed row exceeds the artifact budget')
        if current or not chunks:chunks.append(current)
        refs=[]
        for index,items in enumerate(chunks):
            body=payload(items,index);body['chunk_count']=len(chunks);body['total_rows']=len(rows)
            content=artifact_bytes(body)
            if len(content)>c.EVIDENCE_CHUNK_MAX_BYTES:raise AssemblyError('Artifact chunk exceeds budget')
            digest=content_sha256(content);part=f'{dataset_id}-{index:03}'
            ref=c.ResultArtifactReference(artifact_id=uuid5(self.core.decision.run_id,kind+':'+part+':'+digest),workspace_id=self.core.context.workspace_id,
                run_id=self.core.decision.run_id,kind=kind,part_key=part,artifact_schema=schema,schema_version=1,content_sha256=digest,
                size_bytes=len(content),media_type='application/json',core_fingerprint=self.fingerprint,assembler_version=self.assembler_version)
            self.parts.append(PreparedArtifact(ref,content));refs.append(ref)
        return c.ReferenceDataset(dataset_id=dataset_id,row_schema=schema,row_count=len(rows),artifacts=tuple(refs))


def assemble(result,frozen_context=None,versions=None):
    try:
        if getattr(getattr(result,'output',None),'core',None) is not None and result.output.core.result_schema=='day_scheduling_v1':
            from .day_assembler import assemble_day
            return assemble_day(result,frozen_context,versions)
        return _assemble(result,frozen_context,versions or ASSEMBLER_VERSION)
    except (ValueError,KeyError,TypeError,ArithmeticError) as exc:
        if isinstance(exc,AssemblyError):raise
        raise AssemblyError('D1 assembly failed: '+str(exc)) from exc


def _assemble(result,frozen_context,versions):
    plan=result.recommended;core,evidence=plan.output.core,plan.output.evidence
    schema=resolve_schema(core.result_schema,core.result_schema_version)
    if schema.name!='transport_plan_v1' or versions!=ASSEMBLER_VERSION:raise AssemblyError('Unsupported assembler/schema/version')
    if frozen_context is not None and frozen_context!=core.context:raise AssemblyError('Frozen context mismatch')
    from .validation import validate_certified_plan,validate_bundle
    validate_certified_plan(plan)
    builder=ArtifactBuilder(core)
    builder.dataset('core','engine_core_v1',(core,),'CORE')
    proof=builder.dataset('engine-evidence','engine_evidence_v1',evidence_shards(evidence),'EVIDENCE','PARTITIONED_ENGINE_EVIDENCE_V1')
    trips=builder.dataset('plan','transport_trip_v1',tuple(sorted(core.transport_plan.trips,key=lambda t:t.trip_id)))
    unassigned=builder.dataset('unassigned','demand_resolution_v1',core.transport_plan.unassigned_demand)
    demand_rows=tuple(e for e in evidence.entities if e.entity_type=='ORDER')
    demand=builder.dataset('demand','entity_evidence_v1',demand_rows)
    resources=builder.dataset('resources','resource_usage_v1',plan.resource_usage)
    reasons=builder.dataset('reasons','reason_emission_v1',evidence.reasons,'EVIDENCE')
    entity_data=builder.dataset('evidence','entity_evidence_v1',tuple(sorted(evidence.entities,key=lambda e:(e.entity_type,e.entity_id))),'ENTITY_EVIDENCE')
    entity_index=[]
    for entity in evidence.entities:
        if entity.entity_type=='TRIP' or entity.entity_type=='RESOURCE' and entity.entity_id in {t.resource_id for t in core.transport_plan.trips}:
            entity_index.append(c.EntityEvidence(entity_type=entity.entity_type,entity_id=entity.entity_id,
                facts={'graph_node_id':graph_id(entity.entity_type,entity.entity_id),'scope':'ENTITY_SELECTION'},reason_refs=entity.reason_refs))
    # Destination is a Case dimension/filter in T1, not an invented domain
    # EntityType. Its explicit lookup records the real destination field.
    for destination in sorted({t.destination_id for t in core.transport_plan.trips}):
        entity_index.append(c.EntityEvidence(entity_type='CASE',entity_id=str(core.context.case_id),facts={
            'graph_node_id':graph_id('DESTINATION',destination),'destination_id':destination,'scope':'DESTINATION_FILTER'},reason_refs=()))
    index_data=builder.dataset('sankey-entity-index','entity_evidence_v1',tuple(entity_index),'ENTITY_EVIDENCE')
    visual=sankey(core)
    visual_data=visual if len(artifact_bytes(visual))<=c.VISUAL_INLINE_MAX_BYTES else builder.dataset('sankey','sankey_projection_v1',(visual,),'VISUAL')
    exceptions,assumptions=exceptions_and_assumptions(evidence)
    review=build_review(core,evidence,exceptions,assumptions)
    executive=summary(core)
    alternatives=[];alternative_rows=[]
    from app.engines.assignment.transport_policy_result import plan_signature
    for alt in result.alternatives:
        validate_certified_plan(alt)
        ac=alt.output.core;signature=plan_signature(alt);aid='ALT-'+signature[:24]
        alt_plan=builder.dataset(aid+'-plan','transport_trip_v1',tuple(sorted(ac.transport_plan.trips,key=lambda t:t.trip_id)),'ALTERNATIVE_PLAN')
        alt_entities=builder.dataset(aid+'-entities','entity_evidence_v1',alt.output.evidence.entities,'EVIDENCE')
        builder.dataset(aid+'-core','engine_core_v1',(ac,),'ALTERNATIVE_PLAN')
        builder.dataset(aid+'-proof','engine_evidence_v1',evidence_shards(alt.output.evidence),'EVIDENCE','PARTITIONED_ENGINE_EVIDENCE_V1')
        cost=ac.metrics.total_cost.amount if ac.metrics.total_cost else None
        current_cost=core.metrics.total_cost.amount if core.metrics.total_cost else None
        own=ac.metrics.resource_mix.own_trip_ratio;current_own=core.metrics.resource_mix.own_trip_ratio
        difference=c.AlternativeDifference(cost_delta=cost-current_cost if cost is not None and current_cost is not None else None,
            trip_delta=ac.metrics.trip_count-core.metrics.trip_count,own_share_delta=own-current_own if own is not None and current_own is not None else None)
        metrics=c.AlternativeMetrics(total_cost=cost,trip_count=ac.metrics.trip_count,coverage_ratio=ac.metrics.demand_coverage.ratio,own_trip_ratio=own)
        alternatives.append(c.AlternativeDescriptor(alternative_id=aid,policy=alt.exploration_goal,metrics=metrics,difference_vs_recommended=difference,
            material_differences=('TRIP_ALLOCATIONS_OR_RESOURCE_ASSIGNMENTS',),plan=alt_plan,evidence=alt_entities))
        alternative_rows.append(c.EntityEvidence(entity_type='ALTERNATIVE',entity_id=aid,facts={'policy':alt.exploration_goal,'solver_status':ac.engine.solver_status,
            'plan_fingerprint':signature,'core_result_fingerprint':core_result_fingerprint(ac),'total_cost':cost,'trip_count':metrics.trip_count,
            'coverage_ratio':metrics.coverage_ratio,'own_trip_ratio':metrics.own_trip_ratio,'cost_delta':difference.cost_delta,'trip_delta':difference.trip_delta,'own_share_delta':difference.own_share_delta},reason_refs=()))
    alt_data=builder.dataset('alternatives','entity_evidence_v1',tuple(sorted(alternative_rows,key=lambda r:r.entity_id)))
    exception_rows=tuple(c.EntityEvidence(entity_type=e.entity_type,entity_id=e.entity_ids[0],facts={'exception_id':e.exception_id,'code':e.code,'category':e.category,'severity':e.severity,**e.facts},reason_refs=(e.reason_ref,)) for e in exceptions)
    exception_data=builder.dataset('exceptions','entity_evidence_v1',exception_rows)
    # T1's detail union intentionally uses EntityEvidence for the two metadata
    # projections; dataset IDs distinguish them without inventing an ABI enum.
    currency=core.context.currency_policy.currency;dimension=core.context.primary_dimension
    details=(descriptor('plan','PLAN',trips,[('trip_id','ID',None),('estimated_cost','MONEY',currency)],('trip_id',)),
        descriptor('demand','DEMAND',demand,[('entity_id','ID',None),('facts.requested_'+dimension,'DECIMAL',dimension),('facts.residual_'+dimension,'DECIMAL',dimension),('facts.status','STATUS',None),('facts.coverage_ratio','RATIO',None)],('entity_id',)),
        descriptor('resources','RESOURCES',resources,[('resource_id','ID',None),('total_cost','MONEY',currency)],('resource_id',)),
        descriptor('alternatives','EVIDENCE',alt_data,[('entity_id','ID',None),('facts.total_cost','MONEY',currency)],('entity_id',)),
        descriptor('exceptions','EVIDENCE',exception_data,[('entity_id','ID',None),('facts.code','STATUS',None)],('facts.exception_id',)),
        descriptor('evidence','EVIDENCE',entity_data,[('entity_type','TEXT',None),('entity_id','ID',None)],('entity_type','entity_id')))
    analysis=c.EntityEvidence(entity_type='CASE',entity_id=str(core.context.case_id),facts={'alternatives_status':result.alternatives_status,
        'materiality_version':'D1_MATERIALITY_V1','materiality_rule':'DIFFERENT_RESOURCE_OR_ALLOCATIONS','max_alternatives':3,
        'exploration_scope':'BOUNDED_POLICY_SET_V1','explored_goals':result.explored_goals},reason_refs=())
    analysis_data=builder.dataset('analysis-status','entity_evidence_v1',(analysis,),'EVIDENCE')
    light_constraints=tuple(v for v in evidence.constraints if v.code=='POLICY_CERTIFICATE' or v.code in {g.kind for g in core.context.node_policy.guardrails})
    evidence_summary=c.EvidenceSummary(solver=evidence.solver,policy=evidence.policy,constraints=light_constraints,reason_emissions=reasons,parts=(proof,entity_data,index_data,analysis_data))
    export=builder.dataset('transport-plan-export','export_rows_v1',transport_export_rows(core),'EXPORT_ROWS') if core.feasibility.solution_found else None
    base=build_base(plan,executive,evidence_summary,exceptions,assumptions,review,alternatives)
    ai=builder.dataset('decision-context-base','decision_context_v1',(base,),'AI_BASE','DECISION_CONTEXT_BASE_V1')
    fingerprints=dict(input_context_hash=core.input_context_hash,core_result_fingerprint=core_result_fingerprint(core),
        model_version=core.context.logistics_model_version,data_pack_version=core.context.data_pack_version,
        case_policy_hash=policy_hash(core.context.case_policy),node_policy_hash=policy_hash(core.context.node_policy),
        contract_hash=core.context.contract_hash,engine_version=core.engine.engine_version,upstream_result_fingerprint=None)
    fields=dict(result_schema=core.result_schema,assembler_version=ASSEMBLER_VERSION,decision=core.decision,context=core.context,engine=core.engine,
        feasibility=core.feasibility,transport_plan=c.PublishedTransportPlan(trips=trips,unassigned_demand=unassigned,capacity_gap=core.transport_plan.capacity_gap),
        schedule=None,source_transport_plan=None,summary=executive,metrics=core.metrics,primary_visual=c.PrimaryVisual(type='SANKEY',projection=visual_data),
        details=details,alternatives=tuple(alternatives),alternatives_state='COMPUTED' if alternatives else 'COMPUTED_NONE' if result.alternatives_status=='NO_MATERIAL_ALTERNATIVE' else 'NOT_COMPUTED',
        exceptions=exceptions,assumptions=assumptions,evidence=evidence_summary,approval_review=review,
        exports=c.Exports.model_validate({'csv':dict(available=core.feasibility.solution_found,type='TRANSPORT_PLAN',granularity='TRIP_ORDER',cost_scope='TRIP_ONCE',rows=export),
            'json':dict(available=True,type='DECISION_RESULT_PACKAGE',granularity='PACKAGE')}),ai_context=c.AIContextReference(base_context=ai),
        artifact_manifest=c.ArtifactManifest(artifacts=tuple(p.reference for p in builder.parts)),fingerprints=fingerprints)
    # Canonicalize the typed draft as a mapping; no model_construct or public
    # placeholder fingerprint. The hash excludes only its own final field.
    fields.update(result_schema_version=1,package_version=1)
    fields['fingerprints']['canonical_version']='DATION_CANONICAL_V1'
    fields['fingerprints']['transit_model_version']=core.engine.transit_model_version
    fields['fingerprints']['result_fingerprint']=result_fingerprint(canonical_tree(fields))
    package=c.DecisionResultPackageV1.model_validate(fields)
    context=bind_context(base,package)
    bundle=AssemblyBundle(package,tuple(builder.parts),context,result)
    validate_bundle(bundle)
    return bundle
