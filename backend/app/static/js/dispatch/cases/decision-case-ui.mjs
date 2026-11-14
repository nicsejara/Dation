import {el} from '../models/forms.mjs';
import {wizardIcon} from '../models/wizard-ui.mjs';

export function decisionIcon(kind){
 if(['costs','resources','layers','database','check'].includes(kind))return wizardIcon(kind);
 const paths={target:['M21 12a9 9 0 1 1-9-9','M17 12a5 5 0 1 1-5-5','m12 12 9-9','M17 3h4v4'],document:['M5 3h9l5 5v13H5V3Z','M14 3v6h5','M8 13h8','M8 17h8'],flow:['M9 3h6v5H9z','M2 17h6v5H2z','M16 17h6v5h-6z','M12 8v5','M5 17v-4h14v4'],calendar:['M4 5h16v16H4z','M4 10h16','M8 3v4','M16 3v4','M8 14h3'],people:['M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z','M2 21v-3c0-4 14-4 14 0v3H2Z','M17 4a4 4 0 0 1 0 7','M19 15c2 0 3 1 3 3v3'],review:['M9 4H5v18h14V4h-4','M9 2h6v5H9z','m8 14 3 3 5-6'],medal:['m12 2 3 3 4 1-1 4 1 4-4 1-3 3-3-3-4-1 1-4-1-4 4-1 3-3Z','m8 17-1 5 5-3 5 3-1-5'],balance:['M12 3v18','M5 21h14','M3 7h18','m5 7-4 8h8L5 7Z','m19 7-4 8h8l-4-8Z'],sliders:['M3 6h18','M3 12h18','M3 18h18','M7 3v6','M16 9v6','M9 15v6']};
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','1.7');svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');svg.setAttribute('aria-hidden','true');svg.classList.add('decision-case-icon');
 for(const d of paths[kind]||paths.target){const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',d);svg.append(path);}return svg;
}
export function decisionCard(parent,title,copy,kind){
 const card=el('section',undefined,'decision-case-card'),rail=el('div',undefined,'decision-case-rail'),tile=el('span',undefined,'decision-case-tile'),text=el('div'),controls=el('div',undefined,'decision-case-controls');
 card.dataset.dationTest='case-card-'+kind;tile.append(decisionIcon(kind));text.append(el('h3',title),el('p',copy));rail.append(tile,text);card.append(rail,controls);parent.append(card);return controls;
}
export function decisionChoices(parent,{name,label,options,value,readOnly=false,required=false,icons=[],help=[]}){
 const group=el('fieldset',undefined,'decision-case-choices'),legend=el('legend',label,'d-field__label');legend.id='ultimate-'+name+'-legend';group.setAttribute('role','radiogroup');group.setAttribute('aria-labelledby',legend.id);group.append(legend);group.dataset.dationTest='case-choices-'+name;const inputs=[];
 for(const [i,[key,text]]of options.entries()){
  const choice=el('label',undefined,'decision-case-choice'),input=el('input',undefined,'decision-case-radio'),caption=el('span',text),hint=el('span',help[i]||text,'decision-case-sr-only');
  input.type='radio';input.name=name;input.id='ultimate-'+name+'-'+key;input.value=key;input.checked=key===value;input.disabled=readOnly;input.required=required;input.setAttribute('aria-label',text);hint.id=input.id+'-help';input.setAttribute('aria-describedby',hint.id);choice.htmlFor=input.id;
  if(icons[i])choice.append(decisionIcon(icons[i]));choice.append(caption,input,hint);group.append(choice);inputs.push(input);
 }
 parent.append(group);return {group,inputs,get value(){return inputs.find(n=>n.checked)?.value||'';},set disabled(value){for(const n of inputs)n.disabled=value;}};
}
export function decorateDecisionCase(panel){
 panel.details.classList.add('decision-case-step');panel.body.classList.add('decision-case-body');
 const summary=panel.details.querySelector('summary'),tile=el('span',undefined,'decision-case-tile'),heading=el('span',undefined,'decision-case-heading');tile.append(decisionIcon('target'));heading.append(summary.querySelector('.ultimate-disclosure__title'),panel.body.previousElementSibling);summary.prepend(tile,heading);
 const flow=el('aside',undefined,'decision-case-flow'),copy=el('div',undefined,'decision-case-flow-copy'),steps=el('div',undefined,'decision-case-flow-steps');
 flow.dataset.dationTest='case-flow';copy.append(decisionIcon('flow'),el('strong','Flujo de decisión'));steps.append(el('span','D1 · Asignación'),el('span','→ Aprobación →','decision-case-approval'),el('span','D2 · Planificación'));flow.append(copy,steps,el('p','La ejecución se administrará luego desde Decision Graph.'));panel.body.append(flow);
}
export function mountCaseReview(parent){
 const body=decisionCard(parent,'Resumen de la decisión','Revisá la configuración principal del Case antes de finalizar.','review'),list=el('dl',undefined,'decision-case-review');body.append(list);const values={};
 for(const [key,label,kind]of [['model','Logistics Model','layers'],['contract','Data Contract','database'],['goal','Objetivo','target'],['mode','Modalidad','resources'],['horizon','Horizonte','calendar'],['flow','Flujo','flow'],['identity','Case','document'],['owner','Decision Owner','people']]){
  const row=el('div'),term=el('dt'),value=el('dd');term.append(decisionIcon(kind),el('span',label+':'));row.append(term,value);list.append(row);values[key]=value;
 }
 return {update(data){for(const [key,node]of Object.entries(values)){const text=data[key]||'Pendiente';if(node.textContent!==text)node.textContent=text;}}};
}
export function decorateCaseFooter(kit,{fresh}){
 kit.footer.classList.add('decision-case-footer');const progress=el('div',undefined,'decision-case-progress'),ring=el('span',undefined,'decision-case-ring'),text=el('div'),copy=el('p',fresh?'Completá los datos requeridos para crear el Case.':'Revisá los datos permitidos antes de guardar.'),count=el('p','','d-metadata');ring.setAttribute('aria-hidden','true');text.append(el('strong','Configuración del Decision Case'),copy,count);progress.append(ring,text);kit.footer.prepend(progress);count.dataset.dationTest='case-progress';
 return {update(checks,complete){const done=checks.filter(Boolean).length;ring.style.setProperty('--case-progress',String(done/checks.length*100)+'%');count.textContent=done+' de '+checks.length+' condiciones completas';kit.footer.dataset.caseReady=String(complete);}};
}
