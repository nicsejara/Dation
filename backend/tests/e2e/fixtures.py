"""Small V3 inputs with feasible assignment/scheduling, independent of today's date."""
import csv
import io
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]


def csv_input(kind):
    rows=list(csv.DictReader(io.StringIO((REPO/f'sample_data/v3/{kind}.csv').read_text()),delimiter=';'))
    rows=rows[:2] if kind=='orders' else rows[:1]
    for row in rows:
        if kind=='orders':
            row.update(quantity_units='1',unit_weight_kg='500',distance_km='600',
                estimated_dispatch_date='2026-10-01',delivery_due_date='2026-10-10')
        else:
            row.update(capacity_kg='1000',avg_speed_kmh='100',driving_hours_per_day='10',
                available_from='2026-10-01',available_until='2026-10-31')
    output=io.StringIO()
    writer=csv.DictWriter(output,fieldnames=rows[0].keys(),delimiter=';',lineterminator='\n')
    writer.writeheader();writer.writerows(rows)
    return output.getvalue().encode()
