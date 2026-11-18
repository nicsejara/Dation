# Fuera del alcance — unidad física básica sin productos

El contrato actual exige catálogo vacío en direct. Catalog necesita al menos un producto y una presentación reales. No hay un pallet físico persistente/reutilizable sin productos que derive automáticamente la carga de órdenes en modo básico.

Saga10.5 conserva esa verdad: Básico usa cantidades en CSV; Detallado guarda soportes/productos/presentaciones. La UI no crea SKU dummy, objetos ocultos publicados ni metadata ignorada por D1. El borrador UI reversible se queda en el navegador y se excluye del cuerpo API.

Una iniciativa posterior, con autorización propia, debe diseñar un arquetipo físico ligero, vínculo a órdenes, versión/persistencia/canonical hashes, compiler/normalizer/CSV, compatibilidad y efecto real en D1/D2. Necesitará gates de backend/SQL, FULL y activación controlada si corresponde. No se implementó nada de ese backend en esta saga.

También siguen fuera del contrato: nesting sobre→display→caja, packing3D, optimización del armado de pallets, multiparada, intradía y certificación térmica/hazmat. No son controles prometidos por esta UI.
