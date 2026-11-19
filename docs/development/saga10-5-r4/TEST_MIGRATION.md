# Migración de pruebas al contrato R4

R4 prohíbe expresamente editar catálogos históricos, los seis perfiles, CRUD técnico, wizard de siete pasos y el selector de editor compatible en las nuevas rutas. Las pruebas de Saga10/R2/R3 que exigían esos controles se adaptan a las acciones públicas Guardar/Actualizar y al visor histórico de solo lectura; no se conservan renderers ocultos ni rutas exclusivas para hacer pasar tests.

| Suite anterior | Verificación preservada / reemplazo normativo |
|---|---|
| Saga10 wizard 01/03 | Guardado y publicación reales; dos tipos homogéneos/soporte compartido; directo histórico conserva dos CSV y cero catálogo ficticio |
| Saga10 wizard 02/04 | Sin cambios: relaciones de tres CSV, reparación, reload, creación de Case, hashes stale/mismatch |
| Guided 01–04 | Histórico directo, mixto, perfiles, unidades comerciales, códigos e IDs íntegros en lectura; física validada por API |
| Guided 05/07/09/10/12 | Rechazo backend de física incompleta/contradictoria, densidad continua, límites 100/50/200/30 sin truncar, primaria/pairs/moneda preservados, procedencia de peso declarado |
| Guided 06/08/11 | Stale preview, 503/retry sin pérdida e invalidación; errores locales accesibles sin saltos |
| Ultimate Pro 01/03/04/05/06/07/08 | Escenarios R4 compartidos: física, cinco unidades, dos tipos/edición, cinco anchos/a11y, stale/retry, restricciones/split y revisión legacy |
| Ultimate Pro 02 | Se conserva la prueba de roles, fuentes, tarifas, bases y precisión de moneda |
| R3 01/02/03/05/09 | Conserva las aserciones de navegación/scroll/foco, reset/cancel, recuperación por firma, errores locales y lost-ACK/idempotencia |
| R3 04/06/07/08 | Consulta/recovery sin conversión, cinco unidades discretas, nuevo desde publicado y geometría/a11y del renderer definitivo |

`r4_model_helpers` centraliza acciones públicas; reutilizar un escenario entre suites evita divergencia en fixtures. El reporte distingue ejecuciones de escenarios de cobertura distinta. No se usan skip, sleeps, retries de test, modificaciones de classifier, políticas, ni activación de motores.

Los 70 tests backend de contratos/frontend/normalización/física/D1 originales se conservan sin cambios. El dry run adicional usa el DTO que publicó el navegador; no llama `/runs` ni realiza ejecuciones productivas.
