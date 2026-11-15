// Presentation only. Targets and permissions remain server-owned.
export const IMPLEMENTED = new Set(['logistics_assignment','logistics_scheduling']);
export function visualState(node){
 if(node.node_state==='APPROVED'&&node.freshness==='CURRENT'&&node.approved_run_id&&!node.technical_failure)return {label:'Aprobada',tone:'approved',detail:'Aprobación vigente'};
 if(node.node_state==='NOT_APPLICABLE')return {label:'Bloqueada',tone:'blocked',detail:'No requiere planificación en este Case'};
 if(node.node_state==='COMING_SOON')return {label:'Bloqueada',tone:'blocked',detail:'Capacidad futura, no disponible'};
 if(node.node_state==='LOCKED')return {label:'Bloqueada',tone:'blocked',detail:'Requiere aprobación vigente de D1'};
 const detail=node.freshness==='STALE'?'Resultado desactualizado':node.technical_failure?'La última corrida registró un error técnico':({READY:'Disponible para configurar',DATA_REQUIRED:'Requiere completar datos',IN_PROGRESS:'Corrida en cola o ejecutándose',COMPLETED:'Resultado a revisar',APPROVED:'Aprobación no vigente'})[node.node_state]||'Estado técnico no reconocido; revisá los requisitos';
 return {label:'Pendiente',tone:'pending',detail};
}
export function dependencyActive(first,second){return !!first&&!!second&&visualState(first).tone==='approved'&&second.upstream_run_id===first.approved_run_id;}
export function checkedTarget(action,caseId,nodeId){
 const t=action?.target;
 if(!action?.allowed||!t||t.case_id!==caseId||t.node_id!==nodeId)return null;
 if(t.view==='logistics-config')return {view:t.view,caseId,nodeId,runId:null};
 if(t.view==='decision-dashboard'&&t.run_id)return {view:t.view,caseId,nodeId,runId:t.run_id};
 return null;
}
export function possibleActions(node,caseId,{archived=false,canApprove=false}={}){
 const result=checkedTarget(node.actions?.result,caseId,node.id),configure=checkedTarget(node.actions?.configure,caseId,node.id),again=checkedTarget(node.actions?.new_run,caseId,node.id);
 let primary=null;const secondary=[];
 if(result?.view==='decision-dashboard'&&!['LOCKED','NOT_APPLICABLE','COMING_SOON'].includes(node.node_state)){const current=node.freshness==='CURRENT'&&!node.technical_failure;
  const label=node.node_state==='IN_PROGRESS'?'Ver ejecución':node.node_state==='COMPLETED'&&current?(canApprove?'Ver resultados y aprobar':'Ver resultados'):current?'Ver dashboard':'Ver dashboard histórico';primary={label,target:result,kind:'result'};
 }else if(configure?.view==='logistics-config'&&!archived&&!['LOCKED','NOT_APPLICABLE','COMING_SOON'].includes(node.node_state))primary={label:'Configurar y ejecutar',target:configure,kind:'configure'};
 if(again?.view==='logistics-config'&&!archived&&primary?.kind!=='configure'&&!['LOCKED','NOT_APPLICABLE','COMING_SOON'].includes(node.node_state))secondary.push({label:'Nueva corrida',target:again,kind:'new_run'});
 return {primary,secondary};
}
const REASONS={READ_ONLY:'Tu acceso es de sólo lectura.',ARCHIVED_CASE:'El Case está archivado.',DATA_OWNER_REQUIRED:'Asigná un Data Owner activo desde Core02.',DECISION_OWNER_REQUIRED:'Asigná un Decision Owner activo y elegible.'};
export function requirements(node){
 return [...(node.requirements||[]).map(r=>r.label||r.code),...(node.actions?.configure?.reasons||[]).map(r=>REASONS[r]||r),...(node.stale_reasons||[]).map(()=> 'El contexto consumido cambió; se conserva el historial.'),...(node.technical_failure?['Error técnico: '+node.technical_failure]:[])].filter(Boolean);
}
