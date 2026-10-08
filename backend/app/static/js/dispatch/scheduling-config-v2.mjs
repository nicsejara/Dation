import {api,esc,num,post} from "./shared.mjs";
import {iconSvg} from "./decision-ui.mjs?v=assignment-config-v2";
import {
  bindFocusRuleEvents,
  executionRules,
  focusRulesMarkup,
  focusedTripIds,
  hydrateExecutionRules,
  normalizeFocusConfig,
  validateFocusRules,
} from "./scheduling-focus-rules.mjs?v=scheduling-config-phase2";

const WORKSPACE_KEY="dation.dispatch.workspace.v5";
const CONFIG_KEY="dation.scheduling.config.v1";
const ROOT_ID="dispatch-config-root";
const STYLE_IDS={
  case:"scheduling-case-language",
  assignment:"scheduling-assignment-language",
  own:"scheduling-config-v2-styles",
};
const restoredRuns=new Set();
let observer=null;
let mounting=false;

function ensureLink(id,href){
  if(document.getElementById(id))return;
  const link=document.createElement("link");
  link.id=id;
  link.rel="stylesheet";
  link.href=href;
  document.head.append(link);
}

function ensureStyles(){
  ensureLink(STYLE_IDS.case,"/static/css/decision-map-case-v2.css?v=scheduling-config-phase2");
  ensureLink(STYLE_IDS.assignment,"/static/css/assignment-config-v2.css?v=scheduling-config-phase2");
  ensureLink(STYLE_IDS.own,"/static/css/scheduling-config-v2.css?v=scheduling-config-phase2");
}

function readJson(key,fallback={}){
  try{return JSON.parse(sessionStorage.getItem(key)||"")||fallback;}catch{return fallback;}
}

function workspace(){return readJson(WORKSPACE_KEY,{});}
function configStore(){return readJson(CONFIG_KEY,{});}

function writeConfig(caseId,value){
  if(!caseId)return;
  const store=configStore();
  store[caseId]=value;
  try{sessionStorage.setItem(CONFIG_KEY,JSON.stringify(store));}catch{}
}

function defaults(){
  return {
    strategy:"service_first",
    windowMode:"auto",
    windowStart:"",
    windowEnd:"",
    analysisDepth:"essential",
    temporalRules:[],
    ruleDraft:{
      field:"destination",
      values:[],
      action:"prioritize",
      windowStart:"",
      windowEnd:"",
    },
  };
}

function caseConfig(caseId){
  return {...defaults(),...(configStore()[caseId]||{})};
}

function displayCaseId(value){
  if(!value)return "—";
  return "DC-"+String(value).slice(0,8).toUpperCase();
}

function middleEllipsis(value,max=36){
  const text=String(value||"—");
  if(text.length<=max)return text;
  const extension=text.toLowerCase().endsWith(".csv")?".csv":"";
  const stem=extension?text.slice(0,-4):text;
  const tailLength=Math.min(12,Math.max(8,Math.floor(max*.32)));
  const headLength=Math.max(10,max-tailLength-extension.length-1);
  return stem.slice(0,headLength)+"…"+stem.slice(-tailLength)+extension;
}

function datasetFile(kind,dataset){
  const orders=kind==="orders";
  const total=Number(dataset?.row_count||0);
  const fullName=dataset?.canonical_filename||dataset?.label||dataset?.original_filename||"Archivo sin nombre";
  return '<article class="dispatch-datapack-file is-'+kind+' assignment-case-file">'
    +'<span class="dispatch-datapack-file__accent" aria-hidden="true"></span>'
    +'<span class="dispatch-datapack-file__icon">'+iconSvg(orders?"clipboardList":"truck","dispatch-map-icon")+'</span>'
    +'<div class="dispatch-datapack-file__body">'
      +'<div class="dispatch-datapack-file__topline"><small>'+(orders?'ÓRDENES':'FLOTA')+'</small></div>'
      +'<strong class="dispatch-datapack-file__name" title="'+esc(fullName)+'">'+esc(middleEllipsis(fullName))+'</strong>'
      +'<div class="dispatch-datapack-file__meta"><span class="is-count">'+num(total)+' '+(orders?(total===1?'orden':'órdenes'):(total===1?'vehículo':'vehículos'))+'</span></div>'
    +'</div>'
  +'</article>';
}

function caseStrip(state){
  const id=String(state.decisionCase?.id||"");
  return '<section class="dispatch-case-card assignment-case-strip scheduling-case-strip" aria-label="Decision Case y Data Pack en uso">'
    +'<div class="assignment-case-strip__identity">'
      +'<span class="dispatch-case-identity__icon">'+iconSvg("folderOpen","dispatch-map-icon")+'</span>'
      +'<div><small class="assignment-case-strip__eyebrow">DECISION CASE</small>'
        +'<div class="dispatch-case-identity__idrow">'
          +'<strong title="'+esc(id)+'">'+esc(displayCaseId(id))+'</strong>'
          +'<button type="button" data-scheduling-copy-case title="Copiar ID" aria-label="Copiar ID completo del caso">'+iconSvg("copy","dispatch-map-icon")+'</button>'
        +'</div>'
        +'<span class="assignment-case-strip__feedback" data-scheduling-copy-feedback aria-live="polite"></span>'
      +'</div>'
    +'</div>'
    +'<div class="assignment-case-strip__pack">'
      +'<div class="assignment-case-strip__pack-title"><span>DATA PACK EN USO</span></div>'
      +datasetFile("orders",state.orders)
      +datasetFile("fleet",state.fleet)
    +'</div>'
    +'<button class="assignment-change-data" type="button" data-scheduling-change-data>'
      +iconSvg("refresh","assignment-icon")+'<span>Cambiar datos</span>'
    +'</button>'
  +'</section>';
}

function heroMarkup(){
  return '<section class="dispatch-pro-hero assignment-config-hero">'
    +'<div class="dispatch-pro-hero-copy">'
      +'<div class="assignment-config-hero__badges">'
        +'<span class="dispatch-pro-hero-badge is-step">PASO 3: CONFIGURAR DECISIÓN</span>'
        +'<span class="assignment-decision-chip">DECISIÓN 02 DE 3</span>'
      +'</div>'
      +'<h1>Definí cuándo querés despachar los viajes.</h1>'
      +'<p class="dispatch-pro-hero-lead">Partí de la asignación aprobada, fijá la ventana temporal y elegí qué criterio debe ordenar el calendario. Cargas, cantidades y recursos quedan trazados desde la decisión anterior.</p>'
    +'</div>'
    +'<div class="dispatch-pro-hero-visual">'
      +'<div class="dispatch-pro-how-panel assignment-decision-panel">'
        +'<div class="dispatch-pro-how-title"><span>ESTA DECISIÓN</span></div>'
        +[
          ["1 · PREGUNTA","¿Cuándo conviene ejecutar los viajes ya definidos?","messageCircleQuestion"],
          ["2 · ENTREGA","Calendario operativo + secuencia de despachos.","calendarClock"],
          ["3 · QUEDA PARA DESPUÉS","La ejecución final se consolida en Asignación de vehículos.","truck"],
        ].map(([label,description,icon],index)=>(
          '<div class="dispatch-pro-how-node">'
            +'<span class="dispatch-pro-how-icon">'+iconSvg(icon,"dispatch-pro-icon assignment-icon")+'</span>'
            +'<div><small>'+esc(label)+'</small><strong>'+esc(description)+'</strong></div>'
          +'</div>'+(index<2?'<span class="dispatch-pro-how-connector" aria-hidden="true"></span>':'')
        )).join("")
      +'</div>'
    +'</div>'
  +'</section>';
}

function uniqueResources(trips){
  const resources=new Map();
  (trips||[]).forEach(trip=>{
    if(trip?.vehicle_id&&!resources.has(trip.vehicle_id))resources.set(trip.vehicle_id,trip.ownership||"own");
  });
  return {
    total:resources.size,
    own:[...resources.values()].filter(value=>value==="own").length,
    third:[...resources.values()].filter(value=>value==="third_party").length,
  };
}

function sourceStats(sourceRun){
  const selected=sourceRun?.result_json?.scenarios?.selected||{};
  const trips=selected.trips||[];
  const metrics=selected.metrics||{};
  return {
    trips,
    totalTrips:Number(metrics.total_trips??trips.length??0),
    vehicles:Number(metrics.vehicles_used??uniqueResources(trips).total),
    destinations:new Set(trips.map(item=>item.destination).filter(Boolean)).size,
    resources:uniqueResources(trips),
  };
}

function sectionHead(number,title,copy,badge=""){
  return '<header class="scheduling-section__head">'
    +'<span class="scheduling-section__index">'+esc(String(number).padStart(2,"0"))+'</span>'
    +'<div><h2>'+esc(title)+'</h2><p>'+esc(copy)+'</p></div>'
    +(badge?'<span class="scheduling-section__badge">'+esc(badge)+'</span>':'')
  +'</header>';
}

function choice({name,value,title,copy,selected,disabled=false,tag=""}){
  return '<label class="scheduling-choice '+(selected?'is-selected ':'')+(disabled?'is-disabled':'')+'">'
    +'<input type="radio" name="'+esc(name)+'" value="'+esc(value)+'" '+(selected?'checked':'')+' '+(disabled?'disabled':'')+'>'
    +'<span class="scheduling-choice__top"><strong>'+esc(title)+'</strong>'+(tag?'<em>'+esc(tag)+'</em>':'')+'</span>'
    +'<p>'+esc(copy)+'</p>'
  +'</label>';
}

function formatRunId(id){return id?String(id).slice(0,8).toUpperCase():"—";}

function windowLabel(config){
  if(config.windowMode!=="custom")return "Automática · desde la primera fecha factible";
  return (config.windowStart||"—")+" → "+(config.windowEnd||"—");
}

function objectiveLabel(config){
  return config.strategy==="service_first"?"Servicio primero":"Salida más temprana";
}

function rulesLabel(config,trips){
  const rules=config.temporalRules||[];
  if(!rules.length)return "Sin reglas específicas";
  const focused=focusedTripIds(config,trips).length;
  return rules.length+' '+(rules.length===1?'regla':'reglas')+' · '+focused+' '+(focused===1?'viaje afectado':'viajes afectados');
}

function markup({state,sourceRun,slaAvailable,config}){
  const stats=sourceStats(sourceRun);
  const serviceSelected=config.strategy==="service_first"&&slaAvailable;
  const auto=config.windowMode!=="custom";
  const focused=focusedTripIds(config,stats.trips).length;
  const rules=config.temporalRules||[];

  return '<div class="scheduling-config-v2">'
    +heroMarkup()
    +caseStrip(state)
    +'<section class="scheduling-section">'
      +sectionHead(1,"Alcance temporal","Todos los viajes aprobados en Asignación participan. Definí la ventana general y, si hace falta, aplicá reglas a grupos concretos sin excluirlos del Decision Case.",stats.totalTrips+' viajes heredados')
      +'<div class="scheduling-source">'
        +'<article><small>ASIGNACIÓN APROBADA</small><strong>'+num(stats.totalTrips)+' viajes</strong><span>Run '+esc(formatRunId(sourceRun.id))+'</span></article>'
        +'<article><small>RECURSOS YA DEFINIDOS</small><strong>'+num(stats.vehicles)+' vehículos</strong><span>No pueden reasignarse en esta decisión</span></article>'
        +'<article><small>DESTINOS</small><strong>'+num(stats.destinations)+'</strong><span>Provenientes de los viajes aprobados</span></article>'
      +'</div>'
      +'<div class="scheduling-window-mode">'
        +choice({name:"scheduling-window",value:"auto",title:"Ventana automática",copy:"El motor comienza en la primera fecha factible y encuentra el calendario completo respetando disponibilidad.",selected:auto,tag:"Recomendada"})
        +choice({name:"scheduling-window",value:"custom",title:"Ventana personalizada",copy:"Fijá con calendario el período dentro del cual deben ocurrir las fechas de salida de todos los despachos.",selected:!auto})
      +'</div>'
      +'<div class="scheduling-window-editor '+(!auto?'is-visible':'')+'" data-scheduling-window-editor>'
        +'<label class="scheduling-field"><span>Planificar desde</span><input type="date" data-scheduling-window-start value="'+esc(config.windowStart||"")+'"></label>'
        +'<label class="scheduling-field"><span>Planificar hasta</span><input type="date" data-scheduling-window-end value="'+esc(config.windowEnd||"")+'"></label>'
        +'<p class="scheduling-window-note">La ventana limita las fechas de salida. La llegada y el retorno del vehículo pueden ocurrir después del último día seleccionado.</p>'
      +'</div>'
      +focusRulesMarkup(config,stats.trips)
      +'<div class="scheduling-boundary"><span aria-hidden="true">✓</span><div><b>Asignación congelada.</b> Los filtros sólo priorizan o restringen fechas. Ninguna regla puede eliminar viajes, cambiar cargas ni reasignar vehículos.</div></div>'
    +'</section>'
    +'<section class="scheduling-section">'
      +sectionHead(2,"Objetivo del calendario","Elegí qué debe priorizar el motor cuando varios viajes compiten por el mismo recurso.","Objetivo")
      +'<div class="scheduling-objectives">'
        +choice({name:"scheduling-objective",value:"service_first",title:"Servicio primero",copy:slaAvailable?"Prioriza cumplir fechas objetivo; luego aplica las reglas de foco y reduce espera y duración total.":"No disponible porque delivery_due_date no está completo en Órdenes.",selected:serviceSelected,disabled:!slaAvailable,tag:slaAvailable?"SLA":"Sin datos"})
        +choice({name:"scheduling-objective",value:"earliest_dispatch",title:"Salida más temprana",copy:"Aplica primero las reglas de foco y luego minimiza la espera desde que carga y vehículo están disponibles.",selected:!serviceSelected,tag:"Operativo"})
      +'</div>'
    +'</section>'
    +'<section class="scheduling-section">'
      +sectionHead(3,"Política de recursos","Scheduling no vuelve a decidir la flota: respeta exactamente los vehículos aprobados en Asignación de carga.","Heredada y bloqueada")
      +'<div class="scheduling-resource-policy">'
        +'<div class="scheduling-inherited"><div class="scheduling-inherited__top"><strong>Usar los recursos de la asignación aprobada</strong><span class="scheduling-lock">Bloqueada</span></div><p>Vehículo, órdenes, producto y cantidades permanecen inmutables. Esta decisión sólo agrega fecha, secuencia y reglas temporales.</p></div>'
        +'<div class="scheduling-resource-stats"><div><strong>'+num(stats.resources.own)+'</strong><span>Propios</span></div><div><strong>'+num(stats.resources.third)+'</strong><span>Terceros</span></div></div>'
      +'</div>'
    +'</section>'
    +'<section class="scheduling-section">'
      +sectionHead(4,"Profundidad del análisis","Definí cuánto detalle querés recibir. El motor actual publica la planificación recomendada y su evidencia operativa.","Dashboard")
      +'<div class="scheduling-depth-grid">'
        +'<article class="scheduling-depth is-selected"><strong>Esencial</strong><p>Calendario recomendado, fechas, secuencia, reglas aplicadas, esperas, SLA y excepciones.</p><small>Activo</small></article>'
        +'<article class="scheduling-depth is-disabled"><strong>Comparativo</strong><p>Comparación formal entre estrategias temporales alternativas.</p><small>Próxima fase</small></article>'
        +'<article class="scheduling-depth is-disabled"><strong>Profundo</strong><p>Evidencia ampliada y sensibilidad de restricciones.</p><small>Próxima fase</small></article>'
      +'</div>'
    +'</section>'
    +'<footer class="scheduling-footer">'
      +'<div><small>PLANIFICACIÓN LISTA PARA REVISAR</small><strong>'+esc(objectiveLabel(config))+' · '+esc(windowLabel(config))+'</strong><span>'+num(stats.totalTrips)+' viajes · '+num(stats.vehicles)+' recursos · '+num(rules.length)+' reglas · '+num(focused)+' focalizados</span></div>'
      +'<button class="scheduling-primary" type="button" data-scheduling-review>Revisar y ejecutar →</button>'
    +'</footer>'
    +'<dialog class="scheduling-review" data-scheduling-review-dialog><form method="dialog">'
      +'<small>ANTES DE EJECUTAR</small><h2>Revisar planificación</h2>'
      +'<div class="scheduling-review-grid">'
        +'<p><strong>Entrada</strong><span>'+num(stats.totalTrips)+' viajes de Assignment · Run '+esc(formatRunId(sourceRun.id))+'</span></p>'
        +'<p><strong>Ventana</strong><span>'+esc(windowLabel(config))+'</span></p>'
        +'<p><strong>Reglas por foco</strong><span>'+esc(rulesLabel(config,stats.trips))+'</span></p>'
        +'<p><strong>Objetivo</strong><span>'+esc(objectiveLabel(config))+'</span></p>'
        +'<p><strong>Recursos</strong><span>Heredados de la asignación aprobada</span></p>'
        +'<p><strong>Profundidad</strong><span>Esencial</span></p>'
      +'</div>'
      +'<div data-scheduling-review-error></div>'
      +'<div class="scheduling-review-actions"><button value="cancel">Volver</button><button class="scheduling-primary" type="button" data-scheduling-execute>Generar planificación</button></div>'
    +'</form></dialog>'
  +'</div>';
}

function readinessSla(preflight){
  const decision=preflight?.decision_readiness?.decisions?.find(item=>item.id==="logistics_scheduling");
  return Boolean(decision?.capabilities?.find(item=>item.id==="sla")?.available);
}

function currentSourceRunId(state){
  const node=state.decisionCase?.nodes?.logistics_assignment||{};
  return node.approved_run_id||node.run_id||null;
}

async function restoreFromQuery(caseId,config){
  const query=new URLSearchParams(location.search);
  const runId=query.get("run_id");
  if(query.get("dda")!=="scheduling_v1"||!runId||restoredRuns.has(runId))return config;
  restoredRuns.add(runId);
  try{
    const run=await api('/api/runs/'+runId);
    const source=run?.result_json?.configuration||{};
    const metaCase=run?.result_json?.decision_case?.case_id;
    if(metaCase&&String(metaCase)!==String(caseId))return config;
    const restored={
      ...config,
      strategy:source.strategy||config.strategy,
      windowMode:(source.planning_window_start||source.planning_window_end)?"custom":"auto",
      windowStart:source.planning_window_start||"",
      windowEnd:source.planning_window_end||"",
      temporalRules:hydrateExecutionRules(source.temporal_rules||[]),
      analysisDepth:"essential",
    };
    writeConfig(caseId,restored);
    return restored;
  }catch{return config;}
}

function validateConfig(config,slaAvailable,trips=[]){
  if(config.strategy==="service_first"&&!slaAvailable)return "Servicio primero requiere fechas objetivo completas en Órdenes.";
  if(config.windowMode==="custom"){
    if(!config.windowStart||!config.windowEnd)return "Elegí fecha desde y fecha hasta para la ventana personalizada.";
    const start=new Date(config.windowStart+'T12:00:00');
    const end=new Date(config.windowEnd+'T12:00:00');
    if(Number.isNaN(start.getTime())||Number.isNaN(end.getTime()))return "La ventana temporal no tiene fechas válidas.";
    if(end<start)return "La fecha hasta no puede ser anterior a la fecha desde.";
    const days=Math.round((end-start)/86400000);
    if(days>365)return "La ventana temporal no puede superar 365 días.";
  }
  return validateFocusRules(config,trips);
}

function executionOptions(config){
  if(config.windowMode==="custom"){
    const start=new Date(config.windowStart+'T12:00:00');
    const end=new Date(config.windowEnd+'T12:00:00');
    const days=Math.max(1,Math.round((end-start)/86400000));
    return {max_horizon_days:Math.min(365,days)};
  }
  if((config.temporalRules||[]).some(rule=>rule.action==="window"))return {max_horizon_days:365};
  return {};
}

function executionConfiguration(config){
  return {
    strategy:config.strategy,
    use_delivery_due_dates:config.strategy==="service_first",
    planning_window_start:config.windowMode==="custom"?config.windowStart:null,
    planning_window_end:config.windowMode==="custom"?config.windowEnd:null,
    temporal_rules:executionRules(config),
  };
}

function showPending(runId){
  const url=new URL(location.href);
  url.searchParams.set("run_id",runId);
  url.searchParams.set("dda","scheduling_v1");
  history.replaceState(null,"",url);
  const dashboard=document.getElementById("dispatch-dashboard-root");
  if(dashboard){
    dashboard.innerHTML='<section class="dispatch-panel"><h1>Preparando tu planificación</h1><p role="status">Aplicando ventana temporal, filtros, restricciones y objetivo…</p><div class="dispatch-loading" aria-label="Procesando"></div><p>El Decision Case conserva la trazabilidad de esta corrida.</p></section>';
  }
  window.dationNavigate?.("decision-dashboard");
}

async function execute({state,sourceRun,slaAvailable,config,button,dialog,errorNode}){
  const trips=sourceStats(sourceRun).trips;
  const error=validateConfig(config,slaAvailable,trips);
  if(error){
    if(errorNode)errorNode.innerHTML='<p class="scheduling-error">'+esc(error)+'</p>';
    return;
  }
  const runId=crypto.randomUUID();
  button.disabled=true;
  button.textContent="Generando…";
  dialog?.close();
  showPending(runId);
  try{
    const run=await post('/api/runs?run_id='+runId,{
      orders_dataset_id:state.orders.id,
      fleet_dataset_id:state.fleet.id,
      source_run_id:sourceRun.id,
      configuration:executionConfiguration(config),
      options:executionOptions(config),
      decision_case:{
        case_id:state.decisionCase.id,
        node_id:"logistics_scheduling",
      },
    });
    window.DationDispatch?.show?.(run);
  }catch(errorRun){
    const url=new URL(location.href);
    url.searchParams.delete("run_id");
    url.searchParams.delete("dda");
    history.replaceState(null,"",url);
    window.dationNavigate?.("logistics-config");
    setTimeout(()=>alert(errorRun.message||"No se pudo generar la planificación."),0);
  }
}

function bind(root,context){
  const {state,sourceRun,slaAvailable}=context;
  const caseId=state.decisionCase.id;
  const trips=sourceStats(sourceRun).trips;
  let config=normalizeFocusConfig(context.config,trips);
  const rerender=()=>{
    writeConfig(caseId,config);
    root.innerHTML=markup({state,sourceRun,slaAvailable,config});
    bind(root,{...context,config});
  };

  root.querySelector('[data-scheduling-copy-case]')?.addEventListener("click",async()=>{
    try{
      await navigator.clipboard.writeText(String(caseId));
      const feedback=root.querySelector('[data-scheduling-copy-feedback]');
      if(feedback){feedback.textContent="Copiado";setTimeout(()=>feedback.textContent="",1200);}
    }catch{}
  });
  root.querySelector('[data-scheduling-change-data]')?.addEventListener("click",()=>window.dationNavigate?.("logistics-data"));

  root.querySelectorAll('input[name="scheduling-window"]').forEach(input=>{
    input.addEventListener("change",()=>{
      config={...config,windowMode:input.value};
      rerender();
    });
  });
  root.querySelector('[data-scheduling-window-start]')?.addEventListener("change",event=>{
    config={...config,windowStart:event.target.value};
    writeConfig(caseId,config);
    const footer=root.querySelector('.scheduling-footer strong');
    if(footer)footer.textContent=objectiveLabel(config)+' · '+windowLabel(config);
  });
  root.querySelector('[data-scheduling-window-end]')?.addEventListener("change",event=>{
    config={...config,windowEnd:event.target.value};
    writeConfig(caseId,config);
    const footer=root.querySelector('.scheduling-footer strong');
    if(footer)footer.textContent=objectiveLabel(config)+' · '+windowLabel(config);
  });

  bindFocusRuleEvents(root,{
    config,
    trips,
    onChange:next=>{
      config=next;
      rerender();
    },
  });

  root.querySelectorAll('input[name="scheduling-objective"]').forEach(input=>{
    input.addEventListener("change",()=>{
      config={...config,strategy:input.value};
      rerender();
    });
  });

  const dialog=root.querySelector('[data-scheduling-review-dialog]');
  root.querySelector('[data-scheduling-review]')?.addEventListener("click",()=>{
    const error=validateConfig(config,slaAvailable,trips);
    if(error){
      const footer=root.querySelector('.scheduling-footer');
      let message=footer.querySelector('.scheduling-error');
      if(!message){message=document.createElement('p');message.className='scheduling-error';footer.prepend(message);}
      message.textContent=error;
      return;
    }
    dialog?.showModal();
  });
  root.querySelector('[data-scheduling-execute]')?.addEventListener("click",event=>{
    execute({
      state,
      sourceRun,
      slaAvailable,
      config,
      button:event.currentTarget,
      dialog,
      errorNode:root.querySelector('[data-scheduling-review-error]'),
    });
  });
}

async function mount(root){
  if(mounting||root.querySelector('.scheduling-config-v2'))return;
  const state=workspace();
  if(state.activeNode!=="logistics_scheduling"||!state.decisionCase?.id)return;
  const sourceRunId=currentSourceRunId(state);
  if(!sourceRunId)return;
  mounting=true;
  root.innerHTML='<section class="dispatch-panel"><p role="status">Preparando la configuración temporal…</p><div class="dispatch-loading"></div></section>';
  try{
    let config=caseConfig(state.decisionCase.id);
    config=await restoreFromQuery(state.decisionCase.id,config);
    const [sourceRun,preflight]=await Promise.all([
      api('/api/runs/'+sourceRunId),
      post('/api/runs/preflight',{
        orders_dataset_id:state.orders.id,
        fleet_dataset_id:state.fleet.id,
        allow_third_party:true,
      }),
    ]);
    const slaAvailable=readinessSla(preflight);
    if(!slaAvailable&&config.strategy==="service_first")config={...config,strategy:"earliest_dispatch"};
    config=normalizeFocusConfig(config,sourceStats(sourceRun).trips);
    writeConfig(state.decisionCase.id,config);
    root.innerHTML=markup({state,sourceRun,slaAvailable,config});
    bind(root,{state,sourceRun,slaAvailable,config});
  }catch(error){
    root.innerHTML='<section class="dispatch-panel"><h1>No se pudo preparar Planificación</h1><p>'+esc(error.message||String(error))+'</p><button type="button" data-scheduling-retry>Reintentar</button></section>';
    root.querySelector('[data-scheduling-retry]')?.addEventListener("click",()=>{root.innerHTML="";mount(root);});
  }finally{
    mounting=false;
  }
}

function maybeMount(){
  if(window.dationGetCurrentView?.()!=="logistics-config")return;
  const state=workspace();
  if(state.activeNode!=="logistics_scheduling")return;
  const root=document.getElementById(ROOT_ID);
  if(!root||root.querySelector('.scheduling-config-v2'))return;
  if(!root.querySelector('.dispatch-scheduling-config'))return;
  mount(root);
}

function start(){
  ensureStyles();
  window.addEventListener("dation:view",()=>queueMicrotask(maybeMount));
  if(!observer){
    observer=new MutationObserver(()=>queueMicrotask(maybeMount));
    observer.observe(document.documentElement,{childList:true,subtree:true});
  }
  queueMicrotask(maybeMount);
}

if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start,{once:true});
else start();

export {executionConfiguration,executionOptions,validateConfig,windowLabel};
