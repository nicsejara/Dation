# Dation 2.0 — Saga 10 / Logistics Model 2.0

Baseline: main `f7fb4be3aa750b1c609a3579fd35e9180b40a9c9` (UX09 #125). Desarrollo en `feat/saga10-logistics-model-v2`. Fuente: paquete maestro 00–09 provisto por el propietario. No merge ni despliegue autorizado.

Implementación: wizard de cinco tarjetas dentro de Core01, catálogo inmutable opcional, unidades compartidas, presentaciones simples/mixtas, física Decimal explícita, dos o tres CSV compilados, asignación integral por línea, handoff D1 aprobado → D2 y detalle/exportación con procedencia. Se mantiene el recorrido Core/Studio, los formularios de Case, permisos, historial y operación v1.

- [Baseline, contratos y decisión arquitectónica](G0_BASELINE.md)
- [Gates y resultados verificables](GATES.md)
- [Diccionario de datos y unidades](VARIABLES.md)
- [Diseño de asignación compatible](D1_V2_DESIGN.md)
- [Matriz de aceptación](ACCEPTANCE.md)
- [Escenarios industriales y limitaciones](SCENARIOS.md)
- [Activación manual y rollback](ROLLOUT.md)
- [Evidencia real de navegador y benchmarks](evidence/)

Los flags `saga10_schema_enabled`, `saga10_ui_enabled` y `saga10_optimization_enabled` tienen default false. Los tests de integración habilitan capacidades únicamente en su PostgreSQL temporal. No se consultaron ni modificaron datos productivos. Las migraciones están preparadas en Git, sin aplicar a Supabase real. No se modificó infraestructura, Billing, Cloud Run, Jobs, Scheduler, Cloud Build ni workflows.

## Mapa de cambios

| Componente | Motivo |
|---|---|
| `domain/logistics/cargo*.py`, `physical.py` | Entidades y propiedades físicas explícitas; conservar los DTO/hash v1 |
| `data_contracts_v2.py`, `normalizers_v2.py` | Un descriptor para preview, CSV y validación; relaciones órdenes/líneas |
| `models/ultimate_foundation.py`, servicios de modelo, Pack y Journey | Snapshot completo, CAS, pre-Case privado y publicación atómica |
| Cuatro migraciones `*_saga10_*.sql` | Flags cerrados, comprobaciones de refs/slots, perfil v2 y linaje; sin backfill |
| `engines/assignment/cargo_*.py` y adaptadores de asignación | Quanta enteros y certificación independiente; política/costos vigentes |
| Kernel temporal y D2 | Admitir metadatos de categoría sin cambiar fechas/ciclos; conservar certificado D1 |
| Result contracts/assembler/canonical/export y consumidores | Extensión cargo opcional, detalle y CSV ligados al Core; bytes v1 conservados |
| `model-fields-v2.mjs`, `cargo-editor.mjs`, CSS Foundation | Cinco tarjetas, CRUD real, resúmenes y preview del servidor |
| Planning Model, Data Contract, Preparation, Case y Studio | Entidades dinámicas; proof ligado a revisión; sin rediseñar otras pantallas |
| Data Hub | Usar el mismo snapshot normalizado para OrderLines y conservar las protecciones de archivo/borrado |
| Tests, fixtures y documentación | Invariantes, oracles, regresión, industria, seguridad, evidencia y operación |

No se añaden dependencias del producto. La CLI Supabase fijada usada para generar migraciones se instaló sólo en caché temporal. No cambia la arquitectura Scale-to-Zero.
