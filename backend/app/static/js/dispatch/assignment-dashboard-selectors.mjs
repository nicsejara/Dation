const DEPTHS={
  essential:{label:'Esencial',className:'is-essential'},
  comparative:{label:'Comparativo',className:'is-comparative'},
  deep:{label:'Profundo',className:'is-deep'},
};

const STATUSES={
  running:{label:'Procesando',className:'is-running'},
  review:{label:'En revisión',className:'is-review'},
  approved:{label:'Aprobada',className:'is-approved'},
  error:{label:'Requiere revisión',className:'is-error'},
  stale:{label:'Requiere revisión',className:'is-error'},
  superseded:{label:'Reemplazada',className:'is-review'},
};

const OBJECTIVES={
  min_trips:'Minimizar viajes',
  min_cost:'Minimizar costo',
  max_own_fleet:'Maximizar uso de flota propia',
  min_co2:'Minimizar CO₂',
  balanced:'Objetivo balanceado',
  custom:'Objetivo personalizado',
};

const DIMENSIONS={
  trips:{label:'Viajes',metric:'total_trips'},
  cost:{label:'Costo',metric:'total_cost'},
  own_fleet:{label:'Flota propia',metric:'own_weight_share'},
  co2:{label:'CO₂',metric:'co2_kg'},
};

const OBJECTIVE_DIMENSION={
  min_trips:'trips',
  min_cost:'cost',
  max_own_fleet:'own_fleet',
  min_co2:'co2',
};

const COMPARISON_SCENARIO_ORDER=[
  'balanced',
  'min_cost',
  'min_trips',
  'max_own_fleet',
  'min_co2',
];

const COMPARISON_SCENARIO_LABELS={
  balanced:'Balanceado',
  min_cost:'Costo mínimo',
  min_trips:'Viajes mínimos',
  max_own_fleet:'Mayor uso de flota propia',
  min_co2:'CO₂ mínimo',
};

// Both executive cards and comparisons use these definitions. Ownership is by weight.
export const EXECUTIVE_KPIS=Object.freeze([
  {key:'total_cost',dimension:'cost',label:'Costo total',icon:'dollarSign',format:'money',fallbackDirection:'lower_better',
    description:'Costo estimado de ejecutar toda la asignación.'},
  {key:'total_trips',dimension:'trips',label:'Viajes',icon:'route',format:'integer',fallbackDirection:'lower_better',
    description:'Viajes requeridos para transportar la carga.'},
  {key:'load_utilization',dimension:null,label:'Utilización',icon:'gauge',format:'percent',fallbackDirection:'higher_better',
    description:'Carga transportada dividida por la capacidad total de los viajes utilizados.'},
  {key:'own_weight_share',dimension:'own_fleet',label:'Flota propia',icon:'truck',format:'percent',fallbackDirection:'higher_better',
    description:'Participación de la carga transportada con flota propia, medida por peso.'},
].map(Object.freeze));
const COMPARISON_KPIS=Object.freeze([...EXECUTIVE_KPIS,
  {key:'co2_kg',dimension:'co2',label:'CO₂ estimado',format:'number',fallbackDirection:'lower_better'},
  {key:'avg_cost_per_trip',dimension:null,label:'Costo promedio por viaje',format:'money',fallbackDirection:'lower_better'},
].map(Object.freeze));

function selected(result){
  return result?.scenarios?.selected||{};
}

function normalizeWeight(value){
  const number=Number(value);
  return Number.isFinite(number)&&number>0?number:0;
}

function resourceId(value){
  return value?.vehicle_id||value?.fleet_pool_id||value?.vehicle_type||'Recurso sin ID';
}

function finiteMetric(value){
  if(typeof value!=='number'&&(typeof value!=='string'||!value.trim()))return null;
  const number=Number(value);
  return Number.isFinite(number)?number:null;
}

export function getScenarioMetric(scenario,metricKey){
  const metrics=scenario?.metrics||{};
  if(metricKey!=='avg_cost_per_trip')return finiteMetric(metrics[metricKey]);
  const cost=finiteMetric(metrics.total_cost),trips=finiteMetric(metrics.total_trips);
  if(cost===null||trips===null||trips<=0)return null;
  const value=cost/trips;
  return Number.isFinite(value)?value:null;
}

export function getExecutiveKpisForScenario(scenario){
  return EXECUTIVE_KPIS.map(item=>({...item,value:getScenarioMetric(scenario,item.key)}));
}

export function getAnalysisDepth(run){
  const result=run?.result_json||{};
  const value=result.analysis?.depth
    ||result.configuration?.options?.analysis_depth
    ||run?.configuration_json?.options?.analysis_depth
    ||'comparative';
  return Object.hasOwn(DEPTHS,value)?value:'comparative';
}

export function analysisDepthUi(runOrDepth){
  const depth=typeof runOrDepth==='string'
    ?(Object.hasOwn(DEPTHS,runOrDepth)?runOrDepth:'comparative')
    :getAnalysisDepth(runOrDepth);
  return {depth,...DEPTHS[depth]};
}

export function decisionStatusUi(status){
  return STATUSES[status]||{label:'Decisión disponible',className:'is-available'};
}

export function solverStatusLabel(status){
  const labels={
    optimal:'Óptimo',
    feasible:'Factible',
    heuristic:'Heurística',
    best_candidate:'Mejor solución encontrada',
    infeasible:'No factible',
  };
  return labels[status]||status||'No informado';
}

export function shortRunId(value){
  const id=String(value||'');
  return id.length>10?id.slice(0,8)+'…':id||'—';
}

export function getObjectiveWeights(result){
  const configuration=result?.configuration||{};
  const dimensions=Array.isArray(configuration.dimensions)
    ?configuration.dimensions
    :Object.keys(configuration.weights||{});
  const weights=configuration.weights||{};
  const rows=[];

  for(const dimension of dimensions){
    if(!DIMENSIONS[dimension])continue;
    const weight=normalizeWeight(weights[dimension]);
    if(weight>0){
      rows.push({
        dimension,
        label:DIMENSIONS[dimension].label,
        metric:DIMENSIONS[dimension].metric,
        weight,
      });
    }
  }

  if(rows.length)return rows;
  const fallbackDimension=OBJECTIVE_DIMENSION[configuration.objective];
  if(fallbackDimension&&DIMENSIONS[fallbackDimension]){
    return [{
      dimension:fallbackDimension,
      label:DIMENSIONS[fallbackDimension].label,
      metric:DIMENSIONS[fallbackDimension].metric,
      weight:1,
    }];
  }
  return [];
}

export function getActiveObjectiveMetrics(result){
  return getObjectiveWeights(result).map(item=>({
    ...item,
    metric:item.metric,
  }));
}

export function getAssignmentSummary(result){
  const scenario=selected(result);
  const metrics=scenario.metrics||{};
  const configuration=result?.configuration||{};
  const objective=configuration.objective||result?.decision?.objective||'unknown';
  return {
    orders:finiteMetric(metrics.orders),
    trips:finiteMetric(metrics.total_trips),
    totalWeightKg:finiteMetric(metrics.total_weight_kg),
    vehiclesUsed:finiteMetric(metrics.vehicles_used),
    objective,
    objectiveLabel:OBJECTIVES[objective]||'Objetivo configurado',
    objectiveWeights:getObjectiveWeights(result),
    feasible:scenario.feasible===true,
    solverStatus:scenario.solver?.status||result?.engine?.solver?.status||null,
  };
}

export function getOperationalKpis(result){
  const active=new Set(getActiveObjectiveMetrics(result).map(item=>item.metric));
  // Average cost is descriptive: minimizing total cost does not minimize a ratio.
  return getExecutiveKpisForScenario(selected(result)).map(item=>({...item,objective:active.has(item.key)}));
}

export function getAssignmentTrips(result){
  return (selected(result).trips||[]).map((trip,index)=>{
    const loads=Array.isArray(trip.loads)?trip.loads:[];
    const orders=[...new Set(loads.map(load=>load.order_id).filter(Boolean))];
    return {
      ...trip,
      trip_id:trip.trip_id||`Viaje ${index+1}`,
      resource_id:resourceId(trip),
      order_count:orders.length,
      order_ids:orders,
      ownership_label:trip.ownership==='third_party'?'Tercerizada':'Propia',
    };
  });
}

export function getAssignmentVehicles(result){
  const trips=getAssignmentTrips(result);
  const totalWeight=Number(selected(result).metrics?.total_weight_kg||0);
  const groups=new Map();

  for(const trip of trips){
    const id=trip.resource_id;
    if(!groups.has(id)){
      groups.set(id,{
        id,
        vehicle_type:trip.vehicle_type||null,
        ownership:trip.ownership||null,
        provider_name:trip.provider_name||null,
        base_site:trip.base_site||trip.base_location||null,
        trips:0,
        weights:[],
        capacities:[],
        orders:new Set(),
      });
    }
    const group=groups.get(id);
    group.trips+=1;
    group.weights.push(trip.load_kg);
    group.capacities.push(trip.capacity_kg);
    for(const orderId of trip.order_ids)group.orders.add(orderId);
  }

  return [...groups.values()].map(group=>({
    id:group.id,
    vehicle_type:group.vehicle_type,
    ownership:group.ownership,
    provider_name:group.provider_name,
    base_site:group.base_site,
    trips:group.trips,
    load_kg:completeSum(group.weights),
    utilization:completeSum(group.weights)!==null&&completeSum(group.capacities)>0
      ?completeSum(group.weights)/completeSum(group.capacities):null,
    orders:group.orders.size,
    load_share:totalWeight>0&&completeSum(group.weights)!==null?completeSum(group.weights)/totalWeight:null,
  })).sort((a,b)=>b.load_kg-a.load_kg||a.id.localeCompare(b.id));
}

export function getAssignmentOrders(result){
  return (selected(result).order_outcomes||[]).map(order=>({
    order_id:order.order_id||'—',
    product:order.product||'Producto no registrado',
    units:order.units??null,
    kg:order.kg??null,
    trip_ids:Array.isArray(order.trip_ids)?order.trip_ids:[],
    vehicle_ids:Array.isArray(order.vehicle_ids)?order.vehicle_ids:[],
    split:Boolean(order.split),
    consolidated:Boolean(order.consolidated),
    outsourced:Boolean(order.outsourced),
  }));
}

export function getApprovalWarnings(result){
  const warnings=[];
  const scenario=selected(result);
  const trips=getAssignmentTrips(result);
  const orders=getAssignmentOrders(result);
  const exceptions=Array.isArray(result?.exceptions)?result.exceptions:[];
  const includedAnomalies=(Array.isArray(result?.inputs?.anomalies)?result.inputs.anomalies:[]).filter(item=>item?.decision==='include');
  const outsourcedTrips=trips.filter(trip=>trip.ownership==='third_party');
  const splitOrders=orders.filter(order=>order.split);

  if(scenario.feasible===false||scenario.solver?.status==='infeasible'||result?.engine?.solver?.status==='infeasible'){
    warnings.push({
      key:'infeasible',
      level:'attention',
      label:'Atención crítica',
      title:'El escenario seleccionado está marcado como no factible',
      detail:'La evidencia publicada indica que el plan no es factible. Revisá esta condición antes de considerar una aprobación.',
    });
  }
  if(exceptions.length){
    warnings.push({
      key:'engine_exceptions',
      level:'attention',
      label:'Atención',
      title:`${exceptions.length} observación${exceptions.length===1?'':'es'} publicada${exceptions.length===1?'':'s'} por el motor`,
      detail:exceptions.map(item=>{
        if(typeof item==='string')return item;
        const message=[item?.title,item?.message,item?.detail,item?.description,item?.code].filter(value=>typeof value==='string'&&value.trim());
        const identity=[item?.order_id,item?.trip_id,item?.vehicle_id].filter(value=>typeof value==='string'&&value.trim());
        return [...new Set([...message,...identity])].join(' · ')||'Observación del motor sin detalle adicional publicado.';
      }).join('; '),
    });
  }
  if(outsourcedTrips.length){
    warnings.push({
      key:'outsourced',
      level:'review',
      label:'Revisar',
      title:`${outsourcedTrips.length} viaje${outsourcedTrips.length===1?'':'s'} tercerizado${outsourcedTrips.length===1?'':'s'}`,
      detail:'Confirmá disponibilidad y condiciones comerciales del recurso externo.',
    });
  }
  if(includedAnomalies.length){
    warnings.push({
      key:'anomalies',
      level:'review',
      label:'Revisar',
      title:`${includedAnomalies.length} anomalía${includedAnomalies.length===1?'':'s'} incluida${includedAnomalies.length===1?'':'s'}`,
      detail:'La configuración incluyó estas órdenes atípicas de forma explícita.',
    });
  }
  if(splitOrders.length){
    warnings.push({
      key:'split_orders',
      level:'review',
      label:'Revisar',
      title:`${splitOrders.length} orden${splitOrders.length===1?'':'es'} dividida${splitOrders.length===1?'':'s'} entre viajes`,
      detail:'Verificá que la división sea aceptable para la operación antes de congelar la asignación.',
    });
  }

  return warnings;
}

export function sameAssignmentPlan(first,second){
  const a=first?.plan_fingerprint;
  const b=second?.plan_fingerprint;
  return Boolean(a&&b&&a===b);
}

export function getScenarioLabel(key,scenario){
  return scenario?.name||COMPARISON_SCENARIO_LABELS[key]||String(key||'Escenario').replaceAll('_',' ');
}

export function getComparableScenarios(result){
  const scenarios=result?.scenarios||{};
  const selectedScenario=scenarios.selected||{};
  const known=[];
  const remainder=[];

  for(const [key,scenario] of Object.entries(scenarios)){
    if(key==='selected'||!scenario?.metrics)continue;
    const item={
      key,
      label:getScenarioLabel(key,scenario),
      feasible:scenario.feasible!==false&&scenario.solver?.status!=='infeasible',
      samePlan:sameAssignmentPlan(selectedScenario,scenario),
      solverStatus:scenario.solver?.status||null,
      scenario,
    };
    if(COMPARISON_SCENARIO_ORDER.includes(key))known.push(item);
    else remainder.push(item);
  }

  known.sort((a,b)=>COMPARISON_SCENARIO_ORDER.indexOf(a.key)-COMPARISON_SCENARIO_ORDER.indexOf(b.key));
  remainder.sort((a,b)=>a.label.localeCompare(b.label,'es'));
  return known.concat(remainder);
}

export function getDefaultComparisonKey(result){
  const alternatives=getComparableScenarios(result);
  if(!alternatives.length)return null;
  const selectedScenario=selected(result);
  const objective=result?.configuration?.objective||result?.decision?.objective||null;
  const preferred=[];

  if(objective!=='balanced')preferred.push('balanced');
  if(objective!=='min_cost')preferred.push('min_cost');
  if(objective!=='min_trips')preferred.push('min_trips');
  if(objective!=='max_own_fleet')preferred.push('max_own_fleet');
  if(objective!=='min_co2')preferred.push('min_co2');

  const executableDifferent=alternatives.filter(item=>item.feasible&&!sameAssignmentPlan(selectedScenario,item.scenario));
  for(const key of preferred){
    const match=executableDifferent.find(item=>item.key===key);
    if(match)return match.key;
  }
  return executableDifferent[0]?.key
    ||alternatives.find(item=>item.feasible)?.key
    ||alternatives[0].key;
}

export function getComparisonMetricDefinitions(){
  return COMPARISON_KPIS.map(item=>({...item}));
}

export function compareScenarioMetric(result,referenceKey,metricKey){
  const definition=COMPARISON_KPIS.find(item=>item.key===metricKey);
  const selectedScenario=selected(result);
  const reference=result?.scenarios?.[referenceKey];
  const selectedValue=getScenarioMetric(selectedScenario,metricKey);
  const referenceValue=getScenarioMetric(reference,metricKey);
  const base={
    ...(definition||{key:metricKey,dimension:null,label:metricKey,format:'number',fallbackDirection:'lower_better'}),
    selectedValue,
    referenceValue,
    absolute:null,
    percent:null,
    semantic:'no_comparable',
    semanticLabel:'No comparable',
    reason:null,
  };

  if(!reference){
    return {...base,reason:'Escenario no disponible'};
  }
  if(selectedValue===null||referenceValue===null){
    return {...base,reason:'Métrica no publicada en ambos escenarios'};
  }
  if(reference.feasible===false||reference.solver?.status==='infeasible'){
    return {...base,reason:'La referencia está marcada como no factible'};
  }
  if(selectedScenario.feasible===false||selectedScenario.solver?.status==='infeasible'||result?.engine?.solver?.status==='infeasible'){
    return {...base,reason:'La recomendación está marcada como no factible'};
  }

  const absolute=selectedValue-referenceValue;
  if(!Number.isFinite(absolute))return {...base,reason:'La diferencia no puede representarse como un valor finito'};
  const ratio=referenceValue===0?null:absolute/Math.abs(referenceValue);
  const percent=Number.isFinite(ratio)?ratio:null;
  if(Math.abs(absolute)<1e-12){
    return {
      ...base,
      absolute:0,
      percent:referenceValue===0?null:0,
      semantic:'same',
      semanticLabel:'Sin cambio',
    };
  }

  const direction=definition?.fallbackDirection||result?.kpi_directions?.[metricKey]||base.fallbackDirection;
  const improved=direction==='higher_better'?absolute>0:absolute<0;
  return {
    ...base,
    absolute,
    percent,
    direction,
    semantic:improved?'improvement':'tradeoff',
    semanticLabel:improved?'Mejora':'Trade-off',
  };
}

export function getComparisonRows(result,referenceKey){
  return COMPARISON_KPIS.map(metric=>compareScenarioMetric(result,referenceKey,metric.key));
}

export function getComparisonContext(result,referenceKey){
  const alternatives=getComparableScenarios(result);
  const key=referenceKey&&result?.scenarios?.[referenceKey]
    ?referenceKey
    :getDefaultComparisonKey(result);
  const reference=key?result?.scenarios?.[key]:null;
  const selectedScenario=selected(result);
  return {
    key,
    selected:selectedScenario,
    reference,
    referenceLabel:key?getScenarioLabel(key,reference):'Sin alternativa',
    alternatives,
    samePlan:reference?sameAssignmentPlan(selectedScenario,reference):false,
    feasible:reference?.feasible!==false,
    rows:key?getComparisonRows(result,key):[],
  };
}

// Presentation models never write to the persisted run or infer absent metrics as zero.
export const getEssentialKpis=getOperationalKpis;

export function getAssignmentContext(result){
  const metrics=selected(result).metrics||{},trips=getAssignmentTrips(result);
  const destinations=new Set(trips.map(t=>t.destination).filter(v=>typeof v==='string'&&v.trim()));
  const resources=Array.isArray(result?.resources)?result.resources:null;
  const metadata=result?.inputs?.orders||{};
  const unit=metadata.quantity_unit||metadata.unit_of_measure;
  return {
    orders:finiteMetric(metrics.orders),totalWeightKg:finiteMetric(metrics.total_weight_kg),
    destinations:trips.length&&trips.every(t=>typeof t.destination==='string'&&t.destination.trim())?destinations.size:null,
    evaluatedVehicles:resources?resources.length:null,
    unitsLabel:typeof unit==='string'&&unit.trim()?unit.trim().slice(0,40):'unidades',
  };
}

export function getScenarioTable(result){
  const scenario=selected(result),objective=result?.configuration?.objective||result?.decision?.objective;
  const alternatives=getComparableScenarios(result);
  const published=alternatives.find(item=>item.key===objective&&sameAssignmentPlan(scenario,item.scenario));
  const rows=alternatives.map(item=>({...item,selected:item===published,
    values:Object.fromEntries(EXECUTIVE_KPIS.map(k=>[k.key,getScenarioMetric(item.scenario,k.key)])),
  }));
  if(published){
    const row=rows.find(item=>item.selected);
    row.scenario=scenario;
    row.values=Object.fromEntries(EXECUTIVE_KPIS.map(k=>[k.key,getScenarioMetric(scenario,k.key)]));
  }else{
    rows.unshift({key:'selected',label:scenario.name||COMPARISON_SCENARIO_LABELS[objective]||'Recomendación',scenario,selected:true,
      feasible:scenario.feasible!==false&&scenario.solver?.status!=='infeasible',samePlan:false,
      values:Object.fromEntries(EXECUTIVE_KPIS.map(k=>[k.key,getScenarioMetric(scenario,k.key)]))});
  }
  return rows;
}

export function getDecisionInsights(result){
  const scenario=selected(result),summary=getAssignmentSummary(result),rows=[];
  const utilization=getScenarioMetric(scenario,'load_utilization'),own=getScenarioMetric(scenario,'own_weight_share');
  if(utilization!==null)rows.push({key:'utilization',icon:'gauge',title:'Aprovechamiento de capacidad',
    metric:utilization,format:'percent',detail:'de la capacidad agregada de los viajes publicados está ocupada por carga.'});
  if(own!==null)rows.push({key:'ownership',icon:'truck',title:own===1?'Sin tercerización':own===0?'Ejecución tercerizada':'Combinación de recursos',
    metric:own,format:'percent',detail:'del peso transportado queda asignado a flota propia.'});
  const co2=getScenarioMetric(scenario,'co2_kg');
  const reference=getComparableScenarios(result).find(item=>item.feasible&&!item.samePlan
    &&['min_cost','min_trips'].includes(item.key)&&co2!==null
    &&getScenarioMetric(item.scenario,'co2_kg')!==null&&co2<getScenarioMetric(item.scenario,'co2_kg'));
  if(reference&&summary.feasible)rows.push({key:'emissions',icon:'leaf',title:'Menor impacto ambiental',
    detail:'La recomendación publica menos CO₂ que '+reference.label+'. La estimación corresponde a los factores del motor.'});
  if(rows.length<3)rows.push({key:'objective',icon:summary.objective==='balanced'?'balance':'target',title:'Prioridad aplicada',
    detail:summary.objectiveLabel+'. Se respetan las ponderaciones persistidas de esta corrida.'});
  return rows.slice(0,3);
}

export function getDecisionNarrative(result){
  const summary=getAssignmentSummary(result);
  const copy={
    min_cost:'Dation priorizó el menor costo total según la configuración de la corrida y los recursos elegibles.',
    min_trips:'Dation priorizó reducir la cantidad de viajes necesarios para distribuir la carga.',
    max_own_fleet:'Dation priorizó transportar la mayor proporción de carga con recursos propios.',
    min_co2:'Dation priorizó reducir las emisiones estimadas con los factores publicados de los recursos.',
    balanced:'Dation ponderó las prioridades configuradas para distribuir la carga sin optimizar una única dimensión de forma aislada.',
    custom:'Dation aplicó las ponderaciones personalizadas de esta corrida para construir la recomendación.',
  };
  return copy[summary.objective]||'Dation aplicó el objetivo y las restricciones persistidas de esta corrida.';
}

export function getResourceParticipation(result){
  const trips=getAssignmentTrips(result),total=trips.length;
  return getAssignmentVehicles(result).map(item=>({...item,tripShare:total?item.trips/total:null,totalTrips:total,
    concentrated:total>1&&item.trips/total>=.4,
  })).sort((a,b)=>b.trips-a.trips||a.id.localeCompare(b.id));
}

export function getAssignmentPreview(result,limit=5){
  return getAssignmentTrips(result).slice(0,Math.max(0,Math.min(5,Math.floor(finiteMetric(limit)??5))));
}

export function getDecisionTradeoffs(result,referenceKey=getDefaultComparisonKey(result)){
  const context=getComparisonContext(result,referenceKey);
  const rows=context.samePlan?[]:context.rows.filter(row=>row.absolute!==null&&Math.abs(row.absolute)>1e-10);
  return {...context,gains:rows.filter(row=>row.semantic==='improvement'),
    concessions:rows.filter(row=>row.semantic==='tradeoff')};
}

export function getTripUtilization(result,sort='utilization'){
  return getAssignmentTrips(result).map(trip=>({...trip,utilization:finiteMetric(trip.utilization)})).sort((a,b)=>
    sort==='route'?String(a.destination||'').localeCompare(String(b.destination||''),'es')||a.trip_id.localeCompare(b.trip_id)
      :sort==='trip'?a.trip_id.localeCompare(b.trip_id)
      :(b.utilization??-Infinity)-(a.utilization??-Infinity)||a.trip_id.localeCompare(b.trip_id));
}

function completeSum(values){
  const numbers=values.map(finiteMetric);
  return numbers.length&&numbers.every(n=>n!==null)?numbers.reduce((sum,n)=>sum+n,0):null;
}

export function getCorridorSummary(result){
  const groups=new Map();
  for(const trip of getAssignmentTrips(result)){
    const key=JSON.stringify([trip.origin||null,trip.destination||null]);
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(trip);
  }
  return [...groups.values()].map(trips=>{
    const load=completeSum(trips.map(t=>t.load_kg)),capacity=completeSum(trips.map(t=>t.capacity_kg));
    const loads=trips.flatMap(t=>Array.isArray(t.loads)?t.loads:[]);
    const knownOwnership=trips.every(t=>['own','third_party'].includes(t.ownership));
    const own=knownOwnership?completeSum(trips.map(t=>t.ownership==='own'?t.load_kg:0)):null;
    return {origin:trips[0].origin||null,destination:trips[0].destination||null,loadKg:load,
      units:completeSum(loads.map(l=>l.units)),trips:trips.length,
      vehicles:trips.every(t=>t.vehicle_id||t.fleet_pool_id)?new Set(trips.map(t=>t.resource_id)).size:null,
      utilization:load!==null&&capacity>0?load/capacity:null,
      ownWeightShare:own!==null&&load>0?own/load:null,
      cost:completeSum(trips.map(t=>t.estimated_cost??t.cost)),
    };
  }).sort((a,b)=>String(a.origin).localeCompare(String(b.origin),'es')||String(a.destination).localeCompare(String(b.destination),'es'));
}

const briefString=value=>typeof value==='string'?value.trim():'';
const briefList=value=>(Array.isArray(value)?value:[value]).map(briefString).filter(Boolean);

export function getExecutiveBrief(data){
  const payload=data?.explanation?.response_json||data?.explanation||data?.response_json||data||{};
  const lead=briefString(payload.executive_summary)||briefString(payload.summary)||briefString(payload.title)||briefString(payload.recommendation);
  const impact=payload.business_impact||{};
  return {lead:lead||['cost','trips','distance'].map(key=>briefString(impact[key])).filter(Boolean).join(' '),
    why:briefString(payload.why_recommended)||briefString(payload.why),drivers:briefList(payload.key_drivers||payload.events).slice(0,3),
    tradeoffs:briefList(payload.tradeoffs||payload.trade_offs).slice(0,3),
    review:[...new Set([briefString(payload.recommendation||payload.next_step),...briefList(payload.caveats||payload.risks)].filter(Boolean))].slice(0,3)};
}
export function briefText(brief){
  return [brief.lead,brief.why,...['drivers','tradeoffs','review'].flatMap(key=>brief[key])].filter(Boolean).join('\n\n');
}
