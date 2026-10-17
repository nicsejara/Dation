import {esc,num,pct,date} from './shared.mjs';
import {getSlaDistribution,getWaitAnalysis,getVehicleScheduleSummary,getCorridorScheduleSummary,getTripSla} from './scheduling-dashboard-selectors.mjs';
import {heading,slaBadge} from './scheduling-essential.mjs';
import {renderDetailedTimeline} from './scheduling-timeline.mjs';
const cell=value=>'<td>'+value+'</td>';
function table(labels,rows,label){
  return '<div class="scheduling-table-scroll" role="region" tabindex="0" aria-label="'+esc(label)+'"><table class="scheduling-table"><thead><tr>'+labels.map(x=>'<th scope="col">'+esc(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.join('')+'</tbody></table></div>';
}
const row=(key,values)=>'<tr><th scope="row">'+esc(key)+'</th>'+values.map(cell).join('')+'</tr>';
const section=(id,title,copy,body)=>'<section class="scheduling-advanced__section" id="'+id+'" tabindex="-1">'+heading(title,copy)+body+'</section>';
const slack=value=>value===null?'—':num(value)+' d';
const waitLabels={none:'Sin espera',unassessed:'Sin evaluación SLA',late:'Espera con tardanza; causalidad no demostrada',sensitive:'Espera sensible',controlled:'Espera controlada'};

export function renderSchedulingAdvanced(root,result){
  const sla=getSlaDistribution(result),resources=getVehicleScheduleSummary(result),waits=getWaitAnalysis(result),corridors=getCorridorScheduleSummary(result),trips=result.scenarios.selected.trips||[],rules=result.analysis?.focus_rules||[];
  const slaTable=table(['Orden','Prioridad','Ready','Primera salida','Llegada','Objetivo','Margen','Estado'],sla.orders.map(o=>row(o.order_id,[esc(o.priority),date(o.ready_date),date(o.first_dispatch_date),date(o.arrival_date),date(o.delivery_due_date),slack(o.slack_days),slaBadge(o)])),'Órdenes y márgenes SLA');
  const distribution='<div class="scheduling-sla-distribution">'+[['healthy','Margen saludable'],['low','Margen bajo (1–2 d)'],['critical','Margen crítico (0 d)'],['late','Fuera de fecha'],['unavailable','Sin fecha objetivo']].map(([key,label])=>'<div class="is-'+key+'"><strong>'+num(sla.counts[key])+'</strong><span>'+label+'</span></div>').join('')+'</div><p>'+num(sla.on_time)+' órdenes en fecha; los márgenes saludables, bajos y críticos son categorías excluyentes.</p>';
  root.innerHTML='<section class="scheduling-advanced__section" id="scheduling-timeline-detailed" tabindex="-1"></section>'
    +section('scheduling-service','SLA y márgenes',sla.enabled?'Ordenado desde el menor margen. La fecha de llegada de la orden incluye todas sus cargas.':'Las fechas objetivo no participaron de esta corrida; no se calcula un porcentaje ficticio.',(sla.enabled?distribution:'<p>Sin SLA. Las órdenes conservan sus fechas publicadas.</p>')+slaTable)
    +section('scheduling-waits','Esperas y motivos','La espera no es automáticamente un problema. Una causa se señala sólo cuando las fechas la demuestran.',
      '<label class="scheduling-sort">Ordenar esperas <select data-scheduling-wait-sort><option value="wait">Mayor espera</option><option value="slack">Menor margen</option><option value="resource">Vehículo</option></select></label><div data-scheduling-wait-table></div>')
    +section('scheduling-occupancy','Ocupación de flota','Días ocupados = suma de cycle_days. Los huecos se derivan entre despachos y disponibilidad posterior.',
      table(['Vehículo','Viajes','Ocupación','Participación','Primera salida','Libre nuevamente','Huecos','Propiedad'],resources.map(r=>row(r.id,[num(r.trip_count),num(r.busy_days)+' d',pct(r.busy_share)+'<div class="scheduling-bar"><span style="width:'+Math.round(r.busy_share*100)+'%"></span></div>',date(r.first_dispatch),date(r.last_free),slack(r.idle_days),r.ownership==='own'?'Propio':'Tercerizado'])),'Ocupación por vehículo')
      +(resources[0]?'<p class="scheduling-summary-strip"><strong>Recurso condicionante: '+esc(resources[0].id)+'.</strong> Acumula '+num(resources[0].busy_days)+' días ocupados y '+num(resources[0].trip_count)+' de '+num(trips.length)+' viajes. '+(waits.some(t=>t.vehicle_id===resources[0].id&&t.wait_days>0&&['critical','low'].includes(t.sla.category))?'Su secuencia contiene entregas posteriores con poco margen.':'La concentración temporal por sí sola no implica un riesgo.')+'</p>':''))
    +section('scheduling-corridors','Análisis por corredor','Viajes agrupados por origen y destino; órdenes únicas dentro de cada corredor.',
      table(['Corredor','Viajes','Órdenes','Carga','Primera salida','Última llegada','Espera media','SLA','Margen mínimo','Vehículos'],corridors.map(c=>row(c.origin+' → '+c.destination,[num(c.trip_count),num(c.orders),num(c.kg)+' kg',date(c.first_dispatch),date(c.last_arrival),num(c.avg_wait_days,2)+' d',sla.enabled?(c.on_time_rate===null?'Sin fecha objetivo':pct(c.on_time_rate)+' · '+num(c.on_time_orders)+' de '+num(c.due_orders)):'Sin SLA',slack(c.min_slack),esc(c.vehicles.join(', '))])),'Corredores programados'))
    +section('scheduling-full-plan','Plan completo de despachos','Expandí cada viaje para consultar las cargas heredadas de Assignment. Ready, llegada y disponibilidad del recurso se muestran por separado.',
      table(['Viaje','Vehículo','Ruta','Carga','Ready','Despacho','Llegada','Libre nuevamente','Espera','Ciclo','Objetivo','Margen','SLA'],[...trips].sort((a,b)=>String(a.dispatch_date).localeCompare(String(b.dispatch_date))||String(a.trip_id).localeCompare(String(b.trip_id))).map(t=>{
        const loads='<details><summary>'+esc(t.trip_id)+'</summary><ul class="scheduling-loads">'+(t.loads||[]).map(l=>'<li><strong>'+esc(l.order_id)+'</strong> · '+esc(l.product)+' · '+num(l.units)+' unidades · '+num(l.kg)+' kg</li>').join('')+'</ul></details>',s=getTripSla(result,t);
        return '<tr><th scope="row">'+loads+'</th>'+[esc(t.vehicle_id),esc(t.origin+' → '+t.destination),num(t.load_kg)+' kg',date(t.ready_date),date(t.dispatch_date),date(t.arrival_date),date(t.resource_available_again),num(t.wait_days)+' d',num(t.cycle_days)+' d',date(t.delivery_due_date),slack(s.slack_days),slaBadge(s)].map(cell).join('')+'</tr>';
      }),'Plan completo desplazable'))
    +(rules.length?section('scheduling-rules','Reglas aplicadas','Evidencia temporal publicada por el motor.',table(['Campo','Valores','Acción','Desde','Hasta','Viajes alcanzados'],rules.map((r,i)=>row(r.field||r.match?.field||'Regla '+(i+1),[esc((r.values||r.match?.values||[]).join(', ')),esc(r.action),date(r.planning_window_start),date(r.planning_window_end),num(r.matched_trip_count??r.matched_trip_ids?.length)+' · '+esc((r.matched_trip_ids||[]).join(', '))])),'Reglas temporales')):'')
    +'<p class="scheduling-v2__note">Comparación temporal no incluida porque el contrato actual publica un único escenario Scheduling.</p>';
  function drawWaits(){
    const mode=root.querySelector('[data-scheduling-wait-sort]').value,rows=[...waits];
    if(mode==='slack')rows.sort((a,b)=>(a.sla.slack_days??Infinity)-(b.sla.slack_days??Infinity)||String(a.trip_id).localeCompare(String(b.trip_id)));
    if(mode==='resource')rows.sort((a,b)=>String(a.vehicle_id).localeCompare(String(b.vehicle_id))||String(a.dispatch_date).localeCompare(String(b.dispatch_date)));
    root.querySelector('[data-scheduling-wait-table]').innerHTML=table(['Viaje','Vehículo','Ready','Despacho','Espera','Objetivo','Margen','Lectura','Motivo'],rows.map(t=>row(t.trip_id,[esc(t.vehicle_id),date(t.ready_date),date(t.dispatch_date),num(t.wait_days)+' d',date(t.delivery_due_date),slack(t.sla.slack_days),esc(waitLabels[t.wait_category]),esc(t.reason)+(t.matched_rules.length?'<small>Reglas aplicadas: '+num(t.matched_rules.length)+'</small>':'')])),'Esperas por viaje');
  }
  root.querySelector('[data-scheduling-wait-sort]').onchange=drawWaits;drawWaits();renderDetailedTimeline(root.querySelector('#scheduling-timeline-detailed'),result);
}
