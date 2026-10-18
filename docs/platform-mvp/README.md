# Dation Platform MVP v1

Fase 0 auditada y Fase 1 implementada. Fecha de referencia del usuario: 2026-10-17, `America/Buenos_Aires`. El catálogo conserva su timestamp UTC de captura. Base funcional auditada: `22f1187451429c8e98dfcb9874f89b974500cb35` (`main`, PR #72). Fase 0: commit `2f82015`, PR #73 integrada con CI verde. No se implementan fases futuras.

La [Fase 1](09-phase1-foundation.md) añade foundation visual optativa y un primer consumidor en el panel técnico de Configuración. Contratos y ejemplos: [Design System Platform](DESIGN_SYSTEM.md). El resto de este índice conserva la evidencia histórica de Fase 0.

## Resultado

Logistics sigue funcional. Se preservan motores, configuración, dashboards, aprobaciones, lineage, IA, exports y datos. La entrega de Fase 0 sólo añadió documentación, un snapshot de metadata y dos helpers de auditoría/QA; no cambió app, dependencias, workflow, SQL productivo, Storage ni Auth y no desplegó una revisión nueva durante aquella ejecución. Fase 1 cambia únicamente presentación e interacción compartida de frontend, con scope y regresión verificados.

El producto actual es un workspace privado con Basic compartido. No está preparado todavía para aislar empresas: falta identidad, membresías y autorización explícita en API/servicios/RPC. El roadmap conserva esa funcionalidad y añade la frontera SaaS durante Fase 2, después de la foundation visual de Fase 1.

## Documentos y trazabilidad del pedido

| Requisito de Fase 0 | Evidencia entregada |
|---|---|
| Backend/servicios, entrypoint, middleware, rutas, side effects | [00 · Arquitectura actual](00-architecture-audit.md), [inventario de las 42 operaciones API](api-inventory.md) |
| Arquitectura objetivo y encapsulación | [01 · Arquitectura objetivo](01-target-architecture.md) |
| Datos existentes, backfill, lineage, constraints y rollback | [02 · Plan de migración](02-data-migration-plan.md) |
| API authorization, identidad, roles, RLS y service role | [03 · Modelo de seguridad](03-security-model.md) |
| Tokens/primitives/components/legacy/overrides; Fase 1 exacta | [04 · Design system](04-design-system.md) |
| Tests, CI, deploy y matriz del flujo Logistics | [05 · Baseline y CI](05-baseline-and-ci.md) |
| Frontend, navegación, estado, lifecycle y shell futuro | [06 · Auditoría de shell](06-frontend-shell-audit.md) |
| Esquema real completo, permisos, Storage y conteos | [07 · Supabase/Storage](07-supabase-storage-audit.md), [índice DDL](schema/README.md), [snapshot](schema/live-catalog.json) |
| Riesgos, secuencia y gates de las 13 fases | [08 · Riesgos y gates](08-risk-register-and-phase-gates.md) |
| Phase/status/commit/date/tests/issues/next gate | [Estado durable](IMPLEMENTATION_STATUS.md) |

## Verificación

Pasaron 350 unittest Python, 13 funciones Python adicionales, 77 tests Node, 46 SQL, 10 E2E reales y 6 browser IA, más el helper de persistencia/restauración IA con proveedor HTTP local. Cero cambios de negocio en producción. El catálogo público reconstruido coincide con el real: 12 tablas y 33 funciones, sin diferencias normalizadas. La CI verde del SHA base se identifica separadamente de cualquier CI posterior de esta documentación.

Comandos y límites de la evidencia: [baseline](05-baseline-and-ci.md), [resultados estructurados](baseline-results.json). No se probó un LLM comercial ni el Golden Pallets v2 externo ausente. Aislamiento A/B es un gate de Fase 2, no una propiedad ya existente.

Helpers durables:

- [`scripts/audit_platform_schema.py`](../../scripts/audit_platform_schema.py): captura metadata y agregados de Supabase en transacciones de lectura; no migra ni devuelve filas de negocio.
- [`scripts/qa/platform_baseline_ai.py`](../../scripts/qa/platform_baseline_ai.py): sandbox propio PostgreSQL/PostgREST/Storage/API/worker con proveedor IA loopback; comprueba persistencia y replay tras reiniciar API.

## Foundation y próxima fase

Fase 1 implementa tokens/primitives y componentes visuales, con estados, accesibilidad y responsive, preservando catálogo y D1/D2. Detalle: [09](09-phase1-foundation.md). No incluye Auth, nuevas tablas, sidebar, Home, Data Hub ni Decision Center.

Siguiente fase: **Fase 2**, Auth + identidad + workspace + tenancy. Se detiene la ejecución al cerrar Fase 1 y se espera una nueva instrucción del usuario.
