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

test("new Decision Cases use the v2 run history contract", () => {
  const current = createDecisionCase("case-1", orders, fleet);
  assert.equal(current.schema_version, "decision_case_v2");
  assert.deepEqual(
    {
      latest_run_id: current.nodes.logistics_assignment.latest_run_id,
      approved_run_id: current.nodes.logistics_assignment.approved_run_id,
      run_count: current.nodes.logistics_assignment.run_count,
      latest_execution_status: current.nodes.logistics_assignment.latest_execution_status,
    },
    {
      latest_run_id: null,
      approved_run_id: null,
      run_count: 0,
      latest_execution_status: null,
    },
  );
});

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
      approved_run_id: "run-1",
      latest_run_id: "run-1",
      run_count: 1,
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

test("stale downstream decisions survive readiness derivation", () => {
  let current = createDecisionCase("case-1", orders, fleet);
  current = transitionNode(
    current,
    "logistics_assignment",
    STATUS.APPROVED,
    {run_id: "assignment-2", approved_run_id: "assignment-2"},
  );
  current = transitionNode(
    current,
    "logistics_scheduling",
    STATUS.STALE,
    {
      run_id: "schedule-1",
      approved_run_id: "schedule-1",
      latest_run_id: "schedule-1",
      run_count: 1,
    },
  );

  const nodes = deriveDecisionNodes(current, fullReadiness);
  assert.equal(nodes.logistics_scheduling.status, STATUS.STALE);
  assert.equal(nodes.logistics_scheduling.approved_run_id, "schedule-1");
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
    {run_id: "run-1", approved_run_id: "run-1"},
  );

  const next = replaceInputs(
    current,
    "case-2",
    {id: "orders-2"},
    fleet,
    "2026-10-03T02:00:00Z",
  );

  assert.equal(next.id, "case-2");
  assert.equal(next.schema_version, "decision_case_v2");
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
