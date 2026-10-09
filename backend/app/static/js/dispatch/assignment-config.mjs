import {esc,num,post,api} from "./shared.mjs";
import {iconSvg} from "./decision-ui.mjs?v=assignment-config-v2";
import {
  configSummaryBar,
  decisionCaseCard,
  decisionChoiceCard,
  decisionDataFileCard,
  decisionDepthCard,
  decisionHero,
  decisionSectionHeader,
} from "./decision-config-ui.mjs?v=decision-config-foundation";

const STYLE_ID="assignment-config-v2-styles";
const CASE_STYLE_ID="assignment-config-case-styles";
const STYLE_HREF="/static/css/assignment-config-v2.css?v=assignment-config-v2";
const CASE_STYLE_HREF="/static/css/decision-map-case-v2.css?v=assignment-config-v2";
const PRIORITY_KEYS=["trips","cost","own_fleet","co2"];
const OBJECTIVES=[
  ["min_trips","Menor cantidad de viajes","Consolida la carga para reducir los viajes totales.","route","trips"],
  ["min_cost","Costo mínimo","Minimiza el costo estimado de los viajes.","dollarSign","cost"],
  ["max_own_fleet","Mayor uso de flota propia","Prioriza tus vehículos antes que los transportistas externos.","truck","own_fleet"],
  ["min_co2","CO₂ mínimo","Reduce las emisiones estimadas de los viajes.","leaf","co2"],
  ["balanced","Balanceado","Equilibra las variables activas con el mismo peso.","scale",null],
  ["custom","Personalizado","Definí vos cuánto pesa cada variable.","slidersHorizontal",null],
];
const DIMENSION_COPY={
  trips:"Viajes necesarios para transportar toda la demanda.",
  cost:"Costo estimado por distancia recorrida y costo fijo de cada viaje.",
  own_fleet:"Porción de la carga asignada a vehículos propios frente a terceros.",
  co2:"Emisiones estimadas de ida y vuelta según el factor informado.",
};
const DIMENSION_LABELS={
  trips:"Cantidad de viajes",
  cost:"Costo operativo",
  own_fleet:"Uso de flota propia",
  co2:"Emisiones CO₂",
};
const OBJECTIVE_LABELS=Object.fromEntries(OBJECTIVES.map(([key,label])=>[key,label]));
const RESOURCE_MODES={
  own:{label:"Solo propia",icon:"truck",copy:"Usa únicamente tus vehículos."},
  mixed:{label:"Mixta",icon:"shuffle",copy:"Usa tus vehículos y suma terceros cuando el objetivo lo justifica."},
  outsourced:{label:"Solo tercerizada",icon:"handshake",copy:"Asigna toda la carga a transportistas externos."},
};
const DEPTHS={
  essential:{
    label:"Esencial",
    copy:"Ves la asignación resultante: qué órdenes van en cada viaje y vehículo.",
    rows:[["Asignación",true],["Comparación con alternativas",false],["Evidencia ampliada",false]],
  },
  comparative:{
    label:"Comparativo",
    copy:"Además, comparás la asignación contra alternativas como costo mínimo o menos viajes.",
    rows:[["Asignación",true],["Comparación con alternativas",true],["Evidencia ampliada",false]],
  },
  deep:{
    label:"Profundo",
    copy:"Evidencia ampliada de todas las alternativas evaluadas.",
    rows:[["Asignación",false],["Comparación con alternativas",false],["Evidencia ampliada",false]],
  },
};

function ensureStyles(){
  if(!document.getElementById(CASE_STYLE_ID)){
    const link=document.createElement("link");
    link.id=CASE_STYLE_ID;
    link.rel="stylesheet";
    link.href=CASE_STYLE_HREF;
    document.head.append(link);
  }
  if(!document.getElementById(STYLE_ID)){
    const link=document.createElement("link");
    link.id=STYLE_ID;
    link.rel="stylesheet";
    link.href=STYLE_HREF;
    document.head.append(link);
  }
}

function workflowStep(id,fallback){
  const steps=(window.DationDdaFlow&&Array.isArray(window.DationDdaFlow.steps))
    ?window.DationDdaFlow.steps
    :[];
  return steps.find(step=>step.id===id)||fallback;
}

function variableStatus(key){
  return window.DationDecisionVariables?.[key]?.status||"active";
}

function productVariableAvailable(key){
  return variableStatus(key)==="active";
}

function filterPayload(filters){
  return (filters||[]).map(filter=>({
    column:filter.column,
    type:filter.type,
    operator:filter.type==="category"?"in":"between",
    value:Array.isArray(filter.value)?filter.value:[],
    resolved:Array.isArray(filter.resolved)?filter.resolved:null,
  }));
}

function activeDimensions(capabilities){
  return PRIORITY_KEYS.filter(key=>(
    Boolean(capabilities?.[key]?.available)
    &&productVariableAvailable(key)
  ));
}

function normalizeRawWeights(raw,dimensions){
  const out=Object.fromEntries(PRIORITY_KEYS.map(key=>[key,0]));
  const total=dimensions.reduce((sum,key)=>sum+(Number(raw?.[key])||0),0);
  if(total<=0)return out;
  const parts=dimensions.map((key,index)=>{
    const exact=100*(Number(raw?.[key])||0)/total;
    return {key,index,base:Math.floor(exact),fraction:exact-Math.floor(exact)};
  });
  let missing=100-parts.reduce((sum,item)=>sum+item.base,0);
  [...parts]
    .sort((a,b)=>b.fraction-a.fraction||a.index-b.index)
    .slice(0,missing)
    .forEach(item=>item.base+=1);
  parts.forEach(item=>out[item.key]=item.base);
  return out;
}

function equalRaw(dimensions){
  return Object.fromEntries(PRIORITY_KEYS.map(key=>[
    key,
    dimensions.includes(key)?50:0,
  ]));
}

function presetRaw(objective,dimensions){
  if(objective==="balanced")return equalRaw(dimensions);
  const target={
    min_trips:"trips",
    min_cost:"cost",
    max_own_fleet:"own_fleet",
    min_co2:"co2",
  }[objective];
  return Object.fromEntries(PRIORITY_KEYS.map(key=>[key,key===target?100:0]));
}

function heroMarkup(){
  const step=workflowStep("config",{number:3,label:"Configurar decisión"});
  return decisionHero({
    step,
    decisionIndex:1,
    totalDecisions:3,
    title:"Definí cómo querés distribuir tu carga.",
    description:"Elegí qué datos analizar, qué querés optimizar y cuánto detalle ver en el dashboard. Esta decisión reparte la carga entre tu flota; las fechas se definen después.",
    panelItems:[
      {label:"1 · PREGUNTA",description:"¿Cómo conviene armar los viajes y repartir la carga?",icon:"messageCircleQuestion"},
      {label:"2 · ENTREGA",description:"Viajes propuestos + distribución de carga.",icon:"packageCheck"},
      {label:"3 · QUEDA PARA DESPUÉS",description:"Fechas y calendario: se definen en Planificación de despachos.",icon:"calendarClock"},
    ],
  });
}

function datasetFile(kind,dataset,preview,hasFilters){
  const orders=kind==="orders";
  const total=orders
    ?Number(preview?.orders?.total??dataset?.row_count??0)
    :Number(preview?.fleet?.total??dataset?.row_count??0);
  const included=orders
    ?Number(preview?.orders?.included??total)
    :Number(preview?.fleet?.included??total);
  const count=orders
    ?(
      hasFilters&&included!==total
        ?num(included)+' de '+num(total)+' órdenes'
        :num(total)+' '+(total===1?'orden':'órdenes')
    )
    :num(total)+' '+(total===1?'vehículo':'vehículos');
  return decisionDataFileCard({
    kind,
    dataset,
    countText:count,
    filtered:orders&&hasFilters,
  });
}

function caseStrip(state,preview){
  const hasFilters=Boolean(state.scopeFilters?.length);
  return decisionCaseCard({
    caseId:state.decisionCase?.id,
    files:[
      datasetFile("orders",state.orders,preview,hasFilters),
      datasetFile("fleet",state.fleet,preview,hasFilters),
    ],
  });
}

function scopeSummary(preview,filters){
  const included=Number(preview?.orders?.included??0);
  const total=Number(preview?.orders?.total??0);
  if(!filters.length)return "Todos los datos";
  return num(included)+' de '+num(total)+' órdenes';
}

function resolvedDateRange(field,preset,customValue){
  const latest=field?.max?new Date(field.max+'T12:00:00'):null;
  if(!latest||Number.isNaN(latest.getTime()))return customValue||[];
  let days=null;
  if(preset==="last7")days=7;
  if(preset==="last14")days=14;
  if(preset==="last30")days=30;
  if(days===null)return customValue||[field.min,field.max];
  const start=new Date(latest);
  start.setDate(start.getDate()-(days-1));
  return [start.toISOString().slice(0,10),latest.toISOString().slice(0,10)];
}

function filterControl(filter,field,index){
  if(!field){
    return '<div class="assignment-filter-row is-invalid" data-filter-index="'+index+'">'
      +'<div><strong>'+esc(filter.column)+'</strong><span>Esta columna ya no existe en el archivo actual.</span></div>'
      +'<button type="button" data-filter-remove="'+index+'" aria-label="Quitar filtro">×</button>'
    +'</div>';
  }
  const header='<div class="assignment-filter-row__head"><div><strong>'+esc(field.label)+'</strong><small>'+esc(field.type==="date"?'Fecha':field.type==="category"?'Categoría':'Numérica')+'</small></div><button type="button" data-filter-remove="'+index+'" aria-label="Quitar filtro '+esc(field.label)+'">×</button></div>';
  if(field.type==="category"){
    const selected=new Set((filter.value||[]).map(String));
    return '<div class="assignment-filter-row" data-filter-index="'+index+'">'+header
      +'<input class="assignment-filter-search" type="search" placeholder="Buscar valores…" data-filter-search="'+index+'" aria-label="Buscar valores de '+esc(field.label)+'">'
      +'<div class="assignment-filter-options" data-filter-options="'+index+'">'
        +(field.values||[]).map(item=>(
          '<label data-filter-option-label="'+esc(String(item.value).toLowerCase())+'">'
            +'<input type="checkbox" data-filter-category="'+index+'" value="'+esc(item.value)+'" '+(selected.has(String(item.value))?'checked':'')+'>'
            +'<span>'+esc(item.value)+'</span><small>'+num(item.count)+'</small>'
          +'</label>'
        )).join("")
      +'</div>'
      +'<div class="assignment-filter-inline-actions"><button type="button" data-filter-all="'+index+'">Seleccionar todo</button><button type="button" data-filter-none="'+index+'">Limpiar</button></div>'
    +'</div>';
  }
  if(field.type==="number"){
    const values=filter.value?.length===2?filter.value:[field.min,field.max];
    return '<div class="assignment-filter-row" data-filter-index="'+index+'">'+header
      +'<div class="assignment-filter-range">'
        +'<label><span>Mínimo</span><input type="number" step="any" data-filter-number-min="'+index+'" value="'+esc(values[0])+'" min="'+esc(field.min)+'" max="'+esc(field.max)+'"></label>'
        +'<label><span>Máximo</span><input type="number" step="any" data-filter-number-max="'+index+'" value="'+esc(values[1])+'" min="'+esc(field.min)+'" max="'+esc(field.max)+'"></label>'
      +'</div><small class="assignment-filter-reference">Rango disponible: '+esc(field.min)+' – '+esc(field.max)+'</small>'
    +'</div>';
  }
  const preset=filter.preset||"custom";
  const resolved=filter.resolved?.length===2?filter.resolved:resolvedDateRange(field,preset,filter.value);
  return '<div class="assignment-filter-row" data-filter-index="'+index+'">'+header
    +'<div class="assignment-filter-date">'
      +'<label><span>Período</span><select data-filter-date-preset="'+index+'">'
        +'<option value="last7" '+(preset==="last7"?'selected':'')+'>Últimos 7 días</option>'
        +'<option value="last14" '+(preset==="last14"?'selected':'')+'>Últimas 2 semanas</option>'
        +'<option value="last30" '+(preset==="last30"?'selected':'')+'>Último mes</option>'
        +'<option value="custom" '+(preset==="custom"?'selected':'')+'>Rango personalizado</option>'
      +'</select></label>'
      +'<label><span>Desde</span><input type="date" data-filter-date-from="'+index+'" value="'+esc(resolved[0]||field.min)+'" '+(preset!=="custom"?'readonly':'')+'></label>'
      +'<label><span>Hasta</span><input type="date" data-filter-date-to="'+index+'" value="'+esc(resolved[1]||field.max)+'" '+(preset!=="custom"?'readonly':'')+'></label>'
    +'</div>'
    +'<small class="assignment-filter-reference">El período se resuelve contra la fecha más reciente del archivo: '+esc(field.max||"—")+'.</small>'
  +'</div>';
}

function scopeSection(state,preview){
  const filters=state.scopeFilters||[];
  const fields=preview?.fields||[];
  const fieldMap=Object.fromEntries(fields.map(field=>[field.column,field]));
  const ordersIncluded=Number(preview?.orders?.included??state.orders?.row_count??0);
  const ordersTotal=Number(preview?.orders?.total??state.orders?.row_count??0);
  const fleetIncluded=Number(preview?.resources?.included??preview?.fleet?.included??state.fleet?.row_count??0);
  const fleetTotal=Number(preview?.resources?.total??preview?.fleet?.total??state.fleet?.row_count??0);
  const quick=fields.filter(field=>field.quick);
  const error=ordersIncluded===0
    ?'<div class="assignment-config-alert is-error" role="alert">'+iconSvg("alertTriangle","assignment-icon")+'<span>Los filtros no dejan ninguna orden. Ampliá el alcance.</span></div>'
    :"";
  return '<section class="assignment-section" id="config-scope" data-config-section="scope">'
    +decisionSectionHeader({number:"01",eyebrow:"ALCANCE",title:"Alcance de los datos",copy:"Elegí qué parte de tus datos querés analizar. Tus archivos no se modifican.",icon:"filter",current:scopeSummary(preview,filters)})
    +'<div class="assignment-scope-counters" aria-live="polite">'
      +'<div><span>Órdenes en el análisis</span><strong>'+num(ordersIncluded)+' de '+num(ordersTotal)+'</strong><progress max="'+Math.max(ordersTotal,1)+'" value="'+ordersIncluded+'"></progress></div>'
      +'<div><span>Flota habilitada</span><strong>'+num(fleetIncluded)+' de '+num(fleetTotal)+' vehículos</strong><progress max="'+Math.max(fleetTotal,1)+'" value="'+fleetIncluded+'"></progress></div>'
    +'</div>'
    +(filters.length
      ?'<div class="assignment-filter-list">'+filters.map((filter,index)=>filterControl(filter,fieldMap[filter.column],index)).join("")+'</div>'
      :'<div class="assignment-scope-empty">'+iconSvg("filter","assignment-icon")+'<div><strong>Sin filtros: se analizan todos tus datos.</strong><span>Por ejemplo: solo un destino, o las últimas 2 semanas.</span></div></div>')
    +error
    +'<div class="assignment-scope-actions">'
      +'<button type="button" class="assignment-add-filter" data-filter-dialog-open>'+iconSvg("plus","assignment-icon")+'Agregar filtro</button>'
      +(filters.length?'<button type="button" class="assignment-link-action" data-filter-clear>Limpiar filtros</button>':'')
    +'</div>'
    +(quick.length?'<div class="assignment-quick-filters"><span>Filtros rápidos</span>'+quick.map(field=>'<button type="button" data-filter-quick="'+esc(field.column)+'">'+esc(field.label)+'</button>').join("")+'</div>':'')
  +'</section>';
}

function objectiveEnabled(key,required,capabilities,state){
  if(key==="min_co2"&&!productVariableAvailable("co2"))return false;
  if(required&&!capabilities?.[required]?.available)return false;
  if(key==="max_own_fleet"&&state.resourceMode==="outsourced")return false;
  return true;
}

function objectiveSection(state,capabilities){
  const dims=activeDimensions(capabilities);
  const effective=normalizeRawWeights(state.customWeights||state.weights,dims);
  const customInvalid=state.objective==="custom"&&dims.every(key=>(Number(state.customWeights?.[key])||0)<=0);
  return '<section class="assignment-section" id="config-objective" data-config-section="objective">'
    +decisionSectionHeader({number:"02",eyebrow:"OBJETIVO",title:"Objetivo de la decisión",copy:"Elegí el criterio principal para construir los viajes y distribuir la carga.",icon:"target",current:OBJECTIVE_LABELS[state.objective]||"Balanceado"})
    +'<div class="assignment-objective-grid">'
      +OBJECTIVES.map(([key,label,copy,icon,required])=>{
        const enabled=objectiveEnabled(key,required,capabilities,state);
        const consolidating=key==="min_co2"&&!productVariableAvailable("co2");
        const selected=state.objective===key;
        const tags=[];
        if(key==="custom")tags.push("Avanzado");
        if(consolidating)tags.push("En consolidación");
        if(!enabled&&!consolidating)tags.push("Faltan datos suficientes");
        return decisionChoiceCard({
          className:'assignment-objective-card '+(key==="custom"?'is-custom':''),
          icon,
          title:label,
          copy,
          selected,
          disabled:!enabled,
          tags,
          attributes:{"data-objective":key},
        });
      }).join("")
    +'</div>'
    +(state.resourceMode==="own"&&state.objective==="max_own_fleet"
      ?'<div class="assignment-config-alert is-info">'+iconSvg("checkCircle","assignment-icon")+'<span>Con Solo propia, este objetivo no cambia la selección de recursos porque todos los vehículos habilitados ya son propios.</span></div>'
      :"")
    +(state.objective==="custom"
      ?'<div class="assignment-custom-panel '+(customInvalid?'has-error':'')+'">'
        +'<div class="assignment-custom-panel__head"><div><span>Pesos de prioridad</span><strong>Definí cuánto importa cada variable.</strong><small>Los porcentajes efectivos se normalizan automáticamente para sumar 100%.</small></div>'
          +'<label>Partir de<select data-custom-base><option value="balanced">Balanceado</option><option value="min_trips">Menor cantidad de viajes</option><option value="min_cost">Costo mínimo</option><option value="max_own_fleet">Mayor uso de flota propia</option></select></label></div>'
        +'<div class="assignment-weight-distribution" aria-label="Distribución efectiva de prioridades">'
          +dims.map(key=>'<span class="is-'+key+'" style="--weight:'+effective[key]+'%" title="'+esc(DIMENSION_LABELS[key]+' '+effective[key]+' %')+'"></span>').join("")
        +'</div>'
        +'<div class="assignment-weight-list">'
          +PRIORITY_KEYS.map(key=>{
            const available=dims.includes(key);
            const consolidating=variableStatus(key)==="consolidating";
            const raw=Number(state.customWeights?.[key]??state.weights?.[key]??0);
            return '<label class="assignment-weight-row '+(available?'':'is-disabled')+'">'
              +'<span class="assignment-weight-row__icon">'+iconSvg(key==="trips"?"route":key==="cost"?"dollarSign":key==="own_fleet"?"truck":"leaf","assignment-icon")+'</span>'
              +'<span class="assignment-weight-row__copy"><strong>'+esc(DIMENSION_LABELS[key])+'</strong><small>'+esc(DIMENSION_COPY[key])+'</small>'+(consolidating?'<em>En consolidación</em>':(!available?'<em>Sin datos suficientes</em>':'') )+'</span>'
              +'<input type="range" min="0" max="100" step="1" value="'+raw+'" data-custom-weight="'+key+'" '+(available?'':'disabled')+' aria-valuetext="'+esc(DIMENSION_LABELS[key]+', '+raw+' de 100, equivale al '+effective[key]+' %')+'">'
              +'<output data-effective-weight="'+key+'">'+effective[key]+' %</output>'
            +'</label>';
          }).join("")
        +'</div>'
        +(customInvalid?'<div class="assignment-config-alert is-error" role="alert">'+iconSvg("alertTriangle","assignment-icon")+'<span>Asigná peso a por lo menos una variable.</span></div>':'')
        +'<div class="assignment-custom-actions"><button type="button" data-custom-equal>Igualar pesos</button><button type="button" data-custom-reset>Restablecer</button></div>'
      +'</div>'
      :"")
  +'</section>';
}

function resourceSection(state,preview){
  const own=Number(preview?.resources?.own??state.fleet?.profile_json?.profile?.own_vehicles??0);
  const third=Number(preview?.resources?.third_party??state.fleet?.profile_json?.profile?.third_party_vehicles??0);
  const labels={own:num(own)+' propios',mixed:num(own)+' propios + '+num(third)+' tercerizados',outsourced:num(third)+' tercerizados'};
  return '<section class="assignment-section" id="config-resources" data-config-section="resources">'
    +decisionSectionHeader({number:"03",eyebrow:"RECURSOS",title:"Política de recursos",copy:"Definí qué flota puede participar en esta asignación.",icon:"truck",current:RESOURCE_MODES[state.resourceMode]?.label||"Mixta"})
    +'<div class="assignment-resource-grid">'
      +Object.entries(RESOURCE_MODES).map(([key,item])=>{
        const enabled=(key!=="own"||own>0)&&(key==="own"||third>0)&&(key!=="mixed"||(own>0&&third>0));
        const reason=!enabled
          ?(key==="own"?"Tu flota no incluye vehículos propios":"Tu flota no incluye vehículos tercerizados")
          :"";
        return decisionChoiceCard({
          className:"assignment-resource-card",
          icon:item.icon,
          title:item.label,
          copy:item.copy,
          selected:state.resourceMode===key,
          disabled:!enabled,
          disabledTitle:reason,
          tags:[labels[key]],
          attributes:{"data-resource-mode":key},
        });
      }).join("")
    +'</div>'
    +'<div class="assignment-resource-rule"><span>REGLA 01</span><strong>Modo de flota</strong><small>Este contenedor queda preparado para sumar nuevas reglas de recursos sin cambiar el esqueleto.</small></div>'
  +'</section>';
}

function depthSection(state){
  if(state.analysisDepth==="deep")state.analysisDepth="comparative";
  return '<section class="assignment-section" id="config-depth" data-config-section="depth">'
    +decisionSectionHeader({number:"04",eyebrow:"DASHBOARD",title:"Profundidad del análisis",copy:"No cambia la asignación: define cuánto contexto vas a ver en el dashboard.",icon:"layoutDashboard",current:DEPTHS[state.analysisDepth]?.label||"Comparativo"})
    +'<div class="assignment-depth-grid">'
      +Object.entries(DEPTHS).map(([key,item])=>{
        const disabled=key==="deep";
        const selected=state.analysisDepth===key;
        const tag=key==="comparative"?"Recomendado":disabled?"Próximamente":"";
        return decisionDepthCard({
          key,
          item,
          selected,
          disabled,
          tag,
          disabledTitle:disabled?"Se habilita en futuras versiones":"",
        });
      }).join("")
    +'</div>'
  +'</section>';
}

function blocker(state,preview,capabilities){
  if(Number(preview?.orders?.included??0)<=0)return {section:"config-scope",reason:"Los filtros no dejan órdenes para analizar."};
  if(preview&&preview.valid===false&&preview.errors?.length)return {section:"config-scope",reason:preview.errors[0].detail||"Revisá el alcance de los datos."};
  const dims=activeDimensions(capabilities);
  if(state.objective==="custom"&&dims.every(key=>(Number(state.customWeights?.[key])||0)<=0))return {section:"config-objective",reason:"Asigná peso a por lo menos una variable."};
  const unresolved=(preview?.anomalies||[]).find(item=>!state.decisions?.[item.order_id]);
  if(unresolved)return {section:"config-scope",reason:"Hay órdenes que requieren decidir si se incluyen o excluyen."};
  return null;
}

function anomalyReview(state,preview){
  const anomalies=preview?.anomalies||[];
  if(!anomalies.length)return "";
  return '<div class="assignment-anomaly-review">'
    +'<div><span>REVISIÓN REQUERIDA</span><strong>'+num(anomalies.length)+' '+(anomalies.length===1?'orden necesita':'órdenes necesitan')+' una decisión explícita.</strong><small>Definí si querés incluirla o excluirla de esta ejecución.</small></div>'
    +anomalies.map(item=>'<label><span><strong>'+esc(item.order_id)+'</strong><small>'+esc(item.detail||"Orden atípica")+'</small></span><select data-config-anomaly="'+esc(item.order_id)+'"><option value="">Elegí una acción…</option><option value="include" '+(state.decisions?.[item.order_id]==="include"?'selected':'')+'>Incluir</option><option value="exclude" '+(state.decisions?.[item.order_id]==="exclude"?'selected':'')+'>Excluir</option></select></label>').join("")
  +'</div>';
}

function summaryFooter(state,preview,capabilities){
  const error=blocker(state,preview,capabilities);
  return configSummaryBar({
    ready:!error,
    reason:error?.reason||"",
    chips:[
      {target:"config-scope",icon:"filter",label:"Alcance",value:scopeSummary(preview,state.scopeFilters||[])},
      {target:"config-objective",icon:"target",label:"Objetivo",value:OBJECTIVE_LABELS[state.objective]||"Balanceado"},
      {target:"config-resources",icon:"truck",label:"Recursos",value:RESOURCE_MODES[state.resourceMode]?.label||"Mixta"},
      {target:"config-depth",icon:"layoutDashboard",label:"Dashboard",value:DEPTHS[state.analysisDepth]?.label||"Comparativo"},
    ],
  });
}

function reviewDialog(state,preview,capabilities){
  const dims=activeDimensions(capabilities);
  const effective=state.objective==="custom"?normalizeRawWeights(state.customWeights||state.weights,dims):state.weights;
  const priority=state.objective==="custom"
    ?dims.map(key=>DIMENSION_LABELS[key]+' '+(effective?.[key]||0)+' %').join(' · ')
    :"Definido por el objetivo seleccionado";
  return '<dialog class="dispatch dispatch-review assignment-review-dialog" data-assignment-review-dialog><form method="dialog">'
    +'<span class="assignment-section__eyebrow">ANTES DE EJECUTAR</span><h2>Revisá tu configuración</h2>'
    +'<div class="dispatch-review-summary">'
      +'<p><strong>Alcance</strong><span>'+esc(scopeSummary(preview,state.scopeFilters||[]))+'</span></p>'
      +'<p><strong>Objetivo</strong><span>'+esc(OBJECTIVE_LABELS[state.objective]||"Balanceado")+'</span></p>'
      +'<p><strong>Prioridades</strong><span>'+esc(priority)+'</span></p>'
      +'<p><strong>Recursos</strong><span>'+esc(RESOURCE_MODES[state.resourceMode]?.label||"Mixta")+'</span></p>'
      +'<p><strong>Dashboard</strong><span>'+esc(DEPTHS[state.analysisDepth]?.label||"Comparativo")+'</span></p>'
    +'</div>'
    +'<p class="assignment-review-note">La decisión distribuirá la carga entre los recursos habilitados. Las fechas y el calendario se resolverán después en Planificación de despachos.</p>'
    +'<div class="dispatch-actions"><button value="cancel">Volver</button><button type="button" data-config-execute>Generar asignación</button></div>'
  +'</form></dialog>';
}

function filterDialog(preview){
  const fields=preview?.fields||[];
  return '<dialog class="assignment-filter-dialog" data-filter-dialog><form method="dialog">'
    +'<div class="assignment-filter-dialog__head"><div><span class="assignment-section__eyebrow">ALCANCE</span><h3>Agregar filtro</h3><p>Elegí una columna disponible en el archivo de Órdenes.</p></div><button value="cancel" aria-label="Cerrar">×</button></div>'
    +'<input type="search" placeholder="Buscar columna…" data-filter-field-search aria-label="Buscar columna para filtrar">'
    +'<div class="assignment-filter-field-list" data-filter-field-list>'
      +fields.map(field=>'<button type="button" data-filter-add="'+esc(field.column)+'" data-field-label="'+esc(field.label.toLowerCase())+'"><span>'+esc(field.label)+'</span><small>'+esc(field.type==="date"?'Fecha':field.type==="category"?'Categoría':'Numérica')+'</small></button>').join("")
    +'</div>'
  +'</form></dialog>';
}

function changeDataDialog(hasFilters,hasApproved){
  const impact=[];
  if(hasFilters)impact.push("Los filtros actuales dependen de columnas del Data Pack en uso.");
  if(hasApproved)impact.push("Hay decisiones aprobadas vinculadas a los archivos actuales.");
  return '<dialog class="assignment-change-dialog" data-assignment-change-dialog><form method="dialog">'
    +'<span class="assignment-section__icon">'+iconSvg("refresh","assignment-icon")+'</span><h3>¿Cambiar los datos?</h3>'
    +'<p>Al seleccionar otros archivos, Dation crea un nuevo Decision Case y conserva el historial del actual.</p>'
    +(impact.length?'<ul>'+impact.map(item=>'<li>'+esc(item)+'</li>').join("")+'</ul>':'')
    +'<div class="dispatch-actions"><button value="cancel">Cancelar</button><button type="button" data-change-confirm>Ir a Carga de datos</button></div>'
  +'</form></dialog>';
}

function defaultFilter(field){
  if(field.type==="date"){
    const preset="last14";
    const resolved=resolvedDateRange(field,preset,[field.min,field.max]);
    return {column:field.column,type:"date",operator:"between",value:[...resolved],resolved:[...resolved],preset};
  }
  if(field.type==="number")return {column:field.column,type:"number",operator:"between",value:[field.min,field.max],resolved:null};
  return {column:field.column,type:"category",operator:"in",value:[],resolved:null};
}

export async function mountAssignmentConfig(root,context){
  ensureStyles();
  const {state,persist,capabilities,onData,onExecute}=context;
  state.scopeFilters=Array.isArray(state.scopeFilters)?state.scopeFilters:[];
  state.resourceMode=["own","mixed","outsourced"].includes(state.resourceMode)
    ?state.resourceMode
    :(state.allow===false?"own":"mixed");
  state.allow=state.resourceMode!=="own";
  state.analysisDepth=["essential","comparative"].includes(state.analysisDepth)
    ?state.analysisDepth
    :"comparative";
  const dims=activeDimensions(capabilities);
  state.dimensions=dims.length?dims:["trips"];
  state.customWeights=state.customWeights||{...state.weights};
  if(state.objective==="min_co2"&&!productVariableAvailable("co2"))state.objective="balanced";
  if(state.objective==="max_own_fleet"&&state.resourceMode==="outsourced")state.objective="balanced";
  let preview=null;
  let previewGeneration=0;
  let renderGeneration=0;

  async function fetchPreview(){
    const generation=++previewGeneration;
    const data=await post("/api/runs/assignment-preview",{
      orders_dataset_id:state.orders.id,
      fleet_dataset_id:state.fleet.id,
      filters:filterPayload(state.scopeFilters),
      resource_mode:state.resourceMode,
    });
    if(generation!==previewGeneration)return preview;
    preview=data;
    state.configPreview=data;
    persist();
    return data;
  }

  function syncWeights(){
    const available=activeDimensions(capabilities);
    state.dimensions=available.length?available:["trips"];
    if(state.objective==="custom"){
      state.weights=normalizeRawWeights(state.customWeights,state.dimensions);
    }else if(state.objective==="balanced"){
      state.weights=normalizeRawWeights(equalRaw(state.dimensions),state.dimensions);
    }else{
      state.weights=normalizeRawWeights(presetRaw(state.objective,state.dimensions),state.dimensions);
    }
    state.allow=state.resourceMode!=="own";
    state.configured=true;
    persist();
  }

  function pageMarkup(){
    const approved=Object.values(state.decisionCase?.nodes||{}).some(item=>item?.status==="approved");
    return '<div class="dispatch-config-screen assignment-config-v2">'
      +heroMarkup()
      +caseStrip(state,preview)
      +'<main class="assignment-config-sections">'
        +scopeSection(state,preview)
        +anomalyReview(state,preview)
        +objectiveSection(state,capabilities)
        +resourceSection(state,preview)
        +depthSection(state)
      +'</main>'
      +summaryFooter(state,preview,capabilities)
      +filterDialog(preview)
      +changeDataDialog(Boolean(state.scopeFilters.length),approved)
      +reviewDialog(state,preview,capabilities)
    +'</div>';
  }

  function scrollToProblem(item){
    const target=document.getElementById(item.section);
    if(!target)return;
    target.classList.remove("is-attention");
    void target.offsetWidth;
    target.classList.add("is-attention");
    target.scrollIntoView({behavior:"smooth",block:"center"});
    window.setTimeout(()=>target.classList.remove("is-attention"),1800);
  }

  async function rerender({previewFirst=false}={}){
    const generation=++renderGeneration;
    if(previewFirst){
      try{await fetchPreview();}catch(error){
        preview={valid:false,errors:[{detail:error.message}],orders:{included:0,total:Number(state.orders?.row_count||0)},fleet:{included:Number(state.fleet?.row_count||0),total:Number(state.fleet?.row_count||0)},fields:preview?.fields||[]};
      }
    }
    if(generation!==renderGeneration)return;
    syncWeights();
    root.className="dispatch dispatch-upload-pro assignment-config-root";
    root.innerHTML=pageMarkup();
    bind();
  }

  function addFilter(column){
    const field=(preview?.fields||[]).find(item=>item.column===column);
    if(!field)return;
    if(state.scopeFilters.some(item=>item.column===column))return;
    state.scopeFilters=[...state.scopeFilters,defaultFilter(field)];
    persist();
  }

  function bindFilterRows(){
    root.querySelectorAll("[data-filter-remove]").forEach(button=>button.onclick=async()=>{
      const index=Number(button.dataset.filterRemove);
      state.scopeFilters=state.scopeFilters.filter((_,current)=>current!==index);
      persist();
      await rerender({previewFirst:true});
    });
    root.querySelectorAll("[data-filter-search]").forEach(input=>input.oninput=()=>{
      const index=input.dataset.filterSearch;
      const query=input.value.trim().toLowerCase();
      root.querySelectorAll('[data-filter-index="'+index+'"] [data-filter-option-label]').forEach(label=>{
        label.hidden=Boolean(query&&!label.dataset.filterOptionLabel.includes(query));
      });
    });
    root.querySelectorAll("[data-filter-category]").forEach(input=>input.onchange=async()=>{
      const index=Number(input.dataset.filterCategory);
      const selected=[...root.querySelectorAll('[data-filter-category="'+index+'"]:checked')].map(item=>item.value);
      state.scopeFilters[index]={...state.scopeFilters[index],value:selected,resolved:null};
      persist();
      await rerender({previewFirst:true});
    });
    root.querySelectorAll("[data-filter-all]").forEach(button=>button.onclick=async()=>{
      const index=Number(button.dataset.filterAll);
      const field=(preview?.fields||[]).find(item=>item.column===state.scopeFilters[index]?.column);
      state.scopeFilters[index]={...state.scopeFilters[index],value:(field?.values||[]).map(item=>String(item.value)),resolved:null};
      persist();
      await rerender({previewFirst:true});
    });
    root.querySelectorAll("[data-filter-none]").forEach(button=>button.onclick=async()=>{
      const index=Number(button.dataset.filterNone);
      state.scopeFilters[index]={...state.scopeFilters[index],value:[],resolved:null};
      persist();
      await rerender({previewFirst:true});
    });
    root.querySelectorAll("[data-filter-number-min],[data-filter-number-max]").forEach(input=>input.onchange=async()=>{
      const index=Number(input.dataset.filterNumberMin??input.dataset.filterNumberMax);
      const row=root.querySelector('[data-filter-index="'+index+'"]');
      const min=Number(row.querySelector('[data-filter-number-min]').value);
      const max=Number(row.querySelector('[data-filter-number-max]').value);
      state.scopeFilters[index]={...state.scopeFilters[index],value:[min,max],resolved:null};
      persist();
      await rerender({previewFirst:true});
    });
    root.querySelectorAll("[data-filter-date-preset]").forEach(select=>select.onchange=async()=>{
      const index=Number(select.dataset.filterDatePreset);
      const field=(preview?.fields||[]).find(item=>item.column===state.scopeFilters[index]?.column);
      const preset=select.value;
      const current=state.scopeFilters[index];
      const resolved=resolvedDateRange(field,preset,current.value);
      state.scopeFilters[index]={...current,preset,value:[...resolved],resolved:[...resolved]};
      persist();
      await rerender({previewFirst:true});
    });
    root.querySelectorAll("[data-filter-date-from],[data-filter-date-to]").forEach(input=>input.onchange=async()=>{
      const index=Number(input.dataset.filterDateFrom??input.dataset.filterDateTo);
      const row=root.querySelector('[data-filter-index="'+index+'"]');
      const from=row.querySelector('[data-filter-date-from]').value;
      const to=row.querySelector('[data-filter-date-to]').value;
      state.scopeFilters[index]={...state.scopeFilters[index],preset:"custom",value:[from,to],resolved:[from,to]};
      persist();
      await rerender({previewFirst:true});
    });
  }

  function bind(){
    const copy=root.querySelector("[data-config-copy-case]");
    if(copy)copy.onclick=async()=>{
      const feedback=root.querySelector("[data-config-copy-feedback]");
      try{
        await navigator.clipboard.writeText(String(state.decisionCase?.id||""));
        if(feedback)feedback.textContent="ID copiado";
        window.setTimeout(()=>{if(feedback)feedback.textContent="";},1800);
      }catch{if(feedback)feedback.textContent="No se pudo copiar";}
    };

    const changeDialog=root.querySelector("[data-assignment-change-dialog]");
    root.querySelector("[data-config-change-data]")?.addEventListener("click",()=>{
      const hasImpact=Boolean(state.scopeFilters.length)||Object.values(state.decisionCase?.nodes||{}).some(item=>item?.status==="approved");
      if(hasImpact&&changeDialog?.showModal)changeDialog.showModal();else onData?.();
    });
    root.querySelector("[data-change-confirm]")?.addEventListener("click",event=>{
      event.preventDefault();changeDialog?.close();onData?.();
    });

    const filterDialogNode=root.querySelector("[data-filter-dialog]");
    root.querySelector("[data-filter-dialog-open]")?.addEventListener("click",()=>filterDialogNode?.showModal?.());
    root.querySelector("[data-filter-field-search]")?.addEventListener("input",event=>{
      const query=event.target.value.trim().toLowerCase();
      root.querySelectorAll("[data-field-label]").forEach(button=>button.hidden=Boolean(query&&!button.dataset.fieldLabel.includes(query)));
    });
    root.querySelectorAll("[data-filter-add]").forEach(button=>button.onclick=async()=>{
      addFilter(button.dataset.filterAdd);filterDialogNode?.close();await rerender({previewFirst:true});
    });
    root.querySelectorAll("[data-filter-quick]").forEach(button=>button.onclick=async()=>{
      addFilter(button.dataset.filterQuick);await rerender({previewFirst:true});
    });
    root.querySelector("[data-filter-clear]")?.addEventListener("click",async()=>{
      state.scopeFilters=[];persist();await rerender({previewFirst:true});
    });
    bindFilterRows();

    root.querySelectorAll("[data-objective]").forEach(button=>button.onclick=async()=>{
      if(button.disabled)return;
      const previous=state.objective;
      state.objective=button.dataset.objective;
      if(state.objective!=="custom")state.lastPreset=state.objective;
      if(state.objective==="custom"&&!state.customWeights){
        state.customWeights=presetRaw(previous==="custom"?(state.lastPreset||"balanced"):previous,state.dimensions);
      }
      syncWeights();
      await rerender();
    });

    root.querySelectorAll("[data-custom-weight]").forEach(slider=>slider.oninput=()=>{
      const key=slider.dataset.customWeight;
      state.customWeights={...state.customWeights,[key]:Number(slider.value)};
      state.weights=normalizeRawWeights(state.customWeights,state.dimensions);
      state.configured=true;
      persist();
      const effective=normalizeRawWeights(state.customWeights,state.dimensions);
      root.querySelectorAll("[data-effective-weight]").forEach(output=>output.textContent=(effective[output.dataset.effectiveWeight]||0)+' %');
      root.querySelectorAll(".assignment-weight-distribution span").forEach((segment,index)=>{
        const segmentKey=state.dimensions[index];
        if(segmentKey)segment.style.setProperty("--weight",(effective[segmentKey]||0)+'%');
      });
      slider.setAttribute("aria-valuetext",DIMENSION_LABELS[key]+', '+slider.value+' de 100, equivale al '+effective[key]+' %');
    });
    root.querySelector("[data-custom-base]")?.addEventListener("change",async event=>{
      state.customWeights=presetRaw(event.target.value,state.dimensions);syncWeights();await rerender();
    });
    root.querySelector("[data-custom-equal]")?.addEventListener("click",async()=>{
      state.customWeights=equalRaw(state.dimensions);syncWeights();await rerender();
    });
    root.querySelector("[data-custom-reset]")?.addEventListener("click",async()=>{
      state.customWeights=presetRaw(state.lastPreset||"balanced",state.dimensions);syncWeights();await rerender();
    });

    root.querySelectorAll("[data-resource-mode]").forEach(button=>button.onclick=async()=>{
      if(button.disabled)return;
      state.resourceMode=button.dataset.resourceMode;
      state.allow=state.resourceMode!=="own";
      if(state.resourceMode==="outsourced"&&state.objective==="max_own_fleet")state.objective="balanced";
      persist();
      await rerender({previewFirst:true});
    });

    root.querySelectorAll("[data-depth]").forEach(button=>button.onclick=async()=>{
      if(button.disabled)return;
      state.analysisDepth=button.dataset.depth;
      state.configured=true;
      persist();
      await rerender();
    });

    root.querySelectorAll("[data-config-anomaly]").forEach(select=>select.onchange=async()=>{
      state.decisions={...state.decisions,[select.dataset.configAnomaly]:select.value};
      persist();
      await rerender();
    });

    root.querySelectorAll("[data-summary-target]").forEach(button=>button.onclick=()=>document.getElementById(button.dataset.summaryTarget)?.scrollIntoView({behavior:"smooth",block:"center"}));
    const reviewDialogNode=root.querySelector("[data-assignment-review-dialog]");
    root.querySelector("[data-config-review]")?.addEventListener("click",()=>{
      const problem=blocker(state,preview,capabilities);
      if(problem){scrollToProblem(problem);return;}
      reviewDialogNode?.showModal?.();
    });
    root.querySelector("[data-config-execute]")?.addEventListener("click",event=>{
      event.preventDefault();reviewDialogNode?.close();onExecute?.();
    });
  }

  syncWeights();
  try{await fetchPreview();}catch(error){
    root.innerHTML='<section class="dispatch-panel"><h1>No pudimos preparar la configuración</h1><p>'+esc(error.message)+'</p><button data-config-retry>Reintentar</button></section>';
    root.querySelector("[data-config-retry]").onclick=()=>mountAssignmentConfig(root,context);
    return;
  }
  await rerender();
}

export {filterPayload,normalizeRawWeights};