import {esc,api,post} from '../shared.mjs';
import {iconSvg} from '../decision-ui.mjs';
import {createScope} from '../lifecycle.mjs';
import {getExecutiveBrief,briefText} from '../assignment/assignment-dashboard-selectors.mjs';
const icon=name=>iconSvg(name,'scheduling-v2__icon');
const rich=value=>esc(value).replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replaceAll('\n','<br>');

function narrative(brief){
  const bullets=(title,items)=>items.length?'<h3>'+title+'</h3><ul>'+items.map(item=>'<li>'+rich(item)+'</li>').join('')+'</ul>':'';
  return '<span class="scheduling-ai-summary__badge">'+icon('sparkles')+'Generado por Dation IA</span>'
    +'<p class="scheduling-ai-summary__lead">'+rich(brief.lead)+'</p>'+(brief.why?'<p>'+rich(brief.why)+'</p>':'')
    +bullets('Ventajas principales',brief.drivers)+bullets('Trade-offs relevantes',brief.tradeoffs)+bullets('Qué conviene revisar',brief.review)
    +'<p class="scheduling-ai-summary__grounding">Basado en la evidencia de esta corrida. Dation IA interpreta la evidencia; no modifica el calendario ni la Assignment aprobada.</p>';
}

export function render(root,run){
  const scope=createScope(root),id='scheduling-ai-'+run.id;
  let cached=null,isCurrent=true,expanded=false,busy=false,brief=null,evidenceId=null,epoch=0,cacheVersion=0;
  root.dataset.aiSummaryState='empty';
  root.innerHTML='<div class="scheduling-ai-summary__heading"><div><span class="dispatch-kicker">DATION IA</span><h2>Insight IA</h2>'
    +'<p>Generá una lectura ejecutiva de la secuencia, el nivel de servicio y los principales condicionantes del calendario.</p><span data-ai-summary-availability role="status"></span></div>'
    +'<button type="button" class="d-button d-button--secondary" data-explain aria-expanded="false" aria-controls="'+esc(id)+'">'+icon('sparkles')+'Analizar con Dation IA</button></div>'
    +'<div id="'+esc(id)+'" data-ai-summary-body hidden><p data-ai-summary-freshness role="status" hidden>Hay evidencia más reciente. Actualizá el resumen para incluirla.</p>'
      +'<div data-response class="scheduling-ai-summary__narrative" aria-live="polite"></div>'
      +'<div class="scheduling-ai-summary__controls" data-ai-summary-controls hidden>'
        +'<button type="button" data-ai-regenerate>'+icon('refresh')+'Regenerar</button><button type="button" data-ai-copy>'+icon('copy')+'Copiar</button>'
        +'<button type="button" data-ai-ask>'+icon('sparkles')+'Seguir analizando con Dation IA →</button></div>'
      +'<p data-ai-summary-feedback role="status"></p><button type="button" data-ai-collapse>Contraer resumen '+icon('chevronDown')+'</button></div>';
  const button=root.querySelector('[data-explain]'),body=root.querySelector('[data-ai-summary-body]'),response=root.querySelector('[data-response]');
  const controls=root.querySelector('[data-ai-summary-controls]'),availability=root.querySelector('[data-ai-summary-availability]');
  const freshness=root.querySelector('[data-ai-summary-freshness]'),feedback=root.querySelector('[data-ai-summary-feedback]');
  function sync(){
    button.disabled=busy;button.setAttribute('aria-expanded',String(expanded));button.setAttribute('aria-busy',String(busy));body.hidden=!expanded;
    button.innerHTML=icon(busy?'loader':'sparkles')+(busy?'Analizando secuencia…':!isCurrent?'Actualizar resumen':cached?(expanded?'Resumen ejecutivo':'Ver resumen'):'Analizar con Dation IA');
    availability.textContent=!isCurrent?'Hay evidencia más reciente':cached?'Resumen disponible':'';
    freshness.hidden=isCurrent||!cached;controls.hidden=!brief;
    root.querySelector('[data-ai-regenerate]').disabled=busy;
  }
  async function restore(){
    const version=cacheVersion;
    try{
      const data=await api('/api/runs/'+run.id+'/interpretation',{signal:scope.signal});
      if(!scope.active||version!==cacheVersion)return;
      evidenceId=data.current_evidence_analysis_id||evidenceId;
      if(data.explanation?.response_json&&getExecutiveBrief(data.explanation.response_json).lead){
        cached=data.explanation.response_json;isCurrent=data.explanation_is_current!==false;
        if(!expanded&&!busy)root.dataset.aiSummaryState=isCurrent?'available':'stale';
      }
      sync();
    }catch{ /* A cache read failure still permits an explicit generation attempt. */ }
  }
  let restored=restore();
  scope.listen(window,'focus',()=>{if(cached&&!busy)restored=restore();});
  scope.listen(root,'dispatch:evidence-changed',()=>{if(!busy)restored=restore();});
  function show(data){
    const value=getExecutiveBrief(data);
    if(!value.lead)throw new Error('El servicio no devolvió un resumen ejecutivo. Podés reintentar.');
    brief=value;response.innerHTML=narrative(brief);root.dataset.aiSummaryState=isCurrent?'completed':'stale';
  }
  async function generate(force=false){
    if(busy||!scope.active)return;
    expanded=true;busy=true;feedback.textContent='';root.dataset.aiSummaryState='generating';
    response.innerHTML='<div class="scheduling-ai-summary__loading" role="status">'+icon('sparkles')+'<div><strong>Analizando secuencia, esperas y márgenes de servicio…</strong><p>Interpretando el calendario sin modificar la Assignment aprobada.</p></div></div>';sync();
    try{
      await restored;if(!scope.active)return;
      const version=epoch;
      const data=!force&&cached&&isCurrent?cached:await post('/api/runs/'+run.id+'/explain',undefined,{signal:scope.signal});
      if(!scope.active)return;
      isCurrent=version===epoch;show(data);cached=data;cacheVersion+=1;
    }catch(error){
      if(!scope.active)return;
      root.dataset.aiSummaryState='error';response.innerHTML='<p role="alert">'+esc(error.message||'No se pudo generar el resumen. Podés reintentar.')+'</p>';
      const retry=document.createElement('button');retry.type='button';retry.textContent='Reintentar resumen';retry.onclick=()=>generate(true);response.append(retry);
    }finally{if(scope.active){busy=false;sync();}}
  }
  button.onclick=()=>{if(cached&&isCurrent&&brief&&!busy){expanded=!expanded;sync();}else generate();};
  root.querySelector('[data-ai-regenerate]').onclick=()=>generate(true);
  root.querySelector('[data-ai-copy]').onclick=async()=>{
    try{await navigator.clipboard.writeText(briefText(brief));if(scope.active)feedback.textContent='Resumen copiado.';}
    catch{if(scope.active)feedback.textContent='No se pudo copiar el resumen. Podés seleccionar el texto y copiarlo.';}
  };
  root.querySelector('[data-ai-ask]').onclick=()=>root.dispatchEvent(new CustomEvent('dispatch:open-chat',{bubbles:true,detail:{question:''}}));
  root.querySelector('[data-ai-collapse]').onclick=()=>{expanded=false;sync();root.dispatchEvent(new CustomEvent('dispatch:close-insight',{bubbles:true}));};
  return {async evidenceChanged(artifact){
    await restored;
    if(!scope.active||!artifact?.id||artifact.id===evidenceId)return;
    epoch+=1;evidenceId=artifact.id;isCurrent=!cached;
    if(cached)root.dataset.aiSummaryState='stale';sync();restored=restore();
  }};
}
