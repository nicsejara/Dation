import {esc,num,date,vehicle,api,post,errorBox} from './shared.mjs';import {rebalance} from './selectors.mjs';import {render as dashboard} from './dashboard.mjs?v=decision-map-nodal-v1';
import {mountUploadScreen} from './upload/index.mjs?v=upload-pro-v1';
import {renderDecisionMap} from './decision-map.mjs?v=decision-map-nodal-v1';
import {STATUS,createDecisionCase,replaceInputs,transitionNode,inputSignature,caseRef,deriveDecisionNodes} from './decision-case.mjs';
const KEY='dation.dispatch.workspace.v4';
const NAV_VERSION='workspace-nav-v1';
const DECISION_LABELS={
  logistics_assignment:'Asignación de carga',
  logistics_scheduling:'Planificación',
  logistics_final_assignment:'Asignación final',
};
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
const state={
  orders:saved.orders||null,
  fleet:saved.fleet||null,
  dimensions:restoredDimensions.length?restoredDimensions:[...CORE_DIMENSIONS],
  weights:saved.weights||balancedWeights(restoredDimensions.length?restoredDimensions:CORE_DIMENSIONS),
  objective:validObjectives.includes(saved.objective)?saved.objective:'balanced',
  analysisDepth:['essential','comparative','deep'].includes(saved.analysisDepth)?saved.analysisDepth:'comparative',
  allow:saved.allow??true,
  decisions:saved.decisions||{},
  configured:Boolean(saved.configured),
  decisionCase:saved.decisionCase||null,
  activeNode:saved.navigationVersion===NAV_VERSION
    ?(saved.activeNode||null)
    :null,
  schedulingUseDueDates:saved.schedulingUseDueDates??true,
  preflight:null,
  available:false,
  run:null,
};
if(OBJECTIVE_DIMENSION[state.objective]&&!state.dimensions.includes(OBJECTIVE_DIMENSION[state.objective]))state.objective='balanced';
state.weights=state.objective==='custom'
  ?normalizeWeights(state.weights,state.dimensions)
  :presetWeights(state.objective,state.dimensions);
let timer=null,pollGeneration=0;const roots={};
function persist(){try{sessionStorage.setItem(KEY,JSON.stringify({orders:state.orders,fleet:state.fleet,dimensions:state.dimensions,weights:state.weights,objective:state.objective,analysisDepth:state.analysisDepth,allow:state.allow,decisions:state.decisions,configured:state.configured,decisionCase:state.decisionCase,activeNode:state.activeNode,schedulingUseDueDates:state.schedulingUseDueDates,navigationVersion:NAV_VERSION}));}catch{}}
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
    state.configured=false;
    state.decisions={};
    state.dimensions=[...CORE_DIMENSIONS];
    state.objective='balanced';
    state.weights=balancedWeights(state.dimensions);
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
    hasRun:Boolean(node?.run_id),
    status:node?.status||null,
  });
}
function navigate(view){window.dationSetDataReady(ready());window.dationNavigate(view);}
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
function action(b,fn){b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){alert(e.message);}finally{b.disabled=false;}};}
async function preflight(){
  state.preflight=null;
  window.dationSetDataReady(false);
  if(!state.orders||!state.fleet)return;
  state.preflight=await post('/api/runs/preflight',{
    orders_dataset_id:state.orders.id,
    fleet_dataset_id:state.fleet.id,
    allow_third_party:state.allow,
  });
  ensureDecisionCase();
  window.dationSetDataReady(ready());
  persist();
}
async function loadData() {
  await mountUploadScreen(
    roots.data,
    {
      state,
      persist,
      runPreflight: preflight,
      onNext: () => {ensureDecisionCase();navigate('logistics-map');},
      isReady: ready,
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
    node.innerHTML='<section class="dispatch-panel"><h1>Mapa de decisiones</h1><p>Primero cargá Orders y Fleet para crear un Decision Case.</p><button data-data>Ir al Data Pack</button></section>';
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
  const weights=state.objective==='custom'?normalizeWeights(state.weights,state.dimensions):presetWeights(state.objective,state.dimensions);
  return Object.fromEntries(PRIORITY_KEYS.map(k=>[k,weights[k]/100]));
}
function configuration(){const config={mode:state.objective==='custom'?'custom':'preset',objective:state.objective,dimensions:[...state.dimensions]};if(state.objective==='custom')config.weights=decimalWeights();return config;}
function activeDimensionText(){return state.dimensions.map(k=>DIMENSION_LABELS[k]).join(' · ');}
function decisionSummary(){return `${OBJECTIVE_LABELS[state.objective]} · ${state.dimensions.length} dimensión${state.dimensions.length===1?'':'es'} · análisis ${DEPTH_LABELS[state.analysisDepth].toLowerCase()}`;}


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
    node.innerHTML='<h1>Configurar Planificación</h1><p>Primero seleccioná Orders y Fleet.</p><button data-back>Ir al Data Pack</button>';
    node.querySelector('[data-back]').onclick=()=>navigate('logistics-data');
    return;
  }

  if(!state.preflight){
    try{await preflight();}catch(error){errorBox(node,error,loadSchedulingConfig);return;}
  }

  const scheduling=schedulingEvidence();
  const assignmentNode=state.decisionCase?.nodes?.logistics_assignment;
  if(assignmentNode?.status!==STATUS.APPROVED){
    node.innerHTML='<section class="dispatch-panel"><span class="dispatch-kicker">DECISIÓN 02 · PLANIFICACIÓN</span><h1>Scheduling todavía está bloqueado</h1><p>Primero aprobá Assignment para fijar qué viajes y vehículos puede programar este motor.</p><button data-map>Volver al mapa</button></section>';
    node.querySelector('[data-map]').onclick=()=>navigate('logistics-map');
    return;
  }
  if(!scheduling?.data_ready){
    const missing=(scheduling?.missing||[]).map(item=>item.label).join(' · ');
    node.innerHTML='<section class="dispatch-panel"><span class="dispatch-kicker">DECISIÓN 02 · PLANIFICACIÓN</span><h1>Faltan datos temporales</h1><p>Scheduling necesita completar: '+esc(missing||'datos de planificación')+'.</p><button data-data>Completar Data Pack</button><button data-map>Volver al mapa</button></section>';
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
    errorBox(node,new Error('No se pudo recuperar Assignment aprobada.'),loadSchedulingConfig);
    return;
  }

  const assignment=sourceRun.result_json;
  const assignmentMetrics=assignment.scenarios?.selected?.metrics||{};
  const slaAvailable=schedulingSlaAvailable();
  if(!slaAvailable)state.schedulingUseDueDates=false;

  node.innerHTML=`
    <div class="dispatch-config-screen dispatch-scheduling-config">
      <header class="dispatch-config-heading">
        <span class="dispatch-kicker">DECISIÓN 02 · PLANIFICACIÓN</span>
        <h1>Configurar Scheduling</h1>
        <p>Programá en el tiempo los viajes aprobados. Scheduling no puede cambiar vehículos, cargas ni cantidades definidos en Assignment.</p>
      </header>

      <section class="dispatch-evidence-card">
        <div><span class="dispatch-config-eyebrow">Assignment aprobada</span><strong>${num(assignmentMetrics.total_trips||0)} viajes</strong><small>Corrida ${esc(String(sourceRun.id).slice(0,8))}…</small></div>
        <div><span class="dispatch-config-eyebrow">Vehículos</span><strong>${num(assignmentMetrics.vehicles_used||0)} recursos</strong><small>Asignación bloqueada para esta decisión</small></div>
        <button data-map>Volver al mapa</button>
      </section>

      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">01</span><div><h2>Reglas temporales</h2><p>Estas reglas se aplican automáticamente a cada viaje aprobado.</p></div></div>
        <div class="dispatch-scheduling-rules">
          <article><strong>Fecha mínima de salida</strong><p>La más tardía entre las órdenes cargadas y available_from del vehículo.</p></article>
          <article><strong>Duración del viaje</strong><p>Se calcula con distancia, velocidad media y horas de conducción por día.</p></article>
          <article><strong>Ocupación del vehículo</strong><p>El recurso queda ocupado hasta completar ida, entrega y retorno a su base.</p></article>
          <article><strong>Asignación inmutable</strong><p>Vehicle ID, órdenes, productos y cantidades vienen aprobados desde Assignment.</p></article>
        </div>
      </section>

      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">02</span><div><h2>Prioridad del calendario</h2><p>Scheduling usa una jerarquía explícita para ordenar viajes que compiten por el mismo vehículo.</p></div></div>
        <div class="dispatch-schedule-priority">
          ${slaAvailable
            ?'<ol><li><strong>1. Minimizar órdenes fuera de fecha objetivo</strong><small>delivery_due_date domina el resto del objetivo.</small></li><li><strong>2. Minimizar días totales de tardanza</strong></li><li><strong>3. Minimizar espera desde ready date</strong></li><li><strong>4. Compactar el calendario</strong></li></ol>'
            :'<ol><li><strong>1. Minimizar espera desde ready date</strong></li><li><strong>2. Compactar el calendario</strong></li></ol>'}
        </div>
        <label class="dispatch-policy-row ${slaAvailable?'':'is-unavailable'}"><div><strong>Considerar fecha objetivo de entrega</strong><small>${slaAvailable?'Usa delivery_due_date para proteger el nivel de servicio.':'No disponible: delivery_due_date no está completo en Orders.'}</small></div><input type="checkbox" data-sla ${state.schedulingUseDueDates&&slaAvailable?'checked':''} ${slaAvailable?'':'disabled'}><span class="dispatch-toggle" aria-hidden="true"></span></label>
      </section>

      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">03</span><div><h2>Qué no puede cambiar</h2><p>Esta separación protege la trazabilidad entre decisiones.</p></div></div>
        <div class="dispatch-assignment-boundary"><span aria-hidden="true">✓</span><div><strong>Assignment queda congelada</strong><p>Scheduling sólo agrega dispatch_date, arrival_date, cycle_days y resource_available_again sobre los viajes aprobados.</p></div></div>
      </section>

      <footer class="dispatch-footer dispatch-config-footer"><div><span class="dispatch-config-eyebrow">Scheduling listo para ejecutar</span><strong>${slaAvailable&&state.schedulingUseDueDates?'SLA → tardanza → espera → calendario':'Espera → calendario'}</strong><small>${num(assignmentMetrics.total_trips||0)} viajes fijos · ${num(assignmentMetrics.vehicles_used||0)} vehículos</small></div><button data-review>Revisar y ejecutar →</button></footer>

      <dialog class="dispatch dispatch-review"><form method="dialog"><span class="dispatch-config-eyebrow">Antes de ejecutar</span><h2>Revisar Scheduling</h2><div class="dispatch-review-summary"><p><strong>Input</strong><span>${num(assignmentMetrics.total_trips||0)} viajes de Assignment aprobada</span></p><p><strong>Asignación</strong><span>No se puede modificar</span></p><p><strong>SLA</strong><span>${slaAvailable&&state.schedulingUseDueDates?'Activo':'No participa'}</span></p><p><strong>Objetivo</strong><span>${slaAvailable&&state.schedulingUseDueDates?'Servicio primero':'Salida temprana'}</span></p></div><p>Motor Scheduling 1.0.0 · secuencia temporal por vehículo físico.</p><div class="dispatch-actions"><button value="cancel">Volver</button><button type="button" data-execute>Generar planificación</button></div></form></dialog>
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
    node.innerHTML='<h1>Configurar Assignment</h1><p>Primero seleccioná Orders y Fleet.</p><button data-back>Ir al Data Pack</button>';
    node.querySelector('[data-back]').onclick=()=>navigate('logistics-data');
    return;
  }

  node.innerHTML='<div class="dispatch-config-heading"><span class="dispatch-kicker">DECISIÓN 01 · ASIGNACIÓN DE CARGA</span><h1>Configurar Assignment</h1><p>Elegí cómo querés distribuir la carga entre los vehículos disponibles. Las fechas se resolverán después, en Planificación.</p><p role="status">Validando la evidencia seleccionada…</p></div>';
  try{
    await preflight();
    syncDimensionsToEvidence({initialize:true});
  }catch(error){
    errorBox(node,error,loadConfig);
    return;
  }

  const capabilities=assignmentCapabilities();
  const capabilityAvailable=key=>Boolean(capabilities[key]?.available);
  const objectiveRequirement=key=>OBJECTIVE_DIMENSION[key]||null;
  const objectiveEnabled=key=>{
    const required=objectiveRequirement(key);
    return !required||capabilityAvailable(required);
  };
  const objectives=[
    ['min_trips','Menor cantidad de viajes','Consolida la carga para reducir la cantidad total de viajes.'],
    ['min_cost','Costo mínimo','Minimiza el costo estimado de ida y vuelta más el costo fijo por viaje.'],
    ['max_own_fleet','Mayor uso de flota propia','Reduce el peso asignado a transportistas tercerizados.'],
    ['min_co2','CO₂ mínimo','Reduce las emisiones estimadas de los viajes necesarios.'],
    ['balanced','Balanceado','Equilibra las variables activas con el mismo peso.'],
  ];
  const dimensionCopy={
    trips:'Cantidad de viajes necesarios para transportar toda la demanda.',
    cost:'Costo estimado por distancia recorrida y costo fijo de cada viaje.',
    own_fleet:'Porción de la carga asignada a vehículos propios frente a terceros.',
    co2:'Emisiones estimadas de ida y vuelta según el factor informado.',
  };
  const missingCopy={
    cost:'Requiere cost_per_km y fixed_trip_cost completos en Fleet.',
    co2:'Requiere co2_kg_per_km completo en Fleet.',
  };
  const depths=[
    ['essential','Esencial','Resuelve la recomendación principal con el mínimo análisis necesario.'],
    ['comparative','Comparativo','Suma alternativas por objetivo para entender los trade-offs.'],
    ['deep','Profundo','Conserva evidencia ampliada de las alternativas evaluadas.'],
  ];

  node.innerHTML=`
    <div class="dispatch-config-screen dispatch-assignment-config">
      <header class="dispatch-config-heading">
        <span class="dispatch-kicker">DECISIÓN 01 · ASIGNACIÓN DE CARGA</span>
        <h1>Configurar Assignment</h1>
        <p>Definí qué significa una buena distribución de carga. Esta decisión no programa fechas ni calcula SLA.</p>
      </header>

      <section class="dispatch-evidence-card">
        <div><span class="dispatch-config-eyebrow">Orders</span><strong>${esc(state.orders.original_filename)}</strong><small>${num(state.orders.row_count)} registros</small></div>
        <div><span class="dispatch-config-eyebrow">Fleet</span><strong>${esc(state.fleet.label||state.fleet.original_filename)}</strong><small>${num(state.fleet.row_count)} vehículos</small></div>
        <button data-map>Volver al mapa</button>
        <button data-data>Cambiar datos</button>
      </section>

      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">01</span><div><h2>Objetivo de Assignment</h2><p>Elegí el criterio principal para construir los viajes y distribuir la carga.</p></div></div>
        <div class="dispatch-objective-grid">
          ${objectives.map(([key,label,copy])=>{
            const enabled=objectiveEnabled(key);
            return `<button class="dispatch-objective-card ${enabled?'':'is-disabled'}" data-preset="${key}" aria-pressed="${state.objective===key}" ${enabled?'':'disabled'}><strong>${label}</strong><small>${copy}</small>${enabled?'':`<em>${missingCopy[objectiveRequirement(key)]||'Faltan datos para este objetivo'}</em>`}</button>`;
          }).join('')}
        </div>
        <details class="dispatch-custom-priorities" ${state.objective==='custom'?'open':''}>
          <summary>Personalizar prioridades</summary>
          <p>Combiná únicamente las variables que tengan evidencia suficiente en el Data Pack.</p>
          <button type="button" data-customize>Activar configuración personalizada</button>
          <div class="dispatch-sliders">
            ${PRIORITY_KEYS.map(key=>{
              const available=capabilityAvailable(key);
              return `<label class="dispatch-weight-row ${state.dimensions.includes(key)&&available?'':'is-disabled'}"><span>${DIMENSION_LABELS[key]}</span><output data-weight="${key}">${state.weights[key]} %</output><input type="range" min="0" max="100" step="1" value="${state.weights[key]}" data-slider="${key}" ${state.dimensions.includes(key)&&available?'':'disabled'}></label>`;
            }).join('')}
          </div>
        </details>
      </section>

      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">02</span><div><h2>Variables que intervienen</h2><p>Hacé el análisis tan simple o tan completo como necesites. Lo que no tenga datos suficientes queda deshabilitado.</p></div></div>
        <div class="dispatch-dimensions">
          ${PRIORITY_KEYS.map(key=>{
            const available=capabilityAvailable(key);
            return `<label class="dispatch-dimension-row ${available?'':'is-unavailable'}"><div><strong>${DIMENSION_LABELS[key]}</strong><small>${dimensionCopy[key]}</small>${available?'':`<em>${missingCopy[key]||'No disponible con este Data Pack.'}</em>`}</div><input type="checkbox" data-dimension="${key}" ${state.dimensions.includes(key)?'checked':''} ${available?'':'disabled'}><span class="dispatch-toggle" aria-hidden="true"></span></label>`;
          }).join('')}
        </div>
        <div class="dispatch-locked-model"><div><span class="dispatch-config-eyebrow">Siempre activas</span><strong>Restricciones físicas de Assignment</strong><p>Unidades enteras · capacidad por viaje · origen/site · ruta · distancia</p></div><span class="dispatch-lock">Sin calendario</span></div>
        <div class="dispatch-assignment-boundary"><span aria-hidden="true">→</span><div><strong>Las fechas se deciden después</strong><p>estimated_dispatch_date, velocidad, horas de conducción, disponibilidad futura y SLA quedan reservados para Planificación.</p></div></div>
      </section>

      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">03</span><div><h2>Profundidad del análisis</h2><p>Elegí cuántas alternativas querés evaluar antes de recomendar una asignación.</p></div></div>
        <div class="dispatch-depth-grid">${depths.map(([key,label,copy])=>`<button class="dispatch-depth-card" data-depth="${key}" aria-pressed="${state.analysisDepth===key}"><span class="dispatch-depth-radio" aria-hidden="true"></span><strong>${label}${key==='comparative'?'<em>Recomendado</em>':''}</strong><small>${copy}</small></button>`).join('')}</div>
      </section>

      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">04</span><div><h2>Política de recursos</h2><p>Definí qué flota puede participar en esta asignación.</p></div></div>
        <label class="dispatch-policy-row"><div><strong>Permitir flota tercerizada</strong><small>Permite asignar carga a recursos externos cuando el objetivo seleccionado lo justifica.</small></div><input type="checkbox" data-outsourcing ${state.allow?'checked':''}><span class="dispatch-toggle" aria-hidden="true"></span></label>
      </section>

      ${state.preflight.anomalies.length?`<section class="dispatch-panel dispatch-required-review"><div class="dispatch-config-section-head"><span class="dispatch-config-step">!</span><div><h2>Revisión requerida</h2><p>Estas órdenes son outliers de tamaño y necesitan una decisión explícita antes de ejecutar.</p></div></div>${state.preflight.anomalies.map(a=>`<label class="dispatch-review-row"><span><strong>${esc(a.order_id)}</strong><small>${esc(a.detail)}</small></span><select data-anomaly="${esc(a.order_id)}"><option value="">Elegí una acción…</option><option value="include" ${state.decisions[a.order_id]==='include'?'selected':''}>Incluir</option><option value="exclude" ${state.decisions[a.order_id]==='exclude'?'selected':''}>Excluir</option></select></label>`).join('')}</section>`:''}

      <footer class="dispatch-footer dispatch-config-footer"><div><span class="dispatch-config-eyebrow">Assignment listo para ejecutar</span><strong data-config-summary></strong><small data-config-detail></small></div><button data-review>Revisar y ejecutar →</button></footer>

      <dialog class="dispatch dispatch-review"><form method="dialog"><span class="dispatch-config-eyebrow">Antes de ejecutar</span><h2>Revisar Assignment</h2><div data-summary></div><div class="dispatch-assignment-boundary"><span aria-hidden="true">i</span><div><strong>Esta corrida no programa fechas</strong><p>El resultado será una distribución de carga por viaje y vehículo. El cuándo se ejecuta cada viaje se resolverá en Planificación.</p></div></div><p>Motor Assignment 1.0.0 · capacidad, site, ruta y unidades enteras. La configuración y los archivos quedan vinculados al Decision Case.</p><div class="dispatch-actions"><button value="cancel">Volver</button><button type="button" data-execute>Generar Assignment</button></div></form></dialog>
    </div>`;

  function sync(){
    syncDimensionsToEvidence();
    state.weights=state.objective==='custom'
      ?normalizeWeights(state.weights,state.dimensions)
      :presetWeights(state.objective,state.dimensions);

    node.querySelectorAll('[data-preset]').forEach(button=>{
      const required=OBJECTIVE_DIMENSION[button.dataset.preset];
      const enabled=!required||capabilityAvailable(required);
      button.disabled=!enabled;
      button.setAttribute('aria-pressed',String(button.dataset.preset===state.objective));
    });
    node.querySelectorAll('[data-depth]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.depth===state.analysisDepth)));
    node.querySelectorAll('[data-dimension]').forEach(input=>{
      const available=capabilityAvailable(input.dataset.dimension);
      input.checked=state.dimensions.includes(input.dataset.dimension);
      input.disabled=!available||(state.dimensions.length===1&&input.checked);
    });
    PRIORITY_KEYS.forEach(key=>{
      const output=node.querySelector('[data-weight="'+key+'"]');
      const slider=node.querySelector('[data-slider="'+key+'"]');
      if(output)output.textContent=state.weights[key]+' %';
      if(slider){
        slider.value=state.weights[key];
        slider.disabled=!capabilityAvailable(key)||!state.dimensions.includes(key);
        slider.closest('.dispatch-weight-row')?.classList.toggle('is-disabled',slider.disabled);
      }
    });
    node.querySelector('[data-config-summary]').textContent=decisionSummary();
    node.querySelector('[data-config-detail]').textContent=activeDimensionText()+' · sin variables temporales';
    node.querySelector('[data-review]').disabled=!ready()||state.preflight.anomalies.some(a=>!state.decisions[a.order_id]);
    persist();
  }

  node.querySelector('[data-map]').onclick=()=>navigate('logistics-map');
  node.querySelector('[data-data]').onclick=()=>navigate('logistics-data');
  node.querySelectorAll('[data-preset]').forEach(button=>button.onclick=()=>{
    if(button.disabled)return;
    const next=button.dataset.preset;
    const required=OBJECTIVE_DIMENSION[next];
    if(required&&!state.dimensions.includes(required)){
      state.dimensions=[...new Set([...state.dimensions,required])].sort((a,b)=>PRIORITY_KEYS.indexOf(a)-PRIORITY_KEYS.indexOf(b));
    }
    state.objective=next;
    state.configured=true;
    state.weights=presetWeights(next,state.dimensions);
    sync();
  });
  node.querySelector('[data-customize]').onclick=()=>{
    state.objective='custom';
    state.configured=true;
    state.weights=balancedWeights(state.dimensions);
    node.querySelector('.dispatch-custom-priorities').open=true;
    sync();
  };
  node.querySelectorAll('[data-slider]').forEach(slider=>slider.oninput=()=>{
    state.objective='custom';
    state.configured=true;
    const key=slider.dataset.slider;
    const others=state.dimensions.filter(item=>item!==key);
    const target=others.length?+slider.value:100;
    const next={...state.weights,[key]:target};
    const remaining=100-target;
    if(others.length){
      const total=others.reduce((sum,item)=>sum+(state.weights[item]||0),0);
      const raw=others.map((item,index)=>{
        const share=total?remaining*(state.weights[item]||0)/total:remaining/others.length;
        return {item,index,base:Math.floor(share),fraction:share-Math.floor(share)};
      });
      let missing=remaining-raw.reduce((sum,item)=>sum+item.base,0);
      [...raw].sort((a,b)=>b.fraction-a.fraction||a.index-b.index).slice(0,missing).forEach(item=>item.base+=1);
      raw.forEach(item=>next[item.item]=item.base);
    }
    PRIORITY_KEYS.filter(item=>!state.dimensions.includes(item)).forEach(item=>next[item]=0);
    state.weights=next;
    sync();
  });
  node.querySelectorAll('[data-dimension]').forEach(input=>input.onchange=()=>{
    const key=input.dataset.dimension;
    if(!capabilityAvailable(key))return;
    state.configured=true;
    if(input.checked){
      state.dimensions=[...new Set([...state.dimensions,key])].sort((a,b)=>PRIORITY_KEYS.indexOf(a)-PRIORITY_KEYS.indexOf(b));
    }else{
      state.dimensions=state.dimensions.filter(item=>item!==key);
      if(!state.dimensions.length){
        state.dimensions=[key];
        input.checked=true;
        return;
      }
      if(OBJECTIVE_DIMENSION[state.objective]===key)state.objective='balanced';
    }
    state.weights=state.objective==='custom'
      ?normalizeWeights(state.weights,state.dimensions)
      :presetWeights(state.objective,state.dimensions);
    sync();
  });
  node.querySelectorAll('[data-depth]').forEach(button=>button.onclick=()=>{
    state.analysisDepth=button.dataset.depth;
    state.configured=true;
    sync();
  });
  node.querySelector('[data-outsourcing]').onchange=async event=>{
    state.allow=event.target.checked;
    state.configured=true;
    persist();
    try{
      await preflight();
      syncDimensionsToEvidence();
      sync();
    }catch(error){
      errorBox(node,error,loadConfig);
    }
  };
  node.querySelectorAll('[data-anomaly]').forEach(select=>select.onchange=()=>{
    state.decisions[select.dataset.anomaly]=select.value;
    sync();
  });

  const modal=node.querySelector('dialog');
  node.querySelector('[data-review]').onclick=()=>{
    const weights=decimalWeights();
    node.querySelector('[data-summary]').innerHTML=`<div class="dispatch-review-summary"><p><strong>Objetivo</strong><span>${esc(OBJECTIVE_LABELS[state.objective])}</span></p><p><strong>Variables</strong><span>${esc(activeDimensionText())}</span></p><p><strong>Prioridades</strong><span>${state.dimensions.map(key=>DIMENSION_LABELS[key]+' '+num(weights[key]*100,2)+' %').join(' · ')}</span></p><p><strong>Profundidad</strong><span>${esc(DEPTH_LABELS[state.analysisDepth])}</span></p><p><strong>Tercerización</strong><span>${state.allow?'Permitida':'Deshabilitada'}</span></p></div>`;
    modal.showModal();
  };
  node.querySelector('[data-execute]').onclick=()=>{
    modal.close();
    execute();
  };
  sync();
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
          {run_id:id,error:run.error_message||'La corrida no pudo completarse.'},
        );
        persist();
      }
      throw new Error(run.error_message||'La corrida no pudo completarse.');
    }
    const stage=run.progress_json?.stage||'validating';
    const assignmentNames={
      validating:'Validando Orders y Fleet',
      constructing:'Construyendo alternativas de carga',
      baseline:'Preparando referencia histórica',
      sensitivity:'Comparando objetivos',
      summarizing:'Preparando la asignación recomendada',
    };
    const schedulingNames={
      validating:'Validando Assignment y evidencia temporal',
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
        allow_third_party:state.allow,
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
          state.weights=normalizeWeights(
            Object.fromEntries(
              PRIORITY_KEYS.map(key=>[key,Math.round(+weights[key]*100)])
            ),
            state.dimensions,
          );
        }else{
          state.weights=presetWeights(state.objective,state.dimensions);
        }
        state.analysisDepth=['essential','comparative','deep'].includes(options.analysis_depth)
          ?options.analysis_depth
          :'comparative';
        state.allow=options.allow_third_party??true;
        state.decisions=options.anomaly_decisions||{};
        state.configured=true;
      }else{
        state.activeNode='logistics_assignment';
        state.dimensions=[...CORE_DIMENSIONS];
        state.objective='balanced';
        state.weights=balancedWeights(state.dimensions);
        state.analysisDepth='comparative';
        state.allow=options.allow_third_party??true;
        state.decisions={};
        state.configured=false;
      }

      try{
        const [o,f]=await Promise.all([
          api('/api/datasets/'+r.inputs.orders.dataset_id+'/profile'),
          api('/api/datasets/'+r.inputs.fleet.dataset_id+'/profile'),
        ]);
        state.orders=o.dataset;
        state.fleet=f.dataset;
        state.preflight=null;
        ensureDecisionCase();
        decisionContext(state.activeNode);
        persist();
        navigate('logistics-config');
      }catch(e){
        alert(e.message);
      }
    },
    {
      status:(
        nodeId
        &&caseMeta?.case_id
        &&state.decisionCase?.id===caseMeta.case_id
      )
        ?state.decisionCase.nodes?.[nodeId]?.status
        :null,
      decisionCase:state.decisionCase,
      activeNode:nodeId,
      onFlow:state.decisionCase?()=>navigate('logistics-map'):null,
      onOpenNode:state.decisionCase?openCaseResult:null,
      onApprove:(
        nodeId
        &&caseMeta?.case_id
        &&state.decisionCase?.id===caseMeta.case_id
      )
        ?async()=>{
          const approved=await post(
            '/api/runs/'+run.id+'/approve',
            {
              case_id:state.decisionCase.id,
              node_id:nodeId,
            },
          );
          const approvedAt=approved.result_json?.decision_case?.approved_at||new Date().toISOString();
          state.run=approved;
          state.decisionCase=transitionNode(
            state.decisionCase,
            nodeId,
            STATUS.APPROVED,
            {
              run_id:run.id,
              approved_at:approvedAt,
              error:null,
            },
          );
          unlockNextNode(nodeId);
          persist();
          return state.decisionCase;
        }
        :null,
      onApprovalComplete:(
        nodeId
        &&state.decisionCase
      )
        ?()=>{
          unlockNextNode(nodeId);
          persist();
        }
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
const query=new URLSearchParams(location.search);if(['assignment_v1','scheduling_v1','dispatch_v1','dispatch_v2'].includes(query.get('dda'))&&query.get('run_id')){const queryNode=query.get('dda')==='scheduling_v1'?'logistics_scheduling':'logistics_assignment';state.activeNode=queryNode;if(state.decisionCase?.nodes?.[queryNode]&&!state.decisionCase.nodes[queryNode].run_id){state.decisionCase=transitionNode(state.decisionCase,queryNode,STATUS.RUNNING,{run_id:query.get('run_id'),error:null});}decisionContext(queryNode);pending('Recuperando la corrida…');navigate('decision-dashboard');poll(query.get('run_id'),++pollGeneration,queryNode);}
if(state.activeNode)decisionContext(state.activeNode);
if(window.dationGetCurrentView?.()==='logistics-data')loadData();
if(window.dationGetCurrentView?.()==='logistics-map')loadDecisionMap();
