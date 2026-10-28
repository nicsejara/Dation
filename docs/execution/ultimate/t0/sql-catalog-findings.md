# T0 — Catálogo SQL y reconciliation

Inspección Supabase exclusivamente de metadata: proyecto `gijiinufjjurgfeehufj`, PostgreSQL17.6. No se consultaron filas de clientes, contenido de Runs/CSV, tokens ni datos Auth. Las únicas filas de configuración leídas fueron los flags globales de `platform_release` y metadata del bucket. Ningún write/migration/repair/grant/RLS se ejecutó en remoto.

## Catálogo efectivo

[Snapshot](evidence/sql-catalog-live.json), [metadata extendida](evidence/sql-extended-metadata-live.json), [funciones críticas](evidence/sql-critical-functions-live.json).

| Área | Estado observado |
|---|---|
| Tablas | 26:19 públicas y7 privadas; las19 públicas tienen RLS |
| Columnas | 269 entre ambos schemas;232 públicas |
| Constraints | 187 totales;161 públicas |
| Índices | 90 totales;79 públicos |
| Policies | 17 |
| Funciones | 101, con firma/argumentos/result/config/ACL/security-definer/hash registrados |
| Triggers no internos | 46, con binding/enable/definición registrados |
| Grants de tabla observados | 284 entradas para los schemas de aplicación |
| Runtime flags | admissions_open=true; workflow_gates_enabled=true; no modificados |
| Storage | `dda-inputs` privado,10MiB; MIME CSV/Excel/texto, sin JSON/JSONL habilitado |

No existen todavía las tablas Ultimate de Models/Packs/result artifacts. No se crearon durante T0.

## Git, baseline y history

[Ledger de migraciones](evidence/migration-reconciliation.json), [history remoto](evidence/sql-migration-history-live.json), [rebuild/comparación](evidence/sql-git-rebuild-comparison.json).

- Git contiene31 archivos de migración. El baseline capturado es `supabase/baseline/20261010100000_public_schema.sql`.
- El history remoto contiene10 entradas y termina en `20261005012207`. Algunos nombres/timestamps anteriores tampoco coinciden literalmente con los filenames Git. No se presupone equivalencia de statements a partir del nombre.
- En una base nueva del contenedor owned T0 se aplicó el baseline capturado y los23 archivos posteriores a su cutoff:24 archivos en total. Se usó la misma forma de Auth fixture del E2E actual. Esa base se eliminó al terminar cada comparación.
- **Coincidencia exacta** en tablas, columnas, constraints, índices, policies, las101 funciones —incluyendo source/definition hashes y seguridad— y46 triggers.
- Por tanto, el history no describe toda la expansión efectiva actual. Reejecutar el baseline o los upgrades sobre producción basándose en esos10 registros sería incorrecto. No se hizo repair ni se marcaron migraciones aplicadas.
- La comparación con la auditoría anterior coincide en los campos disponibles:232 columnas,161 constraints públicas,79 índices públicos,17 policies y firmas/ACL/config de101 funciones. Se usó el mismo modo de `pg_get_constraintdef`; pretty=true sólo produce diferencias de formato, no drift.

Esto es un ensayo del schema **actual** para T0; no implementa el helper Ultimate de T2, no crea nuevas migraciones y no certifica los contratos futuros.

## Diferencias explícitas de privilegios/configuración

El rebuild tiene266 grants de tabla frente a284 en producción. Las18 entradas adicionales remotas son de **service_role**, exclusivamente:

- DELETE/TRUNCATE/REFERENCES/TRIGGER sobre profiles, workspace_ddas, workspace_members y workspaces:16 entradas.
- REFERENCES/TRIGGER sobre audit_events:2 entradas.

No hay grants adicionales a anon/authenticated dentro de esa diferencia. Se capturaron también las ACL de los dos schemas y los6 default ACL de Supabase para public; el sandbox genérico tiene0 default ACL. Las ACL literales de schema difieren y se conservan en el JSON para no asumir igualdad administrativa completa. Los defaults gestionados de Supabase otorgan privilegios amplios a roles de plataforma al crear objetos: un sandbox Postgres genérico no reproduce por sí solo ese contexto.

**Impacto:** la ruta de reconstrucción reproduce objetos/funciones/guards de aplicación, pero no es una copia idéntica de la administración de privilegios de Supabase. Antes de una futura expansión T2 hay que contemplar esos defaults y probar grants/RLS efectivos, conforme al plan aprobado. Ninguna recomendación autoriza otorgar ALL, revocar permisos a ciegas o cambiar producción en T0. Esta diferencia queda reconocida como hallazgo de M0; no exige reabrir la arquitectura ni bloquea por sí sola los contratos puros T1.

## Límites de observación

- Metadata y funciones actuales se leyeron en snapshots separados con timestamp de captura. No se guardó un backup de datos ni se afirmó ausencia de writes comerciales concurrentes.
- El Postgres owned ejecutó17.11 con imagen/digest registrados; producción es17.6. Ambos son major17 y los objetos comparados coinciden, pero no se equiparan sus imágenes ni defaults administrados.
- B-SQL usa su SQLSandbox histórico que sólo aplica upgrades anteriores a `20261018090000`; sus46 PASS no cubren por sí solos toda la plataforma. El rebuild completo y B-E2E usan el schema actual; sus resultados se informan por separado, sin ocultar fallos.
- GET administrativo Cloud Run devolvió401: no se recertifican revisión, variables, secretos o IAM. GET productivo health/OpenAPI pasó, sin write ni deploy.

## Acción mínima recomendada

Conservar los snapshots y este mapa como baseline antes de cualquier migración futura. En la fase correspondiente, ensayar la expansión sobre el catálogo/defaults/grants reales reconocidos y mantener readers/worker compatibles. No reparar history ni grants automáticamente. El estado STOP/GO global depende además de las suites y deuda individual del reporte T0.
