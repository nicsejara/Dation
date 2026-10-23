# Dation — Final UX/UI Polish Saga

Estado: en implementación. Baseline real de main/origin/main: `ff8134c6a19fc98c7e6a81029d830b4ab5285560`. Rama: `ux-ui/final-polish-saga`.

El master definitivo se leyó completo antes de editar. Se conservan Dation Precision, navegación, dominio y contratos; no se realiza una auditoría transversal nueva. Baseline: 813 archivos con SHA-256 y 14 capturas de Overview, Datos, Config D1/D2, Dashboard D1/D2 y ejecución a 1440×900 y 375×812. Evidencia local: `/workspace/work/final-polish/`.

## Fases

1. Shared workflow chrome: metadata de paso/decisión separada y sin ceros; command bars con estado canónico, geometría medida, safe-area y viewport de scroll separado. El layout reserva espacio para que los controles no queden detrás de la barra y expone el foco sin animar. ResizeObserver, focus y visualViewport se disponen con el scope existente. Z-index 35, por debajo de menús y overlays. No cambia readiness, Apply, defaults, revisión ni ejecución. La prueba de foco ahora espera un campo visible y comprueba que realmente tenga foco antes de evaluar sus nueve puntos; antes podía evaluar una vista todavía oculta.

## Invariantes

DDA → Case → Decision → Run; Data Pack inmutable; atributos/Data Owner aplicados conjuntamente, cuatro requisitos independientes; Decision Owner/authority actuales; aprobación humana por Run e invalidación downstream en admisión; idempotencia, historia y fingerprints intactos. Assignment no temporal; Scheduling consume Assignment aprobada sin reasignar; D3 permanece disabled. Backend, motores, API, SQL, persistencia, tenancy, roles, permisos, exportación e infraestructura quedan fuera de las modificaciones.

Phase 1 QA: C4/C5 pasan en seis viewports; nueve puntos de cada control enfocado quedan visibles. Ocho browser distintos verificados (cuatro de preparación antes de CSV, dos de aceptación y dos de foco/reflow), seis unitarios y 18 observaciones visuales sin overflow ni fallos de contraste muestreado. Los viewports bajos compactan la barra y permiten desplazar los headers; no se reintroduce una animación de entrada.
