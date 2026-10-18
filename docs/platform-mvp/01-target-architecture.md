# Arquitectura objetivo · Dation Platform MVP v1

Estado: **diseño de Fase 0; no implementado**. Base auditada: `22f1187451429c8e98dfcb9874f89b974500cb35`.

## Decisiones

1. Conservar FastAPI, Cloud Run, PostgreSQL/Supabase, Storage privado y frontend HTML/CSS/ES modules. No segunda aplicación ni cambio de framework.
2. Encapsular Logistics y sus motores detrás de identidad, workspace y autorización. Mantener los contratos de resultados Assignment/Scheduling, histórico Dispatch, aprobaciones, fingerprints, exports e IA.
3. Reutilizar `decision_case_v2` y los nodos `logistics_assignment`, `logistics_scheduling`, `logistics_final_assignment`. D3 sigue bloqueado. Un Decision Case agrupa decisiones; cada decisión tiene versiones de runs. No convertir la plataforma en un listado primario de runs.
4. Separar contexto de seguridad por request y contexto operativo del DDA. Nunca guardar el workspace activo en una variable global Python ni inferirlo desde el dataset actualmente seleccionado en el navegador.
5. La plataforma nueva sigue el orden de fases del prompt. Ninguna tabla, login, navegación o primitive visual futura se introduce durante esta auditoría.

## Frontera de responsabilidades propuesta

```text
Supabase Auth → JWT validado por API
                 ↓
        RequestContext(user, workspace, role)
                 ↓
        Platform / DDA endpoints autorizados
                 ↓
        Services con workspace obligatorio
                 ↓
        REST/RPC + Storage privados
                 ↓
        Jobs durables → worker → runs + reconciliación
```

El worker usa identidad de servicio y contexto obtenido del job/run persistido, no una sesión humana guardada en memoria. Revalida referencias y políticas de cancelación cuando corresponda; el claim global es infraestructura interna, no una ruta disponible para usuarios.

Organización incremental propuesta:

| Área | Owner futuro | Responsabilidad |
|---|---|---|
| Identidad | `backend/app/platform/auth/` | JWT/JWKS, sesión inválida, identidad verificada |
| Tenancy | `backend/app/platform/tenancy/` | membresía activa, contexto, resolución de objetos |
| Miembros | `backend/app/platform/memberships/` | roles, invitaciones y desactivación, en Fase 8 |
| Auditoría | `backend/app/platform/audit/` | evento mínimo de creación en Fase 2; cobertura en Fase 10 |
| Dominio Logistics | servicios existentes | lógica actual con contexto obligatorio; sin mover motores por estética |
| Cliente Platform | `backend/app/static/js/platform/` | auth, cliente API, shell y páginas por fase |
| Runtime DDA | `backend/app/static/js/dispatch/` | Data Pack, config, ejecución, dashboards y restauración actuales |

Son rutas propuestas; se adaptarán a los owners existentes sin trasladar módulos masivamente.

## Modelo mínimo y fase de incorporación

| Entidad | Diseño y relaciones | Fase |
|---|---|---|
| `profiles` | PK/FK `auth.users.id`; nombre, apellido, display name, avatar opcional, timestamps. Email/password siguen siendo propiedad de Auth. | 2 |
| `workspaces` | UUID, nombre, país, zona horaria, idioma, moneda/unidades, estado, creador y timestamps. Datos operativos por workspace, sin reinterpretar runs históricos. | 2 |
| `workspace_members` | única `(workspace_id,user_id)`; `admin/operator/viewer`; estado `invited/active/disabled`; invitador y fechas. | 2; UI en 8 |
| `workspace_ddas` | única `(workspace_id,dda_id)`; estado y configuración administrada. Logistics habilitado; otros DDAs globalmente próximos. | 2; catálogo en 5 |
| Tablas operativas existentes | `workspace_id` y relaciones coherentes; conservar IDs y campos actuales. Alcance completo en [migración](02-data-migration-plan.md). | 2 |
| `audit_events` | contrato append-only workspace/actor/evento/objeto/metadata acotada. Creación de workspace atómica desde Fase 2; actividad completa en 10. | 2/10 |
| `decision_assignments` | única `(case_id,node_id)`; owner/approver miembros activos del mismo workspace. No duplicar estados de aprobación. | 8 |
| Data Pack | reutilizar pareja de datasets del Case para Logistics; un modelo genérico futuro deberá admitir otros tipos de inputs. Elegir tabla/derivado en Fase 6. | 6 |

No crear billing engine. Plan comercial y estado podrán añadirse como metadata ligera en Fase 9. Ningún futuro DDA obtiene motor o ruta operativa por aparecer en el registro.

## Resolución del workspace

Backend consulta membresías activas del usuario validado. Cero membresías lleva al setup; una se selecciona automáticamente. Para varias se usará una preferencia de workspace activa validada en servidor. Si falta o ya no es válida, devolver un error de selección explícito y resolver el caso asistidamente; nunca escoger la primera fila arbitraria ni construir un switcher en esta saga. Headers y query params sólo pueden sugerir un ID que pase nuevamente membership.

El alta deberá ser atómica: workspace + miembro admin + entitlement Logistics + evento de creación. No asignar todos los datos legacy a la primera cuenta que se registre; el administrador de migración vincula explícitamente al custodio autorizado.

## APIs y cliente

Conservar rutas existentes durante la transición y añadir namespace coherente `/api/platform/*` para catálogo, Data Hub y Decision Center. `/api/me` y workspace pueden agrupar contexto. Toda ruta privada debe pasar por el mismo contexto, incluidas las legacy; no dejar un bypass por conservar compatibilidad.

Centralizar token, errores JSON, refresh y tratamiento de 401/403 en un cliente. Paginación estable por fecha + ID y límites en todas las listas; summaries sin `result_json` completo cuando no sea necesario. Política de objetos fuera de workspace: 404 uniforme; permisos insuficientes sobre objetos propios: 403.

El modelo frontend separa `session`, `profile`, `workspace`, `route`, datos Platform y runtime Logistics. Se conserva `createScope`/dispose, abort al navegar y protección de respuestas obsoletas. Logout/expiración/cambio de identidad invalidan caches y drafts asociados al usuario/workspace; sessionStorage no concede permisos.

## Shell futuro

El Inicio actual es un catálogo DDA; no es todavía Workspace Home. La nueva Home será actividad/atención/continuación; el catálogo mantendrá su diseño como página propia. DDA Overview, Data, Decision Map, config y dashboards siguen dentro del shell único, con navegación contextual y breadcrumbs, sin sidebar duplicado.

Las URLs actuales por query conservan compatibilidad mientras se añaden rutas declarativas e History API. Antes de introducir `/app/...`, añadir fallback FastAPI para reload y pruebas de atrás/adelante/deep-link. Plan detallado: [frontend](06-frontend-shell-audit.md).

## Límites y siguientes gates

Fase 1 incorpora únicamente foundation visual, con [alcance y aceptación precisos](04-design-system.md). Fase 2 es un gate de seguridad completo: JWT, membership, todos los accesos/RPC/Storage, migración y dos workspaces aislados. No habilitar empresas distintas antes de ese gate; completar una página de login por sí sola no lo cumple.
