// Display vocabulary and route adaptation only. Business states/actions come from the server.
export const GRAPH_STATE_UI=Object.freeze({
 LOCKED:{label:'En espera',tone:'waiting',style:'locked',icon:'lock'},
 DATA_REQUIRED:{label:'Requiere datos',tone:'waiting',style:'needs_data',icon:'alertTriangle'},
 READY:{label:'Lista para configurar',tone:'available',style:'available',icon:'checkCircle'},
 IN_PROGRESS:{label:'En ejecución',tone:'running',style:'running',icon:'loader'},
 COMPLETED:{label:'Pendiente de aprobación',tone:'review',style:'review',icon:'clipboardCheck'},
 APPROVED:{label:'Aprobada',tone:'approved',style:'approved',icon:'checkCircle'},
 COMING_SOON:{label:'Próximamente',tone:'waiting',style:'locked',icon:'clock'},
 NOT_APPLICABLE:{label:'No aplica',tone:'waiting',style:'locked',icon:'info'},
});
export function graphStateUi(state){return GRAPH_STATE_UI[state]||{label:'Estado no disponible',tone:'waiting',style:'locked'};}
export function graphTarget(target){return target?{view:target.view,caseId:target.case_id,nodeId:target.node_id,runId:target.run_id}:null;}
export function graphActionLabel(action,node){
 if(action?.target?.view==='logistics-case-data')return 'Completar datos del Case';
 if(action?.target?.view==='decision-dashboard')return 'Abrir corrida';
 return 'Configurar '+node.label;
}
export function graphNodeDescription(node){
 if(node.requirements.length)return node.requirements.map(r=>r.label).join(' · ');
 if(node.blocked_by.length)return 'Requiere la aprobación vigente de Transport Plan.';
 if(node.freshness==='STALE')return 'Cambiaron datos consumidos por esta decisión. El historial se conserva.';
 if(node.technical_failure)return 'La última ejecución registró un error técnico. Los datos publicados se conservan.';
 return graphStateUi(node.node_state).label+'.';
}
