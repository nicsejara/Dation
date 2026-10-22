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

const metadata={logistics_assignment:{implemented:true},logistics_scheduling:{implemented:true,label:'Planificación',short:'Planificación'},logistics_final_assignment:{implemented:false,label:'Asignación final'}};
const person={id:'owner',name:'Owner'},workflow={gates_enforced:true,attributes_applied:true,stages:{data_owner:{owner:person,owner_eligible:true},logistics_assignment:{owner:person,owner_eligible:true},logistics_scheduling:{owner:person,owner_eligible:true}}};
test('continuation checks current Run approval and real data readiness without mutations',()=>{
  const current=transitionNode(createDecisionCase('case',orders,fleet),'logistics_assignment',STATUS.APPROVED,{run_id:'approved',approved_run_id:'approved'});
  const before=structuredClone(current);
  assert.equal(continuationState(current,'logistics_assignment','candidate',fullReadiness,metadata,workflow),null);
  assert.equal(continuationState(current,'logistics_assignment','approved',partialReadiness,metadata,workflow).target.view,'logistics-map');
  assert.deepEqual(continuationState(current,'logistics_assignment','approved',fullReadiness,metadata,workflow),{state:'available',nodeId:'logistics_scheduling',label:'Configurar D2 · Planificación',target:{view:'logistics-config',node_id:'logistics_scheduling',run_id:null}});
  assert.deepEqual(current,before);
});
test('missing or ineligible next Owner routes to the same Case Map using dynamic metadata',()=>{
  const current=transitionNode(createDecisionCase('case',orders,fleet),'logistics_assignment',STATUS.APPROVED,{run_id:'a',approved_run_id:'a'});
  const dynamic={...metadata,logistics_scheduling:{...metadata.logistics_scheduling,label:'Scheduling',index:'02'}};
  for(const owner of [null,{id:'inactive'}]){
    const roles=structuredClone(workflow);roles.stages.logistics_scheduling={owner,owner_eligible:false};
    const next=continuationState(current,'logistics_assignment','a',fullReadiness,dynamic,roles);
    assert.equal(next.label,'Asignar Decision Owner · D2 Scheduling');assert.equal(next.target.view,'logistics-map');assert.equal(next.nodeId,'logistics_scheduling');
  }
});
test('last implemented approved Decision completes the Case with no future Decision CTA',()=>{
  let current=transitionNode(createDecisionCase('case',orders,fleet),'logistics_assignment',STATUS.APPROVED,{run_id:'a',approved_run_id:'a'});
  current=transitionNode(current,'logistics_scheduling',STATUS.APPROVED,{run_id:'s',approved_run_id:'s'});
  const next=continuationState(current,'logistics_scheduling','s',fullReadiness,metadata,workflow);
  assert.equal(next.state,'completed');assert.equal(next.target,undefined);assert.match(next.message,/CASE COMPLETADO/);
  assert.equal(nextDecisionId('unknown'),null);assert.equal(nextDecisionId('logistics_final_assignment'),null);
});
test('new-run continuation retains current Case, node and historical evidence',()=>{
  let current=transitionNode(createDecisionCase('case',orders,fleet),'logistics_assignment',STATUS.APPROVED,{run_id:'a',approved_run_id:'a'});
  for(const status of [STATUS.RUNNING,STATUS.REVIEW,STATUS.STALE,STATUS.APPROVED]){
    current=transitionNode(current,'logistics_scheduling',status,{run_id:'s'});const before=structuredClone(current);
    const next=continuationState(current,'logistics_assignment','a',fullReadiness,metadata,workflow);
    assert.equal(next.target.view,'logistics-config');assert.equal(next.target.node_id,'logistics_scheduling');assert.equal(next.target.run_id,null);assert.deepEqual(current,before);
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
