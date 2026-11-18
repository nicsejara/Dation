"""Canonical Trip-Order export: a Trip cost appears on its first row only."""


def transport_export_rows(core):
    if core.transport_plan.cargo is not None:
        from .cargo_projections import line_fields
        rows=[];seen=set();trips={t.trip_id:t for t in core.transport_plan.trips}
        for line in core.transport_plan.cargo.allocations:
            t=trips[line.trip_id]
            rows.append({'trip_id':line.trip_id,**line_fields(line),'origin_id':t.origin_id,'destination_id':t.destination_id,
                'resource_id':t.resource_id,'resource_source':t.resource_source,'distance_km':t.distance_km,
                'ready_date':t.ready_date,'delivery_due_date':t.delivery_due_date,
                'estimated_cost':t.estimated_cost.amount if t.trip_id not in seen and t.estimated_cost else None,'currency':core.context.currency_policy.currency,
                **{'load_'+d:getattr(line.load,d) for d in core.context.active_dimensions}})
            seen.add(t.trip_id)
        return tuple(rows)
    rows=[]
    for trip in sorted(core.transport_plan.trips,key=lambda t:t.trip_id):
        for index,allocation in enumerate(sorted(trip.orders,key=lambda a:a.order_id)):
            row={'trip_id':trip.trip_id,'order_id':allocation.order_id,'origin_id':trip.origin_id,'destination_id':trip.destination_id,
                'resource_id':trip.resource_id,'resource_source':trip.resource_source,'distance_km':trip.distance_km,
                'allocation_fraction':allocation.allocation_fraction,'ready_date':trip.ready_date,'delivery_due_date':trip.delivery_due_date,
                'estimated_cost':trip.estimated_cost.amount if index==0 and trip.estimated_cost else None,
                'currency':core.context.currency_policy.currency}
            row.update({'load_'+d:getattr(allocation.load,d) for d in core.context.active_dimensions})
            rows.append(row)
    return tuple(rows)
