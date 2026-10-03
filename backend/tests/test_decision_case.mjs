import test from "node:test";
import assert from "node:assert/strict";

import {
  STATUS,
  createDecisionCase,
  deriveDecisionNodes,
  replaceInputs,
  transitionNode,
} from "../app/static/js/dispatch/decision-case.mjs";

const orders = {id: "orders-1"};
const fleet = {id: "fleet-1"};

const fullReadiness = {
  decisions: [
    {id: "logistics_assignment", data_ready: true},
    {id: "logistics_scheduling", data_ready: true},
    {id: "logistics_final_assignment", data_ready: true},
  ],
};

const partialReadiness = {
  decisions: [
    {id: "logistics_assignment", data_ready: true},
    {id: "logistics_scheduling", data_ready: false},
    {id: "logistics_final_assignment", data_ready: false},
  ],
};

test("assignment approval unlocks scheduling when its data is ready", () => {
  let current = createDecisionCase(
    "case-1",
    orders,
    fleet,
    "2026-10-03T00:00:00Z",
  );
  current = transitionNode(
    current,
    "logistics_assignment",
    STATUS.APPROVED,
    {
      run_id: "run-1",
      approved_at: "2026-10-03T01:00:00Z",
    },
  );

  const nodes = deriveDecisionNodes(
    current,
    fullReadiness,
  );

  assert.equal(
    nodes.logistics_assignment.status,
    STATUS.APPROVED,
  );
  assert.equal(
    nodes.logistics_scheduling.status,
    STATUS.AVAILABLE,
  );
  assert.equal(
    nodes.logistics_final_assignment.status,
    STATUS.LOCKED,
  );
});

test("assignment approval does not bypass missing scheduling data", () => {
  let current = createDecisionCase(
    "case-1",
    orders,
    fleet,
  );
  current = transitionNode(
    current,
    "logistics_assignment",
    STATUS.APPROVED,
  );

  const nodes = deriveDecisionNodes(
    current,
    partialReadiness,
  );

  assert.equal(
    nodes.logistics_scheduling.status,
    STATUS.NEEDS_DATA,
  );
});

test("changing inputs creates a new case and marks predecessor stale", () => {
  const current = transitionNode(
    createDecisionCase(
      "case-1",
      orders,
      fleet,
      "2026-10-03T00:00:00Z",
    ),
    "logistics_assignment",
    STATUS.APPROVED,
    {run_id: "run-1"},
  );

  const next = replaceInputs(
    current,
    "case-2",
    {id: "orders-2"},
    fleet,
    "2026-10-03T02:00:00Z",
  );

  assert.equal(next.id, "case-2");
  assert.equal(
    next.nodes.logistics_assignment.status,
    STATUS.AVAILABLE,
  );
  assert.equal(
    next.stale_predecessor.status,
    STATUS.STALE,
  );
  assert.equal(
    next.stale_predecessor.approved_run_id,
    "run-1",
  );
});
