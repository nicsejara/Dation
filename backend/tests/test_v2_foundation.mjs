import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {resolveNodeDestination} from '../app/static/js/dispatch/decision-target.mjs';
import {FOUNDATION,objectivePresentation,statePresentation,caseContext} from '../app/static/js/platform/foundation.mjs';
for(const v of JSON.parse(fs.readFileSync(new URL('./foundation_vectors.json',import.meta.url)))){
 test(v.name,()=>assert.deepEqual(resolveNodeDestination(v.node_id,v.node),v.expected));
}
test('registry preserves IDs, aliases, immutable metadata and future availability',()=>{
 assert.equal(objectivePresentation('cost_min').id,'min_cost');assert.equal(objectivePresentation('min_cost').label,'Costo mínimo');
 assert.equal(objectivePresentation(null),null);assert.deepEqual(objectivePresentation('future'),{id:'future',label:'future'});
 assert.equal(FOUNDATION.ddas.filter(d=>d.status==='available').length,1);
 assert.throws(()=>{FOUNDATION.decisions.logistics_assignment.label='changed';},TypeError);
});
test('selection never changes the approval or review semantic',()=>{
 assert.deepEqual(statePresentation('approved',true),{status:'approved',tone:'success',selected:true,selectionTone:'accent'});
 assert.equal(statePresentation('review',true).tone,'warning');assert.equal(statePresentation('error').tone,'danger');
});
test('case context uses the canonical server DTO and preserves identity',()=>{
 const context={caseId:'c',friendlyId:'DC-C',status:'active'};assert.equal(caseContext({context}),context);
 assert.equal(caseContext({id:'abcdef12-0000',label:'Mi caso',current_step:'logistics_assignment'}).friendlyId,'DC-ABCDEF12');
});
