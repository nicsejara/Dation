"""Compact Home presentation over the existing, tenant-authorized case history."""
from app.platform.identity import platform_call
from app.domain.decision_cases import project_case_history, case_projection_options
from app.platform.activity import home_activity
from app.platform.onboarding import home_progress
from app.platform.foundation import REGISTRY, case_context, resolve_node_destination

NODE_LABELS = {key: value['label'] for key, value in REGISTRY['decisions'].items() if value['implemented']}


def recent_case(bundle):
    row = bundle['case']
    options = {**case_projection_options(row), 'summaries': bundle['summaries']}
    try:
        state = project_case_history(row.get('state_json') or {}, [], **options)
    except (ValueError, TypeError, AttributeError):
        state = project_case_history({}, [], **options)
    nodes = [(key, state['nodes'][key]) for key in NODE_LABELS]
    # Retain the replacement as current work instead of silently presenting the
    # next unlocked step. Ordinary navigation still prefers its official result.
    pending = [(key, summary['latest']) for key, summary in bundle['summaries'].items()
               if key in NODE_LABELS and summary.get('latest')
               and not summary['latest'].get('approved_at')
               and not summary['latest'].get('superseded_at')]
    if pending:
        key, latest = max(pending, key=lambda pair: (pair[1].get('created_at') or '', pair[1]['id']))
        status = {'queued': 'running', 'running': 'running', 'error': 'error'}.get(latest['status'], 'review')
        source = bundle['summaries']['logistics_assignment'].get('approved')
        if key == 'logistics_scheduling' and (not source or latest.get('upstream_run_id') != source['id']):
            status = 'stale'
        return _item(row, bundle, key, status, latest['id'], state['nodes'][key])
    # Prefer work needing intervention, then the next available step, then the
    # furthest approved step. Final Assignment is not an executable MVP node.
    chosen = next(((key, node) for status in ('running', 'review', 'error', 'stale', 'available')
                   for key, node in nodes if node['status'] == status), None)
    key, node = chosen or next(((key, node) for key, node in reversed(nodes)
                               if node['status'] == 'approved'), nodes[0])
    run_id = node.get('latest_run_id') if node['status'] in {'running', 'review', 'error'} else None
    return _item(row, bundle, key, node['status'], run_id, node,
                 completed=all(n['status'] == 'approved' for _, n in nodes))


def _item(row, bundle, key, status, run_id, node, completed=False):
    # Keep candidate IDs/status for explicit review. The shared resolver selects
    # the official approval for ordinary resume, just as Center and Map do.
    resume = resolve_node_destination(key, {**node, 'status': status,
        'latest_run_id': run_id or node.get('latest_run_id'),
        'approval_current': node['status'] == 'approved'})
    item = {'case_id': str(row['id']), 'label': bundle.get('label'), 'dda': 'DDA Logística',
            'node_id': key, 'node_label': NODE_LABELS[key],
            'status': 'completed' if completed else status,
            'last_activity_at': row['last_activity_at'], 'run_id': run_id, 'is_demo': bool(row.get('is_demo')),
            'resume': resume or {'view': 'logistics-map', 'node_id': key, 'run_id': None},
            'approval_current': node['status'] == 'approved'}
    if row.get('workflow_version') == 2:
        # T2 retains the Case in shared readers without opening a legacy run/config flow.
        item['workflow_version'] = 2
        item['resume'] = ({'view':'logistics-case-setup','node_id':None,'run_id':None}
                          if row.get('foundation_context_available') or row.get('creation_intent_hash') else None)
    item['context'] = case_context({**item, 'dda': 'logistics'})
    return item


async def home_snapshot(ctx):
    activity = await home_activity(ctx)
    onboarding = await home_progress(ctx)
    if 'logistics' not in ctx.enabled_ddas:
        return {'recent_cases': [], 'attention': {'items': [], 'total': 0, 'scope': 'workspace_review'},
                'activity': activity,'onboarding':onboarding}
    data = await platform_call('platform_home', {'actor_user_id': ctx.user_id,
                                               'target_workspace_id': ctx.workspace_id})
    recent=[recent_case(bundle) for bundle in data['recent_cases']]
    from app.services import decision_graph_service
    graphs={}
    for item in recent:
        if item.get('workflow_version')==2 and item.get('resume') is not None:
            projection=await decision_graph_service.read(ctx,item['case_id']);graph=projection['graph'];graphs[item['case_id']]=graph
            focus=next(n for n in graph['nodes'] if n['id']==graph['attention_node_id'])
            item.update(graph=graph,resume=graph['resume'],status=focus['node_state'],node_id=focus['id'],node_label=focus['label'],approval_current=focus['node_state']=='APPROVED')
    attention=[];removed=0
    for item in data['attention']['items']:
        case_id=item['case_id'];graph=graphs.get(case_id)
        if graph is None:
            cohort=await decision_graph_service.snapshot(ctx,case_id,operation='cohort')
            if cohort['workflow_version']==2:
                graph=(await decision_graph_service.read(ctx,case_id))['graph'];graphs[case_id]=graph
        projected={**item,'node_label':NODE_LABELS[item['node_id']]}
        if graph:
            node=next(n for n in graph['nodes'] if n['id']==item['node_id'])
            # Refine the existing attention candidates using the same graph; do not
            # advertise a stale handoff or a result outside the current read set.
            valid=(item['kind']=='handoff' and node['node_state']=='READY' or
                   item['kind']=='review' and node['node_state']=='COMPLETED' and node['run_id']==item.get('run_id'))
            if not valid:removed+=1;continue
            projected.update(graph=graph,resume=graph['resume'],node_label=node['label'],node_state=node['node_state'])
        attention.append(projected)
    return {'recent_cases': recent,
            'attention': {**data['attention'], 'scope': 'assigned_work','items':attention,
                'total':max(0,data['attention']['total']-removed),
                'total_is_upper_bound':data['attention']['total']>len(data['attention']['items'])},
            'activity': activity,'onboarding':onboarding}
