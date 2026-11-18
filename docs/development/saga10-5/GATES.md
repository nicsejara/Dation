# Saga 10.5 — ejecución y evidencia

Inicio registrado: 2026-11-18 21:19:59 UTC (18:19:59 Argentina). Rama: feat/saga10-5-logistics-guided-ux. No merge ni operación productiva autorizados.

## G0 — PASS

- Repositorio nicsejara/Dation; PR126 integrado a las13:31:52 UTC. Main real recuperado: 8aa07f5ddad315d6e704b5fcfec77ebc0f101a8a. Working tree inicial limpio, nueva rama desde origin/main.
- Paquete maestro leído con sus especificaciones, matriz y ambos mockups. MANIFEST:20 archivos con tamaño/SHA256 verificados. DARK es dirección visual; no reemplaza el shell ni los contratos.
- Inspección única localizada: editor v2, catálogo, collector, preview/publish, helpers/forms, CSS, contratos cargo/physical y suites browser. No cambios de backend/dominio/SQL previstos.
- Baseline: cuatro pruebas Saga10 aprobadas (42,991s de tanda, incluida una entrada de loader inválida que no ejecutó el smoke v1). Nombre corregido; v1 T01 real PASS,19,130s. El error de invocación no fue fallo de producto ni se omitió el test.
- El collector actual mantiene configuración2; el preview es autoridad física; publicación usa intent/CAS/IDs y selección inmutable. Se conservará ese protocolo.
- Riesgo esperado R2: static JS/CSS ultimate/browser más docs R0. Clasificador y workflow vigentes exigirán FAST/browser/required-gate; no se cambiarán para evitar FULL.
- NO_AUTO_DEPLOY: cargo-editor.mjs y model-fields-v2.mjs siguen fuera de la allowlist UX. No cambiar política ni prometer merge=producción.

## Decisiones de compatibilidad

1. Básico=direct, dos CSV y catálogos vacíos. Soporte físico reutilizable sin productos requiere backend y queda fuera del alcance.
2. Detallado=catalog, tres CSV; mismos IDs/DTO/normalizer/compiler. Borrador reversible sólo en el wrapper UI local, nunca en configuración publicada.
3. Medidas vacías completas o ninguna; medidas cargadas en presentación distinta. Datos parciales permanecen editables como borrador, con error y sin publicación.
4. Check visual requiere revisión explícita. Carga requiere además compilación vigente. La validez estructural sigue separada para no bloquear el propio preview.
5. Peso de componentes es bruto, no neto. Participación por bultos comparables no significa ocupación de volumen. Sin packing3D ni productos demo.

## G1–G5 — PASS local

- Cinco encabezados nativos con estados revisados; siete subpasos, radios reales y navegación local. Sin cambios al shell/contratos.
- Editor único por ID, datos avanzados accesibles, clones seguros, borrador reversible y direct limpio. Las propiedades parciales quedan fuera del DTO y bloquean publicación.
- Preview actual + confirmación para Carga; borrado protegido y límites reales. Fuente y masa declarada no se presentan como cálculos certificados.
- Regresión integrada:31 pruebas browser PASS en217,138s. Incluye10 casos nuevos,4 Saga10,12 wizard v1,4 Saga01 y1 de borrador/sesión.
- Contratos/frontend/física:54 PASS en0,402s. Clasificador fail-closed:7 PASS. Sintaxis JS/Python/CSS y diff check PASS local.
- Se comprobaron15 combinaciones de escena/ancho, sin overflow ni controles fuera de ancho ni fallos de contraste; capturas reales en1536/390/320 y geometría en cinco anchos. También teclado, foco y reduced-motion.
- En los focales se corrigió la selección principal al aplicar sugerencias (actualizar opciones antes de seleccionar, conservar la principal si sigue siendo válida), y se mantienen mensajes de grupos separados de la validación nativa individual. No se alteraron reglas físicas ni se agregaron sleeps/retries.
- El test de granel compara el valor0,00125 y su incremento0,004kg, sin exigir un cero final de formato que el servidor no devuelve.
- Focales posteriores de procedencias/fuentes y extensiones de edición/perfil se cierran antes de subir el candidato; sus resultados se registran en el PR.

## G6 — gate externo del candidato

Clasificación local real R2, requires_full=false; no cambios al clasificador ni a su mapa. El required-gate de GitHub debe aprobar el SHA exacto. FULL se omite sólo si así lo decide CI. NO_AUTO_DEPLOY confirmado por política, no modifica esta decisión el resultado de FAST.

El cierre terminal de CI/PR, SHA y tiempo total se registra en el PR. Este documento previo a CI no inventa un resultado terminal ni autoriza merge/publicación.


## Cierre focal antes de CI

- Los focales finales de composición (quitar/restaurar521→665kg), perfiles con datos, borrador y fuentes:3 PASS en36,204s. No se cambió el contrato para hacerlos pasar.
- Procedencias declaradas: T12 PASS; masa por bulto desconocida sigue pendiente y los900kg/1,8m³ declarados no se llaman calculados. Granel T07 también PASS con densidad explícita e incremento0,004kg.
- Se registran33 escenarios únicos de navegador con último resultado PASS: los31 de la tanda integrada más T11/T12. Las repeticiones focales no se suman como cobertura nueva.
- Evidencia de15 escena/anchos: mínimo contraste5,6278:1, overflow0, controles fuera de ancho0. Diez PNG reales, geometría compacta y manifest con SHA256/digest del runtime frontend. No se agregan los mockups al runtime.
- La validación de fuentes de grupo tiene un contenedor v2 propio para que blur de una casilla individual no borre el error lógico. No se modifica forms.mjs compartido.
- El cierre terminal de G6 sigue condicionado a GitHub sobre el commit definitivo; se registra allí sin otro commit de estado.
