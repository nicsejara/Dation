"""Bounded evidence and conservative numeric consistency guard for dispatch explanations."""
import json
import re


def build_dispatch_context(result):
    selected=result['scenarios']['selected']
    context={'schema_version':'dispatch_v1','configuration':result['configuration'],
        'solver':selected['solver'],'normalization':result['normalization'],
        'scenarios':{s['name']:{'metrics':s.get('metrics'),'feasible':s.get('feasible'),'delta_vs_baseline':s.get('delta_vs_baseline')} for s in result['scenarios'].values()},
        'fleet':result['fleet'],'anomalies':result['inputs']['anomalies'][:10],
        'changes':{k:sum(bool(o[k]) for o in selected['order_outcomes']) for k in ('consolidated','outsourced','postponed_days','late_days')},
        'examples':sorted(selected['order_outcomes'],key=lambda o:(-o['late_days'],-o['postponed_days'],o['order_id']))[:5],
        'sensitivity':[{'weights':p['weights'],'metrics':p['metrics'],'orders_changed':p['orders_changed_vs_selected']} for p in result['sensitivity']['weight_sweep']],
        'assumptions':result['assumptions']}
    # Bound user-provided strings and collections before serializing. Never split JSON.
    def bounded(value):
        if isinstance(value,str):return value[:240]
        if isinstance(value,list):return [bounded(v) for v in value[:20]]
        if isinstance(value,dict):return {str(k)[:120]:bounded(v) for k,v in list(value.items())[:30]}
        return value
    context=bounded(context)
    if len(json.dumps(context,ensure_ascii=False))>18000:
        context['examples']=[];context['fleet']=[];context['sensitivity']=[]
        for scenario in context['scenarios'].values():
            if scenario.get('metrics'):scenario['metrics'].pop('trips_by_vehicle_type',None)
        context['context_note']='Se omitieron ejemplos, detalle de flota y sensibilidad para acotar el contexto.'
    if len(json.dumps(context,ensure_ascii=False))>18000:
        context={'schema_version':'dispatch_v1','configuration':{k:result['configuration'][k] for k in ('mode','objective','weights')},
                 'selected_metrics':{k:v for k,v in selected['metrics'].items() if isinstance(v,(int,float))},
                 'assumptions':bounded(result['assumptions']),
                 'context_note':'Contexto reducido: consultar el dashboard para comparaciones y detalle.'}

    return context


def verify_numbers(text, context):
    """Conservative presence check, not a proof of semantic correctness."""
    allowed=set()
    def collect(v):
        if isinstance(v,bool) or v is None:return
        if isinstance(v,(float,int)):
            for n in (v,v*100 if abs(v)<=1 else v):
                for precision in (0,1,2,3,6):allowed.add(round(float(n),precision))
        elif isinstance(v,dict):
            for x in v.values():collect(x)
        elif isinstance(v,list):
            for x in v:collect(x)
    collect(context)
    # Numeric identifiers and dates are not interpreted as numerical claims.
    cleaned=re.sub(r'\b\d{4}-\d{2}-\d{2}\b|\b[A-Za-z]+-\d+\b','',text)
    for token in re.findall(r'(?<![\w])\d+(?:[.,]\d+)*',cleaned):
        variants=[]
        try:variants.append(float(token.replace('.','').replace(',','.')))
        except ValueError:pass
        try:variants.append(float(token.replace(',','')))
        except ValueError:pass
        if not any(any(abs(v-a)<=1e-6 for a in allowed) for v in variants):return False
    return True


def safe_explanation(result):
    m=result['scenarios']['selected']['metrics']
    return {'executive_summary':f"Plan validado para {m['orders']} órdenes y {m['total_trips']} viajes.",
        'recommendation':'Revisá el calendario y las entregas tardías antes de aprobar el despacho.',
        'why_recommended':'El motor evaluó capacidad por unidades enteras, disponibilidad diaria y ventanas de salida.',
        'business_impact':{'cost':'Consultá el costo calculado en los KPIs.','trips':'Consultá el plan de viajes.','distance':'Se contempla ida y vuelta.'},
        'key_drivers':['Disponibilidad de flota y posibilidad de consolidar cargas.'],
        'tradeoffs':['La prioridad elegida puede aumentar la tercerización o postergar salidas.'],
        'assumptions':result['assumptions'],
        'caveats':['La respuesta de IA no superó la comprobación de cifras. Se muestra una explicación determinística de respaldo.'],
        'suggested_questions':['¿Qué órdenes llegan tarde?']}
