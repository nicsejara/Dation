# Activación manual propuesta — requiere GO separado

Esta entrega no autoriza merge, publicación de imagen, cambio de tráfico, migración productiva ni habilitación de motores. J1.02 permanece cerrado por defecto. No se desbloquea `apply`.

## Antes de cualquier escritura productiva

1. Revisar el PR y confirmar el SHA exacto con impact R3, FAST, ambos jobs FULL y required-gate aprobados. Revisar `ACCEPTANCE.csv` y el cierre remoto del PR.
2. Solicitar GO explícito para integración y, separadamente, activación. Identificar el proyecto Supabase correcto sin compartir secretos. Comprobar el historial real de migraciones; si difiere del baseline, detenerse. No repetir migraciones UX04 ni reconciliar automáticamente su historial.
3. Acordar la política de protección de datos del entorno de destino. La dispensa histórica del propietario corresponde a datos descartables de pruebas; no ejecutar resets, borrados ni backfills. J1.02 no requiere ninguno.
4. Probar la migración de esta entrega en una copia aislada con el mismo esquema de partida. Confirmar disponibilidad de los RPC existentes, tabla release y migraciones de Saga 10/Journey/J1.01. Verificar que la fila release existe y J1.02 no está activado.

## Orden autorizado futuro

1. Mantener `DATION_J102_ENABLED=false`, motores y admisiones en su estado cerrado. La configuración actual de infraestructura no cambia.
2. Aplicar **una sola vez** `supabase/migrations/20261121141444_j102_decision_case_definitions.sql` por el circuito de migraciones existente, usando credenciales del propietario fuera del chat y el SHA aprobado. El archivo es transaccional, con lock timeout 5 s y statement timeout 90 s. Si ya figura aplicada, verificar su checksum y no repetirla. Si hay drift o un timeout, detenerse y diagnosticar; no forzar locks ni reparar el ledger automáticamente.
3. Verificar en lectura: columna `j102_enabled=false`; tabla privada de revisiones con RLS; ausencia de permisos directos para anon/authenticated/service_role; sólo los RPC públicos comprobados tienen EXECUTE para service_role; historia anterior conservada. Los tests de ACL reproducibles están en `tests/integration/test_decision_case_j102.py`.
4. Construir/publicar por el runbook manual existente un digest del SHA aprobado, si ese GO lo incluye. Desplegar sin tráfico y sin modificar identidades, límites, Cloud Build, Scheduler ni motores. Probar lectura legacy y capacidad V2 cerrada. No reutilizar el paquete histórico de Gate C para otra versión.
5. Con GO de piloto V2, habilitar los flags runtime y SQL J1.02 sólo junto con los gates/cohortes existentes de foundation, Saga 10, J1.01, Journey y Data Pack. Consultar la capability real `decision_case_v2_enabled`; un flag aislado no basta. No activar motores para probar el wizard y su bridge.
6. Smoke manual autenticado: biblioteca → nuevo borrador → modelo y versión explícitos → seis confirmaciones → Review → preparación de todos los contratos → finalize → un Case/Pack → Graph → Review → retorno. Comprobar revisión inicial, modelo exacto, owner y cero Runs nuevos. Probar otra pestaña/rol viewer y un Case histórico. No ejecutar D1/D2 sin GO independiente.
7. Promover tráfico únicamente con GO específico y recibo de digest/revisión/flags. Supervisar errores de permisos, CAS y finalize; conservar los IDs de intención para recuperar una respuesta perdida, sin crear otra identidad.

## NO-GO

CI pendiente/fallida; contrato o migración divergentes; bridge sin todos los contratos; modelo archivado para una creación nueva; falta de owner elegible; permission/cohort denegado; hashes distintos; cambio matemático en un Case congelado; resultado/KPI sin evidencia; propuesta de habilitar motores, IAM o infraestructura como atajo. Los datos históricos no se convierten a V2 automáticamente.

## Rollback lógico seguro

Cerrar primero nuevos writers/piloto con `DATION_J102_ENABLED=false` y `platform_release.j102_enabled=false` por el circuito autorizado. No cambiar los flags globales de motores ni matar trabajos admitidos. Los RPC de completion/drain anteriores siguen delegados y las revisiones V2 quedan consultables. Preservar el código lector V2, los snapshots, Packs, Runs y aprobaciones. No hacer DROP de tabla/funciones ni revertir hashes/artifacts históricos. Una reversión de imagen sólo es segura si conserva estos lectores y adaptadores, o si no existen Cases V2: verificar esa condición antes de cambiar tráfico.

La preparación incompleta permanece privada y recuperable. Limpiar una sesión expirada es una acción explícita sobre sus CSV privados; no elimina datos publicados de Cases. Un intento FINALIZING se recupera con el mismo Case ID y cuerpo, no se resetea ni se limpia para ocultar una operación desconocida.
