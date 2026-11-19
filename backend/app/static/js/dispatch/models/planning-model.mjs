import {api,post} from '../shared.mjs';
import {mountDialog} from '../../platform/components.mjs';
import {el,button,field,collapsibleSection} from './forms.mjs';
import {mountModelFields,defaultConfiguration,defaultConfigurationV2} from './model-fields.mjs';
import {wizardIcon} from './wizard-ui.mjs';
import {mountDataContractView} from './data-contract-view.mjs';

// Keep v1 recovery copy unchanged. V2 physical validation is structured by
// FastAPI; preserve its relevant business messages instead of hiding the cause.
async function previewV2Draft(configuration,signal){
 const response=await fetch('/api/platform/logistics-models/contract-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({configuration}),signal});
 const data=await response.json();
 if(!response.ok){
  const details=Array.isArray(data.errors)?data.errors.map(e=>({loc:[e.field],msg:e.message})):Array.isArray(data.detail)?data.detail:[],v2=details.filter(e=>e.loc?.some(key=>String(key).includes('LogisticsModelConfigurationV2'))),selected=v2.length?v2:details;
  const message=selected.map(e=>String(e.msg||'').replace(/^Value error, /,'')).filter(Boolean).join(' ');
  throw Object.assign(new Error(message||(typeof data.detail==='string'?data.detail:'Revisá las propiedades físicas del modelo.')),{status:response.status});
 }
 return data;
}

export async function mountPlanningModel(form,scope,{draft={},modelId='',canManage,saga10=false,unified=false,onChange=()=>{},persist=()=>{},onSelected=()=>{},onContinue=()=>{},onContracts}){
 const modelPanel=collapsibleSection(form,'01. Logistics Model','Definí la lógica operativa base del modelo logístico que vas a usar en este Case.',{open:true,initialStatus:'En configuración'}),modelBlock=modelPanel.body;
 modelPanel.details.dataset.dationTest='core-model';modelPanel.details.dataset.modelState='LOADING';modelPanel.setStatus('Cargando');modelPanel.details.classList.add('model-wizard');modelBlock.classList.add('ultimate-planning-model');modelBlock.hidden=true;
 const summary=modelPanel.details.querySelector('summary'),tile=el('span',undefined,'model-wizard-tile'),heading=el('span',undefined,'model-wizard-heading');tile.append(wizardIcon('layers'));heading.append(summary.querySelector('.ultimate-disclosure__title'),modelBlock.previousElementSibling);summary.prepend(tile,heading);
 const intro=el('div',undefined,'model-wizard-intro'),reuse=button('',openPicker),catalogHint=el('p',undefined,'d-metadata'),introIcon=wizardIcon('database');reuse.append(wizardIcon('folder'),el('span','Seleccionar modelo existente'));reuse.dataset.dationTest='model-reuse';const newModel=button('',startNew,'primary');newModel.append(wizardIcon('plus'),el('span','Crear nuevo modelo'));newModel.dataset.modelNew='';const toolbar=el('div',undefined,'model-wizard-top-actions');toolbar.append(reuse,newModel);intro.classList.add('model-wizard-intro-pro');intro.append(introIcon,el('strong','Creá un nuevo modelo operativo o reutilizá uno ya publicado.'),toolbar,catalogHint);
 const editor=el('div'),feedback=el('p','','model-wizard-feedback'),footer=el('footer',undefined,'model-wizard-footer'),progress=el('div',undefined,'model-wizard-progress'),ring=el('span',undefined,'model-wizard-ring'),progressText=el('div'),count=el('p','','d-metadata'),create=button('',publish,'primary');
 feedback.role='status';feedback.setAttribute('aria-live','polite');feedback.dataset.dationTest='model-feedback';progress.dataset.dationTest='model-progress';progress.role='status';progressText.append(el('strong','Configuración del modelo'),count);ring.setAttribute('aria-hidden','true');progress.append(ring,progressText);footer.append(progress,create);modelBlock.append(intro,editor,feedback,footer);
 feedback.id='model-create-feedback';create.setAttribute('aria-describedby',feedback.id);create.dataset.dationTest='model-create';const createLabel=unified?'Guardar y continuar':'Crear y seleccionar modelo',createCaption=el('span',createLabel);create.append(wizardIcon('check'),createCaption);
 const contractPanel=collapsibleSection(form,'02. Data Contract','Dation genera automáticamente la estructura de datos requerida a partir del Logistics Model seleccionado. Descargá las plantillas y consultá sus campos y reglas antes de cargar los datos en el Decision Graph.',{initialStatus:'Pendiente'}),contractView=mountDataContractView(contractPanel,scope,{retry:()=>preview({focusError:true}),onContinue,onContracts}),contractStatus=contractView.status,retry=contractView.retry,modelRetry=button('Reintentar Data Contract',async()=>{if(state.mode==='existing'&&!isSelected()){await render().catch(fail);if(ready)onSelected();}else await preview({focusError:true});});
 retry.hidden=modelRetry.hidden=true;feedback.after(modelRetry);contractPanel.details.dataset.dationTest='core-contract';
 const newDraft=()=>{
  const configuration=(saga10?defaultConfigurationV2:defaultConfiguration)(window.dationSession.identity.workspace.currency);
  // Only brand-new UI drafts use the homogeneous route. Saved and published
  // configurations retain their original mode, dimensions and physical units.
  if(saga10){if(!['ARS','USD','EUR'].includes(configuration.currency_policy.currency))configuration.currency_policy.currency='ARS';configuration.active_dimensions=['weight_kg','volume_m3'];configuration.primary_dimension='weight_kg';configuration.cargo.input_mode='catalog';}
  return {id:crypto.randomUUID(),name:'',description:'',status:'active',expected_revision:1,configuration,...(saga10?{guided_ux:{edition:'ultimate'}}:{})};
 };
 const state={mode:draft.mode||'new',model_id:draft.model_id||modelId,version_id:draft.version_id||'',new_model:draft.new_model||newDraft(),intent:draft.intent||null,locked:!!draft.locked};
 // An old draft may contain an acknowledged version without its selection flag.
 if(state.intent&&state.version_id===state.intent.version_id){state.mode='existing';state.model_id=state.intent.model_id;state.intent.published=true;}
 let fields=null,selected=null,compiled=false,ready=false,generation=0,renderGeneration=0,timer=null,busy=false,pickerOpen=false,previewPending=false,message='',previewFailed=false;
 const models=[];let offset=0,total=0;
 do{const page=await api('/api/platform/logistics-models?'+new URLSearchParams({limit:50,offset}),{signal:scope.signal});if(!scope.active)return;models.push(...page.items.filter(m=>m.status==='active'&&m.versions.length));offset+=50;total=page.total;if(offset<total&&!page.items.length)throw new Error('La lista de Models cambió. Recargá la configuración.');}while(offset<total);
 scope.own(()=>{generation++;clearTimeout(timer);});
 const pending=()=>!!state.intent&&!state.intent.published;
 const isSelected=()=>state.mode==='existing'&&!!selected?.versions.some(v=>v.id===state.version_id);
 const readDraft=()=>({...state,new_model:state.mode==='new'&&fields&&!pending()?fields.read():state.new_model});
 const changed=()=>{sync();onChange();};
 function sync(){
  const valid=fields?.sectionValidity()||[false,false,false],progress=fields?.sectionCompletion?.()||valid,complete=progress.filter(Boolean).length;
  ring.style.setProperty('--model-progress',String(complete/valid.length*100)+'%');count.textContent=complete+' de '+valid.length+(fields?.sectionCompletion?' secciones revisadas':' secciones completas');
  const selectedVersion=isSelected();
  modelPanel.setStatus(selectedVersion?'Configurado':!canManage?'Sólo lectura':previewFailed||pending()&&!busy?'Revisar configuración':'En configuración',selectedVersion?'complete':previewFailed?'warning':'pending');
  modelPanel.details.dataset.modelState=busy?'NEW_PUBLISHING':pickerOpen?'REUSE_PICKER':selectedVersion?'MODEL_SELECTED':!canManage?'READ_ONLY':previewFailed||pending()?'ERROR_RECOVERABLE':previewPending?'NEW_VALIDATING':compiled&&complete===valid.length?'NEW_READY_TO_CREATE':'NEW_EDITING';
  reuse.disabled=!models.length||busy||pending()||state.locked;
  catalogHint.textContent=!canManage?'Un Admin debe crear y publicar modelos. Podés reutilizar una versión disponible.':models.length?'También podés reutilizar una versión ya publicada.':'Todavía no hay modelos publicados para reutilizar.';
  reuse.setAttribute('aria-describedby','model-catalog-hint');catalogHint.id='model-catalog-hint';
  create.hidden=selectedVersion||!canManage;
  create.disabled=busy||(state.locked&&!pending())||(!pending()&&(!compiled||complete!==valid.length||fields?.canPublish&&!fields.canPublish()));create.setAttribute('aria-busy',String(busy));
  const caption=busy?'Creando modelo…':pending()?'Reintentar publicación pendiente':createLabel;if(createCaption.textContent!==caption)createCaption.textContent=caption;
  feedback.textContent=message||(!canManage?'Necesitás permiso de administración para crear un modelo.':'');feedback.hidden=!feedback.textContent;
  modelRetry.hidden=(state.mode!=='new'&&isSelected())||!previewFailed||busy||pending();modelRetry.textContent=state.mode==='existing'&&!isSelected()?'Reintentar selección del modelo':'Reintentar Data Contract';
  newModel.hidden=!canManage;newModel.disabled=busy||pending()||state.locked;retry.hidden=state.mode==='new'||!previewFailed;
  contractView.setState({ready,compiled,pending:previewPending,failed:previewFailed,selected:isSelected(),provisional:state.mode==='new'});
 }
 async function preview({focusError=false}={}){
  clearTimeout(timer);const own=++generation;compiled=ready=previewPending=false;previewFailed=false;previewBody=null;contractView.invalidate();contractPanel.setStatus('Validando','pending');contractStatus.textContent='Resolviendo Data Contract…';contractStatus.role='status';changed();
  try{
   if(state.mode==='new'){
    if(!canManage){contractPanel.setStatus('Pendiente','pending');return;}
    if(!fields.sectionValidity().slice(1).every(Boolean)){contractPanel.setStatus('Pendiente','pending');contractStatus.textContent='Revisá la operación y las reglas de costo del modelo.';return;}
    previewBody={configuration:fields.read().configuration};
   }else{if(!isSelected())throw new Error('Elegí un Model y una versión publicada.');previewBody={model_id:state.model_id,version_id:state.version_id};}
   previewPending=true;changed();const source=structuredClone(previewBody),data=source.configuration?.version===2?await previewV2Draft(source.configuration,scope.signal):await post('/api/platform/logistics-models/contract-preview',source,{signal:scope.signal});if(!scope.active||own!==generation)return;
   previewPending=false;
   if(data.provisional!== (state.mode==='new'))throw new Error('El contrato no corresponde a la versión seleccionada.');
   contractCount=Object.keys(data.contracts).length;fields?.setCompiled?.(data);contractView.render(data,previewBody);compiled=true;ready=isSelected();previewFailed=false;
   contractPanel.setStatus(ready?'Estructura lista':'Vista previa',ready?'complete':'pending');if(!pending())message='';changed();
  }catch(error){if(scope.active&&own===generation){previewPending=false;previewFailed=true;fields?.showServerError?.(error.message,{focus:focusError});contractStatus.textContent=error.message;contractStatus.role='alert';contractPanel.setStatus('Revisar contrato','warning');message=error.message;feedback.role='alert';changed();}}
 }
 let previewBody=null;let contractCount=0;
 async function render(){
  const own=++renderGeneration;generation++;clearTimeout(timer);compiled=ready=false;contractView.invalidate();editor.replaceChildren();
  if(state.mode==='new'){
   fields=mountModelFields(editor,scope,state.new_model,{wizard:true});
   if(pending()||!canManage||state.locked)fields.lock();
   if(pending())message='Hay una publicación pendiente. Se conserva la configuración y su identidad para reintentar sin crear otro modelo.';
  }else{
   let detail;try{detail=await api('/api/platform/logistics-models/'+state.model_id,{signal:scope.signal});}catch(error){if(own!==renderGeneration)return;throw error;}if(!scope.active||own!==renderGeneration)return;
   const chosen=detail.versions.find(v=>v.id===state.version_id);if(detail.model.status!=='active'||!chosen)throw new Error('La versión publicada ya no está disponible. Elegí otra versión.');selected=detail;if(!models.some(m=>m.id===detail.model.id))models.push({...detail.model,versions:detail.versions});
   const selectedSummary=el('div',undefined,'model-wizard-selection'),text=el('div');text.append(el('h3',detail.model.name),el('p',chosen.config_jsonb.version===2?'Modelo publicado seleccionado':'Modelo seleccionado · Versión '+chosen.version,'d-metadata'));
   selectedSummary.append(text);editor.append(selectedSummary);
   fields=mountModelFields(editor,scope,{...detail.model,configuration:chosen.config_jsonb},{wizard:true,version:chosen.version});fields.lock({published:true});
  }
  changed();await preview();
 }
 function fail(error){if(!scope.active)return;ready=compiled=false;previewFailed=true;message=error.message;feedback.role='alert';changed();}
 function startNew(){
  if(!canManage||busy||pending()||state.locked)return;
  if(state.mode==='new'){const input=editor.querySelector('[name=model_name]');input?.closest('details')?.setAttribute('open','');input?.focus();return;}
  state.mode='new';state.model_id='';state.version_id='';state.intent=null;selected=null;message='';render().then(persist).catch(fail);changed();
 }
 async function openPicker(){
  if(reuse.disabled)return;pickerOpen=true;sync();
  if(state.mode==='new'&&fields)state.new_model=fields.read();
  const dialog=el('dialog',undefined,'d-modal model-wizard-picker'),body=el('div',undefined,'d-modal__body'),actions=el('div',undefined,'d-modal__actions'),title=el('h2','Seleccionar modelo existente','d-modal__title'),hint=el('p','Elegí una versión publicada. Su configuración se conserva sin modificaciones.','d-metadata');
  title.id='model-picker-title';dialog.setAttribute('aria-labelledby',title.id);dialog.dataset.dationTest='model-picker';body.append(title,hint);
  const model=field(body,'Logistics Model',{name:'reuse_model',options:[['','Elegí un modelo'],...models.map(m=>[m.id,m.name])],value:''}),description=el('p','','d-metadata'),version=field(body,'Model Version',{name:'reuse_version',options:[['','Elegí una versión publicada']],value:''}),error=el('p','','d-field__error');error.role='alert';body.append(description,error);if(saga10){version.closest('.d-field').hidden=true;hint.textContent='Elegí un modelo publicado. Se selecciona su última publicación verificada.';}
  let detail=null,request=0,choosing=false;
  const cancel=button('Cancelar',()=>mounted.close()),confirm=button('Seleccionar esta versión',async()=>{
   if(choosing||!detail||!version.value)return;choosing=true;confirm.disabled=true;
   try{
    const check=await api('/api/platform/logistics-models/'+model.value,{signal:scope.signal});if(!scope.active||!dialog.open)return;
    if(check.model.status!=='active'||!check.versions.some(v=>v.id===version.value))throw new Error('La versión publicada ya no está disponible. Elegí otra versión.');
    state.mode='existing';state.model_id=model.value;state.version_id=version.value;state.intent=null;selected=check;message='';persist();mounted.close();await render();persist();onSelected();
   }catch(e){if(dialog.open){error.textContent=e.message;choosing=false;confirm.disabled=false;}else fail(e);}
  },'primary');confirm.disabled=true;actions.append(cancel,confirm);dialog.append(body,actions);form.append(dialog);
  const mounted=mountDialog({dialog,trigger:reuse,initialFocus:model});
  scope.listen(model,'change',async()=>{
   const own=++request;detail=null;confirm.disabled=true;version.replaceChildren();description.textContent='';error.textContent='';if(!model.value)return;
   try{const data=await api('/api/platform/logistics-models/'+model.value,{signal:scope.signal});if(!scope.active||!dialog.open||own!==request)return;if(data.model.status!=='active'||!data.versions.length)throw new Error('No hay versiones publicadas disponibles.');detail=data;description.textContent=data.model.description||'Sin descripción.';for(const v of [...data.versions].sort((a,b)=>b.version-a.version)){const o=el('option','Versión '+v.version);o.value=v.id;version.append(o);}if(saga10)version.value=[...data.versions].sort((a,b)=>b.version-a.version)[0].id;confirm.disabled=false;}catch(e){if(scope.active&&dialog.open&&own===request)error.textContent=e.message;}
  });
  dialog.addEventListener('close',()=>{request++;pickerOpen=false;mounted.dispose();dialog.remove();sync();},{once:true});scope.own(()=>{mounted.dispose();dialog.remove();});mounted.open();
 }
 async function publish(){
  // Older Case drafts locked their model before publication. Resume that exact
  // pending intent without allowing its configuration/identity to change.
  if(busy||(state.locked&&!pending())||!canManage||isSelected())return;
  if(!pending()){
   const errors=fields.showErrors();if(Object.keys(errors).length){message=Object.values(errors).join(' ');feedback.role='alert';sync();editor.querySelector('[aria-invalid=true]')?.focus();return;}
   if(!compiled||fields.canPublish&&!fields.canPublish())return;
   state.new_model=fields.read();const value=state.new_model;
   state.intent={model_id:value.id,version_id:crypto.randomUUID(),body:{id:value.id,name:value.name,description:value.description||null,configuration:value.configuration},revision:null};
  }
  busy=true;fields.lock();feedback.role='status';message='';generation++;clearTimeout(timer);changed();persist();
  try{
   if(state.intent.revision===null){
    const saved=await post('/api/platform/logistics-models',state.intent.body,{signal:scope.signal});
    if(saved.model.id!==state.intent.model_id||!Number.isInteger(saved.model.revision))throw new Error('La respuesta no confirma la identidad del modelo.');
    state.intent.revision=saved.model.revision;persist();
   }
   const published=await post('/api/platform/logistics-models/'+state.intent.model_id+'/versions',{version_id:state.intent.version_id,expected_revision:state.intent.revision},{signal:scope.signal});
   if(published.version.id!==state.intent.version_id||published.version.model_id!==state.intent.model_id)throw new Error('La respuesta no confirma la versión publicada.');
   state.intent.published=true;state.model_id=state.intent.model_id;state.version_id=published.version.id;state.mode='existing';state.new_model={...state.new_model,id:crypto.randomUUID(),expected_revision:1};persist();
   if(!scope.active)return;
   await render();message='Modelo creado y seleccionado correctamente';feedback.role='status';persist();onSelected();
  }catch(error){if(scope.active){message='Publicar Logistics Model: '+error.message;feedback.role='alert';previewFailed=true;}}
  finally{busy=false;if(scope.active)changed();}
 }
 // Invalidate immediately: stale provisional responses cannot enable publication.
 const edit=event=>{
  if(state.mode!=='new'||pending()||state.locked)return;
  fields.showErrors();
  if(!['model_name','model_description','model_status'].includes(event.target.name)){fields.invalidateCompiled?.();generation++;compiled=ready=previewPending=false;clearTimeout(timer);timer=setTimeout(()=>preview(),250);}
  changed();
 };
 scope.listen(editor,'keydown',event=>{if(event.key==='Enter'&&event.target.matches('input:not([type=checkbox]):not([type=radio])'))event.preventDefault();});
 scope.listen(editor,'input',edit);scope.listen(editor,'change',edit);
 scope.listen(editor,'model-review',changed);
 scope.listen(editor,'model-editor-mode',event=>{
  if(state.mode!=='new'||busy||pending()||state.locked||!canManage)return;
  state.new_model=event.detail;render().then(persist).catch(fail);
 });
 await render().catch(fail);modelBlock.hidden=false;
 return {
  modelPanel,contractPanel,draft:readDraft,
  read:()=>({model_id:state.mode==='new'?state.intent?.model_id||state.new_model.id:state.model_id,version_id:state.version_id}),
  summary:()=>isSelected()?selected.model.name+' · versión '+selected.versions.find(v=>v.id===state.version_id).version:state.mode==='existing'?'Modelo publicado pendiente de verificación':(fields?.read().name||'Nuevo Model')+' · sin publicar',
  get ready(){return ready;},get contractCount(){return contractCount;},get selected(){return isSelected();},
  validate(){return ready?{}:{model_version_id:'Completá el Model y esperá la resolución válida del Data Contract.'};},
  async ensurePublished(save){
   // Legacy callers retain the same entry point; the wizard publishes explicitly.
   if(!ready)throw new Error('Resolvé el Data Contract antes de crear el Case.');
   state.locked=true;sync();save();return state.version_id;
  }
 };
}
