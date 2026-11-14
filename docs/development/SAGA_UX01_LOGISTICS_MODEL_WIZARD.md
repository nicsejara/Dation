# SAGA UX 01 — Logistics Model Wizard

Baseline: `a464b3a6bb6a0a51d3b41e1063b85376cab2132a` (main, verificado el 14/11/2026).
Rama única: `feat/saga-ux01-logistics-model-wizard`.
Especificación: Master Plan del propietario del 14/11/2026 y mockup aprobado 1536 × 1024 adjunto a la tarea.

## Resultado

Core Configuration tiene navegación real de tres etapas en un único formulario montado. Logistics Model inicia en creación nueva, con tres tarjetas (identidad, operación/recursos, moneda/costos), iconos locales, estado accesible, progreso por validez y CTA propio. El catálogo contiene sólo modelos activos con versiones publicadas. El selector nativo modal conserva el borrador al cancelar y restaura el foco.

`Crear y seleccionar modelo` persiste la intención antes de enviar el modelo y su versión. Conserva IDs, cuerpo y revisión esperada ante 409, 503, timeout o refresh; una publicación pendiente no crea otro modelo. Después de la confirmación se vuelve a resolver el contrato con el model/version definitivo. La versión queda de sólo lectura; `Crear otro modelo` abre una identidad nueva. Un fallo posterior de lectura permite recuperar la selección sin repetir escrituras.

La creación del Case reutiliza la versión seleccionada, mantiene su propia intención estable y sólo se ofrece al final. Los Cases existentes conservan sus vínculos inmutables y `Guardar contexto`. Data Contract y Decision Case conservan sus campos, APIs, validaciones y plantillas; sólo se integran en la navegación.

No se agregaron endpoints, SQL, dependencias, workflows o cambios de motores/infraestructura. `GO_MERGE=NO`, `GO_PUBLISH_IMAGE=NO`, `GO_PROMOTE_TRAFFIC=NO`, `GO_IAM=NO`, `GO_G6_ENABLE=NO`.

## Estados y persistencia

- LOADING: formulario ocupado y contenido de modelo sin valores provisionales visibles.
- NEW_EDITING → NEW_VALIDATING → NEW_READY_TO_CREATE: tres tarjetas válidas más compilación aceptada; una respuesta stale no habilita publicación.
- NEW_PUBLISHING: un intento estable; controles bloqueados contra doble envío.
- MODEL_SELECTED: referencia publicada comprobada; el progreso de tarjetas por sí solo no prueba publicación.
- REUSE_PICKER / READ_ONLY: selección explícita de versión; sin publicación implícita ni mutación.
- ERROR_RECOVERABLE: campos/identidad conservados; reintento de publicación o lectura según la operación pendiente. Un conflicto real de revisión nunca se resuelve sobrescribiendo configuración ni cambiando automáticamente expected_revision.

Se reutiliza `draftStore` en sessionStorage, aislado por workspace/usuario. También se recuperan intenciones de borradores anteriores que bloqueaban el modelo antes de publicar. No se introduce persistencia distinta ni credenciales locales nuevas.

## Evidencia visual

Capturas reales de Chromium sobre API, PostgREST y PostgreSQL locales aislados, con usuarios/datos sintéticos. Son páginas completas tomadas con viewport 1536 × 1024 y 390 × 844; su altura incluye el desplazamiento vertical de la página.

- [Desktop](evidence/ux01/logistics-model-1536.png)
- [Móvil](evidence/ux01/logistics-model-390.png)
- [Tablet](evidence/ux01/logistics-model-1024.png)
- [Mediciones de controles y overflow](evidence/ux01/responsive.json)
- [Contraste](evidence/ux01/contrast.json)

Se preserva el shell global real (sidebar y breadcrumb existentes), sin duplicar el header ilustrativo del mockup. La composición reproduce el rail de etapas, las tres tarjetas con descripción lateral, iconos, superficies navy/teal y footer. En la aplicación, el shell existente reduce el ancho útil respecto del mockup, por lo que la página puede requerir desplazamiento vertical. Se verifican 1536, 1024, 768, 390 y 320 px sin overflow horizontal. En móvil las tarjetas se apilan y el CTA ocupa todo el ancho.

Los valores del mockup no reemplazan defaults: pallets, fuentes propias/externas y ambas bases de km siguen sus contratos actuales. Versión 1 es información calculada; el número seleccionado definitivo proviene del backend. Las bases de km siguen siendo selección múltiple, conforme al contrato existente.

## Validación y aceptación

La ejecución usa fixtures locales existentes, nunca Supabase productivo. El nuevo módulo comprueba además que no se envíen solicitudes de ejecución a motores. Los fallos se corrigieron en esta misma rama; no se aumentaron esperas ni se deshabilitaron assertions. La espera de rutas interceptadas tiene un límite explícito para fallar con diagnóstico.

| Criterio | Evidencia focal |
| --- | --- |
| UX-01/02 | Wizard test 01: capturas, 5 anchos, límites de controles y contraste |
| UX-03/06/07 | Wizard 01: catálogo sólo con borrador no habilita reutilización; progreso 0→1→2→3; publicación inválida bloqueada |
| UX-04/05 | Wizard 02: nuevo por defecto, cancelar preserva borrador; versión elegida inmutable |
| UX-08/09/10 | Wizard 03: latencia y doble clic, un modelo/versión, cero Cases; contrato con IDs definitivos |
| UX-11 | Wizard 04/05/09: 409/503, refresh, respuesta perdida de create/publish, identidad estable y una versión SQL |
| UX-12/14 | Attributes 2 y Saga Planning 04: recarga antes/después de publicar; fallo de Case sin duplicar modelo/versión |
| UX-13/19 | Saga Planning 01/02: modelo→contrato→Case→Graph; CSV coincide con contrato de versión |
| UX-15 | Wizard 07: permisos de modelo cerrados; reutilización permitida y cero escrituras de publicación |
| UX-16 | Ultimate Setup 02/03/09: edición, CAS, sólo lectura y borrador de Case existente |
| UX-17/18 | Wizard 11 y Ultimate Setup 06: pasos por teclado, foco modal/retorno, inputs conservados, labels/contraste |
| Errores de selección | Wizard 10/12: lectura fallida/404 recuperable sin elegir otra versión por defecto |
| UX-20 | Diff limitado a frontend, browser tests y documentación; sin llamadas de motores ni operación productiva |

Se adaptó únicamente la entrada de setup en el E2E de certificación existente, para reutilizar explícitamente la versión que ya publicó. No se ejecuta su recorrido de motores en esta tarea.

**Resultado local:** 32 E2E PASS en 163,457 s, más la comprobación añadida de versión 404 y la recaptura final responsive (2 PASS en 21,596 s; 33 escenarios E2E únicos). [Log de aceptación](evidence/ux01/acceptance.txt) · [Log visual/recuperación final](evidence/ux01/visual-recovery.txt). Navegación Node: 2 archivos PASS; clasificador Rapid: 7 tests PASS; estáticos del diff: PASS. Clasificación real: R2, cuatro browser smokes, FULL no requerido.

Comando de aceptación focal:

```sh
cd backend/tests/browser
python -m unittest -v test_logistics_model_wizard test_saga01_planning test_ultimate_case_setup test_attributes_before_csv
```

También se verifican las dos pruebas Node de navegación de Case/datos, las siete pruebas del clasificador Rapid y los checks estáticos del diff. FAST remoto ejecuta los cuatro smoke tests que selecciona el clasificador existente. FULL corresponde sólo si el diff real exige R3/R4; no se cambia el clasificador ni impact-map.

## Medición y revisión

Inicio registrado de trabajo: 14/11/2026 11:20:16 ART (14:20:16 UTC), baseline y lectura focal. La duración hasta FAST verde, SHA candidato y enlace a su ejecución se registran en el PR al finalizar, sin introducir un commit adicional sólo para reejecutar CI. El PR queda abierto para revisión visual y autorización específica de merge; no se publica una imagen ni se cambia tráfico.

Limitaciones: QA con datos sintéticos y navegador real local; no es una prueba de producción. El acceso sin permiso de administrar modelos se prueba con capabilities restringidas en la UI sobre el sandbox. Los contratos y permisos del backend no cambian. Los borradores siguen limitados al navegador/sesión actual como antes.
