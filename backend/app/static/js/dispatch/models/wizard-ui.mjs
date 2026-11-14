import {el,button} from './forms.mjs';

// Local line icons; decorative because every action/section has a visible label.
export function wizardIcon(kind){
 const paths={layers:['M12 3 2 8l10 5 10-5-10-5Z','m2 12 10 5 10-5','m2 17 10 5 10-5'],identity:['m12 3 9 5v9l-9 5-9-5V8l9-5Z','m3 8 9 5 9-5','M12 13v9','m7 6 10 5v6'],resources:['M3 5h12v12H3z','M15 10h4l3 4v3h-7','M6 20a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z','M18 20a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z'],costs:['M14 3c4 0 7 1 7 3s-3 3-7 3-7-1-7-3 3-3 7-3Z','M7 6v5c0 2 3 3 7 3s7-1 7-3V6','M10 12c-4 0-8 1-8 3s4 3 8 3 8-1 8-3','M2 15v4c0 2 4 3 8 3s8-1 8-3v-5'],database:['M12 3C6 3 3 5 3 7s3 4 9 4 9-2 9-4-3-4-9-4Z','M3 7v10c0 2 3 4 9 4s9-2 9-4V7','M3 12c0 2 3 4 9 4s9-2 9-4'],folder:['M3 6h7l2 2h9v12H3V6Z'],check:['m5 12 4 4L19 6']};
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','1.7');svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');svg.setAttribute('aria-hidden','true');svg.classList.add('model-wizard-icon');
 for(const d of paths[kind]||paths.layers){const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',d);svg.append(path);}return svg;
}

// One mounted form; changing steps only reveals the existing panels.
export function mountSetupSteps(form,panels,{fresh,available}){
 form.classList.add('core-wizard');
 const nav=el('nav',undefined,'core-wizard-steps');nav.setAttribute('aria-label','Etapas de Core Configuration');nav.dataset.dationTest='core-steps';
 const workspace=el('div',undefined,'core-wizard-workspace');form.append(nav,workspace);
 const steps=[['Logistics Model','Modelo operativo'],['Data Contract','Datos y estructura'],['Decision Case','Caso y alcance']];
 let active=fresh?0:2;
 const controls=steps.map(([label,copy],i)=>{
  const action=button('',()=>show(i,true)),number=el('span',String(i+1),'core-step-number'),text=el('span',undefined,'core-step-copy'),status=el('span','','core-step-status');
  text.append(el('strong',label),el('span',copy),status);action.append(number,text);action.dataset.dationTest='core-step-'+(i+1);action.setAttribute('aria-controls','core-wizard-panel-'+i);nav.append(action);
  const panel=panels[i];panel.id='core-wizard-panel-'+i;workspace.append(panel);return {action,status};
 });
 function update(){for(const [i,{action,status}]of controls.entries()){action.disabled=!available(i);if(i===active)action.setAttribute('aria-current','step');else action.removeAttribute('aria-current');status.textContent=!available(i)?'Pendiente de modelo':panels[i].querySelector('.ultimate-disclosure__status')?.textContent||'';}}
 function show(index,focus=false){if(!available(index))return;active=index;panels.forEach((panel,i)=>{panel.hidden=i!==index;if(i===index)panel.open=true;});form.dataset.activeStep=String(index+1);const footer=form.querySelector('.ultimate-footer');if(footer)footer.hidden=index!==2;update();if(focus)panels[index].querySelector('summary').focus();}
 show(active);
 return {show,update,workspace,get active(){return active;}};
}
