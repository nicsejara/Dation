# Golden Dation · Primeros pasos v1

Pack ficticio controlado para recorrer D1 y D2: cuatro órdenes (Córdoba → Rosario/Santa Fe) y dos vehículos, propio/tercerizado. Fechas fijas de octubre de 2026; no representa una operación actual ni el Golden Pallets externo. Los motores ejecutan los mismos cálculos y aprobaciones que con archivos propios.

`manifest.json` fija versión, SHA-256 y filas. La carga verifica los hashes antes de persistir. Los CSV y manifest deben revisarse juntos y probar D1/D2 antes de cambiar la versión. No se genera un resultado precalculado ni se aprueba automáticamente.

Cada workspace reutiliza los mismos bytes: no crea copias por clic ni cambia el origen/nombre de un archivo ya existente. Los nuevos llevan `is_sample=true`, nombre y etiqueta Demo. Casos, packs, historial y contexto de ejecución muestran el origen si cualquiera de sus entradas es demo. La flota predeterminada se conserva y los archivos archivados requieren revisión explícita en Data Hub. Las cargas parciales usan el journal existente y se recuperan repitiendo la acción; abandonar la pantalla no elimina archivos confirmados.
