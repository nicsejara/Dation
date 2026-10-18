# Estado de implementación · Platform MVP v1

Fecha de referencia: 2026-10-17 (`America/Buenos_Aires`). Fuente de requisitos: `PROMPT_MAESTRO_SUPER_PRO_Dation_Platform_MVP_v1.md` adjunto por el usuario. El roadmap contiene Fases 0–12; este registro pertenece a esa saga, no a las anteriores sagas UX/D1/D2.

## Fase actual

| Campo | Valor |
|---|---|
| Phase | 1 · Identidad visual + Design System Platform Foundation |
| Status | Implementada y validada localmente: foundation optativa, componentes accesibles, consumidor Settings y regresiones DDA. Fase 2 no iniciada. |
| Commit | Fase 0 `2f82015c1477fb0c8f247c94b18637ccc19a6c71`, integrada en `ebe82937960fdd9198417459f0e1fb807450f843`. Entrega actual: consultar `git log -1 --format=%H -- docs/platform-mvp/IMPLEMENTATION_STATUS.md`; no se inventa un SHA propio dentro del commit. |
| Date | 2026-10-17, America/Buenos_Aires; timestamp UTC de captura en el snapshot |
| Tests | Fase 1: 350 unittest + 13 funciones Python; 59 Node focalizados; 7 Chromium foundation + 1 Settings + 16 regresiones. 45 estados antes/después y 310 elementos DDA/catalog comparados sin diferencias. Comandos y límites en [09](09-phase1-foundation.md). Workflow habitual preservado; CI del commit actual en su PR/checks. |
| Known issues | No tenancy/usuarios de producto aún; Auth con redirect a localhost y correo por validar; 13 funciones Python fuera de discover CI; Golden externo ausente; LLM real no probado; GCP admin GET 401 y worker host bloqueado por proxy. Detalle y gates en [08](08-risk-register-and-phase-gates.md). |
| Next gate | Instrucción para Fase 2: JWT, membership, workspace, migración no destructiva, autorización API/RPC/Storage y aislamiento A/B. No comenzar automáticamente. |

## Evidencia y límites

El catálogo real y la base reconstruida concuerdan: 12 tablas, 33 funciones, ninguna policy pública, RLS habilitado, sin columnas workspace. Conteos de integridad sin huérfanos ni lineage roto en la captura. Snapshot y checksums en [schema](schema/README.md).

La CI de `main` [39050288728](https://github.com/nicsejara/Dation/actions/runs/39050288728) pasó sobre el **SHA base**, incluida la etapa de 146 pruebas browser. No se atribuye esa ejecución al commit nuevo de documentación. Las verificaciones locales enumeradas se ejecutaron durante esta Fase 0; el helper IA versionado también fue ejecutado exitosamente. Ver [comandos y resultados](05-baseline-and-ci.md).

Fase 0 no modificó código productivo, migrations, dependencias, workflow, secrets, registros, objetos Storage o configuración Auth. Su [PR #73](https://github.com/nicsejara/Dation/pull/73) terminó CI verde antes de integrarse como base de Fase 1. Fase 1 modifica sólo frontend y tests/documentación; datos/motores/API/Auth permanecen sin cambios. Seguridad por usuario/empresa queda por implementar y probar en Fase 2.

## Roadmap

| Phase | Status | Gate |
|---:|---|---|
| 0 | Completada | Auditoría y baseline entregados |
| 1 | Implementada y validada | Foundation optativa, interacción/QA y consumidor real; [detalle](09-phase1-foundation.md) |
| 2 | Pendiente | Auth + identity + workspace + tenancy/security A/B |
| 3 | Pendiente | Platform shell + navegación/routing |
| 4 | Pendiente | Workspace Home real |
| 5 | Pendiente | Catálogo + entitlements |
| 6 | Pendiente | Data Hub |
| 7 | Pendiente | Decision Center |
| 8 | Pendiente | Equipo + colaboración + atribución |
| 9 | Pendiente | Settings + plan manual |
| 10 | Pendiente | Audit trail + actividad |
| 11 | Pendiente | Onboarding/demo/estados |
| 12 | Pendiente | Hardening + seguridad + E2E + release comercial |

Cada fase deberá registrar su commit, fecha, pruebas, riesgos y siguiente gate. No anticipar funciones ni resetear datos actuales.
