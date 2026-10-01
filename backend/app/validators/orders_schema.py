from datetime import datetime, date, timedelta
from app.validators.dispatch_common import rows_from_csv, number, unique, fail

COLUMNS = ['order_id', 'product', 'quantity_units', 'unit_weight_kg', 'origin',
           'destination', 'distance_km', 'priority', 'max_delivery_days', 'dispatch_date']


def validate_orders_csv(contents: bytes) -> dict:
    # A mixed legacy file must go through the explicit converter.
    header = contents.decode('utf-8-sig', errors='replace').splitlines()[0:1]
    if header and any(k in header[0] for k in ('vehicle_capacity_kg', 'fixed_trip_cost', 'cost_per_km')):
        raise ValueError('El archivo mezcla órdenes y flota. Usá el conversor legacy o la plantilla de órdenes.')
    rows, columns = rows_from_csv(contents, COLUMNS, {'shipment_id': 'order_id', 'vehicle_type': 'current_vehicle_type'})
    unique(rows, 'order_id')
    routes, products, warnings = {}, {}, []
    for r in rows:
        for key in ('quantity_units', 'max_delivery_days'):
            r[key] = number(r, key, positive=True, integer=True)
        if r['max_delivery_days'] > 90:
            fail(r['_row'], 'max_delivery_days', 'el horizonte máximo del MVP es 90 días')
        for key in ('unit_weight_kg', 'distance_km'):
            r[key] = number(r, key, positive=True)
        if r['origin'] == r['destination']:
            fail(r['_row'], 'destination', 'debe ser distinta al origen')
        if r['priority'] not in ('High', 'Normal', 'Low'):
            fail(r['_row'], 'priority', 'usar High, Normal o Low')
        try:
            # Slash dates have an explicit day-first contract; never guess US dates.
            value = r['dispatch_date']
            parsed = datetime.strptime(value, '%d/%m/%Y').date() if '/' in value else date.fromisoformat(value)
            r['dispatch_date'] = parsed.isoformat()
            r['deadline'] = (parsed + timedelta(days=r['max_delivery_days'])).isoformat()
        except ValueError:
            fail(r['_row'], 'dispatch_date', 'usar YYYY-MM-DD o d/m/YYYY; no se infiere mes/día')
        route = (r['origin'], r['destination'])
        if route in routes and routes[route] != r['distance_km']:
            fail(r['_row'], 'distance_km', 'distancia inconsistente para la misma ruta')
        routes[route] = r['distance_km']
        if r['product'] in products and products[r['product']] != r['unit_weight_kg']:
            warnings.append({'code': 'PRODUCT_WEIGHT_VARIATION', 'row': r['_row'], 'column': 'unit_weight_kg', 'detail': 'El producto tiene pesos distintos.'})
        products[r['product']] = r['unit_weight_kg']
    return {'schema': 'orders_v1', 'rows': len(rows), 'columns': len(columns), 'warnings': warnings,
            'records': rows, 'profile': {'total_units': sum(r['quantity_units'] for r in rows),
            'total_weight_kg': sum(r['quantity_units'] * r['unit_weight_kg'] for r in rows),
            'routes': len(routes), 'date_from': min(r['dispatch_date'] for r in rows),
            'date_to': max(r['dispatch_date'] for r in rows)}}
