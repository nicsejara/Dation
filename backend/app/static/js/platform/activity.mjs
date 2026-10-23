import {demoBadge} from './onboarding.mjs';
import {api} from '../dispatch/shared.mjs';
import {createScope} from '../dispatch/lifecycle.mjs';
import {workspaceDate,workspaceRelativeDate} from './workspace-format.mjs';
import {resourceUrl} from '../dispatch/navigation/resource.mjs';
import {iconSvg} from '../dispatch/decision-ui.mjs';
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
export function mountActivity(root,{getIdentity,caseId=null,initial=null,limit=10,compact=false,presentation='default'}){
 const scope=createScope(root);let controller,generation=0,cursor=null,items=[],busy=false;
 const list=el('ol',undefined,'platform-activity__list'),status=el('p',undefined,'d-body'),actions=el('div',undefined,'platform-activity__actions');status.role='status';root.classList.add('platform-activity');root.replaceChildren(list,status,actions);
 function button(text,fn){const b=el('button',text,'d-button d-button--secondary');b.type='button';b.addEventListener('click',fn);return b;}
 function render(){list.replaceChildren();
  for(const event of items){const row=el('li',undefined,'platform-activity__event');row.dataset.activityId=event.id;
   if(presentation==='home'){const mark=el('span',undefined,'platform-home__activity-icon'),kind=event.event_type||'';mark.setAttribute('aria-hidden','true');mark.innerHTML=iconSvg(kind==='decision.approved'?'checkCircle':kind==='run.failed'?'alertTriangle':kind.startsWith('dataset.')?'database':kind.startsWith('member.')?'clipboardList':'history');row.append(mark);}
   row.append(el('p',event.label,'d-body'));if(event.is_demo)row.append(demoBadge());const stamp=el('time',presentation==='home'?workspaceRelativeDate(event.created_at,getIdentity().workspace):workspaceDate(event.created_at,getIdentity().workspace),'d-metadata');stamp.dateTime=event.created_at;stamp.title=workspaceDate(event.created_at,getIdentity().workspace);row.append(stamp);
   if(event.case_id&&!caseId){const a=el('a','Ver caso','platform-activity__case');a.href=resourceUrl(location.href,{view:'platform-decisions',center:{caseId:event.case_id}});a.dataset.activityCase=event.case_id;row.append(a);}
   if(presentation!=='home'){const details=el('details',undefined,'platform-activity__technical');details.append(el('summary','Detalles del evento'));for(const [label,value]of [['Evento',event.event_type],['ID',event.id],['Actor',event.actor?.id],['Objeto',event.object_id],['Decisión',event.node_id]])if(value)details.append(el('p',label+': '+value,'d-metadata'));const meta=el('pre',JSON.stringify(event.metadata||{},null,2));details.append(meta);row.append(details);}list.append(row);
  }
  status.textContent=items.length?'':presentation==='home'?'Todavía no hay actividad en este Workspace.':'Todavía no hay eventos registrados. Las nuevas acciones aparecerán acá.';actions.replaceChildren();if(cursor&&!compact)actions.append(button('Ver más actividad',()=>load(true)));
 }
 function accept(data,append=false){const seen=new Set(append?items.map(e=>e.id):[]);items=[...(append?items:[]),...data.items.filter(e=>!seen.has(e.id))];if(presentation==='home')items=items.slice(0,5);cursor=data.next_cursor;render();}
 async function load(append=false){if(busy)return;busy=true;controller?.abort();controller=new AbortController();const own=++generation;root.setAttribute('aria-busy','true');status.textContent='Cargando actividad…';for(const b of actions.querySelectorAll('button'))b.disabled=true;
  try{const q=new URLSearchParams({limit:String(limit)});if(caseId)q.set('case_id',caseId);if(append&&cursor)for(const [k,v]of Object.entries(cursor))q.set(k,v);const data=await api('/api/platform/activity?'+q,{signal:controller.signal});if(own!==generation)return;accept(data,append);}
  catch(error){if(own!==generation||controller.signal.aborted)return;status.textContent='No se pudo cargar la actividad. Reintentá.';actions.replaceChildren(button('Reintentar actividad',()=>load(append)));}
  finally{if(own===generation){busy=false;root.removeAttribute('aria-busy');}}
 }
 scope.listen(root,'click',event=>{const a=event.target.closest('[data-activity-case]');if(!a||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;event.preventDefault();window.DationDispatch.openDecisionCenter({caseId:a.dataset.activityCase});});
 function stop(){generation++;controller?.abort();busy=false;root.removeAttribute('aria-busy');}
 scope.listen(window,'pagehide',stop);
 if(initial?.available)accept(initial);else if(initial){status.textContent=initial.error||(presentation==='home'?'Todavía no hay actividad en este Workspace.':'No hay actividad reciente para mostrar.');if(initial.error)actions.append(button('Reintentar actividad',()=>load()));}else load();
 return {dispose(){stop();scope.dispose();}};
}
