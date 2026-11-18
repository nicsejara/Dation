# Saga10.5 — Logistics Model 2.0 / Guided UX Refinement

Base verificada: main 8aa07f5ddad315d6e704b5fcfec77ebc0f101a8a, PR126 integrado. Rama feat/saga10-5-logistics-guided-ux. Fuente: paquete maestro1.0 del propietario,20 archivos con integridad verificada. No merge ni despliegue forman parte de esta entrega.

## Implementación

Los cinco bloques conservan sus dominios: identidad, operación, carga/capacidad, recursos y moneda/costos. Sus encabezados incluyen icono, descripción siempre visible, estado circular y chevron nativo. Los valores prellenados no equivalen a revisión.

Dentro de Carga hay siete subpasos: perfil; soporte/exterior cargado; nivel de detalle; productos; composición; capacidades/reglas; revisión. Son detalles nativos de la misma página, no otra navegación global. Los checks dependen de confirmación ligada al contenido; el cierre de Carga exige compilación vigente. La validez estructural permanece separada para permitir solicitar ese preview sin un deadlock.

Básico mantiene dos CSV y catálogo vacío. Detallado mantiene tres CSV y las mismas entidades de Saga10. El cambio a Básico con datos pide confirmación y conserva el catálogo sólo como borrador de navegador. La propiedad guided_ux está fuera de configuration: nunca entra en el cuerpo de creación/publicación ni en los hashes del backend. El intent de publicación, CAS, selección/reintento e inmutabilidad siguen en planning-model.

El editor conserva productos, unidades y presentaciones en un único estado por ID. Ofrece filtros reales, edición, clones con IDs y nombres/códigos distintos, protección de referencias y los límites100/50/200/30. Las propiedades parciales se conservan como borrador UI, bloquean validación y no se serializan como dimensiones parciales. No se infiere altura vacía desde la cargada.

Los resúmenes distinguen declarado, calculado, preliminar y validado. El compilador del servidor decide los coeficientes y contradicciones. Las sumas/porcentajes locales son vistas preliminares; no son un solver ni habilitan publicación. Los bultos no comparables no se suman ni se expresan como porcentajes de ocupación.

## Archivos y alcance

| Archivo | Responsabilidad |
|---|---|
| model-fields-v2.mjs | Cinco encabezados, siete subpasos, confirmaciones, reglas y collector compatible |
| cargo-editor.mjs | Catálogo único, CRUD, referencias, unidades compartidas, composición y procedencia |
| guided-ui.mjs | Componentes locales: tarjetas radio, pasos, círculo y lectura; SVG decorativo fijo |
| planning-model.mjs | Integra progreso revisado y gate de publicación sólo cuando el renderer lo ofrece; v1 conserva su protocolo |
| wizard-ui.mjs | Sólo amplía iconos locales; no cambia rutas ni navegación |
| ultimate-foundation.css | Estilos scoped de v2, responsive, contraste y reduced-motion |
| browser/guided_model_helpers.py | Acciones públicas del flujo nuevo |
| browser/test_saga10_5_guided.py | Casos nuevos con API/SQL/browser aislados; límites con fixture del renderer público |
| browser/test_saga10_wizard.py | Adapta controles de dos pruebas, conservando física, publicación, referencias y CSV |
| docs/development/saga10-5 | Matriz, evidencia, decisiones y procedimiento de publicación |

No se cambian backend, D1/D2, DTO, SQL/migraciones, flags, normalizer, Data Contract, dependencias, infraestructura, workflows ni políticas CI/release.

## Decisiones frente a las imágenes

- Se conserva el shell y la paleta dark real de Dation (teal y tokens existentes), no la navegación ficticia ni una paleta azul independiente.
- Básico no promete guardar un pallet físico sin productos. Esa capacidad está en [backlog separado](FUTURE_BASIC_PHYSICAL_MODEL.md).
- El soporte vacío declara tres ejes completos o ninguno; el exterior cargado pertenece a cada presentación.
- 640kg son peso bruto de componentes; con tara25kg son665kg. No se usa la etiqueta incorrecta «peso neto».
- Product.unit_label y units_per_package representan unidades comerciales por bulto. No existe un campo de embalaje recursivo: se usa «bultos» cuando no se puede afirmar «cajas», sin inventar otro catálogo.
- El arte es fijo y decorativo para soportes tipo pallet; granel usa icono de material y cantidad física. No packing3D, armado automático, temperatura ni hazmat certificados.
- El Core actual ofrece dark, sin selector light. No se implementa otro tema; v1/legacy mantiene sus pruebas y estilos.
- No se agrega Guardar borrador duplicado: continúa el guardado existente en este navegador. Publicación es una acción distinta.
- R2/FAST no implica autorelease. Esta entrega es NO_AUTO_DEPLOY.

## Evidencia

- [Gates y resultados](GATES.md)
- [70 criterios de aceptación](ACCEPTANCE.md)
- [Capturas reales y geometría](evidence/)
- [Publicación manual y rollback](RELEASE.md)

T01–T12 refieren a test_saga10_5_guided.Saga10GuidedTests:
T01 revisión explícita; T02 mixto, eliminación/restauración, soporte compartido y capturas; T03 perfiles/borrador reversible; T04 búsqueda/clonado/referencias; T05 medidas/pesos/contradicción; T06 preview obsoleto; T07 granel; T08 error/reintento; T09 límites mediante renderer público con DTO inicial; T10 principal/co-carga/unidades no comparables/duplicados; T11 error accesible de fuentes; T12 procedencia declarada.

El escenario de límites es una prueba de componente con datos sintéticos iniciales, no una publicación E2E fingida. Los restantes escenarios usan las acciones reales de la app y fixtures propias de PostgreSQL/PostgREST/API. Ninguno toca Supabase productivo ni ejecuta motores.

Los checks terminales, SHA, PR y tiempo final se registran en el PR para no atribuir a un nuevo commit la CI de otro SHA. Un check pendiente/fallido bloquea CODE_READY.


## Comparación visual real

| Escena | Escritorio1536 | Móvil390 | Móvil320 |
|---|---|---|---|
| Perfil y soporte | [Ver](evidence/actual-profile-support-1536.png) | [Ver](evidence/actual-profile-support-390.png) | [Ver](evidence/actual-profile-support-320.png) |
| Modo, productos y composición | [Ver](evidence/actual-mode-products-composition-1536.png) | [Ver](evidence/actual-mode-products-composition-390.png) | [Ver](evidence/actual-mode-products-composition-320.png) |
| Revisión | [Ver](evidence/actual-review-1536.png) | [Ver](evidence/actual-review-390.png) | [Ver](evidence/actual-review-320.png) |

[Cinco encabezados cerrados](evidence/actual-five-headers-1536.png). [Métricas](evidence/geometry-and-contrast.json). [Integridad/digest frontend](evidence/manifest.json). [Pruebas nuevas](../../../backend/tests/browser/test_saga10_5_guided.py).
