"""DATION_CANONICAL_V1. Decimal strings, Unicode NFC, exact SHA256 DAG.

Only projections declared here define mathematical fingerprints. Generic JSON
serialization is never permission checking or a replacement for typed validation.
"""
from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
import unicodedata
from uuid import UUID

from pydantic import BaseModel
from app.domain.logistics.base import CANONICAL_VERSION, MAX_SCALED_INTEGER, decimal_text


def _data(value):
    return value.model_dump(mode="python", by_alias=True) if isinstance(value, BaseModel) else value


def _decimal_text(value):
    return decimal_text(value)


def canonical_tree(value, *, _depth=0):
    if _depth > 64:
        raise ValueError("Canonical structure is too deep")
    value = _data(value)
    if value is None or type(value) is bool:
        return value
    if isinstance(value, Enum):
        return canonical_tree(value.value, _depth=_depth+1)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Canonical timestamps require an explicit timezone")
        return value.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if type(value) is int:
        if abs(value) > MAX_SCALED_INTEGER:
            raise ValueError("Canonical integer exceeds the signed 64-bit contract")
        return value
    if isinstance(value, float):
        raise ValueError("Binary floats, NaN and Infinity are not canonical inputs")
    if isinstance(value, str):
        value = unicodedata.normalize('NFC', value)
        value.encode('utf-8')  # reject unpaired Unicode surrogates
        return value
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("Canonical object keys must be strings")
            key = unicodedata.normalize('NFC', key)
            if key in result:
                raise ValueError("Canonical Unicode key collision")
            result[key] = canonical_tree(item, _depth=_depth+1)
        return result
    if isinstance(value, (list, tuple)):
        return [canonical_tree(item, _depth=_depth+1) for item in value]
    raise ValueError("Unsupported canonical value: " + type(value).__name__)


def canonical_bytes(value) -> bytes:
    return json.dumps(canonical_tree(value), sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def content_sha256(content: bytes) -> str:
    if not isinstance(content, bytes):
        raise ValueError("Content hash requires the exact immutable bytes")
    return hashlib.sha256(content).hexdigest()


def _hash(kind, projection):
    return content_sha256(canonical_bytes({'canonical_version':CANONICAL_VERSION, 'kind':kind, 'value':projection}))


def policy_projection(policy):
    value = dict(_data(policy))
    value.pop('override_reason', None)  # historical explanation, not an objective/constraint
    value['guardrails'] = sorted(value.get('guardrails', ()), key=lambda item:item['kind'])
    value['preferences'] = sorted(value.get('preferences', ()), key=lambda item:item['kind'])
    return value


def policy_hash(policy):
    return _hash('POLICY', policy_projection(policy))


def input_context_projection(context, runtime_identity, upstream=None):
    value = dict(_data(context))
    value.pop('case_name', None)
    value.pop('display_metadata', None)
    value['case_policy'] = policy_projection(value['case_policy'])
    value['node_policy'] = policy_projection(value['node_policy'])
    value['read_set'] = sorted(value['read_set'], key=lambda item:item['slot'])
    value['active_dimensions'] = sorted(value['active_dimensions'])
    return {'context':value, 'runtime_identity':_data(runtime_identity),
            'transit_model_version':'DATION_TRANSIT_V1', 'upstream':_data(upstream)}


def input_context_hash(context, runtime_identity, upstream=None):
    return _hash('INPUT_CONTEXT', input_context_projection(context, runtime_identity, upstream))


def core_projection(core):
    value = _data(core)
    engine = dict(value['engine'])
    engine.pop('result_generated_at', None)
    decision = {key:value['decision'][key] for key in ('node_id', 'decision_type')}
    transport = value.get('transport_plan')
    if transport is not None:
        transport = dict(transport)
        transport['trips'] = sorted((dict(trip, orders=sorted(trip['orders'], key=lambda a:a['order_id']),
            reason_codes=sorted(trip['reason_codes'])) for trip in transport['trips']), key=lambda trip:trip['trip_id'])
        transport['unassigned_demand'] = sorted(transport['unassigned_demand'], key=lambda order:order['order_id'])
    schedule = value.get('schedule')
    if schedule is not None:
        schedule = dict(schedule, trips=sorted(schedule['trips'], key=lambda trip:trip['trip_id']))
    metrics = dict(value['metrics'])
    if 'coverage_by_priority' in metrics:
        metrics['coverage_by_priority'] = sorted(metrics['coverage_by_priority'], key=lambda item:item['priority'])
    return {'contract_version':value['contract_version'], 'result_schema':value['result_schema'],
        'result_schema_version':value['result_schema_version'], 'input_context_hash':value['input_context_hash'],
        'decision':decision, 'engine':engine, 'feasibility':value['feasibility'], 'metrics':metrics,
        'transport_plan':transport, 'schedule':schedule, 'source_transport_plan':value.get('source_transport_plan')}


def core_result_fingerprint(core):
    return _hash('CORE_RESULT', core_projection(core))


def artifact_bytes(payload):
    """Artifacts may bind to past upstream/core, never to their future package."""
    value = _data(payload)
    def check(item, path=()):
        item = _data(item)
        if isinstance(item, Mapping):
            for key, child in item.items():
                if key in ('signed_url', 'signed_urls', 'current_permissions', 'approval_allowed', 'approval_overlay'):
                    raise ValueError("Mutable delivery/permission data cannot enter an artifact")
                if key == 'result_fingerprint' and (not path or path[-1] != 'source_transport_plan'):
                    raise ValueError("Artifact cannot contain its future package result fingerprint")
                check(child, (*path, key))
        elif isinstance(item, (tuple, list)):
            for child in item:
                check(child, path)
    check(value)
    return canonical_bytes(value)


def package_projection(package):
    value = _data(package)
    # Response delivery/current authorization are deliberately separate from the
    # immutable publication; callers can hash a typed response without overlay.
    if isinstance(value, Mapping) and 'package' in value:
        value = value['package']
    value = dict(value)
    if any(key in value for key in ('signed_url', 'signed_urls', 'current_permissions', 'approval_allowed', 'approval_overlay')):
        raise ValueError("Hash the immutable package, not an untyped overlay")
    def immutable_fields(item):
        item = _data(item)
        if isinstance(item, Mapping):
            for key, child in item.items():
                if key in ('signed_url','signed_urls','current_permissions','approval_allowed','approval_overlay'):
                    raise ValueError("Mutable authorization/delivery fields cannot be nested in an immutable package")
                immutable_fields(child)
        elif isinstance(item,(list,tuple)):
            for child in item:
                immutable_fields(child)
    immutable_fields(value)
    fingerprints = dict(value['fingerprints'])
    fingerprints.pop('result_fingerprint', None)
    value['fingerprints'] = fingerprints
    manifest = dict(value['artifact_manifest'])
    manifest['artifacts'] = sorted(manifest['artifacts'], key=lambda item:(item['kind'], item['part_key'], str(item['artifact_id'])))
    value['artifact_manifest'] = manifest
    return value


def result_fingerprint(package):
    # Publication identity includes immutable Run/context labels/clock. The two
    # mathematical hashes above explicitly exclude display and execution clock.
    return _hash('RESULT_PACKAGE', package_projection(package))


def decision_context_hash(context):
    value = dict(_data(context))
    value.pop('context_hash', None)
    value['selected_alternative_ids'] = sorted(value.get('selected_alternative_ids', ()))
    return _hash('DECISION_CONTEXT', value)


def intent_hash_v2(intent):
    value = dict(_data(intent))
    value['question'] = unicodedata.normalize('NFC', value['question']).strip()
    if not value['question']:
        raise ValueError("Question cannot be whitespace only")
    value['selected_alternative_ids'] = sorted(value.get('selected_alternative_ids', ()))
    value['evidence_hashes'] = sorted(value['evidence_hashes'])
    return _hash('DECISION_INTENT_V2', value)
