import {scopeFor} from './lifecycle.mjs';
export const CASE_CATEGORIES=[['weekly','Semanal'],['monthly','Mensual'],['extraordinary','Extraordinario'],['simulation','Simulación'],['live_operation','Operación real']];
export function hasCaseExecutions(current){return Object.values(current?.nodes||{}).some(n=>n.run_count>0||n.run_id||n.latest_run_id||n.approved_run_id);}
export function caseAttributesReady(state={}){const value=state.caseIdentity||state.decisionCase||{};return Boolean(value.label?.trim()&&value.category&&!state.identityDirty&&(state.attributesApplied||state.decisionCase?.attributes_applied_at));}
export function caseDataOwnerReady(state={}){return Boolean(state.workflow?.stages?.data_owner?.owner_eligible&&!state.dataOwnerDraft?.dirty);}
export function mountCaseIdentity(root,{state,persist,onSave,onChanged}){
 const scope=scopeFor(root),viewer=window.dationSession?.identity?.membership?.access_role==='viewer';
 const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n;};
 const form=el('form',null,'d-card case-identity');form.dataset.caseIdentity='';form.setAttribute('aria-label','Atributos del Case');
 const header=el('header',null,'case-identity__header');header.append(el('h2','Atributos del Case'),el('p','Definí el contexto operativo y el responsable de los datos.','d-metadata'));form.append(header);
 const body=el('fieldset',null,'case-identity__body');body.disabled=viewer;
 const identity=el('div',null,'case-identity__fields');identity.setAttribute('role','group');identity.setAttribute('aria-label','Identidad del Case');
 state.caseIdentity ||= {label:state.caseContext?.label||'',category:state.decisionCase?.category||null,description:state.decisionCase?.description||null};
 for(const [key,label] of [['label','Nombre del Case'],['category','Categoría'],['description','Descripción (opcional)']]){
  const field=el('div',null,'d-field'),caption=el('label',label);caption.htmlFor='case-identity-'+key;
  const input=el(key==='category'?'select':key==='description'?'textarea':'input',null,'d-input');input.name=key;input.id=caption.htmlFor;
  if(key==='category')for(const [value,text] of [['','Elegí una categoría'],...CASE_CATEGORIES]){const option=el('option',text);option.value=value;input.append(option);}
  else input.maxLength=key==='label'?120:1000;
  input.required=key!=='description';input.value=state.caseIdentity[key]||'';
  scope.listen(input,'input',()=>{state.caseIdentity={...state.caseIdentity,[key]:input.value.trim()||null};state.identityDirty=true;feedback.textContent='Cambios sin aplicar.';persist();onChanged?.();});field.append(caption,input);identity.append(field);
 }
 const owner=el('section',null,'case-identity__owner');owner.append(el('h3','Responsable de datos'));const ownerHost=el('div');ownerHost.dataset.caseDataOwner='';owner.append(ownerHost);body.append(identity,owner);form.append(body);
 const footer=el('footer',null,'case-identity__footer'),feedback=el('p',null,'d-metadata');feedback.role='status';feedback.dataset.caseIdentityFeedback='';
 const save=el('button','Aplicar','d-button d-button--primary');save.type='submit';footer.append(feedback,save);form.append(footer);
 let applying=false;
 function refresh(){save.disabled=viewer||applying||!state.preflight?.valid;body.disabled=viewer||applying;if(!state.preflight?.valid&&!applying&&!feedback.textContent)feedback.textContent='Cargá y validá Órdenes y Flota para aplicar.';else if(state.preflight?.valid&&feedback.textContent==='Cargá y validá Órdenes y Flota para aplicar.')feedback.textContent='';}
 scope.listen(form,'submit',async event=>{
  event.preventDefault();if(applying||save.disabled||!form.reportValidity())return;applying=true;feedback.setAttribute('role','status');save.setAttribute('aria-busy','true');feedback.textContent='Aplicando atributos y Data Owner…';refresh();
  try{await onSave();if(scope.active)feedback.textContent='Atributos y Data Owner aplicados.';}
  catch(error){if(scope.active){feedback.textContent=error.status===409?'El Case o su Data Owner cambió. Recargá la página, revisá los cambios y volvé a aplicar.':error.message;feedback.setAttribute('role','alert');}}
  finally{if(scope.active){applying=false;save.removeAttribute('aria-busy');refresh();onChanged?.();}}
 });
 root.querySelector('.d-page-hero').after(form);refresh();return {form,refresh};
}
