# Saga 02 — validación y estado de entrega

> Evidencia histórica de Saga 02, integrada en #105. La adaptación vigente al
> proyecto nuevo y sus gates se documentan en [Runtime V2](../runtime-v2/README.md).
> No ejecutar pasos del proyecto anterior; la dispensa de backup de DDA Free
> está registrada en el runbook nuevo, sin modificar esta evidencia histórica.

Baseline `main` / `origin/main`: **92656a1c8c94ae1181a18c47ddd681eaa313f92b**,
posterior a #103 y #104. Branch `feat/saga02-zero-idle-runtime`.
No hay despliegue ni autorización de merge: **MERGE_BLOCKED_DEPLOY_TRIGGER**.
Billing permanece OFF por instrucción; verificación contable live
**UNVERIFIED_LIVE**, lecturas GCP 401. No se gestionó otro proyecto.

## Gates por fase

| Fase / gate | Evidencia y decisión | Estado |
|---|---|---|
| 0 continuidad / freeze | fetch, PRs y SHA, árbol inicial limpio; historial de CD y lecturas 401 | BASELINE_IDENTIFIED; freeze preservado |
| 1 auditoría focal | inventario de admisión, D1/D2, comparativas, Case, leases y worker permanente | completada, sin T0–T12 general |
| 2 ADR | matriz A/B/C, probes reales, costo/60 s floor explícitos | ADR_APPROVED_BY_TECHNICAL_EVIDENCE |
| 3 runtime | outbox transaccional, adapter Jobs administrado, proceso finito con hijo supervisado | implementado; validación local |
| 4 infra / deploy | manifiestos v2, plan/validate/apply-hold/rollback, guardias de scripts y CLI legado | implementado; no apply |
| 5 FinOps | SKU/región/unidades, bruto/créditos/neto y proveedores externos separados | estimador reproducible y probado |
| 6 QA | focales de API+SQL+Storage+Jobs fake y contenedor real | resultados abajo; CI exacta en PR |
| 7 integración | se prepara candidato dedicado; CI completa obligatoria del candidato estable | no merge hasta guard remoto verificable |

La ejecución completa requerida de GitHub corresponde al SHA de HEAD del PR que
contiene este reporte. **Este archivo se prepara antes de lanzar esa ejecución**:
no anticipa un resultado GREEN. El estado terminal, conteos y SHA exactos se
registran en el PR y en el informe de cierre, evitando cambiar el candidato por
un commit documental posterior y repetir toda la CI. Los checks de GitHub son
la fuente de verdad de ese gate; no usar los tests focales como sustituto.

## Diagnóstico del baseline y controles existentes

CI automática de main `42136495890` tuvo una falla en
`test_final_polish.FinalPolishTests.test_c1_overview_hero_has_local_art_process_and_unchanged_actions`:
`all_inner_texts()` devolvió tres textos vacíos. El candidato previo de #104
`42128924743` estaba GREEN con 1433 pruebas. Se reprodujo **exactamente el caso**
en Chromium local con los seis viewports originales: PASS sin cambios de UI ni
assertions. Se registra `KNOWN_BASELINE_CI_ISSUE`, no reproducido focalmente;
sin evidencia suficiente para afirmar un defecto funcional o cerrar el incidente
histórico. Si reaparece en CI, diagnóstico y eventual hotfix separados de Saga 02.

Contratos focales `test_dispatch_jobs` + `test_progressive_comparative`: **26 PASS**.
Activación y telemetría existentes se probaron juntos: **21 PASS** en la primera
pasada; los controles finales de release/costo/activación se registran por separado: 8 de activación, 5 guardias, 4 costos y 5 históricos de deploy, todos PASS.
Se conservan cinco tests históricos de despliegue (referencias de secretos,
cuenta/recursos, revisión nueva y distinción 403/404), además de guardias nuevas.

Una pasada local de Python existente+nuevos tests corrió **708** casos: **707
PASS**, uno de rendimiento falló en una muestra con engine+assembler 90,679 s
frente al gate existente 90 s. Coincidió con otro probe intensivo en el host de
2 CPU. No hubo cambio de motor ni de assertion. Se aisló la carga y el flujo
finito grande completó dentro de 90 s; la CI del candidato conserva todos los
probes originales. Ese resultado local no se presenta como suite GREEN. Se
agregaron luego tests del modo default y caída de DB durante el hijo, ambos PASS;
el conteo final lo informa CI.

## Matriz del runtime bajo demanda

`backend/tests/e2e/test_zero_idle_runtime.py` usa PostgreSQL 17, PostgREST,
API/Storage reales, OAuth/Auth sintético y proveedor Jobs HTTP loopback. El fake
sólo despierta procesos finitos: no sustituye solver, SQL, artifacts ni aprobación.
Su selección está prohibida en Cloud Run; no se expone un endpoint worker público.
La pasada focal final del módulo completo terminó **13/13 PASS en 90,841 s**.

| Contrato / fallo inyectado | Evidencia focal |
|---|---|
| D1 → aprobación → D2 → aprobación, graph/historial | resultado durable y upstream exacto; worker residente ausente |
| ACK del proveedor perdido, mismo UUID y admisión pausada | 202 conserva intención; duplicado terminal no recalcula |
| 503 tras commit y activación perdida | token reservado persiste; recovery sin visita crea nueva entrega |
| cuota atómica | 429, sin run ni outbox huérfanos; caso aislado repetido |
| permisos/RLS/readiness | anon/auth sin RPC, tenant ajeno/viewer denegados; 0 workers y API ready 200 |
| activaciones agotadas | intención aceptada finaliza en error, no queued infinito |
| dos claims de la misma entrega | uno claimed, otro busy; cancelación no resucita |
| solver real en contenedor readonly 1 CPU/1 GiB | termina y devuelve child exit 0; sin loop idle |
| comparativa real sin residente | resultado base idéntico, selected conservado |
| crash después de claim | nuevo fence, intento 2, resultado terminal único |
| SIGTERM durante publicación | hijo termina por señal y es recolectado; intención se recupera |
| ABA de Case (delete/reinsert con version 1) | token/epoch y updated_at impiden ACK viejo |
| capacidad global y backlog | 2 reservas compute, tercera espera; al terminar se entrega sin esperar cron |

La migración se generó con Supabase CLI **3.0.0** (`migration new` en contenedor
sin red), después se escribió SQL aditivo. PostgreSQL local aplicó el catálogo
completo y verificó defaults deshabilitados, RLS, search_path y privilegios
service-only. No se usó Supabase productivo ni se ejecutaron sus advisors live;
los controles equivalentes de catálogo se hicieron sobre la DB descartable.

Unitarios nuevos verifican modo default jobs, flag cloud cerrado antes de
reservar, timeout ambiguo, recurso/identidad administrada, fake restringido,
readiness sólo lectura y terminación del hijo. Guards negativos rechazan mínimo
1, CPU permanente, comando residente, secreto literal, test transport y apply
sin evidencia remota. Costos incluyen mínimo 60 s y un único pool CPU/RAM.

## Recursos y rendimiento observados

Ver ADR y `evidence/finite_scale_local.json`: 500 órdenes, 50 recursos, 31 días,
1 CPU/1 GiB, 128 viajes FEASIBLE y 83 artifacts: **88,140 s** desde admisión,
73,297 s de proceso supervisado y pico cgroup **763,14 MiB**. n=1, no P95 ni
latencia Cloud Run. Resultado parcial honesto; no se fabrica cobertura completa.
D2 de fuente real y comparativas ya medidos en la ADR; ninguna matemática cambió.
Telemetría añade UUIDs sanitizados, tiempos de arranque/cola/despacho/solver/
persistencia, CPU/RSS/cgroup, estimación GiB-s de asignación compute y release SHA.
GiB-s local no es factura: no incluye todo el startup ni el floor proveedor.
Sin workspace/PII/prompt/credenciales en labels; tokens de lease no se registran.

## Estado operativo y autorización pendiente

- Código, migración, manifiestos, estimador y runbooks preparados para revisión.
  `CODE_READY_BILLING_OFF` requiere completar los checks del candidato en GitHub;
  este reporte no los supone terminados antes de ejecutarlos.
- **SAFE_TO_MERGE = NO**: existe evidencia histórica de Cloud Build externo por
  main y no se pudo comprobar una barrera live independiente de Billing.
- `apply` cerrado; despliegue productivo **NOT_EXECUTED**; Supabase productivo
  **NOT_MODIFIED**; E2E/idle/facturación reales **PENDING_EXPLICIT_AUTHORIZATION**.
- Siguiente decisión del propietario: verificar guard externo y autorizar por
  separado el smoke/infra de `03_deploy_and_rollback_runbook.md`, con presupuesto
  variable propuesto USD 1 más costos persistentes inventariados, sin garantía
  de cap universal. No activar Billing ni fusionar mientras falte esa evidencia.
