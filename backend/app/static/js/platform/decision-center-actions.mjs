import {mountResponsibilitySelector} from '../dispatch/workflow-responsibility.mjs';
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
   try{const result=await api(BASE+'/'+c.id,{method:'PATCH',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_updated_at:c.updated_at,...(archive?{archived:c.status!=='archived'}:{label:input.value.trim()||null})})});if(modal!==own)return;close();notify(archive?(result.status==='archived'?'Caso archivado. Podés recuperarlo en Archivados.':'Caso restaurado.'):'Caso actualizado.');onChanged(archive?{archived:result.status==='archived',caseId:c.id}:undefined);}
   catch(error){if(modal===own&&!controller.signal.aborted){message.textContent=error.status===409?'El caso cambió. Actualizá el detalle antes de guardar.':error.message;save.disabled=error.status===409;save.removeAttribute('aria-busy');if(error.status===409)actions.append(button('Actualizar detalle',()=>{close();onChanged();}));}}
  });view.open();(input||save).focus();
 }
 function assign(c,stageKey){
  close();
  const dialog=el('dialog',undefined,'d-platform center-dialog'),selector=el('div');dialog.setAttribute('aria-label',stageKey==='data_owner'?'Data Owner':'Decision Owner');dialog.append(selector);root.append(dialog);
  const view=mountDialog({dialog}),controller=new AbortController(),own={dialog,view,controller};modal=own;
  const editor=mountResponsibilitySelector(selector,{caseId:c.id,stageKey,snapshot:c.responsibilities,onCancel:close,onSaved:()=>{if(modal===own){close();notify('Responsable actualizado.');onChanged();}}});
  controller.signal.addEventListener('abort',()=>editor.dispose(),{once:true});dialog.addEventListener('close',()=>{if(modal===own)close();});view.open();selector.querySelector('button')?.click();
 }

 return {edit,assign,close,dispose:close,get isOpen(){return !!modal;}};
}
