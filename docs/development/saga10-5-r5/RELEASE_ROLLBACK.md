# Revisión, activación posterior y rollback

Entrega de código: PR único abierto, sin merge, imagen Docker, deploy, promoción de tráfico, ejecución de motores, SQL ni cambio de datos históricos. La revisión humana precede cualquier integración. No se cambian workflows, IAM, Billing, Scheduler o Cloud Build.

Después de GO explícito: revisar el SHA y required-gate; integrar por el procedimiento del repositorio. Utilizar el runbook manual existente `docs/development/README_RELEASE.md` para publicar el SHA integrado, registrar digest inmutable y preparar revisión sin tráfico. No inventar revisiones productivas o digests en este documento. Validar login/navegación y el smoke del wizard con datos autorizados, manteniendo los motores y sus flags cerrados.

Smoke de UI: ambos formularios completos y métricas abajo a la derecha → primer guardado/guía → segundo/2 de 2 → editar sin cambiar IDs → cinco confirmaciones disabled/check → reload → publicado/Graph/retorno → histórico legible. Si falla geometría, se cruzan assets, cambia un contrato o se pierde estado, NO-GO de promoción.

Rollback técnico: revertir el commit del PR o usar la revisión/digest anterior mediante el mecanismo vigente, sólo con autorización. Base de código conocida `9f466b505ee2b852a5c83e240b6871778c81a380`. El dry run aplica el parche de runtime/assets sobre un worktree de esa base, compara los archivos exactos y lo revierte sin diferencias.

No hay migraciones ni cambios de formato del draft R4. Se preservan guided_ux, catálogo guardado, buffer, IDs e intent de publicación. Conservar exportación íntegra de drafts antes de una promoción/rollback real; no borrar sessionStorage global ni entidades. La selección cm/m mantiene la magnitud en ambos renders; el backend previo entiende las dimensiones y unidades resultantes.

Si un WebP falla, el fallback local no bloquea el guardado ni los cálculos. El rollback de assets es independiente de los datos; no eliminar registros, versiones, runs ni auditoría. Una publicación incierta sigue protegida por los intent/CAS originales y no habilita reset inseguro.

[Dry run real PASS](evidence/rollback-dry-run.json): aplicación, comparación exacta de los 17 archivos runtime/assets y reversión sobre la base limpia, sin operaciones productivas.
