import {loadingState} from './components.mjs';
import {api} from '../dispatch/shared.mjs';
import {createScope} from '../dispatch/lifecycle.mjs';
import {SETTINGS_TABS,readSettingsTab} from './settings-resource.mjs';
import {workspaceDate,workspaceNumber,workspaceLocale} from './workspace-format.mjs';
import {DDA_CATALOG} from './dda-catalog.mjs';

const BASE='/api/platform/settings';
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function button(text,fn,kind='secondary'){const b=el('button',text,'d-button d-button--'+kind);b.type='button';b.addEventListener('click',fn);return b;}
function card(title){const c=el('section',undefined,'d-card workspace-settings__card');c.append(el('h2',title,'d-card-title'));return c;}
function pair(label,value){const row=el('div',undefined,'settings-row d-metadata');row.append(el('dt',label),el('dd',value));return row;}
function select(name,label,values,value){const field=el('div',undefined,'d-field'),title=el('label',label,'d-label'),input=el('select',undefined,'d-input');input.id='workspace-'+name;input.name=name;title.htmlFor=input.id;for(const [key,text]of Object.entries(values)){const option=el('option',text);option.value=key;input.append(option);}if(!Object.hasOwn(values,value)){const current=el('option',value);current.value=value;input.append(current);}input.value=value;field.append(title,input);return field;}

export function mountWorkspaceSettings(root,getIdentity){
 const scope=createScope(root);root.classList.remove('settings-grid');root.classList.add('workspace-settings');let controller,generation=0,notice='',access=getIdentity().membership.access_role;
 const admin=()=>getIdentity().membership.access_role==='admin';
 function open(tab){window.DationDispatch.openWorkspaceSettings(tab);}
 function form(data,section){
  const workspace=data.workspace,c=card(section==='general'?'Datos del workspace':'Preferencias de operación'),form=el('form',undefined,'workspace-settings__form'),grid=el('div',undefined,'workspace-settings__fields');
  if(section==='general'){
   const field=el('div',undefined,'d-field'),label=el('label','Nombre del workspace','d-label'),input=el('input',undefined,'d-input');input.id='workspace-name';input.name='name';input.required=true;input.minLength=2;input.maxLength=120;input.value=workspace.name;label.htmlFor=input.id;field.append(label,input);grid.append(field);
   const display=new Intl.DisplayNames([workspaceLocale(workspace)],{type:'region'}),countries=Object.fromEntries(data.options.countries.map(code=>[code,display.of(code)]));
   grid.append(select('country','País',countries,workspace.country),select('language','Idioma de formatos',data.options.languages,workspace.language));
   const zones=Object.fromEntries(data.options.timezones.filter(zone=>{try{new Intl.DateTimeFormat('es',{timeZone:zone});return true;}catch{return false;}}).map(zone=>[zone,zone.replaceAll('_',' ')]));
   grid.append(select('timezone','Zona horaria',zones,workspace.timezone));
   c.append(el('p','El idioma se aplica a las fechas y los números del workspace. La interfaz conserva sus textos actuales.','d-body'));
  }else{
   for(const [name,label,key]of [['currency','Moneda','currencies'],['weight_unit','Unidad de peso','weight_units'],['distance_unit','Unidad de distancia','distance_units'],['logistics_unit','Unidad logística','logistics_units']])grid.append(select(name,label,data.options[key],workspace[name]));
   c.append(el('p','Estas preferencias no convierten los datos cargados ni los costos y resultados existentes.','d-body'));
  }
  const preview=el('section',undefined,'workspace-settings__preview');preview.setAttribute('aria-label','Vista previa de formato');const previewTitle=el('h3','Vista previa de formato','d-card-title'),sample=el('p',undefined,'d-metadata');preview.append(previewTitle,sample);
  function showPreview(){const values={...workspace,...Object.fromEntries(new FormData(form))};sample.textContent=section==='general'?workspaceDate('2026-01-15T15:30:00Z',values):new Intl.NumberFormat(workspaceLocale(values),{style:'currency',currency:values.currency}).format(1234.5)+' · '+workspaceNumber(1234.5,values)+' '+values.weight_unit+' · '+workspaceNumber(100,values)+' '+values.distance_unit;}
  const message=el('p');message.role='alert';const actions=el('div',undefined,'workspace-settings__actions'),save=el('button',section==='general'?'Guardar datos generales':'Guardar preferencias','d-button d-button--primary');save.type='submit';
  if(admin())actions.append(save);else c.append(el('p','Tu rol permite consultar esta configuración. Un Admin puede modificarla.','d-body'));
  form.append(grid,preview,message,actions);c.append(form);if(!admin())for(const field of grid.querySelectorAll('input,select'))field.disabled=true;
  form.addEventListener('input',showPreview);form.addEventListener('change',showPreview);showPreview();
  form.addEventListener('submit',async event=>{event.preventDefault();if(!admin()||!form.reportValidity())return;const version=generation;save.disabled=true;save.setAttribute('aria-busy','true');message.textContent='';
   try{await api(BASE,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({section,expected_updated_at:workspace.updated_at,...Object.fromEntries(new FormData(form))})});if(version!==generation)return;notice='Configuración guardada.';await window.dationSession.refresh();if(version===generation)load();}
   catch(error){if(version!==generation)return;message.textContent=error.status===409?'La configuración cambió. Actualizá antes de guardar nuevamente; tus cambios todavía no se aplicaron.':error.message;save.disabled=error.status===409;save.removeAttribute('aria-busy');if(error.status===409)actions.append(button('Actualizar configuración',load));}
  });return c;
 }
 function ddaRows(data){return DDA_CATALOG.map(item=>{const grant=data.ddas.find(row=>row.dda_id===(item.entitlementId||item.id));return {title:item.title,status:item.id!=='logistics'?'Próximamente':grant?.status==='enabled'?'Habilitado':'No habilitado',enabled:item.id==='logistics'&&grant?.status==='enabled'};});}
 function ddas(data){const c=card('Decision Data Assets');c.append(el('p','Disponibilidad actual para tu workspace. El plan Free no activa capacidades que todavía están en desarrollo.','d-body'));const list=el('dl',undefined,'workspace-settings__rows');for(const item of ddaRows(data))list.append(pair(item.title,item.status));c.append(list);return c;}
 function plan(data){const c=card('Plan Free'),badge=el('span','Gratis','workspace-settings__badge');c.append(badge,el('p','Todos los usuarios utilizan el plan Free durante esta etapa del MVP. No hay cobros ni se requiere un medio de pago.','d-body'));
  const rows=el('dl',undefined,'workspace-settings__rows');for(const [label,value]of [['Plan',data.plan.name],['Estado','Activo'],['Costo','Gratis'],['Miembros activos',workspaceNumber(data.members.active,data.workspace)],['DDAs habilitados',ddaRows(data).filter(item=>item.enabled).map(item=>item.title).join(', ')||'Ninguno habilitado']])rows.append(pair(label,value));c.append(rows);return c;
 }
 async function load(){
  controller?.abort();controller=new AbortController();const version=++generation,restoreFocus=root.contains(document.activeElement)&&document.activeElement?.getAttribute('role')==='tab';root.setAttribute('aria-busy','true');root.replaceChildren(loadingState('Cargando configuración…'));
  try{const tab=readSettingsTab(location.href),data=await api(BASE,{signal:controller.signal});if(version!==generation||controller.signal.aborted)return;
   const fragment=document.createDocumentFragment();if(notice){const message=el('p',notice,'workspace-settings__notice');message.role='status';fragment.append(message);notice='';}
   const tabs=el('div',undefined,'workspace-settings__tabs');tabs.role='tablist';tabs.setAttribute('aria-label','Configuración del workspace');
   for(const [id,label]of Object.entries(SETTINGS_TABS)){const b=button(label,()=>{if(id!==tab)open(id);});b.id='settings-tab-'+id;b.role='tab';b.setAttribute('aria-selected',String(id===tab));b.setAttribute('aria-controls','settings-panel-'+id);b.tabIndex=id===tab?0:-1;tabs.append(b);}
   tabs.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const items=[...tabs.children],index=items.indexOf(document.activeElement),next=event.key==='Home'?0:event.key==='End'?items.length-1:(index+(event.key==='ArrowRight'?1:-1)+items.length)%items.length;items.forEach((item,i)=>item.tabIndex=i===next?0:-1);items[next].focus();});fragment.append(tabs);
   for(const id of Object.keys(SETTINGS_TABS)){const panel=el('section');panel.id='settings-panel-'+id;panel.role='tabpanel';panel.setAttribute('aria-labelledby','settings-tab-'+id);panel.hidden=id!==tab;if(id===tab)panel.append(id==='general'||id==='operation'?form(data,id):id==='ddas'?ddas(data):plan(data));fragment.append(panel);}
   root.replaceChildren(fragment);if(restoreFocus)root.querySelector('[aria-selected=true]')?.focus();
  }catch(error){if(version!==generation||controller.signal.aborted)return;const message=el('p',error.message,'d-body');message.role='alert';root.replaceChildren(message,button('Reintentar',load),button('Abrir General',()=>open('general')));}
  finally{if(version===generation)root.removeAttribute('aria-busy');}
 }
 function stop(){generation++;controller?.abort();root.removeAttribute('aria-busy');}
 function onView(){if(window.dationGetCurrentView?.()==='settings')load();else stop();}
 scope.listen(window,'dation:view',onView);scope.listen(window,'dation:identity',()=>{const role=getIdentity().membership.access_role;if(role!==access){access=role;onView();}});scope.listen(window,'pagehide',stop);onView();return {dispose(){stop();scope.dispose();}};
}
