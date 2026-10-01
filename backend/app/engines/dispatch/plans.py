from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP
import math
from .normalization import D, transit, capacity_units, raw_cost, departure_days, eligible_fleet


def trip(order, vehicle, day):
    return {'vehicle_type':vehicle['vehicle_type'],'ownership':vehicle['ownership'],
            'dispatch_date':day,'arrival_date':(date.fromisoformat(day)+timedelta(days=transit(order,vehicle))).isoformat(),
            'origin':order['origin'],'destination':order['destination'],'distance_km':order['distance_km'],
            'capacity_kg':vehicle['capacity_kg'],'loads':[], 'load_kg':0}


def add_load(t, order, units):
    kg = D(units)*D(order['unit_weight_kg'])
    t['loads'].append({'order_id':order['order_id'],'units':units,'kg':float(kg)})
    t['load_kg'] = float(D(t['load_kg'])+kg)


def greedy(orders, fleet, objective='min_cost', direct=False, current=False):
    """Deterministic constructive candidate. Failure is UNKNOWN, never proof of infeasibility."""
    plan, used = [], Counter()
    priority={'High':0,'Normal':1,'Low':2}
    ordered=sorted(orders,key=lambda o:(o['deadline'],priority[o['priority']],-o['unit_weight_kg']*o['quantity_units'],o['order_id']))
    for o in ordered:
        remaining=o['quantity_units']
        vehicles=eligible_fleet(o,fleet)
        if current:
            vehicles=[v for v in vehicles if v['vehicle_type']==o.get('current_vehicle_type')]
        while remaining:
            choices=[]
            for v in vehicles:
                days=[o['dispatch_date']] if direct else departure_days(o,v,fleet)
                for day in days:
                    key=(v['vehicle_type'],day)
                    # Existing consolidated trip costs no additional departure.
                    if not direct:
                        for idx,t in enumerate(plan):
                            if (t['vehicle_type'],t['dispatch_date'],t['origin'],t['destination']) != (v['vehicle_type'],day,o['origin'],o['destination']):continue
                            space=int((D(v['capacity_kg'])-D(t['load_kg']))//D(o['unit_weight_kg']))
                            if space:
                                lead=(date.fromisoformat(t['arrival_date'])-date.fromisoformat(o['dispatch_date'])).days
                                score=(lead,0) if objective=='min_time' else (0,lead)
                                choices.append((score,day,v['vehicle_type'],idx,min(space,remaining),v))
                    if v['units_available'] is not None and used[key]>=v['units_available']:continue
                    n=min(capacity_units(o,v),remaining)
                    lead=(date.fromisoformat(day)-date.fromisoformat(o['dispatch_date'])).days+transit(o,v)
                    if direct:
                        # Prefer own fleet; smallest fitting vehicle, largest if a split is needed.
                        score=(v['ownership']!='own',math.ceil(remaining/capacity_units(o,v)),v['capacity_kg'],float(raw_cost(o,v)))
                    elif objective=='min_time':score=(lead,float(raw_cost(o,v))/n)
                    elif objective=='min_trips':score=(1/n,float(raw_cost(o,v))/n,lead)
                    else:score=(float(raw_cost(o,v))/n,1/n,lead)
                    choices.append((score,day,v['vehicle_type'],len(plan),n,v))
            if not choices:return None
            _,day,_,idx,n,v=min(choices,key=lambda c:(c[0],c[1],c[2],c[3]))
            if idx==len(plan):
                if len(plan)>=10000:raise ValueError('El plan supera el límite operativo de 10.000 viajes. Dividí el horizonte en lotes; no se publica cobertura parcial.')
                plan.append(trip(o,v,day));used[(v['vehicle_type'],day)]+=1
            add_load(plan[idx],o,n);remaining-=n
    return canonical(plan)


def canonical(plan):
    result=sorted(plan,key=lambda t:(t['dispatch_date'],t['origin'],t['destination'],t['vehicle_type'],tuple(sorted((l['order_id'],l['units']) for l in t['loads']))))
    for idx,t in enumerate(result,1):
        t['trip_id']=f'V-{idx:05d}'
        t['loads'].sort(key=lambda l:l['order_id'])
    return result


def validate_plan(plan, orders, fleet, *, direct=False):
    by_id={o['order_id']:o for o in orders}; vehicles={v['vehicle_type']:v for v in fleet}
    counts, daily=Counter(),Counter()
    for t in plan:
        v=vehicles[t['vehicle_type']];daily[(v['vehicle_type'],t['dispatch_date'])]+=1
        load=D(0)
        for l in t['loads']:
            o=by_id[l['order_id']]
            if not isinstance(l['units'],int) or l['units']<=0:raise ValueError('Carga no entera.')
            if (t['origin'],t['destination'])!=(o['origin'],o['destination']):raise ValueError('Ruta inconsistente.')
            days=[o['dispatch_date']] if direct else departure_days(o,v,fleet)
            if t['dispatch_date'] not in days:raise ValueError('Salida fuera de ventana.')
            kg=D(o['unit_weight_kg'])*l['units']
            expected_arrival=(date.fromisoformat(t['dispatch_date'])+timedelta(days=transit(o,v))).isoformat()
            if t['arrival_date']!=expected_arrival or D(l['kg'])!=kg:raise ValueError('Llegada o peso de carga inconsistente.')
            if D(t['distance_km'])!=D(o['distance_km']):raise ValueError('Distancia inconsistente.')
            load+=kg;counts[o['order_id']]+=l['units']
        if not t['loads'] or D(t['load_kg'])!=load or D(t['capacity_kg'])!=D(v['capacity_kg']):raise ValueError('Carga o capacidad declarada inconsistente.')
        if load>D(v['capacity_kg']):raise ValueError('Capacidad excedida.')
    if counts!=Counter({o['order_id']:o['quantity_units'] for o in orders}):raise ValueError('No se conservan las unidades.')
    for (name,day),n in daily.items():
        limit=vehicles[name]['units_available']
        if limit is not None and n>limit:raise ValueError('Disponibilidad de flota excedida.')


def rounded(value):
    return float(D(value).quantize(D('.01'),rounding=ROUND_HALF_UP))


def summarize(plan, orders, fleet):
    vehicles={v['vehicle_type']:v for v in fleet};by_id={o['order_id']:o for o in orders}
    outcomes=defaultdict(list);cost=fuel=co2=capacity=load=distance=D(0); lead_units=0
    for t in plan:
        v=vehicles[t['vehicle_type']];o=by_id[t['loads'][0]['order_id']]
        c=raw_cost(o,v);km=D(o['distance_km'])*2
        f=km*D(v['fuel_l_per_100km'])/100;e=km*D(v['co2_kg_per_km'])
        cost+=c;fuel+=f;co2+=e;capacity+=D(v['capacity_kg']);load+=D(t['load_kg']);distance+=km
        t.update(cost=rounded(c),fuel_l=rounded(f),co2_kg=rounded(e),utilization=float(D(t['load_kg'])/D(v['capacity_kg'])))
        for l in t['loads']:
            outcomes[l['order_id']].append(t)
            lead_units+=l['units']*(date.fromisoformat(t['arrival_date'])-date.fromisoformat(by_id[l['order_id']]['dispatch_date'])).days
    order_outcomes=[]
    for o in orders:
        ts=outcomes[o['order_id']];arrival=max(t['arrival_date'] for t in ts);departure=min(t['dispatch_date'] for t in ts)
        order_outcomes.append({'order_id':o['order_id'],'trip_ids':[t['trip_id'] for t in ts],
            'dispatch_date':departure,'arrival_date':arrival,'deadline':o['deadline'],
            'late_days':max(0,(date.fromisoformat(arrival)-date.fromisoformat(o['deadline'])).days),
            'postponed_days':(date.fromisoformat(max(t['dispatch_date'] for t in ts))-date.fromisoformat(o['dispatch_date'])).days,
            'consolidated':any(len(t['loads'])>1 for t in ts),'outsourced':any(t['ownership']=='third_party' for t in ts)})
    units=sum(o['quantity_units'] for o in orders)
    unavoidable=sum(min(transit(o,v) for v in eligible_fleet(o,fleet))>o['max_delivery_days'] for o in orders)
    metrics={'total_cost':rounded(cost),'total_trips':len(plan),'avg_lead_time_days':round(lead_units/units,6),
        'on_time_rate':sum(o['late_days']==0 for o in order_outcomes)/len(orders),
        'late_orders_unavoidable':unavoidable,'units_delivered':units,'load_utilization':float(load/capacity),
        'trips_by_vehicle_type':dict(sorted(Counter(t['vehicle_type'] for t in plan).items())),
        'outsourced_trips_share':sum(t['ownership']=='third_party' for t in plan)/len(plan),
        'fuel_l':rounded(fuel),'co2_kg':rounded(co2),'total_weight_kg':rounded(load),'total_distance_km':rounded(distance),'orders':len(orders)}
    return {'metrics':metrics,'trips':plan,'order_outcomes':sorted(order_outcomes,key=lambda o:o['order_id'])}
