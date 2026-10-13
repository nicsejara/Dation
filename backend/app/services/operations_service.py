"""Private operational reads. Probe failures expose only bounded diagnostic codes."""
import asyncio
import httpx
from app.services import dispatch_service as dispatch
from app.observability import event, metrics


async def operational_snapshot():
    try:
        async with asyncio.timeout(8):
            snapshot = await dispatch.db('POST', 'rpc/dispatch_operational_snapshot', body={})
            snapshot['comparative_queue'] = await dispatch.db('POST', 'rpc/comparative_operational_snapshot', body={})
    except (httpx.HTTPError, TimeoutError):
        event('readiness_unavailable', outcome='database_unavailable')
        return {'ready': False, 'database': 'unavailable', 'alerts': ['database_unavailable']}
    healthy = snapshot['workers']['healthy'] > 0
    queue, repair = snapshot['queue'], snapshot['reconciliation']
    alerts = []
    if not healthy: alerts.append('worker_unavailable')
    if queue['queued'] and not healthy: alerts.append('queue_without_worker')
    if queue['oldest_queued_seconds'] > 30: alerts.append('queue_wait_over_30s')
    if queue['expired_leases']: alerts.append('expired_leases')
    if queue['past_deadline']: alerts.append('job_deadline_expired')
    if repair['oldest_pending_seconds'] > 60: alerts.append('reconciliation_over_60s')
    return {**snapshot, 'ready': healthy, 'database': 'available', 'alerts': alerts,
            'worker_freshness_seconds': 90}


def render_metrics(snapshot):
    lines = [metrics.render().rstrip(), '# Cluster gauges read from the shared database; process histograms above.']
    if snapshot['database'] != 'available':
        lines.append('dation_database_available 0')
        return '\n'.join(lines)+'\n'
    lines.append('dation_database_available 1')
    for group in ('queue', 'workers', 'reconciliation', 'runs_24h', 'chat_24h', 'comparative_queue'):
        for field, value in snapshot[group].items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                lines.append('dation_'+group+'_'+field+' '+str(value))
    lines.append('dation_ready '+str(int(snapshot['ready'])))
    return '\n'.join(lines)+'\n'
