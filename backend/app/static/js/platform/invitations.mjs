// Invitations are associated with the confirmed Auth email, never a supplied user ID.
export const ACCESS_ROLES={admin:'Admin',operator:'Operator',viewer:'Viewer'};
export const RESPONSIBILITIES={data_owner:'Data Owner',decision_owner:'Decision Owner'};
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
export function mountReceivedInvitations(root,{onCount=()=>{}}={}){
 const controller=new AbortController();let active=true;
 async function call(path){const r=await fetch(path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:'{}',signal:controller.signal});const d=await r.json();if(!r.ok)throw Object.assign(new Error(d.detail||'No se pudieron consultar las invitaciones.'),{status:r.status});return d;}
 async function load(){
  root.hidden=false;root.setAttribute('aria-busy','true');
  try{const data=await call('/auth/invitations');if(!active)return;root.replaceChildren();onCount(data.items.length);root.hidden=!data.items.length;
   if(!data.items.length)return;
   root.append(el('h2','Invitaciones recibidas','d-card-title'),el('p','Aceptá para ingresar al workspace con tu email confirmado.','d-body'));
   const list=el('ul',undefined,'team-received');
   for(const invite of data.items){const row=el('li'),copy=el('div');copy.append(el('strong',invite.workspace_name),el('p',[ACCESS_ROLES[invite.access_role],RESPONSIBILITIES[invite.business_role]].filter(Boolean).join(' · '),'d-metadata'));
    const accept=el('button','Aceptar invitación','d-button d-button--primary');accept.type='button';const message=el('p');message.role='alert';
    accept.addEventListener('click',async()=>{accept.disabled=true;message.textContent='';try{await call('/auth/invitations/'+invite.id+'/accept');if(active)location.replace('/app');}catch(error){if(active&&!controller.signal.aborted){message.textContent=error.message;accept.disabled=false;}}});
    row.append(copy,accept,message);list.append(row);
   }root.append(list);
  }catch(error){if(active&&!controller.signal.aborted){root.replaceChildren();if(error.status===401){root.hidden=true;return;}const message=el('p',error.message,'d-body');message.role='alert';const retry=el('button','Reintentar invitaciones','d-button d-button--secondary');retry.type='button';retry.addEventListener('click',load);root.append(message,retry);}}
  finally{if(active)root.removeAttribute('aria-busy');}
 }
 load();return {dispose(){active=false;controller.abort();},reload:load};
}
