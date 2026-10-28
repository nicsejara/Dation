"""T3 application services over checked SQL RPC. No service-key table writes."""
from uuid import UUID, uuid5
from fastapi import HTTPException

from app.models.ultimate_foundation import LogisticsModelConfigurationV1, PlanningContextV1
from app.domain.logistics.contracts import LogisticsModelVersion, Demand, TransportResource
from app.results.canonical import canonical_bytes, canonical_tree, content_sha256, policy_hash
from app.platform.identity import platform_call

GRAPH_VERSION='ULTIMATE_FOUNDATION_V1'
CONTRACT_REGISTRY_VERSION='ULTIMATE_DOMAIN_V1'


def snapshot_hash(kind,value):
    return content_sha256(canonical_bytes({'canonical_version':'DATION_CANONICAL_V1','kind':kind,'value':value}))


def configuration_snapshot(config):
    value=canonical_tree(LogisticsModelConfigurationV1.model_validate(config))
    return value,snapshot_hash('logistics_model_configuration_v1',value)


def contract_reference(configuration_hash):
    """References the static T1 domain ABI; does not compile CSV/slot contracts."""
    value={'schema_version':'ultimate_model_domain_reference_v1','registry_version':CONTRACT_REGISTRY_VERSION,
        'configuration_hash':configuration_hash,'domain_schema_sha256':{
            'Demand':content_sha256(canonical_bytes(Demand.model_json_schema())),
            'TransportResource':content_sha256(canonical_bytes(TransportResource.model_json_schema()))}}
    return value,snapshot_hash('ultimate_model_domain_reference_v1',value)


async def call(ctx,operation,arguments=None):
    return await platform_call('platform_ultimate_foundation',{'target_workspace_id':ctx.workspace_id,
        'actor_user_id':ctx.user_id,'operation':operation,'arguments':arguments or {}})


async def capabilities(ctx):return await call(ctx,'capabilities')


async def list_models(ctx,**options):return await call(ctx,'model_list',options)


async def get_model(ctx,model_id):return await call(ctx,'model_get',{'model_id':str(model_id)})


async def create_model(ctx,payload):
    config,hash_=configuration_snapshot(payload.configuration)
    body=payload.model_dump(mode='json',exclude={'configuration'})
    return await call(ctx,'model_create',{**body,'configuration':config,'configuration_hash':hash_,
        'creation_intent_hash':snapshot_hash('model_creation_intent_v1',{'actor':ctx.user_id,**body,'configuration':config})})


async def update_model(ctx,model_id,payload):
    config,hash_=configuration_snapshot(payload.configuration)
    return await call(ctx,'model_update',{'model_id':str(model_id),**payload.model_dump(mode='json',exclude={'configuration'}),
        'configuration':config,'configuration_hash':hash_})


async def publish_model(ctx,model_id,payload):
    model=await get_model(ctx,model_id)
    # SQL resolves replay before checking mutable draft/revision/status.
    existing=next((v for v in model['versions'] if v['id']==str(payload.version_id)),None)
    if existing:
        return await call(ctx,'model_publish',{'model_id':str(model_id),**payload.model_dump(mode='json')})
    config,hash_=configuration_snapshot(model['model']['draft_config_jsonb'])
    descriptor,contract_hash=contract_reference(hash_)
    return await call(ctx,'model_publish',{'model_id':str(model_id),**payload.model_dump(mode='json'),
        'configuration_hash':hash_,'contract_descriptor':descriptor,'contract_hash':contract_hash})


def empty_pack_snapshot(workspace_id,case_id):
    case_id=UUID(str(case_id));pack_id=uuid5(case_id,'data-pack-v1');version_id=uuid5(case_id,'data-pack-version-1')
    manifest={'version':1,'workspace_id':workspace_id,'case_id':str(case_id),'pack_id':str(pack_id),
              'pack_version_id':str(version_id),'entries':[]}
    return {'pack_id':str(pack_id),'pack_version_id':str(version_id),
        'manifest_hash':snapshot_hash('case_data_pack_manifest_v1',manifest),
        'contract_set_hash':snapshot_hash('case_data_pack_contract_set_v1',[])}


async def create_case(ctx,payload):
    body=payload.model_dump(mode='json');policy=canonical_tree(payload.case_policy)
    result=await call(ctx,'case_create',{**body,'case_policy':policy,'case_policy_hash':policy_hash(payload.case_policy),
        **empty_pack_snapshot(ctx.workspace_id,payload.id),
        'creation_intent_hash':snapshot_hash('case_creation_intent_v1',{'actor':ctx.user_id,**body})})
    return enrich_context(result)


def enrich_context(result):
    row=result['case'];version=result['model_version'];pack=result['pack'];pv=result['pack_version']
    config=LogisticsModelConfigurationV1.model_validate(version['config_jsonb'])
    model=LogisticsModelVersion(workspace_id=row['workspace_id'],model_id=version['model_id'],version_id=version['id'],
        version=version['version'],operating_role=config.operating_role,transport_pattern=config.transport_pattern,
        allowed_sources=config.allowed_sources,active_dimensions=config.active_dimensions,primary_dimension=config.primary_dimension,
        homogeneous_loads_declared=config.homogeneous_loads_declared,split_permitted=config.split_permitted,
        currency_policy=config.currency_policy,contract_registry_version=version['contract_registry_version'],configuration_hash=version['config_hash'])
    context=PlanningContextV1(workspace_id=row['workspace_id'],case_id=row['id'],planning_start=row['planning_start'],planning_end=row['planning_end'],
        operating_mode=row['operating_mode'],horizon_type=row.get('horizon_type'),model=model,case_policy=row['case_policy_jsonb'],
        case_policy_hash=row['case_policy_hash'],graph_definition_version=row['graph_definition_version'],
        data_pack_id=pack['id'],data_pack_version_id=pv['id'],data_pack_version=pv['version'],pack_manifest_hash=pv['manifest_hash'],
        contract_hash=version['contract_hash'],context_frozen_at=row['context_frozen_at'])
    # Display/Owner/freeze audit time is not part of the mathematical context.
    projection=context.model_dump(mode='python',exclude={'context_frozen_at'})
    return {**result,'planning_context':canonical_tree(context),'planning_context_hash':snapshot_hash('planning_context_v1',projection)}


async def get_case_context(ctx,case_id):return enrich_context(await call(ctx,'case_get',{'case_id':str(case_id)}))


async def update_case_context(ctx,case_id,payload):
    changes=payload.model_dump(mode='json',exclude={'expected_updated_at','owner_updates'},exclude_unset=True)
    if payload.case_policy is not None:
        changes['case_policy']=canonical_tree(payload.case_policy);changes['case_policy_hash']=policy_hash(payload.case_policy)
    result=await call(ctx,'case_update',{'case_id':str(case_id),'expected_updated_at':payload.expected_updated_at.isoformat(),
        'changes':changes,'owner_updates':[item.model_dump(mode='json') for item in payload.owner_updates]})
    return enrich_context(result)
