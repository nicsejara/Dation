"""Read-only deterministic KPI over certified D1 facts, never an approval writer."""
from decimal import Decimal, localcontext
from app.results.canonical import canonical_tree, canonical_bytes, content_sha256, core_result_fingerprint


def evaluate_acceptance(output, *, expected_case_id=None, expected_run_id=None,
                        expected_pack_id=None, expected_model_version_id=None,
                        expected_definition_id=None):
    core, evidence = output.core, output.evidence
    context = core.context
    binding = context.decision_definition
    if binding is None:
        return {'status': 'NOT_CONFIGURED', 'reason': 'Configuración histórica sin criterio J1.02.'}
    base = dict(algorithm_version='J102_COVERAGE_V1', metric='TOTAL_DEMAND_COVERAGE',
        case_id=str(context.case_id), run_id=str(core.decision.run_id),
        definition_revision_id=str(binding.definition_revision_id), definition_hash=binding.definition_hash,
        pack_version_id=str(context.data_pack_version_id), model_version_id=str(context.logistics_model_version_id),
        contract_hash=context.contract_hash, basis='CANONICAL_MODEL_PRIMARY_DIMENSION',
        unit=context.primary_dimension.value, threshold=canonical_tree(binding.acceptance_policy.threshold),
        comparator='GTE', human_approval='SEPARATE_WORKFLOW', evaluated_at=core.engine.result_generated_at.isoformat(),
        core_result_fingerprint=core_result_fingerprint(core))
    def unavailable(reason):
        return {**base, 'status': 'NOT_EVALUABLE', 'reason': reason,
                'numerator': None, 'denominator': None, 'ratio': None}
    for expected, actual in [(expected_case_id, context.case_id), (expected_run_id, core.decision.run_id),
            (expected_pack_id, context.data_pack_version_id), (expected_model_version_id, context.logistics_model_version_id),
            (expected_definition_id, binding.definition_revision_id)]:
        if expected is not None and str(expected) != str(actual):
            return unavailable('La evidencia no pertenece al Case, corrida o versión solicitada.')
    if core.result_schema != 'transport_plan_v1':
        return unavailable('D2 consulta el resultado de D1; no recalcula su cobertura.')
    if core.engine.solver_status not in ('OPTIMAL', 'FEASIBLE') or not core.feasibility.solution_found or core.feasibility.hard_constraints_satisfied is not True:
        return unavailable('No existe una solución D1 admisible y certificada.')
    if evidence.core_result_fingerprint != base['core_result_fingerprint']:
        return unavailable('El certificado no coincide con el resultado.')
    proof = next((c for c in evidence.constraints if c.code == 'POLICY_CERTIFICATE'), None)
    if (proof is None or proof.status != 'SATISFIED' or proof.facts.get('candidate_set_complete') is not True
            or not any(k.endswith('_status') for k in proof.facts)
            or any(v != 'OPTIMAL' for k, v in proof.facts.items() if k.endswith('_status'))):
        return unavailable('La búsqueda quedó incompleta o no terminó su certificación.')
    metric = core.metrics.demand_coverage
    if metric.primary_dimension != context.primary_dimension:
        return unavailable('No existe una unidad canónica común verificable.')
    rows = [e for e in evidence.entities if e.entity_type == 'ORDER']
    if not rows or len({e.entity_id for e in rows}) != len(rows):
        return unavailable('Falta evidencia única de las órdenes canónicas.')
    dim = context.primary_dimension.value
    try:
        with localcontext() as arithmetic:
            arithmetic.prec = 60
            requested = sum((Decimal(str(r.facts['requested_' + dim])) for r in rows), Decimal(0))
            assigned = sum((Decimal(str(r.facts['assigned_' + dim])) for r in rows), Decimal(0))
            if requested <= 0 or not 0 <= assigned <= requested or (requested, assigned) != (metric.requested, metric.assigned):
                return unavailable('La base de cobertura es cero, incompleta o inconsistente.')
            critical = [r for r in rows if r.facts['priority'] == 'HIGH']
            cd = sum((Decimal(str(r.facts['requested_' + dim])) for r in critical), Decimal(0))
            cn = sum((Decimal(str(r.facts['assigned_' + dim])) for r in critical), Decimal(0))
            guard = next(g for g in context.case_policy.guardrails if g.kind == 'CRITICAL_DEMAND_COVERAGE')
            critical_status = 'NOT_APPLICABLE' if cd == 0 else 'MEETS' if cn >= guard.limit * cd else 'MISSES'
            result = {**base, 'status': 'MEETS' if assigned >= binding.acceptance_policy.threshold * requested else 'MISSES',
                'reason': None, 'numerator': canonical_tree(assigned), 'denominator': canonical_tree(requested),
                'ratio': canonical_tree((assigned / requested).quantize(Decimal('.000001'))),
                'critical_coverage': {'status': critical_status, 'numerator': canonical_tree(cn), 'denominator': canonical_tree(cd),
                    'threshold': canonical_tree(guard.limit), 'priority': 'HIGH', 'unit': dim}}
    except (KeyError, ValueError, ArithmeticError, StopIteration):
        return unavailable('Faltan cantidades, prioridad o política verificables.')
    result['evidence_hash'] = content_sha256(canonical_bytes(result))
    return result
