/** Pre-Case private inputs; compiler/normalizer and publication remain on server. */
import {api,post} from '../shared.mjs';
import {el,button,field,confirmAction} from '../models/forms.mjs';
import {request as inputRequest,previewTable} from './ultimate-case-data.mjs';
import {createDropCard} from './dropcard.mjs';
import {createValidationDrawer} from './validation-report.mjs';
import {contractEntities} from '../models/data-contract-view.mjs';
import {decisionCard} from '../cases/decision-case-ui.mjs';

function preparationLabel(item){
 const states={DRAFT:'Borrador',VALIDATED:'Datos validados',FINALIZING:'Creación pendiente',CONSUMED:'Case creado',EXPIRED:'Vencida'};
 let date='Fecha no disponible';try{const value=new Date(item.updated_at);if(!Number.isNaN(value.getTime()))date=new Intl.DateTimeFormat('es-AR',{dateStyle:'medium',timeStyle:'short',timeZone:window.dationSession?.identity?.workspace?.timezone}).format(value);}catch{}
 return date+' · '+(states[item.status]||'Preparación guardada');
}

export function mountCorePreparation(root,scope,{canAssign,draft,onDraft,onContinue,onRecovered,parentCaseId=null}){
 const status=el('p','Seleccioná una Model Version publicada para preparar datos.','journey-preparation-status');status.role='status';status.setAttribute('aria-live','polite');root.append(status);
 const ownerRow=el('div',undefined,'journey-session-row');root.append(ownerRow);
 const ownerControls=decisionCard(ownerRow,'Responsable de datos','Gestiona la preparación de los datos.','people'),ownerArea=ownerControls.parentElement;ownerArea.classList.add('journey-data-owner','core-owner-card');ownerArea.dataset.dationTest='preparation-owner-card';
 const owner=field(ownerControls,'Data Owner',{name:'preparation_data_owner',options:[['','Sin asignar']],value:''});owner.disabled=true;if(!canAssign)ownerControls.append(el('p','Un Admin debe asignar el Data Owner. Podés preparar datos sin esa asignación.','d-field__help'));
 const alternatives=decisionCard(ownerRow,'Data Sessions','Retomá sesiones de carga anteriores de este Logistics Model.','layers');
 alternatives.parentElement.classList.add('core-owner-card','core-sessions-card');alternatives.parentElement.dataset.dationTest='preparation-sessions-card';alternatives.classList.add('core-owner-alternatives');
 const availability=el('p','Seleccioná una versión publicada para consultar sesiones.','d-metadata');availability.role='status';availability.setAttribute('aria-live','polite');availability.id='journey-session-availability';alternatives.append(availability);
 const pending=new Set(),drawer=createValidationDrawer(scope);let data=null,source=null,generation=0,busy=false,errorMessage='',readyPromise=Promise.resolve(),footer=null,controls=[],ownerSaving=false;
 const previousLeave=window.dationUltimateCanLeave;const leave=()=>!pending.size||window.confirm('Hay CSV seleccionados sin guardar. Se perderá la selección local al salir. Los candidatos guardados se conservan.');
 const compositeLeave=()=>leave()&&(!previousLeave||previousLeave());window.dationUltimateCanLeave=compositeLeave;scope.own(()=>{if(window.dationUltimateCanLeave===compositeLeave)delete window.dationUltimateCanLeave;generation++;});scope.listen(window,'beforeunload',e=>{if(pending.size){e.preventDefault();e.returnValue='';}});
 // List is actor/workspace scoped, at most 10 entries, with at most 5 active
 // preparations. DRAFT/VALIDATED resume uploads; FINALIZING resumes the frozen
 // creation intent (the server permits recovery even past its expiry).
 let sessionEpoch=0,sessionController=null,sessionKey=null,sessionPhase='idle',sessionItems=[],pickerOpen=false,switching=false;
 const lookupKey=()=>data&&[data.session.id,data.session.model_version_id,data.session.revision,parentCaseId||''].join(':');
 const compatible=item=>item&&item.id!==data?.session.id&&item.model_version_id===data?.session.model_version_id&&(item.parent_case_id||null)===parentCaseId&&(item.status==='FINALIZING'||['DRAFT','VALIDATED'].includes(item.status)&&Date.parse(item.expires_at)>Date.now());
 const resume=button('Ver sesiones',()=>{
  if(!canSwitch())return;
  pickerOpen=true;void lookupSessions(true);
 });resume.disabled=true;resume.setAttribute('aria-describedby',availability.id);resume.setAttribute('aria-expanded','false');
 const retrySessions=button('Reintentar sesiones',()=>{void lookupSessions(true);});retrySessions.hidden=true;alternatives.append(resume,retrySessions);
 scope.own(()=>{sessionEpoch++;sessionController?.abort();});
 scope.listen(window,'focus',()=>{if(!busy&&!switching&&data)void lookupSessions(true);});
 function canSwitch(){
  if(pending.size){tell(new Error('Guardá o quitá los archivos locales antes de cambiar de preparación.'));return false;}
  if(data?.session.creation_intent){tell(new Error('Recuperá la creación congelada antes de cambiar de preparación.'));return false;}
  return !busy&&!switching;
 }
 function sessionsUI(){
  availability.role=sessionPhase==='error'?'alert':'status';retrySessions.hidden=sessionPhase!=='error';
  resume.disabled=sessionPhase!=='ready'||!sessionItems.length||busy||switching;
  if(!alternatives.querySelector('.journey-resume-list'))resume.removeAttribute('aria-controls');
  resume.setAttribute('aria-busy',String(sessionPhase==='loading'||switching));resume.setAttribute('aria-expanded',String(pickerOpen&&!!alternatives.querySelector('.journey-resume-list')));
 }
 function sessionError(error){sessionPhase='error';sessionItems=[];availability.textContent='No se pudieron verificar sesiones. '+error.message;alternatives.querySelector('.journey-resume-list')?.remove();sessionsUI();}
 async function lookupSessions(force=false){
  if(!scope.active||busy||!data||source?.data.provisional)return;
  if(data.session.model_version_id!==source?.snapshot.version_id){sessionPhase='idle';sessionItems=[];availability.textContent='Confirmá la versión actual para consultar sus sesiones.';sessionsUI();return;}
  const key=lookupKey();if(!force&&key===sessionKey)return;
  sessionController?.abort();sessionController=new AbortController();const own=++sessionEpoch;sessionKey=key;sessionPhase='loading';sessionItems=[];
  availability.textContent='Consultando sesiones de esta versión…';alternatives.querySelector('.journey-resume-list')?.remove();sessionsUI();
  try{
   const list=await json('/api/platform/data-preparations',{signal:sessionController.signal});
   if(!scope.active||own!==sessionEpoch||key!==lookupKey())return;
   if(!Array.isArray(list?.items)||list.items.some(item=>!item||typeof item.id!=='string'||typeof item.model_version_id!=='string'||typeof item.status!=='string'||!Number.isInteger(item.revision)||!Number.isFinite(Date.parse(item.expires_at))||!Number.isFinite(Date.parse(item.updated_at))||(item.parent_case_id!==null&&typeof item.parent_case_id!=='string'))||new Set(list.items.map(item=>item.id)).size!==list.items.length)throw new Error('La respuesta de sesiones no es válida.');
   sessionItems=list.items.filter(compatible);sessionPhase='ready';availability.textContent=sessionItems.length?sessionItems.length+' '+(sessionItems.length===1?'sesión disponible':'sesiones disponibles'):'No hay otras sesiones disponibles para esta versión y origen.';
   if(pickerOpen)renderSessions(key);sessionsUI();
  }catch(error){if(scope.active&&own===sessionEpoch&&key===lookupKey())sessionError(error);}
 }
 function renderSessions(key){
  const choices=el('div',undefined,'journey-resume-list');choices.id='journey-session-picker';choices.setAttribute('role','group');choices.setAttribute('aria-label','Sesiones compatibles');resume.setAttribute('aria-controls',choices.id);
  for(const item of sessionItems){const choose=button(preparationLabel(item),()=>{const previous=readyPromise,attempt=selectSession(item,key);readyPromise=attempt;void attempt.catch(()=>{}).finally(()=>{if(readyPromise===attempt)readyPromise=previous;});});choose.dataset.preparationId=item.id;choices.append(choose);}
  if(!choices.children.length){const empty=el('p','No hay otras sesiones disponibles para esta versión y origen.','d-metadata');empty.role='status';choices.append(empty);}
  alternatives.append(choices);
 }
 async function selectSession(item,key){
  if(!canSwitch()||key!==lookupKey()||!compatible(item))return;
  const own=sessionEpoch,selectionGeneration=generation,ownerSessionId=data.session.id,ownerWasDisabled=owner.disabled;switching=true;busy=true;owner.disabled=true;reflect();sessionsUI();for(const b of alternatives.querySelectorAll('.journey-resume-list button'))b.disabled=true;
  try{
   // Recheck this selected resource, not every list item, before changing draft.
   const current=await json('/api/platform/data-preparations/'+item.id);
   if(!scope.active||own!==sessionEpoch)return;
   if(key!==lookupKey())throw new Error('La preparación actual cambió. Volvé a elegir la sesión.');
   if(current?.session?.id!==item.id||!compatible(current.session)||(current.session.status==='FINALIZING'?!current.session.creation_intent:!!current.session.creation_intent))throw new Error('La sesión ya no está disponible. Actualizá la lista.');
   if(pending.size||data?.session.creation_intent){switching=false;canSwitch();return;}
   draft.id=item.id;draft.version_id=item.model_version_id;onDraft();pickerOpen=false;const recovery=refresh(),recoveryGeneration=generation;await recovery;
   if(scope.active&&generation===recoveryGeneration&&(data?.session.id!==item.id||errorMessage))throw new Error(errorMessage||'No se confirmó la sesión elegida.');
  }catch(error){if(scope.active){if(own===sessionEpoch)sessionError(error);throw error;}}
  finally{switching=false;if(scope.active){if(selectionGeneration===generation){busy=false;if(data?.session.id===ownerSessionId&&draft.id===ownerSessionId)owner.disabled=ownerWasDisabled;reflect();}sessionsUI();}}
 }
 const base=()=>'/api/platform/data-preparations/'+data.session.id;
 const saved=()=>{if(data){draft.id=data.session.id;draft.version_id=data.session.model_version_id;onDraft();}};
 let bundleProof=null,bundleAttempt=null,bundleChecking=false,bundleError='';
 const entities=()=>contractEntities(data||source?.data||{});
 const bundleKey=()=>data&&[generation,data.session.id,data.session.revision,data.session.model_version_id,...data.uploads.filter(u=>u.selected&&u.ready).map(u=>u.entity+':'+u.canonical_sha256).sort()].join(':');
 const bundleRetry=button('Revalidar relaciones entre archivos',()=>{bundleAttempt=null;bundleError='';reflect();});bundleRetry.hidden=true;status.after(bundleRetry);
 async function checkBundle(key){
  bundleAttempt=key;bundleChecking=true;bundleError='';bundleProof=null;
  try{
   const result=await inputRequest(base()+'/validate-bundle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_revision:data.session.revision}),signal:scope.signal});
   if(!scope.active||key!==bundleKey())return;
   const selected=data.uploads.filter(u=>u.selected&&u.ready),hashes=result.normalized_hashes;
   if(result.valid!==true||result.preparation_id!==data.session.id||result.expected_revision!==data.session.revision||result.model_version_id!==data.session.model_version_id||!hashes||Object.keys(hashes).length!==selected.length||selected.some(u=>hashes[u.entity]!==u.canonical_sha256))throw new Error('La validación cruzada no corresponde a esta preparación.');
   bundleProof=key;
  }catch(e){if(scope.active&&key===bundleKey())bundleError=e.report?.errors?.map(row=>row.message).filter(Boolean).join(' ')||e.message;}
  finally{bundleChecking=false;if(scope.active)reflect();}
 }
 function reflect(){
  if(!scope.active)return;
  const n=data?.uploads.filter(u=>u.selected&&u.ready).length||0,total=entities().length;
  const needsBundle=!!data?.bundle_validation_required,key=bundleKey(),verified=!needsBundle||bundleProof===key;
  if(needsBundle&&!busy&&!ownerSaving&&!pending.size&&n===total&&bundleAttempt!==key){void checkBundle(key);}
  status.role=errorMessage||bundleError?'alert':'status';
  status.textContent=errorMessage||bundleError||(busy?'Recuperando preparación privada…':n+' de '+total+' candidatos guardados y validados. '+(bundleChecking?'Comprobando relaciones entre órdenes y líneas. ':needsBundle&&!verified&&n===total?'Relaciones pendientes de verificación. ':'')+(pending.size?'Hay archivos locales sin guardar. ':'')+'Todavía no están publicados.');
  bundleRetry.hidden=!bundleError||busy||bundleChecking;bundleRetry.disabled=bundleChecking;
  if(footer){
   footer.next.disabled=!!errorMessage||busy||ownerSaving||n!==total||!!pending.size||!verified;
   footer.skip.disabled=!!errorMessage||busy||ownerSaving;
   const missing=entities().filter(([entity])=>!data?.uploads.some(u=>u.entity===entity&&u.selected&&u.ready)).map(([,label])=>label);
   footer.copy.textContent=n===total?(verified?total+' archivos validados · publicación al finalizar el Case':'Relaciones entre archivos pendientes de validación'):n?'Falta '+missing.join(' y '):'Preparación pendiente · podés continuar sin datos';
  }
  if(!busy&&data)void lookupSessions();
 }

 function tell(e){errorMessage=e.message;status.textContent=e.message;status.role='alert';}
 async function json(path,options){return api(path,{...options,signal:options?.signal||scope.signal});}
 async function renderUploads(grid,own){
  controls=[];const accept=value=>{if(!scope.active||own!==generation)return false;data=value;return true;};
  for(const [entity,label]of entities()){
   const card=grid.querySelector('[data-dation-test=contract-card-'+entity+']');if(!card)continue;card.querySelector('.journey-upload')?.remove();
   const contract=data.contracts[entity],host=el('section',undefined,'journey-upload');host.dataset.preparationEntity=entity;card.append(host);
   const ref=createDropCard(entity==='transport_resources'?'fleet':'orders',{columns:contract.fields.map(f=>({required:!f.nullable}))});ref.dropStrong.textContent='Arrastrá el CSV de '+label;ref.drop.setAttribute('aria-label','Elegir CSV de '+label);ref.file.setAttribute('aria-label','CSV de '+label);ref.file.dataset.journeyFile=entity;
   host.append(ref.drop,ref.file,ref.filePanel,ref.validationBody,ref.cancelUpload);ref.cancelUpload.hidden=true;ref.validationBody.classList.add('journey-validation');
   let file=null,report=null,requestVersion=0,uploadId=null,working=false,controller=null;
   const row=el('div',undefined,'journey-upload-actions'),save=button('Guardar candidato de '+label,store,'primary'),remove=button('Quitar selección',async()=>{if(working)return;requestVersion++;file=null;report=null;pending.delete(entity);ref.file.value='';ref.filePanel.hidden=true;if(data.uploads.some(u=>u.entity===entity&&u.selected)){try{const nextData=await post(base()+'/unselect/'+entity,{expected_revision:data.session.revision},{signal:scope.signal});if(!accept(nextData))return;}catch(e){if(!scope.active||own!==generation)return;tell(e);return;}}ref.validationBody.replaceChildren(el('p','La selección fue retirada. Los snapshots publicados no cambian.'));sync();reflect();});row.append(save,remove);host.append(row);
   const reuse=button('Reutilizar input compatible de '+label,async()=>{if(pending.size){tell(new Error('Guardá o quitá los archivos locales antes de reutilizar un input.'));return;}try{const result=await json(base()+'/reuse/'+entity);const list=el('div',undefined,'journey-reuse');if(!result.items.length)list.append(el('p','No hay inputs compatibles con esta Model Version.','d-metadata'));for(const item of result.items){const choose=button(item.original_filename+' · '+item.row_count+' filas',async()=>{choose.disabled=true;try{const nextData=await post(base()+'/reuse/'+entity,{dataset_id:item.id,expected_revision:data.session.revision},{signal:scope.signal});if(!accept(nextData))return;errorMessage='';saved();await refresh();}catch(e){if(!scope.active||own!==generation)return;tell(e);choose.disabled=false;}});list.append(choose);}host.querySelector('.journey-reuse')?.remove();host.append(list);}catch(e){if(!scope.active||own!==generation)return;tell(e);}});host.append(reuse);
   const selected=data.uploads.find(u=>u.entity===entity&&u.selected&&u.ready);
   if(selected){ref.filePanel.hidden=false;ref.fileName.textContent=selected.filename;ref.fileMeta.textContent='Candidato guardado · no publicado';renderReport(selected.report);}
   for(const u of data.uploads.filter(u=>u.entity===entity&&!u.ready))host.append(button('Recuperar candidato de '+label,async()=>{try{const nextData=await post(base()+'/uploads/'+u.id+'/recover',{}, {signal:scope.signal});if(!accept(nextData))return;saved();await refresh();}catch(e){if(!scope.active||own!==generation)return;tell(e);}}));
   function sync(){const frozen=data?.session.status==='FINALIZING'||data?.session.status==='CONSUMED';save.disabled=frozen||working||!report?.valid;remove.disabled=frozen||working;ref.cancelUpload.hidden=!working;reuse.disabled=frozen||working;ref.file.disabled=ref.choose.disabled=frozen||working;save.setAttribute('aria-busy',String(working));}
   function renderReport(r){ref.validationBody.replaceChildren(el('p',(r.valid?'Válido':'Con errores')+' · '+r.rows+' filas · '+r.counts.errors+' errores · '+r.counts.warnings+' advertencias.','d-body'));if(r.errors.length||r.warnings.length)ref.validationBody.append(button('Ver detalle de '+label,()=>drawer.open({report:r,filename:file?.name||selected?.filename||entity+'.csv',source:ref.choose})));if(r.preview?.length){const details=el('details'),summary=el('summary','Vista previa · '+Math.min(r.preview.length,5)+' filas');details.append(summary);previewTable(details,r.preview.slice(0,5),'Vista previa de '+label);ref.validationBody.append(details);}}
   async function validateFile(chosen){const n=++requestVersion;file=chosen;report=null;uploadId=crypto.randomUUID();pending.add(entity);ref.filePanel.hidden=false;ref.fileName.textContent=file.name;ref.fileMeta.textContent=file.size+' bytes · selección local';ref.validationBody.textContent='Validando CSV…';sync();reflect();const form=new FormData();form.append('file',file);try{report=await inputRequest(base()+'/validate/'+entity+'?contract_hash='+contract.contract_hash,{method:'POST',body:form});if(!scope.active||own!==generation||n!==requestVersion)return;renderReport(report);}catch(e){if(!scope.active||own!==generation||n!==requestVersion)return;report=null;ref.validationBody.textContent=e.message;if(e.report?.errors)renderReport(e.report);}finally{sync();}}
   async function store(){if(working||!report?.valid||!file)return;working=true;controller=new AbortController();scope.own(()=>controller.abort());sync();const form=new FormData();form.append('file',file);try{const result=await json(base()+'/uploads/'+entity+'?'+new URLSearchParams({upload_id:uploadId,expected_revision:data.session.revision,contract_hash:contract.contract_hash}),{method:'POST',body:form,signal:controller.signal});if(!scope.active||own!==generation)return;data=result;pending.delete(entity);report=null;errorMessage='';saved();ref.fileMeta.textContent='Candidato guardado · no publicado';reflect();}catch(e){if(!scope.active||own!==generation)return;tell(e);host.append(button('Recuperar carga pendiente',async()=>{try{const nextData=await post(base()+'/uploads/'+uploadId+'/recover',{}, {signal:scope.signal});if(!accept(nextData))return;pending.delete(entity);errorMessage='';saved();if(!pending.size)await refresh();else{ref.fileMeta.textContent='Candidato recuperado · no publicado';reflect();}}catch(error){if(!scope.active||own!==generation)return;tell(error);}}));}finally{working=false;sync();}}
   scope.listen(ref.cancelUpload,'click',()=>controller?.abort());
   scope.listen(ref.choose,'click',e=>{e.stopPropagation();ref.file.click();});scope.listen(ref.drop,'click',()=>ref.file.click());scope.listen(ref.drop,'keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();ref.file.click();}});scope.listen(ref.drop,'dragover',e=>e.preventDefault());scope.listen(ref.drop,'drop',e=>{e.preventDefault();if(!working&&!['FINALIZING','CONSUMED','EXPIRED'].includes(data?.session.status)&&e.dataTransfer.files[0])validateFile(e.dataTransfer.files[0]);});scope.listen(ref.file,'change',()=>{if(ref.file.files[0])validateFile(ref.file.files[0]);});sync();controls.push({host});
  }
 }
 async function refresh(){if(!source)return;await resolve(source.data,source.snapshot,source.ui);}
 async function resolve(pair,snapshot,ui){
  const own=++generation;sessionEpoch++;sessionController?.abort();sessionKey=null;sessionItems=[];sessionPhase='idle';pickerOpen=false;availability.textContent='Recuperando sesión actual…';alternatives.querySelector('.journey-resume-list')?.remove();source={data:pair,snapshot,ui};footer=ui;busy=true;errorMessage='';reflect();root.hidden=pair.provisional;sessionsUI();
  if(pair.provisional){busy=false;availability.textContent='Seleccioná una versión publicada para consultar sesiones.';sessionsUI();return;}
  try{
   if(draft.id&&draft.version_id!==snapshot.version_id){
    const okay=await confirmAction(root,scope,'Cambió la Model Version','Los candidatos guardados de la preparación anterior se conservan en privado. Los archivos locales sin guardar deberán volver a adjuntarse. ¿Preparar archivos para esta versión?','Preparar esta versión');if(!okay)throw new Error('Se conserva la preparación anterior. Volvé a seleccionar su Model Version para retomarla.');pending.clear();draft.id=null;
   }
   draft.id||=crypto.randomUUID();draft.version_id=snapshot.version_id;onDraft();
   const resolved=await post('/api/platform/data-preparations',{id:draft.id,model_version_id:snapshot.version_id,parent_case_id:parentCaseId},{signal:scope.signal});
   if(!scope.active||own!==generation)return;data=resolved;saved();root.querySelector('[data-stage-recovery]')?.remove();
   if(data.session.status==='EXPIRED'){
    const actions=el('div');actions.dataset.stageRecovery='';actions.append(button('Limpiar preparación expirada e iniciar otra',async()=>{if(!await confirmAction(root,scope,'Iniciar otra preparación','Se eliminarán sólo los CSV privados del borrador expirado. Los datos publicados de Cases se conservan.','Limpiar e iniciar'))return;try{await post(base()+'/cleanup',{}, {signal:scope.signal});if(!scope.active||own!==generation)return;draft.id=crypto.randomUUID();onDraft();await resolve(pair,snapshot,ui);}catch(e){tell(e);}}));root.append(actions);throw new Error('La preparación venció después de 24 horas. Podés limpiarla e iniciar otra sin modificar Cases publicados.');
   }
   if(data.session.creation_intent){const recover=button('Recuperar creación del Case',async()=>{recover.disabled=true;try{const result=await post(base()+'/finalize',{expected_revision:data.session.revision,case:data.session.creation_intent},{signal:scope.signal});onRecovered?.(result.context);}catch(e){tell(e);recover.disabled=false;}});recover.dataset.stageRecovery='';root.append(recover);}
   await renderUploads(ui.grid,own);owner.value=data.session.data_owner_user_id||'';
   if(canAssign){const people=[];let offset=0,total=0;do{const p=await json('/api/platform/team?'+new URLSearchParams({candidates:'true',responsibility:'data_owner',limit:50,offset}));people.push(...p.members);total=p.total;offset+=50;if(!p.members.length&&offset<total)throw new Error('El Equipo cambió. Reintentá la preparación.');}while(offset<total);if(!scope.active||own!==generation)return;owner.replaceChildren(new Option('Sin asignar',''),...people.map(p=>new Option(p.name+' · '+p.email,p.user_id)));owner.value=data.session.data_owner_user_id||'';owner.disabled=data.session.status==='FINALIZING'||data.session.status==='CONSUMED';}
  }catch(e){if(scope.active&&own===generation)tell(e);}finally{if(scope.active&&own===generation){busy=false;reflect();}}
 }
 scope.listen(owner,'change',async()=>{const own=generation;owner.disabled=true;ownerSaving=true;reflect();try{const resolved=await json(base()+'/owner',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_revision:data.session.revision,data_owner_user_id:owner.value||null})});if(!scope.active||own!==generation)return;data=resolved;saved();reflect();}catch(e){tell(e);}finally{ownerSaving=false;if(scope.active&&own===generation){owner.disabled=!canAssign||!!data?.session.creation_intent;reflect();}}});
 return {attach(pair,snapshot,{grid,footer:area,next,copy}){
  next.hidden=true;let c=area.querySelector('[data-journey-next]'),skip=area.querySelector('[data-journey-skip]');if(!c){c=button('Continuar con datos',()=>{if(!c.disabled)onContinue();},'primary');c.dataset.journeyNext='';skip=button('Continuar sin datos',async()=>{if(pending.size&&!await confirmAction(root,scope,'Continuar sin cargar datos','La selección local se perderá. Los candidatos guardados se conservan, sin publicarse.','Continuar sin datos'))return;try{await readyPromise;for(const [entity]of entities())if(data?.uploads.some(u=>u.entity===entity&&u.selected))data=await post(base()+'/unselect/'+entity,{expected_revision:data.session.revision},{signal:scope.signal});pending.clear();reflect();onContinue();}catch(e){tell(e);}});skip.dataset.journeySkip='';(area.querySelector('.journey-step-actions')||area).append(skip,c);}
  readyPromise=resolve(pair,snapshot,{grid,next:c,skip,copy});return readyPromise;
 },async finalize(body){await readyPromise;if(!data)throw new Error('La preparación no está confirmada. Volvé al paso 02.');const result=await post(base()+'/finalize',{expected_revision:data.session.revision,case:body},{signal:scope.signal});data=result.preparation;return result.context;},get validated(){return !ownerSaving&&!!data&&data.uploads.filter(u=>u.selected&&u.ready).length===entities().length&&!pending.size&&(!data.bundle_validation_required||bundleProof===bundleKey());},get snapshot(){return data;},get pending(){return pending.size>0;}};
}
