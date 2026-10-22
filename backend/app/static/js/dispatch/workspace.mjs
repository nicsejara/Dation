import {caseAttributesReady} from './case-identity.mjs';
import {esc,num,api,post,errorBox} from './shared.mjs';
import {render as dashboard} from './dashboard.mjs';
import {mountUploadScreen} from './upload/index.mjs';
import {renderDecisionMap} from './decision-map.mjs';
import {mountAssignmentConfig,filterPayload,normalizeRawWeights} from './assignment-config.mjs';
import {STATUS,createDecisionCase,replaceInputs,transitionNode,inputSignature,caseRef,deriveDecisionNodes,continuationState,getCaseTransitionNotice} from './decision-case.mjs';
import {resolveNodeDestination,resolveDecisionDestination,configurationAvailable} from './decision-target.mjs';
import {DECISION_META} from './decision-ui.mjs';
import {caseContext} from '../platform/foundation.mjs';
import {mountWorkflowContext,mountMapResponsibilities,mountDashboardTrace,renderExecutionProgress} from './workflow-context.mjs';
import {responsibilityProblem} from './workflow-responsibility.mjs';
import {currentLogisticsEnabled,logisticsView} from '../platform/entitlements.mjs';

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
import {createScope,disposeScope,scopeFor} from './lifecycle.mjs';
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
  caseIdentity:saved.caseIdentity||null,
  identityDirty:Boolean(saved.identityDirty),
  attributesApplied:Boolean(saved.attributesApplied),
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
      caseIdentity:state.caseIdentity,
      identityDirty:state.identityDirty,
      attributesApplied:state.attributesApplied,
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
  window.dispatchEvent(new CustomEvent('dation:workspace'));
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
function ready(){return !!(state.available&&state.orders&&state.fleet&&state.preflight?.valid&&caseAttributesReady(state)&&!responsibilityProblem(state.workflow,'data_preparation','data'));}
function pendingWorkflow(){
  const role=window.dationSession?.identity?.membership?.access_role;
  return {gates_enforced:true,stages:{},pending:true,can_assign:role==='admin',can_prepare:['admin','operator'].includes(role)};
}
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
    if(state.decisionCase?.persisted)return state.decisionCase;
    state.decisionCase=null;
    state.activeNode=null;
    window.dationSetDecisionContext?.(null);
    persist();
    return null;
  }
  if(!state.decisionCase){
    state.decisionCase=createDecisionCase(crypto.randomUUID(),state.orders,state.fleet);
    state.workflow=pendingWorkflow();state.caseContext=null;
    transitionCaseId=null;
    state.activeNode=null;
    window.dationSetDecisionContext?.(null);
  }else if(state.decisionCase.signature!==signature){
    const previous=state.decisionCase;
    state.decisionCase=replaceInputs(previous,crypto.randomUUID(),state.orders,state.fleet);
    if(previous.persisted)state.forkedFrom=previous.id;
    transitionCaseId=state.decisionCase.id;
    state.workflow=pendingWorkflow();state.caseContext=null;
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
async function startNewDecision(inputs=[]){
  if(!currentLogisticsEnabled())return navigateResource('inicio');
  transitionCaseId=null;
  saveDraft();
  resetAssignmentConfiguration();
  Object.assign(state,{caseIdentity:null,identityDirty:false,attributesApplied:false,forkedFrom:null,orders:null,fleet:null,decisionCase:null,workflow:null,caseContext:null,run:null,activeNode:null,
    preflight:null,configPreview:null,configured:false,decisions:{},schedulingUseDueDates:true});
  if(Array.isArray(inputs))for(const dataset of inputs){if(['orders','fleet'].includes(dataset?.dataset_type))state[dataset.dataset_type]=dataset;}
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
  return continuationState(state.decisionCase,nodeId,run.id,state.preflight?.decision_readiness,DECISION_META,state.workflow);
}

function urlRun(id,schema='assignment_v1',caseId=state.decisionCase?.id||null){resource={view:'decision-dashboard',caseId,nodeId:schema==='scheduling_v1'?'logistics_scheduling':'logistics_assignment',runId:id};history.replaceState(null,'',resourceUrl(location.href,resource));}

async function preflight(){
  const generation=routeGeneration;
  state.preflight=null;
  window.dationSetDataReady(false);
  if(!state.orders||!state.fleet)return;
  const ordersId=state.orders.id,fleetId=state.fleet.id,allow=state.resourceMode!=='own';
  const result=await post('/api/runs/preflight',{
    orders_dataset_id:ordersId,
    fleet_dataset_id:fleetId,
    allow_third_party:allow,
  },{signal:routeController?.signal});
  if(generation!==routeGeneration||state.orders?.id!==ordersId||state.fleet?.id!==fleetId||allow!==(state.resourceMode!=='own'))return;
  state.preflight=result;
  state.allow=state.resourceMode!=='own';
  ensureDecisionCase();
  if(result.valid&&state.forkedFrom&&!state.decisionCase.persisted)await ensurePersistedCase(generation);
  if(result.valid&&state.decisionCase.persisted&&!state.workflow)await hydrateCase(state.decisionCase.id,generation);
  if(generation!==routeGeneration)return;
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
      saveIdentity:async()=>{
        if(state.preflight?.valid||state.decisionCase?.persisted)await ensurePersistedCase(generation,true);
        else{state.attributesApplied=true;state.identityDirty=false;persist();}
      },
      onNext:async()=>{
        const identityForm=roots.data.querySelector('[data-case-identity]');
        if(identityForm&&!identityForm.reportValidity())return;
        try{if(!caseAttributesReady(state))throw new Error('Aplicá los atributos del Case antes de continuar.');await ensurePersistedCase(generation);await api('/api/platform/decisions/'+state.decisionCase.id+'/workflow-readiness',{signal:routeController?.signal});if(generation===routeGeneration)await navigate('logistics-map');}
        catch(error){if(generation!==routeGeneration)return;const note=document.createElement('p');note.role='alert';note.textContent=error.message;roots.data.querySelector('[data-workflow-data-error]')?.remove();note.dataset.workflowDataError='';roots.data.append(note);}
      },
      mountWorkflow:(node,onSaved)=>{
        const caseId=state.decisionCase?.id,signature=state.decisionCase?.signature;
        return mountWorkflowContext(node,{state,stageKey:'data_preparation',showCase:false,onSaved,onPrepare:async()=>{
          const form=roots.data.querySelector('[data-case-identity]');if(form&&!form.reportValidity())throw new Error('Completá el nombre y la categoría del Case.');
          if(!state.preflight?.valid||!caseId)throw new Error('Cargá y validá Órdenes y Flota antes de guardar.');
          if(state.decisionCase?.id!==caseId||inputSignature(state.orders,state.fleet)!==signature)throw new Error('El Data Pack cambió.');
          if(!state.decisionCase.persisted)await ensurePersistedCase(generation);else await hydrateCase(caseId,generation,signature);
          if(generation!==routeGeneration||state.decisionCase?.id!==caseId||inputSignature(state.orders,state.fleet)!==signature)throw new Error('La etapa cambió.');return state.workflow;
        }});
      },
      isReady:ready,
      isCurrent:()=>generation===routeGeneration,
    },
  );
}
async function openCaseResult(nodeId='logistics_assignment'){
 const target=resolveNodeDestination(nodeId,state.decisionCase?.nodes?.[nodeId]);
 if(target)return navigateResource(target.view,{caseId:state.decisionCase.id,nodeId,runId:target.run_id});
}

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
    await ensurePersistedCase(generation);
    if(generation!==routeGeneration)return;
    const hasHistory=Object.values(state.decisionCase.nodes||{}).some(item=>item.run_id||item.latest_run_id||item.approved_run_id||item.run_count>0);
    if(state.workflow?.gates_enforced&&!hasHistory&&state.caseContext?.status!=='archived'&&window.dationSession?.identity?.membership?.access_role!=='viewer'){
      if(!caseAttributesReady(state)||!state.workflow.stages?.data_owner?.owner_eligible)return navigateResource('logistics-data',{caseId:state.decisionCase.id,nodeId:null,runId:null});
      await api('/api/platform/decisions/'+state.decisionCase.id+'/workflow-readiness',{signal:routeController?.signal});
      if(generation!==routeGeneration)return;
    }
    let predecessor=null;
    if(transitionCaseId===state.decisionCase.id&&state.decisionCase.stale_predecessor?.id){
      try{predecessor=await api('/api/decision-cases/'+state.decisionCase.stale_predecessor.id,{signal:routeController?.signal});}
      catch(error){if(error.status!==404)throw error;}
      if(generation!==routeGeneration)return;
    }
    const transitionNotice=getCaseTransitionNotice({decisionCase:state.decisionCase,predecessor,transitionCaseId});
    transitionCaseId=null;
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
      dataOwner:state.workflow?.stages?.data_owner?.owner?.name,
      onConfigure:(nodeId)=>{
        state.activeNode=nodeId||'logistics_assignment';
        decisionContext(state.activeNode);
        persist();
        navigate('logistics-config');
      },
      onOpenResult:openCaseResult,
      onData:()=>navigate('logistics-data'),
      onSelectCase:()=>{const trigger=node.querySelector('[data-case-switcher] button');trigger?.focus();trigger?.click();},
    });
    if(generation===routeGeneration){decorateDecisionMap(node);mountMapResponsibilities(node,{state,onSaved:()=>{persist();loadDecisionMap();}});
      const target=resource.nodeId&&node.querySelector('article[data-decision-node="'+CSS.escape(resource.nodeId)+'"]');
      if(target&&!state.workflow?.stages?.[resource.nodeId]?.owner_eligible){target.classList.add('d-attention-target','is-attention');scopeFor(node)?.timeout(()=>{target.scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});target.querySelector('.workflow-responsibility button')?.focus({preventScroll:true});},0);}
    }
  }catch(error){
    if(generation!==routeGeneration)return;
    if(error.workflowGate==='data'){
      errorBox(node,Object.assign(error,{actionLabel:'Ir a Datos'}),()=>navigate('logistics-data'));return;
    }
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
    errorBox(node,Object.assign(new Error('Primero aprobá Asignación de carga.'),{kind:'source',actionLabel:'Revisar Assignment'}),()=>navigate('logistics-map'));return;
  }
  if(!state.preflight)await preflight();if(generation!==routeGeneration)return;
  if(!schedulingEvidence()?.data_ready){errorBox(node,Object.assign(new Error('Faltan datos temporales para Planificación.'),{kind:'validation',actionLabel:'Revisar datos'}),()=>navigate('logistics-data'));return;}
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

function pending(stage){document.body.classList.add('dispatch-result');window.dationSetDashboardReady(false);renderExecutionProgress(roots.dashboard,stage);}
function poll(id,generation,nodeId=state.activeNode,{delay=0,graceUntil=0}={}){
  return runPolling.start({runId:id,delay,graceUntil,read:(runId,signal)=>api('/api/runs/'+runId,{signal}),
    onRun:async run=>{
      if(generation!==pollGeneration)return;
      if(run.status==='completed'){try{await show(run);}catch(error){if(generation===pollGeneration)errorBox(roots.dashboard,error,()=>openRun(id,nodeId));}return;}
      if(run.status==='error'){try{await showTerminalRun(run,nodeId);}catch(error){if(generation===pollGeneration)errorBox(roots.dashboard,error,()=>openRun(id,nodeId));}return;}
      pending(run.progress_json?.stage||run.status||'queued');
    },onError:error=>{if(generation===pollGeneration)errorBox(roots.dashboard,error,()=>openRun(id,nodeId));},
  });
}

async function returnToConfiguration(error,nodeId,caseId){
  const nextGeneration=routeGeneration+1;
  await navigateResource('logistics-config',{caseId,nodeId,runId:null,replace:true});
  if(routeGeneration!==nextGeneration)return;
  const note=document.createElement('p');note.role='alert';note.className='workflow-gate-reason';note.textContent=error.message;
  roots.config.prepend(note);
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
  pending('registering');
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
    if(e.workflowGate){await returnToConfiguration(e,'logistics_assignment',decisionCase.id);return;}
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
  pending('registering');
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
    if(e.workflowGate){await returnToConfiguration(e,'logistics_scheduling',decisionCase.id);return;}
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
  urlRun(run.id,context.nodeId==='logistics_scheduling'?'scheduling_v1':'assignment_v1',context.caseId||null);
  const root=roots.dashboard,scope=createScope(root),scheduling=context.nodeId==='logistics_scheduling';
  root.innerHTML='<section class="dispatch-panel dispatch-run-error" data-run-terminal-error>'
    +'<span class="dispatch-kicker">CORRIDA FINALIZADA CON ERROR</span><h1>No se pudo completar '+(scheduling?'la planificación':'la asignación')+'</h1>'
    +'<p class="dispatch-alert">'+esc(run.error_message||'La ejecución terminó con error.')+'</p>'
    +'<p>La evidencia anterior se conserva. Revisá los datos y volvé a configurar la decisión.</p>'
    +'<p>Ajustá la configuración para ejecutar una nueva corrida. Esta ejecución se conserva en el historial.</p>'
    +'<div class="dispatch-run-error__actions"><button type="button" class="d-button d-button--workflow d-button--primary" data-reconfigure-run>Volver a configuración</button></div><p role="alert" data-reconfigure-error hidden></p></section>';
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
  urlRun(run.id,schema||'assignment_v1',caseMeta.case_id||null);
  window.dationSetDashboardReady(true);

  await dashboard(
    roots.dashboard,
    run,
    ()=>reconfigureRun(run,nodeId),
    {
      status:(nodeId&&caseMeta?.case_id&&state.decisionCase?.id===caseMeta.case_id)
        ?runDecisionState(run,state.decisionCase,nodeId)
        :null,
      decisionCase:caseMeta.case_id&&state.decisionCase?.id===caseMeta.case_id?state.decisionCase:null,
      activeNode:nodeId,
      workflow:state.workflow,
      view:'decision-dashboard',
      onNewDecision:startNewDecision,
      onMap:caseMeta?.case_id?()=>navigateResource('logistics-map',{caseId:caseMeta.case_id,nodeId:null,runId:null}):null,
      onCase:caseMeta?.case_id?()=>window.DationDispatch.openCaseInDecisionCenter(caseMeta.case_id):null,
      getContinuation:()=>dashboardContinuation(run,nodeId,generation),
      onContinue:async()=>{
        await hydrateCase(caseMeta.case_id,generation);
        if(generation!==routeGeneration)return;
        const next=await dashboardContinuation(run,nodeId,generation);
        if(generation!==routeGeneration)return;
        if(next?.state==='completed')return window.DationDispatch.openDecisionCenter({filter:'completed'});
        if(next?.target)return navigateResource(next.target.view,{caseId:caseMeta.case_id,nodeId:next.nodeId,runId:null});
        return navigateResource('logistics-map',{caseId:caseMeta.case_id,nodeId:null,runId:null});
      },
      onOpenNode:state.decisionCase?id=>{
        const target=resolveDecisionDestination(id,state.decisionCase.nodes[id],'decision-dashboard');
        if(target)return navigateResource(target.view,{caseId:state.decisionCase.id,nodeId:id,runId:target.run_id});
      }:null,
      onRefresh:async()=>{const fresh=await api('/api/runs/'+run.id,{signal:routeController?.signal});if(generation===routeGeneration)await show(fresh);},
      approvalBlocked:Boolean(caseMeta.case_id&&responsibilityProblem(state.workflow,nodeId,'approve')),
      onApprove:(nodeId&&caseMeta?.case_id&&state.decisionCase?.id===caseMeta.case_id&&state.decisionCase.collaboration?.[nodeId]?.can_approve!==false&&!['stale','superseded'].includes(runDecisionState(run,state.decisionCase,nodeId)))
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
        ?async()=>{persist();await show(state.run);}
        :null,
    },
  );
  if(generation!==routeGeneration)return;
  if(caseMeta.case_id&&state.decisionCase?.id===caseMeta.case_id)mountDashboardTrace(roots.dashboard,{state,run,nodeId});
  const approvalReason=responsibilityProblem(state.workflow,nodeId,'approve');
  if(approvalReason&&runDecisionState(run,state.decisionCase,nodeId)!=='approved'){
    const note=document.createElement('p');note.className='workflow-gate-reason';note.id='workflow-approval-reason';note.textContent=approvalReason;
    roots.dashboard.querySelector('[data-run-trace]')?.after(note);
    roots.dashboard.querySelectorAll('[data-approve-toolbar]').forEach(button=>button.setAttribute('aria-describedby',note.id));
  }
  renderView('decision-dashboard');
}

for(const [key,view]of [['data','logistics-data'],['map','logistics-map'],['config','logistics-config'],['dashboard','decision-dashboard']])roots[key]=root(view,'dispatch-'+key+'-root');

async function ensurePersistedCase(generation=routeGeneration,applyIdentity=false){
  const current=state.decisionCase;if(!current)return;
  if(!current.persisted){
    await post('/api/decision-cases',{id:current.id,orders_dataset_id:state.orders.id,fleet_dataset_id:state.fleet.id,state:current,...((applyIdentity||caseAttributesReady(state))?state.caseIdentity||{}:{})},{signal:routeController?.signal});
    if(generation!==routeGeneration||state.decisionCase?.id!==current.id||inputSignature(state.orders,state.fleet)!==current.signature)return;
    await hydrateCase(current.id,generation,current.signature);
    if(generation!==routeGeneration||state.decisionCase?.id!==current.id||inputSignature(state.orders,state.fleet)!==current.signature)return;
    state.forkedFrom=null;
    resource={...resource,caseId:current.id};history.replaceState(null,'',resourceUrl(location.href,resource));
  }else if(!state.workflow||state.workflow.case_id!==current.id){
    await hydrateCase(current.id,generation);
  }
  if(applyIdentity&&state.caseIdentity&&generation===routeGeneration){
    const identity={...state.caseIdentity};
    await api('/api/platform/decisions/'+current.id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_updated_at:state.caseVersion,...identity}),signal:routeController?.signal});
    if(generation!==routeGeneration)return;state.identityDirty=false;
    await hydrateCase(current.id,generation);
  }
}
async function hydrateCase(caseId,generation=routeGeneration,expectedInputs=null){
  const item=await api('/api/decision-cases/'+caseId,{signal:routeController?.signal});
  if(generation!==routeGeneration)return;
  if(expectedInputs&&(state.decisionCase?.id!==caseId||inputSignature(state.orders,state.fleet)!==expectedInputs))return;
  if(String(item.decision_case?.id)!==String(caseId)||String(item.orders?.id)!==String(item.decision_case?.inputs?.orders_dataset_id||item.case?.orders_dataset_id)||String(item.fleet?.id)!==String(item.decision_case?.inputs?.fleet_dataset_id||item.case?.fleet_dataset_id))throw new Error('El Decision Case no coincide con su Data Pack.');
  if(state.decisionCase?.id!==caseId){saveDraft();resetAssignmentConfiguration();Object.assign(state,cleanDraft(drafts[caseId]));state.preflight=null;state.configPreview=null;state.run=null;transitionCaseId=null;}
  if(state.decisionCase?.id!==caseId)state.identityDirty=false;
  state.attributesApplied=Boolean(item.case.attributes_applied_at);
  if(!state.identityDirty)state.caseIdentity={label:item.case.label||'',category:item.case.category||null,description:item.case.description||null};
  state.caseVersion=item.case.updated_at;
  state.orders=item.orders;state.fleet=item.fleet;state.decisionCase={...item.decision_case,status:item.case.status,label:item.case.label,category:item.case.category,description:item.case.description,attributes_applied_at:item.case.attributes_applied_at,collaboration:item.collaboration,persisted:true};state.workflow=item.workflow_responsibilities||null;state.caseContext=caseContext({...item.case,context:item.context});persist();return item;
}
async function navigateResource(view,options={}){
  if(view==='inicio')view='platform-home';
  if(logisticsView(view)&&!currentLogisticsEnabled()){
    return navigateResource('inicio',{replace:true,caseId:null,nodeId:null});
  }
  const aliases={overview:'logistics-overview',library:'traceability'};
  const publicView=Object.entries(aliases).find(([,value])=>value===view)?.[0]||view;
  const next={view:publicView,caseId:!['logistics-data','logistics-map','logistics-config','decision-dashboard'].includes(publicView)?null:options.caseId===undefined?state.decisionCase?.id||null:options.caseId,nodeId:options.nodeId===undefined?state.activeNode:options.nodeId,runId:options.runId||(publicView==='decision-dashboard'?state.run?.id||resource?.runId:null)};
  saveDraft();routeController?.abort();routeController=new AbortController();const generation=++routeGeneration;
  runPolling.stop();pollGeneration++;
  for(const root of Object.values(roots)){disposeScope(root);root.replaceChildren();root.className='dispatch';}
  resource=next;
  if(publicView==='platform-data')next.hub=options.hub||{};
  if(publicView==='platform-decisions')next.center=options.center||{};
  if(publicView==='settings')next.settingsTab=options.settingsTab||'general';
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
    if(publicView==='logistics-config'){
      const problem=responsibilityProblem(state.workflow,next.nodeId,'configure');
      if(problem||!configurationAvailable(next.nodeId,state.decisionCase,state.workflow)){await navigateResource('logistics-map',{caseId:next.caseId,nodeId:null,runId:null});return;}
      await api('/api/platform/decisions/'+next.caseId+'/workflow-readiness?'+new URLSearchParams({node_id:next.nodeId}),{signal:routeController.signal});
      if(generation!==routeGeneration)return;
      await loadConfig();
    }
    if(publicView==='decision-dashboard'){
      if(!next.runId)throw new Error('Seleccioná una corrida para abrir su resultado.');
      pending('recovering');poll(next.runId,pollGeneration,next.nodeId);
    }
  }catch(error){if(generation===routeGeneration&&!routeController.signal.aborted)errorBox(root,error,()=>navigateResource(view,{...options,replace:true}));}
}
async function openRun(id,nodeId=state.activeNode,caseId=state.decisionCase?.id){return navigateResource('decision-dashboard',{runId:id,nodeId,caseId});}
async function executeConfiguredScheduling({sourceRun,configuration,options}){
  const id=crypto.randomUUID(),caseId=state.decisionCase.id;
  await navigateResource('decision-dashboard',{runId:id,nodeId:'logistics_scheduling',render:false});pending('registering');
  const generation=pollGeneration;
  try{const run=await post('/api/runs?run_id='+id,{orders_dataset_id:state.orders.id,fleet_dataset_id:state.fleet.id,source_run_id:sourceRun.id,configuration,options,decision_case:{case_id:caseId,node_id:'logistics_scheduling'}});if(generation===pollGeneration){if(run.status==='completed')await show(run);else {poll(id,generation,'logistics_scheduling');await runPolling.refresh();}}}
  catch(error){if(generation===pollGeneration){if(error.workflowGate){await returnToConfiguration(error,'logistics_scheduling',caseId);return;}poll(id,generation,'logistics_scheduling',{graceUntil:Date.now()+10000});await runPolling.refresh();}}
}
window.DationDispatch={show,openRun,isReady:ready,getWorkspace:()=>state,startNewDecision,openCase:(caseId,view='logistics-map',nodeId=null)=>navigateResource(view,{caseId,nodeId}),openActiveDecisionResult:()=>openCaseResult(state.activeNode),getActiveDecision:()=>({id:state.activeNode,label:DECISION_LABELS[state.activeNode],hasRun:Boolean(state.decisionCase?.nodes?.[state.activeNode]?.run_id),status:state.decisionCase?.nodes?.[state.activeNode]?.status})};
window.dationNavigate=(view,stage,event)=>{event?.preventDefault();event?.stopPropagation();return navigateResource(view);};
window.DationDispatch.openDataHub=(hub={},options={})=>navigateResource('platform-data',{...options,hub,caseId:null,nodeId:null});
window.DationDispatch.openDecisionCenter=(center={},options={})=>navigateResource('platform-decisions',{...options,center,caseId:null,nodeId:null});
window.DationDispatch.openCaseInDecisionCenter=caseId=>window.DationDispatch.openDecisionCenter({caseId});
window.DationDispatch.openDashboard=(caseId,nodeId,runId)=>openRun(runId,nodeId,caseId);
window.DationDispatch.openWorkspaceSettings=settingsTab=>navigateResource('settings',{settingsTab,caseId:null,nodeId:null});
window.DationDispatch.reuseHubData=inputs=>startNewDecision(inputs);
document.body.classList.add('dispatch-enabled');
mountTraceability();
async function restoreResource(){try{const target=readResource(location.href);await navigateResource(target.view,{...target,history:false});}catch(error){if(location.pathname.replace(/\/$/,'')==='/app/settings')return navigateResource('settings',{history:false,settingsTab:'general',caseId:null,nodeId:null});if(location.pathname.replace(/\/$/,'')==='/app/data')return navigateResource('platform-data',{history:false,caseId:null,nodeId:null});if(location.pathname.replace(/\/$/,'')==='/app/decisions')return navigateResource('platform-decisions',{history:false,caseId:null,nodeId:null});document.body.classList.add('dispatch-result');renderView('decision-dashboard');roots.dashboard.hidden=false;errorBox(roots.dashboard,Object.assign(error,{kind:'navigation',actionLabel:'Volver al Data Pack'}),()=>navigate('logistics-data'));}}
window.addEventListener('popstate',restoreResource);
window.addEventListener('dation:identity',()=>{if(!currentLogisticsEnabled()&&logisticsView(window.dationGetCurrentView?.()))navigateResource('inicio',{replace:true,caseId:null,nodeId:null});});
window.addEventListener('pagehide',()=>{routeController?.abort();routeGeneration++;pollGeneration++;runPolling.stop();for(const root of Object.values(roots))disposeScope(root);});
window.addEventListener('pageshow',event=>{if(event.persisted)restoreResource();});
restoreResource();
