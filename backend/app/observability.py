"""Private, bounded telemetry. No bodies, query strings, credentials or prompts."""
import asyncio
from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import math
import os
import re
from threading import Lock
from time import perf_counter
from uuid import UUID, uuid4

from starlette.responses import JSONResponse

context = ContextVar('dation_observability', default={})
component = 'api'
FIELDS = {'request_id', 'trace_id', 'span_id', 'run_id', 'case_id', 'node_id',
          'attempt', 'version', 'stage', 'outcome', 'status_code', 'route', 'method',
          'duration_ms', 'wait_ms', 'dependency', 'error_type', 'prompt_version',
          'input_tokens', 'output_tokens', 'total_tokens', 'turn_id'}
IDENTITIES = {'request_id', 'run_id', 'case_id', 'turn_id'}
BUCKETS = (.01, .05, .1, .25, .5, 1, 2.5, 5, 10, 30, 60, 120)


def uuid_value(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def trace_value(value):
    return value if isinstance(value, str) and re.fullmatch('[0-9a-f]{32}', value) and int(value, 16) else None


def new_context(request_id=None, trace_id=None):
    return {'request_id': uuid_value(request_id) or str(uuid4()),
            'trace_id': trace_value(trace_id) or uuid4().hex, 'span_id': uuid4().hex[:16]}


@contextmanager
def bind_context(values=None, **identity):
    values = values or {}
    data = new_context(values.get('request_id'), values.get('trace_id'))
    data.update({k: uuid_value(v) for k, v in identity.items() if k in IDENTITIES and uuid_value(v)})
    token = context.set(data)
    try:
        yield data
    finally:
        context.reset(token)


def identify(**identity):
    data = dict(context.get()) or new_context()
    data.update({k: uuid_value(v) for k, v in identity.items() if k in IDENTITIES and uuid_value(v)})
    context.set(data)


class JSONFormatter(logging.Formatter):
    def format(self, record):
        data = {'timestamp': datetime.now(timezone.utc).isoformat(),
                'severity': record.levelname, 'component': component,
                'event': getattr(record, 'event', 'runtime_log'), 'logger': record.name}
        revision = os.getenv('K_REVISION', 'local')
        if re.fullmatch('[a-zA-Z0-9-]{1,100}', revision):
            data['revision'] = revision
        values = {**context.get(), **getattr(record, 'telemetry', {})}
        for key, value in values.items():
            if key not in FIELDS or value is None:
                continue
            if key in IDENTITIES:
                value = uuid_value(value)
            elif key == 'trace_id':
                value = trace_value(value)
            elif isinstance(value, str):
                value = value[:150]
            elif isinstance(value, (int, float)) and not math.isfinite(value):
                continue
            elif not isinstance(value, (int, float, bool)):
                continue
            if value is not None:
                data[key] = value
        if record.exc_info and record.exc_info[0]:
            data['error_type'] = record.exc_info[0].__name__
        project = os.getenv('GOOGLE_CLOUD_PROJECT', 'dation-510100')
        if data.get('trace_id') and re.fullmatch('[a-z][a-z0-9-]{4,62}', project):
            data['logging.googleapis.com/trace'] = 'projects/'+project+'/traces/'+data['trace_id']
            data['logging.googleapis.com/spanId'] = data.get('span_id')
        # Unstructured third-party messages/exception text are intentionally excluded.
        return json.dumps(data, separators=(',', ':'), allow_nan=False)


def configure_logging(role):
    global component
    component = role
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.getLogger().handlers[:] = [handler]
    logging.getLogger().setLevel(logging.INFO)
    for name in ('httpx', 'httpcore', 'uvicorn.access'):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    for name in ('uvicorn', 'uvicorn.error'):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True


def event(name, level=logging.INFO, **fields):
    logging.getLogger('dation').log(level, name, extra={'event': name, 'telemetry': fields})


class Metrics:
    """Fixed buckets and registered route labels; no per-request/UUID series."""
    def __init__(self):
        self.lock = Lock()
        self.counters = defaultdict(float)
        self.histograms = {}

    def count(self, name, labels=(), amount=1):
        with self.lock:
            self.counters[(name, tuple(sorted(labels)))] += amount

    def observe(self, name, seconds, labels=()):
        if not math.isfinite(seconds) or seconds < 0:
            return
        with self.lock:
            key = (name, tuple(sorted(labels)))
            value = self.histograms.setdefault(key, [0, 0., [0]*len(BUCKETS)])
            value[0] += 1
            value[1] += seconds
            for index, bucket in enumerate(BUCKETS):
                if seconds <= bucket:
                    value[2][index] += 1

    def render(self):
        def labels_text(labels):
            return '{'+','.join(k+'='+json.dumps(str(v)) for k, v in labels)+'}' if labels else ''
        lines = []
        with self.lock:
            for (name, labels), value in sorted(self.counters.items()):
                lines.append(name+labels_text(labels)+' '+str(value))
            for (name, labels), (count, total, buckets) in sorted(self.histograms.items()):
                for limit, amount in zip(BUCKETS, buckets):
                    lines.append(name+'_bucket'+labels_text((*labels, ('le', limit)))+' '+str(amount))
                lines.append(name+'_bucket'+labels_text((*labels, ('le', '+Inf')))+' '+str(count))
                lines.append(name+'_sum'+labels_text(labels)+' '+str(total))
                lines.append(name+'_count'+labels_text(labels)+' '+str(count))
        return '\n'.join(lines)+'\n'


metrics = Metrics()


def instrument_http(client):
    """Preserve client identity, pooling, request-local headers and cancellation."""
    if getattr(client, '_dation_instrumented', False):
        return client
    original = client.send

    async def send(request, **kwargs):
        data = context.get()
        if data:
            request.headers['X-Request-ID'] = data['request_id']
            request.headers['traceparent'] = '00-'+data['trace_id']+'-'+uuid4().hex[:16]+'-01'
        path = request.url.path
        dependency = ('supabase_rest' if path.startswith('/rest/v1/') else
                      'supabase_storage' if path.startswith('/storage/v1/') else
                      'llm' if path.endswith('/chat/completions') else 'external')
        method = request.method if request.method in {'GET', 'POST', 'PATCH', 'DELETE', 'PUT', 'HEAD'} else 'OTHER'
        start = perf_counter()
        outcome = 'transport_error'
        status = None
        error = None
        try:
            response = await original(request, **kwargs)
            status = response.status_code
            outcome = 'ok' if status < 400 else 'http_error'
            return response
        except asyncio.CancelledError:
            outcome = 'cancelled'
            raise
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            seconds = perf_counter()-start
            labels = (('dependency', dependency), ('method', method), ('outcome', outcome))
            metrics.observe('dation_dependency_duration_seconds', seconds, labels)
            event('dependency_finished', dependency=dependency, method=method, outcome=outcome,
                  duration_ms=round(seconds*1000, 3), status_code=status, error_type=error,
                  level=logging.INFO if outcome == 'ok' else logging.WARNING)
    client.send = send
    client._dation_instrumented = True
    return client


class RequestTelemetry:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers', []))
        request_id = uuid_value(headers.get(b'x-request-id', b'').decode('latin1'))
        parent = headers.get(b'traceparent', b'').decode('latin1')
        match = re.fullmatch('00-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}', parent)
        trace = trace_value(match[1]) if match and int(match[2], 16) else None
        if not trace:
            google = headers.get(b'x-cloud-trace-context', b'').decode('latin1')
            match = re.fullmatch('([0-9a-f]{32})/[0-9]{1,20}(?:;o=[01])?', google)
            trace = trace_value(match[1]) if match else None
        with bind_context({'request_id': request_id, 'trace_id': trace}) as data:
            status, started = 500, False
            start = perf_counter()
            error = None

            async def observed_send(message):
                nonlocal status, started
                if message['type'] == 'http.response.start':
                    started = True
                    status = message['status']
                    message['headers'] = [*(h for h in message.get('headers', []) if h[0].lower() not in {b'x-request-id', b'traceparent'}),
                        (b'x-request-id', data['request_id'].encode()),
                        (b'traceparent', ('00-'+data['trace_id']+'-'+data['span_id']+'-01').encode())]
                await send(message)

            try:
                await self.app(scope, receive, observed_send)
            except asyncio.CancelledError:
                status = 499
                raise
            except Exception as exc:
                error = type(exc).__name__
                if started:
                    raise
                await JSONResponse({'detail': 'No se pudo completar la solicitud.'}, status_code=500)(scope, receive, observed_send)
            finally:
                route = getattr(scope.get('route'), 'path', 'unmatched')
                method = scope['method'] if scope['method'] in {'GET', 'POST', 'PATCH', 'DELETE', 'PUT', 'HEAD', 'OPTIONS'} else 'OTHER'
                identify(run_id=scope.get('path_params', {}).get('run_id'), case_id=scope.get('path_params', {}).get('case_id'))
                seconds = perf_counter()-start
                labels = (('route', route), ('method', method), ('status', str(status)))
                metrics.count('dation_http_requests_total', labels)
                metrics.observe('dation_http_duration_seconds', seconds, labels)
                event('request_finished', route=route, method=method, status_code=status,
                      duration_ms=round(seconds*1000, 3), error_type=error,
                      level=logging.ERROR if status >= 500 else logging.INFO)
