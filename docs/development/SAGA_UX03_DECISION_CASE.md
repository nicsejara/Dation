# SAGA UX 03 — Decision Case / Strategic Decision Setup

Baseline: `9539d6721435cfb20dfd0d3ad49e1ec887068a99`, main vigente con UX 01/02 integradas, verificado el 14/11/2026.
Rama única: `feat/saga-ux03-decision-case`. Fuente: Master Plan y mockup aprobados adjuntos por el propietario.

## Implementación

El paso 03 presenta header propio, banner informativo D1 → aprobación → D2 y cinco tarjetas con rail descriptivo: identidad, prioridad, alcance, responsable y resumen. El flujo es informativo y no tiene controles de ejecución. Se conserva el shell global y el wizard real.

Los seis objetivos de GOALS se presentan como radios nativos con iconos y etiquetas exactas. Operating Mode usa otro grupo nativo, con los mismos enums. Cada grupo conserva un único valor del formulario, selección exclusiva, teclado y estado accesible. No quedan selects paralelos ni una segunda fuente de verdad.

El detalle Configurar límites y preferencias empieza cerrado. Seleccionar Personalizado lo abre para editar pesos; al restaurar un Case/draft vuelve a empezar cerrado, con sus valores intactos. Los errores abren el detalle y enfocan el primer campo afectado. Los guardrails siguen disponibles con cualquier objetivo; CUSTOM conserva porcentajes precisos y suma 100 %, y otros objetivos no envían preferencias personalizadas. No se cambian GOALS/GUARDS/PREFS ni las funciones de conversión y serialización.

El horizonte conserva los presets UTC inclusivos existentes y CUSTOM mantiene su fecha fin independiente. No hay fechas del mockup como defaults. El Owner procede del Equipo real: Admin debe elegir uno elegible; un operador sin can_assign puede crear con Owner pendiente, sin inventar una persona. La edición conserva responsables por etapa y expected_updated_at.

El resumen actualiza nodos de texto ya montados y muestra modelo/versión, contratos, objetivo, modalidad, fechas, flujo, identidad y Owner. No reconstruye controles ni dispara requests. Se reutilizan kit.footer y su único submit. El progreso consulta la misma validación nativa y de negocio del submit: identidad, política, tiempo, Owner y prerrequisito/permiso. Por ello no marca Listo cuando falla una condición requerida. El nombre sin contenido y la elegibilidad conocida del Owner se reflejan conforme a las reglas existentes del backend.

Se mantienen draftStore, creationIntent, control de doble submit, estados busy/dirty/409, reintentos, POST/PATCH actuales y navegación sólo después del éxito. El flag context_frozen_at bloquea los campos matemáticos protegidos, además de can_edit_mathematical. Nombre/descrición y Owner conservan sus permisos independientes. No se ejecuta D1 ni D2.

## Archivos y alcance

- `cases/ultimate-case-setup.mjs`: composición del paso 03, adaptación del consumidor de primary_goal, resumen y completitud compartida.
- `cases/decision-case-ui.mjs`: tarjetas, iconos locales, radios accesibles, banner, resumen y decoración del footer existente.
- `models/policy.mjs`: presentación de los seis objetivos y apertura del detalle, conservando read/draft/validate y payloads.
- `models/forms.mjs`: expone la validación ya usada por submit y busy; foco inicial de error opt-in para Case, con fallback al resumen. Otros formularios conservan su comportamiento por defecto.
- `ultimate-foundation.css`: estilos nuevos decision-case-* acotados; corrige específicamente la colisión de los radios con los estilos heredados de text inputs.
- Tests de setup adaptados al control radio y nueva expectativa de foco; nuevo test_decision_case_wizard.py.

No hay cambios de backend, SQL, Supabase, modelos persistidos, motores, Graph, Data Hub, infraestructura, G6, workflows, clasificador, IAM, Billing ni publicación. Los módulos y el estilo de Logistics Model/Data Contract no se rediseñan.

## Evidencia visual

Capturas reales de Chromium en sandbox local sintético, de página completa con los viewports indicados. Se preservan sidebar global y breadcrumb reales; el ancho útil menor al mockup y los datos completos requieren scroll vertical. No se comprimen controles para simular su lienzo ideal. A 1536 px el horizonte se distribuye en dos filas para mantener legibilidad; las seis estrategias conservan tres columnas. En móvil se apilan tarjetas y las modalidades se reorganizan según espacio disponible, sin partir sus palabras.

| Estado | Captura |
| --- | --- |
| Mockup aprobado | [Original](evidence/ux03/mockup-approved.png) |
| Nuevo / incompleto, 1536 | [Desktop](evidence/ux03/decision-case-1536.png) |
| Listo, 1536 | [Ready](evidence/ux03/decision-case-1536-ready.png) |
| CUSTOM y límites, 1536 | [Avanzado](evidence/ux03/decision-case-1536-custom.png) |
| Nuevo / incompleto, 390 | [Móvil](evidence/ux03/decision-case-390.png) |
| CUSTOM y límites, 390 | [Móvil avanzado](evidence/ux03/decision-case-390-custom.png) |
| Tablet 1024 | [Tablet](evidence/ux03/decision-case-1024.png) |
| Error visible y campo enfocado | [Validación](evidence/ux03/decision-case-validation.png) |

Los valores ilustrativos se usan sólo en QA. Se conserva el footer real con indicador de cinco condiciones; no se crea una segunda navegación ni otro submit. La onda decorativa del mockup no se agrega. El banner identifica explícitamente la aprobación entre D1 y D2.

## Validación y matriz UX03

**55 E2E focales únicos aprobados**: [53 en 283,479 s](evidence/ux03/acceptance.txt) más dos de navegación. [Tanda final de cuatro PASS en 38,103 s](evidence/ux03/final-targeted.txt): dos repeticiones afectadas por ajustes visuales/validación y dos pruebas de selector/historial. Dos archivos Node de navegación/conversiones y siete tests del clasificador PASS; checks estáticos del diff PASS. Clasificación real: R2, cuatro browser smokes, FULL no requerido.

| Criterios | Evidencia |
| --- | --- |
| 01/02/09/14/15/24 | DecisionCase 01: cards/banner sin acciones, identidad requerida, defaults reales, resumen y progreso, cero ejecuciones |
| 03/04/06 | DecisionCase 02: cada uno de los seis objetivos, draft/reload, POST y respuesta SQL con política idéntica, guardrails no CUSTOM y versión inmutable |
| 05/07/08/21 | DecisionCase 03: suma exacta, límites, habilitación y valor conservado, foco/aria-invalid/error visible, preferencias al alternar objetivo |
| 10/11/12 | DecisionCase 04 + Node: modalidad persistida, DAILY/WEEKLY/MONTHLY/leap/CUSTOM, rango inválido bloqueado, sin efectos de ejecución |
| 13 | DecisionCase 05/06: permisos reales de operador/Admin y falta de personas elegibles; no Owner inventado |
| 19/20 | DecisionCase 07/08 + Ultimate Setup: PATCH, revisión, Owner por etapa, contexto congelado y viewer sin edición |
| 16/17 | DecisionCase 09 + Saga/Setup: doble clic, respuesta perdida/timeout, refresh, misma intención, 5xx y conflicto 409 sin duplicados |
| 18/21/22 | DecisionCase 10 + navegación 04/08: campos preservados entre pasos, flechas de radio, foco, cinco anchos, selector/back/forward/pageshow |
| 23 | Regresión de doce tests UX 01, diez UX 02, Saga Planning, Ultimate Setup y Attributes Before CSV |

Los seis payloads se comparan contra los enums/ratios de los contratos existentes, incluyendo 10,01 % → "0.1001" y pesos CUSTOM que suman 100 %. El backend y sus validadores no cambian. Las fixtures no acceden a producción ni arrancan motores. El test de operador modifica/restaura sólo un miembro sintético mediante API local; el de congelamiento simula el flag en la lectura del contexto para evitar ejecutar una decisión. Los controles de permisos de viewer y el PATCH se ejercitan contra la API real del sandbox.

[Mediciones responsive y controles](evidence/ux03/responsive.json) · [Contraste AA, mínimo 5,43:1](evidence/ux03/contrast.json). No hay overflow horizontal a 1536/1024/768/390/320 px. La QA verifica también que los radios sigan siendo controles circulares nativos de 18 px dentro de sus tarjetas táctiles, sin heredar estilos de text input.

```sh
cd backend/tests/browser
python -m unittest -v test_decision_case_wizard test_logistics_model_wizard test_data_contract_wizard test_saga01_planning test_ultimate_case_setup test_attributes_before_csv
```

## Medición y estado de entrega

Inicio registrado: 14/11/2026 18:12:33 ART (21:12:33 UTC). SHA, FAST/required-gate terminal y duración de preparación/CI se registran en el PR al finalizar, sin crear otro commit sólo para repetir CI.

GO_IMPLEMENT=YES. GO_MERGE=NO. GO_PUBLISH_IMAGE=NO. GO_PROMOTE_TRAFFIC=NO. GO_G6_ENABLE=NO.
Un solo PR abierto para revisión visual; no se publica una imagen, despliega Cloud Run ni cambia tráfico.
