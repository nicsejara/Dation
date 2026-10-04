import {esc,num,api,post,errorBox} from './shared.mjs';
import {render as dashboard} from './dashboard.mjs?v=decision-map-nodal-v1';
import {mountUploadScreen} from './upload/index.mjs?v=upload-canonical-v1';
import {renderDecisionMap} from './decision-map.mjs?v=decision-map-premium-v1';
import {mountAssignmentConfig,filterPayload,normalizeRawWeights} from './assignment-config.mjs?v=assignment-config-v2';
import {STATUS,createDecisionCase,replaceInputs,transitionNode,inputSignature,caseRef,deriveDecisionNodes} from './decision-case.mjs';
import {DECISION_META} from './decision-ui.mjs?v=assignment-config-v2';

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
// "Profundidad del análisis" is rendered by assignment-config.mjs; workspace
// owns and persists the analysis_depth value used by the execution contract.
const DEPTH_LABELS={
  essential:'Esencial',
  comparative:'Comparativo',
  deep:'Profundo',
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

let saved={};
try{saved=JSON.parse(sessionStorage.getItem(KEY)||'{}');}catch{}
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
  analysisDepth:['essential','comparative','deep'].includes(saved.analysisDepth)?saved.analysisDepth:'comparative',
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
let timer=null,pollGeneration=0;const roots={};

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
      analysisDepth:state.analysisDepth,
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
  state.analysisDepth='comparative';
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
    state.activeNode=null;
    window.dationSetDecisionContext?.(null);
  }else if(state.decisionCase.signature!==signature){
    state.decisionCase=replaceInputs(state.decisionCase,crypto.randomUUID(),state.orders,state.fleet);
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
function navigate(view){persist();window.dationSetDataReady(ready());window.dationNavigate(view);}
function nextNodeId(nodeId){
  if(nodeId==='logistics_assignment')return 'logistics_scheduling';
  if(nodeId==='logistics_scheduling')return 'logistics_final_assignment';
  return null;
}
function unlockNextNode(nodeId){
  const next=nextNodeId(nodeId);
  if(!next||!state.decisionCase?.nodes?.[next])return next;
  const current=state.decisionCase.nodes[next];
  if(current.status!==STATUS.LOCKED&&current.status!==STATUS.NEEDS_DATA)return next;
  const evidence=state.preflight?.decision_readiness?.decisions?.find(item=>item.id===next);
  state.decisionCase=transitionNode(
    state.decisionCase,
    next,
    evidence?.data_ready?STATUS.AVAILABLE:STATUS.NEEDS_DATA,
    {error:null},
  );
  return next;
}
function urlRun(id,schema='assignment_v1'){const url=new URL(location.href);url.searchParams.set('run_id',id);url.searchParams.set('dda',schema);history.replaceState(null,'',url);}

async function preflight(){
  state.preflight=null;
  window.dationSetDataReady(false);
  if(!state.orders||!state.fleet)return;
  state.preflight=await post('/api/runs/preflight',{
    orders_dataset_id:state.orders.id,
    fleet_dataset_id:state.fleet.id,
    allow_third_party:state.resourceMode!=='own',
  });
  state.allow=state.resourceMode!=='own';
  ensureDecisionCase();
  window.dationSetDataReady(ready());
  persist();
}
async function loadData(){
  await mountUploadScreen(
    roots.data,
    {
      state,
      persist,
      runPreflight:preflight,
      onNext:()=>{ensureDecisionCase();navigate('logistics-map');},
      isReady:ready,
    },
  );
}
async function openCaseResult(nodeId='logistics_assignment'){
  const runId=state.decisionCase?.nodes?.[nodeId]?.run_id;
  if(!runId)return;
  state.activeNode=nodeId;
  decisionContext(nodeId);
  persist();
  try{
    const run=state.run?.id===runId
      ?state.run
      :await api('/api/runs/'+runId);
    if(run.status==='completed'){
      show(run);
      return;
    }
    if(run.status==='running'||run.status==='queued'){
      pending('Recuperando el estado de la ejecución…');
      navigate('decision-dashboard');
      clearTimeout(timer);
      poll(runId,++pollGeneration,nodeId);
      return;
    }
    if(run.status==='error'){
      state.decisionCase=transitionNode(
        state.decisionCase,
        nodeId,
        STATUS.ERROR,
        {run_id:runId,error:run.error_message||'La ejecución terminó con error.'},
      );
      persist();
      loadDecisionMap();
      return;
    }
  }catch(error){
    errorBox(roots.map,error,loadDecisionMap);
  }
}
async function loadDecisionMap(){
  const node=roots.map;
  if(!state.orders||!state.fleet){
    node.innerHTML='<section class="dispatch-panel"><h1>Mapa de decisiones</h1><p>Primero cargá Órdenes y Flota para crear un Decision Case.</p><button data-data>Ir al Data Pack</button></section>';
    node.querySelector('[data-data]').onclick=()=>navigate('logistics-data');
    return;
  }
  try{
    if(!state.preflight)await preflight();
    ensureDecisionCase();
    state.decisionCase={
      ...state.decisionCase,
      nodes:deriveDecisionNodes(
        state.decisionCase,
        state.preflight?.decision_readiness,
      ),
    };
    persist();
    renderDecisionMap(node,{
      decisionCase:state.decisionCase,
      readiness:state.preflight?.decision_readiness,
      orders:state.orders,
      fleet:state.fleet,
      onConfigure:(nodeId)=>{
        state.activeNode=nodeId||'logistics_assignment';
        decisionContext(state.activeNode);
        persist();
        navigate('logistics-config');
      },
      onOpenResult:openCaseResult,
      onData:()=>navigate('logistics-data'),
    });
  }catch(error){
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
  const node=roots.config;
  if(!state.orders||!state.fleet){
    node.innerHTML='<h1>Configurar planificación de despachos</h1><p>Primero seleccioná Órdenes y Flota.</p><button data-back>Ir al Data Pack</button>';
    node.querySelector('[data-back]').onclick=()=>navigate('logistics-data');
    return;
  }
  if(!state.preflight){
    try{await preflight();}catch(error){errorBox(node,error,loadSchedulingConfig);return;}
  }
  const scheduling=schedulingEvidence();
  const assignmentNode=state.decisionCase?.nodes?.logistics_assignment;
  if(assignmentNode?.status!==STATUS.APPROVED){
    node.innerHTML='<section class="dispatch-panel"><span class="dispatch-kicker">DECISIÓN 02 · PLANIFICACIÓN DE DESPACHOS</span><h1>Planificación de despachos está en espera</h1><p>Primero aprobá Asignación de carga para fijar qué viajes y vehículos puede programar este motor.</p><button data-map>Volver al mapa</button></section>';
    node.querySelector('[data-map]').onclick=()=>navigate('logistics-map');
    return;
  }
  if(!scheduling?.data_ready){
    const missing=(scheduling?.missing||[]).map(item=>item.label).join(' · ');
    node.innerHTML='<section class="dispatch-panel"><span class="dispatch-kicker">DECISIÓN 02 · PLANIFICACIÓN DE DESPACHOS</span><h1>Faltan datos temporales</h1><p>Planificación de despachos necesita completar: '+esc(missing||'datos de planificación')+'.</p><button data-data>Completar Data Pack</button><button data-map>Volver al mapa</button></section>';
    node.querySelector('[data-data]').onclick=()=>navigate('logistics-data');
    node.querySelector('[data-map]').onclick=()=>navigate('logistics-map');
    return;
  }
  let sourceRun;
  try{
    sourceRun=await ensurePersistedApproval('logistics_assignment');
  }catch(error){
    errorBox(node,error,loadSchedulingConfig);
    return;
  }
  if(!sourceRun?.result_json){
    errorBox(node,new Error('No se pudo recuperar la asignación aprobada.'),loadSchedulingConfig);
    return;
  }
  const assignment=sourceRun.result_json;
  const assignmentMetrics=assignment.scenarios?.selected?.metrics||{};
  const slaAvailable=schedulingSlaAvailable();
  if(!slaAvailable)state.schedulingUseDueDates=false;

  node.innerHTML=`
    <div class="dispatch-config-screen dispatch-scheduling-config">
      <header class="dispatch-config-heading">
        <span class="dispatch-kicker">DECISIÓN 02 · PLANIFICACIÓN DE DESPACHOS</span>
        <h1>Configurar planificación de despachos</h1>
        <p>Programá en el tiempo los viajes aprobados. Esta decisión no puede cambiar vehículos, cargas ni cantidades definidos en Asignación de carga.</p>
      </header>
      <section class="dispatch-evidence-card">
        <div><span class="dispatch-config-eyebrow">Asignación de carga aprobada</span><strong>${num(assignmentMetrics.total_trips||0)} viajes</strong><small>Corrida ${esc(String(sourceRun.id).slice(0,8))}…</small></div>
        <div><span class="dispatch-config-eyebrow">Vehículos</span><strong>${num(assignmentMetrics.vehicles_used||0)} recursos</strong><small>Asignación bloqueada para esta decisión</small></div>
        <button data-map>Volver al mapa</button>
      </section>
      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">01</span><div><h2>Reglas temporales</h2><p>Estas reglas se aplican automáticamente a cada viaje aprobado.</p></div></div>
        <div class="dispatch-scheduling-rules">
          <article><strong>Fecha mínima de salida</strong><p>La más tardía entre las órdenes cargadas y la disponibilidad del vehículo.</p></article>
          <article><strong>Duración del viaje</strong><p>Se calcula con distancia, velocidad media y horas de conducción por día.</p></article>
          <article><strong>Ocupación del vehículo</strong><p>El recurso queda ocupado hasta completar ida, entrega y retorno a su base.</p></article>
          <article><strong>Asignación inmutable</strong><p>Vehículo, órdenes, productos y cantidades vienen aprobados desde Asignación de carga.</p></article>
        </div>
      </section>
      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">02</span><div><h2>Prioridad del calendario</h2><p>Planificación usa una jerarquía explícita para ordenar viajes que compiten por el mismo vehículo.</p></div></div>
        <div class="dispatch-schedule-priority">
          ${slaAvailable
            ?'<ol><li><strong>1. Minimizar órdenes fuera de fecha objetivo</strong><small>La fecha objetivo domina el resto del criterio.</small></li><li><strong>2. Minimizar días totales de tardanza</strong></li><li><strong>3. Minimizar espera desde disponibilidad</strong></li><li><strong>4. Compactar el calendario</strong></li></ol>'
            :'<ol><li><strong>1. Minimizar espera desde disponibilidad</strong></li><li><strong>2. Compactar el calendario</strong></li></ol>'}
        </div>
        <label class="dispatch-policy-row ${slaAvailable?'':'is-unavailable'}"><div><strong>Considerar fecha objetivo de entrega</strong><small>${slaAvailable?'Usa la fecha objetivo para proteger el nivel de servicio.':'No disponible: la fecha objetivo no está completa en Órdenes.'}</small></div><input type="checkbox" data-sla ${state.schedulingUseDueDates&&slaAvailable?'checked':''} ${slaAvailable?'':'disabled'}><span class="dispatch-toggle" aria-hidden="true"></span></label>
      </section>
      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">03</span><div><h2>Qué no puede cambiar</h2><p>Esta separación protege la trazabilidad entre decisiones.</p></div></div>
        <div class="dispatch-assignment-boundary"><span aria-hidden="true">✓</span><div><strong>La asignación de carga queda congelada</strong><p>Planificación sólo agrega fechas y secuencia sobre los viajes aprobados.</p></div></div>
      </section>
      <footer class="dispatch-footer dispatch-config-footer"><div><span class="dispatch-config-eyebrow">Planificación lista para ejecutar</span><strong>${slaAvailable&&state.schedulingUseDueDates?'Servicio → tardanza → espera → calendario':'Espera → calendario'}</strong><small>${num(assignmentMetrics.total_trips||0)} viajes fijos · ${num(assignmentMetrics.vehicles_used||0)} vehículos</small></div><button data-review>Revisar y ejecutar →</button></footer>
      <dialog class="dispatch dispatch-review"><form method="dialog"><span class="dispatch-config-eyebrow">Antes de ejecutar</span><h2>Revisar planificación</h2><div class="dispatch-review-summary"><p><strong>Entrada</strong><span>${num(assignmentMetrics.total_trips||0)} viajes de la asignación aprobada</span></p><p><strong>Asignación</strong><span>No se puede modificar</span></p><p><strong>Fecha objetivo</strong><span>${slaAvailable&&state.schedulingUseDueDates?'Activa':'No participa'}</span></p><p><strong>Objetivo</strong><span>${slaAvailable&&state.schedulingUseDueDates?'Servicio primero':'Salida temprana'}</span></p></div><div class="dispatch-actions"><button value="cancel">Volver</button><button type="button" data-execute>Generar planificación</button></div></form></dialog>
    </div>`;

  node.querySelector('[data-map]').onclick=()=>navigate('logistics-map');
  const sla=node.querySelector('[data-sla]');
  if(sla)sla.onchange=()=>{
    state.schedulingUseDueDates=sla.checked;
    persist();
    loadSchedulingConfig();
  };
  const modal=node.querySelector('dialog');
  node.querySelector('[data-review]').onclick=()=>modal.showModal();
  node.querySelector('[data-execute]').onclick=()=>{
    modal.close();
    executeScheduling(sourceRun.id);
  };
  persist();
}

async function loadConfig(){
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
    syncDimensionsToEvidence({initialize:true});
    await mountAssignmentConfig(node,{
      state,
      persist,
      capabilities:assignmentCapabilities(),
      onData:()=>navigate('logistics-data'),
      onExecute:execute,
    });
  }catch(error){
    errorBox(node,error,loadConfig);
  }
}

function pending(message){document.body.classList.add('dispatch-result');roots.dashboard.innerHTML=`<section class="dispatch-panel"><h1>Preparando tu decisión</h1><p role="status">${esc(message)}</p><div class="dispatch-loading" aria-label="Procesando"></div><p>El Decision Case conserva el estado real de esta ejecución.</p><button data-return>Volver al mapa</button></section>`;roots.dashboard.querySelector('[data-return]').onclick=()=>navigate('logistics-map');}
async function poll(id,generation,nodeId=state.activeNode){
  if(generation!==pollGeneration)return;
  try{
    const run=await api('/api/runs/'+id);
    if(generation!==pollGeneration)return;
    if(run.status==='completed'){
      show(run);
      return;
    }
    if(run.status==='error'){
      if(state.decisionCase?.nodes?.[nodeId]?.run_id===id){
        state.decisionCase=transitionNode(
          state.decisionCase,
          nodeId,
          STATUS.ERROR,
          {run_id:id,error:run.error_message||'La ejecución no pudo completarse.'},
        );
        persist();
      }
      throw new Error(run.error_message||'La ejecución no pudo completarse.');
    }
    const stage=run.progress_json?.stage||'validating';
    const assignmentNames={
      validating:'Validando Órdenes y Flota',
      constructing:'Construyendo alternativas de carga',
      baseline:'Preparando referencia histórica',
      sensitivity:'Comparando objetivos',
      summarizing:'Preparando la asignación recomendada',
    };
    const schedulingNames={
      validating:'Validando asignación y evidencia temporal',
      constructing:'Construyendo secuencia temporal',
      summarizing:'Preparando la planificación recomendada',
    };
    const names=nodeId==='logistics_scheduling'?schedulingNames:assignmentNames;
    pending(
      stage.startsWith('optimizing:')
        ?(nodeId==='logistics_scheduling'
          ?'Optimizando secuencia y nivel de servicio'
          :'Optimizando la distribución de carga')
        :(names[stage]||'Evaluando la decisión')
    );
  }catch(e){
    if(e.status!==404){
      errorBox(roots.dashboard,e,()=>poll(id,generation,nodeId));
      return;
    }
  }
  timer=setTimeout(()=>poll(id,generation,nodeId),1500);
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
  pending('Registrando la corrida…');
  navigate('decision-dashboard');
  const generation=++pollGeneration;
  clearTimeout(timer);
  timer=setTimeout(()=>poll(id,generation,'logistics_assignment'),1000);
  try{
    const run=await post('/api/runs?run_id='+id,{
      orders_dataset_id:state.orders.id,
      fleet_dataset_id:state.fleet.id,
      configuration:configuration(),
      options:{
        allow_third_party:state.resourceMode!=='own',
        resource_mode:state.resourceMode,
        analysis_depth:state.analysisDepth,
        anomaly_decisions:Object.fromEntries(
          Object.entries(state.decisions).filter(([,v])=>v),
        ),
      },
      decision_case:caseRef(state.decisionCase),
    });
    if(generation===pollGeneration)show(run);
  }catch(e){
    if(generation!==pollGeneration)return;
    clearTimeout(timer);
    state.decisionCase=transitionNode(
      state.decisionCase,
      'logistics_assignment',
      STATUS.ERROR,
      {run_id:id,error:e.message},
    );
    persist();
    errorBox(roots.dashboard,e,()=>poll(id,generation));
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
  pending('Registrando la planificación…');
  navigate('decision-dashboard');
  const generation=++pollGeneration;
  clearTimeout(timer);
  timer=setTimeout(()=>poll(id,generation,'logistics_scheduling'),1000);
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
    if(generation===pollGeneration)show(run);
  }catch(e){
    if(generation!==pollGeneration)return;
    clearTimeout(timer);
    state.decisionCase=transitionNode(
      state.decisionCase,
      'logistics_scheduling',
      STATUS.ERROR,
      {run_id:id,error:e.message},
    );
    persist();
    errorBox(roots.dashboard,e,()=>poll(id,generation,'logistics_scheduling'));
  }
}

export function show(run){
  clearTimeout(timer);
  pollGeneration++;
  state.run=run;
  const r=run.result_json;
  const schema=r?.schema_version;
  const isAssignmentRun=schema==='assignment_v1';
  const isSchedulingRun=schema==='scheduling_v1';
  const caseMeta=r?.decision_case;
  const nodeId=isSchedulingRun
    ?'logistics_scheduling'
    :(isAssignmentRun?'logistics_assignment':null);

  if(nodeId&&caseMeta?.case_id){
    if(!state.decisionCase||state.decisionCase.id!==caseMeta.case_id){
      state.decisionCase=createDecisionCase(
        caseMeta.case_id,
        {id:r.inputs?.orders?.dataset_id},
        {id:r.inputs?.fleet?.dataset_id},
        run.created_at,
      );
    }
    if(isSchedulingRun){
      const sourceRunId=r.inputs?.assignment?.run_id;
      if(sourceRunId){
        state.decisionCase=transitionNode(
          state.decisionCase,
          'logistics_assignment',
          STATUS.APPROVED,
          {
            run_id:sourceRunId,
            approved_at:r.inputs?.assignment?.approved_at||state.decisionCase.nodes?.logistics_assignment?.approved_at||run.created_at,
            error:null,
          },
        );
      }
    }
    const persistedApproved=caseMeta.status==='approved'&&caseMeta.approved_at;
    state.decisionCase=transitionNode(
      state.decisionCase,
      nodeId,
      persistedApproved?STATUS.APPROVED:STATUS.REVIEW,
      {
        run_id:run.id,
        approved_at:persistedApproved?caseMeta.approved_at:null,
        error:null,
      },
    );
    state.activeNode=nodeId;
    decisionContext(nodeId);
  }

  persist();
  document.body.classList.add('dispatch-result');
  urlRun(run.id,schema||'assignment_v1');
  window.dationSetDashboardReady(true);

  dashboard(
    roots.dashboard,
    run,
    async()=>{
      const config=r.configuration||{};
      const options=config.options||{};
      if(isSchedulingRun){
        state.activeNode='logistics_scheduling';
        state.schedulingUseDueDates=config.use_delivery_due_dates??true;
      }else if(isAssignmentRun){
        state.activeNode='logistics_assignment';
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
        state.analysisDepth=['essential','comparative'].includes(options.analysis_depth)
          ?options.analysis_depth
          :'comparative';
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

      try{
        const [o,f]=await Promise.all([
          api('/api/datasets/'+r.inputs.orders.dataset_id+'/profile'),
          api('/api/datasets/'+r.inputs.fleet.dataset_id+'/profile'),
        ]);
        state.orders=o.dataset;
        state.fleet=f.dataset;
        state.preflight=null;
        state.configPreview=null;
        ensureDecisionCase();
        decisionContext(state.activeNode);
        persist();
        navigate('logistics-config');
      }catch(e){
        alert(e.message);
      }
    },
    {
      status:(nodeId&&caseMeta?.case_id&&state.decisionCase?.id===caseMeta.case_id)
        ?state.decisionCase.nodes?.[nodeId]?.status
        :null,
      decisionCase:state.decisionCase,
      activeNode:nodeId,
      onFlow:state.decisionCase?()=>navigate('logistics-map'):null,
      onOpenNode:state.decisionCase?openCaseResult:null,
      onApprove:(nodeId&&caseMeta?.case_id&&state.decisionCase?.id===caseMeta.case_id)
        ?async()=>{
          const approved=await post('/api/runs/'+run.id+'/approve',{
            case_id:state.decisionCase.id,
            node_id:nodeId,
          });
          const approvedAt=approved.result_json?.decision_case?.approved_at||new Date().toISOString();
          state.run=approved;
          state.decisionCase=transitionNode(
            state.decisionCase,
            nodeId,
            STATUS.APPROVED,
            {run_id:run.id,approved_at:approvedAt,error:null},
          );
          unlockNextNode(nodeId);
          persist();
          return state.decisionCase;
        }
        :null,
      onApprovalComplete:(nodeId&&state.decisionCase)
        ?()=>{unlockNextNode(nodeId);persist();}
        :null,
    },
  );
  navigate('decision-dashboard');
}

for(const [key,view]of [['data','logistics-data'],['map','logistics-map'],['config','logistics-config'],['dashboard','decision-dashboard']])roots[key]=root(view,'dispatch-'+key+'-root');
window.DationDispatch={
  show,
  isReady:ready,
  openActiveDecisionResult:()=>{
    if(!state.activeNode)return;
    return openCaseResult(state.activeNode);
  },
  getActiveDecision:()=>({
    id:state.activeNode,
    label:state.activeNode?DECISION_LABELS[state.activeNode]||'Decisión':null,
    hasRun:Boolean(state.activeNode&&state.decisionCase?.nodes?.[state.activeNode]?.run_id),
    status:state.activeNode?state.decisionCase?.nodes?.[state.activeNode]?.status||null:null,
  }),
};
document.body.classList.add('dispatch-enabled');
window.addEventListener('dation:view',e=>{const view=e.detail.view;if(view==='logistics-data'){roots.data.hidden=false;document.body.classList.add('dispatch-enabled');loadData();}if(view==='logistics-map'&&document.body.classList.contains('dispatch-enabled')){roots.map.hidden=false;loadDecisionMap();}if(view==='logistics-config'&&document.body.classList.contains('dispatch-enabled')){roots.config.hidden=false;loadConfig();}});
const query=new URLSearchParams(location.search);if(['assignment_v1','scheduling_v1','dispatch_v1','dispatch_v2'].includes(query.get('dda'))&&query.get('run_id')){const queryNode=query.get('dda')==='scheduling_v1'?'logistics_scheduling':'logistics_assignment';state.activeNode=queryNode;if(state.decisionCase?.nodes?.[queryNode]&&!state.decisionCase.nodes[queryNode].run_id){state.decisionCase=transitionNode(state.decisionCase,queryNode,STATUS.RUNNING,{run_id:query.get('run_id'),error:null});}window.dationSetDecisionContext?.({id:queryNode,label:DECISION_LABELS[queryNode]||'Decisión',stepLabel:queryNode==='logistics_assignment'?'Decisión 01':'Decisión 02',hasRun:true,status:state.decisionCase?.nodes?.[queryNode]?.status||STATUS.RUNNING});pending('Recuperando la corrida…');navigate('decision-dashboard');poll(query.get('run_id'),++pollGeneration,queryNode);}
if(state.activeNode)decisionContext(state.activeNode);
if(window.dationGetCurrentView?.()==='logistics-data')loadData();
if(window.dationGetCurrentView?.()==='logistics-map')loadDecisionMap();
