import {esc,num,money,pct} from '../shared.mjs';
import {createScope} from '../lifecycle.mjs';
import {
  getComparisonContext,
  getDefaultComparisonKey,
} from './assignment-dashboard-selectors.mjs';

function formatValue(row,value){
  if(value==null)return '—';
  if(row.format==='money')return money(value);
  if(row.format==='percent')return pct(value);
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
  if(row.format==='money'){
    const sign=row.absolute>0?'+':row.absolute<0?'−':'';
    const absolute=money(Math.abs(row.absolute)).replace('$ ','');
    const relative=row.percent==null?'':(' · '+signedNumber(row.percent*100,1)+' %');
    return sign+'$ '+absolute+relative;
  }
  if(row.format==='percent'){
    return signedNumber(row.absolute*100,1)+' pp';
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
  return '<article data-comparison-kpi="'+esc(row.key)+'" class="assignment-comparison__metric '+semanticClass(row)+'">'
    +'<header><span'+(row.description?' title="'+esc(row.description)+'" aria-label="'+esc(row.label+' · '+row.description)+'"':'')+'>'+esc(row.label)+'</span><em>'+esc(row.semanticLabel)+'</em></header>'
    +'<div class="assignment-comparison__metric-values">'
      +'<div><small>Recomendación</small><strong>'+esc(formatValue(row,row.selectedValue))+'</strong></div>'
      +'<span aria-hidden="true">→</span>'
      +'<div><small>'+esc(referenceLabel)+'</small><strong>'+esc(formatValue(row,row.referenceValue))+'</strong></div>'
    +'</div>'
    +'<div class="assignment-comparison__metric-delta"><strong>'+esc(formatDelta(row))+'</strong>'+note+'</div>'
  +'</article>';
}

function comparisonBody(context){
  if(!context.reference){
    return stateMarkup(context);
  }
  return stateMarkup(context)
    +'<div class="assignment-comparison__metrics">'
      +context.rows.map(row=>metricCard(row,context.referenceLabel)).join('')
    +'</div>';
}

export function render(root,result){
  const scope=createScope(root);
  const initialKey=getDefaultComparisonKey(result);
  const initial=getComparisonContext(result,initialKey);

  root.innerHTML=''
    +'<div class="assignment-comparison__heading">'
      +'<label class="assignment-comparison__selector">'
        +'<span>Comparar contra</span>'
        +'<select data-comparison-select '+(initial.alternatives.length?'':'disabled')+'>'
          +initial.alternatives.map(item=>'<option value="'+esc(item.key)+'">'+esc(optionLabel(item))+'</option>').join('')
        +'</select>'
      +'</label>'
    +'</div>'
    +'<div data-comparison-body>'+comparisonBody(initial)+'</div>';

  const select=root.querySelector('[data-comparison-select]');
  const body=root.querySelector('[data-comparison-body]');
  if(!select||!body||!initial.alternatives.length)return;
  if(initial.key)select.value=initial.key;

  scope.listen(select,'change',()=>{
    const context=getComparisonContext(result,select.value);
    body.innerHTML=comparisonBody(context);
    root.dispatchEvent(new CustomEvent('assignment:reference-changed',{bubbles:true,detail:{key:context.key}}));
  });
}
