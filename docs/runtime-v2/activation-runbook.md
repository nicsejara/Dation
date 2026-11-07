# Runtime V2 — activación manual, verificación y rollback

**No ejecutado. Billing OFF; apply bloqueado.** Todo cambio productivo requiere
GO específico. Preparación, una dispensa de datos o un presupuesto orientativo
no habilitan operaciones. El proyecto anterior queda fuera de toda orden.

## Gate de entrada

- SHA exacto del candidato con CI completa GREEN y cambios revisados. Merge o
  despliegue del PR requieren su autorización; no hay auto-merge/release.
- [Inventario de lectura](readonly-and-access.md) válido del proyecto nuevo,
  Billing OFF, triggers/builds/rutas de CD sin automatismo productivo por main.
- SA/IAM, APIs/cuotas, Registry y referencias de secretos concretas revisadas;
  no inventar verificación si hay 401. No es necesario modificar/retirar el
  worker del proyecto anterior para activar este proyecto aislado.
- Proyecto Supabase DDA/ref `gijiinufjjurgfeehufj`, bucket `dda-inputs` privado,
  conexión y catálogo compatibles. Revalidar antes del cambio.
- Propietario, workspace piloto existente, ventana y costos/residual aceptados.

## 1. DDA Free y migración aditiva — GO Supabase separado

No recrear DB ni hacer reset. Se mantiene la decisión del propietario del
7/11/2026: prescindir de respaldo restaurable de los datos operativos de prueba
existentes para esta primera activación. No requiere Pro ni restore. Preservar
esquema, funciones, migraciones, RLS, Auth, tenants y contratos Storage.

Orden exacto:

1. Leer historial/catálogo y queued/running/reconciliaciones. La última lectura
   observó 20 migraciones, RPC base presentes y tres backlogs en cero. Si cambia,
   revisar alcance/costo; no ejecutar ni borrar trabajo antiguo automáticamente.
2. Confirmar SHA-256 del archivo
   `supabase/migrations/20261106021935_zero_idle_execution_outbox.sql`:
   `43460ec4bdcc648e4fb41885ce561f8a6e5e4a6789572ac8112326318ded4123`.
3. Con GO de esa única migración, llamar `supabase_apply_migration` con
   `project_id=gijiinufjjurgfeehufj`, `name=zero_idle_execution_outbox` y `query`
   igual al archivo verificado. Conservar transacción/abort al primer error.
   Registrar receipt/versión real y hash; no repair ciego de timestamps ni
   `db push` de toda la carpeta, reset, seed o down.
4. Verificar tablas privadas policy/outbox con RLS y sin acceso directo de
   anon/auth/service_role; helpers y RPC con search_path/ACL previstos;
   `public.execution_runtime` sólo service_role; triggers y caché PostgREST.
5. Confirmar `enabled=false`, `admissions_open=false`. No ejecutar recover,
   reserve o configure activo todavía. Migrar no activa GCP.

Los datos actuales no necesitan borrado según la evidencia disponible. Si se
demuestra una incoherencia, preparar primero IDs/filas/objetos y FKs del workspace
afectado y obtener GO del cambio concreto. La dispensa no autoriza TRUNCATE,
eliminar Auth, deshabilitar RLS, cambiar credenciales indiscriminadamente o vaciar
el bucket. Preservar Model Versions/definiciones de contrato por defecto.

## 2. Billing, APIs, cuentas, secretos e imagen — GO económico

Sólo después del GO explícito del propietario, habilitar Billing en
**dation-runtime-v2-2026** y las APIs revisadas (Run, Registry, IAM, Secret Manager;
Scheduler sólo si se autoriza). Ninguna orden debe seleccionar el proyecto
anterior. No crear Cloud Build triggers ni usar deploy-from-source automático.

Usar los cuerpos de `infra/zero-idle/prepared-manifests.json` como propuestas:

- Crear/reutilizar `dation-runtime@dation-runtime-v2-2026.iam.gserviceaccount.com`
  y `dation-scheduler@dation-runtime-v2-2026.iam.gserviceaccount.com` tras verificar
  existencia/identidad. Cuentas administradas; ninguna clave JSON estática.
- Role `dationFiniteJobDispatcher`: `run.jobs.get/run/runWithOverrides`, ligado
  sólo a los dos Jobs. Scheduler SA: `roles/run.invoker` sólo en recovery.
  No allUsers en Jobs ni Developer/Editor de proyecto por conveniencia.
- Secret Manager: `dation-supabase-secret` y `dation-access-password`, versiones
  numéricas propuestas 1. Sus valores se cargan fuera de Git sólo tras GO; no
  están en los manifiestos. Verificar referencias reales antes del deploy.
  Runtime: secretAccessor sólo sobre esos secretos. LLM, si ya se usa, conserva
  su configuración/versión de secreto revisada; no se activa consumo nuevo.
- Operador: create/update/get de recursos revisados, Registry writer sólo en
  su repositorio, actAs sólo sobre esas SA. Preservar políticas existentes:
  GET, merge del delta autorizado y setIamPolicy con etag; nunca reemplazo ciego.

Los campos `parent` de las propuestas seleccionan el endpoint, no se envían
como un campo extra del body REST. Operaciones futuras concretas:

| Propuesta | Endpoint | Body |
|---|---|---|
| service_accounts[i] | POST `https://iam.googleapis.com/v1/{parent}/serviceAccounts` | sólo `accountId` y `serviceAccount` |
| iam.custom_role | POST `https://iam.googleapis.com/v1/{parent}/roles` | sólo `roleId` y `role` |
| secret_manager.create_proposals[i] | POST `https://secretmanager.googleapis.com/v1/{parent}/secrets?secretId={secretId}` | sólo el objeto `secret` |

Verificar antes si existen; un conflicto requiere revisar el recurso, no
reemplazarlo. Añadir valores/versiones de secretos es otra operación autorizada
fuera de Git; no hay un body con valores en estas propuestas.

Un único build/push manual autorizado del SHA validado, al Registry nuevo:

```sh
git rev-parse HEAD
git status --porcelain
docker build --label org.opencontainers.image.revision=<SHA_VALIDADO> --tag <IMAGEN_REGISTRY_NUEVO>:<SHA_VALIDADO> .
docker push <IMAGEN_REGISTRY_NUEVO>:<SHA_VALIDADO>
```

Confirmar digest remoto. No secretos en build args/capas ni tag latest como
identidad de release. Crear una copia revisada de release.json fuera de Git con
`release_sha` exacto, digest regional del proyecto nuevo y referencias reales;
generar el plan para esa copia. El validador rechaza otras cuentas/proyectos,
imágenes sin digest y destinos mezclados. No quitar el hold de apply.

## 3. Recursos cerrados: Jobs primero y API después

Con GO de creación/configuración, usar Cloud Run Admin v2, esperando cada
operación y releyendo el resultado:

| Recurso | Método y endpoint de creación (sólo si no existe) |
|---|---|
| Compute | POST `/v2/projects/dation-runtime-v2-2026/locations/us-west1/jobs?jobId=dation-executor` |
| Recovery | POST `/v2/projects/dation-runtime-v2-2026/locations/us-west1/jobs?jobId=dation-recovery` |
| API | POST `/v2/projects/dation-runtime-v2-2026/locations/us-west1/services?serviceId=dation-core` |

Bodies: jobs[0], jobs[1] y service del manifiesto **resuelto**. Si existe un recurso,
revisar snapshot/etag y hacer PATCH sólo del delta autorizado. Un 403 no acredita
ausencia. No ejecutar Jobs al crearlos. No usar el helper histórico de deploy.

Conservar límites ADR: API min=0/max=2/CPU por request/1 CPU/512 MiB/concurrencia8/
timeout300; compute 1 CPU/1 GiB/timeout1800; recovery 1 CPU/512 MiB/timeout120;
taskCount1/parallelism1/retries0. Revisar también mínimos a nivel de servicio,
revisiones y tags. Sin VPC connector/NAT/LB/Redis/VM/worker residente añadidos.

Inicialmente cloud execution=false y DB cerrada. Comprobar Jobs.get y
testIamPermissions(run.jobs.run, run.jobs.runWithOverrides) con la **identidad
runtime real**, sin ejecutarlos. Crear una revisión API puede arrancar
contenedores/cobrar aun sin tráfico; está dentro de esta autorización económica.

## 4. Login en la nueva URL — GO de configuración Auth

Leer la URI HTTPS real de la API nueva; no adivinarla usando un project number
ni reutilizar la URL anterior. Confirmar secreto de acceso y configuración DDA.

Después de GO específico, leer
`GET https://api.supabase.com/v1/projects/gijiinufjjurgfeehufj/config/auth` y
preparar el PATCH mínimo de `site_url` y `uri_allow_list` para la nueva URI:
`/app`, `/auth/callback` y `/auth/callback/recovery`. Preservar otros callbacks
autorizados y políticas actuales; no wildcard, reset de passwords/keys, cambio de
proveedores, SMTP o JWT. Releer el resultado y probar login/logout con el usuario
de prueba existente. No se envió email ni se cambió Auth en esta adaptación.

## 5. Cutover, outbox y recovery — GO de ejecución

1. Revalidar que sólo actúan la revisión nueva y los Jobs finitos **del proyecto
   nuevo**, con IAM/secret refs correctos. El proyecto anterior no se consulta ni
   se toca; no se comparten sus cuentas o recursos de ejecución.
2. Bajo GO de cutover, activar cloud flag en API/Jobs sin eliminar env/secret
   refs al hacer PATCH. Conservar explícitos los cinco campos de identidad del
   manifiesto. No usar el manifiesto con placeholders.
3. Configurar execution_runtime: enabled=true, admissions_open=false, cuotas
   piloto propuestas max_compute1/workspace-day6/global-day6/delivery-day12.
   El enable hace backfill; inspeccionar backlog/costo antes de habilitarlo.
4. Ejecutar un recovery finito autorizado: POST a
   `https://run.googleapis.com/v2/projects/dation-runtime-v2-2026/locations/us-west1/jobs/dation-recovery:run`
   con body `{}`. Esperar ejecución terminal y verificar last_recovery_at/frescura.
5. Scheduler previsto cada 15 min, Etc/UTC, OAuth de la SA separada, sin overrides,
   retries de Scheduler0. El manifiesto es **deshabilitado/no creado por defecto**.
   Crear el Job Scheduler puede activarlo inmediatamente: no hacer create para
   pausar después como supuesto paso inocuo. Su creación/activación exige GO
   separado, con estado y próxima ejecución registrados.
6. Sólo con recuperación fresca y garantizada, abrir admisiones del piloto
   existente. Preservar los flags/cohorte actuales; no habilitar más workspaces.

Los mecanismos DB de idempotencia/leases/fences/cuotas y aprobación humana no
cambian por el nuevo proyecto. El máximo global se controla en DB, no mediante
parallelism=1 por ejecución. No llamar apply ni usar un GO como bypass del hold.

## 6. Smoke: Logistics Model → Data Contract → Case → D1 → aprobación → D2

Un operador/workspace, 30 minutos de nuevas admisiones; USD1 variable orientativo.
Crear datos pequeños nuevos; no borrar los anteriores por rutina.

- Crear/reutilizar Logistics Model y publicar su versión desde UI existente.
- Ver Data Contract/preview y templates de esa versión; crear Case y obtener
  contrato definitivo/CSV del Case, validar/subir/publicar Data Pack. Conservar
  contract_hash, Model Version y Pack Version; no inventar un CSV/payload antiguo.
- D1 con nuevo run UUID y contexto/hashes actuales; esperar resultado/artifacts
  persistidos y Job terminal. Leer review y aprobar el fingerprint exacto.
- D2 sólo después de D1 aprobado, usando su run_id/result_fingerprint. Verificar
  resultado, artifacts y trazabilidad; aprobar D2 bajo las mismas reglas.
- Lectores/dashboard/historial/export/Case y una comparativa sin mutar base;
  replay del mismo UUID y cancelación pequeña dentro de las cuotas. No fake
  transports/flags de test en producción para inyectar pérdida de ACK.
- Cerrar nuevas admisiones, terminar/recuperar trabajo aceptado y comprobar
  Jobs terminales y API escalando a cero sin warmers ni procesos residentes.
  Verificar bytes/hash de artifacts privados; HTTP200 de buckets no prueba uploads.

No aumentar cuotas, timeouts ni debilitar assertions para conseguir verde. Si
falla un contrato, detener nuevas admisiones y diagnosticar sólo ese fallo.

## 7. Rollback y condiciones GO/NO-GO

Error de migración: abortar transacción y comprobar catálogo/historial. Después
del COMMIT, conservar esquema aditivo y cerrar admisiones; no DROP/down/reset.
En incidente operativo, cerrar sólo nuevas admisiones y pausar Scheduler,
terminar/cancelar ejecuciones conforme al GO de incidente; preservar outbox y
resultados aceptados. Volver sólo a una revisión comprobada compatible con DB
y scale-to-zero, o mantenimiento si no existe. Nunca recrear un worker residente
ni apuntar al proyecto anterior como rollback. La dispensa de datos no implica
que sus pérdidas puedan restaurarse ni autoriza una limpieza global.

NO-GO por identidad/IAM/despliegue desconocidos, placeholders, trigger automático,
recovery no fresca, inconsistencia de contrato/tenant/aprobación, proceso sin fin,
cuotas/costos no aceptados o falta de autorización de esa fase. Backup de datos
de prueba está dispensado y no bloquea. Billing permanece OFF hasta su GO.

El GO debe enumerar: proyecto nuevo, recursos/permisos, versión de código/digest,
migración única, Auth URL, ventana/piloto, Scheduler/Jobs/cutover y plan de incidente.
Cada autorización parcial deja cerradas las otras fases.
