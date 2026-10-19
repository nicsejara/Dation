import {api,post} from '../dispatch/shared.mjs';
import {createScope} from '../dispatch/lifecycle.mjs';
import {ddaEnabled} from './entitlements.mjs';
import {describeFailure} from '../dispatch/recovery.mjs';

function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
export function demoBadge(){return el('span','Demo · datos de ejemplo','d-demo-badge');}
export function mountDemoAction(root,getIdentity){
 const scope=createScope(root);let controller,busy=false;
 root.classList.add('d-platform','d-demo-action');
 const copy=el('p','Probá el pack de ejemplo de Logística. Se guardarán Órdenes y Flota una sola vez; tu flota vigente se conserva.','d-metadata'),message=el('p');message.role='status';
 const button=el('button','Usar datos de ejemplo','d-button d-button--secondary');button.type='button';
 const allowed=getIdentity().membership.access_role!=='viewer'&&ddaEnabled(getIdentity(),'logistics');button.disabled=!allowed;
 if(!allowed)copy.textContent=getIdentity().membership.access_role==='viewer'?'Tu rol permite consultar. Un Admin u Operator puede preparar los datos de ejemplo.':'DDA Logística debe estar habilitado para usar el ejemplo.';
 root.replaceChildren(copy,button,message);
 scope.listen(button,'click',async()=>{if(busy||!allowed)return;busy=true;button.disabled=true;root.setAttribute('aria-busy','true');message.textContent='Preparando los datos de ejemplo…';controller=new AbortController();
  try{const data=await post('/api/platform/onboarding/demo',{}, {signal:controller.signal});if(!scope.active)return;
   if(!data.contains_demo_data){message.textContent='Estos archivos ya estaban en tu biblioteca. Se conservan su nombre y su origen.';const next=el('button','Continuar con datos existentes','d-button d-button--primary');next.type='button';next.onclick=()=>window.DationDispatch.reuseHubData([data.orders,data.fleet]);message.append(next);}
   else await window.DationDispatch.reuseHubData([data.orders,data.fleet]);
  }catch(error){if(!scope.active||controller.signal.aborted)return;message.role='alert';message.textContent=error.status===409?error.message:describeFailure(error).message;
   if(error.status===409){const a=el('button','Revisar biblioteca','d-button d-button--secondary');a.type='button';a.onclick=()=>window.DationDispatch.openDataHub({tab:'datasets',filter:'archived'});message.append(a);}
  }finally{if(scope.active){busy=false;button.disabled=false;root.removeAttribute('aria-busy');}}
 });
 return {dispose(){controller?.abort();scope.dispose();}};
}

export function mountWelcome(root,getIdentity,initial){
 const scope=createScope(root);let controller,demo;
 root.classList.add('d-onboarding');
 function action(text,view){const b=el('button',text,'d-button d-button--secondary');b.type='button';b.onclick=()=>window.dationNavigate(view);return b;}
 function render(data){demo?.dispose();root.replaceChildren();
  if(!data?.available){const p=el('p',data?.error||'No se pudo cargar la guía inicial.','d-body'),b=el('button','Reintentar guía','d-button d-button--secondary');p.role='status';b.type='button';b.onclick=load;root.append(p,b);return;}
  const details=el('details'),summary=el('summary',data.first_decision_completed&&data.explored_at?'Tus primeros pasos':'Bienvenido a Dation','d-card-title');details.append(summary);details.open=!(data.first_decision_completed&&data.explored_at);
  const list=el('ol',undefined,'d-onboarding__steps');
  for(const [key,text,done,view]of [['workspace','Workspace creado',data.workspace_created,null],['explore','Explorá los Decision Data Assets',!!data.explored_at,'inicio'],['data','Prepará tus datos',data.data_ready,'platform-data'],['decision','Ejecutá tu primera decisión',data.first_decision_completed,'logistics-data']]){
   const item=el('li');item.dataset.onboardingStep=key;item.dataset.complete=String(!!done);const mark=el('span',done?'✓':'○');mark.setAttribute('aria-hidden','true');item.append(mark,el('span',text),el('span',done?'Completado':'Pendiente','d-metadata'));
   if(view&&!done&&(view!=='logistics-data'||getIdentity().membership.access_role!=='viewer'&&data.logistics_enabled))item.append(action(key==='explore'?'Ver DDAs':key==='data'?'Ver datos':'Abrir Logística',view));list.append(item);
  }
  details.append(el('p','Exploración personal; datos y decisiones reflejan el avance real de tu workspace.','d-metadata'),list);
  if(data.data_includes_demo||data.first_decision_demo)details.append(el('p','El avance incluye datos o decisiones de ejemplo, identificados como Demo.','d-metadata'));
  const actions=el('div',undefined,'d-onboarding__actions');actions.append(action(data.logistics_enabled?'Explorar DDA Logística':'Explorar Decision Data Assets',data.logistics_enabled?'logistics-overview':'inicio'));details.append(actions);
  if(!data.first_decision_completed){const sample=el('div');details.append(sample);demo=mountDemoAction(sample,getIdentity);}
  if(getIdentity().membership.access_role==='viewer')details.append(el('p','Podés explorar y consultar. Para cargar datos o ejecutar, pedile acceso a un administrador.','d-body'));
  root.append(details);
 }
 async function load(){controller?.abort();controller=new AbortController();root.setAttribute('aria-busy','true');try{const data=await api('/api/platform/onboarding',{signal:controller.signal});if(scope.active)render(data);}catch(error){if(scope.active&&!controller.signal.aborted)render({error:describeFailure(error).message});}finally{if(scope.active)root.removeAttribute('aria-busy');}}
 render(initial);return {dispose(){controller?.abort();demo?.dispose();scope.dispose();}};
}

export function trackExploration(getIdentity){
 const root=document.createElement('div'),scope=createScope(root);let done=false,pending=false,controller;
 async function visit(){if(done||pending||!['inicio','logistics-overview'].includes(window.dationGetCurrentView?.()))return;
  pending=true;controller=new AbortController();try{const saved=await api('/api/platform/onboarding',{signal:controller.signal});if(!saved.available)return;if(saved.explored_at){done=true;return;}await post('/api/platform/onboarding/explore',{}, {signal:controller.signal});if(scope.active){done=true;window.dispatchEvent(new CustomEvent('dation:onboarding'));}}catch{}finally{pending=false;}
 }
 scope.listen(window,'dation:view',visit);scope.listen(window,'pagehide',()=>controller?.abort());visit();
 return {dispose(){controller?.abort();scope.dispose();}};
}
