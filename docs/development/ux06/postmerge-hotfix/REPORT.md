# UX06 post-merge — sincronización de T12

**Causa demostrada: test-only.** T12 observaba el formulario anterior antes de la transición asíncrona. Al completar la transición, la aplicación conserva las identidades correctas. El hotfix cambia sólo T12 y su documentación/evidencia; no necesita modificar navegación ni runtime.

## Baseline verificado

- main / merge PR121: `32559265531b7af8f6c161da0e8844e691172c4e`.
- Candidato UX06 validado: `05925956812ecda4407621dd5b8800ab3a3e0497`.
- Árbol Git de ambos: `99aa65170e93b934262594b3f146a99af98598a9`.
- Árbol `backend/app`: `446ea3f3ae18c90b16d8a95ea197d5433ed3b64f`, preservado por este hotfix.
- CI main [43866755551](https://github.com/nicsejara/Dation/actions/runs/43866755551), job133297327102: único error T12, `KeyError: 'parent_case_id'`;368/369 pruebas de navegador aprobadas. impact/FAST GREEN; FULL/required-gate FAILURE.
- Rama: `fix/ux06-derived-core-transition-sync`. Inicio16/11/2026,10:24:08 ART.

## Revisión focal de responsabilidades

|Componente|Contrato observado|
|---|---|
|T12 / `ready(2)`|Comprueba readiness y paso; no identifica el recurso/formulario. El Core original ya está listo en02 antes de confirmar.|
|`confirmAction` / forms.mjs|El botón llama al cierre nativo. La Promise se resuelve en el evento asíncrono `close`. Esperar el click de Playwright no espera esa Promise posterior.|
|`editSource` / journey/navigation.mjs|Tras confirmar, navega con `caseId:null`, padre original, UUID de preparación nuevo, paso02 y origen exacto. No muta el Case/Run original.|
|`coreSourceRoute` / journey/targets.mjs|Recupera el Dashboard y Node/Run originales antes de derivar desde Core; mantiene la whitelist.|
|Router / workspace.mjs|Copia las identidades explícitas, dispone el scope/form anterior, limpia readiness, escribe URL nueva y monta Core asíncronamente.|
|navigation/resource.mjs|Serializa padre/preparación/retorno; valida UUIDs, Node y vistas permitidas. No selecciona latest.|
|ultimate-case-setup.mjs|Carga contexto del padre antes de completar el formulario nuevo; marca readiness al terminar.|

## Reproducción causal en el SHA exacto

Una pasada normal original y diez repeticiones originales con CPU4x aprobaron. No se presenta esto como prueba de ausencia de carrera ni como una estimación de frecuencia.

Un harness exclusivamente local retuvo `close` en captura, antes del listener de aplicación. No editó código de aplicación/repositorio, fabricó URLs, usó producción ni introdujo sleeps. T12 original retornó de `ready(2)` y reprodujo el mismo KeyError. En ese punto:

- `returnValue=confirm`; URL del Case original, sin `parent_case_id`;
- formulario anterior conectado, readiness true, paso02.

Al liberar el evento, la aplicación intacta navegó al recurso derivado con padre, UUID de preparación, Dashboard Node/Run exactos, sin `case_id` y con formulario nuevo. `original-close-held.txt` conserva tanto el fallo como `HELD_CLOSE` / `AFTER_RELEASE`. El dato no se pierde: la aserción se ejecutaba antes de que existiera el recurso nuevo.

## Corrección mínima

T12 captura el formulario anterior antes de confirmar. Espera explícitamente:

1. URL de recurso derivado con `parent_case_id`;
2. Desconexión del formulario anterior;
3. Readiness del nuevo Core02.

Recién entonces verifica identidades. Conserva todas las aserciones originales de padre, return Run y retorno a Dashboard con Case/Node/Run exactos. Agrega `preparation_id` UUID canónico, ausencia de `case_id` prematuro, `return_node` y `return_view` originales.

No cambia el helper global `ready`, producto, sleeps, retries, timeouts ni tolerancias. No omite ni relaja aserciones.

Un segundo harness CPU4x retuvo dos gates independientes: cierre del modal y respuesta del contexto padre después de navegar. La espera de URL permaneció pendiente con el Core anterior aún listo; luego, con URL nueva y formulario anterior desconectado, la espera de montaje permaneció pendiente hasta liberar contexto. T12 completo pasó. Ver `fixed-gates.txt`: `URL_GATE_BLOCKED`, `MOUNT_GATE_BLOCKED`, `NEW_FORM_READY`.

## Validación focal

Chromium153.0.8010.12 de Playwright, igual al de CI; API/PostgreSQL reales de fixtures propios, sin credenciales productivas. CPU4x mediante CDP.

|Validación|Resultado|Evidencia|
|---|---|---|
|T12 corregido, normal ×10|10 PASS,65,450s|fixed-normal.txt|
|T12 corregido, CPU4x serial ×10|10 PASS,77,088s|fixed-cpu4-serial.txt|
|T12 con ambos gates retenidos, CPU4x|PASS,24,640s|fixed-gates.txt|
|T05/T13 + UX04 derivación/cancelación, contexto histórico/reload, cambio de modelo inmutable|5 PASS,49,120s|related-serial.txt|
|Contratos puros de navegación|19 PASS|pure.txt|
|Serialización de recursos|4 PASS|resource.txt|

Dos batches locales paralelos encontraron timeouts de arranque del Dashboard antes de alcanzar la derivación o las líneas corregidas: uno en T12 y otro en T13. La captura de T13 inspeccionada mostró la pantalla genérica de fallo de carga. La causa no quedó confirmada; no se etiqueta como regresión de navegación ni como infraestructura demostrada. Se conservan los logs iniciales fallidos por separado. No se cambió boot, timeout ni aserciones. Las pasadas seriales finales aprobaron; el diagnóstico serial de red/DOM no registró errores. La CI completa del candidato sigue siendo obligatoria.

Repetición significa ejecuciones independientes; no reintentar aserciones fallidas dentro del test. Los harnesses liberan eventos/respuestas explícitamente y conservan los handlers reales y el cleanup normal.

Desde `backend/tests/browser`, con runtime/browser/Docker aislados del repositorio:

```sh
python -m unittest -v \
  test_journey_navigation_ux06.JourneyNavigationTests.test_12_deriving_from_frozen_core_preserves_dashboard_parent_run \
  test_journey_navigation_ux06.JourneyNavigationTests.test_05_derived_parent_and_preparation_identity_survive_previous_and_return \
  test_journey_navigation_ux06.JourneyNavigationTests.test_13_conflict_reload_discards_draft_without_discarding_dashboard_origin \
  test_unified_decision_journey.UnifiedDecisionJourneyTests.test_03_derivation_cancel_confirm_and_original_immutable \
  test_unified_decision_journey.UnifiedDecisionJourneyTests.test_04_frozen_context_and_historical_return_survive_reload \
  test_unified_decision_journey.UnifiedDecisionJourneyTests.test_11_model_change_requires_derivation_without_mutating_existing_binding
```

El clasificador vigente, static y CI terminal del SHA exacto se registran en el único PR. Este documento no reemplaza FAST/FULL/required-gate ni declara GREEN anticipadamente.

## Alcance e integración

El árbol de aplicación debe coincidir exactamente con main. Sin cambios SQL, Supabase, motores, Cloud Run, IAM, Billing, Jobs, Scheduler, publicación ni tráfico. La reconciliación histórica UX04 continúa fuera de alcance.

Después de revisión y GO de merge separado, integrar sólo este PR y observar CI main. Este hotfix de pruebas no requiere publicar imagen, desplegar, migrar ni revertir datos. Revertirlo afectaría sólo sincronización de pruebas/documentación. Esta tarea deja el PR abierto, sin merge ni despliegue.
