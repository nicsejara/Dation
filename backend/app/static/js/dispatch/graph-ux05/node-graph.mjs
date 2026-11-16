import {el,button} from '../models/forms.mjs';
import {wizardIcon} from '../models/wizard-ui.mjs';
import {IMPLEMENTED,visualState,dependencyActive} from './status-presentation.mjs';
export function renderNodes(root,graph,onSelect,scope){
 root.replaceChildren();const nodes=(graph.nodes||[]).filter(n=>IMPLEMENTED.has(n.id)&&n.implemented),row=el('div',undefined,'ux05-node-row');root.append(row);
 const buttons=new Map(),first=nodes.find(n=>n.id==='logistics_assignment'),second=nodes.find(n=>n.id==='logistics_scheduling');
 for(const [index,node] of nodes.entries()){
  const state=visualState(node),host=el('section',undefined,'ux05-node');host.dataset.graphNode=node.id;host.dataset.nodeState=node.node_state;
  const b=button('',()=>onSelect(node.id));b.className='ux05-node-button';b.dataset.ux05Node=node.id;b.dataset.tone=state.tone;b.setAttribute('aria-label',node.label+' · '+state.label);b.setAttribute('aria-expanded','false');b.setAttribute('aria-controls','ux05-decision-panel');
  b.append(wizardIcon(node.id==='logistics_assignment'?'resources':'identity'),el('span',node.id==='logistics_assignment'?'D1':'D2','ux05-monogram'),el('strong',node.label),el('span',state.label,'ux05-status'));
  host.append(b,el('p',node.question,'ux05-question'));row.append(host);buttons.set(node.id,b);
  if(index<nodes.length-1){const edge=el('div',undefined,'ux05-edge');edge.dataset.active=String(dependencyActive(first,second));edge.setAttribute('aria-hidden','true');row.append(edge);}
 }
 const future=el('div',undefined,'ux05-future'),plus=el('span','+','ux05-future-circle'),futureEdge=el('span',undefined,'ux05-future-edge');plus.setAttribute('aria-hidden','true');futureEdge.setAttribute('aria-hidden','true');future.append(plus,el('strong','Futuras decisiones'),el('small','Decision Designer · Próximamente'));if(nodes.length)row.append(futureEdge);row.append(future);
 const note=el('p',second?.node_state==='NOT_APPLICABLE'?'D2 no requiere planificación en este Case.':dependencyActive(first,second)?'D1 tiene aprobación vigente. D2 consume ese plan aprobado.':'D2 requiere la aprobación vigente de D1.','ux05-dependency');root.append(note);
 if(!nodes.length)root.append(el('p','No hay decisiones implementadas disponibles para este Graph.','d-metadata'));
 if(graph.nodes?.some(n=>n.implemented&&!IMPLEMENTED.has(n.id)))root.append(el('p','Hay decisiones adicionales que requieren validación de esta interfaz.','d-metadata'));
 return buttons;
}
