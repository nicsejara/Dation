# UX06 — matriz de aceptación y evidencia

Baseline `b9c9967ad0285d0cb0e873fa359a839ad1fb492b`, PR120 integrado, CI main43761427658 GREEN. Diseño/owners: [DESIGN](DESIGN.md). Futura activación, no ejecutada: [ACTIVATION](ACTIVATION.md). La CI terminal y el SHA exacto se registran en el único PR; este documento no sustituye required-gate.

## Reproducibilidad

Desde `backend/tests/browser`, con Python/Chromium y Docker/PostgreSQL aislados del repositorio:

```sh
python -m unittest -v test_journey_navigation_ux06 test_unified_decision_journey test_decision_graph_ux05 test_ultimate_navigation
```

Desde la raíz:

```sh
node backend/tests/test_journey_navigation_ux06.mjs
node backend/tests/test_journey_routes.mjs
python3 scripts/ci/impact.py --base "$BASE_SHA" --head "$HEAD_SHA"
python3 scripts/ci/static_check.py --base "$BASE_SHA" --head "$HEAD_SHA"
```

Los fixtures comprueban identidad de contenedores propios y eliminan credenciales productivas. El E2E UX04 usa D1/D2 reales **locales**, aprobación/recuperación de respuesta perdida, Dashboard exacto y cierre. Los metadatos T5 de estados/roles no se presentan como resultados matemáticos. No se ejecutan motores productivos ni se aplica SQL a Supabase.

## Pruebas y capturas

`T01`–`T14`: `JourneyNavigationTests`. `W01`–`W15`: UX04, incluido Engine08. `G01`–`G09`: UX05. `L01`–`L10`: navegación histórica OFF. `U`:19 pruebas nuevas puras +4 de serialización existentes. Controles Core responsive/zoom/touch/AA, Saga01 y borradores complementan la regresión UX01–05; FULL completa se exige por clasificación real R3, sin modificar guards/workflows.

Evidencia en [evidence](evidence/): capturas reales de Core01/02/03 y Graph/Configuration/Dashboard a1536/1280/1024/768/390/320. Las vistas ON afirman exactamente tres botones de etapa en Studio, cero edición lateral y ubicación activa sin re-navegar. Graph mantiene una acción de edición canónica. `geometry.json` mide controles y sus contenedores, solapes entre controles, título/retorno, ausencia de barra redundante y overflow. `contrast.json` audita texto/controles con umbral AA, incluidos gradientes. Los PNG son del navegador de fixtures, no mockups ni producción.

`final.txt`, `regression.txt`, `unit.txt`, `resource-unit.txt`, `baseline.txt` y diagnósticos focales documentan resultados reales. `source-sha256.json` identifica archivos de código/test; `impact.json` y `static.txt` registran clasificación y sintaxis. Las ejecuciones FULL y required-gate del candidato se enlazan en el reporte terminal del PR, sin otro commit sólo para actualizar resultados externos.

## Aceptación UX06-01–42

PASS aquí refiere a las pruebas locales identificadas. AC36 exige además el reporte terminal de CI y estado del PR del mismo SHA.

|AC|Evidencia y contrato|Resultado|
|---|---|---|
|01|T07/W15: cuatro niveles; sin segunda barra|PASS|
|02|T01/T07: Core02 sin Administrar datos del Case|PASS|
|03|T01/T07: Core03 sin botonera superior redundante|PASS|
|04|T02/T06/T10: un retorno Graph/Dashboard/Config/Center|PASS|
|05|T07: retorno compacto, rectángulos y AA|PASS|
|06|T01:03→02 mismo form/Case|PASS|
|07|T01:02→01 misma identidad|PASS|
|08|T03/T04: salida protegida, draft/CSV explícitos|PASS|
|09|T04: overview→catálogo canónico y foco|PASS|
|10|T01 con fecha inválida, sin validar ni requests al retroceder|PASS|
|11|T04/W01/W06: gates y validación de avance|PASS|
|12|T07 y owners: CTA existentes, sin nuevo Continuar|PASS|
|13|T01/T07: aria-current y activo no-op|PASS|
|14|T01: misma identidad DOM03→02→01→02→03|PASS|
|15|T05/T07/T13/W04: deep link y refresh preservan paso/Case|PASS|
|16|T01/T03/T11/L03: Back/Forward, cancelación y gates cambiados|PASS|
|17|W02/T03: Graph→Core02 mismo Case sin runs|PASS|
|18|T01/T07/W02: Graph→Core03|PASS|
|19|G01–09: toolbar/panel/owners/historial UX05|PASS|
|20|T05/T12/W03: derivación y original sin cambios|PASS|
|21|T05/T12/W09: parent/preparationId/refresh/replay|PASS|
|22|T02/T05: Graph del Case original exacto|PASS|
|23|T06/T13/W08: Dashboard con Case/Node/Run exactos|PASS|
|24|T06/U:404, mismatch y origen incompleto sin latest|PASS|
|25|T06/T07: Config Anterior→Graph del mismo Case|PASS|
|26|W08/U: Dashboard actual→Config; histórico/readonly→Graph|PASS|
|27|T08/G05/L05: viewer/archivado readonly|PASS|
|28|W08 real: D1→aprobación→D2; respuesta perdida|PASS|
|29|G03/W05/W08: cierre/token/Center|PASS|
|30|T02/T03/T04/W14: no autosave ni pérdida silenciosa CSV|PASS|
|31|T09/G06/G09/W13/L07: scope y respuesta tardía|PASS|
|32|L01–10/W15: renderer y navegación OFF|PASS|
|33|T07/T14: seis anchos y zoom200, contención/solapes/overflow|PASS|
|34|T07/T10/T14/Core06: AA, foco, teclado, nombres|PASS|
|35|Diff: sólo frontend/tests/docs; sin backend/SQL/infra/guards|PASS|
|36|Único PR abierto, SHA/CI terminal y rollback|Ver cierre del PR|
|37|T06/T07/T08/W08: exactamente04/05/06 y sin CTA lateral|PASS|
|38|T07/T08/W08: tres vistas, reload, directos, retorno y roles|PASS|
|39|T01/G01/T07: un Editar Decision Case en Graph→Core03|PASS|
|40|T08/G05: viewer/archivado no obtienen mutaciones|PASS|
|41|T07 y PNG: sin edición, huecos, separador o tab stop residual|PASS|
|42|L01–10/W15 y rama legacy preservada|PASS|

## Hallazgos y correcciones focales

- Duplicación preexistente: header Core tenía regreso al Graph, gestión circular de datos y Cancelar; Cancelar ejecutaba `markSaved` y eliminaba draft. Se usa un solo retorno que conserva el guard/draft. Guardar real mantiene su contrato y retorno UX04.
- Rail preexistente: `showEdit:false` sólo cubría Graph. Se elimina esa rama del owner común ON y el CSS muerto. La edición desde Studio sigue en la toolbar Graph y en el acceso contextual Core del breadcrumb.
- Regresión focal UX06 detectada con campo inválido: focusout insertaba un error que desplazaba Anterior entre pointerdown/pointerup; el click acababa en footer. Traza real en diagnóstico. Se omite exclusivamente la validación de blur al dirigirse a Anterior; submit/avance conservan validación. Sin esperas adicionales.
- Carrera focal UX06: retorno Config pendiente navegaba después de que el usuario retrocediera localmente. Request scope cancelado al cambiar de etapa; T09 reproduce y verifica la corrección.
- Contraste preexistente: texto secundario de etapa activa Config4,40:1. Usar token secundario existente, sin relajar el umbral4,5.
- Selector de test dependía del número de etapa oculto en móvil. Se usa `data-journey-stage` con destino canónico; siguen las assertions exactas de tres controles y labels visibles.
- Fixture de Center utilizaba `active`, que no existe en su whitelist; corregido a `in_progress`, sin cambiar parser/producto.
- Dos arranques locales aislados (touch Core e histórico OFF) mostraron la pantalla genérica de boot, antes de montar navegación. No se reprodujeron al repetir focalmente, sin cambios de código ni de esperas; la traza de consola/red del histórico quedó vacía. Causa inicial no confirmada: no se etiqueta como defecto funcional ni como infraestructura demostrada. El cierre exige su pasada final y FULL del candidato.

- El fixture de roles combinaba una aprobación vigente y otro candidato de error activo; una tentativa directa de cierre fue rechazada por token cambiado. No se alteró el guard ni se agregó retry. El cohort archivado usa ahora un Case independiente close-ready y el flujo UI canónico; W08 y G03 mantienen las assertions de cierre. Se separan las cohortes de Dashboard fallido y Case archivado; no se simula archivado por SQL ni se omite la confirmación/token del cierre real.

- Recuperación heredada: los callbacks de reload409 y retry503 reconstruían Core con sólo caseId/modelId y perdían origen/Run/preparación. T13 lo reprodujo y ahora verifica ambos retornos exactos. Se preserva la ruta validada en ambos callbacks; modo OFF conserva su comportamiento. La CI43773832833 del SHA3efdec22 fue cancelada antes de terminar por ese hallazgo; el PR registra la nueva CI completa del candidato corregido.

- CI43776605265 pasó los 13 casos UX06 y falló únicamente Core04 al medir1690px a zoom200. El baseline intacto b9c9967 reproduce exactamente1690px con Chromium153.0.8010.12 y CPU4x. No es una regresión UX06. CSS zoom deja las media queries de viewport en1440px pero reduce el contenedor Core a424px: el rail216px comprimía el workspace a188px. Capturas anteriores de pruebas que figuraban PASS también medían1690px: la assertion podía leer el layout anterior al zoom. Se mantiene el límite1441 y se mide después de dos frames de render, sin sleeps ni retry. La corrección usa el ancho del contenedor Core para reflow de rail, tarjetas y footer; T14 comprueba los tres pasos ON, formulario/Case idénticos, contención, contraste y progreso legible. Core04 cubre OFF, touch y controles nativos. Los diagnósticos baseline/final conservan resultados fallidos y corregidos.

## Riesgos y límites

Revisión visual del propietario pendiente. Los cambios de navegación mantienen CSV sólo mientras el formulario siga montado; al salir se usa la confirmación vigente y no se promete restaurar un File local. Preparaciones durables y drafts conservan sus identidades; una etapa histórica que perdió el gate vuelve explícitamente a la etapa disponible, sin remount. Los destinos consultan autoridad del servidor, no colores/roles inferidos. El estado productivo y la revisión de rollback se verificarán únicamente en una futura activación autorizada. Historial SQL UX04 intacto y fuera de alcance. Cambios productivos: **NONE**.
