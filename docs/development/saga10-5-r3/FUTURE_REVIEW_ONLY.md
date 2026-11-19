# Blueprint funcional diferido: navegación inversa / modo revisión

**No implementar ahora:** se documenta para siguiente saga E2E.

Cuando el usuario vuelva desde Data Contract, Decision Case o Decision Studio a un Logistics Model completado/publicado:
- Página **«Revisión del Logistics Model»** de solo lectura, visualmente grisada/sin controles interactivos, no un formulario editable disfrazado.
- Encabezado con nombre, versión, fecha si disponible, estado de publicación, CTA de navegación anterior y progreso. Cinco bloques en forma de resumen con categorías y decisiones reales: identidad, operación, unidad/presentaciones/productos y resultados físicos, flota/categorías, moneda/tarifas y precisión.
- Datos proceden exclusivamente del snapshot publicado/versionado, no de un draft mutable; no disparar revalidaciones de publicación ni modificar firmas por visitar.
- Acceso a edición sólo vía «Editar configuración» explícito y autorizado por roles. Antes de editar una versión publicada, definir política de nueva versión/CAS y efectos sobre Data Contract y Cases vinculados.
- Navegación ida: wizard de creación; navegación vuelta: revisión. Si se vuelve a edición: transición de estado explicita, sin pérdidas.
- Esta saga R3 sólo preserva navegación existente y aporta este blueprint. Cualquier sustitución de rutas ahora es fuera de alcance.
