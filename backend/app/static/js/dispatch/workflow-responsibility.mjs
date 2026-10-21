import {api} from './shared.mjs';
import {createScope} from './lifecycle.mjs';
import {ensureStylesheet} from './styles.mjs';

const TYPES={
 data_preparation:{group:'data',label:'Responsable de datos',role:'Data Owner o Data Steward'},
 owner:{group:'decision_owner',label:'Responsable de la decisión',role:'Decision Owner'},
 approver:{group:'approver',label:'Aprobador asignado',role:'Approver'},
};
export function executionPermission(identity=globalThis.window?.dationSession?.identity){
 return identity?.membership?.access_role==='viewer'?'Tu rol permite consultar, pero no ejecutar decisiones.':null;
}
export function responsibilityProblem(snapshot,stageKey,kind='execute'){
 if(!snapshot?.gates_enforced)return null;
 const stages=snapshot.stages||{},data=stages.data_preparation;
 if(kind!=='approve'&&!data?.owner_eligible)return 'Seleccioná un responsable de datos activo y elegible antes de continuar.';
 if(kind==='data')return null;
 const stage=stages[stageKey],field=kind==='approve'?'approver':'owner';
 return stage?.[field+'_eligible']?null:kind==='approve'
  ?'Seleccioná un aprobador asignado activo y elegible antes de aprobar.'
  :'Seleccioná un responsable de la decisión activo y elegible antes de ejecutar.';
}
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function button(text,handler){const b=el('button',text,'d-button d-button--secondary');b.type='button';b.addEventListener('click',handler);return b;}
let sequence=0;

/** One selector for Data, config and validation; SQL remains the authority. */
export function mountResponsibilitySelector(root,{caseId,stageKey,field='owner',snapshot,onSaved,onPrepare}){
 ensureStylesheet('workflow-context-styles','/static/css/workflow-context.css','v2-phase5').catch(()=>{});
 const scope=createScope(root),id='responsibility-'+(++sequence),type=TYPES[stageKey==='data_preparation'?'data_preparation':field];
 let current=snapshot,controller,generation=0;
 root.className='workflow-responsibility';root.id='workflow-responsibility';root.dataset.workflowResponsibility=stageKey;
 function render(){
  controller?.abort();generation++;
  const stage=current?.stages?.[stageKey]||{},person=stage[field],eligible=stage[field+'_eligible'];
  const info=el('div'),heading=el('h2',type.label,'d-card-title'),value=el('p',person?.name||'Sin asignar','d-body');
  info.append(heading,value);
  if(person&&!eligible)info.append(el('p','Esta persona ya no cumple los requisitos. Un administrador debe reasignar la responsabilidad.','d-metadata'));
  else info.append(el('p',type.role,'d-metadata'));
  root.replaceChildren(info);
  if(current?.can_assign)root.append(button(person?'Cambiar':'Seleccionar responsable',edit));
  else {
   if(!person)root.append(el('p','Un administrador debe asignar esta responsabilidad desde esta etapa o desde Decision Center.','d-metadata'));
   if(onPrepare&&(!current.pending||current.can_prepare))root.append(button(current.pending?'Registrar caso para asignar responsable':'Actualizar responsabilidad',async event=>{
    const trigger=event.currentTarget;trigger.disabled=true;
    try{const result=await onPrepare();if(scope.active){current=result;render();onSaved?.(result);}}
    catch(error){if(scope.active){const message=el('p',error.message);message.role='alert';root.append(message);trigger.disabled=false;}}
   }));
  }
 }
 async function edit(){
  if(onPrepare){
   const trigger=root.querySelector('button'),own=++generation;trigger.disabled=true;
   try{const result=await onPrepare();if(!scope.active||own!==generation)return;current=result;if(!current.can_assign){render();onSaved?.(result);return;}}
   catch(error){if(scope.active&&own===generation){const message=el('p',error.message);message.role='alert';root.append(message);trigger.disabled=false;}return;}
  }
  controller?.abort();const own=++generation;let offset=0,query='',saving=false,request=0;
  const panel=el('div',undefined,'workflow-responsibility__editor'),search=el('form',undefined,'workflow-responsibility__search');
  const label=el('label','Buscar personas elegibles','d-label'),input=el('input',undefined,'d-input');input.id=id+'-search';input.type='search';input.maxLength=120;label.htmlFor=input.id;
  const find=el('button','Buscar','d-button d-button--secondary');find.type='submit';search.append(label,input,find);
  const choiceLabel=el('label',type.label,'d-label'),select=el('select',undefined,'d-input');select.id=id+'-choice';choiceLabel.htmlFor=select.id;
  const message=el('p','Cargando candidatos…','d-metadata');message.role='status';select.setAttribute('aria-describedby',id+'-status');message.id=id+'-status';
  const error=el('p');error.role='alert';const actions=el('div',undefined,'workflow-context-actions');
  const save=button('Guardar',commit),cancel=button('Cancelar',()=>{if(!saving){render();root.querySelector('button')?.focus();}});save.disabled=true;
  const prev=button('Anterior',()=>{offset=Math.max(0,offset-25);load();}),next=button('Siguiente',()=>{offset+=25;load();});
  const pager=el('div',undefined,'workflow-context-actions');pager.append(prev,next);actions.append(cancel,save);
  panel.append(search,choiceLabel,select,message,error,pager,actions);root.append(panel);
  root.querySelector('button').hidden=true;
  search.addEventListener('submit',event=>{event.preventDefault();query=input.value.trim();offset=0;load();});
  select.addEventListener('change',()=>save.disabled=!select.value||saving);
  async function load(){
   controller?.abort();controller=new AbortController();const pending=controller,version=++request;select.disabled=true;save.disabled=true;prev.disabled=next.disabled=true;error.replaceChildren();message.textContent='Cargando candidatos…';
   try{
    const result=await api('/api/platform/team?'+new URLSearchParams({candidates:'true',responsibility:type.group,limit:25,offset,q:query}),{signal:controller.signal});
    if(!scope.active||own!==generation||version!==request)return;
    select.replaceChildren();const empty=el('option','Seleccioná una persona…');empty.value='';select.append(empty);
    for(const person of result.members||[]){const option=el('option',person.name+' · '+person.email);option.value=person.user_id;select.append(option);}
    const hasMembers=Boolean(result.members?.length);select.disabled=!hasMembers;
    message.textContent=hasMembers?'Sólo se muestran personas activas con '+type.role+' y permisos operativos.':query?'No hay personas elegibles con esta búsqueda.':'No hay personas con responsabilidad '+type.role+' y permisos operativos en este Workspace. Un administrador debe asignarla desde Equipo.';
    if(!hasMembers&&current.can_assign){const team=button('Ir a Equipo',()=>window.dationNavigate?.('platform-team'));message.append(document.createTextNode(' '),team);}
    prev.disabled=!offset;next.disabled=offset+25>=result.total;
   }catch(exc){if(scope.active&&own===generation&&version===request&&!pending.signal.aborted){message.textContent='';error.append(document.createTextNode(exc.message),button('Reintentar',load));}}
  }
  async function commit(){
   if(!select.value||saving||!scope.active)return;
   saving=true;save.disabled=cancel.disabled=true;save.setAttribute('aria-busy','true');error.replaceChildren();
   const stage=current.stages?.[stageKey]||{};
   const payload={expected_updated_at:stage.updated_at||null,owner_user_id:stage.owner?.id||null,approver_user_id:stage.approver?.id||null};payload[field+'_user_id']=select.value;
   try{
    const result=await api('/api/platform/decisions/'+caseId+'/responsibilities/'+stageKey,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:scope.signal});
    if(!scope.active||own!==generation)return;
    current=result;render();onSaved?.(result);root.querySelector('button')?.focus({preventScroll:true});
   }catch(exc){
    if(!scope.active||own!==generation)return;
    error.textContent=exc.status===409?'La responsabilidad cambió o la persona ya no es elegible. Actualizá la etapa antes de guardar.':exc.message;
    if(exc.status===409)error.append(button('Actualizar etapa',async()=>{
     try{const result=await api('/api/platform/decisions/'+caseId+'/responsibilities',{signal:scope.signal});if(scope.active&&own===generation){current=result;render();onSaved?.(result);}}
     catch(failure){if(scope.active)error.textContent=failure.message;}
    }));
    else save.disabled=false;
   }finally{saving=false;cancel.disabled=false;save.removeAttribute('aria-busy');}
  }
  input.focus();load();
 }
 scope.own(()=>{generation++;controller?.abort();});render();return scope;
}
