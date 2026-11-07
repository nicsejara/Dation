# Dation Runtime V2 — código listo, activación cerrada

Destino único: **dation-runtime-v2-2026 / 332279365872 / us-west1**.
Baseline: main `3e96ca85fbf71c22d3f26b426bb1ef869facf8f7`, posterior a #105.
Estado del candidato y resultado terminal de CI: ver el PR de Runtime V2;
este documento se prepara antes de CI para no añadir otro commit sólo por el resultado.

## Alcance e identidad

La identidad canónica está en `backend/app/cloud_identity.py`, un módulo stdlib
incluido en la imagen. Runtime, release y diagnóstico importan el mismo módulo.
El transporte exige explícitamente proyecto, número, región y los dos recursos
Jobs. Configuración ausente, incompleta, mezclada o de otro proyecto falla antes
de reservar una entrega, leer credenciales administradas o contactar Jobs.

`GOOGLE_CLOUD_PROJECT`, si se suministra, también debe coincidir. El logger no
genera trazas para otro proyecto. Los helpers históricos no pueden escribir GCP;
su diagnóstico admite sólo los servicios conocidos del proyecto nuevo. El
helper de cambios Auth histórico queda cerrado incluso si se importa su función.

`infra/zero-idle/release.json` es configuración deseada, no inventario live.
`prepared-manifests.json` es su salida reproducible de revisión: API, dos Jobs,
cuentas propuestas, IAM por recurso, Secret Manager sin valores y Scheduler
cerrado. Regenerar con `python scripts/zero_idle_release.py plan`.

## Proyecto anterior fuera de alcance

`dation-510100 / 469052310590` permanece con Billing OFF según el propietario.
No se consultó ni modificó en esta adaptación; no se elimina ni neutraliza su
worker. No es una dependencia para activar el proyecto nuevo. Los runbooks
anteriores que proponían retirarlo quedan sustituidos para esta activación.
No reutilizar cuentas, nombres de recursos ni URLs del proyecto anterior.

Los documentos de Saga 02 conservan su evidencia histórica. La referencia
operativa vigente es [activación y rollback](activation-runbook.md).

## Evidencia y límites

- `main` confirmado y árbol limpio al crear la rama dedicada.
- GET del **proyecto nuevo** con la credencial disponible: HTTP 401. Estado
  ACTIVE, número y Billing DISABLED se respaldan con la confirmación del
  propietario; no se afirma una lectura independiente exitosa.
- DDA conservado: REST de dispatch con limit=0 y metadatos Storage: HTTP 200;
  `dda-inputs` privado. Historial: 20 migraciones, Saga 02 pendiente.
- No se aplicó SQL ni se borraron datos. Backup restaurable dispensado para
  datos operativos de prueba de esta primera activación; plan Free conservado.
- Ningún build/push GCP, recurso, Job, schedule, IAM, secreto, trigger o Billing
  fue creado/activado/modificado. Sólo pruebas locales y GitHub CI.
- `apply` sigue rechazando incluso flags GO viejos o nuevos. No hay auto-merge.

## Validación

Focales locales: 48 tests de identidad/transporte/manifiestos/IAM/guardias/
despliegue histórico/telemetría/costos y 13 E2E finitos del runtime. La imagen
local usa una CA montada durante instalación, sin alterar el Dockerfile de
producción ni incorporar credenciales. Sin assertions debilitadas ni cambios
de motores, API, frontend, aprobaciones, SQL, idempotencia o fencing.

La única CI completa del candidato estable se registra en el PR con su SHA y
conteos reales. No presentar la CI del baseline como validación de este candidato.

## Activación futura

1. [Checklist y secuencia de despliegue/rollback](activation-runbook.md).
2. [Lecturas Cloud Shell y acceso](readonly-and-access.md).
3. [Costos y límites del smoke](costs.md).

Resultado de desarrollo: `DATION_RUNTIME_V2_CODE_READY — BILLING_OFF — NOT_DEPLOYED`.
No equivale a GO económico ni a una validación live de IAM, cold start o scale-to-zero.
