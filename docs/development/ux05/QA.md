# UX05 — evidencia y aceptación

Baseline: `7b31c500896543902576cc99e37840dbc2107d69` (PR119 integrado). Rama única `feat/saga-ux05-decision-graph-command-center`. G0 y decisiones: [DESIGN](DESIGN.md). Procedimiento no ejecutado: [ACTIVATION](ACTIVATION.md).

## Reproducción focal

Desde `backend/tests/browser`, con dependencias hashadas y Chromium/Docker del proyecto:

```sh
python -m unittest -v test_decision_graph_ux05 test_unified_decision_journey test_ultimate_navigation
```

Desde la raíz:

```sh
node backend/tests/test_graph_ux05.mjs
python3 scripts/ci/impact.py --base "$BASE_SHA" --head "$HEAD_SHA"
python3 scripts/ci/static_check.py --base "$BASE_SHA" --head "$HEAD_SHA"
```

Los fixtures rechazan contenedores ajenos y eliminan credenciales productivas. Los metadatos T5 explícitos comprueban estados/permisos/linaje/paginación con la API y PostgreSQL reales, **no certifican resultados matemáticos**. `JourneyEngineTests.test_08` ejecuta D1/D2 reales en el fixture local, publica resultados, aprueba (incluida respuesta perdida de D1), consulta Dashboard exacto desde historial y cierra el Case. No se ejecutan motores productivos.

## Evidencia verificable

Capturas reales y medidas en [evidence](evidence/). `geometry.json` registra límites de content/grafo/panel/rail y nodos/flechas, ausencia de solape y overflow en seis anchos; comprueba círculos verdaderos. `contrast.json` audita texto y controles con AA (4,5:1; texto grande3:1), incluidos gradientes. Los PNG provienen del navegador sobre fixtures locales, no son mockups ni capturas productivas. Los estados de referencia aprobada y stale/error se identifican como metadatos de prueba.

Logs locales: `focal.txt`, `ux04-regression.txt`, `status-unit.txt`, `static.txt`, `impact.json`. FAST/FULL/required-gate y el SHA terminal se registran en el único PR; el gate vigente exige FULL para R3. No se modifica el clasificador, los workflows ni sus assertions.

## Matriz UX05-01–40

`T1`–`T9`: métodos numerados de `CommandCenterTests`. `W01`–`W15`: pruebas UX04 existentes. `L01`–`L10`: navegación histórica OFF. `U`: 15 pruebas puras del adaptador. PASS de esta tabla refiere a evidencia local; el cierre de entrega exige además la CI terminal del mismo SHA en el PR.

| AC | Control | Evidencia | Resultado |
|---|---|---|---|
|01|Una barra global de cuatro niveles|T1 geometría; W15|PASS|
|02|Rail tres pasos y acciones sin duplicación|T1; W08; W15|PASS|
|03|Paridad Core216/20/max1560/breakpoint1199|variables compartidas; T1; W07/Core responsive|PASS|
|04|Canvas contenido, seis anchos|T1/T7 geometry.json|PASS|
|05|Panel sin invadir rail/sidebar/breadcrumb|T1/T7 rectángulos y PNG|PASS|
|06|D1→D2 y conector del upstream exacto|U; T8; W08 real|PASS|
|07|Futuro decorativo sin nodo/acción/API|T1; renderer whitelist; API intacta|PASS|
|08|Sin hero/cards/acciones Graph redundantes|T1; capturas default|PASS|
|09|Sólo tres badges principales|U; T1/T3/T8|PASS|
|10|READY pendiente configura si autorizado|T2/T7; W08|PASS|
|11|COMPLETED navega, no aprueba en panel|U; T8; W08|PASS|
|12|Aprobada sólo CURRENT y conector válido|U; T8; W08|PASS|
|13|D2 LOCKED explica y no ejecuta|T1/T2; U|PASS|
|14|D2 READY después de aprobar D1|T8; W08 real|PASS|
|15|NOT_APPLICABLE no bloquea cierre legítimo|T3; W05|PASS|
|16|Stale/error/histórico sin falsa aprobación|U; T4/T8|PASS|
|17|Viewer ve aprobación sin editar/correr|T5; L05|PASS|
|18|Selector real,25/página,Case/destino exactos|T4; L04|PASS|
|19|Sin runs, Core02 mismo Case/retorno|W02|PASS|
|20|Con runs, derivación/original inmutable|W03/W04|PASS|
|21|Editar Core03 exacto y permisos|W02/W04; T5|PASS|
|22|Resumen real readonly, sin paths/secretos|T1/T7/T9; explicit field allowlist|PASS|
|23|Cierre por can_close/token/confirmación/Center|T3; W05/W08; relectura/token en código|PASS|
|24|Archivado consulta, no muta|T3; L05|PASS|
|25|Pack vacío/no disponible no rompe toolbar|T1/T9; W01/W02/W09|PASS|
|26|Click/Enter/Space sin URL/ejecución|T1/T2/T6; requests observadas|PASS|
|27|Un panel y owner del nodo correcto|T2/T6|PASS|
|28|Tres secciones con IO/estado reales|T1/T7/T8; capturas|PASS|
|29|Selector canónico y viewer readonly|T2/T5; mismo componente|PASS|
|30|Guardar owner reconsulta y conserva selección|T2, incluida carrera cambio D2→D1|PASS|
|31|Configurar navega; ejecutar sólo en05|T2; W08|PASS|
|32|Dashboard con corrida exacta; no inventa ID|U; T4/T8; W08|PASS|
|33|Historial25/página y Dashboard exacto|T4; W08 con resultado real|PASS|
|34|Aprobaciones Dashboard regresan a Graph|W08 D1/D2 y respuesta perdida|PASS|
|35|X/Escape/foco/scroll desktop y móvil|T1/T6; foco nativo, panel no modal|PASS|
|36|Cancelación y respuestas tardías|T6/T9; L07/L08; scopes|PASS|
|37|UX01–04/contratos preservados|W01–15; Core/Saga01 focal; FULL en PR|PASS local|
|38|Responsive/AA/capturas reales|T1/T7/T8, geometry/contrast|PASS|
|39|Legacy OFF conserva renderer|L01–10; W15|PASS|
|40|Único PR abierto y SHA/CI final; no merge/deploy|Reporte terminal del PR|Ver PR|

## Fallos clasificados y correcciones focales

- Regresión UX05: estilo genérico de `.dispatch button` prevalecía sobre el círculo. Selectores específicos de UX05; medición de radio/aspecto y seis anchos, sin cambiar estilos globales.
- Regresión UX05: refresh de Owner D2 podía cerrar el panel D1 elegido mientras llegaba la respuesta. Preservar selección actual y draft canónico; abortar scopes anteriores. T2 verifica ambos owners y navegación sin ejecución.
- Geometría móvil: flecha decorativa futura usaba offset desktop fuera de content. Posición en flujo centrada en móvil; T1/T7 miden también flechas y círculos, no sólo el contenedor.
- Fixtures: error sin mensaje y actualización de identidad/resultado terminal rechazados correctamente por SQL. Corregir creación inicial de metadatos aislados (mensaje obligatorio y definición histórica explícita), sin relajar constraints ni mutar identidad/resultado. No se debilitan assertions.

## Riesgos residuales

La estética sigue el mockup dentro del ancho real de content; en móvil los nodos/panel se apilan y existe scroll vertical normal. La revisión visual del propietario sigue pendiente. No hay preview productivo en esta tarea. Un nodo funcional futuro no se activa automáticamente sin revisión de producto. La evidencia de tráfico/flags productivos sigue siendo la informada por el propietario; no se inventa una nueva verificación GCP/Supabase. La reconciliación histórica SQL UX04 queda separada y sin cambios. Producción modificada: **NONE**.
