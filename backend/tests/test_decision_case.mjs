import test from "node:test";
import assert from "node:assert/strict";

import {
  STATUS,
  createDecisionCase,
  deriveDecisionNodes,
  replaceInputs,
  transitionNode,
  continuationState,
  nextDecisionId,
  getCaseTransitionNotice,
} from "../app/static/js/dispatch/decision-case.mjs";

const orders = {id: "orders-1"};
const fleet = {id: "fleet-1"};

test('transition notice requires a fresh, verified lineage with a different Data Pack',()=>{
  const previous={...createDecisionCase('previous',orders,fleet),persisted:true};
  const current=replaceInputs(previous,'current',{id:'orders-2'},fleet);
  const context={decisionCase:current,predecessor:{decision_case:previous},transitionCaseId:current.id};
  assert.deepEqual(getCaseTransitionNotice(context),{caseId:'current',predecessorId:'previous'});
  assert.equal(getCaseTransitionNotice({...context,transitionCaseId:null}),null,'opening history is not a new transition');
  assert.equal(getCaseTransitionNotice({...context,decisionCase:previous}),null,'first case');
  assert.equal(getCaseTransitionNotice({...context,predecessor:null}),null,'deleted predecessor');
  assert.equal(getCaseTransitionNotice({...context,predecessor:{decision_case:{...previous,signature:'wrong'}}}),null);
  assert.equal(getCaseTransitionNotice({...context,decisionCase:{...current,stale_predecessor:{...current.stale_predecessor,id:current.id}}}),null);
  assert.equal(getCaseTransitionNotice({...context,decisionCase:{...current,signature:previous.signature}}),null);
  assert.equal(getCaseTransitionNotice(),null);
});

test('replacing both files preserves the last persisted predecessor through local intermediate cases',()=>{
  const previous={...createDecisionCase('previous',orders,fleet),persisted:true};
  const intermediate=replaceInputs(previous,'intermediate',{id:'orders-2'},fleet);
  const current=replaceInputs(intermediate,'current',{id:'orders-2'},{id:'fleet-2'});
  assert.equal(current.stale_predecessor.id,previous.id);
  assert.equal(current.stale_predecessor.signature,previous.signature);
  assert.equal(previous.stale_predecessor,null);
});

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

const metadata={logistics_scheduling:{implemented:true,label:'Planificación',short:'Planificación'},logistics_final_assignment:{implemented:false,label:'Asignación final'}};
test('continuation uses actual approval and readiness without changing the case',()=>{
  const current=transitionNode(createDecisionCase('case',orders,fleet),'logistics_assignment',STATUS.APPROVED,{run_id:'approved',approved_run_id:'approved'});
  const before=structuredClone(current);
  assert.equal(continuationState(current,'logistics_assignment','candidate',fullReadiness,metadata),null);
  assert.equal(continuationState(current,'logistics_assignment','approved',partialReadiness,metadata).state,'needs_data');
  assert.deepEqual(continuationState(current,'logistics_assignment','approved',fullReadiness,metadata),{state:'available',nodeId:'logistics_scheduling',label:'Continuar con Planificación →'});
  assert.deepEqual(current,before);
});
test('approved downstream and unimplemented decisions do not open an empty configuration',()=>{
  let current=transitionNode(createDecisionCase('case',orders,fleet),'logistics_assignment',STATUS.APPROVED,{run_id:'a',approved_run_id:'a'});
  current=transitionNode(current,'logistics_scheduling',STATUS.APPROVED,{run_id:'s',approved_run_id:'s'});
  assert.equal(continuationState(current,'logistics_assignment','a',fullReadiness,metadata).state,'finished');
  assert.equal(continuationState(current,'logistics_scheduling','s',fullReadiness,metadata).state,'unavailable');
  assert.equal(nextDecisionId('unknown'),null);assert.equal(nextDecisionId('logistics_final_assignment'),null);
});
test('running or review next nodes open through the existing-run rail, never through a new config',()=>{
  let current=transitionNode(createDecisionCase('case',orders,fleet),'logistics_assignment',STATUS.APPROVED,{run_id:'a',approved_run_id:'a'});
  for(const status of [STATUS.RUNNING,STATUS.REVIEW,STATUS.STALE]){
    current=transitionNode(current,'logistics_scheduling',status,{run_id:'s'});
    assert.equal(continuationState(current,'logistics_assignment','a',fullReadiness,metadata).state,status);
  }
});

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
