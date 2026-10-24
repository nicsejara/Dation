import {createScope} from '../dispatch/lifecycle.mjs';
import {readResource,resourceUrl} from '../dispatch/navigation/resource.mjs';
import {focusDdaCatalog} from './dda-catalog.mjs';
import {iconSvg} from '../dispatch/decision-ui.mjs';
import {heroCta} from './components.mjs';

function el(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;}
function icon(name){const n=el('span',undefined,'platform-home__icon');n.setAttribute('aria-hidden','true');n.innerHTML=iconSvg(name);return n;}
function link(text,view,className='d-button d-button--secondary'){
 const a=el('a',text,className);a.href=resourceUrl(location.href,{view});a.dataset.homeResource='';return a;
}
function greeting(identity){
 let hour;try{hour=Number(new Intl.DateTimeFormat('en',{hour:'numeric',hourCycle:'h23',timeZone:identity.workspace.timezone||'UTC'}).format(new Date()));}catch{hour=new Date().getUTCHours();}
 const hello=hour<12?'Buenos días':hour<19?'Buenas tardes':'Buenas noches';
 return hello+(identity.profile.first_name?', '+identity.profile.first_name:'');
}

export function mountWorkspaceHome(root,getIdentity){
 const scope=createScope(root);
 const header=el('header',undefined,'platform-home__header platform-entry-hero d-product-hero'),copy=el('div',undefined,'platform-home__hero-copy d-product-hero__copy');
 const salutation=el('p',undefined,'platform-home__greeting'),title=el('h1','De tus datos a decisiones que podés ','d-page-title'),ctas=el('div',undefined,'platform-home__hero-actions platform-hero-actions');
 title.append(el('span','explicar y repetir.','platform-home__emphasis'));
 const catalog=heroCta(link('Explorar DDA','platform-home','d-button d-button--primary'));
 const center=heroCta(link('Ir a Decision Center','platform-decisions'),'arrowRight');
 ctas.append(catalog,center);
 copy.append(el('p','DATION · DECISION INTELLIGENCE','platform-home__eyebrow'),salutation,title,el('p','Dation combina datos, reglas y motores de decisión para que cada análisis tenga contexto, evidencia y trazabilidad.','d-page-description'),ctas);
 const visual=el('div',undefined,'platform-home__network d-product-hero__art');visual.setAttribute('aria-hidden','true');
 const image=el('img');image.src='/static/assets/home-decision-network-placeholder.svg';image.alt='';image.width=640;image.height=480;image.decoding='async';image.loading='eager';visual.append(image);
 const chain=el('ol',undefined,'platform-home__chain d-product-hero__panel');chain.setAttribute('aria-label','Modelo de decisiones de Dation');
 for(const [label,detail] of [['Data Pack','Datos y contexto de la decisión'],['Decision Case','Objetivo, reglas y responsables'],['Decision Run','Alternativas, evidencia y aprobación']]){
  const step=el('li',undefined,'d-product-hero__step');step.append(el('strong',label,'d-product-hero__label'),el('span',detail,'d-product-hero__detail'));chain.append(step);
 }
 header.append(copy,visual,chain);
 const quick=el('section',undefined,'d-card platform-home__section platform-home__access'),heading=el('h2','Accesos rápidos','d-section-title'),links=el('ul',undefined,'platform-home__quick');
 heading.id='home-actions-title';quick.setAttribute('aria-labelledby',heading.id);
 for(const [text,view,iconName] of [['Decision Center','platform-decisions','link'],['Datos / Data Hub','platform-data','database'],['Equipo','platform-team','clipboardList'],['Configuración','settings','sliders']]){
  const row=el('li'),a=link(undefined,view,'platform-home__quick-link');a.append(icon(iconName),el('strong',text),icon('chevronRight'));row.append(a);links.append(row);
 }
 quick.append(heading,links);
 const ddaCatalog=document.querySelector('[data-home-dda-catalog]');root.replaceChildren(header,quick,...(ddaCatalog?[ddaCatalog]:[]));
 catalog.href='#dation-dda-title';catalog.removeAttribute('data-home-resource');scope.listen(catalog,'click',event=>{event.preventDefault();focusDdaCatalog();});
 function renderHeader(){const identity=getIdentity();salutation.textContent=greeting(identity);}
 scope.listen(root,'click',event=>{
  const a=event.target.closest('a[data-home-resource]');if(!a||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
  const route=readResource(a.href);event.preventDefault();window.dationNavigate(route.view);
 });
 scope.listen(window,'dation:view',()=>{if(window.dationGetCurrentView?.()==='platform-home'){renderHeader();if(location.hash==='#dation-dda-title')requestAnimationFrame(focusDdaCatalog);}});
 scope.listen(window,'dation:identity',renderHeader);renderHeader();
 if(window.dationGetCurrentView?.()==='platform-home'&&location.hash==='#dation-dda-title')requestAnimationFrame(focusDdaCatalog);
 return {dispose:()=>scope.dispose()};
}
