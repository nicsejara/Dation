"""Serializer-only compatibility inputs; never published as business decisions."""
from decimal import Decimal
from app.results import contracts as c
from tests.ultimate_fixtures import core


def cases():
    entity=lambda i,**facts:c.EntityEvidence(entity_type='ORDER',entity_id='SERIALIZER-%03d'%i,facts=facts,reason_refs=())
    return {
        'empty':(core(),'entity_evidence_v1',()),
        'nullable_decimal_unicode':(core(),'entity_evidence_v1',(
            entity(1,unknown=None,zero=Decimal('0'),amount=Decimal('1.2500'),label='Cafe\u0301 · 東京'),)),
        'row_boundary_101':(core(),'entity_evidence_v1',tuple(entity(i,ordinal=i) for i in range(101))),
        'utf8_byte_boundary':(core(),'entity_evidence_v1',tuple(entity(i,test_text='é'*180000) for i in range(3))),
        'upstream_binding':(core('d2'),'engine_core_v1',(core('d2'),)),
    }
