# Publicación posterior — procedimiento manual, NO ejecutado

## Estado de esta entrega

PR abierto para revisión, sin merge, imagen publicada ni despliegue. Cambios exclusivamente de frontend/browser/docs. Motores, flags, Supabase, IAM, Jobs, Scheduler, Cloud Build y Billing no se modifican.

NO_AUTO_DEPLOY: la política actual no allowlist cargo-editor.mjs, model-fields-v2.mjs, guided-ui.mjs ni wizard-ui.mjs. También hay tests/docs fuera de su lista. No ampliar esa política para evitar revisión. CI R2/FAST y elegibilidad de release son gates distintos.

## Secuencia que requiere autorización del propietario

1. Revisar el SHA exacto y required-gate terminal del PR. Obtener GO de merge separado. Integrar sólo ese candidato y verificar el required-gate automático del nuevo main, sin lanzar una suite duplicada.
2. Confirmar baseline operativo y rollback mediante el runbook vigente. Si Saga10 aún no se activó, su SQL/flags/lector compatible son un gate independiente: este PR no aplica migraciones ni habilita capacidades para mostrar una pantalla.
3. Con GO específico de publicación, ejecutar el workflow manual Runtime V2 - manual Gate C image publication (runtime-v2-publish.yml), ref main, application_sha igual al SHA integrado/validado y confirm_publish=true. No usar el SHA móvil de una rama. El workflow verifica origen/checks, reutiliza una imagen idéntica o construye una vez y emite recibo GateC con digest.
4. El workflow publica la imagen, no cambia tráfico. Descargar/verificar su recibo, commit y digest inmutable. Ante resultado ambiguo, detenerse y reconciliar evidencia, sin un segundo build ciego.
5. Con checkout confiable de ese SHA, seguir docs/development/README_RELEASE.md y el helper existente. Operaciones productivas requieren GO; estos ejemplos no se ejecutaron:

    python3 scripts/release/dation_release.py status
    python3 scripts/release/dation_release.py prepare --sha SHA_MAIN_VERDE_40_HEX
    python3 scripts/release/dation_release.py smoke --sha SHA_MAIN_VERDE_40_HEX

Prepare prepara la revisión sin promoción. El smoke de este helper es pasivo (READY/imagen/settings), no prueba HTTP de una revisión sin tráfico. No afirmar login verificado por ese smoke. Una exposición etiquetada o promoción y su verificación HTTP requieren la autorización operativa correspondiente.

6. Preservar min_instances=0, max existente1–2, CPU por solicitud, flags de ejecución/admisión cerrados y Scheduler OFF. Ningún paso de esta saga autoriza cambiar esos guardrails.
7. Sólo con GO de tráfico, usar el procedimiento vigente de promoción y comprobar URL/login, modelo v1 y v2, Básico/Detallado, borrador, publicación controlada y Data Contract. No ejecutar D1/D2 como smoke UX:

    python3 scripts/release/dation_release.py promote --sha SHA_MAIN_VERDE_40_HEX --confirm PROMOTE_100

## Rollback

Registrar previamente revisión/digest comprobados en el recibo de prepare. Si ya hay modelos v2, el destino debe ser lector compatible con Saga10; no regresar ciegamente a una imagen anterior que no los comprende. Saga10.5 no cambia DTO/SQL y permite rollback a un lector Saga10 compatible.

Con GO específico y baseline comprobado, el helper utiliza su recibo por SHA para restaurar la revisión anterior:

    python3 scripts/release/dation_release.py rollback --sha SHA_MAIN_VERDE_40_HEX --confirm ROLLBACK_100

No borrar datos ni modificar el historial de migraciones UX04. No se verificaron recursos, permisos, Billing, revisiones o tráfico live en esta tarea; no se inventa su estado. La publicación/Registry/Cloud Run pueden generar costos y ningún presupuesto orientativo garantiza suspensión automática.

Referencia operativa autoritativa: el runbook y scripts del checkout confiable vigente al autorizar. No nuevos triggers, claves, procesos residentes o modificaciones IAM para publicar esta UX.
