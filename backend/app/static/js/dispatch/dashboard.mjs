import {esc,num,download,dispose,errorBox,api} from './shared.mjs';
import * as hero from './hero.mjs';
import * as assignment from './assignment.mjs';
import * as review from './review.mjs';
import * as explanation from './explanation.mjs';
import * as plan from './plan.mjs';
import * as schedulingDashboard from './scheduling-dashboard.mjs';
import {decisionRail,bindDecisionRail} from './decision-nav.mjs';

export function render(root,run,onRerun,caseActions={}){
  dispose(root);
  const result=run.result_json;
  if(result?.schema_version==='scheduling_v1'){
    return schedulingDashboard.render(
      root,
      run,
      onRerun,
      caseActions,
    );
  }
  const metrics=result.scenarios.selected.metrics;
  const statusLabels={
    running:'Procesando',
    review:'En revisión',
    approved:'Aprobada',
    error:'Error',
  };
  const caseStatus=statusLabels[caseActions.status]||'Decisión disponible';
  const isAssignment=result.schema_version==='assignment_v1';
  const exportLabel=isAssignment?'Exportar asignación':'Exportar distribución';

  root.className='dispatch dispatch-dashboard dispatch-dashboard-focused';
  root.innerHTML=
    '<header class="dispatch-command dispatch-command-focused">'
      +'<div class="dispatch-command-title"><strong>DDA Logística</strong><span class="dispatch-status" data-case-status>'+esc(caseStatus)+'</span></div>'
      +'<div class="dispatch-actions dispatch-actions--focused">'
        +(caseActions.onApprove?'<button data-approve class="dispatch-primary-action" '+(caseActions.status==='approved'?'disabled':'')+'>'+(caseActions.status==='approved'?'✓ Decisión aprobada':'Aprobar decisión')+'</button>':'')
        +'<details class="dispatch-action-menu"><summary>Acciones ···</summary><div class="dispatch-action-menu__panel">'
          +'<button data-csv>↓ '+esc(exportLabel)+' CSV</button>'
          +'<button data-json>Exportar JSON técnico</button>'
          +'<button data-rerun>Re-ejecutar Assignment</button>'
          +'<button data-copy>Copiar detalles técnicos</button>'
          +'<dl>'
            +Object.entries({
              'Corrida':run.id,
              'Motor':result.engine.name+' '+result.engine.version,
              'Solver':result.engine.solver.name||result.engine.solver.method||'Política heurística',
              'Estado':result.engine.solver.status,
              'Huella':result.result_fingerprint,
              'Órdenes':result.inputs.orders.filename||'Órdenes',
              'Flota':result.inputs.fleet.label||result.inputs.fleet.filename||'Flota',
              'Profundidad':result.analysis?.depth||result.configuration?.options?.analysis_depth||'No informada',
              'Escenarios evaluados':result.analysis?.scenario_count??'—',
              'Órdenes incluidas':metrics.orders,
              'Kg totales':num(metrics.total_weight_kg),
            }).map(([key,value])=>'<dt>'+esc(key)+'</dt><dd>'+esc(value)+'</dd>').join('')
          +'</dl>'
          +'<p data-ai-details>Modelo de IA: consultando…</p>'
        +'</div></details>'
      +'</div>'
    +'</header>'
    +decisionRail(caseActions)
    +'<main class="dispatch-focus-main">'
      +'<section class="dispatch-panel dispatch-focus-hero" id="dispatch-hero"></section>'
      +'<section class="dispatch-panel dispatch-focus-assignment" id="dispatch-assignment"></section>'
      +'<section class="dispatch-panel dispatch-focus-review" id="dispatch-review"></section>'
      +'<section class="dispatch-panel dispatch-focus-ai" id="dispatch-explanation"></section>'
    +'</main>'
    +'<button type="button" class="dispatch-ai-fab" data-chat aria-expanded="false" aria-label="Abrir Dation IA"><span>✦</span><strong>Dation IA</strong></button>'
    +'<aside class="dispatch-chat dispatch-panel" hidden aria-label="Chat de la decisión"></aside>';

  api('/api/system/llm-status')
    .then(data=>{
      root.querySelector('[data-ai-details]').textContent='IA: '+(data.configured?(data.provider+' · '+data.model):'Sin configurar');
    })
    .catch(()=>{
      root.querySelector('[data-ai-details]').textContent='No se pudo consultar el modelo de IA.';
    });

  const sections=[
    ['hero',hero,result],
    ['assignment',assignment,result],
    ['review',review,result],
    ['explanation',explanation,run],
  ];

  for(const [key,module,value] of sections){
    const element=root.querySelector('#dispatch-'+key);
    const draw=()=>{
      try{
        module.render(element,value);
      }catch(error){
        errorBox(element,error,draw);
      }
    };
    draw();
  }

  function openChat(question=''){
    const aside=root.querySelector('.dispatch-chat');
    const fab=root.querySelector('[data-chat]');
    aside.hidden=false;
    root.classList.add('with-chat');
    fab?.setAttribute('aria-expanded','true');
    explanation.chat(aside,run,question);
  }

  if(root._dispatchChatHandler){
    root.removeEventListener('dispatch:open-chat',root._dispatchChatHandler);
  }
  root._dispatchChatHandler=event=>{
    openChat(event.detail?.question||'');
  };
  root.addEventListener('dispatch:open-chat',root._dispatchChatHandler);

  function feedback(button,working,done){
    const original=button.dataset.originalLabel||button.textContent;
    button.dataset.originalLabel=original;
    button.disabled=true;
    button.textContent=working;
    window.setTimeout(()=>{
      button.textContent=done;
      window.setTimeout(()=>{
        button.textContent=original;
        button.disabled=false;
      },1200);
    },120);
  }

  root.querySelector('[data-csv]').onclick=event=>{
    try{
      plan.exportPlan(result);
      feedback(event.currentTarget,'Preparando archivo…','✓ Exportado');
    }catch(error){
      event.currentTarget.textContent='No se pudo exportar';
      window.setTimeout(()=>{
        event.currentTarget.textContent=event.currentTarget.dataset.originalLabel||('↓ '+exportLabel+' CSV');
      },1500);
    }
  };
  root.querySelector('[data-rerun]').onclick=onRerun;
  bindDecisionRail(root,caseActions);
  const approveButton=root.querySelector('[data-approve]');
  if(approveButton)approveButton.onclick=async()=>{
    approveButton.disabled=true;
    try{
      await caseActions.onApprove?.();
      approveButton.textContent='Decisión aprobada';
      const status=root.querySelector('[data-case-status]');
      if(status)status.textContent='Aprobada';
      caseActions.onApprovalComplete?.();
    }catch(error){
      approveButton.disabled=false;
      alert(error.message);
    }
  };
  root.querySelector('[data-chat]').onclick=()=>{
    const aside=root.querySelector('.dispatch-chat');
    if(!aside.hidden){
      aside.hidden=true;
      root.classList.remove('with-chat');
      root.querySelector('[data-chat]')?.setAttribute('aria-expanded','false');
      return;
    }
    openChat();
  };
  root.querySelector('[data-json]').onclick=()=>download('decision-'+run.id+'.json',JSON.stringify(result,null,2));
  root.querySelector('[data-copy]').onclick=async event=>{
    try{
      await navigator.clipboard.writeText(JSON.stringify({
        run_id:run.id,
        engine:result.engine,
        analysis:result.analysis,
        inputs:result.inputs,
        result_fingerprint:result.result_fingerprint,
      },null,2));
      event.target.textContent='Copiado';
    }catch{
      event.target.textContent='No se pudo copiar';
    }
  };
}
