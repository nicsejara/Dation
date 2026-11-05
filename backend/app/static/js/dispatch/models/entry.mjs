import {api} from '../shared.mjs';
import {createScope} from '../lifecycle.mjs';
// One landing action; no secondary technical setup/upload card.
export function mountFoundationEntry(){
 const start=document.querySelector('[data-view-panel="logistics-overview"] [data-start-new-decision]');if(!start)return;
 const scope=createScope(start);let generation=0;
 async function refresh(){const own=++generation;
  try{const caps=await api('/api/platform/ultimate-foundation/capabilities',{signal:scope.signal});if(!scope.active||own!==generation)return;
   start.disabled=!caps.can_create_case;start.setAttribute('aria-disabled',String(start.disabled));start.title=start.disabled?'La planificación inicial no está habilitada para este acceso.':'Comenzar una planificación';
  }catch{if(scope.active&&own===generation){start.disabled=true;start.title='No se pudo comprobar el acceso. Recargá para reintentar.';}}
 }
 scope.listen(window,'dation:identity',refresh);scope.listen(window,'pagehide',()=>scope.dispose());refresh();return scope;
}
