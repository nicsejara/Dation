import {api} from '../dispatch/shared.mjs';
import {demoBadge} from './onboarding.mjs';
import {describeFailure} from '../dispatch/recovery.mjs';
import {createScope} from '../dispatch/lifecycle.mjs';
import {readResource,resourceUrl} from '../dispatch/navigation.mjs';
import {mountActivity} from './activity.mjs';
import {workspaceDate,workspaceRelativeDate} from './workspace-format.mjs';
import {caseContext,statePresentation} from './foundation.mjs';
import {DDA_CATALOG} from './dda-catalog.mjs';
import {DECISION_META,iconSvg} from '../dispatch/decision-ui.mjs';
import {heroCta} from './components.mjs';

const states={available:'Listo para continuar',running:'En ejecución',review:'En revisión',approved:'Aprobada',error:'Error de ejecución',stale:'Requiere actualizar',locked:'Pendiente',needs_data:'Faltan datos',completed:'Completado'};
function el(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;}
function icon(name){const n=el('span',undefined,'platform-home__icon');n.setAttribute('aria-hidden','true');n.innerHTML=iconSvg(name);return n;}
function link(text,view,className='d-button d-button--secondary',resource={}){
 const a=el('a',text,className);a.href=resourceUrl(location.href,{view,...resource});a.dataset.homeResource='';return a;
}
function greeting(identity){
 let hour;try{hour=Number(new Intl.DateTimeFormat('en',{hour:'numeric',hourCycle:'h23',timeZone:identity.workspace.timezone||'UTC'}).format(new Date()));}catch{hour=new Date().getUTCHours();}
 const hello=hour<12?'Buenos días':hour<19?'Buenas tardes':'Buenas noches';
 return hello+(identity.profile.first_name?', '+identity.profile.first_name:'');
}
function section(title,id,iconName){const n=el('section',undefined,'d-card platform-home__section'),head=el('div',undefined,'platform-home__section-head'),heading=el('h2',undefined,'d-section-title');heading.id=id;heading.append(icon(iconName),el('span',title));head.append(heading);n.setAttribute('aria-labelledby',id);n.append(head);return n;}
function badge(status,label=states[status]||'En progreso'){
 const n=el('span',label,'d-status d-status--'+statePresentation(status).tone);n.dataset.state=status;return n;
}
function contextLabel(item){return item.friendly_id||caseContext(item).friendlyId;}
function nodeLabel(item){return DECISION_META[item.node_id]?.label||item.node_label||'Decisión';}

export function mountWorkspaceHome(root,getIdentity){
 const scope=createScope(root);let controller=null,generation=0,activityView=null;
 const identityKey=()=>JSON.stringify([getIdentity().workspace,getIdentity().membership.access_role,getIdentity().ddas]);let currentIdentityKey=identityKey();
 const header=el('header',undefined,'platform-home__header'),copy=el('div',undefined,'platform-home__hero-copy');
 const workspace=el('p',undefined,'platform-home__workspace'),title=el('h1',undefined,'d-page-title'),ctas=el('div',undefined,'platform-home__hero-actions platform-hero-actions');
 const catalog=heroCta(link('Explorar DDA','inicio','d-button d-button--primary'));
 const center=heroCta(link('Ir a Decision Center','platform-decisions'),'link');ctas.append(catalog,center);
 copy.append(workspace,title,el('p','Explorá los Decision Data Assets disponibles y convertí tus datos en decisiones trazables.','d-page-description'),ctas);
 const art=el('img',undefined,'platform-home__hero-art');art.src='/static/assets/workspace-home-hero.svg';art.alt='';art.width=420;art.height=280;header.append(copy,art);
 const content=el('div',undefined,'platform-home__content');root.replaceChildren(header,content);
 function renderHeader(){const identity=getIdentity();workspace.textContent=identity.workspace.name;title.textContent=greeting(identity);}
 function render(data){
  const identity=getIdentity(),grid=el('div',undefined,'platform-home__grid'),main=el('div',undefined,'platform-home__main'),side=el('div',undefined,'platform-home__side');
  if(data.attention.items.length){
   const attention=section('Requiere tu atención','home-attention-title','alertTriangle');attention.classList.add('platform-home__attention');
   const total=data.attention.total;attention.append(el('p',total===1?'1 elemento requiere una acción.':`${total} elementos requieren una acción.`,'d-body'));
   const list=el('ul',undefined,'platform-home__reviews');
   for(const item of data.attention.items){
    const row=el('li'),copy=el('div',undefined,'platform-home__review-copy'),name=nodeLabel(item),handoff=item.kind==='handoff',id=contextLabel(item);
    copy.append(el('strong',name),el('span',id,'d-metadata'),badge(handoff?'available':'review',handoff?'Listo para continuar':'En revisión'));
    if(item.is_demo)copy.append(demoBadge());
    const a=link(handoff?'Continuar':'Revisar',handoff?'logistics-config':'decision-dashboard','d-button d-button--secondary',{caseId:item.case_id,nodeId:item.node_id,runId:item.run_id});
    a.setAttribute('aria-label',`${handoff?'Continuar':'Revisar'} ${name} · ${id}`);
    row.append(icon(DECISION_META[item.node_id]?.icon||'link'),copy,a);list.append(row);
   }
   attention.append(list);if(total>data.attention.items.length)attention.append(el('p',`Mostrando ${data.attention.items.length} de ${total}.`,'d-metadata'));main.append(attention);
  }
  const recent=section('Continuar trabajando','home-recent-title','history');
  recent.querySelector('.platform-home__section-head').append(link('Ver todas','platform-decisions','platform-home__text-link'));
  if(data.recent_cases.length){
   recent.append(el('p','Tus decisiones recientes, listas para continuar.','d-body'));const list=el('ul',undefined,'platform-home__cases');
   for(const item of data.recent_cases.slice(0,3)){
    const row=el('li',undefined,'platform-home__case'),context=caseContext(item),id=contextLabel(item),tag=el('div',undefined,'platform-home__case-tags');
    tag.append(el('span',DDA_CATALOG.find(d=>d.id===context.dda)?.title||item.dda||'Decision Data Asset','platform-home__dda'));if(item.is_demo)tag.append(demoBadge());
    row.append(tag,el('h3',item.label||'Decision Case','platform-home__case-title'),el('p',id,'d-metadata'));
    const meta=el('div',undefined,'platform-home__case-meta');meta.append(el('span',nodeLabel(item)),badge(item.status));
    const time=el('time','Última actividad · '+workspaceRelativeDate(item.last_activity_at,identity.workspace),'d-metadata');time.dateTime=item.last_activity_at;time.title=workspaceDate(item.last_activity_at,identity.workspace);meta.append(time);
    if(item.approval_current&&['review','running','error'].includes(item.status))meta.append(el('p','La aprobación vigente se conserva. La nueva corrida está disponible en atención o en Decision Center.','d-metadata'));
    const target=item.resume||{view:'logistics-map',node_id:item.node_id,run_id:null},label=item.status==='completed'?'Ver resultado':'Continuar';
    const next=link(label,target.view,'d-button d-button--secondary',{caseId:item.case_id,nodeId:target.node_id,runId:target.run_id});next.setAttribute('aria-label',`${label} ${id}`);next.append(icon('arrowRight'));row.append(meta,next);list.append(row);
   }
   recent.append(list);
  }else{
   const empty=el('div',undefined,'platform-home__empty');empty.append(el('p','Todavía no tenés decisiones en curso.','d-body'),link('Explorar DDAs','inicio','platform-home__text-link'));recent.append(empty);
  }
  main.append(recent);
  const quick=section('Accesos rápidos','home-actions-title','layoutDashboard'),links=el('ul',undefined,'platform-home__quick');
  for(const [text,view,copy,iconName] of [['Explorar Decision Data Assets','inicio','Descubrí los DDAs disponibles.','database'],['Decision Center','platform-decisions','Visualizá y gestioná tus decisiones.','link'],['Mis datos','platform-data','Consultá las fuentes de datos del Workspace.','folderOpen']]){
   const row=el('li'),a=link(undefined,view,'platform-home__quick-link'),textBlock=el('span',undefined,'platform-home__quick-copy');textBlock.append(el('strong',text),el('span',copy,'d-metadata'));a.append(icon(iconName),textBlock,icon('chevronRight'));row.append(a);links.append(row);
  }
  quick.append(links);side.append(quick);
  const activity=section('Actividad reciente','home-activity-title','history'),feed=el('div');activity.append(feed);side.append(activity);grid.append(main,side);content.replaceChildren(grid);activityView=mountActivity(feed,{getIdentity,initial:data.activity,limit:5,compact:true,presentation:'home'});
 }
 function loading(){
  const pending=el('div',undefined,'platform-home__loading'),status=el('p','Cargando tu workspace…','d-body');status.role='status';pending.append(status);
  const grid=el('div',undefined,'platform-home__grid'),main=el('div',undefined,'platform-home__main'),side=el('div',undefined,'platform-home__side');
  for(const [parent,count] of [[main,2],[side,2]])for(let i=0;i<count;i++){const block=el('div',undefined,'d-card platform-home__skeleton');block.setAttribute('aria-hidden','true');for(let j=0;j<3;j++)block.append(el('span'));parent.append(block);}grid.append(main,side);pending.append(grid);content.replaceChildren(pending);
 }
 async function load(){
  activityView?.dispose();activityView=null;controller?.abort();controller=new AbortController();const ownController=controller,version=++generation;
  renderHeader();content.setAttribute('aria-busy','true');loading();
  try{
   const data=await api('/api/platform/home',{signal:ownController.signal,cache:'no-store'});if(version!==generation||ownController.signal.aborted)return;render(data);
  }catch(error){
   if(version!==generation||ownController.signal.aborted)return;
   const panel=section('No se pudo cargar el inicio','home-error-title','info'),message=el('p','No pudimos recuperar la actividad de tu Workspace.','d-body');message.role='alert';
   const retry=el('button','Reintentar','d-button d-button--secondary');retry.type='button';retry.dataset.homeRetry='';panel.append(message,el('p',describeFailure(error).message,'d-metadata'),retry);content.replaceChildren(panel);
  }finally{if(version===generation)content.removeAttribute('aria-busy');}
 }
 function stop(){activityView?.dispose();activityView=null;generation++;controller?.abort();content.removeAttribute('aria-busy');}
 function onView(){if(window.dationGetCurrentView?.()==='platform-home')load();else stop();}
 scope.listen(root,'click',event=>{
  if(event.target.closest('[data-home-retry]')){load();return;}
  const a=event.target.closest('a[data-home-resource]');if(!a||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
  const route=readResource(a.href);event.preventDefault();
  if(route.runId)window.DationDispatch.openRun(route.runId,route.nodeId,route.caseId);
  else if(route.caseId)window.DationDispatch.openCase(route.caseId,route.view,route.nodeId);
  else window.dationNavigate(route.view);
 });
 scope.listen(window,'dation:view',onView);
 scope.listen(window,'dation:identity',()=>{renderHeader();const next=identityKey();if(next!==currentIdentityKey){currentIdentityKey=next;onView();}});
 scope.listen(window,'pagehide',stop);onView();
 return {dispose(){stop();scope.dispose();}};
}
