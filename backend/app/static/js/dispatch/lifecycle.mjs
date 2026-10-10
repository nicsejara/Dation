const scopes=new WeakMap();
export function scopeFor(root){for(let node=root;node;node=node.parentElement){const scope=scopes.get(node);if(scope)return scope;}return null;}
export function disposeScope(root){scopes.get(root)?.dispose();}
export function createScope(root){
  disposeScope(root);
  const controller=new AbortController(),cleanups=new Set();
  const scope={
    get active(){return !controller.signal.aborted;},signal:controller.signal,
    own(cleanup){if(scope.active)cleanups.add(cleanup);else cleanup();return ()=>cleanups.delete(cleanup);},
    listen(target,type,handler,options){target.addEventListener(type,handler,options);scope.own(()=>target.removeEventListener(type,handler,options));},
    timeout(callback,ms){let release;const id=setTimeout(()=>{release();if(scope.active)callback();},ms);release=scope.own(()=>clearTimeout(id));return id;},
    observe(observer,target,options){observer.observe(target,options);scope.own(()=>observer.disconnect());return observer;},
    dispose(){if(!scope.active)return;controller.abort();for(const fn of [...cleanups].reverse()){try{fn();}catch(error){console.error('Resource cleanup failed',error);}}cleanups.clear();if(scopes.get(root)===scope)scopes.delete(root);},
  };
  scopes.set(root,scope);scopeFor(root.parentElement)?.own(()=>scope.dispose());return scope;
}
export function trapFocus(event,dialog){
  if(event.key!=='Tab')return;
  const items=[...dialog.querySelectorAll('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex="0"]')].filter(node=>node.getClientRects().length);
  if(!items.length){event.preventDefault();dialog.focus();return;}
  const first=items[0],last=items.at(-1);
  if(event.shiftKey&&(document.activeElement===first||!dialog.contains(document.activeElement))){event.preventDefault();last.focus();}
  else if(!event.shiftKey&&(document.activeElement===last||!dialog.contains(document.activeElement))){event.preventDefault();first.focus();}
}
