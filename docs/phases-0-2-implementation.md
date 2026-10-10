# Fases 0–2: dependencias, navegación y recursos de pantalla

La revisión parte de `03d15fab81a6eb04e611a24a5033420bae3acf82`. La restauración del entorno no conservó los diffs anteriores: se recuperaron los locks desde sus logs y se reconstruyeron los cambios de interfaz. La evidencia válida corresponde a esta revisión.

Fase 0 actualiza las dependencias afectadas, fija hashes, separa Playwright y pip-audit del runtime y añade ambos análisis de vulnerabilidades a CI. Las 13 funciones que no descubría unittest se incorporan mediante `load_tests`. Se corrige la expectativa contradictoria del hero comparativo de Assignment, conservando las comprobaciones del comportamiento final.

Fase 1 centraliza navegación y estado en Dispatch: las URLs conservan vista, caso, nodo y corrida; refresh, enlaces históricos y atrás/adelante hidratan el caso y Data Pack. Las configuraciones se guardan por caso y se validan al recuperar almacenamiento corrupto. Reejecutar mantiene la decisión aprobada hasta que se apruebe la nueva candidata. Las decisiones vencidas o reemplazadas no ofrecen aprobación.

Fase 2 asigna un propietario a cada pantalla. Al salir se cancelan peticiones y polling, se desconectan observers, se destruyen gráficos y se retiran drawers. Las respuestas tardías de IA no alteran otra pantalla. Los diálogos capturan Tab y devuelven el foco al cerrar. Los módulos tienen una URL canónica y JS/CSS revalidan con ETag y `Cache-Control: no-cache`.

Validación reproducible desde `backend`: unittest, los selectores Node y las suites de navegación/lifecycle, y `.browser-venv/bin/python tests/browser/test_navigation.py`. El navegador inicia su propia API de QA con Supabase y LLM desactivados y usa fixtures sintéticos. Comprueba 24 recorridos, incluyendo drafts por caso, ejecución de Scheduling, recuperación de respuesta POST perdida, exportación, cancelación, observers, teclado y límites móviles. No escribe datos productivos.

Estas fases no requieren migración SQL ni worker. El despliegue automático existente de Cloud Build se activa al actualizar `main`; hay que comprobar su check para el commit exacto y los módulos servidos por `dation-core` en `us-west1`. CI, build y verificación HTTP son evidencias distintas. La cola durable de la Fase 3 se incorpora después de migrar Supabase y desplegar su worker.
