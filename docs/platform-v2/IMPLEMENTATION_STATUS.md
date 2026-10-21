# Dation V2 · Estado de implementación

Fuentes: MASTER_PLAN_DATION_V2.md, CAMBIOS_HOME.md, CAMBIOS_DESICION_CENTER.md (nombre del archivo recibido), CAMBIOS_DATA_HUB.md y CAMBIOS_TRANSVERSALES.md. Esta saga comprende ocho fases (0–7), separadas del roadmap Platform MVP anterior.

| Fase | Estado | Alcance |
|---:|---|---|
| 0 | Completada | Context reconciliation + delta audit sobre main `9f9a558`; CI verde y 24 contratos Node aprobados |
| 1 | Implementada; evidencia de publicación en [PR #86](https://github.com/nicsejara/Dation/pull/86) | [Shared Foundation](01-shared-foundation.md): navegación, metadata, contexto y responsabilidades múltiples compatibles |
| 2 | Implementada | [Decision Center V2](02-decision-center.md): portfolio global, drawer contextual, responsabilidades y navegación exacta |
| 3 | Implementada | [Data Hub V2](03-data-hub.md): biblioteca de datasets, resumen global, drawer, trazabilidad y gobierno |
| 4 | Implementada | [Home V2](04-home.md): hero, atención, reanudación canónica, accesos y actividad sin onboarding global |
| 5 | Implementada | [Integración transversal](05-transversal-integration.md): selectores/gates por caso, switcher, handoff y Team/Auth |
| 6 | Implementada | [Golden E2E + regresión](06-golden-regression.md): actores distintos, matrices compartidas, aislamiento y restauración de foco tras reload |
| 7 | Pendiente | Release audit |

Decisiones conservadas: Free universal, autoridad tenant-aware, datos/evidencia existentes, motores D1/D2 y permisos técnicos. Decisiones V2: aprobación vigente tiene prioridad al navegar; Data no es un nodo decisional; una persona puede reunir responsabilidades de negocio; Admin conserva asignación. Los gates de Fase 5 son obligatorios para casos nuevos cuando se activa el switch privado después de publicar la aplicación compatible; no invalidan históricos sin responsables.

El benchmark `docs/platform-home-v2-benchmark.md` es anterior al objetivo actual. Home V2 (Fase 4) retira el onboarding y la demo globales; conserva los consumidores de progreso/demo dentro de cada DDA.
