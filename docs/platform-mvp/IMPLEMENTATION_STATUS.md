# Estado de implementación · Platform MVP v1

Fecha de referencia: 2026-10-17 (`America/Buenos_Aires`). Fuente de requisitos: `PROMPT_MAESTRO_SUPER_PRO_Dation_Platform_MVP_v1.md` adjunto por el usuario. El roadmap contiene Fases 0–12; este registro pertenece a esa saga, no a las anteriores sagas UX/D1/D2.

## Fase actual

| Campo | Valor |
|---|---|
| Phase | 0 · Auditoría + baseline + migration strategy |
| Status | Completada: auditoría, metadata real, baseline y diseño durable. Implementación del producto sin cambios. |
| Commit | Base auditada `22f1187451429c8e98dfcb9874f89b974500cb35`. La entrega es el commit que incorpora este registro y los helpers; obtener su SHA con `git log -1 --format=%H -- docs/platform-mvp/IMPLEMENTATION_STATUS.md`. No se escribe un SHA propio ficticio dentro de su contenido. |
| Date | 2026-10-17, America/Buenos_Aires; timestamp UTC de captura en el snapshot |
| Tests | 350 unittest + 13 funciones Python; 77 Node; 46 PostgreSQL; 10 E2E reales; 6 browser IA; helper IA de persistencia/restore. Sin fallos/omisiones. pip check, compile y sintaxis de 67 módulos JS correctos. |
| Known issues | No tenancy/usuarios de producto aún; Auth con redirect a localhost y correo por validar; 13 funciones Python fuera de discover CI; Golden externo ausente; LLM real no probado; GCP admin GET 401 y worker host bloqueado por proxy. Detalle y gates en [08](08-risk-register-and-phase-gates.md). |
| Next gate | Instrucción para Fase 1 y aceptación de foundation visual según [04](04-design-system.md); no comenzar automáticamente. |

## Evidencia y límites

El catálogo real y la base reconstruida concuerdan: 12 tablas, 33 funciones, ninguna policy pública, RLS habilitado, sin columnas workspace. Conteos de integridad sin huérfanos ni lineage roto en la captura. Snapshot y checksums en [schema](schema/README.md).

La CI de `main` [39050288728](https://github.com/nicsejara/Dation/actions/runs/39050288728) pasó sobre el **SHA base**, incluida la etapa de 146 pruebas browser. No se atribuye esa ejecución al commit nuevo de documentación. Las verificaciones locales enumeradas se ejecutaron durante esta Fase 0; el helper IA versionado también fue ejecutado exitosamente. Ver [comandos y resultados](05-baseline-and-ci.md).

No se modificaron código productivo, migrations, dependencias, workflow, secrets, registros, objetos Storage o configuración Auth. No se publicó una revisión nueva en producción. Seguridad por usuario/empresa queda por implementar y probar en Fase 2.

## Roadmap

| Phase | Status | Gate |
|---:|---|---|
| 0 | Completada | Auditoría y baseline entregados |
| 1 | Pendiente, no iniciada | Identidad visual + Design System Platform Foundation |
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
