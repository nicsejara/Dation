import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
globalThis.crypto??=webcrypto;
import {newCaseDraft,caseDefinition,blockErrors,creationBody,invalidateBlock,caseRoute,fromDefinition} from '../app/static/js/dispatch/cases/case-v2-state.mjs';
import {readResource,resourceUrl} from '../app/static/js/dispatch/navigation/resource.mjs';
import {workingCopies,rememberReturn,resolveReturn} from '../app/static/js/dispatch/models/model-library-state.mjs';
test('independent Cases never select a model and require six real validations',()=>{
 const a=newCaseDraft(),b=newCaseDraft();assert.notEqual(a.id,b.id);assert.notEqual(a.workId,b.workId);assert.equal(a.binding,null);
 assert.ok(blockErrors(a,1));assert.ok(blockErrors(a,2));assert.throws(()=>creationBody(a,true));
 a.name='QA';a.critical='100';a.success='98';assert.equal(caseDefinition(a).acceptance_policy.threshold,'0.98');
 a.primary_goal='CUSTOM';a.weights.COST='15';assert.ok(blockErrors(a,4));a.weights.COST='25';assert.equal(blockErrors(a,4),null);
 a.confirmed={1:true,2:true,3:true,4:true,5:true,6:true};invalidateBlock(a,2);assert.equal(a.confirmed[1],true);assert.equal(a.confirmed[2],undefined);assert.equal(a.confirmed[5],undefined);
 const server=caseDefinition({...a,primary_goal:'MINIMIZE_COST'});server.identity.description=null;
 const editing=fromDefinition(server,a.id);assert.equal(editing.description,'');assert.equal(blockErrors(editing,1),null);assert.equal(caseDefinition(editing).identity.description,null);
});
test('Case working copies are tenant scoped and J1.01 returns preserve the typed draft',()=>{
 const data=new Map(),storage={get length(){return data.size;},key:i=>[...data.keys()][i],getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k)};
 const identity={workspace:crypto.randomUUID(),user:crypto.randomUUID(),storage},draft=newCaseDraft(),copies=workingCopies({...identity,kind:'case'});
 copies.write({workId:draft.workId,draft},0);assert.equal(copies.read(draft.workId).draft.id,draft.id);
 assert.equal(workingCopies({...identity,user:crypto.randomUUID(),kind:'case'}).read(draft.workId),null);assert.equal(workingCopies(identity).read(draft.workId),null);
 const route=caseRoute({caseView:'definition',caseMode:'review',caseWorkId:draft.workId}),token=rememberReturn(route,identity);
 assert.equal(resolveReturn(token,identity).caseWorkId,draft.workId);assert.equal(resolveReturn(token,{...identity,user:crypto.randomUUID()}),null);
 storage.removeItem([...data.keys()].find(k=>k.includes('.return.')));assert.equal(resolveReturn(token,identity),null);
});
test('versioned routes survive normalization without changing legacy step semantics',()=>{
 const d=newCaseDraft(),r=caseRoute({caseView:'definition',caseMode:'configure',caseWorkId:d.workId});
 const back=readResource(resourceUrl('https://local.invalid/app',r));assert.equal(back.caseWorkId,d.workId);assert.equal(back.journeyVersion,'v2');assert.equal(back.caseMode,'configure');
 assert.equal(readResource('/app/ddas/logistics/case?core_step=2').coreStep,2);
 assert.throws(()=>readResource('/app/ddas/logistics/case?journey_version=v2&core_step=2'));
 assert.throws(()=>readResource('/app/ddas/logistics/case?journey_version=v2&case_view=definition&case_work_id=bad'));
 assert.equal(caseRoute({caseId:d.id,caseMode:null,caseView:null,coreStep:3}).caseMode,'review');
 assert.equal(caseRoute({caseId:d.id,caseMode:null,caseView:null,coreStep:3}).caseView,'definition');
 for(const caseView of ['inputs','model']){
  const pinned=caseRoute({caseId:d.id,caseView});assert.equal(readResource(resourceUrl('https://local.invalid/app',pinned)).caseView,caseView);
  assert.throws(()=>readResource('/app/ddas/logistics/case?journey_version=v2&case_view='+caseView));
 }
});
