# Fase 7 · Decision Center

`Decision Center` en `/app/decisions` es la memoria de casos del workspace. Reemplaza el acceso provisional al historial. Su primer nivel es el Decision Case; decisiones y corridas quedan dentro del detalle. No crea otro motor ni cambia resultados, aprobaciones o fingerprints.

## Biblioteca

Tabla con caso, DDA, paso actual, progreso, responsable, estado y última actividad. Búsqueda literal por UUID, ID visible o etiqueta; filtros Todos, En progreso, En revisión, Completados y Archivados, más selector DDA. Todos omite archivados. Paginación SQL de 25 filas, máximo 50, con conteo real; no descarga el historial completo al navegador.

La etiqueta es opcional, de hasta 120 caracteres. Sin etiqueta se muestra el ID `DC-<primeros 8 caracteres del UUID>`, como en el mapa actual; el UUID completo permanece secundario y también se puede buscar. La etiqueta no sustituye identidad ni modifica el Data Pack. Home prioriza la etiqueta del caso y conserva el nombre del dataset como fallback. Editar/archivar/restaurar exige rol de escritura y el `updated_at` observado: un conflicto responde 409 y ofrece actualizar, sin repetir la mutación automáticamente.

## Estado y evidencia

Archivado explícito domina. Un caso está Completado cuando D1 y D2 tienen aprobaciones vigentes, D2 depende de la aprobación actual de D1 y no hay una nueva corrida candidata, en ejecución o fallida pendiente en esos nodos. En otro caso queda En progreso. El tercer nodo no cuenta en el denominador del MVP y se muestra Próximamente, sin acción ejecutable. El antiguo campo `status=completed` por sí solo no constituye evidencia de finalización.

En revisión es una condición separada: última candidata completada, sin aprobar ni reemplazar y con dependencia vigente. No se confunde con el estado de ciclo de vida del caso. Una versión nueva puede requerir revisión mientras la aprobación anterior sigue vigente. Si cambia D1, la aprobación D2 anterior se conserva como evidencia y se presenta desactualizada. Los contadores incluyen todas las corridas, incluso aprobaciones antiguas fuera de la página.

La proyección reutiliza `_state_with_history`, los snapshots de historial y la selección de continuación de Home. Una caché histórica malformada se reconstruye sólo en memoria desde ese historial; GET no repara filas. La UI usa la metadata de nodos del Decision Map en un resumen compacto, sin duplicar su pantalla operativa.

## Detalle y navegación

Header con ID, etiqueta, DDA y estado; Continuar, nombre y archivo/restauración según permisos. Contexto de Data Pack con Órdenes, Flota, validación registrada, creador y fecha; Ver datos abre el par derivado en Data Hub.

Cada nodo muestra responsable, aprobador asignado, última corrida, aprobación, autor y fecha de aprobación, y conteo. El historial de corridas se carga sólo al abrir su disclosure, pagina en servidor y conserva selección/página en la URL. Incluye creador, fecha, estado de ejecución, duración, objetivo y aprobación. Motor, fingerprints y UUID quedan en un detalle técnico secundario. No se entregan `result_json` ni configuraciones completas en esta proyección.

Una aprobación D1 abre ese dashboard exacto; D2 en revisión abre la candidata actual; D2 disponible va directamente a configuración D2. Las acciones explícitas distinguen dashboard aprobado y último dashboard cuando son versiones distintas. El owner existente de History API conserva back/forward, recarga y cancelación, y elimina contexto de biblioteca al entrar al DDA. Un enlace malformado ofrece recuperación dentro del centro global. Archivar conserva datos, historial y aprobaciones; no cancela trabajos aceptados. Los dashboards históricos siguen consultables con permiso del DDA; continuar un caso archivado exige restaurarlo.

## Identidad y permisos

La biblioteca y sus metadatos funcionan sin Logística habilitada. Abrir su runtime mantiene ese grant; viewer puede consultar evidencia, no editar ni entrar a configurar desde el centro. Actor/workspace se resuelven por JWT y membresía activa. Las nuevas RPC sólo admiten service_role y revalidan actor/membresía en SQL. No se amplían permisos de REST, Storage, RLS ni funciones anteriores.

Casos y corridas nuevas registran `created_by_user_id` de la autoridad del servidor: el repositorio lo inyecta en INSERT directo y el trigger toma el actor verificado del dispatcher en admisiones de corridas. La autoría es inmutable. No se rellenan autores de datos anteriores ni se los atribuye al administrador actual. Aprobaciones conocidas muestran su actor real; `shared_workspace:dation` se presenta como workspace compartido histórico.

Asignación de responsables y aprobadores pertenece a Fase 8. Aquí sus campos muestran Sin asignar; ser creador, administrador o aprobador histórico no asigna una responsabilidad ficticia.

## Validación y publicación

Pruebas con PostgreSQL 17/PostgREST/Auth/Storage/API/worker reales verifican aislamiento A/B, roles, grant deshabilitado, RPC directa denegada, etiquetas, conflictos, archivo/restauración, autoría, desconocimiento histórico, caché malformada sin reparación, linaje D1/D2, contadores y pureza de GET. Chromium autenticado prueba configuración D2 disponible, dashboard aprobado D1, candidata D2, historial/recarga, Data Hub y nombre/archivo, con ocho capturas responsive. Pruebas sintéticas cubren errores/reintento, filtros, XSS, conflictos, viewer y recuperación de URL. Los tests de recurso comprueban separación entre URL de centro, datos y runtime.

Migración aditiva `20261018130000_platform_decision_center.sql`: tres columnas nullable sin backfill, dos triggers y seis funciones nuevas, más la proyección de etiqueta de Home sin cambiar su contrato ni permisos. Backup/restauración de negocio y bytes en PG propio antes de aplicar. El kit de esta publicación verifica journals privados vacíos; un backup futuro con operaciones pendientes requiere capturarlas y resolver el alcance de sus objetos, sin limpiar producción como QA. No se afirma restauración de cuentas Auth.

Exigir CI del SHA exacto antes de aplicar una sola vez; comparar hashes normalizados sin las columnas nuevas y catálogo/ACL/policies/triggers anteriores, exceptuando la definición revisada de Home; su ACL debe conservarse. Admissions permanece OPEN. Desplegar misma imagen en API y worker, comprobar build, tráfico, assets, salud y protección. No ejecutar DDL en startup ni repetir freeze/apply/activación de identidad. No crear usuarios, membresías ni fixtures productivos. Commit/checks/revisiones finales se registran en el PR y entrega. La prueba manual completa del usuario sigue reservada para terminar todas las fases. Siguiente: Fase 8, Equipo y colaboración.
