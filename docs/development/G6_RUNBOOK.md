# G6 — Operación, recuperación y rollback

Aplicable después del bootstrap y GO inicial. No ejecutar estos comandos para
activar producción durante el PR de infraestructura. [Permisos](G6_BOOTSTRAP_PREVIEW.md).

## Cada cambio de UX autorizado

1. Codex parte de main, implementa el diff puntual y tests afectados en una rama.
2. Un solo PR; corregir fallos en esa rama. Clasificador Rapid real: R1/R2 FAST;
   R3/R4 FAST+FULL y sin autodeploy. No editar mapa/clasificador para reducir CI.
3. Integrar sólo con controles obligatorios verdes y HEAD del PR sin cambiar.
4. El FAST del commit fusionado autoriza el orquestador sólo si es el SHA vigente.
5. GitHub publica una imagen o reutiliza la ya verificada, prepara revisión al 0%,
   comprueba `/health`, promueve al 100%, vuelve a comprobar y sube el recibo.
6. Entregar enlace al run/recibo, SHA, digest, revisión exacta, rollback y `/app`.
   El propietario valida el cambio visual. Health no prueba login ni calidad visual.

Sin variables aprobadas, el run genera SKIPPED y no solicita identidad GCP. La
activación no despliega retroactivamente el PR G6 ni un R3/R4.

## Kill switch y concurrencia

```sh
gh variable set DATION_UX_AUTODEPLOY_ENABLED --repo nicsejara/Dation --body false
```

Detiene nuevas elegibilidades y el job de despliegue que aún no comenzó. No revoca
instantáneamente un token/job ya en ejecución: consultar su estado antes de
intervenir. No cancelar a ciegas una promoción. El grupo común
`dation-core-ux-release`, `cancel-in-progress:false`, serializa autorelease y ops;
GitHub puede sustituir runs pendientes. HEAD/gate/etag/generación/revisión se
revalidan igualmente, por lo que un run atrasado nunca promueve. Un deploy manual
no participa en esa cola; CAS/drift lo detectan y detienen G6.

## Preflight de lectura tras GO de identidad

```sh
gh workflow run dation-ux-ops.yml --repo nicsejara/Dation --ref main -f operation=preflight
```

No modifica GCP. Verifica OIDC y permisos efectivos mediante servicio/revisión,
actAs y Registry; deja recibo READ_ONLY_IDENTITY_VERIFIED con commit OCI activo.
No confundir un test local o metadata IAM con esa prueba real.

## Recibos y checkpoints

Artifacts v4 inmutables, 90 días: `g6-plan-RUN`, `g6-publish-claim-RUN`,
`g6-publication-RUN`, `g6-snapshot-RUN`, `g6-prepared-RUN`, `g6-smoke-RUN`,
`g6-promotion-intent-RUN`, `g6-release-RUN`. Hash SHA-256 del ZIP verificado al
restaurar; repositorio, workflow/ref/evento, run, SHA y release ID comprobados.
No token GitHub al almacenamiento de redirección; no ejecutar código descargado.
No incluir credenciales ni logs/config OCI completos en artefactos.

`G6_RELEASE_RECEIPT.json` final: APPLICATION_SHA, CI_PASS, PUBLISH_PASS,
IMAGE_DIGEST, READY_REVISION, TRAFFIC, HEALTH_PASS, ROLLBACK_REVISION, fingerprints,
PR, gate/build/run, hora y URL. Sólo `ACTIVATED` con TRAFFIC100 y HEALTH_PASS es
release productivo comprobado. `PLANNED`/`PUBLISH_PASS` no significa desplegado.
Estados de fallo: SKIPPED, FAILED, FAILED_PREPARED_CLEANED (antigua100 sin tag),
FAILED_ROLLED_BACK (health post falló y se restauró la antigua), ROLLED_BACK.

## Recuperar un corte (sólo ante solicitud explícita)

```sh
gh workflow run dation-ux-ops.yml --repo nicsejara/Dation --ref main \
  -f operation=recover -f source_run=RUN_CON_CHECKPOINTS \
  -f confirmation=RECOVER_SAME_RELEASE
```

- Claim sin child identificable: NO-GO; no segundo dispatch. Consultar el historial
  del publicador para resolver esa solicitud exacta. Nunca rerun del publisher
  para reconstruir una imagen ya intentada.
- Child existente: correlacionar y recopilar el mismo recibo, sin nuevo POST.
- Snapshot sin revisión exacta: NO-GO; no redeploy ciego. Resolver el intento antes
  de iniciar una nueva release. Un nuevo run FAST puede generar nueva release sólo
  después del diagnóstico; el publicador conserva su guardia build-once por SHA.
- Revisión preparada: reutilizarla sin nueva creación, volver a probar URL exacta,
  persistir intent y promover únicamente si main sigue igual y no hay drift.
- Promoción aplicada pero recibo interrumpido: reconciliar revisión/generación/
  fingerprint y health de lectura, sin otra escritura de tráfico.
- Si main avanzó, otro deploy cambió IAM/config/revisión, falta evidencia o expiró
  el artefacto: detener. No adoptar estado ajeno ni generar recibo ficticio.

## Rollback explícito

```sh
gh workflow run dation-ux-ops.yml --repo nicsejara/Dation --ref main \
  -f operation=rollback -f source_run=RUN_CON_RECIBO \
  -f confirmation=ROLLBACK_100
```

Restaura anterior100 sólo si su revisión sigue READY/config compatible y todavía
controlamos la misma generación/etag nueva. No usa latest. Si ya está antigua100,
no se escribe tráfico. No revierte DB, secretos, IAM ni Jobs. Guardar ambos recibos.
El helper manual original permanece como último fallback bajo autorización.

## Fallos y costos

401/403: fallar sin ampliar roles ni reintentar autenticación a ciegas. Digest o
etiqueta SHA conflictiva: NO-GO sin overwrite. Candidata503: limpiar tag propio y
mantener antigua100. Post-health503: rollback únicamente bajo control exclusivo;
si hay drift, falla explícitamente y exige intervención.

El smoke puede iniciar instancias al consumir la URL de una revisión con tráfico
0; no hay min instances ni CPU residente. Revisiones e imágenes se conservan para
rollback (Registry sí puede tener costo de almacenamiento). GitHub minutos,
requests, logs y red no son capados globalmente por el presupuesto USD5. No se
crean Jobs, Scheduler, builds Cloud Build ni recursos de cómputo permanentes.
