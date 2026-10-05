import {esc,num} from './shared.mjs';
import {DECISION_META} from './decision-ui.mjs?v=traceability-v3';

const OBJECTIVE_LABELS={
  min_trips:'Menor cantidad de viajes',
  min_cost:'Costo mínimo',
  max_own_fleet:'Mayor uso de flota propia',
  min_co2:'CO₂ mínimo',
  balanced:'Balanceado',
  custom:'Personalizado',
};
const RESOURCE_LABELS={
  own:'Solo flota propia',
  mixed:'Flota propia + tercerizada',
  outsourced:'Solo tercerizada',
};
const RUN_STATES={
  approved:{label:'Aprobada vigente',tone:'approved'},
  candidate:{label:'Alternativa',tone:'candidate'},
  superseded:{label:'Aprobación anterior',tone:'superseded'},
  running:{label:'Procesando',tone:'running'},
  error:{label:'Error',tone:'error'},
};

function dateTime(value){
  if(!value)return '—';
  const parsed=new Date(value);
  if(Number.isNaN(parsed.getTime()))return '—';
  return new Intl.DateTimeFormat('es-AR',{
    day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',
  }).format(parsed);
}

function shortCaseId(value){
  return value?'DC-'+String(value).slice(0,8).toUpperCase():'—';
}

function shortRunId(value){
  return value?String(value).slice(0,8).toUpperCase():'—';
}

function datasetName(dataset){
  return dataset?.canonical_filename||dataset?.label||dataset?.original_filename||'Archivo sin nombre';
}

function caseStats(item){
  const nodes=item?.decision_case?.nodes||{};
  const values=Object.values(nodes);
  return {
    approved:values.filter(node=>node?.status==='approved').length,
    runs:values.reduce((sum,node)=>sum+(Number(node?.run_count)||0),0),
  };
}

function caseCard(item,currentCaseId){
  const row=item.case||{};
  const stats=caseStats(item);
  const current=String(row.id||'')===String(currentCaseId||'');
  return '<article class="dispatch-case-option '+(current?'is-current':'')+'">'
    +'<div class="dispatch-case-option__top">'
      +'<div><small>DECISION CASE</small><strong>'+esc(shortCaseId(row.id))+'</strong></div>'
      +(current?'<span class="dispatch-case-option__current">Abierto ahora</span>':'<span class="dispatch-case-option__state">Activo</span>')
    +'</div>'
    +'<div class="dispatch-case-option__pack">'
      +'<span><small>ÓRDENES</small><strong title="'+esc(datasetName(item.orders))+'">'+esc(datasetName(item.orders))+'</strong></span>'
      +'<span><small>FLOTA</small><strong title="'+esc(datasetName(item.fleet))+'">'+esc(datasetName(item.fleet))+'</strong></span>'
    +'</div>'
    +'<div class="dispatch-case-option__metrics">'
      +'<span><strong>'+num(stats.approved)+'/3</strong><small>decisiones vigentes</small></span>'
      +'<span><strong>'+num(stats.runs)+'</strong><small>corridas registradas</small></span>'
    +'</div>'
    +'<div class="dispatch-case-option__footer">'
      +'<span>Última actividad · '+esc(dateTime(row.last_activity_at||row.updated_at))+'</span>'
      +'<button type="button" data-open-case="'+esc(row.id)+'">Abrir caso →</button>'
    +'</div>'
  +'</article>';
}

function makeDialog(className,label){
  const dialog=document.createElement('dialog');
  dialog.className=className;
  dialog.setAttribute('aria-label',label);
  document.body.append(dialog);
  dialog.addEventListener('close',()=>dialog.remove(),{once:true});
  return dialog;
}

export function openCaseSelector(cases,{currentCaseId=null,onSelect}={}){
  const dialog=makeDialog('dispatch-trace-dialog dispatch-case-selector','Seleccionar Decision Case');
  dialog.innerHTML='<div class="dispatch-trace-shell">'
    +'<header class="dispatch-trace-header">'
      +'<div><span class="dispatch-trace-eyebrow">TRAZABILIDAD</span><h2>Elegí el Decision Case que querés abrir.</h2>'
      +'<p>Cada caso conserva su Data Pack y todas las corridas realizadas sobre esos datos.</p></div>'
      +'<button type="button" class="dispatch-trace-close" data-close aria-label="Cerrar">×</button>'
    +'</header>'
    +'<div class="dispatch-case-selector__summary"><strong>'+num(cases.length)+' casos activos</strong><span>Seleccionar un caso restaura automáticamente sus datos y su mapa de decisiones.</span></div>'
    +'<div class="dispatch-case-selector__grid">'+cases.map(item=>caseCard(item,currentCaseId)).join('')+'</div>'
  +'</div>';

  dialog.querySelector('[data-close]').onclick=()=>dialog.close();
  dialog.querySelectorAll('[data-open-case]').forEach(button=>{
    button.onclick=async()=>{
      dialog.querySelectorAll('button').forEach(item=>item.disabled=true);
      button.textContent='Abriendo caso…';
      try{
        await onSelect?.(button.dataset.openCase);
        dialog.close();
      }catch(error){
        dialog.querySelectorAll('button').forEach(item=>item.disabled=false);
        button.textContent='Abrir caso →';
        const summary=dialog.querySelector('.dispatch-case-selector__summary span');
        if(summary)summary.textContent=error?.message||'No pudimos abrir el Decision Case.';
      }
    };
  });
  dialog.showModal();
  return dialog;
}

function runConfiguration(run){
  const config=run.configuration_json||{};
  if(run.node_id==='logistics_assignment'){
    const objective=OBJECTIVE_LABELS[config.objective]||config.objective||'Configuración de asignación';
    const filters=Array.isArray(config.scope?.filters)?config.scope.filters.length:0;
    const resource=RESOURCE_LABELS[config.options?.resource_mode]||null;
    return {
      title:objective,
      meta:[filters?filters+' filtro'+(filters===1?'':'s'):'Sin filtros',resource].filter(Boolean),
    };
  }
  if(run.node_id==='logistics_scheduling'){
    return {
      title:config.use_delivery_due_dates?'Servicio primero':'Salida temprana',
      meta:[run.upstream_run_id?'Assignment '+shortRunId(run.upstream_run_id):null].filter(Boolean),
    };
  }
  return {title:'Configuración registrada',meta:[]};
}

function runCard(run){
  const state=RUN_STATES[run.decision_state]||RUN_STATES.error;
  const config=runConfiguration(run);
  const openable=['approved','candidate','superseded'].includes(run.decision_state);
  return '<article class="dispatch-run-history__item is-'+esc(state.tone)+'">'
    +'<div class="dispatch-run-history__top">'
      +'<div><small>CORRIDA</small><strong>R-'+esc(shortRunId(run.id))+'</strong></div>'
      +'<span class="dispatch-run-history__state is-'+esc(state.tone)+'">'+esc(state.label)+'</span>'
    +'</div>'
    +'<div class="dispatch-run-history__body">'
      +'<strong>'+esc(config.title)+'</strong>'
      +(config.meta.length?'<p>'+config.meta.map(esc).join(' · ')+'</p>':'')
      +'<small>'+esc(dateTime(run.finished_at||run.created_at))+'</small>'
    +'</div>'
    +'<div class="dispatch-run-history__flags">'
      +(run.is_latest?'<span>Última corrida</span>':'')
      +(run.is_current_approved?'<span>Decisión vigente</span>':'')
    +'</div>'
    +'<div class="dispatch-run-history__footer">'
      +(run.error_message?'<span class="dispatch-run-history__error">'+esc(run.error_message)+'</span>':'<span></span>')
      +(openable?'<button type="button" data-open-run="'+esc(run.id)+'" data-run-state="'+esc(run.decision_state)+'">'
        +(run.decision_state==='candidate'?'Ver y decidir →':run.decision_state==='superseded'?'Ver histórico →':'Ver análisis →')
      +'</button>':run.decision_state==='running'?'<small>Resultado disponible al finalizar.</small>':'')
    +'</div>'
  +'</article>';
}

export function openRunHistory({caseId,nodeId,history,onOpenRun}){
  const meta=DECISION_META[nodeId]||{label:'Decisión'};
  const runs=history?.runs||[];
  const dialog=makeDialog('dispatch-trace-dialog dispatch-run-history','Historial de corridas');
  dialog.innerHTML='<div class="dispatch-trace-shell dispatch-trace-shell--history">'
    +'<header class="dispatch-trace-header">'
      +'<div><span class="dispatch-trace-eyebrow">'+esc(shortCaseId(caseId))+' · HISTORIAL</span><h2>'+esc(meta.label)+'</h2>'
      +'<p>Cada corrida conserva la configuración y el resultado que produjo. Aprobar una alternativa no elimina las versiones anteriores.</p></div>'
      +'<button type="button" class="dispatch-trace-close" data-close aria-label="Cerrar">×</button>'
    +'</header>'
    +'<div class="dispatch-run-history__summary">'
      +'<strong>'+num(history?.total||runs.length)+' corrida'+((history?.total||runs.length)===1?'':'s')+'</strong>'
      +(history?.summary?.approved_run_id?'<span>Aprobada vigente · R-'+esc(shortRunId(history.summary.approved_run_id))+'</span>':'<span>Sin aprobación vigente</span>')
    +'</div>'
    +'<div class="dispatch-run-history__list">'
      +(runs.length?runs.map(runCard).join(''):'<div class="dispatch-run-history__empty">Todavía no hay corridas registradas para esta decisión.</div>')
    +'</div>'
  +'</div>';

  dialog.querySelector('[data-close]').onclick=()=>dialog.close();
  dialog.querySelectorAll('[data-open-run]').forEach(button=>{
    button.onclick=async()=>{
      button.disabled=true;
      try{
        await onOpenRun?.(button.dataset.openRun,nodeId,button.dataset.runState);
        dialog.close();
      }catch(error){
        button.disabled=false;
        button.textContent=error?.message||'No pudimos abrir la corrida';
      }
    };
  });
  dialog.showModal();
  return dialog;
}
