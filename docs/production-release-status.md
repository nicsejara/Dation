# Estado de publicación — 10 de octubre de 2026

## Fases 0–2 publicadas y verificadas

- URL: https://dation-core-469052310590.us-west1.run.app/app
- Commit publicado: `c731002633cff19696976912b489cf592cc637da`, incorporado mediante [PR #36](https://github.com/nicsejara/Dation/pull/36).
- Revisión confirmada por el deploy: `dation-core-00467-nd8`.
- [CI de main](https://github.com/nicsejara/Dation/actions/runs/38067835554): éxito.
- [Cloud Build](https://console.cloud.google.com/cloud-build/builds/569ea622-d3d9-448c-b82a-01df30acfe96?project=469052310590): éxito, 100 % del tráfico a la revisión nueva.
- Verificación HTTP contra producción: health, Basic auth de app, contratos Orders/Fleet V3, hashes exactos de navegación/lifecycle/polling/workspace, `no-cache`, ETag 304 y Range 206.
- Cuatro recorridos Chromium con 68 assets recuperados de producción: refresh de Scheduling, atrás/adelante, reejecución que conserva aprobación y configuración móvil. La API fue interceptada con fixtures sintéticos: estos recorridos prueban los assets publicados y no escriben datos ni acreditan persistencia productiva.

El árbol independiente de las Fases 0–2 pasó 280 tests Python, 18 Node y 24 Chromium. Auditorías runtime/navegador sin vulnerabilidades conocidas. El ajuste de empaquetado del contenedor está en [PR #38](https://github.com/nicsejara/Dation/pull/38): propietario de archivos y estructura de ejemplos V3, verificados con arranque sin root y smoke local. No modifica la interfaz ni requiere SQL.

## Fase 3 implementada; activación administrativa pendiente

[PR #37](https://github.com/nicsejara/Dation/pull/37) contiene cola transaccional, leases, fencing, idempotencia, cancelación y reconciliación por versión. Validación local: 301 Python, 18 Node, 24 Chromium y 12 SQL reales sobre PostgreSQL 16. El contenedor incluye worker, API, ejemplos y conocimiento; arranque y permisos se comprobaron con ruedas verificadas por hashes en QA offline. CI remota agrega las pruebas SQL.

La consulta autorizada de Supabase confirmó que aún no existen `dispatch_run_jobs` ni los RPCs de la cola. Los scripts de publicación se ejecutaron hasta sus comprobaciones previas y se detuvieron por falta de `SUPABASE_ACCESS_TOKEN` y de una cuenta/token de Google Cloud. No se aplicó DDL, no se creó el worker productivo y no se incorporó la API durable a main. La clave de datos existente permite REST pero no administración SQL.

Se guardaron los requisitos seguros de ambos accesos y las instrucciones reutilizables del entorno. Para continuar, configurar los secretos en los ajustes, guardar y publicar; seguir el orden de [phase3-production.md](phase3-production.md): migración, worker, API verificada y luego merge a main. No se requiere nueva autorización para producción: el usuario ya la otorgó.
