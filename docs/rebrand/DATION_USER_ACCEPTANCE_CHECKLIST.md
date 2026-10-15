# Dation — Validación end to end

Abrir [Dation](https://dation-core-469052310590.us-west1.run.app/app) con el acceso privado habitual. Usar archivos y un caso propios de prueba para recorrer nuevas ejecuciones y aprobaciones; los históricos existentes sirven para comprobar lectura, comparativa y exportación.

| Paso | Acción | Resultado esperado |
|---|---|---|
| Inicio | Abrir DDA Logística | Overview dark, explicación compacta y dos acciones distinguibles |
| Contexto | Probar nueva decisión y luego volver a un caso existente | Nueva decisión limpia el contexto; el selector recupera el caso elegido y conserva sus datos |
| Data Pack | Subir/reutilizar Órdenes y Flota; abrir validación, guía y biblioteca | Archivos y conteos correctos, errores explicados y un único CTA que continúa sólo cuando corresponde |
| Map | Abrir contexto, historial y seleccionar otra corrida | Estado, dependencias, archivos y caso coherentes; el histórico conserva su resultado |
| Asignación | Configurar objetivo, recursos, filtros y pesos; revisar y ejecutar | Resumen coincide con la elección; opciones futuras deshabilitadas; no hay selector de profundidad |
| Dashboard | Revisar cuatro KPI, evidencia, validación y exportar CSV/JSON | Valores y exportación corresponden a la corrida; menús exclusivos, cierre exterior y Escape |
| Comparativa | Generar o recuperar referencia; cerrar y reabrir | Comparación a demanda sin reemplazar el resultado original |
| Aprobación | Aprobar la Asignación de prueba y continuar | Planificación usa la fuente aprobada y conserva el lineage del caso |
| Planificación | Ajustar ventana/reglas, revisar, ejecutar y aprobar | Calendario, disponibilidad, esperas y SLA corresponden a la corrida seleccionada |
| Dation IA | Abrir/cerrar chat; preguntar sobre la corrida | Contexto correcto, historial accesible, cierre y Enviar alcanzables |
| Navegación | Recargar, volver/avanzar y abrir un histórico | Se recupera la ruta correcta, sin resultados ni controles de otro caso |
| Móvil/teclado | Repetir vistas clave en pantalla estrecha; Tab, Shift+Tab, Enter y Escape | Foco visible, contenido alcanzable y tablas/chips con scroll local |

La decisión de Asignación de vehículos sigue marcada como futura. El workspace conserva el acceso privado compartido. Nuevas Asignaciones usan el contrato essential vigente; no se presupone que produzcan el mismo plan que una corrida comparative histórica. Detalles técnicos y mediciones: [Fase 4](DATION_DARK_PHASE4_IMPLEMENTATION.md).

Para el próximo plan de ajustes, registrar por cada observación:

- Pantalla y acción realizada.
- Resultado actual y resultado deseado.
- Ancho/dispositivo y caso/corrida si aplica.
- Prioridad: bloquea el trabajo, dificulta el uso o preferencia visual.

El cierre técnico, verificaciones automatizadas y límites de cobertura están en [Fase 7](DATION_DARK_PHASE7_IMPLEMENTATION.md); los contratos visuales, en [Design System](DATION_DESIGN_SYSTEM_V1.md).
