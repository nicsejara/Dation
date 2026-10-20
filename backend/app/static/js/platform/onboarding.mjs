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

export function trackExploration(getIdentity){
 const root=document.createElement('div'),scope=createScope(root);let done=false,pending=false,controller;
 async function visit(){if(done||pending||!['inicio','logistics-overview'].includes(window.dationGetCurrentView?.()))return;
  pending=true;controller=new AbortController();try{const saved=await api('/api/platform/onboarding',{signal:controller.signal});if(!saved.available)return;if(saved.explored_at){done=true;return;}await post('/api/platform/onboarding/explore',{}, {signal:controller.signal});if(scope.active){done=true;window.dispatchEvent(new CustomEvent('dation:onboarding'));}}catch{}finally{pending=false;}
 }
 scope.listen(window,'dation:view',visit);scope.listen(window,'pagehide',()=>controller?.abort());visit();
 return {dispose(){controller?.abort();scope.dispose();}};
}
