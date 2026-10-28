// T5 presents server graph/actions. No readiness or dependency resolver in JS.
import {api,post,errorBox} from '../shared.mjs';
import {scopeFor,createScope} from '../lifecycle.mjs';
import {ensureStylesheet,ensureDecisionCaseStyles} from '../styles.mjs';
import {loadingState} from '../../platform/components.mjs';
import {el,button} from '../models/forms.mjs';
import {heroMarkup,graphNodeMarkup} from './decision-map.mjs';
import {graphStateUi,graphTarget} from '../navigation/ultimate-graph.mjs';
import {openCaseSelector} from '../traceability-ui.mjs';
import {mountResponsibilitySelector} from './workflow-responsibility.mjs';

export async function mountUltimateGraph(root,{route,navigate,onContext}){
 const scope=scopeFor(root);root.append(loadingState('Recuperando mapa de decisiones…'));
 let pickerVersion=0,activePicker=null;const historyVersions=new Map();
 const follow=t=>{const target=graphTarget(t);return target&&navigate(target.view,target);};
 try{
  await ensureDecisionCaseStyles();await ensureStylesheet('ultimate-graph-styles','/static/css/ultimate-graph.css','t5-v1');
  const base='/api/platform/logistics-cases/'+route.caseId,query=new URLSearchParams();
  if(route.runId)query.set('run_id',route.runId);if(route.nodeId)query.set('node_id',route.nodeId);
  let data=await api(base+'/graph?'+query,{signal:scope.signal});if(!scope.active)return;
  const selected=()=>data.graph.nodes.find(n=>n.id===route.nodeId);
  if(route.view==='logistics-config'&&selected()?.actions.configure.allowed){data=await api(base+'/graph/config/'+route.nodeId,{signal:scope.signal});if(!scope.active)return;}
  onContext?.(data.case,data.graph);
  root.className='dispatch dispatch-upload-pro dispatch-decision-map dispatch-decision-map--premium dispatch-decision-map--case-v2 ultimate-graph-view';root.innerHTML=heroMarkup(data.case);
  const actions=el('div',undefined,'t5-actions'),context=el('section',undefined,'d-card t5-context');
  const map=()=>navigate('logistics-map',{caseId:route.caseId,nodeId:null,runId:null});
  actions.append(button('Mapa de decisiones',map),button('Datos del Case',()=>navigate('logistics-case-data',{caseId:route.caseId,nodeId:null,runId:null})),button('Contexto del Case',()=>navigate('logistics-case-setup',{caseId:route.caseId,nodeId:null,runId:null})));
  const choose=button('Seleccionar Decision Case',()=>picker(0,choose));actions.append(choose);root.append(actions);
  context.append(el('h2',data.case.label,'d-card-title'),el('p',data.model.name+' · '+data.case.planning_start+' a '+data.case.planning_end,'d-body'),el('p','Pack versión '+data.pack_version.version+' · '+data.graph.approved_count+' de '+data.graph.nodes.length+' decisiones aprobadas.','d-metadata'));root.append(context);
  if(route.view==='logistics-map'){
   const owner=el('div');context.append(owner);mountResponsibilitySelector(owner,{caseId:route.caseId,stageKey:'data_owner',snapshot:data.responsibilities,onSaved:map});
  }
  if(data.case.status==='archived')root.append(el('p','Case archivado. El historial permanece disponible en modo de lectura.','t5-readonly'));
  async function picker(offset,trigger){
   const own=++pickerVersion;
   try{
    const list=await api('/api/platform/decisions?'+new URLSearchParams({dda:'logistics',limit:25,offset}),{signal:scope.signal});if(!scope.active||own!==pickerVersion)return;
    activePicker?.close();
    const child=createScope(document.createElement('div'));scope.own(()=>child.dispose());
    const dialog=openCaseSelector(list.items.map(item=>({case:item,graph:item.graph,decision_case:{nodes:{}},orders:item.orders,fleet:item.fleet})),{scope:child,trigger,currentCaseId:route.caseId,onSelect:id=>navigate('logistics-map',{caseId:id,nodeId:null,runId:null})});
    activePicker=dialog;
    dialog.querySelector('.dispatch-case-selector__summary strong').textContent=list.total+' casos · página '+(offset/25+1);
    const controls=el('div',undefined,'t5-actions'),previous=button('Página anterior',()=>{dialog.close();picker(offset-25,trigger);}),next=button('Página siguiente',()=>{dialog.close();picker(offset+25,trigger);});previous.disabled=offset===0;next.disabled=offset+25>=list.total;controls.append(previous,next);dialog.querySelector('.dispatch-trace-shell').append(controls);
   }catch(error){if(scope.active)context.append(el('p',error.message,'d-body'));}
  }
  if(route.view==='logistics-map'){
   const chain=el('section',undefined,'dispatch-map-chain-section dispatch-map-chain-section--open');chain.append(el('h2','Decisiones del Case'));
   const list=el('div',undefined,'dispatch-node-map');list.setAttribute('aria-label','Cadena de decisiones');chain.append(list);root.append(chain);
   for(const [index,node]of data.graph.nodes.entries()){
    const host=el('section',undefined,'t5-node');host.dataset.graphNode=node.id;host.dataset.nodeState=node.node_state;host.innerHTML=graphNodeMarkup(node,index);list.append(host);
    const owners=el('section',undefined,'workflow-map-responsibilities'),owner=el('div');owners.setAttribute('aria-label','Responsables de '+node.label);owners.append(owner);host.querySelector('article').append(owners);
    mountResponsibilitySelector(owner,{caseId:route.caseId,stageKey:node.id,snapshot:data.responsibilities,onSaved:map});
    for(const b of host.querySelectorAll('[data-map-action]'))scope.listen(b,'click',()=>follow(node.primary_action.target));
    const extra=el('div',undefined,'t5-node-extra');
    const reasons=node.actions.configure.reasons||[];if(reasons.length)extra.append(el('p',reasons.includes('DATA_OWNER_REQUIRED')?'Asigná un Data Owner activo en este Map.':reasons.includes('DECISION_OWNER_REQUIRED')?'Asigná un Decision Owner activo en este Map.':'Acceso de sólo lectura para esta decisión.','d-metadata'));
    extra.append(button('Historial de '+node.label,()=>history(node,extra,0)));host.append(extra);
    if(index<data.graph.nodes.length-1){const edge=el('div','↓','t5-edge');edge.setAttribute('aria-hidden','true');list.append(edge);}
   }
  }else if(route.view==='logistics-config'){
   const node=selected();if(!node)throw new Error('Seleccioná una decisión desde el Map.');
   const panel=el('section',undefined,'d-card t5-context');panel.dataset.graphConfig=node.id;panel.append(el('h2','Configurar '+node.label,'d-card-title'),el('p',graphStateUi(node.node_state).label,'d-body'));
   if(data.configuration_context){panel.append(el('p','Objetivo y reglas: los del contexto guardado del Case.','d-body'));if(data.configuration_context.upstream_run_id)panel.append(el('p','Upstream aprobado: '+data.configuration_context.upstream_run_id,'d-metadata'));}
   else panel.append(el('p','La configuración no está habilitada para este acceso o contexto. Revisá el Map y los responsables.','d-body'));
   const status=el('p','La ejecución de esta decisión todavía no está disponible.','d-body');status.setAttribute('role','status');
   const execute=button('Ejecutar decisión',null,'primary');execute.disabled=true;panel.append(status,execute);root.append(panel);
   // Graph readiness permits configuration. T8/T9 run-context is the checked
   // authority for admission; the earlier graph capability projection is not.
   if(node.actions.configure.allowed){
    status.textContent='Recuperando el contexto publicado para ejecutar…';
    try{
     const configured=await api(base+'/run-context?'+new URLSearchParams({node_id:node.id}),{signal:scope.signal});
     if(!scope.active)return;
     execute.disabled=!configured.admission_available;
     status.textContent=configured.admission_available?'La ejecución usará el Model, Pack y reglas publicados de este Case.':'La admisión de nuevas corridas no está habilitada.';
     let intention=null,pending=false;
     scope.listen(execute,'click',async()=>{
      if(pending||execute.disabled)return;
      if(!intention){
       const request={request_schema:'ultimate_run_request_v1',workflow_version:2,case_id:route.caseId,node_id:node.id,
        expected_context_hash:configured.expected_context_hash,model_version_id:configured.model_version_id,
        data_pack_version_id:configured.data_pack_version_id,node_policy:configured.node_policy};
       if(node.id==='logistics_scheduling')request.source_transport_plan=configured.source_transport_plan;
       intention={runId:crypto.randomUUID(),request};
      }
      const restoreFocus=document.activeElement===execute;let failed=false;
      pending=true;execute.disabled=true;execute.setAttribute('aria-busy','true');status.setAttribute('role','status');status.textContent='Creando la corrida con el contexto guardado…';
      try{
       // A retry after a lost response keeps the exact UUID and frozen body.
       // All permissions/freshness/lineage rules remain in checked admission.
       const run=await post('/api/runs?'+new URLSearchParams({run_id:intention.runId}),intention.request,{signal:scope.signal});
       if(scope.active)navigate('decision-dashboard',{caseId:route.caseId,nodeId:node.id,runId:run.id});
      }catch(error){
       failed=true;
       if(scope.active){status.textContent=error.message||'No se pudo confirmar la corrida. Reintentá la misma intención.';status.setAttribute('role','alert');}
      }finally{pending=false;if(scope.active){execute.disabled=!configured.admission_available;execute.removeAttribute('aria-busy');if(failed&&restoreFocus&&(document.activeElement===document.body||document.activeElement===execute))execute.focus({preventScroll:true});}}
     });
    }catch(error){if(scope.active){status.textContent=error.message;status.setAttribute('role','alert');}}
   }
  }else if(route.view==='decision-dashboard'){
   const run=data.selected_run;if(!run||run.id!==route.runId)throw new Error('La corrida solicitada no pertenece a este contexto.');
   const node=selected(),panel=el('section',undefined,'d-card t5-context');panel.dataset.graphHistoricalRun=run.id;
   panel.append(el('h2','Corrida '+run.id,'d-card-title'),el('p','Estado de la ejecución: '+run.status,'d-body'),el('p',run.approved_at?'Aprobación registrada: '+run.approved_at:'Sin aprobación registrada.','d-metadata'),el('p',run.superseded_at?'La corrida fue reemplazada; su historial se conserva.':'La selección histórica no modifica el Map actual.','d-metadata'));
   if(run.upstream_run_id)panel.append(el('p','Upstream: '+run.upstream_run_id,'d-metadata'));
   panel.append(el('p','La visualización del resultado de esta decisión todavía no está disponible.','d-body'));
   if(node){const rerun=button('Nueva corrida · '+node.label,()=>follow(node.actions.new_run.target),'primary');rerun.disabled=!node.actions.new_run.allowed;panel.append(rerun);}root.append(panel);
  }
  async function history(node,parent,offset){
   const own=(historyVersions.get(node.id)||0)+1;historyVersions.set(node.id,own);
   try{
    const data=await api(base+'/graph/history/'+node.id+'?'+new URLSearchParams({limit:25,offset}),{signal:scope.signal});if(!scope.active||own!==historyVersions.get(node.id))return;
    let section=parent.querySelector('[data-t5-history]');if(!section){section=el('section',undefined,'d-card t5-context');section.dataset.t5History='';parent.append(section);}section.replaceChildren(el('h3','Historial de '+node.label,'d-card-title'));
    for(const run of data.items){const row=el('div',undefined,'t5-history-row');row.append(el('p',run.id+' · '+run.status+(run.approved_at?' · aprobación registrada':'')+(run.superseded_at?' · reemplazada':''),'d-body'),button('Abrir corrida '+run.id.slice(0,8),()=>navigate('decision-dashboard',{caseId:route.caseId,nodeId:node.id,runId:run.id})));section.append(row);}
    if(!data.items.length)section.append(el('p','Todavía no hay corridas registradas.','d-metadata'));
    const paging=el('div',undefined,'t5-actions'),back=button('Corridas anteriores',()=>history(node,parent,offset+25)),previous=button('Volver a corridas recientes',()=>history(node,parent,offset-25));back.disabled=offset+25>=data.total;previous.disabled=offset===0;paging.append(previous,back);section.append(paging);
   }catch(error){if(scope.active)parent.append(el('p',error.message,'d-body'));}
  }
  root.dataset.ultimateReady='true';root.dataset.graphReady='true';
 }catch(error){if(scope.active)errorBox(root,error,()=>navigate('logistics-map',{caseId:route.caseId,nodeId:null,runId:null,replace:true}));}
}
