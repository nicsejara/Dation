import {createScope,trapFocus} from '../dispatch/lifecycle.mjs';
import {iconSvg} from '../dispatch/decision-ui.mjs';

/** Shared hero CTA presentation; callers retain their existing navigation. */
export function heroCta(node,iconName='database'){
  node.classList.add('platform-hero-cta');
  const icon=document.createElement('span');icon.className='platform-hero-cta__icon';icon.setAttribute('aria-hidden','true');icon.innerHTML=iconSvg(iconName);node.prepend(icon);
  return node;
}

let nextId=0;
const focusableSelector='button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex="0"]';
const menuItemSelector='[role="menuitem"],[role="menuitemcheckbox"],[role="menuitemradio"]';
const enabled=node=>!node.matches(':disabled,[aria-disabled="true"]');
const visible=node=>!node.hidden&&node.getClientRects().length>0;
const restoreAttribute=(node,name,value)=>value===null?node.removeAttribute(name):node.setAttribute(name,value);
const focusSafely=node=>{if(node?.isConnected&&enabled(node))node.focus({preventScroll:true});};

/**
 * Mount a caller-rendered dropdown. A role=menu panel additionally receives the
 * menu keyboard contract; generic popovers keep their native Tab order.
 * Caller owns labels, menuitem roles, actions and disabled state.
 */
export function mountDropdown({trigger,panel,closeOnSelect=true}){
  if(!trigger||!panel)throw new TypeError('Dropdown requires a trigger and a panel.');
  const scope=createScope(panel),doc=panel.ownerDocument,win=doc.defaultView;
  const original={id:panel.getAttribute('id'),controls:trigger.getAttribute('aria-controls'),haspopup:trigger.getAttribute('aria-haspopup'),style:panel.getAttribute('style')};
  const tabIndexes=new Map();
  let opened=false;
  if(!panel.id)panel.id=`d-platform-dropdown-${++nextId}`;
  trigger.setAttribute('aria-controls',panel.id);
  const popupRole=panel.getAttribute('role');
  if(['menu','listbox','tree','grid','dialog'].includes(popupRole))trigger.setAttribute('aria-haspopup',popupRole);
  else trigger.removeAttribute('aria-haspopup');
  trigger.setAttribute('aria-expanded','false');
  panel.hidden=true;

  const isMenu=()=>panel.getAttribute('role')==='menu';
  const items=()=>[...panel.querySelectorAll(menuItemSelector)].filter(node=>node.closest('[role="menu"]')===panel&&enabled(node)&&visible(node));
  const focusItem=item=>{
    for(const node of items()){
      if(!tabIndexes.has(node))tabIndexes.set(node,node.getAttribute('tabindex'));
      node.tabIndex=node===item?0:-1;
    }
    focusSafely(item);
  };
  const position=()=>{
    if(!opened)return;
    const viewportWidth=doc.documentElement.clientWidth,viewportHeight=win.innerHeight;
    const triggerRect=trigger.getBoundingClientRect(),gap=8;
    panel.style.position='fixed';panel.style.inset='auto';panel.style.left='0px';panel.style.top='0px';
    panel.style.maxHeight=`${Math.max(0,viewportHeight-gap*2)}px`;
    const rect=panel.getBoundingClientRect();
    const below=viewportHeight-triggerRect.bottom-gap,above=triggerRect.top-gap;
    const placeBelow=rect.height<=below||below>=above;
    const available=Math.max(0,(placeBelow?below:above)-gap);
    panel.style.maxHeight=`${available}px`;
    const height=Math.min(rect.height,available);
    panel.style.left=`${Math.max(gap,Math.min(triggerRect.right-rect.width,viewportWidth-rect.width-gap))}px`;
    panel.style.top=`${Math.max(gap,Math.min(placeBelow?triggerRect.bottom+gap:triggerRect.top-gap-height,viewportHeight-height-gap))}px`;
  };
  const open=({focus='first'}={})=>{
    if(!scope.active||!enabled(trigger))return false;
    opened=true;panel.hidden=false;trigger.setAttribute('aria-expanded','true');position();
    if(isMenu()&&focus)focusItem(focus==='last'?items().at(-1):items()[0]);
    return true;
  };
  const close=({restoreFocus=true}={})=>{
    if(!opened)return;
    opened=false;panel.hidden=true;trigger.setAttribute('aria-expanded','false');
    if(restoreFocus)focusSafely(trigger);
  };
  const toggle=()=>opened?close():open();
  scope.listen(trigger,'click',event=>{event.preventDefault();toggle();});
  scope.listen(trigger,'keydown',event=>{
    if(isMenu()&&['ArrowDown','ArrowUp'].includes(event.key)){
      event.preventDefault();open({focus:event.key==='ArrowUp'?'last':'first'});
    }
  });
  scope.listen(panel,'keydown',event=>{
    if(!opened||!isMenu())return;
    if(event.key==='Tab'){
      scope.timeout(()=>close({restoreFocus:false}),0);return;
    }
    if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){
      const nodes=items();if(!nodes.length)return;
      event.preventDefault();
      const current=nodes.indexOf(doc.activeElement);
      const index=event.key==='Home'?0:event.key==='End'?nodes.length-1:event.key==='ArrowDown'?(current+1)%nodes.length:(current<=0?nodes.length:current)-1;
      focusItem(nodes[index]);
    }
  });
  scope.listen(doc,'keydown',event=>{
    if(opened&&event.key==='Escape'){
      event.preventDefault();event.stopPropagation();close();
    }
  });
  scope.listen(doc,'pointerdown',event=>{
    if(opened&&!panel.contains(event.target)&&!trigger.contains(event.target))close({restoreFocus:false});
  });
  scope.listen(doc,'focusin',event=>{
    if(opened&&!panel.contains(event.target)&&!trigger.contains(event.target))close({restoreFocus:false});
  });
  scope.listen(panel,'click',event=>{
    const item=event.target.closest(menuItemSelector);
    if(item&&panel.contains(item)&&!enabled(item)){event.preventDefault();event.stopPropagation();}
  },true);
  scope.listen(panel,'click',event=>{
    const item=event.target.closest(isMenu()?menuItemSelector:'button,a[href]');
    if(!item||!panel.contains(item))return;
    if(!enabled(item)){event.preventDefault();event.stopPropagation();return;}
    if(closeOnSelect)close();
  });
  scope.listen(win,'resize',position);
  scope.listen(doc,'scroll',position,true);
  scope.own(()=>{
    close({restoreFocus:false});
    for(const [node,index] of tabIndexes)restoreAttribute(node,'tabindex',index);
    restoreAttribute(panel,'id',original.id);restoreAttribute(panel,'style',original.style);
    restoreAttribute(trigger,'aria-controls',original.controls);restoreAttribute(trigger,'aria-haspopup',original.haspopup);
  });
  return {open,close,toggle,dispose:()=>scope.dispose(),get isOpen(){return opened;}};
}

/**
 * Mount a native <dialog>, shared by modal and drawer presentation. The caller
 * supplies aria-labelledby/aria-label, content and business actions. Navigation
 * and lifecycle disposal never submit forms or execute caller actions.
 */
export function mountDialog({dialog,trigger,initialFocus,closeSelector='[data-dialog-close]',closeOnBackdrop=false}){
  if(!dialog||typeof dialog.showModal!=='function')throw new TypeError('Dialog requires a native dialog element.');
  const scope=createScope(dialog),doc=dialog.ownerDocument;
  const originalTabIndex=dialog.getAttribute('tabindex');
  let returnFocus=null;
  const restoreFocus=()=>{focusSafely(returnFocus);returnFocus=null;};
  const open=()=>{
    if(!scope.active||dialog.open||trigger&&!enabled(trigger))return false;
    returnFocus=doc.activeElement===doc.body?(trigger||doc.activeElement):doc.activeElement;
    dialog.showModal();
    const target=typeof initialFocus==='string'?dialog.querySelector(initialFocus):initialFocus;
    if(target&&dialog.contains(target))focusSafely(target);
    else if(!dialog.contains(doc.activeElement)){
      const first=[...dialog.querySelectorAll(focusableSelector)].find(node=>enabled(node)&&visible(node));
      if(first)focusSafely(first);
      else {dialog.tabIndex=-1;focusSafely(dialog);}
    }
    return true;
  };
  const close=(returnValue='')=>{if(dialog.open)dialog.close(returnValue);};
  if(trigger)scope.listen(trigger,'click',event=>{event.preventDefault();open();});
  scope.listen(dialog,'keydown',event=>trapFocus(event,dialog));
  scope.listen(dialog,'cancel',event=>{
    if(event.defaultPrevented)return;
    event.preventDefault();close();
  });
  scope.listen(dialog,'close',restoreFocus);
  scope.listen(dialog,'click',event=>{
    const button=closeSelector?event.target.closest(closeSelector):null;
    if(button&&dialog.contains(button)&&enabled(button)){event.preventDefault();close(button.value||'');return;}
    if(closeOnBackdrop&&event.target===dialog){
      const rect=dialog.getBoundingClientRect();
      if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)close();
    }
  });
  scope.own(()=>{
    close();restoreFocus();restoreAttribute(dialog,'tabindex',originalTabIndex);
  });
  return {open,close,dispose:()=>scope.dispose(),get isOpen(){return dialog.open;}};
}

/** Shared loading geometry; the caller retains request, abort and stale-response ownership. */
export function loadingState(label,{rows=4}={}){
 const block=document.createElement('div');block.className='d-loading';block.role='status';
 const text=document.createElement('span');text.className='d-metadata';text.textContent=label;block.append(text);
 for(let i=0;i<rows;i++){const row=document.createElement('div');row.className='d-skeleton';row.setAttribute('aria-hidden','true');block.append(row);}
 return block;
}

/** Initials are presentation only; preserve multi-codepoint names and emoji. */
export function personInitials(...parts){
 const words=parts.flatMap(value=>String(value||'').trim().split(/\s+/)).filter(Boolean);
 const selected=words.length>1?[words[0],words.at(-1)]:words;
 const segmenter=typeof Intl.Segmenter==='function'?new Intl.Segmenter(undefined,{granularity:'grapheme'}):null;
 return selected.map(word=>segmenter?[...segmenter.segment(word)][0].segment:Array.from(word)[0]).join('').toLocaleUpperCase()||'—';
}
