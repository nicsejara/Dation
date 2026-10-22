import {resolveNodeDestination} from './decision-target.mjs';
import {DECISION_META} from './decision-ui.mjs';
import {decisionRail,bindDecisionRail} from './decision-nav.mjs';
import {scopeFor} from './lifecycle.mjs';
import {hasCaseExecutions} from './case-identity.mjs';

const views=['logistics-data','logistics-map','logistics-config','decision-dashboard'];
const signatures=new WeakMap();
export function caseFlowSteps(view,route,state={}){
 const own=state.decisionCase?.id===route.caseId?state.decisionCase:null;
 const node=own?.nodes?.[route.nodeId],target=node&&resolveNodeDestination(route.nodeId,node);
 const hasRun=target?.view==='decision-dashboard',selected=Boolean(node&&target);
 const mapAvailable=own?.persisted&&(hasCaseExecutions(own)||state.preflight?.valid&&(!state.workflow?.gates_enforced||state.workflow?.stages?.data_preparation?.owner_eligible));
 return ['Datos del Case','Mapa de decisiones','Configurar decisión','Dashboard'].map((label,index)=>({
  label,view:views[index],current:views[index]===view,
  disabled:index===1?!mapAvailable:index===2?!selected:index===3?!hasRun:false,
  completed:index===0?Boolean(own?.persisted):index===1?selected:index===2?hasRun:false,
  context:index>=2&&views[index]===view?DECISION_META[route.nodeId]?.label:null,
  target:{view:views[index],caseId:route.caseId,nodeId:index>=2?route.nodeId:null,runId:index===3?target?.run_id:null},
 }));
}
function open(target){
 if(target.view==='decision-dashboard')window.DationDispatch.openDashboard(target.caseId,target.nodeId,target.runId);
 else window.DationDispatch.openCase(target.caseId,target.view,target.nodeId);
}
export function renderCaseFlow(root,{view,route,state={}}){
 root.parentElement.hidden=!views.includes(view);
 if(!views.includes(view)){root.replaceChildren();signatures.delete(root);return;}
 const steps=caseFlowSteps(view,route,state),signature=JSON.stringify(steps);
 if(signatures.get(root)===signature&&root.children.length)return;
 signatures.set(root,signature);root.replaceChildren();
 for(const [index,step] of steps.entries()){
  const button=document.createElement('button');button.type='button';button.className='dda-workspace-step';button.dataset.step=String(index+1);
  button.classList.toggle('is-current',step.current);button.classList.toggle('is-complete',step.completed&&!step.current);
  button.disabled=step.disabled;button.setAttribute('aria-disabled',String(step.disabled));if(step.current)button.setAttribute('aria-current','step');
  const marker=document.createElement('span');marker.className='dda-workspace-step__marker';marker.textContent=step.completed&&!step.current?'✓':String(index+1);
  const copy=document.createElement('span');copy.className='dda-workspace-step__copy';const label=document.createElement('strong');label.textContent=step.label;copy.append(label);
  if(step.context){const small=document.createElement('small');small.className='dda-workspace-step__context';small.textContent=step.context;copy.append(small);}
  button.append(marker,copy);button.addEventListener('click',()=>open(step.target));root.append(button);
  if(index<steps.length-1){const connector=document.createElement('span');connector.className='dda-workspace-nav__connector';connector.setAttribute('aria-hidden','true');root.append(connector);}
 }
}
export function mountDecisionViews(root,{state,nodeId,view,onConfigure}){
 const current=state.decisionCase;if(!current?.id||!DECISION_META[nodeId]?.implemented)return;
 const scope=scopeFor(root);if(!scope)return;
 let rail=root.querySelector('.dispatch-decision-rail');
 if(!rail){const host=document.createElement('div');host.innerHTML=decisionRail({decisionCase:current,activeNode:nodeId,view});root.prepend(host);rail=host.firstElementChild;
  bindDecisionRail(host,{onOpenNode:id=>{const target=resolveNodeDestination(id,current.nodes[id]);if(target)open({...target,caseId:current.id,nodeId:id,runId:target.run_id});}});
 }
 if(rail&&!rail.querySelector('[data-back-map]')){const back=document.createElement('button');back.type='button';back.dataset.backMap='';back.className='case-back-map';back.textContent='← Mapa de decisiones';scope.listen(back,'click',()=>window.DationDispatch.openCase(current.id));rail.prepend(back);}
 const hero=root.querySelector('#dispatch-hero,.d-page-hero');if(!hero)return;
 const tabs=document.createElement('nav');tabs.className='decision-view-tabs';tabs.setAttribute('aria-label','Vistas de la decisión');
 const target=resolveNodeDestination(nodeId,current.nodes[nodeId]);
 for(const [label,selected,enabled,callback] of [
  ['Configuración',view==='logistics-config',true,onConfigure],
  ['Resultado',view==='decision-dashboard',target?.view==='decision-dashboard',()=>open({...target,caseId:current.id,nodeId,runId:target?.run_id})],
 ]){const button=document.createElement('button');button.type='button';button.textContent=label;button.disabled=!enabled;button.className='d-button d-button--secondary';if(selected)button.setAttribute('aria-current','page');scope.listen(button,'click',()=>{if(!selected)callback?.();});tabs.append(button);}
 hero.append(tabs);
}
