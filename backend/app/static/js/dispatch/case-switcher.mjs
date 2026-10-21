import {api} from './shared.mjs';
import {createScope} from './lifecycle.mjs';
import {ensureStylesheet} from './styles.mjs';
import {caseContext} from '../platform/foundation.mjs';

function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
let sequence=0;
export function mountCaseSwitcher(root,{decisionCase,context}){
 ensureStylesheet('workflow-context-styles','/static/css/workflow-context.css','v2-phase5').catch(()=>{});
 const scope=createScope(root),current=context||caseContext(decisionCase),id='case-switcher-'+(++sequence);
 root.className='workflow-case-switcher';root.dataset.caseSwitcher='';
 const approved=['logistics_assignment','logistics_scheduling'].filter(key=>decisionCase.nodes?.[key]?.status==='approved').length;
 const trigger=el('button',undefined,'workflow-case-switcher__trigger');trigger.type='button';trigger.setAttribute('aria-expanded','false');trigger.setAttribute('aria-controls',id);
 const identity=el('span'),label=el('strong',current.label||current.friendlyId),status=el('small',(current.status==='archived'?'Archivado':approved===2?'Completado':'En progreso')+' · '+approved+' de 2 aprobadas');
 identity.append(el('small','DECISION CASE'),label);if(current.label)identity.append(el('small',current.friendlyId));identity.append(status);trigger.append(identity,el('span','⌄'));
 const panel=el('nav',undefined,'workflow-case-switcher__panel');panel.id=id;panel.hidden=true;panel.setAttribute('aria-label','Decision Cases recientes');root.append(trigger,panel);
 let controller,generation=0;
 function close(focus=false){generation++;controller?.abort();panel.hidden=true;trigger.setAttribute('aria-expanded','false');if(focus&&scope.active)trigger.focus({preventScroll:true});}
 function action(label,handler){const b=el('button',label,'d-button d-button--secondary');b.type='button';b.addEventListener('click',handler);return b;}
 async function open(){
  controller?.abort();controller=new AbortController();const own=++generation;panel.hidden=false;trigger.setAttribute('aria-expanded','true');const loading=el('p','Cargando casos…');loading.role='status';panel.replaceChildren(loading);
  try{
   const result=await api('/api/platform/decisions?'+new URLSearchParams({dda:current.dda||'logistics',limit:8,offset:0}),{signal:controller.signal});
   if(!scope.active||own!==generation)return;
   panel.replaceChildren(el('h3','Decision Cases recientes','d-card-title'));
   for(const item of result.items||[]){
    if(item.status==='archived')continue;
    const value=caseContext(item),selected=value.caseId===current.caseId;
    const choice=action((selected?'✓ ':'')+(value.label||value.friendlyId)+(value.label?' · '+value.friendlyId:'')+(selected?' · Actual':''),()=>{close();if(selected)trigger.focus();else window.DationDispatch.openCase(value.caseId,'logistics-map',null);});
    choice.append(el('small',({active:'En progreso',in_progress:'En progreso',review:'En revisión',pending_approval:'Requiere aprobación',approved:'Aprobado',completed:'Completado'})[item.status]||'En progreso'));
    if(selected)choice.setAttribute('aria-current','true');panel.append(choice);
   }
   if(!(result.items||[]).length)panel.append(el('p','No hay otros casos recientes.'));
   panel.append(action('Abrir este caso en Decision Center',()=>window.DationDispatch.openCaseInDecisionCenter(current.caseId)),action('Ver todos en Decision Center',()=>window.DationDispatch.openDecisionCenter({dda:current.dda||'logistics'})));
  }catch(exc){if(scope.active&&own===generation&&!controller.signal.aborted){const error=el('p',exc.message);error.role='alert';panel.replaceChildren(error,action('Reintentar',open));}}
 }
 scope.listen(trigger,'click',()=>panel.hidden?open():close());
 scope.listen(root,'keydown',event=>{if(event.key==='Escape'&&!panel.hidden){event.preventDefault();event.stopPropagation();close(true);}});
 scope.listen(document,'pointerdown',event=>{if(!root.contains(event.target))close();});
 scope.listen(root,'focusout',event=>{if(event.relatedTarget&&!root.contains(event.relatedTarget))close();});
 scope.own(()=>{generation++;controller?.abort();});return scope;
}
