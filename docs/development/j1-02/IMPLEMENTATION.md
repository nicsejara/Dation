# J1.02 — Decision Case V2

Baseline: `a41d644c4e25c7c9b85a8b9881ab3f4fb61989fc`, posterior a PR #133 y #134. Rama `feat/j1-02-decision-case-v2`. Especificación: paquete J1.02 Ultimate Pro, sus 117 criterios y la precedencia del Master Prompt. Inicio: 21/11/2026 11:04:11 ART. La versión de aplicación de este informe es el commit que contiene este archivo; el SHA y la CI terminal se registran en el cierre del PR sin modificar el candidato verificado.

## Cambios

1. Wizard de seis bloques: identidad; familia y versión publicada seleccionadas manualmente; horizonte inclusivo y modalidad; seis objetivos existentes; desempate económico y cobertura HIGH obligatoria; cobertura total y aprobación humana. Configure, Review semántico y Edit son modos distintos. Confirmar una definición todavía no crea un Case.
2. Biblioteca sobre `/api/platform/decisions`, búsqueda/paginación real y proyección de versión vinculada. Historial append-only de definiciones separado del historial de corridas. Derivar conserva la revisión exacta del origen y genera otra identidad. Los Cases históricos siguen siendo consultables sin inventar políticas ni KPI retrospectivos.
3. Persistencia privada, esquema V2 estricto, hashes canónicos, revisión CAS y mutation ID recuperable. Se verifica pertenencia de modelo/versión/workspace y sus dos hashes; no se permite sustituir la versión vinculada. Los metadatos admitidos generan otra revisión sin cambiar snapshots de Runs.
4. Adaptación mínima de D1: luego de la frontera lexicográfica de servicio y del costo óptimo entero, el desempate opcional maximiza carga propia. Nunca paga más. Un timeout o conjunto incompleto no certifica el desempate. Se reutiliza la restricción HIGH existente; no se modifica la física R6. El KPI usa hechos certificados en la dimensión principal canónica; sin denominador o evidencia válida es no evaluable. No aprueba corridas.
5. Bridge fino con Data Preparation existente: contratos reales de la versión exacta, dos o tres CSV, Data Owner, candidatos privados y finalize recuperable. Se exige preparación exacta validada también en SQL. Identidad, cuerpo e intención quedan fijos antes de crear Case/Pack. Cambiar modelo conserva la preparación anterior y necesita otra sesión.
6. Navegación compatible: recursos V2 tipados, return token J1.01, Review desde Graph y retorno comprobado al origen. Los enlaces históricos `core_step=1/2` de un Case V2 conservan modelo publicado y datos del mismo Case. Los enlaces derivados con Runs crean otra copia local, nunca sustituyen el Case original.

## Decisiones y límites

- `CasePolicy` continúa en V1. El envoltorio `decision_case_definition_v2` evita reinterpretar contratos anteriores. No se agrega un séptimo bloque.
- El desempate propio sólo es admisible con MINIMIZE_COST sin preferencias adicionales ni override de objetivo. Las combinaciones no ejecutables se rechazan; los otros cinco objetivos conservan sus reglas existentes.
- El Run guarda revisión y hash completos. La proyección matemática excluye únicamente esos dos identificadores administrativos; incluye reglas y aceptación. SQL y Python prueban el mismo hash. D2 conserva el binding exacto del D1 aprobado, incluso después de editar su nombre.
- Las reglas de congelación, admisión, aprobación, leases, cancelación e idempotencia previas siguen siendo autoridad. No se implementa J1.03/J1.04 globalmente.
- La biblioteca agrega una consulta batch de metadatos para la página, no una consulta por Case. Se conserva el enriquecimiento anterior. El benchmark de 27 Cases es una medición local sintética, no una garantía de latencia productiva.
- Copias y tokens locales están separados por usuario/workspace/tipo. Web Locks impide editar el mismo borrador en dos pestañas. CAS protege dos copias distintas del mismo Case en servidor. Cerrar sesión elimina ambas clases de copias.
- No se agregan dependencias, workers residentes ni cambios de CI/infraestructura. No se ejecutó ninguna operación productiva.

## Gates y evidencia

| Gate | Implementación / autoridad | Pruebas y evidencia | Riesgo / rollback |
|---|---|---|---|
| G0 | Baseline real y handoff #133 | `G0_BASELINE.md`, `evidence/g0-*` | Divergencia controlada; rama aislada |
| G1 | DTO, rutas, versiones, matemática, bridge | `G1_ARCHITECTURE.md`, contratos inicialmente RED | R3 por persistencia y solver; flag OFF |
| G2 | DTO/servicio/RPC, migración privada aditiva | 35 SQL J1.02 + históricos; CAS, ACL, freeze, replay, hashes | No aplicar producción; conservar historia |
| G3 | D1, KPI y binding de Run | Solver real, 2 E2E con worker/artefactos/D1/D2/aprobación | Flag OFF no altera corridas admitidas |
| G4 | `case-v2-*`, CSS compartido | Navegador, seis bloques, teclado, cuatro anchos | Ruta V2 cerrada por defecto |
| G5 | Biblioteca, revisión exacta, derivación | Paginación 25+1, error real, CAS dos pestañas, SQL de historia | Lectores disponibles con writers OFF |
| G6 | Selector J1.01, preparación, router, Graph | Dos/tres contratos, respuesta perdida, origen, Back/Forward y expiración | No cambia rutas legacy; no perder CSV publicados |
| G7 | Regresión y matriz de 117 criterios | `ACCEPTANCE.csv`, logs focales, geometría, FAST/FULL requeridos | Cierre remoto obligatorio antes de declarar verde |
| G8 | Un PR abierto y runbook | `ACTIVATION_AND_ROLLBACK.md`, `HANDOFF.md`, manifiesto | Sin merge/despliegue automático |

`ACCEPTANCE.csv` distingue evidencia local de los controles remotos que sólo pueden cerrarse después de publicar el candidato. El cierre del PR registra para esos IDs el mismo SHA, run terminal y estado abierto. No se afirma CI verde anticipadamente.

## Correcciones comprobadas durante desarrollo

Los logs RED se conservan. Se corrigieron: alias SQL de proyección; normalización de `case_mode=null` al regresar desde Graph; descripción canónica `null` al hidratar Edit; compatibilidad de rutas de modelo/datos; creación explícita de una sesión nueva después de limpiar una preparación expirada en modo GET-only. Ninguna aserción de integridad se eliminó. El catálogo JSON estático del contrato se regeneró al detectar correctamente la adición del binding; su prueba permanece intacta.

La migración se generó con Supabase CLI y se probó únicamente en PostgreSQL 17 local aislado. Los valores de fixture son sintéticos. Los seeds SQL de persistencia se diferencian de los E2E, que suben CSV reales y ejecutan workers locales. No hay prueba productiva ni declaración de disponibilidad en Cloud Run.
