import {scopeFor} from './lifecycle.mjs';

/** Shared D1/D2 disclosure lifecycle; feature shells own their markup/content. */
export function bindDashboardPresentation(root,{advanced,toggle,content,label,storageKey,onAdvancedOpen}){
  const scope=scopeFor(root);
  let open=false;
  function setAdvanced(value,{target,scroll=false}={}){
    const previous=open;
    open=Boolean(value);
    root.dataset.visualDepth=open?'advanced':'essential';
    toggle.setAttribute('aria-expanded',String(open));
    content.hidden=!open;
    advanced.classList.toggle('is-open',open);
    label.textContent=open?'Ocultar análisis avanzado':'Mostrar análisis avanzado';
    try{sessionStorage.setItem(storageKey,open?'advanced':'essential');}catch{}
    if(open&&!previous)onAdvancedOpen?.();
    if(open&&scroll)scope.timeout(()=>{
      const node=typeof target==='string'?content.querySelector(target):target;
      (node||advanced).scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
      node?.focus({preventScroll:true});
    },0);
  }
  scope.listen(toggle,'click',()=>setAdvanced(!open));
  let restored=false;
  try{restored=sessionStorage.getItem(storageKey)==='advanced';}catch{}
  setAdvanced(restored);
  return {openAdvanced:target=>setAdvanced(true,{target,scroll:true})};
}
