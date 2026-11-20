# J1.01 — 83 acceptance criteria

Evidence IDs and complete methods: [verification index](G6_TEST_MATRIX_REPORT.md). All tests use synthetic local resources. PR/CI criteria remain PENDING until their actual terminal result.

| ID | Criterion | Status | Evidence | Notes |
|---|---|---|---|---|
| J101-001 | Se utiliza la ruta y biblioteca existente models/index.mjs, sin duplicar páginas. | PASS | G0 / models/index.mjs | Verified by the referenced real test/source evidence. |
| J101-002 | Se identifica editor R6 real y se conserva todos sus subpasos. | PASS | G0 / R6 | Verified by the referenced real test/source evidence. |
| J101-003 | Se inspeccionan operaciones reales create/update/publish y permisos. | PASS | SQL | Verified by the referenced real test/source evidence. |
| J101-004 | El nuevo shell no se activa de forma productiva antes de J1.02. | PASS | B12 / U04 | Default-off real server capability; no productive activation. |
| J101-005 | Existe evidencia del baseline y comandos de pruebas reales. | PASS | G0 / SQL | Verified by the referenced real test/source evidence. |
| J101-006 | Hay adapter único que no mezcla Case draft y Model draft. | PASS | U01 / U02 | Verified by the referenced real test/source evidence. |
| J101-007 | El contrato de navegación diferencia Library Review y Case Pinned Review. | PASS | B02 / B10 | Verified by the referenced real test/source evidence. |
| J101-008 | No se simula estado de publicación en front sin confirmación backend. | PASS | B09 / U02 | Verified by the referenced real test/source evidence. |
| J101-009 | Workspace sin Models muestra empty state y CTA de crear si hay permiso. | PASS | B01 / B12 | Verified by the referenced real test/source evidence. |
| J101-010 | Workspace con dos Models muestra dos tarjetas de familias diferentes. | PASS | B02 | Verified by the referenced real test/source evidence. |
| J101-011 | Búsqueda envía filtro soportado y maneja búsqueda sin resultados. | PASS | B06 / B07 | Verified by the referenced real test/source evidence. |
| J101-012 | Paginación de 25/50+ elementos no duplica ni pierde modelos. | PASS | B07 | Verified by the referenced real test/source evidence. |
| J101-013 | GET con error muestra retry, no se interpreta como biblioteca vacía. | PASS | B04 | Verified by the referenced real test/source evidence. |
| J101-014 | Sin can_manage_models no aparece CTA mutante habilitado. | PASS | B05 | Verified by the referenced real test/source evidence. |
| J101-015 | Modelos archivados conservan lectura histórica permitida. | PASS | B07 | Verified by the referenced real test/source evidence. |
| J101-016 | Ningún CTA en biblioteca crea Case. | PASS | B01 / B02 | Verified by the referenced real test/source evidence. |
| J101-017 | Ninguna tarjeta marca de modo autoritativo una Model Version como elección del Case. | PASS | B02 / B05 | Verified by the referenced real test/source evidence. |
| J101-018 | Metadata visible de tarjeta proviene de respuesta real, sin campos inventados. | PASS | B06 / G0 | Verified by the referenced real test/source evidence. |
| J101-019 | Loading conserva geometría y evita salto de layout excesivo. | PASS | B06 / CSS min-block-size | Reserved grid height; final scene geometry verified at four widths. |
| J101-020 | Primer nuevo modelo recibe identidad propia y se crea exactamente una familia. | PASS | B02 / U01 | Verified by the referenced real test/source evidence. |
| J101-021 | Segundo nuevo modelo de la sesión no reutiliza ID de A. | PASS | B02 / U01 | Verified by the referenced real test/source evidence. |
| J101-022 | Nombres, cargas y costos de A no contaminan B. | PASS | B01 / B02 | Verified by the referenced real test/source evidence. |
| J101-023 | Guardar borrador A preserva A sin publicar ni crear Case. | PASS | B01 | Verified by the referenced real test/source evidence. |
| J101-024 | Borrador B es recuperable sin sobrescribir A. | PASS | B01 / B11 | Durable browser copies, authenticated scope; one lock per mounted copy. |
| J101-025 | Recarga de A recupera datos del draft correcto o informa que sólo era local. | PASS | B01 | Incomplete saves explicitly browser-local; logout intentionally clears private recovery. |
| J101-026 | El editor renderizado es el wizard R6 aprobado, no editor V1 degradado. | PASS | B06 / R6 | Verified by the referenced real test/source evidence. |
| J101-027 | Cinco confirmaciones internas sólo activan después de validación real. | PASS | B02 / R6 | Verified by the referenced real test/source evidence. |
| J101-028 | Cambiar un dato validado invalida únicamente confirmaciones dependientes. | PASS | R6 | Existing R6 confirmation dependencies unchanged and regressed. |
| J101-029 | Hasta dos tipos homogéneos y semántica alternativa se mantienen. | PASS | B02 / R6 | Verified by the referenced real test/source evidence. |
| J101-030 | Comprobación rígida volumétrica R6 y preview vigente siguen funcionando. | PASS | R6 / DOMAIN | Verified by the referenced real test/source evidence. |
| J101-031 | Iconos R6 de vacío/cargado/bulto individual permanecen correctos. | PASS | B06 / R6 | Verified by the referenced real test/source evidence. |
| J101-032 | Guardar explícitamente no publica automáticamente el modelo. | PASS | B01 / B08 | Verified by the referenced real test/source evidence. |
| J101-033 | Publicar explícitamente no crea Case ni Data Pack. | PASS | B02 | Verified by the referenced real test/source evidence. |
| J101-034 | Salir con cambios ofrece guardar/descartar/seguir y no borra sin aviso. | PASS | B03 / B06 | Verified by the referenced real test/source evidence. |
| J101-035 | Modelo A validado se publica como v1 con snapshot/hash real. | PASS | B02 | Verified by the referenced real test/source evidence. |
| J101-036 | Modelo A publica v2 sin mutar snapshot v1. | PASS | B02 / SQL | Verified by the referenced real test/source evidence. |
| J101-037 | A-v1 y B-v1 son modelos diferentes, no dos versiones de la misma familia. | PASS | B02 | Verified by the referenced real test/source evidence. |
| J101-038 | Library Review no hace POST/PUT/PATCH ni usa Case ficticio. | PASS | B04 / B10 | Verified by the referenced real test/source evidence. |
| J101-039 | Case C fijado A-v1 sigue mostrando A-v1 después de publicar A-v2. | PASS | B02 / B10 | Verified by the referenced real test/source evidence. |
| J101-040 | Historial lista versiones publicadas del modelo correcto. | PASS | B02 / B07 | Verified by the referenced real test/source evidence. |
| J101-041 | Modelos legacy V1 se visualizan sin adaptación mutante. | PASS | B04 / R6 | Legacy snapshots read without conversion; new R6 successors only if representable. |
| J101-042 | No se inventan fechas de publicación ni cantidad de Cases asociados. | PASS | B06 / G0 | Verified by the referenced real test/source evidence. |
| J101-043 | Retry publish con mismo intent no duplica version_id. | PASS | B09 / U02 / SQL | Verified by the referenced real test/source evidence. |
| J101-044 | Conflicto expected_revision conserva borrador local y no pisa server. | PASS | B08 / U02 | Verified by the referenced real test/source evidence. |
| J101-045 | Archivar modelo no elimina versiones ni Cases. | PASS | B07 / SQL | Verified by the referenced real test/source evidence. |
| J101-046 | Versión publicada jamás se edita in-place. | PASS | B02 / SQL | Verified by the referenced real test/source evidence. |
| J101-047 | El punto de entrada del nuevo Paso 01 es la biblioteca. | PASS | B12 / B06 | Preview entry point is the existing library route; legacy Core step order intentionally retained until J1.02. |
| J101-048 | Continuar abre Case sin autoseleccionar último Model publicado. | PASS | B02 | Continues the existing Core flow without candidate/last-published selection; no J1.02 selector. |
| J101-049 | Volver de Case draft abre biblioteca, no editor del último modelo. | PASS | B05 | Explicit Core library action opens library, not latest model editor; legacy internal step Back is preserved. |
| J101-050 | Volver al Case draft conserva nombre, descripción y elección provisional. | PASS | B05 | Existing Case draft identity/name and candidate remain in their own store. |
| J101-051 | Publicar B en biblioteca no reemplaza A seleccionada en Case draft. | PASS | B05 / U01 | Publishing B never writes Case state; independent return token preserves A candidate. |
| J101-052 | Abrir model_id válido lleva a la familia/versión correcta. | PASS | B02 / B10 | Verified by the referenced real test/source evidence. |
| J101-053 | ID inválido/ajeno muestra error controlado sin fallback mutante. | PASS | B04 / U01 / B05 | Verified by the referenced real test/source evidence. |
| J101-054 | Browser Back/Forward restaura navegación sin crear/guardar/publicar. | PASS | B03 / B07 | Verified by the referenced real test/source evidence. |
| J101-055 | Cambiar de Review a Edit exige acción explícita y permisos. | PASS | B05 / B08 | Verified by the referenced real test/source evidence. |
| J101-056 | Navegación conserva origen/returnTarget sin usarlo como autorización. | PASS | B05 / B10 / U01 | Verified by the referenced real test/source evidence. |
| J101-057 | Volver de Graph a pinned review conserva Case y run original. | PASS | B10 / R6 | Verified by the referenced real test/source evidence. |
| J101-058 | No hay bucles de router ni headers duplicados tras repetidos Back/Forward. | PASS | B03 / B07 / B10 | Verified by the referenced real test/source evidence. |
| J101-059 | Flujo de creación Case/Graph actual sigue disponible bajo flag legacy. | PASS | B12 / R6 / NAV | Default-off browser plus existing R6/legacy regression tests. |
| J101-060 | Biblioteca usa tokens reales y dark mode de Dation. | PASS | B06 | Verified by the referenced real test/source evidence. |
| J101-061 | Título/Hero no se distorsionan con regreso desde Case/Graph. | PASS | B10 / B06 | Verified by the referenced real test/source evidence. |
| J101-062 | Header informativo no dibuja marco turquesa espurio al enfocarse. | PASS | B10 | Verified by the referenced real test/source evidence. |
| J101-063 | Botones reales mantienen :focus-visible accesible. | PASS | B06 | Verified by the referenced real test/source evidence. |
| J101-064 | Cada vista tiene CTA primario inequívoco y permisos reales. | PASS | B05 / B06 | Verified by the referenced real test/source evidence. |
| J101-065 | Footer de biblioteca mantiene 4 zonas semánticas coherentes. | PASS | B06 | Verified by the referenced real test/source evidence. |
| J101-066 | Sin overflow, tarjetas 2-col y acciones alineadas. | PASS | B06 | Verified by the referenced real test/source evidence. |
| J101-067 | Sin overflow con rail real y tipografía legible. | PASS | B06 | Verified by the referenced real test/source evidence. |
| J101-068 | Tarjetas y toolbar adaptables sin truncar botones. | PASS | B06 | Verified by the referenced real test/source evidence. |
| J101-069 | Tarjetas 1-col, botones >=44px, sin scroll horizontal. | PASS | B06 | Verified by the referenced real test/source evidence. |
| J101-070 | No se confunde Confirmado/Publicado/Vinculado/Consulta. | PASS | B01 / B02 / B06 | Verified by the referenced real test/source evidence. |
| J101-071 | Estado busy/error, role y aria-live correctos; keyboard dialogs. | PASS | B03 / B04 / B06 | Verified by the referenced real test/source evidence. |
| J101-072 | Acceso a model_id de otro workspace es rechazado por backend. | PASS | B05 / SQL | Verified by the referenced real test/source evidence. |
| J101-073 | Intentos write sin permiso son rechazados aunque se fuerce el request. | PASS | B05 / SQL | Verified by the referenced real test/source evidence. |
| J101-074 | GET/Review no escriben y no alteran checks/hash publicados. | PASS | B04 / B07 / B10 | Verified by the referenced real test/source evidence. |
| J101-075 | Todos los Cases históricos mantienen version_id/Pack/Run/approval. | PASS | B02 / B10 / SQL | Synthetic historical fixtures compared; no claim of querying production data. |
| J101-076 | Regresiones R6 / Saga10 de dominio, D1, D2 continúan pasando. | PASS | R6 / DOMAIN | Verified by the referenced real test/source evidence. |
| J101-077 | Fallos/redirecciones no exponen información de otro workspace. | PASS | B05 / U01 | Verified by the referenced real test/source evidence. |
| J101-078 | Hay un PR J1.01 sin cambios no relacionados ni conflictos. | PENDING | PR checks | Await PR creation and conflict verification. |
| J101-079 | Cada AC presenta test/evidencia real o BLOCKED/FAIL honesto. | PASS | This matrix / verification index | Verified by the referenced real test/source evidence. |
| J101-080 | Checks reportados son los verdaderamente ejecutados y requeridos. | PENDING | GitHub FAST / FULL / required-gate | PENDING until exact candidate GitHub terminal required checks. |
| J101-081 | Existe ruta reversible con feature flag o equivalente real. | PASS | B12 / RELEASE_ROLLBACK.md | Verified by the referenced real test/source evidence. |
| J101-082 | Sin merge, despliegue, promoción, billing ni activación de tráfico. | PASS | Git diff / PR state | Verified by the referenced real test/source evidence. |
| J101-083 | Hay inventario de contratos/IDs y baseline para implementar J1.02. | PASS | HANDOFF_J102.md | Verified by the referenced real test/source evidence. |
