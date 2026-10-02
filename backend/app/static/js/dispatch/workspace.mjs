import {esc,num,date,vehicle,api,post,errorBox} from './shared.mjs';import {rebalance} from './selectors.mjs';import {render as dashboard} from './dashboard.mjs';
import {mountUploadScreen} from './upload/index.mjs';
const KEY='dation.dispatch.workspace.v3';
const PRIORITY_KEYS=['cost','time','utilization','co2'];
const DEFAULT_DIMENSIONS=[...PRIORITY_KEYS];
const DEFAULT_WEIGHTS={cost:25,time:25,utilization:25,co2:25};
const PRESETS={min_cost:{cost:100,time:0,utilization:0,co2:0},min_time:{cost:0,time:100,utilization:0,co2:0},max_utilization:{cost:0,time:0,utilization:100,co2:0},min_co2:{cost:0,time:0,utilization:0,co2:100}};
const OBJECTIVE_DIMENSION={min_cost:'cost',min_time:'time',max_utilization:'utilization',min_co2:'co2'};
const OBJECTIVE_LABELS={min_cost:'Costo mínimo',min_time:'Tiempo mínimo',max_utilization:'Máxima utilización propia',min_co2:'CO₂ mínimo',balanced:'Balanceado',custom:'Personalizado'};
const DIMENSION_LABELS={cost:'Costo operativo',time:'Tiempo de entrega',utilization:'Uso de flota propia',co2:'Emisiones CO₂'};
const DEPTH_LABELS={essential:'Esencial',comparative:'Comparativo',deep:'Profundo'};
function balancedWeights(dimensions){const out=Object.fromEntries(PRIORITY_KEYS.map(k=>[k,0]));const base=Math.floor(100/dimensions.length);let rest=100-base*dimensions.length;dimensions.forEach(k=>{out[k]=base+(rest>0?1:0);rest=Math.max(0,rest-1);});return out;}
function normalizeWeights(weights,dimensions){const out=Object.fromEntries(PRIORITY_KEYS.map(k=>[k,0]));const total=dimensions.reduce((s,k)=>s+(Number(weights?.[k])||0),0);if(total<=0)return balancedWeights(dimensions);const raw=dimensions.map((k,i)=>{const v=100*(Number(weights?.[k])||0)/total;return {k,i,base:Math.floor(v),fraction:v-Math.floor(v)};});let missing=100-raw.reduce((s,x)=>s+x.base,0);[...raw].sort((a,b)=>b.fraction-a.fraction||a.i-b.i).slice(0,missing).forEach(x=>x.base+=1);raw.forEach(x=>out[x.k]=x.base);return out;}
function presetWeights(objective,dimensions){if(objective==='balanced')return balancedWeights(dimensions);const out=Object.fromEntries(PRIORITY_KEYS.map(k=>[k,0]));const key=OBJECTIVE_DIMENSION[objective];if(key)out[key]=100;return out;}
let saved={};try{saved=JSON.parse(sessionStorage.getItem(KEY)||'{}');}catch{}
const restoredDimensions=Array.isArray(saved.dimensions)?DEFAULT_DIMENSIONS.filter(k=>saved.dimensions.includes(k)):DEFAULT_DIMENSIONS;
const state={orders:saved.orders||null,fleet:saved.fleet||null,dimensions:restoredDimensions.length?restoredDimensions:[...DEFAULT_DIMENSIONS],weights:saved.weights||{...DEFAULT_WEIGHTS},objective:['min_cost','min_time','max_utilization','min_co2','balanced','custom'].includes(saved.objective)?saved.objective:'balanced',analysisDepth:['essential','comparative','deep'].includes(saved.analysisDepth)?saved.analysisDepth:'comparative',allow:saved.allow??true,maxLateDays:Number.isFinite(+saved.maxLateDays)?Math.min(90,Math.max(0,+saved.maxLateDays)):30,decisions:saved.decisions||{},preflight:null,available:false,run:null};
if(!Array.isArray(state.dimensions)||!state.dimensions.length)state.dimensions=[...DEFAULT_DIMENSIONS];
state.dimensions=DEFAULT_DIMENSIONS.filter(k=>state.dimensions.includes(k));
if(OBJECTIVE_DIMENSION[state.objective]&&!state.dimensions.includes(OBJECTIVE_DIMENSION[state.objective]))state.objective='balanced';
state.weights=state.objective==='custom'?normalizeWeights(state.weights,state.dimensions):presetWeights(state.objective,state.dimensions);
let timer=null,pollGeneration=0;const roots={};
function persist(){try{sessionStorage.setItem(KEY,JSON.stringify({orders:state.orders,fleet:state.fleet,dimensions:state.dimensions,weights:state.weights,objective:state.objective,analysisDepth:state.analysisDepth,allow:state.allow,maxLateDays:state.maxLateDays,decisions:state.decisions}));}catch{}}
function root(view,id){const parent=document.querySelector('[data-view-panel="'+view+'"]');let node=document.getElementById(id);if(!node){node=document.createElement('div');node.id=id;node.className='dispatch';parent.append(node);}return node;}
function ready(){return !!(state.available&&state.orders&&state.fleet&&state.preflight?.valid);}
function navigate(view){window.dationSetDataReady(ready());window.dationNavigate(view);}
function urlRun(id,schema='dispatch_v2'){const url=new URL(location.href);url.searchParams.set('run_id',id);url.searchParams.set('dda',schema);history.replaceState(null,'',url);}
function action(b,fn){b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){alert(e.message);}finally{b.disabled=false;}};}
async function preflight(){state.preflight=null;window.dationSetDataReady(false);if(!state.orders||!state.fleet)return;state.preflight=await post('/api/runs/preflight',{orders_dataset_id:state.orders.id,fleet_dataset_id:state.fleet.id,allow_third_party:state.allow});window.dationSetDataReady(ready());persist();}
async function loadData() {
  await mountUploadScreen(
    roots.data,
    {
      state,
      persist,
      runPreflight: preflight,
      onNext: () => navigate('logistics-config'),
      isReady: ready,
    },
  );
}
function decimalWeights(){
  const weights=state.objective==='custom'?normalizeWeights(state.weights,state.dimensions):presetWeights(state.objective,state.dimensions);
  return Object.fromEntries(PRIORITY_KEYS.map(k=>[k,weights[k]/100]));
}
function configuration(){const config={mode:state.objective==='custom'?'custom':'preset',objective:state.objective,dimensions:[...state.dimensions]};if(state.objective==='custom')config.weights=decimalWeights();return config;}
function activeDimensionText(){return state.dimensions.map(k=>DIMENSION_LABELS[k]).join(' · ');}
function decisionSummary(){return `${OBJECTIVE_LABELS[state.objective]} · ${state.dimensions.length} dimensión${state.dimensions.length===1?'':'es'} · análisis ${DEPTH_LABELS[state.analysisDepth].toLowerCase()}`;}
async function loadConfig(){
  const node=roots.config;
  if(!state.orders||!state.fleet){
    node.innerHTML='<h1>Configurar la decisión</h1><p>Primero seleccioná órdenes y flota.</p><button data-back>Ir a cargar data</button>';
    node.querySelector('[data-back]').onclick=()=>navigate('logistics-data');
    return;
  }

  node.innerHTML='<div class="dispatch-config-heading"><span class="dispatch-kicker">Modelo de decisión</span><h1>Configurar la decisión</h1><p>Definí qué querés optimizar, qué dimensiones deben intervenir y cuánto análisis necesita esta decisión.</p><p role="status">Validando la evidencia seleccionada…</p></div>';
  try{await preflight();}catch(error){errorBox(node,error,loadConfig);return;}

  const objectives=[
    ['min_cost','Costo mínimo','Reduce el costo total después de proteger el SLA.'],
    ['min_time','Tiempo mínimo','Prioriza entregas más rápidas con el mejor nivel de servicio encontrado.'],
    ['max_utilization','Máxima utilización propia','Reduce la participación de kg tercerizados.'],
    ['min_co2','CO₂ mínimo','Reduce las emisiones estimadas del ciclo ida y vuelta.'],
    ['balanced','Balanceado','Equilibra todas las dimensiones activas.'],
  ];
  const dimensionCopy={
    cost:'Costo total de ida y vuelta más costo fijo por viaje.',
    time:'Tiempo desde disponibilidad hasta entrega.',
    utilization:'Participación del peso transportado con flota propia.',
    co2:'Emisiones estimadas según los factores cargados.',
  };
  const depths=[
    ['essential','Esencial','Decisión principal con el mínimo conjunto de escenarios necesario.'],
    ['comparative','Comparativo','Decisión + alternativas para entender trade-offs entre dimensiones activas.'],
    ['deep','Profundo','Comparación completa + sensibilidad y evidencia ampliada.'],
  ];

  node.innerHTML=`
    <div class="dispatch-config-screen">
      <header class="dispatch-config-heading">
        <span class="dispatch-kicker">Modelo de decisión</span>
        <h1>Configurar la decisión</h1>
        <p>Definí qué querés optimizar, qué dimensiones deben intervenir y cuánto análisis necesita esta decisión.</p>
      </header>

      <section class="dispatch-evidence-card">
        <div><span class="dispatch-config-eyebrow">Órdenes</span><strong>${esc(state.orders.original_filename)}</strong><small>${num(state.orders.row_count)} registros</small></div>
        <div><span class="dispatch-config-eyebrow">Flota</span><strong>${esc(state.fleet.label||state.fleet.original_filename)}</strong><small>${num(state.fleet.row_count)} registros</small></div>
        <button data-data>Cambiar datos</button>
      </section>

      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">01</span><div><h2>Objetivo de la decisión</h2><p>Elegí el criterio principal. El SLA permanece por encima del objetivo de negocio.</p></div></div>
        <div class="dispatch-objective-grid">${objectives.map(([key,label,copy])=>`<button class="dispatch-objective-card" data-preset="${key}" aria-pressed="${state.objective===key}"><strong>${label}</strong><small>${copy}</small></button>`).join('')}</div>
        <div class="dispatch-sla-guard"><span aria-hidden="true">✓</span><div><strong>Nivel de servicio protegido</strong><p>Dation busca primero la menor cantidad posible de incumplimientos y días de tardanza. Después optimiza tus prioridades de negocio.</p></div></div>
        <details class="dispatch-custom-priorities" ${state.objective==='custom'?'open':''}>
          <summary>Personalizar prioridades</summary>
          <p>Usá pesos sólo si necesitás una combinación distinta de los objetivos predefinidos.</p>
          <button type="button" data-customize>Activar configuración personalizada</button>
          <div class="dispatch-sliders">${PRIORITY_KEYS.map(key=>`<label class="dispatch-weight-row ${state.dimensions.includes(key)?'':'is-disabled'}"><span>${DIMENSION_LABELS[key]}</span><output data-weight="${key}">${state.weights[key]} %</output><input type="range" min="0" max="100" step="1" value="${state.weights[key]}" data-slider="${key}" ${state.dimensions.includes(key)?'':'disabled'}></label>`).join('')}</div>
        </details>
      </section>

      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">02</span><div><h2>Dimensiones del modelo</h2><p>Elegí qué variables de negocio deben intervenir en el balance, las comparaciones y la sensibilidad.</p></div></div>
        <div class="dispatch-dimensions">${PRIORITY_KEYS.map(key=>`<label class="dispatch-dimension-row"><div><strong>${DIMENSION_LABELS[key]}</strong><small>${dimensionCopy[key]}</small></div><input type="checkbox" data-dimension="${key}" ${state.dimensions.includes(key)?'checked':''}><span class="dispatch-toggle" aria-hidden="true"></span></label>`).join('')}</div>
        <div class="dispatch-locked-model"><div><span class="dispatch-config-eyebrow">Siempre activas</span><strong>Restricciones operativas esenciales</strong><p>Capacidad · ubicación · disponibilidad · ready date · distancia · ocupación temporal · SLA</p></div><span class="dispatch-lock">Modelo físico</span></div>
      </section>

      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">03</span><div><h2>Profundidad del análisis</h2><p>Elegí cuánto querés explorar antes de generar la Decisión recomendada.</p></div></div>
        <div class="dispatch-depth-grid">${depths.map(([key,label,copy])=>`<button class="dispatch-depth-card" data-depth="${key}" aria-pressed="${state.analysisDepth===key}"><span class="dispatch-depth-radio" aria-hidden="true"></span><strong>${label}${key==='comparative'?'<em>Recomendado</em>':''}</strong><small>${copy}</small></button>`).join('')}</div>
      </section>

      <section class="dispatch-panel dispatch-config-section">
        <div class="dispatch-config-section-head"><span class="dispatch-config-step">04</span><div><h2>Políticas operativas</h2><p>Definí qué políticas puede usar Dation al construir la distribución.</p></div></div>
        <label class="dispatch-policy-row"><div><strong>Permitir flota tercerizada</strong><small>Habilita recursos externos cuando mejoran la decisión dentro de las restricciones.</small></div><input type="checkbox" data-outsourcing ${state.allow?'checked':''}><span class="dispatch-toggle" aria-hidden="true"></span></label>
        <details class="dispatch-advanced-policy"><summary>Configuración avanzada</summary><label>Horizonte máximo de recuperación SLA <span><input type="number" min="0" max="90" step="1" value="${state.maxLateDays}" data-late-days> días</span><small>Hasta cuántos días posteriores al plazo puede explorar el motor para encontrar una distribución completa con excepciones.</small></label></details>
      </section>

      ${state.preflight.anomalies.length?`<section class="dispatch-panel dispatch-required-review"><div class="dispatch-config-section-head"><span class="dispatch-config-step">!</span><div><h2>Revisión requerida</h2><p>Sólo estas anomalías necesitan una acción explícita antes de ejecutar.</p></div></div>${state.preflight.anomalies.map(a=>`<label class="dispatch-review-row"><span><strong>${esc(a.order_id)}</strong><small>${esc(a.detail)}</small></span><select data-anomaly="${esc(a.order_id)}"><option value="">Elegí una acción…</option><option value="include" ${state.decisions[a.order_id]==='include'?'selected':''}>Incluir</option><option value="exclude" ${state.decisions[a.order_id]==='exclude'?'selected':''}>Excluir</option></select></label>`).join('')}</section>`:''}

      <footer class="dispatch-footer dispatch-config-footer"><div><span class="dispatch-config-eyebrow">Configuración lista</span><strong data-config-summary></strong><small data-config-detail></small></div><button data-review>Revisar y ejecutar →</button></footer>

      <dialog class="dispatch dispatch-review"><form method="dialog"><span class="dispatch-config-eyebrow">Antes de ejecutar</span><h2>Revisar la decisión</h2><div data-summary></div><p>Motor Dispatch 2.1.0 · SLA jerárquico + capacidad espacial y temporal. La configuración y los archivos quedan vinculados a la corrida.</p><div class="dispatch-actions"><button value="cancel">Volver</button><button type="button" data-execute>Generar decisión</button></div></form></dialog>
    </div>`;

  function sync(){
    state.weights=state.objective==='custom'?normalizeWeights(state.weights,state.dimensions):presetWeights(state.objective,state.dimensions);
    node.querySelectorAll('[data-preset]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.preset===state.objective)));
    node.querySelectorAll('[data-depth]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.depth===state.analysisDepth)));
    node.querySelectorAll('[data-dimension]').forEach(input=>{input.checked=state.dimensions.includes(input.dataset.dimension);input.disabled=state.dimensions.length===1&&input.checked;});
    PRIORITY_KEYS.forEach(key=>{const output=node.querySelector('[data-weight="'+key+'"]');const slider=node.querySelector('[data-slider="'+key+'"]');if(output)output.textContent=state.weights[key]+' %';if(slider){slider.value=state.weights[key];slider.disabled=!state.dimensions.includes(key);slider.closest('.dispatch-weight-row')?.classList.toggle('is-disabled',slider.disabled);}});
    node.querySelector('[data-config-summary]').textContent=decisionSummary();
    node.querySelector('[data-config-detail]').textContent=activeDimensionText()+' · SLA protegido';
    node.querySelector('[data-review]').disabled=!ready()||state.preflight.anomalies.some(a=>!state.decisions[a.order_id]);
    persist();
  }

  node.querySelector('[data-data]').onclick=()=>navigate('logistics-data');
  node.querySelectorAll('[data-preset]').forEach(button=>button.onclick=()=>{const next=button.dataset.preset;const required=OBJECTIVE_DIMENSION[next];if(required&&!state.dimensions.includes(required))state.dimensions=[...new Set([...state.dimensions,required])].sort((a,b)=>PRIORITY_KEYS.indexOf(a)-PRIORITY_KEYS.indexOf(b));state.objective=next;state.weights=presetWeights(next,state.dimensions);sync();});
  node.querySelector('[data-customize]').onclick=()=>{state.objective='custom';state.weights=balancedWeights(state.dimensions);node.querySelector('.dispatch-custom-priorities').open=true;sync();};
  node.querySelectorAll('[data-slider]').forEach(slider=>slider.oninput=()=>{state.objective='custom';const key=slider.dataset.slider;const others=state.dimensions.filter(item=>item!==key);const target=others.length?+slider.value:100;const next={...state.weights,[key]:target};const remaining=100-target;if(others.length){const total=others.reduce((sum,item)=>sum+(state.weights[item]||0),0);const raw=others.map((item,index)=>{const share=total?remaining*(state.weights[item]||0)/total:remaining/others.length;return {item,index,base:Math.floor(share),fraction:share-Math.floor(share)};});let missing=remaining-raw.reduce((sum,item)=>sum+item.base,0);[...raw].sort((a,b)=>b.fraction-a.fraction||a.index-b.index).slice(0,missing).forEach(item=>item.base+=1);raw.forEach(item=>next[item.item]=item.base);}PRIORITY_KEYS.filter(item=>!state.dimensions.includes(item)).forEach(item=>next[item]=0);state.weights=next;sync();});
  node.querySelectorAll('[data-dimension]').forEach(input=>input.onchange=()=>{const key=input.dataset.dimension;if(input.checked){state.dimensions=[...new Set([...state.dimensions,key])].sort((a,b)=>PRIORITY_KEYS.indexOf(a)-PRIORITY_KEYS.indexOf(b));}else{state.dimensions=state.dimensions.filter(item=>item!==key);if(!state.dimensions.length){state.dimensions=[key];input.checked=true;return;}if(OBJECTIVE_DIMENSION[state.objective]===key)state.objective='balanced';}state.weights=state.objective==='custom'?normalizeWeights(state.weights,state.dimensions):presetWeights(state.objective,state.dimensions);sync();});
  node.querySelectorAll('[data-depth]').forEach(button=>button.onclick=()=>{state.analysisDepth=button.dataset.depth;sync();});
  node.querySelector('[data-outsourcing]').onchange=async event=>{state.allow=event.target.checked;persist();await preflight();sync();};
  node.querySelector('[data-late-days]').onchange=event=>{state.maxLateDays=Math.min(90,Math.max(0,Number(event.target.value)||0));event.target.value=state.maxLateDays;sync();};
  node.querySelectorAll('[data-anomaly]').forEach(select=>select.onchange=()=>{state.decisions[select.dataset.anomaly]=select.value;sync();});

  const modal=node.querySelector('dialog');
  node.querySelector('[data-review]').onclick=()=>{
    const weights=decimalWeights();
    node.querySelector('[data-summary]').innerHTML=`<div class="dispatch-review-summary"><p><strong>Objetivo</strong><span>${esc(OBJECTIVE_LABELS[state.objective])}</span></p><p><strong>Dimensiones</strong><span>${esc(activeDimensionText())}</span></p><p><strong>Prioridades</strong><span>${state.dimensions.map(key=>DIMENSION_LABELS[key]+' '+num(weights[key]*100,2)+' %').join(' · ')}</span></p><p><strong>Profundidad</strong><span>${esc(DEPTH_LABELS[state.analysisDepth])}</span></p><p><strong>Tercerización</strong><span>${state.allow?'Permitida':'Deshabilitada'}</span></p><p><strong>Recuperación SLA</strong><span>Hasta ${num(state.maxLateDays)} días</span></p></div><div class="dispatch-sla-guard"><span aria-hidden="true">✓</span><div><strong>SLA protegido antes del objetivo de negocio</strong><p>Dation aplicará siempre capacidad, ubicación, disponibilidad, fechas, distancia y ocupación temporal.</p></div></div>`;
    modal.showModal();
  };
  node.querySelector('[data-execute]').onclick=()=>{modal.close();execute();};
  sync();
}
function pending(message){document.body.classList.add('dispatch-result');roots.dashboard.innerHTML=`<section class="dispatch-panel"><h1>Preparando tu decisión</h1><p role="status">${esc(message)}</p><div class="dispatch-loading" aria-label="Procesando"></div><p>Se muestran etapas reales, sin porcentajes estimados.</p><button data-return>Volver a configuración</button></section>`;roots.dashboard.querySelector('[data-return]').onclick=()=>navigate('logistics-config');}
async function poll(id,generation){if(generation!==pollGeneration)return;try{const run=await api('/api/runs/'+id);if(generation!==pollGeneration)return;if(run.status==='completed'){show(run);return;}if(run.status==='error')throw new Error(run.error_message||'La corrida no pudo completarse.');const stage=run.progress_json?.stage||'validating',names={validating:'Validando órdenes y flota',baseline:'Construyendo referencia directa',sensitivity:'Comparando objetivos de negocio',summarizing:'Preparando la decisión recomendada'};pending(stage.startsWith('optimizing:')?'Protegiendo SLA y evaluando alternativas':(names[stage]||'Evaluando alternativas de asignación'));}catch(e){if(e.status!==404){errorBox(roots.dashboard,e,()=>poll(id,generation));return;}}timer=setTimeout(()=>poll(id,generation),1500);}
async function execute(){const id=crypto.randomUUID();urlRun(id);pending('Registrando la corrida…');navigate('decision-dashboard');const generation=++pollGeneration;clearTimeout(timer);timer=setTimeout(()=>poll(id,generation),1000);try{const run=await post('/api/runs?run_id='+id,{orders_dataset_id:state.orders.id,fleet_dataset_id:state.fleet.id,configuration:configuration(),options:{allow_third_party:state.allow,max_late_days:state.maxLateDays,analysis_depth:state.analysisDepth,anomaly_decisions:Object.fromEntries(Object.entries(state.decisions).filter(([,v])=>v))}});if(generation===pollGeneration)show(run);}catch(e){if(generation!==pollGeneration)return;clearTimeout(timer);errorBox(roots.dashboard,e,()=>poll(id,generation));}}
export function show(run){clearTimeout(timer);pollGeneration++;state.run=run;const r=run.result_json;document.body.classList.add('dispatch-result');urlRun(run.id,r?.schema_version||'dispatch_v2');window.dationSetDashboardReady(true);dashboard(roots.dashboard,run,async()=>{const config=r.configuration||{},w=config.weights||{};const dims=Array.isArray(config.dimensions)?DEFAULT_DIMENSIONS.filter(k=>config.dimensions.includes(k)):DEFAULT_DIMENSIONS;state.dimensions=dims.length?dims:[...DEFAULT_DIMENSIONS];state.objective=['min_cost','min_time','max_utilization','min_co2','balanced','custom'].includes(config.objective)?config.objective:'balanced';if(PRIORITY_KEYS.every(k=>Number.isFinite(+w[k]))){state.weights=normalizeWeights(Object.fromEntries(PRIORITY_KEYS.map(k=>[k,Math.round(+w[k]*100)])),state.dimensions);}else{state.weights=presetWeights(state.objective,state.dimensions);}state.analysisDepth=['essential','comparative','deep'].includes(config.options?.analysis_depth)?config.options.analysis_depth:(config.options?.sensitivity?'deep':'comparative');state.allow=config.options?.allow_third_party??true;state.maxLateDays=config.options?.max_late_days??30;state.decisions=config.options?.anomaly_decisions||{};try{const [o,f]=await Promise.all([api('/api/datasets/'+r.inputs.orders.dataset_id+'/profile'),api('/api/datasets/'+r.inputs.fleet.dataset_id+'/profile')]);state.orders=o.dataset;state.fleet=f.dataset;persist();navigate('logistics-config');}catch(e){alert(e.message);}});navigate('decision-dashboard');}
for(const [key,view]of [['data','logistics-data'],['config','logistics-config'],['dashboard','decision-dashboard']])roots[key]=root(view,'dispatch-'+key+'-root');
window.DationDispatch={show,isReady:ready};document.body.classList.add('dispatch-enabled');
window.addEventListener('dation:view',e=>{const view=e.detail.view;if(view==='logistics-data'){roots.data.hidden=false;document.body.classList.add('dispatch-enabled');loadData();}if(view==='logistics-config'&&document.body.classList.contains('dispatch-enabled')){roots.config.hidden=false;loadConfig();}});
const query=new URLSearchParams(location.search);if(['dispatch_v1','dispatch_v2'].includes(query.get('dda'))&&query.get('run_id')){pending('Recuperando la corrida…');navigate('decision-dashboard');poll(query.get('run_id'),++pollGeneration);}
if(window.dationGetCurrentView?.()==='logistics-data')loadData();
