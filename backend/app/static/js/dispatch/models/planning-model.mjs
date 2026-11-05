import {api,post,download} from '../shared.mjs';
import {el,button,field,section} from './forms.mjs';
import {mountModelFields,defaultConfiguration} from './model-fields.mjs';

// Compose the existing Model editor with the server's ingestion contract compiler.
export async function mountPlanningModel(form,scope,{draft={},modelId='',canManage,onChange=()=>{}}){
 const modelBlock=section(form,'01 Logistics Model','Definí cómo opera tu logística o reutilizá una versión publicada.'),controls=el('div',undefined,'ultimate-actions'),editor=el('div');modelBlock.classList.add('ultimate-planning-model');modelBlock.append(controls,editor);
 const contractBlock=section(form,'02 Data Contract','Revisá la estructura requerida. Los archivos operativos se cargan desde el Decision Graph.'),contractStatus=el('p','Seleccioná o configurá un Model.','d-metadata'),contractRows=el('div',undefined,'ultimate-contracts'),retry=button('Reintentar Data Contract',()=>preview());retry.hidden=true;contractStatus.role='status';contractBlock.append(contractStatus,retry,contractRows);
 const state={mode:draft.mode||'existing',model_id:draft.model_id||modelId,version_id:draft.version_id||'',new_model:draft.new_model||{id:crypto.randomUUID(),name:'',description:'',status:'active',expected_revision:1,configuration:defaultConfiguration(window.dationSession.identity.workspace.currency)},intent:draft.intent||null,locked:!!draft.locked};
 let fields=null,selected=null,selector=null,version=null,ready=false,generation=0,renderGeneration=0,timer=null,previewBody=null;
 scope.own(()=>clearTimeout(timer));
 const models=[];let offset=0,total=0;
 do{const page=await api('/api/platform/logistics-models?'+new URLSearchParams({limit:50,offset}),{signal:scope.signal});if(!scope.active)return;models.push(...page.items.filter(m=>m.status==='active'&&m.versions.length));offset+=50;total=page.total;if(offset<total&&!page.items.length)throw new Error('La lista de Models cambió. Recargá la configuración.');}while(offset<total);
 if(!models.length)state.mode='new';
 if(state.model_id&&!models.some(m=>m.id===state.model_id)&&state.mode==='existing')state.model_id='';
 const readDraft=()=>({...state,new_model:state.mode==='new'&&fields?fields.read():state.new_model});
 function renderContract(data){
  contractRows.replaceChildren();
  contractStatus.textContent=data.provisional?'Vista previa derivada del Model. Se vinculará a su versión al crear el Case.':'Contrato de la versión publicada seleccionada.';
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
  const own=++generation;ready=false;previewBody=null;retry.hidden=true;contractRows.replaceChildren();contractStatus.textContent='Resolviendo Data Contract…';contractStatus.role='status';onChange();
  try{
   if(state.mode==='new'){
    if(!canManage)throw new Error('Un Admin debe crear y publicar el primer Logistics Model.');
    const errors=fields.validate();if(Object.keys(errors).length)throw new Error(Object.values(errors).join(' '));
    previewBody={configuration:fields.read().configuration};
   }else{if(!state.version_id)throw new Error('Elegí un Model y una versión publicada.');previewBody={model_id:state.model_id,version_id:state.version_id};}
   const data=await post('/api/platform/logistics-models/contract-preview',previewBody,{signal:scope.signal});if(!scope.active||own!==generation)return;
   renderContract(data);ready=true;onChange();
  }catch(error){if(scope.active&&own===generation){contractStatus.textContent=error.message;contractStatus.role='alert';retry.hidden=false;onChange();}}
 }
 async function render(){
  const own=++renderGeneration;
  generation++;clearTimeout(timer);ready=false;onChange();editor.replaceChildren();controls.replaceChildren();
  if(models.length){controls.append(button('Usar Model publicado',()=>changeMode('existing')));if(canManage)controls.append(button('Crear nuevo Logistics Model',()=>changeMode('new')));}
  if(state.mode==='new'){
   editor.append(el('h3','Crear nuevo Logistics Model','d-section-title'));
   fields=mountModelFields(editor,scope,state.new_model);const status=editor.querySelector('[name=model_status]');status.closest('.d-field').hidden=true;
   if(state.intent||!canManage)fields.lock();
   if(state.intent)editor.append(el('p','Hay un intento de guardado pendiente. Se conserva la configuración para reintentar la creación del Case.','d-metadata'));
  }else{
   selector=field(editor,'Logistics Model',{name:'model_id',options:models.map(m=>[m.id,m.name]),value:state.model_id||models[0].id,required:true});state.model_id=selector.value;
   const detail=await api('/api/platform/logistics-models/'+state.model_id,{signal:scope.signal});if(!scope.active||own!==renderGeneration)return;selected=detail;
   version=field(editor,'Model Version',{name:'model_version_id',options:detail.versions.map(v=>[v.id,'Versión '+v.version]),value:state.version_id||detail.versions[0]?.id,required:true});state.version_id=version.value;
   const showVersion=()=>{editor.querySelector('[data-published-model-fields]')?.remove();const v=detail.versions.find(v=>v.id===state.version_id);if(!v)return;const host=el('div');host.dataset.publishedModelFields='';editor.append(host);fields=mountModelFields(host,scope,{...detail.model,configuration:v.config_jsonb});fields.lock();host.querySelector('[name=model_status]').closest('.d-field').hidden=true;};showVersion();
   scope.listen(selector,'change',()=>{state.model_id=selector.value;state.version_id='';render().catch(fail);});
   scope.listen(version,'change',()=>{state.version_id=version.value;showVersion();preview();});
  }
  if(state.locked)for(const n of modelBlock.querySelectorAll('input,select,textarea,button'))n.disabled=true;
  for(const b of controls.querySelectorAll('button'))b.disabled=!!state.intent||!!state.locked;
  await preview();
 }
 function fail(error){if(scope.active){ready=false;contractStatus.textContent=error.message;contractStatus.role='alert';onChange();}}
 function changeMode(mode){if(state.intent||state.locked)return;if(state.mode==='new'&&fields)state.new_model=fields.read();state.mode=mode;state.version_id='';render().catch(fail);}
 // Invalidate a preview immediately; responses from older configurations never unlock Case creation.
 scope.listen(editor,'input',event=>{if(state.mode!=='new'||state.intent)return;if(['model_name','model_description','model_status'].includes(event.target.name)){onChange();return;}generation++;ready=false;onChange();clearTimeout(timer);timer=setTimeout(()=>preview(),250);});
 await render();
 return {
  draft:readDraft,
  read:()=>({model_id:state.mode==='new'?state.intent?.model_id||state.new_model.id:state.model_id,version_id:state.mode==='new'?state.intent?.version_id||'':state.version_id}),
  summary:()=>state.mode==='new'?(fields?.read().name||'Nuevo Model')+(state.version_id?' · versión 1':' · nueva versión'):selected?.model.name+' · versión '+(selected?.versions.find(v=>v.id===state.version_id)?.version||''),
  get ready(){return ready;},
  validate(){const errors=state.mode==='new'?fields.validate():{};if(state.mode==='new'&&!fields.read().name)errors.model_name='Ingresá el nombre del Logistics Model.';if(!ready)errors.model_version_id='Completá el Model y esperá la resolución válida del Data Contract.';return errors;},
  async ensurePublished(persist){
   if(!ready)throw new Error('Resolvé el Data Contract antes de crear el Case.');
   state.locked=true;for(const n of modelBlock.querySelectorAll('input,select,textarea,button'))n.disabled=true;persist();
   if(state.mode==='existing')return state.version_id;
   const value=fields.read();
   state.intent||={model_id:value.id,version_id:crypto.randomUUID(),body:{id:value.id,name:value.name,description:value.description||null,configuration:value.configuration},revision:null};fields.lock();persist();
   try{const saved=await post('/api/platform/logistics-models',state.intent.body,{signal:scope.signal});state.intent.revision??=saved.model.revision;persist();}catch(error){throw new Error('Crear Logistics Model: '+error.message);}
   try{const published=await post('/api/platform/logistics-models/'+state.intent.model_id+'/versions',{version_id:state.intent.version_id,expected_revision:state.intent.revision},{signal:scope.signal});state.version_id=published.version.id;persist();return state.version_id;}catch(error){throw new Error('Publicar Logistics Model: '+error.message);}
  }
 };
}
