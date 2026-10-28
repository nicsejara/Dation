# T12 — escenarios piloto preparados localmente

Estos archivos no están cargados en producción. No crean usuarios/workspaces, no ejecutan motores y no son fixtures permanentes. Estado general: **HOLD** por los gates del [reporte T12](../t12-rollout-report.md).

[scenarios.json](scenarios.json) fija los datos, objetivos, fechas, expectativas y referencias a tests certificados. [input-validation.json](input-validation.json) registra diez CSV válidos y un rechazo esperado, usando el normalizer del RC sin modificaciones. No es evidencia de ejecución productiva.

Cada carpeta A–E contiene `model-configuration.json`, `transport_demand.csv` y `transport_resources.csv`. E incluye además `transport_demand-duplicate-invalid.csv`; ese archivo debe fallar validación, no publicarse ni ejecutar una Run.

## Procedimiento cuando los gates permitan el piloto

1. Identificar 1–3 workspaces controlados y usuarios reales con roles Admin/Owner/Viewer. Mantener fuera del piloto a todos los demás mediante gating server-side certificado. No reutilizar UUIDs del sandbox ni service role como token de usuario.
2. Crear/publish Model con la configuración del escenario y crear Case sintético con horizonte semanal 2026-11-02 a 2026-11-08, `MINIMIZE_COST`, Data Owner y Decision Owners elegibles. Usar nombres `[DATION SYNTHETIC PILOT]`.
3. Descargar templates del Model Version real, comprobar que sus columnas/configuración coincidan y usar su contract hash para validar/subir/publicar los CSV. Los hashes de `input-validation.json` son sólo locales y no se reutilizan en las APIs reales.
4. D1: Config contextual, admisión, worker real, COMPLETED, fingerprint y artifacts READY. Revisar Sankey, detalle, export, Approval Review y excepciones antes de aprobar. En C no ocultar la cobertura parcial ni su reason.
5. D2: exacto D1 aprobado, Config D2, admisión/worker, resultado, fechas/ciclos/Gantt/export/review/aprobación; no cambiar las asignaciones de D1. En D verificar reutilización OWN con intervalos exclusivos; en E disponibilidad asumida y margen cero explícitos.
6. Releer cada Run/package/manifest/artifact/export, comprobar fingerprint y lineage después de reload. Conservar historia; ninguna limpieza de datos comerciales ni DELETE de evidencia.
7. Verificar roles/tenant, IA contextual/fallback y observabilidad del pipeline/worker/API/frontend durante la cadena. Registrar duración de D1/D2, retrieval, dashboard, artifacts e IA. No ampliar automáticamente.

Los resultados numéricos esperados se referencian a fixtures T7/T9 certificados. La nueva Run tendrá IDs, hashes de contexto y fingerprints propios. Comparar todos sus consumers entre sí; no imponerle el fingerprint de una fixture de QA.

## Captura de hallazgos

Registrar severidad P0–P4, build/digest/schema, workspace, Case/Run/fingerprint, paso, esperado/observado, timestamp, evidencia y reproducción mínima sin secretos. P0/P1: detener expansión; P2: evaluar antes de expandir; P3/P4: backlog. Ante un fallo de integridad/seguridad/lineage, cerrar admissions del perfil afectado y aplicar el rollback certificado conservando datos/historia.
