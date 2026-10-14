/** Shared stylesheet identity, readiness and retry; no duplicate link nodes. */
const pendingStyles=new WeakMap();
const failedStyles=new WeakSet();
export function ensureStylesheet(id,path,version="dark-dashboard-phase5-v1"){
  const existing=[...document.querySelectorAll('link[rel="stylesheet"]')].find(link=>new URL(link.href,location.href).pathname===path);
  if(existing&&failedStyles.has(existing)){
    existing.remove();
    return ensureStylesheet(id,path,version);
  }
  const href=new URL(path+'?v='+version,location.href).href;
  if(existing?.href===href&&existing.sheet&&!failedStyles.has(existing))return Promise.resolve();
  const link=existing||document.createElement('link');
  const pending=pendingStyles.get(link);
  if(pending?.href===href)return pending.promise;
  const promise=new Promise((resolve,reject)=>{
    const cleanup=()=>{link.removeEventListener('load',loaded);link.removeEventListener('error',failed);pendingStyles.delete(link);};
    const loaded=()=>{cleanup();failedStyles.delete(link);resolve();};
    const failed=()=>{cleanup();failedStyles.add(link);reject(new Error('No pudimos cargar los estilos de esta vista. Reintentá.'));};
    link.addEventListener('load',loaded);link.addEventListener('error',failed);
    if(!existing){link.id=id;link.rel='stylesheet';}
    // A settled failed link must issue a new request when the user retries.
    link.href=href;
    if(!existing)document.head.append(link);
  });
  pendingStyles.set(link,{href,promise});
  return promise;
}
