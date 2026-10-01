"""Pure preparation and cross-file validation; no persistence."""
from datetime import date, timedelta
from decimal import Decimal
import math

D = lambda value: Decimal(str(value))


def transit(order, vehicle):
    return math.ceil(D(order['distance_km']) / (D(vehicle['avg_speed_kmh']) * D(vehicle['driving_hours_per_day'])))


def capacity_units(order, vehicle):
    return int(D(vehicle['capacity_kg']) // D(order['unit_weight_kg']))


def raw_cost(order, vehicle):
    return 2 * D(order['distance_km']) * D(vehicle['cost_per_km']) + D(vehicle['fixed_trip_cost'])


def eligible_fleet(order, fleet):
    return [v for v in fleet if capacity_units(order,v) and v['units_available'] != 0]


def departure_days(order, vehicle, fleet):
    start = date.fromisoformat(order['dispatch_date'])
    deadline = date.fromisoformat(order['deadline'])
    eligible = eligible_fleet(order, fleet)
    if not eligible:
        return []
    inevitable = all(transit(order,v) > order['max_delivery_days'] for v in eligible)
    end = start if inevitable else deadline - timedelta(days=transit(order, vehicle))
    return [(start + timedelta(days=i)).isoformat() for i in range(max(0,(end-start).days+1))]


def preflight(orders, fleet, reference_fleet=None):
    warnings, errors, anomalies = [], [], []
    names = {v['vehicle_type'] for v in (reference_fleet or fleet)}
    own = [v['capacity_kg'] for v in fleet if v['ownership']=='own']
    cap = max(own or [v['capacity_kg'] for v in fleet])
    if not any(v['units_available'] is None for v in fleet):
        warnings.append({'code':'FINITE_FLEET','detail':'No hay flota ilimitada; la cobertura depende de las fechas y la disponibilidad.'})
    for o in orders:
        base = {'order_id':o['order_id'], 'row':o.get('_row')}
        if o.get('current_vehicle_type') and o['current_vehicle_type'] not in names:
            errors.append({**base,'code':'UNKNOWN_CURRENT_VEHICLE','detail':'El camión de referencia no existe en la flota.'})
        eligible = eligible_fleet(o,fleet)
        if not eligible:
            errors.append({**base,'code':'UNIT_EXCEEDS_CAPACITY','detail':'No hay un camión disponible que pueda transportar una unidad entera.'})
        elif min(transit(o,v) for v in eligible) > o['max_delivery_days']:
            warnings.append({**base,'code':'UNAVOIDABLE_LATE','detail':'La entrega resulta tardía aun con la salida más temprana y el camión más rápido.'})
        n = min((math.ceil(o['quantity_units']/capacity_units(o,v)) for v in eligible), default=0)
        if n > 20:
            warnings.append({**base,'code':'MANY_TRIPS','detail':f'La orden requiere al menos {n} viajes independientes.'})
        if D(o['quantity_units'])*D(o['unit_weight_kg']) > D(cap)*20:
            anomalies.append({**base,'code':'ORDER_WEIGHT_OUTLIER','detail':'La orden supera 20 veces la mayor capacidad propia; decidí incluirla o excluirla.'})
    return {'valid':not errors,'errors':errors,'warnings':warnings,'anomalies':anomalies}
