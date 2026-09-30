# Logistics DDA — Lógica de decisión y trade-offs

## Preset: minimizar costo

Para cada despacho el engine prioriza:

1. menor `total_cost`,
2. ante empate, menor `required_trips`,
3. ante nuevo empate, menor `total_distance_km`,
4. finalmente nombre de vehículo para desempate determinístico.

## Preset: minimizar viajes

Para cada despacho el engine prioriza:

1. menor `required_trips`,
2. ante empate, menor `total_distance_km`,
3. ante nuevo empate, menor `total_cost`,
4. finalmente nombre de vehículo.

## Modo personalizado

Para cada despacho:

1. se evalúan todas las alternativas disponibles;
2. costo y viajes se normalizan con Min-Max;
3. se aplica el score ponderado;
4. se elige el menor score;
5. se aplican criterios de desempate determinísticos.

Si el peso de costo es mayor o igual que el de viajes, el desempate favorece primero menor costo. Si viajes tiene mayor peso, favorece primero menor cantidad de viajes.

Los extremos 100/0 y 0/100 reutilizan exactamente las lógicas de los presets para garantizar compatibilidad matemática.

## Baseline

Baseline no es una alternativa optimizada. Es la asignación de vehículo informada en el archivo de entrada y funciona como referencia comparativa para cuantificar impacto potencial. No debe interpretarse automáticamente como la situación operativa actual.

## Sensibilidad

Cuando una configuración personalizada coincide con `min_cost` o `min_trips`, explicalo explícitamente.

Ejemplo:

> Con 85% de prioridad sobre costo y 15% sobre viajes, la asignación resultante coincide con el escenario de costo mínimo. Aumentar todavía más el peso de costo no cambia la solución dentro de las alternativas modeladas.

Si no coincide con ningún extremo, describí qué cambia y cuántas asignaciones difieren.

## Trade-offs esperables

### Vehículo más grande

Puede reducir viajes y kilómetros, pero aumentar costo por km o costo fijo.

### Vehículo más pequeño

Puede tener menor costo unitario, pero necesitar más viajes y acumular más kilómetros o costos fijos.

Por lo tanto, capacidad, costo y viajes pueden empujar la decisión en direcciones distintas.

## Cómo explicar una recomendación

1. Identificá modo y pesos.
2. Identificá el escenario recomendado.
3. Compará contra la asignación de referencia (`baseline`) para cuantificar impacto.
4. Compará contra ambos extremos para explicar sensibilidad.
5. Indicá cuántos despachos cambian de vehículo.
6. Usá los principales drivers provistos por backend.
7. Cerrá con el supuesto o restricción más material.

## "Mejor alternativa"

Cuando el usuario pregunte "¿por qué es la mejor alternativa?", interpretalo como:

> ¿por qué el motor la recomienda para la configuración seleccionada dentro del universo de alternativas modeladas?

No conviertas esa frase en una afirmación absoluta.
