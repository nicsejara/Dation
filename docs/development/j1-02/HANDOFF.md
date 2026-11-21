# Contratos para J1.03 / J1.04

## J1.03 — Data Preparation

Entrada: definición V2 confirmada, `case_work_id` estable, nuevo Case UUID y binding explícito `{model_id, model_version_id, configuration_hash, contract_hash}`. La vista J1.01 no selecciona ni sobrescribe ese binding por navegar. Los drafts tienen namespace `dation.cases.working.v2` con usuario/workspace y TTL ya existentes.

El adaptador usa `mountCorePreparation`, `mountDataContractView` y el compilador existente. La preparación recibe la versión exacta y, si corresponde, parent Case. Dos entidades para modelos históricos; tres para catálogo, incluyendo `order_lines`. `readExisting=true` evita POST en Back/Forward; iniciar, cambiar modelo o limpiar una sesión expirada son acciones explícitas. Se preservan candidatos de otra sesión sin mezclarlos.

Finalize congela `UltimateCaseCreateV2` completo y el Case UUID antes de la petición. No crear por el endpoint directo sin preparación: API y SQL lo rechazan. Una respuesta perdida requiere reenvío del mismo intent. El servicio existente recupera Case + Pack, sin duplicarlos. La definición inicial se escribe atómicamente con el Case. Los límites, permisos, owners y contratos previos siguen vigentes.

## J1.04 — navegación y Graph

Ruta existente `/app/ddas/logistics/case` con `journey_version=v2`. `case_view=library|definition|history|runs|data|inputs|model`; modos `configure|review|edit`. `data` exige borrador, `inputs` y `model` exigen Case persistido. Revision UUID y work UUID son recursos distintos. Los campos de negocio no se serializan en URL.

Se conservan `return_view`, `return_node`, `return_run`, centro y validación de existencia/permisos del destino por `returnFromCore`. Si la corrida no está accesible, el usuario confirma el fallback al Graph del mismo Case. No se elige otra corrida ni se pierde el origen para facilitar el retorno.

Graph abre Review del Case, nunca Edit automático. `core_step=1/2/3` conserva su significado legacy; el adaptador de un Case V2 muestra el modelo publicado / los datos del Case / su definición, respectivamente. La derivación desde Graph conserva parent y revisión exacta, genera otro borrador y requiere reconfirmación. El historial de definiciones se consulta en sus RPC; las corridas se consultan en el historial real de cada nodo.

## Reglas inmutables de ejecución

Run/context/artifacts guardan el binding completo de definición. Sólo los IDs administrativos de revisión se excluyen de la proyección matemática; políticas y aceptación están incluidas. Una edición de nombre no cambia el input hash ni reescribe el resultado. El D2 de un D1 aprobado conserva la definición que usó ese D1, incluso si el nombre del Case cambió después. KPI es lectura certificada, no aprobación ni nuevo motor.

Flags OFF cierran creación/edición/admisiones nuevas V2 y mantienen lectura. La capa SQL es aditiva y no debe revertirse destructivamente después de crear Cases V2. Ver `ACTIVATION_AND_ROLLBACK.md`.
