from app.validators.dispatch_common import rows_from_csv, number, unique, fail

COLUMNS = ['vehicle_type', 'ownership', 'capacity_kg', 'cost_per_km', 'fixed_trip_cost',
           'units_available', 'avg_speed_kmh', 'driving_hours_per_day', 'fuel_l_per_100km', 'co2_kg_per_km']


def validate_fleet_csv(contents: bytes) -> dict:
    rows, columns = rows_from_csv(contents, [k for k in COLUMNS if k != 'units_available'])
    if 'units_available' not in columns:
        raise ValueError('Falta la columna units_available.')
    unique(rows, 'vehicle_type')
    for r in rows:
        if r['ownership'] not in ('own', 'third_party'):
            fail(r['_row'], 'ownership', 'usar own o third_party')
        for key in ('capacity_kg', 'avg_speed_kmh'):
            r[key] = number(r, key, positive=True)
        for key in ('cost_per_km', 'fixed_trip_cost', 'fuel_l_per_100km', 'co2_kg_per_km'):
            r[key] = number(r, key)
        r['driving_hours_per_day'] = number(r, 'driving_hours_per_day', minimum=1)
        if r['driving_hours_per_day'] > 24:
            fail(r['_row'], 'driving_hours_per_day', 'no puede superar 24')
        if r.get('units_available', '') == '':
            if r['ownership'] != 'third_party':
                fail(r['_row'], 'units_available', 'la flota propia requiere disponibilidad')
            r['units_available'] = None
        else:
            r['units_available'] = number(r, 'units_available', integer=True)
    return {'schema': 'fleet_v1', 'rows': len(rows), 'columns': len(columns), 'warnings': [],
            'records': rows, 'profile': {'fleet': rows, 'own_capacity_kg_per_day': sum(
                r['capacity_kg'] * r['units_available'] for r in rows if r['ownership'] == 'own')}}
