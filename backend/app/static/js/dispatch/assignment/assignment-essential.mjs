import {esc,num,money,pct} from '../shared.mjs';
import {iconSvg} from '../decision-ui.mjs';
import {formatWeight} from './assignment-summary.mjs';
import {getAssignmentContext,getEssentialKpis,getDecisionInsights,getScenarioTable,getResourceParticipation,getAssignmentPreview,getAssignmentSummary} from './assignment-dashboard-selectors.mjs';
const icon=name=>iconSvg(name,'assignment-v2__icon');
export const formatMetric=item=>item.value==null?'—':item.format==='money'?money(item.value):item.format==='percent'?pct(item.value):num(item.value,1);
const heading=(title,copy='')=>'<div class="assignment-v2__heading"><h2>'+esc(title)+'</h2>'+(copy?'<p>'+esc(copy)+'</p>':'')+'</div>';

export function context(root,result){
  const ctx=getAssignmentContext(result);
  const cards=[['clipboardList','Órdenes',num(ctx.orders),'Órdenes incluidas'],['weight','Carga total',formatWeight(ctx.totalWeightKg),'Volumen total asignado'],
    ['mapPin','Destinos',num(ctx.destinations),'Destinos incluidos'],['truck','Vehículos evaluados',num(ctx.evaluatedVehicles),'Recursos considerados']];
  root.innerHTML=heading('Contexto')+'<div class="assignment-context__grid">'+cards.map(([name,label,value,copy])=>
    '<article>'+icon(name)+'<div><small>'+esc(label)+'</small><strong>'+esc(value)+'</strong><span>'+esc(copy)+'</span></div></article>').join('')+'</div>';
}
export function kpis(root,result){
  root.innerHTML=heading('Indicadores de la asignación')+'<div class="assignment-essential__kpi-strip">'+getEssentialKpis(result).map(item=>
    '<article data-executive-kpi="'+esc(item.key)+'" class="assignment-essential__kpi '+(item.objective?'is-objective':'is-descriptive')+'">'
      +'<div class="assignment-essential__kpi-top">'+icon(item.icon)+'<span>'+esc(item.label)+'</span></div>'
      +'<strong>'+esc(formatMetric(item))+'</strong><p>'+esc(item.description)+'</p></article>').join('')+'</div>';
}
export function insights(root,result){
  root.innerHTML=heading('¿Qué decidió Dation?')+'<div class="assignment-insights__grid">'+getDecisionInsights(result).map(item=>
    '<article>'+icon(item.icon)+'<h3>'+esc(item.title)+'</h3><p>'+(item.metric==null?'':'<strong>'+pct(item.metric)+'</strong> ')+esc(item.detail)+'</p></article>').join('')
    +'</div><p class="assignment-insights__summary"><strong>En resumen:</strong> La recomendación responde a '+esc(getAssignmentSummary(result).objectiveLabel.toLocaleLowerCase('es'))+' con los recursos y restricciones de esta corrida.</p>';
}
export function scenarios(root,result,{onGenerate,state='available'}={}){
  const rows=getScenarioTable(result),busy=['queued','running','submitting'].includes(state);
  root.innerHTML=heading('Comparación de escenarios','La selección corresponde a la decisión del motor. Las alternativas se muestran como referencia.')
    +'<div class="dispatch-table-wrap assignment-scenarios__scroll"><table class="assignment-v2__table"><caption class="sr-only">Escenarios publicados de esta corrida</caption>'
    +'<thead><tr><th scope="col">Escenario</th><th scope="col" class="d-number">Costo total</th><th scope="col" class="d-number">Viajes</th><th scope="col" class="d-number">Utilización</th><th scope="col" class="d-number">Flota propia</th></tr></thead><tbody>'
    +rows.map(row=>'<tr data-scenario-row="'+esc(row.key)+'"'+(row.selected?' class="is-selected" aria-current="true"':'')+'><th scope="row">'
      +(row.selected?icon('checkCircle'):'')+esc(row.label)+'<span class="assignment-scenarios__badge">'+(row.selected?'Seleccionado':!row.feasible?'No factible':row.samePlan?'Misma distribución':'Referencia')+'</span>'
      +(row.selected&&!row.feasible?'<span class="assignment-scenarios__badge is-warning">No factible</span>':'')+'</th>'
      +['total_cost','total_trips','load_utilization','own_weight_share'].map(key=>'<td class="d-number">'+esc(formatMetric({value:row.values[key],format:key==='total_cost'?'money':['load_utilization','own_weight_share'].includes(key)?'percent':'number'}))+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>'
    +(rows.length===1?'<div class="assignment-scenarios__available"><p>'+(busy?'Generando evidencia comparativa…':'Podés generar escenarios adicionales sin modificar la recomendación.')+'</p>'
      +'<button type="button" class="d-button d-button--secondary" data-essential-comparative '+(busy?'disabled aria-busy="true"':'')+'>'+icon('chartBar')+(state==='error'?'Reintentar comparación':'Generar comparación')+'</button></div>':'');
  root.querySelector('[data-essential-comparative]')?.addEventListener('click',()=>onGenerate?.());
}
export function resources(root,result){
  const rows=getResourceParticipation(result),top=rows[0];
  root.innerHTML=heading('Cómo se ejecuta la recomendación','Participación de cada recurso en los viajes publicados.')
    +(rows.length?'<ol class="assignment-resources__list">'+rows.map(item=>'<li><div><strong>'+esc(item.id)+'</strong><span>'+num(item.trips)+' viajes</span><strong>'+pct(item.tripShare)+'</strong></div>'
      +'<div class="assignment-resources__bar" role="img" aria-label="'+esc(item.id+': '+pct(item.tripShare)+' de los viajes')+'"><span style="width:'+Math.min(100,item.tripShare*100)+'%"></span></div></li>').join('')+'</ol>'
      :'<p>No hay detalle de recursos publicado.</p>')
    +(top?.concentrated?'<p class="assignment-resources__continuity">'+icon('info')+'<span>'+esc(top.id)+' concentra '+num(top.trips)+' de '+num(top.totalTrips)+' viajes. Su disponibilidad temporal se evaluará en Planificación.</span></p>':'');
}
export function preview(root,result,{onOpen}={}){
  const rows=getAssignmentPreview(result);
  root.innerHTML=heading('Vista rápida de asignaciones','Hasta cinco viajes de la recomendación seleccionada.')
    +'<div class="dispatch-table-wrap"><table class="assignment-v2__table"><thead><tr><th scope="col">Viaje</th><th scope="col">Destino</th><th scope="col">Vehículo</th><th scope="col" class="d-number">Carga</th><th scope="col" class="d-number">Utilización</th></tr></thead><tbody>'
    +rows.map(row=>'<tr><th scope="row">'+esc(row.trip_id)+'</th><td>'+esc(row.destination||'—')+'</td><td>'+esc(row.resource_id)+'</td><td class="d-number">'+esc(formatWeight(row.load_kg,true))+'</td><td class="d-number">'+pct(row.utilization)+'</td></tr>').join('')
    +'</tbody></table></div>'+(rows.length?'':'<p>No hay viajes publicados.</p>')
    +'<button type="button" class="d-button d-button--secondary" data-assignment-full-plan>Ver detalle completo '+icon('arrowRight')+'</button>';
  root.querySelector('[data-assignment-full-plan]').onclick=()=>onOpen?.();
}
