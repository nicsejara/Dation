import test from 'node:test';
import assert from 'node:assert/strict';
globalThis.window={};
const {caseFlowSteps}=await import('../app/static/js/dispatch/navigation/case-flow.mjs');
import {hasCaseExecutions} from '../app/static/js/dispatch/cases/case-identity.mjs';
import {resolveDecisionDestination} from '../app/static/js/dispatch/navigation/decision-target.mjs';
import {configurationAvailable} from '../app/static/js/dispatch/navigation/decision-target.mjs';
import {caseAttributesReady} from '../app/static/js/dispatch/cases/case-identity.mjs';
const {decisionRail}=await import('../app/static/js/dispatch/navigation/decision-nav.mjs');

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
test('horizontal navigation keeps its level and vertical navigation keeps D2',()=>{
 const nodes={...state.decisionCase.nodes,logistics_scheduling:{status:'review',latest_run_id:'d2-result'}};
 for(const id of Object.keys(nodes)){
  assert.deepEqual(resolveDecisionDestination(id,nodes[id],'logistics-config'),{view:'logistics-config',node_id:id,run_id:null});
  assert.equal(resolveDecisionDestination(id,nodes[id],'decision-dashboard').run_id,id==='logistics_assignment'?'approved-d1':'d2-result');
 }
 for(const view of ['logistics-config','decision-dashboard']){
  const steps=caseFlowSteps(view,{caseId:cid,nodeId:'logistics_scheduling'},{...state,decisionCase:{...state.decisionCase,nodes}});
  assert.equal(steps[2].target.nodeId,'logistics_scheduling');assert.equal(steps[3].target.nodeId,'logistics_scheduling');
  assert.equal(steps[3].target.runId,'d2-result');assert.equal(steps[3].disabled,false);
 }
});
test('available decisions can open Config, never an absent Dashboard; locked decisions stay disabled',()=>{
 assert.equal(resolveDecisionDestination('logistics_scheduling',{status:'available'},'decision-dashboard'),null);
 assert.equal(resolveDecisionDestination('logistics_scheduling',{status:'available'},'logistics-config').view,'logistics-config');
 for(const view of ['logistics-config','decision-dashboard']){
  assert.equal(resolveDecisionDestination('logistics_scheduling',{status:'locked'},view),null);
  assert.equal(resolveDecisionDestination('logistics_final_assignment',{status:'available'},view),null);
 }
 const html=decisionRail({decisionCase:state.decisionCase,activeNode:'logistics_assignment',view:'decision-dashboard'});
 assert.match(html,/data-decision-node="logistics_scheduling"[^>]*disabled/);
 assert.doesNotMatch(html,/data-back-map|dispatch-decision-rail__head|decision-view-tabs/);
});
test('configuration requires its canonical owners and an approved upstream; historical Dashboards remain readable',()=>{
 const current={...state.decisionCase,nodes:{...state.decisionCase.nodes,logistics_scheduling:{status:'stale',latest_run_id:'old-d2'}}};
 const workflow={gates_enforced:true,attributes_applied:true,stages:{data_owner:{owner_eligible:true},logistics_assignment:{owner_eligible:true},logistics_scheduling:{owner_eligible:false}}};
 assert.equal(configurationAvailable('logistics_scheduling',current,workflow),false);
 assert.equal(resolveDecisionDestination('logistics_scheduling',current.nodes.logistics_scheduling,'logistics-config',{decisionCase:current,workflow}),null);
 assert.equal(resolveDecisionDestination('logistics_scheduling',current.nodes.logistics_scheduling,'decision-dashboard',{decisionCase:current,workflow}).run_id,'old-d2');
 workflow.stages.logistics_scheduling.owner_eligible=true;
 assert.equal(configurationAvailable('logistics_scheduling',current,workflow),true);
 current.nodes.logistics_assignment={status:'review',latest_run_id:'new-d1'};
 assert.equal(configurationAvailable('logistics_scheduling',current,workflow),false);
});
test('attributes are ready only after Apply; editing a previously applied draft blocks readiness again',()=>{
 const value={caseIdentity:{label:'SEMANA 43',category:'weekly'},attributesApplied:false};
 assert.equal(caseAttributesReady(value),false);
 value.attributesApplied=true;assert.equal(caseAttributesReady(value),true);
 value.identityDirty=true;assert.equal(caseAttributesReady(value),false);
});
