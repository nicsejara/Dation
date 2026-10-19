# Fase 9 · Configuración y plan Free

El usuario definió el plan Free como gratuito para todos los usuarios durante la maduración del MVP. Reemplaza el ejemplo Early Adopter/facturación manual del documento maestro: no hay pagos, tarjeta requerida, prueba con vencimiento, límite comercial de miembros ni botones de upgrade. La gratuidad no modifica roles, aislamiento ni disponibilidad de productos futuros.

## Configuración del workspace

Cuatro pestañas en `/app/settings`: General, Operación, Decision Data Assets y Plan y facturación. `settings_tab` conserva la selección en enlaces, atrás/adelante y recarga mediante el router compartido. Tabs con roles ARIA, foco por flechas/Home/End y activación Enter/Space; disposición de ancho completo y filas adaptadas a móvil. Los estados de carga/error permiten reintentar sin mutaciones. El diagnóstico interno sigue como disclosure secundario exclusivo de Admin y tiene su propio lifecycle, separado del formulario.

General guarda nombre, país ISO, idioma de formatos y zona horaria. El idioma modifica la presentación de fechas/números; los textos de la interfaz siguen en español. No se agrega upload de logo en esta fase, porque el alcance lo define como opcional. Operación guarda moneda, peso, distancia y unidad logística en los campos existentes de `workspaces`. Hay una vista previa explícita de formatos. No se convierten datasets, costos ni resultados guardados, ni se cambian unidades canónicas de los motores.

Sólo Admin guarda. Operator y Viewer consultan formularios deshabilitados. Cada guardado declara la sección y la versión del workspace; body estricto y SQL impiden modificar plan, roles, entitlements o workspace por este endpoint. Lock y revalidación de membresía/rol dentro de la transacción. Conflicto 409 exige actualizar y revisar, sin replay implícito. Se auditan sección, actor y valores anteriores/nuevos. General conserva preferencias operativas y viceversa. Cambios confirmados refrescan la identidad, incluido el nombre del workspace en el shell.

Los helpers de presentación usan idioma, país y zona horaria del workspace en Home, Data Hub, Decision Center y Equipo. Moneda y unidades quedan como preferencias persistentes y vista previa; los dashboards históricos conservan sus valores, cálculos y formatos actuales hasta que exista un contrato de moneda/unidades en cada corrida. No atribuir a un resultado histórico una moneda nueva del workspace.

## Disponibilidad y Free

Decision Data Assets reutiliza el catálogo y los grants actuales. Logística muestra Habilitado/No habilitado según acceso; las seis familias futuras siguen Próximamente aunque un grant esté mal configurado como enabled. No hay configuración de motores por cliente ni compra de acceso.

Las definiciones de productos viven en `platform/dda-catalog.mjs`, sin depender del renderizador opcional del catálogo. Si falla ese renderizador, el shell, el acceso de respaldo a Logística y las pestañas de Configuración siguen disponibles. La regresión de navegador bloquea explícitamente su descarga y verifica ambos recorridos.

`platform_workspace_settings` devuelve la política universal Free desde el servidor para el workspace heredado y los creados después: activo, importe cero, sin método de pago, sin trial y sin límite comercial de miembros. No hacen falta columnas comerciales ni una tabla de suscripción mientras todos comparten esa política. Plan y facturación muestra Free/Gratis, miembros activos reales y DDAs habilitados. No inventa facturas, pagos, fecha de renovación, límites de uso ni automatizaciones comerciales. No se envían datos a proveedores de cobro.

## Persistencia y verificación

Migración `20261019110000_platform_workspace_settings.sql`: únicamente dos RPC service-only, sin tablas nuevas, backfill, cambios a funciones previas o modificaciones de filas. El GET es una proyección acotada; PATCH administra campos existentes y audita. Se mantienen las ACL/RLS previas. La configuración es accesible sin grant Logística y no lo activa.

`test_workspace_settings.py` comprueba Free para workspace existente/nuevo, roles, aislamiento, DTO y RPC, conflictos/CAS simultáneos, independencia de grants y conservación exacta de corridas/datasets/aprobaciones tras guardar. Un navegador con BFF real edita General/Operación, verifica guardado, teclado, 16 capturas 1440/1024/768/390, geometría, contraste, atrás/adelante/recarga y vuelve al dashboard original. La suite sintética añade retry/conflicto/sólo lectura sin replay. Node cubre recursos del router y formatos concretos por locale/timezone sin conversión de cantidades.

Antes de publicar se exige CI del SHA exacto, backup/restauración en PG17 con todas las migraciones y comparación de valores/permisos. Después se registran CI de main, build/revisiones/100% API y worker, HTTP privado, assets y archivos originales. No se crean cuentas, membresías ni fixtures productivos. La prueba manual del usuario sigue prevista para terminar todas las fases.

Siguiente: Fase 10, auditoría y actividad. No se inicia automáticamente.
