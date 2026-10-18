import {createScope} from '../dispatch/lifecycle.mjs';
import {readResource, resourceUrl} from '../dispatch/navigation.mjs';
import {ddaEnabled} from './entitlements.mjs';

const states={available:'Listo para continuar',running:'En ejecución',review:'Para revisar',approved:'Aprobado',error:'Requiere revisión',stale:'Requiere actualizar',locked:'Pendiente',needs_data:'Faltan datos',completed:'Completado'};
function el(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;}
function link(text,view,className='d-button d-button--secondary',resource={}){
 const a=el('a',text,className);a.href=resourceUrl(location.href,{view,...resource});a.dataset.homeResource='';return a;
}
function dateLabel(value,timezone){
 const date=new Date(value);if(!Number.isFinite(date.getTime()))return '';
 try{return new Intl.DateTimeFormat('es',{day:'numeric',month:'short',timeZone:timezone||'UTC'}).format(date);}catch{return new Intl.DateTimeFormat('es',{day:'numeric',month:'short',timeZone:'UTC'}).format(date);}
}
function greeting(identity){
 let hour;try{hour=Number(new Intl.DateTimeFormat('en',{hour:'numeric',hourCycle:'h23',timeZone:identity.workspace.timezone||'UTC'}).format(new Date()));}catch{hour=new Date().getUTCHours();}
 const hello=hour<12?'Buenos días':hour<19?'Buenas tardes':'Buenas noches';
 return hello+(identity.profile.first_name?', '+identity.profile.first_name:'');
}
function section(title,id){const n=el('section',undefined,'d-card platform-home__section');n.setAttribute('aria-labelledby',id);n.append(el('h2',title,'d-section-title'));n.firstChild.id=id;return n;}

export function mountWorkspaceHome(root,getIdentity){
 const scope=createScope(root);let controller=null,generation=0;
 const header=el('header',undefined,'platform-home__header');
 const workspace=el('p',undefined,'platform-home__workspace'),title=el('h1',undefined,'d-page-title');
 header.append(workspace,title,el('p','Tu espacio de decisiones y actividad operativa.','d-page-description'));
 const content=el('div',undefined,'platform-home__content');root.replaceChildren(header,content);
 function renderHeader(){const identity=getIdentity();workspace.textContent=identity.workspace.name;title.textContent=greeting(identity);}
 function render(data){
  const identity=getIdentity(),fragment=document.createDocumentFragment();
  if(data.attention.items.length){
   const attention=section('Requiere tu atención','home-attention-title');attention.classList.add('platform-home__attention');
   const total=data.attention.total;
   attention.append(el('p',total===1?'Hay una versión lista para revisar en tu workspace.':`Hay ${total} versiones listas para revisar en tu workspace.`,'d-body'));
   const list=el('ul',undefined,'platform-home__reviews');
   for(const item of data.attention.items){
    const row=el('li'),copy=el('div');copy.append(el('strong',item.node_label),el('span','DC-'+item.case_id.slice(0,8),'d-metadata'));
    row.append(copy,link('Revisar','decision-dashboard','d-button d-button--secondary',{caseId:item.case_id,nodeId:item.node_id,runId:item.run_id}));list.append(row);
   }
   attention.append(list);if(total>data.attention.items.length)attention.append(el('p',`Mostrando ${data.attention.items.length} de ${total}.`,'d-metadata'));
   fragment.append(attention);
  }
  const grid=el('div',undefined,'platform-home__grid');
  if(data.recent_cases.length){
   const recent=section('Continuar trabajando','home-recent-title'),list=el('ul',undefined,'platform-home__cases');
   for(const item of data.recent_cases){
    const row=el('li',undefined,'platform-home__case');row.append(el('p',item.dda,'platform-home__kicker'));
    row.append(el('h3',item.label||'Decision Case','platform-home__case-title'),el('p','DC-'+item.case_id.slice(0,8),'d-metadata'));
    const meta=el('div',undefined,'platform-home__case-meta'),status=el('span',states[item.status]||'En progreso','platform-home__status');status.dataset.state=item.status;
    meta.append(el('span',item.node_label),status);
    const formatted=dateLabel(item.last_activity_at,identity.workspace.timezone);if(formatted){const time=el('time','Actividad: '+formatted,'d-metadata');time.dateTime=item.last_activity_at;meta.append(time);}
    const view=item.run_id?'decision-dashboard':'logistics-map';
    const next=link(item.status==='completed'?'Ver caso':'Continuar',view,'d-button d-button--secondary',{caseId:item.case_id,nodeId:item.node_id,runId:item.run_id});
    next.setAttribute('aria-label',`${item.status==='completed'?'Ver caso':'Continuar'} DC-${item.case_id.slice(0,8)}`);
    row.append(meta,next);list.append(row);
   }
   recent.append(list);grid.append(recent);
  }else{
   const empty=section('Todavía no hay actividad.','home-empty-title');empty.classList.add('platform-home__empty');
   const image=el('img');image.src='/static/assets/dda-logistics.svg';image.alt='';image.width=48;image.height=48;
   empty.prepend(image);empty.append(el('p',ddaEnabled(identity,'logistics')?'Empezá explorando DDA Logística. Conectá tus datos y prepará una decisión.':'Explorá las capacidades de Dation y su disponibilidad para tu workspace.','d-body'),link('Ver Decision Data Assets','inicio','d-button d-button--primary'));grid.append(empty);
  }
  const side=el('div',undefined,'platform-home__side'),quick=section('Accesos rápidos','home-actions-title'),links=el('ul',undefined,'platform-home__quick');
  for(const [text,view,copy] of [['Abrir DDA Logística','logistics-overview','Datos, criterios y evidencia.'],['Ver Decision Center','platform-decisions','Consultá tus decisiones.'],['Ver datos','platform-data','Archivos de tu workspace.']]){
   if(view==='logistics-overview'&&!ddaEnabled(identity,'logistics'))continue;
   const row=el('li'),a=link(text,view,'platform-home__quick-link');a.append(el('span','→','platform-home__arrow'));row.append(a,el('p',copy,'d-metadata'));links.append(row);
  }
  quick.append(links);side.append(quick);
  const activity=section('Actividad reciente','home-activity-title');
  // Only render persisted audit items when that contract becomes available.
  const items=data.activity.available?data.activity.items.slice(0,5):[];
  if(items.length){const list=el('ul',undefined,'platform-home__activity');for(const item of items){const row=el('li',item.label);list.append(row);}activity.append(list);}
  else activity.append(el('p','No hay actividad reciente para mostrar.','d-body'));
  side.append(activity);grid.append(side);fragment.append(grid);content.replaceChildren(fragment);
 }
 async function load(){
  controller?.abort();controller=new AbortController();const ownController=controller,version=++generation;
  renderHeader();content.setAttribute('aria-busy','true');
  const pending=el('div',undefined,'platform-home__loading');pending.role='status';pending.append(el('span','Cargando tu workspace…','d-body'));
  const skeleton=el('div',undefined,'platform-home__skeleton');skeleton.setAttribute('aria-hidden','true');pending.append(skeleton);content.replaceChildren(pending);
  try{
   const response=await fetch('/api/platform/home',{signal:ownController.signal,cache:'no-store'});
   if(!response.ok)throw new Error('No pudimos cargar tu workspace. Reintentá en unos instantes.');
   const data=await response.json();if(version!==generation||ownController.signal.aborted)return;
   render(data);
  }catch(error){
   if(version!==generation||ownController.signal.aborted)return;
   const panel=section('No se pudo cargar el inicio','home-error-title'),message=el('p','Revisá tu conexión y reintentá en unos instantes.','d-body');message.role='alert';
   const retry=el('button','Reintentar','d-button d-button--secondary');retry.type='button';retry.dataset.homeRetry='';panel.append(message,retry);content.replaceChildren(panel);
  }finally{if(version===generation)content.removeAttribute('aria-busy');}
 }
 function stop(){generation++;controller?.abort();content.removeAttribute('aria-busy');}
 function onView(){if(window.dationGetCurrentView?.()==='platform-home')load();else stop();}
 scope.listen(root,'click',event=>{
  if(event.target.closest('[data-home-retry]')){load();return;}
  const a=event.target.closest('a[data-home-resource]');if(!a||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
  const route=readResource(a.href);event.preventDefault();
  if(route.runId)window.DationDispatch.openRun(route.runId,route.nodeId,route.caseId);
  else if(route.caseId)window.DationDispatch.openCase(route.caseId,route.view,route.nodeId);
  else window.dationNavigate(route.view);
 });
 scope.listen(window,'dation:view',onView);scope.listen(window,'dation:identity',onView);scope.listen(window,'pagehide',stop);onView();
 return {dispose(){stop();scope.dispose();}};
}
