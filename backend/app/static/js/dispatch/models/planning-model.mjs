import {api,post,download} from '../shared.mjs';
import {mountDialog} from '../../platform/components.mjs';
import {el,button,field,collapsibleSection} from './forms.mjs';
import {mountModelFields,defaultConfiguration} from './model-fields.mjs';
import {wizardIcon} from './wizard-ui.mjs';

export async function mountPlanningModel(form,scope,{draft={},modelId='',canManage,onChange=()=>{},persist=()=>{},onSelected=()=>{}}){
 const modelPanel=collapsibleSection(form,'01. Logistics Model','Definí la lógica operativa base del modelo logístico que vas a usar en este Case.',{open:true,initialStatus:'En configuración'}),modelBlock=modelPanel.body;
 modelPanel.details.dataset.dationTest='core-model';modelPanel.details.dataset.modelState='LOADING';modelPanel.setStatus('Cargando');modelPanel.details.classList.add('model-wizard');modelBlock.classList.add('ultimate-planning-model');modelBlock.hidden=true;
 const summary=modelPanel.details.querySelector('summary'),tile=el('span',undefined,'model-wizard-tile'),heading=el('span',undefined,'model-wizard-heading');tile.append(wizardIcon('layers'));heading.append(summary.querySelector('.ultimate-disclosure__title'),modelBlock.previousElementSibling);summary.prepend(tile,heading);
 const intro=el('div',undefined,'model-wizard-intro'),reuse=button('',openPicker),catalogHint=el('p',undefined,'d-metadata'),introIcon=wizardIcon('database');reuse.append(wizardIcon('folder'),el('span','Seleccionar modelo existente'));reuse.dataset.dationTest='model-reuse';intro.append(introIcon,el('strong','Creá un nuevo modelo operativo o reutilizá uno ya publicado.'),reuse,catalogHint);
 const editor=el('div'),feedback=el('p','','model-wizard-feedback'),footer=el('footer',undefined,'model-wizard-footer'),progress=el('div',undefined,'model-wizard-progress'),ring=el('span',undefined,'model-wizard-ring'),progressText=el('div'),count=el('p','','d-metadata'),create=button('',publish,'primary');
 feedback.role='status';feedback.setAttribute('aria-live','polite');feedback.dataset.dationTest='model-feedback';progress.dataset.dationTest='model-progress';progress.role='status';progressText.append(el('strong','Configuración del modelo'),count);ring.setAttribute('aria-hidden','true');progress.append(ring,progressText);footer.append(progress,create);modelBlock.append(intro,editor,feedback,footer);
 create.dataset.dationTest='model-create';const createCaption=el('span','Crear y seleccionar modelo');create.append(wizardIcon('check'),createCaption);
 const contractPanel=collapsibleSection(form,'02 Data Contract','Revisá las variables y descargá las plantillas derivadas del Logistics Model. Los datos se cargan luego desde el Decision Graph.',{initialStatus:'Pendiente'}),contractBlock=contractPanel.body,contractStatus=el('p','Seleccioná o configurá un Model.','d-metadata'),contractRows=el('div',undefined,'ultimate-contracts'),retry=button('Reintentar Data Contract',()=>preview()),modelRetry=button('Reintentar Data Contract',async()=>{if(state.mode==='existing'&&!isSelected()){await render().catch(fail);if(ready)onSelected();}else await preview();});
 retry.hidden=modelRetry.hidden=true;contractStatus.role='status';contractBlock.append(contractStatus,retry,contractRows);feedback.after(modelRetry);contractPanel.details.dataset.dationTest='core-contract';
 const newDraft=()=>({id:crypto.randomUUID(),name:'',description:'',status:'active',expected_revision:1,configuration:defaultConfiguration(window.dationSession.identity.workspace.currency)});
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
  const valid=fields?.sectionValidity()||[false,false,false],complete=valid.filter(Boolean).length;
  ring.style.setProperty('--model-progress',String(complete/3*100)+'%');count.textContent=complete+' de 3 secciones completas';
  const selectedVersion=isSelected();
  modelPanel.setStatus(selectedVersion?'Configurado':!canManage?'Sólo lectura':previewFailed||pending()&&!busy?'Revisar configuración':'En configuración',selectedVersion?'complete':previewFailed?'warning':'pending');
  modelPanel.details.dataset.modelState=busy?'NEW_PUBLISHING':pickerOpen?'REUSE_PICKER':selectedVersion?'MODEL_SELECTED':!canManage?'READ_ONLY':previewFailed||pending()?'ERROR_RECOVERABLE':previewPending?'NEW_VALIDATING':compiled&&complete===3?'NEW_READY_TO_CREATE':'NEW_EDITING';
  reuse.disabled=!models.length||busy||pending()||state.locked;
  catalogHint.textContent=!canManage?'Un Admin debe crear y publicar modelos. Podés reutilizar una versión disponible.':models.length?'También podés reutilizar una versión ya publicada.':'Todavía no hay modelos publicados para reutilizar.';
  reuse.setAttribute('aria-describedby','model-catalog-hint');catalogHint.id='model-catalog-hint';
  create.hidden=selectedVersion||!canManage;
  create.disabled=busy||(state.locked&&!pending())||(!pending()&&(!compiled||complete!==3));create.setAttribute('aria-busy',String(busy));
  const caption=busy?'Creando modelo…':pending()?'Reintentar publicación pendiente':'Crear y seleccionar modelo';if(createCaption.textContent!==caption)createCaption.textContent=caption;
  feedback.textContent=message||(!canManage?'Necesitás permiso de administración para crear un modelo.':'');feedback.hidden=!feedback.textContent;
  modelRetry.hidden=(state.mode!=='new'&&isSelected())||!previewFailed||busy||pending();modelRetry.textContent=state.mode==='existing'&&!isSelected()?'Reintentar selección del modelo':'Reintentar Data Contract';
  const another=editor.querySelector('[data-model-new]');if(another)another.disabled=busy||state.locked;retry.hidden=state.mode==='new'||!previewFailed;
 }
 function renderContract(data){
  contractRows.replaceChildren();
  contractStatus.textContent=data.provisional?'Vista previa preparatoria. Publicá y seleccioná el modelo para confirmar su contrato.':'Contrato de la versión publicada seleccionada.';
  for(const [entity,label]of [['transport_demand','Órdenes / Demanda'],['transport_resources','Flota / Recursos']]){
   const c=data.contracts[entity],part=el('section',undefined,'ultimate-contract');part.append(el('h3',label+' · Requerido','d-card-title'));
   const wrap=el('div',undefined,'dispatch-table-wrap');wrap.tabIndex=0;wrap.role='region';wrap.setAttribute('aria-label','Data Contract · '+label);
   const table=el('table'),head=el('thead'),titles=el('tr');for(const name of ['Campo canónico','Tipo / unidad','Requisito y validación']){const th=el('th',name);th.scope='col';titles.append(th);}head.append(titles);table.append(head);const body=el('tbody');
   for(const f of c.fields){const row=el('tr');for(const value of [f.public_header,f.type+(f.unit?' · '+f.unit:''),(f.nullable?'Admite vacío':'Requerido')+(Object.keys(f.applies_when).length?' cuando '+JSON.stringify(f.applies_when):'')+' · '+JSON.stringify(f.validation)])row.append(el('td',value));body.append(row);}table.append(body);wrap.append(table);part.append(wrap);
   const source=structuredClone(previewBody),template=button('Descargar template de '+label,async()=>{
    try{const response=await fetch('/api/platform/logistics-models/contract-preview/templates/'+entity,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(source),signal:scope.signal});if(!response.ok)throw new Error('No se pudo descargar el template. Volvé a resolver el contrato.');download(entity+'.csv',await response.text(),'text/csv;charset=utf-8');}catch(error){if(scope.active){contractStatus.textContent=error.message;contractStatus.role='alert';}}
   });part.append(template);contractRows.append(part);
  }
 }
 async function preview(){
  clearTimeout(timer);const own=++generation;compiled=ready=previewPending=false;previewFailed=false;previewBody=null;contractRows.replaceChildren();contractPanel.setStatus('Validando','pending');contractStatus.textContent='Resolviendo Data Contract…';contractStatus.role='status';changed();
  try{
   if(state.mode==='new'){
    if(!canManage){contractPanel.setStatus('Pendiente','pending');return;}
    if(!fields.sectionValidity().slice(1).every(Boolean)){contractPanel.setStatus('Pendiente','pending');contractStatus.textContent='Revisá la operación y las reglas de costo del modelo.';return;}
    previewBody={configuration:fields.read().configuration};
   }else{if(!isSelected())throw new Error('Elegí un Model y una versión publicada.');previewBody={model_id:state.model_id,version_id:state.version_id};}
   previewPending=true;changed();const source=structuredClone(previewBody),data=await post('/api/platform/logistics-models/contract-preview',source,{signal:scope.signal});if(!scope.active||own!==generation)return;
   previewPending=false;
   if(data.provisional!== (state.mode==='new'))throw new Error('El contrato no corresponde a la versión seleccionada.');
   renderContract(data);compiled=true;ready=isSelected();previewFailed=false;
   contractPanel.setStatus(ready?'Validado':'Vista previa',ready?'complete':'pending');if(!pending())message='';changed();
  }catch(error){if(scope.active&&own===generation){previewPending=false;previewFailed=true;contractStatus.textContent=error.message;contractStatus.role='alert';contractPanel.setStatus('Revisar contrato','warning');message=error.message;feedback.role='alert';changed();}}
 }
 let previewBody=null;
 async function render(){
  const own=++renderGeneration;generation++;clearTimeout(timer);compiled=ready=false;editor.replaceChildren();
  if(state.mode==='new'){
   fields=mountModelFields(editor,scope,state.new_model,{wizard:true});
   if(pending()||!canManage||state.locked)fields.lock();
   if(pending())message='Hay una publicación pendiente. Se conserva la configuración y su identidad para reintentar sin crear otro modelo.';
  }else{
   let detail;try{detail=await api('/api/platform/logistics-models/'+state.model_id,{signal:scope.signal});}catch(error){if(own!==renderGeneration)return;throw error;}if(!scope.active||own!==renderGeneration)return;
   const chosen=detail.versions.find(v=>v.id===state.version_id);if(detail.model.status!=='active'||!chosen)throw new Error('La versión publicada ya no está disponible. Elegí otra versión.');selected=detail;if(!models.some(m=>m.id===detail.model.id))models.push({...detail.model,versions:detail.versions});
   const selectedSummary=el('div',undefined,'model-wizard-selection'),text=el('div');text.append(el('h3',detail.model.name),el('p','Modelo seleccionado · Versión '+chosen.version,'d-metadata'));
   const another=button('Crear otro modelo',()=>{if(busy||pending()||state.locked)return;state.mode='new';state.model_id='';state.version_id='';state.intent=null;selected=null;message='';render().catch(fail);changed();});another.dataset.modelNew='';another.hidden=!canManage;another.disabled=state.locked||busy;selectedSummary.append(text,another);editor.append(selectedSummary);
   fields=mountModelFields(editor,scope,{...detail.model,configuration:chosen.config_jsonb},{wizard:true,version:chosen.version});fields.lock();
  }
  changed();await preview();
 }
 function fail(error){if(!scope.active)return;ready=compiled=false;previewFailed=true;message=error.message;feedback.role='alert';changed();}
 async function openPicker(){
  if(reuse.disabled)return;pickerOpen=true;sync();
  if(state.mode==='new'&&fields)state.new_model=fields.read();
  const dialog=el('dialog',undefined,'d-modal model-wizard-picker'),body=el('div',undefined,'d-modal__body'),actions=el('div',undefined,'d-modal__actions'),title=el('h2','Seleccionar modelo existente','d-modal__title'),hint=el('p','Elegí una versión publicada. Su configuración se conserva sin modificaciones.','d-metadata');
  title.id='model-picker-title';dialog.setAttribute('aria-labelledby',title.id);dialog.dataset.dationTest='model-picker';body.append(title,hint);
  const model=field(body,'Logistics Model',{name:'reuse_model',options:[['','Elegí un modelo'],...models.map(m=>[m.id,m.name])],value:''}),description=el('p','','d-metadata'),version=field(body,'Model Version',{name:'reuse_version',options:[['','Elegí una versión publicada']],value:''}),error=el('p','','d-field__error');error.role='alert';body.append(description,error);
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
   try{const data=await api('/api/platform/logistics-models/'+model.value,{signal:scope.signal});if(!scope.active||!dialog.open||own!==request)return;if(data.model.status!=='active'||!data.versions.length)throw new Error('No hay versiones publicadas disponibles.');detail=data;description.textContent=data.model.description||'Sin descripción.';for(const v of data.versions){const o=el('option','Versión '+v.version);o.value=v.id;version.append(o);}confirm.disabled=false;}catch(e){if(scope.active&&dialog.open&&own===request)error.textContent=e.message;}
  });
  dialog.addEventListener('close',()=>{request++;pickerOpen=false;mounted.dispose();dialog.remove();sync();},{once:true});scope.own(()=>{mounted.dispose();dialog.remove();});mounted.open();
 }
 async function publish(){
  // Older Case drafts locked their model before publication. Resume that exact
  // pending intent without allowing its configuration/identity to change.
  if(busy||(state.locked&&!pending())||!canManage||isSelected())return;
  if(!pending()){
   const errors=fields.showErrors();if(Object.keys(errors).length){message=Object.values(errors).join(' ');feedback.role='alert';sync();editor.querySelector('[aria-invalid=true]')?.focus();return;}
   if(!compiled)return;
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
  if(!['model_name','model_description','model_status'].includes(event.target.name)){generation++;compiled=ready=previewPending=false;clearTimeout(timer);timer=setTimeout(()=>preview(),250);}
  changed();
 };
 scope.listen(editor,'input',edit);scope.listen(editor,'change',edit);
 await render().catch(fail);modelBlock.hidden=false;
 return {
  modelPanel,contractPanel,draft:readDraft,
  read:()=>({model_id:state.mode==='new'?state.intent?.model_id||state.new_model.id:state.model_id,version_id:state.version_id}),
  summary:()=>isSelected()?selected.model.name+' · versión '+selected.versions.find(v=>v.id===state.version_id).version:state.mode==='existing'?'Modelo publicado pendiente de verificación':(fields?.read().name||'Nuevo Model')+' · sin publicar',
  get ready(){return ready;},get selected(){return isSelected();},
  validate(){return ready?{}:{model_version_id:'Completá el Model y esperá la resolución válida del Data Contract.'};},
  async ensurePublished(save){
   // Legacy callers retain the same entry point; the wizard publishes explicitly.
   if(!ready)throw new Error('Resolvé el Data Contract antes de crear el Case.');
   state.locked=true;sync();save();return state.version_id;
  }
 };
}
