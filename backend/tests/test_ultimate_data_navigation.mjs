import test from 'node:test';
import assert from 'node:assert/strict';
import {readResource,resourceUrl} from '../app/static/js/dispatch/navigation/resource.mjs';
import {getDatasetTypePresentation} from '../app/static/js/platform/data-presentation.mjs';
const id='10000000-0000-4000-8000-000000000001';
test('Case Data deep link preserves its Case without a legacy pair or Run',()=>{
 const url=resourceUrl('https://example.test/app?run_id='+id+'&model_id='+id,{view:'logistics-case-data',caseId:id,nodeId:null,runId:null});
 assert.equal(url.pathname,'/app/ddas/logistics/case/data');assert.equal(readResource(url).caseId,id);assert.equal(readResource(url).runId,null);assert.equal(url.searchParams.has('model_id'),false);
 assert.equal(readResource(resourceUrl(url,{view:'logistics-case-setup',caseId:id})).caseId,id);
});
test('Data Hub labels Ultimate semantic inputs without changing legacy presentation',()=>{
 assert.equal(getDatasetTypePresentation({dataset_type:'transport_demand'}),'Demanda de transporte');
 assert.equal(getDatasetTypePresentation({dataset_type:'transport_resources'}),'Recursos de transporte');
 assert.equal(getDatasetTypePresentation({dataset_type:'unknown'}),'unknown');
});
