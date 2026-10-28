"""T8 admission and worker adapter. Mathematical production remains T7 only."""
import asyncio,json
from datetime import datetime,timezone
from uuid import UUID
from fastapi import HTTPException
from app.platform.identity import platform_call
from app.platform.context import current
from app.domain.logistics.contracts import FrozenCaseContext,NodePolicy,SemanticInput
from app.domain.logistics.definitions import DEFINITIONS,definition_hash
from app.domain.logistics.requirements import read_identity,input_requirements
from app.domain.logistics.units import QuantityVector
from app.results.canonical import canonical_tree,input_context_hash,policy_hash,content_sha256,canonical_bytes,core_result_fingerprint
from app.results.registry import resolve_persisted_runtime,resolve_test_policy,resolve_worker_producer
from app.engines.assignment.transport_plan import IDENTITY
from app.engines.assignment.transport_contracts import TransportPlanInput
from app.services.logistics_model_service import enrich_context
from app.services import case_data_pack_service as inputs


async def call(ctx,operation,**arguments):
    return await platform_call('platform_ultimate_execution',{'target_workspace_id':ctx.workspace_id,'actor_user_id':ctx.user_id,'operation':operation,'arguments':canonical_tree(arguments)})


def pinned_context(raw,node_policy=None):
    planning=enrich_context(raw)['planning_context'];model=planning['model'];row=raw['case'];pv=raw['pack_version']
    policy=NodePolicy.model_validate(node_policy or row['case_policy_jsonb'])
    from app.domain.logistics.contracts import CasePolicy
    policy.validate_case_policy(CasePolicy.model_validate(row['case_policy_jsonb']))
    refs=[e for e in raw['pinned_entries'] if e['slot_key'] in ('transport_demand','transport_resources')]
    context=FrozenCaseContext(workspace_id=row['workspace_id'],case_id=row['id'],case_name=row['label'],
        operating_role=model['operating_role'],logistics_model_id=model['model_id'],logistics_model_version_id=model['version_id'],logistics_model_version=model['version'],
        data_pack_version_id=pv['id'],data_pack_version=pv['version'],model_hash=model['configuration_hash'],pack_manifest_hash=pv['manifest_hash'],
        graph_version=row['graph_definition_version'],contract_hash=raw['model_version']['contract_hash'],planning_start=row['planning_start'],planning_end=row['planning_end'],
        case_policy=row['case_policy_jsonb'],node_policy=policy,currency_policy=model['currency_policy'],primary_dimension=model['primary_dimension'],active_dimensions=model['active_dimensions'],
        read_set=tuple(SemanticInput(slot=e['slot_key'],canonical_sha256=e['canonical_sha256'],contract_hash=e['contract_hash'],normalizer_version=e['normalizer_version']) for e in refs))
    return model,context,refs


async def configuration(ctx,case_id,node_id='logistics_assignment'):
    raw=await call(ctx,'state',case_id=str(case_id),node_id=node_id)
    try:model,frozen,refs=pinned_context(raw)
    except ValueError:raise HTTPException(409,'Completá y publicá los inputs del Case antes de ejecutar.') from None
    source=None;identity=IDENTITY
    if node_id=='logistics_scheduling':
        from app.engines.scheduling.day_scheduling import IDENTITY as D2
        identity=D2;source={'run_id':raw['source_run']['id'],'result_fingerprint':raw['source_run']['result_fingerprint']}
    return {'context':canonical_tree(frozen),'expected_context_hash':input_context_hash(frozen,identity,source),'model_version_id':str(frozen.logistics_model_version_id),
        'data_pack_version_id':str(frozen.data_pack_version_id),'node_policy':canonical_tree(frozen.node_policy),
        'admission_available':raw['admissions_enabled'] and (node_id=='logistics_assignment' or raw.get('scheduling_enabled',False)),
        'runtime_profile':identity.runtime_profile,'d2_runtime_available':raw.get('scheduling_enabled',False),'source_transport_plan':source}


async def source_facts(package,rows):
    from app.services import result_artifact_service as artifacts
    from app.results.validation import reassemble_evidence
    from app.results import contracts as c
    from app.results.ai_context import DecisionContextBase
    package,_=artifacts.bound_rows(package,rows);await artifacts.verify_all(package,rows)
    core_ref=next(a for a in rows if a['kind']=='CORE')
    core=c.EngineCoreResult.model_validate(json.loads(await artifacts.read(core_ref))['rows'][0])
    proof=next(d for d in package.evidence.parts if d.dataset_id=='engine-evidence')
    evidence=reassemble_evidence(await artifacts.dataset(proof,rows))
    base=DecisionContextBase.model_validate((await artifacts.dataset(package.ai_context.base_context,rows))[0])
    c.EngineOutput(core=core,evidence=evidence)
    if core_result_fingerprint(core)!=package.fingerprints.core_result_fingerprint:raise HTTPException(409,'Upstream Core binding mismatch')
    return core,evidence,base.input_summary


async def verify_inputs(entry_refs):
    records={}
    for ref in entry_refs:
        # SQL metadata reserves this exact private path; it never comes from the
        # browser, and an immutable hash/size binds the normalized snapshot.
        expected=f"{ref['workspace_id']}/normalized/{ref['dataset_id']}/{ref['canonical_sha256']}.json"
        if ref['normalized_path']!=expected:raise HTTPException(409,'La referencia de input no coincide con su snapshot.')
        blob=await inputs.read_object(ref['normalized_bucket'],expected,ref['canonical_sha256'],ref['normalized_size'])
        data=json.loads(blob)
        if data['schema_version']!='normalized_logistics_input_v1' or data['semantic_entity']!=ref['slot_key'] or data['contract_hash']!=ref['contract_hash'] or data['normalizer_version']!=ref['normalizer_version'] or data['model_version_id']!=ref['model_version_id']:
            raise HTTPException(409,'El snapshot normalizado no corresponde a la interpretación fijada.')
        records[ref['slot_key']]=data['records']
    return records


async def enqueue(ctx,payload,run_id):
    request=payload.model_dump(mode='python')
    replay=await call(ctx,'replay',case_id=str(payload.case_id),run_id=str(run_id),client_request=request)
    if replay['replayed']:return replay['run']
    raw=await call(ctx,'state',case_id=str(payload.case_id),node_id=payload.node_id,source_transport_plan=payload.source_transport_plan)
    model,frozen,refs=pinned_context(raw,payload.node_policy)
    from app.engines.scheduling.day_scheduling import IDENTITY as D2
    identity=IDENTITY if payload.node_id=='logistics_assignment' else D2
    if input_context_hash(frozen,identity,payload.source_transport_plan)!=payload.expected_context_hash or frozen.logistics_model_version_id!=payload.model_version_id or frozen.data_pack_version_id!=payload.data_pack_version_id:
        raise HTTPException(409,'El contexto cambió. Recuperá la configuración antes de crear otra intención.')
    definition=next(d for d in DEFINITIONS if d.id==payload.node_id)
    missing=input_requirements(definition,raw['model_version'],raw['entries'],canonical_tree(frozen.node_policy))
    if missing:raise HTTPException(409,{'message':'Faltan requisitos publicados de D1.','requirements':missing})
    upstream={}
    if payload.node_id=='logistics_assignment':
        records=await verify_inputs(refs)
        input_=TransportPlanInput(model=model,context=frozen,demands=records['transport_demand'],resources=records['transport_resources'],run_id=run_id,result_generated_at=datetime.now(timezone.utc))
    else:
        from app.engines.scheduling.day_contracts import DaySchedulingInput
        core,evidence,summary=await source_facts(raw['source_run']['result_json'],raw['source_artifacts'])
        input_=DaySchedulingInput(model=model,context=frozen,source_core=core,source_evidence=evidence,source_transport_plan=payload.source_transport_plan,
            resources=raw['source_input']['resources'],input_summary=summary,run_id=run_id,result_generated_at=datetime.now(timezone.utc))
        upstream={'logistics_assignment':{'node_state':'APPROVED','approved_run_id':raw['source_run']['id']}}
    reads=read_identity(definition,raw['case'],raw['entries'],upstream,node_policy=policy_hash(frozen.node_policy))
    body=await call(ctx,'admit',run_id=str(run_id),case_id=str(payload.case_id),client_request=request,input=input_,entries=refs,
        dataset_id=next(r['dataset_id'] for r in refs if r['slot_key']=='transport_demand'),graph_snapshot={'definition_hash':definition_hash(),'read_set':reads})
    return body['run']


async def execute_job(job,progress=None):
    from app.services import result_artifact_service as artifacts
    ctx=current();request=job['request_json']
    registration=resolve_persisted_runtime(request)
    from app.engines.scheduling.day_scheduling import IDENTITY as D2
    if registration.identity not in (IDENTITY,D2):raise ValueError('Unsupported Ultimate job runtime identity')
    if registration.identity==D2:
        from app.engines.scheduling.day_contracts import DaySchedulingInput
        input_=DaySchedulingInput.model_validate(request['input'])
        source,evidence,summary=await source_facts(request['source_package'],request['source_artifacts'])
        if canonical_bytes((source,evidence,summary))!=canonical_bytes((input_.source_core,input_.source_evidence,input_.input_summary)):raise ValueError('Published upstream differs from frozen D2 input')
    else:input_=TransportPlanInput.model_validate(request['input'])
    if str(input_.run_id)!=job['run_id'] or str(input_.context.workspace_id)!=ctx.workspace_id:raise ValueError('Worker input binding mismatch')
    if registration.identity==IDENTITY:
        records=await verify_inputs(request['entries'])
        if canonical_bytes(input_.demands)!=canonical_bytes(records['transport_demand']) or canonical_bytes(input_.resources)!=canonical_bytes(records['transport_resources']):raise ValueError('Pinned input records changed')
    lease={'run_id':job['run_id'],'worker_token':job['lease_token']}
    prepared=await call(ctx,'prepared',**lease)
    if prepared['publication'] is not None:
        recovered=await artifacts.verify_all(prepared['publication']['package'],prepared['artifacts'],missing=True)
        if recovered:return (await call(ctx,'finish',**lease,result_fingerprint=prepared['publication']['result_fingerprint'],verified_manifest_hash=prepared['publication']['manifest_hash']))['run']
    producer=resolve_worker_producer(request)
    result=await asyncio.to_thread(producer,input_)
    from app.results.assembler import assemble
    bundle=await asyncio.to_thread(assemble,result,input_.context)
    if progress:progress('publishing')
    reserved=await call(ctx,'prepare',**lease,package=bundle.package,artifact_indexes=artifacts.indexes(bundle))
    expected={str(a.reference.artifact_id):a for a in bundle.artifacts}
    for ref in reserved['artifacts']:
        artifact=expected.get(ref['id'])
        if artifact is None:raise ValueError('Prepared artifact belongs to another candidate')
        await artifacts.upload(ref,artifact.content)
    await artifacts.verify_all(reserved['package'],reserved['artifacts'])
    manifest_hash=content_sha256(canonical_bytes(bundle.package.artifact_manifest.artifacts))
    return (await call(ctx,'finish',**lease,result_fingerprint=bundle.package.fingerprints.result_fingerprint,verified_manifest_hash=manifest_hash))['run']
