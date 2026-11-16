/** Canonical local return targets. Never deserialize an arbitrary URL. */
import {api} from '../shared.mjs';
import {el,button,confirmAction} from '../models/forms.mjs';
import {createScope} from '../lifecycle.mjs';
import {resourceUrl} from '../navigation/resource.mjs';
import {RETURN_VIEWS,coreReturn,returnLabel,checkedCoreReturn,studioPrevious} from './targets.mjs';
export {RETURN_VIEWS} from './targets.mjs';
export async function journeyEnabled(scope){const c=await api('/api/platform/ultimate-foundation/capabilities',{signal:scope.signal});window.dationUnifiedJourney=!!c.unified_journey_enabled;return window.dationUnifiedJourney;}
export function origin(route){return {returnView:RETURN_VIEWS.includes(route.view)?route.view:'logistics-map',returnNode:route.nodeId||null,returnRun:route.view==='decision-dashboard'?route.runId:null,...(route.view==='platform-decisions'?{returnCenter:route.center||route.returnCenter||{}}:{})};}
export async function returnFromCore(route,navigate,scope,{root}={}){
 const intent=coreReturn(route);let data=null;
 if(['logistics-config','decision-dashboard'].includes(intent.view))try{
  const query=intent.view==='decision-dashboard'?new URLSearchParams({run_id:intent.runId||'',node_id:intent.nodeId||''}):new URLSearchParams();
  if(intent.nodeId&&(intent.view!=='decision-dashboard'||intent.runId))data=await api('/api/platform/logistics-cases/'+intent.caseId+'/graph?'+query,{signal:scope.signal});
 }catch(e){if(![403,404].includes(e.status))throw e;}
 if(!scope.active)return;const {target,reason}=checkedCoreReturn(route,data);
 if(reason&&(!root||!await confirmAction(root,scope,'Origen no disponible',reason,'Volver al Decision Graph')))return;
 if(scope.active)return navigate(target.view,{...target,replace:true});
}
export function mountCoreReturn(header,root,scope,{route,navigate,beforeReturn=()=>{}}){
 const target=coreReturn(route),area=el('div',undefined,'journey-context-return'),link=el('a', '← '+returnLabel(target),'journey-return-link'),note=el('p','','d-metadata');
 link.href=resourceUrl(location.href,target);link.dataset.journeyReturn='';note.role='status';area.append(link,note);header.append(area);let busy=false,request=null;
 const cancel=()=>{request?.dispose();request=null;busy=false;link.removeAttribute('aria-busy');};scope.own(cancel);scope.listen(window,'dation:core-step',cancel);
 scope.listen(link,'click',async event=>{if(event.button||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;event.preventDefault();if(busy)return;busy=true;const own=request=createScope(document.createElement('div'));link.setAttribute('aria-busy','true');note.textContent='';
  try{beforeReturn();await returnFromCore(route,navigate,own,{root});}catch(e){if(scope.active&&own.active){note.textContent=e.message;note.role='alert';}}finally{own.dispose();if(request===own)cancel();}
 });return link;
}
export function mountStudioPrevious(parent,scope,{route,data,navigate,advance=null}){
 const footer=el('footer',undefined,'journey-sequential-footer'),note=el('p','','d-metadata');footer.dataset.journeyFooter='';note.role='status';let target=studioPrevious(route,data),busy=false,unavailable=false;
 const label=()=> '← Anterior · '+(target.view==='logistics-config'?'Decision Configuration':'Decision Graph');
 const previous=button(label(),async()=>{if(busy)return;busy=true;previous.disabled=true;note.textContent='';try{
  if(route.view==='decision-dashboard'&&!unavailable){
   const checked=await api('/api/platform/logistics-cases/'+route.caseId+'/graph?'+new URLSearchParams({run_id:route.runId,node_id:route.nodeId}),{signal:scope.signal});if(!scope.active)return;target=studioPrevious(route,checked);
  }
  if(scope.active)return navigate(target.view,target);
 }catch(e){if(scope.active){note.textContent=e.message;if([403,404].includes(e.status)){target={view:'logistics-map',caseId:route.caseId,nodeId:null,runId:null};previous.textContent=label();unavailable=true;note.textContent='La corrida ya no está disponible. Volvé al Graph del mismo Case.';}}}finally{busy=false;if(scope.active)previous.disabled=false;}});
 previous.dataset.journeyPrevious='';footer.append(previous);if(advance)footer.append(advance);footer.append(note);parent.append(footer);return footer;
}
export async function editSource(root,scope,route,navigate,{forceDerive=false}={}){
 const data=await api('/api/platform/logistics-cases/'+route.caseId+'/journey',{signal:scope.signal});if(!scope.active)return;
 if(!data.has_runs&&!forceDerive)return navigate('logistics-case-setup',{caseId:route.caseId,coreStep:2,...origin(route)});
 if(!await confirmAction(root,scope,'Crear una nueva planificación',data.has_runs?'Este Decision Case ya tiene una corrida registrada. Para trabajar con otros datos o condiciones sin modificar su historial, Dation preparará un nuevo Case basado en el actual. Se conserva el Case original, las corridas, sus aprobaciones y versiones de datos. Podrás revisar los nuevos archivos y ajustar la configuración antes de crear el nuevo Case.':'La Model Version vinculada es inmutable. Dation preparará un Case derivado para que puedas seleccionar otra versión y revisar sus datos, preservando el Case actual.','Preparar nuevo Decision Case'))return;
 return navigate('logistics-case-setup',{caseId:null,parentCaseId:route.caseId,preparationId:crypto.randomUUID(),coreStep:2,...origin(route)});
}
export function mountStudioRail(root,scope,{route,data,navigate,showHeading=true}){
 root.classList.add('journey-studio');const layout=el('div',undefined,'journey-studio-layout'),rail=el('nav',undefined,'journey-studio-rail'),content=el('div',undefined,'journey-studio-content');rail.setAttribute('aria-label','Etapas de Decision Studio');if(showHeading)rail.append(el('h2','Decision Studio'),el('p','Seleccioná una decisión, configurá su ejecución y evaluá los resultados de tu Case.','d-metadata'));
 const node=data.graph.nodes.find(n=>n.id===route.nodeId)||data.graph.nodes.find(n=>n.id===data.graph.attention_node_id);
 const result=node?.actions.result;
 for(const [i,label,view,target,allowed]of [[4,'Decision Graph','logistics-map',{caseId:route.caseId},true],[5,'Decision Configuration','logistics-config',{caseId:route.caseId,nodeId:node?.id},!!node?.actions.configure.allowed],[6,'Decision Dashboard','decision-dashboard',{caseId:route.caseId,nodeId:route.nodeId||node?.id,runId:route.runId||result?.target?.run_id},!!route.runId||!!result?.allowed]]){
  const current=view===route.view,b=button('',current?null:()=>navigate(view,target));const copy=el('span',undefined,'core-step-copy');copy.append(el('strong',label),el('small',i===4?'Mapa y requisitos':i===5?'Configurar D1/D2':'Análisis y aprobación'));b.append(el('span',String(i),'core-step-number'),copy);b.disabled=!allowed;if(!allowed)b.title=i===6?'Todavía no hay una corrida disponible.':'Revisá los requisitos de la decisión en Graph.';b.dataset.journeyStage=view;if(current){b.setAttribute('aria-current','step');b.tabIndex=-1;}rail.append(b);
 }
 for(const child of [...root.childNodes])content.append(child);layout.append(rail,content);root.append(layout);return content;
}
