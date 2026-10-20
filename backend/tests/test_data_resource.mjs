import test from 'node:test';
import assert from 'node:assert/strict';
import {readResource,resourceUrl} from '../app/static/js/dispatch/navigation.mjs';
import {readHubResource} from '../app/static/js/platform/data-resource.mjs';
import {validateCsvFile,storeCsvFile} from '../app/static/js/dispatch/upload/file-api.mjs';
const id='00000000-0000-4000-8000-000000000001',other='00000000-0000-4000-8000-000000000002';

test('Data Hub links retain independent filters, pagination and selected dataset',()=>{
 const hub={q:'Órdenes + 1',type:'orders',validation:'validated',state:'all',offset:25,datasetId:id,casesOffset:25};
 const url=resourceUrl('https://qa/app?case_id='+id+'&run_id='+other,{view:'platform-data',hub});
 assert.equal(url.pathname,'/app/data');assert.equal(url.searchParams.get('case_id'),null);
 assert.deepEqual(readResource(url).hub,hub);
 const away=resourceUrl(url,{view:'platform-decisions',center:{caseId:other}});assert.equal(away.searchParams.get('dataset_id'),null);assert.equal(away.searchParams.get('data_q'),null);
});
test('legacy pack links open dataset library and combined filters migrate',()=>{
 for(const query of ['data_tab=packs','pack_orders_id='+id+'&pack_fleet_id='+other])assert.equal(readHubResource('https://qa/app/data?'+query).datasetId,null);
 assert.equal(readHubResource('https://qa/app/data?data_filter=orders').type,'orders');
 assert.equal(readHubResource('https://qa/app/data?data_filter=archived').state,'archived');
});
test('invalid dataset identifiers, dimensions and bounded offsets fail before provider calls',()=>{
 for(const query of ['dataset_id=bad','data_offset=-1','data_offset=1.5','data_offset=1000001','data_cases_offset=-1','data_type=bad','data_validation=bad','data_state=bad','data_filter=unknown','data_tab=unknown'])assert.throws(()=>readHubResource('https://qa/app/data?'+query),query);
});

test('DDA and Data Hub share multipart validation/upload while retaining their authorization namespaces',async()=>{
 const original=globalThis.fetch,calls=[],file=new File(['a,b\n1,2'],'datos.csv',{type:'text/csv'}),controller=new AbortController();
 globalThis.fetch=async(path,options)=>{calls.push({path,options});return new Response(JSON.stringify({valid:true}),{status:200,headers:{'Content-Type':'application/json'}});};
 try{
  await validateCsvFile('orders',file,{signal:controller.signal});await storeCsvFile('fleet',file,{base:'/api/platform/data',signal:controller.signal});
  assert.deepEqual(calls.map(call=>call.path),['/api/datasets/validate?dataset_type=orders','/api/platform/data/datasets/upload?dataset_type=fleet']);
  for(const call of calls){assert.equal(call.options.method,'POST');assert.equal(call.options.body.get('file').name,'datos.csv');assert.equal(call.options.signal,controller.signal);assert.equal(call.options.headers,undefined);}
 }finally{globalThis.fetch=original;}
});
