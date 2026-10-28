import {resourceUrl} from '../dispatch/navigation/resource.mjs';
import {openDdaCatalog} from './dda-catalog.mjs';
const rendered=new WeakMap();

/** Context navigation uses the existing canonical destinations and route contract. */
export function renderDdaNavigation(root,{view,route,workspace={}}){
 const currentCase=workspace.decisionCase?.id===route.caseId?workspace.decisionCase:null;
 const ultimate=workspace.ultimateCaseContext?.id===route.caseId?workspace.ultimateCaseContext:null;
 const signature=JSON.stringify([view,route.caseId,workspace.caseContext?.label,currentCase?.label,ultimate?.label]);
 if(rendered.get(root)===signature&&root.firstElementChild?.tagName==='OL')return;
 rendered.set(root,signature);root.replaceChildren();root.classList.add('dda-navigation');root.setAttribute('aria-label','Navegación del DDA');
 const list=document.createElement('ol');root.append(list);
 const entries=[
  {label:'Decision Data Assets',target:{view:'platform-home',caseId:null,nodeId:null,runId:null},state:'available'},
  {label:'DDA Logística',target:{view:'logistics-overview',caseId:null,nodeId:null,runId:null},state:view==='logistics-overview'?'current':'available'},
 ];
 if(view==='logistics-models')entries.push({label:'Logistics Models',target:null,state:'current'});
 else if(view==='logistics-case-data')entries.push({label:ultimate?.label||'Decision Case',target:{view:'logistics-map',caseId:route.caseId,nodeId:null,runId:null},state:'available'},{label:'Datos del Case',target:null,state:'current'});
 else if(view==='logistics-case-setup')entries.push({label:ultimate?.label||(route.caseId?'Contexto del Case':'Nuevo Case'),target:null,state:'current'});
 else if(route.caseId){
  entries.push({label:ultimate?.label||workspace.caseContext?.label||currentCase?.label||'Decision Case',target:{view:'logistics-map',caseId:route.caseId,nodeId:null,runId:null},state:view==='logistics-map'?'current':'available'});
 }else if(view==='logistics-data'){
  entries.push({label:'Nuevo Case',target:null,state:'current'});
 }
 list.style.setProperty('--context-levels',entries.length);
 for(const entry of entries){
  const item=document.createElement('li'),control=document.createElement(entry.target?'a':'span');
  control.className='dda-navigation__step';control.dataset.state=entry.state;
  const label=document.createElement('span');label.textContent=entry.label;control.append(label);control.title=entry.label;
  if(entry.state==='completed')control.prepend(document.createTextNode('✓ '));
  if(entry.state==='current')control.setAttribute('aria-current','step');
  if(!entry.target){control.setAttribute('aria-disabled','true');control.title='Completá la etapa anterior para habilitar esta decisión.';}
  else{
   const url=resourceUrl(location.href,entry.target);if(entry.target.view==='platform-home')url.hash='dation-dda-title';control.href=url;
   control.addEventListener('click',event=>{
    if(event.button||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
    event.preventDefault();const target=entry.target;
    if(target.view==='platform-home')openDdaCatalog();
    else if(target.view==='decision-dashboard')window.DationDispatch.openDashboard(target.caseId,target.nodeId,target.runId);
    else window.DationDispatch.openCase(target.caseId,target.view,target.nodeId);
   });
  }
  item.append(control);list.append(item);
 }
}
