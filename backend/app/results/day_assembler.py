"""D2 specialization of the shared Result Package / ArtifactBuilder boundary."""
from . import contracts as c
from .canonical import canonical_tree,artifact_bytes,core_result_fingerprint,result_fingerprint,policy_hash
from .assembler import ArtifactBuilder,AssemblyBundle,AssemblyError
from .projections import descriptor,evidence_shards
from .ai_context import build_base,bind_context
from .day_projections import day_gantt,day_summary,trip_facts,day_export_rows,day_exceptions,day_review

ASSEMBLER_VERSION='RESULT_ASSEMBLER_D2_V1'

def assemble_day(result,frozen_context=None,versions=None):
    from app.engines.scheduling.day_validator import certify_schedule
    certify_schedule(result);core=result.output.core;evidence=result.output.evidence
    if versions not in (None,ASSEMBLER_VERSION) or frozen_context is not None and frozen_context!=core.context:raise AssemblyError('D2 assembler/version/context mismatch')
    builder=ArtifactBuilder(core,ASSEMBLER_VERSION)
    builder.dataset('core','engine_core_v1',(core,),'CORE')
    proof=builder.dataset('engine-evidence','engine_evidence_v1',evidence_shards(evidence),'EVIDENCE','PARTITIONED_ENGINE_EVIDENCE_V1')
    schedule=builder.dataset('schedule','day_schedule_trip_v1',core.schedule.trips)
    trips=builder.dataset('trips','entity_evidence_v1',trip_facts(result))
    resources=builder.dataset('resources','resource_timeline_v1',result.resource_timeline)
    service=builder.dataset('service','service_analysis_v1',result.service_analysis)
    entities=builder.dataset('evidence','entity_evidence_v1',evidence.entities,'ENTITY_EVIDENCE')
    reasons=builder.dataset('reason-emissions','reason_emission_v1',evidence.reasons,'EVIDENCE')
    exceptions=day_exceptions(result);assumptions=();review=day_review(result,exceptions);summary=day_summary(result)
    ex_rows=tuple(c.EntityEvidence(entity_type='TRIP',entity_id=e.entity_ids[0],facts={'exception_id':e.exception_id,'code':e.code,**e.facts},reason_refs=(e.reason_ref,)) for e in exceptions)
    ex_data=builder.dataset('exceptions','entity_evidence_v1',ex_rows)
    visual=day_gantt(result)
    visual_data=visual if len(artifact_bytes(visual))<=c.VISUAL_INLINE_MAX_BYTES else builder.dataset('day-gantt','day_gantt_projection_v1',(visual,),'VISUAL')
    parts=(proof,entities)
    evidence_summary=c.EvidenceSummary(solver=evidence.solver,policy=evidence.policy,constraints=tuple(v for v in evidence.constraints if v.code in ('POLICY_CERTIFICATE','SCHEDULE_FEASIBILITY')),reason_emissions=reasons,parts=parts)
    export=builder.dataset('day-schedule-export','export_rows_v1',day_export_rows(core),'EXPORT_ROWS')
    base=build_base(result,summary,evidence_summary,exceptions,assumptions,review,())
    ai=builder.dataset('decision-context-base','decision_context_v1',(base,),'AI_BASE','DECISION_CONTEXT_BASE_V1')
    details=(descriptor('schedule','SCHEDULE',schedule,[('trip_id','ID',None),('dispatch_date','DATE',None),('expected_arrival_date','DATE',None),('schedule_margin_days','COUNT','calendar_days'),('status','STATUS',None)],('trip_id',)),
        descriptor('trips','TRIPS',trips,[('entity_id','ID',None),('facts.resource_id','ID',None),('facts.order_ids','TEXT',None)],('entity_id',)),
        descriptor('resources','RESOURCES',resources,[('resource_id','ID',None),('resource_source','TEXT',None)],('resource_id',)),
        descriptor('service','SERVICE',service,[('trip_id','ID',None),('margin_days','COUNT','calendar_days'),('status','STATUS',None)],('trip_id',)),
        descriptor('exceptions','EVIDENCE',ex_data,[('entity_id','ID',None),('facts.code','STATUS',None)],('entity_id',)),
        descriptor('evidence','EVIDENCE',entities,[('entity_type','TEXT',None),('entity_id','ID',None)],('entity_type','entity_id')))
    # Service order is certified by the engine, independent of its primary key.
    details=tuple(d.model_copy(update={'stable_order':('margin_days','trip_id')}) if d.dataset_id=='service' else d for d in details)
    fields=dict(result_schema='day_scheduling_v1',result_schema_version=1,package_version=1,assembler_version=ASSEMBLER_VERSION,decision=core.decision,context=core.context,engine=core.engine,
        feasibility=core.feasibility,transport_plan=None,schedule=c.PublishedSchedule(trips=schedule),source_transport_plan=core.source_transport_plan,summary=summary,metrics=core.metrics,
        primary_visual=c.PrimaryVisual(type='DAY_GANTT',projection=visual_data),details=details,alternatives=(),alternatives_state='NOT_COMPUTED',exceptions=exceptions,assumptions=assumptions,
        evidence=evidence_summary,approval_review=review,exports=c.Exports.model_validate({'csv':{'available':True,'type':'DAY_SCHEDULE','granularity':'TRIP','rows':export},'json':{'available':True,'type':'DECISION_RESULT_PACKAGE','granularity':'PACKAGE'}}),
        ai_context=c.AIContextReference(base_context=ai),artifact_manifest=c.ArtifactManifest(artifacts=tuple(p.reference for p in builder.parts)),
        fingerprints={'canonical_version':'DATION_CANONICAL_V1','input_context_hash':core.input_context_hash,'core_result_fingerprint':core_result_fingerprint(core),'model_version':core.context.logistics_model_version,
            'data_pack_version':core.context.data_pack_version,'case_policy_hash':policy_hash(core.context.case_policy),'node_policy_hash':policy_hash(core.context.node_policy),'contract_hash':core.context.contract_hash,
            'engine_version':core.engine.engine_version,'transit_model_version':core.engine.transit_model_version,'upstream_result_fingerprint':core.source_transport_plan.result_fingerprint})
    fields['fingerprints']['result_fingerprint']=result_fingerprint(canonical_tree(fields))
    package=c.DecisionResultPackageV1.model_validate(fields);bundle=AssemblyBundle(package,tuple(builder.parts),bind_context(base,package),result)
    from .validation import validate_bundle
    validate_bundle(bundle);return bundle
