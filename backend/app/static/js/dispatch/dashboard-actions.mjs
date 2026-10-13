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
  async function refresh(){
    retry.hidden=true;
    if(!button)return;
    button.hidden=true;
    if(message)message.textContent='';
    try{
      const next=await caseActions.getContinuation?.();
      if(!scope?.active)return;
      if(next?.state==='available'){
        button.textContent=next.label;
        button.hidden=false;
      }else if(message&&next?.message){
        message.textContent=next.message;
      }
    }catch{
      if(scope?.active&&message){message.textContent='No se pudo comprobar la siguiente decisión.';retry.hidden=false;}
    }
  }
  if(button)button.onclick=async()=>{
    button.disabled=true;
    let failure=null;
    try{
      await caseActions.onContinue?.();
    }catch(error){
      failure=error;
    }finally{
      if(scope?.active){
        button.disabled=false;await refresh();
        if(failure&&scope.active&&message){message.textContent=failure.message;retry.hidden=false;}
      }
    }
  };
  refresh();
  return {refresh};
}
