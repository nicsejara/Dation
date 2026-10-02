import copy
import hashlib
import json
from datetime import datetime, timezone
from time import perf_counter
from app.models.dispatch_config import DispatchConfig, DispatchOptions, PRESETS
from app.validators.orders_schema import validate_orders_csv
from app.validators.fleet_schema import validate_fleet_csv
from .normalization import preflight
from .plans import greedy, summarize, validate_plan
from .model import solve

ENGINE_NAME='logistics-dispatch-engine'
ENGINE_VERSION='1.1.0'
NAMES={'baseline_direct':'Despacho directo','baseline_current':'Asignación informada','min_cost':'Costo mínimo',
       'min_trips':'Viajes mínimos','min_time':'Entrega más rápida','selected':'Decisión recomendada'}
DIRECTIONS={k:('higher_better' if k in ('on_time_rate','load_utilization') else 'lower_better') for k in
            ('total_cost','total_trips','avg_lead_time_days','on_time_rate','load_utilization','co2_kg','fuel_l','outsourced_trips_share')}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def plan_signature(scenario):
    return [(t['dispatch_date'],t['fleet_pool_id'],t['origin'],t['destination'],[(l['order_id'],l['units']) for l in t['loads']]) for t in scenario['trips']]


def run_dispatch_engine(orders_bytes, fleet_bytes, configuration=None, options=None, inputs=None, progress=None):
    started=perf_counter();config=DispatchConfig.model_validate(configuration or {}).model_dump()
    opts=DispatchOptions.model_validate(options or {}).model_dump()
    def notify(stage):
        if perf_counter()-started > opts['total_time_limit_s']:
            raise TimeoutError('Se agotó el presupuesto global; no se publica una decisión parcial.')
        if progress:progress(stage)
    notify('validating')
    orders=sorted(validate_orders_csv(orders_bytes)['records'],key=lambda o:o['order_id'])
    full_fleet=sorted(validate_fleet_csv(fleet_bytes)['records'],key=lambda v:(v['base_location'],v['vehicle_type'],v['fleet_pool_id']))
    fleet=[v for v in full_fleet if opts['allow_third_party'] or v['ownership']=='own']
    if not fleet:raise ValueError('No hay flota habilitada.')
    check=preflight(orders,fleet,full_fleet)
    if check['errors']:raise ValueError('; '.join(e['detail']+' '+e.get('order_id','') for e in check['errors']))
    anomalies=check['anomalies']
    for a in anomalies:
        decision=opts['anomaly_decisions'].get(a['order_id'])
        if decision is None:raise ValueError('Debés decidir incluir o excluir la anomalía '+a['order_id'])
        a['decision']=decision
    excluded={a['order_id'] for a in anomalies if a['decision']=='exclude'}
    orders=[o for o in orders if o['order_id'] not in excluded]
    if not orders:raise ValueError('No quedan órdenes incluidas.')
    notify('baseline');scenarios={};candidates=[]
    for key,current in [('baseline_direct',False),('baseline_current',True)]:
        if current and not all(o.get('current_vehicle_type') for o in orders):continue
        p=greedy(orders,fleet,direct=True,current=current)
        if p:
            validate_plan(p,orders,fleet,direct=True)
            scenarios[key]={**summarize(p,orders,fleet),'name':NAMES[key],'feasible':True,'solver':{'status':'feasible','method':'declared_policy','gap':None}}
        else:
            scenarios[key]={'name':NAMES[key],'feasible':False,'metrics':None,'trips':[],
                'solver':{'status':'unknown','method':'declared_policy','gap':None},
                'warning':'La política directa no encuentra cobertura con la flota disponible; no es una prueba de inviabilidad global.'}
    for objective in ('min_cost','min_trips','min_time'):
        p=greedy(orders,fleet,objective)
        if p:
            validate_plan(p,orders,fleet)
            candidates.append(summarize(p,orders,fleet))
    # Only a direct reference that also satisfies the planning windows is a candidate.
    baseline=scenarios['baseline_direct']
    if baseline['feasible']:
        try:validate_plan(baseline['trips'],orders,fleet);candidates.append(copy.deepcopy(baseline))
        except ValueError:baseline['feasible']=False;baseline['warning']='Referencia directa fuera de las ventanas de planificación.'
    def metric(s,k):return s['metrics'][{'cost':'total_cost','trips':'total_trips','time':'avg_lead_time_days'}[k]]
    scales={k:1.0 for k in ('cost','trips','time')}
    def choose(weights):
        return min(candidates,key=lambda s:(sum(weights[k]*metric(s,k)/scales[k] for k in weights),metric(s,'cost'),metric(s,'trips'),plan_signature(s)))
    def optimize(weights,label):
        notify('optimizing:'+label)
        if len(orders)<=300:
            p,meta=solve(orders,fleet,weights,scales,opts,choose(weights)['trips'] if candidates else None)
        else:p,meta=None,{'status':'feasible','method':'heuristic','gap':None,'reason':'Política determinística para más de 300 órdenes'}
        if p:
            validate_plan(p,orders,fleet);candidate=summarize(p,orders,fleet);candidates.append(candidate)
        if not candidates:
            raise ValueError('No se encontró una distribución factible dentro del presupuesto. Revisá bases, flota y ventanas; no se descartaron órdenes.')
        result=copy.deepcopy(choose(weights))
        if not p or plan_signature(result)!=plan_signature(candidate):
            meta={**meta,'status':'feasible','method':'heuristic' if not p else 'best_candidate','gap':None}
        result.update(solver=meta,feasible=True,name=NAMES.get(label,label))
        return result
    for k in ('min_cost','min_trips','min_time'):
        scenarios[k]=optimize(dict(zip(('cost','trips','time'),PRESETS[k])),k)
    # Known feasible extremes, never claim f* unless certified optimal.
    normalization={}
    for k in scales:
        vals=[metric(s,k) for s in scenarios.values() if s.get('feasible') and s.get('metrics')]
        low=min(vals);ref=metric(baseline,k) if baseline['feasible'] else max(vals)
        scales[k]=max(ref-low,max(vals)-low,abs(low)*.01,1.0)
        normalization[k]={'best_known':low,'reference':ref,'scale':scales[k],
                          'certified_optimal':scenarios['min_'+k]['solver']['status']=='optimal'}
    weights=config['weights'];preset=next((k for k,v in PRESETS.items() if k!='balanced' and all(abs(weights[n]-w)<1e-8 for n,w in zip(weights,v))),None)
    scenarios['selected']=copy.deepcopy(scenarios[preset]) if preset else optimize(weights,'selected')
    scenarios['selected']['name']=NAMES['selected']
    notify('sensitivity');sweep=[]
    settings=[(1,0,0),(0,1,0),(0,0,1),(.5,.5,0),(.5,0,.5),(0,.5,.5),(1/3,1/3,1/3)] if opts['sensitivity'] else []
    selected=scenarios['selected']
    def order_map(s):
        mapping={o['order_id']:[] for o in orders}
        for t in s['trips']:
            signature=(t['dispatch_date'],t['fleet_pool_id'],tuple((l['order_id'],l['units']) for l in t['loads']))
            for l in t['loads']:mapping[l['order_id']].append(signature)
        return {k:tuple(sorted(v)) for k,v in mapping.items()}
    selected_map=order_map(selected)
    previous_map=None
    for index,ws in enumerate(settings):
        w=dict(zip(('cost','trips','time'),ws))
        if index<3:s=scenarios[('min_cost','min_trips','min_time')[index]]
        else:s=optimize(w,'sensitivity')
        om=order_map(s)
        sweep.append({'weights':w,'metrics':s['metrics'],'solver':s['solver'],
                      'plan_fingerprint':digest(plan_signature(s)),
                      'orders_changed_vs_selected':sum(om[k]!=selected_map[k] for k in om),
                      'orders_changed_vs_previous':None if previous_map is None else sum(om[k]!=previous_map[k] for k in om)})
        previous_map=om
    notify('summarizing')
    for name,s in scenarios.items():
        if s.get('metrics'):
            s['plan_fingerprint']=digest(plan_signature(s))
            s['delta_vs_baseline']={k:s['metrics'][k]-baseline['metrics'][k] for k in DIRECTIONS} if baseline['feasible'] else None
        if name not in ('selected','baseline_direct'):
            s.pop('trips',None)
            s.pop('order_outcomes',None)
    result={'schema_version':'dispatch_v1','engine':{'name':ENGINE_NAME,'version':ENGINE_VERSION,'executed_at':datetime.now(timezone.utc).isoformat(),'solver':selected['solver']},
        'inputs':{'orders':{'sha256':hashlib.sha256(orders_bytes).hexdigest(),'rows':len(orders)+len(excluded),**(inputs or {}).get('orders',{})},
                  'fleet':{'sha256':hashlib.sha256(fleet_bytes).hexdigest(),'rows':len(full_fleet),**(inputs or {}).get('fleet',{})},'anomalies':anomalies,'preflight':check},
        'configuration':{**config,'options':opts},'fleet':full_fleet,'kpi_directions':DIRECTIONS,'normalization':normalization,
        'assumptions':['Un viaje conecta un origen y un destino; no hay multiparada.',
            'La flota se asigna sólo desde pools cuya base coincide con el origen; tercerizados con base * pueden operar desde cualquier origen.',
            'La flota propia se limita por salidas diarias por pool, sin ocupación durante el retorno.',
            'Costo, combustible y CO₂ contemplan ida y vuelta. El costo por km ya incluye combustible.',
            'El plazo se pondera por unidades; llegada de una orden es la última entrega.',
            'Factores de emisiones informados por el usuario; no están certificados.',
            'No se modelan volumen, dimensiones, ventanas horarias ni tarifas por ruta.',
            'Las escalas usan extremos factibles conocidos; un resultado factible no demuestra optimalidad.'],
        'scenarios':scenarios,'sensitivity':{'weight_sweep':sweep,'frontier':sweep,'complete':len(sweep)==len(settings)}}
    # Exclude timing, storage identity, and solver runtime metadata from the deterministic fingerprint.
    stable={'version':ENGINE_VERSION,'configuration':result['configuration'],'orders_hash':result['inputs']['orders']['sha256'],
            'fleet_hash':result['inputs']['fleet']['sha256'],'scenarios':{k:{n:v for n,v in s.items() if n!='solver'} for k,s in scenarios.items()},
            'sensitivity':[{k:v for k,v in p.items() if k!='solver'} for p in sweep]}
    if perf_counter()-started > opts['total_time_limit_s']:
        raise TimeoutError('Se agotó el presupuesto global; no se publica una decisión parcial.')
    result['result_fingerprint']=digest(stable)
    result['engine']['wall_ms']=int((perf_counter()-started)*1000)
    return result
