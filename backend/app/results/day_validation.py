"""D2 cross-projection certifier. Checks facts; never repairs dates or schedules."""
import json
from . import contracts as c
from .canonical import canonical_bytes,artifact_bytes,content_sha256
from .validation import read_delivery,reassemble_evidence

def validate_day_bundle(bundle):
    from app.engines.scheduling.day_validator import certify_schedule
    from .day_projections import day_gantt,day_summary,trip_facts,day_export_rows,day_review,day_exceptions
    from .ai_context import DecisionContextBase,bind_context
    def require(ok,message):
        if not ok:raise ValueError('D2 package: '+message)
    def same(a,b,message):require(canonical_bytes(a)==canonical_bytes(b),message)
    result=bundle.result;core=result.output.core;evidence=result.output.evidence;package=c.DecisionResultPackageV1.model_validate(bundle.package)
    certify_schedule(result);c.ResultContractBundle(core=core,evidence=evidence,package=package)
    require(len(bundle.artifacts)==len({a.reference.artifact_id for a in bundle.artifacts}),'Duplicate artifact')
    require(set(package.artifact_manifest.artifacts)=={a.reference for a in bundle.artifacts},'Manifest differs')
    for a in bundle.artifacts:
        require(len(a.content)==a.reference.size_bytes and len(a.content)<=c.EVIDENCE_CHUNK_MAX_BYTES and content_sha256(a.content)==a.reference.content_sha256,'Artifact integrity')
        body=json.loads(a.content);require(artifact_bytes(body)==a.content,'Noncanonical artifact')
        row_type=DecisionContextBase if body['row_semantics']=='DECISION_CONTEXT_BASE_V1' else c._row_schema_type(a.reference.artifact_schema)
        for row in body['rows']:
            if row_type is not dict:row_type.model_validate(row)
    def rows(d):return read_delivery(d,bundle.artifacts)
    def named(name):
        parts=sorted([a for a in bundle.artifacts if json.loads(a.content)['dataset_id']==name],key=lambda a:json.loads(a.content)['chunk_index'])
        require(bool(parts),'Missing '+name);h=json.loads(parts[0].content)
        return rows(c.ReferenceDataset(dataset_id=name,row_schema=h['row_schema'],row_count=h['total_rows'],artifacts=tuple(a.reference for a in parts)))
    same(named('core'),[core],'Core changed');same(rows(package.schedule.trips),core.schedule.trips,'Schedule changed')
    details={d.dataset_id:d for d in package.details};require(set(details)=={'schedule','trips','resources','service','exceptions','evidence'},'Missing six D2 datasets')
    for key,expected in [('schedule',core.schedule.trips),('trips',trip_facts(result)),('resources',result.resource_timeline),('service',result.service_analysis),('evidence',evidence.entities)]:same(rows(details[key].data),expected,key+' differs')
    visual=package.primary_visual.projection
    if isinstance(visual,c.ReferenceDataset):visual=c.GanttProjection.model_validate(rows(visual)[0])
    same(visual,day_gantt(result),'Gantt dates/occupancy changed');same(rows(package.exports.csv.rows),day_export_rows(core),'CSV rows changed')
    require(len(rows(package.exports.csv.rows))==len(result.source.source_core.transport_plan.trips),'CSV omits source Trips')
    same(package.metrics,core.metrics,'Metric changed');same(package.summary,day_summary(result),'Summary changed')
    same(rows(package.evidence.reason_emissions),evidence.reasons,'Reason changed')
    restored=reassemble_evidence(named('engine-evidence'))
    for field,key in [('constraints','evidence_id'),('reasons','emission_id')]:same({getattr(v,key):v for v in getattr(restored,field)},{getattr(v,key):v for v in getattr(evidence,field)},'Evidence differs')
    same(package.exceptions,day_exceptions(result),'Exception invented');same(package.approval_review,day_review(result,package.exceptions),'Review changed')
    same(bind_context(DecisionContextBase.model_validate(rows(package.ai_context.base_context)[0]),package),bundle.context,'Context binding changed')
    require(package.fingerprints.upstream_result_fingerprint==result.source.source_transport_plan.result_fingerprint,'Wrong upstream fingerprint')
    return True
