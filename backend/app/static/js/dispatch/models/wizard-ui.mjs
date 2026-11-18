import {el,button} from './forms.mjs';
import {corePrevious} from '../journey/targets.mjs';

// Local line icons; decorative because every action/section has a visible label.
export function wizardIcon(kind){
 const paths={back:['M19 12H5','m11 6-6 6 6 6'],layers:['M12 3 2 8l10 5 10-5-10-5Z','m2 12 10 5 10-5','m2 17 10 5 10-5'],identity:['m12 3 9 5v9l-9 5-9-5V8l9-5Z','m3 8 9 5 9-5','M12 13v9','m7 6 10 5v6'],resources:['M3 5h12v12H3z','M15 10h4l3 4v3h-7','M6 20a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z','M18 20a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z'],costs:['M14 3c4 0 7 1 7 3s-3 3-7 3-7-1-7-3 3-3 7-3Z','M7 6v5c0 2 3 3 7 3s7-1 7-3V6','M10 12c-4 0-8 1-8 3s4 3 8 3 8-1 8-3','M2 15v4c0 2 4 3 8 3s8-1 8-3v-5'],database:['M12 3C6 3 3 5 3 7s3 4 9 4 9-2 9-4-3-4-9-4Z','M3 7v10c0 2 3 4 9 4s9-2 9-4V7','M3 12c0 2 3 4 9 4s9-2 9-4'],folder:['M3 6h7l2 2h9v12H3V6Z'],check:['m5 12 4 4L19 6']};
 Object.assign(paths,{tag:['M3 3h8l10 10-8 8L3 11Z','M7 7h.01'],box:paths.identity,pallet:['M3 18h18M4 21v-3m8 3v-3m8 3v-3','M5 9h6v7H5zm8 0h6v7h-6zM8 2h8v5H8z'],mound:['M2 19c3-1 3-6 6-7s3-7 6-7 5 11 8 14Z','M8 15h.01M13 10h.01M16 16h.01'],drop:['M12 2C10 6 5 11 5 15a7 7 0 0 0 14 0c0-4-5-9-7-13Z'],container:['M3 7h18v14H3zM6 10v8m4-8v8m4-8v8m4-8v8M8 7l4-5 4 5'],search:['m21 21-6-6','M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z'],plus:['M12 5v14M5 12h14'],copy:['M8 8h13v13H8zM4 16H2V2h14v2'],edit:['m16 3 5 5-13 13H3v-5Z','m13 6 5 5'],trash:['M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7'],info:['M12 17v-5m0-5h.01','M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z'],clipboard:['M8 4H5v18h14V4h-3M8 2h8v4H8zM8 11h8m-8 4h8']});
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','1.7');svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');svg.setAttribute('aria-hidden','true');svg.classList.add('model-wizard-icon');
 for(const d of paths[kind]||paths.layers){const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',d);svg.append(path);}return svg;
}

// One mounted form; changing steps only reveals the existing panels.
export function mountSetupSteps(form,panels,{fresh,available,unified=false,initialStep=null,onStep=()=>{},onExit=()=>{}}){
 form.classList.add('core-wizard');
 const nav=el('nav',undefined,'core-wizard-steps');nav.setAttribute('aria-label','Etapas de Core Configuration');nav.dataset.dationTest='core-steps';
 const workspace=el('div',undefined,'core-wizard-workspace');form.append(nav,workspace);
 const steps=unified?[['Logistics Model','Modelo operativo'],['Data Contract & Preparation','Estructura y preparación de datos'],['Decision Case','Objetivo y alcance de la decisión']]:[['Logistics Model','Modelo operativo'],['Data Contract','Datos y estructura'],['Decision Case','Caso y alcance']];
 let active=initialStep?initialStep-1:fresh?0:2;
 const controls=steps.map(([label,copy],i)=>{
  const action=button('',()=>show(i,true)),number=el('span',String(i+1),'core-step-number'),text=el('span',undefined,'core-step-copy'),status=el('span','','core-step-status');
  text.append(el('strong',label),el('span',copy),status);action.append(number,text);action.dataset.dationTest='core-step-'+(i+1);action.setAttribute('aria-controls','core-wizard-panel-'+i);nav.append(action);
  const panel=panels[i];panel.id='core-wizard-panel-'+i;workspace.append(panel);return {action,status};
 });
 function update(){for(const [i,{action,status}]of controls.entries()){action.disabled=!available(i);if(i===active){action.setAttribute('aria-current','step');action.tabIndex=unified?-1:0;}else{action.removeAttribute('aria-current');action.tabIndex=0;}status.textContent=!available(i)?'Pendiente de modelo':panels[i].querySelector('.ultimate-disclosure__status')?.textContent||'';}}
 function show(index,focus=false,{history='push',force=false}={}){if(!available(index)||unified&&!force&&index===active)return;active=index;panels.forEach((panel,i)=>{panel.hidden=i!==index;if(i===index)panel.open=true;});form.dataset.activeStep=String(index+1);const footer=form.querySelector('.ultimate-footer');if(footer)footer.hidden=index!==2;update();onStep(index,{history});if(focus)panels[index].querySelector(unified?'header':'summary')?.focus();}
 if(unified)panels.forEach((panel,index)=>{
  const header=panel.querySelector(':scope > header');header.classList.add('journey-step-header');
  let heading=header.querySelector('.model-wizard-heading,.data-contract-heading,.decision-case-heading');
  if(!heading){heading=el('span',undefined,'journey-step-heading');heading.append(header.querySelector('.ultimate-disclosure__title'));const copy=panel.querySelector('.ultimate-disclosure__content > p.d-metadata');if(copy)heading.append(copy);const tile=el('span',undefined,'journey-step-tile');tile.append(wizardIcon(index===0?'layers':'database'));header.prepend(tile,heading);}
  heading.classList.add('journey-step-heading');header.querySelector('.model-wizard-tile,.data-contract-tile,.decision-case-tile')?.classList.add('journey-step-tile');
  const intent=corePrevious(index+1),previous=button('',()=>intent.local?show(intent.step-1,true):onExit(intent.target));previous.dataset.journeyPrevious='';previous.setAttribute('aria-label','Volver a '+intent.label);previous.title='Volver a '+intent.label;previous.append(wizardIcon('back'));
  let footer=index===2?form.querySelector('.ultimate-footer'):panel.querySelector('.model-wizard-footer,.data-contract-footer');
  if(!footer){footer=el('footer',undefined,'journey-sequential-footer');panel.append(footer);}
  if(index<2)panel.append(footer);
  const actions=el('div',undefined,'journey-step-actions');for(const action of footer.querySelectorAll(':scope > button'))actions.append(action);
  const context=el('div',undefined,'journey-step-context');
  for(const note of footer.querySelectorAll(':scope > p[role]'))context.append(note);
  const feedback=panel.querySelector('.model-wizard-feedback');if(feedback)context.append(feedback);
  // Move the existing live preparation copy, keeping its update reference intact.
  if(index===1){const copy=footer.querySelector('.data-contract-progress .d-metadata');if(copy)context.append(copy);}
  footer.classList.add('journey-step-footer');footer.prepend(previous);footer.append(context,actions);
 });
 if(!available(active))active=0;show(active,false,{history:'replace',force:true});
 return {show,update,workspace,get active(){return active;}};
}

// Remove the redundant principal disclosure semantically; inner details stay native.
export function flattenCorePanel(panel){
 const old=panel.details,next=document.createElement('section');for(const a of old.attributes)if(a.name!=='open')next.setAttribute(a.name,a.value);
 const summary=old.querySelector(':scope > summary'),header=document.createElement('header');header.className=summary.className;header.tabIndex=-1;
 summary.querySelector('.ultimate-disclosure__chevron')?.remove();while(summary.firstChild)header.append(summary.firstChild);summary.remove();next.append(header);while(old.firstChild)next.append(old.firstChild);old.replaceWith(next);panel.details=next;
}
