import {api,esc,num,post} from "./shared.mjs";
import {
  configSummaryBar,
  decisionCaseCard,
  decisionChoiceCard,
  decisionDataFileCard,
  decisionDepthCard,
  decisionHero,
  decisionInfoNote,
  decisionSectionHeader,
} from "./decision-config-ui.mjs?v=scheduling-shared-phase2-v1";
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
  shared:"scheduling-shared-phase2-styles",
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
  ensureLink(STYLE_IDS.case,"/static/css/decision-map-case-v2.css?v=scheduling-shared-phase2-v1");
  ensureLink(STYLE_IDS.assignment,"/static/css/assignment-config-v2.css?v=scheduling-shared-phase2-v1");
  ensureLink(STYLE_IDS.own,"/static/css/scheduling-config-v2.css?v=scheduling-shared-phase2-v1");
  ensureLink(STYLE_IDS.shared,"/static/css/scheduling-config-shared-phase2.css?v=scheduling-shared-phase2-v1");
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
    focusRulesOpen:false,
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

function datasetFile(kind,dataset){
  const orders=kind==="orders";
  const total=Number(dataset?.row_count||0);
  return decisionDataFileCard({
    kind,
    dataset,
    countText:num(total)+" "+(orders?(total===1?"orden":"órdenes"):(total===1?"vehículo":"vehículos")),
  });
}

function caseStrip(state){
  return decisionCaseCard({
    caseId:state.decisionCase?.id,
    files:[
      datasetFile("orders",state.orders),
      datasetFile("fleet",state.fleet),
    ],
    copyHook:"data-scheduling-copy-case",
    feedbackHook:"data-scheduling-copy-feedback",
    changeHook:"data-scheduling-change-data",
    extraClass:"scheduling-case-strip",
  });
}

function heroMarkup(){
  return decisionHero({
    step:{number:3,label:"Configurar decisión"},
    decisionIndex:2,
    totalDecisions:3,
    title:"Definí cuándo querés despachar los viajes.",
    description:"Partí de la asignación aprobada, fijá la ventana temporal y elegí qué criterio debe ordenar el calendario. Cargas, cantidades y recursos quedan trazados desde la decisión anterior.",
    panelItems:[
      {label:"1 · PREGUNTA",description:"¿Cuándo conviene ejecutar los viajes ya definidos?",icon:"messageCircleQuestion"},
      {label:"2 · ENTREGA",description:"Calendario operativo + secuencia de despachos.",icon:"calendarClock"},
      {label:"3 · QUEDA PARA DESPUÉS",description:"La ejecución final se consolida en Asignación de vehículos.",icon:"truck"},
    ],
  });
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
  return rules.length+" "+(rules.length===1?"regla":"reglas")+" · "+focused+" "+(focused===1?"viaje afectado":"viajes afectados");
}

function scopeCurrent(config,trips){
  const rules=config.temporalRules||[];
  if(!rules.length)return config.windowMode==="custom"?"Ventana personalizada":"Ventana automática";
  return (config.windowMode==="custom"?"Ventana personalizada":"Ventana automática")+" · "+rules.length+" "+(rules.length===1?"regla":"reglas");
}

function resourceLabel(stats){
  return num(stats.vehicles)+" heredados";
}

function configProblem(config,slaAvailable,trips){
  const reason=validateConfig(config,slaAvailable,trips);
  if(!reason)return null;
  const objectiveIssue=reason.startsWith("Servicio primero");
  return {
    section:objectiveIssue?"scheduling-objective":"scheduling-scope",
    reason,
  };
}

function sourceSummary(stats,sourceRun){
  return '<div class="scheduling-source" aria-label="Entrada heredada de la asignación aprobada">'
    +'<article><small>ASIGNACIÓN APROBADA</small><strong>'+num(stats.totalTrips)+' viajes</strong><span>Run '+esc(formatRunId(sourceRun.id))+'</span></article>'
    +'<article><small>RECURSOS YA DEFINIDOS</small><strong>'+num(stats.vehicles)+' vehículos</strong><span>No pueden reasignarse en esta decisión</span></article>'
    +'<article><small>DESTINOS</small><strong>'+num(stats.destinations)+'</strong><span>Provenientes de los viajes aprobados</span></article>'
  +'</div>';
}

function focusDisclosure(config,trips){
  const rules=config.temporalRules||[];
  const focused=focusedTripIds(config,trips).length;
  const open=Boolean(config.focusRulesOpen);
  const summary=rules.length
    ?rules.length+" "+(rules.length===1?"regla":"reglas")+" · "+focused+" "+(focused===1?"viaje":"viajes")
    :"Opcional";
  return '<div class="scheduling-focus-disclosure '+(open?"is-open":"")+'">'
    +'<button type="button" class="scheduling-focus-disclosure__toggle" data-scheduling-focus-toggle aria-expanded="'+open+'">'
      +'<span class="scheduling-focus-disclosure__icon">'
        +'<svg class="assignment-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16l-6 7v5l-4 2v-7Z"/></svg>'
      +'</span>'
      +'<span class="scheduling-focus-disclosure__copy"><small>REGLAS POR FOCO</small><strong>Aplicá condiciones sólo cuando necesites priorizar un grupo</strong><span>Destino, origen, vehículo, tipo de recurso o producto. Los viajes nunca se eliminan del caso.</span></span>'
      +'<em>'+esc(summary)+'</em>'
      +'<svg class="scheduling-focus-disclosure__chevron assignment-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>'
    +'</button>'
    +'<div class="scheduling-focus-disclosure__body" '+(open?"":"hidden")+'>'+focusRulesMarkup(config,trips)+'</div>'
  +'</div>';
}

function scopeSection(config,stats,sourceRun){
  const auto=config.windowMode!=="custom";
  return '<section class="assignment-section scheduling-section" id="scheduling-scope" data-config-section="scope">'
    +decisionSectionHeader({
      number:"01",
      eyebrow:"ALCANCE",
      title:"Alcance temporal",
      copy:"Todos los viajes aprobados participan. Definí la ventana general y abrí reglas por foco sólo si necesitás priorizar o restringir un subconjunto.",
      icon:"calendarRange",
      current:scopeCurrent(config,stats.trips),
    })
    +sourceSummary(stats,sourceRun)
    +'<div class="assignment-objective-grid scheduling-window-mode">'
      +decisionChoiceCard({
        className:"scheduling-window-card",
        icon:"calendarRange",
        title:"Ventana automática",
        copy:"El motor comienza en la primera fecha factible y encuentra el calendario completo respetando disponibilidad.",
        selected:auto,
        tags:["Recomendada"],
        attributes:{"data-scheduling-window-mode":"auto"},
      })
      +decisionChoiceCard({
        className:"scheduling-window-card",
        icon:"calendarClock",
        title:"Ventana personalizada",
        copy:"Fijá el período dentro del cual deben ocurrir las fechas de salida de todos los despachos.",
        selected:!auto,
        attributes:{"data-scheduling-window-mode":"custom"},
      })
    +'</div>'
    +'<div class="scheduling-window-editor '+(!auto?"is-visible":"")+'" data-scheduling-window-editor>'
      +'<label class="scheduling-field"><span>Planificar desde</span><input type="date" data-scheduling-window-start value="'+esc(config.windowStart||"")+'"></label>'
      +'<label class="scheduling-field"><span>Planificar hasta</span><input type="date" data-scheduling-window-end value="'+esc(config.windowEnd||"")+'"></label>'
      +'<p class="scheduling-window-note">La ventana limita las fechas de salida. La llegada y el retorno del vehículo pueden ocurrir después del último día seleccionado.</p>'
    +'</div>'
    +focusDisclosure(config,stats.trips)
    +decisionInfoNote({
      icon:"lock",
      title:"Asignación congelada.",
      copy:"Los filtros y reglas sólo priorizan o restringen fechas. Ninguna regla puede eliminar viajes, cambiar cargas ni reasignar vehículos.",
      className:"scheduling-boundary-note",
    })
  +'</section>';
}

function objectiveSection(config,slaAvailable){
  const serviceSelected=config.strategy==="service_first"&&slaAvailable;
  return '<section class="assignment-section scheduling-section" id="scheduling-objective" data-config-section="objective">'
    +decisionSectionHeader({
      number:"02",
      eyebrow:"OBJETIVO",
      title:"Objetivo del calendario",
      copy:"Elegí qué debe priorizar el motor cuando varios viajes compiten por el mismo recurso.",
      icon:"target",
      current:objectiveLabel(config),
    })
    +'<div class="assignment-objective-grid scheduling-objectives">'
      +decisionChoiceCard({
        className:"scheduling-objective-card",
        icon:"target",
        title:"Servicio primero",
        copy:slaAvailable
          ?"Prioriza cumplir fechas objetivo; luego aplica las reglas de foco y reduce espera y duración total."
          :"No disponible porque delivery_due_date no está completo en Órdenes.",
        selected:serviceSelected,
        disabled:!slaAvailable,
        disabledTitle:!slaAvailable?"Requiere fechas objetivo completas en Órdenes":"",
        tags:[slaAvailable?"SLA":"Sin datos"],
        attributes:{"data-scheduling-objective":"service_first"},
      })
      +decisionChoiceCard({
        className:"scheduling-objective-card",
        icon:"clock",
        title:"Salida más temprana",
        copy:"Aplica primero las reglas de foco y luego minimiza la espera desde que carga y vehículo están disponibles.",
        selected:!serviceSelected,
        tags:["Operativo"],
        attributes:{"data-scheduling-objective":"earliest_dispatch"},
      })
    +'</div>'
  +'</section>';
}

function resourceSection(stats){
  return '<section class="assignment-section scheduling-section" id="scheduling-resources" data-config-section="resources">'
    +decisionSectionHeader({
      number:"03",
      eyebrow:"RECURSOS",
      title:"Política de recursos",
      copy:"Planificación no vuelve a decidir la flota: respeta exactamente los vehículos aprobados en Asignación de carga.",
      icon:"truck",
      current:"Heredada y bloqueada",
    })
    +'<div class="scheduling-resource-policy">'
      +decisionChoiceCard({
        className:"scheduling-resource-card",
        icon:"lock",
        title:"Usar los recursos de la asignación aprobada",
        copy:"Vehículo, órdenes, producto y cantidades permanecen inmutables. Esta decisión sólo agrega fecha, secuencia y reglas temporales.",
        selected:true,
        locked:true,
        tags:["Bloqueada"],
        attributes:{"data-scheduling-resource-policy":"inherited"},
      })
      +'<div class="scheduling-resource-stats" aria-label="Composición de recursos heredados">'
        +'<div><strong>'+num(stats.resources.own)+'</strong><span>Propios</span></div>'
        +'<div><strong>'+num(stats.resources.third)+'</strong><span>Terceros</span></div>'
      +'</div>'
    +'</div>'
  +'</section>';
}

function depthSection(config){
  const depths={
    essential:{
      label:"Esencial",
      copy:"Calendario recomendado, fechas, secuencia, reglas aplicadas, esperas, SLA y excepciones.",
      rows:[["Calendario recomendado",true],["SLA y excepciones",true],["Comparación de estrategias",false]],
    },
    comparative:{
      label:"Comparativo",
      copy:"Comparación formal entre estrategias temporales alternativas.",
      rows:[["Calendario recomendado",false],["SLA y excepciones",false],["Comparación de estrategias",false]],
    },
    deep:{
      label:"Profundo",
      copy:"Evidencia ampliada y sensibilidad de restricciones.",
      rows:[["Calendario recomendado",false],["SLA y excepciones",false],["Comparación de estrategias",false]],
    },
  };
  return '<section class="assignment-section scheduling-section" id="scheduling-dashboard" data-config-section="dashboard">'
    +decisionSectionHeader({
      number:"04",
      eyebrow:"DASHBOARD",
      title:"Profundidad del análisis",
      copy:"Definí cuánto detalle querés recibir. En esta versión Planificación publica el análisis Esencial.",
      icon:"layoutDashboard",
      current:"Esencial",
    })
    +'<div class="assignment-depth-grid scheduling-depth-grid">'
      +decisionDepthCard({key:"essential",item:depths.essential,selected:config.analysisDepth==="essential",tag:"Activo"})
      +decisionDepthCard({key:"comparative",item:depths.comparative,disabled:true,tag:"Próximamente",disabledTitle:"Se habilita en futuras versiones"})
      +decisionDepthCard({key:"deep",item:depths.deep,disabled:true,tag:"Próximamente",disabledTitle:"Se habilita en futuras versiones"})
    +'</div>'
  +'</section>';
}

function summaryBar(config,stats,slaAvailable){
  const problem=configProblem(config,slaAvailable,stats.trips);
  return configSummaryBar({
    ready:!problem,
    reason:problem?.reason||"",
    ctaLabel:"Revisar y ejecutar",
    reviewHook:"data-scheduling-review",
    extraClass:"scheduling-summary-bar",
    chips:[
      {target:"scheduling-scope",icon:"calendarRange",label:"Alcance",value:scopeCurrent(config,stats.trips)},
      {target:"scheduling-objective",icon:"target",label:"Objetivo",value:objectiveLabel(config)},
      {target:"scheduling-resources",icon:"truck",label:"Recursos",value:resourceLabel(stats)},
      {target:"scheduling-dashboard",icon:"layoutDashboard",label:"Dashboard",value:"Esencial"},
    ],
  });
}

function reviewDialog(config,stats,sourceRun){
  return '<dialog class="dispatch dispatch-review assignment-review-dialog scheduling-review" data-scheduling-review-dialog><form method="dialog">'
    +'<span class="assignment-section__eyebrow">ANTES DE EJECUTAR</span><h2>Revisar planificación</h2>'
    +'<div class="dispatch-review-summary scheduling-review-grid">'
      +'<p><strong>Entrada</strong><span>'+num(stats.totalTrips)+' viajes de Assignment · Run '+esc(formatRunId(sourceRun.id))+'</span></p>'
      +'<p><strong>Ventana</strong><span>'+esc(windowLabel(config))+'</span></p>'
      +'<p><strong>Reglas por foco</strong><span>'+esc(rulesLabel(config,stats.trips))+'</span></p>'
      +'<p><strong>Objetivo</strong><span>'+esc(objectiveLabel(config))+'</span></p>'
      +'<p><strong>Recursos</strong><span>Heredados de la asignación aprobada</span></p>'
      +'<p><strong>Profundidad</strong><span>Esencial</span></p>'
    +'</div>'
    +'<div data-scheduling-review-error></div>'
    +'<div class="dispatch-actions scheduling-review-actions"><button value="cancel">Volver</button><button class="scheduling-primary" type="button" data-scheduling-execute>Generar planificación</button></div>'
  +'</form></dialog>';
}

function markup({state,sourceRun,slaAvailable,config}){
  const stats=sourceStats(sourceRun);
  return '<div class="scheduling-config-v2 assignment-config-v2">'
    +heroMarkup()
    +caseStrip(state)
    +'<main class="assignment-config-sections scheduling-config-sections">'
      +scopeSection(config,stats,sourceRun)
      +objectiveSection(config,slaAvailable)
      +resourceSection(stats)
      +depthSection(config)
    +'</main>'
    +summaryBar(config,stats,slaAvailable)
    +reviewDialog(config,stats,sourceRun)
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
    const run=await api("/api/runs/"+runId);
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
      focusRulesOpen:Boolean(source.temporal_rules?.length),
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
    const start=new Date(config.windowStart+"T12:00:00");
    const end=new Date(config.windowEnd+"T12:00:00");
    if(Number.isNaN(start.getTime())||Number.isNaN(end.getTime()))return "La ventana temporal no tiene fechas válidas.";
    if(end<start)return "La fecha hasta no puede ser anterior a la fecha desde.";
    const days=Math.round((end-start)/86400000);
    if(days>365)return "La ventana temporal no puede superar 365 días.";
  }
  return validateFocusRules(config,trips);
}

function executionOptions(config){
  if(config.windowMode==="custom"){
    const start=new Date(config.windowStart+"T12:00:00");
    const end=new Date(config.windowEnd+"T12:00:00");
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
    const run=await post("/api/runs?run_id="+runId,{
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

function scrollToProblem(problem){
  const target=document.getElementById(problem.section);
  if(!target)return;
  target.classList.remove("is-attention");
  void target.offsetWidth;
  target.classList.add("is-attention");
  target.scrollIntoView({behavior:"smooth",block:"center"});
  window.setTimeout(()=>target.classList.remove("is-attention"),1800);
}

function bind(root,context){
  const {state,sourceRun,slaAvailable}=context;
  const caseId=state.decisionCase.id;
  const stats=sourceStats(sourceRun);
  const trips=stats.trips;
  let config=normalizeFocusConfig(context.config,trips);
  const rerender=()=>{
    writeConfig(caseId,config);
    root.innerHTML=markup({state,sourceRun,slaAvailable,config});
    bind(root,{...context,config});
  };

  root.querySelector("[data-scheduling-copy-case]")?.addEventListener("click",async()=>{
    try{
      await navigator.clipboard.writeText(String(caseId));
      const feedback=root.querySelector("[data-scheduling-copy-feedback]");
      if(feedback){feedback.textContent="Copiado";setTimeout(()=>feedback.textContent="",1200);}
    }catch{}
  });
  root.querySelector("[data-scheduling-change-data]")?.addEventListener("click",()=>window.dationNavigate?.("logistics-data"));

  root.querySelectorAll("[data-scheduling-window-mode]").forEach(button=>{
    button.addEventListener("click",()=>{
      if(button.disabled)return;
      config={...config,windowMode:button.dataset.schedulingWindowMode};
      rerender();
    });
  });

  root.querySelector("[data-scheduling-window-start]")?.addEventListener("change",event=>{
    config={...config,windowStart:event.target.value};
    rerender();
  });
  root.querySelector("[data-scheduling-window-end]")?.addEventListener("change",event=>{
    config={...config,windowEnd:event.target.value};
    rerender();
  });

  root.querySelector("[data-scheduling-focus-toggle]")?.addEventListener("click",()=>{
    config={...config,focusRulesOpen:!config.focusRulesOpen};
    rerender();
  });

  bindFocusRuleEvents(root,{
    config,
    trips,
    onChange:next=>{
      config={...next,focusRulesOpen:true};
      rerender();
    },
  });

  root.querySelectorAll("[data-scheduling-objective]").forEach(button=>{
    button.addEventListener("click",()=>{
      if(button.disabled)return;
      config={...config,strategy:button.dataset.schedulingObjective};
      rerender();
    });
  });

  root.querySelectorAll("[data-summary-target]").forEach(button=>button.addEventListener("click",()=>{
    document.getElementById(button.dataset.summaryTarget)?.scrollIntoView({behavior:"smooth",block:"center"});
  }));

  const dialog=root.querySelector("[data-scheduling-review-dialog]");
  root.querySelector("[data-scheduling-review]")?.addEventListener("click",()=>{
    const problem=configProblem(config,slaAvailable,trips);
    if(problem){
      if(problem.section==="scheduling-scope"&&(config.temporalRules||[]).length)config={...config,focusRulesOpen:true};
      writeConfig(caseId,config);
      scrollToProblem(problem);
      return;
    }
    dialog?.showModal();
  });
  root.querySelector("[data-scheduling-execute]")?.addEventListener("click",event=>{
    execute({
      state,
      sourceRun,
      slaAvailable,
      config,
      button:event.currentTarget,
      dialog,
      errorNode:root.querySelector("[data-scheduling-review-error]"),
    });
  });
}

async function mount(root){
  if(mounting||root.querySelector(".scheduling-config-v2"))return;
  const state=workspace();
  if(state.activeNode!=="logistics_scheduling"||!state.decisionCase?.id)return;
  const sourceRunId=currentSourceRunId(state);
  if(!sourceRunId)return;
  mounting=true;
  root.className="dispatch dispatch-upload-pro assignment-config-root scheduling-config-root";
  root.innerHTML='<section class="dispatch-panel"><p role="status">Preparando la configuración temporal…</p><div class="dispatch-loading"></div></section>';
  try{
    let config=caseConfig(state.decisionCase.id);
    config=await restoreFromQuery(state.decisionCase.id,config);
    const [sourceRun,preflight]=await Promise.all([
      api("/api/runs/"+sourceRunId),
      post("/api/runs/preflight",{
        orders_dataset_id:state.orders.id,
        fleet_dataset_id:state.fleet.id,
        allow_third_party:true,
      }),
    ]);
    const slaAvailable=readinessSla(preflight);
    if(!slaAvailable&&config.strategy==="service_first")config={...config,strategy:"earliest_dispatch"};
    config={...normalizeFocusConfig(config,sourceStats(sourceRun).trips),analysisDepth:"essential"};
    writeConfig(state.decisionCase.id,config);
    root.innerHTML=markup({state,sourceRun,slaAvailable,config});
    bind(root,{state,sourceRun,slaAvailable,config});
  }catch(error){
    root.innerHTML='<section class="dispatch-panel"><h1>No se pudo preparar Planificación</h1><p>'+esc(error.message||String(error))+'</p><button type="button" data-scheduling-retry>Reintentar</button></section>';
    root.querySelector("[data-scheduling-retry]")?.addEventListener("click",()=>{root.innerHTML="";mount(root);});
  }finally{
    mounting=false;
  }
}

function maybeMount(){
  if(window.dationGetCurrentView?.()!=="logistics-config")return;
  const state=workspace();
  if(state.activeNode!=="logistics_scheduling")return;
  const root=document.getElementById(ROOT_ID);
  if(!root||root.querySelector(".scheduling-config-v2"))return;
  if(!root.querySelector(".dispatch-scheduling-config"))return;
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
