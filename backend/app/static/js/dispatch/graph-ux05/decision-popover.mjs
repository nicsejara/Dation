import {el,button} from '../models/forms.mjs';
import {createScope} from '../lifecycle.mjs';
import {mountResponsibilitySelector} from '../cases/workflow-responsibility.mjs';
import {visualState,requirements,possibleActions} from './status-presentation.mjs';

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
 info.append(el('h3','Información general'),el('span',state.label,'ux05-status'),el('p',state.detail,'ux05-secondary'),el('p',node.question));
 const io=el('dl');for(const [label,value]of [['Entradas',node.id==='logistics_assignment'?'Demanda + Flota':'Plan de transporte aprobado de D1 + horizonte'],['Salida',(node.outputs||[]).length?(node.id==='logistics_assignment'?'Plan de transporte':'Calendario de despachos'):'Sin salida informada']]){io.append(el('dt',label),el('dd',value));}info.append(io);
 const reasons=requirements(node);if(reasons.length){const ul=el('ul',undefined,'ux05-requirements');for(const r of reasons)ul.append(el('li',r));info.append(ul);}
 owner.setAttribute('aria-label','Decision Owner');owner.append(el('h3','Decision Owner'));const selector=el('div');owner.append(selector);
 const snapshot=data.case.status==='archived'?{...data.responsibilities,can_assign:false}:data.responsibilities;
 const child=mountResponsibilitySelector(selector,{caseId:data.case.id,stageKey:node.id,snapshot,draft:ownerDraft,onSaved:onOwnerSaved});scope.own(()=>child.dispose());
 actions.append(el('h3','Acciones posibles'));const stage=data.responsibilities?.stages?.[node.id],choices=possibleActions(node,data.case.id,{archived:data.case.status==='archived',canApprove:!!stage?.can_approve});
 if(choices.primary){const a=choices.primary;const b=button(a.label,()=>onAction(a),'primary');b.dataset.ux05Action=a.kind;b.dataset.mapAction=a.kind;actions.append(b);}
 for(const a of choices.secondary){const b=button(a.label,()=>onAction(a));b.dataset.ux05Action=a.kind;actions.append(b);}
 if(!choices.primary)actions.append(el('p',state.detail+'. '+(reasons.join(' ')||'Revisá los requisitos del Graph.'),'d-metadata'));
 if(node.actions?.data?.allowed&&journey.can_prepare&&data.case.status!=='archived')actions.append(button('Preparar datos',onPrepare));
 if(node.history_count>0){const b=button('Ver historial',()=>onHistory());b.dataset.ux05History='';actions.append(b);}
 grid.append(info,owner,actions);panel.append(grid);
}
