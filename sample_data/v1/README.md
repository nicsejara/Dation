# Guía de pruebas — DDA Logística 1.0

Todos los datos de esta carpeta son **sintéticos**. No representan disponibilidad, tarifas ni emisiones reales.

## Prueba de la nueva pantalla de carga

1. Abrir **Inicio → DDA Logística → Cargar datos**.
2. Confirmar que aparecen dos tarjetas: **Órdenes de envío** y **Flota disponible**.
3. Descargar una única plantilla desde cada tarjeta. Cada plantilla contiene 5 registros de ejemplo y debe volver a cargarse sin errores.
4. Cargar `orders.csv`: la pantalla principal debe mostrar sólo nombre, tamaño, estado y 100 registros.
5. Cargar `fleet.csv`: la pantalla principal debe mostrar sólo nombre, tamaño, estado y 4 registros.
6. Revisar la validación técnica. No deben aparecer advertencias de plazos, capacidad, costos, viajes ni resultados del optimizador.
7. Continuar a **Configurar decisión** cuando ambos archivos superen los controles técnicos.
8. Ejecutar y verificar calendario, viajes, entregas por orden y comparación contra **Despacho directo**.
9. Reejecutar el mismo caso: el `result_fingerprint` debe mantenerse; ID y hora de corrida cambian.
10. Recargar la pantalla: órdenes y flota guardadas deben poder reutilizarse sin volver a subir los CSV.

Si las migraciones aún no están activadas, los pasos 2–4 siguen funcionando como validación local. La pantalla muestra **Activación pendiente** y no permite guardar ni avanzar.

## Casos de error

- `cases/08_fecha_invalida`: debe informar fila, columna y formato de fecha esperado.
- `cases/09_ruta_inconsistente`: debe informar la distancia inconsistente.
- El archivo histórico `sample_data/InputData-LogisticsDDA.csv` debe detectarse como formato anterior que mezcla órdenes y flota.
- Un CSV con múltiples problemas debe presentar todos los detectados hasta el límite de 100 y permitir descargar el informe.

## Prueba del motor

`orders_1000.csv` repite patrones con IDs únicos para probar 1.000 órdenes y 26.820 unidades. Usa `fleet.csv`. Para este tamaño el motor aplica heurística y no debe etiquetar la solución como óptima.

La flota propia sintética tiene 167.000 kg de capacidad de salidas diarias. El tercerizado grande usa una tarifa 30 % mayor al grande propio. Es una calibración de demostración, no un dato comercial.

| Caso | Configuración | Resultado esperado |
|---|---|---|
| 01_consolidacion | Viajes mínimos | 2 órdenes de 400 kg, 1 viaje de 800 kg |
| 02_unidades_indivisibles | Costo mínimo | 3 unidades de 600 kg, 3 viajes; 2 tercerizados |
| 03_reprogramacion | Costo mínimo | 2 viajes propios en dos días, sin tercerización |
| 04_tardanza_inevitable | Entrega más rápida | 1 viaje, sale el 1/oct, llega el 4/oct; 2 días tarde |
| 05_anomalia_incluir | Costo mínimo, incluir A | 52 unidades conservadas |
| 06_anomalia_excluir | Costo mínimo, excluir A | Solo B: 1 unidad |
| 07_sin_cobertura | Costo mínimo | Error sin plan parcial |
| 08_fecha_invalida | Carga | Rechazar 31/feb |
| 09_ruta_inconsistente | Carga | Rechazar distancias diferentes para la misma ruta |

Regenerar casos:

```bash
PYTHONPATH=backend python scripts/generate_dispatch_fixtures.py
```


## Criterios visuales de la carga

Con estos fixtures la UI debe mostrar 100 órdenes, 2.682 unidades, 2.384 t, 28 rutas,
3 orígenes → 10 destinos, período 1–10 oct 2026 y prioridades 27 / 62 / 11. La flota
debe resumirse como 4 tipos, 11 camiones propios por día y 167 t/día.

La revisión conjunta debe agrupar las 7 órdenes con tardanza inevitable en un solo
aviso y mostrar que la demanda supera la capacidad propia en 9 de 10 días, con pico de
351,8 t el 9 oct.
