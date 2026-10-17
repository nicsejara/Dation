import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {daysBetween,getSchedulingContext,getSchedulingEssentialKpis,getSchedulingInsights,getVehicleScheduleSummary,getCriticalResource,getDispatchPreview,getOrderSlack,getSlaDistribution,getWaitAnalysis,getCorridorScheduleSummary,getSchedulingWarnings,getTripSla} from '../app/static/js/dispatch/scheduling-dashboard-selectors.mjs';
function fixture(){
  const trip=(id,vehicle,ready,dispatch,free,cycle,wait)=>({trip_id:id,vehicle_id:vehicle,origin:'Base',destination:'Norte',ownership:'own',load_kg:100,cycle_days:cycle,transit_days:1,ready_date:'2026-10-'+ready,dispatch_date:'2026-10-'+dispatch,arrival_date:'2026-10-'+String(Number(dispatch)+1).padStart(2,'0'),resource_available_again:'2026-10-'+free,wait_days:wait,loads:[{order_id:id,product:'P',units:2,kg:100}]});
  return {analysis:{assignment_locked:true,sla_enabled:true,focus_rules:[]},inputs:{assignment:{run_id:'approved-D1',trip_count:3}},decision:{strategy:'service_first'},
    scenarios:{selected:{feasible:true,metrics:{orders:3,total_trips:3,vehicles_used:2,on_time_rate:1,on_time_orders:3,due_orders:3,late_orders:0,makespan_days:6,avg_wait_days:1},trips:[trip('T1','V1','01','01','04',3,0),trip('T2','V1','01','04','07',3,3),trip('T3','V2','01','01','03',2,0)],
      order_outcomes:[{order_id:'T1',arrival_date:'2026-10-02',delivery_due_date:'2026-10-10',trip_ids:['T1']},{order_id:'T2',arrival_date:'2026-10-05',delivery_due_date:'2026-10-09',trip_ids:['T2']},{order_id:'T3',arrival_date:'2026-10-02',delivery_due_date:'2026-10-03',trip_ids:['T3']}]}}};
}
function freeze(value){if(value&&typeof value==='object'){Object.freeze(value);Object.values(value).forEach(freeze);}return value;}
test('context preserves approved source and counts unique orders and load',()=>{
  const r=fixture();assert.deepEqual(getSchedulingContext(r),{trips:3,vehicles:2,orders:3,load_kg:300,source_run_id:'approved-D1',source_approved_at:null,assignment_locked:true});
  delete r.scenarios.selected.metrics.orders;r.scenarios.selected.trips[1].loads[0].order_id='T1';assert.equal(getSchedulingContext(r).orders,2);
});
test('exactly the four essential KPI models retain SLA and raw published metrics',()=>{
  const k=getSchedulingEssentialKpis(fixture());assert.equal(k.on_time_rate,1);assert.equal(k.on_time_orders,3);assert.equal(k.makespan_days,6);assert.equal(k.avg_wait_days,1);assert.equal(k.critical_resource.id,'V1');
});
test('disabled SLA and null rate never become zero percent or 100 percent',()=>{
  const r=fixture();r.analysis.sla_enabled=false;assert.equal(getSchedulingEssentialKpis(r).on_time_rate,null);assert.equal(getSlaDistribution(r).counts.unavailable,3);
  r.analysis.sla_enabled=true;r.scenarios.selected.metrics.on_time_rate=null;assert.equal(getSchedulingEssentialKpis(r).on_time_rate,null);assert.notEqual(getSchedulingInsights(r)[0].title,'Todo dentro de fecha');
});
test('slack boundaries are date-based including leap days and unavailable dates',()=>{
  for(const [due,category,slack] of [['2026-10-01','late',-1],['2026-10-02','critical',0],['2026-10-03','low',1],['2026-10-04','low',2],['2026-10-05','healthy',3],[null,'unavailable',null]]){
    const actual=getOrderSlack({arrival_date:'2026-10-02',delivery_due_date:due});assert.equal(actual.category,category);assert.equal(actual.slack_days,slack);
  }
  assert.equal(daysBetween('2024-02-28','2024-03-01'),2);assert.equal(daysBetween(null,'2026-10-01'),null);
});
test('SLA groups are exclusive and ranked from late to missing',()=>{
  const r=fixture();r.scenarios.selected.order_outcomes[0].delivery_due_date='2026-10-01';delete r.scenarios.selected.order_outcomes[1].delivery_due_date;
  const d=getSlaDistribution(r);assert.deepEqual(d.counts,{healthy:0,low:1,critical:0,late:1,unavailable:1});assert.equal(d.orders[0].order_id,'T1');assert.equal(d.on_time,1);
});
test('critical resource uses occupied days then trips, idle and stable identifier',()=>{
  const r=fixture();r.scenarios.selected.trips[2].load_kg=999999;assert.equal(getCriticalResource(r).id,'V1');
  r.scenarios.selected.trips[2].cycle_days=6;assert.equal(getCriticalResource(r).id,'V1');
  const ties={scenarios:{selected:{trips:[{trip_id:'A',vehicle_id:'Z',cycle_days:2,dispatch_date:'2026-10-01',resource_available_again:'2026-10-04'},{trip_id:'B',vehicle_id:'Y',cycle_days:2,dispatch_date:'2026-10-01',resource_available_again:'2026-10-03'}]}}};
  assert.equal(getCriticalResource(ties).id,'Y');ties.scenarios.selected.trips[0].resource_available_again='2026-10-03';assert.equal(getCriticalResource(ties).id,'Y');
});
test('resource span and idle use resource release, never arrival',()=>{
  const r=getVehicleScheduleSummary(fixture())[0];assert.equal(r.busy_days,6);assert.equal(r.last_free,'2026-10-07');assert.equal(r.idle_days,0);assert.equal(r.gaps[0].days,0);assert.equal(r.trip_share,2/3);
});
test('preview is chronological, deterministic and capped at five',()=>{
  const r=fixture();r.scenarios.selected.trips.reverse();assert.deepEqual(getDispatchPreview(r).map(t=>t.trip_id),['T1','T3','T2']);
  for(let i=0;i<8;i++)r.scenarios.selected.trips.push({...r.scenarios.selected.trips[0],trip_id:'Z'+i});assert.equal(getDispatchPreview(r,99).length,5);
});
test('trip SLA uses complete order arrival rather than early partial trip arrival',()=>{
  const r=fixture();Object.assign(r.scenarios.selected.order_outcomes[0],{arrival_date:'2026-10-12',delivery_due_date:'2026-10-10'});assert.equal(getTripSla(r,r.scenarios.selected.trips[0]).slack_days,-2);
});
test('occupied resource is a demonstrated wait cause; waiting alone is not warning',()=>{
  const r=fixture(),wait=getWaitAnalysis(r)[0];assert.equal(wait.trip_id,'T2');assert.equal(wait.reason,'Recurso ocupado hasta el despacho');assert.equal(wait.wait_category,'controlled');assert.deepEqual(getSchedulingWarnings(r),[]);
});
test('unknown causality retains optimizer sequence and sensitive wait is not late',()=>{
  const r=fixture();r.scenarios.selected.trips[0].resource_available_again='2026-10-03';r.scenarios.selected.order_outcomes[1].delivery_due_date='2026-10-05';
  const wait=getWaitAnalysis(r)[0];assert.equal(wait.reason,'Secuencia resultante del optimizador');assert.equal(wait.wait_category,'sensitive');assert.equal(getSchedulingWarnings(r)[0].severity,'review');
});
test('late wait is classified without claiming causal inefficiency',()=>{
  const r=fixture();r.scenarios.selected.order_outcomes[1].delivery_due_date='2026-10-04';r.scenarios.selected.metrics.late_orders=1;
  assert.equal(getWaitAnalysis(r)[0].wait_category,'late');assert.equal(getSchedulingWarnings(r).find(w=>w.code==='late').severity,'warning');assert.equal(getSchedulingInsights(r)[0].title,'Excepciones de servicio');
});
test('corridors aggregate unique orders, vehicles, dates and minimum SLA',()=>{
  const c=getCorridorScheduleSummary(fixture())[0];assert.equal(c.trip_count,3);assert.equal(c.orders,3);assert.equal(c.kg,300);assert.deepEqual(c.vehicles,['V1','V2']);assert.equal(c.min_slack,1);assert.equal(c.avg_wait_days,1);
});
test('no overlap, ready and Assignment boundary violations block approval',()=>{
  const r=fixture();r.scenarios.selected.trips[1].dispatch_date='2026-09-30';r.inputs.assignment.trip_count=4;
  const codes=getSchedulingWarnings(r).filter(w=>w.severity==='critical').map(w=>w.code);for(const code of ['assignment','overlap','ready'])assert.ok(codes.includes(code));
});
test('infeasible and published resource constraint are critical',()=>{
  const r=fixture();r.scenarios.selected.feasible=false;r.exceptions=[{type:'available_until_conflict',vehicle_id:'V1'}];
  assert.ok(getSchedulingWarnings(r).some(w=>w.code==='infeasible'));assert.equal(getSchedulingWarnings(r).find(w=>w.code==='exception').severity,'critical');
});
test('all selectors accept missing optional fields and empty results',()=>{
  for(const fn of [getSchedulingContext,getSchedulingEssentialKpis,getSchedulingInsights,getVehicleScheduleSummary,getCriticalResource,getDispatchPreview,getSlaDistribution,getWaitAnalysis,getCorridorScheduleSummary,getSchedulingWarnings])assert.doesNotThrow(()=>fn({}));assert.equal(getCriticalResource({}),null);
});
test('selectors never mutate scheduling evidence, including actual fixture',()=>{
  const real=JSON.parse(readFileSync(new URL('./browser/fixtures.json',import.meta.url))).runs.scheduling.result_json;
  for(const result of [freeze(fixture()),freeze(real)]){const before=JSON.stringify(result);for(const fn of [getSchedulingContext,getSchedulingEssentialKpis,getSchedulingInsights,getVehicleScheduleSummary,getCriticalResource,getDispatchPreview,getSlaDistribution,getWaitAnalysis,getCorridorScheduleSummary,getSchedulingWarnings])fn(result);assert.equal(JSON.stringify(result),before);}
});
