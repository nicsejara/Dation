import {esc,num,money,pct} from './shared.mjs';
import {
  getComparisonContext,
  getDefaultComparisonKey,
} from './assignment-dashboard-selectors.mjs?v=assignment-dashboard-phase3';

function formatValue(row,value){
  if(value==null)return '—';
  if(row.format==='money')return money(value);
  if(row.format==='percent')return pct(value);
  if(row.format==='co2')return num(value,1)+' kg';
  if(row.format==='integer')return num(value);
  return num(value,2);
}

function signedNumber(value,digits=1){
  if(value==null)return '—';
  const sign=value>0?'+':value<0?'−':'';
  return sign+num(Math.abs(value),digits);
}

function formatDelta(row){
  if(row.semantic==='no_comparable')return '—';
  if(row.semantic==='same')return '0';
  if(row.format==='money'){
    const sign=row.absolute>0?'+':row.absolute<0?'−':'';
    const absolute=money(Math.abs(row.absolute)).replace('$ ','');
    const relative=row.percent==null?'':(' · '+signedNumber(row.percent*100,1)+' %');
    return sign+'$ '+absolute+relative;
  }
  if(row.format==='percent'){
    return signedNumber(row.absolute*100,1)+' pp';
  }
  if(row.format==='co2'){
    const relative=row.percent==null?'':(' · '+signedNumber(row.percent*100,1)+' %');
    return signedNumber(row.absolute,1)+' kg'+relative;
  }
  const relative=row.percent==null?'':(' · '+signedNumber(row.percent*100,1)+' %');
  return signedNumber(row.absolute,0)+relative;
}

function semanticClass(row){
  return {
    improvement:'is-improvement',
    tradeoff:'is-tradeoff',
    same:'is-same',
    no_comparable:'is-not-comparable',
  }[row.semantic]||'is-not-comparable';
}

function optionLabel(item){
  const suffix=[];
  if(item.samePlan)suffix.push('misma distribución');
  if(!item.feasible)suffix.push('no factible');
  return item.label+(suffix.length?' · '+suffix.join(' · '):'');
}

function stateMarkup(context){
  if(!context.reference){
    return '<div class="assignment-comparison__state is-empty"><strong>No hay escenarios comparables</strong><span>La corrida no publicó alternativas de referencia para esta decisión.</span></div>';
  }
  if(!context.feasible){
    return '<div class="assignment-comparison__state is-warning"><strong>Referencia no factible</strong><span>'+esc(context.referenceLabel)+' está marcada como no factible. Sus métricas se muestran como referencia, pero no se interpreta como alternativa ejecutable.</span></div>';
  }
  if(context.samePlan){
    return '<div class="assignment-comparison__state is-same"><strong>Misma distribución</strong><span>'+esc(context.referenceLabel)+' produce el mismo plan de asignación que la recomendación. No hay diferencias operativas que atribuir a esa referencia.</span></div>';
  }
  return '';
}

function metricCard(row,referenceLabel){
  const note=row.semantic==='no_comparable'&&row.reason
    ?'<small>'+esc(row.reason)+'</small>'
    :'<small>Recomendación frente a '+esc(referenceLabel)+'</small>';
  return '<article class="assignment-comparison__metric '+semanticClass(row)+'">'
    +'<header><span>'+esc(row.label)+'</span><em>'+esc(row.semanticLabel)+'</em></header>'
    +'<div class="assignment-comparison__metric-values">'
      +'<div><small>Recomendación</small><strong>'+esc(formatValue(row,row.selectedValue))+'</strong></div>'
      +'<span aria-hidden="true">→</span>'
      +'<div><small>'+esc(referenceLabel)+'</small><strong>'+esc(formatValue(row,row.referenceValue))+'</strong></div>'
    +'</div>'
    +'<div class="assignment-comparison__metric-delta"><strong>'+esc(formatDelta(row))+'</strong>'+note+'</div>'
  +'</article>';
}

function implicationText(row,referenceLabel){
  const selected=formatValue(row,row.selectedValue);
  const reference=formatValue(row,row.referenceValue);
  if(row.semantic==='improvement'){
    return '<li class="is-improvement"><span>'+esc(row.semanticLabel)+'</span><strong>'+esc(row.label)+'</strong><p>La recomendación queda en '+esc(selected)+' frente a '+esc(reference)+' de '+esc(referenceLabel)+'.</p></li>';
  }
  if(row.semantic==='tradeoff'){
    return '<li class="is-tradeoff"><span>'+esc(row.semanticLabel)+'</span><strong>'+esc(row.label)+'</strong><p>La recomendación cede en esta dimensión: '+esc(selected)+' frente a '+esc(reference)+' de '+esc(referenceLabel)+'.</p></li>';
  }
  if(row.semantic==='same'){
    return '<li class="is-same"><span>Sin cambio</span><strong>'+esc(row.label)+'</strong><p>Ambos escenarios publican '+esc(selected)+' en esta métrica.</p></li>';
  }
  return '<li class="is-not-comparable"><span>No comparable</span><strong>'+esc(row.label)+'</strong><p>'+esc(row.reason||'No hay datos comparables publicados para esta métrica.')+'</p></li>';
}

function prioritiesMarkup(context){
  const priorities=context.priorities||[];
  const priorityHtml=priorities.length
    ?priorities.map(item=>'<div class="assignment-comparison__priority"><span>'+esc(item.label)+'</span><strong>'+esc(num(item.weight*100,0))+' %</strong></div>').join('')
    :'<div class="assignment-comparison__priority is-empty"><span>Configuración</span><strong>Sin ponderaciones publicadas</strong></div>';

  return '<section class="assignment-comparison__implications">'
    +'<div class="assignment-comparison__implications-head">'
      +'<span class="assignment-dashboard-v2__eyebrow">LECTURA DE LA ELECCIÓN</span>'
      +'<h3>Prioridades configuradas → Qué implicó la elección</h3>'
      +'<p>La relación se muestra con datos persistidos de la corrida. No se atribuye causalidad a métricas que no formaron parte del objetivo.</p>'
    +'</div>'
    +'<div class="assignment-comparison__implications-grid">'
      +'<div class="assignment-comparison__priorities"><h4>Prioridades configuradas</h4>'+priorityHtml+'</div>'
      +'<div class="assignment-comparison__outcomes"><h4>Frente a '+esc(context.referenceLabel)+'</h4><ul>'+context.rows.map(row=>implicationText(row,context.referenceLabel)).join('')+'</ul></div>'
    +'</div>'
  +'</section>';
}

function comparisonBody(context){
  if(!context.reference){
    return stateMarkup(context);
  }
  return stateMarkup(context)
    +'<div class="assignment-comparison__metrics">'
      +context.rows.map(row=>metricCard(row,context.referenceLabel)).join('')
    +'</div>'
    +prioritiesMarkup(context);
}

export function render(root,result){
  const initialKey=getDefaultComparisonKey(result);
  const initial=getComparisonContext(result,initialKey);

  root.innerHTML=''
    +'<div class="assignment-comparison__heading">'
      +'<div>'
        +'<span class="assignment-dashboard-v2__eyebrow">RECOMENDACIÓN VS ALTERNATIVAS</span>'
        +'<h2>Compará la recomendación antes de aprobarla</h2>'
        +'<p>Cada alternativa conserva únicamente métricas agregadas. El detalle de viajes y órdenes pertenece a la recomendación seleccionada y no se reconstruye para escenarios de referencia.</p>'
      +'</div>'
      +'<label class="assignment-comparison__selector">'
        +'<span>Comparar contra</span>'
        +'<select data-comparison-select '+(initial.alternatives.length?'':'disabled')+'>'
          +initial.alternatives.map(item=>'<option value="'+esc(item.key)+'">'+esc(optionLabel(item))+'</option>').join('')
        +'</select>'
      +'</label>'
    +'</div>'
    +'<div class="assignment-comparison__legend" aria-label="Significado de estados">'
      +'<span class="is-improvement">Mejora</span>'
      +'<span class="is-tradeoff">Trade-off</span>'
      +'<span class="is-same">Sin cambio</span>'
      +'<span class="is-not-comparable">No comparable</span>'
    +'</div>'
    +'<div data-comparison-body>'+comparisonBody(initial)+'</div>';

  const select=root.querySelector('[data-comparison-select]');
  const body=root.querySelector('[data-comparison-body]');
  if(!select||!body||!initial.alternatives.length)return;
  if(initial.key)select.value=initial.key;

  select.addEventListener('change',()=>{
    const context=getComparisonContext(result,select.value);
    body.innerHTML=comparisonBody(context);
  });
}
