"""Compact Home presentation over the existing, tenant-authorized case history."""
from app.platform.identity import platform_call
from app.services.decision_case_service import _state_with_history

NODE_LABELS = {'logistics_assignment': 'Assignment', 'logistics_scheduling': 'Scheduling'}


def recent_case(bundle):
    row = bundle['case']
    state = _state_with_history(row.get('state_json') or {}, [], case_id=str(row['id']),
        orders_dataset_id=str(row['orders_dataset_id']), fleet_dataset_id=str(row['fleet_dataset_id']),
        summaries=bundle['summaries'])
    nodes = [(key, state['nodes'][key]) for key in NODE_LABELS]
    # Canonical workflow state retains an existing approval while a replacement
    # executes. Resume that newer work, rather than silently selecting the next
    # step that was unlocked by the older approved version.
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
        return _item(row, bundle, key, status, latest['id'])
    # Prefer work needing intervention, then the next available step, then the
    # furthest approved step. Final Assignment is not an executable MVP node.
    chosen = next(((key, node) for status in ('running', 'review', 'error', 'stale', 'available')
                   for key, node in nodes if node['status'] == status), None)
    key, node = chosen or next(((key, node) for key, node in reversed(nodes)
                               if node['status'] == 'approved'), nodes[0])
    run_id = node.get('latest_run_id') if node['status'] in {'running', 'review', 'error'} else None
    return _item(row, bundle, key, node['status'], run_id)


def _item(row, bundle, key, status, run_id):
    return {'case_id': str(row['id']), 'label': bundle.get('label'), 'dda': 'DDA Logística',
            'node_id': key, 'node_label': NODE_LABELS[key],
            'status': 'completed' if row['status'] == 'completed' else status,
            'last_activity_at': row['last_activity_at'], 'run_id': run_id}


async def home_snapshot(ctx):
    if 'logistics' not in ctx.enabled_ddas:
        return {'recent_cases': [], 'attention': {'items': [], 'total': 0, 'scope': 'workspace_review'},
                'activity': {'available': False, 'items': []}}
    data = await platform_call('platform_home', {'actor_user_id': ctx.user_id,
                                               'target_workspace_id': ctx.workspace_id})
    return {'recent_cases': [recent_case(bundle) for bundle in data['recent_cases']],
            'attention': {**data['attention'], 'scope': 'workspace_review',
                          'items': [{**item, 'node_label': NODE_LABELS[item['node_id']]}
                                    for item in data['attention']['items']]},
            # Phase 10 owns the full audit feed. No synthetic activity or inferred actors.
            'activity': {'available': False, 'items': []}}
