# Lectura e identidad — proyecto nuevo

No compartir tokens ni contraseñas. El binding de GCP figura ready en este
entorno, pero el GET de Resource Manager respondió **401 UNAUTHENTICATED**.
No prueba falta de un rol concreto; resolver autenticación antes de conceder
permisos. No se probó otro token como bypass. Billing/Scheduler tampoco están
en los dominios de red/binding actuales de esta sesión.

## Cloud Shell del propietario

Desde el checkout del candidato, con la sesión de Cloud Shell ya autenticada:

```sh
python scripts/runtime_v2_readonly.py
python scripts/runtime_v2_readonly.py --cloud-shell > runtime-v2-readonly.json
```

La primera orden sólo imprime el plan. La segunda captura el access token de
`gcloud` en memoria, hace exclusivamente GET a los endpoints fijos del proyecto
nuevo y emite metadatos sanitizados. No imprime token, variables de contenedores,
valores de secretos, headers ni cuerpos de error. No usa comandos gcloud que
puedan proponer habilitar una API. Un 401/403/API deshabilitada queda sin verificar;
**no se habilita una API para que un listado pase**.

Exige projectId, número y ACTIVE antes de continuar. Nunca acepta un proyecto
por argumento/env ni sigue con el inventario si esa identidad falla. Si hay
`next_page_present=true`, el listado es incompleto y no se certifica como PASS;
completar esas páginas sólo en Console/API del mismo proyecto.

Compartir únicamente ese JSON sanitizado y las lecturas faltantes necesarias:
políticas IAM por recurso, límites de API/Job y versiones/estados de los secretos,
sin sus valores. Revisar permisos con la identidad que realmente los usará.

## Qué debe demostrar el inventario

- `dation-runtime-v2-2026`, número `332279365872`, ACTIVE y Billing false.
- Sin trigger global/regional de despliegue por main ni builds activos. No crear
  un trigger para activar Runtime V2.
- API/Jobs/Scheduler existentes, si los hubiera, identificados. No presumir
  vacío sólo porque el proyecto es nuevo; comprobar que no haya un worker residente
  **en este proyecto** ni mínimos/CPU permanente inesperados.
- Cuentas propuestas `dation-runtime` y `dation-scheduler`, su existencia o
  ausencia e IAM efectivo. Ningún grant sobre el proyecto anterior.
- Repositorio regional e imágenes/retención; secretos sólo por metadatos y
  versiones numéricas. Las referencias versión 1 del manifiesto son propuestas,
  no evidencia de existencia o de que sus valores sean correctos.
- APIs necesarias y cuotas. Habilitarlas es una operación futura con GO, distinta
  de esta lectura. Cualquier acceso a recursos de otros proyectos queda excluido.

Si se quiere reparar la conexión de Codex, renovar el binding seguro de la
identidad elegida en la configuración del entorno. Ampliar sólo los dominios de
lectura necesarios para Billing/Scheduler, sin pegar credenciales en chat ni
conceder Owner/Editor por conveniencia. También se acepta la evidencia de Cloud
Shell del propietario para avanzar en la revisión del GO.
