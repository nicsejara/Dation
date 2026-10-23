import {describeFailure} from '../dispatch/recovery.mjs';
import {api} from '../dispatch/shared.mjs';
import {createScope} from '../dispatch/lifecycle.mjs';
import {mountDialog,loadingState} from './components.mjs';
import {ACCESS_ROLES,RESPONSIBILITIES,mountReceivedInvitations} from './invitations.mjs';
import {workspaceDate} from './workspace-format.mjs';

const BASE='/api/platform/team',size=25;
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function button(text,handler,kind='secondary'){const b=el('button',text,'d-button d-button--'+kind);b.type='button';b.addEventListener('click',handler);return b;}
function select(label,name,values,value){const field=el('div',undefined,'d-field'),title=el('label',label,'d-label'),input=el('select',undefined,'d-input');input.id='team-'+name;input.name=name;title.htmlFor=input.id;for(const [value,text]of Object.entries(values)){const option=el('option',text);option.value=value;input.append(option);}input.value=value||'';field.append(title,input);return field;}

export function mountTeam(root,getIdentity){
 const scope=createScope(root);root.classList.add('platform-team');let controller,generation=0,offset=0,query='',notice='',modal,received;
 const admin=()=>getIdentity().membership.access_role==='admin';
 const stamp=value=>workspaceDate(value,getIdentity().workspace,{dateStyle:'medium'});
 function close(){if(!modal)return;const own=modal;modal=null;own.view.dispose();own.dialog.remove();}
 function edit(title,content,saveAction){
  close();const dialog=el('dialog',undefined,'d-platform team-dialog'),form=el('form'),heading=el('h2',title,'d-card-title');heading.id='team-dialog-title';dialog.setAttribute('aria-labelledby',heading.id);
  const message=el('p');message.role='alert';const actions=el('div',undefined,'team-actions'),save=el('button','Guardar','d-button d-button--primary');save.type='submit';actions.append(button('Cancelar',()=>close()),save);form.append(heading,...content,message,actions);dialog.append(form);root.append(dialog);
  const view=mountDialog({dialog}),own={dialog,view};modal=own;dialog.addEventListener('close',()=>{if(modal===own)close();});
  form.addEventListener('submit',async event=>{event.preventDefault();if(!form.reportValidity())return;save.disabled=true;save.setAttribute('aria-busy','true');message.textContent='';
   try{const result=await saveAction(Object.fromEntries(new FormData(form)));if(modal!==own)return;close();notice=result||'Equipo actualizado.';await window.dationSession.refresh();if(scope.active&&window.dationGetCurrentView?.()==='platform-team')load();}
   catch(error){if(modal!==own)return;message.textContent=error.message;save.disabled=error.status===409;save.removeAttribute('aria-busy');if(error.status===409)actions.append(button('Actualizar equipo',()=>{close();load();}));}
  });view.open();form.querySelector('input,select,button')?.focus();
 }
 function invite(){const field=el('div',undefined,'d-field'),label=el('label','Email','d-label'),input=el('input',undefined,'d-input');input.id='team-email';input.name='email';input.type='email';input.required=true;input.maxLength=254;label.htmlFor=input.id;field.append(label,input);
  edit('Invitar al equipo',[field,select('Rol de acceso','access_role',ACCESS_ROLES,'operator'),select('Responsabilidad de negocio','business_role',{'':'Sin asignar',...RESPONSIBILITIES},''),el('p','La persona verá la invitación al registrarse con este email y confirmarlo. Compartile el enlace de acceso; esta acción no envía un correo. La invitación vence en 7 días.','d-body')],async values=>{await api(BASE+'/invitations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...values,business_role:values.business_role||null})});return 'Invitación creada. Compartí el enlace de acceso con la persona.';});
  modal.dialog.querySelector('button[type=submit]').textContent='Invitar';
  const access=el('a','Enlace para crear la cuenta','team-link');access.href='/register';access.target='_blank';access.rel='noopener';modal.dialog.querySelector('form').append(access);
 }
 function member(row){
  const roles=el('fieldset',undefined,'team-responsibilities');roles.append(el('legend','Responsabilidades de negocio','d-label'));
  for(const [role,label]of Object.entries(RESPONSIBILITIES)){const item=el('label'),input=el('input');input.type='checkbox';input.name='responsibility_'+role;input.checked=(row.business_roles||[row.business_role]).includes(role);item.append(input,document.createTextNode(label));roles.append(item);}
  edit('Editar acceso de '+row.name,[select('Rol de acceso','access_role',ACCESS_ROLES,row.access_role),roles,select('Estado','status',{active:'Activo',disabled:'Deshabilitado'},row.status),el('p','Una persona puede reunir varias responsabilidades. Los permisos dependen del rol de acceso. Un administrador puede reasignar personas que hayan perdido su elegibilidad.','d-body')],async values=>{
   const business_roles=Object.keys(RESPONSIBILITIES).filter(role=>values['responsibility_'+role]);
   await api(BASE+'/members/'+row.user_id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({access_role:values.access_role,status:values.status,business_roles,expected_updated_at:row.updated_at})});
  });
 }
 function revoke(row){edit('Revocar invitación',[el('p','Se revocará la invitación de '+row.email+'.','d-body')],async()=>{await api(BASE+'/invitations/'+row.id+'/revoke',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_updated_at:row.updated_at})});return 'Invitación revocada.';});}
 function render(data){
  const frag=document.createDocumentFragment(),header=el('div',undefined,'team-actions');header.append(el('p','Personas, acceso y responsabilidades de '+getIdentity().workspace.name+'.','d-body'));if(admin())header.append(button('Invitar',invite,'primary'));frag.append(header);
  const info=el('p','Admin administra el equipo y las asignaciones. Operator trabaja y aprueba según la asignación. Viewer consulta. Las responsabilidades de negocio no otorgan permisos adicionales.','d-metadata');frag.append(info);

  if(admin()&&!query&&data.total===1&&!data.invitation_total){const empty=el('section',undefined,'d-card');empty.dataset.teamEmpty='';empty.append(el('h2','Tu equipo empieza con vos','d-card-title'),el('p','Invitá a otra persona para preparar datos, operar decisiones o consultar resultados. Elegí su rol según el acceso que necesite.','d-body'));frag.append(empty);}
  const search=el('form',undefined,'team-search'),label=el('label','Buscar miembro o invitación','d-label'),input=el('input',undefined,'d-input');input.id='team-search';input.type='search';input.maxLength=120;input.value=query;label.htmlFor=input.id;const submit=el('button','Buscar','d-button d-button--secondary');submit.type='submit';search.append(label,input,submit);search.addEventListener('submit',event=>{event.preventDefault();query=input.value.trim();offset=0;load();});frag.append(search);
  const wrap=el('div',undefined,'team-table-scroll');wrap.tabIndex=0;wrap.role='region';wrap.setAttribute('aria-label','Miembros del equipo');const table=el('table',undefined,'team-table'),thead=el('thead'),tr=el('tr'),body=el('tbody');for(const title of ['Miembro','Rol de acceso','Responsabilidad','Estado','Acciones']){const th=el('th',title);th.scope='col';tr.append(th);}thead.append(tr);const caption=el('caption','Acceso y responsabilidades · desplazá la tabla para ver todas las columnas');table.append(caption,thead,body);wrap.append(table);
  function row(item,invitation=false){const r=el('tr'),name=el('td'),strong=el('strong',invitation?item.email:item.name);name.append(strong);if(!invitation)name.append(el('span',item.email,'d-metadata'));r.append(name,el('td',ACCESS_ROLES[item.access_role]),el('td',(item.business_roles||[item.business_role]).map(role=>RESPONSIBILITIES[role]).filter(Boolean).join(' · ')||'Sin asignar'),el('td',invitation?(item.status==='expired'?'Invitación vencida':'Invitación pendiente · vence '+stamp(item.expires_at)):({active:'Activo',disabled:'Deshabilitado',invited:'Invitado'}[item.status]||item.status)));const actions=el('td');if(admin())actions.append(button(invitation?'Revocar':'Editar acceso',()=>invitation?revoke(item):member(item)));else actions.textContent='Solo consulta';r.append(actions);body.append(r);}
  data.members.forEach(item=>row(item));data.invitations.forEach(item=>row(item,true));if(data.members.length||data.invitations.length)frag.append(wrap);else frag.append(el('p','No encontramos personas con esa búsqueda.','d-body'));
  const total=Math.max(data.total,data.invitation_total),pager=el('nav',undefined,'team-actions');pager.setAttribute('aria-label','Paginación del equipo');const prev=button('Anterior',()=>{offset=Math.max(0,offset-size);load();}),next=button('Siguiente',()=>{offset+=size;load();});prev.disabled=!offset;next.disabled=offset+size>=total;pager.append(prev,el('span',`${data.total} miembros · ${data.invitation_total} invitaciones pendientes`,'d-metadata'),next);frag.append(pager);
  const incoming=el('section',undefined,'d-card team-incoming');incoming.hidden=true;frag.append(incoming);return {frag,incoming};
 }
 async function load(){
  controller?.abort();received?.dispose();controller=new AbortController();close();const version=++generation;root.setAttribute('aria-busy','true');root.replaceChildren(loadingState('Cargando equipo…'));
  try{const data=await api(BASE+'?'+new URLSearchParams({q:query,limit:size,offset}),{signal:controller.signal});if(version!==generation||controller.signal.aborted)return;const {frag,incoming}=render(data);if(notice){const message=el('p',notice,'team-notice');message.role='status';frag.prepend(message);notice='';}root.replaceChildren(frag);received=mountReceivedInvitations(incoming);}
  catch(error){if(version===generation&&!controller.signal.aborted){const message=el('p',describeFailure(error).message,'d-body');message.role='alert';root.replaceChildren(message,button('Reintentar',load));}}
  finally{if(version===generation)root.removeAttribute('aria-busy');}
 }
 function stop(){generation++;controller?.abort();received?.dispose();close();root.removeAttribute('aria-busy');}
 function onView(){if(window.dationGetCurrentView?.()==='platform-team')load();else stop();}
 scope.listen(window,'dation:view',onView);scope.listen(window,'dation:identity',onView);scope.listen(window,'pagehide',stop);onView();return {dispose(){stop();scope.dispose();}};
}
