import assert from 'node:assert/strict';import {delta,rebalance,samePlan,filteredTrips} from '../app/static/js/dispatch/selectors.mjs';
assert.equal(delta(.9,.5,'higher_better').tone,'good');assert.equal(delta(120,100,'lower_better').tone,'bad');assert.equal(delta(10,0,'lower_better').percent,null);assert.equal(delta(10,null,'lower_better').tone,'neutral');
for(let n=0;n<=100;n++){const w=rebalance({cost:20,trips:30,time:50},'cost',n);assert.equal(w.cost+w.trips+w.time,100);assert.ok(w.trips>=0&&w.time>=0);}
assert.equal(samePlan({plan_fingerprint:'x'},{plan_fingerprint:'x'}),true);assert.equal(samePlan({},{}),false);
const r={scenarios:{selected:{trips:[{trip_id:'1',dispatch_date:'2026-01-01',fleet_pool_id:'TP-A',base_location:'A',vehicle_type:'T',ownership:'third_party',origin:'A',destination:'B',cost:5}],order_outcomes:[{late_days:1,trip_ids:['1']}]}}};assert.equal(filteredTrips(r,{late:true,outsourced:true}).length,1);assert.equal(filteredTrips(r,{vehicle:'X'}).length,0);assert.equal(filteredTrips(r,{pool:'TP-A'}).length,1);assert.equal(filteredTrips(r,{pool:'TP-B'}).length,0);
console.log('dispatch selectors: ok');
