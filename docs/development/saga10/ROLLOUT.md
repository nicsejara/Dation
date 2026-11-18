# Activación propuesta y rollback — no ejecutar en esta tarea

No merge, migración productiva, imagen Docker, despliegue ni promoción de tráfico fue autorizado. El PR es revisable; no equivale a un GO. No se modifica el historial de Supabase ni se repite UX04 `20261114225017`.

## Gates antes de cualquier activación

1. Revisar SHA del PR y CI obligatoria FAST/FULL/required-gate. Resolver conflictos sobre el main real. Obtener autorización de merge separada; comprobar que no active una ruta de despliegue sin GO.
2. Confirmar en el entorno de destino qué versiones SQL ya existen, mediante lectura. Si persiste el historial UX04 pendiente de reconciliar, decidir explícitamente su reconciliación con evidencia, sin repetir SQL sobre producción.
3. Ensayar los cuatro archivos Saga10 y su orden en staging/base aislada con el esquema real, RLS/grants/CAS/immutability. Esta tarea verificó un PostgreSQL17/PostgREST/Storage local con el catálogo completo de migraciones.
4. Registrar plan de recuperación. El propietario dispensó el backup restaurable para el entorno de pruebas DDA FREE y aceptó pérdida de datos operativos descartables; no extender esa dispensa a otro entorno ni ejecutar un reset. Estas migraciones no necesitan borrar datos, recrear tablas ni transformar modelos anteriores.

## Orden exacto de migración aditiva

Los archivos fueron generados con CLI Supabase fijada y sólo probados localmente:

1. `20261117234035_saga10_logistics_model_v2.sql`: tipos de configuración JSONB, validaciones y tres flags false; conserva RPC v1 privados y fachada autorizada.
2. `20261117235546_saga10_catalog_data_contracts.sql`: entidad OrderLines, constraints/índice parcial y selección/publicación dinámica, dos slots v1 o tres catálogo.
3. `20261118034739_saga10_cargo_execution.sql`: runtime D1v2 exacto, read-set, snapshot completo, Core hash y comprobación independiente del gate de optimización, incluida disponibilidad D2.
4. `20261118040429_saga10_data_hub_lineage.sql`: proyección de archivo de OrderLines; conserva referencias y bloqueos de borrado.

No incluir otras migraciones pendientes automáticamente. Generar y revisar el dry-run del comando oficial de migraciones contra el destino correcto antes de un GO específico de SQL. No entregar ni ejecutar `db reset` o un `db push` irrestricto como paso de activación.

## Despliegue posterior (requiere GO)

- Publicar una imagen del SHA integrado y validado con el runbook manual vigente; fijar digest. No crear nuevos workflows, IAM, triggers, Scheduler ni procesos residentes.
- Mantener API min_instances=0, límites de recursos, CPU por solicitud y los guardrails de outbox/Jobs/leases/cancelación existentes. No hay cambios de infraestructura en Saga10.
- Primera promoción: flags Saga10 OFF y motores/D1/D2/cómputo cerrados. Smoke legacy login → Core → datos → Case → Graph; lectura de resultados e historial anteriores.
- Habilitar esquema y UI v2 sólo después de un GO de producto para pruebas controladas. Conservar `saga10_optimization_enabled=false`, las admisiones cerradas y `DATION_CLOUD_EXECUTION_ENABLED=false` mientras no exista GO de motores. Probar modelos directos/catálogo, template exacto, error de filas/relaciones, reuso, borrador y creación sin ejecutar corridas.
- Activación de D1v2/D2 es un GO posterior: calificar el perfil3.0.0 sobre datos del piloto, todos los límites, permisos, presupuesto/leases, aprobación humana y recuperación. No activar el registro público ni flags globales sólo porque el workflow o el wizard estén verdes.

## Rollback seguro

Primero cerrar optimización/admisiones y UI v2 por el mecanismo autorizado existente. No borrar modelos, presentaciones, inputs, Runs ni paquetes. Conservar lectores compatibles con v2 y las columnas/checks aditivos.

- Si todavía no existen publicaciones/corridas v2: un rollback de imagen al digest anterior puede proponerse tras verificar compatibilidad y los gates de publicación; no se ejecuta aquí.
- Si hay datos v2: no volver a una imagen que sólo comprende v1. Mantener lector v2 y corregir hacia adelante, o preparar una imagen compatible con v2 pero con nueva creación/ejecución deshabilitada. Conservar hashes, IDs y paquetes históricos.
- Las cuatro migraciones son aditivas y no tienen un down destructivo. No quitar constraints/funciones/entidades nuevas mientras haya referencias. Los cuerpos originales privados se conservan para compatibilidad, no para habilitar acceso directo.

Riesgos residuales: mayor cantidad de variables y memoria para enteros por línea; precisión canónica del granel; envelope de volumen no es packing; límite explícito de fracción histórica para asignaciones diminutas; SQL falla si no reconoce su ancla de baseline; bibliotecas/infraestructura productiva y reconciliación de historial no se verificaron en vivo en esta tarea. Benchmark sintético no es SLA ni estimación de gastos. Ninguna prueba local genera costos de GCP ni afirma el estado actual live de Billing.
