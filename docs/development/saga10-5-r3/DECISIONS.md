# Decisiones de compatibilidad

| Caso | Resultado |
|---|---|
| Nuevo limpio | Catálogo homogéneo vacío, peso+volumen, primaria peso, tres pasos y cero confirmaciones. Defaults no confirman. |
| Homogéneo representable sin edition | Guiado sin convertir negocio. UUID/referencias intactos; confirmaciones sólo si firma válida y preview vigente. |
| edition compatible antiguo, DTO representable | Selector explícito: guiado o compatible. No se monta siete pasos antes de elegir. |
| Direct sin catálogo | Dos CSV conservados. Compatible explícito, o guiado nuevo confirmado con copia restaurable. No productos ficticios. |
| Composición mixta, continuo, unidades comerciales >1 | Compatible. Componentes/cantidades/unidades siguen intactos; nunca se recorta a un producto. |
| Dimensiones pallets/units o primaria no canónica | Compatible; cambiar esos contratos afectaría al motor. No se altera silenciosamente la primaria ni se agrega pallets oculto. |
| Borrador guiado temporalmente inválido | Conserva datos incompletos, incluso selección vacía de límites, sin habilitar publicación. Permite reparar en tres pasos. Un array vacío por sí solo no prueba representabilidad. |
| Granel dentro de soporte | Perfil y tipo físico son independientes. Nuevas presentaciones guiadas son discretas; continuidad sólo en la ruta compatible correspondiente. |
| Publicado | Consulta del contrato exacto. Contexto inmutable propagado al renderer; referencias de producto/soporte bloqueadas. Ninguna conversión se envía al backend. |
| Datos compartidos | Soporte reutilizable; producto compartido bloqueado hasta duplicar; IDs nuevos sólo por acciones explícitas. |
| Reset y checkpoint | Sólo draft propio, nuevo UUID; advertencia si descarta datos o copia recuperable. Cancel no altera nada. Pending intent conserva body, version_id, revisión y reintento idempotente. |

No se detectó necesidad de cambiar backend. La geometría física existente determina665kg y1.8m³; las dimensiones del bulto son informativas y no se usan como packing. CATEGORIZED conserva grupos y pares explícitos. Líneas de órdenes cuentan presentaciones y no la dimensión técnica primaria.
