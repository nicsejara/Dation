import test from 'node:test';
import assert from 'node:assert/strict';
import {modelController} from '../app/static/js/dispatch/models/model-library-controller.mjs';
import {newModelDraft} from '../app/static/js/dispatch/models/model-library-state.mjs';
test('incomplete explicit save is honestly local and makes no API call',async()=>{
 let saved;const c=modelController({record:{draft:newModelDraft('ARS')},saveRecord:r=>(saved=structuredClone(r)),request:()=>assert.fail('unexpected API write')});
 assert.equal((await c.save()).where,'browser');assert.equal(saved.savedWhere,'browser');assert.equal(saved.savedDraft.id,c.record.draft.id);
});
test('lost create/publish responses retain exact intents, never write a Case and never duplicate versions',async()=>{
 const draft=newModelDraft('ARS'),requests=[];let created=false,published=false,version;
 const c=modelController({record:{draft},saveRecord:r=>structuredClone(r),request:async(path,method,body)=>{
  requests.push({path,method,body:structuredClone(body)});assert.ok(!/cases|packs|runs/.test(path));
  if(path.endsWith('/versions')){if(!published){published=true;version={id:body.version_id,model_id:draft.id,config_hash:'a'.repeat(64),version:1};throw new Error('response lost');}return {version};}
  if(method==='POST'&&!created){created=true;throw new Error('response lost');}return {model:{id:draft.id,revision:method==='POST'?1:2}};
 }});
 await assert.rejects(c.save({valid:true}),/response lost/);assert.ok(c.pending);assert.throws(()=>c.updateDraft({...draft,name:'unsafe'}),/pendiente/);
 await c.save({valid:true});assert.deepEqual(requests[0],requests[1]);
 await assert.rejects(c.publish(),/response lost/);const first=c.record.publishIntent;assert.ok(first);
 await c.publish();assert.deepEqual(requests.at(-2),requests.at(-1));assert.equal(c.record.publishedVersionId,first.version_id);assert.ok(!c.pending);
});
test('revision conflict retains local content and original revision until explicit reload',async()=>{
 const draft={...newModelDraft('ARS'),expected_revision:3};let body;
 const c=modelController({record:{draft,modelId:draft.id},saveRecord:r=>structuredClone(r),request:async(p,m,b)=>{body=structuredClone(b);throw Object.assign(new Error('CAS'),{status:409});}});
 await assert.rejects(c.save({valid:true}));assert.equal(body.expected_revision,3);assert.equal(c.record.draft.expected_revision,3);assert.ok(c.record.saveIntent);assert.deepEqual(c.record.draft,draft);
});
test('creation replay after another edit cannot silently adopt the newer server draft',async()=>{
 const draft=newModelDraft('ARS');
 const c=modelController({record:{draft},saveRecord:r=>structuredClone(r),request:async()=>({model:{id:draft.id,revision:4}})});
 await assert.rejects(c.save({valid:true}),error=>error.status===409);assert.ok(c.record.createIntent);assert.equal(c.record.modelId,undefined);assert.equal(c.record.draft.expected_revision,1);
});
