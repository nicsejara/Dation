# Diccionario de variables y procedencia

| Entidad / variable | Unidad / contrato | Consumidor / regla |
|---|---|---|
| Model `version=1` | Configuración histórica | Bytes y hash v1 preservados; dos CSV |
| Model `version=2` | JSONB publicado inmutable | Hash `logistics_model_configuration_v2`; registry `SAGA10_DOMAIN_V2` |
| Product `product_id`, name/code/category | ID local al snapshot, nombre/código únicos | Referencias internas; no catálogo global mutable ni Products.csv obligatorio |
| `unit_label`, `units_per_package` | Nombre del bulto, entero ≥1 | Unidades = bultos por presentación × unidades por bulto × cantidad |
| Product `gross_mass`, `net_mass` | kg o t | Bruto positivo; neto informativo y no mayor al bruto; sin inferir tara ausente |
| Product `dimensions`, `density_kg_per_m3` | m/cm; kg/m³ | Dimensiones informativas, densidad sólo explícita |
| LogisticUnit `logistic_unit_id`, type | PALLET/BOX/CRATE/BIG_BAG/OTHER | Reutilizable por muchas presentaciones; referencias no clonadas |
| `empty_dimensions`, `tare_mass`, `structural_limit_kg` | m/cm, kg/t, kg | Exterior vacío no sustituye al cargado; límite requiere bruto conocido |
| LoadPresentation `presentation_id`, components | ID; producto/cantidad por presentación | Uno o más productos; sin referencias recursivas/nesting ni armado automático |
| `loaded_dimensions`, `external_volume` | m/cm, m³/litros | Exterior cargado como envelope escalar; discrepancias se rechazan |
| `gross_mass`, `extra_tare_mass` | kg/t | Compuesto de brutos + tara logística + tara adicional, o declaración válida |
| `quantity_kind`, `quantity_unit` | DISCRETE/presentation o CONTINUOUS/kg,t,m3,l | Discreto entero; granel un material por unidad física, sin unidades anidadas |
| `allocation_increment` | Incremento explícito de la unidad de presentación | Mínimo múltiplo de 0,001 que conserva todas las escalas; discreto =1 |
| `coefficients`, `provenance` | kg(3), m³(6), pallets(3), units(3) | Decimal / ROUND_HALF_UP; fuentes declaradas/derivadas y precisión fijadas |
| `stackable_metadata`, `orientation_metadata` | Informativo | No restricciones de packing/ejes/carga certificadas |
| `primary_dimension`, active_dimensions | Una dimensión común positiva por presentación | Objetivos sobre primaria; capacidades garantizadas en todas las activas |
| `split_policy`, order.split_allowed | INDIVISIBLE / DISCRETE / CONTINUOUS | Intersección modelo/orden; no relaja la integridad discreta de ninguna línea |
| `consolidation_permitted` | Boolean | Permite varias órdenes por Trip; independiente de split |
| `compatibility_policy`, co_load_pairs | Declaración uniforme o matriz explícita simétrica | Co-carga entre productos separada de elegibilidad carga→recurso |
| `resource_categories` | Categorías explícitas opcionales | Filtro del recurso, sin prometer certificación térmica/hazmat/compartimentos |
| `transport_demand` | CSV Orders real: IDs, ruta/distancia/fechas/prioridad | Directo: cantidades activas; catálogo: cantidades provienen sólo de líneas |
| `order_lines` | CSV order_id,presentation_id,quantity | UUID5 por ModelVersion/orden/presentación; no pares duplicados ni huérfanas |
| `transport_resources` | CSV Fleet, capacidades/fuentes/disponibilidad/costos | Contrato dinámico y capacidades garantizadas; categorías si están configuradas |
| `catalog_hash`, normalizer_version | SHA256, DATION_CARGO_INPUT_NORMALIZER_V2 | Fijan catálogo y política física, reutilización sólo bajo el mismo snapshot |
| `cargo_assignment_v2` | Detalle tipado por Trip/orden/línea | requested=assigned+unserved; cantidades, productos, unidades y cargas exactas |
| `allocation_fraction` histórico | Ratio primaria asignada / solicitada, 6 decimales | Presentación agregada; nunca convertir porcentajes de orden mixta en productos |
| D2 source binding | Run ID / result fingerprint del D1 aprobado | Trips, recursos y detalle cargo exactos; sólo programa días |
| Costos | Moneda / minor_units / ROUND_HALF_UP | OWN km ×2×rate; externo PER_TRIP o PER_KM ONE_WAY/ROUND_TRIP, sin tarifas nuevas |

Límites explícitos: hasta 100 productos, 50 unidades compartidas, 200 presentaciones, 30 componentes por presentación; CSV ≤10 MB /10.000 filas; admisión ≤500 órdenes/500 líneas/50 recursos; búsqueda predeterminada ≤128 candidatos/20.000 variables con máximos 256/30.000 y presupuesto de restricciones. El límite que se excede se informa; no se sustituye una relajación continua ni se afirma cobertura u óptimo sin prueba.
