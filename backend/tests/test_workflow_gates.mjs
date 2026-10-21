import test from 'node:test';
import assert from 'node:assert/strict';
import {responsibilityProblem} from '../app/static/js/dispatch/workflow-responsibility.mjs';

test('legacy cases retain navigation and execution without invented assignments',()=>{
 for(const kind of ['data','execute','approve'])assert.equal(responsibilityProblem({gates_enforced:false,stages:{}},'logistics_assignment',kind),null);
});
test('a retained person whose eligibility was revoked does not satisfy a new-case gate',()=>{
 const data={owner:{id:'person'},owner_eligible:false};
 const snapshot={gates_enforced:true,stages:{data_preparation:data,logistics_assignment:{owner_eligible:true,approver_eligible:true}}};
 assert.match(responsibilityProblem(snapshot,'logistics_assignment'),/responsable de datos/);
 data.owner_eligible=true;assert.equal(responsibilityProblem(snapshot,'logistics_assignment'),null);
 snapshot.stages.logistics_assignment.owner_eligible=false;
 assert.match(responsibilityProblem(snapshot,'logistics_assignment'),/responsable de la decisión/);
 assert.equal(responsibilityProblem(snapshot,'logistics_assignment','approve'),null);
});
test('each decision has independent owner and approval gates; Data is a workflow stage',()=>{
 const snapshot={gates_enforced:true,stages:{data_preparation:{owner_eligible:true},logistics_assignment:{owner_eligible:true,approver_eligible:true}}};
 assert.equal(responsibilityProblem(snapshot,'data_preparation','data'),null);
 assert.match(responsibilityProblem(snapshot,'logistics_scheduling'),/responsable de la decisión/);
 assert.match(responsibilityProblem(snapshot,'logistics_scheduling','approve'),/aprobador asignado/);
});
