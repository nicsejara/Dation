# Fase 11 · Onboarding, demo y recuperación

La guía «Bienvenido a Dation» aparece en Inicio. Comprueba workspace creado, exploración personal del catálogo, datos validados activos y primera ejecución completada. Los dos últimos pasos reflejan el workspace; la UI lo aclara y señala el origen demo cuando corresponde. No simula avances, corridas ni aprobaciones. Al completar el recorrido queda plegada y se puede volver a abrir.

## Progreso personal

`GET /api/platform/onboarding` no escribe. Dos RPC service-only revalidan membresía activa y email confirmado. La tabla privada `workspace_onboarding` sólo conserva workspace, usuario y fecha de exploración, con clave única, RLS y sin acceso directo para los roles de producto. `POST /api/platform/onboarding/explore` registra una visita real al catálogo o al overview de Logística y es idempotente. Viewer puede registrar ese avance personal, pero no preparar datos o ejecutar decisiones. La excepción HTTP sólo permite esa ruta exacta, sin abrir una excepción genérica de escritura.

El progreso persiste al recargar y volver a ingresar. Sin grant de Logística no se exponen avances operativos. Un fallo de la guía tiene reintento independiente y no impide leer los casos de Inicio. No se cargan datos al crear un workspace, abrir Inicio o visitar el catálogo.

## Pack controlado

«Usar datos de ejemplo» está disponible en la guía, Data Hub y el paso de carga de Logística. Explica qué guardará y conserva la flota predeterminada. `POST /api/platform/onboarding/demo` usa el mismo servicio que la ruta anterior `/api/datasets/load-sample`, con rol de escritura y grant revalidados.

`sample_data/onboarding-v1` contiene cuatro órdenes y dos vehículos ficticios con fechas fijas, versión y SHA-256 en un manifest. Se verifica antes de escribir. Este pack propio no se presenta como el Golden Pallets externo ni como una operación actual. Ambos motores, sus resultados y las aprobaciones usan el flujo normal: no hay resultados precalculados o aprobación automática. El ejemplo V3 anterior no ofrecía una programación temporal factible en todos los casos; se conserva su contenido histórico y se usa este pack pequeño para el primer recorrido.

La deduplicación sigue siendo por bytes/tipo/workspace y usa los journals de carga existentes. Repetir el clic o recuperar una respuesta perdida reutiliza los archivos confirmados. Un archivo idéntico existente conserva ID, nombre, autor, origen y estado; no se vuelve a etiquetar como demo. Los nuevos llevan `is_sample=true`, etiquetas y nombres explícitos. Los archivados o en eliminación requieren revisión en Data Hub, sin restauración automática. Una carga parcial se retoma; abandonar la pantalla no elimina archivos confirmados. La UI cancela su solicitud y no navega después de abandonar la vista.

No hay un segundo motor demo ni un workspace compartido de ejemplos. Cada workspace posee sus recursos. Preparar ejemplos no crea casos, ejecuciones o aprobaciones automáticamente; continuar usa el flujo vigente de Data Pack y caso.

## Identificación del origen

Se reutiliza `datasets.is_sample` como marca equivalente a `is_demo`, sin añadir columnas o reinterpretar resultados guardados. Una pareja/caso es demo si cualquiera de sus entradas lo es. Las proyecciones de Data Hub, Decision Center, Home y actividad incorporan ese origen y la UI lo etiqueta. El contexto de carga/mapa/configuración/dashboard también muestra un aviso demo; desaparece al cambiar a entradas propias o salir del DDA. La evidencia y sus métricas permanecen intactas.

La migración añade una tabla privada y dos funciones públicas. Modifica sólo cuatro proyecciones de lectura para añadir la marca: `hub_dataset`, `center_bundle`, `platform_home` y `platform_activity`. Conserva sus decisiones de estado, filtros, permisos, cursores y cálculos. No modifica valores anteriores, flags históricos, archivos, RLS existentes, funciones de mutación o motores. La preservación y los cambios revisados se comprueban antes/después de publicar.

## Vacíos y recuperación

Inicio ofrece guía y siguientes acciones; Decision Center orienta a preparar un Data Pack y abrir Logística; Data Hub ofrece cargar archivos propios o el ejemplo; Equipo con un único Admin y sin invitaciones explica cómo sumar personas. Búsquedas sin resultados conservan limpiar filtros y no se presentan como un workspace vacío.

La política compartida de recuperación distingue acceso inválido, sesión vencida, permisos, desconexión, timeout, validación, carga, ejecución fallida, origen ausente y decisión desactualizada. Los detalles técnicos quedan secundarios. Los mensajes de timeout no afirman que una operación haya fallado. Ninguna escritura se repite automáticamente. Una sesión vencida lleva a ingresar nuevamente; un error del motor conserva evidencia y permite reconfigurar; Scheduling sin origen o desactualizado dirige a revisar Assignment. Los reportes de validación existentes y sus filas/errores se conservan.

## Verificación y límites

Los E2E nuevos usan PostgreSQL 17, PostgREST, Storage, BFF, API y worker reales en un entorno aislado. Comprueban progreso personal/pureza de GET, roles, aislamiento, idempotencia, concurrencia, archivos propios idénticos, flota vigente, archivos archivados, ambos motores y la identificación demo. El recorrido de navegador incluye vacíos, recuperación de conexión, recarga y ocho estados a 1440/1024/768/390. Chromium comprueba Viewer y una respuesta demo tardía al salir. La prueba de integridad rechaza un pack alterado antes de cualquier carga.

La publicación exige CI del head exacto, backup/restauración y preservación de datos/archivos, seguido de build y CI de main. Se incluye el pack en la imagen Docker. No se crean cuentas, recursos demo ni fixtures productivos durante el release. La prueba personal del usuario sigue prevista para terminar todas las fases. Free universal se conserva.

Siguiente: Fase 12, hardening, seguridad, E2E y gate de release. No se inicia automáticamente.
