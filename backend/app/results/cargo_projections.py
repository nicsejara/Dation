"""Read-only projections of the independently certified cargo certificate."""
from . import contracts as c
from .canonical import canonical_bytes


def cargo_rows(detail):
    rows=[]
    for line in detail.lines:
        selected=tuple(a for a in detail.allocations if a.line_id==line.line_id)
        facts={**line.model_dump(exclude={'order_id'}),'catalog_hash':detail.catalog_hash,
            'trip_ids':tuple(sorted(a.trip_id for a in selected))}
        for index,a in enumerate(selected):
            facts['trip_'+str(index)+'_id']=a.trip_id;facts['trip_'+str(index)+'_quantity']=a.quantity
        rows.append(c.EntityEvidence(entity_type='ORDER',entity_id=line.order_id,facts=facts,reason_refs=()))
    return tuple(sorted(rows,key=lambda row:(row.entity_id,row.facts['line_id'])))


def cargo_descriptor(builder,detail):
    from .projections import descriptor
    data=builder.dataset('cargo','entity_evidence_v1',cargo_rows(detail))
    return descriptor('cargo','EVIDENCE',data,[('entity_id','ID',None),('facts.presentation_label','TEXT',None),('facts.requested','DECIMAL',None),
        ('facts.assigned','DECIMAL',None),('facts.unserved','DECIMAL',None),('facts.quantity_unit','TEXT',None),('facts.trip_ids','TEXT',None)],('entity_id','facts.line_id'))


def line_fields(row):
    return {'order_id':row.order_id,'line_id':row.line_id,'presentation_id':row.presentation_id,'presentation_label':row.presentation_label,
        'quantity':row.quantity,'quantity_unit':row.quantity_unit,'products_json':canonical_bytes(row.products).decode()}
