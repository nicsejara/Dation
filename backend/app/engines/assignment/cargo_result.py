"""Extract exact physical line quantities; no percentages create cargo."""
from collections import defaultdict
from decimal import Decimal
from app.domain.logistics.physical import normalize_catalog
from app.domain.logistics.units import QUANTITY_SCALES,QuantityVector
from app.results.canonical import canonical_bytes,content_sha256
from app.results import contracts as c


def allocations_for_slot(request,orders,slot,physical=None):
    from .transport_plan import ratio
    dims=request.model.active_dimensions;primary=request.model.primary_dimension;totals=defaultdict(lambda:{d:Decimal(0) for d in dims});lines=[]
    cfg=request.model.configuration;catalog=physical if physical is not None else normalize_catalog(cfg.cargo,dims);products={p.product_id:p for p in cfg.cargo.products}
    for key,n in sorted((slot.line_values or {}).items()):
        if not n:continue
        quantum=slot.line_quantums[key];order=orders[key[0]];load=QuantityVector(**{d:Decimal(n*quantum.coefficients[d]).scaleb(-QUANTITY_SCALES[d]) for d in dims})
        for d in dims:totals[order.order_id][d]+=getattr(load,d)
        if quantum.line_id:
            presentation=catalog[quantum.presentation_id];quantity=Decimal(n)*quantum.step;portions=[]
            for part in presentation.composition:
                product=products[part['product_id']];bulk=presentation.quantity_kind=='CONTINUOUS'
                portions.append(c.CargoProductPortion(product_id=product.product_id,product_name=product.name,quantity=part['quantity']*quantity,unit_label=presentation.quantity_unit if bulk else product.unit_label,
                    product_units=None if bulk else part['product_units']*quantity))
            lines.append({'order_id':order.order_id,'line_id':quantum.line_id,'presentation_id':quantum.presentation_id,'presentation_label':next(p.label for p in cfg.cargo.presentations if p.presentation_id==quantum.presentation_id),'quantity':quantity,'quantity_unit':presentation.quantity_unit,'load':load,'products':tuple(sorted(portions,key=lambda p:p.product_id))})
    by_id={o.order_id:o for o in orders};allocations=[]
    for oid,values in sorted(totals.items()):
        allocations.append(c.Allocation(order_id=oid,allocation_fraction=ratio(values[primary],getattr(by_id[oid].requested,primary),6),load=QuantityVector(**values)))
    return allocations,lines


def cargo_detail(request,allocations):
    cfg=request.model.configuration
    if cfg.cargo.input_mode!='catalog':return None
    catalog=normalize_catalog(cfg.cargo,cfg.active_dimensions);amounts=defaultdict(Decimal)
    for line in allocations:amounts[line.line_id]+=line.quantity
    resolutions=[]
    for order in sorted(request.demands,key=lambda o:o.order_id):
        for line in sorted(order.lines,key=lambda l:l.line_id):
            p=catalog[line.presentation_id];assigned=amounts[line.line_id]
            resolutions.append(c.CargoLineResolution(order_id=order.order_id,line_id=line.line_id,presentation_id=line.presentation_id,presentation_label=next(p.label for p in cfg.cargo.presentations if p.presentation_id==line.presentation_id),quantity_kind=p.quantity_kind,quantity_unit=p.quantity_unit,
                requested=line.quantity,assigned=assigned,unserved=line.quantity-assigned))
    return c.CargoPlanDetail(catalog_hash=content_sha256(canonical_bytes(catalog)),allocations=tuple(sorted(allocations,key=lambda a:(a.trip_id,a.order_id,a.line_id))),lines=tuple(resolutions))


def trip_groups(request,trip,cargo):
    if cargo is None:return {g for o in request.demands if o.order_id in {a.order_id for a in trip.orders} for g in o.compatibility_groups}
    selected={a.line_id for a in cargo.allocations if a.trip_id==trip.trip_id}
    return {g for o in request.demands for line in o.lines if line.line_id in selected for g in line.compatibility_groups}
