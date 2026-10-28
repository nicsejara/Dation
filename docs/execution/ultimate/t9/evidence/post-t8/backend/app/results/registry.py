"""Known schemas are not executable capabilities. Resolution never uses node-only fallback."""
from dataclasses import asdict, dataclass
from types import MappingProxyType

from .contracts import RuntimeIdentity

REGISTRY_VERSION = "DATION_RESULTS_REGISTRY_V1"


class UnsupportedResultSchema(ValueError):
    code = "UNSUPPORTED_RESULT_SCHEMA"


class UnsupportedRuntimeIdentity(ValueError):
    code = "UNSUPPORTED_RUNTIME_IDENTITY"


class RuntimeUnavailable(ValueError):
    code = "RUNTIME_UNAVAILABLE"


@dataclass(frozen=True)
class SchemaRegistration:
    name: str
    version: int
    cohort: str
    reader: str


@dataclass(frozen=True)
class RuntimeRegistration:
    engine_name: str
    engine_version: str
    runtime_profile: str | None
    result_schema: str
    result_schema_version: int
    node_id: str | None
    implemented: bool
    available: bool

    @property
    def identity(self):
        return RuntimeIdentity(**{key:getattr(self, key) for key in RuntimeIdentity.model_fields})


SCHEMAS = MappingProxyType({(item.name, item.version):item for item in (
    SchemaRegistration('assignment_v1', 1, 'LEGACY', 'LEGACY_ORIGINAL'),
    SchemaRegistration('scheduling_v1', 1, 'LEGACY', 'LEGACY_ORIGINAL'),
    SchemaRegistration('dispatch_v2', 2, 'LEGACY', 'LEGACY_ORIGINAL'),
    SchemaRegistration('transport_plan_v1', 1, 'ULTIMATE', 'DecisionResultPackageV1'),
    SchemaRegistration('day_scheduling_v1', 1, 'ULTIMATE', 'DecisionResultPackageV1'),
)})
RUNTIMES = (
    RuntimeRegistration('logistics-assignment-engine', '1.0.0', None, 'assignment_v1', 1, 'logistics_assignment', True, True),
    RuntimeRegistration('logistics-scheduling-engine', '1.0.0', None, 'scheduling_v1', 1, 'logistics_scheduling', True, True),
    RuntimeRegistration('logistics-dispatch-engine', '2.2.0', None, 'dispatch_v2', 2, None, True, True),
    RuntimeRegistration('transport_plan', '2.0.0', 'transport_plan_v1', 'transport_plan_v1', 1, 'logistics_assignment', False, False),
    RuntimeRegistration('day_scheduling', '2.0.0', 'day_scheduling_v1', 'day_scheduling_v1', 1, 'logistics_scheduling', False, False),
)


def resolve_test_core(identity):
    """Explicit inactive T6 test profile; never used by public admission.

    The production registration remains unavailable until policy/publication
    phases are complete. Matching only a node or schema is insufficient.
    """
    entry = resolve_runtime(identity)
    if entry.identity != RuntimeIdentity(engine_name='transport_plan',engine_version='2.0.0',
            runtime_profile='transport_plan_v1',result_schema='transport_plan_v1',result_schema_version=1):
        raise RuntimeUnavailable('No test Core producer for this exact identity')
    from app.engines.assignment.transport_plan import run_transport_plan
    return run_transport_plan


def resolve_test_policy(identity):
    """T7 producer remains test-only; public availability is unchanged."""
    resolve_test_core(identity)
    from app.engines.assignment.transport_policy_result import run_transport_policy
    return run_transport_policy


def resolve_schema(name, version):
    if type(version) is not int:
        raise UnsupportedResultSchema("Explicit integer result schema version required")
    try:
        return SCHEMAS[(name, version)]
    except KeyError as exc:
        raise UnsupportedResultSchema("Unsupported result schema/version") from exc


def resolve_runtime(identity: RuntimeIdentity, *, require_available=False):
    identity = RuntimeIdentity.model_validate(identity)
    resolve_schema(identity.result_schema, identity.result_schema_version)
    found = next((entry for entry in RUNTIMES if entry.identity == identity), None)
    if found is None:
        raise UnsupportedRuntimeIdentity("Persisted engine/version/profile/schema do not match a registered identity")
    if require_available and not (found.implemented and found.available):
        raise RuntimeUnavailable("Known result schema has no available runtime producer")
    return found


def resolve_persisted_runtime(row, *, require_available=False):
    # Legacy rows lack runtime_profile and integer result_schema_version. Their
    # full persisted identity is matched exactly; node_id never determines it.
    name, version, schema = row.get('engine_name'), row.get('engine_version'), row.get('schema_version')
    if not all(isinstance(v, str) and v for v in (name, version, schema)):
        raise UnsupportedRuntimeIdentity("Persisted runtime identity is incomplete")
    candidates = [entry for entry in RUNTIMES if (entry.engine_name, entry.engine_version, entry.result_schema) == (name, version, schema)]
    if len(candidates) != 1:
        raise UnsupportedRuntimeIdentity("Unknown persisted runtime; no node fallback")
    entry = candidates[0]
    if row.get('runtime_profile') != entry.runtime_profile:
        raise UnsupportedRuntimeIdentity("Persisted runtime_profile mismatch")
    pinned_version = row.get('result_schema_version')
    if (entry.runtime_profile is not None or pinned_version is not None) and (type(pinned_version) is not int or pinned_version != entry.result_schema_version):
        raise UnsupportedRuntimeIdentity("Ultimate rows pin the schema version")
    return resolve_runtime(entry.identity, require_available=require_available)


def resolve_result_header(payload, persisted=None):
    if 'result_schema' in payload:
        schema = resolve_schema(payload['result_schema'], payload.get('result_schema_version'))
        if schema.cohort != 'ULTIMATE' or ('schema_version' in payload and payload['schema_version'] != schema.name):
            raise UnsupportedResultSchema("Ambiguous legacy/Ultimate header")
    elif 'schema_version' in payload:
        name = payload['schema_version']
        candidates = [s for (key, _), s in SCHEMAS.items() if key == name and s.cohort == 'LEGACY']
        if len(candidates) != 1:
            raise UnsupportedResultSchema("Unknown legacy schema; original data is not a Dispatch result")
        schema = candidates[0]
    else:
        raise UnsupportedResultSchema("Missing result schema")
    if persisted is not None:
        runtime = resolve_persisted_runtime(persisted)
        if runtime.result_schema != schema.name or runtime.result_schema_version != schema.version:
            raise UnsupportedResultSchema("Persisted header conflicts with result body")
    return schema


def lifecycle_status(status):
    try:
        return {'queued':'QUEUED', 'running':'RUNNING', 'completed':'COMPLETED', 'error':'FAILED'}[status]
    except KeyError as exc:
        raise ValueError("Unsupported persisted Run lifecycle") from exc


API_ABI = (
    ('GET', '/api/runs/{run_id}/result', 'expected_result_fingerprint'),
    ('GET', '/api/runs/{run_id}/details/{dataset_id}', 'expected_result_fingerprint'),
    ('GET', '/api/runs/{run_id}/entities/{entity_type}/{entity_id}', 'expected_result_fingerprint'),
    ('GET', '/api/runs/{run_id}/artifacts/{artifact_id}', 'expected_result_fingerprint'),
    ('GET', '/api/runs/{run_id}/approval-review', 'expected_result_fingerprint'),
    ('POST', '/api/runs/{run_id}/decision-context', 'expected_result_fingerprint'),
    ('POST', '/api/runs/{run_id}/decision-assistant/v1', 'expected_result_fingerprint'),
)


def contract_metadata():
    """Generated declaration only. These new routes/producers are NOT installed."""
    from pydantic.json_schema import models_json_schema
    from app.domain.logistics import contracts as domain
    from app.domain.logistics.base import CANONICAL_VERSION
    from app.domain.logistics.units import QUANTITY_SCALES, Money, CurrencyPolicy
    from . import contracts as dto
    from .metrics import METRICS, METRIC_CATALOG_VERSION, MetricDescriptor
    from .reason_codes import REASON_CODES, REASON_CATALOG_VERSION, ReasonCodeDefinition
    roots = [domain.Demand, domain.TransportResource, domain.LogisticsModelVersion, domain.FrozenCaseContext,
        domain.CasePolicy, domain.NodePolicy, Money, CurrencyPolicy, MetricDescriptor, ReasonCodeDefinition,
        dto.EngineCoreResult, dto.EngineEvidence, dto.EngineOutput, dto.ResultContractBundle, dto.DecisionResultPackageV1,
        dto.DecisionContextV1, dto.DecisionIntentV2, dto.UltimateRunRequest, dto.ResultResponse,
        dto.DecisionContextResponse, dto.ApprovalReviewResponse, dto.ApprovalReview, dto.ResultArtifactReference,
        dto.DetailDatasetDescriptor, dto.AlternativeDescriptor, dto.ExceptionDescriptor, dto.AssumptionDescriptor,
        dto.FingerprintSet, dto.ArtifactReadError, dto.DetailPage[dto.DetailRow], dto.ResultError]
    references, definitions = models_json_schema([(root, 'validation') for root in roots], by_alias=True)
    return {'contract':'DATION_RESULT_CONTRACTS_V1', 'registry_version':REGISTRY_VERSION,
        'schemas':[asdict(v) for v in SCHEMAS.values()], 'runtimes':[asdict(v) for v in RUNTIMES],
        'decimal_wire_format':'FINITE_DECIMAL_STRING', 'canonical_version':CANONICAL_VERSION,
        'units':{'quantity_scales':dict(QUANTITY_SCALES), 'distance_km_scale':3, 'ratio_scale':4,
                 'rate_scale':6, 'money_scale':'context.currency_policy.minor_units', 'rounding':'ROUND_HALF_UP',
                 'scaled_integer_bound':2**63-1, 'fx':False},
        'budgets':{'package_bytes':dto.PACKAGE_MAX_BYTES, 'visual_inline_bytes':dto.VISUAL_INLINE_MAX_BYTES,
            'evidence_chunk_bytes':dto.EVIDENCE_CHUNK_MAX_BYTES, 'entities_per_chunk':dto.EVIDENCE_CHUNK_MAX_ENTITIES,
            'page_rows':dto.PAGE_MAX_ROWS, 'selected_entity_bytes':dto.SELECTED_ENTITY_MAX_BYTES},
        'reason_catalog_version':REASON_CATALOG_VERSION,
        'reason_codes':[v.model_dump(mode='json') for v in REASON_CODES.values()],
        'metric_catalog_version':METRIC_CATALOG_VERSION,
        'metrics':[v.model_dump(mode='json') for v in METRICS.values()],
        'api':[{'method':m, 'path':p, 'required_query':q, 'implemented':False} for m,p,q in API_ABI],
        '$schema':'https://json-schema.org/draft/2020-12/schema', '$defs':definitions['$defs'],
        'json_schemas':{root.__name__:references[(root, 'validation')] for root in roots}}
