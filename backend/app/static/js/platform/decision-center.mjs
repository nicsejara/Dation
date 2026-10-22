import {caseContext,statePresentation,objectivePresentation} from './foundation.mjs';
import {DDA_CATALOG} from './dda-catalog.mjs';
import {CASE_CATEGORIES} from '../dispatch/case-identity.mjs';
import {describeFailure} from '../dispatch/recovery.mjs';
import {demoBadge} from './onboarding.mjs';
import {api} from '../dispatch/shared.mjs';
import {createScope} from '../dispatch/lifecycle.mjs';
import {resourceUrl} from '../dispatch/navigation.mjs';
import {DECISION_META,iconSvg} from '../dispatch/decision-ui.mjs';
import {mountDialog,mountDropdown,heroCta} from './components.mjs';
import {mountCenterActions} from './decision-center-actions.mjs';
import {ddaEnabled} from './entitlements.mjs';
import {CENTER_FILTERS,readCenterResource} from './center-resource.mjs';
import {mountActivity} from './activity.mjs';
import {workspaceDate} from './workspace-format.mjs';

const BASE='/api/platform/decisions',size=25;
const statusNames={active:'En progreso',completed:'Completado',archived:'Archivado',review:'En revisión',pending_approval:'Pendiente de aprobación',approved:'Aprobada',running:'En ejecución',error:'Requiere revisión',stale:'Requiere actualizar',available:'Disponible',locked:'Bloqueado',needs_data:'Faltan datos',coming_soon:'Próximamente'};
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function icon(name){const box=el('span',undefined,'center-icon');box.innerHTML=iconSvg(name);return box;}
function button(text,handler,kind='secondary'){const n=el('button',text,'d-button d-button--'+kind);n.type='button';n.addEventListener('click',handler);return n;}
function pill(status){const n=el('span',statusNames[status]||status,'center-status');n.dataset.state=status;n.dataset.tone=statePresentation(status==='pending_approval'?'review':status).tone;return n;}
function person(value,fallback='Sin asignar'){return value?.name?value.name+(value.active===false?' (inactivo)':''):fallback;}
function ddaLabel(id){return DDA_CATALOG.find(d=>d.id===id)?.title||id||'DDA';}
function namedPerson(value){const wrap=el('span',undefined,'center-person'),initials=(value?.name||'').split(/\s+/).filter(Boolean).slice(0,2).map(s=>s[0]).join('').toUpperCase()||'—',avatar=el('span',initials,'center-avatar');avatar.setAttribute('aria-hidden','true');wrap.append(avatar,el('span',person(value)));return wrap;}

export function mountDecisionCenter(root,getIdentity){
 const scope=createScope(root),wide=matchMedia('(min-width:1100px)');root.classList.add('decision-center');
 let route={},listKey=null,detailKey=null,listController,detailController,listVersion=0,detailVersion=0,data=null,active=false,returnFocus=null,notice='';
 let activityView=null,historySync=()=>{},drawerCleanups=[],portfolioCleanups=[];
 const writable=()=>getIdentity().membership.access_role!=='viewer',admin=()=>getIdentity().membership.access_role==='admin',zone=()=>getIdentity().workspace;
 const hero=el('header',undefined,'center-hero'),copy=el('div',undefined,'center-hero__copy');copy.append(el('p','DECISION INTELLIGENCE','d-eyebrow'),el('h1','Decision Center','d-page-title'),el('p','Gestioná, revisá y recuperá todas las decisiones de tu Workspace desde un único lugar.','d-page-description'));
 copy.append(heroCta(button('Explorar DDA',()=>window.dationNavigate('inicio'),'primary')));const illustration=el('img');illustration.src='/static/assets/decision-center-hero.svg';illustration.alt='';illustration.width=400;illustration.height=240;hero.append(copy,illustration);
 const message=el('p',undefined,'center-message');message.role='status';message.hidden=true;
 const layout=el('div',undefined,'center-layout'),portfolio=el('div',undefined,'center-portfolio'),aside=el('aside',undefined,'center-drawer'),sheet=el('dialog',undefined,'d-platform center-drawer center-drawer--sheet'),body=el('div',undefined,'center-drawer__body');
 aside.dataset.centerDrawer='';sheet.dataset.centerSheet='';for(const panel of [aside,sheet])panel.setAttribute('aria-labelledby','center-drawer-title');aside.hidden=true;
 const actionsRoot=el('div');layout.append(portfolio,aside);root.replaceChildren(hero,message,layout,sheet,actionsRoot);
 const actions=mountCenterActions(actionsRoot,{onChanged:result=>{if(result?.archived!==undefined){listKey=detailKey=null;open({filter:result.archived?'archived':'all',q:'',dda:'all',owner:'all',offset:0,caseId:null,nodeId:null,runsOffset:0});}else refresh();},notify:text=>{notice=text;showNotice();}}),sheetView=mountDialog({dialog:sheet,initialFocus:'[data-center-close]',closeOnBackdrop:true});
 function showNotice(){message.hidden=!notice;message.textContent=notice;}
 function open(value){window.DationDispatch.openDecisionCenter({...route,...value});}
 function selectCase(c){if(!route.caseId)returnFocus=document.activeElement;open({caseId:c.id,nodeId:null,runsOffset:0});}
 function closeCase(){const target=returnFocus,selected=route.caseId;open({caseId:null,nodeId:null,runsOffset:0});requestAnimationFrame(()=>{if(target?.isConnected)target.focus({preventScroll:true});else (portfolio.querySelector('[data-case-open="'+selected+'"]')||portfolio.querySelector('[data-case-open]'))?.focus({preventScroll:true});});}
 function link(text,value,cls='center-link'){
  const a=el('a',text,cls);a.href=resourceUrl(location.href,{view:'platform-decisions',center:{...route,...value}});
  a.addEventListener('click',event=>{if(event.button||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;event.preventDefault();if(value.caseId&&!route.caseId)returnFocus=a;open(value);});return a;
 }
 function destination(text,target,c,{primary=false,continuation=false}={}){
  const a=el('a',text,'d-button d-button--'+(primary?'primary':'secondary'));
  const disabled=!target||!ddaEnabled(getIdentity(),c.dda)||target.view==='logistics-config'&&!writable()||c.status==='archived'&&(continuation||target.view!=='decision-dashboard');
  if(disabled){a.setAttribute('role','link');a.setAttribute('aria-disabled','true');a.tabIndex=-1;return a;}
  const value={view:target.view,caseId:c.id,nodeId:target.node_id,runId:target.run_id};a.href=resourceUrl(location.href,value);
  a.addEventListener('click',event=>{if(event.button||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;event.preventDefault();if(value.runId)window.DationDispatch.openDashboard(c.id,value.nodeId,value.runId);else window.DationDispatch.openCase(c.id,value.view,value.nodeId);});return a;
 }
 function cleanupPortfolio(){portfolioCleanups.forEach(fn=>fn());portfolioCleanups=[];}
 function cleanupDrawer(){drawerCleanups.forEach(fn=>fn());drawerCleanups=[];activityView?.dispose();activityView=null;historySync=()=>{};}
 function maintenance(c){
  const wrap=el('div',undefined,'center-maintenance'),trigger=button('',()=>{}),panel=el('div',undefined,'center-maintenance__menu');trigger.className='d-button d-button--ghost center-icon-button';trigger.append(icon('moreHorizontal'));trigger.setAttribute('aria-label','Acciones de '+c.friendly_id);panel.role='menu';
  const add=(text,fn)=>{const b=button(text,fn);b.role='menuitem';panel.append(b);};
  if(writable())add('Editar nombre',()=>actions.edit(c));
  add('Copiar ID',async()=>{try{await navigator.clipboard.writeText(c.friendly_id);notice='ID copiado.';}catch{notice='No se pudo copiar el ID. Podés seleccionarlo en el detalle.';}showNotice();});
  if(writable())add(c.status==='archived'?'Restaurar':'Archivar',()=>actions.edit(c,true));
  wrap.append(trigger,panel);const menu=mountDropdown({trigger,panel});return {node:wrap,dispose:()=>menu.dispose()};
 }
 function pager(total,offset,change){const nav=el('nav',undefined,'center-pagination');nav.setAttribute('aria-label','Paginación');const prev=button('Anterior',()=>change(Math.max(0,offset-size))),next=button('Siguiente',()=>change(offset+size));prev.disabled=offset===0;next.disabled=offset+size>=total;nav.append(prev,el('span',total?`${Math.min(offset+1,total)}–${Math.min(offset+size,total)} de ${total}`:'0 resultados','d-metadata'),next);return nav;}
 function loading(target,drawer=false){target.setAttribute('aria-busy','true');const block=el('div',undefined,drawer?'center-loading center-loading--drawer':'center-loading');block.setAttribute('aria-label',drawer?'Cargando caso':'Cargando Decision Center');block.role='status';block.append(el('span',drawer?'Cargando caso…':'Cargando Decision Center…','d-metadata'));for(let i=0;i<(drawer?4:6);i++)block.append(el('div',undefined,'center-skeleton'));target.replaceChildren(block);}
 function failure(target,title,error,retry){target.removeAttribute('aria-busy');const card=el('section',undefined,'d-card center-error');card.append(el('h2',title,'d-card-title'));const text=el('p',describeFailure(error).message,'d-body');text.role='alert';card.append(text,button('Reintentar',retry));target.replaceChildren(card);}
 function renderPortfolio(){
  cleanupPortfolio();const frag=document.createDocumentFragment(),summary=data.summary||{},kpis=el('div',undefined,'center-kpis');kpis.setAttribute('aria-label','Resumen del workspace');
  for(const [key,label,filter,name]of [['active_cases','Cases activos','in_progress','folderOpen'],['in_review','En revisión','review','eye'],['pending_approval','Pendientes de aprobación','pending_approval','clock'],['approved','Aprobadas','approved','checkCircle']]){
   const card=button('',()=>open({filter,offset:0}), 'ghost');card.className='center-kpi';card.dataset.kpi=key;card.setAttribute('aria-pressed',String(route.filter===filter));card.append(icon(name),el('span',label,'center-kpi__label'),el('strong',String(summary[key]??'—'),'center-kpi__value'),el('span','›','center-kpi__arrow'));kpis.append(card);
  }frag.append(kpis);
  if(summary.pending_approval>0){const attention=el('section',undefined,'center-attention'),text=el('div');text.append(el('h2','Requiere tu atención'),el('p',summary.pending_approval===1?'1 decisión espera tu aprobación.':`${summary.pending_approval} decisiones esperan tu aprobación.`));attention.append(icon('clock'),text,button('Ver pendientes',()=>open({filter:'pending_approval',offset:0})));frag.append(attention);}
  const form=el('form',undefined,'center-search'),controls={};
  function control(key,label,options){const wrap=el('div',undefined,'center-filter'),l=el('label',label,'center-sr-only'),input=el(options?'select':'input',undefined,'d-input');input.id='center-'+key;l.htmlFor=input.id;input.name=key;
   if(options)for(const [value,text]of Object.entries(options)){const o=el('option',text);o.value=value;input.append(o);}else{input.type='search';input.maxLength=120;input.placeholder='Buscar por Decision Case, ID o nombre…';}
   input.value=route[key]||'all';controls[key]=input;wrap.append(l,input);form.append(wrap);return input;
  }
  control('q','Buscar por ID o etiqueta');controls.q.value=route.q;control('filter','Estado',CENTER_FILTERS);
  const ddas={all:'Todos los DDAs'};for(const id of new Set([...(data.dda_options||[]),...(route.dda!=='all'?[route.dda]:[])]))ddas[id]=ddaLabel(id);control('dda','DDA',ddas);
  const owners={all:'Todos los responsables',me:'Mis casos',unassigned:'Sin asignar'};for(const p of data.owner_options||[])if(p)owners[p.id]=person(p);if(!owners[route.owner||'all'])owners[route.owner]='Responsable seleccionado';control('owner','Responsable',owners);
  const submit=el('button','Buscar','d-button d-button--secondary');submit.type='submit';form.append(submit,button('Limpiar filtros',()=>open({filter:'all',q:'',dda:'all',owner:'all',offset:0}),'ghost'));
  function filter(){open({q:controls.q.value.trim(),filter:controls.filter.value,dda:controls.dda.value,owner:controls.owner.value,offset:0});}
  form.addEventListener('submit',event=>{event.preventDefault();filter();});for(const key of ['filter','dda','owner'])controls[key].addEventListener('change',filter);frag.append(form);
  if(!data.items.length){const empty=el('section',undefined,'d-card center-empty'),filtered=route.q||route.filter!=='all'||route.dda!=='all'||route.owner!=='all';empty.append(icon('folderOpen'),el('h2',filtered?'No encontramos Decision Cases con estos filtros.':'Todavía no hay decisiones en este Workspace.','d-section-title'));
   if(filtered)empty.append(button('Limpiar filtros',()=>open({filter:'all',q:'',dda:'all',owner:'all',offset:0})));else empty.append(el('p','Explorá un DDA para iniciar tu primer Decision Case.','d-body'),heroCta(button('Explorar DDA',()=>window.dationNavigate('inicio'),'primary')));frag.append(empty);
  }else{
   const wrap=el('div',undefined,'center-table-scroll'),table=el('table',undefined,'center-table'),head=el('thead'),header=el('tr'),tbody=el('tbody');wrap.tabIndex=0;wrap.role='region';wrap.setAttribute('aria-label','Portfolio de Decision Cases');
   const titles=['Case','DDA','Objetivo actual','Paso actual','Progreso','Responsable','Estado','Última actividad','Acción'];for(const [i,text]of titles.entries()){const th=el('th',text);th.scope='col';th.dataset.column=i;header.append(th);}head.append(header);table.append(head,tbody);
   for(const c of data.items){const context=caseContext(c),row=el('tr');row.dataset.centerCase=c.id;row.tabIndex=0;row.setAttribute('aria-label','Inspeccionar '+(context.label||context.friendlyId));row.setAttribute('aria-selected',String(c.id===route.caseId));
    const add=(i,value)=>{const td=el('td');td.dataset.column=i;td.dataset.label=titles[i];td.append(typeof value==='string'?document.createTextNode(value):value);row.append(td);};
    const name=el('div',undefined,'center-name');name.append(link(context.label||(c.is_demo?'Demo · '+ddaLabel(c.dda):context.friendlyId),{caseId:c.id,nodeId:null,runsOffset:0}),el('span',context.friendlyId,'d-metadata'));if(c.is_demo)name.append(demoBadge());add(0,name);
    add(1,el('span',ddaLabel(c.dda),'center-dda-tag'));add(2,c.current_objective?.label||'Por definir');add(3,c.current_step_label||'Por definir');
    const progress=el('div',undefined,'center-progress'),bar=el('progress');bar.max=c.progress.total||1;bar.value=c.progress.approved;bar.setAttribute('aria-label',`${c.progress.approved} de ${c.progress.total} aprobadas`);progress.append(el('span',`${c.progress.approved} de ${c.progress.total} aprobadas`),bar);add(4,progress);
    add(5,namedPerson(c.owner));add(6,pill(c.display_status||c.status));add(7,workspaceDate(c.last_activity_at,zone()));const action=el('div',undefined,'center-row-actions'),a=link('Abrir',{caseId:c.id,nodeId:null,runsOffset:0},'d-button d-button--secondary');a.dataset.caseOpen=c.id;const menu=maintenance(c);action.append(a,menu.node);portfolioCleanups.push(menu.dispose);add(8,action);
    row.addEventListener('click',event=>{if(!event.target.closest('a,button,input,select,summary,[role=menu]'))selectCase(c);});row.addEventListener('keydown',event=>{if(event.target===row&&['Enter',' '].includes(event.key)){event.preventDefault();selectCase(c);}});tbody.append(row);
   }wrap.append(table);frag.append(wrap);
  }
  frag.append(pager(data.total,route.offset,offset=>open({offset})));portfolio.replaceChildren(frag);portfolio.removeAttribute('aria-busy');
 }
 function syncSelection(){for(const row of portfolio.querySelectorAll('[data-center-case]'))row.setAttribute('aria-selected',String(row.dataset.centerCase===route.caseId));}
 function drawerLayout(){const focus=document.activeElement,hadFocus=body.contains(focus);
  if(!active||!route.caseId){sheetView.close();aside.hidden=true;layout.classList.remove('has-selection');}
  else{aside.hidden=true;layout.classList.remove('has-selection');if(body.parentNode!==sheet)sheet.append(body);sheetView.open();}
  if(hadFocus&&focus?.isConnected)focus.focus({preventScroll:true});
 }
 function drawerFrame(c){const header=el('header',undefined,'center-drawer__header'),copy=el('div');copy.append(el('span','DECISION CASE','d-eyebrow'));const title=el('h2',c?.label||c?.friendly_id||'Caso seleccionado','d-section-title');title.id='center-drawer-title';copy.append(title);if(c)copy.append(el('p',c.friendly_id,'d-metadata'));
  const close=button('',closeCase,'ghost');close.dataset.centerClose='';close.className='d-button d-button--ghost center-icon-button';close.setAttribute('aria-label','Cerrar detalle del caso');close.append(icon('x'));header.append(copy,close);return header;}
 function personField(c,stageKey,key,label,value){const field=el('div',undefined,'center-responsibility');field.append(el('span',label,'d-metadata'),namedPerson(value));
  if(admin()&&c.status!=='archived'&&(['data_preparation','data_owner','data_steward'].includes(stageKey)||DECISION_META[stageKey]?.implemented)){const assign=button(value?'Cambiar':'Asignar',()=>actions.assign(c,stageKey,key),'ghost');assign.className='center-inline-action';assign.setAttribute('aria-label',`${value?'Cambiar':'Asignar'} ${label.toLowerCase()} · ${stageKey==='data_preparation'?'datos':DECISION_META[stageKey]?.label||stageKey}`);field.append(assign);}return field;}
 function renderDrawer(c){
  cleanupDrawer();const content=el('div',undefined,'center-drawer__content');body.replaceChildren(drawerFrame(c),content);const top=el('div',undefined,'center-case-meta');top.append(el('span',ddaLabel(c.dda),'center-dda-tag'),pill(c.display_status||c.status));if(c.is_demo)top.append(demoBadge());const menu=maintenance(c);top.append(menu.node);drawerCleanups.push(menu.dispose);content.append(top);
  if(c.category)content.append(el('p','Categoría · '+(CASE_CATEGORIES.find(([id])=>id===c.category)?.[1]||c.category),'d-metadata'));
  if(c.description)content.append(el('p',c.description,'d-body'));
  const ctas=el('div',undefined,'center-drawer__ctas'),relevant=c.nodes?.find(n=>n.id===c.current_step),official=c.resume?.run_id&&relevant?.approval_current&&c.resume.run_id===relevant.approved_run?.id;ctas.append(destination(official?'Ver resultado aprobado':c.status==='completed'?'Ver resultado':relevant?.status==='review'?'Revisar':'Continuar',c.resume,c,{primary:true,continuation:true}),destination('Ir al Decision Map',c.dda==='logistics'?{view:'logistics-map',node_id:c.current_step,run_id:null}:null,c,{continuation:true}));content.append(ctas);
  const objective=el('div',undefined,'center-objective');objective.append(icon('target'),el('div','Objetivo actual','d-metadata'),el('strong',c.current_objective?.label||'Por definir'));content.append(objective);
  const responsibility=el('section',undefined,'center-responsibilities');if(c.current_step&&relevant)responsibility.append(personField(c,c.current_step,'owner','Responsable',relevant.owner),personField(c,c.current_step,'approver','Aprobador asignado',relevant.approver));content.append(responsibility);
  const linked=el('section',undefined,'center-linked-data');linked.append(el('h3','Datos vinculados','d-card-title'));
  for(const dataset of [c.orders,c.fleet].filter(Boolean)){const row=el('div',undefined,'center-linked-file'),text=el('div');text.append(el('strong',dataset.original_filename||dataset.canonical_filename||dataset.label||'Archivo'),el('span',`${dataset.row_count??'—'} registros · ${dataset.validation==='validated'?'Validado':'Revisar validación'}`,'d-metadata'));row.append(icon('fileJson'),text);
   if(!dataset.deletion_pending){const a=el('a',undefined,'d-button d-button--ghost center-icon-button');a.href='/api/platform/data/datasets/'+dataset.id+'/download';a.download=dataset.original_filename||'datos.csv';a.setAttribute('aria-label','Descargar '+(dataset.original_filename||dataset.canonical_filename||'archivo'));a.append(icon('download'));row.append(a);}linked.append(row);
  }
  const stages=c.responsibilities?.stages||{};for(const [key,label]of [['data_owner','Data Owner'],['data_steward','Data Steward']])if(stages[key])linked.append(personField(c,key,'owner',label,stages[key].owner));if(!stages.data_owner&&stages.data_preparation)linked.append(personField(c,'data_preparation','owner','Responsable de datos',stages.data_preparation.owner));content.append(linked);
  const chain=el('section',undefined,'center-chain');chain.append(el('h3','Cadena de decisiones','d-card-title'));const list=el('ol',undefined,'center-timeline');chain.append(list);content.append(chain);const histories=[];
  for(const [index,node]of (c.nodes||[]).entries()){
   const meta=DECISION_META[node.id]||{label:node.label},item=el('li',undefined,'center-node');item.dataset.centerNode=node.id;const header=el('div',undefined,'center-node__header');header.append(el('span',String(index+1).padStart(2,'0'),'center-node__number'),el('h4',meta.label,'center-node-title'),pill(node.status));item.append(header,el('p','Objetivo · '+(node.objective?.label||'Por definir'),'center-node__objective'));
   if(node.target&&!['locked','needs_data','coming_soon'].includes(node.status)){const label={approved:'Ver dashboard',review:'Revisar',available:'Configurar',running:'Ver ejecución'}[node.status]||'Ver decisión',candidate=['review','running','error'].includes(node.status)&&node.latest_run&&!node.latest_run.approved_at;
    item.append(destination(label,candidate?{view:'decision-dashboard',node_id:node.id,run_id:node.latest_run.id}:node.target,c,{continuation:true}));
    if(candidate&&node.latest_objective?.id!==node.objective?.id)item.append(el('p','Objetivo de la candidata · '+(node.latest_objective?.label||'Por definir'),'d-metadata'));
   }
   const details=el('details',undefined,'center-node-details');details.append(el('summary','Responsables y aprobación'));const fields=el('div',undefined,'center-responsibilities');fields.append(personField(c,node.id,'owner','Responsable',node.owner),personField(c,node.id,'approver','Aprobador asignado',node.approver));details.append(fields);
   const approved=node.approved_run;if(approved)details.append(el('p','Aprobada por · '+(approved.legacy_approval?'Workspace compartido (histórico)':person(approved.approved_by,'Sin registro')),'d-metadata'),el('p',workspaceDate(approved.approved_at,zone()),'d-metadata'),el('p','RUN-'+approved.id.slice(0,8),'d-metadata'),destination('Abrir dashboard aprobado',{view:'decision-dashboard',node_id:node.id,run_id:approved.id},c));
   if(node.latest_run&&node.latest_run.id!==approved?.id)details.append(destination('Abrir último dashboard',{view:'decision-dashboard',node_id:node.id,run_id:node.latest_run.id},c));if(['stale','error'].includes(node.status))details.append(el('p',describeFailure(null,{kind:node.status==='stale'?'stale':'run'}).message,'d-metadata'));
   item.append(details);const history=el('details',undefined,'center-history'),historyBody=el('div');history.dataset.nodeHistory=node.id;history.append(el('summary',`Historial de corridas (${node.run_count})`),historyBody);item.append(history);list.append(item);let requestKey=null,version=0,controller;
   async function loadHistory(){const key=route.runsOffset;if(requestKey===key)return;requestKey=key;const own=++version;controller?.abort();controller=new AbortController();historyBody.replaceChildren(el('p','Cargando historial…','d-metadata'));
    try{const data=await api(BASE+'/'+c.id+'/runs?'+new URLSearchParams({node_id:node.id,limit:size,offset:key}),{signal:controller.signal});if(own!==version)return;const rows=el('ol',undefined,'center-run-list');
     for(const r of data.items){const row=el('li',undefined,'center-run');row.append(destination('RUN-'+r.id.slice(0,8),{view:'decision-dashboard',node_id:node.id,run_id:r.id},c),el('p',`${workspaceDate(r.created_at,zone())} · ${objectivePresentation(r.objective)?.label||'Por definir'}`,'d-metadata'),el('p',`${{queued:'En cola',running:'En ejecución',completed:'Completada',error:'Error'}[r.status]||r.status} · ${r.approved_at?(r.superseded_at?'Reemplazada':r.decision_state==='stale'?'Requiere actualizar':'Aprobada'):'Sin aprobar'}`,'d-metadata'));
      const technical=el('details');technical.append(el('summary','Datos técnicos'));for(const [label,value]of [['ID',r.id],['Creada por',person(r.created_by,'Sin registro')],['Aprobada por',person(r.approved_by,'Sin registro')],['Duración',r.duration_ms==null?'—':r.duration_ms+' ms'],['Motor',[r.engine_name,r.engine_version].filter(Boolean).join(' ')],['Input fingerprint',r.input_fingerprint],['Result fingerprint',r.result_fingerprint]])technical.append(el('p',label+': '+(value||'Sin registro'),'d-metadata'));row.append(technical);rows.append(row);
     }historyBody.replaceChildren(data.items.length?rows:el('p','No hay corridas en esta página.','d-metadata'),pager(data.total,key,runsOffset=>open({nodeId:node.id,runsOffset})));
    }catch(error){if(own===version&&!controller.signal.aborted){requestKey=null;historyBody.replaceChildren(el('p',error.message,'d-metadata'),button('Reintentar historial',loadHistory));}}
   }
   history.addEventListener('toggle',()=>{if(history.open&&route.nodeId!==node.id)open({nodeId:node.id,runsOffset:0});else if(!history.open&&route.nodeId===node.id)open({nodeId:null,runsOffset:0});});histories.push(()=>{history.open=route.nodeId===node.id;if(history.open)loadHistory();});drawerCleanups.push(()=>{version++;controller?.abort();});
  }
  historySync=()=>histories.forEach(fn=>fn());historySync();const activity=el('section',undefined,'center-case-activity');activity.dataset.caseActivity='';activity.append(el('h3','Actividad reciente','d-card-title'));const feed=el('div');activity.append(feed);content.append(activity);activityView=mountActivity(feed,{getIdentity,caseId:c.id,limit:5,compact:true});activity.append(button('Ver toda la actividad',()=>{activityView?.dispose();activityView=mountActivity(feed,{getIdentity,caseId:c.id,limit:10});}));
  const technical=el('details',undefined,'center-technical');technical.append(el('summary','Información técnica'),el('code',c.id),el('p','Creado por · '+person(c.created_by,'Sin registro'),'d-metadata'),el('p',workspaceDate(c.created_at,zone()),'d-metadata'));content.append(technical);body.removeAttribute('aria-busy');drawerLayout();if(!wide.matches&&!sheet.contains(document.activeElement))body.querySelector('[data-center-close]')?.focus({preventScroll:true});
 }
 async function loadPortfolio(){const own=++listVersion;listController?.abort();listController=new AbortController();loading(portfolio);
  try{const params=new URLSearchParams({filter:route.filter,q:route.q,dda:route.dda,owner:route.owner,limit:size,offset:route.offset});const result=await api(BASE+'?'+params,{signal:listController.signal});if(own!==listVersion||!active)return;data=result;renderPortfolio();syncSelection();}
  catch(error){if(own===listVersion&&!listController.signal.aborted)failure(portfolio,'No pudimos cargar Decision Center.',error,()=>{listKey=null;load();});}
 }
 async function loadDetail(){const own=++detailVersion;detailController?.abort();detailController=new AbortController();cleanupDrawer();body.replaceChildren(drawerFrame());const pending=el('div');body.append(pending);loading(pending,true);drawerLayout();
  try{const result=await api(BASE+'/'+route.caseId,{signal:detailController.signal});if(own!==detailVersion||!active)return;if(String(result.id).toLowerCase()!==String(route.caseId).toLowerCase())throw new Error('El Decision Case recibido no coincide con el seleccionado.');renderDrawer(result);}
  catch(error){if(own===detailVersion&&!detailController.signal.aborted)failure(pending,'No pudimos recuperar este Decision Case.',error,()=>{detailKey=null;load();});}
 }
 function refresh(){listKey=null;detailKey=null;load();}
 function load(){if(!active)return;let next;try{next=readCenterResource(location.href);}catch(error){failure(portfolio,'No pudimos cargar Decision Center.',error,()=>window.DationDispatch.openDecisionCenter({}));cleanupDrawer();route={};drawerLayout();return;}
  route=next;showNotice();const key=JSON.stringify([route.q,route.filter,route.dda,route.owner,route.offset]);if(listKey!==key){listKey=key;loadPortfolio();}else syncSelection();
  if(!route.caseId){detailVersion++;detailController?.abort();detailKey=null;cleanupDrawer();drawerLayout();}else if(detailKey!==route.caseId){detailKey=route.caseId;loadDetail();}else{drawerLayout();historySync();}
 }
 function stop(){active=false;listVersion++;detailVersion++;listController?.abort();detailController?.abort();listKey=detailKey=null;actions.close();cleanupPortfolio();cleanupDrawer();drawerLayout();}
 function onView(){if(window.dationGetCurrentView?.()==='platform-decisions'){active=true;load();}else stop();}
 scope.listen(window,'dation:view',onView);scope.listen(window,'pagehide',stop);scope.listen(window,'dation:identity',()=>{if(active){actions.close();refresh();}});scope.listen(wide,'change',drawerLayout);
 scope.listen(sheet,'cancel',event=>{event.preventDefault();if(active&&route.caseId)closeCase();});
 scope.listen(sheet,'click',event=>{if(event.target!==sheet)return;const rect=sheet.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)closeCase();});
 scope.listen(root,'keydown',event=>{if(event.key==='Escape'&&wide.matches&&route.caseId&&!actions.isOpen&&!event.target.closest('[role=menu]')){event.preventDefault();closeCase();}});
 onView();return {dispose(){stop();sheetView.dispose();actions.dispose();scope.dispose();}};
}
