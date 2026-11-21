# Validación J1.02

Clasificador vigente: **R3, FULL obligatorio**. No se modifica su política ni ningún workflow. Los resultados siguientes pertenecen a fixtures locales sintéticas; el cierre remoto del PR debe confirmar el SHA candidato y los checks terminales antes de declarar CI verde.

| Validación | Resultado | Evidencia |
|---|---|---|
| G0 contratos + J1.01 | 19 contratos y 14 browser PASS | `evidence/g0-*` |
| PostgreSQL 17, nuevo esquema e históricos | 35/35 PASS, 39.340 s | `evidence/g2-sql-green.txt` |
| Dominio, contratos y regresión física | 116 PASS | `evidence/g7-focal-python.txt` |
| Dominio + gates + import graph posteriores | 87 PASS | `evidence/g7-final-domain-gates.txt` |
| Certificado incompleto/timeout + gates + imports | 17/17 PASS | `evidence/g3-kpi-certificate-green.txt` |
| JavaScript individual | 31 archivos PASS; 202 subtests reportados más el script de selectores con assertions | `evidence/g7-node-direct.txt` |
| J1.02 navegador integrado | 20/20 PASS, 163.278 s | `evidence/g7-browser-stable.txt` |
| Revisión histórica → vigente → Edit | PASS, 21.309 s, sin mutar el origen al derivar | `evidence/g5-exact-review-edit-green.txt` |
| Workers D1/D2, artefactos y aprobación | 2 E2E reales locales PASS | `evidence/g3-g6-real-worker-green.txt` |
| J1.01 regresión después de cambios compartidos | 14 browser PASS | `evidence/g7-j101-r6-regression.txt` |
| R6 geometría/physics/review histórico | 10/10 PASS, 68.635 s | `evidence/g7-r6-recovery.txt` |
| Presets, selector paginado, modalidad, CUSTOM y bounds | PASS | `evidence/g4-picker-presets-green.txt` |
| Recuperación de preparación expirada | PASS, 19.061 s | `evidence/g6-expired-recovery-green.txt` |
| Capturas / geometría / contraste | 44 PNG originales, 11 escenarios × 4 anchos | `evidence/visual/README.md` |

Las filas se superponen; no sumarlas como si fueran tests únicos. FULL añade la regresión completa histórica, SQL y browser requerida. No se usa un conteo local como sustituto del required-gate remoto.

## Reproducción

Con dependencias hasheadas del repositorio, Python 3.13, Node 22, Docker y Chromium instalados:

```sh
cd backend
DATION_EXECUTION_MODE=legacy python -m unittest tests.test_decision_case_j102 tests.test_decision_case_j102_gate tests.test_frontend_import_graph -v
node tests/test_decision_case_j102_state.mjs
node tests/test_model_library_session.mjs
DATION_EXECUTION_MODE=legacy python -m unittest tests.e2e.test_decision_case_j102 -v
```

Los E2E crean y eliminan su propio entorno Docker; no configurar variables de Supabase productivo. Para SQL, usar un PostgreSQL 17 local exclusivo como los jobs vigentes (`DATION_SQL_TEST_CONTAINER`) y ejecutar `tests.integration.test_decision_case_j102` y `tests.integration.test_ultimate_case_models`. Para browser, desde `backend/tests/browser`, ejecutar `test_decision_case_j102`, `test_decision_case_j102_visual`, `test_model_library_j101` y `test_saga10_5_r6` con `DATION_RUNTIME_PYTHON` apuntando al Python del backend y `CHROMIUM_EXECUTABLE` al Chromium instalado. No lanzar fixtures Docker concurrentes en un host local sin capacidad comprobada.

## Fallos encontrados y clasificación

- **Funcional J1.02:** modo nulo después de Graph; descripción `null` al hidratar edición; captura de alias SQL; selección CSS que ocultaba la limpieza de preparación expirada; nueva sesión GET-only inexistente tras esa limpieza. Corregidos, con pruebas focales conservadas y sin debilitar assertions.
- **Control correcto del contrato:** el catálogo estático no incluía todavía el binding aditivo. Regenerado desde el registry; la assertion no cambia.
- **Fixture local / sincronización bajo ejecución concurrente:** una corrida conjunta dejó dos timeouts de montaje de ruta, un fallo de arranque TCP PostgreSQL para R6 y otro para workers. Los logs se conservan. Los mismos casos y R6 pasaron sin concurrencia y sin aumentar tiempos. No se atribuye una causa interna de PostgreSQL no capturada ni se presenta aquella ejecución fallida como verde. La ejecución integrada posterior pasó 20/20.
- **Fixture del test negativo:** los contratos son inmutables; la primera prueba intentó modificar un mapa y fue rechazada. Se construyen copias de evidencia con certificado incompleto/FEASIBLE/UNKNOWN para verificar el rechazo, sin tocar el resultado original.

## Cierre remoto

`QA-01`, `DEL-01` y `DEL-02` quedan como `PENDING_GITHUB` en la matriz del candidato: sólo pueden comprobarse después de crear el PR. El reporte de cierre del mismo PR debe registrar esos tres IDs con SHA exacto, URL, FAST/FULL/required-gate y estado OPEN/sin auto-merge. Esto evita modificar el candidato sólo para insertar su propio hash o una CI que aún no existía.

No se activaron flags productivos, motores, Jobs, Scheduler, migraciones ni despliegues. El runbook de activación requiere GO separado.
