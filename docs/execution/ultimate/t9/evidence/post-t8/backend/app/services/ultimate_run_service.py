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
from app.results.canonical import canonical_tree,input_context_hash,policy_hash,content_sha256,canonical_bytes
from app.results.registry import resolve_persisted_runtime,resolve_test_policy
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


async def configuration(ctx,case_id):
    raw=await call(ctx,'state',case_id=str(case_id))
    try:model,frozen,refs=pinned_context(raw)
    except ValueError:raise HTTPException(409,'Completá y publicá los inputs del Case antes de ejecutar.') from None
    return {'context':canonical_tree(frozen),'expected_context_hash':input_context_hash(frozen,IDENTITY),'model_version_id':str(frozen.logistics_model_version_id),
        'data_pack_version_id':str(frozen.data_pack_version_id),'node_policy':canonical_tree(frozen.node_policy),
        'admission_available':raw['admissions_enabled'],'runtime_profile':'transport_plan_v1','d2_runtime_available':False}


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
    if payload.node_id!='logistics_assignment':raise HTTPException(409,'Day Scheduling todavía no admite ejecuciones Ultimate.')
    raw=await call(ctx,'state',case_id=str(payload.case_id))
    model,frozen,refs=pinned_context(raw,payload.node_policy)
    if input_context_hash(frozen,IDENTITY)!=payload.expected_context_hash or frozen.logistics_model_version_id!=payload.model_version_id or frozen.data_pack_version_id!=payload.data_pack_version_id:
        raise HTTPException(409,'El contexto cambió. Recuperá la configuración antes de crear otra intención.')
    missing=input_requirements(DEFINITIONS[0],raw['model_version'],raw['entries'],canonical_tree(frozen.node_policy))
    if missing:raise HTTPException(409,{'message':'Faltan requisitos publicados de D1.','requirements':missing})
    records=await verify_inputs(refs)
    input_=TransportPlanInput(model=model,context=frozen,demands=records['transport_demand'],resources=records['transport_resources'],run_id=run_id,result_generated_at=datetime.now(timezone.utc))
    reads=read_identity(DEFINITIONS[0],raw['case'],raw['entries'],{},node_policy=policy_hash(frozen.node_policy))
    body=await call(ctx,'admit',run_id=str(run_id),case_id=str(payload.case_id),client_request=request,input=input_,entries=refs,
        dataset_id=next(r['dataset_id'] for r in refs if r['slot_key']=='transport_demand'),graph_snapshot={'definition_hash':definition_hash(),'read_set':reads})
    return body['run']


async def execute_job(job,progress=None):
    from app.services import result_artifact_service as artifacts
    ctx=current();request=job['request_json']
    registration=resolve_persisted_runtime(request)
    if registration.identity!=IDENTITY:raise ValueError('Unsupported Ultimate job runtime identity')
    input_=TransportPlanInput.model_validate(request['input'])
    if str(input_.run_id)!=job['run_id'] or str(input_.context.workspace_id)!=ctx.workspace_id:raise ValueError('Worker input binding mismatch')
    records=await verify_inputs(request['entries'])
    if canonical_bytes(input_.demands)!=canonical_bytes(records['transport_demand']) or canonical_bytes(input_.resources)!=canonical_bytes(records['transport_resources']):raise ValueError('Pinned input records changed')
    lease={'run_id':job['run_id'],'worker_token':job['lease_token']}
    prepared=await call(ctx,'prepared',**lease)
    if prepared['publication'] is not None:
        recovered=await artifacts.verify_all(prepared['publication']['package'],prepared['artifacts'],missing=True)
        if recovered:return (await call(ctx,'finish',**lease,result_fingerprint=prepared['publication']['result_fingerprint'],verified_manifest_hash=prepared['publication']['manifest_hash']))['run']
    producer=resolve_test_policy(registration.identity)
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
