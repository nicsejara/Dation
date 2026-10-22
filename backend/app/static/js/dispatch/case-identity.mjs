import {scopeFor} from './lifecycle.mjs';
export const CASE_CATEGORIES=[['weekly','Semanal'],['monthly','Mensual'],['extraordinary','Extraordinario'],['simulation','Simulación'],['live_operation','Operación real']];
export function hasCaseExecutions(current){return Object.values(current?.nodes||{}).some(n=>n.run_count>0||n.run_id||n.latest_run_id||n.approved_run_id);}
export function mountCaseIdentity(root,{state,persist,onSave}){
 const scope=scopeFor(root);const form=document.createElement('form');form.className='d-card case-identity';form.dataset.caseIdentity='';form.setAttribute('aria-label','Identidad del Decision Case');
 const title=document.createElement('h2');title.textContent='Identidad del Case';form.append(title);
 state.caseIdentity ||= {label:state.caseContext?.label||'',category:state.decisionCase?.category||null,description:state.decisionCase?.description||null};
 const draft=state.caseIdentity;
 for(const [key,label] of [['label','Nombre del Case'],['category','Categoría'],['description','Descripción (opcional)']]){
  const field=document.createElement('div');field.className='d-field';const caption=document.createElement('label');caption.textContent=label;caption.htmlFor='case-identity-'+key;
  const input=document.createElement(key==='category'?'select':key==='description'?'textarea':'input');input.name=key;input.className='d-input';
  input.id=caption.htmlFor;
  if(key==='category')for(const [value,text] of [['','Elegí una categoría'],...CASE_CATEGORIES]){const option=document.createElement('option');option.value=value;option.textContent=text;input.append(option);}
  else input.maxLength=key==='label'?120:1000;
  input.required=key!=='description';input.value=draft[key]||'';input.disabled=window.dationSession?.identity?.membership?.access_role==='viewer';
  scope.listen(input,'input',()=>{draft[key]=input.value.trim()||null;state.identityDirty=true;persist();});field.append(caption,input);form.append(field);
 }
 const technical=document.createElement('p');technical.className='d-metadata';technical.textContent=state.decisionCase?.id?'Decision Case · DC-'+state.decisionCase.id.slice(0,8).toUpperCase():'El ID técnico se asigna al registrar el Data Pack.';form.append(technical);
 const save=document.createElement('button');save.type='submit';save.className='d-button d-button--secondary';save.textContent='Guardar identidad';save.disabled=window.dationSession?.identity?.membership?.access_role==='viewer';
 const feedback=document.createElement('p');feedback.role='status';feedback.dataset.caseIdentityFeedback='';form.append(save,feedback);
 scope.listen(form,'submit',async event=>{event.preventDefault();save.disabled=true;try{await onSave();feedback.textContent=state.decisionCase?.persisted?'Identidad guardada.':'Identidad preparada. Validá el Data Pack para registrarla.';}catch(error){feedback.textContent=error.message;}finally{if(scope.active)save.disabled=false;}});
 root.querySelector('.d-page-hero').after(form);
 return form;
}
