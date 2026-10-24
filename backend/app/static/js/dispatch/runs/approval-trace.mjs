import {createScope} from '../lifecycle.mjs';
import {api} from '../shared.mjs';

const actors=new Map();
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}

export function mountDashboardTrace(root,{state,run,nodeId}){
 const hero=root.querySelector('#dispatch-hero,.d-page-hero');if(!hero)return;
 hero.classList.add('has-decision-trace');
 const host=el('aside',undefined,'dashboard-hero-trace');host.setAttribute('aria-label','Trazabilidad de la decisión');
 const visual=hero.querySelector('[data-dashboard-visual]');if(visual)visual.prepend(host);else hero.append(host);
 const scope=createScope(host),context={host,scope,dispose:()=>scope.dispose()},trace=el('dl');trace.dataset.runTrace='';host.append(trace);
 const assigned=state.workflow?.stages?.[nodeId]?.owner;
 const key=[state.decisionCase.id,run.id,run.approved_by_user_id,run.approved_at].join(':');
 const draw=people=>{if(!scope.active)return;trace.replaceChildren();
  for(const [label,value] of [
   [run.approved_at?'Aprobado por':'Pendiente de aprobación',run.approved_at?(people?.approved_by?.name||(run.approved_by==='shared_workspace:dation'?'Workspace compartido (histórico)':'Sin registro de aprobación')):assigned?.name||'Sin asignar'],
  ]){const row=el('div');row.append(el('dt',label),el('dd',value));trace.append(row);}
 };
 draw(actors.get(key));
 if(actors.has(key))return context;
 api('/api/platform/decisions/'+state.decisionCase.id+'/runs?'+new URLSearchParams({node_id:nodeId,run_id:run.id,limit:1}),{signal:scope.signal}).then(detail=>{
  if(!scope.active)return;const person=detail.items?.find(r=>r.id===run.id);
  if(person){actors.set(key,person);if(actors.size>20)actors.delete(actors.keys().next().value);}draw(person);
 }).catch(error=>{if(scope.active&&!scope.signal.aborted){const note=el('p','No pudimos recuperar los nombres de trazabilidad.','d-metadata');note.role='status';trace.append(note);}});
 return context;
}
