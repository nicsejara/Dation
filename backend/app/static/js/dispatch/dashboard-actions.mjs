import {workflowActionLabel,WORKFLOW_ACTION_CLASS} from "./workflow-action-bar.mjs";
import {scopeFor} from './lifecycle.mjs';

// Resolve again after approval and immediately before navigating; state is owned by the workspace.
export function bindDashboardActions(root,caseActions={}){
  const scope=scopeFor(root);
  root.querySelectorAll('[data-new-decision]').forEach(button=>{
    button.onclick=()=>caseActions.onNewDecision?.();
  });
  const button=root.querySelector('[data-after-approve]');
  const message=root.querySelector('[data-next-decision-status]');
  const retry=document.createElement('button');retry.type='button';retry.hidden=true;retry.textContent='Reintentar comprobación';
  message?.after(retry);retry.onclick=()=>refresh();
  const map=document.createElement('button');map.type='button';map.className=WORKFLOW_ACTION_CLASS+' d-button--secondary';map.dataset.approvedMap='';map.hidden=true;
  scope?.listen(map,'click',()=>caseActions.onMap?.());button?.after(map);
  let generation=0;
  async function refresh(){
    const own=++generation;
    retry.hidden=true;
    if(!button)return;
    button.hidden=true;
    map.hidden=true;
    if(message)message.textContent='';
    try{
      const next=await caseActions.getContinuation?.();
      if(!scope?.active||own!==generation)return;
      if(next){
        const completed=next.state==='completed';
        root.querySelectorAll('[data-approve-final]').forEach(approve=>{approve.hidden=true;});
        button.innerHTML=workflowActionLabel(completed?'Volver a Decision Center':'Configurar siguiente decisión');
        button.hidden=!completed&&next.target?.view!=='logistics-config';
        map.hidden=!caseActions.onMap;map.textContent=completed?'Ver mapa del Case':'Ver mapa de decisiones';
        if(message)message.textContent=completed?next.message:'✓ Decisión aprobada'+(next.target?'':' · '+(next.message||'Consultá el mapa para continuar.'));
      }
    }catch{
      if(scope?.active&&message){message.textContent='No se pudo comprobar la siguiente decisión.';retry.hidden=false;}
    }
  }
  if(button)button.onclick=async()=>{
    button.disabled=true;
    button.setAttribute('aria-busy','true');
    let failure=null;
    try{
      await caseActions.onContinue?.();
    }catch(error){
      failure=error;
    }finally{
      if(scope?.active){
        button.disabled=false;button.removeAttribute('aria-busy');await refresh();
        if(failure&&scope.active&&message){message.textContent=failure.message;retry.hidden=false;}
      }
    }
  };
  refresh();
  return {refresh};
}
