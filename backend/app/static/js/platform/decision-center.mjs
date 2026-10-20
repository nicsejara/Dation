import {objectivePresentation,caseContext} from './foundation.mjs';
import {describeFailure} from '../dispatch/recovery.mjs';
import {demoBadge} from './onboarding.mjs';
import {api} from '../dispatch/shared.mjs';
import {createScope} from '../dispatch/lifecycle.mjs';
import {resourceUrl} from '../dispatch/navigation.mjs';
import {DECISION_META} from '../dispatch/decision-ui.mjs';
import {mountDialog} from './components.mjs';
import {ddaEnabled} from './entitlements.mjs';
import {CENTER_FILTERS,readCenterResource} from './center-resource.mjs';
import {mountActivity} from './activity.mjs';
import {workspaceDate} from './workspace-format.mjs';

const BASE='/api/platform/decisions',size=25;
const statusNames={active:'En progreso',completed:'Completado',archived:'Archivado',review:'En revisión',approved:'Aprobado',running:'En ejecución',error:'Requiere revisión',stale:'Requiere actualizar',available:'Disponible',locked:'Bloqueado',needs_data:'Faltan datos',coming_soon:'Próximamente'};
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function button(text,handler,kind='secondary'){const n=el('button',text,'d-button d-button--'+kind);n.type='button';n.addEventListener('click',handler);return n;}
function card(title){const n=el('section',undefined,'d-card center-card');n.append(el('h2',title,'d-card-title'));return n;}
function pill(status){const n=el('span',statusNames[status]||status,'center-status');n.dataset.state=status;return n;}
function person(value,fallback='Sin registro'){return value?.name?value.name+(value.active===false?' (inactivo)':''):fallback;}
function stamp(value,workspace){return workspaceDate(value,workspace);}
function field(label,value){const n=el('div',undefined,'center-field');n.append(el('dt',label),el('dd',value??'—'));return n;}
function table(headers){const wrap=el('div',undefined,'center-table-scroll');wrap.tabIndex=0;wrap.role='region';wrap.setAttribute('aria-label','Tabla de '+headers[0]);const t=el('table',undefined,'center-table'),head=el('thead'),r=el('tr'),body=el('tbody');for(const title of headers){const h=el('th',title);h.scope='col';r.append(h);}head.append(r);t.append(head,body);wrap.append(t);return {wrap,body};}
function cell(row,value){const n=el('td');n.append(typeof value==='string'?document.createTextNode(value):value);row.append(n);}

export function mountDecisionCenter(root,getIdentity){
 let activityView=null;
 const scope=createScope(root);root.classList.add('decision-center');let controller,generation=0,route={},notice='',modal,access='';
 const writable=()=>getIdentity().membership.access_role!=='viewer',enabled=()=>ddaEnabled(getIdentity(),'logistics'),zone=()=>getIdentity().workspace;
 function open(value){window.DationDispatch.openDecisionCenter(value);}
 function link(text,value){const a=el('a',text,'center-link');a.href=resourceUrl(location.href,{view:'platform-decisions',center:value});a.addEventListener('click',event=>{if(event.button||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;event.preventDefault();open(value);});return a;}
 function external(text,target,disabled=false){
  const a=el('a',text,'d-button d-button--secondary');
  if(disabled){a.removeAttribute('href');a.setAttribute('role','link');a.setAttribute('aria-disabled','true');a.tabIndex=-1;a.title='Restaurá el caso y verificá que Logística esté habilitada.';return a;}
  a.href=resourceUrl(location.href,target);a.addEventListener('click',event=>{if(event.button||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;event.preventDefault();
   if(target.view==='platform-data')window.DationDispatch.openDataHub(target.hub);
   else if(target.runId)window.DationDispatch.openRun(target.runId,target.nodeId,target.caseId);
   else if(target.caseId)window.DationDispatch.openCase(target.caseId,target.view,target.nodeId);
   else window.dationNavigate(target.view);
  });return a;
 }
 function runtime(text,c,target,continuation=false){return external(text,{view:target.view,caseId:c.id,nodeId:target.node_id,runId:target.run_id},!enabled()||target.view==='logistics-config'&&!writable()||c.status==='archived'&&(continuation||target.view!=='decision-dashboard'));}
 function pager(total,offset,change){const nav=el('nav',undefined,'center-pagination');nav.setAttribute('aria-label','Paginación');const prev=button('Anterior',()=>change(Math.max(0,offset-size))),next=button('Siguiente',()=>change(offset+size));prev.disabled=offset===0;next.disabled=offset+size>=total;nav.append(prev,el('span',total?`${Math.min(offset+1,total)}–${Math.min(offset+size,total)} de ${total}`:'0 resultados','d-metadata'),next);return nav;}
 function close(){if(modal){const own=modal;modal=null;own.controller?.abort();own.view.dispose();own.dialog.remove();}}
 function assign(c,node){
  close();const dialog=el('dialog',undefined,'d-platform center-dialog'),form=el('form'),title=el('h2','Responsables · '+node.label,'d-card-title');title.id='center-assignment-title';dialog.setAttribute('aria-labelledby',title.id);
  const searchLabel=el('label','Buscar personas por nombre o email','d-label'),search=el('input',undefined,'d-input');search.type='search';search.maxLength=120;search.id='center-people-search';searchLabel.htmlFor=search.id;
  const count=el('p',undefined,'d-metadata'),message=el('p');message.role='alert';const inputs={},known=new Map();for(const p of [node.owner,node.approver])if(p)known.set(p.id,p);
  form.append(title,el('p','Sólo Admin puede asignar. El responsable coordina el trabajo; el aprobador asignado limita quién puede aprobar. Admin puede intervenir con auditoría. Sin aprobador asignado, pueden aprobar Admin y Operator.','d-body'),searchLabel,search);
  const lookup=button('Buscar personas',()=>loadPeople());form.append(lookup,count);
  for(const [key,label,value]of [['owner_user_id','Responsable',node.owner],['approver_user_id','Aprobador asignado',node.approver]]){const l=el('label',label,'d-label'),select=el('select',undefined,'d-input');select.id='center-'+key;l.htmlFor=select.id;select.name=key;inputs[key]=select;form.append(l,select);select.dataset.initial=value?.id||'';}
  const actions=el('div',undefined,'center-actions'),save=el('button','Guardar responsables','d-button d-button--primary');save.type='submit';actions.append(button('Cancelar',()=>close()),save);form.append(message,actions);dialog.append(form);root.append(dialog);
  const view=mountDialog({dialog}),controller=new AbortController(),own={dialog,view,controller};modal=own;dialog.addEventListener('close',()=>{if(modal===own)close();});let peopleVersion=0;
  function options(members){for(const select of Object.values(inputs)){const value=select.value||select.dataset.initial||'';delete select.dataset.initial;select.replaceChildren();const none=el('option','Sin asignar');none.value='';select.append(none);const rows=new Map(members.map(p=>[p.user_id,{id:p.user_id,name:p.name,active:p.status==='active'}]));if(value&&known.has(value)&&!rows.has(value))rows.set(value,known.get(value));for(const p of rows.values()){known.set(p.id,p);const option=el('option',person(p));option.value=p.id;select.append(option);}select.value=value;}}
  async function loadPeople(){const version=++peopleVersion;lookup.disabled=true;save.disabled=true;message.textContent='';try{const data=await api('/api/platform/team?'+new URLSearchParams({candidates:'true',q:search.value.trim(),limit:50}),{signal:controller.signal});if(modal!==own||version!==peopleVersion)return;options(data.members);count.textContent=`${data.members.length} de ${data.total} personas disponibles. Si falta alguien, refiná la búsqueda.`;save.disabled=false;}catch(error){if(modal===own&&!controller.signal.aborted)message.textContent=error.message;}finally{if(modal===own&&version===peopleVersion)lookup.disabled=false;}}
  search.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();loadPeople();}});
  form.addEventListener('submit',async event=>{event.preventDefault();save.disabled=true;message.textContent='';try{await api(BASE+'/'+c.id+'/assignments/'+node.id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_updated_at:node.assignment_updated_at,owner_user_id:inputs.owner_user_id.value||null,approver_user_id:inputs.approver_user_id.value||null})});if(modal!==own)return;close();notice='Responsables actualizados.';load();}catch(error){if(modal===own){message.textContent=error.status===409?'La asignación cambió o la persona ya no está disponible. Actualizá el detalle antes de guardar.':error.message;save.disabled=error.status===409;if(error.status===409)actions.append(button('Actualizar detalle',()=>{close();load();}));}}});
  view.open();search.focus();loadPeople();
 }
 function edit(c,archive=false){
  close();const dialog=el('dialog',undefined,'d-platform center-dialog'),title=el('h2',archive?(c.status==='archived'?'Restaurar caso':'Archivar caso'):'Nombre del Decision Case','d-card-title');title.id='center-dialog-title';dialog.setAttribute('aria-labelledby',title.id);
  const form=el('form'),actions=el('div',undefined,'center-actions'),message=el('p');message.role='alert';let input;
  form.append(title);
  if(archive)form.append(el('p',c.status==='archived'?'El caso volverá a estar disponible.':'Se conservarán datos, aprobaciones y corridas. Los trabajos ya aceptados pueden terminar.','d-body'));
  else{const label=el('label','Etiqueta opcional','d-label');input=el('input',undefined,'d-input');input.id='center-case-label';label.htmlFor=input.id;input.value=c.label||'';input.maxLength=120;form.append(label,input,el('p','Dejá el campo vacío para mostrar sólo el ID del caso.','d-metadata'));}
  const cancel=button('Cancelar',()=>view.close()),save=el('button',archive?(c.status==='archived'?'Restaurar':'Archivar'):'Guardar','d-button d-button--primary');save.type='submit';actions.append(cancel,save);form.append(message,actions);dialog.append(form);root.append(dialog);
  const view=mountDialog({dialog});modal={dialog,view};const own=createScope(form);own.listen(dialog,'close',()=>{if(modal?.dialog===dialog){modal=null;view.dispose();dialog.remove();}});
  own.listen(form,'submit',async event=>{event.preventDefault();save.disabled=true;save.setAttribute('aria-busy','true');
   try{await api(BASE+'/'+c.id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_updated_at:c.updated_at,...(archive?{archived:c.status!=='archived'}:{label:input.value.trim()||null})})});if(!own.active)return;close();notice='Caso actualizado.';load();}
   catch(error){if(own.active){message.textContent=error.status===409?'El caso cambió. Actualizá el detalle antes de guardar.':error.message;save.disabled=error.status===409;save.removeAttribute('aria-busy');if(error.status===409)actions.append(button('Actualizar detalle',()=>{close();load();}));}}
  });view.open();(input||save).focus();
 }
 function listing(data){
  const frag=document.createDocumentFragment(),form=el('form',undefined,'center-search');let input,filter,dda;
  for(const [key,label]of [['q','Buscar por ID o etiqueta'],['filter','Estado'],['dda','DDA']]){
   const wrap=el('div',undefined,'d-field'),title=el('label',label,'d-label'),control=el(key==='q'?'input':'select',undefined,'d-input');control.id='center-'+key;title.htmlFor=control.id;
   if(key==='q'){input=control;control.type='search';control.maxLength=120;control.value=route.q;}
   else{const values=key==='filter'?CENTER_FILTERS:{all:'Todos los DDAs',logistics:'DDA Logística'};for(const [value,label]of Object.entries(values)){const option=el('option',label);option.value=value;control.append(option);}control.value=route[key];if(key==='filter')filter=control;else dda=control;}
   wrap.append(title,control);form.append(wrap);
  }
  const submit=el('button','Buscar','d-button d-button--secondary');submit.type='submit';form.append(submit);form.addEventListener('submit',event=>{event.preventDefault();open({filter:filter.value,dda:dda.value,q:input.value.trim()});});
  for(const select of [filter,dda])select.addEventListener('change',()=>open({filter:filter.value,dda:dda.value,q:input.value.trim()}));frag.append(form);
  if(!data.items.length){const empty=card(route.q||route.filter!=='all'?'No encontramos casos':'Tu memoria de decisiones empieza acá');empty.append(el('p',writable()?'Prepará Órdenes y Flota y abrí DDA Logística para crear tu primer caso.':'Los casos que prepare tu equipo aparecerán acá. Podés consultar los datos mientras tanto.','d-body'));if(route.q||route.filter!=='all')empty.append(button('Limpiar filtros',()=>open({})));else{empty.append(external('Ver datos',{view:'platform-data'}));if(enabled())empty.append(external('Abrir DDA Logística',{view:'logistics-overview'}));}frag.append(empty);}
  else{const grid=table(['Decision Case','DDA','Paso actual','Progreso','Responsable','Estado','Última actividad','Acciones']);
   for(const c of data.items){const context=caseContext(c);const row=el('tr'),name=el('div',undefined,'center-name');name.append(link(context.label||(c.is_demo?'Demo · DDA Logística':context.friendlyId),{...route,caseId:c.id,nodeId:null,runsOffset:0}));if(c.is_demo)name.append(demoBadge());if(c.label||c.is_demo)name.append(el('span',c.friendly_id,'d-metadata'));cell(row,name);cell(row,'DDA Logística');cell(row,c.current_step_label);cell(row,`${c.progress.approved}/${c.progress.total} aprobadas`);cell(row,person(c.owner,'Sin asignar'));const status=el('div',undefined,'center-statuses');status.append(pill(c.status));if(c.in_review)status.append(pill('review'));cell(row,status);cell(row,stamp(c.last_activity_at,zone()));cell(row,link('Abrir',{...route,caseId:c.id,nodeId:null,runsOffset:0}));grid.body.append(row);}frag.append(grid.wrap);
  }
  frag.append(pager(data.total,route.offset,offset=>open({...route,offset})));return frag;
 }
 function approval(run,current=true){return !run.approved_at?'Sin aprobar':run.superseded_at?'Reemplazada':!current?'Requiere actualizar':'Aprobada';}
 function history(node,c,version){
  const details=el('details',undefined,'center-history');details.append(el('summary',`Historial de corridas (${node.run_count})`));const body=el('div');details.append(body);
  async function read(){
   body.replaceChildren(el('p','Cargando historial…','d-body'));
   try{const data=await api(BASE+'/'+c.id+'/runs?'+new URLSearchParams({node_id:node.id,limit:size,offset:route.runsOffset}),{signal:controller.signal});if(version!==generation)return;
    if(!data.items.length){body.replaceChildren(el('p','No hay corridas en esta página.','d-body'));return;}
    const grid=table(['Corrida','Creada por','Creación','Estado','Duración','Objetivo','Aprobación']);
    for(const r of data.items){const row=el('tr'),run=el('div',undefined,'center-run');run.append(runtime('RUN-'+r.id.slice(0,8),c,{view:'decision-dashboard',node_id:node.id,run_id:r.id}));
     const technical=el('details');technical.append(el('summary','Datos técnicos'));for(const [label,value]of [['ID',r.id],['Motor',[r.engine_name,r.engine_version].filter(Boolean).join(' ')],['Input fingerprint',r.input_fingerprint],['Result fingerprint',r.result_fingerprint]])technical.append(el('p',label+': '+(value||'Sin registro'),'d-metadata'));run.append(technical);cell(row,run);cell(row,person(r.created_by));cell(row,stamp(r.created_at,zone()));cell(row,{queued:'En cola',running:'En ejecución',completed:'Completada',error:'Error'}[r.status]||'Sin registro');cell(row,r.duration_ms==null?'—':(r.duration_ms/1000).toFixed(1)+' s');cell(row,objectivePresentation(r.objective)?.label||'Sin registro');cell(row,approval(r,r.decision_state!=='stale'));grid.body.append(row);}
    body.replaceChildren(grid.wrap,pager(data.total,route.runsOffset,runsOffset=>open({...route,nodeId:node.id,runsOffset})));
   }catch(error){if(version===generation&&!controller.signal.aborted)body.replaceChildren(el('p',error.message,'d-body'),button('Reintentar historial',read));}
  }
  details.addEventListener('toggle',()=>{if(details.open&&route.nodeId!==node.id)open({...route,nodeId:node.id,runsOffset:0});});
  if(route.nodeId===node.id){details.open=true;return {details,after:read};}return {details,after:()=>{}};
 }
 function detail(c,version){
  const frag=document.createDocumentFragment();frag.append(link('← Volver a Decision Center',{...route,caseId:null,nodeId:null,runsOffset:0}));
  const header=card(c.label||(c.is_demo?'Demo · DDA Logística':c.friendly_id)),actions=el('div',undefined,'center-actions');header.append(el('p',c.friendly_id+' · DDA Logística','d-metadata'),pill(c.status));if(c.in_review)header.append(pill('review'));
  actions.append(runtime(c.status==='completed'?'Ver resultado':'Continuar',c,c.resume,true));if(writable())actions.append(button('Editar nombre',()=>edit(c)),button(c.status==='archived'?'Restaurar':'Archivar',()=>edit(c,true)));if(c.is_demo)header.append(demoBadge(),el('p','Este caso usa datos de ejemplo. Sus resultados son demostrativos.','d-body'));header.append(actions);frag.append(header);
  const data=card('Contexto de datos'),fields=el('dl',undefined,'center-fields');for(const [label,value]of [['Órdenes',c.orders?.label||c.orders?.canonical_filename],['Flota',c.fleet?.label||c.fleet?.canonical_filename],['Validación',c.orders?.validation==='validated'&&c.fleet?.validation==='validated'?'Ambos datasets validados':'Revisar validación de los datasets'],['Creado por',person(c.created_by)],['Creado',stamp(c.created_at,zone())]])fields.append(field(label,value));data.append(fields,external('Ver datos',{view:'platform-data',hub:{tab:'packs',ordersId:c.orders.id,fleetId:c.fleet.id}}));frag.append(data);
  const flow=card('Decisiones del caso'),list=el('ol',undefined,'center-timeline'),afters=[];
  for(const node of c.nodes){const item=el('li',undefined,'center-node'),meta=DECISION_META[node.id];item.dataset.centerNode=node.id;item.append(el('h3',meta.index+' · '+meta.label,'center-node-title'),pill(node.status));
   const info=el('dl',undefined,'center-fields'),approved=node.approved_run;
   for(const [label,value]of [['Responsable',person(node.owner,'Sin asignar')],['Aprobador asignado',person(node.approver,'Sin asignar')],['Última corrida',node.latest_run?'RUN-'+node.latest_run.id.slice(0,8):'Sin corridas'],['Corrida aprobada',approved?'RUN-'+approved.id.slice(0,8):'Sin aprobación'],['Aprobada por',approved?.legacy_approval?'Workspace compartido (histórico)':person(approved?.approved_by)],['Aprobada',stamp(approved?.approved_at,zone())],['Corridas',String(node.run_count)]])info.append(field(label,value));item.append(info);
   if(['stale','error'].includes(node.status))item.append(el('p',describeFailure(null,{kind:node.status==='stale'?'stale':'run'}).message,'d-body'));
   if(node.id==='logistics_scheduling'&&node.status==='locked')item.append(el('p',describeFailure(null,{kind:'source'}).message,'d-body'));
   const bar=el('div',undefined,'center-actions');if(getIdentity().membership.access_role==='admin'&&c.status!=='archived')bar.append(button('Asignar responsables',()=>assign(c,node)));if(node.target){bar.append(runtime('Continuar decisión',c,node.target,true));if(approved)bar.append(runtime('Abrir dashboard aprobado',c,{view:'decision-dashboard',node_id:node.id,run_id:approved.id}));if(node.latest_run&&node.latest_run.id!==approved?.id)bar.append(runtime('Abrir último dashboard',c,{view:'decision-dashboard',node_id:node.id,run_id:node.latest_run.id}));}else item.append(el('p','Este paso todavía no está disponible para ejecutar.','d-metadata'));item.append(bar);
   const h=history(node,c,version);item.append(h.details);afters.push(h.after);list.append(item);
  }
  flow.append(list);frag.append(flow);const activity=el('details',undefined,'d-card center-card');activity.dataset.caseActivity='';activity.append(el('summary','Actividad del caso'));const feed=el('div');activity.append(feed);activity.addEventListener('toggle',()=>{activityView?.dispose();activityView=null;if(activity.open)activityView=mountActivity(feed,{getIdentity,caseId:c.id});});frag.append(activity);const technical=el('details',undefined,'d-card center-card');technical.append(el('summary','Información técnica'),el('code',c.id));frag.append(technical);return {frag,after:()=>afters.forEach(fn=>fn())};
 }
 async function load(){
  activityView?.dispose();activityView=null;controller?.abort();controller=new AbortController();close();const version=++generation;root.setAttribute('aria-busy','true');root.replaceChildren(el('p','Cargando Decision Center…','d-body'));
  try{route=readCenterResource(location.href);const params=new URLSearchParams({filter:route.filter,q:route.q,dda:route.dda,limit:size,offset:route.offset});const data=await api(BASE+(route.caseId?'/'+route.caseId:'?'+params),{signal:controller.signal});if(version!==generation||controller.signal.aborted)return;
   const frag=document.createDocumentFragment();if(notice){const message=el('p',notice,'center-message');message.role='status';frag.append(message);notice='';}let after;if(route.caseId){const result=detail(data,version);frag.append(result.frag);after=result.after;}else frag.append(listing(data));root.replaceChildren(frag);after?.();
  }catch(error){if(version!==generation||controller.signal.aborted)return;const panel=card('No se pudo abrir Decision Center'),message=el('p',describeFailure(error).message,'d-body');message.role='alert';panel.append(message,button('Reintentar',load),link('Volver al listado',{}));root.replaceChildren(panel);}
  finally{if(version===generation)root.removeAttribute('aria-busy');}
 }
 function stop(){activityView?.dispose();activityView=null;generation++;controller?.abort();close();root.removeAttribute('aria-busy');}
 function onView(){if(window.dationGetCurrentView?.()==='platform-decisions')load();else stop();}
 scope.listen(window,'dation:view',onView);scope.listen(window,'pagehide',stop);scope.listen(window,'dation:identity',()=>{const next=getIdentity().membership.access_role+':'+enabled();if(next!==access){access=next;onView();}});access=getIdentity().membership.access_role+':'+enabled();onView();
 return {dispose(){stop();scope.dispose();}};
}
