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


def assignment_matrix_inputs():
    """Reproducible QA tradeoffs; not the unavailable Golden Pallets v2 pack."""
    order_template=next(csv.DictReader(io.StringIO(csv_input('orders').decode()),delimiter=';'))
    fleet_template=next(csv.DictReader(io.StringIO(csv_input('fleet').decode()),delimiter=';'))
    orders=[{**order_template,'order_id':'QA-'+str(i+1),'product':'Carga QA '+str(i+1),
        'quantity_units':'6','unit_weight_kg':'500','origin':'Cordoba','destination':'Rosario','distance_km':'400'} for i in range(4)]
    fleet=[]
    for identifier,ownership,capacity,cost,fixed,co2 in (
        ('QA-OWN-L','own',8000,2.8,220,1.6),('QA-OWN-S','own',5000,1.1,70,.65),
        ('QA-EXTERNAL','third_party',12000,4.5,220,2.1)):
        fleet.append({**fleet_template,'vehicle_id':identifier,'license_plate':'','ownership':ownership,
            'provider_name':'Proveedor QA' if ownership=='third_party' else '',
            'base_site':'*' if ownership=='third_party' else 'Cordoba','capacity_kg':str(capacity),
            'cost_per_km':str(cost),'fixed_trip_cost':str(fixed),'co2_kg_per_km':str(co2)})
    result={}
    for kind,rows in (('orders',orders),('fleet',fleet)):
        stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=rows[0].keys(),delimiter=';',lineterminator='\n')
        writer.writeheader();writer.writerows(rows);result[kind]=stream.getvalue().encode()
    return result


def scheduling_dashboard_inputs():
    """QA temporal reproducible: dos bases, secuencias paralelas y cargas en pallets.

    No sustituye ni se presenta como el paquete externo Golden Pallets v2.
    """
    order_template=next(csv.DictReader(io.StringIO(csv_input('orders').decode()),delimiter=';'))
    fleet_template=next(csv.DictReader(io.StringIO(csv_input('fleet').decode()),delimiter=';'))
    orders=[];fleet=[]
    for site,index in (('Cordoba',1),('Rosario',2)):
        for ordinal,due,priority in ((1,'2026-10-04','High'),(2,'2026-10-20','Normal')):
            orders.append({**order_template,'order_id':f'D2-{index}-{ordinal}','product':'Pallet QA',
                'quantity_units':'20','unit_weight_kg':'500','origin':site,'destination':'Destino '+str(index),
                'distance_km':'600','priority':priority,'estimated_dispatch_date':'2026-10-01','delivery_due_date':due})
        fleet.append({**fleet_template,'vehicle_id':'QA-TIME-'+str(index),'license_plate':'','ownership':'own',
            'base_site':site,'capacity_kg':'8000' if index==1 else '5000','available_from':'2026-10-01','available_until':'2026-10-31'})
    result={}
    for kind,rows in (('orders',orders),('fleet',fleet)):
        output=io.StringIO();writer=csv.DictWriter(output,fieldnames=rows[0].keys(),delimiter=';',lineterminator='\n')
        writer.writeheader();writer.writerows(rows);result[kind]=output.getvalue().encode()
    return result
