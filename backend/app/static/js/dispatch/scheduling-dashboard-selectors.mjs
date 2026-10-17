// Pure presentation models: scheduling_v1 remains the source of truth.
export const SLACK_LOW_DAYS=2;
const finite=value=>value!==null&&value!==''&&Number.isFinite(Number(value));
const number=value=>finite(value)?Number(value):0;
const selected=result=>result?.scenarios?.selected||{};
const tripsOf=result=>selected(result).trips||[];
const stable=(a,b)=>String(a??'').localeCompare(String(b??''));
export function daysBetween(from,to){
  const parse=value=>/^\d{4}-\d{2}-\d{2}$/.test(value||'')?Date.parse(value+'T00:00:00Z'):NaN;
  const days=(parse(to)-parse(from))/86400000;
  return Number.isFinite(days)?days:null;
}
export function getOrderSlack(order,slaEnabled=true){
  const slack=slaEnabled?daysBetween(order?.arrival_date,order?.delivery_due_date):null;
  const category=slack===null?'unavailable':slack<0?'late':slack===0?'critical':slack<=SLACK_LOW_DAYS?'low':'healthy';
  return {...order,slack_days:slack,category,label:{unavailable:slaEnabled?'Sin fecha objetivo':'Sin SLA',late:'Fuera de fecha',critical:'Margen crítico',low:'Margen bajo',healthy:'En fecha'}[category]};
}
export function getVehicleScheduleSummary(result){
  const groups=new Map();
  for(const trip of tripsOf(result)){
    const id=trip.vehicle_id||'Recurso sin identificar';
    if(!groups.has(id))groups.set(id,{id,ownership:trip.ownership,vehicle_type:trip.vehicle_type,trips:[]});
    groups.get(id).trips.push(trip);
  }
  const totalBusy=tripsOf(result).reduce((sum,t)=>sum+number(t.cycle_days),0),total=tripsOf(result).length;
  return [...groups.values()].map(group=>{
    const trips=[...group.trips].sort((a,b)=>stable(a.dispatch_date,b.dispatch_date)||stable(a.trip_id,b.trip_id));
    const busy_days=trips.reduce((sum,t)=>sum+number(t.cycle_days),0);
    const first_dispatch=trips[0]?.dispatch_date,last_free=trips.map(t=>t.resource_available_again).filter(Boolean).sort().at(-1);
    const span=daysBetween(first_dispatch,last_free);
    const gaps=trips.slice(1).map((t,i)=>({previous:trips[i].trip_id,next:t.trip_id,days:daysBetween(trips[i].resource_available_again,t.dispatch_date)}));
    return {...group,trips,trip_count:trips.length,busy_days,first_dispatch,last_free,span_days:span,
      idle_days:span===null?null:Math.max(0,span-busy_days),gaps,
      busy_share:totalBusy?busy_days/totalBusy:0,trip_share:total?trips.length/total:0};
  }).sort((a,b)=>b.busy_days-a.busy_days||b.trip_count-a.trip_count||(a.idle_days??Infinity)-(b.idle_days??Infinity)||stable(a.id,b.id));
}
export const getCriticalResource=result=>getVehicleScheduleSummary(result)[0]||null;
export function getSchedulingContext(result){
  const trips=tripsOf(result),metrics=selected(result).metrics||{},source=result?.inputs?.assignment||{};
  return {trips:metrics.total_trips??trips.length,vehicles:metrics.vehicles_used??new Set(trips.map(t=>t.vehicle_id)).size,
    orders:metrics.orders??new Set(trips.flatMap(t=>(t.loads||[]).map(l=>l.order_id))).size,
    load_kg:trips.reduce((sum,t)=>sum+(finite(t.load_kg)?Number(t.load_kg):(t.loads||[]).reduce((n,l)=>n+number(l.kg),0)),0),
    source_run_id:source.run_id||null,source_approved_at:source.approved_at||null,assignment_locked:result?.analysis?.assignment_locked===true};
}
export function getSchedulingEssentialKpis(result){
  const metrics=selected(result).metrics||{},sla=result?.analysis?.sla_enabled===true;
  return {sla_enabled:sla,on_time_rate:sla&&finite(metrics.on_time_rate)?Number(metrics.on_time_rate):null,
    on_time_orders:sla?metrics.on_time_orders??null:null,due_orders:sla?metrics.due_orders??null:null,
    makespan_days:metrics.makespan_days??null,schedule_start:metrics.schedule_start??null,schedule_end:metrics.schedule_end??null,
    avg_wait_days:metrics.avg_wait_days??null,critical_resource:getCriticalResource(result)};
}
export function getSlaDistribution(result){
  const enabled=result?.analysis?.sla_enabled===true;
  const orders=(selected(result).order_outcomes||[]).map(order=>getOrderSlack(order,enabled))
    .sort((a,b)=>(a.slack_days??Infinity)-(b.slack_days??Infinity)||stable(a.delivery_due_date,b.delivery_due_date)||stable(a.order_id,b.order_id));
  const counts={healthy:0,low:0,critical:0,late:0,unavailable:0};
  for(const order of orders)counts[order.category]++;
  return {enabled,orders,counts,on_time:counts.healthy+counts.low+counts.critical};
}
export function getTripSla(result,trip){
  const enabled=result?.analysis?.sla_enabled===true;
  if(!enabled)return getOrderSlack(trip,false);
  const orders=(selected(result).order_outcomes||[]).filter(o=>(o.trip_ids||[]).includes(trip.trip_id)).map(o=>getOrderSlack(o));
  const known=orders.filter(o=>o.slack_days!==null).sort((a,b)=>a.slack_days-b.slack_days);
  if(known.length)return {...known[0],partial:known.length<orders.length};
  return getOrderSlack(trip);
}
export function getDispatchPreview(result,limit=5){
  return [...tripsOf(result)].sort((a,b)=>stable(a.dispatch_date,b.dispatch_date)||stable(a.vehicle_id,b.vehicle_id)||stable(a.trip_id,b.trip_id))
    .slice(0,Math.max(0,Math.min(5,limit))).map(trip=>({...trip,sla:getTripSla(result,trip)}));
}
export function getWaitAnalysis(result){
  const groups=getVehicleScheduleSummary(result),window=result?.analysis?.planning_window||{},rules=result?.analysis?.focus_rules||[];
  return groups.flatMap(group=>group.trips.map((trip,index)=>{
    const previous=group.trips[index-1],sla=getTripSla(result,trip),wait=number(trip.wait_days);
    let reason='Secuencia resultante del optimizador';
    if(wait>0&&previous&&previous.resource_available_again===trip.dispatch_date&&daysBetween(trip.ready_date,previous.resource_available_again)>0)reason='Recurso ocupado hasta el despacho';
    else if(wait>0&&window.start===trip.dispatch_date&&daysBetween(trip.ready_date,window.start)>0)reason='Inicio de la ventana temporal';
    else if(wait===0)reason='Sin espera desde la disponibilidad';
    const category=wait===0?'none':sla.slack_days===null?'unassessed':sla.slack_days<0?'late':sla.partial?'unassessed':sla.slack_days<=SLACK_LOW_DAYS?'sensitive':'controlled';
    return {...trip,sla,wait_category:category,reason,matched_rules:rules.filter(r=>(r.matched_trip_ids||[]).includes(trip.trip_id))};
  })).sort((a,b)=>number(b.wait_days)-number(a.wait_days)||stable(a.trip_id,b.trip_id));
}
export function getCorridorScheduleSummary(result){
  const groups=new Map();
  for(const trip of tripsOf(result)){
    const key=JSON.stringify([trip.origin,trip.destination]);
    if(!groups.has(key))groups.set(key,{origin:trip.origin,destination:trip.destination,trips:[]});
    groups.get(key).trips.push(trip);
  }
  return [...groups.values()].map(group=>{
    const slack=group.trips.map(t=>getTripSla(result,t).slack_days).filter(v=>v!==null);
    const ids=new Set(group.trips.flatMap(t=>(t.loads||[]).map(l=>l.order_id)));
    const assessed=getSlaDistribution(result).orders.filter(o=>ids.has(o.order_id)&&o.slack_days!==null);
    const on_time_orders=assessed.filter(o=>o.slack_days>=0).length;
    return {...group,trip_count:group.trips.length,orders:new Set(group.trips.flatMap(t=>(t.loads||[]).map(l=>l.order_id))).size,
      kg:group.trips.reduce((sum,t)=>sum+number(t.load_kg),0),vehicles:[...new Set(group.trips.map(t=>t.vehicle_id))].sort(),
      first_dispatch:group.trips.map(t=>t.dispatch_date).filter(Boolean).sort()[0],last_arrival:group.trips.map(t=>t.arrival_date).filter(Boolean).sort().at(-1),
      avg_wait_days:group.trips.reduce((sum,t)=>sum+number(t.wait_days),0)/group.trips.length,min_slack:slack.length?Math.min(...slack):null,
      due_orders:assessed.length,on_time_orders,late_orders:assessed.length-on_time_orders,on_time_rate:assessed.length?on_time_orders/assessed.length:null};
  }).sort((a,b)=>b.trip_count-a.trip_count||stable(a.origin,b.origin)||stable(a.destination,b.destination));
}
export function getSchedulingWarnings(result){
  const plan=selected(result),warnings=[],metrics=plan.metrics||{},solver=plan.solver||result?.engine?.solver||{};
  const add=(code,severity,title,detail)=>warnings.push({code,severity,title,detail});
  if(plan.feasible===false||['infeasible','invalid','model_invalid'].includes(String(solver.status).toLowerCase()))add('infeasible','critical','No existe una planificación factible',solver.reason||result?.decision?.message||'Revisá las restricciones y la ventana publicada por el motor.');
  if(result?.analysis?.assignment_locked===false||(result?.inputs?.assignment?.trip_count!=null&&result.inputs.assignment.trip_count!==tripsOf(result).length))add('assignment','critical','La Assignment no coincide','El calendario no conserva el contrato de viajes aprobado.');
  for(const group of getVehicleScheduleSummary(result)){
    for(const gap of group.gaps)if(gap.days!==null&&gap.days<0)add('overlap','critical','Conflicto de disponibilidad',group.id+': '+gap.previous+' y '+gap.next+' se superponen.');
    for(const trip of group.trips){
      if(daysBetween(trip.ready_date,trip.dispatch_date)<0)add('ready','critical','Salida anterior a la disponibilidad',trip.trip_id);
      if((daysBetween(trip.dispatch_date,trip.resource_available_again)??Infinity)<number(trip.transit_days))add('cycle','critical','Disponibilidad temporal inconsistente',trip.trip_id);
    }
  }
  if(result?.analysis?.sla_enabled&&number(metrics.late_orders)>0)add('late','warning','Órdenes fuera de fecha',metrics.late_orders+' órdenes requieren revisión antes de aprobar.');
  const critical=getSlaDistribution(result).counts.critical;
  if(critical)add('slack','review','Entregas sin margen',critical+' órdenes llegan en su fecha objetivo. No es un incumplimiento.');
  for(const exception of result?.exceptions||[]){
    if(exception.order_id&&exception.late_days!=null)continue;
    add('exception',/conflict|infeasible|mismatch|available_until/i.test(exception.type||exception.code||'')?'critical':'review',exception.message||exception.type||exception.code||'Restricción temporal publicada',exception.detail||exception.vehicle_id||exception.trip_id||'Revisá el detalle publicado por el motor.');
  }
  return warnings;
}
export function getSchedulingInsights(result){
  const metrics=selected(result).metrics||{},sla=getSlaDistribution(result),resource=getCriticalResource(result),waits=getWaitAnalysis(result);
  const service=!sla.enabled?{title:'Calendario sin SLA',text:'Las fechas objetivo no participaron de esta optimización.'}
    :number(metrics.late_orders)>0?{title:'Excepciones de servicio',text:metrics.late_orders+' órdenes superan su fecha objetivo y requieren revisión.'}
    :metrics.on_time_rate===1?{title:'Todo dentro de fecha',text:metrics.on_time_orders+' órdenes con fecha objetivo llegan dentro del SLA configurado.'}
    :{title:'Servicio evaluado',text:'Revisá las órdenes con fecha objetivo y sus márgenes publicados.'};
  const insights=[service];
  if(resource)insights.push({title:resource.id+' concentra el calendario',text:'Ejecuta '+resource.trip_count+' de '+tripsOf(result).length+' viajes y acumula '+resource.busy_days+' días de ocupación temporal.'});
  const controlled=waits.filter(t=>t.wait_category==='controlled'),occupied=waits.filter(t=>t.wait_days>0&&t.reason.startsWith('Recurso ocupado'));
  insights.push(occupied.length?{title:'La disponibilidad ordena la secuencia',text:occupied.length+' viajes salen cuando el vehículo queda libre del viaje anterior.'}
    :controlled.length?{title:'Espera con margen disponible',text:controlled.length+' viajes esperan y conservan más de dos días de margen de servicio.'}
    :{title:'Espera y servicio se revisan juntos',text:'Una espera no implica un error. El margen de cada entrega permite interpretar su sensibilidad.'});
  return insights.slice(0,3);
}
