import {renderAssistantLauncher,bindAssistantLauncher} from '../runs/contextual-assistant.mjs';
import {iconSvg} from '../decision-ui.mjs';
import {bindDashboardPresentation,renderDecisionIntelligence} from '../dashboard-presentation.mjs';
import {decisionRail,bindDecisionRail} from '../navigation/decision-nav.mjs';
import {renderDashboardToolbar,bindDashboardToolbar} from '../runs/dashboard-toolbar.mjs';
export const schedulingIcon=name=>iconSvg(name,'scheduling-v2__icon');

export function renderSchedulingShell(root,run,caseActions={}){
  const id='scheduling-presentation-'+run.id;
  const {toolbar,drawer}=renderDashboardToolbar(run,caseActions,{placement:'hero'});
  root.className='dispatch dispatch-scheduling-dashboard scheduling-dashboard-v2 d-decision-dashboard';
  root.innerHTML='<div class="scheduling-v2__rail">'+decisionRail(caseActions)+'</div>'
    +'<main class="scheduling-v2__main">'
      +'<section class="dispatch-panel scheduling-v2__panel scheduling-hero" id="dispatch-hero"><div data-scheduling-hero></div>'+toolbar+'</section>'
      +'<section id="scheduling-context" aria-label="Contexto"></section>'
      +'<section id="scheduling-kpis" aria-label="Indicadores de la planificación"></section>'
      +'<section class="dispatch-panel scheduling-v2__panel" id="scheduling-timeline"></section>'
      +'<section class="dispatch-panel scheduling-v2__panel" id="scheduling-insights"></section>'
      +'<div class="scheduling-v2__execution"><section class="dispatch-panel scheduling-v2__panel" id="scheduling-resources"></section><section class="dispatch-panel scheduling-v2__panel" id="scheduling-preview"></section></div>'
      +renderDecisionIntelligence({kind:'scheduling',id,advancedMarkup:''})
      +'<section class="dispatch-panel scheduling-v2__panel" id="scheduling-validation"></section>'
    +'</main>'
    +'<aside class="dispatch-chat dispatch-panel" hidden aria-label="Chat de la planificación"></aside>'+drawer+renderAssistantLauncher(run);
  const find=selector=>root.querySelector(selector);
  return {hero:find('[data-scheduling-hero]'),context:find('#scheduling-context'),kpis:find('#scheduling-kpis'),insights:find('#scheduling-insights'),timeline:find('#scheduling-timeline'),resources:find('#scheduling-resources'),preview:find('#scheduling-preview'),ai:find('#dispatch-explanation'),advanced:find('[data-scheduling-advanced-content]'),validation:find('#scheduling-validation'),chat:find('.dispatch-chat')};
}
export function bindSchedulingShell(root,run,{onRerun,caseActions={},onOpenChat,onAdvancedOpen}={}){
  bindDecisionRail(root,caseActions);
  const advanced=root.querySelector('[data-scheduling-advanced]');
  const presentation=bindDashboardPresentation(root,{
    advanced,toggle:root.querySelector('[data-scheduling-advanced-toggle]'),
    content:advanced.querySelector('[data-scheduling-advanced-content]'),
    storageKey:'dation.scheduling.presentation.'+run.id,onAdvancedOpen,
  });
  bindAssistantLauncher(root,()=>onOpenChat?.());
  return {...bindDashboardToolbar(root,run,{onRerun,caseActions}),...presentation};
}
