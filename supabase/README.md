# Esquema de aplicación

El baseline `baseline/20261010100000_public_schema.sql` captura el catálogo real
del proyecto `gijiinufjjurgfeehufj` al cierre de la Fase 3 (2026-10-10): siete
tablas, trece funciones, columnas/defaults, constraints/FKs, índices, triggers,
RLS y permisos. `20261010100000_catalog.json` es el manifiesto verificable.
No contiene filas ni credenciales. La versión capturada es PostgreSQL 17.6;
el privilegio `MAINTAIN` requiere PostgreSQL 17 o superior.

## Instalación nueva

Sobre un proyecto Supabase nuevo, con sus roles `anon`, `authenticated` y
`service_role` y su infraestructura administrada:

1. Aplicar **una sola vez** el baseline completo `20261010100000_public_schema.sql`.
2. Aplicar sólo las migraciones cuya fecha sea **posterior a `20261010100000`**, en
   orden: `20261010183000_persistence_traceability.sql` y
   `20261010190000_approval_clock_after_lock.sql`.
3. Configurar el bucket privado de entradas `dda-inputs` en Supabase Storage y las
   variables/secretos de la aplicación. El baseline no reemplaza `auth`, `storage`,
   `vault`, roles administrados ni configuración del proveedor.

No ejecutar las migraciones anteriores después del baseline: sus cambios ya están
incluidos. Los archivos históricos se conservan para documentar upgrades previos;
el DDL inicial anterior a octubre no estaba versionado.

## Actualización de la instalación existente

Sobre producción ya en Fase 3, aplicar únicamente
`20261010183000_persistence_traceability.sql` y luego
`20261010190000_approval_clock_after_lock.sql`, usando
`python scripts/apply_production_persistence.py` con el token administrativo
configurado de forma segura. El script compara el catálogo completo antes de
mutar y aborta si encuentra drift. **El baseline nunca se aplica a producción.**

La migración es transaccional y aditiva. No inventa actores ni eventos para
aprobaciones históricas. Los resultados y archivos conservan sus identificadores.
La API/worker anteriores siguen funcionando con el esquema nuevo; un rollback
repliega la imagen y conserva las tablas, columnas y evidencia nuevas.

Si Fase 4 ya está aplicada, el mismo script verifica la función de aprobación y
aplica únicamente el ajuste de reloj pendiente. Aborta ante una definición ajena a
las versiones revisadas; no reescribe fechas históricas.

## Prueba reproducible

CI crea PostgreSQL 17 efímero sin publicar puertos; sólo los roles de infraestructura
se simulan. Todos los tests SQL usan el DDL real capturado, en lugar del fixture
parcial de tablas antiguas. Se verifica la equivalencia del catálogo reconstruido,
instalación nueva + Fase 4, upgrade desde Fase 3 con datos históricos, privacidad,
concurrencia, historial y contratos del worker.

```bash
docker run -d --name dation-qa-postgres -e POSTGRES_HOST_AUTH_METHOD=trust postgres:17-alpine
cd backend
DATION_SQL_TEST_CONTAINER=dation-qa-postgres python -m unittest discover -s tests/integration -v
docker rm -f dation-qa-postgres
```

`scripts/capture_public_schema.py` es una herramienta de lectura administrativa;
se limita al esquema de Fase 3 para evitar sobrescribir este baseline con otro
estado. Para capturas futuras se debe versionar un baseline nuevo.
