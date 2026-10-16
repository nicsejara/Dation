import {iconSvg} from "./decision-ui.mjs";
import {createScope} from './lifecycle.mjs';
import {api,post,esc} from './shared.mjs';
import {getAnalysisDepth,getComparableScenarios} from './assignment-dashboard-selectors.mjs';
import * as summary from './assignment-comparative-summary.mjs';
import * as comparison from './assignment-comparison.mjs';

export function render(root,run,{onEvidenceReady,onReady,onStateChange,inline=false}={}){
  const scope=createScope(root);
  let artifact={status:'available'};
  let timer=null;
  let runningRequest=false;
  let notified=false;
  let needsRefresh=false;
  let deferredGenerate=false,lastReady=null;
  const visibilityKey='dation.comparative.collapsed.'+run.id;
  let collapsed=false;
  try{collapsed=!inline&&sessionStorage.getItem(visibilityKey)==='true';}catch{}
  scope.own(()=>clearTimeout(timer));
  const endpoint='/api/runs/'+run.id+'/comparative';

  function completed(){
    const contentId='comparative-content-'+run.id;
    if(collapsed){
      root.innerHTML='<div class="assignment-comparative-layer__collapsed"><strong>Análisis comparativo disponible</strong><button type="button" data-open-comparative aria-expanded="false" aria-controls="'+esc(contentId)+'">Ver análisis</button></div><div id="'+esc(contentId)+'" hidden></div>';
      root.querySelector('[data-open-comparative]').onclick=()=>setCollapsed(false);
    }else{
      root.innerHTML='<div class="assignment-comparative-layer__header"><div data-comparative-summary></div>'+(inline?'':'<button type="button" data-close-comparative aria-label="Cerrar análisis comparativo" aria-expanded="true" aria-controls="'+esc(contentId)+'">Cerrar '+iconSvg("x","dispatch-action-icon")+'</button>')+'</div><div id="'+esc(contentId)+'" data-comparative-content></div>';
      summary.render(root.querySelector('[data-comparative-summary]'),artifact.result_json);
      comparison.render(root.querySelector('[data-comparative-content]'),artifact.result_json);
      const close=root.querySelector('[data-close-comparative]');if(close)close.onclick=()=>setCollapsed(true);
    }
    if(lastReady!==artifact.result_json){lastReady=artifact.result_json;onReady?.(artifact);}
    if(needsRefresh&&!notified){notified=true;onEvidenceReady?.(artifact);}
  }
  function setCollapsed(value){
    if(!scope.active)return;
    collapsed=value;
    try{sessionStorage.setItem(visibilityKey,String(value));}catch{}
    completed();root.querySelector(value?'[data-open-comparative]':'[data-close-comparative]')?.focus({preventScroll:true});
  }

  function draw(){
    if(!scope.active)return;
    root.dataset.comparativeState=artifact.status;
    onStateChange?.(artifact.status);
    if(artifact.status==='completed')return completed();
    const busy=['queued','running','submitting'].includes(artifact.status);
    root.innerHTML='<div class="assignment-comparative-layer__intro">'
      +'<span class="assignment-dashboard-v2__eyebrow">ANÁLISIS COMPARATIVO</span><h2>Profundizá el análisis</h2>'
      +'<p>La decisión ya está resuelta. Generá un análisis comparativo para evaluar escenarios alternativos y entender qué cambia cuando varían los criterios.</p>'
      +(busy?'<div class="assignment-comparative-layer__loading"><span class="dispatch-loading" aria-hidden="true"></span><p role="status">'+(artifact.status==='queued'?'El análisis está en cola…':'Generando escenarios comparativos…')+'</p></div>'
        :'<button type="button" data-generate-comparative>'+(artifact.status==='error'?'Reintentar':'Generar análisis comparativo')+'</button>')
      +(artifact.status==='error'?'<p role="alert">'+esc(artifact.error_message||'No se pudo recuperar el comparativo. Tu asignación sigue disponible.')+'</p>':'')+'</div>';
    root.querySelector('[data-generate-comparative]')?.addEventListener('click',generate);
  }

  function schedule(){
    clearTimeout(timer);
    if(scope.active&&['queued','running'].includes(artifact.status))timer=setTimeout(restore,1500);
  }

  async function restore(){
    if(!scope.active||runningRequest)return;
    runningRequest=true;
    try{
      const data=await api(endpoint,{signal:scope.signal});
      if(!scope.active)return;
      if(['queued','running'].includes(data.status))needsRefresh=true;
      artifact=data;draw();schedule();
    }catch(error){
      if(scope.active){artifact={status:'error',error_message:error.message};draw();}
    }finally{runningRequest=false;if(deferredGenerate&&scope.active&&!['completed','queued','running'].includes(artifact.status)){deferredGenerate=false;generate();}}
  }

  async function generate(){
    if(runningRequest){if(['available','error'].includes(artifact.status))deferredGenerate=true;return;}
    runningRequest=true;
    needsRefresh=true;
    const retry=artifact.status==='error';
    artifact={status:'submitting'};draw();
    try{
      const data=await post(endpoint+(retry?'?retry=true':''),undefined,{signal:scope.signal});
      if(!scope.active)return;
      artifact=data;draw();schedule();
    }catch(error){
      if(scope.active){artifact={status:'error',error_message:error.message};draw();}
    }finally{runningRequest=false;}
  }

  if(getAnalysisDepth(run)!=='essential'&&getComparableScenarios(run.result_json).length){
    artifact={status:'completed',source_mode:'original',result_json:run.result_json};draw();
  }else{
    draw();restore();
  }
  return {generate,restore};
}
