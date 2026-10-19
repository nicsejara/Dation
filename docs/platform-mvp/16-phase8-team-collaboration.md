# Fase 8 · Equipo, colaboración y responsables

Equipo (`/app/team`) reemplaza el placeholder con miembros, email, rol de acceso, responsabilidad, estado y acciones. Los tres roles son Admin, Operator y Viewer. Una responsabilidad primaria opcional —Data Owner, Data Steward, Decision Owner o Approver— describe la función y no concede permisos adicionales. La prueba manual del usuario sigue prevista para terminar todas las fases.

## Invitaciones y acceso

Sólo Admin invita, revoca y edita membresías. Una invitación queda pendiente durante siete días; email normalizado, rol y responsabilidad viven en SQL. Esta versión no envía emails: la pantalla lo informa y permite compartir el enlace de registro. Al registrarse y confirmar ese mismo email, la persona ve la invitación en Workspace Setup; quienes ya tienen un workspace la ven en Equipo. Aceptar es una acción explícita y selecciona el workspace invitado. No hay asociación por un email enviado por el cliente, primer signup ni conocimiento del ID de invitación.

La aceptación valida la identidad confirmada directamente en Auth, el email actual, vencimiento, revocación, workspace activo y que quien invitó siga siendo Admin activo. Crea membresía, selecciona workspace, consume la invitación y registra auditoría en una transacción. Repetir conserva la membresía; nunca reactiva a alguien deshabilitado. Para una membresía existente se utiliza la administración de miembros, sin una invitación que la reemplace. El propietario heredado autorizado conserva su flujo anterior; no se crean cuentas ni contraseñas en la migración.

Todos los miembros activos consultan su equipo. Sólo Admin ve las invitaciones pendientes de ese equipo. Las invitaciones recibidas se consultan con sesión propia, sin exigir membresía previa, bajo `/auth/*`, cookies HttpOnly, CSRF y validación de identidad confirmada. No se expone un token de invitación: el ID no autoriza sin la identidad destinataria. La página usa texto DOM seguro, búsqueda literal y páginas acotadas; no muestra actividad inferida.

Cambiar rol, responsabilidad o estado exige la versión leída. No se elimina al miembro ni su atribución histórica. Siempre debe quedar al menos un administrador activo con email confirmado. Un lock por workspace serializa cambios de acceso, aceptación, asignaciones y aprobación; dos administradores no pueden deshabilitarse mutuamente dejando el workspace sin administración. Una escritura fallida no se reenvía automáticamente.

## Responsables y aprobación

`decision_assignments` conserva una fila por caso/nodo, con owner y approver opcionales, timestamps y FK compuestas hacia el caso y las membresías del mismo workspace. Admin asigna desde el detalle del Decision Center, también antes de que D2 esté disponible. Sólo personas activas y confirmadas con rol Admin u Operator pueden recibir nuevas asignaciones. No se infieren responsables del creador o de las aprobaciones anteriores; no hay backfill.

El owner coordina el trabajo; el rol sigue gobernando los permisos de ejecución. Un approver asignado limita la aprobación a esa persona y a Admin. Si no hay approver, se mantiene la aprobación de Admin/Operator. Un cambio de responsabilidad de negocio no altera esta regla. Deshabilitar o convertir a Viewer a un aprobador conserva la asignación visible; no abre la aprobación a todos. Admin debe reasignar o intervenir. El tercer nodo sigue sin motor de ejecución.

El dashboard hidrata la política actual y oculta el CTA para un Operator no asignado. SQL vuelve a comprobar identidad, membresía, rol y asignación bajo lock; la UI no es la frontera de seguridad. Admin puede intervenir y la auditoría registra `admin_override` y el aprobador asignado. Se conservan validaciones de corrida completada, caso/nodo, supersesión y aprobación upstream vigente. Un caso archivado requiere restauración para aprobar.

Se reutilizan `approved_by`, `approved_by_user_id`, `approved_at`, el run aprobado y `decision_approval_events`. No se agrega un segundo estado de aprobación. Un retry conserva actor, fecha y evento; la aprobación, supersesión, outbox y evento `decision.approved` se confirman juntos. El evento incluye el handoff a D2 y sus asignaciones preconfiguradas. La proyección de casos continúa siendo recuperable desde el historial persistido.

Al aprobar D1, D2 se habilita desde el linaje real y conserva sus responsables. Inicio muestra revisiones permitidas y el handoff D2 al owner asignado, con CTA hacia configuración. No muestra como propia la revisión reservada a otra persona; Admin conserva la intervención. Las consultas no reparan estado ni disparan trabajos. Se mantiene aprobación + nueva corrida; no se introduce un workflow de rechazo.

## Persistencia, validación y publicación

Migración aditiva `20261019100000_platform_collaboration.sql`: dos tablas con RLS, versión de membresía, responsabilidades válidas y RPC service-only. Sin escrituras directas de navegador; invitaciones privadas y asignaciones de lectura bajo RLS. Se revisan tres cuerpos existentes: aprobación privada, Home y Decision Center. Sus ACL y contratos anteriores se conservan; las proyecciones reciben campos adicionales. Motores, datasets, resultados y evidencias existentes no se recalculan.

`tests/e2e/test_collaboration.py` usa PostgreSQL/PostgREST, API, worker y navegador reales aislados. Cubre dos sesiones BFF, invitación/aceptación, acceso sin membresía, roles, responsabilidades, vencimiento/revocación/email confirmado, idempotencia, permisos y aislamiento, aprobador asignado, intervención Admin, atribución, handoff, CAS y carreras de último administrador/asignación. Ocho capturas 1440/1024/768/390 y auditoría de tema/overflow acompañan el recorrido. La fixture Auth no certifica entrega de correos reales.

Antes de publicar: CI del head exacto, backup privado y restauración en PG17 sobre todas las migraciones, comparación de negocio/identidad/permisos y migración aplicada una sola vez. Después: CI de main, Cloud Build API/worker, assets exactos y protección HTTP, worker Ready y hashes de archivos originales. La evidencia concreta y las revisiones se registran en el PR de esta fase. No se ejecuta QA con cuentas, invitaciones ni decisiones productivas.

Siguiente alcance: Fase 9, configuración del workspace y estructura de planes/facturación; no se inicia automáticamente.
