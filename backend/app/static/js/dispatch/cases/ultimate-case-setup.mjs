import {api,post,errorBox,download} from '../shared.mjs';
import {scopeFor,disposeScope} from '../lifecycle.mjs';
import {ensureStylesheet} from '../styles.mjs';
import {loadingState} from '../../platform/components.mjs';
import {el,button,field,section,collapsibleSection,pageHeader,draftStore,mountForm,confirmAction} from '../models/forms.mjs';
import {decisionCard,decisionChoices,decorateDecisionCase,mountCaseReview,decorateCaseFooter} from './decision-case-ui.mjs';
import {mountPolicy,policyInputValues,GOALS} from '../models/policy.mjs';
import {ROLES,DIMENSIONS} from '../models/model-fields.mjs';
import {mountModelFieldsV2} from '../models/model-fields-v2.mjs';
import {mountPlanningModel} from '../models/planning-model.mjs';
import {mountSetupSteps,flattenCorePanel} from '../models/wizard-ui.mjs';
import {mountCorePreparation} from '../upload/core-preparation.mjs';
import {mountCaseData} from '../upload/ultimate-case-data.mjs';
import {mountResponsibilitySelector} from './workflow-responsibility.mjs';
import {editSource,returnFromCore,mountCoreReturn,origin} from '../journey/navigation.mjs';
import {sameCoreJourney,coreSourceRoute} from '../journey/targets.mjs';
import {horizonEnd} from '../models/setup-values.mjs';


function showPublishedContracts(host,caseId,contracts,scope){
 for(const [entity,label] of [['transport_demand','Órdenes / Demanda'],['order_lines','Líneas de órdenes'],['transport_resources','Flota / Recursos']]){
  const contract=contracts[entity];if(!contract)continue;
  const panel=el('section',undefined,'ultimate-contract');
  panel.append(el('h3',label+' · '+contract.fields.length+' columnas','d-card-title'));
  const wrap=el('div',undefined,'dispatch-table-wrap');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Data Contract · '+label);
  const table=el('table'),head=el('thead'),titles=el('tr');
  for(const title of ['Variable','Tipo / unidad','Regla']){const th=el('th',title);th.scope='col';titles.append(th);}
  head.append(titles);table.append(head);
  const body=el('tbody');
  for(const f of contract.fields){const tr=el('tr');const when=Object.keys(f.applies_when||{}).length?' · Aplica cuando '+JSON.stringify(f.applies_when):'';
   for(const value of [f.public_header,f.type+(f.unit?' · '+f.unit:''),(f.nullable?'Admite vacío':'Obligatorio')+when])tr.append(el('td',value));
   body.append(tr);
  }
  table.append(body);wrap.append(table);panel.append(wrap);
  const action=button('Descargar template de '+label,async()=>{
   try{
    const response=await fetch('/api/platform/logistics-cases/'+caseId+'/data/templates/'+entity,{signal:scope.signal});
    if(!response.ok)throw new Error('No se pudo obtener la plantilla. Volvé a intentarlo.');
    download(entity+'.csv',await response.text(),'text/csv;charset=utf-8');
   }catch(error){if(scope.active){const message=el('p',error.message,'d-metadata');message.setAttribute('role','alert');panel.append(message);}}
  });
  panel.append(action);
  host.append(panel);
 }
}

export async function mountCaseSetup(root,{route,navigate,onContext}){
 delete root.dataset.ultimateReady;
 const scope=scopeFor(root);await ensureStylesheet('ultimate-foundation-styles','/static/css/ultimate-foundation.css','t3-v1');if(!scope.active)return;
 root.className='dispatch d-platform ultimate-foundation ultimate-core-setup';root.append(loadingState(route.caseId?'Recuperando contexto del Case…':'Inicializando Core Configuration…'));
 try{
  const fresh=!route.caseId,[caps,current]=await Promise.all([api('/api/platform/ultimate-foundation/capabilities',{signal:scope.signal}),fresh?Promise.resolve(null):api('/api/platform/logistics-cases/'+route.caseId+'/context',{signal:scope.signal})]);
  if(!scope.active)return;if(fresh&&!caps.can_create_case)throw Object.assign(new Error('La creación de Cases no está disponible para este acceso.'),{status:403});
  if(current)onContext?.(current);
  const unified=!!caps.unified_journey_enabled;window.dationUnifiedJourney=unified;
  const parent=unified&&fresh&&route.parentCaseId?await api('/api/platform/logistics-cases/'+route.parentCaseId+'/context',{signal:scope.signal}):null;
  const row=current?.case,store=draftStore('case',route.caseId||(route.preparationId?'derived-'+route.preparationId:'new')),saved=store.read(),policy=(current||parent)?.planning_context.case_policy||{version:1,primary_goal:'MINIMIZE_COST',guardrails:[],preferences:[]};
  const initial={id:row?.id||crypto.randomUUID(),name:row?.label||'',description:row?.description||'',model_id:current?.model.id||route.modelId||'',logistics_model_version_id:row?.logistics_model_version_id||'',
   planning_start:row?.planning_start||'',planning_end:row?.planning_end||'',horizon_type:row?.horizon_type||'WEEKLY',operating_mode:row?.operating_mode||'OPERATIONAL',expected_updated_at:row?.updated_at||null,decision_owner_user_id:'',
   owners:Object.fromEntries(['logistics_assignment','logistics_scheduling'].map(id=>[id,{id:current?.responsibilities.stages[id].owner?.id||'',updated_at:current?.responsibilities.stages[id].updated_at||null}])),policy_values:policyInputValues(policy),planning_model:saved?.planning_model||null};
  if(parent){Object.assign(initial,{model_id:parent.model.id,planning_start:parent.case.planning_start,planning_end:parent.case.planning_end,horizon_type:parent.case.horizon_type,operating_mode:parent.case.operating_mode,planning_model:{mode:'existing',model_id:parent.model.id,version_id:parent.model_version.id}});}
  const preparationDraft=saved?.preparation||{id:route.preparationId||null,version_id:parent?.model_version.id||null};
  const draft=saved||initial,editable=fresh||current.permissions.can_edit,mathEditable=fresh||(current.permissions.can_edit_mathematical&&!row.context_frozen_at),canAssign=fresh?caps.can_assign:current.permissions.can_assign;
  root.replaceChildren();const header=pageHeader(root,'Core Configuration',fresh?'Configurá los tres bloques para crear el Case. Los datos operativos se gestionan después en el Decision Graph.':'Revisá el Logistics Model y el Data Contract, o editá la información permitida del Decision Case.');
  if(row&&!unified){
   header.append(button('Volver al Decision Graph',()=>navigate('logistics-map',{caseId:row.id,nodeId:null,runId:null})));
   // Keep the existing, recoverable Case Data route until the graph modal replaces it.
   try{
    const inputs=await api('/api/platform/logistics-cases/'+row.id+'/data',{signal:scope.signal});
    if(scope.active&&(inputs.enabled||inputs.entries.length))
     header.append(button('Administrar datos del Case',()=>unified?editSource(root,scope,{...route,view:'logistics-map'},navigate):navigate('logistics-case-data',{caseId:row.id,nodeId:null,runId:null})));
   }catch(error){if(error.name==='AbortError')throw error;}
  }
  let savedCard=null;
  if(row){savedCard=el('section',undefined,'d-card ultimate-saved-context');savedCard.append(el('h2','Contexto guardado','d-card-title'),el('p','Versión '+current.model_version.version+' de '+current.model.name+' · '+row.planning_start+' a '+row.planning_end,'d-body'),el('p','Data Pack inicial: '+(current.entry_count?'datos vinculados':'sin archivos')+'. El contexto se conserva al recargar.','d-metadata'));
   if(row.context_frozen_at)savedCard.append(el('p','El horizonte y la política quedaron congelados con la primera admisión. El nombre, la descripción y los responsables conservan sus reglas de edición.','d-body'));}
  let planningModel=null,steps=null,preparation=null,initialized=false,existingContractsReady=false,creationIntent=draft.creation_intent||null;
  const kit=mountForm(root,scope,{initial,store,focusFirstError:true,submitLabel:fresh?'Finalizar configuración':'Guardar contexto',onReload:()=>navigate('logistics-case-setup',unified?{...route,replace:true}:{caseId:route.caseId,replace:true}),onSave:async value=>{
   let result;
   if(fresh){
    creationIntent||={id:value.id,name:value.name,description:value.description||null,planning_start:value.planning_start,planning_end:value.planning_end,horizon_type:value.horizon_type,operating_mode:value.operating_mode,case_policy:policyUI.read(),decision_owner_user_id:canAssign?value.decision_owner_user_id||null:null};
    reflect();store.write(collect());
    const versionId=await planningModel.ensurePublished(()=>store.write(collect()));
    creationIntent.logistics_model_version_id=versionId;store.write(collect());
    try{result=unified?await preparation.finalize(creationIntent):await post('/api/platform/logistics-cases',creationIntent,{signal:scope.signal});}catch(error){error.message='Crear Decision Case: '+error.message;throw error;}}

   else{
    const body={expected_updated_at:value.expected_updated_at,name:value.name,description:value.description||null};
    if(mathEditable)Object.assign(body,{planning_start:value.planning_start,planning_end:value.planning_end,horizon_type:value.horizon_type,operating_mode:value.operating_mode,case_policy:policyUI.read()});
    if(canAssign)body.owner_updates=Object.entries(value.owners).filter(([id,o])=>o.id!==(current.responsibilities.stages[id].owner?.id||'')).map(([id,o])=>({node_id:id,owner_user_id:o.id||null,expected_updated_at:o.updated_at}));
    result=await api('/api/platform/logistics-cases/'+row.id+'/context',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:scope.signal});
   }
   kit.markSaved();if(scope.active){onContext?.(result);if(unified&&!fresh)return returnFromCore(route,navigate,scope,{root});await navigate(fresh?'logistics-map':'logistics-case-setup',{caseId:result.case.id,nodeId:null,runId:null,replace:true});}
  }});
  const form=kit.form;form.inert=true;form.setAttribute('aria-busy','true');
  const preparationRoot=unified&&fresh?el('section',undefined,'journey-preparation'):null;
  if(preparationRoot)preparation=mountCorePreparation(preparationRoot,scope,{canAssign:caps.can_assign,draft:preparationDraft,parentCaseId:route.parentCaseId||null,onRecovered:result=>{kit.markSaved();onContext?.(result);navigate('logistics-map',{caseId:result.case.id,nodeId:null,runId:null,replace:true});},onDraft:()=>{if(initialized){store.write(collect());reflect();}},onContinue:()=>steps?.show(2,true)});
  if(fresh)planningModel=await mountPlanningModel(form,scope,{draft:draft.planning_model||{},modelId:draft.model_id,canManage:caps.can_manage_models,saga10:!!caps.saga10_ui_enabled,unified,onChange:()=>{if(initialized){reflect();kit.saveDraft();}},persist:()=>{if(initialized)store.write(collect());},onSelected:()=>steps?.show(1,true),onContinue:()=>steps?.show(2,true),onContracts:unified?(...args)=>preparation.attach(...args):undefined});
  if(unified&&planningModel){planningModel.contractPanel.body.insertBefore(preparationRoot,planningModel.contractPanel.body.querySelector('.data-contract-footer'));const p=planningModel.contractPanel;p.details.querySelector('.data-contract-heading .d-metadata').textContent='Dation genera la estructura exacta que necesitan tus datos. Descargá las plantillas, completalas con tu operación y validalas antes de definir el Decision Case.';p.details.querySelector('.ultimate-disclosure__title').textContent='02 · Data Contract & Preparation';p.body.querySelector('.data-contract-info')?.remove();}
  if(!scope.active)return;
  // Existing Cases keep a read-only Model/Contract summary; a published
  // Model Version is immutable once linked to a Case.
  const existingModelPanel=!fresh?collapsibleSection(form,'01 Logistics Model','Modelo y versión publicada vinculados a este Case. No pueden reemplazarse desde la edición.',{initialStatus:'Publicado'}):null;
  const existingContractPanel=!fresh?collapsibleSection(form,'02 Data Contract','Esquema vigente de las entradas de Demanda y Recursos.',{initialStatus:'Cargando'}):null;
  const casePanel=collapsibleSection(form,'03. Decision Case','Definí qué querés optimizar, en qué horizonte y bajo qué condiciones se ejecutará este Case.',{open:true,initialStatus:fresh?'Por completar':'Guardado'});
  casePanel.details.dataset.dationTest='core-case';decorateDecisionCase(casePanel);
  if(existingModelPanel)existingModelPanel.details.dataset.dationTest='core-model';
  if(existingContractPanel)existingContractPanel.details.dataset.dationTest='core-contract';
  const caseRoot=el('fieldset',undefined,'ultimate-case-fields');caseRoot.dataset.planningCase='';casePanel.body.append(caseRoot);
  if(savedCard)caseRoot.append(savedCard);
  const identity=decisionCard(caseRoot,'Identidad del Case','Definí un nombre y una descripción para identificar este Case.','document'),name=field(identity,'Nombre del Case',{name:'case_name',value:draft.name,required:true,maxLength:120}),description=field(identity,'Descripción (opcional)',{name:'case_description',type:'textarea',value:draft.description,maxLength:1000});
  let modelSelect,versionSelect,models;
  if(!fresh&&caps.saga10_ui_enabled&&current.model_version.config_jsonb.version===2){
   // Review the exact pinned version; never instantiate a new planning draft.
   const review=mountModelFieldsV2(existingModelPanel.body,scope,{...current.model,configuration:current.model_version.config_jsonb},{published:true});review.lock({published:true});
   modelSelect={value:current.model.id};versionSelect={value:current.model_version.id};models=async()=>{};
  }else if(!fresh){
  const modelGroup=section(existingModelPanel.body,'Model y versión publicada','La versión elegida queda ligada al Case y no puede reemplazarse después de crear el contexto.');
  let selectedModel=current?.model.id||draft.model_id,selectedVersion=draft.logistics_model_version_id,modelsGeneration=0;
  const modelSearch=field(modelGroup,'Buscar Model por nombre',{name:'case_model_search',type:'search',maxLength:120});modelSelect=field(modelGroup,'Logistics Model',{name:'model_id',options:[['','Elegí un Model']],required:true});versionSelect=field(modelGroup,'Model Version',{name:'model_version_id',options:[['','Elegí una versión publicada']],required:true});
  const summary=el('p',undefined,'d-field__help');modelGroup.append(summary);
  async function versions(id){const own=++modelsGeneration;versionSelect.disabled=true;const data=await api('/api/platform/logistics-models/'+id,{signal:scope.signal});if(!scope.active||own!==modelsGeneration)return;
   versionSelect.replaceChildren();const empty=el('option','Elegí una versión publicada');empty.value='';versionSelect.append(empty);
   for(const v of data.versions){const option=el('option','Versión '+v.version);option.value=v.id;versionSelect.append(option);}
   versionSelect.value=selectedVersion;versionSelect.disabled=!fresh;const render=()=>{const v=data.versions.find(v=>v.id===versionSelect.value);summary.textContent=v?[ROLES.find(([k])=>k===v.config_jsonb.operating_role)?.[1],DIMENSIONS.find(([k])=>k===v.config_jsonb.primary_dimension)?.[1],v.config_jsonb.currency_policy.currency].filter(Boolean).join(' · '):'Elegí una versión publicada. Los borradores no se pueden vincular.';};scope.listen(versionSelect,'change',render);render();
  }
  models=async function(){const own=++modelsGeneration;const result=await api('/api/platform/logistics-models?'+new URLSearchParams({q:modelSearch.value,limit:50}),{signal:scope.signal});if(!scope.active||own!==modelsGeneration)return;
   modelSelect.replaceChildren();const placeholder=el('option','Elegí un Model');placeholder.value='';modelSelect.append(placeholder);for(const m of result.items.filter(x=>x.versions.length)){const o=el('option',m.name);o.value=m.id;modelSelect.append(o);}
   if(selectedModel&&!result.items.some(m=>m.id===selectedModel)){const data=await api('/api/platform/logistics-models/'+selectedModel,{signal:scope.signal});if(!scope.active)return;const o=el('option',data.model.name);o.value=selectedModel;modelSelect.append(o);}
   modelSelect.value=selectedModel;modelSelect.disabled=!fresh;if(selectedModel)await versions(selectedModel);
  }
  const search=button('Buscar Models',()=>models().catch(e=>{if(scope.active){summary.textContent=e.message;summary.role='alert';}}));modelGroup.append(search);modelSearch.disabled=search.disabled=!fresh;
  scope.listen(modelSelect,'change',()=>{selectedModel=modelSelect.value;selectedVersion='';if(selectedModel)versions(selectedModel).catch(e=>{if(scope.active){summary.textContent=e.message;summary.role='alert';}});else versionSelect.replaceChildren();});
  }
  const policyUI=mountPolicy(caseRoot,scope,policy,{readOnly:!mathEditable,draftValues:draft.policy_values});
  const horizon=decisionCard(caseRoot,'Alcance de la planificación','Definí el modo de operación, el horizonte y la ventana de planificación.','calendar');
  const mode=decisionChoices(horizon,{name:'operating_mode',label:'Operating Mode',options:[['OPERATIONAL','Operacional'],['SIMULATION','Simulación']],value:draft.operating_mode,readOnly:!mathEditable}),type=field(horizon,'Tipo de horizonte',{name:'horizon_type',options:[['DAILY','Diario'],['WEEKLY','Semanal'],['MONTHLY','Mensual'],['CUSTOM','Personalizado']],value:draft.horizon_type});
  const start=field(horizon,'Inicio de planificación',{name:'planning_start',type:'date',value:draft.planning_start,required:true}),end=field(horizon,'Fin de planificación',{name:'planning_end',type:'date',value:draft.planning_end,required:true});
  const preset=()=>{const value=horizonEnd(start.value,type.value);if(value){end.value=value;end.dispatchEvent(new Event('input',{bubbles:true}));}};scope.listen(type,'change',preset);scope.listen(start,'change',preset);
  for(const input of [mode,type,start,end])input.disabled=!mathEditable;
  horizon.append(el('p','Fechas inclusivas. El horizonte ofrece un punto de partida; se guardan las fechas concretas.','d-field__help'));
  for(const [input,label]of [[start,'Inicio'],[end,'Fin']]){input.setAttribute('aria-label',input.labels[0].textContent);input.labels[0].textContent=label;}
  if(!mathEditable)horizon.append(el('p',row?.context_frozen_at?'El horizonte, la modalidad y la política están congelados con la primera admisión.':'No tenés permiso para editar la modalidad, el horizonte ni la política.','d-field__help'));
  const ownersGroup=decisionCard(caseRoot,'Responsable de la decisión','Asume la responsabilidad del Case.','people');ownersGroup.parentElement.classList.add('core-owner-card');
  const ownerHelp=el('p','Elegí una persona con responsabilidad vigente de Decision Owner.','d-field__help');ownerHelp.hidden=!canAssign;ownersGroup.append(ownerHelp);
  const owners={};
  if(fresh)owners.initial=field(ownersGroup,'Decision Owner inicial (D1 y D2)',{name:'decision_owner_user_id',options:[['','Elegí un Decision Owner']],value:draft.decision_owner_user_id,required:canAssign});
  else for(const [id,label]of [['logistics_assignment','Decision Owner · Asignación de carga'],['logistics_scheduling','Decision Owner · Planificación de despachos']])owners[id]=field(ownersGroup,label,{name:'owner_'+id,options:[['','Sin asignar']],value:draft.owners[id].id});
  if(owners.initial){owners.initial.setAttribute('aria-label',owners.initial.labels[0].textContent);owners.initial.labels[0].textContent='Decision Owner';}
  if(canAssign){const people=[];let offset=0,total=0;do{const result=await api('/api/platform/team?'+new URLSearchParams({candidates:'true',responsibility:'decision_owner',limit:50,offset}),{signal:scope.signal});if(!scope.active)return;people.push(...result.members);offset+=50;total=result.total;if(offset<total&&!result.members.length)throw new Error('El Equipo cambió. Recargá la lista de personas.');}while(offset<total);
   for(const [id,control]of Object.entries(owners)){const currentId=id==='initial'?draft.decision_owner_user_id:draft.owners[id].id;for(const person of people){const option=el('option',person.name+' · '+person.email);option.value=person.user_id;control.append(option);}if(currentId&&!people.some(p=>p.user_id===currentId)){const option=el('option',(current?.responsibilities.stages[id]?.owner?.name||'Responsable anterior')+' (no elegible)');option.value=currentId;option.disabled=true;control.append(option);}control.value=currentId;}
   if(!people.length)ownersGroup.append(el('p','No hay personas elegibles. Revisá las responsabilidades en Equipo antes de asignar.','d-field__help'));
  }else{for(const [id,control]of Object.entries(owners)){const person=current?.responsibilities.stages[id]?.owner;if(person){const option=el('option',person.name);option.value=person.id;control.append(option);control.value=person.id;}control.disabled=true;}ownersGroup.append(el('p',fresh?'Podés crear el Case con Owner pendiente. Un Admin debe completar la asignación antes de ejecutar decisiones.':'La asignación está administrada por un Admin.','d-field__help'));}
  const ownerNote=ownersGroup.querySelector('.d-field__help');ownerNote.classList.add('decision-case-owner-note');ownerNote.dataset.single=String(fresh);ownersGroup.append(ownerNote);
  const collect=()=>({id:draft.id,name:name.value.trim(),description:description.value.trim(),model_id:planningModel?planningModel.read().model_id:modelSelect.value,logistics_model_version_id:planningModel?planningModel.read().version_id:versionSelect.value,planning_model:planningModel?.draft()||null,creation_intent:creationIntent,...(unified?{preparation:preparationDraft}:{}),
   planning_start:start.value,planning_end:end.value,horizon_type:type.value,operating_mode:mode.value,expected_updated_at:draft.expected_updated_at,
   decision_owner_user_id:owners.initial?.value||'',owners:Object.fromEntries(['logistics_assignment','logistics_scheduling'].map(id=>[id,{id:owners[id]?.value||draft.owners[id].id,updated_at:draft.owners[id].updated_at}])),policy_values:policyUI.draft()});
  kit.setCollector(collect,()=>{const errors={...(mathEditable?policyUI.validate():{}),...(planningModel?.validate()||{})};if(unified&&fresh&&preparation?.pending)errors.data_preparation='Guardá o quitá los CSV locales en Data Contract & Preparation antes de finalizar.';if(!name.value.trim())errors.case_name='Ingresá el nombre del Case.';if(start.value&&end.value&&start.value>end.value)errors.planning_end='La fecha de fin debe ser igual o posterior a la de inicio.';if(fresh&&canAssign&&(!owners.initial.value||owners.initial.selectedOptions[0]?.disabled))errors.decision_owner_user_id='Elegí un Decision Owner activo y elegible.';return errors;});
  const review=mountCaseReview(caseRoot),progress=decorateCaseFooter(kit,{fresh});
  function reflect(){
   const errors=kit.validation(),keys=Object.keys(errors).filter(key=>errors[key]);
   const checks=[!!name.value.trim()&&!keys.some(k=>k.startsWith('case_')), !keys.some(k=>k==='primary_goal'||k.startsWith('guard_')||k.startsWith('weight_')), !!(start.value&&end.value&&start.value<=end.value)&&!keys.some(k=>['operating_mode','horizon_type','planning_start','planning_end'].includes(k)), !keys.some(k=>k.startsWith('owner_')||k==='decision_owner_user_id'), editable&&!(unified&&fresh&&preparation?.pending)&&(fresh?!!planningModel?.ready:!!current?.model_version.id)];
   const complete=checks.every(Boolean)&&!keys.length;
   if(fresh){casePanel.setStatus(complete?'Listo para crear':'Por completar',complete?'complete':'pending');caseRoot.disabled=!!creationIntent||!planningModel.ready;kit.submit.disabled=kit.busy||!planningModel.ready;}
   else casePanel.setStatus(kit.dirty?'Cambios pendientes':'Guardado',kit.dirty?'pending':'complete');
   steps?.update();progress.update(checks,complete);
   const ownerText=control=>control?.value?control.selectedOptions[0]?.textContent||'Pendiente':'Pendiente';
   review.update({model:fresh?planningModel.summary():current.model.name+' · versión '+current.model_version.version,contract:(fresh?planningModel.ready:existingContractsReady)?(fresh?planningModel.contractCount:(current.model_version.config_jsonb?.cargo?.input_mode==='catalog'?3:2))+' contratos generados':'Pendiente',goal:GOALS.find(([key])=>key===policyUI.draft().goal)?.[1],mode:({'OPERATIONAL':'Operacional','SIMULATION':'Simulación'})[mode.value]||'Pendiente',horizon:(type.selectedOptions[0]?.textContent||'Pendiente')+' · '+(start.value||'Pendiente')+' a '+(end.value||'Pendiente'),flow:'D1 → aprobación → D2',identity:name.value.trim()||'Pendiente',owner:fresh?ownerText(owners.initial):'D1: '+ownerText(owners.logistics_assignment)+' · D2: '+ownerText(owners.logistics_scheduling)});
  }
  initialized=true;scope.listen(form,'input',reflect);scope.listen(form,'change',reflect);reflect();
  if(unified)for(const panel of [planningModel?.modelPanel||existingModelPanel,planningModel?.contractPanel||existingContractPanel,casePanel])flattenCorePanel(panel);
  kit.finish();steps=mountSetupSteps(form,[planningModel?.modelPanel.details||existingModelPanel.details,planningModel?.contractPanel.details||existingContractPanel.details,casePanel.details],{fresh,unified,initialStep:unified?route.coreStep:null,onExit:target=>navigate(target.view,target),onStep:(index,meta)=>{if(unified){window.dationJourneyProgress={step:index+1,modelReady:planningModel?.ready||!!current?.model_version.id,dataReady:preparation?.validated||current?.entry_count===(current?.model_version.config_jsonb?.cargo?.input_mode==='catalog'?3:2)};route.coreStep=index+1;window.dationSetCoreStep?.(index+1,meta);window.dispatchEvent(new CustomEvent('dation:core-step',{detail:{step:index+1,caseId:route.caseId}}));}},available:index=>!fresh||index===0||(index===1?planningModel.selected:planningModel.ready)});(unified?casePanel.details:steps.workspace).append(kit.footer);if(!editable){for(const control of form.querySelectorAll('input,select,textarea,button:not(.core-wizard-steps > button):not([data-journey-previous])'))control.disabled=true;kit.status.textContent='Contexto de sólo lectura.';}
  if(saved)kit.status.textContent='Borrador recuperado. La versión guardada se mantiene hasta que apliques los cambios.';
  if(unified){
   header.querySelector('.d-page-description').textContent='Configurá el modelo, prepará los datos y definí tu Case. Las decisiones se ejecutan después desde Decision Studio.';
   root.classList.add('unified-journey','dispatch-upload-pro');
   if(parent)header.append(el('p','Nuevo Case derivado de '+parent.case.label+'. Se conserva el original, sus corridas y aprobaciones. El borrador derivado se conserva en este navegador.','d-metadata'));
   if(row||parent||route.returnView)mountCoreReturn(header,root,scope,{route,navigate,beforeReturn:()=>{if(kit.dirty||parent)store.write(collect());}});
   const localNavigation={matches:target=>scope.active&&sameCoreJourney(route,target),restore:target=>{if(!localNavigation.matches(target))return false;const wanted=(target.coreStep||1)-1;steps.show(wanted,true,{history:'none'});if(steps.active!==wanted){steps.show(steps.active,true,{history:'replace',force:true});let note=header.querySelector('[data-journey-navigation-note]');if(!note){note=el('p','','d-metadata');note.dataset.journeyNavigationNote='';note.role='status';header.querySelector('.d-page-header__copy').append(note);}note.textContent='La etapa anterior requiere una versión de modelo seleccionada y su contrato válido. Se conserva el borrador en la etapa disponible.';}return true;}};
   scope.listen(window,'dation:core-step',()=>header.querySelector('[data-journey-navigation-note]')?.remove());
   window.dationCoreNavigation=localNavigation;scope.own(()=>{if(window.dationCoreNavigation===localNavigation)delete window.dationCoreNavigation;});
   if(row&&editable)existingModelPanel.body.append(button('Crear un Case con otra Model Version',()=>editSource(root,scope,coreSourceRoute(route),navigate,{forceDerive:true})));
   if(row){if(!mathEditable&&editable)horizon.append(button('Crear nuevo Case a partir de este',()=>editSource(root,scope,coreSourceRoute(route),navigate)));}
  }
  if(!fresh){
   await models();
   try{
    const data=await api('/api/platform/logistics-cases/'+route.caseId+'/data',{signal:scope.signal});if(!scope.active)return;
    if(unified){
     existingContractPanel.body.classList.add('journey-existing-preparation');
     const journey=await api('/api/platform/logistics-cases/'+route.caseId+'/journey',{signal:scope.signal});
     existingContractPanel.details.querySelector('.ultimate-disclosure__title').textContent='02 · Data Contract & Preparation';
     if(journey.has_runs){showPublishedContracts(existingContractPanel.body,route.caseId,data.contracts,scope);existingContractPanel.body.append(el('p','Los datos del Case con corridas se consultan sin reemplazar su historial.','d-metadata'),button('Editar datos de origen',()=>editSource(root,scope,coreSourceRoute(route),navigate)));}
     else{const host=el('div');existingContractPanel.body.append(host);scope.own(()=>disposeScope(host));await mountCaseData(host,{route,navigate,embedded:true,guarded:true});}
     const ownerHost=el('section');existingContractPanel.body.append(ownerHost);const ownerWidget=mountResponsibilitySelector(ownerHost,{caseId:route.caseId,stageKey:'data_owner',snapshot:current.responsibilities});scope.own(()=>ownerWidget.dispose());
    }else showPublishedContracts(existingContractPanel.body,route.caseId,data.contracts,scope);existingContractPanel.setStatus('Vigente','complete');existingContractsReady=['transport_demand','transport_resources',...(current.model_version.config_jsonb?.cargo?.input_mode==='catalog'?['order_lines']:[])].every(entity=>!!data.contracts?.[entity]);
   }catch(error){if(error.name==='AbortError')throw error;existingContractPanel.body.append(el('p','No se pudo cargar la vista del contrato: '+error.message,'d-metadata'));existingContractPanel.setStatus('Revisar','warning');}
  }
  if(!scope.active)return;form.inert=false;form.removeAttribute('aria-busy');if(!saved)kit.markSaved();reflect();steps.update();root.dataset.ultimateReady='true';
 }catch(error){if(scope.active)errorBox(root,error,()=>navigate('logistics-case-setup',{...route,replace:true}));}
}
