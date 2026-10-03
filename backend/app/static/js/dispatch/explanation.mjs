import {esc,api,post,errorBox} from './shared.mjs';

function textBlock(value){
  if(Array.isArray(value)){
    return '<ul>'+value.map(item=>'<li>'+esc(item)+'</li>').join('')+'</ul>';
  }
  if(value&&typeof value==='object'){
    return '<div class="dispatch-ai-evidence-grid">'
      +Object.entries(value).map(([key,item])=>
        '<div><small>'+esc(key.replaceAll('_',' '))+'</small><strong>'+esc(item)+'</strong></div>'
      ).join('')
      +'</div>';
  }
  return '<p>'+esc(value??'')
    .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')
    .replaceAll('\n','<br>')+'</p>';
}

function explanationView(data){
  const value=data.explanation||data.response_json||data;
  const summary=value.executive_summary||value.title||value.recommendation;
  const events=value.key_drivers||value.events;
  const why=value.why_recommended||value.why;
  const evidence=value.business_impact||value.evidence;
  const caveats=value.caveats||value.risks;
  const next=value.recommendation||value.next_step;
  const tradeoffs=value.tradeoffs||value.trade_offs;

  return '<div class="dispatch-ai-answer dispatch-ai-story">'
    +(summary?'<section class="dispatch-ai-story__lead"><span>Qué decidió Dation</span>'+textBlock(summary)+'</section>':'')
    +(events?'<section><span>Eventos clave</span>'+textBlock(events)+'</section>':'')
    +(why?'<section><span>Por qué ocurrió</span>'+textBlock(why)+'</section>':'')
    +(evidence?'<section><span>Evidencia</span>'+textBlock(evidence)+'</section>':'')
    +(tradeoffs?'<section><span>Trade-offs</span>'+textBlock(tradeoffs)+'</section>':'')
    +(caveats?'<section><span>Qué no concluye el modelo</span>'+textBlock(caveats)+'</section>':'')
    +(next?'<section class="dispatch-ai-story__next"><span>Qué revisar ahora</span>'+textBlock(next)+'</section>':'')
    +'</div>';
}

function schemaMeta(result){
  if(result.schema_version==='scheduling_v1'){
    return {
      label:'Planificación',
      title:'Entender esta planificación',
      description:'Dation explica fechas, esperas, secuencia y excepciones usando únicamente la evidencia de Scheduling.',
      placeholder:'Ej.: ¿Por qué A-00004 sale el 8 de octubre?',
    };
  }
  if(result.schema_version==='assignment_v1'){
    return {
      label:'Assignment',
      title:'Entender esta asignación',
      description:'Dation explica cómo quedó distribuida la carga y qué trade-offs produjo el objetivo seleccionado.',
      placeholder:'Ej.: ¿Por qué VEH-003 concentra más carga?',
    };
  }
  return {
    label:'Decisión',
    title:'Entender esta decisión',
    description:'Dation interpreta la evidencia persistida sin modificar el cálculo.',
    placeholder:'Preguntá por esta decisión…',
  };
}

function starterQuestions(result){
  const selected=result.scenarios?.selected||{};
  const trips=selected.trips||[];
  const metrics=selected.metrics||{};

  if(result.schema_version==='scheduling_v1'){
    const waited=[...trips]
      .filter(trip=>Number(trip.wait_days||0)>0)
      .sort((a,b)=>Number(b.wait_days||0)-Number(a.wait_days||0))[0];
    const late=(result.exceptions||[])[0];
    const first=trips[0];
    return [
      waited
        ? '¿Por qué '+waited.trip_id+' espera '+waited.wait_days+' días antes de salir?'
        : (first?'¿Por qué '+first.trip_id+' sale en esa fecha?':'¿Cómo se construyó este calendario?'),
      late
        ? '¿Por qué '+late.order_id+' queda fuera de la fecha objetivo?'
        : '¿Qué vehículo tiene la secuencia más ajustada?',
      '¿Qué eventos de esta planificación debería revisar antes de aprobarla?',
      '¿Qué parte de este resultado quedó congelada desde Assignment?',
    ];
  }

  if(result.schema_version==='assignment_v1'){
    const byVehicle=new Map();
    for(const trip of trips){
      const id=trip.vehicle_id||trip.vehicle_type||'Vehículo';
      const current=byVehicle.get(id)||{id,kg:0,trips:0};
      current.kg+=Number(trip.load_kg||0);
      current.trips+=1;
      byVehicle.set(id,current);
    }
    const top=[...byVehicle.values()].sort((a,b)=>b.kg-a.kg)[0];
    return [
      top
        ? '¿Por qué '+top.id+' concentra más carga que los demás vehículos?'
        : '¿Cómo se distribuyó la carga entre los vehículos?',
      Number(metrics.outsourced_weight_share||0)>0
        ? '¿Por qué esta Assignment utiliza flota tercerizada?'
        : '¿Qué órdenes fueron consolidadas o divididas?',
      '¿Cómo influyó el objetivo seleccionado en esta distribución?',
      '¿Qué debería revisar antes de aprobar Assignment?',
    ];
  }

  return [
    '¿Cuál fue el evento más importante de esta decisión?',
    '¿Qué evidencia respalda la recomendación?',
    '¿Qué debería revisar antes de aprobar?',
  ];
}

export function render(root,run){
  const result=run.result_json;
  const meta=schemaMeta(result);
  const questions=starterQuestions(result).slice(0,4);

  root.innerHTML=
    '<div class="dispatch-section-heading dispatch-ai-heading">'
      +'<div><span class="dispatch-kicker">DATION IA · '+esc(meta.label.toUpperCase())+'</span>'
      +'<h2>Explicar los eventos de la decisión</h2>'
      +'<p>'+esc(meta.description)+' La IA no recalcula ni modifica el resultado.</p></div>'
      +'<button data-explain class="dispatch-ai-primary">✦ Generar explicación</button>'
    +'</div>'
    +'<div class="dispatch-ai-response" data-response aria-live="polite">'
      +'<div class="dispatch-ai-empty"><strong>Todavía no generamos la explicación.</strong><span>Podés generar un resumen causal o abrir una pregunta puntual.</span></div>'
    +'</div>'
    +'<div class="dispatch-ai-questions"><small>Explorar esta corrida</small>'
      +questions.map(question=>'<button data-question="'+esc(question)+'">'+esc(question)+'</button>').join('')
    +'</div>'
    +'<details class="dispatch-model-assumptions"><summary>Supuestos y límites del modelo</summary>'
      +(result.assumptions||[]).map(item=>'<p>'+esc(item)+'</p>').join('')
    +'</details>';

  const response=root.querySelector('[data-response]');
  const button=root.querySelector('[data-explain]');

  function show(data){
    response.innerHTML=explanationView(data);
  }

  button.onclick=async()=>{
    button.disabled=true;
    const original=button.textContent;
    button.textContent='Analizando evidencia…';
    response.innerHTML='<div class="dispatch-ai-loading"><span></span><p>Identificando eventos, causas modeladas y puntos que requieren revisión…</p></div>';
    try{
      show(await post('/api/runs/'+run.id+'/explain'));
      button.textContent='↻ Regenerar explicación';
    }catch(error){
      errorBox(response,error,()=>button.click());
      button.textContent=original;
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
      if(data.explanation?.response_json){
        show(data.explanation.response_json);
        button.textContent='↻ Regenerar explicación';
      }
    })
    .catch(()=>{});
}

export function chat(root,run,initialQuestion=''){
  const result=run.result_json;
  const meta=schemaMeta(result);
  const questions=starterQuestions(result).slice(0,4);

  root.innerHTML=
    '<div class="dispatch-chat-heading">'
      +'<div><span class="dispatch-kicker">DATION IA</span><h2>'+esc(meta.title)+'</h2>'
      +'<small class="dispatch-chat-context">Contexto · '+esc(meta.label)+' · corrida '+esc(String(run.id).slice(0,8))+'…</small></div>'
      +'<button data-close class="dispatch-chat-close" aria-label="Cerrar chat">×</button>'
    +'</div>'
    +'<div class="dispatch-chat-boundary"><span>✦</span><p>'+esc(meta.description)+' Si una causa no está demostrada por la evidencia, Dation lo indica explícitamente.</p></div>'
    +'<div class="dispatch-chat-starters">'
      +questions.map(question=>'<button type="button" data-starter="'+esc(question)+'">'+esc(question)+'</button>').join('')
    +'</div>'
    +'<div class="dispatch-chat-thread" data-messages role="log" aria-live="polite"></div>'
    +'<form class="dispatch-chat-composer">'
      +'<textarea required minlength="2" maxlength="2000" rows="3" placeholder="'+esc(meta.placeholder)+'" aria-label="Pregunta para Dation"></textarea>'
      +'<div><small>Enter para enviar · Shift+Enter para nueva línea</small><button type="submit">Enviar ↑</button></div>'
    +'</form>';

  root.querySelector('[data-close]').onclick=()=>{
    root.hidden=true;
    const dashboard=root.closest('.dispatch-dashboard');
    dashboard?.classList.remove('with-chat');
    dashboard?.querySelector('[data-chat]')?.setAttribute('aria-expanded','false');
  };

  const messages=root.querySelector('[data-messages]');
  const field=root.querySelector('textarea');
  const form=root.querySelector('form');
  const submit=form.querySelector('button[type="submit"]');
  let historyLoaded=false;
  let sending=false;

  function add(role,text,{loading=false,error=false}={}){
    const article=document.createElement('article');
    article.className='dispatch-chat-message is-'+role+(loading?' is-loading':'')+(error?' is-error':'');
    const label=document.createElement('small');
    label.textContent=role==='user'?'Vos':'Dation';
    const body=document.createElement('div');
    body.textContent=text;
    article.append(label,body);
    messages.append(article);
    messages.scrollTop=messages.scrollHeight;
    return article;
  }

  async function sendQuestion(raw){
    const question=String(raw||'').trim();
    if(question.length<2||sending)return;
    sending=true;
    submit.disabled=true;
    add('user',question);
    field.value='';
    const pending=add('assistant','Analizando la evidencia de esta corrida…',{loading:true});
    try{
      const data=await post('/api/runs/'+run.id+'/chat',{question});
      pending.remove();
      add('assistant',data.answer||data.message||data.response||'La respuesta no tiene texto.');
    }catch(error){
      pending.remove();
      add('assistant',error.message,{error:true});
      field.value=question;
    }finally{
      sending=false;
      submit.disabled=false;
      field.focus();
    }
  }

  api('/api/runs/'+run.id+'/interpretation')
    .then(data=>{
      (data.messages||[]).forEach(message=>add(message.role,message.content));
    })
    .catch(()=>{})
    .finally(()=>{
      historyLoaded=true;
      if(initialQuestion)sendQuestion(initialQuestion);
    });

  root.querySelectorAll('[data-starter]').forEach(button=>{
    button.onclick=()=>sendQuestion(button.dataset.starter);
  });

  form.onsubmit=event=>{
    event.preventDefault();
    sendQuestion(field.value);
  };

  field.onkeydown=event=>{
    if(event.key==='Enter'&&!event.shiftKey){
      event.preventDefault();
      if(historyLoaded)sendQuestion(field.value);
    }
  };

  field.focus();
}
