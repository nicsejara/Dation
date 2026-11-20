# Integración posterior y rollback

Entrega: PR único abierto, sin merge/auto-merge, Docker, despliegue o tráfico. Motores productivos cerrados. Se exige autorización del propietario antes de integrar o publicar.

Después de GO: revisar SHA y required-gate, integrar por proceso vigente y utilizar `docs/development/README_RELEASE.md`. Los nuevos módulos/imports requieren revisión explícita de alcance; no se amplía la política G6 ni sus permisos. Registrar SHA integrado/digest/revisión reales; no se inventan aquí. Hacer smoke en revisión sin tráfico: wizard60cajas,90bloqueadas,80advertencia, dos tipos/editar, cinco confirmaciones, Case/Graph/Review y CTA de versión. Sólo promover con GO.

Rollback de código: revertir el commit del PR o volver al digest/revisión previo por runbook autorizado. Base `2bc0d934350dbef3d303b2a931432c445a04305a`. Dry run documentado en evidence/rollback-dry-run.json: aplicar runtime/assets a la base limpia, comparar bytes y revertir sin diferencias.

No hay migración ni nueva estructura persistida: se conservan claves R4/R5, IDs, buffers, guided_ux y publication intents. Conservar snapshots íntegros de drafts y versiones antes del cambio real; no borrar almacenamiento global ni datos. Un draft que R6 marca inconsistente puede volver a consultarse con la versión previa sin perder su contenido. La reversión de la guardia frontend elimina esa advertencia/bloqueo local; no corrige ni transforma los datos.

Rollback de navegación: volver a Case/Graph es Review de la versión pinneada, no restauración de draft ni rollback productivo. Crear Case con otra versión prepara un recurso independiente y conserva el padre. No resetear datos para resolver un problema de UI.

NO-GO de publicación si se pierde pin de versión, cambian hashes/IDs, falla DC/D1, hay overflow/halos, CTA inerte o la cabecera deja de ser simétrica. APIs y motores conservan sus guardas actuales. Ninguna operación productiva se ejecuta en esta tarea.
