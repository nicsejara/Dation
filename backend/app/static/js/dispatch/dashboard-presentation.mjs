import {scopeFor} from './lifecycle.mjs';
import {iconSvg} from './decision-ui.mjs';
import {esc} from './shared.mjs';

/** Shared capability shell. All evidence remains owned by its decision module. */
export function renderDecisionIntelligence({kind,id,advancedMarkup=''}){
  const assignment=kind==='assignment';
  const preview=assignment?'Comparación · Utilización · Asignaciones · Corredores · Plan completo':'Timeline · Simultaneidad · Utilización temporal · SLA · Plan detallado';
  return '<section class="decision-intelligence" aria-labelledby="'+esc(id)+'-intelligence">'
    +'<header><h2 id="'+esc(id)+'-intelligence">DECISION INTELLIGENCE</h2><p>Profundizá la recomendación con explicación asistida y evidencia detallada.</p></header>'
    +'<div class="decision-intelligence__capabilities" role="group" aria-label="Profundizar la recomendación">'
      +'<button type="button" class="decision-intelligence__capability" data-insight-toggle aria-expanded="false" aria-controls="dispatch-explanation">'+iconSvg('sparkles','dispatch-action-icon')+'<strong>Insight IA</strong><span>Lectura ejecutiva, drivers y puntos a revisar de esta corrida.</span><small>Resumen · Drivers · Puntos a revisar</small><b>Ver análisis completo →</b></button>'
      +'<button type="button" class="decision-intelligence__capability" data-'+kind+'-advanced-toggle aria-expanded="false" aria-controls="'+esc(id)+'-content">'+iconSvg('chartBar','dispatch-action-icon')+'<strong>Análisis avanzado</strong><span>Explorá la evidencia detrás de la recomendación.</span><small>'+preview+'</small><b>Explorar →</b></button>'
    +'</div>'
    +'<section class="dispatch-panel '+kind+'-ai-summary decision-intelligence__content" id="dispatch-explanation" tabindex="-1" hidden></section>'
    +'<section class="dispatch-panel '+kind+'-advanced decision-intelligence__content" data-'+kind+'-advanced hidden tabindex="-1" aria-label="Análisis avanzado">'
      +'<h3>Análisis avanzado</h3><div id="'+esc(id)+'-content" data-'+kind+'-advanced-content hidden>'+advancedMarkup+'</div>'
    +'</section></section>';
}

export function bindDashboardPresentation(root,{advanced,toggle,content,storageKey,onAdvancedOpen}){
  const scope=scopeFor(root),insight=root.querySelector('#dispatch-explanation'),insightToggle=root.querySelector('[data-insight-toggle]');
  let selected=null;
  function select(value,{target,scroll=false}={}){
    const previous=selected;selected=value;
    const open=selected==='advanced',showInsight=selected==='insight';
    root.dataset.visualDepth=open?'advanced':'essential';
    toggle.setAttribute('aria-expanded',String(open));toggle.classList.toggle('is-selected',open);
    insightToggle.setAttribute('aria-expanded',String(showInsight));insightToggle.classList.toggle('is-selected',showInsight);
    content.hidden=!open;advanced.hidden=!open;advanced.classList.toggle('is-open',open);insight.hidden=!showInsight;
    try{sessionStorage.setItem(storageKey,open?'advanced':'essential');}catch{}
    if(open&&previous!=='advanced')onAdvancedOpen?.();
    if(showInsight&&insight.querySelector('[data-ai-summary-body]')?.hidden)insight.querySelector('[data-explain]')?.click();
    if(open&&scroll)scope.timeout(()=>{
      const node=typeof target==='string'?content.querySelector(target):target;
      (node||advanced).scrollIntoView({block:'start',behavior:'instant'});
      (node||advanced).focus({preventScroll:true});
    },0);
  }
  scope.listen(toggle,'click',()=>select(selected==='advanced'?null:'advanced'));
  scope.listen(insightToggle,'click',()=>select(selected==='insight'?null:'insight'));
  scope.listen(root,'dispatch:close-insight',()=>{select(null);insightToggle.focus({preventScroll:true});});
  let restored=false;
  try{restored=sessionStorage.getItem(storageKey)==='advanced';}catch{}
  select(restored?'advanced':null);
  return {openAdvanced:target=>select('advanced',{target,scroll:true})};
}
