"""Independent physical certificate, without solver or extraction imports."""
from collections import defaultdict
from decimal import Decimal
from itertools import combinations

from app.domain.logistics.physical import normalize_catalog, line_load
from app.results.canonical import canonical_bytes, content_sha256


def certify_cargo(request, plan):
    def check(value, message):
        if not value:
            raise ValueError(message)

    cfg = getattr(request.model, 'configuration', None)
    detail = plan.cargo
    catalog_mode = cfg is not None and cfg.cargo.input_mode == 'catalog'
    if not catalog_mode:
        check(detail is None, 'Unexpected catalog result')
    if cfg is None:
        return
    dims = cfg.active_dimensions
    orders = {o.order_id: o for o in request.demands}
    resources = {r.resource_id: r for r in request.resources}
    trips = {t.trip_id: t for t in plan.trips}
    trip_groups = defaultdict(list)
    if catalog_mode:
        check(detail is not None, 'Missing catalog conservation certificate')
        catalog = normalize_catalog(cfg.cargo, dims)
        check(detail.catalog_hash == content_sha256(canonical_bytes(catalog)), 'Catalog hash differs')
        inputs = {line.line_id: (o, line) for o in orders.values() for line in o.lines}
        summaries = {line.line_id: line for line in detail.lines}
        check(len(summaries) == len(detail.lines) and set(summaries) == set(inputs), 'Line resolution set differs')
        totals = defaultdict(Decimal)
        vectors = defaultdict(lambda: {d: Decimal(0) for d in dims})
        line_trips = defaultdict(set)
        seen = set()
        for row in detail.allocations:
            key = row.trip_id, row.line_id
            check(key not in seen and row.trip_id in trips and row.line_id in inputs, 'Duplicate/orphan cargo allocation')
            seen.add(key)
            order, line = inputs[row.line_id]
            check(row.order_id == order.order_id and row.presentation_id == line.presentation_id, 'Line identity changed')
            check(row.order_id in {a.order_id for a in trips[row.trip_id].orders}, 'Cargo not represented by Trip allocation')
            check(row.presentation_label == next(p.label for p in cfg.cargo.presentations if p.presentation_id == line.presentation_id), 'Presentation label changed')
            physical = catalog[line.presentation_id]
            check(row.quantity_unit == physical.quantity_unit, 'Line quantity unit changed')
            expected = line_load(physical, row.quantity)
            check(row.load == expected, 'Line physical vector differs')
            products = {p.product_id: p for p in row.products}
            check(len(products) == len(row.products) and set(products) == {p['product_id'] for p in physical.composition}, 'Line composition changed')
            source_products = {p.product_id: p for p in cfg.cargo.products}
            for part in physical.composition:
                product = products[part['product_id']]
                continuous = physical.quantity_kind == 'CONTINUOUS'
                check(product.product_name == source_products[product.product_id].name, 'Product name changed')
                check(product.quantity == part['quantity'] * row.quantity, 'Product quantity changed')
                check(product.product_units == (None if continuous else part['product_units'] * row.quantity), 'Product units changed')
                check(product.unit_label == (physical.quantity_unit if continuous else source_products[product.product_id].unit_label), 'Product unit label changed')
            totals[row.line_id] += row.quantity
            line_trips[row.line_id].add(row.trip_id)
            for d in dims:
                vectors[row.trip_id, row.order_id][d] += getattr(expected, d)
            trip_groups[row.trip_id].append(line.compatibility_groups)
        for lid, (order, line) in inputs.items():
            summary = summaries[lid]
            check(summary.presentation_label == next(p.label for p in cfg.cargo.presentations if p.presentation_id == line.presentation_id), 'Resolution label changed')
            physical = catalog[line.presentation_id]
            check((summary.order_id, summary.presentation_id, summary.quantity_kind, summary.quantity_unit) ==
                  (order.order_id, line.presentation_id, physical.quantity_kind, physical.quantity_unit), 'Line resolution identity differs')
            check(summary.requested == line.quantity and summary.assigned == totals[lid] and
                  summary.assigned + summary.unserved == line.quantity and summary.unserved >= 0, 'Line conservation violated')
            if not (order.split_allowed and cfg.split_permitted):
                check(totals[lid] in (0, line.quantity) and len(line_trips[lid]) <= 1, 'Indivisible line split')
        for trip in plan.trips:
            for allocation in trip.orders:
                check(all(getattr(allocation.load, d) == vectors[trip.trip_id, allocation.order_id][d] for d in dims), 'Aggregate and line loads differ')
        for order in orders.values():
            if not (order.split_allowed and cfg.split_permitted):
                assigned = [totals[line.line_id] > 0 for line in order.lines]
                check(not any(assigned) or all(assigned), 'Indivisible order has missing lines')
                check(len(set().union(*(line_trips[line.line_id] for line in order.lines))) <= 1, 'Indivisible order spans Trips')
    else:
        for trip in plan.trips:
            for allocation in trip.orders:
                trip_groups[trip.trip_id].append(orders[allocation.order_id].compatibility_groups)
                for d in ('pallets', 'units'):
                    amount = getattr(allocation.load, d)
                    check(amount is None or amount == amount.to_integral_value(), 'Fractional physical object')
    # Resource eligibility and co-load authorization are distinct contracts.
    for tid, trip in trips.items():
        resource = resources[trip.resource_id]
        if cfg.resource_categories:
            check(getattr(resource, 'resource_category', None) in cfg.resource_categories, 'Ineligible resource category')
        check(cfg.consolidation_permitted or len(trip.orders) <= 1, 'Consolidation disabled')
        groups = trip_groups[tid]
        for tags in groups:
            check(set(tags).issubset(resource.compatibility_groups) if tags else cfg.homogeneous_loads_declared, 'Ineligible line/resource')
        if cfg.cargo.compatibility_policy == 'CATEGORIZED':
            pairs = {frozenset(pair) for pair in cfg.cargo.co_load_pairs}
            for left, right in (*((g,g) for g in groups), *combinations(groups, 2)):
                check(bool(left) and bool(right) and all(a == b or frozenset((a, b)) in pairs for a in left for b in right), 'Incompatible co-loaded cargo')
