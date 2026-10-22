"""A read-only case projection over the canonical history, never a state repair."""
from app.platform.identity import platform_call
from app.platform.home import recent_case
from app.services.decision_case_service import _state_with_history, _history_item, NODE_IDS
from app.platform.foundation import REGISTRY,resolve_node_destination,case_context,objective_presentation

LABELS={key:value['label'] for key,value in REGISTRY['decisions'].items()}

def canonical(bundle):
    row=bundle['case']
    options={'case_id':row['id'],'orders_dataset_id':row['orders_dataset_id'],
        'fleet_dataset_id':row['fleet_dataset_id'],'summaries':bundle['summaries']}
    try:return _state_with_history(bundle.get('state_json') or {},[],**options)
    except (ValueError,TypeError,AttributeError):
        # A historical cache cannot hide persisted evidence or break the entire
        # library. Reconstruct in memory, without repairing the stored row.
        return _state_with_history({},[],**options)

def project(bundle,detail=False):
    row=bundle['case'];summaries=bundle['summaries']
    if row.get('domain','logistics')!='logistics':
        result={'id':row['id'],'friendly_id':'DC-'+row['id'][:8].upper(),'label':row.get('label'),'dda':row['domain'],
            'status':bundle['status'],'display_status':bundle['status'],'in_review':False,'is_demo':bool(bundle.get('is_demo')),
            'current_step':None,'current_step_label':'Por definir','current_objective':None,'progress':{'approved':0,'total':0},
            'owner':None,'approver':None,'created_by':bundle.get('created_by'),'created_at':row['created_at'],
            'updated_at':row['updated_at'],'last_activity_at':row['last_activity_at'],'resume':None}
        result.update(category=row.get('category'),description=row.get('description'))
        result['context']=case_context(result)
        if detail:result.update(nodes=[],orders=bundle.get('orders'),fleet=bundle.get('fleet'),responsibilities=bundle.get('responsibilities'))
        return result
    state=canonical(bundle)
    resume=recent_case({'case':{**row,'status':bundle['status'],'state_json':state},'summaries':summaries})
    collaboration=bundle.get('collaboration') or {}
    # A closed/archived database cache is not an approval. Completion uses both
    # implemented nodes and their current lineage, computed in the SQL snapshot.
    result={'id':row['id'],'friendly_id':'DC-'+row['id'][:8].upper(),'label':row.get('label'),
        'dda':'logistics','status':bundle['status'],'in_review':bundle['in_review'],'is_demo':bool(bundle.get('is_demo')),
        'current_step':resume['node_id'],'current_step_label':LABELS[resume['node_id']],
        'progress':{'approved':sum(state['nodes'][k]['status']=='approved' for k in NODE_IDS[:2]),'total':2},
        'owner':(collaboration.get(resume['node_id']) or {}).get('owner'),'created_by':bundle.get('created_by'),'created_at':row['created_at'],
        'last_activity_at':row['last_activity_at'],'updated_at':row['updated_at'],
        'resume':target(resume['node_id'],resume['status'],resume.get('run_id'),state['nodes'][resume['node_id']]) or {'view':'logistics-map','node_id':resume['node_id'],'run_id':None}}
    result.update(category=row.get('category'),description=row.get('description'))
    result['context']=case_context(result)
    relevant=resume['node_id'];assignment=collaboration.get(relevant) or {}
    result['approver']=assignment.get('approver')
    result['current_objective']=node_objective(summaries[relevant],state['nodes'][relevant]['status']=='approved')
    facts=bundle.get('portfolio_facts') or {}
    result['display_status']=('archived' if result['status']=='archived' else 'pending_approval' if facts.get('pending') else
        'review' if result['in_review'] else 'running' if facts.get('running') else result['status'])
    if detail:
        people=bundle.get('run_people') or {};nodes=[]
        for key in NODE_IDS:
            node={**state['nodes'][key]};summary=summaries[key];latest=summary.get('latest');approved=summary.get('approved')
            candidate=latest and not latest.get('approved_at') and not latest.get('superseded_at')
            status=node['status']
            if candidate:
                status={'queued':'running','running':'running','error':'error'}.get(latest['status'],'review')
                source=summaries['logistics_assignment'].get('approved')
                if key=='logistics_scheduling' and (not source or latest.get('upstream_run_id')!=source['id']):status='stale'
            if key==NODE_IDS[2]:status='coming_soon'
            assignment=collaboration.get(key) or {}
            nodes.append({'id':key,'label':LABELS[key],'status':status,'owner':assignment.get('owner'),'approver':assignment.get('approver'),
                'assignment_updated_at':assignment.get('updated_at'),'can_approve':assignment.get('can_approve',False),'admin_override':assignment.get('admin_override',False),
                'run_count':node['run_count'],'latest_run':people.get((latest or {}).get('id')),
                'approved_run':people.get((approved or {}).get('id')),
                'approval_current':node['status']=='approved',
                'objective':node_objective(summary,node['status']=='approved'),
                'latest_objective':node_objective(summary,False),
                'target':None if key==NODE_IDS[2] else target(key,status,(latest or {}).get('id') if candidate else None,node)})
        result.update(orders=bundle['orders'],fleet=bundle['fleet'],nodes=nodes,responsibilities=bundle.get('responsibilities'))
    return result

def node_objective(summary,approval_current):
    approved=summary.get('approved') if approval_current else None
    run=approved or summary.get('latest')
    if not run:return None  # Local browser drafts are not persisted Case configuration.
    config=run.get('configuration_json') or {}
    value=objective_presentation(config.get('objective') or config.get('strategy') or run.get('objective'))
    return {**value,'source':'approved_run' if approved else 'latest_run','run_id':run['id']} if value else None

def target(node_id,status,run_id,node):
    return resolve_node_destination(node_id,{**node,'status':status,'latest_run_id':run_id or node.get('latest_run_id'),
        'approval_current':node.get('status')=='approved'})

async def read(ctx,**options):
    return await platform_call('platform_decision_portfolio',{'actor_user_id':ctx.user_id,'target_workspace_id':ctx.workspace_id,**options})

async def listing(ctx,**options):
    data=await read(ctx,**options)
    return {**data,'items':[project(item) for item in data['items']]}

async def detail(ctx,case_id):return project(await read(ctx,target_case_id=str(case_id)),True)

async def history(ctx,case_id,node_id,limit,offset,run_id=None):
    if run_id:limit,offset=1,0
    options={'search_text':str(run_id)} if run_id else {}
    data=await read(ctx,target_case_id=str(case_id),target_node_id=node_id,page_limit=limit,page_offset=offset,**options)
    state=canonical(data)
    return {'items':[_history_item(run,state) for run in data['runs']],
        'total':len(data['runs']) if run_id else data['summaries'][node_id]['run_count'],'limit':limit,'offset':offset}
