import {FOUNDATION} from '../platform/foundation.mjs';

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
