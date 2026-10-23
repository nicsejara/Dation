import {esc} from '../shared.mjs';
import {resolveDecisionDestination} from './decision-target.mjs';
import {statePresentation} from '../../platform/foundation.mjs';
import {
  DECISION_ORDER,
  DECISION_META,
  statusUi,
} from '../decision-ui.mjs';

export function decisionRail(caseActions={}){
  const decisionCase=caseActions.decisionCase;
  if(!decisionCase?.nodes)return '';

  const activeNode=caseActions.activeNode;
  const nodes=DECISION_ORDER
    .map((nodeId)=>{
      const meta=DECISION_META[nodeId];
      const node=decisionCase.nodes[nodeId]||{};
      const ui=statusUi(node.status);
      const phase=!meta.implemented||node.status==='locked'||node.status==='needs_data'?'LOCKED':node.status==='approved'?'APPROVED':node.status==='review'?'WAITING_APPROVAL':node.run_id?'EXECUTED':nodeId===activeNode&&caseActions.view==='logistics-config'?'CONFIGURING':'AVAILABLE';
      const target=resolveDecisionDestination(nodeId,node,caseActions.view,caseActions);
      const canOpen=Boolean(target);
      const presentation=statePresentation(node.status,nodeId===activeNode);
      return '<button type="button" class="dispatch-decision-tab'
        +(nodeId===activeNode?' is-active':'')
        +(node.status==='approved'?' is-approved':'')
        +'" data-decision-node="'+esc(nodeId)+'" '
        +'data-decision-state="'+phase+'" data-status-tone="'+presentation.tone+'" '+(presentation.selected?'aria-current="page" ':'')
        +(canOpen?'':'disabled')
        +'>'
          +'<span>'+esc(meta.index)+'</span>'
          +'<div><strong>'+esc(meta.label)+'</strong>'
          +'<small>'+esc(phase==='CONFIGURING'?'En configuración':phase==='WAITING_APPROVAL'?'Esperando aprobación':ui.label)+'</small></div>'
          +(node.status==='approved'?'<i aria-hidden="true">✓</i>':'')
        +'</button>';
    })
    .join('');

  return '<section class="dispatch-decision-rail" aria-label="Decisiones del caso">'
    +'<nav>'+nodes+'</nav>'
    +'</section>';
}

export function bindDecisionRail(root,caseActions={}){
  root.querySelectorAll('[data-decision-node]').forEach(button=>{
    button.onclick=()=>{
      if(button.disabled)return;
      caseActions.onOpenNode?.(button.dataset.decisionNode);
    };
  });
}
