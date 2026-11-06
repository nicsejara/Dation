# Release y rollback: permiso económico separado

Estado actual: **MERGE_BLOCKED_DEPLOY_TRIGGER**, Billing OFF por instrucción,
**UNVERIFIED_LIVE** por las lecturas 401. Ningún paso productivo de este runbook
fue ejecutado. El SHA base es `92656a1c8c94ae1181a18c47ddd681eaa313f92b`.

## Controles entregados

`python scripts/zero_idle_release.py` equivale a `plan`, sin red ni escritura.
`validate` valida proyecto/región, cero instancias mínimas, CPU de API por
request, recursos, comandos finitos, referencias de secretos y todos los
scripts Python de despliegue. Genera cuerpos Cloud Run v2 revisables desde
`infra/zero-idle/release.json`; no construye ni publica imágenes. Los campos
SHA/digest/cuenta/secretos sin verificar permanecen pendientes explícitos.

`apply --authorize ...` existe como entrada separada **bloqueada**: rechaza antes
de cualquier llamada productiva, incluso con una variable antigua o flag GO.
No se entrega un bypass de los gates que hoy no se pueden demostrar. Después
de la autorización futura se debe revisar y retirar ese hold con evidencia
live, sin confundir un flag con prueba de IAM, CI, Billing o seguridad de CD.
`rollback` genera un plan, sin aplicarlo. El entrypoint histórico
`deploy_production_phase3.py` delega al plan seguro; su transporte histórico
rechaza escrituras. `release_platform_identity.py` rechaza su CLI legado.
Los helpers antiguos siguen cubiertos por sus pruebas de preservación de
secretos/cuenta/recursos y de readiness de la revisión nueva.

## Gate de merge independiente de Billing

El propietario debe identificar y deshabilitar **todos** los triggers externos
que construyen/publican/despliegan por `main`, o demostrar una aprobación manual
que impida esos efectos antes de empezar. Verificar global y `us-west1`, filtros
de branch, repositorio, substitutions/build inline y cuentas utilizadas.
Guardar IDs, configuración y resultado de una prueba inocua autorizada.
Un archivo de GitHub en este PR no administra esos triggers remotos. Hasta
entonces: PR abierto, nunca merge automático. No se cambian triggers en esta tarea.

## Orden futuro, solamente con GO explícito

1. Confirmar CI completa del SHA exacto, árbol limpio y guard de CD real. Capturar
   inventario live de servicios, revisiones, Jobs, IAM, Scheduler, secretos y
   recursos persistentes; limitarlo al proyecto `dation-510100` / `469052310590`.
2. Acordar presupuesto del smoke: propuesta **USD 1 de consumo bruto variable**,
   más cargos persistentes ya inventariados. No es un cap garantizado. Si el
   propietario no acepta el residual, permanecer Billing OFF y sin despliegue.
3. Verificar backup/restore y aplicar **la migración aditiva** únicamente con
   autorización separada de Supabase. Política inicia `enabled=false` y
   `admissions_open=false`; no inicia Jobs, cron ni activación de GCP.
4. Sustituir placeholders por SHA/digest exactos, cuenta(s) verificadas y
   referencias **versionadas** de Secret Manager, sin valores en JSON/CLI/logs.
   Supabase URL/bucket son configuración, no deben inventarse a partir del fixture.
5. Billing sigue OFF hasta el GO económico específico del propietario. No hay
   script para enlazar Billing automáticamente. Verificar su estado real antes
   de aplicar recursos facturables; 401/estado desconocido implica NO-GO.
6. Publicar la imagen revisada bajo un proceso manual autorizado. Crear los dos
   Jobs **sin ejecutarlos** y el servicio API con `minInstanceCount=0`, máximo 2,
   `cpuIdle=true`, 1 CPU/512 MiB, concurrencia 8. Compute: 1 CPU/1 GiB, 1 tarea,
   paralelismo 1, timeout 1800 s, retries de plataforma 0. Control: 1 CPU/512 MiB,
   timeout 120 s. No VPC/NAT/LB/Redis adicionales. Revisar diferencias completas
   y preservar referencias de secretos antes de cualquier reemplazo de servicio.
7. IAM: identidad administrada para la API y ejecutores. Rol personalizado con
   `run.jobs.get`, `run.jobs.run`, `run.jobs.runWithOverrides`, vinculado solamente
   a `dation-executor`/`dation-recovery`; verificarlo con `testIamPermissions`.
   Scheduler usa una identidad distinta, OAuth y permiso de invocación solamente
   sobre el Job control, sin overrides. No `allUsers`, cuenta de usuario, clave
   estática de GCP ni rol Developer a nivel de proyecto. Runtime accede solamente
   a los secretos necesarios mediante referencias; no IAM de administración.
8. Drenar el worker legado antes de cambiar de modo. No ejecutar ambos claimers
   sobre trabajo vivo. Deshabilitar su tráfico/instancias y verificar eliminación
   de su revisión permanente según inventario autorizado, sin reutilizarla.
9. Configurar `DATION_EXECUTION_MODE=jobs`, nombres estrictos de ambos Jobs y
   `DATION_CLOUD_EXECUTION_ENABLED=true` **sólo tras los gates**. Mantener admisión
   DB cerrada. Activar outbox (`configure enabled=true`) y verificar backfill de
   trabajo previamente aceptado; no eliminar decisiones/outbox para un cutover.
10. Autorizar por separado Scheduler cada 15 min → `dation-recovery:run` con
    OAuth, no una URL pública ni un warmer de API. Ejecutar un recovery autorizado,
    comprobar frescura/capacidad, recién entonces `admissions_open=true`.
11. Smoke pequeño D1→aprobación→D2→aprobación, lectores/dashboard/historial/export,
    comparativa y Case. Probar duplicado, pérdida de ACK y cancelación. Verificar
    que todos los procesos y ejecuciones terminen. Jobs no ofrecen un SLA de
    inicio de 10 s; medir P50/P95 live antes de prometerlo.
12. Tras idle, verificar instancias API = 0 y ausencia de ejecutores residentes.
    El control Job programado sí tiene actividad periódica; no es idle total.
    Revisar cargos por SKU tras demora contable, incluyendo Registry/Build/red.

## Rollback y operación de fallos

- Congelar sólo **nuevas** admisiones (`configure admissions_open=false`). Un replay
  conserva su intención; decisiones ya aceptadas conservan outbox y recuperación.
- Revertir sólo a una revisión demostrada de cero idle compatible con esta DB.
  Si no existe, elegir mantenimiento temporal. **Nunca** restaurar el servicio
  worker con mínimo 1, CPU permanente o el comando `worker.py`.
- No DROP de tablas/migraciones, no borrado de artifacts/historial. `enabled=false`
  es un freno de despacho y requiere plan explícito para trabajo ya aceptado.
- Dependencia caída: conservar intención, recuperar con lease/epoch nuevo,
  máximo 3 activaciones y plazo de negocio existente de 30 min. El Scheduler
  de 15 min puede observar un startup lease de 5 min aún válido: demora hasta
  aproximadamente 20 min más latencia del proveedor, sin prometer un SLA live.
- Dead letter de Case se conserva y alerta; no se aplica un ACK ciego. Reabrir
  únicamente con versión/fence válidos y revisión operacional autorizada.
- En incidente económico, suspender nuevas admisiones y Scheduler, cancelar
  ejecuciones autorizadamente y evaluar Billing OFF manual del proyecto Dation.
  Conservar datos, evidencias y permisos; no gestionar otros proyectos/cuentas.
