import {esc,num,api,post,errorBox} from './shared.mjs';
import {render as dashboard} from './dashboard.mjs';
import {mountUploadScreen} from './upload/index.mjs';
import {renderDecisionMap} from './decision-map.mjs';
import {mountAssignmentConfig,filterPayload,normalizeRawWeights} from './assignment-config.mjs';
import {STATUS,createDecisionCase,replaceInputs,transitionNode,inputSignature,caseRef,deriveDecisionNodes,continuationState,getCaseTransitionNotice} from './decision-case.mjs';
import {DECISION_META} from './decision-ui.mjs';

const KEY='dation.dispatch.workspace.v5';
const NAV_VERSION='workspace-nav-v1';
const DECISION_LABELS=Object.fromEntries(
  Object.entries(DECISION_META).map(([id,meta])=>[id,meta.label])
);
const PRIORITY_KEYS=['trips','cost','own_fleet','co2'];
const CORE_DIMENSIONS=['trips','own_fleet'];
const PRESETS={
  min_trips:{trips:100,cost:0,own_fleet:0,co2:0},
  min_cost:{trips:0,cost:100,own_fleet:0,co2:0},
  max_own_fleet:{trips:0,cost:0,own_fleet:100,co2:0},
  min_co2:{trips:0,cost:0,own_fleet:0,co2:100},
};
const OBJECTIVE_DIMENSION={
  min_trips:'trips',
  min_cost:'cost',
  max_own_fleet:'own_fleet',
  min_co2:'co2',
};
const OBJECTIVE_LABELS={
  min_trips:'Menor cantidad de viajes',
  min_cost:'Costo mínimo',
  max_own_fleet:'Mayor uso de flota propia',
  min_co2:'CO₂ mínimo',
  balanced:'Balanceado',
  custom:'Personalizado',
};
const DIMENSION_LABELS={
  trips:'Cantidad de viajes',
  cost:'Costo operativo',
  own_fleet:'Uso de flota propia',
  co2:'Emisiones CO₂',
};

function balancedWeights(dimensions){
  const out=Object.fromEntries(PRIORITY_KEYS.map(k=>[k,0]));
  const base=Math.floor(100/dimensions.length);
  let rest=100-base*dimensions.length;
  dimensions.forEach(k=>{
    out[k]=base+(rest>0?1:0);
    rest=Math.max(0,rest-1);
  });
  return out;
}
function normalizeWeights(weights,dimensions){
  const out=Object.fromEntries(PRIORITY_KEYS.map(k=>[k,0]));
  const total=dimensions.reduce((s,k)=>s+(Number(weights?.[k])||0),0);
  if(total<=0)return balancedWeights(dimensions);
  const raw=dimensions.map((k,i)=>{
    const v=100*(Number(weights?.[k])||0)/total;
    return {k,i,base:Math.floor(v),fraction:v-Math.floor(v)};
  });
  let missing=100-raw.reduce((s,x)=>s+x.base,0);
  [...raw].sort((a,b)=>b.fraction-a.fraction||a.i-b.i)
    .slice(0,missing).forEach(x=>x.base+=1);
  raw.forEach(x=>out[x.k]=x.base);
  return out;
}
function presetWeights(objective,dimensions){
  if(objective==='balanced')return balancedWeights(dimensions);
  const out=Object.fromEntries(PRIORITY_KEYS.map(k=>[k,0]));
  const key=OBJECTIVE_DIMENSION[objective];
  if(key)out[key]=100;
  return out;
}

import {readResource,resourceUrl,runDecisionState,runContext} from './navigation.mjs';
import {createScope,disposeScope} from './lifecycle.mjs';
import {runPolling} from './run-polling.mjs';
import {restoreRunConfiguration,mount as mountSchedulingConfig} from './scheduling-config-v2.mjs';
import {decorateDecisionMap,mountTraceability} from './traceability-controller.mjs';
let saved={};
try{saved=JSON.parse(sessionStorage.getItem(KEY)||'{}');}catch{}
if(!saved||typeof saved!=='object'||Array.isArray(saved))saved={};
const restoredDimensions=Array.isArray(saved.dimensions)
  ?PRIORITY_KEYS.filter(k=>saved.dimensions.includes(k))
  :[...CORE_DIMENSIONS];
const validObjectives=['min_trips','min_cost','max_own_fleet','min_co2','balanced','custom'];
const savedResourceMode=['own','mixed','outsourced'].includes(saved.resourceMode)
  ?saved.resourceMode
  :(saved.allow===false?'own':'mixed');
const state={
  orders:saved.orders||null,
  fleet:saved.fleet||null,
  dimensions:restoredDimensions.length?restoredDimensions:[...CORE_DIMENSIONS],
  weights:saved.weights||balancedWeights(restoredDimensions.length?restoredDimensions:CORE_DIMENSIONS),
  customWeights:saved.customWeights||null,
  lastPreset:saved.lastPreset||'balanced',
  objective:validObjectives.includes(saved.objective)?saved.objective:'balanced',
  allow:savedResourceMode!=='own',
  resourceMode:savedResourceMode,
  scopeFilters:Array.isArray(saved.scopeFilters)?saved.scopeFilters:[],
  decisions:saved.decisions||{},
  configured:Boolean(saved.configured),
  decisionCase:saved.decisionCase||null,
  activeNode:saved.navigationVersion===NAV_VERSION
    ?(saved.activeNode||null)
    :(saved.activeNode||null),
  schedulingUseDueDates:saved.schedulingUseDueDates??true,
  configPreview:null,
  preflight:null,
  available:false,
  run:null,
};
if(OBJECTIVE_DIMENSION[state.objective]&&!state.dimensions.includes(OBJECTIVE_DIMENSION[state.objective]))state.objective='balanced';
state.weights=state.objective==='custom'
  ?normalizeWeights(state.weights,state.dimensions)
  :presetWeights(state.objective,state.dimensions);
let pollGeneration=0,routeGeneration=0,routeController=null,resource=null,transitionCaseId=null;const roots={};
const renderView=window.dationNavigate;
const DRAFT_KEY='dation.dispatch.drafts.v1';
let drafts={};try{drafts=JSON.parse(sessionStorage.getItem(DRAFT_KEY)||'{}');}catch{}
if(!drafts||typeof drafts!=='object'||Array.isArray(drafts))drafts={};
const draftFields=['dimensions','weights','customWeights','lastPreset','objective','resourceMode','allow','scopeFilters','decisions','configured'];
// Restore only active criteria, including drafts saved by earlier versions.
const cleanDraft=value=>Object.fromEntries(draftFields.filter(key=>Object.hasOwn(value||{},key)).map(key=>[key,value[key]]));
drafts=Object.fromEntries(Object.entries(drafts).map(([id,value])=>[id,cleanDraft(value)]));
try{sessionStorage.setItem(DRAFT_KEY,JSON.stringify(drafts));}catch{}
function saveDraft(){if(state.decisionCase?.id){drafts[state.decisionCase.id]=Object.fromEntries(draftFields.map(key=>[key,state[key]]));try{sessionStorage.setItem(DRAFT_KEY,JSON.stringify(drafts));}catch{}}}

function persist(){
  try{
    sessionStorage.setItem(KEY,JSON.stringify({
      orders:state.orders,
      fleet:state.fleet,
      dimensions:state.dimensions,
      weights:state.weights,
      customWeights:state.customWeights,
      lastPreset:state.lastPreset,
      objective:state.objective,
      allow:state.allow,
      resourceMode:state.resourceMode,
      scopeFilters:state.scopeFilters,
      decisions:state.decisions,
      configured:state.configured,
      decisionCase:state.decisionCase,
      activeNode:state.activeNode,
      schedulingUseDueDates:state.schedulingUseDueDates,
      navigationVersion:NAV_VERSION,
    }));
  }catch{}
}
function root(view,id){const parent=document.querySelector('[data-view-panel="'+view+'"]');let node=document.getElementById(id);if(!node){node=document.createElement('div');node.id=id;node.className='dispatch';parent.append(node);}return node;}
function assignmentEvidence(){
  return state.preflight?.decision_readiness?.decisions?.find(item=>item.id==='logistics_assignment')||null;
}
function schedulingEvidence(){
  return state.preflight?.decision_readiness?.decisions?.find(item=>item.id==='logistics_scheduling')||null;
}
function schedulingSlaAvailable(){
  return Boolean(
    schedulingEvidence()?.capabilities?.find(item=>item.id==='sla')?.available
  );
}
function assignmentCapabilities(){
  return Object.fromEntries(
    (assignmentEvidence()?.capabilities||[]).map(item=>[item.id,item])
  );
}
function availableDimensions(){
  const capabilities=assignmentCapabilities();
  return PRIORITY_KEYS.filter(key=>capabilities[key]?.available);
}
function syncDimensionsToEvidence({initialize=false}={}){
  const available=availableDimensions();
  if(!available.length)return;
  if(initialize&&!state.configured){
    state.dimensions=[...available];
    state.objective='balanced';
    state.weights=balancedWeights(state.dimensions);
    state.customWeights=null;
    state.lastPreset='balanced';
    state.configured=true;
    persist();
    return;
  }
  state.dimensions=state.dimensions.filter(key=>available.includes(key));
  if(!state.dimensions.length){
    state.dimensions=CORE_DIMENSIONS.filter(key=>available.includes(key));
  }
  if(!state.dimensions.length){
    state.dimensions=[available[0]];
  }
  const required=OBJECTIVE_DIMENSION[state.objective];
  if(required&&!available.includes(required))state.objective='balanced';
  state.weights=state.objective==='custom'
    ?normalizeWeights(state.weights,state.dimensions)
    :presetWeights(state.objective,state.dimensions);
}
function ready(){return !!(state.available&&state.orders&&state.fleet&&state.preflight?.valid);}
function resetAssignmentConfiguration(){
  state.configured=false;
  state.decisions={};
  state.dimensions=[...CORE_DIMENSIONS];
  state.objective='balanced';
  state.weights=balancedWeights(state.dimensions);
  state.customWeights=null;
  state.lastPreset='balanced';
  state.resourceMode='mixed';
  state.allow=true;
  state.scopeFilters=[];
  state.configPreview=null;
}
function ensureDecisionCase(){
  const signature=inputSignature(state.orders,state.fleet);
  if(!signature){
    state.decisionCase=null;
    state.activeNode=null;
    window.dationSetDecisionContext?.(null);
    persist();
    return null;
  }
  if(!state.decisionCase){
    state.decisionCase=createDecisionCase(crypto.randomUUID(),state.orders,state.fleet);
    transitionCaseId=null;
    state.activeNode=null;
    window.dationSetDecisionContext?.(null);
  }else if(state.decisionCase.signature!==signature){
    state.decisionCase=replaceInputs(state.decisionCase,crypto.randomUUID(),state.orders,state.fleet);
    transitionCaseId=state.decisionCase.id;
    state.run=null;
    resetAssignmentConfiguration();
    state.activeNode=null;
    state.schedulingUseDueDates=true;
    window.dationSetDecisionContext?.(null);
  }
  persist();
  return state.decisionCase;
}
function decisionContext(nodeId){
  if(!nodeId){
    window.dationSetDecisionContext?.(null);
    return;
  }
  const node=state.decisionCase?.nodes?.[nodeId]||null;
  window.dationSetDecisionContext?.({
    id:nodeId,
    label:DECISION_LABELS[nodeId]||'Decisión',
    stepLabel:nodeId==='logistics_assignment'?'Decisión 01':nodeId==='logistics_scheduling'?'Decisión 02':'Decisión 03',
    hasRun:Boolean(node?.run_id),
    status:node?.status||null,
  });
}
function navigate(view,options={}){persist();window.dationSetDataReady(ready());return navigateResource(view,options);}
async function startNewDecision(){
  transitionCaseId=null;
  saveDraft();
  resetAssignmentConfiguration();
  Object.assign(state,{orders:null,fleet:null,decisionCase:null,run:null,activeNode:null,
    preflight:null,configPreview:null,configured:false,decisions:{},schedulingUseDueDates:true});
  decisionContext(null);
  window.dationSetDataReady(false);
  persist();
  return navigateResource('logistics-data',{caseId:null,nodeId:null,runId:null});
}

async function dashboardContinuation(run,nodeId,generation){
  if(!nodeId||!state.decisionCase)return null;
  if(runDecisionState(run,state.decisionCase,nodeId)!=='approved')return null;
  if(!state.preflight)await preflight();
  if(generation!==routeGeneration)return null;
  return continuationState(state.decisionCase,nodeId,run.id,state.preflight?.decision_readiness,DECISION_META);
}

function urlRun(id,schema='assignment_v1'){resource={view:'decision-dashboard',caseId:state.decisionCase?.id||null,nodeId:schema==='scheduling_v1'?'logistics_scheduling':'logistics_assignment',runId:id};history.replaceState(null,'',resourceUrl(location.href,resource));}

async function preflight(){
  const generation=routeGeneration;
  state.preflight=null;
  window.dationSetDataReady(false);
  if(!state.orders||!state.fleet)return;
  const result=await post('/api/runs/preflight',{
    orders_dataset_id:state.orders.id,
    fleet_dataset_id:state.fleet.id,
    allow_third_party:state.resourceMode!=='own',
  },{signal:routeController?.signal});
  if(generation!==routeGeneration)return;
  state.preflight=result;
  state.allow=state.resourceMode!=='own';
  ensureDecisionCase();
  window.dationSetDataReady(ready());
  persist();
}
async function loadData(){
  const generation=routeGeneration;
  await mountUploadScreen(
    roots.data,
    {
      state,
      persist,
      runPreflight:preflight,
      onNext:()=>{ensureDecisionCase();navigate('logistics-map');},
      isReady:ready,
      isCurrent:()=>generation===routeGeneration,
    },
  );
}
async function openCaseResult(nodeId='logistics_assignment'){const runId=state.decisionCase?.nodes?.[nodeId]?.run_id;if(runId)return openRun(runId,nodeId);}

async function loadDecisionMap(){
  const generation=routeGeneration;
  const node=roots.map;
  if(!state.orders||!state.fleet){
    node.innerHTML='<section class="dispatch-panel"><h1>Mapa de decisiones</h1><p>Primero cargá Órdenes y Flota para crear un Decision Case.</p><button data-data>Ir al Data Pack</button></section>';
    node.querySelector('[data-data]').onclick=()=>navigate('logistics-data');
    return;
  }
  try{
    if(!state.preflight)await preflight();
    if(generation!==routeGeneration)return;
    ensureDecisionCase();
    // Register the case before execution so the API picker and deep links also
    // work for a freshly validated Data Pack. The endpoint is idempotent by ID.
    if(!state.decisionCase.persisted){
      const current=state.decisionCase;
      await post('/api/decision-cases',{
        id:current.id,orders_dataset_id:state.orders.id,fleet_dataset_id:state.fleet.id,state:current,
      },{signal:routeController?.signal});
      if(generation!==routeGeneration)return;
      state.decisionCase={...current,persisted:true};
      resource={...resource,caseId:current.id,nodeId:null,runId:null};
      history.replaceState(null,'',resourceUrl(location.href,resource));
      persist();
    }
    let predecessor=null;
    if(transitionCaseId===state.decisionCase.id&&state.decisionCase.stale_predecessor?.id){
      try{predecessor=await api('/api/decision-cases/'+state.decisionCase.stale_predecessor.id,{signal:routeController?.signal});}
      catch(error){if(error.status!==404)throw error;}
      if(generation!==routeGeneration)return;
    }
    const transitionNotice=getCaseTransitionNotice({decisionCase:state.decisionCase,predecessor,transitionCaseId});
    state.decisionCase={
      ...state.decisionCase,
      nodes:deriveDecisionNodes(
        state.decisionCase,
        state.preflight?.decision_readiness,
      ),
    };
    persist();
    await renderDecisionMap(node,{
      decisionCase:state.decisionCase,
      readiness:state.preflight?.decision_readiness,
      orders:state.orders,
      fleet:state.fleet,
      transitionNotice,
      onConfigure:(nodeId)=>{
        state.activeNode=nodeId||'logistics_assignment';
        decisionContext(state.activeNode);
        persist();
        navigate('logistics-config');
      },
      onOpenResult:openCaseResult,
      onData:()=>navigate('logistics-data'),
      onSelectCase:trigger=>window.DationDispatch.openDecisionMap({trigger,forceSelector:true}),
    });
    if(generation===routeGeneration)decorateDecisionMap(node);
  }catch(error){
    if(generation!==routeGeneration)return;
    errorBox(node,error,loadDecisionMap);
  }
}
function decimalWeights(){
  const weights=state.objective==='custom'
    ?normalizeRawWeights(state.customWeights||state.weights,state.dimensions)
    :presetWeights(state.objective,state.dimensions);
  return Object.fromEntries(PRIORITY_KEYS.map(k=>[k,(weights[k]||0)/100]));
}
function configuration(){
  const config={
    mode:state.objective==='custom'?'custom':'preset',
    objective:state.objective,
    dimensions:[...state.dimensions],
    scope:{filters:filterPayload(state.scopeFilters||[])},
  };
  if(state.objective==='custom')config.weights=decimalWeights();
  return config;
}

async function ensurePersistedApproval(nodeId){
  const node=state.decisionCase?.nodes?.[nodeId];
  if(!node?.run_id||node.status!==STATUS.APPROVED)return null;
  const run=await api('/api/runs/'+node.run_id);
  const meta=run.result_json?.decision_case||{};
  if(meta.status==='approved'&&meta.approved_at)return run;
  return await post('/api/runs/'+node.run_id+'/approve',{
    case_id:state.decisionCase.id,
    node_id:nodeId,
  });
}

async function loadSchedulingConfig(){
  const node=roots.config,generation=routeGeneration;
  if(!state.orders||!state.fleet||state.decisionCase?.nodes?.logistics_assignment?.status!=='approved'){
    errorBox(node,new Error('Primero aprobá Asignación de carga.'),()=>navigate('logistics-map'));return;
  }
  if(!state.preflight)await preflight();if(generation!==routeGeneration)return;
  if(!schedulingEvidence()?.data_ready){errorBox(node,new Error('Faltan datos temporales para Planificación.'),()=>navigate('logistics-data'));return;}
  return mountSchedulingConfig(node,{state,preflight:state.preflight,isCurrent:()=>generation===routeGeneration,onExecute:executeConfiguredScheduling});
}

async function loadConfig(){
  const generation=routeGeneration;
  // Legacy visible sections "Variables que intervienen" and "Las fechas se deciden después"
  // were removed from Assignment. The active renderer root is dispatch-config-screen in
  // assignment-config.mjs; these source-only markers keep older structural contracts clear.
  const node=roots.config;
  if(!state.activeNode){
    node.innerHTML='<section class="dispatch-panel"><span class="dispatch-kicker">CONFIGURAR DECISIÓN</span><h1>Primero elegí una decisión.</h1><p>Volvé al mapa para seleccionar qué decisión querés analizar antes de configurar criterios.</p><button data-map>Ir al mapa de decisiones</button></section>';
    node.querySelector('[data-map]').onclick=()=>navigate('logistics-map');
    return;
  }
  decisionContext(state.activeNode);
  if(state.activeNode==='logistics_scheduling'){
    return loadSchedulingConfig();
  }
  if(!state.orders||!state.fleet){
    node.innerHTML='<h1>Configurar asignación</h1><p>Primero seleccioná Órdenes y Flota.</p><button data-back>Ir al Data Pack</button>';
    node.querySelector('[data-back]').onclick=()=>navigate('logistics-data');
    return;
  }
  node.innerHTML='<section class="dispatch-panel"><p role="status">Preparando la configuración…</p><div class="dispatch-loading"></div></section>';
  try{
    await preflight();
    if(generation!==routeGeneration)return;
    syncDimensionsToEvidence({initialize:true});
    await mountAssignmentConfig(node,{
      state,
      persist,
      capabilities:assignmentCapabilities(),
      onData:()=>navigate('logistics-data'),
      onExecute:execute,
      isCurrent:()=>generation===routeGeneration,
    });
  }catch(error){
    errorBox(node,error,loadConfig);
  }
}

function pending(message){document.body.classList.add('dispatch-result');roots.dashboard.innerHTML=`<section class="dispatch-panel"><h1>Preparando tu decisión</h1><p role="status">${esc(message)}</p><div class="dispatch-loading" aria-label="Procesando"></div><p>El Decision Case conserva el estado real de esta ejecución.</p><button data-return>Volver al mapa</button></section>`;roots.dashboard.querySelector('[data-return]').onclick=()=>navigate('logistics-map');}
function poll(id,generation,nodeId=state.activeNode,{delay=0,graceUntil=0}={}){
  return runPolling.start({runId:id,delay,graceUntil,read:(runId,signal)=>api('/api/runs/'+runId,{signal}),
    onRun:async run=>{
      if(generation!==pollGeneration)return;
      if(run.status==='completed'){try{await show(run);}catch(error){if(generation===pollGeneration)errorBox(roots.dashboard,error,()=>openRun(id,nodeId));}return;}
      if(run.status==='error'){try{await showTerminalRun(run,nodeId);}catch(error){if(generation===pollGeneration)errorBox(roots.dashboard,error,()=>openRun(id,nodeId));}return;}
      pending('Etapa: '+(run.progress_json?.stage||run.status||'queued'));
    },onError:error=>{if(generation===pollGeneration)errorBox(roots.dashboard,error,()=>openRun(id,nodeId));},
  });
}

async function execute(){
  const decisionCase=ensureDecisionCase();
  const id=crypto.randomUUID();
  state.activeNode='logistics_assignment';
  state.decisionCase=transitionNode(
    decisionCase,
    'logistics_assignment',
    STATUS.RUNNING,
    {run_id:id,error:null},
  );
  decisionContext('logistics_assignment');
  persist();
  urlRun(id);
  await navigate('decision-dashboard',{runId:id,nodeId:'logistics_assignment',render:false});
  pending('Registrando la corrida…');
  const generation=++pollGeneration;
  runPolling.stop();
  try{
    const run=await post('/api/runs?run_id='+id,{
      orders_dataset_id:state.orders.id,
      fleet_dataset_id:state.fleet.id,
      configuration:configuration(),
      options:{
        allow_third_party:state.resourceMode!=='own',
        resource_mode:state.resourceMode,
        analysis_depth:'essential',
        anomaly_decisions:Object.fromEntries(
          Object.entries(state.decisions).filter(([,v])=>v),
        ),
      },
      decision_case:caseRef(state.decisionCase),
    });
    if(generation===pollGeneration){if(run.status==='completed')await show(run);else {poll(id,generation,'logistics_assignment');await runPolling.refresh();}}
  }catch(e){
    if(generation!==pollGeneration)return;
    poll(id,generation,'logistics_assignment',{graceUntil:Date.now()+10000});
    await runPolling.refresh();
  }
}

async function executeScheduling(sourceRunId){
  const decisionCase=ensureDecisionCase();
  const id=crypto.randomUUID();
  state.activeNode='logistics_scheduling';
  state.decisionCase=transitionNode(
    decisionCase,
    'logistics_scheduling',
    STATUS.RUNNING,
    {run_id:id,error:null},
  );
  decisionContext('logistics_scheduling');
  persist();
  urlRun(id,'scheduling_v1');
  await navigate('decision-dashboard',{runId:id,nodeId:'logistics_scheduling',render:false});
  pending('Registrando la planificación…');
  const generation=++pollGeneration;
  runPolling.stop();
  try{
    const run=await post('/api/runs?run_id='+id,{
      orders_dataset_id:state.orders.id,
      fleet_dataset_id:state.fleet.id,
      source_run_id:sourceRunId,
      configuration:{
        strategy:'service_first',
        use_delivery_due_dates:Boolean(state.schedulingUseDueDates),
      },
      options:{},
      decision_case:caseRef(state.decisionCase,'logistics_scheduling'),
    });
    if(generation===pollGeneration){if(run.status==='completed')await show(run);else {poll(id,generation,'logistics_scheduling');await runPolling.refresh();}}
  }catch(e){
    if(generation!==pollGeneration)return;
    poll(id,generation,'logistics_scheduling',{graceUntil:Date.now()+10000});
    await runPolling.refresh();
  }
}

async function reconfigureRun(run,nodeId){
  const generation=routeGeneration,context=runContext(run,nodeId);
  if(context.caseId)await hydrateCase(context.caseId,generation);
  if(generation!==routeGeneration)return;
  const config=context.configuration;
  const options=config.options||{};
  if(context.nodeId==='logistics_scheduling'){
    state.activeNode='logistics_scheduling';
    restoreRunConfiguration(state.decisionCase.id,config);
    state.schedulingUseDueDates=config.use_delivery_due_dates??true;
  }else if(context.nodeId==='logistics_assignment'){
    state.activeNode='logistics_assignment';
    state.customWeights=null;
    const dims=Array.isArray(config.dimensions)
      ?PRIORITY_KEYS.filter(key=>config.dimensions.includes(key))
      :[...CORE_DIMENSIONS];
    state.dimensions=dims.length?dims:[...CORE_DIMENSIONS];
    state.objective=validObjectives.includes(config.objective)
      ?config.objective
      :'balanced';
    const weights=config.weights||{};
    if(PRIORITY_KEYS.every(key=>Number.isFinite(+weights[key]))){
      const restored=Object.fromEntries(
        PRIORITY_KEYS.map(key=>[key,Math.round(+weights[key]*100)])
      );
      state.weights=normalizeWeights(restored,state.dimensions);
      if(state.objective==='custom')state.customWeights={...restored};
    }else{
      state.weights=presetWeights(state.objective,state.dimensions);
    }
    state.scopeFilters=Array.isArray(config.scope?.filters)
      ?config.scope.filters.map(item=>({...item,preset:'custom'}))
      :[];
    state.resourceMode=['own','mixed','outsourced'].includes(options.resource_mode)
      ?options.resource_mode
      :(options.allow_third_party===false?'own':'mixed');
    state.allow=state.resourceMode!=='own';
    state.decisions=options.anomaly_decisions||{};
    if(state.objective!=='custom')state.lastPreset=state.objective;
    state.configured=true;
  }else{
    state.activeNode='logistics_assignment';
    resetAssignmentConfiguration();
  }

  const ordersId=context.ordersId||state.orders?.id,fleetId=context.fleetId||state.fleet?.id;
  if(!ordersId||!fleetId)throw new Error('No se encontró el Data Pack de esta corrida.');
  const [orders,fleet]=await Promise.all([
    api('/api/datasets/'+ordersId+'/profile',{signal:routeController?.signal}),
    api('/api/datasets/'+fleetId+'/profile',{signal:routeController?.signal}),
  ]);
  if(generation!==routeGeneration)return;
  state.orders=orders.dataset;state.fleet=fleet.dataset;state.preflight=null;state.configPreview=null;
  ensureDecisionCase();decisionContext(state.activeNode);persist();
  return navigateResource('logistics-config',{caseId:context.caseId||state.decisionCase?.id,nodeId:context.nodeId,runId:null});
}

async function showTerminalRun(run,nodeId){
  const generation=routeGeneration,context=runContext(run,nodeId);
  if(context.caseId)await hydrateCase(context.caseId,generation);
  if(generation!==routeGeneration)return;
  state.run=run;state.activeNode=context.nodeId;decisionContext(state.activeNode);persist();
  urlRun(run.id,context.nodeId==='logistics_scheduling'?'scheduling_v1':'assignment_v1');
  const root=roots.dashboard,scope=createScope(root),scheduling=context.nodeId==='logistics_scheduling';
  root.innerHTML='<section class="dispatch-panel dispatch-run-error" data-run-terminal-error>'
    +'<span class="dispatch-kicker">CORRIDA FINALIZADA CON ERROR</span><h1>No se pudo completar '+(scheduling?'la planificación':'la asignación')+'</h1>'
    +'<p class="dispatch-alert">'+esc(run.error_message||'La ejecución terminó con error.')+'</p>'
    +'<p>Ajustá la configuración para ejecutar una nueva corrida. Esta ejecución se conserva en el historial.</p>'
    +'<div class="dispatch-run-error__actions"><button type="button" data-reconfigure-run>Volver a configurar '+(scheduling?'planificación':'asignación')+'</button>'
      +(context.caseId?'<button type="button" data-error-map>Decision Map</button>':'')+'</div><p role="alert" data-reconfigure-error hidden></p></section>';
  const button=root.querySelector('[data-reconfigure-run]'),errorBox=root.querySelector('[data-reconfigure-error]');
  scope.listen(button,'click',async()=>{
    if(button.disabled)return;button.disabled=true;errorBox.hidden=true;
    try{await reconfigureRun(run,context.nodeId);}
    catch(error){if(scope.active){button.disabled=false;errorBox.hidden=false;errorBox.textContent=error.message;}}
  });
  const map=root.querySelector('[data-error-map]');
  if(map)scope.listen(map,'click',()=>navigateResource('logistics-map',{caseId:context.caseId,nodeId:null,runId:null}));
}

export async function show(run){
  if(run.status!=='completed'||!run.result_json)return openRun(run.id);
  const generation=routeGeneration;
  runPolling.stop();
  state.run=run;
  const r=run.result_json;
  const schema=r?.schema_version;
  const isAssignmentRun=schema==='assignment_v1';
  const isSchedulingRun=schema==='scheduling_v1';
  const caseMeta={...r?.decision_case,case_id:runContext(run).caseId};
  const nodeId=isSchedulingRun
    ?'logistics_scheduling'
    :(isAssignmentRun?'logistics_assignment':null);

  if(nodeId&&caseMeta?.case_id){
    await hydrateCase(caseMeta.case_id,generation);
    if(generation!==routeGeneration)return;
    state.activeNode=nodeId;decisionContext(nodeId);
  }

  state.run=run;
  persist();
  document.body.classList.add('dispatch-result');
  urlRun(run.id,schema||'assignment_v1');
  window.dationSetDashboardReady(true);

  await dashboard(
    roots.dashboard,
    run,
    ()=>reconfigureRun(run,nodeId),
    {
      status:(nodeId&&caseMeta?.case_id&&state.decisionCase?.id===caseMeta.case_id)
        ?runDecisionState(run,state.decisionCase,nodeId)
        :null,
      decisionCase:state.decisionCase,
      activeNode:nodeId,
      onNewDecision:startNewDecision,
      onMap:caseMeta?.case_id?()=>navigateResource('logistics-map',{caseId:caseMeta.case_id,nodeId:null,runId:null}):null,
      getContinuation:()=>dashboardContinuation(run,nodeId,generation),
      onContinue:async()=>{
        await hydrateCase(caseMeta.case_id,generation);
        if(generation!==routeGeneration)return;
        state.preflight=null;
        const next=await dashboardContinuation(run,nodeId,generation);
        if(generation!==routeGeneration)return;
        if(next?.state!=='available')throw new Error(next?.message||'La siguiente decisión todavía no está disponible.');
        return navigateResource('logistics-config',{caseId:caseMeta.case_id,nodeId:next.nodeId,runId:null});
      },
      onOpenNode:state.decisionCase?openCaseResult:null,
      onApprove:(nodeId&&caseMeta?.case_id&&state.decisionCase?.id===caseMeta.case_id&&!['stale','superseded'].includes(runDecisionState(run,state.decisionCase,nodeId)))
        ?async()=>{
          const approved=await post('/api/runs/'+run.id+'/approve',{
            case_id:state.decisionCase.id,
            node_id:nodeId,
          });
          if(generation!==routeGeneration)return state.decisionCase;
          state.run=approved;
          await hydrateCase(caseMeta.case_id,generation);
          if(generation!==routeGeneration)return state.decisionCase;
          if(state.preflight)state.decisionCase={...state.decisionCase,nodes:deriveDecisionNodes(state.decisionCase,state.preflight.decision_readiness)};
          persist();
          return state.decisionCase;
        }
        :null,
      onApprovalComplete:(nodeId&&state.decisionCase)
        ?()=>{persist();}
        :null,
    },
  );
  if(generation!==routeGeneration)return;
  renderView('decision-dashboard');
}

for(const [key,view]of [['data','logistics-data'],['map','logistics-map'],['config','logistics-config'],['dashboard','decision-dashboard']])roots[key]=root(view,'dispatch-'+key+'-root');

async function hydrateCase(caseId,generation=routeGeneration){
  const item=await api('/api/decision-cases/'+caseId,{signal:routeController?.signal});
  if(generation!==routeGeneration)return;
  if(String(item.decision_case?.id)!==String(caseId)||String(item.orders?.id)!==String(item.decision_case?.inputs?.orders_dataset_id||item.case?.orders_dataset_id)||String(item.fleet?.id)!==String(item.decision_case?.inputs?.fleet_dataset_id||item.case?.fleet_dataset_id))throw new Error('El Decision Case no coincide con su Data Pack.');
  if(state.decisionCase?.id!==caseId){saveDraft();resetAssignmentConfiguration();Object.assign(state,cleanDraft(drafts[caseId]));state.preflight=null;state.configPreview=null;state.run=null;}
  transitionCaseId=null;
  state.orders=item.orders;state.fleet=item.fleet;state.decisionCase={...item.decision_case,persisted:true};persist();return item;
}
async function navigateResource(view,options={}){
  const aliases={overview:'logistics-overview',library:'traceability'};
  const publicView=Object.entries(aliases).find(([,value])=>value===view)?.[0]||view;
  const next={view:publicView,caseId:options.caseId===undefined?state.decisionCase?.id||null:options.caseId,nodeId:options.nodeId===undefined?state.activeNode:options.nodeId,runId:options.runId||(publicView==='decision-dashboard'?state.run?.id||resource?.runId:null)};
  saveDraft();routeController?.abort();routeController=new AbortController();const generation=++routeGeneration;
  runPolling.stop();pollGeneration++;
  for(const root of Object.values(roots)){disposeScope(root);root.replaceChildren();root.className='dispatch';}
  resource=next;
  if(options.history!==false){const url=resourceUrl(location.href,next);history[options.replace?'replaceState':'pushState'](null,'',url);}
  state.activeNode=next.nodeId||null;decisionContext(state.activeNode);persist();
  document.body.classList.toggle('dispatch-result',publicView==='decision-dashboard');
  renderView(aliases[publicView]||publicView);
  if(options.render===false)return;
  const root=roots[{'logistics-data':'data','logistics-map':'map','logistics-config':'config','decision-dashboard':'dashboard'}[publicView]];
  if(!root)return;
  root.hidden=false;
  createScope(root);
  try{
    if(next.caseId){try{await hydrateCase(next.caseId,generation);}catch(error){if(!(error.status===404&&state.decisionCase?.id===next.caseId&&!state.decisionCase.persisted&&state.orders&&state.fleet))throw error;}}
    if(generation!==routeGeneration)return;
    if(publicView==='logistics-data')await loadData();
    if(publicView==='logistics-map')await loadDecisionMap();
    if(publicView==='logistics-config')await loadConfig();
    if(publicView==='decision-dashboard'){
      if(!next.runId)throw new Error('Seleccioná una corrida para abrir su resultado.');
      pending('Recuperando la corrida…');poll(next.runId,pollGeneration,next.nodeId);
    }
  }catch(error){if(generation===routeGeneration&&!routeController.signal.aborted)errorBox(root,error,()=>navigateResource(view,{...options,replace:true}));}
}
async function openRun(id,nodeId=state.activeNode,caseId=state.decisionCase?.id){return navigateResource('decision-dashboard',{runId:id,nodeId,caseId});}
async function executeConfiguredScheduling({sourceRun,configuration,options}){
  const id=crypto.randomUUID(),caseId=state.decisionCase.id;
  await navigateResource('decision-dashboard',{runId:id,nodeId:'logistics_scheduling',render:false});pending('Registrando la planificación…');
  const generation=pollGeneration;
  try{const run=await post('/api/runs?run_id='+id,{orders_dataset_id:state.orders.id,fleet_dataset_id:state.fleet.id,source_run_id:sourceRun.id,configuration,options,decision_case:{case_id:caseId,node_id:'logistics_scheduling'}});if(generation===pollGeneration){if(run.status==='completed')await show(run);else {poll(id,generation,'logistics_scheduling');await runPolling.refresh();}}}
  catch(error){if(generation===pollGeneration){poll(id,generation,'logistics_scheduling',{graceUntil:Date.now()+10000});await runPolling.refresh();}}
}
window.DationDispatch={show,openRun,isReady:ready,getWorkspace:()=>state,startNewDecision,openCase:(caseId,view='logistics-map',nodeId=null)=>navigateResource(view,{caseId,nodeId}),openActiveDecisionResult:()=>openCaseResult(state.activeNode),getActiveDecision:()=>({id:state.activeNode,label:DECISION_LABELS[state.activeNode],hasRun:Boolean(state.decisionCase?.nodes?.[state.activeNode]?.run_id),status:state.decisionCase?.nodes?.[state.activeNode]?.status})};
window.dationNavigate=(view,stage,event)=>{event?.preventDefault();return navigateResource(view);};
document.body.classList.add('dispatch-enabled');
mountTraceability();
async function restoreResource(){try{const target=readResource(location.href);await navigateResource(target.view,{...target,history:false});}catch(error){document.body.classList.add('dispatch-result');renderView('decision-dashboard');roots.dashboard.hidden=false;errorBox(roots.dashboard,error,()=>navigate('logistics-data'));}}
window.addEventListener('popstate',restoreResource);
window.addEventListener('pagehide',()=>{routeController?.abort();routeGeneration++;pollGeneration++;runPolling.stop();for(const root of Object.values(roots))disposeScope(root);});
window.addEventListener('pageshow',event=>{if(event.persisted)restoreResource();});
restoreResource();
