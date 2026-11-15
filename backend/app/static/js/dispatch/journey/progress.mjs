import {origin} from './navigation.mjs';
import {el,button} from '../models/forms.mjs';
import {resourceUrl} from '../navigation/resource.mjs';
export function journeySteps(view,route,workspace){
 const core=view==='logistics-case-setup',g=workspace.ultimateGraph?.case_id===route.caseId?workspace.ultimateGraph:null,p=window.dationJourneyProgress||{},node=g?.nodes.find(n=>n.id===(route.nodeId||g.attention_node_id)),result=node?.actions.result;
 const current=core?(p.step||route.coreStep||1):view==='logistics-config'?5:view==='decision-dashboard'?6:4;
 const steps=['Logistics Model','Data Contract & Preparation','Decision Case','Decision Graph','Decision Configuration','Decision Dashboard'].map((label,i)=>({label,index:i+1,current:i+1===current,complete:false,allowed:false,target:null,reason:'Completá el contexto anterior.'}));
 for(let i=0;i<3;i++){steps[i].allowed=!!route.caseId||core&&(i===0||p.modelReady);steps[i].complete=i===0?(!!route.caseId||!!p.modelReady):i===1?(g?Boolean(g.nodes.find(n=>n.id==='logistics_assignment')?.read_set.transport_demand&&g.nodes.find(n=>n.id==='logistics_assignment')?.read_set.transport_resources):!!p.dataReady):!!route.caseId;steps[i].target={view:'logistics-case-setup',caseId:route.caseId,coreStep:i+1};}
 steps[3].allowed=!!route.caseId;steps[3].target={view:'logistics-map',caseId:route.caseId};
 steps[4].allowed=!!node?.actions.configure.allowed;steps[4].target={view:'logistics-config',caseId:route.caseId,nodeId:node?.id};steps[4].reason='Revisá requisitos y permisos de la decisión en Graph.';
 steps[5].allowed=!!route.runId||!!result?.allowed;steps[5].target={view:'decision-dashboard',caseId:route.caseId,nodeId:route.nodeId||node?.id,runId:route.runId||result?.target?.run_id};steps[5].reason='Todavía no hay una corrida disponible.';
 return steps;
}
export function renderJourneyProgress(root,{view,route,state}){
 root.replaceChildren();root.classList.add('journey-six-steps');root.setAttribute('aria-label','Journey: Core Configuration y Decision Studio');
 const steps=journeySteps(view,route,state),current=steps.find(s=>s.current);
 for(const step of steps){const b=button('',()=>{if(step.target.view==='logistics-case-setup'){const local=view==='logistics-case-setup'?document.querySelector('[data-dation-test=core-step-'+step.index+']'):null;if(local)local.click();else window.DationDispatch.openCore(route.caseId,{coreStep:step.index,...origin(route)});}else if(step.target.view==='decision-dashboard')window.DationDispatch.openDashboard(route.caseId,step.target.nodeId,step.target.runId);else window.DationDispatch.openCase(route.caseId,step.target.view,step.target.nodeId);});b.className='dda-workspace-step';b.classList.toggle('is-current',step.current);b.classList.toggle('is-complete',step.complete&&!step.current);b.classList.toggle('is-disabled',!step.allowed);b.disabled=!step.allowed;b.setAttribute('aria-disabled',String(!step.allowed));b.title=step.allowed?step.label:step.reason;b.append(el('span',step.complete&&!step.current?'✓':String(step.index),'dda-workspace-step__marker'),el('span',step.label,'journey-step-label'));if(step.current)b.setAttribute('aria-current','step');root.append(b);}
 const text=el('p','Paso '+current.index+' de 6 · '+current.label,'journey-current-step');text.role='status';root.after(text);return text;
}
