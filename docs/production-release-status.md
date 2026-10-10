# Estado de publicación — 10 de octubre de 2026

## Fases 0–2 publicadas y verificadas

- URL: https://dation-core-469052310590.us-west1.run.app/app
- Commit publicado: `c731002633cff19696976912b489cf592cc637da`, incorporado mediante [PR #36](https://github.com/nicsejara/Dation/pull/36).
- Revisión confirmada por el deploy: `dation-core-00467-nd8`.
- [CI de main](https://github.com/nicsejara/Dation/actions/runs/38067835554): éxito.
- [Cloud Build](https://console.cloud.google.com/cloud-build/builds/569ea622-d3d9-448c-b82a-01df30acfe96?project=469052310590): éxito, 100 % del tráfico a la revisión nueva.
- Verificación HTTP contra producción: health, Basic auth de app, contratos Orders/Fleet V3, hashes exactos de navegación/lifecycle/polling/workspace, `no-cache`, ETag 304 y Range 206.
- Cuatro recorridos Chromium con 68 assets recuperados de producción: refresh de Scheduling, atrás/adelante, reejecución que conserva aprobación y configuración móvil. La API fue interceptada con fixtures sintéticos: estos recorridos prueban los assets publicados y no escriben datos ni acreditan persistencia productiva.

El árbol independiente de las Fases 0–2 pasó 280 tests Python, 18 Node y 24 Chromium. Auditorías runtime/navegador sin vulnerabilidades conocidas. El ajuste de empaquetado del contenedor se incorporó mediante [PR #38](https://github.com/nicsejara/Dation/pull/38), commit `bdffa4995911a5ca51b10bd8504dc42e10280b47`: propietario de archivos y estructura de ejemplos V3, verificados con arranque sin root y smoke local. El [Cloud Build posterior](https://console.cloud.google.com/cloud-build/builds/830f1e72-7750-410b-bc6f-85fb1b0463c8?project=469052310590) publicó la revisión `dation-core-00468-85p`, comprobada por HTTP. No modifica la interfaz ni requiere SQL.

## Fase 3 publicada y verificada

[PR #37](https://github.com/nicsejara/Dation/pull/37) contiene cola transaccional, leases, fencing, idempotencia, cancelación y reconciliación por versión. El registro siguiente corresponde a la activación y comprobación realizadas **antes de incorporar el PR a main**; el Cloud Build automático puede crear una revisión posterior con el mismo código funcional.

- Commit de la imagen: `73df3b27bf086efb794fe580b1601670e12a4595`.
- [CI del commit exacto](https://github.com/nicsejara/Dation/actions/runs/38073355779): éxito. Validación: 306 Python, 18 Node, 24 Chromium y 12 SQL reales sobre PostgreSQL 16; auditorías runtime/navegador sin vulnerabilidades conocidas.
- Migración `20261010100000_dispatch_durable_jobs.sql`: aplicada atómicamente mediante Supabase Management API. Tablas, ocho funciones, dos triggers y RLS verificados; los seis RPCs requeridos son visibles para la clave de datos. No había corridas antiguas en vuelo. No se reescribió el histórico.
- [Cloud Build de la imagen compartida](https://console.cloud.google.com/cloud-build/builds/61274a41-ee72-4a8f-86a1-97ccb140b5e2?project=469052310590): éxito. Imagen en `cloud-run-source-deploy/dation-phase3/dation-core:73df3b27bf086efb794fe580b1601670e12a4595`.
- Worker: `dation-core-worker-00001-wf5`, Ready, mínimo 1, máximo 2, CPU permanente, 2 GiB, un solver por proceso. IAM privado y comprobación de invocador habilitada; utiliza las referencias existentes de Secret Manager.
- API: `dation-core-00469-vdc`, Ready, 100 % del tráfico. Se conservaron cuenta de servicio, autenticación, variables, secretos, recursos y escalado de la API. Revisión previa para rollback: `dation-core-00468-85p`.
- HTTP: `/health`, acceso autenticado a `/app`, rechazo anónimo, diagnóstico Dispatch disponible, hashes de cinco módulos publicados, `no-cache`, ETag 304 y Range 206 verificados.

Prueba con persistencia real terminada el **10 de octubre de 2026, 14:59 ART (17:59 UTC)**: archivos CSV sintéticos, caso aislado `74a47dc2-aca9-4416-a38b-1f2cf34f8f54`, Assignment → aprobación → Scheduling → aprobación. Ambos trabajos completaron en un intento. POST devolvió 202 con Location/Retry-After; repetir UUID conservó la corrida y cambiar la intención devolvió 409. La aprobación y el upstream se conservaron, el outbox se vació y las lecturas repetidas mantuvieron el resultado terminal. Un primer ejemplo de 30 órdenes sin programación factible también guardó correctamente el estado de error; no se cambió el motor para acomodar esos datos.

Todos los casos y archivos de QA quedaron archivados y la flota vigente permaneció igual. La recuperación tras reinicio y el fencing se comprobaron con SQL transaccional aislado; no se reinició un worker con trabajos de operadores para hacer QA.

Los accesos administrativos ya están configurados en el entorno seguro. Las instrucciones y el orden reproducible de publicación están en [phase3-production.md](phase3-production.md). La verificación posterior al merge debe consultar el check de Cloud Build del commit de main y la revisión que recibe tráfico, además de salud y el diagnóstico durable.
