import {createScope} from './lifecycle.mjs';
import {mountCaseSwitcher} from './case-switcher.mjs';
import {mountResponsibilitySelector,executionPermission} from './workflow-responsibility.mjs';

const mounted=new WeakMap();
export function mountWorkflowContext(root,{state,stageKey,field='owner',showCase=true,onSaved,onPrepare}){
 mounted.get(root)?.dispose();
 if(!showCase&&!state.preflight?.valid)return;
 const current=state.decisionCase;if(!current?.id)return;
 const host=document.createElement('section');host.className='workflow-context';host.setAttribute('aria-label','Contexto del Decision Case');
 const hero=root.querySelector('.d-page-hero');if(hero)hero.after(host);else root.prepend(host);
 const scope=createScope(host);mounted.set(root,scope);scope.own(()=>{host.remove();if(mounted.get(root)===scope)mounted.delete(root);});
 if(showCase){const switcher=document.createElement('div');host.append(switcher);mountCaseSwitcher(switcher,{decisionCase:current,context:state.caseContext});}
 if(stageKey&&stageKey!=='data_preparation'&&field==='owner'&&executionPermission()){
  const note=document.createElement('p');note.id='workflow-permission';note.className='d-metadata';note.textContent=executionPermission();host.append(note);
 }
 if(stageKey&&state.workflow){
  const selector=document.createElement('div');host.append(selector);
  mountResponsibilitySelector(selector,{caseId:current.id,stageKey,field,snapshot:state.workflow,onPrepare,onSaved:result=>{if(scope.active){state.workflow=result;onSaved?.(result);}}});
 }
 return scope;
}
