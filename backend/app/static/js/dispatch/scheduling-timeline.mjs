import {esc,num,date,chart} from './shared.mjs';
import {chartPalette} from './chart-theme.mjs';
import {daysBetween,getVehicleScheduleSummary,getTripSla} from './scheduling-dashboard-selectors.mjs';
import {heading} from './scheduling-essential.mjs';
export function tripTooltip(result,trip){
  const sla=getTripSla(result,trip);
  return trip.trip_id+' · '+trip.vehicle_id+'\n'+trip.origin+' → '+trip.destination
    +'\nReady: '+date(trip.ready_date)+'\nSalida: '+date(trip.dispatch_date)+'\nLlegada: '+date(trip.arrival_date)
    +'\nDisponible: '+date(trip.resource_available_again)+'\nEspera: '+num(trip.wait_days)+' d'
    +'\nObjetivo: '+date(trip.delivery_due_date)+'\n'+sla.label+(sla.slack_days===null?'':' · margen '+num(sla.slack_days)+' d');
}
export function renderEssentialTimeline(root,result){
  const groups=getVehicleScheduleSummary(result),metrics=result.scenarios.selected.metrics||{},start=metrics.schedule_start;
  if(!groups.length){root.innerHTML=heading('Resumen temporal del plan')+'<p>No hay viajes programados.</p>';return;}
  const records=groups.flatMap((g,row)=>g.trips.map((trip,index)=>({trip,row,series:2*index+1})));
  root.innerHTML=heading('Resumen temporal del plan','Cada bloque representa cuándo un vehículo queda ocupado por un viaje, incluido su retorno.')
    +'<div class="scheduling-timeline-scroll" role="region" tabindex="0" aria-label="Resumen temporal desplazable"><div class="scheduling-timeline-chart dispatch-chart" role="img" aria-label="Una fila por vehículo; detalle accesible debajo"></div></div>'
    +'<p class="scheduling-legend"><span>Programado</span><span class="is-critical">Margen bajo o crítico</span><span class="is-late">Fuera de fecha</span></p>'
    +'<details class="scheduling-timeline-accessible"><summary>Consultar fechas y detalle accesible de los viajes</summary><ul>'+records.map(({trip:t})=>'<li><button type="button" data-timeline-trip="'+esc(t.trip_id)+'">'+esc(t.trip_id)+' · '+esc(t.vehicle_id)+' · '+esc(t.destination)+'</button><p>'+esc(tripTooltip(result,t)).replaceAll('\n',' · ')+'</p></li>').join('')+'</ul></details>';
  const node=root.querySelector('.dispatch-chart'),palette=chartPalette(node),style=getComputedStyle(node),colors={late:style.getPropertyValue('--color-danger').trim(),critical:style.getPropertyValue('--color-warning').trim(),low:style.getPropertyValue('--color-warning').trim()};
  node.style.height=Math.max(240,groups.length*48+90)+'px';
  // Each offset/duration pair shares a stack: one row per vehicle, one chart.
  // Uses the already-vendored BarChart; no extra chart bundle is required.
  const series=[];
  for(let index=0;index<Math.max(...groups.map(g=>g.trips.length));index++){
    series.push({type:'bar',stack:'vehicle-sequence',silent:true,itemStyle:{opacity:0},data:groups.map(g=>{
      const t=g.trips[index];return t?Math.max(0,daysBetween(index?g.trips[index-1].resource_available_again:start,t.dispatch_date)||0):0;
    })});
    series.push({type:'bar',stack:'vehicle-sequence',barMaxWidth:24,data:groups.map(g=>{
      const t=g.trips[index];return t?{value:Math.max(0,daysBetween(t.dispatch_date,t.resource_available_again)||0),trip_id:t.trip_id,itemStyle:{color:colors[getTripSla(result,t).category]||palette.series[0],borderColor:style.getPropertyValue('--color-surface').trim(),borderWidth:1.5}}:0;
    })});
  }
  const instance=chart(node,{animation:false,grid:{left:110,right:28,top:20,bottom:48},tooltip:{trigger:'item',renderMode:'richText',formatter:p=>{
    const trip=records.find(r=>r.trip.trip_id===p.data?.trip_id)?.trip;return trip?tripTooltip(result,trip):'';
  }},
    xAxis:{type:'value',min:0,max:Math.max(1,daysBetween(start,metrics.schedule_end)||1),minInterval:1,axisLabel:{formatter:value=>{const d=new Date(start+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+value);return date(d.toISOString().slice(0,10)).replace(/ de \d{4}$/,'');}}},
    yAxis:{type:'category',inverse:true,data:groups.map(g=>g.id),axisLabel:{width:98,overflow:'truncate'}},series});
  root.querySelectorAll('[data-timeline-trip]').forEach((button,index)=>button.onfocus=()=>instance?.dispatchAction({type:'showTip',seriesIndex:records[index].series,dataIndex:records[index].row}));
}
export function renderDetailedTimeline(root,result){
  const trips=getVehicleScheduleSummary(result).flatMap(g=>g.trips),metrics=result.scenarios.selected.metrics||{},start=[metrics.schedule_start,...trips.map(t=>t.ready_date)].filter(Boolean).sort()[0];
  root.innerHTML=heading('Timeline completo','El viaje termina en la llegada; el recurso queda libre nuevamente después del ciclo y retorno.')
    +'<div class="dispatch-schedule-chart-scroll" role="region" tabindex="0" aria-label="Calendario completo desplazable"><div class="dispatch-schedule-chart dispatch-chart" role="img" aria-label="Calendario detallado por viaje"></div></div>';
  if(!trips.length){root.innerHTML+='<p>No hay viajes programados.</p>';return;}
  const node=root.querySelector('.dispatch-chart');node.style.height=Math.max(320,trips.length*30+70)+'px';
  const style=getComputedStyle(node);
  chart(node,{legend:{data:['Espera','Tránsito','Retorno / ciclo restante'],top:0},grid:{left:170,right:28,top:40,bottom:45},tooltip:{trigger:'item',renderMode:'richText',formatter:p=>tripTooltip(result,trips[p.dataIndex])},
    xAxis:{type:'value',min:0,max:Math.max(1,daysBetween(start,metrics.schedule_end)||1),axisLabel:{formatter:value=>{const d=new Date(start+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+Number(value));return date(d.toISOString().slice(0,10));}}},
    yAxis:{type:'category',inverse:true,data:trips.map(t=>t.vehicle_id+' · '+t.trip_id),axisLabel:{width:160,overflow:'truncate'}},
    series:[{type:'bar',stack:'schedule',silent:true,itemStyle:{opacity:0},data:trips.map(t=>daysBetween(start,t.ready_date))},
      {name:'Espera',type:'bar',stack:'schedule',itemStyle:{color:style.getPropertyValue('--color-info').trim()},data:trips.map(t=>Math.max(0,daysBetween(t.ready_date,t.dispatch_date)||0))},
      {name:'Tránsito',type:'bar',stack:'schedule',itemStyle:{color:style.getPropertyValue('--color-brand-hover').trim()},data:trips.map(t=>Math.max(0,daysBetween(t.dispatch_date,t.arrival_date)||0))},
      {name:'Retorno / ciclo restante',type:'bar',stack:'schedule',itemStyle:{color:style.getPropertyValue('--color-text-muted').trim()},data:trips.map(t=>Math.max(0,daysBetween(t.arrival_date,t.resource_available_again)||0))}]});
}
