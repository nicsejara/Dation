# V2 · Fase 6 · Golden E2E y regresión

Base: main `eeee37c1f9ab0560902e12f10a874a36d55cad3a`, Fase 5 publicada en PR92. Alcance: secciones 65–73 del Master Plan y 103–127 de CAMBIOS_TRANSVERSALES. No añade funcionalidades ni reconstruye superficies correctas. Los resultados de CI, fuente productiva y verificaciones finales se registran en `/workspace/dation-audit/platform-v2-phase6/ENTREGA.md`.

## Golden con personas distintas

`tests/e2e/test_v2_golden.py` y `golden_journey.py` recorren la plataforma con cinco sesiones BFF independientes: Admin, Data Steward, Decision Owner, Approver y Viewer. Tres identidades sintéticas nuevas se confirman exclusivamente en el Auth fixture local y se incorporan al workspace mediante invitaciones y aceptación reales. Los roles y nombres se guardan por los endpoints existentes; Admin no recibe responsabilidades implícitas. El fixture de login admite estas identidades sólo si existe su archivo de configuración dentro del sandbox descartable; se conserva el contrato anterior de A/B y refresh.

El recorrido prueba login → Home → catálogo → Logística → CSV Orders/Fleet → registro explícito del Case por Operator → asignación Data por Admin → Map → Owner de D1 → configuración/ejecución real → Approver → aprobación por la persona asignada → handoff → D2 → segunda ejecución/aprobación. No se simulan respuestas de SQL, API o motores, ni se inyecta estado de negocio en el navegador.

Se comprueba que:

- Admin asigna, Steward carga, Owner ejecuta y Approver aprueba. Un Operator no asignado no obtiene aprobación, y Viewer sigue sin ejecutar o asignar aunque tenga todas las responsabilidades de negocio.
- La revisión muestra el responsable; los bloqueos desaparecen sólo después de guardar asignaciones elegibles. Cada selector ofrece únicamente la persona que corresponde a su responsabilidad y workspace.
- D1/D2 abren sus dashboards canónicos, sin perder Case/nodo/run. El switcher conserva foco, marca el Case actual y muestra el estado aprobado mediante texto además del color.
- Decision Center refleja Data Responsible, ambos Owners/Approvers, actor real de aprobación, objetivos, dos archivos, estado completado y actividad. Data Hub muestra el uso del dataset y vuelve al mismo dataset tras Back y reload.
- Navegar no altera configuración, fingerprints, actor ni linaje. Quedan exactamente dos corridas y dos eventos de aprobación. `run.queued` conserva los responsables de datos/decisión, distintos del actor cuando corresponde.

## Matriz funcional, accesibilidad y rendimiento

El Golden verifica 1440/1280/1024/768/390 en nueve superficies: Home, Datos, Map, Config, Dashboard, editor de responsabilidad abierto, Case switcher abierto, Decision Center y Data Hub. Guarda 45 probes de contraste/reflow y capturas; utiliza reduced motion. Se ejercitan Escape, foco, controles nativos, etiquetas, selección semántica y razones de bloqueo. Las regresiones previas mantienen su cobertura adicional 320/360 y zoom.

La instrumentación observa solicitudes reales, sin interceptarlas: redimensionar no repite summaries/portfolios; el switcher solicita una página de 8 del mismo DDA; historiales y previews no se cargan antes de abrirlos; navegar entre los recursos no añade ejecuciones ni aprobaciones. Los KPIs siguen consumiendo snapshots globales del backend. La suite SQL existente mantiene sus pruebas de paginación acotada, metadata ligera, historial grande y consultas compartidas; las suites anteriores mantienen cancelación de respuestas tardías, listeners y errores/reintentos. Se reutiliza esa cobertura, sin recrearla como tests triviales.

La prueba de seguridad nueva recorre ambas direcciones A/B: lectura, descarga, archivo, borrado, mutación de Case y asignación ajena deben fallar. Los candidatos no incluyen B ni Viewer; responsabilidades de negocio no convierten a Viewer en writer. Se comparan los Cases antes/después para detectar escrituras pese a un rechazo.

## Regresión corregida

Cerrar un drawer abierto por URL o después de reload perdía la referencia al trigger y enviaba el foco al primer elemento del portfolio. Afectaba a Data Hub y Decision Center. La corrección conserva el ID seleccionado antes de cerrar y usa su botón como fallback; mantiene el trigger original cuando todavía existe y el fallback anterior si la fila ya no está.

`tests/browser/test_v2_regression.py` reproduce primero ambos fallos con el segundo elemento de una lista y comprueba el arreglo a 1440/390, tanto drawer lateral como modal nativo. Espera la restauración de foco y verifica que cerrar no vuelve a consultar el portfolio. El Golden añade la comprobación sobre un dataset real tras reload. No modifica layout, filtros ni navegación.

## Gate y publicación

CI sigue ejecutando todas las suites y rechazando E2E vacío o con skips. El límite del job pasa de 30 a 45 min: la CI final de Fase 5 requirió aproximadamente 25 min y esta fase agrega sesiones y matrices reales; cada espera y subprocess conserva sus límites. No se eliminan ni relajan comprobaciones de contraste, overflow, permisos o evidencia para entrar en ese presupuesto.

Sin dependencias, SQL/RPC, migraciones, cambios de roles productivos o motores nuevos. En producción se comprueban fuente/bytes exactos de los dos módulos corregidos, límites públicos de acceso, heartbeat del worker y conservación del catálogo y datos anteriores. No se crean cuentas, CSV, invitaciones o solvers productivos ni se usa una sesión personal. Los fixtures de Auth/Storage son locales; la suite no acredita entrega real de email ni un login personal contra Supabase alojado.

La siguiente fase es Fase 7, Release audit. No comienza automáticamente al cerrar este gate.
