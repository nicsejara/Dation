import test from 'node:test';
import assert from 'node:assert/strict';
import {readResource,resourceUrl} from '../app/static/js/dispatch/navigation.mjs';
import {readHubResource} from '../app/static/js/platform/data-resource.mjs';
import {validateCsvFile,storeCsvFile} from '../app/static/js/dispatch/upload/file-api.mjs';
const id='00000000-0000-4000-8000-000000000001',other='00000000-0000-4000-8000-000000000002';

test('Data Hub links retain filters and selected resources without decision context',()=>{
 const hub={tab:'packs',filter:'all',q:'Órdenes + 1',offset:25,ordersId:id,fleetId:other};
 const url=resourceUrl('https://qa/app?case_id='+id+'&run_id='+other,{view:'platform-data',hub,caseId:id,runId:other});
 assert.equal(url.pathname,'/app/data');assert.equal(url.searchParams.get('case_id'),null);
 const parsed=readResource(url);assert.equal(parsed.view,'platform-data');assert.deepEqual(parsed.hub,{...hub,datasetId:null});
 const away=resourceUrl(url,{view:'logistics-map',caseId:id});assert.equal(away.searchParams.get('pack_orders_id'),null);assert.equal(away.searchParams.get('data_q'),null);
});

test('invalid data identifiers, pair links, offsets and filters fail before provider calls',()=>{
 for(const query of ['dataset_id=bad','pack_orders_id='+id,'pack_orders_id='+id+'&pack_fleet_id='+other+'&dataset_id='+id,'data_offset=-1','data_offset=1.5','data_offset=1000001','data_filter=unknown','data_tab=unknown'])assert.throws(()=>readHubResource('https://qa/app/data?'+query),query);
 assert.equal(readHubResource('https://qa/app/data').tab,'datasets');
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
