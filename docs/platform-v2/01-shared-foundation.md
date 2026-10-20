# V2 · Fase 1 · Shared Foundation

Base revisada: `9f9a5585c4c1478bf7842f3309a569f900f6447a`. Fuentes: MASTER_PLAN_DATION_V2 y sus cuatro especificaciones, reconciliadas en la Fase 0 del mismo chat. Esta saga contiene Fases 0–7. El trabajo anterior de Platform MVP Fase 12 quedó preservado localmente en la rama `platform/phase12-hardening`, commit `6b1781c`; no está incluido ni se presenta como publicado en esta entrega.

## Alcance y decisiones

Se implementan contratos compartidos, sin rediseñar Home, Decision Center o Data Hub. Se conserva el plan Free, los motores, la configuración ejecutada, evidencia, invitaciones, archivos, aprobaciones e historial. No se crea D3 ni otro DDA operativo.

- Registro común `backend/app/static/contracts/foundation-v2.json`: catálogo/categorías existentes, metadata de decisiones, objetivos/aliases de presentación, tipos de dataset, responsabilidades, grupos elegibles, tonos y reglas de destino. Python y navegador consumen el mismo archivo. Se sirve como JSON público sin secretos y con revalidación; el navegador utiliza importación JSON nativa. No hay dependencia nueva.
- `foundation.py` y `platform/foundation.mjs` adaptan metadata/contexto. El DTO aditivo `context` del Case contiene `caseId`, `friendlyId`, `label`, `dda`, `status`, `currentNode` y `progress`. No añade un store ni persiste otra copia del estado.
- `resolveNodeDestination` y su adaptador Python consumen las mismas reglas y vectores de contrato. Precedencia: aprobación vigente → candidata/ejecución identificada → configuración disponible. Locked/needs_data/coming soon y motores no implementados no navegan. Stale nunca se certifica como aprobado. La candidata y el histórico conservan acceso explícito mediante su run ID; no se eliminan ni se cambian resultados.
- Consumidores reales: destino de Center, apertura desde Map/workspace y rail compartido de dashboards. `openCaseInDecisionCenter(caseId)` y `openDashboard(caseId,nodeId,runId)` delegan al router existente. `openCase` conserva acceso al mapa; el selector de casos actual mantiene su owner. `aria-current` y metadata de tono separan selección y estado sin modificar el layout.
- Los labels actuales se conservan. Los aliases `cost_min`/`co2_min` sólo corrigen presentación hacia los IDs reales `min_cost`/`min_co2`; no reescriben configuraciones guardadas.

## Responsabilidades múltiples y compatibilidad

Access Role sigue definiendo permisos. Una persona puede tener varias responsabilidades de negocio. La tabla privada normalizada `member_responsibilities` es la fuente canónica para elegibilidad; `workspace_members.business_role` queda como proyección de compatibilidad de un único valor.

La migración copia responsabilidades existentes sin actualizar filas de membresía. Una escritura legacy que cambia `business_role` reemplaza el conjunto canónico por ese valor (o vacío); una actualización que conserva ese valor preserva las responsabilidades adicionales. La API nueva modifica el conjunto atómicamente y mantiene la proyección. No hay dos listas de roles que se consulten alternativamente para autorizar.

Asignar sigue siendo una operación Admin. Los candidatos requieren workspace correcto, membresía activa, email confirmado, Access Role Admin/Operator y responsabilidad correspondiente. Una responsabilidad de negocio nunca concede permisos técnicos a Viewer.

Data utiliza `workflow_stage_assignments`, separada de los nodos decisionales. Owner/Approver de decisiones siguen usando la tabla `decision_assignments`; no se duplican en JSON o en la nueva tabla de etapas. Los históricos sin asignación continúan cargando. Las APIs nuevas informan elegibilidad actual de asignaciones retenidas cuando una persona pierde su rol, se deshabilita o pasa a Viewer.

**Los gates obligatorios todavía no se activan.** Se integrarán en Fase 5, con política persistente explícita para casos nuevos y compatibilidad legacy. La ruta legacy de asignación conserva su política actual durante esta transición; la nueva ruta de responsabilidades sí exige elegibilidad. No inferir cumplimiento de los futuros gates por la mera presencia de un assignment.

## APIs

| Operación | Contrato |
|---|---|
| `GET /api/platform/team` | Conserva respuesta, añade `business_roles` por miembro |
| `GET /api/platform/team?candidates=true&responsibility=data` | Candidatos Data Owner o Data Steward |
| `...responsibility=decision_owner` / `approver` | Grupo exacto, filtrado antes de paginar/contar |
| `PATCH /api/platform/team/members/{id}/responsibilities` | `business_roles` y `expected_updated_at`; Admin, CAS y valores distintos |
| `GET /api/platform/decisions/{id}/responsibilities` | Snapshot de Data/D1/D2, personas, elegibilidad, versiones, `can_assign`, `gates_enforced=false` |
| `PUT /api/platform/decisions/{id}/responsibilities/{stage}` | `expected_updated_at`, `owner_user_id`, `approver_user_id`; Admin y validación backend |

Etapas aceptadas: `data_preparation`, `logistics_assignment`, `logistics_scheduling`. Data no acepta aprobador. Las lecturas no crean filas ni audit events. Las escrituras idénticas conservan versión y no duplican eventos; las versiones obsoletas devuelven 409. No se aceptan actor/workspace desde el payload.

## SQL y seguridad

Migración aditiva `20261020010000_platform_v2_foundation.sql`, transaccional y con límites de bloqueo/ejecución. Crea dos tablas privadas, tres helpers privados, tres RPC públicos de servicio y un trigger de compatibilidad. No toca datos de negocio existentes ni backfillea responsables/actores.

Ambas tablas privadas tienen RLS forzado y carecen de privilegios directos para anon, authenticated y service_role. Los RPC sólo admiten service_role y vuelven a validar identidad/tenant/rol. El owner de despliegue debe poder aplicar la política de RLS forzado; comprobarlo antes de DDL. No repetir la migración si una respuesta de administración deja su resultado incierto: inspeccionar primero.

Asignaciones revalidan elegibilidad bajo el mismo lock de workspace que las mutaciones de equipo. Se conserva CAS y la identidad del actor desde el contexto verificado. Los eventos de responsabilidad incluyen etapa/nodo, persona anterior, persona nueva y actor. La proyección de actividad amplía sólo su allowlist de UUID/etapa; no expone cuerpos, credenciales ni perfiles completos. Aprobador asignado y `approved_by_user_id` continúan siendo verdades distintas, incluido override Admin.

Rollback: una imagen tenant-aware anterior tolera tablas/RPC nuevos y usa el campo de compatibilidad. Conservar DDL aditivo para no perder responsabilidades nuevas; no borrar tablas como rollback. No regresar a una imagen anterior a Auth/tenancy.

## Validación y siguiente fase

Los vectores compartidos cubren precedencia, reemplazo, stale, ausencia de corrida, bloqueo y D3. E2E con PostgreSQL/PostgREST/API/worker reales cubren backfill sin alterar membresías, múltiples responsabilidades, CAS, paginación, aislamiento, permisos, RLS/ACL, asignaciones de etapas, lectura pura, auditoría, actor real y acceso explícito a candidatas. Chromium comprueba que el rail abre la aprobación oficial y conserva selección/estado. Se exige regresión completa y CI de head/main antes de publicar.

El commit, PR, CI y revisiones exactas se registran en el PR y en `/workspace/dation-audit/platform-v2-phase1/ENTREGA.md`. La evidencia de runtime no se infiere de esta documentación. Después del cierre corresponde Fase 2: Decision Center V2. No se inicia automáticamente.

La regresión detectó contención preexistente entre cargas demo simultáneas: el journal podía quedar pendiente porque una transición recibía `55006` y se omitía. Las transiciones idempotentes de finalización/compensación reintentan de forma acotada sólo el 409 marcado `X-Dation-Retryable`; no se reintentan creación de intents, archivos, permisos ni resultados de red inciertos. Se mantienen los locks SQL, la recuperación explícita y la procedencia del archivo original. Pruebas con contención inyectada reproducen ambos fallos antes de la corrección y verifican finalización sin recargar/eliminar datos válidos.
