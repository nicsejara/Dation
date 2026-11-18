# Matriz de aceptación — Saga 10

PASS en esta matriz significa validación focal local; el gate de entrega exige además los checks requeridos del SHA del PR. La evidencia de CI se registra en el PR para no atribuirla anticipadamente a otro commit. No se declara producción activa.

| ID | Criterio | Verificación |
|---|---|---|
| A01 | Baseline real UX09/main fijado antes de editar | G0_BASELINE, SHA/CI de main |
| A02 | Configuración v1 conserva serialización y hashes | `test_ultimate_contracts`, `test_ultimate_case_models`, G3 legacy |
| A03 | Configuración v2 inmutable, sin backfill ni downgrade implícito | `test_saga10_persistence` T02/T03 |
| A04 | Catálogo opcional; directo sin producto ficticio | `test_saga10_domain_physical`, navegador T03 |
| A05 | Producto/SKU tiene ID estable, referencias y unicidad | Domain/physical y persistence T03 |
| A06 | Una unidad logística compartida por varias presentaciones | Domain/physical, navegador T01 |
| A07 | Producto con varias presentaciones | Domain/physical, industries T03, navegador T01 |
| A08 | Presentación prearmada mixta real, sin nesting | Domain/physical, industries T03, navegador T01 |
| A09 | Tara y bruto declarado/derivado coherentes | Domain/physical; ejemplos A/B; UI preview |
| A10 | m/cm, kg/t y m³/litros convertidos con Decimal | Domain/physical, contratos de granel |
| A11 | Densidad explícita; no inferida del nombre/perfil | Domain/physical, industries T04/T06 |
| A12 | Exterior cargado; no sustituido por volumen de producto/unidad vacía | Domain/physical, provenance y copy UI |
| A13 | Precisión y quantum conservan todas las dimensiones | Domain/physical (100 propiedades), D1 T08 |
| A14 | Contradicciones, NaN/floats, negativos y overflow se rechazan | Domain/physical y contracts |
| A15 | Directo/v1 conservan dos CSV; catálogo tiene exactamente tres | `test_saga10_data_contracts`, navegador T01/T03 |
| A16 | Preview/templates/validación salen del compiler | Contracts, G3 API; navegador T01 |
| A17 | Orders/OrderLines unidos por ID, sin huérfanas ni pares duplicados | Contracts, catalog_pack T02/T03 |
| A18 | No Products.csv obligatorio ni overrides ambiguos | Campos exactos de contracts/normalizers |
| A19 | Upload privado pre-Case y publicación atómica, CAS y recovery | `test_saga10_catalog_pack`, `test_decision_journey` |
| A20 | Prueba cruzada ligada a revisión, versión y hashes | API validate-bundle; navegador T02/T04 |
| A21 | HTTP200 incorrecto u obsoleto no habilita Continuar | Navegador T04 con respuestas controladas, sin sleeps |
| A22 | D1 conserva cada línea: requested=assigned+unserved | Assignment y certificador adversarial |
| A23 | Discreto entero; no 1,5+1,5 pallets | Assignment T03; industrias tornillos/cemento |
| A24 | Orden indivisible completa en un Trip o sin servir | Assignment T05; industries T10/T13 |
| A25 | Consolidación separada de split | Assignment T06 |
| A26 | Carga→recurso separada de co-carga | Assignment T04 y multicategoría directa; industrias8/9 |
| A27 | Capacidades garantizadas multidimensionales simultáneas | Assignment T07; literal26pallet/12t vs14t |
| A28 | Metas, guardrails y fórmulas de costos preservados | Oracles de D1, `test_transport_plan_policies`, todas las metas |
| A29 | Fechas, disponibilidad finita y ciclos OWN sin solapamiento | Kernel y regresión D1/D2 históricos |
| A30 | Búsqueda acotada; no óptimo/viabilidad falsos | Budget tests, benchmark y trace explícito |
| A31 | Perfil3.0.0 exacto, snapshot íntegro y worker revalida archivos | Execution integration; v1 rechaza DTOs v2 |
| A32 | D2 consume D1 aprobado y conserva Trips/cargas/productos | Scheduling, execution T01, mutantes de handoff |
| A33 | Detalles y CSV muestran presentación/cantidad/productos; costo Trip una vez | `test_saga10_result_consumers`, execution HTTP/Storage |
| A34 | Data Hub conserva hash, permisos y protección de borrado | Execution integration; regression Data Pack |
| A35 | Cinco tarjetas accesibles, teclado, borrador, CRUD, condicionales | `test_saga10_wizard`; UI nativa details/labels, HTML constraint validation |
| A36 | Geometría y contraste en320/390/768/1024/1536px | Capturas y geometry.json del navegador |
| A37 | Core/Studio/Graph/derivación/historial v1 conservados | Focal UX09, UX06 T12, Logistics Model v1 y FULL CI requerida |
| A38 |12 sectores soportados o limitación explícita, sin capacidades ficticias | `test_saga10_industries`, SCENARIOS.md |
| A39 | Seguridad: tenant/RLS/grants, CSV/file limits y flags OFF | Persistence, catalog_pack, execution y legacy Journey |
| A40 | No motores, migración, infraestructura ni despliegue productivo | Diff y alcance de comandos; ROLLOUT.md; merge no ejecutado |

Decisiones: se preservan nombres semánticos reales `transport_demand`/`transport_resources`, agregando `order_lines`; un perfil runtime v2 separado impide mezclar matemática nueva e histórica. La fracción agregada sirve para presentación/compatibilidad de ABI, el detalle por líneas contiene las cantidades físicas. El lector v2 se conserva en un rollback que tenga datos v2.

Controles de salida: FAST/FULL/required-gate deben corresponder al HEAD exacto del PR. Un run pendiente o fallido bloquea la declaración de entrega GREEN; no hay omisiones, retries automáticos ni cambios del clasificador.
