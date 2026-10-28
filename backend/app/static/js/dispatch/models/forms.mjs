// T3 composition of Dation's existing form/control classes, not a second design system.
import {mountDialog} from '../../platform/components.mjs';
import {draftSignature} from './setup-values.mjs';
export {percentToRatio,ratioToPercent} from './setup-values.mjs';
export const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
export function button(text,run,kind='secondary'){const b=el('button',text,'d-button d-button--'+kind);b.type='button';if(run)b.addEventListener('click',run);return b;}
export function field(parent,label,{name,type='text',value='',options,required=false,maxLength,help,readOnly=false}={}){
 const host=el('div',undefined,'d-field'),id='ultimate-'+name,caption=el('label',label,'d-field__label');caption.htmlFor=id;
 const input=el(options?'select':type==='textarea'?'textarea':'input',undefined,options?'d-select':type==='textarea'?'d-textarea':'d-input');input.id=id;input.name=name;
 if(!options&&type!=='textarea')input.type=type;
 if(options)for(const [v,text]of options){const o=el('option',text);o.value=v;input.append(o);}
 input.value=value??'';input.required=required;if(maxLength)input.maxLength=maxLength;if(readOnly)input.readOnly=true;
 const error=el('p',undefined,'d-field__error');error.id=id+'-error';error.dataset.errorFor=name;
 const hint=el('p',help||'', 'd-field__help');hint.id=id+'-help';input.setAttribute('aria-describedby',hint.id+' '+error.id);
 host.append(caption,input,hint,error);parent.append(host);return input;
}
export function section(form,title,copy){const node=el('fieldset',undefined,'d-card ultimate-section'),legend=el('legend',title,'d-card-title');node.append(legend);if(copy)node.append(el('p',copy,'d-metadata'));const body=el('div',undefined,'ultimate-grid');node.append(body);form.append(node);return body;}
export function choices(parent,title,name,options,values){
 const box=el('fieldset',undefined,'ultimate-choices');box.append(el('legend',title,'d-field__label'));
 for(const [v,text]of options){const label=el('label',undefined,'d-choice'),input=el('input',undefined,'d-check');input.type='checkbox';input.name=name;input.value=v;input.checked=values.includes(v);label.append(input,el('span',text,'d-choice__copy'));box.append(label);}
 parent.append(box);return ()=>[...box.querySelectorAll('input:checked')].map(n=>n.value);
}
export function pageHeader(root,title,copy){const header=el('header',undefined,'d-page-header'),text=el('div',undefined,'d-page-header__copy');text.append(el('p','DDA Logística','d-eyebrow'),el('h1',title,'d-page-title'),el('p',copy,'d-page-description'));header.append(text);root.append(header);return header;}

export function draftStore(kind,id='new'){
 const identity=window.dationSession?.identity,key=['dation.ultimate.setup.v1',identity?.membership?.workspace_id,identity?.profile?.id,kind,id].join('.');
 return {read(){try{return JSON.parse(sessionStorage.getItem(key)||'null');}catch{return null;}},write(value){try{sessionStorage.setItem(key,JSON.stringify(value));}catch{}},clear(){try{sessionStorage.removeItem(key);}catch{}}};
}

export function mountForm(root,scope,{initial,store,onSave,onReload,submitLabel='Guardar cambios'}){
 const form=el('form',undefined,'ultimate-form');form.noValidate=true;form.setAttribute('aria-label',submitLabel);
 const errors=el('div',undefined,'ultimate-errors');errors.hidden=true;errors.role='alert';errors.tabIndex=-1;form.append(errors);root.append(form);
 const footer=el('footer',undefined,'d-card ultimate-footer'),status=el('p','Sin cambios pendientes.','d-metadata');status.role='status';status.setAttribute('aria-live','polite');
 const submit=el('button',submitLabel,'d-button d-button--primary');submit.type='submit';footer.append(status,submit);
 let collect=()=>initial,check=()=>({}),busy=false,clean=draftSignature(initial),dirty=false;
 const saveDraft=()=>{const value=collect();dirty=draftSignature(value)!==clean;if(dirty)store?.write(value);else store?.clear();status.textContent=dirty?'Cambios sin guardar. El borrador se conserva en este navegador.':'Sin cambios pendientes.';};
 const inline=(name,message)=>{const input=form.elements.namedItem(name);const error=form.querySelector('[data-error-for="'+name+'"]');if(error)error.textContent=message||'';if(input?.setAttribute){if(message){input.setAttribute('aria-invalid','true');const details=input.closest('details');if(details)details.open=true;}else input.removeAttribute('aria-invalid');}};
 const showErrors=values=>{
  for(const item of form.querySelectorAll('[data-error-for]'))inline(item.dataset.errorFor,'');
  errors.replaceChildren();const entries=Object.entries(values).filter(([,v])=>v);errors.hidden=!entries.length;
  if(entries.length){errors.append(el('h2','Revisá estos campos','d-card-title'));for(const [name,message]of entries){inline(name,message);const link=el('a',message);link.href='#ultimate-'+name;link.addEventListener('click',e=>{e.preventDefault();form.elements.namedItem(name)?.focus?.();});errors.append(link);}errors.focus();}
 };
 const conflict=message=>{status.textContent=message;status.role='alert';if(onReload&&!footer.querySelector('[data-conflict-reload]')){const b=button('Descartar borrador y recargar',async()=>{if(await confirmAction(root,scope,'Descartar el borrador','Se cargarán los datos guardados. Tus cambios pendientes se descartarán.','Descartar y recargar')){store?.clear();dirty=false;await onReload();}});b.dataset.conflictReload='true';footer.append(b);}};
 scope.listen(form,'input',saveDraft);scope.listen(form,'change',saveDraft);
 scope.listen(form,'focusout',event=>{const n=event.target;if(n.matches?.('input,select,textarea'))inline(n.name,n.validity.valid?'':n.validationMessage);});
 scope.listen(form,'submit',async event=>{
  event.preventDefault();if(busy)return;
  const values={};for(const n of form.querySelectorAll('input,select,textarea'))if(!n.disabled&&!n.validity.valid)values[n.name]=n.validationMessage;
  Object.assign(values,check());showErrors(values);if(Object.values(values).some(Boolean))return;
  busy=true;submit.disabled=true;submit.setAttribute('aria-busy','true');status.textContent='Guardando…';
  try{await onSave(collect());if(scope.active){store?.clear();dirty=false;clean=draftSignature(collect());status.textContent='Cambios guardados.';}}
  catch(error){if(scope.active){status.textContent=error.status===409?'La versión guardada cambió. Tu borrador se conserva; revisá la versión actual antes de reintentar.':error.message;status.role='alert';
   if(error.status===409)conflict(status.textContent);
  }}finally{busy=false;if(scope.active){submit.disabled=false;submit.removeAttribute('aria-busy');}}
 });
 const beforeUnload=e=>{if(dirty){e.preventDefault();e.returnValue='';}};scope.listen(window,'beforeunload',beforeUnload);
 const leave=()=>!dirty||window.confirm('Tenés cambios sin guardar. El borrador se conservará en este navegador. ¿Querés salir?');
 window.dationUltimateCanLeave=leave;scope.own(()=>{if(window.dationUltimateCanLeave===leave)delete window.dationUltimateCanLeave;});
 return {form,footer,status,submit,conflict,setCollector(fn,validate=()=>({})){collect=fn;check=validate;dirty=draftSignature(collect())!==clean;},finish(){form.append(footer);},markSaved(){store?.clear();dirty=false;clean=draftSignature(collect());},get dirty(){return dirty;},showErrors};
}

export function confirmAction(root,scope,title,copy,action='Confirmar'){
 return new Promise(resolve=>{
  const dialog=el('dialog',undefined,'d-modal'),header=el('h2',title,'d-modal__title');header.id='ultimate-dialog-title';dialog.setAttribute('aria-labelledby',header.id);
  const body=el('div',undefined,'d-modal__body'),actions=el('div',undefined,'d-modal__actions');body.append(header,el('p',copy,'d-body'));
  const cancel=button('Cancelar',()=>mounted.close('cancel')),yes=button(action,()=>mounted.close('confirm'),'primary');actions.append(cancel,yes);dialog.append(body,actions);root.append(dialog);
  const mounted=mountDialog({dialog,initialFocus:cancel});let settled=false;
  const finish=value=>{if(settled)return;settled=true;mounted.dispose();dialog.remove();resolve(value);};
  dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'),{once:true});scope.own(()=>finish(false));mounted.open();
 });
}

