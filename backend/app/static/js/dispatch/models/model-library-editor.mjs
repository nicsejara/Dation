import {api} from '../shared.mjs';
import {mountDialog} from '../../platform/components.mjs';
import {el,button,confirmAction} from './forms.mjs';
import {mountModelFields} from './model-fields.mjs';
import {mountHistorical} from './model-historical-view.mjs';
import {previewV2Draft} from './planning-model.mjs';
import {fingerprint} from './cargo-guided-state.mjs';
import {draftContent,lockWorkingCopy} from './model-library-state.mjs';
import {modelController} from './model-library-controller.mjs';
import {libraryFooter} from './model-library.mjs';

export async function mountLibraryEditor(root,{route,scope,copies,back,go,loadModel,shell}){
 if(route.modelWorkId)await lockWorkingCopy(route.modelWorkId,scope);if(!scope.active)return;
 let record=route.modelWorkId?copies.read(route.modelWorkId):null;
 if(route.modelWorkId&&!record)throw Object.assign(new Error('El borrador no está disponible para esta cuenta en este navegador. No se creó otro en su lugar.'),{status:404});
 if(record?.modelId&&route.modelId==='new')return go({modelId:record.modelId,modelWorkId:record.workId,modelView:'edit',replace:true});
 const existing=route.modelId!=='new'?await loadModel():null;if(!scope.active)return;
 if(existing?.model.status==='archived')throw Object.assign(new Error('El modelo archivado se conserva en consulta histórica.'),{status:409});
 if(record&&(record.modelId?record.modelId!==route.modelId:route.modelId!=='new'))throw new Error('La identidad de la copia local no corresponde al modelo solicitado.');
 if(!record){
  const model=existing.model,draft={id:model.id,name:model.name,description:model.description||'',status:model.status,expected_revision:model.revision,configuration:structuredClone(model.draft_config_jsonb)};
  record=copies.write({workId:crypto.randomUUID(),modelId:model.id,draft,initialDraft:draft,savedDraft:draft,savedWhere:'server'},0);
  return go({modelId:model.id,modelWorkId:record.workId,modelView:'edit',replace:true});
 }
 if(record.publishedVersionId)return go({modelId:record.modelId,modelVersionId:record.publishedVersionId,modelView:'review',replace:true});
 if(!record.initialDraft)record=copies.write({...record,initialDraft:record.draft},record.recordRevision);
 shell(existing?'Preparar nueva versión':'Crear Logistics Model','Configurá una operación reusable. Publicar una versión no crea ningún Decision Case.');
 const form=el('form',undefined,'ultimate-form j101-editor');form.noValidate=true;form.setAttribute('aria-label','Configuración del Logistics Model');root.append(form);
 const historical=record.draft.configuration.version!==2;
 const fields=historical?{...mountHistorical(form,record.draft,{reason:'Contrato histórico en consulta. Creá un modelo nuevo para una configuración diferente.'}),historical:true}:mountModelFields(form,scope,record.draft,{wizard:true});
 const feedback=el('p','','model-wizard-feedback');feedback.role='status';feedback.setAttribute('aria-live','polite');feedback.dataset.libraryFeedback='';root.append(feedback);
 const save=button('Guardar borrador',()=>runSave()),publish=button('Publicar modelo',()=>runPublish(),'primary'),retryPreview=button('Reintentar validación',()=>preview(true)),reload=button('Descartar copia local y recargar servidor',async()=>{
  if(busy||!existing||controller.record.publishIntent)return;
  if(!await confirmAction(root,scope,'Recargar borrador del servidor','Se descartarán los cambios locales. Las versiones publicadas y los Cases se conservan.','Descartar y recargar'))return;
  copies.remove(record.workId,controller.record.recordRevision);allowLeave=true;await go({modelId:existing.model.id,modelView:'edit',replace:true});
 });
 save.dataset.librarySave='';publish.dataset.libraryPublish='';retryPreview.hidden=true;reload.hidden=true;
 const footer=libraryFooter(root,{back,status:'Borrador sin publicar',notice:'No se crea ni se vincula un Case desde esta pantalla.',actions:[retryPreview,reload,save,publish]});
 const controller=modelController({record,saveRecord:value=>{const next=copies.write(value,value.recordRevision);record=next;return next;},request:(path,method,body)=>api(path,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:scope.signal})});
 let busy=false,allowLeave=false,previewGeneration=0,timer=null,configKey='',compiledKey='',previewPending=false,storageFailure=false;
 const readCurrent=()=>({...fields.read(),expected_revision:controller.record.draft.expected_revision});
 const clean=()=>draftContent(controller.record.savedDraft||controller.record.initialDraft),dirty=()=>!historical&&draftContent(readCurrent())!==clean();
 function say(message,error=false){feedback.textContent=message;feedback.role=error?'alert':'status';}
 function sync(){
  const complete=fields.sectionCompletion?.()||[];footer.state.textContent=historical||fields.historical?'Consulta histórica':complete.filter(Boolean).length+' de 5 bloques confirmados';
  save.disabled=busy||historical||!!fields.historical||!!controller.record.publishIntent||storageFailure;
  publish.disabled=busy||historical||!!fields.historical||storageFailure||(!controller.record.publishIntent&&(controller.pending||!fields.canPublish?.()||compiledKey!==fingerprint(fields.read().configuration)));
  save.textContent=controller.record.createIntent||controller.record.saveIntent?'Reintentar guardado pendiente':'Guardar borrador';publish.textContent=controller.record.publishIntent?'Reintentar publicación pendiente':'Publicar modelo';
  for(const control of [save,publish])control.setAttribute('aria-busy',String(busy));
 }
 function persistRecovery(){
  if(busy||historical||fields.historical||controller.pending)return;
  const value=readCurrent();
  try{if(JSON.stringify(value)!==JSON.stringify(controller.record.draft))controller.updateDraft(value);storageFailure=false;}
  catch(error){storageFailure=true;say(error.message,true);}
 }
 function changed(){
  persistRecovery();const key=historical||fields.historical?'':fingerprint(fields.read().configuration);
  if(key&&key!==configKey){configKey=key;compiledKey='';clearTimeout(timer);timer=scope.timeout(()=>preview(),300);}
  sync();
 }
 async function preview(focus=false){
  if(historical||fields.historical||busy||controller.pending)return;
  const own=++previewGeneration,key=fingerprint(fields.read().configuration);compiledKey='';retryPreview.hidden=true;
  if(!fields.sectionValidity().slice(1).every(Boolean)){sync();return;}
  previewPending=true;sync();
  try{const data=await previewV2Draft(fields.read().configuration,scope.signal);if(!scope.active||own!==previewGeneration||busy||controller.pending||key!==fingerprint(fields.read().configuration))return;
   if(data.provisional!==true||!data.contracts)throw new Error('La validación no corresponde al borrador actual.');
   compiledKey=key;fields.setCompiled(data);persistRecovery();
  }catch(error){if(scope.active&&own===previewGeneration&&!busy&&!controller.pending){fields.showServerError(error.message,{focus});retryPreview.hidden=false;say(error.message,true);}}
  finally{if(scope.active&&own===previewGeneration){previewPending=false;sync();}}
 }
 function freeze(){const controls=[...form.querySelectorAll('input,select,textarea,button')].map(n=>[n,n.disabled]);for(const [n]of controls)n.disabled=true;return ()=>{if(!controller.pending)for(const [n,disabled]of controls)n.disabled=disabled;};}
 async function runSave({navigateAfter=true}={}){
  if(busy||historical||fields.historical)return false;
  persistRecovery();if(storageFailure)return false;const valid=Object.keys(fields.validate()).length===0;busy=true;const restore=freeze();sync();
  try{const result=await controller.save({valid});
   say(result.where==='server'?'Borrador guardado en el servidor. No está publicado.':'Borrador guardado en este navegador para esta cuenta. No está en el servidor ni publicado.');
   if(navigateAfter&&result.where==='server'){allowLeave=true;await go({modelId:controller.record.modelId,modelWorkId:record.workId,modelView:'edit',replace:true});}return true;
  }catch(error){if(scope.active){say(error.status===409?'Conflicto: el servidor cambió. Tu copia y revisión original se conservan; recargá explícitamente antes de continuar.':error.message,true);reload.hidden=!existing||!!controller.record.publishIntent;}return false;}
  finally{busy=false;if(scope.active){restore();sync();if(!controller.pending&&!compiledKey)preview();}}
 }
 async function runPublish(){
  if(busy||historical||fields.historical)return;
  if(!controller.record.publishIntent){
   if(controller.pending){say('Resolvé el guardado pendiente antes de confirmar una publicación.',true);return;}
   if(previewPending||!fields.canPublish?.()){fields.showErrors?.();sync();return;}
   if(!await confirmAction(root,scope,'Publicar esta versión','La configuración publicada será inmutable. Podrás preparar una versión sucesora sin afectar los Cases vinculados a versiones anteriores.','Publicar esta versión'))return;
   persistRecovery();if(storageFailure)return;
  }
  busy=true;const restore=freeze();sync();
  try{const result=await controller.publish();if(!scope.active)return;allowLeave=true;say('Modelo publicado correctamente · Versión '+result.version.version);await go({modelId:result.version.model_id,modelVersionId:result.version.id,modelView:'review'});}
  catch(error){if(scope.active){say(error.status===409?'Conflicto de versión: se conserva el intento y la copia local. Recargá explícitamente el servidor.':error.message,true);reload.hidden=!existing||!!controller.record.publishIntent;}}
  finally{busy=false;if(scope.active){restore();sync();}}
 }
 let pendingLeave=null;
 const chooseLeave=async()=>{
  if(allowLeave)return true;if(busy)return false;if(!dirty()&&!controller.pending)return true;
  if(controller.pending){say('Hay un intento pendiente conservado. Reintentá la operación o recargá explícitamente antes de descartar cambios.',true);return false;}
  const choice=await dirtyDialog(root,scope);
  if(choice==='save')return runSave({navigateAfter:false});
  if(choice==='discard'){
   const checkpoint=controller.record.savedDraft||controller.record.initialDraft;
   controller.updateDraft(checkpoint);allowLeave=true;return true;
  }
  return false;
 };
 const leave=()=>pendingLeave||(pendingLeave=chooseLeave().finally(()=>{pendingLeave=null;}));
 window.dationModelCanLeave=leave;scope.own(()=>{previewGeneration++;clearTimeout(timer);if(window.dationModelCanLeave===leave)delete window.dationModelCanLeave;});
 scope.listen(window,'beforeunload',event=>{if(dirty()&&!allowLeave){event.preventDefault();event.returnValue='';}});
 scope.listen(form,'submit',event=>{event.preventDefault();runSave();});
 for(const event of ['input','change','model-review'])scope.listen(form,event,changed);
 scope.listen(window,'storage',event=>{if(event.key?.endsWith('.'+record.workId)){storageFailure=true;say('El borrador cambió en otra pestaña. Se conserva este formulario; recargá antes de guardar.',true);reload.hidden=!existing;sync();}});
 if(historical||fields.historical)say('Contrato histórico en consulta. No se convierte ni se publica desde este editor.');
 else if(controller.pending){fields.lock();say('Se recuperó una operación pendiente con su identidad original. Reintentá para confirmar el resultado.',true);reload.hidden=!existing||!!controller.record.publishIntent;}
 else if(record.savedWhere)say(record.savedWhere==='server'?'Borrador del servidor recuperado.':'Borrador recuperado de este navegador. No está guardado en el servidor.');
 else say('Copia de recuperación local. Usá Guardar borrador para confirmar el guardado.');
 changed();
}
function dirtyDialog(root,scope){
 return new Promise(resolve=>{
  const dialog=el('dialog',undefined,'d-modal'),body=el('div',undefined,'d-modal__body'),title=el('h2','Tenés cambios sin guardar en este modelo.','d-modal__title'),actions=el('div',undefined,'d-modal__actions');title.id='j101-dirty-title';dialog.setAttribute('aria-labelledby',title.id);body.append(title,el('p','Podés guardar el borrador, descartar los cambios o seguir editando.','d-body'));
  const keep=button('Seguir editando',()=>modal.close('keep')),discard=button('Descartar cambios',()=>modal.close('discard')),save=button('Guardar borrador',()=>modal.close('save'),'primary');actions.append(keep,discard,save);dialog.append(body,actions);root.append(dialog);const modal=mountDialog({dialog,initialFocus:keep});let settled=false;
  const finish=value=>{if(settled)return;settled=true;modal.dispose();dialog.remove();resolve(value);};dialog.addEventListener('close',()=>finish(dialog.returnValue),{once:true});scope.own(()=>finish('keep'));modal.open();
 });
}
