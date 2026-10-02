import {esc,num,download,dispose,errorBox,api} from './shared.mjs';
import * as hero from './hero.mjs';
import * as assignment from './assignment.mjs';
import * as review from './review.mjs';
import * as explanation from './explanation.mjs';
import * as plan from './plan.mjs';

export function render(root,run,onRerun){
  dispose(root);
  const result=run.result_json;
  const metrics=result.scenarios.selected.metrics;

  root.className='dispatch dispatch-dashboard dispatch-dashboard-focused';
  root.innerHTML=
    '<header class="dispatch-command dispatch-command-focused">'
      +'<div class="dispatch-command-title"><strong>DDA Logística</strong><span class="dispatch-status">Decisión disponible</span></div>'
      +'<div class="dispatch-actions">'
        +'<button data-csv class="dispatch-primary-action">Exportar distribución</button>'
        +'<button data-rerun>Reejecutar</button>'
        +'<button data-chat>Preguntale a Dation</button>'
        +'<details class="dispatch-more"><summary>Más</summary><div class="dispatch-details">'
          +'<button data-json>Exportar JSON</button>'
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
    +'<main class="dispatch-focus-main">'
      +'<section class="dispatch-panel dispatch-focus-hero" id="dispatch-hero"></section>'
      +'<section class="dispatch-panel dispatch-focus-assignment" id="dispatch-assignment"></section>'
      +'<section class="dispatch-panel dispatch-focus-review" id="dispatch-review"></section>'
      +'<section class="dispatch-panel dispatch-focus-ai" id="dispatch-explanation"></section>'
    +'</main>'
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
    aside.hidden=false;
    root.classList.add('with-chat');
    explanation.chat(aside,run,question);
  }

  root.addEventListener('dispatch:open-chat',event=>{
    openChat(event.detail?.question||'');
  });

  root.querySelector('[data-csv]').onclick=()=>plan.exportPlan(result);
  root.querySelector('[data-rerun]').onclick=onRerun;
  root.querySelector('[data-chat]').onclick=()=>openChat();
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
