# ADR 0002 — Pantalla única de ingesta

**Estado:** aceptado  
**Fecha:** 2026-10-01

## Contexto

Dispatch v1 requiere órdenes y flota separados, pero la SPA conservaba una pantalla legacy de un CSV mezclado y una pantalla nueva que quedaba vacía cuando la migración no estaba disponible. Además, validar un CSV estaba acoplado a persistirlo en Supabase.

## Decisión

1. DDA Logística expone una sola pantalla de carga con dos tarjetas: órdenes y flota.
2. La validación es una operación sin persistencia y puede ejecutarse aun con Supabase no activado.
3. Guardar es una operación posterior y requiere que el diagnóstico de persistencia esté disponible.
4. `contracts.py` es la fuente única de columnas, alias, obligatoriedad, reglas, ejemplos y plantillas.
5. Los errores se acumulan y se muestran con fila, columna y sugerencia; no se corrige ni descarta nada silenciosamente.
6. La pantalla legacy de carga se retira, pero se conservan API y renderer necesarios para corridas históricas.
7. La biblioteca usa archivado lógico y versionado; la flota vigente no puede archivarse directamente.

## Consecuencias

- Un problema de migración ya no produce una pantalla vacía.
- El usuario puede depurar archivos antes de activar almacenamiento.
- Cambiar el contrato requiere cambiar una sola definición y sus tests.
- El endpoint de status no afirma distinguir una migración ausente de un schema cache desactualizado cuando PostgREST no aporta evidencia suficiente.
- El configurador histórico permanece temporalmente, por lo que `dispatch-enabled` todavía tiene una función de compatibilidad.

## Alternativas descartadas

- Mantener dos pantallas de carga: duplica contratos y UX.
- Validar únicamente durante upload: impide diagnóstico sin DB.
- Inferir automáticamente el baseline SQL: riesgo de versionar un esquema que no coincide con producción.


## Evolución UX v2

Se mantiene la decisión de una sola pantalla, pero se reduce el tiempo hasta el primer
valor: la ayuda extensa pasa a un drawer, la introducción sólo aparece la primera vez y
la flota vigente se reutiliza. El backend redacta findings agrupados para evitar que la
UI repita un aviso por orden.

El estado visible de cada tarjeta depende exclusivamente de `deriveCardState`. El
texto "No se guardó" sólo corresponde a errores de validación o persistencia.
