import test from 'node:test';
import assert from 'node:assert/strict';
import {describeFailure,responseFailure} from '../app/static/js/dispatch/recovery.mjs';

test('session expiration and invalid login offer different recovery',()=>{
 assert.equal(describeFailure({status:401}).kind,'session');
 assert.equal(describeFailure({status:401},{auth:true}).kind,'auth');
 assert.match(describeFailure({status:401}).message,/trabajo guardado/);
});
test('offline and timeout do not assert that an operation failed',()=>{
 assert.equal(describeFailure(new TypeError('fetch failed')).kind,'disconnected');
 const timeout=describeFailure({status:504});assert.equal(timeout.kind,'timeout');assert.match(timeout.message,/no confirma/);
});
test('permissions and validation require deliberate correction',()=>{
 assert.equal(describeFailure({status:403}).kind,'permission');
 assert.equal(describeFailure({status:422}).kind,'validation');
 const err=responseFailure({status:422},{detail:[{input:'sensitive-password',msg:'invalid'}]});
 assert.equal(err.status,422);assert.ok(!err.message.includes('sensitive-password'));
});
test('source and stale decisions preserve evidence and direct to the upstream approval',()=>{
 assert.match(describeFailure(null,{kind:'source'}).message,/Assignment/);
 assert.match(describeFailure(null,{kind:'stale'}).message,/evidencia anterior/);
 assert.match(describeFailure(null,{kind:'run'}).message,/configurar/);
});
