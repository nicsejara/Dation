# Runtime V2 — costos y pruebas iniciales

Misma región/recursos ADR de Saga 02; no se cambia el modelo económico ni se
promete factura cero. Supabase DDA **Free confirmado por el propietario**,
sin Pro ni respaldo restaurable obligatorio para los datos de prueba actuales.
No se contrató plan ni se crearon recursos. Billing nuevo y anterior OFF según
el propietario; estado nuevo no verificado por esta credencial (401).

El estimador existente se ejecuta sin red:

```sh
python scripts/estimate_monthly_cost.py
```

| Escenario | GCP bruto ilustrativo USD |
|---|---:|
| Idle con recovery cada 15 min y auxiliares del modelo | 3,8292/mes |
| Un piloto, 5 parejas D1/D2 × 22 días | 4,6589/mes |
| Diez pilotos, dos activaciones extra, D1 120s | 29,2821/mes |
| Smoke nominal: compute245s/control420s/API120s/build10min/red0,02GiB/log0,01GiB | 0,083310 |
| Sensibilidad: 12 reservas compute al timeout1800s, 3 recovery120s, API2×30min, mismos auxiliares | 0,597140 |

USD1 es un presupuesto **orientativo, no cap garantizado**, más cargos
persistentes/proveedores/impuestos y gastos fuera de esos supuestos. El costo
de build es equivalente al estimador: el constructor manual elegido debe
presupuestarse; no implica habilitar Cloud Build.

Jobs tiene mínimo60s por tarea, también para duplicados/ACK perdido. Recovery
cada15min implica 2.880 ticks/30días: USD3,2832 bruto Jobs, más Scheduler0,10 y
auxiliares. Dos secretos requeridos y un tercero opcional LLM no equivalen a
existencia/consumo live; el escenario conservador reserva tres versiones.

API min0/CPU por request y Jobs finitos eliminan el worker permanente. Scheduler
periódico sí genera cómputo finito aunque no haya decisiones; Registry/secretos/
logs/red y Supabase tienen sus propios límites/cargos. Créditos disponibles=0
hasta comprobar asignación; no sumar dos free tiers CPU/RAM.

Las tarifas/supuestos provienen de [costos Saga02](../finops/04_cost_inventory.md).
Revisar precios y SKUs reales antes del GO. No asumir egress gratis entre GCP
us-west1 y Supabase us-west-2, ni disponibilidad/capacidad ilimitada de Free.

Límites piloto propuestos, sin aplicar: un workspace/operador, 30 minutos de
nuevas admisiones, max_compute1, max_control1, seis admisiones globales y por
workspace/día, doce entregas/día, tres activaciones por intención; timeouts ADR
intactos. Verificar que cubran el backlog/Case. No ampliar cuotas automáticamente.

Parar nuevas admisiones por errores de contratos, permisos, resultados, Storage,
aprobación, recovery, memoria/timeout, duplicación o consumo fuera de lo acordado.
El trabajo aceptado requiere terminar/recuperarse: cerrar admisiones no cancela
su costo. Alertas USD1/5/10, si se autorizan, informan con demora y no detienen
gasto universalmente. Registrar cargos por SKU tras la demora contable.
