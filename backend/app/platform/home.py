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
    # Prefer work needing intervention, then the next available step, then the
    # furthest approved step. Final Assignment is not an executable MVP node.
    chosen = next(((key, node) for status in ('running', 'review', 'error', 'stale', 'available')
                   for key, node in nodes if node['status'] == status), None)
    key, node = chosen or next(((key, node) for key, node in reversed(nodes)
                               if node['status'] == 'approved'), nodes[0])
    run_id = node.get('latest_run_id') if node['status'] in {'running', 'review', 'error'} else None
    return {'case_id': str(row['id']), 'label': bundle.get('label'), 'dda': 'DDA Logística',
            'node_id': key, 'node_label': NODE_LABELS[key],
            'status': 'completed' if row['status'] == 'completed' else node['status'],
            'last_activity_at': row['last_activity_at'], 'run_id': run_id}


async def home_snapshot(ctx):
    data = await platform_call('platform_home', {'actor_user_id': ctx.user_id,
                                               'target_workspace_id': ctx.workspace_id})
    return {'recent_cases': [recent_case(bundle) for bundle in data['recent_cases']],
            'attention': {**data['attention'], 'scope': 'workspace_review',
                          'items': [{**item, 'node_label': NODE_LABELS[item['node_id']]}
                                    for item in data['attention']['items']]},
            # Phase 10 owns the full audit feed. No synthetic activity or inferred actors.
            'activity': {'available': False, 'items': []}}
