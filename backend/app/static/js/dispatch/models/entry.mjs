import {api} from '../shared.mjs';
import {createScope} from '../lifecycle.mjs';
import {ensureStylesheet} from '../styles.mjs';
import {el,button} from './forms.mjs';
export function mountFoundationEntry(){
 const anchor=document.querySelector('[data-view-panel="logistics-overview"] .dda-landing__hero');if(!anchor)return;
 const host=el('section',undefined,'d-platform d-card ultimate-entry');host.hidden=true;host.setAttribute('aria-label','Models y contexto de Logística');anchor.after(host);
 const scope=createScope(host);let generation=0;
 async function refresh(){host.hidden=true;const own=++generation;
  try{const caps=await api('/api/platform/ultimate-foundation/capabilities',{signal:scope.signal});if(!scope.active||own!==generation||!caps.enabled)return;
   await ensureStylesheet('ultimate-foundation-styles','/static/css/ultimate-foundation.css','t3-v1');if(!scope.active||own!==generation)return;
   const actions=el('div',undefined,'platform-actions');actions.append(button('Logistics Models',()=>window.dationNavigate('logistics-models')));
   if(caps.can_create_case)actions.append(button('Crear Case sin archivos',()=>window.DationDispatch.openCase(null,'logistics-case-setup'),'primary'));
   host.replaceChildren(el('h2','Planificá desde el contexto','d-card-title'),el('p','Reutilizá un Model publicado y guardá el Case antes de cargar datos.','d-body'),actions);host.hidden=false;
  }catch{if(scope.active&&own===generation)host.hidden=true;}
 }
 scope.listen(window,'dation:identity',refresh);scope.listen(window,'pagehide',()=>scope.dispose());refresh();return scope;
}
