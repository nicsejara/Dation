import test from 'node:test';
import assert from 'node:assert/strict';
import {newModelDraft,workingCopies,rememberReturn,resolveReturn,modelRoute} from '../app/static/js/dispatch/models/model-library-state.mjs';
import {readResource,resourceUrl} from '../app/static/js/dispatch/navigation/resource.mjs';
const a='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',b='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
function memory(){const data=new Map();return {get length(){return data.size;},key:i=>[...data.keys()][i],getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k)};}
test('new models use independent R6 defaults and never inherit a Case candidate',()=>{
 const first=newModelDraft('ARS'),second=newModelDraft('ARS');first.configuration.cargo.products.push({name:'A'});
 assert.notEqual(first.id,second.id);assert.equal(second.name,'');assert.deepEqual(second.configuration.cargo.products,[]);
 assert.equal(second.configuration.version,2);assert.equal(second.configuration.cargo.input_mode,'catalog');assert.ok(!('case_id' in second));
});
test('durable copies isolate users, workspaces, working IDs and revisions',()=>{
 const storage=memory(),s=workingCopies({workspace:a,user:a,storage}),other=workingCopies({workspace:b,user:a,storage});
 const x=s.write({workId:a,draft:newModelDraft('ARS')},0),y=s.write({workId:b,draft:newModelDraft('ARS')},0);
 assert.equal(s.list().length,2);assert.equal(other.list().length,0);assert.notEqual(x.draft.id,y.draft.id);
 assert.throws(()=>s.write({...x,draft:y.draft},0),/otra pestaña/);assert.equal(s.read(a).draft.id,x.draft.id);
 assert.throws(()=>workingCopies({workspace:'',user:a,storage}),/identidad/);
});
test('exact review/version routes roundtrip and reject malformed or mixed identities',()=>{
 const route=modelRoute({modelId:a,modelVersionId:b,modelView:'review',modelReturnId:a});
 const url=resourceUrl('https://qa/app?case_id='+b,route),r=readResource(url);
 assert.equal(r.modelVersionId,b);assert.equal(r.modelView,'review');assert.equal(r.modelReturnId,a);assert.equal(r.caseId,null);
 for(const tail of ['model_view=delete','model_version_id=latest','model_return_id=https://evil','model_view=review&model_version_id='+b])assert.throws(()=>readResource('https://qa/app/ddas/logistics/models?'+tail));
});
test('typed return preserves Case draft and run; publishing a different model cannot overwrite it',()=>{
 const storage=memory(),identity={workspace:a,user:a,storage},target={view:'logistics-case-setup',caseId:a,coreStep:1,parentCaseId:b,returnView:'decision-dashboard',returnNode:'logistics_assignment',returnRun:b};
 const token=rememberReturn(target,identity);assert.deepEqual(resolveReturn(token,identity),readResource(resourceUrl('https://qa/app',target)));
 workingCopies(identity).write({workId:a,draft:newModelDraft('ARS')},0);assert.equal(resolveReturn(token,identity).caseId,a);
 assert.equal(resolveReturn(token,{...identity,user:b}),null);assert.throws(()=>rememberReturn({view:'https://evil'},identity));
});
