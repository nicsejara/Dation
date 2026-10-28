import test from 'node:test';
import assert from 'node:assert/strict';
globalThis.window={};
const {caseFlowSteps}=await import('../app/static/js/dispatch/navigation/case-flow.mjs');
import {graphTarget,graphActionLabel} from '../app/static/js/dispatch/navigation/ultimate-graph.mjs';
const caseId='10000000-0000-4000-8000-000000000001',runId='20000000-0000-4000-8000-000000000001';
function state(allowed=true){return {ultimateGraph:{case_id:caseId,attention_node_id:'logistics_assignment',nodes:[{id:'logistics_assignment',label:'Transport Plan',node_state:'READY',runtime_available:false,actions:{configure:{allowed,target:{view:'logistics-config',case_id:caseId,node_id:'logistics_assignment',run_id:null}},result:{allowed:true,target:{view:'decision-dashboard',case_id:caseId,node_id:'logistics_assignment',run_id:runId}}}}]}};}
test('Ultimate navigation respects server permission independently of READY and runtime',()=>{
 const route={caseId,nodeId:'logistics_assignment'};
 assert.equal(caseFlowSteps('logistics-map',route,state())[2].disabled,false);
 assert.equal(caseFlowSteps('logistics-map',route,state(false))[2].disabled,true);
 assert.equal(caseFlowSteps('logistics-case-data',route,state())[1].disabled,false);
});
test('Historical dashboard step keeps explicit Run instead of server current result',()=>{
 const historic='30000000-0000-4000-8000-000000000001';
 const steps=caseFlowSteps('decision-dashboard',{caseId,nodeId:'logistics_assignment',runId:historic},state());
 assert.equal(steps[3].target.runId,historic);assert.equal(steps[3].target.caseId,caseId);
});
test('Serialized primary action labels and routes retain contextual Case/node/Run',()=>{
 const action=JSON.parse(JSON.stringify({allowed:true,target:{view:'logistics-case-data',case_id:caseId,node_id:null,run_id:null}}));
 assert.equal(graphActionLabel(action,{label:'Transport Plan'}),'Completar datos del Case');
 assert.deepEqual(graphTarget(action.target),{view:'logistics-case-data',caseId,nodeId:null,runId:null});
});
