import {resourceUrl} from '../dispatch/navigation.mjs';
const rendered=new WeakMap();

/** Context navigation uses the existing canonical destinations and route contract. */
export function renderDdaNavigation(root,{view,route,workspace={}}){
 const currentCase=workspace.decisionCase?.id===route.caseId?workspace.decisionCase:null;
 const signature=JSON.stringify([view,route.caseId,workspace.caseContext?.label,currentCase?.label]);
 if(rendered.get(root)===signature&&root.firstElementChild?.tagName==='OL')return;
 rendered.set(root,signature);root.replaceChildren();root.classList.add('dda-navigation');root.setAttribute('aria-label','Navegación del DDA');
 const list=document.createElement('ol');root.append(list);
 const entries=[
  {label:'Decision Data Assets',target:{view:'inicio',caseId:null,nodeId:null,runId:null},state:'available'},
  {label:'DDA Logística',target:{view:'logistics-overview',caseId:null,nodeId:null,runId:null},state:view==='logistics-overview'?'current':'available'},
 ];
 if(route.caseId){
  entries.push({label:workspace.caseContext?.label||currentCase?.label||'Decision Case',target:{view:'logistics-map',caseId:route.caseId,nodeId:null,runId:null},state:view==='logistics-map'?'current':'available'});
 }else if(view==='logistics-data'){
  entries.push({label:'Nuevo Case',target:null,state:'current'});
 }
 for(const entry of entries){
  const item=document.createElement('li'),control=document.createElement(entry.target?'a':'span');
  control.className='dda-navigation__step';control.dataset.state=entry.state;
  control.textContent=entry.label;
  if(entry.state==='completed')control.prepend(document.createTextNode('✓ '));
  if(entry.state==='current')control.setAttribute('aria-current','step');
  if(!entry.target){control.setAttribute('aria-disabled','true');control.title='Completá la etapa anterior para habilitar esta decisión.';}
  else{
   control.href=resourceUrl(location.href,entry.target);
   control.addEventListener('click',event=>{
    if(event.button||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
    event.preventDefault();const target=entry.target;
    if(target.view==='decision-dashboard')window.DationDispatch.openDashboard(target.caseId,target.nodeId,target.runId);
    else window.DationDispatch.openCase(target.caseId,target.view,target.nodeId);
   });
  }
  item.append(control);list.append(item);
 }
}
