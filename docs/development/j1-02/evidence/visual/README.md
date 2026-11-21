# Capturas reales J1.02

Chromium con API/Auth/Storage y PostgreSQL locales, datos sintéticos. Sin edición de imágenes. Cuatro viewports: 375, 768, 1280 y 1440 px. Las geometrías registran ancho de documento, controles de al menos 44 px y contraste medido; cero overflow horizontal.

| Escena | 1440 | 1280 | 768 | 375 |
|---|---|---|---|---|
| definition-history | [1440px](definition-history-1440.png) | [1280px](definition-history-1280.png) | [768px](definition-history-768.png) | [375px](definition-history-375.png) |
| derive-modal | [1440px](derive-modal-1440.png) | [1280px](derive-modal-1280.png) | [768px](derive-modal-768.png) | [375px](derive-modal-375.png) |
| dirty-modal | [1440px](dirty-modal-1440.png) | [1280px](dirty-modal-1280.png) | [768px](dirty-modal-768.png) | [375px](dirty-modal-375.png) |
| edit-error | [1440px](edit-error-1440.png) | [1280px](edit-error-1280.png) | [768px](edit-error-768.png) | [375px](edit-error-375.png) |
| graph-acceptance | [1440px](graph-acceptance-1440.png) | [1280px](graph-acceptance-1280.png) | [768px](graph-acceptance-768.png) | [375px](graph-acceptance-375.png) |
| library | [1440px](library-1440.png) | [1280px](library-1280.png) | [768px](library-768.png) | [375px](library-375.png) |
| library-error | [1440px](library-error-1440.png) | [1280px](library-error-1280.png) | [768px](library-error-768.png) | [375px](library-error-375.png) |
| review-draft | [1440px](review-draft-1440.png) | [1280px](review-draft-1280.png) | [768px](review-draft-768.png) | [375px](review-draft-375.png) |
| review-history | [1440px](review-history-1440.png) | [1280px](review-history-1280.png) | [768px](review-history-768.png) | [375px](review-history-375.png) |
| wizard-confirmed | [1440px](wizard-confirmed-1440.png) | [1280px](wizard-confirmed-1280.png) | [768px](wizard-confirmed-768.png) | [375px](wizard-confirmed-375.png) |
| wizard-empty | [1440px](wizard-empty-1440.png) | [1280px](wizard-empty-1280.png) | [768px](wizard-empty-768.png) | [375px](wizard-empty-375.png) |

Pruebas: `backend/tests/browser/test_decision_case_j102_visual.py`. `graph-acceptance` muestra el KPI PENDING real sin corridas; no simula una publicación productiva. El resto muestra biblioteca, definición, errores y confirmaciones reales de la fixture.

El benchmark corresponde a una lista inicial local con 27 Cases; página filtrada 25+1. La prueba de servicio verifica una sola llamada batch de metadatos por página, sin afirmar una latencia productiva garantizada.
