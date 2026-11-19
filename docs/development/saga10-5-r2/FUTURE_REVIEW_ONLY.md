# FUTURO — NAVEGACIÓN INVERSA / REVIEW-ONLY DEL LOGISTICS MODEL

**Estado: DESIGNED_FOR_NEXT_SAGA / NOT_IMPLEMENT_IN_THIS_PR.** El usuario solicitó dejar al menos planteada funcionalmente la revisión al volver desde fases posteriores. Esto NO autoriza cambios al workflow E2E ahora, API de edición ni cambios de versiones publicadas.

## 1. Objetivo de producto
- Viaje hacia adelante: configurar Logistics Model → Data Contract → Decision Case → Decision Studio.
- Viaje inverso: desde Data Contract, Decision Case, Graph/Studio, regresar a Logistics Model **para revisar** sin reabrir la sesión editable ni rehacer Wizard. La representación es un panel/página completamente **solo lectura**, con información preservada, inputs grisados o sustituidos por readouts visuales, sin CTAs de confirmación visibles que parezcan interactivos.
- **Edición futura** sólo tras acción inequívoca `Editar configuración` y control de permisos/estado, con borrador o nueva Model Version; jamás mutar snapshot inmutable. Este affordance puede quedar diseñado/documentado, pero NO debe presentarse como botón funcional hoy si no existe implementación.

## 2. Máquina de estados futura propuesta
- `MODEL_NEW_DRAFT` → edición normal si posee permisos.
- `MODEL_DRAFT_CONFIRMED` → configurado localmente, todavía no publicado; navegación hacia atrás podría mostrar review de draft con banner `Borrador no publicado`, sin perder identidad. Edición requeriría intención separada.
- `MODEL_PUBLISHED_SELECTED` → versión publicada, inmutable. Read-only review con nombre, número de versión, fecha si está en API, estado verificable y hash/version/contrato cuando corresponda.
- `REVIEW_READ_ONLY` → se navega hacia atrás: renderiza resumen estático de configuración; **no** simula input deshabilitado que pueda enviarse, y no invalida firmas/preview por visita.
- `EDIT_REQUESTED` (futuro) → abre confirmación contextual de duplicación/nueva versión, advierte impactos en contratos y Decision Case; no reescribe la versión publicada.
- `REVIEW_ERROR` → si no puede recuperar versión por permiso/red, explica error y reintenta; no reemplaza con valores por defecto.

## 3. Wireframe textual futuro
Header `Logistics Model · Revisión` con nombre, versión, estado; acción de retorno al punto de origen; badge gris discreto `Solo lectura` si la UI lo necesita; no botones CTA de sección. 5 tarjetas resumen en el mismo orden oficial:
1. Identidad: nombre, descripción, versión.
2. Operación: rol, patrón directo y si se pueden consolidar órdenes.
3. Carga y capacidad: unidad seleccionada, imagen de referencia (pallet vacío / cargado) si hay datos; producto/bulto/cantidad por presentación, masas/volumen con provenance; dimensiones activas, primaria interna explicada de manera técnica si necesario, split y compatibilidad. Si legacy mixed, lista de componentes con sus nombres/cantidades; jamás falsear homogeneous.
4. Recursos: fuentes, categorías declaradas o `Sin filtro global de categoría`.
5. Moneda y costos: moneda, decimales, propias/externas y bases; ningún importe real si no está en Logistics Model.
Pie: vínculo de contexto `Volver a Data Contract/Decision Case/Studio` según origen. Si la futura edición se habilita, botón secundario `Editar configuración` con permiso/confirmación; no mantener cinco CTAs Confirmar.

## 4. Diseño visual
Dark mode Dation, campos/readouts de fondo gris carbón, contraste suficiente y `readonly` visual obvio; evitar usar `disabled` para ocultar texto a lectores. Los checks de sección indican validez registrada, no posibilidad de edición. Resumen no debe aparentar cálculo nuevo ni reabrir preview al entrar si la versión es inmutable.

## 5. Datos y seguridad
- Render a partir de snapshot exacto `model_id/version_id`; código no debe mutar config ni cambiar draft por navegar.
- Versión publicada: read-only por backend y frontend; no permitir actualizarla. Para editar, la siguiente saga decidirá clonación/nueva versión, conflicto CAS y repercusión en Data Contract, Case y sesiones.
- Draft no publicado: recuperar `new_model` real/identidad; no seed ni auto-publicación.
- No persistir un segundo catálogo sombra sin hash/versión. Mostrar solo datos realmente disponibles; `Pendiente` o `No declarado` en vez de 0 inventado.

## 6. Criterios de aceptación para la SAGA FUTURA (NO tests de esta entrega)
- Desde Data Contract y Decision Case, Back entra review sin mutación de modelo ni de DOM editable; desde Studio respeta navegación de origen/versión.
- El usuario recorre las 5 tarjetas y ve todo lo configurado, con propiedades físicas y datos de costos claros.
- Modo read-only real para todos los controls, incluyendo subpanels ocultos, operaciones CRUD, top create/select si el contexto lo restringe.
- La acción explícita editar solicita permisos y abre borrador/nueva versión, nunca muta published ni sus contratos históricos.
- Los resultados de Decision Case/Studio mantienen referencia a Model Version anterior hasta una actualización explícita y validada.
- Retorno de review al punto de origen preserva scroll/contexto y no ejecuta D1/D2.

## 7. Alcance actual mínimo
En esta SAGA R2 Codex debe **verificar que el regreso existente no borra datos ni modifica publicados**, documentar los puntos de integración (Core step nav/route state) y anexar este blueprint al PR. No implementar review-only page ahora, no dejar un CTA falso `Editar configuración`, no introducir nueva ruta o esquema.
