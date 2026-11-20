# Ingeniería R6 y límites

## Guardia de coherencia

`cargo-volume-coherence.mjs` es puro: decimales se representan como fracciones BigInt. cm³ se convierte a m³ exactamente; cantidad debe ser entero positivo seguro. Comparación sin redondeo de pantalla. Se define una banda relativa de **10⁻¹²** respecto al exterior: exceso mayor que esa banda es inconsistencia rígida; igualdad dentro de banda produce advertencia. No hay tolerancia física/ingenieril ni inferencia de capacidad útil. Bordes a ±epsilon, exponente, grandes cantidades, inválidos y cambios cm/m se prueban en Node.

Sólo el valor real `packageType=caja` activa bloqueo, por ser la opción rectangular rígida identificada. Saco/bolsa/fardo/bulto/otra muestran comparación orientativa. Dimensiones/cantidades inválidas siguen los validadores previos. El guardado fallido conserva el buffer y no genera IDs; cada guardado válido sigue siendo un upsert R4 con máximo dos tipos y unidad compartida.

Se evalúan ambos tipos guardados con la envolvente actual. Un inválido sigue visible, exige revisión y bloquea confirmación B03; se conservan sus referencias. Cambiar P1 no reconfirma firmas ni publica. El indicador compara volumen nominal/exterior con barra visual acotada a100%, etiqueta de ratio real sin truncar y texto de alcance. Error junto a cantidad, aria-describedby/aria-invalid y role=alert. No se agregan inputs ni CTA.

El volumen D1 sigue siendo loaded_dimensions o external_volume de la LoadPresentation. Nunca se sustituye por la suma de bultos. Pesos siguen cantidad×peso+tara una sola vez. Sin cambios de DTO, esquema, normalizador, motores, backend o tres CSV. La API no impone esta guardia de UX R6: importaciones/clientes externos pueden conservar un contrato contradictorio. Eso se informa en Review sin mutación ni bloqueo de consulta.

## Presentación y assets

R5 conserva su grilla60/40, r5-form-tail y volumeCard única de176px. Títulos usan un token compartido; Paso3 usa tres filas subgrid (título, ayuda, tarjetas). No altura de párrafo simulada con margin-top.

Selector=soporte vacío; P1=unidad cargada; P2=bulto individual (caja sola o icono neutral explícito para otros tipos); historial=unidad cargada. PNG/WebP locales; marcos estables, lazy/decode async, fallback WebP→PNG→SVG. Sin fondo radial o máscara para ocultar bordes. Misma URL/nodo mientras no cambia el tipo; cero requests por tecla. Arte decorativo no implica packing.

## Review y navegación

`model-published-review.mjs` recibe exclusivamente las tres entidades de servidor. Reutiliza la proyección humana histórica para los cinco bloques expandibles. Sin inputs, confirmaciones, editores JSON o operaciones de escritura. El indicador Publicado describe publicación, no afirma completitud de un wizard histórico. Datos ausentes se presentan como no disponibles; fechas proceden de servidor, en Buenos Aires. No se atribuyen límites de flota al Model.

Se conserva la estructura Unified Journey, navegación global/lateral y return targets. El CTA secundario invoca editSource(forceDerive) con confirmación y prepara otro Case con parent_case_id/preparation_id, abriendo Core01; no reemplaza la versión del padre. La nueva selección queda bajo las guardas originales. Badge no interactivo sin tab stop. Dos controles de cabecera comparten ancho/alto/padding/radio/tipografía:240×48 desktop, ancho disponible×64 móvil, conservando el texto completo.

Históricos no representables siguen legibles y completos; no se convierten al límite de dos ni se corrigen en almacenamiento. Review no resucita new_model ni borra sessionStorage. No se tocan roles, CAS, idempotencia, Data Preparation, API, D1/D2, Billing, infraestructura, Jobs, Scheduler o workflows.
