import {api} from '../shared.mjs';
import {createScope} from '../lifecycle.mjs';
import {ensureStylesheet} from '../styles.mjs';

const TYPES={
 data_preparation:{group:'data_owner',label:'Data Owner',role:'Data Owner'},
 data_owner:{group:'data_owner',label:'Data Owner',role:'Data Owner'},
 owner:{group:'decision_owner',label:'Decision Owner',role:'Decision Owner'},
};
export function executionPermission(identity=globalThis.window?.dationSession?.identity){
 return identity?.membership?.access_role==='viewer'?'Tu rol permite consultar, pero no ejecutar decisiones.':null;
}
export function responsibilityProblem(snapshot,stageKey,kind='execute'){
 if(!snapshot?.gates_enforced)return null;
 const stages=snapshot.stages||{},data=stages.data_owner;
 if(kind!=='approve'&&!data?.owner_eligible)return 'Asigná un Data Owner activo y elegible antes de continuar.';
 if(kind==='data')return null;
 const stage=stages[stageKey];
 if(!stage?.owner_eligible)return 'Asigná un Decision Owner activo y elegible antes de continuar.';
 if(kind!=='configure'&&stage?.[kind==='approve'?'can_approve':'can_execute']===false)return 'Esta acción requiere al Decision Owner o a un Admin.';
 return null;
}
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function button(text,handler){const b=el('button',text,'d-button d-button--secondary');b.type='button';b.addEventListener('click',handler);return b;}
let sequence=0;

/** Shared, bounded Team select; assignment authority remains in SQL. */
export function mountResponsibilitySelector(root,{caseId,stageKey,field='owner',snapshot,onSaved,onPrepare,onCancel,canSave=()=>true,draft={},deferSave=false,onChanged}){
 ensureStylesheet('workflow-context-styles','/static/css/workflow-context.css','optimized-responsibilities').catch(()=>{});
 const scope=createScope(root),id='responsibility-'+(++sequence),type=TYPES[stageKey]||TYPES[field];
 let current=snapshot,controller,generation=0;
 root.className='workflow-responsibility'+(deferSave?' workflow-responsibility--inline':'');root.id=id;root.dataset.workflowResponsibility=stageKey;
 root.dataset.responsibilityField=field;
 function render(){
  controller?.abort();generation++;
  const stage=current?.stages?.[stageKey]||{},person=stage[field],eligible=stage[field+'_eligible'];
  if(deferSave&&current?.can_assign){root.replaceChildren();edit(false);return;}
  const info=el('div'),heading=el('h2',type.label,'d-card-title');info.append(heading,el('p',person?.name||'Sin asignar','d-body'));
  info.append(el('p',person&&!eligible?'Esta persona ya no cumple los requisitos. Un administrador debe reasignarla.':type.role,'d-metadata'));root.replaceChildren(info);
  if(current?.can_assign){root.append(button(person?'Cambiar':'Seleccionar responsable',()=>edit()));if(draft.open)edit(false);}
  else{
   if(!person)root.append(el('p','Un administrador debe asignar esta responsabilidad desde Datos, el Mapa o Decision Center.','d-metadata'));
   if(!deferSave&&onPrepare&&current?.can_prepare!==false){const refresh=button(current?.pending?'Registrar caso para asignar responsable':'Actualizar responsabilidad',async()=>{
    refresh.disabled=true;try{const result=await onPrepare();if(scope.active){current=result;render();onSaved?.(result);}}
    catch(error){if(scope.active){const note=el('p',error.message);note.role='alert';root.append(note);refresh.disabled=false;}}
   });refresh.disabled=!canSave();root.append(refresh);}
  }
 }
 function edit(focus=true){
  if(!draft.open)draft.version=current?.stages?.[stageKey]?.updated_at||null;
  draft.open=true;
  controller?.abort();controller=new AbortController();const own=++generation,signal=controller.signal;
  let saving=false,loaded=false,candidates=[];const initial=current?.stages?.[stageKey]?.[field]?.id||'',editVersion=draft.version;
  const panel=el('div',undefined,'workflow-responsibility__editor'),label=el('label',type.label,'d-label'),select=el('select',undefined,'d-input d-responsibility-select');select.id=id+'-choice';label.htmlFor=select.id;
  const message=el('p','Cargando personas del Equipo…','d-metadata'),error=el('p');message.id=id+'-status';message.role='status';error.role='alert';select.setAttribute('aria-describedby',message.id);
  const actions=el('div',undefined,'workflow-context-actions workflow-responsibility__actions'),save=button('Guardar',commit),cancel=button('Cancelar',()=>{if(!saving){draft.open=false;delete draft.value;if(onCancel)onCancel();else{render();root.querySelector('button')?.focus();}}});save.classList.replace('d-button--secondary','d-button--primary');save.disabled=true;actions.append(cancel,save);panel.append(label,select,message,error);if(!deferSave)panel.append(actions);root.append(panel);const trigger=root.querySelector('button');if(trigger)trigger.hidden=true;
  function ready(){save.disabled=!loaded||saving||!canSave()||select.value===initial;}
  function selection(){draft.value=select.value;if(deferSave){const person=candidates.find(p=>p.user_id===select.value);draft.owner=person?{...person,id:person.user_id}:null;draft.ownerEligible=Boolean(person);draft.dirty=select.value!==initial;onChanged?.();}ready();}
  select.addEventListener('change',selection);
  async function load(){
   loaded=false;select.disabled=true;save.disabled=true;error.replaceChildren();
   try{
    const people=[];let total=0,offset=0;
    do{
     const result=await api('/api/platform/team?'+new URLSearchParams({candidates:'true',responsibility:type.group,limit:50,offset}),{signal});
     if(!scope.active||own!==generation)return;
     if(!Number.isSafeInteger(result.total)||result.total<0||result.total>1000000)throw new Error('La lista del Equipo no es válida.');
     total=result.total;const members=result.members||[];people.push(...members);offset+=50;
     if(!members.length&&offset<total)throw new Error('La lista del Equipo cambió. Volvé a abrir el selector.');
    }while(offset<total);
    select.replaceChildren();const empty=el('option','Sin asignar');empty.value='';select.append(empty);
    for(const person of people){const option=el('option',person.name+' · '+person.email);option.value=person.user_id;select.append(option);}
    if(initial&&!people.some(p=>p.user_id===initial)){const previous=el('option',(current.stages[stageKey][field].name||'Asignación anterior')+' (no elegible)');previous.value=initial;previous.disabled=true;select.append(previous);}
    select.value=draft.value??initial;candidates=people;loaded=true;select.disabled=false;if(deferSave)selection();else ready();
    message.textContent=deferSave?(people.length?'Se guarda junto con los atributos al aplicar.':'No hay personas elegibles. Revisá las responsabilidades en Equipo.'):!canSave()?'Cargá y validá Órdenes y Flota antes de guardar esta asignación.':people.length?'Personas activas del Equipo con responsabilidad '+type.role+'.':'No hay personas elegibles. Revisá las responsabilidades en Equipo.';
    if(focus||draft.restoreFocus)select.focus();draft.restoreFocus=false;
   }catch(exc){if(scope.active&&own===generation&&!signal.aborted){message.textContent='';error.append(document.createTextNode(exc.message),button('Reintentar',load));}}
  }
  async function commit(){
   if(saving||!loaded||!canSave()||!scope.active)return;
   const selected=select.value;saving=true;save.disabled=cancel.disabled=select.disabled=true;save.setAttribute('aria-busy','true');error.replaceChildren();
   try{
    if(onPrepare){const prepared=await onPrepare();if(!scope.active||own!==generation)return;current=prepared;}
    const stage=current.stages?.[stageKey]||{},payload={expected_updated_at:editVersion,owner_user_id:stage.owner?.id||null};payload[field+'_user_id']=selected||null;
    const result=await api('/api/platform/decisions/'+(current.case_id||caseId)+'/responsibilities/'+stageKey,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal});
    if(!scope.active||own!==generation)return;draft.open=false;delete draft.value;current=result;render();onSaved?.(result);root.querySelector('button')?.focus({preventScroll:true});
   }catch(exc){
    if(!scope.active||own!==generation)return;
    error.textContent=exc.status===409?'La responsabilidad cambió. Actualizá antes de volver a guardar.':exc.message;
    if(exc.status===409)error.append(button('Actualizar etapa',async()=>{
     try{const result=await api('/api/platform/decisions/'+(current.case_id||caseId)+'/responsibilities',{signal});if(scope.active&&own===generation){draft.open=false;delete draft.value;current=result;render();onSaved?.(result);}}
     catch(failure){if(scope.active)error.textContent=failure.message;}
    }));
   }finally{saving=false;if(scope.active&&own===generation){cancel.disabled=select.disabled=false;ready();save.removeAttribute('aria-busy');}}
  }
  load();
 }
 scope.own(()=>{generation++;controller?.abort();});render();return scope;
}
