import {renderDecisionMap as renderBase} from './decision-map.mjs?v=traceability-v3';
import {DECISION_ORDER,DECISION_META} from './decision-ui.mjs?v=traceability-v3';
import {STATUS} from './decision-case.mjs?v=traceability-v3';

function candidateState(node){
  return Boolean(
    node?.approved_run_id
    &&node?.latest_run_id
    &&String(node.latest_run_id)!==String(node.approved_run_id)
    &&node.latest_execution_status==='completed'
  );
}

function runMeta(card,node){
  const old=card.querySelector('.dispatch-decision-node__run');
  if(!old)return;
  const count=Number(node?.run_count||0);
  const approved=node?.approved_run_id||null;
  const latest=node?.latest_run_id||null;
  const wrap=document.createElement('div');
  wrap.className='dispatch-decision-node__runmeta';
  wrap.innerHTML=count
    ?'<small>'+(count+' corrida'+(count===1?'':'s'))+(approved?' · vigente '+String(approved).slice(0,8):latest?' · última '+String(latest).slice(0,8):'')+'</small>'
      +'<button type="button" class="dispatch-node-history-button" data-trace-action="history">Historial · '+count+'</button>'
    :'<small class="is-empty" aria-hidden="true">&nbsp;</small>';
  old.replaceWith(wrap);
}

function actionButton(label,action,{primary=false,compact=false,runId=null}={}){
  const className=primary
    ?'dispatch-decision-node__action'
    :'dispatch-map-secondary-action'+(compact?' is-compact':'');
  return '<button type="button" class="'+className+'" data-trace-action="'+action+'"'
    +(runId?' data-trace-run="'+runId+'"':'')+'>'+label+'</button>';
}

function decorateActions(card,nodeId,node,options){
  const row=card.querySelector('.dispatch-decision-node__actionrow');
  if(!row)return;
  const meta=DECISION_META[nodeId]||{};
  const count=Number(node?.run_count||0);
  const hasCandidate=candidateState(node);
  const status=node?.status;

  if(status===STATUS.APPROVED){
    row.classList.add('dispatch-decision-node__actions--trace');
    if(hasCandidate){
      row.innerHTML=actionButton('Revisar alternativa →','open',{
        primary:true,
        runId:node.latest_run_id,
      })+actionButton('Ver aprobada','open',{
        compact:true,
        runId:node.approved_run_id,
      })+(
        meta.implemented
          ?actionButton('Nueva corrida','configure',{compact:true})
          :''
      );
      const statusLine=card.querySelector('.dispatch-decision-node__statusline span');
      if(statusLine){
        statusLine.textContent='La decisión vigente sigue aprobada. Tenés una alternativa nueva para revisar.';
      }
    }else{
      row.innerHTML=actionButton('Ver análisis','open',{
        runId:node.approved_run_id||node.run_id,
      })+(
        meta.implemented
          ?actionButton('Nueva corrida','configure',{compact:true})
          :''
      );
    }
  }else if(status===STATUS.STALE){
    row.classList.add('dispatch-decision-node__actions--trace');
    row.innerHTML=actionButton('Ver análisis anterior','open',{
      runId:node.approved_run_id||node.run_id,
    })+(
      meta.implemented
        ?actionButton('Actualizar decisión','configure',{compact:true})
        :''
    );
  }

  card.querySelectorAll('[data-trace-action]').forEach(button=>{
    button.onclick=()=>{
      const action=button.dataset.traceAction;
      if(action==='open'){
        options.onOpenResult?.(nodeId,button.dataset.traceRun||null);
      }else if(action==='configure'){
        options.onConfigure?.(nodeId);
      }
    };
  });

  const history=card.querySelector('[data-trace-action="history"]');
  if(history&&count){
    history.onclick=()=>options.onHistory?.(nodeId);
  }
}

export function renderDecisionMap(root,options){
  renderBase(root,options);
  const nodes=options.decisionCase?.nodes||{};
  const cards=[...root.querySelectorAll('.dispatch-decision-node')];
  DECISION_ORDER.forEach((nodeId,index)=>{
    const card=cards[index];
    if(!card)return;
    card.dataset.traceNode=nodeId;
    const node=nodes[nodeId]||{};
    runMeta(card,node);
    decorateActions(card,nodeId,node,options);
  });
}
