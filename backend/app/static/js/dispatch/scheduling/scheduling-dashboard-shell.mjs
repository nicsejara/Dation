import {iconSvg} from '../decision-ui.mjs';
import {esc} from '../shared.mjs';
import {scopeFor} from '../lifecycle.mjs';
import {bindDashboardPresentation} from '../dashboard-presentation.mjs';
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
      +'<section class="dispatch-panel scheduling-v2__panel" id="scheduling-insights"></section>'
      +'<section class="dispatch-panel scheduling-v2__panel" id="scheduling-timeline"></section>'
      +'<div class="scheduling-v2__execution"><section class="dispatch-panel scheduling-v2__panel" id="scheduling-resources"></section><section class="dispatch-panel scheduling-v2__panel" id="scheduling-preview"></section></div>'
      +'<section class="dispatch-panel scheduling-v2__panel scheduling-ai-summary" id="dispatch-explanation"></section>'
      +'<section class="dispatch-panel scheduling-v2__panel scheduling-advanced" data-scheduling-advanced>'
        +'<button type="button" class="scheduling-advanced__toggle" data-scheduling-advanced-toggle aria-expanded="false" aria-controls="'+esc(id)+'-content"><span>'+schedulingIcon('chartBar')+'<strong data-scheduling-advanced-label>Mostrar análisis avanzado</strong></span><span class="scheduling-advanced__chevron" aria-hidden="true">'+schedulingIcon('chevronDown')+'</span></button>'
        +'<p>Revisá el timeline completo, los márgenes SLA, las esperas y la evidencia viaje por viaje.</p>'
        +'<div class="scheduling-advanced__chips" aria-hidden="true"><span>Timeline completo</span><span>SLA y márgenes</span><span>Esperas y motivos</span><span>Ocupación de flota</span><span>Plan completo</span></div>'
        +'<div id="'+esc(id)+'-content" data-scheduling-advanced-content hidden></div>'
      +'</section>'
      +'<section class="dispatch-panel scheduling-v2__panel" id="scheduling-validation"></section>'
    +'</main>'
    +'<aside class="dispatch-chat dispatch-panel" hidden aria-label="Chat de la planificación"></aside>'+drawer;
  const find=selector=>root.querySelector(selector);
  return {hero:find('[data-scheduling-hero]'),context:find('#scheduling-context'),kpis:find('#scheduling-kpis'),insights:find('#scheduling-insights'),timeline:find('#scheduling-timeline'),resources:find('#scheduling-resources'),preview:find('#scheduling-preview'),ai:find('#dispatch-explanation'),advanced:find('[data-scheduling-advanced-content]'),validation:find('#scheduling-validation'),chat:find('.dispatch-chat')};
}
export function bindSchedulingShell(root,run,{onRerun,caseActions={},onOpenChat,onAdvancedOpen}={}){
  bindDecisionRail(root,caseActions);
  const advanced=root.querySelector('[data-scheduling-advanced]');
  const presentation=bindDashboardPresentation(root,{
    advanced,toggle:advanced.querySelector('[data-scheduling-advanced-toggle]'),
    content:advanced.querySelector('[data-scheduling-advanced-content]'),
    label:advanced.querySelector('[data-scheduling-advanced-label]'),
    storageKey:'dation.scheduling.presentation.'+run.id,onAdvancedOpen,
  });
  scopeFor(root).listen(root.querySelector('[data-chat]'),'click',()=>onOpenChat?.());
  return {...bindDashboardToolbar(root,run,{onRerun,caseActions}),...presentation};
}
