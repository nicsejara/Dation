import {esc} from './shared.mjs';
import {
  DECISION_ORDER,
  DECISION_META,
  statusUi,
} from './decision-ui.mjs?v=decision-map-premium-v1';

export function decisionRail(caseActions={}){
  const decisionCase=caseActions.decisionCase;
  if(!decisionCase?.nodes)return '';

  const activeNode=caseActions.activeNode;
  const nodes=DECISION_ORDER
    .map((nodeId)=>{
      const meta=DECISION_META[nodeId];
      const node=decisionCase.nodes[nodeId]||{};
      const ui=statusUi(node.status);
      const hasResult=Boolean(node.run_id);
      const canOpen=hasResult&&['review','approved','running'].includes(node.status);
      return '<button type="button" class="dispatch-decision-tab'
        +(nodeId===activeNode?' is-active':'')
        +(node.status==='approved'?' is-approved':'')
        +'" data-decision-node="'+esc(nodeId)+'" '
        +(canOpen?'':'disabled')
        +'>'
          +'<span>'+esc(meta.index)+'</span>'
          +'<div><strong>'+esc(meta.label)+'</strong>'
          +'<small>'+esc(ui.label)+'</small></div>'
          +(node.status==='approved'?'<i aria-hidden="true">✓</i>':'')
        +'</button>';
    })
    .join('');

  return '<section class="dispatch-decision-rail" aria-label="Decisiones del caso">'
    +'<div class="dispatch-decision-rail__head">'
      +'<div><span class="dispatch-kicker">DECISION CASE</span><strong>Decisiones del análisis</strong></div>'
      +'<button type="button" data-flow class="dispatch-flow-button">Explorar mapa →</button>'
    +'</div>'
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
  root.querySelectorAll('[data-flow]').forEach(flow=>{
    flow.onclick=()=>caseActions.onFlow?.();
  });
}
