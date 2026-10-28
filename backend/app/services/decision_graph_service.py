"""One graph projection for Map, Config, Case, Home and Center; no execution."""
from fastapi import HTTPException
from app.platform.identity import platform_call
from app.domain.logistics.definitions import definition_hash, definition_snapshot
from app.domain.logistics.graph import resolve_case_graph

async def snapshot(ctx,case_id,operation='snapshot',node_id=None,run_id=None,limit=25,offset=0):
    return await platform_call('platform_ultimate_graph',{'target_workspace_id':ctx.workspace_id,'actor_user_id':ctx.user_id,
        'target_case_id':str(case_id),'operation':operation,'target_node_id':node_id,
        'selected_run_id':str(run_id) if run_id else None,'page_limit':limit,'page_offset':offset})

def project(data):
    registry=data.get('definition') or {}
    if registry.get('definition_hash')!=definition_hash() or registry.get('definition_jsonb')!=definition_snapshot():
        raise HTTPException(409,'La Definition del graph no coincide con este release. No se habilitó ejecución.')
    graph=resolve_case_graph(data['case'],data['model_version'],{'entries':data['entries']},data['runs'],
        data['responsibilities'],data.get('runtime_capabilities',{}),permissions=data['permissions'])
    for node in graph['nodes']:
        node['history_count']=data.get('history_counts',{}).get(node['id'],node['history_count'])
    return {'case':data['case'],'graph':graph,'pack':data['pack'],'pack_version':data['pack_version'],
        'model':data['model'],'responsibilities':data['responsibilities'],'selected_run':data.get('selected_run')}

async def read(ctx,case_id,node_id=None,run_id=None):return project(await snapshot(ctx,case_id,node_id=node_id,run_id=run_id))

async def configure(ctx,case_id,node_id):
    data=project(await snapshot(ctx,case_id,'configure',node_id))
    node=next(n for n in data['graph']['nodes'] if n['id']==node_id)
    if not node['actions']['configure']['allowed']:
        raise HTTPException(409,{'message':'La decisión no puede configurarse en el contexto actual.','node':node})
    return {**data,'configuration_context':{'case_id':str(case_id),'node_id':node_id,
        'upstream_run_id':node['upstream_run_id'],'read_set':node['read_set'],'read_set_hash':node['read_set_hash'],
        'definition_hash':data['graph']['definition_hash'],'runtime_available':node['runtime_available'],'admission_available':False}}

async def history(ctx,case_id,node_id,limit=25,offset=0):return await snapshot(ctx,case_id,'history',node_id,limit=limit,offset=offset)

def center_item(item,data):
    graph=data['graph'];focus=next(n for n in graph['nodes'] if n['id']==graph['attention_node_id'])
    runs={r['id']:r for r in data.get('runs',[])}
    projected=[{**n,'status':n['node_state'],'run_count':n['history_count'],
        'approval_current':n['node_state']=='APPROVED','latest_run':runs.get(n['run_id']),
        'approved_run':runs.get(n['approved_run_id']),
        'target':n['primary_action']['target'] if n['primary_action'] and n['primary_action']['allowed'] else None}
        for n in graph['nodes']]
    return {**item,'workflow_version':2,'graph':graph,'resume':graph['resume'],
        'current_step':focus['id'],'current_step_label':focus['label'],'display_status':'archived' if item.get('status')=='archived' else focus['node_state'],
        'progress':{'approved':graph['approved_count'],'total':len(graph['nodes'])},
        'nodes':projected,'owner':focus['owner'],'runtime_execution_available':False,
        'responsibilities':data['responsibilities']}

async def enrich_center(ctx,items):
    import asyncio
    semaphore=asyncio.Semaphore(4)
    async def enrich(item):
        if item.get('workflow_version')!=2 or item.get('resume') is None:return item
        async with semaphore:
            raw=await snapshot(ctx,item['id']);data=project(raw)
            return center_item(item,{**data,'runs':raw['runs']})
    return await asyncio.gather(*(enrich(item) for item in items))

async def case_context(ctx,case_id):
    from app.services.logistics_model_service import enrich_context
    raw=await snapshot(ctx,case_id)
    context=enrich_context({k:v for k,v in raw.items() if k not in ('definition','runs','entries','selected_run')})
    return {**context,'graph':project(raw)['graph']}
