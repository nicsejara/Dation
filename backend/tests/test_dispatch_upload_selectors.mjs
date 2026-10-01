import assert from "node:assert/strict";
import {
  cardState,
  continueState,
  groupProblems,
  preflightTitle,
} from "../app/static/js/dispatch/upload/selectors.mjs";

assert.equal(cardState({}).key, "sin_archivo");
assert.equal(
  cardState({
    report: {valid: true, counts: {warnings: 0}},
    storageAvailable: false,
  }).key,
  "guardado_pendiente",
);
assert.equal(
  cardState({
    report: {valid: false},
  }).key,
  "invalido",
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
  "Falta activar el almacenamiento de Dispatch.",
);
assert.equal(
  continueState({
    storageAvailable: true,
    orders: {id: "o"},
    fleet: {id: "f"},
    preflight: {valid: true},
  }).enabled,
  true,
);
assert.equal(
  preflightTitle({code: "UNAVOIDABLE_LATE"}),
  "Plazo no alcanzable",
);

console.log("dispatch upload selectors: ok");
