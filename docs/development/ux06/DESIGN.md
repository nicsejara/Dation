# UX06 — diseño y continuidad

G0: main `b9c9967ad0285d0cb0e873fa359a839ad1fb492b`; PR120 integrado. CI post-merge43761427658: impact/FAST/FULL/required-gate GREEN. Sin otro PR abierto de navegación. Worktree propio limpio al crear rama `feat/saga-ux06-navigation-journey-refinement`. Inicio15/11/2026 19:24:36 ART. Tres contratos focales UX04/UX05 PASS (41,957s).

Revisión productiva00015-gap, Journey ON y motores OFF: informados por el propietario, no comprobados mediante consultas productivas. Sin operaciones GCP/Supabase. Historial SQL20261114225017 fuera de alcance: no reparar/reaplicar.

## Ownership y diagnóstico antes/después

|Control actual|Owner/handler|Target/problema|Solución UX06|
|---|---|---|---|
|Volver al Graph grande + Administrar datos + Cancelar|ultimate-case-setup; navigate/editSource/returnFromCore|Core02 autocircular; Cancelar markSaved elimina borrador; origen duplicado|Un retorno compacto por whitelist y guard existente, sin marcar guardado|
|Rail Core|wizard-ui.mountSetupSteps|show revela paneles; actual dispara onStep/replaceState de nuevo|Mismo form, no-op activo, Anterior en footer real, paso/URL sincronizados|
|Recuperar409/503|ultimate-case-setup onReload/errorBox retry|Al descartar draft se perdían origen, Run y preparación|Preservar ruta validada; no confundir descarte de valores con contexto de navegación|
|Back/Forward|workspace.restoreResource|history:false omite guard y remonta todo Core, pudiendo perder CSV|Restaurar paso compatible en form montado; salida protegida con índice de HistoryAPI del router existente|
|Editar Decision Case lateral|navigation.mountStudioRail showEdit=true|Graph llama false, Config/Dashboard no; CTA redundante|Eliminar rama de dominio del owner común; exactamente04/05/06|
|Editar Case funcional|UX05 command-toolbar/command-center|Core03 + origin canónico|Conservar única acción principal de Graph; breadcrumb Core permite edición contextual desde Studio|
|Config→Graph / Dashboard→Config|ultimate-decision-map / results.mount|Retornos dispersos; histórico no debe cambiar a latest|Footer secundario; target sólo según acción autorizada y Run actual exacto; histórico/readonly vuelve a Graph|
|Breadcrumb|platform.dda-navigation + resource|Studio activo aún era link; firma no incluía Node/Run|Activo indicador sin listener; firma incluye identidad exacta|
|Borrador/CSV/preparación|forms + planning-model + core-preparation + embedded CaseData|Form y guards compuestos; staging idempotente|Reutilizar sin autoPATCH/publicación ni nuevos IDs al retroceder|

## Matriz de navegación

Anterior: Core03→02→01 local, sin validación ni requests; Core01→overview con guard. Config→Graph mismo Case. Dashboard→Config sólo si el Run seleccionado es el actual, CURRENT, no superseded y configure.allowed/target exactos; si no, Graph. Graph conserva sus dos atajos, sin nuevo footer redundante.

Origen: whitelist Graph/Config/Dashboard/Center existente, parentCaseId para derivación, overview explícito para creación sin Case. Dashboard verifica Run/Node/Case exactos; Config verifica acción real.403/404/target inválido ofrecen fallback explícito al Graph del mismo Case;500/autenticación no se confunden con autorización. No latest ni URLs arbitrarias. Guardado real conserva retorno UX04; navegación no guarda ni descarta implícitamente.

## Riesgos y mitigación

1. CSV perdido por popstate: restauración local sin desmontar y guard al salir; test de cancelar/confirmar Back y breadcrumb.
2. Run histórico cambiado: resolver puro y revalidación de origen; tests de identidad/fallback sin latest.
3. Derivación pierde padre/intención: conservar route/preparationId/journal; pruebas de refresh y retorno al padre.
4. Rail limpio pierde acceso: Graph mantiene CTA y breadcrumb permite Core03; pruebas de las tres vistas, viewer/archivado y modo OFF.
5. Footer altera gating: reubicar CTA existentes conservando sus handlers; Anterior type=button fuera de fieldsets readonly; seis anchos/AA y regresión UX01–05.

Sin backend de aplicación, API, SQL, motores, flags, dependencias, workflows ni infraestructura nuevos. FULL obligatorio en el candidato estable por clasificador vigente; no cambiarlo para evitar tests. G7 acaba con un único PR abierto, no merge ni publicación/despliegue.
