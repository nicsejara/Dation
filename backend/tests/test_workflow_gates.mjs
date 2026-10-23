import test from 'node:test';
import assert from 'node:assert/strict';
import {responsibilityProblem} from '../app/static/js/dispatch/cases/workflow-responsibility.mjs';

test('legacy cases retain navigation and execution without invented assignments',()=>{
 for(const kind of ['data','execute','approve'])assert.equal(responsibilityProblem({gates_enforced:false,stages:{}},'logistics_assignment',kind),null);
});
test('a retained person whose eligibility was revoked does not satisfy a new-case gate',()=>{
 const data={owner:{id:'person'},owner_eligible:false};
 const snapshot={gates_enforced:true,stages:{data_owner:data,logistics_assignment:{owner_eligible:true}}};
 assert.match(responsibilityProblem(snapshot,'logistics_assignment'),/Data Owner/);
 data.owner_eligible=true;assert.equal(responsibilityProblem(snapshot,'logistics_assignment'),null);
 snapshot.stages.logistics_assignment.owner_eligible=false;
 assert.match(responsibilityProblem(snapshot,'logistics_assignment'),/Decision Owner/);
 assert.match(responsibilityProblem(snapshot,'logistics_assignment','approve'),/Decision Owner/);
});
test('each decision requires its own canonical owner for execution and approval',()=>{
 const snapshot={gates_enforced:true,stages:{data_owner:{owner_eligible:true},logistics_assignment:{owner_eligible:true}}};
 assert.equal(responsibilityProblem(snapshot,'data_preparation','data'),null);
 assert.match(responsibilityProblem(snapshot,'logistics_scheduling'),/Decision Owner/);
 assert.match(responsibilityProblem(snapshot,'logistics_scheduling','approve'),/Decision Owner/);
 snapshot.stages.data_owner.owner_eligible=false;
 assert.match(responsibilityProblem(snapshot,'logistics_assignment'),/Data Owner/);
 assert.equal(responsibilityProblem(snapshot,'logistics_assignment','approve'),null);
 snapshot.stages.logistics_assignment.can_approve=false;
 assert.match(responsibilityProblem(snapshot,'logistics_assignment','approve'),/Decision Owner o a un Admin/);
});
