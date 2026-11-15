import {api,post} from '../shared.mjs';
import {createScope} from '../lifecycle.mjs';
import {el,button,confirmAction,pageHeader} from '../models/forms.mjs';
import {mountStudioRail,editSource,origin} from '../journey/navigation.mjs';
import {openCaseSelector} from '../traceability-ui.mjs';
import {renderToolbar} from './command-toolbar.mjs';
import {renderNodes} from './node-graph.mjs';
import {contextualPanel,decisionContent} from './decision-popover.mjs';
import {renderSummary} from './core-summary.mjs';
import {possibleActions,IMPLEMENTED} from './status-presentation.mjs';

export async function mountCommandCenter(root,{scope,route,data,journey,navigate,onContext}){
 const base='/api/platform/logistics-cases/'+encodeURIComponent(route.caseId);
 const ownerDrafts=new Map();
 let pack,selected=null,panelView=null,viewScope,buttons=new Map(),slot,notice,chooseTrigger,refreshVersion=0,pickerVersion=0,pickerDialog=null,pickerRequest=null;
 async function read(signal=scope.signal){
  const [graph,nextJourney,nextPack]=await Promise.all([api(base+'/graph',{signal}),api(base+'/journey',{signal}),api(base+'/data',{signal}).catch(e=>{if([403,404].includes(e.status))return {unavailable:true};throw e;})]);
  if(graph.case.id!==route.caseId||graph.graph.case_id!==route.caseId)throw new Error('El Graph no pertenece al Case seleccionado.');
  return {data:graph,journey:nextJourney,pack:nextPack};
 }
 function error(message,retry){if(!scope.active||!notice?.isConnected)return;notice.replaceChildren(el('p',message));notice.setAttribute('role','alert');if(retry)notice.append(button('Reintentar',retry));}
 async function refresh(keep=selected){
  const own=++refreshVersion;root.setAttribute('aria-busy','true');
   try{const next=await read();if(!scope.active||own!==refreshVersion)return;({data,journey,pack}=next);render();}
  catch(e){if(scope.active&&own===refreshVersion)error(e.message,()=>refresh(keep));}
  finally{if(scope.active&&own===refreshVersion)root.removeAttribute('aria-busy');}
 }
 function clearPanel({restoreFocus=false}={}){panelView?.close({restoreFocus});panelView=null;selected=null;}
 function cancelPicker(){pickerVersion++;pickerRequest?.abort();pickerRequest=null;}
 function openNode(id){
  cancelPicker();
  const node=data.graph.nodes.find(n=>n.id===id&&n.implemented&&IMPLEMENTED.has(n.id));if(!node)return;
  clearPanel();selected=id;
  const trigger=buttons.get(id);panelView=contextualPanel(slot,viewScope,{trigger,title:(id==='logistics_assignment'?'D1':'D2')+' · '+node.label,onClose:()=>{selected=null;panelView=null;}});
  const align=()=>{if(!panelView?.scope.active||selected!==id)return;const a=trigger.getBoundingClientRect(),b=slot.getBoundingClientRect();panelView.panel.style.setProperty('--ux05-caret',Math.max(24,Math.min(b.width-24,a.left+a.width/2-b.left))+'px');};panelView.scope.observe(new ResizeObserver(align),slot);align();
  if(!ownerDrafts.has(id))ownerDrafts.set(id,{});
  decisionContent(panelView.panel,node,{data,journey,scope:panelView.scope,ownerDraft:ownerDrafts.get(id),onPrepare:()=>editSource(root,scope,route,navigate),onOwnerSaved:()=>refresh(id),onAction:a=>followAction(id,a),onHistory:()=>history(id,0)});
  panelView.focus();
 }
 async function followAction(id,expected){
  const active=panelView;if(!active?.scope.active)return;
  try{
   const next=await read(active.scope.signal);if(!scope.active||!active.scope.active)return;const node=next.data.graph.nodes.find(n=>n.id===id);
   const choices=node?possibleActions(node,route.caseId,{archived:next.data.case.status==='archived',canApprove:!!next.data.responsibilities?.stages?.[id]?.can_approve}):{secondary:[]};
   const actual=[choices.primary,...choices.secondary].find(a=>a?.kind===expected.kind);
   if(!actual||JSON.stringify(actual.target)!==JSON.stringify(expected.target)){({data,journey,pack}=next);selected=id;render();error('El contexto cambió. Revisá las acciones disponibles.');return;}
   return navigate(actual.target.view,actual.target);
  }catch(e){if(active.scope.active)error(e.message,()=>refresh(id));}
 }
 async function history(id,offset){
  const active=panelView;if(!active?.scope.active||selected!==id)return;
  let host=active.panel.querySelector('[data-ux05-history-view]');if(!host){host=el('section',undefined,'ux05-history');host.dataset.ux05HistoryView='';active.panel.append(host);}
  host.replaceChildren(el('p','Recuperando historial…'));const own=host.dataset.request=String(Number(host.dataset.request||0)+1);
  try{
   const list=await api(base+'/graph/history/'+encodeURIComponent(id)+'?'+new URLSearchParams({limit:25,offset}),{signal:active.scope.signal});if(!active.scope.active||selected!==id||host.dataset.request!==own)return;
   host.replaceChildren(el('h3','Historial de '+data.graph.nodes.find(n=>n.id===id).label));
   for(const run of list.items){const row=el('div',undefined,'ux05-history-row'),open=button('Abrir corrida '+run.id.slice(0,8),async()=>{
    try{const checked=await api(base+'/graph?'+new URLSearchParams({node_id:id,run_id:run.id}),{signal:active.scope.signal});if(!active.scope.active)return;if(checked.case.id!==route.caseId||checked.selected_run?.id!==run.id)throw new Error('La corrida no pertenece a este contexto.');navigate('decision-dashboard',{caseId:route.caseId,nodeId:id,runId:run.id});}catch(e){if(active.scope.active)error(e.message);}
   });row.append(el('span',run.id+' · '+run.status+(run.approved_at?' · aprobación registrada':'')+(run.superseded_at?' · reemplazada':'')),open);host.append(row);}
   if(!list.items.length)host.append(el('p','Todavía no hay corridas registradas.'));
   const page=el('div',undefined,'ux05-paging'),previous=button('Volver a corridas recientes',()=>history(id,offset-25)),next=button('Corridas anteriores',()=>history(id,offset+25));previous.disabled=offset===0;next.disabled=offset+25>=list.total;page.append(previous,next);host.append(page);
  }catch(e){if(active.scope.active){host.replaceChildren(el('p',e.message));host.append(button('Reintentar historial',()=>history(id,offset)));}}
 }
 async function choose(offset=0){
  cancelPicker();const own=pickerVersion,request=pickerRequest=new AbortController(),release=scope.own(()=>request.abort());
  try{
   const list=await api('/api/platform/decisions?'+new URLSearchParams({dda:'logistics',limit:25,offset}),{signal:request.signal});if(!scope.active||own!==pickerVersion)return;
   pickerDialog?.close();clearPanel();const child=createScope(document.createElement('div'));scope.own(()=>child.dispose());
   const dialog=openCaseSelector(list.items.map(item=>({case:item,graph:item.graph,decision_case:{nodes:{}},orders:item.orders,fleet:item.fleet})),{scope:child,trigger:chooseTrigger,currentCaseId:route.caseId,onSelect:id=>navigate('logistics-map',{caseId:id,nodeId:null,runId:null})});pickerDialog=dialog;
   dialog.querySelector('.dispatch-case-selector__summary strong').textContent=list.total+' casos · página '+(offset/25+1);
   const paging=el('div',undefined,'ux05-paging'),previous=button('Página anterior',()=>{dialog.close();choose(offset-25);}),next=button('Página siguiente',()=>{dialog.close();choose(offset+25);});previous.disabled=offset===0;next.disabled=offset+25>=list.total;paging.append(previous,next);dialog.querySelector('.dispatch-trace-shell').append(paging);
  }catch(e){if(!request.signal.aborted)error(e.message,()=>choose(offset));}
  finally{release();if(pickerRequest===request)pickerRequest=null;}
 }
 async function summary(trigger){
  cancelPicker();clearPanel();const current=panelView=contextualPanel(slot,viewScope,{trigger,title:'Resumen Core Configuration',id:'ux05-core-summary',onClose:()=>{panelView=null;}});current.panel.append(el('p','Recuperando contexto publicado…'));current.focus();
  try{const context=await api(base+'/context',{signal:current.scope.signal});if(!current.scope.active)return;current.panel.lastElementChild.remove();renderSummary(current.panel,context,pack,data.responsibilities);}
  catch(e){if(current.scope.active){current.panel.lastElementChild.textContent=e.message;current.panel.append(button('Reintentar resumen',()=>summary(trigger)));}}
 }
 let closing=false;
 async function closeCase(){
  if(closing)return;cancelPicker();closing=true;
  try{
   const checked=await api(base+'/journey',{signal:scope.signal});if(!scope.active)return;
   if(!checked.can_close){await refresh();error(checked.reason||'El cierre no está disponible.');return;}
   if(!await confirmAction(root,scope,'Cerrar Decision Case','Se conservarán el Case, sus corridas, aprobaciones y datos. El servidor volverá a verificar su vigencia y que no haya trabajo pendiente.','Cerrar Decision Case'))return;
   const latest=await api(base+'/journey',{signal:scope.signal});if(!scope.active)return;
   if(!latest.can_close||latest.token!==checked.token){await refresh();error('El contexto cambió. Volvé a revisar el cierre.');return;}
   await post(base+'/close',{token:latest.token},{signal:scope.signal});if(scope.active)navigate('platform-decisions',{caseId:null,nodeId:null,runId:null});
  }catch(e){if(scope.active){await refresh();error(e.message);}}finally{closing=false;}
 }
 function render(){
  const keep=selected;viewScope?.dispose();panelView=null;root.replaceChildren();root.className='dispatch ultimate-graph-view ux05-command-center';
  pageHeader(root,'Decision Studio','Supervisá el estado del Case, navegá las decisiones y accedé a su configuración y análisis.');
  const body=el('div');root.append(body);viewScope=createScope(body);scope.own(()=>viewScope?.dispose());
  const content=mountStudioRail(body,viewScope,{route,data,navigate,showHeading:false,showEdit:false});
  const toolbar=el('section',undefined,'ux05-case-toolbar');toolbar.setAttribute('aria-label','Control del Decision Case');content.append(toolbar);
  renderToolbar(toolbar,{data,journey,pack},{choose:()=>choose(),setChoose:b=>{chooseTrigger=b;},editSource:()=>editSource(root,scope,route,navigate),editCase:()=>navigate('logistics-case-setup',{caseId:route.caseId,coreStep:3,...origin(route)}),summary:event=>summary(event.currentTarget),close:closeCase});
  notice=el('div',undefined,'ux05-notice');content.append(notice);
  const region=el('section',undefined,'ux05-graph');region.setAttribute('aria-label','Decision Graph');const canvas=el('div',undefined,'ux05-canvas');slot=el('div',undefined,'ux05-panel-slot');region.append(canvas,slot);content.append(region);
  buttons=renderNodes(canvas,data.graph,openNode,viewScope);onContext?.(data.case,data.graph);root.dataset.ultimateReady='true';root.dataset.graphReady='true';root.dataset.ux05Ready='true';
  if(keep&&buttons.has(keep))openNode(keep);
 }
 pack=await api(base+'/data',{signal:scope.signal}).catch(e=>{if([403,404].includes(e.status))return {unavailable:true};throw e;});if(!scope.active)return;render();
 scope.own(()=>{refreshVersion++;cancelPicker();pickerDialog?.close();viewScope?.dispose();});
}
