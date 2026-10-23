import {dispose,errorBox} from '../shared.mjs';
import {scopeFor,disposeScope} from '../lifecycle.mjs';
import {renderSchedulingShell,bindSchedulingShell} from './scheduling-dashboard-shell.mjs';
import * as essential from './scheduling-essential.mjs';
import {renderEssentialTimeline} from './scheduling-timeline.mjs';
import {renderSchedulingAdvanced} from './scheduling-advanced.mjs';
import * as validation from './scheduling-validation.mjs';
import * as aiSummary from './scheduling-ai-summary.mjs';
import * as explanation from '../explanation.mjs';
import {getSchedulingWarnings} from './scheduling-dashboard-selectors.mjs';

export function render(root,run,onRerun,caseActions={}){
  dispose(root);
  const result=run.result_json,warnings=getSchedulingWarnings(result),blocked=warnings.some(w=>w.severity==='critical');
  const actions={...caseActions,approvalBlocked:Boolean(caseActions.approvalBlocked)||blocked||caseActions.status==='stale',onApprovalComplete:async()=>{
    const status=root.querySelector('[data-scheduling-hero-status]');
    if(status){status.className='scheduling-status is-good';status.textContent='Planificación aprobada';}
    await caseActions.onApprovalComplete?.();
  }};
  const nodes=renderSchedulingShell(root,run,actions),scope=scopeFor(root);
  const safe=(node,draw)=>{try{draw();}catch(error){errorBox(node,error,()=>safe(node,draw));}};
  if(blocked){
    root.dataset.schedulingState='infeasible';validation.renderUnavailable(nodes.hero,result);
    for(const name of ['context','kpis','insights','timeline','resources','preview','ai'])nodes[name].hidden=true;
    nodes.resources.parentElement.hidden=true;root.querySelector('[data-scheduling-advanced]').hidden=true;
  }else{
    root.dataset.schedulingState=caseActions.status||'completed';
    safe(nodes.hero,()=>essential.hero(nodes.hero,result,caseActions));
    for(const name of ['context','kpis','insights','resources'])safe(nodes[name],()=>essential[name](nodes[name],result));
    safe(nodes.timeline,()=>renderEssentialTimeline(nodes.timeline,result));
    safe(nodes.ai,()=>aiSummary.render(nodes.ai,run));
  }
  validation.render(nodes.validation,result);
  function toggleChat(question=''){
    const button=root.querySelector('[data-chat]');
    if(question||nodes.chat.hidden){nodes.chat.hidden=false;root.classList.add('with-chat');button.setAttribute('aria-expanded','true');explanation.chat(nodes.chat,run,question);}
    else{disposeScope(nodes.chat);nodes.chat.hidden=true;root.classList.remove('with-chat');button.setAttribute('aria-expanded','false');}
  }
  scope.listen(root,'dispatch:open-chat',event=>{nodes.chat.hidden=true;toggleChat(event.detail?.question||'');});
  let advancedDrawn=false;
  const shell=bindSchedulingShell(root,run,{onRerun,caseActions:actions,onOpenChat:()=>toggleChat(),onAdvancedOpen:()=>{
    if(blocked)return;
    if(!advancedDrawn){safe(nodes.advanced,()=>renderSchedulingAdvanced(nodes.advanced,result));advancedDrawn=true;}
    else nodes.advanced.querySelectorAll('.dispatch-chart').forEach(node=>window.DationCharts?.getInstanceByDom(node)?.resize());
  }});
  if(!blocked)essential.preview(nodes.preview,result,()=>shell.openAdvanced('#scheduling-full-plan'));
}
