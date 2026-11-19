# Activación y rollback — solo propuesta, sin ejecución

Esta entrega es un PR para revisión. No merge, publicación Docker, deploy, cambio de tráfico, migración, activación de motores ni operación en producción. No cambia Billing, Supabase, IAM, Scheduler, Cloud Build, SQL, backend ni workflows.

Tras GO explícito: revisar HEAD exacto y required-gate, integrar por el procedimiento del repositorio y usar el runbook manual vigente (`docs/development/README_RELEASE.md`) para publicar/desplegar ese SHA con digest inmutable. Revalidar en revisión sin tráfico: nuevo modelo → 1/2 tipos → edición → cinco CTA → publicación solo en workspace de pruebas autorizado → revisión desde Graph. Mantener flags de motores cerradas y scale-to-zero.

NO-GO: cualquier tipo pisado, ID regenerado, CTA confirmado habilitado, resultado stale, control DENY en rutas nuevas, publicado mutable, CI requerida roja o falta de autorización. No activar automáticamente infraestructura para resolverlo.

Rollback de código: revertir el commit del PR, conservando base conocida `797f9fc49b497fb6d266621926cdffbe03640e77`; validar el diff inverso en worktree temporal (dry run). No cambia schema ni requiere rollback de BD. Para promoción posterior, registrar digest/revisión previa reales y usar el mecanismo de rollback existente; no inventar una revisión productiva a partir del SHA de código.

Compatibilidad de drafts en rollback: `guided_ux.catalogue` mantiene el DTO que R3 lee; metadata `r4` adicional es UI y puede ignorarse por código previo. **Exportar/conservar el draft completo antes de revertir**, especialmente un buffer de tipo aún sin guardar que R3 no renderiza. No borrar sessionStorage, modelos, versiones, Cases ni auditoría como atajo. La revisión de solo lectura conserva los contratos históricos publicados.
