import {esc,num,pct,date} from './shared.mjs';
import {schedulingIcon as icon} from './scheduling-dashboard-shell.mjs';
import {getSchedulingContext,getSchedulingEssentialKpis,getSchedulingInsights,getVehicleScheduleSummary,getDispatchPreview} from './scheduling-dashboard-selectors.mjs';
export const heading=(title,copy='')=>'<div class="scheduling-v2__heading"><h2>'+esc(title)+'</h2>'+(copy?'<p>'+esc(copy)+'</p>':'')+'</div>';
export const slaBadge=sla=>'<span class="scheduling-sla is-'+esc(sla.category)+'">'+esc(sla.label)+(sla.slack_days===null?'':' · '+num(sla.slack_days)+' d')+(sla.partial?' · parcial':'')+'</span>';
export function hero(root,result,caseActions={}){
  const k=getSchedulingEssentialKpis(result),m=result.scenarios?.selected?.metrics||{},solver=result.scenarios?.selected?.solver||result.engine?.solver||{},rules=result.analysis?.focus_rules||[];
  const exceptions=k.sla_enabled&&Number(m.late_orders)>0;
  const status=caseActions.status==='stale'?'Evidencia desactualizada':caseActions.status==='approved'?'Planificación aprobada':exceptions?'Plan con excepciones':solver.status==='feasible'?'Plan factible':'Plan ejecutable';
  const service=!k.sla_enabled?'utilizando la secuencia temporal recomendada':exceptions?'con '+num(m.late_orders)+' órdenes fuera de fecha objetivo':k.on_time_rate===1?'manteniendo el 100% de las órdenes con SLA dentro de fecha':'con el nivel de servicio publicado por el motor';
  root.innerHTML='<span class="dispatch-kicker">DECISIÓN 02 · PLANIFICACIÓN DE DESPACHOS</span><h1>Planificación recomendada</h1>'
    +'<div class="scheduling-hero__badges"><span class="scheduling-status '+(exceptions||caseActions.status==='stale'?'is-warning':'is-good')+'" data-scheduling-hero-status>'+icon(exceptions||caseActions.status==='stale'?'alertTriangle':'checkCircle')+esc(status)+'</span><span class="scheduling-status">'+icon('lock')+'Assignment bloqueada</span></div>'
    +'<p class="scheduling-hero__headline">Ejecutar '+num(m.total_trips)+' viajes entre '+date(k.schedule_start)+' y '+date(k.schedule_end)+' '+esc(service)+'.</p>'
    +'<p>'+(result.decision?.strategy==='earliest_dispatch'?'Dation prioriza despachar cada viaje tan pronto como carga y recurso están disponibles, compactando el calendario.':'Dation prioriza el cumplimiento de fechas objetivo y luego reduce esperas y duración total del calendario.')+'</p>'
    +(rules.length?'<p>El plan incorpora reglas temporales específicas sobre '+num(result.analysis?.focused_trip_count)+' viajes.</p>':'')
    +(caseActions.status==='stale'?'<p role="status">La Assignment o los datos del caso cambiaron. Reconfigurá la planificación antes de aprobar.</p>':'');
}
export function context(root,result){
  const c=getSchedulingContext(result);
  root.innerHTML=heading('Contexto')+'<div class="scheduling-context__grid">'
    +[['route','Viajes asignados',num(c.trips),'Viajes del plan'],['weight','Carga total',num(c.load_kg)+' kg','Carga del plan'],['truck','Vehículos utilizados',num(c.vehicles),'Recursos del plan'],['clipboardList','Órdenes',num(c.orders),'Órdenes incluidas']]
      .map(([glyph,label,value,copy])=>'<article>'+icon(glyph)+'<div><small>'+label+'</small><strong>'+value+'</strong><span>'+copy+'</span></div></article>').join('')+'</div>'
    +'<p class="scheduling-lock">'+icon('lock')+'<span><strong>Assignment bloqueada.</strong> Los viajes y recursos ya fueron aprobados. Scheduling sólo define fecha y secuencia. Viajes, cargas y vehículos no cambian en esta decisión.'
    +(c.source_run_id?' <span class="scheduling-source">Corrida fuente: '+esc(c.source_run_id)+'</span>':'')+'</span></p>';
}
export function kpis(root,result){
  const k=getSchedulingEssentialKpis(result),r=k.critical_resource;
  const values=[['target','Cumplimiento SLA',k.sla_enabled?(k.on_time_rate===null?'Sin dato':pct(k.on_time_rate)):'Sin SLA',k.sla_enabled?num(k.on_time_orders)+' de '+num(k.due_orders)+' órdenes en fecha':'Las fechas objetivo no participaron de la optimización'],
    ['calendarRange','Horizonte operativo',num(k.makespan_days)+' días',date(k.schedule_start)+' → '+date(k.schedule_end)],
    ['clock','Espera promedio',num(k.avg_wait_days,2)+' días','Entre disponibilidad y despacho'],
    ['truck','Recurso crítico',r?.id||'Sin recurso',r?num(r.trip_count)+' de '+num(result.scenarios.selected.trips.length)+' viajes · '+num(r.busy_days)+' días ocupado':'No hay viajes publicados']];
  root.innerHTML=heading('Indicadores de la planificación')+'<div class="scheduling-kpis">'+values.map(([glyph,label,value,copy],i)=>'<article data-scheduling-kpi="'+i+'">'+icon(glyph)+'<small>'+label+'</small><strong>'+esc(value)+'</strong><p>'+esc(copy)+'</p></article>').join('')+'</div>';
}
export function insights(root,result){
  const warnings=getSchedulingInsights(result),strategy=result.decision?.strategy;
  root.innerHTML=heading('¿Qué planificó Dation?')+'<div class="scheduling-insights">'+warnings.map((item,i)=>'<article>'+icon(['target','truck','clock'][i])+'<h3>'+esc(item.title)+'</h3><p>'+esc(item.text)+'</p></article>').join('')+'</div>'
    +'<p class="scheduling-summary-strip"><strong>En resumen:</strong> Dation conserva los recursos aprobados y define su secuencia temporal. '+(strategy==='earliest_dispatch'?'Prioriza las salidas más tempranas.':'Prioriza el servicio cuando el SLA está activo y después reduce esperas y horizonte.')+'</p>';
}
export function resources(root,result){
  const groups=getVehicleScheduleSummary(result);
  root.innerHTML=heading('Cómo se ejecuta el plan','Participación por recurso; la ocupación incluye el retorno.')+'<ul class="scheduling-resources">'+groups.map(g=>'<li><div><strong>'+esc(g.id)+'</strong><span>'+num(g.trip_count)+' viajes · '+pct(g.trip_share)+'</span></div><div class="scheduling-bar"><span style="width:'+Math.round(g.trip_share*100)+'%"></span></div><p>'+num(g.busy_days)+' días ocupado · '+(g.ownership==='own'?'Propio':'Tercerizado')+'</p><details><summary>Ver secuencia de '+esc(g.id)+'</summary><p>'+g.trips.map(t=>esc(t.trip_id)).join(' → ')+'</p></details></li>').join('')+'</ul>';
}
export function preview(root,result,onOpen){
  root.innerHTML=heading('Vista rápida de despachos','Primeros cinco viajes por fecha de salida.')+'<div class="scheduling-table-scroll" role="region" tabindex="0" aria-label="Vista rápida desplazable"><table class="scheduling-table"><thead><tr>'+['Viaje','Destino','Vehículo','Despacho','Llegada','SLA'].map(s=>'<th scope="col">'+s+'</th>').join('')+'</tr></thead><tbody>'+getDispatchPreview(result).map(t=>'<tr><th scope="row">'+esc(t.trip_id)+'</th><td>'+esc(t.destination)+'</td><td>'+esc(t.vehicle_id)+'</td><td>'+date(t.dispatch_date)+'</td><td>'+date(t.arrival_date)+'</td><td>'+slaBadge(t.sla)+'</td></tr>').join('')+'</tbody></table></div><button type="button" class="d-button d-button--secondary" data-scheduling-full-plan>Ver plan completo '+icon('arrowRight')+'</button>';
  root.querySelector('button').onclick=onOpen;
}
