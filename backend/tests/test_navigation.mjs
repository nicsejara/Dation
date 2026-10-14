import assert from 'node:assert/strict';
import test from 'node:test';
import {readResource,resourceUrl,runDecisionState,runContext} from '../app/static/js/dispatch/navigation.mjs';
const id='00000000-0000-4000-8000-000000000004';
test('legacy scheduling links preserve decision identity',()=>{assert.equal(readResource('http://qa/app?dda=scheduling_v1&run_id='+id).nodeId,'logistics_scheduling');});
test('map transitions remove run and legacy schema parameters',()=>{const url=resourceUrl('http://qa/app?dda=scheduling_v1&run_id='+id,{view:'logistics-map',caseId:id});assert.equal(url.searchParams.get('run_id'),null);assert.equal(url.searchParams.get('dda'),null);});
test('invalid identifiers and screens fail explicitly',()=>{assert.throws(()=>readResource('http://qa/app?view=unknown'));assert.throws(()=>readResource('http://qa/app?run_id=bad'));});
test('viewing an alternative does not replace the approved run',()=>{const decisionCase={nodes:{logistics_assignment:{status:'approved',approved_run_id:id}}};assert.equal(runDecisionState({id:'other'},decisionCase,'logistics_assignment'),'review');assert.equal(runDecisionState({id},decisionCase,'logistics_assignment'),'approved');});
test('superseded and stale evidence remains historical',()=>{assert.equal(runDecisionState({id,superseded_at:'2026-10-10'},null,'logistics_assignment'),'superseded');assert.equal(runDecisionState({id},{nodes:{logistics_assignment:{status:'stale',approved_run_id:id}}},'logistics_assignment'),'stale');});
test('failed run exposes persisted configuration and lineage without a result',()=>{
  const configuration={strategy:'service_first',planning_window_start:'2026-10-01',planning_window_end:'2026-10-02',temporal_rules:[{action:'prioritize'}]};
  const run={status:'error',decision_case_id:id,node_id:'logistics_scheduling',orders_dataset_id:'orders',fleet_dataset_id:'fleet',configuration_json:configuration};
  assert.deepEqual(runContext(run),{caseId:id,nodeId:'logistics_scheduling',configuration,ordersId:'orders',fleetId:'fleet'});
  assert.equal(run.configuration_json,configuration);
});
test('historical run uses result case lineage rather than another selected case',()=>{
  const run={decision_case_id:'old',configuration_json:{decision_case:{case_id:'stored'}},result_json:{schema_version:'assignment_v1',decision_case:{case_id:id},configuration:{objective:'min_cost'},inputs:{orders:{dataset_id:'o'},fleet:{dataset_id:'f'}}}};
  assert.deepEqual(runContext(run),{caseId:id,nodeId:'logistics_assignment',configuration:{objective:'min_cost'},ordersId:'o',fleetId:'f'});
});
test('older failed scheduling metadata and schema still identify the correct case',()=>{
  const config={decision_case:{case_id:id},strategy:'earliest_dispatch'};
  assert.equal(runContext({schema_version:'scheduling_v1',configuration_json:config}).caseId,id);
  assert.equal(runContext({schema_version:'scheduling_v1',configuration_json:config}).nodeId,'logistics_scheduling');
  assert.equal(runContext({}).caseId,null);
});
