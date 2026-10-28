import test from 'node:test';
import assert from 'node:assert/strict';
import {readResource,resourceUrl} from '../app/static/js/dispatch/navigation/resource.mjs';
import {horizonEnd,percentToRatio,draftSignature} from '../app/static/js/dispatch/models/setup-values.mjs';
const id='10000000-0000-4000-8000-000000000001';
test('Ultimate setup deep links retain Case/Model identities without a Run or fake pair',()=>{
 const url=resourceUrl('https://example.test/app?run_id='+id,{view:'logistics-case-setup',caseId:id,modelId:id});
 assert.equal(readResource(url).caseId,id);assert.equal(readResource(url).modelId,id);assert.equal(readResource(url).runId,null);
 const models=resourceUrl(url,{view:'logistics-models',modelId:'new'});assert.equal(readResource(models).modelId,'new');assert.equal(readResource(models).caseId,null);
 assert.throws(()=>readResource('https://example.test/app/ddas/logistics/case?model_id=new'));
});
test('Horizon presets produce concrete UTC dates across month and leap boundaries',()=>{
 assert.equal(horizonEnd('2026-11-02','DAILY'),'2026-11-02');assert.equal(horizonEnd('2026-11-28','WEEKLY'),'2026-12-04');
 assert.equal(horizonEnd('2028-02-01','MONTHLY'),'2028-02-29');assert.equal(horizonEnd('2026-02-01','MONTHLY'),'2026-02-28');assert.equal(horizonEnd('2026-11-02','CUSTOM'),null);
});
test('Preference input uses exact bounded decimal strings rather than binary wire floats',()=>{
 assert.equal(percentToRatio('0'),'0');assert.equal(percentToRatio('100'),'1');assert.equal(percentToRatio('10.01'),'0.1001');
 for(const value of ['NaN','101','-1','0.001',''])assert.throws(()=>percentToRatio(value));
});
test('Dirty comparison ignores JSON object key order while preserving meaningful array edits',()=>{
 assert.equal(draftSignature({name:'Caso',configuration:{a:1,b:[1,2]}}),draftSignature({configuration:{b:[1,2],a:1},name:'Caso'}));
 assert.notEqual(draftSignature({sources:['OWN','EXTERNAL']}),draftSignature({sources:['EXTERNAL','OWN']}));
});
