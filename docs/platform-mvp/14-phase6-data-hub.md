# Fase 6 · Data Hub

La entrada «Datos» del sidebar abre `/app/data`, con título «Data Hub». Es la biblioteca del workspace, independiente de tener Logística habilitada. No construye ETL, otra aplicación ni un nuevo motor de carga.

## Biblioteca y detalles

Datasets: nombre y archivo canónico, tipo, registros, validación, autor conocido, creación, uso por casos/corridas y acciones. La búsqueda por nombre original/canónico/etiqueta es literal, no construye filtros SQL. Se pagina en servidor (25 por defecto, máximo 50) y permite Todos, Órdenes, Flota, Validados, Con problemas y Archivados. La biblioteca normal omite archivados; el filtro Archivados los recupera. La validación refleja el reporte persistido, sin confundir errores de una corrida con errores del CSV.

El detalle muestra identidad, tipo, tamaño, registros, fechas, autor, esquema, errores/avisos y Decision Cases que usan el dataset, incluidos archivados. Mensajes limitados a los primeros 50 con total explícito. La vista previa lee el archivo autorizado y pagina filas (25 por defecto, máximo 50); hasta 100 columnas y 500 caracteres por celda, con el límite visible. UTF-8 y separadores CSV existentes. Descargar conserva los bytes. El ID queda en un disclosure técnico con copia.

Las cargas nuevas registran `uploaded_by_user_id` desde la identidad del servidor. Su FK y un trigger protegen esa atribución; el cliente no selecciona autor. No se atribuyen los archivos anteriores al usuario actual: quedan «Sin registro» cuando falta evidencia. Los datos legacy siguen visibles con su tipo anterior y validación desconocida cuando corresponde, sin reinterpretarlos como Órdenes o Flota.

## Data Packs derivados

Se eligió la estrategia B del maestro: derivar el Data Pack del par inmutable `orders_dataset_id / fleet_dataset_id` de los Decision Cases actuales. La auditoría confirmó que ya existe esa identidad y sus FK de workspace. No se crea otra tabla de pares, no se duplican archivos y no se reescribe el historial.

Un par usado por varios casos aparece una sola vez, con etiqueta derivada de los nombres de sus datasets, ambos archivos, validación registrada, cantidad de casos y fecha del primer caso que usó el par. El detalle permite ver los datasets y los casos paginados. Logística es el único DDA compatible por formato; la compatibilidad operativa se comprueba en el runtime existente al preparar la decisión. Un pack con datos archivados no se reutiliza hasta restaurarlos.

Reutilizar vuelve al upload/Data Pack existente del DDA, seleccionando el dataset o ambos archivos, limpiando el borrador operativo anterior y conservando sus casos y evidencia. La acción no crea un Decision Case persistido: ese paso sigue siendo explícito en el mapa existente. Requiere Logística habilitada y rol con escritura. Las rutas y el owner de History API conservan selección, búsqueda, filtros y página, permiten recarga/atrás/adelante y quitan contexto DDA al entrar a la biblioteca.

## Carga y recuperación

«Cargar datos» usa `createDropCard`, contratos, plantillas, validadores y `store_input` existentes; el cliente multipart es compartido con el DDA. El selector declara Órdenes/Flota. La carga inválida muestra problemas sin guardar; el límite sigue siendo 10 MB. La deduplicación permanece por workspace/tipo/hash, sin cambiar la atribución original.

Para las cargas iniciadas desde Data Hub se registra una intención privada **antes** de escribir Storage. Si falla el INSERT, la intención comprueba bajo lock si la fila quedó confirmada antes de autorizar cualquier compensación. Una respuesta perdida conserva metadatos y bytes; el reintento deduplica. Si no hay fila, se bloquea un alta tardía y se intenta retirar el objeto. Si también falla esa limpieza, el objeto sigue identificado por la intención: «Cargas interrumpidas» permite descartarlo explícitamente. Las cargas de resultado incierto permanecen protegidas durante 15 minutos antes de ofrecer recuperación; una carga que ya tiene metadatos se conserva. La recuperación autoriza workspace/rol en DB antes de tocar bytes, es idempotente y bloquea un alta tardía de una carga descartada. Las rutas directas anteriores del DDA conservan su compensación existente; extenderles el journal es trabajo de hardening, no un cambio de contrato encubierto.

## Archivo y eliminación

Archivar es el retiro recomendado y reversible. No elimina archivo, casos, resultados ni referencias; la flota vigente exige elegir primero otra versión. Restaurar vuelve a habilitar el dataset en la biblioteca.

La eliminación definitiva exige rol de escritura, dataset archivado, no ser flota vigente y ausencia de referencias en las once tablas de negocio, incluidos JSON de evidencia, versiones, casos archivados y corridas terminales. Ante duda se conserva. Sólo el servidor ofrece esta acción tras consultar DB y vuelve a comprobarla en la operación.

Una intención privada persiste la identidad inmutable del objeto y marca el dataset como pendiente antes del DELETE de Storage. Los servicios anteriores omiten datasets pendientes. Triggers y locks de workspace impiden incorporarles referencias nuevas; los conflictos de row locks responden con un 409 reintentable sin esperar en un ciclo de deadlock. Se retira Storage y después se finaliza la fila; una interrupción conserva intención y estado recuperable. Repetir el DELETE termina la operación; un objeto ya ausente se admite como reintento. No hay eliminación masiva ni cascada de evidencia.

## Autorización y validación

Todas las rutas `/api/platform/data/*` usan JWT/membresía/contexto existentes. Viewer consulta y descarga, sin cargar, archivar, restaurar, reutilizar ni descartar archivos. La biblioteca funciona con el entitlement Logística deshabilitado; entrar a su runtime sigue requiriendo el grant. Las RPC `platform_data_hub`, `platform_dataset_delete` y `platform_dataset_upload` sólo permiten service_role y revalidan actor/workspace/rol; ningún ID, path, autor o workspace del cliente sustituye esa autoridad. La respuesta pública no incluye paths/buckets de Storage. Se preservan RLS y ACL anteriores, incluido `is_member`.

Se agregan pruebas reales de SQL/REST/Storage/API: dos workspaces, identidad de carga, búsqueda literal, paginación, packs derivados, lectura sin mutar casos, permisos con DDA deshabilitado, viewer, RPC directa denegada, bytes de preview/descarga, referencias pendientes, bloqueo concurrente y recuperación de fallos de metadatos+Storage. El recorrido Chromium autenticado completa carga/reutilización/descarga/eliminación y verifica XSS/responsive con stack real. La suite sintética cubre filtros, estados, historia, diálogo/teclado, archivo, reintento de eliminación y limpieza explícita de cargas interrumpidas. Datos históricos sin autor o con otro formato de reporte conservan su estado desconocido.

## Publicación

La copia privada previa conserva 94 registros de negocio y 6 objetos. Su restauración se verificó en PostgreSQL 17 aislado con todas las migraciones, FK validadas y comparación exacta de campos anteriores. No restaura cuentas ni contraseñas de Auth; los actores/workspaces mínimos de la prueba son identidades locales sintéticas.

Migración aditiva `20261018120000_platform_data_hub.sql`: dos columnas nullable sin backfill, dos journals privados, índices, triggers y funciones con permisos mínimos. No mueve objetos ni modifica campos previos de negocio. Capturar antes/después hashes normalizados sin las dos columnas nuevas, además de ACL/funciones previas; verificar definición y permisos exactos. Admissions permanece abierto. Aplicar sólo una vez, con preflight de ausencia y CI verde del SHA exacto; después desplegar API y worker y comprobar build, tráfico, assets y endpoints protegidos. No repetir migraciones de identidad ni freeze, y nunca ejecutar este DDL en startup.

Las operaciones de QA con escritura usan exclusivamente el sandbox; no se crean usuarios, membresías ni archivos productivos. La prueba manual completa del usuario queda para terminar todas las fases. Commit, checks, revisiones y resultados finales se registran en el PR/informe de entrega. Siguiente alcance: Fase 7, Decision Center; no se inicia automáticamente.
