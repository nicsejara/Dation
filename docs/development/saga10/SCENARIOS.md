# Desafíos industriales y alcance certificado

`tests.test_saga10_industries` verifica los 12 sectores y un caso negativo literal adicional. Los IDs estables y las cantidades provienen del mismo snapshot del modelo; todos son datos sintéticos.

| # | Escenario | Resultado comprobado / límite |
|---|---|---|
| 1 | Fábrica de jugos | Unidad compartida, alturas cargadas distintas; 12 pallets =13.140 kg/27,24 m³, tres líneas conservadas |
| 2 | Tornillos en cajas | Capacidad 250 unidades, cajas de100: asigna dos cajas/200 unidades/2,2kg y deja una caja; no fracciones de cajas |
| 3 | Gaseosas y agua | Presentación mixta prearmada + otra del mismo producto: 30 unidades/42kg, dos líneas |
| 4 | Arena | Densidad1.600kg/m³ explícita; 25m³/40.000kg en tres servicios de10m³ |
| 5 | Cemento | Pallet2.025kg; recurso12t admite cinco de seis pallets, aunque quepan por cantidad |
| 6 | Oil & gas | 20m³/17.000kg, categoría TANKER; categoría ajena y `hazmat_certified` rechazados |
| 7 | Minería | Ruta no admitida: carga sin servir y NO_COMPATIBLE_RESOURCE; ciclos horarios especializados rechazados |
| 8 | Granos | Trigo/cebada explícitos; recurso elegible para ambos no autoriza co-carga; dos Trips separados |
| 9 | Cadena de frío | Tags COLD y categoría REFRIGERATED reales; recurso DRY no sirve carga. Campo de garantía térmica no soportado se rechaza |
| 10 | Acero | Orden de tres piezas indivisible: no asignable en dos recursos de capacidad2; completa con capacidad3. Sin promesa de geometría/amarre |
| 11 | Hormigón elaborado | D2 es diario; fecha con hora rechazada por el contrato. No resultado ficticio de entregas horarias |
| 12 | E-commerce urbano | Despacho directo de cinco paquetes; MULTI_STOP rechazado, sin ruteo urbano nuevo |
| 13 | Negativo literal | Recurso26pallets/12t no transporta una orden indivisible12pallets/14t |

Otras pruebas: 3 pallets no se dividen en1,5+1,5; todas las metas y fórmulas de costo; hard guardrails no relajados; órdenes mixtas elegibles por línea; conservación de granel; co-carga directa multicategoría exige autorización; v1 no admite silenciosamente DTOs de línea v2; mutantes re-firmados de cantidades, productos, resoluciones y CSV fallan; D2 no pierde ni duplica líneas.

No se implementa: packing3D, nesting recursivo, apilado optimizado, ejes/amarres, hazmat/compartimentos, garantías térmicas, multiparada, retornos, logística inversa, tarifas complejas o programación intradía. Los metadatos informativos no son restricciones certificadas. Los perfiles del wizard son sugerencias de dimensiones y copy, no algoritmos industriales nuevos.

Los fixtures CSV de `examples/` son ejemplos de estructura y cálculo; capacidades o tarifas ilustrativas no reemplazan datos reales de una operación. La validación de CSV no promete factibilidad física completa del solver.
