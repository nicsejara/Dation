// Product definitions shared with the backend and other platform surfaces.
import {FOUNDATION} from './foundation.mjs';
export const DDA_CATEGORIES=FOUNDATION.categories;
export const DDA_CATALOG=FOUNDATION.ddas;

export function focusDdaCatalog(){
 const heading=document.getElementById('dation-dda-title');
 if(!heading)return;
 heading.tabIndex=-1;heading.focus({preventScroll:true});
 heading.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
}
export async function openDdaCatalog(){
 await window.dationNavigate('platform-home');
 if(window.dationGetCurrentView?.()==='platform-home')focusDdaCatalog();
}
