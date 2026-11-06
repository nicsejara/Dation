# Saga 02 — baseline y seguridad de release

## G0: BASELINE_IDENTIFIED

Repositorio `nicsejara/Dation`. `main`, `origin/main` y HEAD se verificaron en
`92656a1c8c94ae1181a18c47ddd681eaa313f92b`, con árbol limpio antes de crear
`feat/saga02-zero-idle-runtime`. Se ejecutó `git fetch origin main`.
PR #103 está integrado mediante `fbc2a9986aefebcfd2784ea00207bfb65f6abad8`;
PR #104 mediante el SHA del baseline. No se reabren esas implementaciones.

| Evidencia | Resultado verificado |
|---|---|
| Candidato anterior `d739e3d7`, Actions 42128924743 | GREEN, 1.433 pruebas |
| Push a main, Actions 42136495890/job 127625868972 | RED: un fallo browser del hero C1 |
| Browser del push a main | 298 ejecutados; falla la lista `small` vacía frente a los tres textos esperados |
| Etapas posteriores de ese push | SQL/E2E omitidos; no se presentan como PASS |
| Clasificación inicial del incidente | `KNOWN_BASELINE_CI_ISSUE`, causa aún no demostrada |
| Cloud Build después de main | Check automático observado en GitHub; no demuestra trigger desactivado |
| GET de Cloud Run API/worker y triggers regional/global de Dation | HTTP 401, `UNVERIFIED_LIVE` |
| Billing | OFF por mandato del propietario; estado live `UNVERIFIED_LIVE` |

La política de red no incluye `cloudbilling.googleapis.com`; no se intenta
sortearla ni se usa otra identidad para buscar acceso. Las lecturas GCP se
limitaron a `dation-510100`, región `us-west1` y trigger global del mismo
proyecto. No se consultaron otros proyectos ni se modificaron recursos.

## Freeze económico y gate de integración

- Sin habilitación de Billing, Cloud Build manual, publicación de imágenes,
  despliegue/ejecución GCP, cambios de IAM/servicios ni SQL/Storage productivo.
- Docker, PostgreSQL, API, worker y transportes falsos son locales/efímeros.
- Ningún merge mientras no se demuestre `SAFE_TO_MERGE_WITH_BILLING_OFF`.
- Billing OFF no cuenta como protección suficiente del trigger externo.
- Estado actual del gate CD: **MERGE_BLOCKED_DEPLOY_TRIGGER**. Se continúa
  diseño, implementación y validación en la rama, sin operaciones productivas.
- El fallo de UI previo se diagnostica focalmente y, si necesita corrección,
  se mantiene en hotfix independiente. Nunca se debilita el gate completo.

## Secuencia de gates

G0 baseline → inventario focal/mediciones → ADR A/B/C con evidencia → runtime
durable y manifests seguros → contratos/SQL/E2E focales → candidato estable →
una CI completa → revisión de CD. Un gate live pendiente no se simula como PASS.
El informe de validación y el PR registrarán los SHA y resultados finales.
