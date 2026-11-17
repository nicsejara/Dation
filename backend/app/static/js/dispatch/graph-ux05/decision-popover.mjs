import {el,button} from '../models/forms.mjs';
import {createScope} from '../lifecycle.mjs';
import {mountResponsibilitySelector} from '../cases/workflow-responsibility.mjs';
import {visualState,requirements,possibleActions} from './status-presentation.mjs';
import {decisionIcon} from '../cases/decision-case-ui.mjs';

export function contextualPanel(slot,parent,{trigger,title,onClose,id='ux05-decision-panel'}){
 const scope=createScope(slot),panel=el('section',undefined,'ux05-panel'),heading=el('h2',title);parent.own(()=>scope.dispose());
 panel.id=id;heading.id=id+'-title';heading.tabIndex=-1;panel.setAttribute('role','dialog');panel.setAttribute('aria-labelledby',heading.id);
 trigger?.setAttribute('aria-expanded','true');trigger?.setAttribute('aria-controls',id);
 const close=({restoreFocus=true}={})=>{if(!scope.active)return;scope.dispose();slot.replaceChildren();trigger?.setAttribute('aria-expanded','false');onClose?.();if(restoreFocus&&trigger?.isConnected)trigger.focus();};
 const dismiss=button('',()=>close());dismiss.className='ux05-panel-close';dismiss.setAttribute('aria-label','Cerrar panel');dismiss.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="m6 6 12 12M18 6 6 18"/></svg>';panel.append(heading,dismiss);slot.replaceChildren(panel);
 scope.listen(document,'keydown',event=>{if(event.key==='Escape'){event.preventDefault();close();}});
 scope.listen(document,'pointerdown',event=>{if(!panel.contains(event.target)&&!trigger?.contains(event.target)&&!event.target.closest('.ux05-node-button'))close({restoreFocus:false});});
 scope.own(()=>trigger?.setAttribute('aria-expanded','false'));
 return {scope,panel,close,focus:()=>heading.focus()};
}
export function decisionContent(panel,node,{data,journey,scope,onAction,onHistory,onPrepare,onOwnerSaved,ownerDraft}){
 const state=visualState(node),grid=el('div',undefined,'ux05-panel-grid'),info=el('section'),owner=el('section',undefined,'ux05-owner'),actions=el('section',undefined,'ux05-possible-actions');
 const output=(node.outputs||[]).length?(node.id==='logistics_assignment'?'Plan de transporte':'Calendario de despachos'):'Sin salida informada';
 const heading=panel.querySelector(':scope > h2'),header=el('header',undefined,'ux08-node-header'),identity=el('div',undefined,'ux08-node-identity'),tile=el('span',undefined,'ux08-node-tile'),copy=el('div'),meta=el('dl',undefined,'ux08-node-meta'),badge=el('span',state.label,'ux05-status ux08-panel-state');badge.dataset.tone=state.tone;tile.append(decisionIcon(node.id==='logistics_assignment'?'resources':'calendar'));copy.append(heading,el('p',node.id==='logistics_assignment'?'Asigná demanda a recursos y viajes.':'Programá los viajes del plan de transporte aprobado.','ux05-secondary'));identity.append(tile,copy);
 for(const [label,value]of [['Estado',badge],['Salida',output]]){const fact=el('div'),dd=el('dd');if(typeof value==='string')dd.textContent=value;else{dd.append(value,el('small',state.detail,'ux08-state-detail'));}fact.append(el('dt',label),dd);meta.append(fact);}header.append(identity,meta);panel.prepend(header);
 const infoTitle=el('h3','Información general');infoTitle.prepend(decisionIcon('review'));info.append(infoTitle,el('p',node.question,'ux08-node-question'));
 const io=el('dl',undefined,'ux08-node-io');io.append(el('dt','Entradas'),el('dd',node.id==='logistics_assignment'?'Demanda + Flota':'Plan de transporte aprobado de D1 + horizonte'));info.append(io);
 const reasons=requirements(node);if(reasons.length){const label=el('h4','Requisitos'),ul=el('ul',undefined,'ux05-requirements');for(const r of reasons)ul.append(el('li',r));info.append(label,ul);}
 owner.setAttribute('aria-label','Decision Owner');owner.append(el('h3','Decision Owner'));const selector=el('div');owner.append(selector);
 const snapshot=data.case.status==='archived'?{...data.responsibilities,can_assign:false}:data.responsibilities;
 const child=mountResponsibilitySelector(selector,{caseId:data.case.id,stageKey:node.id,snapshot,draft:ownerDraft,onSaved:onOwnerSaved});scope.own(()=>child.dispose());
 actions.append(el('h3','Acciones posibles'));const stage=data.responsibilities?.stages?.[node.id],choices=possibleActions(node,data.case.id,{archived:data.case.status==='archived',canApprove:!!stage?.can_approve});let primary=null;
 if(choices.primary){const a=choices.primary;const b=button(a.label,()=>onAction(a),'primary');b.dataset.ux05Action=a.kind;b.dataset.mapAction=a.kind;primary=b;}
 for(const a of choices.secondary){const b=button(a.label,()=>onAction(a));b.dataset.ux05Action=a.kind;actions.append(b);}
 if(!choices.primary)actions.append(el('p','Revisá los requisitos del Graph.','d-metadata'));
 if(node.actions?.data?.allowed&&journey.can_prepare&&data.case.status!=='archived'){const prepare=button('Preparar datos',onPrepare,choices.primary?'secondary':'primary');if(choices.primary)actions.append(prepare);else primary=prepare;}
 if(node.history_count>0){const b=button('Ver historial',()=>onHistory());b.dataset.ux05History='';actions.append(b);}
 if(primary){primary.classList.add('ux08-panel-primary');actions.append(primary);}
 grid.append(info,owner,actions);panel.append(grid);
}
