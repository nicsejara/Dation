import {esc} from './shared.mjs';

const META={
  logistics_assignment:{index:'01',label:'Assignment'},
  logistics_scheduling:{index:'02',label:'Planificación'},
  logistics_final_assignment:{index:'03',label:'Asignación final'},
};

const STATUS_LABELS={
  available:'Disponible',
  running:'Procesando',
  review:'En revisión',
  approved:'Aprobada',
  locked:'Bloqueada',
  needs_data:'Requiere datos',
  error:'Error',
  stale:'Desactualizada',
};

export function decisionRail(caseActions={}){
  const decisionCase=caseActions.decisionCase;
  if(!decisionCase?.nodes)return '';

  const activeNode=caseActions.activeNode;
  const nodes=Object.entries(META)
    .map(([nodeId,meta])=>{
      const node=decisionCase.nodes[nodeId]||{};
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
          +'<small>'+esc(STATUS_LABELS[node.status]||node.status||'Pendiente')+'</small></div>'
          +(node.status==='approved'?'<i aria-hidden="true">✓</i>':'')
        +'</button>';
    })
    .join('');

  return '<section class="dispatch-decision-rail" aria-label="Decisiones del caso">'
    +'<div class="dispatch-decision-rail__head">'
      +'<div><span class="dispatch-kicker">DECISION CASE</span><strong>Decisiones del análisis</strong></div>'
      +'<button type="button" data-flow class="dispatch-flow-button">Ver flujo completo →</button>'
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
  const flow=root.querySelector('[data-flow]');
  if(flow)flow.onclick=()=>caseActions.onFlow?.();
}
