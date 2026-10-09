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

const COMPARISON_METRICS=[
  {key:'total_trips',dimension:'trips',label:'Viajes',format:'integer',fallbackDirection:'lower_better'},
  {key:'total_cost',dimension:'cost',label:'Costo estimado',format:'money',fallbackDirection:'lower_better'},
  {key:'own_weight_share',dimension:'own_fleet',label:'Flota propia',format:'percent',fallbackDirection:'higher_better'},
  {key:'co2_kg',dimension:'co2',label:'CO₂ estimado',format:'co2',fallbackDirection:'lower_better'},
];

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
  if(value===null||value===undefined||value==='')return null;
  const number=Number(value);
  return Number.isFinite(number)?number:null;
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
  const objective=configuration.objective||result?.decision?.objective||'balanced';
  return {
    orders:metrics.orders??0,
    trips:metrics.total_trips??0,
    totalWeightKg:metrics.total_weight_kg??null,
    vehiclesUsed:metrics.vehicles_used??null,
    objective,
    objectiveLabel:OBJECTIVES[objective]||'Objetivo configurado',
    objectiveWeights:getObjectiveWeights(result),
    feasible:scenario.feasible===true,
    solverStatus:scenario.solver?.status||result?.engine?.solver?.status||null,
  };
}

export function getOperationalKpis(result){
  const metrics=selected(result).metrics||{};
  const active=new Set(getActiveObjectiveMetrics(result).map(item=>item.metric));
  const rows=[
    {
      key:'total_trips',
      label:'Viajes propuestos',
      value:metrics.total_trips,
      format:'integer',
      objective:active.has('total_trips'),
    },
    {
      key:'load_utilization',
      label:'Utilización media',
      value:metrics.load_utilization,
      format:'percent',
      objective:false,
    },
    {
      key:'own_weight_share',
      label:'Flota propia',
      value:metrics.own_weight_share,
      secondaryValue:metrics.outsourced_weight_share,
      secondaryLabel:'Tercerizada',
      format:'percent',
      objective:active.has('own_weight_share'),
    },
    {
      key:'vehicles_used',
      label:'Vehículos utilizados',
      value:metrics.vehicles_used,
      format:'integer',
      objective:false,
    },
    {
      key:'total_cost',
      label:'Costo estimado',
      value:metrics.total_cost,
      format:'money',
      objective:active.has('total_cost'),
    },
    {
      key:'co2_kg',
      label:'CO₂ estimado',
      value:metrics.co2_kg,
      format:'co2',
      objective:active.has('co2_kg'),
    },
  ];
  return rows.filter(item=>item.value!==null&&item.value!==undefined);
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
        load_kg:0,
        utilization_sum:0,
        utilization_count:0,
        orders:new Set(),
      });
    }
    const group=groups.get(id);
    group.trips+=1;
    group.load_kg+=Number(trip.load_kg||0);
    if(Number.isFinite(Number(trip.utilization))){
      group.utilization_sum+=Number(trip.utilization);
      group.utilization_count+=1;
    }
    for(const orderId of trip.order_ids)group.orders.add(orderId);
  }

  return [...groups.values()].map(group=>({
    id:group.id,
    vehicle_type:group.vehicle_type,
    ownership:group.ownership,
    provider_name:group.provider_name,
    base_site:group.base_site,
    trips:group.trips,
    load_kg:group.load_kg,
    utilization:group.utilization_count?group.utilization_sum/group.utilization_count:null,
    orders:group.orders.size,
    load_share:totalWeight?group.load_kg/totalWeight:null,
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
  const includedAnomalies=(result?.inputs?.anomalies||[]).filter(item=>item?.decision==='include');
  const outsourcedTrips=trips.filter(trip=>trip.ownership==='third_party');
  const splitOrders=orders.filter(order=>order.split);

  if(scenario.feasible===false){
    warnings.push({
      key:'infeasible',
      level:'attention',
      label:'Atención',
      title:'El escenario seleccionado está marcado como no factible',
      detail:'El resultado persistido indica feasible = false. No conviene aprobar esta asignación sin revisar la corrida.',
    });
  }
  if(exceptions.length){
    warnings.push({
      key:'engine_exceptions',
      level:'attention',
      label:'Atención',
      title:`${exceptions.length} observación${exceptions.length===1?'':'es'} publicada${exceptions.length===1?'':'s'} por el motor`,
      detail:'Revisá la evidencia persistida de la corrida antes de aprobar.',
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
      feasible:scenario.feasible!==false,
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
  return COMPARISON_METRICS.map(item=>({...item}));
}

export function compareScenarioMetric(result,referenceKey,metricKey){
  const definition=COMPARISON_METRICS.find(item=>item.key===metricKey);
  const selectedScenario=selected(result);
  const reference=result?.scenarios?.[referenceKey];
  const selectedValue=finiteMetric(selectedScenario?.metrics?.[metricKey]);
  const referenceValue=finiteMetric(reference?.metrics?.[metricKey]);
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
  if(reference.feasible===false){
    return {...base,reason:'La referencia está marcada como no factible'};
  }

  const absolute=selectedValue-referenceValue;
  const percent=referenceValue===0?null:absolute/Math.abs(referenceValue);
  if(Math.abs(absolute)<1e-12){
    return {
      ...base,
      absolute:0,
      percent:0,
      semantic:'same',
      semanticLabel:'Sin cambio',
    };
  }

  const direction=result?.kpi_directions?.[metricKey]||base.fallbackDirection;
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
  return COMPARISON_METRICS.map(metric=>compareScenarioMetric(result,referenceKey,metric.key));
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
    priorities:getObjectiveWeights(result),
  };
}
