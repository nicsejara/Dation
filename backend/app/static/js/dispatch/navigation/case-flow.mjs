import {resolveNodeDestination,resolveDecisionDestination} from './decision-target.mjs';
import {DECISION_META} from '../decision-ui.mjs';
import {decisionRail,bindDecisionRail} from './decision-nav.mjs';
import {hasCaseExecutions,caseAttributesReady} from '../cases/case-identity.mjs';
import {configurationAvailable} from './decision-target.mjs';
import {graphTarget} from './ultimate-graph.mjs';

const views=['logistics-data','logistics-map','logistics-config','decision-dashboard'];
const signatures=new WeakMap();
export function caseFlowSteps(view,route,state={}){
 const graph=state.ultimateGraph?.case_id===route.caseId?state.ultimateGraph:null;
 if(graph){
  const node=graph.nodes.find(n=>n.id===(route.nodeId||graph.attention_node_id)),result=node?.actions.result;
  return ['Datos del Case','Mapa de decisiones','Configurar decisión','Dashboard'].map((label,index)=>{
   const target=index===0?{view:'logistics-case-data',caseId:route.caseId,nodeId:null,runId:null}:index===1?{view:'logistics-map',caseId:route.caseId,nodeId:null,runId:null}:index===2?graphTarget(node?.actions.configure.target):route.runId?{view:'decision-dashboard',caseId:route.caseId,nodeId:route.nodeId,runId:route.runId}:graphTarget(result?.target);
   return {label,view:target?.view,current:target?.view===view,disabled:index===2?!node?.actions.configure.allowed:index===3?!route.runId&&!result?.allowed:false,
    completed:false,context:index>=2&&target?.view===view?node?.label:null,target};
  });
 }
 const own=state.decisionCase?.id===route.caseId?state.decisionCase:null;
 const node=own?.nodes?.[route.nodeId],target=node&&resolveNodeDestination(route.nodeId,node);
 const hasRun=target?.view==='decision-dashboard',selected=Boolean(node&&target);
 const mapAvailable=own?.persisted&&(hasCaseExecutions(own)||state.preflight?.valid&&caseAttributesReady(state)&&(!state.workflow?.gates_enforced||state.workflow?.stages?.data_owner?.owner_eligible));
 return ['Datos del Case','Mapa de decisiones','Configurar decisión','Dashboard'].map((label,index)=>({
  label,view:views[index],current:views[index]===view,
  disabled:index===1?!mapAvailable:index===2?!configurationAvailable(route.nodeId,own,state.workflow):index===3?!hasRun:false,
  completed:index===0?Boolean(own?.persisted):index===1?selected:index===2?hasRun:false,
  context:index>=2&&views[index]===view?DECISION_META[route.nodeId]?.label:null,
  target:{view:views[index],caseId:route.caseId,nodeId:index>=2?route.nodeId:null,runId:index===3?target?.run_id:null},
 }));
}
function open(target){
 if(target.view==='decision-dashboard')window.DationDispatch.openDashboard(target.caseId,target.nodeId,target.runId);
 else window.DationDispatch.openCase(target.caseId,target.view,target.nodeId);
}
/** Horizontal scroll only: never move page focus or scroll position. */
export function revealCurrentStep(root){
 const step=root.querySelector('[aria-current="step"]');
 if(!step||root.scrollWidth<=root.clientWidth)return;
 const offset=step.getBoundingClientRect().left-root.getBoundingClientRect().left;
 root.scrollLeft+=offset-(root.clientWidth-step.offsetWidth)/2;
}
export function renderCaseFlow(root,{view,route,state={}}){
 const visible=[...views,'logistics-case-data'].includes(view);
 root.parentElement.hidden=!visible;
 if(!visible){root.replaceChildren();signatures.delete(root);return;}
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
 revealCurrentStep(root);
}
export function mountDecisionViews(root,{state,nodeId,view}){
 const current=state.decisionCase;if(!current?.id||!DECISION_META[nodeId]?.implemented)return;
 if(!root.querySelector('.dispatch-decision-rail')){const host=document.createElement('div');host.innerHTML=decisionRail({decisionCase:current,workflow:state.workflow,activeNode:nodeId,view});root.prepend(host);
  bindDecisionRail(host,{onOpenNode:id=>{const target=resolveDecisionDestination(id,current.nodes[id],view,{decisionCase:current,workflow:state.workflow});if(target)open({...target,caseId:current.id,nodeId:id,runId:target.run_id});}});
 }
}
