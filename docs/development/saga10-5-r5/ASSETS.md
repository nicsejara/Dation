# Assets, procedencia y costo estático

Diez ilustraciones R5 suministradas por el usuario, creadas para su paquete. Se utilizan los WebP originales, sin recomprimir, regenerar ni incorporar stock/tipografías de terceros. [Mapa, tamaños y SHA-256](ASSETS.json).

- Familia completa: **69,156 bytes (67.54 KiB)**, diez URLs locales.
- PNG suministrados equivalentes: 1,160,149 bytes; WebP reduce aproximadamente 94 % esa alternativa. Esto compara formatos del paquete, no afirma que R5 pese menos que los SVG inline de R4.
- Primera combinación Pallet con cinco opciones vacías y resumen cargado: hasta 38,964 bytes de archivos únicos. Miniaturas y resumen vacío reutilizan las mismas URLs.
- Tamaño nativo 300×335, object-fit contain, marcos estables; carga lazy y decode async. Imágenes y tarjetas se reutilizan entre inputs; prueba real confirma cero solicitudes de arte por pulsación.
- Mapa completo 5×2 y miniaturas comprobado en navegador. Sin solicitudes de imágenes/fuentes a terceros. Fallback 404 ensayado expresamente y separado de la prueba de carga normal.

`evidence/asset-network.json` contiene transferencia y duración medidas en el fixture local; no son un SLA ni una medición Cloud Run. En un enlace ideal de 10 Mbit/s, 69 KB representan unos 55 ms de transferencia pura, excluidos RTT, TLS, servidor y decode. No se crean servicios, procesos residentes ni infraestructura. El costo monetario futuro depende del tráfico/cache y de las tarifas de la plataforma; esta tarea no publica ni genera operaciones GCP.
