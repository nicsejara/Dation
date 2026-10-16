# Workflow UI / Design System — Fase 7: QA End-to-End y cierre

Base: `d2631fe8418b69cacec7b95ebd074fd64e1186a7`, con las Fases 0–6 integradas. Esta entrega completa la regresión E2E de la saga sobre la interfaz compartida. No modifica el runtime ni incorpora cambios de negocio.

## Cobertura consolidada

La suite inicial pasa sus siete escenarios con API, worker, PostgreSQL 17, PostgREST y motores reales. La cobertura anterior comenzaba en Overview y continuaba directamente a Scheduling después de aprobar Assignment. Ahora el navegador entra por Inicio, abre DDA Logística y recorre también la ruta explícita de aprobación → mapa → configurar Scheduling. Conserva la continuación directa, atrás/adelante y recarga.

El recorrido completo se ejecuta con un caso nuevo en **1440 × 1000** y otro en **390 × 844**. Cada test usa la base y el Storage de prueba limpios. El segundo escenario agrega cobertura móvil completa; no comparte un caso ya ejecutado con escritorio.

Los ocho escenarios E2E cubren:

- Acceso privado, ingesta real de CSV, deduplicación y rechazo de bytes alterados.
- Admisión durable, reinicio de API, pérdida de worker y recuperación del lease sin permitir escrituras de un worker obsoleto.
- Assignment/Scheduling, aprobaciones, reemplazo de resultados, historial, estado stale y proyección durable.
- Comparativos progresivos, recuperación, reintento y reutilización sin alterar el caso original.
- Dos recorridos completos de Chromium con carga, configuración, revisión, ejecución, dashboard, aprobación, mapa, Scheduling y nueva decisión.

En cada recorrido de navegador se comprueban tres ejecuciones persistidas del mismo caso: Assignment completado y aprobado, Scheduling fallido por una ventana deliberadamente incompatible y un nuevo Scheduling completado y aprobado. Se verifican sus tres trabajos terminales, el upstream de ambos Scheduling, los dos eventos de aprobación y los IDs aprobados del caso. La reconfiguración conserva intacto el intento fallido.

## Contrato visual dentro del flujo real

`workflow_ui_audit.py` agrega verificaciones de interfaz al recorrido real, sin interceptar respuestas de API ni reemplazar resultados del motor. Comprueba:

- Hero compartido, panel visible y metadata vertical; a 1440 px los Heroes conservan 260 px.
- Órdenes/Flota y Alcance/Objetivo/Recursos del mismo tamaño; CTA principal más ancho.
- Estado disabled al faltar archivos, hover estable del botón deshabilitado, activación tras validar ambos CSV y hover del primario.
- Ocho acciones progresivas con los mismos estilos, flecha decorativa y ausencia de recorte.
- Ambas revisiones con shell nativo común, ancho y centrado correctos, contenido propio, secundario compartido y foco atrapado en ambas direcciones.
- Apertura/cancelación sin ejecutar ni cambiar la ruta; Escape y Volver restituyen el flujo. La revisión de Scheduling identifica el Run de Assignment aprobado.
- Diecinueve puntos de control por recorrido, con contraste HTML, ausencia de overflow, vista activa y capturas. Incluyen espera después de recargar una ejecución pendiente, error terminal y recuperación.

Cada escenario conserva su informe, capturas y traza en un directorio separado. Los informes incluyen el commit del checkout; una prueba valida que corresponde a la fuente que ejecutó el runner. Las suites de las Fases 1–6 mantienen cobertura de cinco anchos requeridos, 320 px, orientación horizontal, pantallas bajas, movimiento reducido, teclado y estados loading/error.

## Infraestructura y publicación

El E2E usa exclusivamente direcciones loopback y una red Docker propia. PostgreSQL y PostgREST son reales; Storage es el gateway HTTP de prueba que conserva los bytes subidos. La API, el worker y los motores ejecutan su código real. El runner sustituye las credenciales productivas y limpia sus contenedores, procesos y archivos. No acredita las políticas del Storage alojado ni una sesión manual con lectores de pantalla específicos.

Antes de integrar se requieren las suites completas, las regresiones SQL y los ocho escenarios E2E, más CI del head exacto. El merge conserva el mismo árbol de contenido validado. La publicación usa el pipeline existente y verifica fuente de Cloud Build, plantilla, hashes de assets, salud y acceso privado.

La QA productiva recorre los estados ya existentes en nueve tamaños, con teclado, nombres accesibles, espaciado de texto y movimiento reducido. Abre y cancela las revisiones; compara los registros consultados antes/después. Las ejecuciones y aprobaciones de QA permanecen en el entorno desechable.

## Guía de prueba manual

1. Recargar la plataforma y entrar por **Inicio → DDA Logística**.
2. Elegir **Nueva decisión**, subir Órdenes y Flota y comprobar la validación y habilitación del CTA.
3. Abrir el mapa, configurar Assignment y revisar alcance, objetivo, prioridades y recursos.
4. Abrir la revisión, probar Volver/Escape, volver a abrir y confirmar la ejecución.
5. Revisar el dashboard, sus detalles y exportación; aprobar el resultado.
6. Volver al mapa, abrir Scheduling y comprobar que usa la asignación aprobada.
7. Revisar ventana, reglas, objetivo y recursos; ejecutar y revisar su dashboard.
8. Probar recarga, atrás/adelante y consulta del historial; repetir los pasos principales en móvil.

Para preparar otro plan, registrar cada ajuste con: pantalla, pasos para reproducir, resultado actual, resultado esperado y prioridad. Si corresponde a un caso concreto, anotar su Decision Case y Run. Las trazas y capturas de QA permiten comparar la presentación actual con el cambio propuesto.

## Archivos

- `backend/tests/e2e/browser_journey.py`: recorrido ampliado y puntos de control.
- `backend/tests/e2e/workflow_ui_audit.py`: contrato visual sobre el navegador real.
- `backend/tests/e2e/test_workflow.py`: escenario móvil y comprobaciones persistidas.
- Este informe.

Con la validación y publicación aprobadas, queda cerrado el plan de **Fases 0–7**. Los siguientes cambios se definirán a partir de la prueba funcional del usuario.
