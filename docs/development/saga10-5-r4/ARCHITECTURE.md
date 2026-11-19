# Estado, compatibilidad y decisiones R4

- `cargo-guided-state.mjs`: estado puro con unidad compartida, catálogo guardado y buffer independiente; guardar/actualizar hace un upsert local atómico. Máximo dos tipos, un Product por Presentation. IDs UUID generados una sola vez. La selección y el render no generan entidades.
- `cargo-guided-editor.mjs`: único renderer de Paso 1/2; sin importar/montar el administrador anterior. Historia debajo del formulario. El formulario vacío tras el primer guardado espera otro input; tras el segundo bloquea el alta. Tarjetas permiten editar; un diálogo protege cambios no guardados.
- `model-fields-v2.mjs`: tres secciones permanentes, reglas por orden y footer común de cinco CTA. Las confirmaciones R3 se invalidan al ingresar a R4; se conservan los datos. Las firmas R4 se recuperan por bloque, con nuevo preview físico para B03.
- `planning-model.mjs`: mantiene CAS, intent/model/version IDs, control de generación y reintento de publicación. La invalidación de preview compara **configuración canónica**, no cambios de UI, foco, estado de revisión o apertura de bloques. Esto evita que el `change` al perder foco invalide un preview recién recibido solo porque cambió el estado visual de revisión.
- `ultimate-case-setup.mjs`: los Cases V2 revisan el snapshot publicado pinneado mediante el mismo renderer, bloqueado. No se reemplaza su versión ni se crea un nuevo draft al volver del Graph.

## Física

Las dimensiones del Paso 1 son exterior cargado en cada presentación, nunca empty_dimensions. Tara compartida en LogisticUnit; cada presentación deriva su masa desde sus propios bultos. No se escribe un total bruto calculado redundante. Big bag/Otra usan volumen exterior explícito y cantidades discretas. Los cálculos JS son informativos; la autoridad sigue siendo Decimal/backend. No hay inferencia de packing.

## Compatibilidad conservadora y GAP-01

Nuevos tipos usan `CATEGORIZED` y un grupo estable distinto `LOAD_<product UUID sin guiones>` por producto. Se conserva en el DTO, y las plantillas/contratos existentes lo exponen para elegibilidad del recurso. `co_load_pairs=[]`: compartir soporte **no** autoriza compartir viaje. Grupos/políticas ya existentes se preservan.

Dry run con DTO publicado real en el fixture: vino 745 kg/1.8 m³; aceite 665 kg/1.8 m³. Orden 10+6: 11440 kg/28.8 m³. Una orden indivisible con ambos tipos no se sirve con grupos distintos sin un par autorizado; DISCRETE puede separarlos en dos viajes cuando `split_allowed=true`. Dos órdenes separadas mantienen viajes separados. Un par explícito o una misma categoría permite co-carga en el escenario de prueba; R4 **no aplica** esas concesiones al producto.

**GAP-01:** edición de co-carga entre tipos permanece fuera del alcance. Requiere decisión posterior de producto; no bloquea configurar/publicar dos tipos ni servir órdenes separadas. No se añade selector oculto ni política permisiva.

## Históricos y límites

Directo, continuo, composición mixta, >2 tipos, varios soportes, dimensiones legacy, unidades comerciales anidadas, exteriores distintos o física adicional no representable: consulta read-only completa, sin truncar, sin montar siete pasos. El lector devuelve una copia exacta del draft/snapshot. Se muestran además los datos parciales de catálogo recuperado sin publicar, cuando difieren de la configuración.

No se implementa borrado de tipos guardados. Para descartar un segundo tipo aún sin guardar, seleccionar una tarjeta inferior y confirmar el descarte. Un publicado no se edita; Crear nuevo produce una identidad independiente mediante la acción existente y sus permisos.
