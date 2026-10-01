"""Reproducible synthetic CSV cases. Run from root with PYTHONPATH=backend."""
import csv
import json
from pathlib import Path
from app.validators.orders_schema import COLUMNS
from app.validators.fleet_schema import COLUMNS as FLEET_COLUMNS

ROOT = Path(__file__).resolve().parents[1] / 'sample_data/v1'


def order(identifier='A', units=1, weight=400, window=2, distance=100):
    return dict(zip(COLUMNS, [identifier, 'Producto sintético', units, weight,
        'Origen', 'Destino', distance, 'Normal', window, '2026-10-01']))


def fleet(third_party=True):
    rows = [dict(zip(FLEET_COLUMNS, ['Small', 'own', 1000, 1, 10, 1, 100, 10, 20, .5]))]
    if third_party:
        rows.append(dict(zip(FLEET_COLUMNS, ['External', 'third_party', 1000, 2, 20, '', 100, 10, 20, .5])))
    return rows


def write(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=columns, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)


def generate():
    cases = [
        ('01_consolidacion', [order('A'), order('B')], fleet(), {'objective': 'min_trips'}, {},
         {'units_delivered': 2, 'total_trips': 1}),
        ('02_unidades_indivisibles', [order(units=3, weight=600, window=1)], fleet(), {'objective': 'min_cost'}, {},
         {'units_delivered': 3, 'total_trips': 3, 'outsourced_trips_share': 2/3}),
        ('03_reprogramacion', [order(units=2, weight=600)], fleet(False), {'objective': 'min_cost'}, {},
         {'units_delivered': 2, 'total_trips': 2, 'outsourced_trips_share': 0}),
        ('04_tardanza_inevitable', [order(window=1, distance=2500)], fleet(), {'objective': 'min_time'}, {},
         {'units_delivered': 1, 'late_orders_unavoidable': 1, 'on_time_rate': 0}),
        ('05_anomalia_incluir', [order('A', 51), order('B')], fleet(), {'objective': 'min_cost'}, {'anomaly_decisions': {'A': 'include'}},
         {'units_delivered': 52}),
        ('06_anomalia_excluir', [order('A', 51), order('B')], fleet(), {'objective': 'min_cost'}, {'anomaly_decisions': {'A': 'exclude'}},
         {'units_delivered': 1}),
        ('07_sin_cobertura', [order(units=3, weight=600, window=1)], fleet(False), {'objective': 'min_cost'}, {},
         {'error_contains': 'No se encontró un plan factible'}),
        ('08_fecha_invalida', [{**order(), 'dispatch_date': '31/02/2026'}], fleet(), {'objective': 'min_cost'}, {},
         {'error_contains': 'dispatch_date'}),
        ('09_ruta_inconsistente', [order('A'), order('B', distance=200)], fleet(), {'objective': 'min_cost'}, {},
         {'error_contains': 'distancia inconsistente'}),
    ]
    manifest = []
    for name, orders, vehicles, config, options, expected in cases:
        folder = ROOT / 'cases' / name
        write(folder/'orders.csv', COLUMNS, orders)
        write(folder/'fleet.csv', FLEET_COLUMNS, vehicles)
        manifest.append({'case': name, 'configuration': config, 'options': options, 'expected': expected})
    (ROOT/'cases/expected.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    with (ROOT/'orders.csv').open(encoding='utf-8') as source:
        originals = list(csv.DictReader(source, delimiter=';'))
    write(ROOT/'orders_1000.csv', list(originals[0]),
          ({**originals[i % len(originals)], 'order_id': f'B-{i+1:05d}'} for i in range(1000)))
    print(f'Generated {len(cases)} cases and orders_1000.csv')


if __name__ == '__main__':
    generate()
