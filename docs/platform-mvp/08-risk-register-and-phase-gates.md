# Riesgos, secuencia y gates

Estado: auditoría Fase 0. Los riesgos de capacidades futuras no se presentan como regresiones introducidas por esta entrega.

| ID | Riesgo observado / evidencia | Prioridad y tratamiento | Gate |
|---|---|---|---|
| R01 | Basic compartido; sin usuarios ni workspace en rutas/servicios/tablas | Bloqueante para múltiples empresas. JWT + membership + ownership end-to-end; Basic fuera del flujo de producto. | 2 |
| R02 | Service role bypassa RLS; 33 funciones históricas sin contexto tenant | Backend + SQL deben validar todas las referencias; no abrir grants a clientes sobre RPC legacy. | 2 |
| R03 | Dedup por hash/tipo y default Fleet globales | Rehacer filtros e índices por workspace; CSV idéntico A/B sin mezcla. | 2 |
| R04 | Tablas auxiliares IA/comparativas/jobs/outbox y snapshots globales | Incluir 11 tablas tenant, worker con contexto persistido, métricas globales internas. No limitar migración a tres tablas. | 2 |
| R05 | Actor aprobado fijo y triggers de identidad/append-only | Migrar checks/RPC de forma coordinada; preservar histórico compartido y no inventar identidad humana. | 2/8 |
| R06 | Storage legacy sin workspace y path protegido por trigger | Mantener paths históricos autorizados por fila; prefijar nuevas cargas. Plan de compensación para futuros delete/move. | 2/6 |
| R07 | `POST /api/runs/{dataset_id}` legacy síncrono sigue activo | Aplicar autorización igual o deprecar explícitamente; no dejar bypass al cerrar sólo Dispatch. | 2 |
| R08 | Navegación repartida template/workspace/app; estados y CSS diferidos permanecen | Owners claros, compatibilidad query/History, dispose/abort, limpiar identidad/caches y probar deep links. | 3 |
| R09 | CSS histórico amplio con overrides e inline styles | Foundation incremental, pruebas de D1/D2; no consolidación ciega ni cambio de framework. | 1 |
| R10 | 13 funciones Python no descubiertas por CI; sí pasaron con runner explícito | Registrar cobertura pendiente para ajuste de CI; no considerar que discover las ejecuta. Helper IA nuevo tampoco está en workflow. | Próximo cambio de CI; antes de 12 |
| R11 | Golden Pallets v2 externo ausente; LLM real no probado en esta fase | Mantener fixtures QA; obtener paquete autorizado y validar proveedor real antes del release comercial. No afirmar validación de cliente. | 12 |
| R12 | GCP GET 401 y host worker bloqueado por proxy | No hay deploy en Fase 0. Renovar acceso/alcance seguro cuando se necesite; revalidar IAM, settings y salud worker antes de publicar. | Próximo deploy / 12 |
| R13 | Rollback a API sin tenancy después de admitir clientes nuevos | Bloquear ese rollback; versión tenant-aware o mantenimiento y fix forward. Restore aislado previo. | 2/12 |
| R14 | JWKS ES256 presente; redirect a localhost, allowlist vacía y SMTP personalizado ausente; flujos Auth no probados | Configurar destinos HTTPS y validar signup/recovery/email con usuarios autorizados antes de login comercial; no inferirlo del schema ni de la presencia de JWKS. | 2 |
| R15 | DB y Storage no transaccionan juntos; compensación de upload no comprueba status | Conservar cero huérfanos como preflight; diseñar retry/intención y safe archive/delete. | 6 |
| R16 | `ensure_case` ocurre antes de admisión transaccional run/job | Una admisión rechazada puede dejar case válido sin run. Diseñar empty/error recuperable sin prometer atomicidad de todo el flujo. | 7/12 |

## Secuencia autorizada por el roadmap

| Fase | Alcance | Gate verificable antes de continuar |
|---:|---|---|
| 0 | Auditoría, esquema real, baseline y estrategia | Documentación completa, baseline Logistics verde, ningún cambio de datos/producto |
| 1 | Identidad y foundation visual | Primitives/tokens coherentes, estados/a11y/responsive, sin alterar flujos DDA |
| 2 | Auth, identidad, workspace y tenancy | A/B aislados en API/REST/RPC/Storage; roles y sesión; backfill íntegro |
| 3 | Shell y routing global | Reload/back/forward/deep-link; sin listeners duplicados ni fuga de sesión |
| 4 | Workspace Home | Atención/continuación reales o empty states; sin actividad inventada |
| 5 | Catálogo y entitlements | Logistics actual abre; futuros DDAs y accesos directos no habilitados |
| 6 | Data Hub | List/detail/reuse/archive; safe delete y Storage autorizado; Data Pack compatible |
| 7 | Decision Center | Case → decision → runs; restore directo D1/D2, historia y archive |
| 8 | Equipo, ownership y colaboración | Invite/join/roles/disabled; owner/approver persistidos; actor real y override auditado |
| 9 | Settings y plan | Cambios admin reales, unidades/timezone por workspace, plan manual sin pagos ficticios |
| 10 | Audit/activity | Eventos append-only reales por workspace/case/actor, sin secretos ni CSV en metadata |
| 11 | Onboarding/demo/estados | Demo identificada e idempotente; empty/error comprensibles |
| 12 | Hardening/release | Dos empresas/dos usuarios recuperan casos al día siguiente; cero cruce, Golden/LLM y deploy verificados |

## Propuesta exacta para Fase 1

Ejecutar sólo foundation visual indicada en [04-design-system.md](04-design-system.md): inventario de primitives faltantes y contratos de tamaño/estado; evolucionar `tokens.css`/`dation-design-system.css`; icon registry existente; patrón de page header, forms, badges, superficies, tabla y filtros reutilizables. Crear una galería de QA interna únicamente si facilita verificación, sin exponer una página nueva al cliente por obligación.

Preservar catálogo, category pills y geometría aprobada de Hero/toolbar/Contexto/KPI D1/D2. Mantener como está la navegación y el comportamiento operativo. No Auth, nuevas tablas, workspace setup, sidebar nueva, Home, Data Hub ni Decision Center en Fase 1.

Aceptación: controles con estados default/hover/active/focus/disabled/loading, labels y keyboard; contrastes y reduced motion; widths 1440/1280/1024/768/390 sin overflow; baseline D1/D2 aprobado. Prerequisito técnico ya disponible: entorno Python/Node/Docker/Chromium validado. El gate GCP de despliegue no bloquea la implementación local de primitives; sí debe resolverse antes de cualquier publicación que requiera administración.

## Cierre de Fase 0

Se entregan auditoría y plan, no una plataforma multiusuario ya construida. No hay migraciones aplicadas ni rediseño productivo. Se detiene la ejecución antes de Fase 1, como exige el documento del usuario.
