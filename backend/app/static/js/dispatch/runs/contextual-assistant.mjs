import {iconSvg} from '../decision-ui.mjs';
import {esc} from '../shared.mjs';
import {scopeFor} from '../lifecycle.mjs';

export function renderAssistantLauncher(run){
  return '<button type="button" class="d-button d-button--primary dispatch-ai-fab" data-chat aria-expanded="false" aria-haspopup="dialog" aria-controls="assistant-'+esc(run.id)+'" aria-label="Abrir Dation IA">'+iconSvg('sparkles','dispatch-action-icon')+'<span data-assistant-label>Dation IA</span></button>';
}

/** Presentation only. The dashboard continues to own the existing chat callbacks. */
export function bindAssistantLauncher(root,onOpen,{avoidSelector=null}={}){
  const scope=scopeFor(root),button=root.querySelector('[data-chat]');
  scope.listen(button,'click',onOpen);
  scope.listen(root,'dispatch:assistant-busy',event=>{
    button.querySelector('[data-assistant-label]').textContent=event.detail.busy?'Analizando…':'Dation IA';
    button.setAttribute('aria-label',event.detail.busy?'Dation IA · Analizando…':'Abrir Dation IA');
  });
  function layout(){
    const viewport=window.visualViewport;
    const keyboard=Math.max(0,innerHeight-(viewport?.height||innerHeight)-(viewport?.offsetTop||0));
    let bottom=24+keyboard;
    const field=document.activeElement;
    if(field&&field!==button&&root.contains(field)&&!field.closest('.dispatch-chat')){
      const r=field.getBoundingClientRect(),b=button.getBoundingClientRect();
      if(r.right>b.left-12&&r.left<b.right+12&&r.bottom>innerHeight-bottom-b.height-12&&r.top<innerHeight-bottom+12){
        bottom=Math.min(innerHeight-b.height-12,Math.max(bottom,innerHeight-r.top+12));
      }
    }
    if(avoidSelector){
      const bounds=[...root.querySelectorAll(avoidSelector)].map(node=>node.getBoundingClientRect()).filter(r=>r.width&&r.height&&r.bottom>0&&r.top<innerHeight);
      const fab=button.getBoundingClientRect();
      if(bounds.some(r=>r.right>fab.left-12&&r.left<fab.right+12&&r.bottom>innerHeight-bottom-fab.height-12&&r.top<innerHeight-bottom+12)){
        bottom=Math.min(innerHeight-fab.height-12,Math.max(bottom,innerHeight-Math.min(...bounds.map(r=>r.top))+12));
      }
    }
    root.style.setProperty('--assistant-bottom',bottom+'px');
    root.style.setProperty('--assistant-keyboard',keyboard+'px');
    root.style.setProperty('--assistant-height',(viewport?.height||innerHeight)+'px');
  }
  scope.listen(document,'focusin',layout);scope.listen(document,'scroll',layout,{capture:true,passive:true});
  scope.listen(window,'resize',layout);
  if(avoidSelector)scope.listen(root,'toggle',layout,{capture:true});
  if(window.visualViewport){scope.listen(visualViewport,'resize',layout);scope.listen(visualViewport,'scroll',layout);}
  scope.own(()=>['--assistant-bottom','--assistant-keyboard','--assistant-height'].forEach(key=>root.style.removeProperty(key)));
  layout();
}
