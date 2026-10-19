# Estado de implementación · Platform MVP v1

Fecha de referencia: 2026-10-18 (`America/Buenos_Aires`). Fuente de requisitos: `PROMPT_MAESTRO_SUPER_PRO_Dation_Platform_MVP_v1.md` adjunto por el usuario. El roadmap contiene Fases 0–12; este registro pertenece a esa saga, no a las anteriores sagas UX/D1/D2.

## Estado vigente

Fases 2 y 3 publicadas en el [PR #75](https://github.com/nicsejara/Dation/pull/75), con cierre de BFCache en [#76](https://github.com/nicsejara/Dation/pull/76). Fases 4 y 5 publicadas en [#77](https://github.com/nicsejara/Dation/pull/77) y [#78](https://github.com/nicsejara/Dation/pull/78), con CI de head/main verdes y API/worker al 100%. Fase 6 publicada en [#79](https://github.com/nicsejara/Dation/pull/79) y Fase 7 en [#80](https://github.com/nicsejara/Dation/pull/80). Fase 8 implementa Equipo, invitaciones, responsabilidades y aprobación asignada; su publicación exacta se registra en el PR tras validar CI y despliegue. No se inicia Fase 9 automáticamente. La prueba manual completa del usuario queda para terminar todas las fases.

- [Auth, identidad y migración](10-phase2-auth-tenancy.md).
- [Shell y navegación](11-phase3-shell-navigation.md).
- [Workspace Home](12-phase4-workspace-home.md): casos recientes, atención real, accesos y estados. Feed de actividad reservado a Fase 10, sin eventos inventados.
- [Catálogo y entitlements](13-phase5-dda-entitlements.md): diseño conservado, permisos desde DB y controles en UI/rutas/API. Sin migraciones ni escrituras productivas de release.
- [Data Hub](14-phase6-data-hub.md): biblioteca transversal, detalle/preview, autoría nueva, pares derivados y reutilización; archivo y eliminación segura con recuperación.
- [Decision Center](15-phase7-decision-center.md): biblioteca de casos, detalle por nodo, etiquetas, historial secundario y recuperación directa de D1/D2.
- [Equipo y colaboración](16-phase8-team-collaboration.md): aceptación con email confirmado, roles, asignaciones por nodo, atribución, intervención Admin auditada y handoff D1/D2.
- Baseline de CI de Fase 7: 360 unittest, 85 Node, 167 Chromium, 46 SQL históricos y 34 E2E del esquema final sin skips. Fase 8 añade cuatro E2E con recorridos reales de invitación, aprobación y aceptación sin membresía; CI del SHA exacto se exige antes de publicar.
- Verificación productiva: ingreso, refresh y logout reales de Supabase; cuenta temporal sin membresía bloqueada y luego eliminada; template y diez assets exactos. Evidencia de negocio sin cambios.
- Backup/restauración previa: 91 registros y seis archivos, evidencia existente sin cambios; artifacts privados fuera del repo.
- Configuración reutilizable de entorno: install_script y start_skill actualizados para Auth/Bearer, smoke sin escrituras y QA aislado. No se agregaron secretos nuevos.
- Límite: la fixture Auth no certifica entrega real de correo. Primer acceso requiere registro y confirmación del administrador autorizado; no se envían correos desde scripts de release.

Los snapshots de auditoría anteriores describen deliberadamente el esquema previo a tenancy. No deben interpretarse como estado actual tras migrar. Commit/checks/revisiones exactos se agregan al PR y al informe de publicación; no se inventa el SHA del propio commit.

## Roadmap

| Phase | Status | Gate |
|---:|---|---|
| 0 | Completada | Auditoría y baseline entregados |
| 1 | Implementada y validada | Foundation optativa, interacción/QA y consumidor real; [detalle](09-phase1-foundation.md) |
| 2 | Implementada · gate A/B validado | Auth + identity + workspace + tenancy/security A/B |
| 3 | Implementada y publicada | Platform shell + navegación/routing |
| 4 | Implementada y publicada | Workspace Home, aislamiento, estados y navegación real; PR #77 |
| 5 | Implementada y publicada | Catálogo + entitlements; PR #78 |
| 6 | Implementada y publicada | Data Hub, Data Packs y recuperación; PR #79 |
| 7 | Implementada y publicada | Decision Center y memoria de casos; PR #80 |
| 8 | Implementada · publicación verificable en PR | Equipo + colaboración + atribución y handoff |
| 9 | Pendiente | Settings + plan manual |
| 10 | Pendiente | Audit trail + actividad |
| 11 | Pendiente | Onboarding/demo/estados |
| 12 | Pendiente | Hardening + seguridad + E2E + release comercial |

Cada fase deberá registrar su commit, fecha, pruebas, riesgos y siguiente gate. No anticipar funciones ni resetear datos actuales.
