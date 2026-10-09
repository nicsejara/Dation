import {esc,num,money,pct} from './shared.mjs';
import {
  getAssignmentSummary,
  getOperationalKpis,
} from './assignment-dashboard-selectors.mjs?v=assignment-dashboard-phase2';

function formatKpi(item){
  if(item.value==null)return '—';
  if(item.format==='percent')return pct(item.value);
  if(item.format==='money')return money(item.value);
  if(item.format==='co2')return num(item.value,1)+' kg';
  return num(item.value);
}

function weightsMarkup(summary){
  if(!summary.objectiveWeights.length){
    return '<span class="assignment-essential__objective-chip">Sin ponderaciones publicadas</span>';
  }
  return summary.objectiveWeights.map(item=>
    '<span class="assignment-essential__objective-chip">'
      +'<strong>'+esc(item.label)+'</strong>'
      +'<small>'+pct(item.weight)+'</small>'
    +'</span>'
  ).join('');
}

function kpiMarkup(item){
  const secondary=item.secondaryValue==null
    ?''
    :'<small>'+esc(item.secondaryLabel||'Referencia')+' '+pct(item.secondaryValue)+'</small>';
  return '<article class="assignment-essential__kpi '+(item.objective?'is-objective':'is-descriptive')+'">'
    +'<div class="assignment-essential__kpi-top">'
      +'<span>'+esc(item.label)+'</span>'
      +'<em>'+(item.objective?'Parte del objetivo':'KPI del resultado')+'</em>'
    +'</div>'
    +'<strong>'+esc(formatKpi(item))+'</strong>'
    +secondary
  +'</article>';
}

export function render(root,result){
  const summary=getAssignmentSummary(result);
  const kpis=getOperationalKpis(result);

  root.innerHTML=
    '<div class="assignment-essential__summary">'
      +'<div class="assignment-essential__summary-copy">'
        +'<span class="dispatch-kicker">DECISIÓN 01 · ASIGNACIÓN DE CARGA</span>'
        +'<h1>'+num(summary.trips)+' viaje'+(summary.trips===1?'':'s')+' propuesto'+(summary.trips===1?'':'s')+' para distribuir '+num(summary.orders)+' orden'+(summary.orders===1?'':'es')+'</h1>'
        +'<p>Dation priorizó <strong>'+esc(summary.objectiveLabel)+'</strong> bajo la configuración persistida de esta corrida.</p>'
      +'</div>'
      +'<aside class="assignment-essential__objective" aria-label="Objetivo de la corrida">'
        +'<span>Objetivo de la corrida</span>'
        +'<strong>'+esc(summary.objectiveLabel)+'</strong>'
        +'<div class="assignment-essential__objective-chips">'+weightsMarkup(summary)+'</div>'
      +'</aside>'
    +'</div>'
    +'<div class="assignment-essential__kpi-strip" aria-label="Métricas de la asignación">'
      +kpis.map(kpiMarkup).join('')
    +'</div>'
    +'<p class="assignment-essential__metric-note">Las etiquetas <strong>Parte del objetivo</strong> indican métricas con ponderación activa en esta corrida. El resto describe el resultado y no se presenta como causa de la recomendación.</p>';
}
