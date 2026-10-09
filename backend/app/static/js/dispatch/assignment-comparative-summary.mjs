import {esc,num,money,pct} from './shared.mjs';
import {
  getAssignmentSummary,
  getActiveObjectiveMetrics,
  getComparableScenarios,
  solverStatusLabel,
} from './assignment-dashboard-selectors.mjs?v=assignment-dashboard-phase3';

function formatMetric(key,value){
  if(value==null)return '—';
  if(key==='total_cost')return money(value);
  if(key==='own_weight_share')return pct(value);
  if(key==='co2_kg')return num(value,1)+' kg';
  return num(value);
}

function metricCard(key,label,value,active){
  return '<article class="assignment-comparative-summary__metric '+(active?'is-objective':'')+'">'
    +'<div><span>'+esc(label)+'</span>'+(active?'<em>Parte del objetivo</em>':'<em>KPI comparado</em>')+'</div>'
    +'<strong>'+esc(formatMetric(key,value))+'</strong>'
  +'</article>';
}

export function render(root,result){
  const summary=getAssignmentSummary(result);
  const selected=result?.scenarios?.selected||{};
  const metrics=selected.metrics||{};
  const active=new Set(getActiveObjectiveMetrics(result).map(item=>item.metric));
  const alternatives=getComparableScenarios(result);
  const referenceCount=result?.analysis?.scenario_count??alternatives.length;

  root.innerHTML=''
    +'<div class="assignment-comparative-summary">'
      +'<div class="assignment-comparative-summary__copy">'
        +'<span class="assignment-dashboard-v2__eyebrow">RECOMENDACIÓN COMPARATIVA</span>'
        +'<h1>Esta es la asignación recomendada para la prioridad configurada.</h1>'
        +'<p>La corrida expone <strong>'+esc(num(referenceCount))+' escenarios de referencia</strong> para contrastar la recomendación antes de aprobarla. Las alternativas se comparan por métricas; el detalle operativo permanece en la recomendación seleccionada.</p>'
        +'<div class="assignment-comparative-summary__status">'
          +'<span><small>Objetivo</small><strong>'+esc(summary.objectiveLabel)+'</strong></span>'
          +'<span><small>Estado del solver</small><strong>'+esc(solverStatusLabel(summary.solverStatus))+'</strong></span>'
          +'<span><small>Órdenes</small><strong>'+esc(num(summary.orders))+'</strong></span>'
        +'</div>'
      +'</div>'
      +'<aside class="assignment-comparative-summary__guide">'
        +'<span>Cómo leer esta pantalla</span>'
        +'<strong>Recomendación → alternativa → trade-offs</strong>'
        +'<p>Elegí una referencia, revisá qué mejora y qué cede la recomendación, y aprobá sólo después de validar la evidencia.</p>'
      +'</aside>'
    +'</div>'
    +'<div class="assignment-comparative-summary__metrics" aria-label="Métricas de la recomendación">'
      +metricCard('total_trips','Viajes',metrics.total_trips,active.has('total_trips'))
      +metricCard('total_cost','Costo estimado',metrics.total_cost,active.has('total_cost'))
      +metricCard('own_weight_share','Flota propia',metrics.own_weight_share,active.has('own_weight_share'))
      +metricCard('co2_kg','CO₂ estimado',metrics.co2_kg,active.has('co2_kg'))
    +'</div>';
}
