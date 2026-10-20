# Dation V2 · Estado de implementación

Fuentes: MASTER_PLAN_DATION_V2.md, CAMBIOS_HOME.md, CAMBIOS_DESICION_CENTER.md (nombre del archivo recibido), CAMBIOS_DATA_HUB.md y CAMBIOS_TRANSVERSALES.md. Esta saga comprende ocho fases (0–7), separadas del roadmap Platform MVP anterior.

| Fase | Estado | Alcance |
|---:|---|---|
| 0 | Completada | Context reconciliation + delta audit sobre main `9f9a558`; CI verde y 24 contratos Node aprobados |
| 1 | Implementada; cierre de publicación en PR | [Shared Foundation](01-shared-foundation.md): navegación, metadata, contexto y responsabilidades múltiples compatibles |
| 2 | Pendiente | Decision Center V2 |
| 3 | Pendiente | Data Hub V2 |
| 4 | Pendiente | Home V2 |
| 5 | Pendiente | Integración transversal, selectores/gates, switcher, handoff y Team/Auth |
| 6 | Pendiente | Golden E2E + regresión |
| 7 | Pendiente | Release audit |

Decisiones conservadas: Free universal, autoridad tenant-aware, datos/evidencia existentes, motores D1/D2 y permisos técnicos. Decisiones V2: aprobación vigente tiene prioridad al navegar; Data no es un nodo decisional; una persona puede reunir responsabilidades de negocio; Admin conserva asignación. Los gates obligatorios se reservan a Fase 5 y no invalidarán históricos sin responsables.

El benchmark `docs/platform-home-v2-benchmark.md` es anterior al nuevo objetivo: la futura Home retirará onboarding global según los adjuntos actuales. No se cambia Home en esta fase.
