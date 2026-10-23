import {esc,num,money,pct,chart,dispose} from '../shared.mjs';
import {createScope} from '../lifecycle.mjs';
import {chartPalette} from '../chart-theme.mjs';
import {getScenarioTable,getDecisionTradeoffs,getCorridorSummary,getTripUtilization,getDefaultComparisonKey,getAssignmentContext,getScenarioMetric} from './assignment-dashboard-selectors.mjs';
const title=(text,copy='')=>'<div class="assignment-v2__heading"><h2>'+esc(text)+'</h2>'+(copy?'<p>'+esc(copy)+'</p>':'')+'</div>';
const compact=value=>Math.abs(value)>=1e6?num(value/1e6,1)+' M':Math.abs(value)>=1e3?num(value/1e3,1)+' k':num(value,1);
function difference(row){
  const sign=row.absolute>0?'+':'−',value=Math.abs(row.absolute);
  return sign+(row.format==='money'?money(value):row.format==='percent'?num(value*100,1)+' pp':num(value,1))
    +(row.percent!==null&&row.format!=='percent'?' · '+(row.percent>0?'+':'−')+num(Math.abs(row.percent)*100,1)+' %':'');
}
function tradeoffs(root,result,key){
  const context=getDecisionTradeoffs(result,key);
  const column=(label,rows,className)=>'<section class="'+className+'"><h3>'+label+'</h3>'+(rows.length?'<ul>'+rows.map(row=>'<li><span>'+esc(row.label)+'</span><strong>'+esc(difference(row))+'</strong></li>').join('')+'</ul>':'<p>No hay diferencias comparables en esta categoría.</p>')+'</section>';
  root.innerHTML=title('Qué ganás / qué cedés',context.reference?'Recomendación frente a '+context.referenceLabel+'.':'No hay una referencia publicada para comparar.')
    +(context.samePlan?'<p>Misma distribución: no se atribuyen diferencias operativas a esta referencia.</p>':!context.feasible?'<p>La referencia no es factible. No se interpreta como una alternativa ejecutable.</p>':'<div class="assignment-tradeoffs__grid">'+column('Ganás',context.gains,'is-improvement')+column('Cedés',context.concessions,'is-tradeoff')+'</div>');
}
function utilization(root,result,sort='utilization'){
  const rows=getTripUtilization(result,sort);
  root.innerHTML=rows.length?'<ol class="assignment-utilization__list">'+rows.map(row=>'<li title="'+esc([row.trip_id,row.destination||'Destino no publicado',row.resource_id,pct(row.utilization)].join(' · '))+'">'
    +'<div><strong>'+esc(row.trip_id)+'</strong><span>'+esc(row.destination||'—')+' · '+esc(row.resource_id)+'</span><strong>'+pct(row.utilization)+'</strong></div>'
    +'<div class="assignment-resources__bar"><span style="width:'+Math.max(0,Math.min(100,(row.utilization??0)*100))+'%"></span></div></li>').join('')+'</ol>':'<p>No hay utilización por viaje publicada.</p>';
}
function corridors(root,result){
  const rows=getCorridorSummary(result),unit=getAssignmentContext(result).unitsLabel;
  root.innerHTML=title('Corredores','Agregación de los viajes seleccionados. El costo solo se suma cuando todos los viajes lo publican.')
    +'<div class="dispatch-table-wrap"><table class="assignment-v2__table"><thead><tr>'+['Origen','Destino','Carga','Cantidad ('+unit+')','Viajes','Vehículos','Utilización','Flota propia','Costo estimado'].map(label=>'<th scope="col">'+esc(label)+'</th>').join('')+'</tr></thead><tbody>'
    +rows.map(row=>'<tr><th scope="row">'+esc(row.origin||'—')+'</th><td>'+esc(row.destination||'—')+'</td><td>'+num(row.loadKg,1)+' kg</td><td>'+num(row.units,1)+'</td><td>'+num(row.trips)+'</td><td>'+num(row.vehicles)+'</td><td>'+pct(row.utilization)+'</td><td>'+pct(row.ownWeightShare)+'</td><td>'+money(row.cost)+'</td></tr>').join('')+'</tbody></table></div>';
}
function frontier(root,result){
  const rows=getScenarioTable(result).filter(row=>row.feasible&&row.values.total_cost!==null&&getScenarioMetric(row.scenario,'co2_kg')!==null);
  root.innerHTML=title('Frontera de decisión','Costo total frente a CO₂ estimado. El tamaño de cada punto representa los viajes; la recomendación se distingue por el contorno y la etiqueta.')
    +'<div class="dispatch-chart assignment-frontier__chart" role="img" aria-label="Escenarios factibles por costo total y CO₂, con la recomendación destacada"></div>'
    +'<p class="assignment-v2__note">Solo se grafican escenarios factibles con costo y CO₂ publicados.</p>'
    +'<details><summary>Datos de la frontera</summary><div class="dispatch-table-wrap"><table class="assignment-v2__table"><thead><tr><th scope="col">Escenario</th><th scope="col">Costo total</th><th scope="col">CO₂ estimado (kg)</th><th scope="col">Viajes</th></tr></thead><tbody>'
      +rows.map(row=>'<tr><th scope="row">'+esc(row.label)+(row.selected?' · Seleccionado':'')+'</th><td>'+money(row.values.total_cost)+'</td><td>'+num(getScenarioMetric(row.scenario,'co2_kg'),1)+'</td><td>'+num(row.values.total_trips)+'</td></tr>').join('')+'</tbody></table></div></details>';
  const node=root.querySelector('.dispatch-chart');
  if(!rows.length){node.textContent='No hay escenarios con costo y CO₂ publicados para representar.';return;}
  const palette=chartPalette(node),maxTrips=Math.max(1,...rows.map(row=>row.values.total_trips??0));
  const data=rows.map(row=>({name:row.label,selected:row.selected,metrics:row.values,
    value:[row.values.total_cost,getScenarioMetric(row.scenario,'co2_kg'),row.values.total_trips],
    symbolSize:row.values.total_trips===null?12:14+20*Math.sqrt(Math.max(0,row.values.total_trips)/maxTrips),
    itemStyle:{color:row.selected?palette.series[0]:palette.series[1],borderColor:row.selected?palette.text:palette.surface,borderWidth:row.selected?3:1},
    label:{show:row.selected,formatter:'Seleccionado',position:'top'},
  }));
  chart(node,{grid:{left:54,right:18,top:36,bottom:62},xAxis:{type:'value',name:'Costo total ($)',nameLocation:'middle',nameGap:35,axisLabel:{formatter:compact}},
    yAxis:{type:'value',name:'CO₂ (kg)',axisLabel:{formatter:compact}},
    tooltip:{trigger:'item',confine:true,formatter:params=>{const d=params.data,m=d.metrics;return '<strong>'+esc(d.name)+'</strong><br>Costo total: '+money(m.total_cost)+'<br>CO₂: '+num(d.value[1],1)+' kg<br>Viajes: '+num(m.total_trips)+'<br>Utilización: '+pct(m.load_utilization)+'<br>Flota propia: '+pct(m.own_weight_share);}},
    series:[{type:'scatter',data,emphasis:{scale:1.15}}]});
}
export function render(root,result){
  dispose(root);const scope=createScope(root);
  root.innerHTML='<section data-assignment-frontier></section><section data-assignment-tradeoffs></section>'
    +'<section>'+title('Utilización por viaje')+'<label class="assignment-utilization__sort">Ordenar por <select data-trip-sort><option value="utilization">Mayor utilización</option><option value="route">Destino</option><option value="trip">Viaje</option></select></label><div data-assignment-utilization></div></section>'
    +'<section data-assignment-corridors></section>'
    +(result.assumptions?.length?'<details class="dispatch-model-assumptions"><summary>Supuestos y límites del modelo</summary>'+result.assumptions.map(value=>'<p>'+esc(value)+'</p>').join('')+'</details>':'');
  frontier(root.querySelector('[data-assignment-frontier]'),result);
  const trade=root.querySelector('[data-assignment-tradeoffs]');tradeoffs(trade,result,getDefaultComparisonKey(result));
  const util=root.querySelector('[data-assignment-utilization]');utilization(util,result);
  scope.listen(root.querySelector('[data-trip-sort]'),'change',event=>utilization(util,result,event.currentTarget.value));
  corridors(root.querySelector('[data-assignment-corridors]'),result);
  return {setReference:key=>{if(scope.active)tradeoffs(trade,result,key);}};
}
