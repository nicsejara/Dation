# Dation Dark — Wireframe V1

**Fase 0: auditoría y especificación.** Fecha: 14 de octubre de 2026.

Fuente auditada: `main` en `bcda3e55f80ec216711e428c9451ac6ef8d86756`, contrastada con el remoto. Requisito: `Dation_PROMPT_PRO_Dark_Rebrand_GrowUp_EndToEnd.md`. Esta fase produce documentación; la interfaz actual continúa light. La implementación dark comienza en Fase 1, por petición del usuario.

Documentos complementarios: [design system](DATION_DESIGN_SYSTEM_V1.md) e [inventario y mapa de migración](DATION_COMPONENT_INVENTORY_V1.md).

## A. Diagnóstico

La navegación operativa ya pasa por `dispatch/workspace.mjs`, con recursos identificados por `view`, `case_id`, `node_id` y `run_id`. Assignment y Scheduling tienen renderers propios y comparten toolbar, configuración y componentes de contexto. Se reutilizará esta estructura.

El shell, cards, formularios y overlays son mayormente light; algunos heroes y la sidebar ya son dark. `tokens.css` sigue definiendo superficies blancas y `app.html` declara `color-scheme=light`. Hay estilos globales, específicos y otros inyectados al visitar pantallas. Una navegación SPA Scheduling → Assignment deja dos links de `assignment-config-v2.css` y dos de `decision-map-case-v2.css`, con IDs/querystrings diferentes.

Medidas del baseline a 1440 × 1000 px, con fixtures sintéticas:

| Pantalla | Alto de Hero actual | Tamaño de H1 |
|---|---:|---:|
| Inicio | 425 px | 58 px |
| Overview | 470 px | 57.6 px |
| Upload | 481 px | 48 px |
| Map | 426 px | 48 px |
| Assignment Config | 403 px | 48 px |
| Scheduling Config | 403 px | 48 px |

El footer de Config mide 97 px en desktop; el bloque final de Upload mide 140 px y convive con otro footer sticky mediante IntersectionObserver. El Overview conserva el bloque `.dda-landing__final`, aunque ya no contiene otro botón. Su retiro corresponde a Fase 2.

La toolbar permite dos menús abiertos y no los cierra al hacer click fuera. Se reprodujo con teclado en los cinco anchos; en móvil el menú Exportar también puede interceptar el click sobre Más. Escape y la apertura del drawer sí cierran menús. La corrección corresponde a Fase 5.

`analysis_depth` sigue en Config, sesión, drafts, payload, badge, detalles y comparative. Además participa en el conjunto de candidatos del motor Assignment: no debe tratarse como un dato exclusivamente visual. La estrategia de compatibilidad se especifica abajo; en Fase 0 no se retira ningún campo.

## B. Intención y estructura común

La jerarquía será: shell → contexto de página → tarea → evidencia → acción. La densidad operativa reemplaza los heroes grandes; los estados conservan icono, etiqueta y explicación.

```text
SIDEBAR       TOPBAR / BREADCRUMB
              JOURNEY NAV, cuando corresponda
              PAGE HERO compacto
              CONTEXTO de caso, cuando corresponda
              CONTENIDO de la tarea
              WORKFLOW ACTION BAR en Upload y Config
```

El Dashboard usa su toolbar superior y conserva la ocultación actual del workspace nav. No se agrega un segundo footer de ejecución ni otra aprobación inline. Nueva corrida abre Config; continuar después de aprobar abre la siguiente Config; Map sigue siendo una salida voluntaria.

### 01. Inicio — `?view=inicio`

```text
┌ PAGE HERO ──────────────────────────────────────────┐
│ Dation · Decision Intelligence     visual compacto  │
│ Título breve + definición del DDA                   │
└────────────────────────────────────────────────────┘
DECISION DATA ASSETS · Elegí qué sistema utilizar
┌ DDA Logística · Activo ┐  ┌ DDA Producción          ┐
│ Descripción breve     │  │ Próximamente · inactivo │
│ Abrir DDA Logística → │  │ Sin navegación          │
└──────────────────────┘  └─────────────────────────┘
```

Conservar el logo y las dos DDA cards actuales. El hero de Home puede tener hasta un 10 % más de altura de contenido que el operativo equivalente. Su definición extensa se resume en Fase 2; no se introduce una landing comercial ni un CTA final.

### 02. DDA Logística Overview — `?view=overview`

Alias admitido: `logistics-overview`.

```text
┌ PAGE HERO compacto ─────────────────────────────────┐
│ DDA Logística · título + explicación breve          │
│ [Iniciar nueva decisión →] [Ir al Decision Map →]    │
└────────────────────────────────────────────────────┘
CÓMO FUNCIONA · Datos → análisis → revisión
CADENA CONCEPTUAL · Assignment → Scheduling → Final
DATOS / RESULTADO / LÍMITES
FAQ · disclosures nativos
```

Preservar íntegro el contrato del PR #47: Nueva decisión siempre habilitado y llama `startNewDecision()`; Map visible y disabled sin caso seleccionado ni casos disponibles; un caso abre directamente; varios usan el selector existente aun con selección actual. Conservar generación de refresh, cases-ready, BFCache y drafts. La cadena es informativa, no representa el estado del caso.

Eliminar `.dda-landing__final` y el texto «¿Listo para tomar tu primera decisión?» en Fase 2. No mover ese bloque a Inicio.

### 03. Cargar Data Pack — `?view=logistics-data`

```text
PAGE HERO compacto · qué archivos habilitan la decisión
DATA PACK
┌ ÓRDENES ─────────────────┐  ┌ FLOTA ──────────────────┐
│ Subir / reutilizar CSV   │  │ Subir / reutilizar CSV  │
│ Archivo + validación    │  │ Archivo + validación    │
└────────────────────────┘  └────────────────────────┘
Compatibilidad y advertencias reales, si existen
┌ WORKFLOW ACTION BAR ─────────────────────────────────┐
│ Data Pack · [Órdenes ✓] [Flota ✓] [Seleccionar decisión →]│
└────────────────────────────────────────────────────┘
```

Una sola barra y una sola acción principal en el DOM. Sustituir `makeFinalBar()` y `makeSticky()` por un patrón común en Fase 3. El estado decide la acción: pendiente → falta archivo; validando → espera; inválido → enfocar el problema; listo → `onNext` existente. No crear un caso ni ejecutar un motor por cambiar un estado visual.

Conservar library/reuse, plantilla, guía, reporte de validación, retry, límites CSV y preflight. Un error de servicio conserva su recuperación; un archivo inválido no habilita continuar.

### 04. Decision Map — `?view=logistics-map&case_id=<id>`

```text
PAGE HERO compacto
[Decision Case actual ▾] · selector existente
PROGRESO · decisiones aprobadas / total
▸ Decision Case / Data Pack
DECISIONES DEL CASO
[Assignment] → [Scheduling] → [Asignación de vehículos]
```

Progreso y selector permanecen fuera del disclosure. Contexto cerrado por defecto, summary full width; al abrir: identidad → encabezado/acción → Órdenes y Flota. No revertir el reset de grid del PR #47 al migrar colores. La decisión final continúa marcada como no implementada; el rebrand no la habilita.

Conservar estados disponible, procesando, revisión, aprobada, bloqueada, error y obsoleta según el caso real. Cambiar datos mantiene la confirmación de impacto y columnas mantiene el drawer de guía.

### 05. Configurar Assignment — `?view=logistics-config&case_id=<id>&node_id=logistics_assignment`

```text
PAGE HERO compacto · Configurar asignación de carga
▸ Decision Case / Data Pack
01 · ALCANCE        filtros + inclusión/exclusión
02 · OBJETIVO       preset o pesos válidos
03 · RECURSOS       propia / mixta / tercerizada
04 · OPCIONES AVANZADAS · Próximamente
     Límite de tercerización        [disabled]
     Utilización mínima por viaje   [disabled]
     Reglas por proveedor           [disabled]
┌ WORKFLOW ACTION BAR ────────────────────────────────┐
│ [Alcance] [Objetivo] [Recursos] [Revisar y ejecutar →]│
└───────────────────────────────────────────────────┘
```

Eliminar el selector de profundidad, el chip Dashboard y la fila de profundidad del review en Fase 4. Las opciones futuras no tienen handlers, estado, persistencia ni payload. El review sigue precediendo la ejecución y muestra la configuración efectiva.

### 06. Dashboard Assignment — recurso `decision-dashboard`

```text
┌ DASHBOARD TOOLBAR ───────────────────────────────────┐
│ Decisión + estado + corrida                         │
│ [Aprobar / Continuar] [Map] [Exportar ▾] [Más ▾]      │
└────────────────────────────────────────────────────┘
RESUMEN · objetivo y asignación recomendada
[Viajes] [Ocupación] [Costo medio por viaje] [Flota propia]
EVIDENCIA · viajes, cargas y detalle contextual
VALIDACIÓN HUMANA · controles reales / estado vacío
▸ ANÁLISIS COMPARATIVO · generar / restaurar / reabrir
DATION IA · FAB y drawer contextual
```

Un mismo shell por decisión, sin identidad «Essential/Comparative/Deep». Preservar los cuatro KPIs canónicos, participación propia por peso, costo medio calculado por escenario, diferencias en puntos porcentuales y exportaciones actuales. Aprobar permanece en la toolbar, con la continuidad de caso existente.

El comparative está cerrado por defecto en el modelo objetivo. Datos históricos ya calculados se reabren sin POST; un Essential genera el artefacto al pedirlo. Conservar polling, retry, restore, fingerprint, cierre/reapertura y procedencia de IA. El nuevo tratamiento de apertura se implementa en Fase 5, sin recalcular históricos.

### 07. Configurar Scheduling — `logistics-config`, nodo `logistics_scheduling`

```text
PAGE HERO compacto · Planificar despachos
ASIGNACIÓN APROBADA · fuente visible y trazable
▸ Decision Case / Data Pack
01 · ALCANCE TEMPORAL · ventana + reglas por foco
02 · OBJETIVO · servicio primero / salida temprana
03 · RECURSOS HEREDADOS · sólo lectura
04 · OPCIONES AVANZADAS · Próximamente
     Buffer entre viajes      [disabled]
     Ventanas por recurso     [disabled]
     Penalización por atraso  [disabled]
┌ WORKFLOW ACTION BAR ─────────────────────────────────┐
│ [Ventana] [Objetivo] [Recursos] [Revisar y ejecutar →] │
└────────────────────────────────────────────────────┘
```

Mantener fuente aprobada visible fuera del disclosure, reglas, ventana ISO, SLA, identidad del upstream y recursos heredados. Retirar profundidad de Config, resumen, review y sesión en Fase 4; Scheduling ya no necesita enviarla en su contrato. Las opciones futuras no alteran reglas temporales existentes.

### 08. Dashboard Scheduling — `decision-dashboard`, nodo `logistics_scheduling`

```text
DASHBOARD TOOLBAR compartida
RESUMEN DE PLANIFICACIÓN · objetivo y ventana
TIMELINE · viajes por recurso + alternativa tabular
NIVEL DE SERVICIO · métricas con denominador verificable
VALIDACIÓN / EXCEPCIONES reales
DATION IA · mismo patrón de FAB / chat
```

Preservar el motor temporal y la Assignment fuente. Mantener CSV/JSON, timeline, SLA, detalle de ejecución y aprobación compartida. No agregar otro botón de exportación al calendario ni otra profundidad.

### 09. Errores, carga y estados vacíos

```text
CONTEXTO de decisión y caso, cuando sea conocido
[icono + estado] Explicación concreta
Detalle útil para actuar
[Volver a configurar] [Decision Map]   ← error terminal
[Reintentar lectura]                  ← error transitorio
```

Son estados distintos. Reconfigurar restaura datos y criterios y, al ejecutar, crea una corrida nueva; conserva la fallida y su upstream. Reintentar una lectura no vuelve a ejecutar el motor. Loading/polling mantiene el run ID y cancela suscripción al salir. Empty state explica qué falta y ofrece la siguiente acción válida. El cambio dark migra estos estados también.

### 10. Dialogs, drawers y Dation IA

```text
DIALOG centrado                  DRAWER lateral
Título + explicación             Título + [Cerrar]
Contenido / controles            Contexto persistido
[Cancelar] [Confirmar]            Contenido con scroll propio
```

Casos: revisión antes de ejecutar, cambio de datos, filtro, selector de casos, historial, guía, detalles y chat. Backdrop y superficies usan el mismo sistema. Abrir drawer cierra menús; Escape cierra la capa superior y devuelve foco al disparador; Tab no escapa de un modal. Click fuera cierra menús, sin consumir un click dentro de un diálogo/drawer.

Chat mantiene historial, retry con turn ID, evidencia original/comparative y cancelación de respuestas tardías. No se crean conversaciones durante el audit visual.

## C. Responsive y comportamiento compartido

Anchos de referencia: **1440, 1280, 1024, 768 y 390 px**. Se adaptan al ancho real del contenido, conservando la navegación actual; no se introduce un nuevo drawer de navegación móvil en esta saga.

- Desktop: hero de dos columnas, Data Pack de dos cards y KPI 4 columnas cuando entren con su ancho mínimo.
- Tablet: visual de hero compacto o debajo del copy; cards pueden seguir en dos columnas. La toolbar envuelve por grupos, con popovers dentro del viewport.
- Móvil: hero apilado; dos CTAs del Overview full width; archivos y KPI en una columna. El summary del contexto sigue siendo compacto.
- Footer móvil: resumen con scroll local o dos filas compactas y CTA full width. Reservar altura real de la barra más offset y safe area en la página; ni el último campo ni su foco pueden quedar cubiertos.
- Tablas extensas tienen scroll dentro de su panel, no del documento. Nombres largos conservan `title` y elipsis; la información operativa no se elimina para hacerla entrar.

## D. Archivos y límites de Fase 0

Sólo se agregan estos tres documentos de repositorio:

1. `docs/rebrand/DATION_DARK_WIREFRAME_V1.md`
2. `docs/rebrand/DATION_DESIGN_SYSTEM_V1.md`
3. `docs/rebrand/DATION_COMPONENT_INVENTORY_V1.md`

Los scripts temporales, métricas y capturas de auditoría se guardan fuera del checkout, en `/workspace/dation-audit`. No se cambian templates, CSS, JS, API, engines, dependencias, Supabase ni migraciones en esta fase. El mapa de archivos para las fases posteriores está en el inventario.

## E. Checks ejecutados

Desde `backend`, con `/workspace/.dation-cloud/activate.sh` activado:

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_*.js tests/test_*.mjs
```

Baseline: **349 Python y 37 Node pasan**, sin tests nuevos para este cambio documental. El baseline Chromium adicional usa las fixtures y el servidor loopback de `backend/tests/browser/test_navigation.py`; las API se interceptan, incluidas preflight y preview. No usa credenciales ni realiza escrituras productivas.

También se comprueban enlaces relativos, cobertura del inventario, diez wireframes, números de contraste, consistencia de fases y `git diff --check`. CI conserva sus checks obligatorios; resultados y publicación se registran en el PR de Fase 0.

## F. Visual QA y evidencia

Se capturaron **70 screenshots actuales**: 14 estados por cada uno de los cinco anchos, cubriendo Inicio, Overview, Upload, Map, ambas Config cerradas/abiertas, ambos Dashboards, error terminal, review, drawer y chat. No hubo errores JavaScript ni overflow horizontal del documento en estas fixtures. Esto es un baseline light; no certifica todavía el tema dark ni la totalidad de combinaciones de datos.

Evidencia de esta sesión:

- `/workspace/dation-audit/rebrand-phase0/baseline.json`: dimensiones, estilos cargados, menús y estados.
- `/workspace/dation-audit/rebrand-phase0/*.png`: capturas por pantalla y ancho.
- `/workspace/dation-audit/rebrand-phase0-contrast.json`: cálculo de pares y gradientes propuestos.
- `/workspace/dation-audit/rebrand-phase0-css.json`: conteo de literales y `!important` por hoja.

Los defectos reproducidos de los menús se registran como deuda de Fase 5, no como una prueba de que su comportamiento actual sea correcto. Fase 6 repetirá visual, teclado y contraste sobre la implementación dark.

## G. Riesgos y compatibilidad

1. **Cascade por navegación:** controlar links duplicados y probar cold/warm routes. Retener el fix de disclosure del PR #47 al mover estilos.
2. **Transición parcial:** texto dark-global sobre cards todavía blancas puede volverse ilegible; el design system define un bridge limitado hasta migrar cada dueño.
3. **Profundidad y motor:** `AssignmentOptions` y `DispatchOptions` aceptan `essential`, pero el default es `comparative`. En Fase 4 enviar `essential` explícito; sólo omitirlo conserva el default anterior. El motor usa profundidad para candidatos y sensibilidad: comparar objetivos representativos y documentar diferencias de nuevas corridas. No prometer equivalencia de plan sin medirla.
4. **Históricos:** mantener JSON, getAnalysisDepth y sus consumidores técnicos mientras comparative los necesite. Normalizar presentación sin reescribir corridas ni eliminar artefactos.
5. **Overlays y footer:** la altura del contenido, teclado, safe area y z-index requieren QA real; el baseline ya reproduce interferencia entre menús en móvil.

Los criterios de salida por fase y sus archivos están en el [mapa de migración](DATION_COMPONENT_INVENTORY_V1.md#mapa-de-migración).

## H. Gate

**FASE 0 COMPLETA — LISTA PARA FASE 1.**

Hay wireframes, especificación, inventario y mapa de migración. No se ha aplicado Dark Foundation ni se han retirado profundidad o componentes actuales. La siguiente fase comienza cuando el usuario solicite Fase 1.
