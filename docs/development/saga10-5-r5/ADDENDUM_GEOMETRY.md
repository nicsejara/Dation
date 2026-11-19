# Addendum obligatorio de geometría

Prioridad del propietario sobre los mockups. Ocho controles adicionales; no sustituyen los 110 del paquete.

| Control | Resultado y evidencia |
|---|---|
| Layout compartido 60/40, formulario izquierdo y resumen derecho | PASS · misma clase CSS/componente, R5.T01 |
| Ancho, padding, borde y alineación de resúmenes | PASS · iguales en cada viewport; padding 20 px |
| Ancho y alto de ambas tarjetas | PASS · ancho idéntico en cada viewport; alto 176 px |
| Padding, borde y radio de métricas | PASS · 16 px, 1 px, 10 px; igualdad CSS medida |
| Icono, tipografía y espacios interiores | PASS · icono 20×20, lectura 28 px; rectángulos interiores comparados |
| Inferior derecha del formulario izquierdo | PASS · right=0 y bottom=0 en ambos; columna 2/fila 1 hasta tablet |
| Reglas responsive compartidas | PASS · móvil columna 1/fila 2; resúmenes apilados con mismo gap |
| Sin overflow ni solapamientos | PASS · scrollWidth≤innerWidth y todos los hijos dentro de su tarjeta |

| Viewport | Resumen P1/P2 | Tarjeta P1/P2 | Posición grid |
|---|---|---|---|
| 1440 px | 306.39 / 306.39 px | 221.80×176 / 221.80×176 px | 2 / 1 |
| 1280 px | 242.39 / 242.39 px | 173.80×176 / 173.80×176 px | 2 / 1 |
| 768 px | 542.00 / 542.00 px | 263.00×176 / 263.00×176 px | 2 / 1 |
| 375 px | 217.00 / 217.00 px | 217.00×176 / 217.00×176 px | 1 / 2 |

[Mediciones JSON completas](evidence/addendum-geometry.json) · [Capturas](VISUALS.md). Tolerancia geométrica 0,5 px por redondeo subpixel; sin tolerancia para diferencias de estilos/grid. Los formularios contienen distinto número de campos: en vista apilada se compara el gap al formulario y la alineación izquierda, no una altura absoluta artificialmente igualada.
