import {el} from './forms.mjs';
import {wizardIcon} from './wizard-ui.mjs';

// Presentation helpers only. They never alter configuration or certify physics.
export function statusCircle(node,label,state='pending'){
 node.className='guided-status';node.dataset.state=state;
 node.textContent=state==='complete'?'✓':state==='error'?'!':'';
 node.setAttribute('role','img');node.setAttribute('aria-label',label);node.title=label;
}
export function guidedBlock(parent,index,title,copy,icon,{open=false}={}){
 const details=el('details',undefined,'d-card ultimate-disclosure model-v2-block'),summary=el('summary',undefined,'ultimate-disclosure__summary');
 const tile=el('span',undefined,'guided-icon-tile'),heading=el('span',undefined,'guided-heading'),status=el('span'),chevron=el('span',undefined,'ultimate-disclosure__chevron');
 tile.append(wizardIcon(icon));heading.append(el('span',String(index).padStart(2,'0')+'. '+title,'ultimate-disclosure__title'),el('span',copy,'guided-description'));
 statusCircle(status,title+': pendiente de revisión');chevron.setAttribute('aria-hidden','true');
 summary.append(tile,heading,status,chevron);
 const content=el('div',undefined,'ultimate-disclosure__content'),body=el('div',undefined,'ultimate-grid');content.append(body);details.append(summary,content);details.open=open;parent.append(details);
 details.dataset.dationTest='model-v2-block-'+index;
 return {details,body,setStatus(label,state){statusCircle(status,title+': '+label,state);}};
}
export function guidedStep(parent,index,title,copy,{open=false}={}){
 const details=el('details',undefined,'guided-step'),summary=el('summary'),number=el('span',String(index),'guided-step-number'),heading=el('span',undefined,'guided-heading'),status=el('span'),chevron=el('span',undefined,'ultimate-disclosure__chevron');
 heading.append(el('strong','Paso '+index+' · '+title),el('span',copy,'guided-description'));
 statusCircle(status,title+': pendiente de revisión');chevron.setAttribute('aria-hidden','true');summary.append(number,heading,status,chevron);
 const body=el('div',undefined,'guided-step-body');details.append(summary,body);details.open=open;details.dataset.cargoStep=String(index);parent.append(details);
 return {details,body,status,setStatus(label,state){statusCircle(status,title+': '+label,state);}};
}
export function radioCards(parent,title,name,options,value){
 const group=el('fieldset',undefined,'guided-radio-group');group.append(el('legend',title,'d-field__label'));
 const grid=el('div',undefined,'guided-radio-grid');group.append(grid);
 for(const [key,label,copy,icon]of options){
  const card=el('label',undefined,'guided-radio-card'),input=el('input'),text=el('span',undefined,'guided-heading'),mark=el('span',undefined,'guided-radio-mark');
  input.type='radio';input.name=name;input.value=key;input.checked=value===key;input.required=true;input.id='guided-'+name+'-'+key;
  text.append(el('strong',label),el('span',copy,'guided-description'));mark.setAttribute('aria-hidden','true');
  card.append(input,wizardIcon(icon),text,mark);grid.append(card);
 }
 parent.append(group);
 return {root:group,get value(){return group.querySelector('input:checked')?.value||'';},set value(v){for(const n of group.querySelectorAll('input'))n.checked=n.value===v;}};
}
export function note(parent,text){const n=el('p',undefined,'guided-note');n.append(wizardIcon('info'),el('span',text));parent.append(n);return n;}
export function readout(parent,label,value,origin=''){
 const row=el('div',undefined,'guided-readout');row.append(el('dt',label),el('dd',value??'Sin declarar'));
 if(origin)row.lastChild.append(el('small',origin,'guided-origin'));parent.append(row);return row;
}
export function display(value,unit='',digits=3){
 if(value===null||value===undefined||value==='')return 'Sin declarar';
 const number=Number(value);if(!Number.isFinite(number))return 'Pendiente';
 return new Intl.NumberFormat('es-AR',{maximumFractionDigits:digits}).format(number)+(unit?' '+unit:'');
}
export function palletArt(){
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 220 170');svg.setAttribute('aria-hidden','true');svg.classList.add('guided-pallet-art');
 // Fixed decorative illustration. Its box positions never imply packing.
 svg.innerHTML='<ellipse cx="110" cy="153" rx="91" ry="12" fill="#9a7045" opacity=".12"/><path d="m22 123 85-39 91 41-84 39Z" fill="#c48a4b"/><path d="m22 123 92 40v-13l-92-40Z" fill="#ac703c"/><path d="m114 150 84-39v14l-84 39Z" fill="#946031"/><path d="m36 116 85 39m-58-52 85 39m-57-52 85 39" stroke="#e6ba79" stroke-width="7"/><path d="m38 64 67-31 72 33-67 32Z" fill="#eac68c"/><path d="m38 64 72 34v48l-72-34Z" fill="#ce9c61"/><path d="m110 98 67-32v48l-67 32Z" fill="#b88048"/><path d="m60 54 71 34m-49-44 72 34M63 77v46m24-34v46m47-49v47m23-58v46" stroke="#f8dcac" stroke-width="2"/><path d="m53 105 14 7m58 15 15-7" stroke="#895b31" stroke-width="2"/>';
 return svg;
}
