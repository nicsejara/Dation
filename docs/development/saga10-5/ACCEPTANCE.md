# Matriz de aceptación — Saga10.5

Los70 IDs conservan el contrato del paquete. PASS local corresponde a comprobaciones de navegador/DTO real o invariantes inspeccionadas del diff, según evidencia. Los dos gates externos se cierran en el reporte del PR con el SHA y la CI reales; este archivo previo a CI no los declara aprobados anticipadamente. Un resultado pendiente o fallido bloquea CODE_READY.

T01–T12 y el alcance exacto de las fixtures se describen en [README](README.md). No se confunde la prueba de límites del renderer con publicación E2E. Las capturas reales y el JSON de geometría están en [evidence](evidence/).

| ID | Criterio | Estado | Evidencia verificable |
|---|---|---|---|
| UX-001 | Se conservan exactamente cinco bloques del Logistics Model | PASS local | T01: cinco bloques DOM; captura five-headers. |
| UX-002 | Encabezado cerrado muestra icono, título, microdescripción, círculo y chevron | PASS local | T02/capture_scenes: cinco encabezados cerrados; icono/copy/círculo/chevron. |
| UX-003 | Estado no usa badges textuales cambiantes como indicador primario | PASS local | T01: ningún badge textual en los cinco encabezados. |
| UX-004 | Valores por defecto no hacen validar automáticamente todos los bloques | PASS local | T01 y T09: cero checks por defaults/DTO prellenado. |
| UX-005 | Editar un bloque validado invalida check si cambia una dependencia | PASS local | T01/T05/T06: edición retira consentimiento y bloqueo vigente. |
| UX-006 | `<details>`/summary navegable con teclado y foco visible | PASS local | T02: Space/Enter, foco auditado y acordeones nativos. |
| UX-007 | Header del bloque 02 no promete horizonte/cobertura no configurados | PASS local | Copy localizado de bloque02 + captura real; no horizonte/cobertura. |
| UX-008 | Header del bloque 04 menciona fuentes/categorías reales | PASS local | Copy localizado de bloque04 + captura real; fuentes/categorías. |
| UX-009 | Tema dark reutiliza tokens del producto sin nuevo shell | PASS local | Capturas dark reales, tokens existentes; diff sin nuevo shell. |
| UX-010 | Tema light existente (si está habilitado) no se degrada | PASS local | Condicional: Core sólo ofrece dark; tokens.css y regresión v1/legacy. No se agrega otro tema. |
| P1-001 | Seis perfiles y valores backend exactos | PASS local | T03: seis enums exactos en radios. |
| P1-002 | Radio exclusivo, tarjetas completas clickeables y keyboard operable | PASS local | T03: click de tarjeta y ArrowRight, checked nativo; T02 foco visible. |
| P1-003 | Selección se conserva al volver al paso y recargar draft | PASS local | T03: perfil persistido tras reload y regreso al catálogo. |
| P1-004 | Cambio perfil no elimina datos ocultos sin consentimiento | PASS local | T03: cambio a MIXED/PACKAGED conserva IDs y capacidades. |
| P1-005 | Granel no obliga a crear pallet | PASS local | T07: granel continuo, sin soporte requerido ni dibujo de pallet. |
| P1-006 | Card 3×2/2×3/1×6 sin overflow | PASS local | T02: grid3/2/1 columnas y geometría en cinco anchos. |
| P2-001 | Se diferencia soporte vacío de presentación cargada | PASS local | T05: payload separa empty_dimensions y loaded_dimensions. |
| P2-002 | Dimensiones vacías se guardan sólo con 3 ejes válidos o no se guardan | PASS local | T05: ejes parciales bloqueados, conservados en borrador; tres ejes al publicar. |
| P2-003 | `loaded_dimensions` llega a presentación, no a unidad vacía | PASS local | T05: altura soporte15cm y cargada180cm distintas. |
| P2-004 | Tara, límite estructural y bruto no se confunden | PASS local | T02/T05/T12: tara/bruto/límite y procedencias separadas. |
| P2-005 | Volumen 120×100×150 cm =1,80m³ cuando valores cargados completos | PASS local | T02: backend1,80m³ desde120×100×150cm. |
| P2-006 | Peso desconocido se muestra pendiente, nunca cero inventado | PASS local | T05/T12: masa desconocida pendiente; no cero inventado. |
| P2-007 | Resumen responde a cambios pero no pretende certificar packing3D | PASS local | T02: resumen vivo, fuente del servidor y advertencia scalar/no packing. |
| P2-008 | Una unidad compartida admite múltiples presentaciones sin clonar ID | PASS local | T02: dos presentaciones, un logistic_unit_id. |
| P2-009 | Unidad referenciada no se puede borrar silenciosamente | PASS local | T04 + Saga10 T01: borrado de unidad referenciada deshabilitado. |
| P2-010 | No se pierde geometría no persistible tras elegir modo básico sin aviso | PASS local | T03: aviso, Escape/cancelación y borrador reversible tras reload. |
| P3-001 | Dos opciones exclusivas de nivel básico/detallado | PASS local | T03: radios direct/catalog exclusivos. |
| P3-002 | Básico mapea `direct` y envía catálogos vacíos | PASS local | T03 + Saga10 T03: cuerpo API direct con tres listas vacías. |
| P3-003 | Detallado mapea `catalog` y muestra 4/5 | PASS local | T02/T03: catálogo muestra4/5 sin datos ejemplo precreados. |
| P3-004 | Transición detailed→basic con datos pide decisión y no destruye draft | PASS local | T03: cancelar y conservar, IDs intactos. |
| P3-005 | Básico informa correctamente 2 CSV, detallado 3 CSV | PASS local | T01/T02:2/3 cards del contrato real tras publicación. |
| P3-006 | No se crea SKU/producto invisible para simular modo directo | PASS local | T03: sin guided_ux ni catálogo en cuerpo API direct. |
| P4-001 | Buscar filtra de verdad; filtro solo opciones reales | PASS local | T04: búsqueda por código y categorías reales, sin invalidar snapshot. |
| P4-002 | Agregar producto crea ID real nuevo sin datos ficticios | PASS local | T02/T04: cero productos iniciales; IDs nuevos por acción. |
| P4-003 | Editar conserva ID y modificaciones | PASS local | T03/T04: edición y recuperación preservan product_id. |
| P4-004 | Duplicar crea ID único sin colisión de nombre/código | PASS local | T04: duplicado con ID/nombre/código distintos y masa conservada. |
| P4-005 | Eliminar producto referenciado queda bloqueado y explica razón | PASS local | T04: protección viva por referencias y motivo accesible. |
| P4-006 | Campos avanzados soportados siguen accesibles | PASS local | T04/T07 y DOM: disclosures de datos avanzados; densidad y grupos operativos. |
| P4-007 | `gross_mass` se muestra como bruto por bulto | PASS local | T02/T12: peso bruto por bulto; bruto no se rotula neto. |
| P4-008 | Límite 100 productos no se sobrepasa | PASS local | T09:99→100 y Agregar/Duplicar bloqueados en límite. |
| P5-001 | Picker de unidad usa IDs reales, no nombre textual | PASS local | T02/T10: selector y payload usan logistic_unit_id original. |
| P5-002 | Composición por `product_id`, cantidad entera en discreto | PASS local | T02/T06: IDs de producto reales y fracciones discretas rechazadas. |
| P5-003 | Naranja32×8=256; manzana24×10=240; durazno24×6=144 | PASS local | T02: subtotales256/240/144kg. |
| P5-004 | Suma componentes 640kg + tara25kg = bruto665kg | PASS local | T02:640kg componentes +25kg tara =665kg. |
| P5-005 | Tabla no rotula 640kg como peso neto | PASS local | T02: no aparece Peso neto de productos. |
| P5-006 | 40/30/30 es % de cajas, no de peso/volumen | PASS local | T02/T10:40/30/30 por cantidad; unidades distintas No comparable. |
| P5-007 | Presentación mixta y homogénea se publican si válidas | PASS local | T02: publicación real mixta y homogénea, mismo soporte. |
| P5-008 | Eliminar componente y cambiar cantidad recalcula/invalida preview | PASS local | T02: quitar/restaurar componente521→665kg; T06 cantidad invalida preview. |
| P5-009 | La unidad compartida no se clona por presentación | PASS local | T02/T10: soporte no se duplica por presentación. |
| P5-010 | No se prometen pallets armados automáticamente ni packing3D | PASS local | Copy permanente y captura real: no armado automático/packing. |
| P5-011 | Producto, unidad o presentación faltante bloquea publish con guía | PASS local | Saga10 T01/T09, validación local y54 contratos/física: no publicación con catálogo incompleto. |
| P5-012 | Contradicción gross 500kg frente a 985kg se informa y bloquea | PASS local | T05 + Saga10 T01:500kg contradice985kg, error y bloqueo. |
| P6-001 | Dimensiones activas usan 4 enums vigentes | PASS local | T01/T07/T10 + DTO vigente: pallets/weight_kg/volume_m3/units. |
| P6-002 | Primaria pertenece a activas; se valida | PASS local | T10: principal inactiva bloquea; elegir activa recupera. |
| P6-003 | Sugerencia no pisa selecciones sin acción explícita | PASS local | T03/T07: perfil no aplica sugerencia; botón y confirmación explícitos. |
| P6-004 | Reglas split y compatibilidad conservan semántica | PASS local | T07/T10 + snapshot API: políticas/fraccionamiento preservados. |
| P6-005 | Co-carga separada de elegibilidad recurso | PASS local | T10: co_load_pairs SECO/FRIO distinto de categorías de recurso GENERAL/REFRIGERATED. |
| P7-001 | Resumen solo datos actuales y procedencia | PASS local | T02/T05/T12: resumen actual, bruto pendiente/declarado/calculado y procedencia. |
| P7-002 | Preview stale no habilita publicación | PASS local | T06 + wizard v1 T06: response obsoleta no habilita publicar. |
| P7-003 | Check final condicionado a validación actual/confirmación | PASS local | T01/T06/T08: consentimiento y preview actual; errores retiran check. |
| P7-004 | No hay submit duplicado ni doble creación en published/retry | PASS local | Wizard v1 T03–T05/T09/T10: misma intención ante doble submit/ACK; publicación Saga10 T01. |
| REG-001 | Modelos v1 siguen el flujo histórico | PASS local | Los12 escenarios de test_logistics_model_wizard, más cuatro Saga01. |
| REG-002 | Reusar modelo publicado deja configuración read-only | PASS local | T03 y Saga10 T02: versión elegida read-only e IDs inmutables. |
| REG-003 | CRUD y Data Contract con 3 CSV conservados | PASS local | Los cuatro escenarios Saga10 y T02: tres CSV/CAS/validación cruzada. |
| REG-004 | D1/D2, fórmulas, CAS, flags, hash y migraciones sin cambios | PASS local | Diff limitado a static/browser/docs; flags de cómputo locales false; no backend/SQL/infra. |
| REG-005 | 320/390/768/1024/1536 sin overflow ni foco invisible | PASS local | T02:15 escena/anchos, scrollWidth/clientWidth y controles dentro del viewport. |
| REG-006 | Contraste, teclado, aria labels y reduced-motion | PASS local | T02: contraste mínimo5,62+, foco, teclado y reduced-motion; T11 error de grupo. |
| REG-007 | R2/FAST y required-gate según clasificador real | Ver PR | Gate externo: impact R2, requires_full=false, FAST y required-gate del SHA exacto en PR. |
| REG-008 | No afirmar autopromoción con paths no permitidos | PASS local | Clasificador de release sin cambios: NO_AUTO_DEPLOY por cuatro módulos fuera de allowlist. |
| REG-009 | Código PR con evidencia, SHA y pruebas reales, sin merge/deploy no autorizado | Ver PR | Gate externo: PR abierto, SHA/checks terminales y ausencia de merge/deploy, ver reporte del PR. |

El cierre integral de esta matriz está en el único PR de la rama feat/saga10-5-logistics-guided-ux, incluidos REG-007 y REG-009. Publicación e infraestructura quedan fuera de la aceptación de código.
