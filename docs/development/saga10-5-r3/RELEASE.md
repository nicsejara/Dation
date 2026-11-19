# Activación posterior y rollback — NO EJECUTADOS

1. Revisar SHA exacto del PR y required-gate verde. Obtener GO específico para merge; verificar CI de main después.
2. Estos módulos siguen fuera de la allowlist de UX Autopilot. No ampliar política. Se requiere el circuito manual vigente y autorización de publicación.
3. Usar [README_RELEASE](../README_RELEASE.md) y las interfaces actuales del helper para status/prepare/smoke/promote. Registrar revisión/digest anterior y nuevo antes del GO de tráfico; no inventar comandos de infraestructura ni reconstruir a ciegas.
4. Validar login, draft recuperado, reset/cancel/refresh, B04/B05 sin saltos, tres pasos/perfiles y versiones publicadas/Data Contract. Mantener motores, Jobs, Scheduler y guardrails económicos según estado autorizado.
5. Rollback autorizado al código/revisión/digest anterior compatible con Saga10 v2; no borrar modelos, versiones ni bases. R3 no necesita migración SQL. El retorno a R2 conserva DTO, aunque puede recuperar la experiencia legada reportada; documentar el incidente y verificar consulta de publicados.

Fixtures usan PostgreSQL/PostgREST/API locales propios, con teardown acotado. No se ejecuta limpieza de Supabase. Una purga de datos reales requeriría otro alcance/autorización. La copia de draft es recuperación de UI, no rollback de datos ni el futuro modo review-only.
