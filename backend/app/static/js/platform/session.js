/* The only owner of the browser access token. Refresh tokens remain HttpOnly. */
(function(){
 'use strict';
 const nativeFetch=window.fetch.bind(window);let session=null,pending=null,owner=null;
 const channel=typeof BroadcastChannel==='function'?new BroadcastChannel('dation-session'):null;
 function clearPrivateState(){for(const store of [sessionStorage,localStorage]){for(const key of Object.keys(store)){if(key.startsWith('dation.'))store.removeItem(key);}}}
 async function load(){
  const response=await nativeFetch('/auth/session',{method:'POST',credentials:'same-origin'});
  const body=await response.json();
  if(!response.ok){if(response.status===401)location.replace('/login');throw Object.assign(new Error(body.detail||'No se pudo resolver tu acceso.'),{status:response.status});}
  if(!body.membership){location.replace('/workspace-setup');throw new Error('Configurá tu workspace para continuar.');}
  const next=body.profile.id+':'+body.membership.workspace_id;
  if(owner&&owner!==next){clearPrivateState();location.replace('/app');throw new Error('La sesión cambió.');}
  if(sessionStorage.getItem('_dation_identity')!==next){clearPrivateState();sessionStorage.setItem('_dation_identity',next);}
  owner=next;session=body;return body;
 }
 async function refresh(){if(!pending)pending=load().finally(()=>{pending=null;});return pending;}
 const ready=refresh();
 window.fetch=async function(input,options={}){
  const url=new URL(typeof input==='string'?input:input.url,location.href);
  if(url.origin!==location.origin||!url.pathname.startsWith('/api/'))return nativeFetch(input,options);
  await ready;
  if(Date.now()/1000>=session.expires_at-30)await refresh();
  const headers=new Headers(options.headers||(input instanceof Request?input.headers:undefined));headers.set('Authorization','Bearer '+session.access_token);
  const response=await nativeFetch(input,{...options,headers,credentials:'same-origin'});
  // A failed mutation is never replayed implicitly. Let the user retry deliberately.
  if(response.status===401){await refresh();}
  return response;
 };
 async function logout(){
  const response=await nativeFetch('/auth/logout',{method:'POST',credentials:'same-origin'});
  if(!response.ok)throw new Error('No se pudo cerrar la sesión. Reintentá.');
  clearPrivateState();session=null;channel?.postMessage('logout');location.replace('/login');
 }
 channel?.addEventListener('message',event=>{if(event.data==='logout'){clearPrivateState();location.replace('/login');}});
 window.dationSession=Object.freeze({ready,refresh,logout,get identity(){return session;}});
 window.addEventListener('pagehide',()=>document.documentElement.classList.add('d-session-loading'));
 window.addEventListener('pageshow',event=>{if(event.persisted)refresh().then(()=>document.documentElement.classList.remove('d-session-loading')).catch(()=>{});});
 ready.catch(error=>{
  if(error.status===401)return;
  document.documentElement.classList.remove('d-session-loading');
  const shell=document.querySelector('.app-shell');if(shell)shell.hidden=true;
  const panel=document.createElement('main');panel.className='d-platform d-auth';
  const card=document.createElement('section');card.className='d-card d-auth__card';
  const title=document.createElement('h1');title.textContent='No se pudo abrir el workspace';
  const text=document.createElement('p');text.textContent=error.message;
  const retry=document.createElement('button');retry.className='d-button d-button--primary';retry.textContent='Reintentar';retry.onclick=()=>location.reload();
  const exit=document.createElement('button');exit.className='d-button d-button--secondary';exit.textContent='Cerrar sesión';exit.onclick=()=>logout().catch(exc=>{text.textContent=exc.message;});
  card.append(title,text,retry,exit);panel.append(card);document.body.append(panel);
 });
})();
