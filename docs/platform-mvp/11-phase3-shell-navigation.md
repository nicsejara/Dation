# Fase 3 · Shell, navegación y perfil

Implementación autorizada el 18 de octubre de 2026, después del gate de aislamiento de Fase 2. Mantiene HTML/CSS/JavaScript y el flujo existente de Logística.

El sidebar incorpora Inicio, Decision Data Assets, Decision Center, Datos, Equipo y Configuración. El footer muestra nombre y workspace, con menú accesible para perfil/configuración/logout. La navegación contextual de Logística permanece en el contenido y no crea un segundo sidebar completo. Un breadcrumb compacto muestra catálogo, DDA, caso y nodo cuando corresponde. El stack técnico deja el sidebar; el diagnóstico existente queda colapsado y reservado a administradores.

Rutas canónicas mediante History API:

| Vista | Ruta |
|---|---|
| Inicio | `/app` |
| Catálogo | `/app/ddas` |
| Decision Center | `/app/decisions` |
| Datos | `/app/data` |
| Equipo | `/app/team` |
| Settings | `/app/settings` |
| Perfil | `/app/profile` |
| Logística | `/app/ddas/logistics` |
| Data Pack / Map / Config / Dashboard | Subrutas `data`, `decisions`, `configure`, `dashboard` |
| Historial existente | `/app/history` |

Los enlaces anteriores `?view=...&case_id=...&node_id=...&run_id=...` siguen válidos. URLs de negocio conservan lineage; las globales omiten IDs de caso/corrida sin borrar el contexto guardado. Reload y atrás/adelante usan el mismo owner de navegación. Si vence la cookie de acceso, el refresh conserva el destino privado validado; no admite redirects a otros orígenes. Los eventos inline paran propagación para evitar dos entradas de historial por un click.

El shell espera Auth/profile/membership/workspace antes de cargar módulos y exponer contenido privado. El estado de navegador se limpia al cambiar cuenta/workspace; logout llega a otras pestañas. BFCache oculta y revalida sesión antes de restablecer contenido. No se duplican listeners al navegar. Fallos del módulo opcional de catálogo conservan el fallback utilizable, sin mostrar datos antes de resolver Auth.

Perfil permite cambiar nombre/apellido propios; email pertenece a Auth y rol/responsabilidad son readonly. La API rechaza campos extra y no puede cambiar permisos. Avatar usa iniciales; upload de avatares no se incorpora.

Inicio es una entrada mínima al workspace; la Home con atención/actividad se implementará en Fase 4. Decision Center y Datos enlazan capacidades existentes y describen su próxima ampliación. Equipo muestra el acceso actual y el alcance pendiente de colaboración. No se simulan invitaciones, analytics ni capacidades aún no construidas. Catálogo/entitlements, Data Hub y Decision Center completos mantienen sus fases respectivas.

Validación: recorrido con API real de login, rutas, un click/una entrada de historial, back/forward/reload, edición/persistencia de perfil, campos readonly, teclado del menú y logout; cuatro anchos (1440/1024/768/390). Además, regresiones de D1/D2, exportaciones, IA, lineage y revisión de contraste/AX/overflow. La inspección AX espera el paint del bootstrap autenticado; conserva las mismas aserciones de nombre/rol. Sidebar con scroll propio mantiene controles accesibles en alturas bajas. Resultados exactos de CI y publicación en el PR/estado.
