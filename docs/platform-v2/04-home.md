# V2 · Fase 4 · Home

Base: main `2fe2c42`, Fase 3 publicada en PR89. Fuente funcional: CAMBIOS_HOME.md y Fase 4 del MASTER_PLAN_DATION_V2. Se evoluciona la Home existente, sin sustituir Decision Center/Data Hub, motores, Auth, Team ni el catálogo. La integración transversal y sus gates siguen reservados a Fase 5.

## Producto y navegación

Hero con Workspace, saludo según su timezone y exactamente dos CTA: **Explorar catálogo de DDAs** e **Ir a Decision Center**. SVG decorativo local con conexiones y grid, sin librería nueva. Primary teal con texto oscuro usando tokens existentes; acciones secundarias conservan su jerarquía. No hay KPIs, catálogo embebido ni nueva fuente de estado.

El cuerpo conserva atención real (hasta cinco filas), hasta tres Cases recientes, accesos completos a catálogo/Center/Datos y los cinco últimos eventos humanos del Workspace. Se organiza en principal/rail a partir de 1200 px, columna en tablet y cards/acciones apiladas en móvil. Attention desaparece cuando no hay trabajo accionable; recientes y actividad mantienen vacíos compactos. Loading respeta la geometría de las secciones y los errores permiten reintentar sin perder shell ni hero.

Se retira `mountWelcome` y su consumo global: no stepper, checklist, card de primera decisión ni demo en Home. Las APIs de onboarding, progreso personal y demo se conservan para compatibilidad y para los consumidores reales de DDA/Center. La demo permanece dentro de Data de DDA Logística, con su autorización y protección contra respuestas tardías. El snapshot legacy `onboarding` sigue disponible en la API, pero Home ya no lo representa ni genera actividad por leerlo.

Todos los enlaces usan `resourceUrl`/`readResource`, `dationNavigate` y `DationDispatch`; Back/Forward y reload conservan su significado. Actividad abre Center con `center_case_id`; los accesos globales limpian contexto previo. No hay rutas paralelas ni `window.location` arbitrario.

## Contrato incremental sin SQL

Se reutiliza `platform_home` sin cambiar su definición ni sus privilegios. Mantiene límites, orden, aislamiento, asignaciones y visibilidad por Access Role/DDA. No hay migración, backfill ni escritura de datos productivos.

La proyección Python añade a cada Case reciente `resume`, `context` y `approval_current`; conserva los campos previos, incluido el ID de la candidata. `resume` usa el resolver compartido de Fase 1: aprobación vigente → candidata identificada → configuración disponible → mapa como fallback seguro. Así, **Continuar** abre el resultado oficial mientras **Revisar** abre la nueva corrida exacta. Se conservan Case, nodo y run. Un Scheduling stale no se presenta como aprobación vigente. La selección del trabajo actual no cambia la evidencia ni revoca aprobaciones.

Los labels de decisiones provienen del registro común. Completion se deriva de las dos aprobaciones con linaje vigente, no de un estado cacheado `completed`. Un cache histórico inválido se reconstruye sólo en memoria, sin repararlo en base de datos. Decision Center reutiliza la elección del nodo actual y conserva su propio resolver/contrato.

La actividad añade una presentación optativa `home`: timeline, iconos lineales del registro existente, fechas relativas con fecha absoluta en tooltip y sin códigos/detalles técnicos. Los demás consumidores, incluido el drawer de Center, conservan su presentación. El helper de fechas relativas no cambia cantidades ni timestamps guardados.

## Verificación y límites

Regresión Python/Node/Chromium, SQL histórico y E2E con PostgreSQL/PostgREST/API/worker reales. Pruebas específicas cubren prioridad de aprobación durante reemplazo, candidata explícita, handoff D2, cache inválido/obsoleto, aislamiento entre dos workspaces, Viewer, etiquetas seguras, límites de Cards/actividad, ausencia de onboarding global, demo DDA y cancelación, error/retry/BFCache, teclado, contraste y reflow desde 320 px. Capturas sintéticas y de stack real; no se crean cuentas/fixtures ni se ejecutan solvers en producción.

La publicación exige CI exacto de head/main, build del mismo árbol, API/worker listos, assets exactos y checks protegidos de sólo lectura. Se captura y restaura el backup de aplicación en PostgreSQL aislado y se verifican hashes de archivos originales. Una imagen tenant-aware anterior puede revertir esta fase sin DDL inverso ni pérdida de datos. La evidencia de publicación se registra en el PR y `/workspace/dation-audit/platform-v2-phase4/ENTREGA.md`; este documento no sustituye las comprobaciones runtime.

## Cierre de dependencias

Después de publicar Home, CI de main detectó GHSA-6q48-6c7w-9gw2 en el bundle CA de certifi2026.7.22. Se actualiza únicamente certifi a2026.10.19 en los locks runtime y de auditoría, con hashes de wheel/sdist obtenidos de PyPI oficial. Se mantienen los demás pins, validación TLS y checks de seguridad; no se ignora el aviso. La corrección complementa PR90 y vuelve a verificar instalación, auditorías, clientes HTTPS, suites y revisión productiva. No modifica el código de Home ni SQL.
