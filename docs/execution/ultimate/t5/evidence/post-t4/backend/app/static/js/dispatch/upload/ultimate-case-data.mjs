// T4 composes the existing upload cards and validation drawer. No graph states.
import {api,errorBox,download} from '../shared.mjs';
import {scopeFor} from '../lifecycle.mjs';
import {ensureStylesheet} from '../styles.mjs';
import {loadingState,mountDialog} from '../../platform/components.mjs';
import {el,button,pageHeader,draftStore,confirmAction} from '../models/forms.mjs';
import {createDropCard} from './dropcard.mjs';
import {createValidationDrawer} from './validation-report.mjs';

const ENTITIES=[['transport_demand','Demanda','orders'],['transport_resources','Recursos','fleet']];

async function request(path,options={}){
 let response;try{response=await fetch(path,options);}catch(e){if(e.name==='AbortError')throw e;throw Object.assign(new Error('No se confirmó la operación. Conservá el CSV y recuperá el candidato.'),{status:503});}
 const data=await response.json();if(!response.ok)throw Object.assign(new Error(typeof data.detail==='string'?data.detail:'Revisá las filas y columnas indicadas.'),{status:response.status,report:data.detail?.errors?data.detail:null});return data;
}

function previewTable(parent,records,label){
 if(!records?.length){parent.append(el('p','Sin filas para mostrar.','d-metadata'));return;}
 const wrap=el('div',undefined,'dispatch-table-wrap');wrap.tabIndex=0;wrap.role='region';wrap.setAttribute('aria-label',label);
 const table=el('table'),head=el('thead'),titles=el('tr'),columns=Object.keys(records[0]);
 for(const key of columns){const th=el('th',key);th.scope='col';titles.append(th);}head.append(titles);table.append(head);const body=el('tbody');
 for(const row of records){const tr=el('tr');for(const key of columns){const value=row[key];tr.append(el('td',value===null?'Desconocido':typeof value==='object'?JSON.stringify(value):String(value)));}body.append(tr);}table.append(body);wrap.append(table);parent.append(wrap);
}

function showContract(root,scope,contract,source){
 const dialog=el('dialog',undefined,'d-modal t4-contract-dialog'),body=el('div',undefined,'d-modal__body'),title=el('h2','Columnas del contrato','d-modal__title');title.id='t4-contract-title';dialog.setAttribute('aria-labelledby',title.id);body.append(title,el('p','Headers exactos, sin aliases ni columnas comerciales. Dejá vacíos los campos que no aplican a la fuente.','d-body'));
 const wrap=el('div',undefined,'dispatch-table-wrap');wrap.tabIndex=0;wrap.role='region';wrap.setAttribute('aria-label','Especificación de columnas');const table=el('table'),head=el('thead'),hr=el('tr');for(const text of ['Columna','Tipo / unidad','Aplica cuando','Regla / ejemplo'])hr.append(el('th',text));head.append(hr);table.append(head);const rows=el('tbody');
 for(const f of contract.fields){const tr=el('tr');for(const value of [f.public_header,f.type+(f.unit?' · '+f.unit:''),Object.keys(f.applies_when).length?JSON.stringify(f.applies_when):'Todas las filas',(f.nullable?'Puede ser desconocido / vacío. ':'Requerido. ')+JSON.stringify(f.validation)+' · '+f.examples.join(', ')])tr.append(el('td',value));rows.append(tr);}table.append(rows);wrap.append(table);body.append(wrap);const actions=el('div',undefined,'d-modal__actions'),close=button('Cerrar',()=>mounted.close());actions.append(close);dialog.append(body,actions);root.append(dialog);const mounted=mountDialog({dialog,initialFocus:close});dialog.addEventListener('close',()=>{mounted.dispose();dialog.remove();source?.focus();},{once:true});scope.own(()=>{mounted.dispose();dialog.remove();});mounted.open();
}

export async function mountCaseData(root,{route,navigate,onContext}){
 delete root.dataset.ultimateReady;const scope=scopeFor(root);root.className='dispatch dispatch-upload-pro d-platform ultimate-foundation ultimate-case-data';root.append(loadingState('Recuperando Data Pack…'));
 if(!route.caseId){errorBox(root,Object.assign(new Error('Elegí un Case para administrar sus datos.'),{status:404}),()=>navigate('logistics-case-setup',{caseId:null}));return;}
 try{
  await ensureStylesheet('ultimate-foundation-styles','/static/css/ultimate-foundation.css','t3-v1');await ensureStylesheet('ultimate-case-data-styles','/static/css/ultimate-case-data.css','t4-v1');
  const base='/api/platform/logistics-cases/'+route.caseId+'/data',data=await api(base,{signal:scope.signal});if(!scope.active)return;onContext?.(data.case);
  const store=draftStore('pack',route.caseId),draft=store.read()||{selection:{},uploadIntents:{},publication:null};draft.selection||={};draft.uploadIntents||={};const save=()=>store.write(draft);
  root.replaceChildren();const header=pageHeader(root,'Datos del Case',data.case.label+' · '+data.case.planning_start+' a '+data.case.planning_end);header.append(button('Contexto del Case',()=>navigate('logistics-case-setup',{caseId:route.caseId})));
  const message=el('p','Validar o guardar un candidato no cambia el Pack publicado.','d-metadata');message.dataset.packMessage='';message.role='status';root.append(message);
  const current=el('section',undefined,'d-card t4-current'),headline=el('h2','Pack · versión '+data.version.version,'d-card-title');headline.dataset.packCurrentVersion=String(data.version.version);current.append(headline,el('p','Revisión '+data.pack.revision+' · '+(data.entries.length?data.entries.length+' entradas publicadas':'Pack inicial vacío')+'. El Case existe aunque todavía no tenga archivos.','d-body'),el('p','Inputs publicados no equivalen a una decisión READY. La ejecución Ultimate todavía no está disponible.','d-metadata'));
  if(!data.can_edit)current.append(el('p','Publicación cerrada o acceso de sólo lectura. Los snapshots existentes se conservan.','d-body'));root.append(current);
  const validationDrawer=createValidationDrawer(scope),slots=el('div',undefined,'t4-slots');root.append(slots);const pendingFiles=new Set();
  const leave=()=>!pendingFiles.size||window.confirm('Tenés un archivo seleccionado sin guardar como candidato. Conservá el CSV antes de salir.');window.dationUltimateCanLeave=leave;scope.own(()=>{if(window.dationUltimateCanLeave===leave)delete window.dationUltimateCanLeave;});scope.listen(window,'beforeunload',e=>{if(pendingFiles.size){e.preventDefault();e.returnValue='';}});
  const reload=()=>navigate('logistics-case-data',{caseId:route.caseId,replace:true});
  function tell(error){if(!scope.active)return;message.textContent=error.message;message.role='alert';}
  const publishArea=el('section',undefined,'d-card t4-publish');let publicationBusy=false;
  const selections=el('p',undefined,'d-body'),publish=button('Publicar versión del Pack',()=>publishSelection(),'primary');
  function reflectSelection(){selections.textContent=pendingFiles.size?'Guardá los CSV seleccionados como candidatos o quitá su selección antes de publicar.':Object.values(draft.selection).length?'Selección para la próxima publicación: '+Object.keys(draft.selection).map(x=>x==='transport_demand'?'Demanda':'Recursos').join(' + ')+'. El manifest conserva también los slots publicados anteriores.':'Elegí candidatos válidos o inputs compatibles para publicar.';publish.disabled=!data.can_edit||!Object.keys(draft.selection).length||pendingFiles.size>0;}
  async function publishSelection(recover=false){
   if(publicationBusy)return;publicationBusy=true;publish.disabled=true;
   try{
    if(!recover&&!await confirmAction(root,scope,'Publicar Data Pack','Se creará una versión inmutable con el manifest completo. Los snapshots anteriores se conservan.','Publicar Pack'))return;
    const body=draft.publication||{publication_id:crypto.randomUUID(),expected_revision:data.pack.revision,selection:Object.values(draft.selection)};
    draft.publication=body;save();const result=await request(base+'/publish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:scope.signal});
    if(!scope.active)return;draft.publication=null;draft.selection={};save();await reload();
   }catch(error){if(scope.active){tell(error);if(error.status===409){const review=button('Recargar Pack y revisar',()=>{draft.publication=null;save();reload();});publishArea.append(review);}else message.textContent='No se confirmó la publicación. Recuperá la misma intención antes de publicar otra versión.';}}
   finally{publicationBusy=false;if(scope.active)reflectSelection();}
  }
  for(const [entity,label,visualKind]of ENTITIES){
   const contract=data.contracts[entity],published=data.entries.find(e=>e.slot_key===entity),format={columns:contract.fields.map(f=>({name:f.public_header,required:!f.nullable,type:f.type,rule:JSON.stringify(f.validation),example:f.examples[0]}))};
   const ref=createDropCard(visualKind,format),host=el('section',undefined,'t4-slot');host.dataset.t4Slot=entity;host.append(ref.card);slots.append(host);
   ref.card.querySelector('h3').textContent=label;ref.card.querySelector('.dispatch-pro-file-copy p').textContent=entity==='transport_demand'?'Órdenes pseudonimizadas, rutas, fechas y cantidades activas del Model.':'Recursos propios o externos, capacidades garantizadas, disponibilidad y tarifas explícitas.';
   ref.drop.setAttribute('aria-label','Elegir CSV de '+label);ref.dropStrong.textContent='Arrastrá el CSV de '+label;ref.file.setAttribute('aria-label','CSV de '+label);ref.file.dataset.t4File=entity;
   ref.previousView.querySelector('strong').textContent='Inputs compatibles de '+label;ref.previousEmpty.querySelector('p').textContent='Todavía no hay inputs compatibles con esta Model Version.';ref.previousAll.textContent='Siguiente página';
   const chips=[...ref.card.querySelectorAll('.dispatch-pro-requirement')];const nullable=contract.fields.filter(f=>f.nullable||Object.keys(f.applies_when).length).length;
   for(const [i,chip]of chips.entries()){chip.title='Todos los headers del template deben estar presentes. Sólo las celdas opcionales o no aplicables quedan vacías.';chip.lastChild.textContent=i===0?contract.fields.length+' columnas exactas':nullable+' admiten vacío según la fila';}
   ref.template.href=base+'/templates/'+entity;ref.template.download=entity+'.csv';ref.template.setAttribute('aria-label','Descargar template de '+label);
   scope.listen(ref.template,'click',async e=>{e.preventDefault();try{const r=await fetch(ref.template.href,{signal:scope.signal});if(!r.ok)throw new Error('No se pudo descargar el template.');download(entity+'.csv',await r.text(),'text/csv;charset=utf-8');}catch(error){tell(error);}});
   scope.listen(ref.reviewColumns,'click',()=>showContract(root,scope,contract,ref.reviewColumns));
   ref.headerState.textContent=published?'Publicado · v'+data.version.version:'Sin publicar';ref.headerState.classList.toggle('is-success',!!published);ref.headerState.classList.toggle('is-pending',!published);ref.validationHint.textContent='La validación no publica datos.';
   ref.validationBody.append(el('p','Descargá el template exacto. No incluyas nombre de cliente, CUIT, SKU, factura, ingresos ni margen.','d-body'));
   if(published){const summary=published.summary;const text=el('p','Publicado: '+published.record_count+' filas. '+(summary.assumed_external_count?summary.assumed_external_count+' disponibilidades ASSUMED. ':'')+(summary.unknown_cost_count?summary.unknown_cost_count+' costos desconocidos. ':''),'d-metadata');text.dataset.publishedSummary='';host.append(text,button('Vista previa publicada de '+label,async()=>{try{const result=await api(base+'/preview/'+published.dataset_id,{signal:scope.signal});const preview=el('section',undefined,'d-card t4-preview');preview.append(el('h3','Snapshot publicado de '+label,'d-card-title'));previewTable(preview,result.records,'Vista previa publicada de '+label);host.append(preview);}catch(error){tell(error);}}));}
   let file=null,report=null,busy=false,generation=0,controller=null,offset=0;
   const saveCandidate=button('Guardar candidato de '+label,()=>storeCandidate(),'primary');saveCandidate.disabled=true;host.append(saveCandidate);
   function controls(){saveCandidate.disabled=!data.can_edit||busy||!report?.valid;saveCandidate.setAttribute('aria-busy',String(busy));ref.choose.disabled=!data.can_edit||busy;ref.drop.setAttribute('aria-disabled',String(!data.can_edit||busy));ref.file.disabled=!data.can_edit||busy;ref.actions.hidden=!file;ref.replace.disabled=!data.can_edit||busy;ref.remove.disabled=!data.can_edit||busy;ref.cancelUpload.hidden=!busy;ref.progress.hidden=!busy;ref.progressTitle.textContent='Guardando candidato…';ref.progressFile.textContent=file?.name||'';}
   async function validateFile(selected){
    const own=++generation;file=selected;report=null;pendingFiles.add(entity);reflectSelection();ref.filePanel.hidden=false;ref.fileName.textContent=file.name;ref.fileMeta.textContent=file.size+' bytes · candidato local';ref.validationBody.replaceChildren(loadingState('Validando CSV…'));controls();
    const form=new FormData();form.append('file',file);
    try{const result=await request(base+'/validate/'+entity+'?'+new URLSearchParams({contract_hash:contract.contract_hash}),{method:'POST',body:form,signal:scope.signal});if(!scope.active||own!==generation)return;report=result;ref.validationBody.replaceChildren(el('p','Válido: '+result.rows+' filas. '+result.counts.warnings+' advertencias. Todavía no está publicado.','d-body'));previewTable(ref.validationBody,result.preview,'Vista previa del candidato de '+label);
     if(result.warnings.length)ref.validationBody.append(button('Revisar advertencias de '+label,e=>validationDrawer.open({report,filename:file.name,source:ref.choose})));
    }catch(error){if(!scope.active||own!==generation)return;report=error.report;ref.validationBody.replaceChildren(el('p',error.report?'El archivo contiene errores. No se creó un candidato ni se guardaron bytes.':error.message,'d-body'));if(error.report)ref.validationBody.append(button('Revisar errores de '+label,()=>validationDrawer.open({report:error.report,filename:file.name,source:ref.choose})));}finally{if(scope.active&&own===generation)controls();}
   }
   const choose=()=>{if(data.can_edit&&!busy)ref.file.click();};scope.listen(ref.choose,'click',e=>{e.stopPropagation();choose();});scope.listen(ref.drop,'click',choose);scope.listen(ref.drop,'keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();choose();}});scope.listen(ref.file,'change',()=>{if(ref.file.files[0])validateFile(ref.file.files[0]);});scope.listen(ref.drop,'dragover',e=>e.preventDefault());scope.listen(ref.drop,'drop',e=>{e.preventDefault();if(data.can_edit&&!busy&&e.dataTransfer.files[0])validateFile(e.dataTransfer.files[0]);});scope.listen(ref.replace,'click',choose);
   ref.remove.textContent='Quitar selección';scope.listen(ref.remove,'click',()=>{generation++;file=null;report=null;ref.file.value='';ref.filePanel.hidden=true;pendingFiles.delete(entity);reflectSelection();ref.validationBody.replaceChildren(el('p','El Pack publicado se conserva.','d-metadata'));controls();});
   scope.listen(ref.cancelUpload,'click',()=>controller?.abort());
   async function storeCandidate(){
    if(busy||!file||!report?.valid)return;busy=true;controller=new AbortController();scope.own(()=>controller?.abort());controls();const id=draft.uploadIntents[entity]||crypto.randomUUID();draft.uploadIntents[entity]=id;save();const form=new FormData();form.append('file',file);
    try{const candidate=await request(base+'/uploads/'+entity+'?'+new URLSearchParams({contract_hash:contract.contract_hash,upload_id:id}),{method:'POST',body:form,signal:controller.signal});if(!scope.active)return;draft.selection[entity]={slot_key:entity,upload_id:candidate.id};delete draft.uploadIntents[entity];save();pendingFiles.delete(entity);report=null;reflectSelection();if(!pendingFiles.size)await reload();else message.textContent='Candidato de '+label+' guardado. El otro CSV seleccionado se conserva hasta que lo guardes o quites.';}
    catch(error){if(scope.active){message.textContent='Carga pendiente. El Pack publicado no cambió. Recuperá el candidato o volvé a adjuntar el mismo CSV.';message.role='alert';const recover=button('Consultar carga pendiente de '+label,()=>{pendingFiles.delete(entity);reload();});host.append(recover);}}
    finally{busy=false;if(scope.active)controls();}
   }
   async function loadReuse(){try{const result=await api(base+'/reuse/'+entity+'?offset='+offset,{signal:scope.signal});if(!scope.active)return;ref.previousList.replaceChildren();ref.previousEmpty.hidden=result.items.length>0;for(const item of result.items){const row=el('div',undefined,'d-card t4-reuse-row');row.append(el('p',item.original_filename+' · '+item.row_count+' filas','d-body'),button('Seleccionar input compatible',()=>{draft.selection[entity]={slot_key:entity,dataset_id:item.id};draft.publication=null;save();reflectSelection();message.textContent='Input compatible seleccionado. Todavía no se publicó una versión.';}));ref.previousList.append(row);}ref.previousAll.disabled=result.items.length<25;ref.setReuseCount(result.items.length);}catch(error){tell(error);}}
   scope.listen(ref.reuseTab,'click',loadReuse);scope.listen(ref.previousAll,'click',()=>{offset+=25;loadReuse();});controls();
   const candidates=el('section',undefined,'d-card t4-candidates');candidates.setAttribute('aria-label','Candidatos de '+label);candidates.append(el('h3','Candidatos de '+label,'d-card-title'));
   for(const j of data.uploads.filter(j=>j.entity===entity)){
    const row=el('div',undefined,'t4-candidate');row.dataset.uploadId=j.id;const included=data.entries.some(e=>e.slot_key===entity&&e.dataset_id===j.dataset_id);row.append(el('p',j.filename+' · '+(included?'Publicado en el Pack vigente':j.status==='READY'?'Candidato válido; no está en el Pack vigente':'Carga interrumpida: recuperable'),'d-body'));
    if(j.status==='READY'){const select=button('Seleccionar candidato',()=>{draft.selection[entity]={slot_key:entity,upload_id:j.id};draft.publication=null;save();reflectSelection();message.textContent='Candidato seleccionado; el Pack vigente no cambió.';});select.disabled=!data.can_edit;row.append(select);}
    else{const recover=button('Recuperar candidato',async()=>{recover.disabled=true;try{const value=await request(base+'/uploads/'+j.id+'/recover',{method:'POST',signal:scope.signal});if(!scope.active)return;draft.selection[entity]={slot_key:entity,upload_id:value.id};delete draft.uploadIntents[entity];save();pendingFiles.delete(entity);if(!pendingFiles.size)await reload();else reflectSelection();}catch(error){tell(error);if(scope.active)recover.disabled=false;}});recover.disabled=!data.can_edit;row.append(recover);}
    const discard=button('Descartar candidato',async()=>{if(!await confirmAction(root,scope,'Descartar candidato','Se conserva el Pack publicado y toda su historia. Sólo se retira este candidato.','Descartar candidato'))return;try{await request(base+'/uploads/'+j.id+'/discard',{method:'POST',signal:scope.signal});if(!scope.active)return;if(draft.selection[entity]?.upload_id===j.id)delete draft.selection[entity];if(draft.uploadIntents[entity]===j.id)delete draft.uploadIntents[entity];save();pendingFiles.delete(entity);await reload();}catch(error){tell(error);}});discard.disabled=!data.can_edit;row.append(discard);candidates.append(row);
   }host.append(candidates);
  }
  publishArea.append(el('h2','Publicación explícita','d-card-title'),selections,publish);reflectSelection();if(draft.publication){const recover=button('Recuperar publicación',()=>publishSelection(true));recover.disabled=!data.can_edit;publishArea.append(el('p','Hay una intención de publicación pendiente de confirmar. Reintentá la misma antes de crear otra.','d-body'),recover);}root.append(publishArea);
  const history=el('section',undefined,'d-card t4-history');history.append(el('h2','Historial del Pack','d-card-title'));let historyOffset=0;
  const historyRows=el('div'),historyNext=button('Versiones anteriores',async()=>{try{historyOffset+=20;const older=await api(base+'?offset='+historyOffset,{signal:scope.signal});if(scope.active)renderHistory(older.history,older.history_total);}catch(error){tell(error);}});history.append(historyRows,historyNext);root.append(history);
  function renderHistory(versions,total){historyRows.replaceChildren();for(const v of versions){const row=el('div',undefined,'t4-history-row');row.append(el('span','Versión '+v.version+(v.id===data.version.id?' · vigente':''),'d-body'),button('Ver manifest de versión '+v.version,async()=>{try{const value=await api(base+'/versions/'+v.id,{signal:scope.signal});if(!scope.active)return;const details=el('section',undefined,'d-card t4-manifest');details.append(el('h3','Manifest de versión '+v.version,'d-card-title'));for(const entry of value.entries)details.append(el('p',entry.slot_key+' · '+entry.record_count+' filas · '+entry.canonical_sha256,'d-id'));if(!value.entries.length)details.append(el('p','Manifest vacío inicial.','d-body'));history.append(details);}catch(error){tell(error);}}));historyRows.append(row);}historyNext.disabled=historyOffset+20>=total;}renderHistory(data.history,data.history_total);
  root.dataset.ultimateReady='true';
 }catch(error){if(scope.active)errorBox(root,error,()=>navigate('logistics-case-data',{caseId:route.caseId,replace:true}));}
}
