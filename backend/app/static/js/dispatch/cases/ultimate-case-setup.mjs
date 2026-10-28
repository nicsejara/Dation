import {api,post,errorBox} from '../shared.mjs';
import {scopeFor} from '../lifecycle.mjs';
import {ensureStylesheet} from '../styles.mjs';
import {loadingState} from '../../platform/components.mjs';
import {el,button,field,section,pageHeader,draftStore,mountForm} from '../models/forms.mjs';
import {mountPolicy,policyInputValues} from '../models/policy.mjs';
import {ROLES,DIMENSIONS} from '../models/index.mjs';
import {horizonEnd} from '../models/setup-values.mjs';

export async function mountCaseSetup(root,{route,navigate,onContext}){
 delete root.dataset.ultimateReady;
 const scope=scopeFor(root);await ensureStylesheet('ultimate-foundation-styles','/static/css/ultimate-foundation.css','t3-v1');if(!scope.active)return;
 root.className='dispatch d-platform ultimate-foundation';root.append(loadingState('Recuperando contexto del Case…'));
 try{
  const fresh=!route.caseId,[caps,current]=await Promise.all([api('/api/platform/ultimate-foundation/capabilities',{signal:scope.signal}),fresh?Promise.resolve(null):api('/api/platform/logistics-cases/'+route.caseId+'/context',{signal:scope.signal})]);
  if(!scope.active)return;if(fresh&&!caps.can_create_case)throw Object.assign(new Error('La creación de Cases no está disponible para este acceso.'),{status:403});
  if(current)onContext?.(current);
  const row=current?.case,store=draftStore('case',route.caseId||'new'),saved=store.read(),policy=current?.planning_context.case_policy||{version:1,primary_goal:'MINIMIZE_COST',guardrails:[],preferences:[]};
  const initial={id:row?.id||crypto.randomUUID(),name:row?.label||'',description:row?.description||'',model_id:current?.model.id||route.modelId||'',logistics_model_version_id:row?.logistics_model_version_id||'',
   planning_start:row?.planning_start||'',planning_end:row?.planning_end||'',horizon_type:row?.horizon_type||'WEEKLY',operating_mode:row?.operating_mode||'OPERATIONAL',expected_updated_at:row?.updated_at||null,decision_owner_user_id:'',
   owners:Object.fromEntries(['logistics_assignment','logistics_scheduling'].map(id=>[id,{id:current?.responsibilities.stages[id].owner?.id||'',updated_at:current?.responsibilities.stages[id].updated_at||null}])),policy_values:policyInputValues(policy)};
  const draft=saved||initial,editable=fresh||current.permissions.can_edit,mathEditable=fresh||current.permissions.can_edit_mathematical,canAssign=fresh?caps.can_assign:current.permissions.can_assign;
  root.replaceChildren();const header=pageHeader(root,fresh?'Crear Decision Case':row.label||'Contexto del Case','El Case guarda el objetivo, el horizonte y la versión del Model. Podés crearlo antes de cargar archivos.');header.append(button('Logistics Models',()=>navigate('logistics-models',{modelId:null})));
  if(row){header.append(button('Mapa de decisiones',()=>navigate('logistics-map',{caseId:row.id,nodeId:null,runId:null})));try{const inputs=await api('/api/platform/logistics-cases/'+row.id+'/data',{signal:scope.signal});if(scope.active&&(inputs.enabled||inputs.entries.length))header.append(button('Administrar datos del Case',()=>navigate('logistics-case-data',{caseId:row.id})));}catch(error){if(error.name==='AbortError')throw error;}}
  if(row){const savedCard=el('section',undefined,'d-card ultimate-saved-context');savedCard.append(el('h2','Contexto guardado','d-card-title'),el('p','Versión '+current.model_version.version+' de '+current.model.name+' · '+row.planning_start+' a '+row.planning_end,'d-body'),el('p','Data Pack inicial: '+(current.entry_count?'datos vinculados':'sin archivos')+'. El contexto se conserva al recargar.','d-metadata'));
   if(row.context_frozen_at)savedCard.append(el('p','El horizonte y la política quedaron congelados con la primera admisión. El nombre, la descripción y los responsables conservan sus reglas de edición.','d-body'));root.append(savedCard);}
  const kit=mountForm(root,scope,{initial,store,submitLabel:fresh?'Crear Case':'Guardar contexto',onReload:()=>navigate('logistics-case-setup',{caseId:route.caseId,replace:true}),onSave:async value=>{
   let result;
   if(fresh){result=await post('/api/platform/logistics-cases',{id:value.id,name:value.name,description:value.description||null,logistics_model_version_id:value.logistics_model_version_id,
     planning_start:value.planning_start,planning_end:value.planning_end,horizon_type:value.horizon_type,operating_mode:value.operating_mode,case_policy:policyUI.read(),decision_owner_user_id:canAssign?value.decision_owner_user_id||null:null},{signal:scope.signal});}
   else{
    const body={expected_updated_at:value.expected_updated_at,name:value.name,description:value.description||null};
    if(mathEditable)Object.assign(body,{planning_start:value.planning_start,planning_end:value.planning_end,horizon_type:value.horizon_type,operating_mode:value.operating_mode,case_policy:policyUI.read()});
    if(canAssign)body.owner_updates=Object.entries(value.owners).filter(([id,o])=>o.id!==(current.responsibilities.stages[id].owner?.id||'')).map(([id,o])=>({node_id:id,owner_user_id:o.id||null,expected_updated_at:o.updated_at}));
    result=await api('/api/platform/logistics-cases/'+row.id+'/context',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:scope.signal});
   }
   kit.markSaved();if(scope.active){onContext?.(result);await navigate(fresh?'logistics-map':'logistics-case-setup',{caseId:result.case.id,nodeId:null,runId:null,replace:true});}
  }});
  const form=kit.form;form.inert=true;form.setAttribute('aria-busy','true');
  const identity=section(form,'Identidad del Case'),name=field(identity,'Nombre del Case',{name:'case_name',value:draft.name,required:true,maxLength:120}),description=field(identity,'Descripción (opcional)',{name:'case_description',type:'textarea',value:draft.description,maxLength:1000});
  const modelGroup=section(form,'Model y versión publicada','La versión elegida queda ligada al Case y no puede reemplazarse después de crear el contexto.');
  let selectedModel=current?.model.id||draft.model_id,selectedVersion=draft.logistics_model_version_id,modelsGeneration=0;
  const modelSearch=field(modelGroup,'Buscar Model por nombre',{name:'case_model_search',type:'search',maxLength:120}),modelSelect=field(modelGroup,'Logistics Model',{name:'model_id',options:[['','Elegí un Model']],required:true}),versionSelect=field(modelGroup,'Model Version',{name:'model_version_id',options:[['','Elegí una versión publicada']],required:true});
  const summary=el('p',undefined,'d-field__help');modelGroup.append(summary);
  async function versions(id){const own=++modelsGeneration;versionSelect.disabled=true;const data=await api('/api/platform/logistics-models/'+id,{signal:scope.signal});if(!scope.active||own!==modelsGeneration)return;
   versionSelect.replaceChildren();const empty=el('option','Elegí una versión publicada');empty.value='';versionSelect.append(empty);
   for(const v of data.versions){const option=el('option','Versión '+v.version);option.value=v.id;versionSelect.append(option);}
   versionSelect.value=selectedVersion;versionSelect.disabled=!fresh;const render=()=>{const v=data.versions.find(v=>v.id===versionSelect.value);summary.textContent=v?[ROLES.find(([k])=>k===v.config_jsonb.operating_role)?.[1],DIMENSIONS.find(([k])=>k===v.config_jsonb.primary_dimension)?.[1],v.config_jsonb.currency_policy.currency].filter(Boolean).join(' · '):'Elegí una versión publicada. Los borradores no se pueden vincular.';};scope.listen(versionSelect,'change',render);render();
  }
  async function models(){const own=++modelsGeneration;const result=await api('/api/platform/logistics-models?'+new URLSearchParams({q:modelSearch.value,limit:50}),{signal:scope.signal});if(!scope.active||own!==modelsGeneration)return;
   modelSelect.replaceChildren();const placeholder=el('option','Elegí un Model');placeholder.value='';modelSelect.append(placeholder);for(const m of result.items.filter(x=>x.versions.length)){const o=el('option',m.name);o.value=m.id;modelSelect.append(o);}
   if(selectedModel&&!result.items.some(m=>m.id===selectedModel)){const data=await api('/api/platform/logistics-models/'+selectedModel,{signal:scope.signal});if(!scope.active)return;const o=el('option',data.model.name);o.value=selectedModel;modelSelect.append(o);}
   modelSelect.value=selectedModel;modelSelect.disabled=!fresh;if(selectedModel)await versions(selectedModel);
  }
  const search=button('Buscar Models',()=>models().catch(e=>{if(scope.active){summary.textContent=e.message;summary.role='alert';}}));modelGroup.append(search);modelSearch.disabled=search.disabled=!fresh;
  scope.listen(modelSelect,'change',()=>{selectedModel=modelSelect.value;selectedVersion='';if(selectedModel)versions(selectedModel).catch(e=>{if(scope.active){summary.textContent=e.message;summary.role='alert';}});else versionSelect.replaceChildren();});
  const horizon=section(form,'Horizonte de planificación','Fechas inclusivas que delimitan las salidas de la decisión. El tipo ofrece un punto de partida; se guardan las fechas concretas.');
  const mode=field(horizon,'Operating Mode',{name:'operating_mode',options:[['OPERATIONAL','Operacional'],['SIMULATION','Simulación']],value:draft.operating_mode}),type=field(horizon,'Tipo de horizonte',{name:'horizon_type',options:[['DAILY','Diario'],['WEEKLY','Semanal'],['MONTHLY','Mensual'],['CUSTOM','Personalizado']],value:draft.horizon_type});
  const start=field(horizon,'Inicio de planificación',{name:'planning_start',type:'date',value:draft.planning_start,required:true}),end=field(horizon,'Fin de planificación',{name:'planning_end',type:'date',value:draft.planning_end,required:true});
  const preset=()=>{const value=horizonEnd(start.value,type.value);if(value){end.value=value;end.dispatchEvent(new Event('input',{bubbles:true}));}};scope.listen(type,'change',preset);scope.listen(start,'change',preset);
  for(const input of [mode,type,start,end])input.disabled=!mathEditable;
  const policyUI=mountPolicy(form,scope,policy,{readOnly:!mathEditable,draftValues:draft.policy_values});
  const ownersGroup=section(form,'Decision Owner','La asignación usa las responsabilidades vigentes del Equipo. Sólo un Admin puede cambiar responsables.');
  const owners={};
  if(fresh)owners.initial=field(ownersGroup,'Decision Owner inicial (D1 y D2)',{name:'decision_owner_user_id',options:[['','Elegí un Decision Owner']],value:draft.decision_owner_user_id,required:canAssign});
  else for(const [id,label]of [['logistics_assignment','Decision Owner · Asignación de carga'],['logistics_scheduling','Decision Owner · Planificación de despachos']])owners[id]=field(ownersGroup,label,{name:'owner_'+id,options:[['','Sin asignar']],value:draft.owners[id].id});
  if(canAssign){const people=[];let offset=0,total=0;do{const result=await api('/api/platform/team?'+new URLSearchParams({candidates:'true',responsibility:'decision_owner',limit:50,offset}),{signal:scope.signal});if(!scope.active)return;people.push(...result.members);offset+=50;total=result.total;if(offset<total&&!result.members.length)throw new Error('El Equipo cambió. Recargá la lista de personas.');}while(offset<total);
   for(const [id,control]of Object.entries(owners)){const currentId=id==='initial'?draft.decision_owner_user_id:draft.owners[id].id;for(const person of people){const option=el('option',person.name+' · '+person.email);option.value=person.user_id;control.append(option);}if(currentId&&!people.some(p=>p.user_id===currentId)){const option=el('option',(current?.responsibilities.stages[id]?.owner?.name||'Responsable anterior')+' (no elegible)');option.value=currentId;option.disabled=true;control.append(option);}control.value=currentId;}
   if(!people.length)ownersGroup.append(el('p','No hay personas elegibles. Revisá las responsabilidades en Equipo antes de asignar.','d-field__help'));
  }else{for(const [id,control]of Object.entries(owners)){const person=current?.responsibilities.stages[id]?.owner;if(person){const option=el('option',person.name);option.value=person.id;control.append(option);control.value=person.id;}control.disabled=true;}ownersGroup.append(el('p',fresh?'Podés crear el Case con Owner pendiente. Un Admin debe completar la asignación antes de ejecutar decisiones.':'La asignación está administrada por un Admin.','d-field__help'));}
  const collect=()=>({id:draft.id,name:name.value.trim(),description:description.value.trim(),model_id:modelSelect.value,logistics_model_version_id:versionSelect.value,
   planning_start:start.value,planning_end:end.value,horizon_type:type.value,operating_mode:mode.value,expected_updated_at:draft.expected_updated_at,
   decision_owner_user_id:owners.initial?.value||'',owners:Object.fromEntries(['logistics_assignment','logistics_scheduling'].map(id=>[id,{id:owners[id]?.value||draft.owners[id].id,updated_at:draft.owners[id].updated_at}])),policy_values:policyUI.draft()});
  kit.setCollector(collect,()=>{const errors=mathEditable?policyUI.validate():{};if(start.value&&end.value&&start.value>end.value)errors.planning_end='La fecha de fin debe ser igual o posterior a la de inicio.';if(fresh&&!versionSelect.value)errors.model_version_id='Elegí una Model Version publicada.';if(fresh&&canAssign&&!owners.initial.value)errors.decision_owner_user_id='Elegí un Decision Owner activo y elegible.';return errors;});
  kit.finish();if(!editable){for(const control of form.querySelectorAll('input,select,textarea,button'))control.disabled=true;kit.status.textContent='Contexto de sólo lectura.';}
  if(saved)kit.status.textContent='Borrador recuperado. La versión guardada se mantiene hasta que apliques los cambios.';
  await models();
  if(!scope.active)return;form.inert=false;form.removeAttribute('aria-busy');if(!saved)kit.markSaved();root.dataset.ultimateReady='true';
 }catch(error){if(scope.active)errorBox(root,error,()=>navigate('logistics-case-setup',{caseId:route.caseId,modelId:route.modelId,replace:true}));}
}
