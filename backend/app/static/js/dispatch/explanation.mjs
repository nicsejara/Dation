import {iconSvg} from "./decision-ui.mjs";
import {createScope,trapFocus} from "./lifecycle.mjs";
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
  const scope=createScope(root);
  const result=run.result_json;
  const meta=schemaMeta(result);
  const questions=starterQuestions(result).slice(0,4);

  root.innerHTML=
    '<div class="dispatch-section-heading dispatch-ai-heading">'
      +'<div><span class="dispatch-kicker">DATION IA · '+esc(meta.label.toUpperCase())+'</span>'
      +'<h2>Explicar los eventos de la decisión</h2>'
      +'<p>'+esc(meta.description)+' La IA no recalcula ni modifica el resultado.</p></div>'
      +'<button data-explain class="dispatch-ai-primary">'+iconSvg("sparkles","dispatch-action-icon")+'<span>Generar explicación</span></button>'
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
    if(!scope.active)return;
    response.innerHTML=explanationView(data);
  }

  button.onclick=async()=>{
    button.disabled=true;
    const original=button.innerHTML;
    button.innerHTML=iconSvg('clock','dispatch-action-icon')+'<span>Analizando evidencia…</span>';
    response.innerHTML='<div class="dispatch-ai-loading"><span></span><p>Identificando eventos, causas modeladas y puntos que requieren revisión…</p></div>';
    try{
      show(await post('/api/runs/'+run.id+'/explain',undefined,{signal:scope.signal}));
      if(!scope.active)return;
      button.innerHTML=iconSvg('refresh','dispatch-action-icon')+'<span>Regenerar explicación</span>';
    }catch(error){
      if(!scope.active)return;
      errorBox(response,error,()=>button.click());
      button.innerHTML=original;
    }finally{
      if(!scope.active)return;
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

  api('/api/runs/'+run.id+'/interpretation',{signal:scope.signal})
    .then(data=>{
      if(!scope.active)return;
      if(data.explanation?.response_json){
        show(data.explanation.response_json);
        if(data.explanation_is_current===false){
          const notice=document.createElement('p');notice.className='dispatch-model-note';notice.setAttribute('role','status');
          notice.textContent='Esta interpretación corresponde a la corrida original. Ya hay nueva evidencia comparativa; generá una interpretación enriquecida para incluirla.';
          response.prepend(notice);
        }
        button.innerHTML=iconSvg('refresh','dispatch-action-icon')+'<span>Regenerar explicación</span>';
      }
    })
    .catch(()=>{});
}

export function chat(root,run,initialQuestion=''){
  const scope=createScope(root);
  const result=run.result_json;
  const meta=schemaMeta(result);
  const questions=starterQuestions(result).slice(0,4);
  const dashboard=root.closest('.d-decision-dashboard');
  const launcher=dashboard?.querySelector('[data-chat]');
  root.id=launcher?.getAttribute('aria-controls')||'decision-assistant';
  root.setAttribute('role','dialog');root.setAttribute('aria-label','Dation IA · '+meta.label);
  const workspace=window.dationSession?.identity?.workspace?.name;
  const context=[workspace,'DDA Logística',run.decision_case_id?'Case '+String(run.decision_case_id).slice(0,8):null,meta.label,'Run '+String(run.id).slice(0,8)].filter(Boolean).join(' · ');
  const busy=value=>{root.setAttribute('aria-busy',String(value));dashboard?.dispatchEvent(new CustomEvent('dispatch:assistant-busy',{detail:{busy:value}}));};
  scope.own(()=>busy(false));
  const modal=()=>root.setAttribute('aria-modal',String(matchMedia('(max-width:700px)').matches));
  scope.listen(window,'resize',modal);modal();

  root.innerHTML=
    '<div class="dispatch-chat-heading">'
      +'<div><span class="dispatch-kicker">DATION IA</span><h2>'+esc(meta.title)+'</h2>'
      +'<small class="dispatch-chat-context">'+esc(context)+'</small></div>'
      +'<button data-close class="dispatch-chat-close" aria-label="Cerrar chat">'+iconSvg("x","dispatch-action-icon")+'</button>'
    +'</div>'
    +'<div class="dispatch-chat-boundary">'+iconSvg("sparkles","dispatch-action-icon")+'<p>'+esc(meta.description)+' Si una causa no está demostrada por la evidencia, Dation lo indica explícitamente.</p></div>'
    +'<div class="dispatch-chat-starters">'
      +questions.map(question=>'<button type="button" data-starter="'+esc(question)+'">'+esc(question)+'</button>').join('')
    +'</div>'
    +'<button type="button" data-older hidden>Ver mensajes anteriores</button>'
    +'<div class="dispatch-chat-thread" data-messages role="log" aria-live="polite"></div>'
    +'<form class="dispatch-chat-composer">'
      +'<textarea required minlength="2" maxlength="2000" rows="3" placeholder="'+esc(meta.placeholder)+'" aria-label="Pregunta para Dation"></textarea>'
      +'<div><small>Enter para enviar · Shift+Enter para nueva línea</small><button type="submit"><span>Enviar</span>'+iconSvg("arrowUp","dispatch-action-icon")+'</button></div>'
    +'</form>';

  const closeChat=()=>{
    scope.dispose();
    root.hidden=true;
    const dashboard=root.closest('.d-decision-dashboard');
    dashboard?.classList.remove('with-chat');
    const toggle=dashboard?.querySelector('[data-chat]');
    toggle?.setAttribute('aria-expanded','false');toggle?.focus({preventScroll:true});
  };
  root.querySelector('[data-close]').onclick=closeChat;
  scope.listen(root,'keydown',event=>{if(root.getAttribute('aria-modal')==='true')trapFocus(event,root);if(event.key==='Escape'){event.preventDefault();event.stopPropagation();closeChat();}});

  const messages=root.querySelector('[data-messages]');
  const field=root.querySelector('textarea');
  const form=root.querySelector('form');
  const submit=form.querySelector('button[type="submit"]');
  let historyLoaded=false;
  let sending=false;
  let retryTurn=null;
  let nextOffset=0;
  let currentEvidence=null;
  const seenMessages=new Set();
  const older=root.querySelector("[data-older]");

  function add(role,text,{loading=false,error=false,before=null,evidence=null}={}){
    const article=document.createElement('article');
    article.dataset.evidenceId=evidence||'';
    article.dataset.pending=String(loading||error);
    article.className='dispatch-chat-message is-'+role+(loading?' is-loading':'')+(error?' is-error':'');
    const label=document.createElement('small');
    label.textContent=role==='user'?'Vos':(currentEvidence&&!loading&&!error&&evidence!==currentEvidence?'Dation · interpretación de la corrida original':'Dation');
    const body=document.createElement('div');
    body.textContent=text;
    article.append(label,body);
    messages.insertBefore(article,before);
    messages.scrollTop=messages.scrollHeight;
    return article;
  }

  async function sendQuestion(raw){
    const question=String(raw||'').trim();
    if(question.length<2||sending)return;
    const turn=retryTurn?.question===question?retryTurn:{question,id:crypto.randomUUID()};
    sending=true;busy(true);
    submit.disabled=true;
    add('user',question);
    field.value='';
    const pending=add('assistant','Analizando la evidencia de esta corrida…',{loading:true});
    try{
      const data=await post('/api/runs/'+run.id+'/chat',{question,turn_id:turn.id},{signal:scope.signal});
      if(!scope.active)return;
      retryTurn=null;
      nextOffset+=2;
      pending.remove();
      add('assistant',data.answer||data.message||data.response||'La respuesta no tiene texto.',{evidence:data.evidence_analysis_id||null});
    }catch(error){
      if(!scope.active)return;
      retryTurn=turn;
      pending.remove();
      add('assistant',error.message,{error:true});
      field.value=question;
    }finally{
      if(!scope.active)return;
      sending=false;busy(false);
      submit.disabled=false;
      field.focus();
    }
  }

  function showHistory(data,{prepend=false}={}){
    currentEvidence=data.current_evidence_analysis_id||null;
    const before=prepend?messages.firstChild:null;
    (data.messages||[]).forEach(message=>{
      if(message.id&&seenMessages.has(message.id))return;
      if(message.id)seenMessages.add(message.id);
      add(message.role,message.content,{before,evidence:message.evidence_analysis_id||null});
    });
    nextOffset=data.pagination?.next_offset||nextOffset;
    older.hidden=!data.pagination?.has_more;
  }

  scope.listen(root,'dispatch:evidence-changed',event=>{
    currentEvidence=event.detail.id;
    messages.querySelectorAll('article.is-assistant').forEach(article=>{
      if(article.dataset.pending==='true')return;
      const label=article.querySelector('small');
      if(label)label.textContent=article.dataset.evidenceId!==currentEvidence?'Dation · interpretación de la corrida original':'Dation';
    });
  });

  older.onclick=async()=>{
    older.disabled=true;
    try{
      const data=await api('/api/runs/'+run.id+'/interpretation?offset='+nextOffset,{signal:scope.signal});
      if(scope.active)showHistory(data,{prepend:true});
    }catch(error){
      if(scope.active)add('assistant',error.message,{error:true});
    }finally{
      if(scope.active)older.disabled=false;
    }
  };

  api('/api/runs/'+run.id+'/interpretation',{signal:scope.signal})
    .then(data=>{
      if(!scope.active)return;
      showHistory(data);
    })
    .catch(()=>{})
    .finally(()=>{
      if(!scope.active)return;
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
