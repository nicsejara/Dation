# Fase 4: persistencia y trazabilidad

Corresponde a F06, F14 y F17 de la auditoría integral. Se conserva el workspace
privado compartido por decisión del usuario; no se habilitan múltiples clientes
independientes en esta instancia ni se atribuye una credencial compartida a una
persona. El servicio permanece protegido por la autenticación existente.

## Historial e integridad

`decision_case_history` obtiene, en una sola instantánea PostgreSQL, los totales
completos, la última corrida y la aprobación no reemplazada de los tres nodos,
independientemente de la página solicitada. La paginación se ejecuta en SQL con
orden `created_at DESC, id DESC`; no hay ventana previa de 1.000 corridas ni se
descartan las aprobaciones del nodo anterior al consultar Scheduling.

La API, listado de casos y reconciliador usan esos resúmenes. La UI permite
Anterior/Siguiente, informa el rango y el total, conserva la aprobación fuera de
la página y permite reintentar una página fallida. Cerrar o navegar cancela la
observación; una respuesta tardía no recrea el diálogo. El historial es vivo:
nuevas corridas pueden desplazar los offsets entre solicitudes. `result_json`
queda fuera de las páginas; abrir una corrida carga su resultado completo.

Las aprobaciones toman primero un lock por caso, compartido por todos sus nodos.
Dos alternativas simultáneas se serializan; queda una aprobación vigente y la
anterior conserva su fecha y el identificador que la reemplazó. Repetir una
aprobación vigente conserva fecha/actor/eventos. La fecha se toma después de
adquirir el bloqueo, para reflejar la aprobación efectiva aunque la solicitud
haya esperado otra transacción. Una aprobación reemplazada se
rechaza con conflicto HTTP 409; para elegir de nuevo se crea una nueva corrida.
Las validaciones del upstream se repiten dentro de la transacción, incluida la
admisión de nuevas dependencias. Una corrida ya admitida conserva su evidencia
aunque el upstream cambie; su resultado desactualizado no puede aprobarse.

Las aprobaciones nuevas registran `approved_by=shared_workspace:dation` y eventos
inmutables `approved`/`superseded` en la misma transacción. Las históricas conservan
`approved_by=NULL`; no se inventan autores ni eventos retroactivos. La UI distingue
acceso compartido, autor histórico no registrado y aprobaciones desactualizadas.
Los clientes no pueden enviar un autor en el comando de aprobación.

Triggers impiden cambiar la identidad de archivos/Data Packs/corridas,
configuración, resultados terminales, fingerprints y aprobaciones históricas.
Etiquetas, perfiles derivados, archivo/desarchivo y flota predeterminada siguen
siendo editables. La verificación SHA256 de los bytes al calcular continúa activa.
La tabla de eventos tiene RLS y acceso sólo desde el backend; `anon` y
`authenticated` no pueden invocar las RPCs privadas. El administrador de PostgreSQL
conserva sus capacidades administrativas; esto no es un registro externo firmado.

## Esquema reproducible y despliegue

El [baseline real y su orden de instalación](../supabase/README.md) sustituyen el
fixture incompleto. Se comparan el catálogo capturado y el reconstruido, la
instalación nueva y el upgrade con evidencia histórica en PostgreSQL 17.

1. Validar CI de la revisión candidata y registrar la imagen/revisión anterior.
2. Ejecutar `python scripts/apply_production_persistence.py` con el token
   administrativo seguro: sólo aplica la migración aditiva de Fase 4 si el catálogo
   coincide con el de Fase 3 y luego el ajuste `approval_clock_after_lock`.
   Si Fase 4 ya existe, verifica y completa sólo el ajuste pendiente.
   Nunca aplica el baseline a producción.
3. Incorporar la revisión validada en `main`. Cloud Build usa el Dockerfile y
   publica la misma imagen primero en el worker y luego en la API, preservando
   secretos, IAM y configuración existentes.
4. Comprobar build, autenticación, salud, esquema, recursos servidos y persistencia
   real con datos sintéticos. Archivar el caso y datasets de QA sin cambiar la flota
   predeterminada de los operadores.

Rollback: replegar la imagen anterior de API/worker sin eliminar esquema ni
evidencia. Las restricciones y RPCs nuevas son compatibles con los consumidores
de Fase 3; las nuevas aprobaciones mantienen semántica monotónica también durante
el rollback. El estado de CI y la verificación de publicación de esta fase se
registran en [PR #39](https://github.com/nicsejara/Dation/pull/39).
