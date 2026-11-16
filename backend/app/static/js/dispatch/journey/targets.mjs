// Presentation targets only: existing resources and server-owned actions.
export const RETURN_VIEWS=['logistics-map','logistics-config','decision-dashboard','platform-decisions'];
const IDS=['caseId','parentCaseId','preparationId','modelId','returnView','returnNode','returnRun'];
export function sameCoreJourney(a,b){return a?.view==='logistics-case-setup'&&b?.view===a.view&&IDS.every(k=>(a[k]||null)===(b[k]||null))&&JSON.stringify(a.returnCenter||{})===JSON.stringify(b.returnCenter||{});}
export function corePrevious(step){return step>1?{local:true,step:step-1,label:step===3?'Data Contract & Preparation':'Logistics Model'}:{local:false,target:{view:'logistics-overview',caseId:null,nodeId:null,runId:null},label:'DDA Logística'};}
export function coreReturn(route){
 const caseId=route.caseId||route.parentCaseId||null;
 const view=RETURN_VIEWS.includes(route.returnView)?route.returnView:caseId?'logistics-map':'logistics-overview';
 if(view==='platform-decisions')return {view,center:route.returnCenter||{},caseId:null,nodeId:null,runId:null};
 if(!caseId)return {view:'logistics-overview',caseId:null,nodeId:null,runId:null};
 if(['logistics-config','decision-dashboard'].includes(view)&&(!route.returnNode||view==='decision-dashboard'&&!route.returnRun))return {view:'logistics-map',caseId,nodeId:null,runId:null};
 return {view,caseId,nodeId:['logistics-config','decision-dashboard'].includes(view)?route.returnNode||null:null,runId:view==='decision-dashboard'?route.returnRun||null:null};
}
export function coreSourceRoute(route){const target=coreReturn(route);return {...route,view:target.view,nodeId:target.nodeId,runId:target.runId,center:target.center};}
export const returnLabel=target=>({'logistics-map':'Volver al Decision Graph','decision-dashboard':'Volver al Dashboard','logistics-config':'Volver a Decision Configuration','platform-decisions':'Volver a Decision Center','logistics-overview':'Volver a DDA Logística'})[target.view];
export function checkedCoreReturn(route,data){
 const target=coreReturn(route),fallback=reason=>({target:{view:'logistics-map',caseId:target.caseId,nodeId:null,runId:null},reason});
 if(['logistics-config','decision-dashboard'].includes(route.returnView)&&target.view!==route.returnView&&target.caseId)return fallback('El enlace de origen no identifica una decisión y corrida válidas. Podés volver al Graph del mismo Case; no se seleccionará otra corrida.');
 if(!['logistics-config','decision-dashboard'].includes(target.view))return {target};
 if(!data||data.case?.id!==target.caseId||data.graph?.case_id!==target.caseId)return fallback('El origen ya no está disponible. Podés volver al Graph del mismo Case; no se seleccionará otra corrida.');
 if(target.view==='decision-dashboard'){
  if(!target.runId||!target.nodeId||data.selected_run?.id!==target.runId||data.selected_run.node_id!==target.nodeId)return fallback('La corrida de origen ya no está disponible. Podés volver al Graph del mismo Case; no se seleccionará la última corrida.');
 }else{
  const a=data.graph.nodes.find(n=>n.id===target.nodeId)?.actions?.configure,t=a?.target;
  if(!a?.allowed||t?.view!==target.view||t.case_id!==target.caseId||t.node_id!==target.nodeId)return fallback('La configuración de origen no está disponible para este acceso o estado. Podés volver al Graph del mismo Case.');
 }
 return {target};
}
export function studioPrevious(route,data){
 const graph={view:'logistics-map',caseId:route.caseId,nodeId:null,runId:null},run=data.selected_run,node=data.graph.nodes.find(n=>n.id===route.nodeId),a=node?.actions?.configure,t=a?.target;
 if(route.view==='decision-dashboard'&&run?.id===route.runId&&run.node_id===route.nodeId&&!run.superseded_at&&node?.run_id===route.runId&&node.freshness==='CURRENT'&&a?.allowed&&t?.view==='logistics-config'&&t.case_id===route.caseId&&t.node_id===route.nodeId)return {view:t.view,caseId:route.caseId,nodeId:route.nodeId,runId:null};
 return graph;
}
