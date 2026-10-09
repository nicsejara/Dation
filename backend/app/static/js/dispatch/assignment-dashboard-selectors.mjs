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
