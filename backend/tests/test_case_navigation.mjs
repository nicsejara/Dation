import test from 'node:test';
import assert from 'node:assert/strict';
globalThis.window={};
const {caseFlowSteps}=await import('../app/static/js/dispatch/case-navigation.mjs');
import {hasCaseExecutions} from '../app/static/js/dispatch/case-identity.mjs';

const cid='00000000-0000-4000-8000-000000000001';
const state={decisionCase:{id:cid,persisted:true,nodes:{
 logistics_assignment:{status:'approved',approved_run_id:'approved-d1',latest_run_id:'candidate-d1'},
 logistics_scheduling:{status:'available'},
}}};
test('D2 configuration reuses step 3 after D1 result, preserving the Case for every link',()=>{
 const steps=caseFlowSteps('logistics-config',{caseId:cid,nodeId:'logistics_scheduling'},state);
 assert.equal(steps.findIndex(s=>s.current),2);
 assert.equal(steps[3].disabled,true);
 assert.equal(steps[0].disabled,false);assert.equal(steps[1].disabled,false);
 assert.ok(steps.every(s=>s.target.caseId===cid));
 assert.equal(steps[2].context,'Planificación de despachos');
});
test('returning to Map reflects current position rather than furthest completed step',()=>{
 const steps=caseFlowSteps('logistics-map',{caseId:cid,nodeId:null},state);
 assert.equal(steps.findIndex(s=>s.current),1);
 assert.equal(steps[2].disabled,true);assert.equal(steps[3].disabled,true);
 const result=caseFlowSteps('decision-dashboard',{caseId:cid,nodeId:'logistics_assignment'},state);
 assert.equal(result[3].target.runId,'approved-d1');
});
test('new Cases cannot skip preparation and queued or failed executions protect inputs',()=>{
 assert.equal(caseFlowSteps('logistics-data',{caseId:null},{}).filter(s=>!s.disabled).length,1);
 assert.equal(hasCaseExecutions({nodes:{a:{status:'available',run_count:0}}}),false);
 assert.equal(hasCaseExecutions({nodes:{a:{status:'running',latest_run_id:'queued'}}}),true);
 assert.equal(hasCaseExecutions({nodes:{a:{status:'error',run_count:1}}}),true);
});
