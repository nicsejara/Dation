import test from 'node:test';
import assert from 'node:assert/strict';
import {
  EXECUTIVE_KPIS,getOperationalKpis,getExecutiveKpisForScenario,getScenarioMetric,
  getComparisonMetricDefinitions,getComparisonRows,getApprovalWarnings,sameAssignmentPlan,
} from '../app/static/js/dispatch/assignment-dashboard-selectors.mjs';

const keys=['total_trips','load_utilization','avg_cost_per_trip','own_weight_share'];
function result(){
  return {configuration:{objective:'min_cost'},scenarios:{
    selected:{feasible:true,plan_fingerprint:'original',metrics:{total_cost:1000,total_trips:4,load_utilization:.82,own_weight_share:.78}},
    balanced:{feasible:true,plan_fingerprint:'reference',metrics:{total_cost:1200,total_trips:3,load_utilization:.75,own_weight_share:.64}},
  }};
}

test('main and comparator share exactly four definitions, including absent historical values',()=>{
  assert.deepEqual(getOperationalKpis(result()).map(k=>k.key),keys);
  assert.deepEqual(getComparisonMetricDefinitions().map(k=>k.key),keys);
  assert.deepEqual(getOperationalKpis({}).map(k=>k.value),[null,null,null,null]);
  assert.deepEqual(getOperationalKpis(result()).map(k=>k.label),['Cantidad de viajes','Utilización media','Costo promedio por viaje','% flota propia']);
  assert.deepEqual(getExecutiveKpisForScenario(result().scenarios.balanced).map(k=>k.key),keys);
  assert.ok(Object.isFrozen(EXECUTIVE_KPIS)&&EXECUTIVE_KPIS.every(Object.isFrozen));
});
test('average cost uses its own scenario denominator and is never mixed or rounded early',()=>{
  const r=result(),before=structuredClone(r);
  assert.equal(getScenarioMetric(r.scenarios.selected,'avg_cost_per_trip'),250);
  assert.equal(getScenarioMetric(r.scenarios.balanced,'avg_cost_per_trip'),400);
  const row=getComparisonRows(r,'balanced').find(x=>x.key==='avg_cost_per_trip');
  assert.equal(row.absolute,-150);assert.equal(row.percent,-.375);assert.equal(row.semantic,'improvement');
  assert.equal(getScenarioMetric({metrics:{total_cost:1000,total_trips:3}},'avg_cost_per_trip'),1000/3);
  assert.deepEqual(r,before);
});
test('average cost rejects missing, nonpositive, nonfinite and nonnumeric inputs safely',()=>{
  for(const metrics of [
    {total_cost:1000,total_trips:0},{total_cost:1000,total_trips:-1},{total_cost:1000,total_trips:null},
    {total_cost:null,total_trips:4},{total_cost:undefined,total_trips:4},{total_cost:Infinity,total_trips:4},
    {total_cost:1000,total_trips:NaN},{total_cost:true,total_trips:4},{total_cost:1000,total_trips:[]},
    {total_cost:' ',total_trips:4},{total_cost:'invalid',total_trips:4},{total_cost:1e308,total_trips:1e-308},
    {total_cost:Symbol('invalid'),total_trips:4},
  ])assert.equal(getScenarioMetric({metrics},'avg_cost_per_trip'),null);
  assert.equal(getScenarioMetric({metrics:{total_cost:'1000',total_trips:'4'}},'avg_cost_per_trip'),250);
  assert.equal(getScenarioMetric({metrics:{total_cost:0,total_trips:4}},'avg_cost_per_trip'),0);
});
test('an untrusted precomputed average does not override the canonical ratio',()=>{
  const scenario={metrics:{total_cost:1000,total_trips:4,avg_cost_per_trip:999}};
  assert.equal(getScenarioMetric(scenario,'avg_cost_per_trip'),250);
});
test('own fleet share remains the persisted weight share, never a trip or vehicle ratio',()=>{
  const r=result();Object.assign(r.scenarios.selected.metrics,{own_trips:4,vehicles_used:1,own_weight_kg:9999,total_weight_kg:10000});
  assert.equal(getOperationalKpis(r).find(x=>x.key==='own_weight_share').value,.78);
  assert.match(EXECUTIVE_KPIS.find(x=>x.key==='own_weight_share').description,/peso/);
});
test('utilization is the persisted canonical metric and both percent metrics compare in fractions',()=>{
  const r=result();r.kpi_directions={load_utilization:'lower_better'};
  const rows=getComparisonRows(r,'balanced');
  assert.ok(Math.abs(rows[1].absolute*100-7)<1e-10);assert.equal(rows[1].semantic,'improvement');
  assert.ok(Math.abs(rows[3].absolute*100-14)<1e-10);assert.equal(rows[3].semantic,'improvement');
  r.scenarios.selected.trips=[{load_kg:1,capacity_kg:100}];
  assert.equal(getOperationalKpis(r)[1].value,.82);
});
test('average cost is descriptive even when the engine minimizes total cost',()=>{
  const r=result();r.configuration={objective:'min_cost',dimensions:['cost'],weights:{cost:1}};
  assert.equal(getOperationalKpis(r).find(x=>x.key==='avg_cost_per_trip').objective,false);
});
test('missing historical reference values stay visible and noncomparable',()=>{
  const r=result();delete r.scenarios.balanced.metrics.load_utilization;delete r.scenarios.balanced.metrics.total_cost;
  const rows=getComparisonRows(r,'balanced');assert.equal(rows.length,4);
  assert.equal(rows[1].referenceValue,null);assert.equal(rows[1].semantic,'no_comparable');
  assert.equal(rows[2].referenceValue,null);assert.equal(rows[2].semantic,'no_comparable');
});
test('infeasible selected or reference scenarios never claim improvements',()=>{
  const r=result();r.scenarios.balanced.feasible=false;
  assert.ok(getComparisonRows(r,'balanced').every(x=>x.semantic==='no_comparable'));
  r.scenarios.balanced.feasible=true;r.scenarios.selected.feasible=false;
  assert.ok(getComparisonRows(r,'balanced').every(x=>x.semantic==='no_comparable'));
});
test('relative deltas require a nonzero reference and same-plan fingerprints remain intact',()=>{
  const r=result();r.scenarios.balanced.metrics.total_trips=0;
  assert.equal(getComparisonRows(r,'balanced')[0].percent,null);
  r.scenarios.selected.metrics.total_trips=0;
  assert.equal(getComparisonRows(r,'balanced')[0].semantic,'same');assert.equal(getComparisonRows(r,'balanced')[0].percent,null);
  r.scenarios.balanced.plan_fingerprint='original';assert.equal(sameAssignmentPlan(r.scenarios.selected,r.scenarios.balanced),true);
});
test('empty review has no invented solver checklist; genuine controls remain',()=>{
  const r=result();assert.deepEqual(getApprovalWarnings(r),[]);
  r.scenarios.selected.trips=[{trip_id:'T',ownership:'third_party'}];
  r.scenarios.selected.order_outcomes=[{order_id:'O',split:true}];r.inputs={anomalies:[{decision:'include'}]};
  assert.deepEqual(getApprovalWarnings(r).map(x=>x.key),['outsourced','anomalies','split_orders']);
});
test('critical feasibility and concrete engine exceptions are never filtered out',()=>{
  const r=result();r.scenarios.selected.feasible=false;
  r.exceptions=[{title:'Carga incompatible',detail:'Revisar el vehículo',trip_id:'T1'}];
  const warnings=getApprovalWarnings(r);assert.equal(warnings[0].key,'infeasible');assert.match(warnings[0].label,/crítica/);
  assert.match(warnings[1].detail,/Carga incompatible.*Revisar el vehículo.*T1/);
  delete r.scenarios.selected.feasible;r.engine={solver:{status:'infeasible'}};
  assert.equal(getApprovalWarnings(r)[0].key,'infeasible');
});
