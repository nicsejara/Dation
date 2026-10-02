import assert from "node:assert/strict";
import {
  continueState,
  deriveCardState,
  groupProblems,
  stepTone,
} from "../app/static/js/dispatch/upload/selectors.mjs";

const table = [
  [
    {},
    "sin_archivo",
  ],
  [
    {validating: true},
    "validando",
  ],
  [
    {
      validation: {
        valid: false,
        counts: {errors: 2, warnings: 0},
      },
    },
    "invalido",
  ],
  [
    {
      validation: {
        valid: true,
        counts: {errors: 0, warnings: 2},
      },
      saved: {id: "saved"},
    },
    "con_avisos",
  ],
  [
    {
      validation: {
        valid: true,
        counts: {errors: 0, warnings: 0},
      },
      saved: {id: "saved"},
    },
    "valido",
  ],
  [
    {
      validation: {
        valid: true,
        counts: {errors: 0, warnings: 0},
      },
      storageAvailable: false,
    },
    "valido_sin_guardar",
  ],
  [
    {
      validation: {
        valid: true,
        counts: {errors: 0, warnings: 0},
      },
      error: "network",
    },
    "error_de_guardado",
  ],
  [
    {
      validation: {
        valid: true,
        counts: {errors: 0, warnings: 0},
      },
      saved: {id: "saved"},
      duplicate: true,
    },
    "reutilizado",
  ],
  [
    {
      validation: {
        valid: false,
        detected_format: "legacy_mixed",
        counts: {errors: 1, warnings: 0},
      },
    },
    "formato_anterior",
  ],
];

for (const [input, expected] of table) {
  const state = deriveCardState(input);
  assert.equal(state.key, expected);
}

const validSaved = deriveCardState({
  validation: {
    valid: true,
    counts: {errors: 0, warnings: 0},
  },
  saved: {id: "saved"},
});
assert.equal(
  validSaved.message.includes("No se guardó"),
  false,
);

const groups = groupProblems({
  errors: [
    {code: "INVALID_DATE", message: "Fecha inválida"},
    {code: "INVALID_DATE", message: "Fecha inválida"},
  ],
  warnings: [
    {code: "EXTRA_COLUMN", message: "Columna extra"},
  ],
});
assert.equal(groups.length, 2);
assert.equal(groups[0].items.length, 2);

assert.equal(
  continueState({
    storageAvailable: false,
  }).message,
  "Falta activar el almacenamiento de datos.",
);

assert.equal(
  continueState({
    storageAvailable: true,
    orders: {id: "o"},
    fleet: {id: "f"},
    preflight: {
      valid: true,
      findings: [
        {severity: "warning"},
        {severity: "warning"},
      ],
      readiness: {
        blockers: [],
      },
    },
  }).message,
  "2 avisos: podés continuar.",
);

assert.equal(
  continueState({
    storageAvailable: true,
    orders: {id: "o"},
    fleet: {id: "f"},
    preflight: {
      valid: true,
      readiness: {
        blockers: [],
      },
    },
  }).enabled,
  true,
);

assert.equal(
  stepTone({
    dataset: {id: "o"},
    report: {counts: {errors: 0, warnings: 0}},
    kind: "orders",
  }),
  "success",
);

console.log("dispatch upload selectors: ok");
