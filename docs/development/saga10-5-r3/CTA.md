# Auditoría CTA y eventos

Inventario browser completo en cta-audit.json; geometría width/height/rightGap/padding/borde/radio/font/icono en geometry.json. La tabla relaciona handlers y efectos con pruebas verificables.

| Acción | Guard/efecto | Evidencia |
|---|---|---|
| Seleccionar existente / cancelar | Picker verificado, no destruye draft por abrir/cancelar; busy/pending/locked bloquean | Wizard V1 test02/07/11/12 |
| Crear nuevo | Nuevo UUID/defaults/cero catálogo y checks; advertencia de descarte; no POST | R3 test02/07, V1 test02/08 |
| Cancel reset | Estado exacto anterior y copia recuperable intacta | R3 test02/04 |
| Reset pendiente | Disabled; intención/revisión/IDs no cambian | R3 test09, V1 lost-ACK/CAS tests |
| Confirmar B01/B02/B04/B05 | Errores sólo de su bloque, firma local sin publicar | R3 test05; Ultimate02; guided11 |
| Confirmar B03 | Local física+preview vigente; puede explicar datos faltantes sin abrir otros bloques; no publica | R3 test05, Ultimate01/06/07 |
| Global guardar / reintentar | Único protocolo Model+Version; CAS y body/IDs persistidos | R3 test09; V1 test03/04/05/09/10 |
| Retry Data Contract | Preview del padre, generación actual; foco sólo por intención explícita | Ultimate06; guided08; CI contract-recovery |
| Fuentes/categorías/moneda/tarifas/bases/rol/consolidación | Cambios in situ, sin abrir otros acordeones ni saltar foco | R3 test01,88 interacciones nuevo/recuperado × desktop/mobile |
| Perfil seis opciones | Actualiza profile; no transforma split ni borra soporte | R3 test06 |
| Tipo unidad | Confirm/cancel, medidas/IDs preservados, arte coherente | Ultimate03 |
| Añadir soporte/producto/presentación | Entidad blank real, refs coherentes, límites existentes | Ultimate01/04/07; guided09 |
| Duplicar / eliminar | IDs únicos, dependencias bloqueadas, Cancel no elimina | Ultimate07; guided04/09/10 |
| Elegir editor | Sólo UI/metadatos; DTO intacto. Legacy sólo tras elección explícita, o consulta publicada marcada | R3 test03/04; Ultimate08 |
| Guiado nuevo desde compatible | Advierte dos→tres CSV, copia restaurable, no conversión oculta | R3 test04 |
| Restaurar anterior | Copia exacta, confirmación si hay configuración nueva material | R3 test04 |
| Selector de presentación | Consulta, permitido readonly | Ultimate04 |
| Selector de soporte/producto | Cambia referencia: disabled y handler guardado al bloquear | Ultimate04 reforzado |
| Core anterior/siguiente | Flujos existentes y contexto preservados | Saga10 tests02/04 y CI smokes |

Los cinco footers usan confirmFooter y guided-confirm-cta. La barra tiene exactamente dos CTA hermanos. Campo ordinario no ejecuta showErrors global: usa cálculo puro y refresca errores ya solicitados sin abrir/focalizar. Los dos eventos nativos equivalentes se deduplican por snapshot. Test global inválido despacha deliberadamente el click deshabilitado para verificar el guard de publicación; no se debilita el bloqueo visual.
