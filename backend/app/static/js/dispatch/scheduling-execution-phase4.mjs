import {api,esc,post} from "./shared.mjs";
import {STATUS,transitionNode} from "./decision-case.mjs";
import {
  executionConfiguration,
  executionOptions,
  validateConfig,
} from "./scheduling-config-v2.mjs?v=scheduling-execution-phase4-v1";

const WORKSPACE_KEY="dation.dispatch.workspace.v5";
const CONFIG_KEY="dation.scheduling.config.v1";
const NODE_ID="logistics_scheduling";
const SCHEMA="scheduling_v1";
const STYLE_ID="scheduling-execution-phase4-styles";
const STYLE_HREF="/static/css/scheduling-execution-phase4.css?v=scheduling-execution-phase4-v1";
const POLL_MS=1200;

let lifecycleToken=0;
let pollTimer=null;
let active=false;
let evidenceRunId=null;
let evidencePending=false;

function ensureStyles(){
  if(document.getElementById(STYLE_ID))return;
  const link=document.createElement("link");
  link.id=STYLE_ID;
  link.rel="stylesheet";
  link.href=STYLE_HREF;
  document.head.append(link);
}

function readJson(key,fallback={}){
  try{return JSON.parse(sessionStorage.getItem(key)||"")||fallback;}catch{return fallback;}
}

function writeJson(key,value){
  try{sessionStorage.setItem(key,JSON.stringify(value));}catch{}
}

function workspace(){return readJson(WORKSPACE_KEY,{});}
function configStore(){return readJson(CONFIG_KEY,{});}

function configForCase(caseId){
  return caseId?(configStore()[caseId]||null):null;
}

function schedulingNode(state){
  return state?.decisionCase?.nodes?.[NODE_ID]||null;
}

function sourceRunId(state){
  const node=state?.decisionCase?.nodes?.logistics_assignment||{};
  return node.approved_run_id||node.run_id||null;
}

function persistNodeStatus(state,status,patch={}){
  if(!state?.decisionCase?.id)return state;
  const next={
    ...state,
    activeNode:NODE_ID,
    decisionCase:transitionNode(
      state.decisionCase,
      NODE_ID,
      status,
      patch,
    ),
    navigationVersion:state.navigationVersion||"workspace-nav-v1",
  };
  writeJson(WORKSPACE_KEY,next);
  return next;
}

function syncDecisionContext(state,status,runId){
  window.dationSetDecisionContext?.({
    id:NODE_ID,
    label:"Planificación de despachos",
    stepLabel:"Decisión 02",
    hasRun:Boolean(runId||schedulingNode(state)?.run_id),
    status,
  });
}

function setRunUrl(runId){
  const url=new URL(location.href);
  url.searchParams.set("run_id",runId);
  url.searchParams.set("dda",SCHEMA);
  history.replaceState(null,"",url);
}

function clearRunUrl(){
  const url=new URL(location.href);
  url.searchParams.delete("run_id");
  url.searchParams.delete("dda");
  history.replaceState(null,"",url);
}

function dashboardRoot(){
  return document.getElementById("dispatch-dashboard-root");
}

function stageCopy(stage){
  if(String(stage||"").startsWith("optimizing:")){
    return {
      title:"Optimizando la secuencia",
      copy:"Dation está ordenando los viajes y resolviendo la disponibilidad temporal de cada vehículo.",
    };
  }
  const labels={
    validating:{
      title:"Validando la evidencia",
      copy:"Verificando la asignación aprobada, la ventana temporal y las reglas por foco.",
    },
    constructing:{
      title:"Construyendo el calendario",
      copy:"Aplicando restricciones temporales sin modificar vehículos, cargas ni cantidades aprobadas.",
    },
    summarizing:{
      title:"Preparando la recomendación",
      copy:"Consolidando calendario, nivel de servicio, excepciones y trazabilidad de la corrida.",
    },
    registering:{
      title:"Registrando la planificación",
      copy:"Creando la corrida y vinculándola con el Decision Case antes de ejecutar el motor.",
    },
  };
  return labels[stage]||{
    title:"Generando la planificación",
    copy:"La corrida sigue activa y Dation está esperando el resultado persistido por el motor.",
  };
}

function pendingMarkup(runId,stage="registering"){
  const copy=stageCopy(stage);
  return '<section class="scheduling-run-phase4" aria-live="polite">'
    +'<div class="scheduling-run-phase4__hero">'
      +'<div class="scheduling-run-phase4__spinner" aria-hidden="true"></div>'
      +'<div><span>DECISIÓN 02 · PLANIFICACIÓN</span><h1>'+esc(copy.title)+'</h1><p>'+esc(copy.copy)+'</p></div>'
      +'<code>'+esc(String(runId).slice(0,8).toUpperCase())+'</code>'
    +'</div>'
    +'<div class="scheduling-run-phase4__progress" role="progressbar" aria-label="Ejecución de la planificación" aria-valuetext="'+esc(copy.title)+'"><i></i></div>'
    +'<div class="scheduling-run-phase4__steps">'
      +'<span class="'+(stage==="validating"?"is-active":"")+'">Validar</span>'
      +'<span class="'+(stage==="constructing"||String(stage).startsWith("optimizing:")?"is-active":"")+'">Secuenciar</span>'
      +'<span class="'+(stage==="summarizing"?"is-active":"")+'">Consolidar</span>'
      +'<span>Persistir</span>'
    +'</div>'
    +'<p class="scheduling-run-phase4__trust">La barra es indeterminada: el backend no expone un porcentaje real de avance. El Run ID permite recuperar esta misma corrida si recargás la página.</p>'
  +'</section>';
}

function renderPending(runId,stage="registering"){
  document.body.classList.add("dispatch-result");
  window.dationSetDashboardReady?.(false);
  const root=dashboardRoot();
  if(root)root.innerHTML=pendingMarkup(runId,stage);
}

function errorMarkup(message,runId){
  return '<section class="scheduling-run-phase4 scheduling-run-phase4--error" aria-live="assertive">'
    +'<div class="scheduling-run-phase4__error-icon" aria-hidden="true">!</div>'
    +'<span>PLANIFICACIÓN · EJECUCIÓN INTERRUMPIDA</span>'
    +'<h1>No se pudo completar esta corrida</h1>'
    +'<p>'+esc(message||"El motor no pudo completar la planificación.")+'</p>'
    +(runId?'<code>Run '+esc(String(runId).slice(0,8).toUpperCase())+'</code>':'')
    +'<div class="scheduling-run-phase4__error-actions">'
      +'<button type="button" data-phase4-retry>Reintentar ejecución</button>'
      +'<button type="button" class="is-secondary" data-phase4-config>Volver a configuración</button>'
    +'</div>'
    +'<small>La configuración de ventana, objetivo y reglas por foco sigue guardada en este Decision Case.</small>'
  +'</section>';
}

function renderError(message,runId){
  const root=dashboardRoot();
  if(!root)return;
  root.innerHTML=errorMarkup(message,runId);
  root.querySelector("[data-phase4-retry]")?.addEventListener("click",()=>beginExecution());
  root.querySelector("[data-phase4-config]")?.addEventListener("click",()=>{
    clearRunUrl();
    window.dationNavigate?.("logistics-config");
  });
}

function readinessSla(preflight){
  const decision=preflight?.decision_readiness?.decisions?.find(item=>item.id===NODE_ID);
  return Boolean(decision?.capabilities?.find(item=>item.id==="sla")?.available);
}

function stopLifecycle(){
  lifecycleToken+=1;
  active=false;
  if(pollTimer){clearTimeout(pollTimer);pollTimer=null;}
}

function executedWindowLabel(result){
  const windowInfo=result?.analysis?.planning_window||{};
  if(windowInfo.start||windowInfo.end){
    return (windowInfo.start||"—")+" → "+(windowInfo.end||"—");
  }
  return "Automática";
}

function strategyLabel(configuration){
  return configuration?.strategy==="service_first"?"Servicio primero":"Salida más temprana";
}

function ruleLabel(rule){
  const fields={
    destination:"Destino",
    origin:"Origen",
    vehicle_id:"Vehículo",
    ownership:"Tipo de recurso",
    product:"Producto",
  };
  const action=rule.action==="window"?"Ventana específica":"Priorizar salida";
  return (fields[rule.field]||rule.field)+" · "+action;
}

function evidenceMarkup(run){
  const result=run?.result_json||{};
  const configuration=result.configuration||{};
  const analysis=result.analysis||{};
  const rules=analysis.focus_rules||[];
  const source=result.inputs?.assignment?.run_id||"—";
  const focused=Number(analysis.focused_trip_count||0);
  return '<div class="scheduling-execution-evidence__head">'
      +'<div><span>CONFIGURACIÓN EJECUTADA</span><h2>Qué produjo este calendario</h2><p>La evidencia corresponde a esta corrida y se lee directamente del DecisionResult persistido.</p></div>'
      +'<code>'+esc(String(run.id||"").slice(0,8).toUpperCase())+'</code>'
    +'</div>'
    +'<div class="scheduling-execution-evidence__grid">'
      +'<div><small>Objetivo</small><strong>'+esc(strategyLabel(configuration))+'</strong></div>'
      +'<div><small>Ventana general</small><strong>'+esc(executedWindowLabel(result))+'</strong></div>'
      +'<div><small>Reglas por foco</small><strong>'+rules.length+' · '+focused+' '+(focused===1?'viaje':'viajes')+'</strong></div>'
      +'<div><small>Assignment fuente</small><strong>'+esc(String(source).slice(0,8).toUpperCase())+'</strong></div>'
    +'</div>'
    +(rules.length?'<div class="scheduling-execution-evidence__rules">'
      +rules.map(rule=>'<span title="'+esc(rule.id||"")+'"><b>'+esc(ruleLabel(rule))+'</b><em>'+Number(rule.matched_trip_count||0)+' '+(Number(rule.matched_trip_count||0)===1?'viaje':'viajes')+'</em></span>').join("")
      +'</div>':'')
    +'<p class="scheduling-execution-evidence__note">Assignment permanece bloqueada: esta configuración sólo modifica fechas, secuencia y prioridad temporal.</p>';
}

function injectExecutionEvidence(run){
  if(run?.result_json?.schema_version!==SCHEMA)return;
  const root=dashboardRoot();
  const main=root?.querySelector(".dispatch-scheduling-dashboard .dispatch-focus-main");
  if(!main)return;
  let section=main.querySelector("[data-scheduling-execution-evidence]");
  if(!section){
    section=document.createElement("section");
    section.className="dispatch-panel scheduling-execution-evidence";
    section.dataset.schedulingExecutionEvidence="";
    const timeline=main.querySelector("#scheduling-timeline");
    if(timeline)main.insertBefore(section,timeline);
    else main.prepend(section);
  }
  section.innerHTML=evidenceMarkup(run);
  evidenceRunId=run.id||null;
}

async function enhanceHistoricalDashboard(){
  if(evidencePending)return;
  const root=dashboardRoot();
  if(!root?.querySelector(".dispatch-scheduling-dashboard"))return;
  const query=new URLSearchParams(location.search);
  const runId=query.get("run_id");
  if(query.get("dda")!==SCHEMA||!runId||runId===evidenceRunId)return;
  evidencePending=true;
  try{
    const run=await api("/api/runs/"+runId);
    if(run?.status==="completed")injectExecutionEvidence(run);
  }catch{}finally{evidencePending=false;}
}

function finalizeSuccess(run,token){
  if(token!==lifecycleToken)return;
  stopLifecycle();
  let state=workspace();
  state=persistNodeStatus(state,STATUS.REVIEW,{run_id:run.id,error:null,approved_at:null});
  syncDecisionContext(state,STATUS.REVIEW,run.id);
  window.dationSetDashboardReady?.(true);
  window.DationDispatch?.show?.(run);
  queueMicrotask(()=>injectExecutionEvidence(run));
}

function finalizeError(error,runId,token){
  if(token!==lifecycleToken)return;
  const message=error?.message||String(error||"La planificación no pudo completarse.");
  stopLifecycle();
  let state=workspace();
  state=persistNodeStatus(state,STATUS.ERROR,{run_id:runId,error:message});
  syncDecisionContext(state,STATUS.ERROR,runId);
  renderError(message,runId);
}

async function pollRun(runId,token){
  if(token!==lifecycleToken)return;
  try{
    const run=await api("/api/runs/"+runId);
    if(token!==lifecycleToken)return;
    if(run?.status==="completed"){
      finalizeSuccess(run,token);
      return;
    }
    if(run?.status==="error"){
      finalizeError(new Error(run.error_message||"La planificación terminó con error."),runId,token);
      return;
    }
    renderPending(runId,run?.progress_json?.stage||"running");
  }catch(error){
    if(error?.status!==404&&token===lifecycleToken){
      // A transient polling failure does not cancel the POST already running.
      renderPending(runId,"running");
    }
  }
  if(token===lifecycleToken){
    pollTimer=setTimeout(()=>pollRun(runId,token),POLL_MS);
  }
}

async function recoverAfterPostError(runId,token,originalError){
  if(token!==lifecycleToken)return;
  try{
    const run=await api("/api/runs/"+runId);
    if(run?.status==="completed"){
      finalizeSuccess(run,token);
      return;
    }
    if(run?.status==="running"||run?.status==="queued"){
      renderPending(runId,run?.progress_json?.stage||"running");
      return;
    }
    if(run?.status==="error"){
      finalizeError(new Error(run.error_message||originalError?.message),runId,token);
      return;
    }
  }catch{}
  finalizeError(originalError,runId,token);
}

async function beginExecution(){
  if(active)return;
  const state=workspace();
  const caseId=state?.decisionCase?.id;
  const sourceId=sourceRunId(state);
  const config=configForCase(caseId);
  if(!caseId||!state?.orders?.id||!state?.fleet?.id||!sourceId||!config){
    renderError("No se pudo reconstruir la configuración de Planificación. Volvé a Configurar decisión y revisala antes de ejecutar.",null);
    return;
  }

  active=true;
  const token=++lifecycleToken;
  let sourceRun;
  let preflight;
  try{
    [sourceRun,preflight]=await Promise.all([
      api("/api/runs/"+sourceId),
      post("/api/runs/preflight",{
        orders_dataset_id:state.orders.id,
        fleet_dataset_id:state.fleet.id,
        allow_third_party:true,
      }),
    ]);
  }catch(error){
    active=false;
    renderError(error.message||"No se pudo validar la evidencia previa.",null);
    return;
  }

  const trips=sourceRun?.result_json?.scenarios?.selected?.trips||[];
  const validation=validateConfig(config,readinessSla(preflight),trips);
  if(validation){
    active=false;
    clearRunUrl();
    window.dationNavigate?.("logistics-config");
    window.setTimeout(()=>{
      const errorNode=document.querySelector("[data-scheduling-rule-error]");
      if(errorNode)errorNode.innerHTML='<p class="scheduling-error">'+esc(validation)+'</p>';
      else alert(validation);
    },0);
    return;
  }

  const runId=crypto.randomUUID();
  let nextState=persistNodeStatus(state,STATUS.RUNNING,{run_id:runId,error:null,approved_at:null});
  syncDecisionContext(nextState,STATUS.RUNNING,runId);
  setRunUrl(runId);
  window.dationNavigate?.("decision-dashboard");
  renderPending(runId,"registering");
  pollTimer=setTimeout(()=>pollRun(runId,token),500);

  try{
    const run=await post("/api/runs?run_id="+runId,{
      orders_dataset_id:state.orders.id,
      fleet_dataset_id:state.fleet.id,
      source_run_id:sourceId,
      configuration:executionConfiguration(config),
      options:executionOptions(config),
      decision_case:{case_id:caseId,node_id:NODE_ID},
    });
    finalizeSuccess(run,token);
  }catch(error){
    await recoverAfterPostError(runId,token,error);
  }
}

function interceptExecute(event){
  const button=event.target?.closest?.("[data-scheduling-execute]");
  if(!button||!button.closest(".scheduling-config-v2"))return;
  event.preventDefault();
  event.stopImmediatePropagation();
  button.disabled=true;
  const dialog=button.closest("dialog");
  dialog?.close();
  beginExecution().finally(()=>{
    if(document.contains(button))button.disabled=false;
  });
}

function hideLegacyRenderer(){
  document.documentElement.classList.add("scheduling-phase4-lifecycle");
}

function start(){
  ensureStyles();
  hideLegacyRenderer();
  document.addEventListener("click",interceptExecute,true);
  window.addEventListener("dation:view",event=>{
    if(event.detail?.view==="decision-dashboard")queueMicrotask(enhanceHistoricalDashboard);
  });
  const observer=new MutationObserver(()=>queueMicrotask(enhanceHistoricalDashboard));
  observer.observe(document.documentElement,{childList:true,subtree:true});
  queueMicrotask(enhanceHistoricalDashboard);
}

start();

export {
  beginExecution,
  evidenceMarkup,
  injectExecutionEvidence,
  pendingMarkup,
};