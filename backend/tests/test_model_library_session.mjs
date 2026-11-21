import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../app/static/js/platform/session.js',import.meta.url),'utf8');
const workspace='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',user='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',prefix='dation.models.working.v1.'+workspace+'.'+user+'.';
function storage(seed={}){const s={...seed};Object.defineProperties(s,{getItem:{value:k=>s[k]??null},setItem:{value:(k,v)=>{s[k]=v;}},removeItem:{value:k=>{delete s[k];}}});return s;}
async function client(previous=null){
 const localStorage=storage({[prefix+'one']:'private model','dation.models.working.v1.other.subject.two':'foreign model','dation.old':'old'}),sessionStorage=storage(previous?{_dation_identity:previous}:{}),events={};
 const window={fetch:async()=>({ok:true,json:async()=>({profile:{id:user},membership:{workspace_id:workspace}})}),dispatchEvent(){},addEventListener(name,fn){events[name]=fn;}},document={addEventListener(){},documentElement:{classList:{add(){},remove(){}}}};
 vm.runInNewContext(source,{window,document,localStorage,sessionStorage,CustomEvent:class{},location:{replace(){}},URL,Date,Headers,Request});await window.dationSession.ready;return {localStorage,sessionStorage,window};
}
test('fresh authenticated tab preserves only its subject-scoped model copies',async()=>{
 const c=await client();assert.equal(c.localStorage[prefix+'one'],'private model');assert.equal(c.localStorage['dation.models.working.v1.other.subject.two'],undefined);assert.equal(c.localStorage['dation.old'],undefined);
});
test('identity change and logout erase model copies rather than leaking across sessions',async()=>{
 const changed=await client('different:identity');assert.equal(changed.localStorage[prefix+'one'],undefined);
 const same=await client();await same.window.dationSession.logout();assert.equal(same.localStorage[prefix+'one'],undefined);
});
