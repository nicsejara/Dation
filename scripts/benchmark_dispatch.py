"""Run from repo root: PYTHONPATH=backend python scripts/benchmark_dispatch.py."""
import csv,io,json,time
from pathlib import Path
from app.engines.dispatch import run_dispatch_engine


def orders_scaled(n):
    rows=list(csv.DictReader(Path('sample_data/v1/orders.csv').open(),delimiter=';'))
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=rows[0].keys(),delimiter=';');w.writeheader()
    for i in range(n):w.writerow({**rows[i%len(rows)],'order_id':f'B-{i+1:05d}'})
    return out.getvalue().encode()


if __name__=='__main__':
    for n in (100,1000):
        data=orders_scaled(n);fleet=Path('sample_data/v1/fleet.csv').read_bytes();start=time.perf_counter()
        result=run_dispatch_engine(data,fleet)
        elapsed=time.perf_counter()-start
        if n==100:Path('/tmp/dispatch100.json').write_text(json.dumps(result))
        print(json.dumps({'orders':n,'seconds':round(elapsed,3),'bytes':len(json.dumps(result).encode()),
            'trips':result['scenarios']['selected']['metrics']['total_trips'],'units':result['scenarios']['selected']['metrics']['units_delivered'],
            'method':result['scenarios']['selected']['solver']['method'],'fingerprint':result['result_fingerprint']}),flush=True)
