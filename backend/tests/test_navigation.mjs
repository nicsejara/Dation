import assert from 'node:assert/strict';
import test from 'node:test';
import {readResource,resourceUrl,runDecisionState} from '../app/static/js/dispatch/navigation.mjs';
const id='00000000-0000-4000-8000-000000000004';
test('legacy scheduling links preserve decision identity',()=>{assert.equal(readResource('http://qa/app?dda=scheduling_v1&run_id='+id).nodeId,'logistics_scheduling');});
test('map transitions remove run and legacy schema parameters',()=>{const url=resourceUrl('http://qa/app?dda=scheduling_v1&run_id='+id,{view:'logistics-map',caseId:id});assert.equal(url.searchParams.get('run_id'),null);assert.equal(url.searchParams.get('dda'),null);});
test('invalid identifiers and screens fail explicitly',()=>{assert.throws(()=>readResource('http://qa/app?view=unknown'));assert.throws(()=>readResource('http://qa/app?run_id=bad'));});
test('viewing an alternative does not replace the approved run',()=>{const decisionCase={nodes:{logistics_assignment:{status:'approved',approved_run_id:id}}};assert.equal(runDecisionState({id:'other'},decisionCase,'logistics_assignment'),'review');assert.equal(runDecisionState({id},decisionCase,'logistics_assignment'),'approved');});
test('superseded and stale evidence remains historical',()=>{assert.equal(runDecisionState({id,superseded_at:'2026-10-10'},null,'logistics_assignment'),'superseded');assert.equal(runDecisionState({id},{nodes:{logistics_assignment:{status:'stale',approved_run_id:id}}},'logistics_assignment'),'stale');});
