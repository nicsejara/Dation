import {el,button,pageHeader} from '../models/forms.mjs';
import {libraryFooter} from '../models/model-library.mjs';
import {mountDialog} from '../../platform/components.mjs';
import {CASE_GOALS} from './case-v2-state.mjs';

export function caseShell(root,{title='Decision Case',copy,mode,active=2,onModels,onCases,onData,hasData=false}){
 root.replaceChildren();root.className='dispatch d-platform ultimate-foundation j102-shell';
 const header=pageHeader(root,title,copy||'Definí qué decisión querés tomar y las condiciones que debe respetar Dation.');
 header.querySelector('.d-eyebrow').textContent='DDA Logística · Core Configuration / '+String(active).padStart(2,'0');
 header.append(el('span',mode||'Biblioteca','j102-mode'));
 const layout=el('div',undefined,'j102-layout'),nav=el('nav',undefined,'j102-rail'),content=el('div',undefined,'j102-content');
 nav.setAttribute('aria-label','Core Configuration');
 for(const [n,label,handler]of [[1,'Logistics Models',onModels],[2,'Decision Case',onCases],[3,'Data Preparation',onData]]){
  const b=button(String(n).padStart(2,'0')+' · '+label,handler);b.disabled=n===3&&!hasData;b.classList.add('j102-stage');
  if(n===active){b.setAttribute('aria-current','step');b.tabIndex=-1;}nav.append(b);
 }
 layout.append(nav,content);root.append(layout);return {header,content,layout};
}
export function caseFooter(root,options){const result=libraryFooter(root,options);result.footer.classList.add('j102-footer');return result;}
export function readPair(parent,label,value){const box=el('div',undefined,'j102-fact');box.append(el('dt',label),el('dd',value??'No configurado'));parent.append(box);return box;}
export function definitionFacts(parent,d,{owner,versionName}={}){
 const facts=el('dl',undefined,'j102-facts'),goal=CASE_GOALS.find(([g])=>g===d.case_policy.primary_goal)?.[1]||d.case_policy.primary_goal;
 readPair(facts,'Nombre',d.identity.name);readPair(facts,'Descripción',d.identity.description||'Sin descripción');
 readPair(facts,'Model Version',versionName||d.model_binding.model_version_id);readPair(facts,'Modalidad',d.decision_context.operating_mode==='OPERATIONAL'?'Operacional':'Simulación');
 readPair(facts,'Horizonte',d.decision_context.planning_start+' → '+d.decision_context.planning_end+' · inclusivo');readPair(facts,'Objetivo',goal);
 if(d.case_policy.primary_goal==='CUSTOM')readPair(facts,'Pesos',d.case_policy.preferences.map(p=>p.kind+': '+Number(p.weight)*100+' %').join(' · '));
 readPair(facts,'Preferencia',d.business_rules.prefer_own_fleet_on_cost_tie?'Flota propia con costo óptimo idéntico':'Sin desempate por flota propia');
 readPair(facts,'Restricción obligatoria',Number(d.case_policy.guardrails[0].limit)*100+' % demanda crítica HIGH');
 readPair(facts,'Criterio de éxito','Cobertura total ≥ '+Number(d.acceptance_policy.threshold)*100+' %');
 readPair(facts,'Aprobación','Manual · Decision Owner'+(owner?' · '+owner:''));
 if(d.provenance)readPair(facts,'Origen',d.provenance.parent_case_id+' · '+d.provenance.reason);
 parent.append(facts);return facts;
}
export function dirtyChoice(root,scope){return new Promise(resolve=>{
 const dialog=el('dialog',undefined,'d-modal'),body=el('div',undefined,'d-modal__body'),title=el('h2','Cambios sin guardar','d-modal__title'),actions=el('div',undefined,'d-modal__actions');
 title.id='j102-dirty-title';dialog.setAttribute('aria-labelledby',title.id);body.append(title,el('p','Podés guardar el borrador, descartar los cambios o seguir editando. Los datos ya preparados no se eliminan.','d-body'));
 const stay=button('Seguir editando',()=>mounted.close('stay')),discard=button('Descartar cambios',()=>mounted.close('discard')),save=button('Guardar y salir',()=>mounted.close('save'),'primary');actions.append(stay,discard,save);dialog.append(body,actions);root.append(dialog);
 const mounted=mountDialog({dialog,initialFocus:stay});let settled=false;const finish=value=>{if(settled)return;settled=true;mounted.dispose();dialog.remove();resolve(value);};
 dialog.addEventListener('close',()=>finish(dialog.returnValue||'stay'),{once:true});scope.own(()=>finish('stay'));mounted.open();
});}
