# Dation Platform Home V2 — Benchmark y dirección UX

## Objetivo

Rediseñar la Home autenticada de Dation para que combine onboarding guiado, siguiente mejor acción, continuidad operativa y contexto de Workspace sin convertirse en un dashboard BI ni duplicar el catálogo de DDAs o el Decision Center.

## Benchmark aplicado

### Snowflake / Snowsight
Patrones relevantes: Home como entrada inicial, navegación global, búsqueda, quick actions y recently viewed. La lección aplicable a Dation es combinar descubrimiento, acción inmediata y continuidad, pero sin introducir una búsqueda global todavía.

### Databricks
Patrones relevantes: workspace como hub central, accesos directos a tareas frecuentes, recents y una página Discover separada para exploración curada. Para Dation, Home debe orientar a la tarea y el catálogo de DDAs debe seguir siendo una superficie separada.

### Microsoft Fabric / OneLake Catalog
Patrones relevantes: Home personalizada, contenido reciente, Create, y exploración con detalles in-context para no perder la lista. Para Dation, Home debe conservar contexto y evitar enviar al usuario a otra superficie sólo para entender qué estaba haciendo.

### Atlan
Patrones relevantes: el problema no es sólo encontrar activos, sino entender contexto, ownership y confianza. Para Dation, esta idea se traduce en mostrar el Decision Case, nodo, estado, actividad y ownership cuando los payloads existentes lo permitan, sin inventar metadata.

### Palantir Foundry
Patrones relevantes: Home guiada por objetivos, recomendación de un punto de partida y onboarding orientado a workflows. Para Dation, el usuario nuevo debe recibir una siguiente mejor acción explícita y no una lista pasiva de capacidades.

## Qué aplicar a Dation

1. Next best action como principio rector del onboarding.
2. Home adaptativa: nuevo usuario, onboarding parcial y usuario activo.
3. Separar discovery de execution: el catálogo DDA vive fuera de Home.
4. Quick actions y recents, pero limitados a lo que ya existe.
5. Continuidad: reabrir el case/nodo/run correcto en un clic.
6. Onboarding como workflow guiado, no como `<details>` utilitario.
7. Contexto visible: Workspace, DDA, case, nodo, estado, última actividad.
8. Diseño de control plane premium, sobrio y operativo.

## Qué NO aplicar

- Search global sin backend/product scope.
- Marketplace dentro de Home.
- KPIs globales de portfolio; pertenecen al Decision Center.
- Recomendaciones AI inexistentes.
- Gráficos decorativos.
- Carruseles o hero de marketing.
- Duplicar las cards del catálogo de DDAs.

## Riesgos de sobrecarga

La Home ya dispone de onboarding, attention, recent cases, quick links y activity. El rediseño debe priorizar jerarquía y composición, no sumar más módulos. El onboarding debe reducir su presencia una vez completado para que el usuario recurrente llegue directamente a sus tareas.

## Arquitectura UX objetivo

### Estado A — Workspace nuevo
1. Workspace Hero
2. Onboarding V2 con progreso
3. Siguiente mejor acción
4. Empty state de primera decisión
5. Accesos rápidos
6. Actividad si existe

### Estado B — Onboarding parcial
1. Workspace Hero
2. Onboarding V2 compacto
3. Requiere tu atención
4. Continuar trabajando
5. Utility rail

### Estado C — Usuario activo
1. Workspace Hero compacto
2. Requiere tu atención, si existe
3. Continuar trabajando
4. Activity + quick links
5. Onboarding completado reducido a una banda compacta u oculto

## Wireframe textual

```text
┌──────────────────────────────────────────────────────────────────┐
│ ACME ARGENTINA · DECISION INTELLIGENCE WORKSPACE                │
│ Buenas tardes, Nicolás                                           │
│ Tu espacio para convertir datos en decisiones trazables.         │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ Tu primera decisión en Dation               2 de 4 completados  │
│ ━━━━━━━━━━━━━━━━━━━────────────                                  │
│ ✓ Workspace   ✓ Explorar DDAs   ● Preparar datos   ○ Ejecutar   │
│                                                                  │
│ Siguiente paso                                                   │
│ Prepará los datos de DDA Logística                               │
│ [ Continuar en Logística → ]   Probar con datos de ejemplo      │
└──────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────┬─────────────────────────┐
│ Requiere tu atención / Continuar       │ Accesos rápidos         │
│                                        │ Actividad reciente       │
│ [ Decision Case card ]                 │                         │
│ [ Decision Case card ]                 │                         │
└────────────────────────────────────────┴─────────────────────────┘
```

## Decisiones visuales

- Mantener identidad dark actual de Dation.
- Teal/cyan para acción, foco y progreso.
- Verde sólo para success/completed.
- Amber sólo para warning real.
- Hero compacto, no fotográfico.
- Cards con tres niveles de énfasis.
- Hover 180–220ms con elevación mínima.
- Stepper vertical en mobile.
- `prefers-reduced-motion` respetado.

## Regla de producto

Home responde “¿qué hago ahora?” y “¿qué requiere mi atención?”.

Decision Center responde “¿cómo está el portfolio de decisiones?”.

Decision Data Assets responde “¿qué capacidades puedo usar?”.
