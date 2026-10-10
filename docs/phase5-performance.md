# Fase 5: rendimiento del workspace

El selector de casos repetía lecturas de los mismos Data Packs y abría clientes
HTTP por operación. Tras Fase 4, cada caso añadía dos lecturas de datasets y una
de historial: **1 + 3N** peticiones REST (10 para tres casos; 301 para cien),
incluso cuando todos compartían archivos. Esto corresponde al hallazgo F10.

## Comportamiento y presupuesto

`GET /api/decision-cases` realiza **una petición** a la función SQL
`list_decision_cases`, para páginas vacías o de hasta 100 casos. Datasets, conteos,
última ejecución y aprobación vigente se leen en un único snapshot. El orden es
`last_activity_at DESC, id DESC`, estable también cuando coinciden las fechas.
No se descargan resultados, configuraciones ni resúmenes pesados de las corridas
para reconstruir los estados de los nodos.

El selector solicita `summary=true`: cada dataset contiene únicamente identidad,
tipo y nombres. Mantiene métricas, badges y actividad, y carga el Data Pack completo
al seleccionar un caso. La respuesta sin este parámetro conserva los campos
anteriores. El detalle y las páginas de historial conservan sus contratos de Fase 4.

Las conexiones a Supabase se comparten por proceso/event loop durante el lifespan
de la API y del worker: 32 conexiones como máximo, 16 keepalive, expiración de
30 segundos. Se cierran al terminar, incluso ante cancelación. Scripts y tests sin
lifespan crean un cliente temporal y lo cierran. Cada operación conserva su timeout
original y sus headers; las respuestas y las aprobaciones se vuelven a consultar.

## Despliegue

1. Ejecutar CI, incluidas las regresiones SQL con PostgreSQL 17 real.
2. Aplicar la migración aditiva con `python scripts/apply_production_performance.py`.
   El token administrativo se toma de la configuración segura. El script verifica
   prerrequisitos, definición exacta, límites, lectura sin escrituras y permisos.
3. Integrar en `main`; Cloud Build publica la misma imagen en worker y API, en ese
   orden, y espera a que el worker esté listo.
4. Verificar el hash del módulo publicado, autenticación, lista completa y compacta,
   igualdad de estados, apertura del caso e historial en navegador.

Un rollback vuelve a la imagen anterior en ambos servicios. La función nueva
puede permanecer instalada: es aditiva y no modifica datos ni contratos anteriores.
No se reinicia producción para simular fallos ni se cambia la flota por defecto.

## Evidencia y límites

Las regresiones verifican una petición para 0/3/100 casos, ausencia de hidratación
por fila, datos completos compatibles, orden/paginación, conteos de 1.006 corridas,
aprobación fuera de la página, actualización inmediata de aprobaciones y estado
stale. SQL corre sobre el baseline real y todas las migraciones. Un plan
`EXPLAIN ANALYZE` de 100 casos con 5.100 corridas sintéticas verifica lecturas por
índices y exclusión de resultados pesados. Chromium abre un selector de 100 tarjetas
con una sola petición de lista y obtiene el detalle al seleccionar.

CI espera al servidor PostgreSQL definitivo mediante TCP dentro del contenedor,
sin publicar puertos. El servidor temporal de `initdb`, accesible únicamente por
socket, no permite iniciar los tests antes de que termine la inicialización.

La línea base productiva, antes del despliegue, contiene cinco casos activos y
87.613 bytes: 10,539 s en la primera solicitud; 1,382 y 1,222 s en las siguientes.
Estas son tres observaciones desde el entorno de desarrollo, no un p95 ni una
prueba de carga. La comparación posterior y los identificadores de CI/Cloud Build
se registran en el PR de publicación. No se añaden índices sin evidencia ni cachés
de larga duración que puedan mostrar aprobaciones obsoletas.
