import {createScope,scopeFor} from './lifecycle.mjs';
import {api} from './shared.mjs';
import {DECISION_META} from './decision-ui.mjs';
import {mountCaseSwitcher} from './case-switcher.mjs';
import {mountResponsibilitySelector,executionPermission} from './workflow-responsibility.mjs';
import {configurationAvailable} from './decision-target.mjs';

const mounted=new WeakMap(),actors=new Map(),dataDrafts=new WeakMap();
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
export function mountWorkflowContext(root,{state,stageKey,field='owner',showCase=true,onSaved,onPrepare}){
 const data=stageKey==='data_preparation',current=state.decisionCase;
 let drafts;
 if(data){
  drafts=dataDrafts.get(state);
  if(!drafts||drafts.caseId&&drafts.caseId!==current?.id){drafts={caseId:current?.id,roles:{data_owner:{}}};dataDrafts.set(state,drafts);}
  drafts.caseId=current?.id;
  for(const key of ['data_owner'])drafts.roles[key].restoreFocus=Boolean(root.querySelector('[data-workflow-responsibility="'+key+'"]')?.contains(document.activeElement));
 }
 mounted.get(root)?.dispose();
 if(!data&&!current?.id)return;
 const host=el('section',undefined,'workflow-context');host.setAttribute('aria-label',data?'Responsables del Data Pack':'Contexto del Decision Case');
 const anchor=data?root.querySelector('.dispatch-pro-compatibility'):root.querySelector('.d-page-hero');if(anchor)anchor.after(host);else root.prepend(host);
 const scope=createScope(host);mounted.set(root,scope);scope.own(()=>{host.remove();if(mounted.get(root)===scope)mounted.delete(root);});
 if(showCase&&current?.id){const switcher=el('div');host.append(switcher);const view=mountCaseSwitcher(switcher,{decisionCase:current,context:state.caseContext});scope.own(()=>view?.dispose());}
 if(data){
  const snapshot=state.workflow||{stages:{},pending:true,can_assign:window.dationSession?.identity?.membership?.access_role==='admin',can_prepare:window.dationSession?.identity?.membership?.access_role!=='viewer'};
  host.append(el('h2','Data Owner del Case','d-card-title'));
  if(!state.preflight?.valid)host.append(el('p','Las asignaciones se guardan en el Decision Case después de validar Órdenes y Flota.','d-metadata'));
  function dataSaved(key,result){
   if(!scope.active)return;state.workflow=result;onSaved?.(result);
   mountWorkflowContext(root,{state,stageKey,field,showCase,onSaved,onPrepare});
   root.querySelector('[data-workflow-responsibility="'+key+'"] button')?.focus({preventScroll:true});
  }
  for(const key of ['data_owner']){const selector=el('div');host.append(selector);const child=mountResponsibilitySelector(selector,{caseId:current?.id,stageKey:key,snapshot,draft:drafts.roles[key],onPrepare:key==='data_owner'||snapshot.can_assign?onPrepare:null,canSave:()=>Boolean(state.preflight?.valid),onSaved:result=>dataSaved(key,result)});scope.own(()=>child.dispose());}
 }else if(stageKey){
  const stage=state.workflow?.stages?.[stageKey]||{},info=el('div',undefined,'workflow-responsibility workflow-responsibility--readonly');
  if(field==='owner'){
   info.id='workflow-responsibility';
   info.append(el('p','Decision Owner: '+(stage.owner?.name||'Sin asignar'),'d-body'));
   if(executionPermission())info.append(el('p',executionPermission(),'d-metadata'));
   if(!stage.owner_eligible){const link=el('button','Ir al Mapa para asignar responsables','d-button d-button--secondary');link.type='button';link.addEventListener('click',()=>window.DationDispatch.openCase(current.id));info.append(link);}
  }
  host.append(info);
 }
 return {scope,host,dispose:()=>scope.dispose()};
}

export function mountMapResponsibilities(root,{state,onSaved}){
 const scope=scopeFor(root)||createScope(root);
 for(const stageKey of Object.keys(DECISION_META).filter(key=>DECISION_META[key].implemented)){
  const card=root.querySelector('article[data-decision-node="'+stageKey+'"]');if(!card)continue;
  for(const action of card.querySelectorAll('[data-map-action="configure"]')){
   action.disabled=!configurationAvailable(stageKey,state.decisionCase,state.workflow);
   if(action.disabled)action.title='Asigná el Decision Owner y completá las decisiones anteriores para configurar.';
  }
  card.removeAttribute('aria-disabled');
  const group=el('section',undefined,'workflow-map-responsibilities');group.setAttribute('aria-label','Responsables de '+DECISION_META[stageKey].label);card.append(group);
  for(const field of ['owner']){const selector=el('div');group.append(selector);const child=mountResponsibilitySelector(selector,{caseId:state.decisionCase.id,stageKey,field,snapshot:state.workflow,onSaved:result=>{if(scope.active){state.workflow=result;onSaved?.(result);}}});scope.own(()=>child.dispose());}
 }
 return scope;
}

export function mountDashboardTrace(root,{state,run,nodeId}){
 const hero=root.querySelector('#dispatch-hero,.d-page-hero');if(!hero)return;
 hero.classList.add('has-decision-trace');
 const host=el('aside',undefined,'dashboard-hero-trace');host.setAttribute('aria-label','Trazabilidad de la decisión');hero.append(host);
 const scope=createScope(host),context={host,scope,dispose:()=>scope.dispose()},trace=el('dl');trace.dataset.runTrace='';host.append(trace);
 const assigned=state.workflow?.stages?.[nodeId]?.owner;
 const key=[state.decisionCase.id,run.id,run.approved_by_user_id,run.approved_at].join(':');
 const draw=people=>{if(!scope.active)return;trace.replaceChildren();
  for(const [label,value] of [
   [run.approved_at?'Aprobado por':'Pendiente de aprobación',run.approved_at?(people?.approved_by?.name||(run.approved_by==='shared_workspace:dation'?'Workspace compartido (histórico)':'Sin registro de aprobación')):assigned?.name||'Sin asignar'],
  ]){const row=el('div');row.append(el('dt',label),el('dd',value));trace.append(row);}
 };
 draw(actors.get(key));
 if(actors.has(key))return context;
 api('/api/platform/decisions/'+state.decisionCase.id+'/runs?'+new URLSearchParams({node_id:nodeId,run_id:run.id,limit:1}),{signal:scope.signal}).then(detail=>{
  if(!scope.active)return;const person=detail.items?.find(r=>r.id===run.id);
  if(person){actors.set(key,person);if(actors.size>20)actors.delete(actors.keys().next().value);}draw(person);
 }).catch(error=>{if(scope.active&&!scope.signal.aborted){const note=el('p','No pudimos recuperar los nombres de trazabilidad.','d-metadata');note.role='status';trace.append(note);}});
 return context;
}

/** Backend stages only; this indicator deliberately has no numeric progress. */
export function executionStageLabel(stage){
 const labels={registering:'Registrando la corrida',recovering:'Recuperando la corrida',queued:'En cola de ejecución',running:'Ejecutando motor',validating:'Validando datos y configuración',constructing:'Preparando la solución',summarizing:'Generando la recomendación'};
 return (String(stage).startsWith('optimizing:')?'Ejecutando motor':labels[stage]||String(stage||'Ejecución en curso')).toLocaleUpperCase('es');
}
export function renderExecutionProgress(root,stage){
 let panel=root.querySelector('[data-execution-progress]');
 if(!panel){
  panel=el('section',undefined,'dispatch-panel decision-execution');panel.dataset.executionProgress='';
  panel.append(el('span','EJECUCIÓN EN CURSO','dispatch-kicker'),el('h1','Preparando tu decisión'));
  const status=el('p',undefined,'decision-execution__stage');status.dataset.runStage='';status.setAttribute('role','status');status.setAttribute('aria-live','polite');panel.append(status);
  const bar=el('div',undefined,'decision-execution__progress');bar.setAttribute('role','progressbar');bar.setAttribute('aria-label','Ejecución en curso');bar.append(el('span'));panel.append(bar);
  panel.append(el('p','La corrida sigue activa. Podés recuperarla en este mismo Case si recargás la página.','d-metadata'));root.replaceChildren(panel);
 }
 const label=executionStageLabel(stage),status=panel.querySelector('[data-run-stage]');
 if(status.textContent!==label)status.textContent=label;
 panel.querySelector('[role=progressbar]').setAttribute('aria-valuetext',label);
}
