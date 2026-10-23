import {createScope,scopeFor} from '../lifecycle.mjs';
import {DECISION_META} from '../decision-ui.mjs';
import {mountResponsibilitySelector} from './workflow-responsibility.mjs';
import {configurationAvailable} from '../navigation/decision-target.mjs';

const mounted=new WeakMap();
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}

export function mountCasePreparation(root,{state,onSaved}){
 const current=state.decisionCase;
 mounted.get(root)?.dispose();
 const host=el('section',undefined,'workflow-context');host.setAttribute('aria-label','Responsables del Data Pack');
 const anchor=root.querySelector('[data-case-data-owner]');if(!anchor)return;anchor.append(host);
 const scope=createScope(host);mounted.set(root,scope);scope.own(()=>{host.remove();if(mounted.get(root)===scope)mounted.delete(root);});
 let snapshot=state.workflow||{stages:{},pending:true,can_assign:window.dationSession?.identity?.membership?.access_role==='admin',can_prepare:window.dationSession?.identity?.membership?.access_role!=='viewer'};
 if(state.appliedPreparation)snapshot={...snapshot,stages:{...snapshot.stages,data_owner:{owner:state.appliedPreparation.owner,owner_eligible:state.appliedPreparation.ownerEligible}}};
 const currentId=current?.id||null;
 if(!state.dataOwnerDraft||state.dataOwnerDraft.caseId&&state.dataOwnerDraft.caseId!==currentId)state.dataOwnerDraft={caseId:currentId};
 state.dataOwnerDraft.caseId=currentId;
 const draft=state.dataOwnerDraft;
 const selector=el('div');host.append(selector);
 const child=mountResponsibilitySelector(selector,{caseId:currentId,stageKey:'data_owner',snapshot,draft,deferSave:true,onChanged:()=>{if(state.appliedPreparation&&!draft.dirty)state.appliedPreparation.ownerEligible=draft.ownerEligible;onSaved?.();}});scope.own(()=>child.dispose());
 return {scope,host,dispose:()=>scope.dispose()};
}

export function mountMapResponsibilities(root,{state,onSaved}){
 const scope=scopeFor(root)||createScope(root);
 for(const stageKey of Object.keys(DECISION_META).filter(key=>DECISION_META[key].implemented)){
  const card=root.querySelector('article[data-decision-node="'+stageKey+'"]');if(!card)continue;
  for(const action of card.querySelectorAll('[data-map-action="configure"]')){
   action.disabled=!configurationAvailable(stageKey,state.decisionCase,state.workflow);
   if(action.disabled)action.title='Asigná el Decision Owner y completá las decisiones anteriores para configurar.';
  }
  card.removeAttribute('aria-disabled');
  const group=el('section',undefined,'workflow-map-responsibilities');group.setAttribute('aria-label','Responsables de '+DECISION_META[stageKey].label);card.append(group);
  for(const field of ['owner']){const selector=el('div');group.append(selector);const child=mountResponsibilitySelector(selector,{caseId:state.decisionCase.id,stageKey,field,snapshot:state.workflow,onSaved:result=>{if(scope.active){state.workflow=result;onSaved?.(result);}}});scope.own(()=>child.dispose());}
 }
 return scope;
}

// Keep named imports from workspace modules loaded before the rollout working.
export {mountCasePreparation as mountWorkflowContext};
export {mountDashboardTrace} from '../runs/approval-trace.mjs';
export {executionStageLabel,renderExecutionProgress} from '../runs/execution-progress.mjs';
