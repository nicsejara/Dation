import test from 'node:test';
import assert from 'node:assert/strict';
import {readResource,resourceUrl} from '../app/static/js/dispatch/navigation.mjs';
import {readCenterResource} from '../app/static/js/platform/center-resource.mjs';
const id='11111111-2222-4333-8444-555555555555';
test('Decision Center retains list/detail/history state and clears DDA/Data Hub context',()=>{
 const center={filter:'review',q:'Semana ñ',dda:'logistics',owner:'me',offset:25,caseId:id,nodeId:'logistics_scheduling',runsOffset:50};
 const url=resourceUrl('https://dation.test/app/data?case_id='+id+'&dataset_id='+id+'&run_id='+id,{view:'platform-decisions',center});
 assert.equal(url.pathname,'/app/decisions');assert.equal(url.searchParams.has('case_id'),false);assert.equal(url.searchParams.has('dataset_id'),false);assert.deepEqual(readResource(url).center,center);
 const run=resourceUrl(url,{view:'decision-dashboard',caseId:id,nodeId:'logistics_scheduling',runId:id});
 assert.equal(run.searchParams.has('center_case_id'),false);assert.equal(readResource(run).runId,id);
});
test('Decision Center rejects malformed targets and pagination before reading data',()=>{
 for(const query of ['center_case_id=oops','center_offset=-1','center_offset=1.5','center_runs_offset=1000001','center_filter=unknown','center_dda=other','center_owner=broken','center_node=logistics_assignment'])assert.throws(()=>readCenterResource('https://dation.test/app/decisions?'+query));
});

test('Portfolio KPI and owner links retain selected drawer and reset only explicitly changed fields',()=>{
 const url=resourceUrl('https://dation.test/app/decisions',{view:'platform-decisions',center:{filter:'pending_approval',dda:'production',owner:id,caseId:id,q:'A'}});
 const state=readCenterResource(url);assert.equal(state.owner,id);assert.equal(state.dda,'production');assert.equal(state.filter,'pending_approval');
 const closed=resourceUrl(url,{view:'platform-decisions',center:{...state,caseId:null,nodeId:null,runsOffset:0}});
 assert.equal(readCenterResource(closed).caseId,null);assert.equal(readCenterResource(closed).owner,id);
 assert.equal(resourceUrl(closed,{view:'platform-home'}).searchParams.has('center_owner'),false);
});
