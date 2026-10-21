# V2 · Fase 5 · Integración transversal

Base: main `a8dfdb94289df0eadaef0ff1a6976f67fb7c4d52`, Home V2 publicada en PR90/91. Fuente funcional: Fase 5 del MASTER_PLAN_DATION_V2 y CAMBIOS_TRANSVERSALES. Se conservan los heroes, composición y portfolios de Home, Decision Center y Data Hub. La evidencia de CI, activación y revisiones productivas se registra en el PR y en `/workspace/dation-audit/platform-v2-phase5/ENTREGA.md`; este documento describe el contrato, no sustituye la comprobación runtime.

## Responsabilidades y política de casos

Se reutilizan las fuentes persistentes de Foundation: `member_responsibilities`, `workflow_stage_assignments` para Data y `decision_assignments` para D1/D2. No se crea un nodo decisional para Data ni otra copia de owners en JSON.

`decision_cases.workflow_policy_version` conserva 0 para los casos existentes y fija 1 para cada inserción nueva. Es inmutable, incluso si un cliente intenta enviar 0; los campos dentro de `state_json` no deciden la política. No se backfillean responsables ni actores, ni se invalidan aprobaciones históricas.

Los casos nuevos requieren:

- Data Owner o Data Steward activo y con permisos operativos para continuar desde Datos.
- Decision Owner elegible de la decisión correspondiente para ejecutar D1 o D2.
- Approver elegible asignado para aprobar cada decisión.

Una persona puede reunir varias responsabilidades. Access Role sigue controlando permisos; una responsabilidad nunca concede escritura a Viewer ni limita la visibilidad de páginas. Admin conserva la asignación y su override de aprobación auditado. Operator puede ejecutar según el contrato técnico actual; el responsable asignado y el actor real continúan siendo identidades distintas.

Las acciones vuelven a comprobar membership, email confirmado, workspace, Access Role y responsabilidades canónicas en SQL, bajo el mismo lock de workspace que las asignaciones y cambios de equipo. Los replays de una intención ya admitida y de una aprobación ya persistida conservan su resultado, autor y fecha. No se reejecutan cálculos ni se duplican eventos por navegar o reintentar una respuesta perdida.

## SQL y activación

Migración aditiva `20261021010000_platform_workflow_gates.sql`, transaccional, con límites de bloqueo y ejecución. Añade la política del Case y un switch privado `platform_release.workflow_gates_enabled`, inicialmente desactivado. La publicación lo activa después de comprobar la API, worker y assets de la fuente revisada. Desactivarlo permite revertir la aplicación sin borrar responsabilidades, evidencia ni cambiar la política inmutable de los casos.

Se añaden dos RPC de servicio: `platform_validate_data_stage` y `platform_update_member_foundation`. Los helpers privados no son ejecutables por anon, authenticated ni service_role; se invocan dentro de operaciones autorizadas. Se preservan RLS, grants existentes, CAS, last Admin, cola durable, linaje, outbox y reconciliación. Las funciones existentes se evolucionan con comprobaciones de su definición anterior; una instalación incierta se inspecciona antes de considerar cualquier reintento.

La admisión verifica Data y owner después de reconocer replays. Approval verifica el Approver después de reconocer una aprobación idéntica y conserva la política del aprobador asignado/override Admin. Los errores de requisitos faltantes usan mensajes humanos 409 explícitamente permitidos, sin revelar errores internos ni reintentarlos como contención. El header tipado `X-Dation-Workflow-Gate` distingue estos rechazos definitivos de las respuestas inciertas: vuelve a configuración con el Case y criterios conservados, sin consultar una corrida nunca admitida. Un error de red conserva la recuperación existente por run ID.

La responsabilidad se valida al cambiar cada persona. Una asignación histórica que perdió elegibilidad puede conservarse al editar el otro campo; esto no satisface los gates. La ruta legacy no permite reinstalar a una persona ineligible con una petición repetida.

## UI compartida por etapa

Un único selector sirve Datos, las dos configuraciones y los dashboards. Consulta candidatos por responsabilidad antes de paginar (25), ofrece búsqueda y explica la ausencia de personas elegibles. Admin puede ir a Equipo para corregir responsabilidades. Conflictos CAS requieren actualizar la etapa antes de guardar; respuestas canceladas o de una vista anterior no reconstruyen el formulario.

En Datos, validar o reemplazar archivos no registra automáticamente casos intermedios. Abrir la selección de responsable registra el Case del Data Pack validado; la asignación se guarda mediante el RPC existente. Operator dispone de registro explícito para que Admin asigne desde Decision Center y puede actualizar la responsabilidad sin obtener permisos de asignación. Cambiar el Data Pack o salir de la etapa cancela la representación de respuestas anteriores; las respuestas se vinculan también a la firma de inputs.

La barra de Datos explica por qué no permite continuar. Configuración muestra el responsable en la revisión y mantiene bloqueada la ejecución mientras falta un requisito. Dashboard muestra el aprobador asignado y el motivo accesible del bloqueo. La lectura de casos legacy continúa funcionando con asignaciones nulas. Los mapas con historial y la consulta de Viewer siguen disponibles si una persona asignada perdió elegibilidad; los gates no se convierten en permisos de página. Viewer no obtiene ejecución aunque todas las responsabilidades estén cubiertas.

Equipo edita Access Role y múltiples responsabilidades en una única transacción CAS. Conserva la protección del último Admin y permite una auto-democión válida cuando permanece otro administrador. El contrato de un único `business_role` sigue disponible para clientes anteriores; las peticiones deben indicar explícitamente cuál contrato utilizan.

## Contexto, navegación y handoff

El context switcher compartido de Map, Config y Dashboard muestra Case actual, progreso y hasta ocho casos recientes del mismo DDA. Abrirlo no recarga la vista. Tiene controles nativos de teclado, Escape y restauración de foco. Cambiar de Case abre su Map y descarta run/nodo de la URL anterior; abrir el actual en Decision Center conserva `center_case_id` y su drawer. El selector global de historial existente permanece disponible para sus consumidores; el dropdown nuevo no carga todas sus páginas.

Map, Center, Home, el rail de dashboards y la continuación reutilizan la resolución canónica. Una aprobación vigente gana frente a una candidata posterior; la candidata conserva su enlace explícito. D1 y D2 con corrida abren directamente su dashboard; un nodo disponible sin corrida abre configuración. Stale no se representa como aprobación vigente y D3 continúa sin motor ni navegación ficticia.

La selección usa borde teal y `aria-current`; aprobación conserva un marcador/texto verde sobre superficie neutral, y revisión su estado amber. No se cambia el estado al seleccionar un nodo.

Después de aprobar se vuelve a representar el mismo dashboard, con confirmación y acciones intencionales. D1 ofrece **Continuar con Planificación**, resolviendo nuevamente si corresponde configuración o una corrida existente. D2 explica que la etapa siguiente todavía no está disponible y ofrece Map/Case. Se conservan Back, Forward, reload, filtros y contexto de las superficies globales.

## Trazabilidad y compatibilidad

La admisión captura en el evento inmutable `run.queued` los IDs y versiones de los responsables de datos/decisión vigentes en ese momento. Cambiar posteriormente la asignación no reescribe ese registro. El actor de la solicitud sigue siendo `created_by_user_id`; los eventos de worker siguen siendo del sistema. Approval conserva por separado aprobador asignado, actor real, timestamp y override. La proyección de actividad añade únicamente los UUID/timestamps permitidos; no incorpora perfiles completos, archivos ni credenciales.

Home, Center y Data Hub conservan sus layouts y sus consumidores existentes. Se mantienen Free universal, Auth/tenancy, permisos técnicos, cálculo D1/D2, configuraciones ejecutadas, resultados, fingerprints, historial, demo dentro del DDA, descarga protegida y recuperación de uploads.

## Equipo y recuperación de acceso

Equipo mantiene una única entrada principal **Invitar**. El vacío ofrece contexto sin duplicar el botón; el enlace de registro queda dentro de ese mismo modal. Invitaciones conservan email, Access Role, responsabilidad inicial, vencimiento y aceptación. El copy aclara que esta acción no envía correo.

Recovery finaliza en `/login?recovery=sent`, con confirmación genérica que no revela si existe la cuenta. Se mantienen PKCE, callback y controles de origen. Guardar contraseña termina en `/login?password=updated`, limpia las cookies de este navegador e intenta revocar su sesión local. Un fallo de limpieza del proveedor no transforma una contraseña ya persistida en un supuesto fallo de guardado. Los mensajes de confirmación no se saltan por la detección automática de una sesión previa.

## Validación y límites de la publicación

El gate incluye regresión Python/Node, Chromium sintético, SQL histórico y E2E sobre PostgreSQL/PostgREST/API/worker/Chromium reales. Se verifican gates independientes, pérdida de roles, candidatos, CAS, aislamiento, Viewer, actor vs responsable, replay, legacy, switcher, navegación oficial/candidata, handoff, Equipo, Auth y reflow/teclado.

Antes del SQL productivo se captura y restaura un backup de aplicación en PostgreSQL aislado, conservando la política legacy y verificando los archivos originales. La comparación productiva permite únicamente las columnas, funciones, constraint y trigger declarados, más la activación privada; los valores de negocio y journals anteriores deben conservarse. No se crean fixtures, cuentas, invitaciones, correos ni solvers en producción ni se suplanta una sesión personal. La restauración de aplicación no incluye contraseñas de Auth.

La siguiente fase sigue siendo Fase 6, Golden E2E + regresión del roadmap. No se inicia automáticamente por completar los checks de publicación de esta fase.
