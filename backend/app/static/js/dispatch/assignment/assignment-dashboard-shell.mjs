import {iconSvg} from '../decision-ui.mjs';
import {esc} from '../shared.mjs';
import {scopeFor} from '../lifecycle.mjs';
import {bindDashboardPresentation} from '../dashboard-presentation.mjs';
import {decisionRail,bindDecisionRail} from '../navigation/decision-nav.mjs';
import {analysisDepthUi} from './assignment-dashboard-selectors.mjs';
import {renderDashboardToolbar,bindDashboardToolbar} from '../runs/dashboard-toolbar.mjs';
const icon=name=>iconSvg(name,'assignment-v2__icon');

export function renderAssignmentShell(root,run,caseActions={}){
  const depth=analysisDepthUi(run),id='assignment-presentation-'+run.id;
  const {toolbar,drawer}=renderDashboardToolbar(run,caseActions,{placement:'hero'});
  root.className='dispatch assignment-dashboard-v2 d-decision-dashboard';root.dataset.analysisDepth=depth.depth;
  root.innerHTML='<div class="assignment-dashboard-v2__rail">'+decisionRail(caseActions)+'</div>'
    +'<main class="assignment-dashboard-v2__main">'
      +'<section class="dispatch-panel assignment-dashboard-v2__section assignment-dashboard-v2__hero" id="dispatch-hero"><div data-assignment-hero-copy></div>'+toolbar+'</section>'
      +'<section id="assignment-context" class="assignment-context"></section>'
      +'<section id="assignment-kpis"></section>'
      +'<section id="assignment-insights" class="assignment-v2__panel"></section>'
      +'<section id="assignment-scenarios" class="assignment-v2__panel"></section>'
      +'<div class="assignment-essential__execution"><section id="assignment-resources" class="assignment-v2__panel"></section>'
        +'<section id="assignment-preview" class="assignment-v2__panel"></section></div>'
      +'<section class="assignment-v2__panel assignment-ai-summary" id="dispatch-explanation"></section>'
      +'<section class="assignment-v2__panel assignment-advanced" data-assignment-advanced>'
        +'<button type="button" class="assignment-advanced__toggle" data-assignment-advanced-toggle aria-expanded="false" aria-controls="'+esc(id)+'-advanced-content"><span class="assignment-advanced__copy">'+icon('chartBar')+'<strong data-assignment-advanced-label>Mostrar análisis avanzado</strong></span><span class="assignment-advanced__chevron" data-assignment-advanced-chevron aria-hidden="true">'+icon('chevronDown')+'</span></button><p class="assignment-advanced__description">Compará escenarios en detalle, revisá utilización por viaje, corredores y la evidencia completa.</p>'
        +'<div class="assignment-advanced__chips" aria-hidden="true"><span>Frontera de decisión</span><span>Comparación detallada</span><span>Utilización por viaje</span><span>Corredores</span><span>Plan completo</span></div>'
        +'<div id="'+esc(id)+'-advanced-content" data-assignment-advanced-content hidden>'
          +'<section class="assignment-comparative-layer" id="dispatch-comparative"></section>'
          +'<div data-assignment-advanced-analysis></div>'
          +'<section class="assignment-dashboard-v2__assignment" id="dispatch-assignment" tabindex="-1"></section>'
        +'</div></section>'
      +'<section class="dispatch-panel assignment-dashboard-v2__section assignment-dashboard-v2__review" id="dispatch-review"><div data-review-content></div></section>'
    +'</main>'
    +'<button type="button" class="dispatch-ai-fab assignment-dashboard-v2__ai-fab" data-chat aria-expanded="false" aria-label="Abrir Dation IA">'+icon('sparkles')+'<strong>Dation IA</strong></button>'
    +'<aside class="dispatch-chat dispatch-panel assignment-dashboard-v2__chat" hidden aria-label="Chat de la decisión"></aside>'+drawer;
  const find=selector=>root.querySelector(selector);
  return {hero:find('[data-assignment-hero-copy]'),context:find('#assignment-context'),kpis:find('#assignment-kpis'),insights:find('#assignment-insights'),
    scenarios:find('#assignment-scenarios'),resources:find('#assignment-resources'),preview:find('#assignment-preview'),assignment:find('#dispatch-assignment'),
    review:find('[data-review-content]'),comparative:find('#dispatch-comparative'),advanced:find('[data-assignment-advanced-analysis]'),
    explanation:find('#dispatch-explanation'),chat:find('.assignment-dashboard-v2__chat')};
}

export function bindAssignmentShell(root,run,{onRerun,caseActions={},onOpenChat,onAdvancedOpen}={}){
  bindDecisionRail(root,caseActions);
  const advanced=root.querySelector('[data-assignment-advanced]');
  const presentation=bindDashboardPresentation(root,{
    advanced,toggle:advanced.querySelector('[data-assignment-advanced-toggle]'),
    content:advanced.querySelector('[data-assignment-advanced-content]'),
    label:advanced.querySelector('[data-assignment-advanced-label]'),
    storageKey:'dation.assignment.presentation.'+run.id,onAdvancedOpen,
  });
  scopeFor(root).listen(root.querySelector('[data-chat]'),'click',()=>onOpenChat?.());
  return {...bindDashboardToolbar(root,run,{onRerun,caseActions}),...presentation};
}
