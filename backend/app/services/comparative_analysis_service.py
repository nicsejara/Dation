"""Progressive deterministic evidence, independent of case history and approval."""
import asyncio
import copy
import hashlib
from time import perf_counter
from uuid import uuid4
import httpx
from app.platform.context import bind, job_context
from app.observability import bind_context, context, event, identify, metrics
from app.services import dispatch_service as dispatch
from app.services.run_service import get_run
from app.engines.assignment.engine import SCENARIO_FOR_OBJECTIVE
from app.engines.assignment import run_assignment_engine


class AnalysisConflict(ValueError):
    pass


def expected_references(result):
    dimensions = result.get('configuration', {}).get('dimensions') or result.get('analysis', {}).get('active_dimensions') or []
    return {'balanced', *(SCENARIO_FOR_OBJECTIVE[d] for d in dimensions if d in SCENARIO_FOR_OBJECTIVE)}


def references_available(result):
    return all(isinstance(result.get('scenarios', {}).get(name, {}).get('metrics'), dict)
               for name in expected_references(result))


async def base_run(run_id):
    run = await get_run(run_id)
    if not run: raise LookupError('No se encontró la corrida base.')
    if run['status'] != 'completed': raise AnalysisConflict('La corrida debe estar completada para profundizar el análisis.')
    if run.get('schema_version') != 'assignment_v1' or (run.get('node_id') not in (None, 'logistics_assignment')):
        raise ValueError('El análisis comparativo está disponible para Assignment.')
    return run


def public_artifact(row):
    fields = ('id','base_run_id','status','source_mode','created_at','started_at','finished_at',
              'progress_json','error_message','result_json','result_fingerprint','generation','attempts')
    return {key: row.get(key) for key in fields}


async def completed_evidence(run):
    if run.get('schema_version') != 'assignment_v1': return run['result_json'], None
    rows = await dispatch.db('GET','decision_comparative_analyses',params={
        'base_run_id':'eq.'+run['id'],'status':'eq.completed','limit':'1'}) or []
    if not rows: return run['result_json'], None
    row = rows[0]
    if row['result_json']['scenarios']['selected'] != run['result_json']['scenarios']['selected']:
        raise RuntimeError('La evidencia comparativa no conserva la decisión original.')
    merged = copy.deepcopy(run['result_json'])
    merged['scenarios'] = row['result_json']['scenarios']
    merged['sensitivity'] = copy.deepcopy(row['result_json'].get('sensitivity', {}))
    merged['analysis'] = {**merged.get('analysis', {}), 'comparative_analysis_id':row['id'],
                          'scenario_count':row['result_json']['analysis']['scenario_count']}
    return merged, row['id']


async def get_analysis(run_id):
    run = await base_run(run_id)
    rows = await dispatch.db('GET','decision_comparative_analyses',params={'base_run_id':'eq.'+run_id,'limit':'1'}) or []
    if rows: return public_artifact(rows[0])
    if run['result_json'].get('analysis', {}).get('depth') in ('comparative','deep') and references_available(run['result_json']):
        return {'id':None,'base_run_id':run_id,'status':'completed','source_mode':'original',
                'result_json':run['result_json'],'result_fingerprint':run.get('result_fingerprint')}
    return {'id':None,'base_run_id':run_id,'status':'available','can_reuse':references_available(run['result_json'])}


async def generate_analysis(run_id, *, retry=False):
    run = await base_run(run_id)
    identify(run_id=run_id, case_id=run.get('decision_case_id'))
    result = run['result_json']
    if result.get('analysis', {}).get('depth') in ('comparative','deep') and references_available(result):
        return await get_analysis(run_id)
    configuration = {key:value for key,value in result['configuration'].items() if key!='options'}
    options = {**result['configuration']['options'], 'analysis_depth':'comparative'}
    request = {'base_run_id':run_id,'configuration':configuration,'options':options,
               'engine_name':run['engine_name'],'engine_version':run['engine_version'],'schema_version':run['schema_version'],
               'decision_case':{'case_id':run.get('decision_case_id'),'node_id':'logistics_assignment'}}
    if context.get(): request['_observability'] = {k:context.get()[k] for k in ('request_id','trace_id')}
    if not references_available(result):
        from app.services.dispatch_job_service import engine_identity
        if (run['engine_name'],run['engine_version'],run['schema_version']) != engine_identity('logistics_assignment'):
            raise AnalysisConflict('La versión del motor de esta corrida no permite generar nuevas referencias.')
        if not run.get('orders_dataset_id') or not run.get('fleet_dataset_id'):
            raise ValueError('La corrida no conserva los datasets necesarios para generar referencias.')
    try:
        rows = await dispatch.db('POST','rpc/enqueue_comparative_analysis',body={
            'target_base_id':run_id,'job_request':request,'existing_result':result if references_available(result) else None,
            'retry_failed':retry})
    except httpx.HTTPStatusError as exc:
        try: code = exc.response.json().get('code')
        except (ValueError,AttributeError): code = None
        if code=='22023': raise AnalysisConflict('La intención no coincide con la corrida base.') from exc
        if code=='53300':
            from app.services.dispatch_job_service import QueueFull
            raise QueueFull('La cola comparativa está llena. Podés reintentar.') from exc
        raise
    if not rows: raise RuntimeError('No se pudo registrar el análisis comparativo.')
    event('comparative_admitted', analysis_id=rows[0]['id'], stage=rows[0]['status'])
    return public_artifact(rows[0])


async def process_analysis_job(job):
    from app.services.dispatch_job_service import _process_job
    request = job['request_json']
    started = perf_counter()
    with bind(job_context(job)), bind_context(request.get('_observability'),run_id=job['base_run_id'],case_id=request['decision_case'].get('case_id'),analysis_id=job['id']):
        event('comparative_claimed',attempt=job['attempts'])
        async def execute(request, writer, progress):
            base = await base_run(request['base_run_id'])
            orders,fleet,orders_bytes,fleet_bytes = await dispatch.load_inputs(base['orders_dataset_id'],base['fleet_dataset_id'])
            for kind,dataset,data in [('orders',orders,orders_bytes),('fleet',fleet,fleet_bytes)]:
                original_hash=dataset.get('sha256')
                if not original_hash or hashlib.sha256(data).hexdigest()!=original_hash:
                    raise ValueError('Los bytes del Data Pack no coinciden con la corrida base.')
            result = await asyncio.to_thread(run_assignment_engine,orders_bytes,fleet_bytes,
                request['configuration'],request['options'],base['result_json']['inputs'],progress,
                reference_result=base['result_json'])
            if result['scenarios']['selected'] != base['result_json']['scenarios']['selected']:
                raise ValueError('El análisis debe conservar íntegra la recomendación original.')
            rows = await writer({'status':'completed','result_json':result,
                                 'result_fingerprint':result['result_fingerprint'],'duration_ms':int((perf_counter()-started)*1000)})
            return rows[0]
        try:
            return await _process_job({**job,'run_id':job['id']},executor=execute,
                job_kind='comparative_analysis',target_key='target_analysis_id',event_prefix='comparative')
        finally:
            metrics.observe('dation_comparative_execution_seconds',perf_counter()-started)
