# G6 — Evidencia y pilotos

## Estado inicial

- Inicio real de implementación: **2026-11-13 21:49:19 UTC / 18:49:19 ART**.
- Baseline: `baefc6788b11a1aa9f5e02a21c60d033860e1342`, main posterior a PR113.
- Rama: `feat/g6-ux-autopilot`. Riesgo **R4** por workflows/identidad/release.
- No hay cambio de producto, motor, datos ni runtime API en este PR.
- GCP read HTTP401 ACCESS_TOKEN_TYPE_UNSUPPORTED; live no verificado.
- Main sin protección verificado en GitHub. Bootstrap/auto variables no activados.

## Validación de implementación

La suite focal cubre R1/R2 de Git real y merge-base, rechazo R3/R4/desconocido/mixto,
fork/head no fusionado, assertions preservadas, CI roja/pendiente/otra SHA, último
gate, kill switch, policy hash, WIF, dispatch único, recibo faltante/conflictivo,
artefactos/redirect sin credenciales, OCI real frente a marcador viejo, drift
IAM/config/CAS, dos merges, interrupción antes/después de prepare/promoción,
smoke503, limpieza de tag, rollback seguro y negativa ante despliegue ajeno.
También simula el bootstrap exacto e idempotente, preservando otros miembros IAM.
Todas son simulaciones sin llamadas GCP ni credenciales reales.

Resultados locales y runs FAST/FULL del candidato se registran en el PR. La
medición hasta CI verde se completa con timestamps reales de Actions; no confundir
la duración de un test local con la latencia completa de implementación y CI.

## Pilotos productivos pendientes

| Gate | Estado y evidencia necesaria |
| --- | --- |
| G6.0 diseño focal | Completado con evidencia GitHub y limitación GCP401 |
| G6.1 implementación R4 | Preparada; control del candidato/CI en el PR |
| G6.2 seguridad/simulación | Pruebas locales; FAST+FULL obligatorios del PR |
| G6.3 bootstrap | **NO AUTORIZADO / NO APLICADO**; ver plan exacto |
| Preflight OIDC real de lectura | Pendiente tras GO; no simulado como PASS |
| G6.4 piloto R1 | Pendiente cambio CSS inocuo específicamente aprobado |
| G6.4 piloto R2 | Pendiente interacción Core/Graph específicamente aprobada y E2E |
| Validación visual | Pendiente propietario, para ambos pilotos |

Cada piloto debe registrar inicio/FAST/main CI/publish/prepare/health/promote/
post-health, PR, SHA, digest, revisión, anterior READY, tráfico100, URL y aceptación
visual. No se ejecutan pilotos productivos con esta autorización. No usar el antiguo
Piloto01 como prueba del pipeline G6: fue otro mecanismo.

**Resultado honesto actual:** código G6 preparado con activación cerrada;
`DATION_G6_UX_AUTOPILOT_READY` sigue pendiente de bootstrap + pilotos reales.
