# SAGA UX 02 — Data Contract

Baseline confirmado: `f0f57c9f6937131395f27b9db14448e9c2f62844`, main del 14/11/2026, con UX 01 integrada.
Rama única: `feat/saga-ux02-data-contract`.
Fuente: Master Prompt definitivo y PNG aprobado adjuntos por el propietario.

## Cambio implementado

El segundo paso del wizard presenta dos tarjetas simétricas: Órdenes / Demanda y Flota / Recursos. Cada una tiene descripción de negocio, icono local, identificadores del CSV, un CTA de descarga de ancho completo y un único desplegable Campos y reglas debajo de la descarga. Ambos detalles comienzan cerrados y funcionan de forma independiente. La tabla muestra Campo, Descripción y Condición; Especificación técnica conserva el contrato completo, incluidos tipos, unidades, reglas, condiciones, ejemplos y hashes disponibles, dentro de un segundo detalle anidado y cerrado.

Se agregan la banda ¿Qué es un Data Contract? y el footer Estructura de datos lista. Continuar a Decision Case usa la misma instancia de `steps.show(2,true)`; no envía el formulario, crea un Case ni exige descargas. El submit final permanece exclusivamente en el paso 03.

La implementación reutiliza el preview y las descargas actuales. El componente de presentación recibe los estados ya vigentes de UX 01; no introduce una segunda verdad de selección. La validación estructural de la respuesta exige ambas entidades completas, y las versiones definitivas deben corresponder al version_id seleccionado. Los previews provisionales no incluyen los IDs/hashes de publicación por contrato del backend, siguen identificados como provisionales y no habilitan continuar.

Las descargas conservan endpoint, body, filename, MIME y contenido generado en servidor. Cada tarjeta bloquea dobles clics durante su descarga y presenta errores localizados sin invalidar el otro CSV ni la estructura válida. Invalidar una selección retira sus tarjetas y descarta previews/descargas que terminen tarde. No se muestran reglas JSON como contenido principal.

## Archivos de producto

- `backend/app/static/js/dispatch/models/data-contract-view.mjs`: presentación, catálogo de copy, condiciones legibles, descargas, validación de respuesta y estados del paso 02.
- `backend/app/static/js/dispatch/models/planning-model.mjs`: sustituye exclusivamente el render técnico de Data Contract por el nuevo componente; preserva publicación del modelo, permisos, IDs, revisiones, generaciones y reintentos.
- `backend/app/static/js/dispatch/cases/ultimate-case-setup.mjs`: un callback para continuar con el wizard existente, sin cambiar el formulario ni la creación del Case.
- `backend/app/static/css/ultimate-foundation.css`: nuevas reglas acotadas a `.data-contract-*`; no modifica estilos de UX 01 ni del Case.

No hay cambios en backend, generador de contratos, modelos persistidos, Supabase/SQL, motores, infraestructura, IAM, G6, workflows, clasificador ni publicación. La vista y las descargas de Cases existentes siguen usando su render y endpoints anteriores.

## Catálogo y condiciones

El catálogo local sólo documenta encabezados públicos conocidos del compilador vigente: identificadores, fechas, prioridad, demanda/capacidad en pallets/peso/volumen/unidades, fuentes, disponibilidad, costos y compatibilidad. Un encabezado desconocido se presenta literalmente con el fallback Campo «encabezado» del contrato seleccionado, sin deducir su propósito. Se usa DOM textContent, incluyendo contenido técnico y encabezados desconocidos.

`nullable` determina Requerido/Opcional en esta presentación de plantilla. `applies_when` agrega la condición: se traducen únicamente los valores conocidos de `source` (OWN/EXTERNAL) y `cost_model` (PER_TRIP/PER_KM), combinados con «y». Una condición desconocida o compleja se muestra como «según condición técnica», sin inventar una interpretación. Las condiciones y `required_for` completos permanecen en la especificación técnica; no se modifica su validación efectiva ni se transforma null en cero.

## QA visual y decisiones que prevalecen sobre el mockup

1. Un único toggle bajo la descarga; se omite la flecha redundante del header de cada tarjeta.
2. Ambos detalles cerrados por defecto, aunque el PNG ilustre Órdenes abierto.
3. La estructura lista depende de dos contratos de una versión publicada; nunca de descargar archivos.

Se conserva el shell global real y la sidebar de UX 01, sin recrear el header ilustrativo del PNG. Su menor ancho útil puede producir más líneas y scroll vertical. No se agregan los chips «Campos requeridos» del mockup porque algunos campos son opcionales o condicionales. La tabla conserva todos los campos reales, aunque la imagen de referencia ilustre sólo cinco; el scroll queda dentro de su región accesible.

| Referencia / navegador real | Enlace |
| --- | --- |
| Mockup aprobado por el propietario | [PNG](evidence/ux02/mockup-approved.png) |
| Desktop 1536 × 1024, cerrado | [Captura](evidence/ux02/data-contract-1536-closed.png) |
| Desktop 1536 × 1024, Órdenes abierto | [Captura](evidence/ux02/data-contract-1536-open.png) |
| Móvil 390 × 844, cerrado | [Captura](evidence/ux02/data-contract-390-closed.png) |
| Móvil 390 × 844, Órdenes abierto | [Captura](evidence/ux02/data-contract-390-open.png) |
| Tablet 1024, cerrado / abierto | [Cerrado](evidence/ux02/data-contract-1024-closed.png) · [Abierto](evidence/ux02/data-contract-1024-open.png) |

Las capturas son de página completa, obtenidas con Chromium y datos sintéticos en el sandbox local de API/PostgREST/PostgreSQL. Se miden 1536/1024/768/390/320 px, sin overflow horizontal general, botones a ancho completo, cards de ancho/alto equivalente al cerrar y sin estirar la otra tarjeta al expandir. El detalle técnico conserva foco y scroll por teclado; el movimiento reducido y contraste AA se verifican con los checks existentes.

## Matriz de aceptación focal

| Caso | Evidencia |
| --- | --- |
| A/G: nuevo modelo → contratos → Case, sin descargar | DataContractWizard test 01; un modelo, una versión, un Case sólo al submit final |
| B/D: reutilización y ambos CSV | test 02: igualdad de bytes/headers/filename/body y versión inmutable |
| C/E: toggles independientes, copy y técnica completa | test 03: campos en orden real, requeridos/condicionales/opcionales, JSON completo idéntico al backend |
| D/F: errores locales y doble clic | test 04: 503/timeout, reintento, otra descarga y continuar habilitados; una solicitud en curso |
| F: respuesta parcial, versión incorrecta, timeout, 503 | test 05: no tarjetas stale ni avance falso; retry recupera ambos contratos |
| E: metadatos futuros y seguridad DOM | test 06: fallback literal, condiciones no inventadas, datos técnicos intactos y sin HTML ejecutable |
| I: Case existente | test 07: render anterior, CSV anterior idéntico y contexto sin mutaciones |
| H: responsive, teclado, foco y contraste | test 08: seis capturas y mediciones en cinco anchos |
| F: preview tardío de otra versión | test 09: no sustituye el contrato de la selección vigente |
| F: descarga tardía de otra versión | test 10: se descarta el resultado anterior y el nuevo CSV corresponde a su versión |

La regresión focal incluye los doce casos de UX 01, Saga Planning, Ultimate Case Setup y Attributes Before CSV. No se ejecutan motores ni el recorrido general de certificación D1/D2. Las pruebas anteriores sólo se adaptan al nuevo título, estado y detalle cerrado; no se eliminan controles de negocio ni se aumentan timeouts. El riesgo y los cuatro smokes FAST los determina el clasificador existente, sin cambios.

```sh
cd backend/tests/browser
python -m unittest -v test_data_contract_wizard test_logistics_model_wizard test_saga01_planning test_ultimate_case_setup test_attributes_before_csv
```

**Resultados locales:** [43 E2E PASS en 212,950 s](evidence/ux02/acceptance.txt); [3 casos afectados por ajustes finales PASS en 22,961 s](evidence/ux02/final-targeted.txt), más [QA visual final PASS en 17,040 s](evidence/ux02/captures.txt). Dos pruebas Node de navegación y siete pruebas del clasificador Rapid PASS; estáticos del diff PASS. Clasificación vigente: R2, cuatro smoke tests, FULL no requerido.

[Mediciones responsive](evidence/ux02/responsive.json) · [Contraste](evidence/ux02/contrast.json).

## Medición y entrega

Inicio registrado: 14/11/2026 15:49:34 ART (18:49:34 UTC). Resultados locales y logs se adjuntan a esta evidencia. El SHA candidato, FAST/required-gate remoto, duración hasta verde y tiempo de CI se registran en la descripción del único PR al finalizar, evitando un nuevo commit sólo para repetir CI.

GO_IMPLEMENT=YES. GO_MERGE=NO. GO_PUBLISH_IMAGE=NO. GO_PROMOTE_TRAFFIC=NO. GO_IAM=NO. GO_G6_ENABLE=NO.
El PR permanece abierto para revisión visual del propietario; después de su GO_MERGE, la publicación manual GitHub Actions → Cloud Shell corresponde a otra tarea.
