# G6 — Plan exacto inicial de identidad y permisos

**PREVIEW ONLY — requiere GO específico del propietario.** Ningún comando de este
plan fue aplicado. Automatización productiva deshabilitada. Proyecto único:
`dation-runtime-v2-2026` / `332279365872`, región `us-west1`.

Plan SHA-256: `042f6a60d77ed59ddef567120971b49130d6564eace8252138d4e610a4648c6f`.
Política SHA-256: `8a85c8fabec653f1d95aa1bf00b35950304021e47639c7cad342bd9257f2b9a2`.
Recalcular con el script de preview y `sha256sum` desde el candidato revisado;
un cambio de cualquiera de esos planes exige nueva revisión.

## Evidencia actual y límites

- GitHub main observado: `baefc6788b11a1aa9f5e02a21c60d033860e1342`.
- API GitHub: `protected=false`, required status checks apagados. CODEOWNERS por sí
  solo no es protección; el preflight de G6 rechazará este estado.
- Lectura GCP de dation-core: HTTP401 UNAUTHENTICATED,
  `ACCESS_TOKEN_TYPE_UNSUPPORTED`. IAM actual, revisión/digest activos, flags y
  configuración live siguen **sin verificación nueva**. No es prueba de ausencia.
- No se repitieron Gate A/B ni inventario general. No se hicieron escrituras GCP,
  Supabase ni activación de variables/environments productivos.

## Delta GCP propuesto (no aplicado)

Crear SA `dation-ux-deployer@dation-runtime-v2-2026.iam.gserviceaccount.com`, sin
claves JSON. Mantener intacta `dation-image-builder`: sólo publica en Registry,
no recibe permiso de despliegue.

| Recurso exacto | Permiso/rol para la identidad indicada |
| --- | --- |
| Servicio existente `projects/dation-runtime-v2-2026/locations/us-west1/services/dation-core` | Custom role `projects/dation-runtime-v2-2026/roles/dationUxServiceReleaser` a la nueva SA |
| Repositorio `projects/dation-runtime-v2-2026/locations/us-west1/repositories/dation-runtime` | `roles/artifactregistry.reader` a la nueva SA |
| SA runtime `dation-runtime@dation-runtime-v2-2026.iam.gserviceaccount.com` | `roles/iam.serviceAccountUser` a la nueva SA; únicamente `actAs` sobre esa identidad |
| SA deployer nueva | `roles/iam.workloadIdentityUser` al principal federado exacto indicado abajo |

Custom role: exclusivamente `run.services.get`, `run.services.update`,
`run.services.getIamPolicy`, `run.revisions.get`. No create/delete, setIamPolicy,
run.jobs.*, secretAccessor, actAs sobre otras cuentas, Owner, Editor, Token Creator,
roles de proyecto ni permiso de ejecutar Jobs. Se consulta servicio/revisión,
no operaciones a nivel proyecto. El rol se define en el proyecto pero **se asigna
sólo al servicio**. Lectura Registry es metadata/contenido de la imagen, no secretos.

Pool nuevo dedicado `dation-github-ux`, provider `github-main-ux` en global:

- Issuer: `https://token.actions.githubusercontent.com`.
- Provider: `projects/332279365872/locations/global/workloadIdentityPools/dation-github-ux/providers/github-main-ux`.
- Audience exclusiva: `https://iam.googleapis.com/` seguida del provider completo.
- Mapping: `google.subject=assertion.repository_id`.
- Binding exclusivo: `principal://iam.googleapis.com/projects/332279365872/locations/global/workloadIdentityPools/dation-github-ux/subject/1114679650`.
- Condiciones simultáneas: repository `nicsejara/Dation`, repository_id `1114679650`,
  repository_owner_id `249153366`, ref `refs/heads/main`, sub
  `repo:nicsejara/Dation:environment:ux-mvp-auto`.
- Más uno de estos pares exactos:
  - event `workflow_run`, workflow_ref `nicsejara/Dation/.github/workflows/dation-ux-autorelease.yml@refs/heads/main`;
  - event `workflow_dispatch`, workflow_ref `nicsejara/Dation/.github/workflows/dation-ux-ops.yml@refs/heads/main`.

No se habilitan APIs. Si IAM Credentials/STS u otra API requerida no están ya ON,
NO-GO con evidencia; pedir autorización puntual. Cloud Build/Scheduler deben seguir
OFF. No se consulta ni modifica el proyecto anterior.

### Procedimiento único preparado para después de aprobar

Desde un checkout limpio del SHA de G6 revisado, Python estándar + gcloud:

```sh
python3 scripts/release/g6_bootstrap.py
# Revisar el plan y su plan_sha256. NO ejecutar la línea siguiente sin GO específico.
python3 scripts/release/g6_bootstrap.py --apply \
  --owner-go GO_G6_BOOTSTRAP_IDENTITY --plan-sha256 SHA256_DEL_PLAN_APROBADO
```

Sin `--apply` no hay red ni mutaciones. Con GO+hash exactos: verificar identidad,
APIs y políticas reales antes de escribir; imprimir delta por recurso y etags;
crear sólo identidades/rol faltantes y sumar los cuatro bindings sin borrar otros
miembros. Objetos existentes diferentes, políticas condicionales inesperadas,
roles amplios, claves estáticas, otro provider en ese pool, padre de proyecto no
revisado o HTTP401/403 son NO-GO. Repetición tras corte comprueba el estado parcial
y no recrea lo correcto. El SDK gcloud hace read-modify-write con etag en bindings.
No es una transacción multirrecurso: si falla, se conserva el estado parcial y se
inspecciona la causa sin ampliar permisos. No cambia tráfico ni activa autodeploy.

La comprobación final de metadatos no prueba OIDC. Luego se ejecutará sólo
`dation-ux-ops.yml / preflight`, con lectura del servicio y revisión, testIamPermissions
sobre servicio/actAs runtime y lectura OCI por digest con crane verificado. Cualquier
fallo es NO-GO. No se hace deploy para probar permisos.

## Delta GitHub propuesto (no aplicado)

1. Integrar G6 únicamente con FAST+FULL+required-gate verdes en su candidato R4.
2. Ruleset activo para main: PR requerido, `required-gate` obligatorio, push directo
   restringido y revisión CODEOWNERS en paths críticos. R1/R2 sin paths críticos
   no exige otro aprobador de infraestructura en cada release. El verificador usa
   las reglas efectivas de `/rules/branches/main` y exige protección real.
   Con un único propietario que también crea el PR, no puede autoaprobar su
   CODEOWNERS review: acordar segundo revisor de confianza o bypass administrativo
   explícito exclusivamente para cambios críticos R4; no ocultar esta limitación.
3. Environment `ux-mvp-auto`: sólo main, sin secretos estáticos. Después del GO
   inicial no añadir un reviewer obligatorio para cada R1/R2 autorizado. El subject
   del environment y ambos workflow_ref se verifican también en WIF.
4. Variables de repositorio, controladas por administrador:

| Variable | Valor tras aprobación/verificación |
| --- | --- |
| `DATION_UX_BOOTSTRAP_APPROVED` | `true` sólo tras metadata IAM verificada para el preflight |
| `DATION_UX_POLICY_SHA256` | SHA-256 real de `infra/zero-idle/ux-autopilot-policy.json` revisado |
| `DATION_UX_BASELINE_SHA` | Commit OCI de la imagen activa verificado por preflight, no supuesto |
| `DATION_UX_AUTODEPLOY_ENABLED` | Mantener ausente/`false` hasta GO del primer piloto; `true` sólo entonces |

La política y el baseline son guardas adicionales. Un baseline más nuevo no permite
colar un backend pendiente: también se compara con el commit OCI realmente activo.
No usar `792470...` ni PR113 como estado desplegado sin lectura real.

## Cierre del bootstrap

Evidencia exigida: IAM delta leído/aplicado/read-back, OIDC de lectura PASS, main
protegido, environment main-only y hashes/baseline confirmados. Después, autorizar
un pequeño piloto R1 y posteriormente R2; comprobar visualmente ambos. Hasta ese
momento el resultado es código preparado, **no autopilot operativo**.
