"""Explicit converter. Preserve current assignment only as optional reference."""
import argparse
import csv
from pathlib import Path

COLUMNS = ['order_id', 'product', 'quantity_units', 'unit_weight_kg', 'origin', 'destination', 'distance_km', 'priority', 'max_delivery_days', 'dispatch_date', 'current_vehicle_type']


def convert(source: Path, target: Path):
    text = source.read_text(encoding='utf-8-sig')
    delimiter = ';' if ';' in text.splitlines()[0] else ','
    rows = list(csv.DictReader(text.splitlines(), delimiter=delimiter))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter=';')
        writer.writeheader()
        for row in rows:
            row['order_id'] = row['shipment_id']
            row['current_vehicle_type'] = row['vehicle_type']
            writer.writerow({k: row[k] for k in COLUMNS})
    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    print(f'{convert(args.source, args.target)} órdenes convertidas.')
