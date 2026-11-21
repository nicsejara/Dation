import {api} from '../shared.mjs';
import {el,button,field,collapsibleSection,confirmAction} from '../models/forms.mjs';
import {CASE_BLOCKS,CASE_GOALS,caseDefinition,blockErrors,invalidateBlock} from './case-v2-state.mjs';

const HELP=[
 'Identificá la decisión que querés preparar.',
 'Elegí manualmente un modelo y una versión publicada. Visitar la biblioteca no los selecciona.',
 'Definí fechas inclusivas. La modalidad no programa ni ejecuta decisiones automáticamente.',
 'El objetivo guía D1 dentro de su frontera de cobertura. D2 conserva su configuración temporal.',
 'Una preferencia económica y una restricción obligatoria, aplicadas por D1.',
 'Medí resultados reales de D1. El criterio no aprueba ninguna corrida.'
];
export async function mountCaseV2Editor(host,{root,scope,draft,caps,current,onChange,onReviewModel,onOpenModels,onError,onState}){
 const form=el('form',undefined,'j102-form');form.noValidate=true;form.setAttribute('aria-label','Configuración del Decision Case');scope.listen(form,'submit',e=>e.preventDefault());host.append(form);
 const side=el('aside',undefined,'d-card j102-summary');side.setAttribute('aria-label','Resumen de la configuración');host.append(side);
 const blocks=[],inputs=new Map(),statuses=[],errors=[],confirms=[];let busy=false,modelReady=false,modelGeneration=0,modelPage=0,modelTotal=0,query='',family=null;
 const canMath=!current||!!current.permissions?.can_edit_mathematical;
 function add(parent,label,key,index,options={}){const input=field(parent,label,{name:'j102_'+key,value:draft[key],...options});inputs.set(key,input);
  if(current&&(key==='owner'||!canMath&&index>1))input.disabled=true;
  scope.listen(input,input.tagName==='SELECT'?'change':'input',()=>{if(busy)return;draft[key]=input.type==='checkbox'?input.checked:input.value;invalidateBlock(draft,index);if(key==='primary_goal')custom.hidden=draft.primary_goal!=='CUSTOM';onChange();reflect();});return input;}
 function problem(index){return blockErrors(draft,index,{canAssign:!current&&caps.can_assign})||(index===2&&!modelReady?'Confirmá una versión publicada disponible para este acceso.':null);}
 for(const [i,title]of CASE_BLOCKS.entries()){
  const index=i+1,panel=collapsibleSection(form,String(index).padStart(2,'0')+' · '+title,HELP[i],{open:true});panel.details.dataset.caseBlock=String(index);panel.body.classList.add('j102-block-body');blocks.push(panel);
  const error=el('p','','d-field__error');error.role='alert';error.dataset.blockError=String(index);errors.push(error);
  const confirm=button('Confirmar '+title,()=>{const message=problem(index);error.textContent=message||'';if(message){panel.details.open=true;panel.body.querySelector('input:invalid,select:invalid,input,select')?.focus();return;}draft.confirmed[index]=true;onChange();reflect();});confirm.dataset.caseConfirm=String(index);panel.body.append(error,confirm);confirms.push(confirm);statuses.push(panel.setStatus);
 }
 const area=i=>blocks[i-1].body;
 add(area(1),'Nombre del Case','name',1,{required:true,maxLength:120});add(area(1),'Descripción (opcional)','description',1,{type:'textarea',maxLength:1000});
 const picker=el('div',undefined,'j102-model-picker');area(2).prepend(picker);
 const search=field(picker,'Buscar modelos publicados',{name:'j102_model_search',type:'search',maxLength:120}),searchButton=button('Buscar modelos',()=>{query=search.value.trim();modelPage=0;void loadModels();});
 picker.append(searchButton);const model=field(picker,'Logistics Model',{name:'j102_model_id',options:[['','Elegí un modelo publicado']],value:draft.binding?.model_id||''});
 const version=field(picker,'Versión publicada',{name:'j102_version_id',options:[['','Seleccionar versión']],value:''});
 const pager=el('nav',undefined,'j102-picker-pages');pager.setAttribute('aria-label','Páginas de modelos publicados');picker.append(pager);
 const selected=el('div',undefined,'j102-selected-model');picker.append(selected);
 const openModels=button('Abrir biblioteca de modelos',onOpenModels),review=button('Revisar versión seleccionada',()=>{if(draft.binding)onReviewModel(draft.binding);});picker.append(openModels,review);
 scope.listen(search,'keydown',e=>{if(e.key==='Enter'){e.preventDefault();searchButton.click();}});
 scope.listen(model,'change',async()=>{
  if(busy)return;const chosen=model.value,old=draft.binding?.model_id||'';
  if(draft.preparation?.id&&!await confirmAction(root,scope,'Cambiar modelo','La preparación anterior y sus candidatos se conservan. Esta selección necesita una preparación independiente.','Cambiar modelo')){model.value=old;return;}
  draft.binding=null;draft.preparation={id:null,version_id:null};invalidateBlock(draft,2);family=null;modelReady=false;version.replaceChildren(new Option('Seleccionar versión',''));selected.replaceChildren();onChange();reflect();
  if(chosen)await loadFamily(chosen);
 });
 scope.listen(version,'change',async()=>{
  if(busy||!family)return;const chosen=family.versions.find(v=>v.id===version.value);if(!chosen)return;
  if(draft.preparation?.id&&draft.binding?.model_version_id!==chosen.id&&!await confirmAction(root,scope,'Cambiar versión','Los candidatos guardados se conservan en la preparación anterior. No se reutilizarán automáticamente.','Cambiar versión')){version.value=draft.binding.model_version_id;return;}
  if(draft.binding?.model_version_id!==chosen.id)draft.preparation={id:null,version_id:null};
  draft.binding={model_id:family.model.id,model_version_id:chosen.id,configuration_hash:chosen.config_hash,contract_hash:chosen.contract_hash};modelReady=family.model.status==='active'||!!current;
  invalidateBlock(draft,2);showSelected(chosen);onChange();reflect();
 });
 async function loadModels(){const own=++modelGeneration;searchButton.disabled=true;
  try{const data=await api('/api/platform/logistics-models?'+new URLSearchParams({q:query,limit:25,offset:modelPage*25}),{signal:scope.signal});if(!scope.active||own!==modelGeneration)return;
   if(!Array.isArray(data.items)||!Number.isSafeInteger(data.total))throw new Error('La lista de modelos no es válida.');modelTotal=data.total;
   model.replaceChildren(new Option('Elegí un modelo publicado',''),...data.items.filter(m=>m.status==='active'&&m.versions.length).map(m=>new Option(m.name+' · '+m.versions.length+' versiones',m.id)));
   if(draft.binding&&!data.items.some(m=>m.id===draft.binding.model_id))model.append(new Option(family?.model.name||'Modelo seleccionado',draft.binding.model_id));
   model.value=draft.binding?.model_id||'';pager.replaceChildren();
   const prev=button('Modelos anteriores',()=>{modelPage--;void loadModels();}),next=button('Más modelos',()=>{modelPage++;void loadModels();});prev.disabled=modelPage===0;next.disabled=(modelPage+1)*25>=modelTotal;pager.append(prev,el('span',(modelPage*25+1)+'–'+Math.min((modelPage+1)*25,modelTotal)+' de '+modelTotal,'d-metadata'),next);
  }catch(error){if(scope.active&&own===modelGeneration)onError(error);}
  finally{if(scope.active&&own===modelGeneration){searchButton.disabled=busy||!!current;model.disabled=busy||!!current;}}
 }
 async function loadFamily(id){const own=++modelGeneration;modelReady=false;version.disabled=true;
  try{const data=await api('/api/platform/logistics-models/'+id,{signal:scope.signal});if(!scope.active||own!==modelGeneration||busy)return;
   family=data;version.replaceChildren(new Option('Seleccionar versión',''),...data.versions.map(v=>new Option('Versión '+v.version+(v.version===Math.max(...data.versions.map(x=>x.version))?' · más reciente':''),v.id)));
   if(draft.binding?.model_id===id){const chosen=data.versions.find(v=>v.id===draft.binding.model_version_id);if(!chosen||chosen.config_hash!==draft.binding.configuration_hash||chosen.contract_hash!==draft.binding.contract_hash)throw new Error('La versión seleccionada no está disponible o sus huellas no coinciden. Tu borrador conserva la referencia.');
    version.value=chosen.id;modelReady=data.model.status==='active'||!!current;showSelected(chosen);}
  }catch(error){if(scope.active&&own===modelGeneration)onError(error);}
  finally{if(scope.active&&own===modelGeneration){version.disabled=busy||!!current;reflect();}}
 }
 function showSelected(v){draft.modelLabel=(family?.model.name||'Modelo')+' · Versión '+v.version;selected.replaceChildren(el('strong',draft.modelLabel),el('p','Modelo seleccionado · no vinculado definitivamente hasta crear el Case.','d-metadata'));
  const c=v.config_jsonb;selected.append(el('p',[c.operating_role,c.transport_pattern,c.allowed_sources.join(' + '),c.primary_dimension,c.currency_policy.currency].join(' · '),'d-body'),el('p','Publicada: '+v.published_at,'d-metadata'));
  const details=el('details'),summary=el('summary','Identidad de la versión');details.append(summary,el('p',v.id,'d-metadata'),el('p',v.config_hash,'d-metadata'),el('p',v.contract_hash,'d-metadata'));selected.append(details);
 }
 const context=el('div',undefined,'j102-two');area(3).prepend(context);
 add(context,'Modalidad','operating_mode',3,{options:[['OPERATIONAL','Operacional'],['SIMULATION','Simulación']]});add(context,'Horizonte','horizon_type',3,{options:[['DAILY','Diario'],['WEEKLY','Semanal'],['MONTHLY','Mensual'],['CUSTOM','Personalizado']]});
 const start=add(context,'Inicio de planificación','planning_start',3,{type:'date',required:true}),end=add(context,'Fin de planificación','planning_end',3,{type:'date',required:true});
 const preset=button('Proponer fecha de fin',async()=>{if(busy)return;if(draft.planning_end&&!await confirmAction(root,scope,'Actualizar fecha de fin','Se conservará el inicio. Confirmá el ajuste asistido del fin del horizonte.','Actualizar fin'))return;
  const {horizonEnd}=await import('../models/setup-values.mjs');const value=horizonEnd(start.value,inputs.get('horizon_type').value);if(value){end.value=value;end.dispatchEvent(new Event('input',{bubbles:true}));}});preset.disabled=!!current&&!canMath;area(3).append(preset);
 const goal=add(area(4),'Objetivo global','primary_goal',4,{options:CASE_GOALS});
 const custom=el('div',undefined,'j102-two');custom.dataset.customWeights='';custom.hidden=draft.primary_goal!=='CUSTOM';area(4).append(custom);
 for(const [key,label]of [['COST','Costo'],['TRIPS','Viajes'],['SERVICE','Servicio'],['OWN_CAPACITY','Flota propia']]){const input=field(custom,label+' (%)',{name:'j102_weight_'+key,type:'number',value:draft.weights[key]});input.min='0';input.max='100';input.step='0.01';if(current&&!canMath)input.disabled=true;scope.listen(input,'input',()=>{if(busy)return;draft.weights[key]=input.value;invalidateBlock(draft,4);onChange();reflect();});}
 area(4).append(el('p','Las ponderaciones usan la normalización existente y deben sumar exactamente 100 %.','d-metadata'));
 const tie=add(area(5),'Preferir flota propia con costo óptimo idéntico','preferOwn',5,{type:'checkbox'});tie.checked=draft.preferOwn;tie.className='d-check';
 area(5).append(el('p','Primero se demuestra el costo mínimo en la frontera de servicio. Sólo después se maximiza la carga canónica asignada a flota propia. Si no se demuestra el óptimo, se informa sin garantía.','d-metadata'));
 const critical=add(area(5),'Cobertura mínima de demanda crítica (%)','critical',5,{type:'number',required:true,help:'Obligatoria · demanda canónica con prioridad HIGH. Sin HIGH: no aplica.'});critical.min='0';critical.max='100';critical.step='0.01';
 const success=add(area(6),'Cobertura total objetivo (%)','success',6,{type:'number',required:true,help:'Métrica de resultado en una unidad canónica común; nunca autoaprueba D1/D2.'});success.min='0';success.max='100';success.step='0.01';
 let owner;
 if(!current&&caps.can_assign){owner=add(area(6),'Decision Owner','owner',6,{options:[['','Seleccioná una persona elegible']],required:true});await loadOwners();}
 else area(6).append(el('p','Aprobación manual · '+(current?.responsibilities?.stages?.logistics_assignment?.owner?.name||'Responsable según el workflow vigente. Un Admin asigna responsables.'),'d-body'));
 async function loadOwners(){try{const people=[];let offset=0,total=0;do{const page=await api('/api/platform/team?'+new URLSearchParams({candidates:'true',responsibility:'decision_owner',limit:50,offset}),{signal:scope.signal});if(!scope.active)return;people.push(...page.members);total=page.total;offset+=50;if(!page.members.length&&offset<total)throw new Error('El Equipo cambió. Reabrí el selector.');}while(offset<total);
   if(scope.active){owner.replaceChildren(new Option('Seleccioná una persona elegible',''),...people.map(p=>new Option(p.name,p.user_id)));owner.value=draft.owner;}}
  catch(error){if(scope.active)onError(error);}}
 function reflect(){
  for(let i=1;i<=6;i++){const valid=!problem(i),confirmed=!!draft.confirmed[i]&&valid;statuses[i-1](confirmed?'✓ Confirmado':draft.confirmed[i]?'Requiere revisión':'Pendiente',confirmed?'complete':'pending');confirms[i-1].disabled=busy||confirmed||!!current&&(!canMath&&i>1||i===2);}
  review.disabled=busy||!draft.binding;custom.hidden=goal.value!=='CUSTOM';
  side.replaceChildren(el('h2','Resumen del Case','d-card-title'),el('p',draft.name||'Nuevo Decision Case','d-body'),el('p',draft.binding?'Versión elegida manualmente':'Sin modelo seleccionado','d-metadata'),el('p',draft.planning_start&&draft.planning_end?draft.planning_start+' → '+draft.planning_end:'Horizonte pendiente','d-body'),el('p',CASE_GOALS.find(([g])=>g===draft.primary_goal)?.[1]||'Objetivo pendiente','d-body'),el('p',draft.critical+' % demanda crítica HIGH','d-metadata'),el('p','Éxito: cobertura total ≥ '+draft.success+' %','d-metadata'),el('p','Aprobación humana · independiente del KPI','d-metadata'));
  onState?.();
 }
 // Move confirmations after their fields while keeping each block self-contained.
 for(let i=0;i<6;i++)blocks[i].body.append(errors[i],confirms[i]);
 await loadModels();if(draft.binding)await loadFamily(draft.binding.model_id);reflect();
 return {form,reflect,validate(){const failures=CASE_BLOCKS.map((_,i)=>problem(i+1));failures.forEach((message,i)=>{errors[i].textContent=message||'';});return failures;},get complete(){return CASE_BLOCKS.every((_,i)=>draft.confirmed[i+1]&&!problem(i+1));},
  freeze(value){busy=value;for(const n of form.querySelectorAll('input,select,textarea,button')){if(value){n.dataset.wasDisabled=String(n.disabled);n.disabled=true;}else n.disabled=n.dataset.wasDisabled==='true';}reflect();},read:()=>caseDefinition(draft)};
}
