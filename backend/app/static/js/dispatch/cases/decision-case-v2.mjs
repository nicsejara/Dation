import {api,post} from '../shared.mjs';
import {ensureStylesheet} from '../styles.mjs';
import {el,button,collapsibleSection,confirmAction,field} from '../models/forms.mjs';
import {browserIdentity,workingCopies,lockWorkingCopy,rememberReturn} from '../models/model-library-state.mjs';
import {mountDataContractView} from '../models/data-contract-view.mjs';
import {mountCorePreparation} from '../upload/core-preparation.mjs';
import {mountCaseData} from '../upload/ultimate-case-data.mjs';
import {mountPublishedReview} from '../models/model-published-review.mjs';
import {flattenCorePanel} from '../models/wizard-ui.mjs';
import {disposeScope} from '../lifecycle.mjs';
import {returnFromCore} from '../journey/navigation.mjs';
import {caseRoute,newCaseDraft,fromDefinition,creationBody} from './case-v2-state.mjs';
import {caseShell,caseFooter,definitionFacts,readPair,dirtyChoice} from './case-v2-ui.mjs';
import {mountCaseV2Editor} from './case-v2-editor.mjs';
import {mountResponsibilitySelector} from './workflow-responsibility.mjs';
import {mountCaseAcceptance} from './case-v2-acceptance.mjs';

export async function mountDecisionCaseV2(root,{route,navigate,onContext,caps,current,sourceParent,scope}){
 delete root.dataset.j102Ready;
 await ensureStylesheet('decision-case-v2-styles','/static/css/decision-case-v2.css','j102-v1');if(!scope.active)return;
 route=caseRoute({...route,caseView:route.caseView||(current?'definition':'library')});
 const identity=browserIdentity(),copies=workingCopies({...identity,kind:'case'});
 const go=values=>navigate('logistics-case-setup',caseRoute({...route,...values}));
 if(sourceParent&&!route.caseWorkId){
  const value=fromDefinition(sourceParent.case_definition.snapshot);value.definitionWorkId=null;value.owner='';value.confirmed={};value.confirmedDefinition=null;
  value.provenance={parent_case_id:sourceParent.case.id,parent_definition_revision_id:sourceParent.case_definition.id,reason:'Nueva preparación desde Decision Graph'};
  const saved=copies.write({workId:value.workId,draft:value,initialDraft:value,savedDraft:value},0);
  return go({caseId:null,caseWorkId:saved.workId,caseMode:'configure',caseView:'definition',preparationId:null,replace:true});
 }
 const library=()=>go({caseId:null,caseWorkId:null,definitionRevisionId:null,caseView:'library',caseMode:'review',returnView:null,returnNode:null,returnRun:null});
 let record=null,draft=null,busy=false,allowLeave=false,editor=null,footer=null,preparation=null,reloadControl=null;
 const say=(error=false,message='')=>{if(footer){footer.context.textContent=message;footer.context.role=error?'alert':'status';}};
 const fail=error=>say(true,error.message||String(error));
 const act=fn=>async()=>{try{await fn();}catch(error){if(scope.active)fail(error);}};
 const done=()=>{if(scope.active){root.dataset.j102Ready='true';root.dataset.ultimateReady='true';}};
 const persist=()=>{if(!record)return;record=copies.write({...record,draft:structuredClone(draft)},record.recordRevision);};
 const checkpoint=()=>{persist();record=copies.write({...record,savedDraft:structuredClone(draft)},record.recordRevision);};
 const dirty=()=>record&&JSON.stringify(draft)!==JSON.stringify(record.savedDraft||record.initialDraft);
 async function canLeave(){if(allowLeave)return true;if(busy){say(true,'Esperá la confirmación del intento en curso.');return false;}
  if(window.dationUltimateCanLeave&&!window.dationUltimateCanLeave())return false;
  if(!dirty())return true;const choice=await dirtyChoice(root,scope);
  if(choice==='stay')return false;if(choice==='save')checkpoint();else{draft=structuredClone(record.savedDraft||record.initialDraft);persist();}return true;}
 const prior=window.dationModelCanLeave;window.dationModelCanLeave=canLeave;
 scope.own(()=>{if(window.dationModelCanLeave===canLeave){if(prior)window.dationModelCanLeave=prior;else delete window.dationModelCanLeave;}});
 scope.listen(window,'beforeunload',e=>{if(busy||dirty()){e.preventDefault();e.returnValue='';}});
 function modelLibrary(binding=null){checkpoint();const token=rememberReturn(caseRoute({...route,caseView:'definition',caseMode:current?'review':draft.confirmedDefinition?'review':'configure'}),identity);
  return navigate('logistics-models',{caseId:null,modelReturnId:token,...(binding?{modelId:binding.model_id,modelVersionId:binding.model_version_id,modelView:'review'}:{})});}
 function shell(options={}){return caseShell(root,{...options,onModels:act(()=>{if(record)return modelLibrary();const modelReturnId=current?rememberReturn(route,identity):null;return navigate('logistics-models',{caseId:null,modelReturnId});}),onCases:library,onData:act(()=>openData()),hasData:!current&&!!draft?.confirmedDefinition});}
 async function start(definition=null,source=null){if(!caps.decision_case_v2_enabled||!caps.can_create_case)throw new Error('La creación V2 no está habilitada para este acceso.');
  const value=definition?fromDefinition(definition):newCaseDraft();value.id=crypto.randomUUID();value.definitionWorkId=null;value.confirmed={};value.confirmedDefinition=null;value.owner='';
  if(source)value.provenance=source;
  const saved=copies.write({workId:value.workId,draft:value,initialDraft:value,savedDraft:value},0);allowLeave=true;
  return go({caseId:null,caseWorkId:saved.workId,definitionRevisionId:null,caseView:'definition',caseMode:'configure',returnView:null,returnNode:null,returnRun:null});}
 if(route.caseView==='library'){
  const {content,header}=shell({title:'Decision Cases',copy:'Consultá definiciones, versiones vinculadas y ejecuciones. Los borradores locales se muestran por separado.',mode:'Biblioteca'});
  if(caps.can_create_case&&caps.decision_case_v2_enabled)header.append(button('Crear Decision Case',act(()=>start()),'primary'));
  const toolbar=el('form',undefined,'j102-toolbar'),search=field(toolbar,'Buscar Cases',{name:'j102_case_search',type:'search',maxLength:120}),filter=field(toolbar,'Estado del Case',{name:'j102_case_filter',value:'all',options:[['all','Todos'],['in_progress','En curso'],['archived','Archivados']]});
  const list=el('div',undefined,'j102-case-list'),pager=el('nav',undefined,'j102-pager');pager.setAttribute('aria-label','Páginas de Decision Cases');content.append(toolbar,list,pager);
  let offset=0,generation=0;const searchButton=button('Buscar Cases',()=>{offset=0;void load();});toolbar.append(searchButton);scope.listen(toolbar,'submit',e=>{e.preventDefault();searchButton.click();});scope.listen(filter,'change',()=>{offset=0;void load();});
 const locals=copies.list();if(locals.length){const saved=el('section',undefined,'d-card j102-local-drafts');saved.append(el('h2','Copias en este navegador','d-card-title'),el('p','Incluyen borradores aún no creados y copias de edición. Se eliminan al cerrar sesión.','d-metadata'));for(const r of locals)saved.append(button((r.caseId?'Edición local · ':'Borrador · ')+(r.draft.name||'Sin nombre')+' · '+r.workId.slice(0,8),()=>go({caseId:r.caseId||null,caseWorkId:r.workId,caseView:'definition',caseMode:r.caseId?'edit':r.draft.confirmedDefinition?'review':'configure'})));content.append(saved);}
  footer=caseFooter(root,{back:()=>navigate('logistics-models',{caseId:null}),status:'Cases del workspace',notice:'Las definiciones y las ejecuciones tienen historiales separados.'});
  async function load(){const own=++generation;searchButton.disabled=true;list.replaceChildren(el('p','Consultando Cases…','d-metadata'));
   try{const data=await api('/api/platform/decisions?'+new URLSearchParams({dda:'logistics',filter:filter.value,q:search.value.trim(),limit:25,offset}),{signal:scope.signal});if(!scope.active||own!==generation)return;
    if(!Array.isArray(data.items)||!Number.isSafeInteger(data.total))throw new Error('La respuesta de Cases no es válida.');list.replaceChildren();
    if(!data.items.length)list.append(el('p','No hay Cases que coincidan con esta búsqueda.','d-card d-body'));
    for(const item of data.items){const c=item.case_definition_context,card=el('article',undefined,'d-card j102-case-card');card.dataset.caseId=item.id;
     card.append(el('h2',item.label||item.friendly_id,'d-card-title'),el('p',(item.display_status||item.status)+' · '+item.id.slice(0,8),'d-metadata'),el('p',c?.model_version_id?(c.model_name||'Modelo')+' · v'+c.model_version:'Configuración histórica','d-body'),el('p',c?.planning_start?c.planning_start+' → '+c.planning_end+' · '+c.operating_mode:'Período no configurado','d-metadata'),el('p',c?.case_policy?.primary_goal||'Objetivo histórico según sus ejecuciones','d-metadata'),el('p','Responsable: '+(item.owner?.name||'Sin asignar')+' · '+item.created_at,'d-metadata'));
     const origin=c?.case_definition?.snapshot?.provenance;if(origin)card.append(el('p','Derivado de '+origin.parent_case_id.slice(0,8),'d-metadata'));
     card.append(button('Revisar Case',()=>go({caseId:item.id,caseWorkId:null,caseView:'definition',caseMode:'review',definitionRevisionId:null})),button('Historial de definiciones',()=>go({caseId:item.id,caseWorkId:null,caseView:'history'})),button('Ver ejecuciones',()=>go({caseId:item.id,caseWorkId:null,caseView:'runs'})));list.append(card);}
    pager.replaceChildren();const prev=button('Cases anteriores',()=>{offset-=25;void load();}),next=button('Más Cases',()=>{offset+=25;void load();});prev.disabled=offset===0;next.disabled=offset+25>=data.total;pager.append(prev,el('span',data.total+' Cases','d-metadata'),next);
   }catch(error){if(scope.active&&own===generation){list.replaceChildren(el('p',error.message,'d-body'),button('Reintentar Cases',load));list.role='alert';}}
   finally{if(scope.active&&own===generation)searchButton.disabled=false;}}
  await load();done();return;
 }
 if(current)onContext?.(current);
 if(current&&['model','inputs'].includes(route.caseView)){
  const model=route.caseView==='model',{content}=shell({title:model?'Logistics Model':'Data Contract & Preparation',mode:'Versión vinculada al Case',active:model?1:3});
  if(model){const panel=collapsibleSection(content,'Logistics Model','Versión publicada vinculada al Case.',{open:true});
   mountPublishedReview(panel,current,{reviewContext:'case_pinned',onChooseVersion:caps.decision_case_v2_enabled&&caps.can_create_case?act(async()=>{
    if(!await confirmAction(root,scope,'Crear Case con otra versión','Se preparará una nueva identidad desde esta definición. Elegí y confirmá la versión deseada; el Case original se conserva.','Preparar derivado'))return;
    return start(current.case_definition.snapshot,{parent_case_id:current.case.id,parent_definition_revision_id:current.case_definition.id,reason:'Otra versión desde el modelo publicado'});
   }):null});flattenCorePanel(panel);
  }else{const host=el('section');content.append(host);scope.own(()=>disposeScope(host));await mountCaseData(host,{route,navigate,embedded:true,guarded:true});if(!scope.active)return;
   if(current.permissions?.can_edit&&caps.decision_case_v2_enabled){const ownerHost=el('section',undefined,'d-card j102-owner');content.append(ownerHost);const owner=mountResponsibilitySelector(ownerHost,{caseId:current.case.id,stageKey:'data_owner',snapshot:current.responsibilities});scope.own(()=>owner.dispose());}}
  footer=caseFooter(root,{back:()=>returnFromCore(route,navigate,scope,{root}),status:model?'Modelo publicado · sólo lectura':'Datos del mismo Case · permisos vigentes',notice:'Se conserva el Case, su versión vinculada y el origen de navegación.'});done();return;
 }
 if(route.caseView==='history'||route.caseView==='runs'){
  const definitions=route.caseView==='history',{content}=shell({title:definitions?'Historial de definiciones':'Historial de ejecuciones',mode:'Consulta'});
  const node=definitions?null:field(content,'Decisión',{name:'j102_history_node',value:'logistics_assignment',options:[['logistics_assignment','D1 · Assignment'],['logistics_scheduling','D2 · Scheduling']]}),list=el('div',undefined,'j102-history'),pager=el('nav',undefined,'j102-pager');content.append(list,pager);let offset=0,generation=0;
  footer=caseFooter(root,{back:()=>go({caseView:'definition',caseMode:'review',definitionRevisionId:null}),status:definitions?'Snapshots de configuración':'Corridas reales del nodo',notice:definitions?'Consultar una revisión no modifica el Case ni sus corridas.':'Las ejecuciones no son revisiones de la definición.'});
  async function load(){const own=++generation;try{const path=definitions?'/api/platform/logistics-cases/'+route.caseId+'/definitions':'/api/platform/decisions/'+route.caseId+'/runs';
   const data=await api(path+'?'+new URLSearchParams({limit:25,offset,...(!definitions?{node_id:node.value}:{})}),{signal:scope.signal});if(!scope.active||own!==generation)return;list.replaceChildren();
   if(!data.items.length)list.append(el('p',definitions?'Configuración histórica · no existen revisiones V2 persistidas.':'Este nodo todavía no tiene ejecuciones.','d-card d-body'));
   for(const item of data.items){const row=el('article',undefined,'d-card j102-history-item');row.append(el('h2',definitions?'Revisión '+item.revision:'Corrida '+item.id.slice(0,8),'d-card-title'),el('p',item.created_at,'d-metadata'));
    if(definitions){row.append(el('p','Autor: '+item.actor_user_id,'d-metadata'),el('p','Huella: '+item.definition_hash,'d-metadata'),button('Revisar definición '+item.revision,()=>go({caseView:'definition',caseMode:'review',definitionRevisionId:item.id})));}
    else row.append(el('p',item.status||item.engine_status||'Estado según historial','d-metadata'),button('Abrir corrida',()=>navigate('decision-dashboard',{caseId:route.caseId,nodeId:node.value,runId:item.id})));list.append(row);}
   pager.replaceChildren();const prev=button('Anteriores',()=>{offset-=25;void load();}),next=button('Siguientes',()=>{offset+=25;void load();});prev.disabled=!offset;next.disabled=offset+25>=data.total;pager.append(prev,el('span',data.total+' registros','d-metadata'),next);
  }catch(error){if(scope.active&&own===generation){fail(error);list.replaceChildren(button('Reintentar historial',load));}}}
  if(node)scope.listen(node,'change',()=>{offset=0;void load();});await load();done();return;
 }
 let revision=current?.case_definition||null;
 let originNotice='';
 if(current&&route.returnRun&&!route.definitionRevisionId){
  try{const fromRun=await api('/api/platform/logistics-cases/'+route.caseId+'/definitions/from-run/'+route.returnRun,{signal:scope.signal});if(fromRun.revision)revision=fromRun.revision;else originNotice='La corrida de origen usa una configuración histórica sin revisión J1.02.';}
  catch(error){if(error.status!==404)throw error;originNotice='La corrida de origen ya no está disponible. Se muestra la definición vigente de este mismo Case.';}
 }
 if(route.definitionRevisionId)revision=await api('/api/platform/logistics-cases/'+route.caseId+'/definitions/'+route.definitionRevisionId,{signal:scope.signal});
 if(!scope.active)return;
 if(route.caseWorkId){await lockWorkingCopy(route.caseWorkId,scope,'case');record=copies.read(route.caseWorkId);if(!record)throw new Error('Este borrador no está disponible para tu cuenta en este navegador. No se creó otro en su lugar.');
  if((record.caseId||null)!==(route.caseId||null))throw new Error('La copia de trabajo pertenece a otro Case.');draft=record.draft;}
 if(current&&!revision){
  const {content}=shell({mode:'Review · Histórico'});content.dataset.caseReview='legacy';const facts=el('dl',undefined,'d-card j102-facts');readPair(facts,'Nombre',current.case.label||current.case.friendly_id);readPair(facts,'Descripción',current.case.description);readPair(facts,'Model Version',current.model_version?.id);readPair(facts,'Objetivo',current.planning_context?.case_policy.primary_goal||'Según configuración histórica');readPair(facts,'Horizonte',current.case.planning_start?current.case.planning_start+' → '+current.case.planning_end:'No configurado');readPair(facts,'KPI J1.02','No configurado');content.append(facts);
  const actions=[button('Historial de ejecuciones',()=>go({caseView:'runs'}))];if(current.model_version&&caps.decision_case_v2_enabled&&caps.can_create_case)actions.push(button('Crear Case basado en este',act(async()=>{if(!await confirmAction(root,scope,'Crear Case derivado','Se creará otra identidad. El Case original y sus datos se conservan.','Preparar derivado'))return;
   const value=newCaseDraft();value.name=current.case.label||'';value.description=current.case.description||'';Object.assign(value,{planning_start:current.case.planning_start,planning_end:current.case.planning_end,horizon_type:current.case.horizon_type,operating_mode:current.case.operating_mode,provenance:{parent_case_id:current.case.id,parent_definition_revision_id:null,reason:'Derivado de configuración histórica'}});
   copies.write({workId:value.workId,draft:value,initialDraft:value,savedDraft:value},0);allowLeave=true;return go({caseId:null,caseWorkId:value.workId,caseMode:'configure',caseView:'definition'});}))); 
  footer=caseFooter(root,{back:()=>returnFromCore(route,navigate,scope,{root}),status:'Configuración histórica · sólo lectura',notice:'No se rellena una definición V2 ni un KPI retrospectivo.',actions});done();return;
 }
 if(current&&route.caseMode==='edit'&&!record){if(!caps.decision_case_v2_enabled||!current.permissions?.can_edit||route.definitionRevisionId&&route.definitionRevisionId!==current.case_definition.id)throw new Error('La revisión no admite edición. Podés crear un Case derivado si tenés permiso.');
  const value=fromDefinition(revision.snapshot,current.case.id);value.owner=current.responsibilities.stages.logistics_assignment.owner?.id||'';
  const saved=copies.write({workId:value.workId,caseId:current.case.id,draft:value,initialDraft:value,savedDraft:value,expectedRevision:revision.revision,expectedUpdatedAt:current.case.updated_at},0);allowLeave=true;return go({caseWorkId:saved.workId,definitionRevisionId:null,replace:true});}
 if(!draft&&current)draft=fromDefinition(revision.snapshot,current.case.id);
 if(!draft)throw new Error('Indicá un borrador de Case recuperable.');
 const mode=route.caseMode==='configure'?'Configuración':route.caseMode==='edit'?'Edición':'Revisión';
 const {content}=shell({title:route.caseView==='data'?'Data Contract & Preparation':'Decision Case',mode,active:route.caseView==='data'?3:2});
 if(originNotice)content.append(el('p',originNotice,'d-card j102-origin'));
 if(draft.provenance)content.append(el('aside','Derivado de '+draft.provenance.parent_case_id+' · '+draft.provenance.reason+' · El original se conserva.','d-card j102-origin'));
 function refresh(){if(!footer)return;const pending=!!draft.creationIntent||!!draft.updateIntent;
  footer.state.textContent=current?'Case persistido · '+(current.case.context_frozen_at?'contexto congelado':'sin congelar')+' · '+mode:draft.confirmedDefinition?'Definición confirmada · preparación pendiente':Object.keys(draft.confirmed).length+' de 6 bloques confirmados · borrador';
  for(const b of footer.controls.querySelectorAll('button'))b.disabled=busy;
  if(editor)footer.controls.querySelector('[data-j102-confirm]').disabled=busy||!pending&&!editor.complete;
  if(preparation){const primary=footer.controls.querySelector('[data-j102-finalize]');primary.disabled=busy||(draft.creationIntent?!preparation.snapshot:!preparation.validated);primary.textContent=draft.creationIntent?'Recuperar creación pendiente':'Crear Case y abrir Decision Graph';content.inert=busy||!!draft.creationIntent;}}
 async function openData(){if(current||!draft?.confirmedDefinition)throw new Error('Confirmá una definición nueva antes de preparar sus datos.');
  if(!caps.decision_case_v2_enabled)throw new Error('El bridge de preparación V2 no está habilitado.');
  busy=true;refresh();try{draft.preparation.id||=crypto.randomUUID();draft.preparation.version_id=draft.binding.model_version_id;persist();
   const data=await post('/api/platform/data-preparations',{id:draft.preparation.id,model_version_id:draft.binding.model_version_id,parent_case_id:draft.provenance?.parent_case_id||null},{signal:scope.signal});
   if(data.session.model_version_id!==draft.binding.model_version_id||data.session.creation_intent&&data.session.creation_intent.id!==draft.id)throw new Error('La sesión no pertenece a esta intención de Case.');checkpoint();allowLeave=true;return go({caseView:'data',caseMode:'review'});
  }finally{busy=false;refresh();}}
 if(route.caseView==='data'){
  if(current||!draft.confirmedDefinition||!draft.preparation.id)throw new Error('No hay una definición y sesión compatibles. Volvé al Case.');
  content.classList.add('j102-data');const panel=collapsibleSection(content,'03 · Datos del Case','Contratos de la versión elegida. Guardá y validá todos los archivos antes de crear el Case.',{open:true}),prepRoot=el('section',undefined,'journey-preparation');panel.body.append(prepRoot);
  const primary=button(draft.creationIntent?'Recuperar creación pendiente':'Crear Case y abrir Decision Graph',act(finalize),'primary');primary.dataset.j102Finalize='';
  footer=caseFooter(root,{back:()=>go({caseView:'definition',caseMode:'review'}),status:'Preparación privada',notice:'No se crea ningún Case hasta la confirmación final.',actions:[primary]});
  preparation=mountCorePreparation(prepRoot,scope,{canAssign:caps.can_assign,draft:draft.preparation,parentCaseId:draft.provenance?.parent_case_id||null,readExisting:true,caseIntentId:draft.id,
   onDraft:()=>{persist();refresh();},onStateChange:refresh,onContinue:()=>primary.focus(),onRecovered:result=>finish(result)});
  const bridge=mountDataContractView(panel,scope,{retry:()=>{},onContinue:()=>{},onContracts:(...args)=>preparation.attach(...args)});
  const data=await api('/api/platform/logistics-models/'+draft.binding.model_id+'/versions/'+draft.binding.model_version_id+'/contracts',{signal:scope.signal});if(!scope.active)return;
  bridge.render(data,{model_id:draft.binding.model_id,version_id:draft.binding.model_version_id});panel.body.querySelector('.data-contract-info')?.remove();refresh();done();return;
 }
 async function finish(result){if(result.case.id!==draft.id||result.case.logistics_model_version_id!==draft.binding.model_version_id)throw new Error('El Case confirmado no corresponde a esta intención.');allowLeave=true;copies.remove(record.workId,record.recordRevision);onContext?.(result);await navigate('logistics-map',{caseId:result.case.id,nodeId:null,runId:null,replace:true});}
 async function finalize(){if(busy)return;if(!draft.creationIntent){if(!preparation.validated)throw new Error('Guardá y validá todos los archivos de esta versión.');if(!await confirmAction(root,scope,'Crear Decision Case','Se fijarán esta definición, la Model Version seleccionada y los datos preparados. No se ejecutarán motores.','Crear Case'))return;
   draft.creationIntent=creationBody(draft,caps.can_assign);persist();}
  busy=true;refresh();content.inert=true;try{await finish(await preparation.finalize(draft.creationIntent));}finally{busy=false;if(scope.active){content.inert=!!draft.creationIntent;refresh();}}}
 const viewing=route.caseMode==='review';
 if(viewing){const definition=current?revision.snapshot:draft.confirmedDefinition;if(!definition)throw new Error('La definición aún no está confirmada. Continuá en configuración.');
  const review=el('section',undefined,'d-card j102-review');review.dataset.caseReview=current?'persisted':'confirmed-draft';definitionFacts(review,definition,{owner:current?.responsibilities?.stages?.logistics_assignment?.owner?.name,versionName:current?current.model.name+' · v'+current.model_version.version:draft.modelLabel});content.append(review);
  if(current){review.append(el('p','Revisión '+revision.revision+' · '+revision.created_at+' · '+revision.definition_hash,'d-metadata'));}
  if(current&&current.responsibilities){
   const owners=el('section',undefined,'j102-two');owners.setAttribute('aria-label','Responsabilidades vigentes');content.append(owners);
   for(const stageKey of ['logistics_assignment','logistics_scheduling']){const host=el('section',undefined,'d-card j102-owner');owners.append(host);
    const widget=mountResponsibilitySelector(host,{caseId:current.case.id,stageKey,field:'owner',snapshot:current.responsibilities,onSaved:snapshot=>{current.responsibilities=snapshot;}});scope.own(()=>widget.dispose());}
  }
  const actions=[];const pending=draft.creationIntent||draft.updateIntent;
  if(current&&revision.id!==current.case_definition.id)actions.push(button('Revisar definición vigente',()=>go({caseMode:'review',caseWorkId:null,definitionRevisionId:current.case_definition.id})));
  if((!current||current.permissions?.can_edit&&revision.id===current.case_definition.id)&&caps.decision_case_v2_enabled&&!pending)actions.push(button('Editar configuración',()=>{if(record)record=copies.write({...record,editBaseline:structuredClone(draft)},record.recordRevision);return go({caseMode:'edit',caseWorkId:current?null:record.workId});}));
  if(caps.models_library_enabled)actions.push(button('Revisar Model Version',act(async()=>{if(!record){const token=rememberReturn(route,identity);return navigate('logistics-models',{modelId:definition.model_binding.model_id,modelVersionId:definition.model_binding.model_version_id,modelView:'review',modelReturnId:token});}return modelLibrary(definition.model_binding);})));
  if(!current)actions.push(button(pending?'Recuperar creación pendiente':'Continuar a preparación de datos',act(openData),'primary'));
  if(current){actions.push(button('Historial de definiciones',()=>go({caseView:'history',caseWorkId:null})),button('Historial de ejecuciones',()=>go({caseView:'runs',caseWorkId:null})));
   if(caps.can_create_case&&caps.decision_case_v2_enabled)actions.push(button('Crear Case derivado',act(async()=>{if(!await confirmAction(root,scope,'Crear Case derivado','Se creará un Case nuevo desde esta revisión exacta. El original, sus datos y corridas se conservan.','Preparar derivado'))return;
    return start(definition,{parent_case_id:current.case.id,parent_definition_revision_id:revision.id,reason:'Nueva planificación desde revisión '+revision.revision});})));
   await mountCaseAcceptance(content,scope,{caseId:current.case.id,runId:route.returnRun});}
  footer=caseFooter(root,{back:()=>current?returnFromCore(route,navigate,scope,{root}):modelLibrary(),status:current?(current.case.status==='archived'?'Case archivado':'Case vigente')+' · revisión '+revision.revision:'Definición confirmada · todavía no es un Case',notice:current?'Sólo lectura. La edición y la derivación son acciones explícitas.':'La creación final ocurre después de preparar y validar los datos.',actions});done();return;
 }
 if(!caps.decision_case_v2_enabled||current&&!current.permissions?.can_edit||!record)throw new Error('La edición V2 no está disponible para este acceso.');
 const save=button('Guardar borrador',act(async()=>{checkpoint();say(false,'Borrador guardado sólo en este navegador para esta cuenta.');})),confirm=button(current?'Guardar cambios':'Confirmar definición',act(confirmDefinition),'primary');confirm.dataset.j102Confirm='';
 const actions=[save];if(route.caseMode==='edit')actions.push(button('Cancelar cambios',act(()=>{draft=structuredClone(record.editBaseline||record.initialDraft);checkpoint();allowLeave=true;return go({caseMode:'review',caseWorkId:current?null:record.workId});})));actions.push(confirm);
 if(current){reloadControl=button('Consultar versión del servidor',()=>{checkpoint();allowLeave=true;return go({caseMode:'review',caseWorkId:null,definitionRevisionId:null});});reloadControl.hidden=!draft.updateIntent;actions.push(reloadControl);}
 footer=caseFooter(root,{back:()=>modelLibrary(),status:'Configuración en progreso',notice:'Confirmá los seis bloques. Los checks no significan Case creado.',actions});
 editor=await mountCaseV2Editor(content,{root,scope,draft,caps,current,onChange:()=>{try{persist();refresh();}catch(error){fail(error);editor?.freeze(true);}},onReviewModel:binding=>modelLibrary(binding),onOpenModels:()=>modelLibrary(),onError:fail,onState:refresh});
 if(draft.updateIntent)editor.freeze(true);refresh();done();
 async function confirmDefinition(){if(busy)return;if(!draft.updateIntent&&!editor.complete){editor.validate();throw new Error('Revisá y confirmá los seis bloques.');}
  busy=true;editor.freeze(true);refresh();try{const definition=draft.updateIntent?.definition_v2||editor.read();
   if(current){draft.updateIntent||={mutation_id:crypto.randomUUID(),expected_revision:record.expectedRevision,expected_updated_at:record.expectedUpdatedAt,definition_v2:definition};persist();
    const result=await api('/api/platform/logistics-cases/'+current.case.id+'/definition',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(draft.updateIntent),signal:scope.signal});
    if(result.case.id!==current.case.id||result.case_definition.snapshot.identity.name!==definition.identity.name)throw new Error('La confirmación del servidor no corresponde al intento.');allowLeave=true;copies.remove(record.workId,record.recordRevision);onContext?.(result);return go({caseWorkId:null,caseMode:'review',definitionRevisionId:result.case_definition.id});}
   await post('/api/platform/decision-case-definitions/validate',definition,{signal:scope.signal});draft.confirmedDefinition=structuredClone(definition);checkpoint();allowLeave=true;return go({caseMode:'review'});
  }catch(error){if(current&&error.status===409){reloadControl.hidden=false;error.message='Conflicto de revisión. Tu copia y el intento original se conservan; consultá la versión del servidor antes de reconciliar o derivar.';}throw error;}
  finally{busy=false;if(scope.active){editor.freeze(!!draft.updateIntent);refresh();}}}
}
