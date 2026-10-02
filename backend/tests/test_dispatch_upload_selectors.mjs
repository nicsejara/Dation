import assert from "node:assert/strict";
import {
  continueState,
  deriveCardState,
  groupProblems,
  technicalPreflightErrors,
} from "../app/static/js/dispatch/upload/selectors.mjs";

assert.equal(deriveCardState({}).key, "empty");
assert.equal(
  deriveCardState({phase: "processing"}).key,
  "processing",
);
assert.equal(
  deriveCardState({phase: "uploading"}).key,
  "uploading",
);
assert.equal(
  deriveCardState({
    report: {
      valid: false,
      counts: {errors: 3, warnings: 0},
    },
  }).key,
  "error",
);
assert.equal(
  deriveCardState({
    report: {
      valid: true,
      counts: {errors: 0, warnings: 2},
    },
    dataset: {id: "saved"},
  }).key,
  "warning",
);
assert.equal(
  deriveCardState({
    report: {
      valid: true,
      counts: {errors: 0, warnings: 0},
    },
    dataset: {id: "saved"},
  }).label,
  "✓ Archivo correcto",
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

const businessOnly = {
  valid: false,
  errors: [
    {
      code: "UNIT_EXCEEDS_CAPACITY",
      detail: "Una unidad supera la capacidad disponible.",
    },
  ],
  warnings: [
    {
      code: "UNAVOIDABLE_LATE",
      detail: "Entrega tardía.",
    },
  ],
};
assert.equal(technicalPreflightErrors(businessOnly).length, 0);

const ready = continueState({
  storageAvailable: true,
  orders: {id: "o"},
  fleet: {id: "f"},
  reports: {
    orders: {valid: true, counts: {errors: 0, warnings: 0}},
    fleet: {valid: true, counts: {errors: 0, warnings: 0}},
  },
  preflight: businessOnly,
  phases: {orders: "idle", fleet: "idle"},
  saveErrors: {},
});
assert.equal(ready.enabled, true);

const relationFailure = continueState({
  storageAvailable: true,
  orders: {id: "o"},
  fleet: {id: "f"},
  reports: {
    orders: {valid: true, counts: {errors: 0, warnings: 0}},
    fleet: {valid: true, counts: {errors: 0, warnings: 0}},
  },
  preflight: {
    errors: [
      {
        code: "UNKNOWN_CURRENT_VEHICLE",
        detail: "Referencia inexistente.",
      },
    ],
  },
  phases: {orders: "idle", fleet: "idle"},
  saveErrors: {},
});
assert.equal(relationFailure.enabled, false);
assert.equal(relationFailure.kind, "error");

console.log("dispatch upload selectors: ok");
