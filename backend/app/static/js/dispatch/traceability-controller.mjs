import {api} from './shared.mjs';
import {createScope} from './lifecycle.mjs';
import {openCaseSelector,openRunHistory} from './traceability-ui.mjs';
import {DECISION_ORDER} from './decision-ui.mjs';
let scope=null;
function interaction(){scope?.dispose();scope=createScope(document.createElement('div'));return scope;}
export async function listDecisionCases(signal){const payload=await api('/api/decision-cases?status=active&limit=100&offset=0',{signal});return Array.isArray(payload.cases)?payload.cases:[];}
export async function openDecisionMap(){
  const owner=interaction();
  try{
    const cases=await listDecisionCases(owner.signal);if(!owner.active)return;
    if(!cases.length)return window.dationNavigate('logistics-map');
    if(cases.length===1)return window.DationDispatch.openCase(cases[0].case.id);
    openCaseSelector(cases,{scope:owner,currentCaseId:window.DationDispatch.getWorkspace().decisionCase?.id,onSelect:caseId=>window.DationDispatch.openCase(caseId)});
  }catch(error){if(owner.active)window.dationNavigate('logistics-map');}
}
export async function showHistory(nodeId){
  const owner=interaction(),caseId=window.DationDispatch.getWorkspace().decisionCase?.id;if(!caseId)return;
  try{
    const history=await api('/api/decision-cases/'+caseId+'/runs?node_id='+nodeId+'&limit=100&offset=0',{signal:owner.signal});if(!owner.active)return;
    openRunHistory({scope:owner,caseId,nodeId,history,onOpenRun:(runId,node)=>window.DationDispatch.openRun(runId,node,caseId)});
  }catch(error){if(owner.active)console.error('History unavailable',error);}
}
export function decorateDecisionMap(root){
  const workspace=window.DationDispatch.getWorkspace();
  for(const nodeId of DECISION_ORDER){
    const card=root.querySelector('[data-decision-node="'+nodeId+'"]');if(!card)continue;
    const node=workspace.decisionCase?.nodes?.[nodeId];if(!node?.run_count)continue;
    const bar=document.createElement('div');bar.className='dispatch-decision-node__tracebar';
    const history=document.createElement('button');history.type='button';history.textContent='Historial · '+node.run_count;history.onclick=()=>showHistory(nodeId);bar.append(history);
    if(['approved','review','stale','error'].includes(node.status)&&['logistics_assignment','logistics_scheduling'].includes(nodeId)){const fresh=document.createElement('button');fresh.type='button';fresh.dataset.traceNew=nodeId;fresh.textContent='+ Nueva corrida';fresh.onclick=()=>window.DationDispatch.openCase(workspace.decisionCase.id,'logistics-config',nodeId);bar.append(fresh);}
    card.append(bar);
  }
}
export function mountTraceability(){
  if(!document.getElementById('decision-trace-v3-styles')){const link=document.createElement('link');link.id='decision-trace-v3-styles';link.rel='stylesheet';link.href='/static/css/decision-trace-v3.css';document.head.append(link);}
  Object.assign(window.DationDispatch,{listDecisionCases,openDecisionMap,openRunHistory:showHistory});
  window.addEventListener('dation:view',()=>scope?.dispose());window.addEventListener('pagehide',()=>scope?.dispose());
  window.dispatchEvent(new CustomEvent('dation:cases-ready'));
}
