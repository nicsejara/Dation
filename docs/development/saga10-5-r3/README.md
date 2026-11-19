# Saga10.5 R3 — Corrección de UX, estado y navegación

R3 corrige la experiencia de main `1a1e39e365676972fb26a0c30a797d56a134ca97`, merge de PR128. Medición iniciada el19/11/2026 a11:31:07 Argentina (14:31:07UTC). El SHA final, tiempos terminales y CI se registran en el PR al terminar, evitando otro commit que duplique CI.

## G0 — Reproducción real

Las tres pruebas nuevas fallaron sobre el baseline: navegación entre bloques, reset y recuperación de borrador. Los70 tests de contratos/física/D1 pasaron antes y después. No se accedió a la sesión productiva ni se presupone conocer el metadato exacto de la captura del usuario.

En fixture aislado con B03 parcial cerrado, el click OWN abrió B03 y desplazó559px; categoría también lo abrió; USD lo abrió y desplazó69px. Se conservaron snapshots de openBlocks, scroll, foco y atributos invalid, y capturas antes/después: [JSON](evidence/baseline-navigation.json), [reproducción](evidence/baseline-nav.txt).

Causas confirmadas: planning-model.edit llamaba a showErrors global en input/change, que abría details inválidos. Además se aisló la validación focusout del formulario común para impedir reapertura implícita del modelo. El guard de R2 exigía edition=ultimate y perpetuaba siete pasos aunque el catálogo fuera representable. startNew enfocaba o recuperaba el draft anterior en vez de crear uno.

## G1–G4 — Implementación

- Validación pura sin navegación; errores locales sólo al CTA local; errores globales sólo al publicar. Se actualizan errores ya solicitados sin abrir/focalizar bloques. Eventos input/change equivalentes se deduplican por snapshot. Preview conserva debounce, generation y firma actual.
- Crear nuevo genera UUID, configuración y firmas vacíos. Descarte confirmado si hay cambios o copia recuperable; Cancel conserva todo. Se invalidan timers/respuestas antiguas y se reemplaza sólo el draft propio. Publicación pendiente/locked/busy y permisos bloquean el reset.
- La evaluación del DTO decide si hay tres pasos; no se convierte por un metadato arbitrario. Se conservan IDs, cantidades, tara, exterior cargado, orden de dimensiones y categorías/pares. Marca compatible antigua requiere elección explícita; ausencia de marcador con DTO homogéneo representable abre guiado.
- Direct/mixed/continuous/unidades comerciales/dimensiones o primaria no representables muestran selector antes de montar el editor. Sólo tras elección existe el DOM legado. Se puede iniciar guiado nuevo con confirmación, copia recuperable y restauración; el modelo directo no cambia a tres CSV a escondidas.
- Perfil de seis tarjetas dentro de Paso1, separado de tipo físico. Granel puede seguir siendo discreto: cambiar perfil no cambia split ni crea continuidad. El catálogo es el mismo estado/DTO del editor existente.
- Barra sin copy repetido; ayuda de campos antes del input sólo en Model; DIRECT y OWN en bandas compactas; fuentes/categorías/tarifas y cinco CTA uniformes conservados.
- Publicados v1/v2 no se reescriben. En la consulta guiada se bloquean también los selectores que cambian referencias; los selectores de vista permiten consultar otra presentación.

## G5–G6 — Validación

Ver [resultados](evidence/results.json), [contratos](evidence/contracts.txt), [regresión inicial](evidence/browser-regression.txt) y [cierre focal](evidence/focused-final.txt). El registro conserva los fallos encontrados y corregidos, sin ocultarlos con sleeps/retries. Las pruebas actualizadas expresan las nuevas reglas: reset real y errores sólo tras intención local/global; conservan aserciones de datos, identidad, publicación, inmutabilidad y freshness.

El circuito es R2/FAST sólo si lo confirma el clasificador real; no se cambian políticas. Los recorridos nuevos se ejecutan localmente aunque FAST seleccione sólo sus cuatro smokes. FULL se ejecuta únicamente si la clasificación lo requiere. No se modifica la allowlist de autopublicación: los módulos centrales quedan fuera, NO_AUTO_DEPLOY.

[35 criterios R3](ACCEPTANCE.md) · [revalidación de103 criterios anteriores](ACCEPTANCE_HISTORY.md) · [inventario CTA](CTA.md) · [decisiones](DECISIONS.md) · [release/rollback](RELEASE.md) · [review-only futuro](FUTURE_REVIEW_ONLY.md).

## Evidencia visual

[Índice completo antes/después](VISUALS.md): cinco bloques en1536/1024/768/390/320, selector explícito y editor compatible; [mediciones](evidence/geometry.json), [contraste](evidence/a11y.json), [trazas navegación](evidence/navigation.json), [CTA DOM](evidence/cta-audit.json). Capturas reales del browser, sin retoque; baseline y R3 usan el mismo escenario sintético físico.

## Archivos y límites

model-editor-mode evalúa representabilidad y ofrece elección sin tocar datos. model-fields-v2 implementa APIs de validación y el wizard; cargo-editor conserva el catálogo y distingue cambios de referencias de navegación readonly. planning-model controla reset, checkpoint y preview; model-fields propaga contexto publicado; guided-ui añade helper opt-in; CSS queda scoped. Tests y documentos completan el diff. No backend/API/SQL/motores/flags/Supabase/infra/workflows/dependencias.

La copia recuperable vive en el draft del navegador, no es una copia productiva de base de datos. La futura página review-only queda documentada; no hay ruta nueva de navegación inversa en este PR. No merge, imagen, despliegue ni promoción de tráfico.
