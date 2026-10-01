# Guía de pruebas — DDA Logística 1.0

Todos los datos de esta carpeta son **sintéticos**. No representan disponibilidad, tarifas ni emisiones reales. Primero debe estar aplicada la migración y desplegada la versión nueva; consultar `backend/DEPLOYMENT.md`.

## Prueba principal

1. Cargar `fleet.csv` como Flota, etiquetarla y marcarla vigente.
2. Cargar `orders.csv` como Órdenes: debe mostrar 100 registros, 2.682 unidades, 2.384.000 kg, 28 rutas y fechas del 1 al 10 de octubre de 2026.
3. Continuar a configuración, elegir Balanceado y permitir tercerización. Revisar las advertencias de tardanza inevitable; no son errores de carga.
4. Ejecutar. Verificar calendario, viajes y entregas por orden; comparar con Despacho directo. Abrir filas de carga y exportar JSON y plan CSV.
5. Reejecutar el mismo caso y verificar igual `result_fingerprint`; el ID y la hora de corrida cambian. Reabrir la corrida desde el historial.
6. Cambiar a Entrega más rápida y contrastar plazo, costo y viajes; los resultados pueden coincidir para ciertas prioridades y la interfaz debe indicarlo.
7. Recargar la página y abrir otra carga: la flota vigente debe poder reutilizarse sin volver a subirla.

`orders_1000.csv` repite los patrones de demanda con IDs únicos para probar el tamaño de 1.000 órdenes y 26.820 unidades. Usa `fleet.csv`. El motor aplica heurística para este tamaño y debe decirlo; no exigirle etiqueta de óptimo.

La flota propia tiene 167.000 kg de capacidad de salidas diarias. El tercerizado grande tiene tarifa 30 % mayor al grande propio. Es una calibración de ejemplo para hacer visibles tercerización/reprogramación, no un dato comercial real.

## Casos de control calculables

Usar **los dos CSV de la misma subcarpeta**, con el objetivo y decisión indicados. `cases/expected.json` contiene comprobaciones automáticas.

| Caso | Configuración | Resultado esperado |
|---|---|---|
| 01_consolidacion | Viajes mínimos | 2 órdenes de 400 kg, 1 viaje de 800 kg |
| 02_unidades_indivisibles | Costo mínimo | 3 unidades de 600 kg, 3 viajes; 2 tercerizados |
| 03_reprogramacion | Costo mínimo | 2 viajes propios en dos días, sin tercerización |
| 04_tardanza_inevitable | Entrega más rápida | 1 viaje, sale el 1/oct, llega el 4/oct; 2 días tarde |
| 05_anomalia_incluir | Costo mínimo, incluir A | 52 unidades conservadas; la anomalía queda registrada |
| 06_anomalia_excluir | Costo mínimo, excluir A | Solo B: 1 unidad; A excluida explícitamente |
| 07_sin_cobertura | Costo mínimo | Error sin plan parcial: 3 viajes requeridos, 1 salida disponible |
| 08_fecha_invalida | Carga | Rechazar 31/feb con indicación de columna/fila |
| 09_ruta_inconsistente | Carga | Rechazar distancias diferentes para la misma ruta |

En los casos 05 y 06 el archivo es intencionalmente idéntico: la deduplicación debe reutilizar el dataset, pero las decisiones de anomalía generan corridas diferentes. Varias flotas de control también son idénticas; reutilizarlas es correcto.

## Comprobaciones de uso

- Los tres sliders suman 100 % y el modal muestra ambas versiones.
- “Configuración lista” tiene el mismo ancho que los otros bloques, también en móvil.
- Ningún viaje supera capacidad ni salidas disponibles; todas las unidades incluidas se entregan.
- El comparador no muestra ahorro ejecutable contra una referencia sin cobertura válida.
- La explicación puede fallar por configuración externa del proveedor; eso no debe invalidar el plan persistido.
- El plan CSV exportado tiene una fila por carga de orden/viaje. El costo y CO₂ del viaje aparecen solo en la primera carga para evitar sumarlos varias veces.

Regenerar casos: `PYTHONPATH=backend python scripts/generate_dispatch_fixtures.py` desde la raíz. La conversión del archivo original preservó fechas ISO y vehículo informado como referencia opcional. Las pruebas automatizadas leen estos mismos CSV.
