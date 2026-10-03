# ADR 0008 — Decision Case y Decision Map

Estado: implementado en Fase 2.

## Contexto

Fase 1 separó el Logistics Data Pack de la cadena de decisiones mediante Decision Readiness, pero el usuario todavía navegaba directamente desde Cargar datos hacia Configurar decisión. Esa navegación no representaba que:

- Assignment es una decisión distinta de Scheduling;
- cada decisión tiene estado propio;
- una decisión posterior depende de aprobación humana upstream;
- cambiar la evidencia invalida decisiones previas.

## Decisión

Dation incorpora un **Decision Case V1** y un **Decision Map** como capa de orquestación entre datos y motores.

El caso se identifica por:
- `case_id`;
- `orders_dataset_id`;
- `fleet_dataset_id`;
- los estados de cada nodo de decisión.

La cadena inicial es:

1. `logistics_assignment`
2. `logistics_scheduling`
3. `logistics_final_assignment`

## Estados

Los nodos pueden usar:

- `AVAILABLE`: datos y dependencias permiten comenzar;
- `RUNNING`: hay una ejecución en curso;
- `REVIEW`: existe resultado pero requiere validación humana;
- `APPROVED`: el usuario aprobó explícitamente el resultado;
- `LOCKED`: una decisión anterior todavía no fue aprobada;
- `NEEDS_DATA`: dependencia satisfecha, pero faltan variables requeridas;
- `ERROR`: falló la ejecución;
- `STALE`: el caso quedó desactualizado porque cambió la evidencia.

## Reglas de desbloqueo

Assignment queda AVAILABLE cuando Decision Readiness confirma el núcleo mínimo y compatibilidad del Data Pack.

Scheduling:
- permanece LOCKED hasta que Assignment sea APPROVED;
- luego queda AVAILABLE si su Data Readiness está completo;
- en caso contrario queda NEEDS_DATA.

Final Assignment:
- permanece LOCKED hasta Scheduling APPROVED;
- luego depende de su propio Data Readiness.

En Fase 2 sólo Assignment tiene motor ejecutable. Mostrar Scheduling como AVAILABLE no implica que el motor ya exista; la UI lo comunica explícitamente.

## Aprobación humana

Una corrida completada no se considera automáticamente aprobada.

Transición:

`RUNNING → REVIEW → APPROVED`

La aprobación sólo puede ejecutarse para una corrida cuyo `decision_case.case_id` coincide con el caso activo. Corridas históricas sin lineage de caso no pueden aprobar el caso actual.

## Cambio de datos

El caso usa una firma basada en los IDs de Orders y Fleet.

Si cambia cualquiera:
- se crea un Decision Case nuevo;
- el caso anterior se conserva como `stale_predecessor`;
- una aprobación previa no se reutiliza.

## Persistencia

No se crea una tabla nueva en Fase 2.

El estado completo del caso vive temporalmente en `sessionStorage` para navegación dentro de la sesión.

Las corridas persistidas guardan:

```json
{
  "decision_case": {
    "case_id": "...",
    "node_id": "logistics_assignment"
  }
}
```

en `configuration_json` y `result_json`.

Esta metadata se agrega después del cálculo y no altera el `result_fingerprint`.

## Consecuencias

Ventajas:
- UX representa la cadena real de decisiones;
- separación explícita entre data-ready y decision-ready;
- aprobación humana visible;
- lineage de corridas;
- cambio de evidencia invalida aprobaciones previas;
- no requiere migración Supabase.

Limitaciones:
- la aprobación no es durable fuera de la sesión;
- sólo Assignment tiene ejecución;
- Scheduling y Final Assignment todavía no generan resultados;
- no existe aún historial persistente de Decision Cases.

Estas limitaciones se resuelven en fases posteriores al separar motores y persistir eventos de aprobación.
