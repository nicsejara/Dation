import test from 'node:test';
import assert from 'node:assert/strict';
import {hasDemoData} from '../app/static/js/dispatch/cases/data-provenance.mjs';

const state=()=>({decisionCase:{id:'case-a',persisted:true,inputs:{orders_dataset_id:'orders-a',fleet_dataset_id:'fleet-a'}},caseContext:{caseId:'case-a'},orders:{id:'orders-a',is_sample:false},fleet:{id:'fleet-a',is_sample:false}});
test('uploaded, reused and historical real Data Packs never infer demo from labels or categories',()=>{
  const s=state();s.orders.original_filename='demo.csv';s.decisionCase.category='simulation';
  for(const view of ['logistics-data','logistics-map','logistics-config','decision-dashboard'])assert.equal(hasDemoData(s,{caseId:'case-a'},view),false);
  s.run={id:'historical',decision_case_id:'case-a',orders_dataset_id:'orders-a',fleet_dataset_id:'fleet-a'};
  assert.equal(hasDemoData(s,{caseId:'case-a',runId:'historical'},'decision-dashboard'),false);
});
test('actual sample provenance is shown, including a mixed Data Pack, with strict booleans',()=>{
  const s=state();s.orders.is_sample=true;
  assert.equal(hasDemoData(s,{caseId:'case-a'},'logistics-data'),true);
  s.orders.is_sample=false;s.fleet.is_sample=true;
  assert.equal(hasDemoData(s,{caseId:'case-a'},'logistics-config'),true);
  s.fleet.is_sample='false';assert.equal(hasDemoData(s,{caseId:'case-a'},'logistics-data'),false);
});
test('cached or mismatched Case/Run provenance is not displayed during resource hydration',()=>{
  const s=state();s.orders.is_sample=true;
  assert.equal(hasDemoData(s,{caseId:'case-b'},'logistics-data'),false);
  s.caseContext=null;assert.equal(hasDemoData(s,{caseId:'case-a'},'logistics-data'),false);
  s.caseContext={caseId:'case-a'};s.run={id:'run-a',decision_case_id:'case-a',orders_dataset_id:'orders-b'};
  assert.equal(hasDemoData(s,{caseId:'case-a',runId:'run-a'},'decision-dashboard'),false);
  assert.equal(hasDemoData(s,{caseId:'case-a',runId:'run-b'},'decision-dashboard'),false);
  assert.equal(hasDemoData(s,{},'platform-home'),false);
});
