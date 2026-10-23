import test from 'node:test';
import assert from 'node:assert/strict';
import {executionStageIndex,executionStageLabel} from '../app/static/js/dispatch/runs/execution-progress.mjs';

test('only observed engine stages imply ordered progress; admission, recovery and unknown stages do not',()=>{
  for(const stage of ['registering','recovering','queued','running','unrecognized',undefined])assert.equal(executionStageIndex(stage),null);
  assert.equal(executionStageIndex('validating'),0);
  for(const stage of ['constructing','optimizing:service','optimizing:earliest','optimizing:cost'])assert.equal(executionStageIndex(stage),1);
  assert.equal(executionStageIndex('summarizing'),2);assert.equal(executionStageIndex('completed'),3);
  assert.equal(executionStageLabel('optimizing:service'),'EJECUTANDO MOTOR');
  assert.equal(executionStageLabel('unrecognized'),'UNRECOGNIZED');
});
