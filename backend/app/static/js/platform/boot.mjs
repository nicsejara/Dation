// Load existing DDA modules once, after identity and tab caches are isolated.
async function start(){
 try{await window.dationSession.ready;}catch{return;}
 const {syncEntitlementFallback,ddaEnabled}=await import('./entitlements.mjs');
 window.dationDdaEnabled=id=>ddaEnabled(window.dationSession.identity,id);syncEntitlementFallback();
 window.addEventListener('dation:identity',syncEntitlementFallback);
 for(const element of document.querySelector('#dation-app-scripts').content.querySelectorAll('script')){
  if(element.type==='module')continue;
  await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=element.src;script.onload=resolve;script.onerror=()=>reject(new Error('No se pudo cargar la aplicación.'));document.body.append(script);});
 }
 await import('../dispatch/workspace.mjs');
 try{await import('../app.js');}catch{const notice=document.querySelector('#toast');if(notice){notice.textContent='Algunas vistas no pudieron cargarse. Podés continuar o recargar la página.';notice.classList.add('is-visible');}}
 const {mountPlatformShell}=await import('./shell.mjs');mountPlatformShell();
 document.documentElement.classList.remove('d-session-loading');
}
start().catch(()=>{document.documentElement.classList.remove('d-session-loading');document.querySelector('.app-shell').hidden=true;const p=document.createElement('p');p.textContent='No se pudo cargar la aplicación. Recargá la página para reintentar.';document.body.append(p);});
