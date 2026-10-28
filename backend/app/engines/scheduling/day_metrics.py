"""D2 metric certifier: disjoint counts, known-margin denominator, stable peak."""
from collections import Counter
from decimal import Decimal,ROUND_HALF_UP,localcontext
from app.results.metrics import DaySchedulingMetrics

def rounded(n,d):
    with localcontext() as ctx:
        ctx.prec=60
        return None if not d else (Decimal(n)/Decimal(d)).quantize(Decimal('.0001'),rounding=ROUND_HALF_UP)

def schedule_metrics(trips):
    counts=Counter(t.status for t in trips);days=Counter(t.dispatch_date for t in trips if t.dispatch_date is not None)
    scheduled=sum(counts[s] for s in ['ON_TIME','AT_RISK','LATE']);margins=[t.schedule_margin_days for t in trips if t.schedule_margin_days is not None]
    peak=min(days,key=lambda day:(-days[day],day)) if days else None
    return DaySchedulingMetrics(scheduled_trips={'scheduled':scheduled,'total':len(trips),'ratio':rounded(scheduled,len(trips))},
        service_level={'on_time':counts['ON_TIME'],'at_risk':counts['AT_RISK'],'late':counts['LATE'],'pre_horizon':counts['PRE_HORIZON_DISPATCH_REQUIRED'],'unscheduled':counts['UNSCHEDULED']},
        on_time_ratio=rounded(counts['ON_TIME']+counts['AT_RISK'],len(trips)),average_schedule_margin_days=rounded(sum(margins),len(margins)),
        peak_dispatch_day={'date':peak,'trip_count':days[peak]} if peak else None,exception_count=sum(t.status!='ON_TIME' for t in trips))
