import {scopeFor} from './lifecycle.mjs';
import {decisionRail,bindDecisionRail} from './decision-nav.mjs';
import {analysisDepthUi} from './assignment-dashboard-selectors.mjs';
import {renderDashboardToolbar,bindDashboardToolbar} from './dashboard-toolbar.mjs';

export function renderAssignmentShell(root,run,caseActions={}){
  const depth=analysisDepthUi(run);
  const {toolbar,drawer}=renderDashboardToolbar(run,caseActions);
  root.className='dispatch assignment-dashboard-v2';root.dataset.analysisDepth=depth.depth;
  root.innerHTML=toolbar
    +'<div class="assignment-dashboard-v2__rail">'+decisionRail(caseActions)+'</div>'
    +'<main class="assignment-dashboard-v2__main">'
      +'<section class="dispatch-panel assignment-dashboard-v2__section assignment-dashboard-v2__hero" id="dispatch-hero"></section>'
      +'<section class="dispatch-panel assignment-dashboard-v2__section assignment-dashboard-v2__assignment" id="dispatch-assignment"></section>'
      +'<section class="dispatch-panel assignment-dashboard-v2__section assignment-dashboard-v2__review" id="dispatch-review"><div data-review-content></div></section>'
      +'<section class="dispatch-panel assignment-dashboard-v2__section assignment-comparative-layer" id="dispatch-comparative"></section>'
      +'<section class="dispatch-panel assignment-dashboard-v2__section assignment-dashboard-v2__ai" id="dispatch-explanation"></section>'
    +'</main>'
    +'<button type="button" class="dispatch-ai-fab assignment-dashboard-v2__ai-fab" data-chat aria-expanded="false" aria-label="Abrir Dation IA"><span>✦</span><strong>Dation IA</strong></button>'
    +'<aside class="dispatch-chat dispatch-panel assignment-dashboard-v2__chat" hidden aria-label="Chat de la decisión"></aside>'
    +drawer;
  return {
    hero:root.querySelector('#dispatch-hero'),assignment:root.querySelector('#dispatch-assignment'),
    review:root.querySelector('[data-review-content]'),comparative:root.querySelector('#dispatch-comparative'),
    explanation:root.querySelector('#dispatch-explanation'),chat:root.querySelector('.assignment-dashboard-v2__chat'),
  };
}

export function bindAssignmentShell(root,run,{onRerun,caseActions={},onOpenChat}={}){
  bindDecisionRail(root,caseActions);
  scopeFor(root).listen(root.querySelector('[data-chat]'),'click',()=>onOpenChat?.());
  return bindDashboardToolbar(root,run,{onRerun,caseActions});
}
