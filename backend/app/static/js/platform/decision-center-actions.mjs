import {api} from '../dispatch/shared.mjs';
import {mountDialog} from './components.mjs';
const BASE='/api/platform/decisions';
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function button(text,handler){const n=el('button',text,'d-button d-button--secondary');n.type='button';n.addEventListener('click',handler);return n;}
export function mountCenterActions(root,{onChanged,notify}){
 let modal=null;
 function close(){if(modal){const own=modal;modal=null;own.controller?.abort();own.view.dispose();own.dialog.remove();}}
 function edit(c,archive=false){
  close();const dialog=el('dialog',undefined,'d-platform center-dialog'),title=el('h2',archive?(c.status==='archived'?'Restaurar caso':'Archivar caso'):'Nombre del Decision Case','d-card-title');title.id='center-dialog-title';dialog.setAttribute('aria-labelledby',title.id);
  const form=el('form'),actions=el('div',undefined,'center-actions'),message=el('p');message.role='alert';let input;
  form.append(title);
  if(archive)form.append(el('p',c.status==='archived'?'El caso volverá a estar disponible.':'Se conservarán datos, aprobaciones y corridas. Los trabajos ya aceptados pueden terminar.','d-body'));
  else{const label=el('label','Etiqueta opcional','d-label');input=el('input',undefined,'d-input');input.id='center-case-label';label.htmlFor=input.id;input.value=c.label||'';input.maxLength=120;form.append(label,input,el('p','Dejá el campo vacío para mostrar sólo el ID del caso.','d-metadata'));}
  const save=el('button',archive?(c.status==='archived'?'Restaurar':'Archivar'):'Guardar','d-button d-button--primary');save.type='submit';actions.append(button('Cancelar',close),save);form.append(message,actions);dialog.append(form);root.append(dialog);
  const view=mountDialog({dialog}),controller=new AbortController(),own={dialog,view,controller};modal=own;dialog.addEventListener('close',()=>{if(modal===own)close();});
  form.addEventListener('submit',async event=>{event.preventDefault();save.disabled=true;save.setAttribute('aria-busy','true');
   try{await api(BASE+'/'+c.id,{method:'PATCH',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_updated_at:c.updated_at,...(archive?{archived:c.status!=='archived'}:{label:input.value.trim()||null})})});if(modal!==own)return;close();notify('Caso actualizado.');onChanged();}
   catch(error){if(modal===own&&!controller.signal.aborted){message.textContent=error.status===409?'El caso cambió. Actualizá el detalle antes de guardar.':error.message;save.disabled=error.status===409;save.removeAttribute('aria-busy');if(error.status===409)actions.append(button('Actualizar detalle',()=>{close();onChanged();}));}}
  });view.open();(input||save).focus();
 }
 function assign(c,stageKey){
  close();const stage=c.responsibilities?.stages?.[stageKey]||c.nodes?.find(n=>n.id===stageKey)||{},dataStage=stageKey==='data_preparation';
  const dialog=el('dialog',undefined,'d-platform center-dialog'),form=el('form'),title=el('h2',dataStage?'Responsable de los datos':'Responsables de la decisión','d-card-title');title.id='center-assignment-title';dialog.setAttribute('aria-labelledby',title.id);
  const label=el('label','Buscar personas por nombre o email','d-label'),search=el('input',undefined,'d-input');search.type='search';search.maxLength=120;search.id='center-people-search';label.htmlFor=search.id;
  const count=el('p',undefined,'d-metadata'),message=el('p');message.role='alert';const fields={};
  form.append(title,el('p','Sólo Admin puede asignar. Las personas deben estar activas y tener la responsabilidad correspondiente en este workspace.','d-body'),label,search);const lookup=button('Buscar personas',()=>loadPeople());form.append(lookup,count);
  for(const [key,text,group]of [['owner','Responsable',dataStage?'data':'decision_owner'],...(!dataStage?[['approver','Aprobador asignado','approver']]:[])]){
   const l=el('label',text,'d-label'),select=el('select',undefined,'d-input');select.id='center-'+key+'_user_id';l.htmlFor=select.id;select.dataset.initial=stage[key]?.id||'';fields[key]={select,group,person:stage[key]};form.append(l,select);
  }
  const actions=el('div',undefined,'center-actions'),save=el('button','Guardar responsables','d-button d-button--primary');save.type='submit';actions.append(button('Cancelar',close),save);form.append(message,actions);dialog.append(form);root.append(dialog);
  const view=mountDialog({dialog}),controller=new AbortController(),own={dialog,view,controller};modal=own;dialog.addEventListener('close',()=>{if(modal===own)close();});let version=0;
  async function loadPeople(){const request=++version;lookup.disabled=save.disabled=true;message.textContent='';
   try{const entries=Object.entries(fields),results=await Promise.all(entries.map(([,field])=>api('/api/platform/team?'+new URLSearchParams({candidates:'true',responsibility:field.group,q:search.value.trim(),limit:50}),{signal:controller.signal})));if(modal!==own||request!==version)return;
    for(let i=0;i<entries.length;i++){const [,field]=entries[i],value=field.select.value||field.select.dataset.initial||'',selected=field.people?.get(value)||field.person;delete field.select.dataset.initial;field.select.replaceChildren();const none=el('option','Sin asignar');none.value='';field.select.append(none);const people=new Map(results[i].members.map(p=>[p.user_id,{id:p.user_id,name:p.name}]));if(value&&!people.has(value)&&selected?.id===value)people.set(value,selected);field.people=people;
     for(const person of people.values()){const option=el('option',person.name+(person.active===false?' (inactivo)':''));option.value=person.id;field.select.append(option);}field.select.value=value;
    }count.textContent='Si falta alguien, verificá sus responsabilidades en Equipo o refiná la búsqueda.';save.disabled=false;
   }catch(error){if(modal===own&&!controller.signal.aborted)message.textContent=error.message;}finally{if(modal===own&&request===version)lookup.disabled=false;}
  }
  search.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();loadPeople();}});
  form.addEventListener('submit',async event=>{event.preventDefault();save.disabled=true;message.textContent='';
   try{await api(BASE+'/'+c.id+'/responsibilities/'+stageKey,{method:'PUT',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_updated_at:stage.updated_at??stage.assignment_updated_at??null,owner_user_id:fields.owner.select.value||null,approver_user_id:fields.approver?.select.value||null})});if(modal!==own)return;close();notify('Responsables actualizados.');onChanged();}
   catch(error){if(modal===own&&!controller.signal.aborted){message.textContent=error.status===409?'La asignación cambió o la persona ya no está disponible. Actualizá el detalle antes de guardar.':error.message;save.disabled=error.status===409;if(error.status===409)actions.append(button('Actualizar detalle',()=>{close();onChanged();}));}}
  });view.open();search.focus();loadPeople();
 }
 return {edit,assign,close,dispose:close,get isOpen(){return !!modal;}};
}
