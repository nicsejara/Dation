# Barreras económicas y riesgo residual

Billing debe permanecer deshabilitado durante el desarrollo. Su estado real no
pudo certificarse con las credenciales de lectura disponibles: **UNVERIFIED_LIVE**.
No se activó Billing, no se ejecutó un Job GCP, Cloud Build ni deploy productivo,
ni se escribieron datos en Supabase productivo. Docker/Postgres/Storage/fake Jobs
utilizados en validación son locales y descartables.

## Barreras implementadas

- Runtime predeterminado `jobs`, cloud execution deshabilitado por defecto;
  política SQL deshabilitada y admisiones cerradas por defecto. Fallar antes de
  reservar una entrega si falta configuración; no consumir reintentos en idle.
- API solamente acepta intención nueva si activación, IAM y recuperación están
  disponibles. Outbox y admisión persisten en la misma transacción. Fallo después
  del commit conserva el 202 y la recuperación, sin fingir ejecución exitosa.
- DB: máximo global 2 reservas compute y 1 control, 3 activaciones por intención,
  dominio con leases/fencing y límite existente de 30 min. Cuotas iniciales:
  50 admisiones/día/workspace, 500 globales, 1000 entregas/día; rechazo atómico 429.
- Jobs: una tarea, paralelismo 1 **por ejecución**, retries de plataforma 0.
  El límite global lo implementa DB; `parallelism=1` no es un límite regional.
  Duplicados/arranques con ACK perdido pueden cobrar el mínimo aun sin solver.
- API min=0/max=2/CPU por request; comando residente prohibido en el manifiesto.
  Guardia contra deployer viejo y regresiones de flags en scripts; rollback
  preserva datos y no puede elegir una revisión always-on.
- `apply` sigue bloqueado por falta de guard externo verificable. Billing OFF
  no constituye la única defensa: **MERGE_BLOCKED_DEPLOY_TRIGGER**.

## Propuesta futura: alertas y límites del proveedor

Autorizar presupuestos alert-only bajos por proyecto: USD 1/5/10 (50/80/100% y
forecast). Verificar periodicidad y destinatarios; no enviar notificaciones ni
crear presupuesto durante esta tarea. Ninguna alerta detiene automáticamente
el gasto. Cuotas duras de API/CPU/ejecuciones, si se ofrecen en esa región,
complementan los límites de aplicación, sin asumir que cubren todos los SKUs.

Google documenta [spend caps](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps)
para servicios elegibles, entre ellos Cloud Run (ID `152E-C115-5142`). Se basan en
costo bruto estimado; pueden tener retraso y sobrepasarse. Pueden detener nuevas
operaciones/causar errores 5xx; trabajo en vuelo puede finalizar, recursos con
cargos fijos y otros servicios siguen facturando. Confirmar comportamiento de
Jobs y reinicio mensual antes de aceptarlos como barrera operativa. No se
configuró ni se probó un cap live. Registry, Cloud Build, red y proveedores
externos requieren protección propia. Revisar vigencia antes del GO.

Free tier/créditos se asignan por cuenta y pueden estar consumidos por otro uso.
El estimador usa asignación disponible **cero** por defecto y un solo pool CPU/RAM
compartido entre modalidades Cloud Run; no se suman dos free tiers. No se consulta
ni administra otro proyecto para estimar esa disponibilidad.

## Qué no queda garantizado

No se promete factura cero: recuperación cada 15 min cobra un Job de al menos
60 s incluso sin cola, Scheduler/Registry/secretos/build/logs/red pueden cobrar;
Supabase puede requerir plan mensual. La modalidad técnica elimina computación
residente del worker; los ticks del control son trabajo finito explícito.
Revisar facturación real por SKU después de autorización y demora de imputación.
