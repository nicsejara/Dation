import {esc,api,post,errorBox} from './shared.mjs';

function textBlock(value){
  if(Array.isArray(value))return value.map(item=>'<p>'+esc(item)+'</p>').join('');
  if(value&&typeof value==='object')return Object.entries(value).map(([key,item])=>'<p><strong>'+esc(key.replaceAll('_',' '))+'</strong> · '+esc(item)+'</p>').join('');
  return '<p>'+esc(value??'').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replaceAll('\n','<br>')+'</p>';
}

function explanationView(data){
  const value=data.explanation||data.response_json||data;
  const summary=value.executive_summary||value.title||value.recommendation;
  const why=value.why_recommended||value.why||value.key_drivers;
  const tradeoffs=value.tradeoffs||value.trade_offs||value.business_impact;
  const caveats=value.caveats||value.risks;

  return '<div class="dispatch-ai-answer">'
    +(summary?'<section><span>En síntesis</span>'+textBlock(summary)+'</section>':'')
    +(why?'<section><span>Por qué esta distribución</span>'+textBlock(why)+'</section>':'')
    +(tradeoffs?'<section><span>Trade-offs relevantes</span>'+textBlock(tradeoffs)+'</section>':'')
    +(caveats?'<section><span>Qué revisar</span>'+textBlock(caveats)+'</section>':'')
    +'</div>';
}

export function render(root,run){
  const result=run.result_json;
  const outsourced=result.scenarios.selected.metrics.outsourced_weight_share||0;
  const late=result.scenarios.selected.metrics.late_orders||0;
  const isAssignment=result.schema_version==='assignment_v1';

  const questions=(isAssignment?[
    '¿Por qué algunos vehículos reciben más carga que otros?',
    ...(outsourced?['¿Por qué se utiliza flota tercerizada?']:[]),
    '¿Qué productos lleva cada vehículo?',
    '¿Cómo se relaciona esta asignación con el objetivo seleccionado?',
  ]:[
    '¿Por qué algunos recursos tienen más carga que otros?',
    ...(outsourced?['¿Por qué se utiliza flota tercerizada?']:[]),
    ...(late?['¿Qué órdenes fuera de SLA debería revisar primero?']:[]),
    '¿Cómo se relaciona esta asignación con el objetivo seleccionado?',
  ]).slice(0,4);

  root.innerHTML=
    '<div class="dispatch-section-heading">'
      +'<div><span class="dispatch-kicker">DATION IA</span><h2>Explicar la decisión</h2>'
      +'<p>La IA interpreta el resultado ya calculado. No reasigna camiones, no recalcula el optimizador y no inventa un ahorro contra una operación histórica.</p></div>'
      +'<button data-explain>'+(isAssignment?'Explicar esta asignación':'Explicar esta distribución')+'</button>'
    +'</div>'
    +'<div class="dispatch-ai-response" data-response aria-live="polite"></div>'
    +'<div class="dispatch-ai-questions"><small>Preguntas útiles</small>'
      +questions.map(question=>'<button data-question="'+esc(question)+'">'+esc(question)+'</button>').join('')
    +'</div>'
    +'<details class="dispatch-model-assumptions"><summary>Ver supuestos del modelo</summary>'
      +(result.assumptions||[]).map(item=>'<p>'+esc(item)+'</p>').join('')
    +'</details>';

  const response=root.querySelector('[data-response]');
  const button=root.querySelector('[data-explain]');

  function show(data){
    response.innerHTML=explanationView(data);
  }

  button.onclick=async()=>{
    button.disabled=true;
    response.innerHTML='<p>Preparando una explicación basada en la distribución persistida…</p>';
    try{
      show(await post('/api/runs/'+run.id+'/explain'));
    }catch(error){
      errorBox(response,error,()=>button.click());
    }finally{
      button.disabled=false;
    }
  };

  root.querySelectorAll('[data-question]').forEach(question=>{
    question.onclick=()=>{
      root.dispatchEvent(new CustomEvent('dispatch:open-chat',{
        bubbles:true,
        detail:{question:question.dataset.question},
      }));
    };
  });

  api('/api/runs/'+run.id+'/interpretation')
    .then(data=>{
      if(data.explanation?.response_json)show(data.explanation.response_json);
    })
    .catch(()=>{});
}

export function chat(root,run,initialQuestion=''){
  root.innerHTML=
    '<div class="dispatch-chat-heading"><div><span class="dispatch-kicker">DATION IA</span><h2>Preguntar sobre esta distribución</h2></div><button data-close aria-label="Cerrar chat">Cerrar</button></div>'
    +'<p>Las respuestas usan la corrida persistida y su evidencia. La IA no modifica la asignación ni decide fechas.</p>'
    +'<div data-messages role="log" aria-live="polite"></div>'
    +'<form><label>Tu pregunta<textarea required minlength="2" maxlength="2000" rows="3" placeholder="¿Por qué este vehículo concentra más carga?"></textarea></label><button>Enviar</button></form>';

  root.querySelector('[data-close]').onclick=()=>{
    root.hidden=true;
    root.closest('.dispatch-dashboard')?.classList.remove('with-chat');
  };

  const messages=root.querySelector('[data-messages]');
  const field=root.querySelector('textarea');

  function add(role,text){
    const p=document.createElement('p');
    const strong=document.createElement('strong');
    strong.textContent=role==='user'?'Vos: ':'Dation: ';
    p.append(strong,document.createTextNode(text));
    messages.append(p);
    p.scrollIntoView({block:'nearest'});
  }

  api('/api/runs/'+run.id+'/interpretation')
    .then(data=>(data.messages||[]).forEach(message=>add(message.role,message.content)))
    .catch(()=>{});

  if(initialQuestion)field.value=initialQuestion;

  root.querySelector('form').onsubmit=async event=>{
    event.preventDefault();
    const submit=root.querySelector('form button');
    const question=field.value.trim();
    if(question.length<2)return;
    submit.disabled=true;
    add('user',question);
    try{
      const data=await post('/api/runs/'+run.id+'/chat',{question});
      add('assistant',data.answer||data.message||data.response||'La respuesta no tiene texto.');
      field.value='';
    }catch(error){
      add('assistant',error.message);
    }finally{
      submit.disabled=false;
    }
  };

  field.focus();
}
