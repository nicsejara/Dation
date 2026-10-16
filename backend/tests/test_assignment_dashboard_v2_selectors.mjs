import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {getAssignmentContext,getEssentialKpis,getDecisionInsights,getScenarioTable,getResourceParticipation,
  getAssignmentPreview,getDecisionTradeoffs,getCorridorSummary,getTripUtilization,getDecisionNarrative,
  getAssignmentSummary,getAssignmentVehicles} from '../app/static/js/dispatch/assignment-dashboard-selectors.mjs';
const fixture=JSON.parse(readFileSync(new URL('./fixtures/assignment_dashboard/assignment_comparative_run.json',import.meta.url))).result_json;
const result=()=>structuredClone(fixture);
test('context counts destinations and evaluated resources independently from vehicles used',()=>{
 const r=result(),ctx=getAssignmentContext(r);
 assert.equal(ctx.orders,2);assert.equal(ctx.destinations,1);assert.equal(ctx.evaluatedVehicles,2);assert.equal(r.scenarios.selected.metrics.vehicles_used,1);
 assert.equal(ctx.unitsLabel,'unidades');r.inputs.orders.quantity_unit='pallets';assert.equal(getAssignmentContext(r).unitsLabel,'pallets');
});
test('missing context remains unavailable, while published zeros remain zeros',()=>{
 assert.deepEqual(getAssignmentContext({}),{orders:null,totalWeightKg:null,destinations:null,evaluatedVehicles:null,unitsLabel:'unidades'});
 const r={scenarios:{selected:{metrics:{orders:0,total_weight_kg:0}}},resources:[]};
 assert.equal(getAssignmentContext(r).orders,0);assert.equal(getAssignmentContext(r).evaluatedVehicles,0);
 assert.equal(getAssignmentSummary({}).objective,'unknown');
});
test('the four essential KPIs use canonical selected metrics including total cost',()=>{
 const r=result();assert.deepEqual(getEssentialKpis(r).map(x=>x.key),['total_cost','total_trips','load_utilization','own_weight_share']);
 assert.equal(getEssentialKpis(r)[0].value,2600);assert.ok(getEssentialKpis({}).every(x=>x.value===null));
});
test('every objective highlights exactly its real selected scenario, never assuming balanced',()=>{
 for(const objective of ['balanced','min_cost','min_trips','max_own_fleet','min_co2']){
  const r=result();r.configuration.objective=objective;r.scenarios.selected=structuredClone(r.scenarios[objective]);
  const rows=getScenarioTable(r);assert.equal(rows.filter(x=>x.selected).length,1);assert.equal(rows.find(x=>x.selected).key,objective);
  assert.match(getDecisionNarrative(r),/Dation/);
 }
});
test('unpublished custom selection, missing metrics, same plan and infeasible references remain explicit',()=>{
 const r=result();r.configuration.objective='custom';r.scenarios.selected.plan_fingerprint='custom-plan';
 delete r.scenarios.min_cost.metrics.total_cost;r.scenarios.min_co2.feasible=false;
 let rows=getScenarioTable(r);assert.equal(rows[0].key,'selected');assert.equal(rows[0].selected,true);
 assert.equal(rows.find(x=>x.key==='min_cost').values.total_cost,null);assert.equal(rows.find(x=>x.key==='min_co2').feasible,false);
 r.configuration.objective='min_trips';r.scenarios.selected=structuredClone(r.scenarios.min_trips);
 r.scenarios.balanced.plan_fingerprint=r.scenarios.selected.plan_fingerprint;
 rows=getScenarioTable(r);assert.equal(rows.filter(x=>x.selected).length,1);assert.equal(rows.find(x=>x.key==='balanced').samePlan,true);
});
test('resource shares derive from actual trip evidence and concentration is informational',()=>{
 const r=result(),rows=getResourceParticipation(r);assert.equal(rows[0].trips,2);assert.equal(rows[0].tripShare,1);assert.equal(rows[0].concentrated,true);
 r.scenarios.selected.trips[1].vehicle_id='OTHER';assert.equal(getResourceParticipation(r)[0].tripShare,.5);
 assert.deepEqual(getResourceParticipation({}),[]);
});
test('preview is capped at five and utilization ordering does not mutate the run',()=>{
 const r=result(),trip=r.scenarios.selected.trips[0];
 r.scenarios.selected.trips=Array.from({length:8},(_,i)=>({...trip,trip_id:'T'+i,utilization:i/10}));
 const before=structuredClone(r);assert.equal(getAssignmentPreview(r,99).length,5);assert.equal(getAssignmentPreview(r,0).length,0);
 assert.equal(getTripUtilization(r)[0].trip_id,'T7');assert.equal(getTripUtilization(r,'trip')[0].trip_id,'T0');assert.deepEqual(r,before);
});
test('deterministic insights are limited to three and emissions require feasible published comparisons',()=>{
 const r=result();const first=getDecisionInsights(r);assert.ok(first.length<=3);assert.equal(first.find(x=>x.key==='ownership').metric,1);
 for(const s of Object.values(r.scenarios))s.feasible=false;
 assert.ok(!getDecisionInsights(r).some(x=>x.key==='emissions'));
 delete r.scenarios.selected.metrics.own_weight_share;assert.ok(!getDecisionInsights(r).some(x=>x.key==='ownership'));
});
test('tradeoffs exclude equal values, missing evidence and infeasible references',()=>{
 const r=result();const trade=getDecisionTradeoffs(r,'balanced');assert.ok(trade.gains.some(x=>x.key==='load_utilization'));
 r.scenarios.balanced.feasible=false;assert.deepEqual(getDecisionTradeoffs(r,'balanced').gains,[]);assert.deepEqual(getDecisionTradeoffs(r,'balanced').concessions,[]);
 r.scenarios.balanced.feasible=true;r.scenarios.balanced.plan_fingerprint=r.scenarios.selected.plan_fingerprint;
 assert.deepEqual(getDecisionTradeoffs(r,'balanced').gains,[]);
});
test('corridors aggregate loads, explicit unit quantities, weighted utilization and reliable trip costs',()=>{
 const r=result(),corridor=getCorridorSummary(r)[0];assert.equal(corridor.trips,2);assert.equal(corridor.vehicles,1);
 assert.equal(corridor.loadKg,10000);assert.equal(corridor.units,10);assert.equal(corridor.utilization,10000/12000);assert.equal(corridor.ownWeightShare,1);
 assert.equal(corridor.cost,2600);delete r.scenarios.selected.trips[0].estimated_cost;assert.equal(getCorridorSummary(r)[0].cost,null);
});
test('missing trip measurements cannot become zero costs, loads, utilization or ownership',()=>{
 const r={scenarios:{selected:{trips:[{trip_id:'T',origin:'A',destination:'B',vehicle_id:'V'}]}}};
 const c=getCorridorSummary(r)[0];for(const key of ['loadKg','units','utilization','ownWeightShare','cost'])assert.equal(c[key],null);
 assert.equal(getAssignmentVehicles(r)[0].utilization,null);assert.equal(getTripUtilization(r)[0].utilization,null);
});
test('all presentation models leave the selected plan, configuration and persisted metrics intact',()=>{
 const r=result(),before=structuredClone(r);
 for(const fn of [getAssignmentContext,getEssentialKpis,getDecisionInsights,getScenarioTable,getResourceParticipation,getAssignmentPreview,getDecisionTradeoffs,getCorridorSummary,getTripUtilization])fn(r);
 assert.deepEqual(r,before);
});
