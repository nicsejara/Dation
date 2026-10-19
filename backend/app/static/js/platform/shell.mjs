import {mountDropdown} from './components.mjs';
import {createScope} from '../dispatch/lifecycle.mjs';
import {PLATFORM_PATHS,readResource} from '../dispatch/navigation.mjs';
import {mountWorkspaceHome} from './home.mjs';
import {ddaEnabled} from './entitlements.mjs';
import {mountDataHub} from './data-hub.mjs';
import {mountDecisionCenter} from './decision-center.mjs';
import {mountTeam} from './team.mjs';

const labels={'platform-home':'Inicio',inicio:'Decision Data Assets','platform-decisions':'Decision Center','platform-data':'Data Hub','platform-team':'Equipo',settings:'Configuración',profile:'Mi perfil'};
const roles={admin:'Administrador',operator:'Operador',viewer:'Solo lectura'};
function node(tag,text,className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;}
function action(text,view){const a=node('a',text,'d-button d-button--secondary');a.href=PLATFORM_PATHS[view]||'/app/history';a.dataset.platformView=view;return a;}
function card(title,copy,links=[]){const el=node('article',undefined,'d-card');el.append(node('h2',title,'d-card-title'),node('p',copy,'d-body'));const actions=node('div',undefined,'platform-actions');for(const [text,view]of links)actions.append(action(text,view));el.append(actions);return el;}

export function mountPlatformShell(){
 const scope=createScope(document.querySelector('.sidebar'));
 let identity=window.dationSession.identity;
 const profile=()=>identity.profile;
 const display=()=>profile().display_name||[profile().first_name,profile().last_name].filter(Boolean).join(' ')||'Mi cuenta';
 const name=document.querySelector('[data-user-name]'),workspaceName=document.querySelector('[data-workspace-name]'),avatar=document.querySelector('[data-user-avatar]');
 function renderIdentity(){name.textContent=display();workspaceName.textContent=identity.workspace.name;avatar.textContent=(profile().first_name?.[0]||display()[0]||'D')+(profile().last_name?.[0]||'');}
 renderIdentity();
 const menu=mountDropdown({trigger:document.querySelector('[data-user-menu]'),panel:document.querySelector('[data-user-menu-panel]')});scope.own(()=>menu.dispose());
 const logout=document.querySelector('[data-logout]');
 scope.listen(logout,'click',async()=>{logout.disabled=true;try{await window.dationSession.logout();}catch(error){document.querySelector('[data-account-status]').textContent=error.message;logout.disabled=false;}});
 scope.listen(document,'click',event=>{
  const link=event.target.closest('[data-platform-view]');
  if(!link||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
  event.preventDefault();menu.close({restoreFocus:false});window.dationNavigate(link.dataset.platformView);
 });
 const home=mountWorkspaceHome(document.querySelector('[data-platform-home]'),()=>identity);scope.own(()=>home.dispose());
 function renderAccess(){
  const access=document.querySelector('#profile-access_role'),business=document.querySelector('#profile-business_role');
  if(access)access.value=roles[identity.membership.access_role];if(business)business.value=identity.membership.business_role||'Sin asignar';
  document.querySelector('[data-platform-diagnostics]').hidden=identity.membership.access_role!=='admin';
 }
 scope.listen(window,'dation:identity',()=>{identity={...window.dationSession.identity,profile:identity.profile};renderIdentity();renderAccess();});
 const center=mountDecisionCenter(document.querySelector('[data-platform-decisions]'),()=>window.dationSession.identity);scope.own(()=>center.dispose());
 const dataHub=mountDataHub(document.querySelector('[data-platform-data]'),()=>window.dationSession.identity);scope.own(()=>dataHub.dispose());
 const team=mountTeam(document.querySelector('[data-platform-team]'),()=>window.dationSession.identity);scope.own(()=>team.dispose());
 const settings=document.querySelector('[data-workspace-settings]');
 for(const [title,values]of [['Workspace',[['Nombre',identity.workspace.name],['País',identity.workspace.country],['Zona horaria',identity.workspace.timezone]]],['Preferencias',[['Idioma',identity.workspace.language],['Moneda',identity.workspace.currency],['Unidades',[identity.workspace.weight_unit,identity.workspace.distance_unit].filter(Boolean).join(' · ')]]],['Mi acceso',[['Rol',roles[identity.membership.access_role]],['Responsabilidad',identity.membership.business_role||'Sin asignar'],['Workspace','Activo']]]]){
  const item=node('article',undefined,'d-card');item.append(node('h2',title,'d-card-title'));
  for(const [label,value]of values){const row=node('div',undefined,'settings-row d-metadata');row.append(node('span',label),node('strong',value||'—'));item.append(row);}settings.append(item);
 }
 const diagnostics=document.querySelector('[data-platform-diagnostics]');diagnostics.hidden=identity.membership.access_role!=='admin';
 const profileRoot=document.querySelector('[data-profile-form]');const form=node('form');form.className='platform-profile-form';
 for(const [key,label,value,readonly]of [['first_name','Nombre',profile().first_name,false],['last_name','Apellido',profile().last_name,false],['email','Email',profile().email,true],['access_role','Rol de acceso',roles[identity.membership.access_role],true],['business_role','Responsabilidad',identity.membership.business_role||'Sin asignar',true]]){
  const field=node('div',undefined,'d-field');const title=node('label',label,'d-label');title.htmlFor='profile-'+key;
  const input=node('input');Object.assign(input,{id:title.htmlFor,name:key,value:value||'',readOnly:readonly,required:!readonly,maxLength:key==='email'?254:100});input.className='d-input';if(key==='email')input.type='email';
  field.append(title,input);form.append(field);
 }
 const message=node('p');message.role='status';message.setAttribute('aria-live','polite');
 const save=node('button','Guardar perfil','d-button d-button--primary');save.type='submit';form.append(message,save);profileRoot.append(form);
 scope.listen(form,'submit',async event=>{
  event.preventDefault();save.disabled=true;save.setAttribute('aria-busy','true');message.textContent='';
  try{
   const response=await fetch('/api/platform/profile',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({first_name:form.elements.first_name.value,last_name:form.elements.last_name.value})});
   const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'No se pudo guardar el perfil.');
   identity={...identity,profile:{...identity.profile,...data}};renderIdentity();message.textContent='Perfil actualizado.';
  }catch(error){message.textContent=error.message;}finally{save.disabled=false;save.removeAttribute('aria-busy');}
 });
 function updateNavigation(){
  const view=window.dationGetCurrentView?.();
  for(const link of document.querySelectorAll('.nav [data-platform-view]')){
   const active=link.dataset.platformView===view;link.classList.toggle('is-active',active);if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
  }
  const breadcrumb=document.querySelector('[data-platform-breadcrumb]');breadcrumb.replaceChildren();
  const ddaView=view?.startsWith('logistics-')||view==='decision-dashboard';
  breadcrumb.hidden=!ddaView;
  if(!ddaView){const title=node('span',labels[view]||(view==='traceability'?'Historial y evidencia':'Dation'),'journey-step journey-step--title is-current');document.querySelector('#journey-nav').replaceChildren(title);}
  if(ddaView){
   breadcrumb.append(action('Decision Data Assets','inicio'),node('span','/'),action('DDA Logística','logistics-overview'));
   try{const route=readResource(location.href);if(route.caseId)breadcrumb.append(node('span','/'),node('span','DC-'+route.caseId.slice(0,8)));if(route.nodeId)breadcrumb.append(node('span','/'),node('span',route.nodeId==='logistics_scheduling'?'Scheduling':'Assignment'));}catch{}
  }else{breadcrumb.append(node('span',labels[view]||(view==='traceability'?'Historial y evidencia':'Dation')));}
 }
 scope.listen(window,'dation:view',updateNavigation);updateNavigation();
 scope.listen(window,'pagehide',event=>{if(!event.persisted)scope.dispose();});
 return {dispose:()=>scope.dispose()};
}
