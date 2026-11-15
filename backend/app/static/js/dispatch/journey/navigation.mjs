/** Canonical local return targets. Never deserialize an arbitrary URL. */
import {api} from '../shared.mjs';
import {el,button,confirmAction} from '../models/forms.mjs';
export const RETURN_VIEWS=['logistics-map','logistics-config','decision-dashboard','platform-decisions'];
export async function journeyEnabled(scope){const c=await api('/api/platform/ultimate-foundation/capabilities',{signal:scope.signal});window.dationUnifiedJourney=!!c.unified_journey_enabled;return window.dationUnifiedJourney;}
export function origin(route){return {returnView:RETURN_VIEWS.includes(route.view)?route.view:'logistics-map',returnNode:route.nodeId||null,returnRun:route.view==='decision-dashboard'?route.runId:null};}
export async function returnFromCore(route,navigate,scope){
 let view=RETURN_VIEWS.includes(route.returnView)?route.returnView:'logistics-map';
 if(view==='decision-dashboard'&&(!route.returnRun||!route.returnNode))view='logistics-map';
 if(view==='decision-dashboard')try{await api('/api/platform/logistics-cases/'+route.caseId+'/graph?'+new URLSearchParams({run_id:route.returnRun,node_id:route.returnNode}),{signal:scope.signal});}catch(e){if(![403,404].includes(e.status))throw e;view='logistics-map';}
 return navigate(view,{center:view==='platform-decisions'?route.returnCenter||{}:undefined,caseId:view==='platform-decisions'?null:route.caseId,nodeId:['logistics-config','decision-dashboard'].includes(view)?route.returnNode:null,runId:view==='decision-dashboard'?route.returnRun:null,replace:true});
}
export async function editSource(root,scope,route,navigate,{forceDerive=false}={}){
 const data=await api('/api/platform/logistics-cases/'+route.caseId+'/journey',{signal:scope.signal});if(!scope.active)return;
 if(!data.has_runs&&!forceDerive)return navigate('logistics-case-setup',{caseId:route.caseId,coreStep:2,...origin(route)});
 if(!await confirmAction(root,scope,'Crear una nueva planificación',data.has_runs?'Este Decision Case ya tiene una corrida registrada. Para trabajar con otros datos o condiciones sin modificar su historial, Dation preparará un nuevo Case basado en el actual. Se conserva el Case original, las corridas, sus aprobaciones y versiones de datos. Podrás revisar los nuevos archivos y ajustar la configuración antes de crear el nuevo Case.':'La Model Version vinculada es inmutable. Dation preparará un Case derivado para que puedas seleccionar otra versión y revisar sus datos, preservando el Case actual.','Preparar nuevo Decision Case'))return;
 return navigate('logistics-case-setup',{caseId:null,parentCaseId:route.caseId,preparationId:crypto.randomUUID(),coreStep:2,...origin(route)});
}
export function mountStudioRail(root,scope,{route,data,navigate,onEdit}){
 root.classList.add('journey-studio');const layout=el('div',undefined,'journey-studio-layout'),rail=el('nav',undefined,'journey-studio-rail'),content=el('div',undefined,'journey-studio-content');rail.setAttribute('aria-label','Etapas de Decision Studio');rail.append(el('h2','Decision Studio'),el('p','Seleccioná una decisión, configurá su ejecución y evaluá los resultados de tu Case.','d-metadata'));
 const node=data.graph.nodes.find(n=>n.id===route.nodeId)||data.graph.nodes.find(n=>n.id===data.graph.attention_node_id);
 const result=node?.actions.result;
 for(const [i,label,view,target,allowed]of [[4,'Decision Graph','logistics-map',{caseId:route.caseId},true],[5,'Decision Configuration','logistics-config',{caseId:route.caseId,nodeId:node?.id},!!node?.actions.configure.allowed],[6,'Decision Dashboard','decision-dashboard',{caseId:route.caseId,nodeId:route.nodeId||node?.id,runId:route.runId||result?.target?.run_id},!!route.runId||!!result?.allowed]]){
  const b=button('',()=>navigate(view,target));b.append(el('span',String(i),'core-step-number'),el('strong',label),el('small',i===4?'Mapa y requisitos':i===5?'Configurar D1/D2':'Análisis y aprobación'));b.disabled=!allowed;if(!allowed)b.title=i===6?'Todavía no hay una corrida disponible.':'Revisá los requisitos de la decisión en Graph.';if(view===route.view)b.setAttribute('aria-current','step');rail.append(b);
 }
 const edit=button('Editar Decision Case',onEdit);edit.classList.add('journey-studio-edit');edit.disabled=!onEdit;rail.append(el('p',node?.label||'Seleccioná una decisión','d-metadata'),edit);
 for(const child of [...root.childNodes])content.append(child);layout.append(rail,content);root.append(layout);return content;
}
