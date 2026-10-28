"""Canonical Trip-Order export: a Trip cost appears on its first row only."""


def transport_export_rows(core):
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
