import {FOUNDATION} from '../../platform/foundation.mjs';

// Official navigation never substitutes a replacement for a current approval.
// Call openRun explicitly when the user chooses a candidate or historical run.
export function resolveNodeDestination(nodeId,node={}){
 if(!FOUNDATION.decisions[nodeId]?.implemented||['coming_soon','locked','needs_data'].includes(node.status))return null;
 const approved=node.approved_run_id||node.approved_run?.id||(node.status==='approved'?node.run_id:null);
 const latest=node.latest_run_id||node.latest_run?.id||node.run_id;
 const current=['approved','review','running','error'].includes(node.status)&&(node.approval_current??Boolean(approved));
 const matches={approved:current&&Boolean(approved),candidate:['review','running','stale','error'].includes(node.status)&&Boolean(latest),available:node.status==='available'};
 const rule=FOUNDATION.destinationRules.find(rule=>matches[rule.when]);
 return rule?{view:rule.view,node_id:nodeId,run_id:rule.run==='approved'?approved:rule.run==='latest'?latest:null}:null;
}

// Horizontal navigation keeps the workflow level; the canonical run still wins.
export function configurationAvailable(nodeId,decisionCase,workflow){
 if(!decisionCase?.nodes)return false;
 const order=Object.keys(FOUNDATION.decisions),index=order.indexOf(nodeId);
 if(index<0||!FOUNDATION.decisions[nodeId].implemented||!resolveNodeDestination(nodeId,decisionCase.nodes[nodeId]))return false;
 if(order.slice(0,index).some(id=>FOUNDATION.decisions[id].implemented&&decisionCase.nodes[id]?.status!=='approved'))return false;
 return !workflow?.gates_enforced||Boolean(workflow.stages?.data_owner?.owner_eligible&&workflow.stages?.[nodeId]?.owner_eligible&&workflow.attributes_applied!==false);
}
export function resolveDecisionDestination(nodeId,node={},view,context={}){
 const target=resolveNodeDestination(nodeId,node);
 if(!target)return null;
 if(view==='logistics-config')return context.decisionCase&&!configurationAvailable(nodeId,context.decisionCase,context.workflow)?null:{...target,view,run_id:null};
 if(view==='decision-dashboard')return target.view===view&&target.run_id?target:null;
 return target;
}
