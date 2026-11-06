# Inventario de costo y escenarios reproducibles

Precios públicos verificados 05/11/2026 ART (consultas también registradas en UTC
el 06/11). USD antes de impuestos; región `us-west1`, Tier 1. Configuración,
consumo y plan **live no verificados**. La identidad existente devolvió 401;
no se consultó otra cuenta/proyecto ni se activó Billing.

## SKUs, unidades y supuestos

| Proveedor / SKU | Precio bruto utilizado | Free tier/crédito público | Comportamiento en idle |
|---|---:|---|---|
| Cloud Run API CPU request-based | 0,000024 / vCPU-s | equivalente hasta USD 4,32 CPU compartidos | sin instancia mínima; arranque/requests cobran |
| Cloud Run API RAM | 0,0000025 / GiB-s | hasta USD 0,90 RAM compartidos | mismo criterio de asignación |
| Cloud Run requests | 0,40 / millón | 2 millones/mes por cuenta | probes/lecturas también cuentan |
| Cloud Run Jobs CPU | 0,000018 / vCPU-s | comparte pool CPU, no se suma al de API | mínimo **60 s por tarea** |
| Cloud Run Jobs RAM | 0,000002 / GiB-s | comparte pool RAM | lifetime, incluido startup, mínimo 60 s |
| Cloud Scheduler | 0,10 / job-mes | 3 jobs por cuenta; pausados cuentan | un job programado, aún sin cola |
| Cloud Tasks (alternativa A) | 0,40 / millón operaciones | primer millón | enqueue/delivery/consultas cuentan, chunks 32 KiB |
| Artifact Registry | 0,10 / GiB-mes | primeros 0,5 GiB | imágenes retenidas pueden cobrar |
| Cloud Build e2-standard-2 | 0,006 / min | hasta 2500 min elegibles por cuenta | builds por trigger, retención/red aparte |
| Cloud Logging | 0,50 / GiB ingerido | primeros 50 GiB/proyecto | retención adicional y destinos aparte |
| Secret Manager | 0,06 / versión activa-mes; 0,03 / 10k accesos | 6 versiones / 10k accesos | versiones activas pueden cobrar |
| Red GCP → Supabase/usuarios | parámetro, ejemplo 0,12 / GiB | no se asigna crédito por defecto | verificar destinos y tier real; no egress universal gratis |
| Supabase DB/Auth/Storage | Free 0; Pro desde 25/mes | depende de plan y uso | instancia propia; Free puede pausarse por inactividad |
| Netlify | Free: 300 créditos/mes | planes legacy/créditos difieren | auto-recharge/producción pueden cobrar |
| Groq/LLM | tokens × tarifa del modelo | no asumir cuota disponible | uso sólo cuando se invoca; límites propios |

Fuentes oficiales reconsultadas:
[Cloud Run](https://cloud.google.com/run/pricing),
[modalidades y CPU](https://docs.cloud.google.com/run/docs/about-instance-autoscaling),
[Jobs](https://docs.cloud.google.com/run/docs/execute/jobs),
[Scheduler](https://cloud.google.com/scheduler/pricing),
[Tasks](https://cloud.google.com/tasks/pricing),
[Registry](https://cloud.google.com/artifact-registry/pricing),
[Build](https://cloud.google.com/build/pricing),
[Logging](https://cloud.google.com/stackdriver/pricing),
[Secret Manager](https://cloud.google.com/secret-manager/pricing),
[network](https://cloud.google.com/vpc/network-pricing),
[Supabase](https://supabase.com/pricing),
[Netlify](https://www.netlify.com/pricing/),
[créditos Netlify](https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/how-credits-work/),
[modelos Groq](https://console.groq.com/docs/models).

Supabase Free publica 500 MB DB, 1 GB archivos y 5 GB egress; Pro desde USD 25,
con créditos compute de su propia organización. No se supone que producción sea
Free. Netlify publica 15 créditos/deploy productivo, 10/GB-h compute, 20/GB red y
2/10k requests. El repositorio sirve la aplicación desde FastAPI; no se agrega
hosting Netlify ni se modifica su plan. Groq hoy lista GPT-OSS-20B a 0,075/0,30
USD por millón input/output; Llama 3.1/3.3 figura Contact Sales. Son ejemplos,
**no cambio del modelo configurado** ni asunción de tarifa de la cuenta.

## Método y costo de control

`python scripts/estimate_monthly_cost.py` produce los escenarios completos por
SKU, bruto, créditos asignados y neto. `--input '{...}'` modifica campos de
`Scenario`; `--credits '{"cpu":1,"ram":0.2}'` representa disponibilidad verificada
que el propietario decide asignar. El default es **0 créditos disponibles**.
CPU/RAM usan un único pool monetario entre API y Jobs: nunca dos free tiers.
No se convierte crédito sobrante de CPU en RAM, red o Registry.

Una pareja significa **D1 y D2 como ejecuciones independientes**, con sus
aprobaciones. D1 se modela en 65 s, D2 en 5 s (cobra 60), comparativa 0,25 por
pareja (60 s), hasta cuatro proyecciones Case de 2 s (cada una cobra 60). API
suma 6 s de instancia asignada por pareja y 1000 lecturas/mes a 0,1 s; no se usa
CPU de proceso como duración facturable. Ajustar overlap de requests concurrentes
con medición live. La comparativa y Case no desaparecen del presupuesto.

Recovery cada 15 min: 2880 ticks/30 días × 60 s × (1 CPU + 0,5 GiB) cuesta
**USD 3,2832 bruto** de Jobs, más Scheduler USD 0,10. El Job termina incluso si
no hay trabajo. Elegir esta recuperación implica ese costo para garantizar
progreso sin una visita futura. Créditos disponibles podrían cubrirlo; no se
promete su disponibilidad. No se crea programación por defecto.

## Resultado de los escenarios por defecto

| Escenario | Parejas/mes | GCP bruto = neto sin créditos (USD) |
|---|---:|---:|
| Idle, control finito cada 15 min | 0 | 3,8292 |
| 1 piloto, 5 parejas × 22 días hábiles | 110 | 4,6589 |
| 1 piloto, 5 parejas × 30 días calendario | 150 | 4,9596 |
| 3 pilotos, 5 parejas × 22 días | 330 | 6,3125 |
| 10 pilotos, 5 parejas × 22 días | 1100 | 12,1001 |
| 10 pilotos, dos activaciones extra y D1 120 s | 1100 | 29,2821 |
| 1 piloto, D1 300 s y compute 2 GiB: sensibilidad, no manifiesto elegido | 110 | 5,2584 |

Los totales incluyen ejemplo de Registry 1 GiB, builds 20 min, logs 0,05 GiB,
3 versiones de secretos/3000 accesos, y 0,1 GiB de red. Esos son inputs, no
inventario de cuenta: actualizar retención/artefactos/transferencia por volumen.
El escenario idle conserva esos consumos auxiliares conservadores; no afirma
builds mensuales obligatorios. Proveedores externos se informan **separados**;
Supabase Pro añadiría desde USD 25, Netlify/LLM según plan/tokens reales.
Una descarga grande o builds repetidos pueden dominar el solver.

## Comparación A/B/C y sensibilidad

Sólo cómputo de dos decisiones pequeñas de 3 s cada una, 1 CPU/1 GiB:
A HTTP cobra aproximadamente USD 0,000159 + operaciones Tasks; B Jobs cobra
USD 0,0024 por el floor 60+60 s. Para D1 65 s + D2 5 s, B cobra aproximadamente
USD 0,0025; A unos USD 0,001855 + Tasks. API, recovery, Case, artifacts y red se
suman en ambas. C inline puede parecer barato, pero no conserva la aceptación
202 durable ni el aislamiento del solver; API de 512 MiB no cubre la muestra
grande. B se elige por integridad/simplicidad, aceptando la diferencia monetaria
medida en bajo volumen; no se declara la alternativa siempre más barata.

Las muestras pequeñas locales n=3 y el probe grande n=1 de la ADR son evidencia
descriptiva, no P95 live. El estimador admite wall-time, CPU/RAM, reintentos,
red/storage/retención y tokens externos como inputs. Máximo global DB 2 no es
un cap de gasto: duplicados que no calculan pueden cobrar startup, y la
facturación de recursos auxiliares no depende del lease. Revisar precios y
cuotas antes del GO, y gasto real por SKU después del retraso contable.
