// R5 presentation only: no catalog mutation, network services or physical math.
import {el} from './forms.mjs';
import {supportArt} from './guided-ui.mjs';
import {volumeNumber,volumeText} from './cargo-presentation-values.mjs';
export {volumeText};
import {wizardIcon} from './wizard-ui.mjs';
export const UNIT_ART=Object.freeze(Object.fromEntries(['PALLET','BOX','CRATE','BIG_BAG','OTHER'].map(type=>[type,Object.freeze({empty:'/static/img/logistics/r6/'+type.toLowerCase()+'-empty.webp',loaded:'/static/img/logistics/r6/'+type.toLowerCase()+'-loaded.webp'})])));
function artFrame(resolve,fallbackFor){
 const frame=el('span',undefined,'r5-unit-art r6-unit-art'),img=el('img');img.alt='';img.width=300;img.height=335;img.decoding='async';img.loading='lazy';frame.setAttribute('aria-hidden','true');frame.append(img);let current,fallback,phase=0,url='';
 function update(next){
  if(current===next)return;current=next;fallback?.remove();fallback=null;phase=0;img.hidden=false;url=resolve(next);frame.dataset.artFallback='false';
  if(url)img.src=url;else{img.hidden=true;fallback=fallbackFor(next);frame.append(fallback);}
 }
 img.addEventListener('error',()=>{if(fallback)return;if(phase===0){phase=1;img.src=url.replace(/\.webp$/,'.png');return;}img.hidden=true;fallback=fallbackFor(current);delete fallback.dataset.supportArt;frame.dataset.artFallback='true';frame.append(fallback);});
 return {node:frame,update};
}
export function unitArt(type,{loaded=false}={}){
 const art=artFrame(next=>UNIT_ART[next]?.[loaded?'loaded':'empty']||UNIT_ART.OTHER[loaded?'loaded':'empty'],next=>supportArt(next,{loaded}));
 const update=next=>{art.node.dataset.unitType=next;art.node.dataset.supportArt=loaded?'loaded':'empty';art.node.dataset.artState=loaded?'loaded':'empty';art.node.dataset.artContext='unit';art.update(next);};update(type);return {node:art.node,update};
}
export function bultoArt(packageType){
 const art=artFrame(next=>next==='caja'?'/static/img/logistics/r6/caja-individual.webp':null,()=>wizardIcon('box'));
 const update=next=>{art.node.dataset.packageType=next;art.node.dataset.supportArt='individual';art.node.dataset.artState='individual';art.node.dataset.artContext=next==='caja'?'package':'neutral';art.update(next);};update(packageType);return {node:art.node,update};
}
export function sectionHeading(parent,title,copy){const heading=el('div',undefined,'r5-section-heading');heading.append(el('h5',title,'r6-section-title'),el('p',copy,'d-field__help'));parent.append(heading);return heading;}
export function volumeCard(label,copy){
 const card=el('output',undefined,'r5-volume-card'),icon=wizardIcon('box'),caption=el('span',label,'r5-volume-label'),reading=el('span',undefined,'r5-volume-reading'),value=el('strong'),unit=el('span','m³','r5-volume-unit'),help=el('span',copy,'r5-volume-help');
 const id='r5-volume-'+crypto.randomUUID();caption.id=id;card.setAttribute('aria-labelledby',id);card.setAttribute('aria-live','off');reading.append(value,document.createTextNode(' '),unit);card.append(icon,caption,reading,help);
 return {node:card,update(number,explanation=copy){const pending=number===null||number===undefined;card.dataset.pending=String(pending);card.dataset.value=pending?'':String(number);value.textContent=pending?'Pendiente de completar':volumeNumber(number);unit.hidden=pending;help.textContent=explanation;}};
}
