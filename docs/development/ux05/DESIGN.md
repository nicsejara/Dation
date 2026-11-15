# UX05 — diseño y gates

G0 PASS. Baseline `7b31c500896543902576cc99e37840dbc2107d69`, PR119 mergeado. CI main [43713411333](https://github.com/nicsejara/Dation/actions/runs/43713411333): impact/FAST/FULL/required-gate success. Cuatro contratos UX04 focales PASS (31,067 s). Inicio 15/11/2026 12:14:27 ART. Rama única `feat/saga-ux05-decision-graph-command-center`.

La evidencia productiva (revisión 00013-xut, tráfico100, flags ON y motores OFF) es informada por el propietario; no se realizan consultas/mutaciones productivas. La reconciliación del historial SQL20261114225017 queda fuera de alcance; no reaplicar ni editar migraciones.

## Composición

La nueva vista sólo intercepta `unified_journey_enabled && logistics-map`. Config, Dashboard y modo OFF mantienen sus renderers. Componentes pequeños: adaptación pura de estado/acciones, toolbar, nodos y conector, panel contextual, resumen y orquestador. El estado técnico y todas las autorizaciones siguen en Graph/Journey; no se ejecuta ni aprueba en el panel.

Grid Studio comparte geometría efectiva de Core: 1560px, rail216/gap20, colapso1199px. Panel no modal dentro de la columna; no portal ni z-index global. Único panel, Escape/cierre y foco restaurado; cambios de Case/nodo cancelan su scope. Selector de owner reutilizado sin contratos nuevos; historial25/página; selector Case existente.

## Riesgos y mitigación

1. Aprobación histórica/stale confundida con vigente: adaptador exige APPROVED+CURRENT; targets/actions del servidor, tests puros y API real.
2. Respuestas tardías de owner/historia/Case: AbortController/scopes y generaciones; revalidación antes de navegar.
3. Popover invadiendo rail: layout en flujo de columna; mediciones de rectángulos en seis anchos, sin clipping global.
4. Selectores UX04 cambian legítimamente: adaptar sólo la interacción de selección de nodo, preservando assertions de IDs, publicación, aprobación y cierre; OFF sin cambios.
5. Estados de datos incompletos/permisos: resumen con campos explícitos y fuentes existentes; sin rutas Storage ni secretos, ayudas visibles y recuperaciones acotadas.

Sin backend/SQL/API/motores/workflows/infra. Rollback propuesto: revisión anterior por digest tras GO separado; ningún cambio DB necesario para UX05. No se ejecuta merge, publicación, despliegue ni rollback en esta tarea.
