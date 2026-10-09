import {api,esc,num} from './shared.mjs';
import {decisionRail,bindDecisionRail} from './decision-nav.mjs?v=assignment-dashboard-phase1';
import {exportDecision,exportDecisionJson} from './export.mjs?v=assignment-dashboard-phase1';
import {
  analysisDepthUi,
  decisionStatusUi,
  shortRunId,
  solverStatusLabel,
} from './assignment-dashboard-selectors.mjs?v=assignment-dashboard-phase1';

function detailRows(run,caseActions){
  const result=run.result_json||{};
  const solver=result.engine?.solver||{};
  const depth=analysisDepthUi(run);
  const decisionCase=caseActions.decisionCase||{};
  const rows=[
    ['Corrida',run.id||'—'],
    ['Decision Case',decisionCase.id||result.decision_case?.case_id||'—'],
    ['Motor',[result.engine?.name,result.engine?.version].filter(Boolean).join(' ')||'—'],
    ['Solver',solver.name||solver.method||'Política heurística'],
    ['Estado solver',solverStatusLabel(solver.status)],
    ['Profundidad',depth.label],
    ['Escenarios evaluados',result.analysis?.scenario_count??'—'],
    ['Huella',result.result_fingerprint||'—'],
    ['Órdenes',result.inputs?.orders?.filename||result.inputs?.orders?.label||'Órdenes'],
    ['Flota',result.inputs?.fleet?.label||result.inputs?.fleet?.filename||'Flota'],
  ];
  return rows;
}

function approvalMarkup(caseActions){
  if(!caseActions.onApprove)return '';
  const approved=caseActions.status==='approved';
  return '<div class="assignment-dashboard-v2__approval '+(approved?'is-approved':'is-review')+'" data-approval-block>'
    +'<div class="assignment-dashboard-v2__approval-copy">'
      +'<span class="assignment-dashboard-v2__approval-icon" aria-hidden="true">'+(approved?'✓':'✓')+'</span>'
      +'<div>'
        +'<strong data-approval-title>'+(approved?'Decisión aprobada':'Validá la evidencia antes de aprobar')+'</strong>'
        +'<p data-approval-copy>'+(approved
          ?'La asignación quedó fijada para este Decision Case. Podés continuar desde el mapa cuando quieras.'
          :'La aprobación fija esta asignación como entrada de la próxima decisión. Dation IA no es requisito para aprobar.')+'</p>'
      +'</div>'
    +'</div>'
    +'<div class="assignment-dashboard-v2__approval-actions">'
      +'<button type="button" data-approve class="assignment-dashboard-v2__approve" '+(approved?'disabled':'')+'>'
        +(approved?'✓ Decisión aprobada':'Aprobar decisión →')
      +'</button>'
      +(caseActions.onFlow
        ?'<button type="button" data-after-approve data-flow class="assignment-dashboard-v2__continue" '+(approved?'':'hidden')+'>Continuar en el mapa →</button>'
        :'')
    +'</div>'
  +'</div>';
}

function toolsMarkup(){
  return '<div class="assignment-dashboard-v2__tools" aria-label="Herramientas de la decisión">'
    +'<details class="assignment-dashboard-v2__menu" data-export-menu>'
      +'<summary>Exportar <span aria-hidden="true">⌄</span></summary>'
      +'<div class="assignment-dashboard-v2__menu-panel" role="menu">'
        +'<button type="button" data-export-csv role="menuitem"><span aria-hidden="true">↓</span><div><strong>Asignación CSV</strong><small>Viajes, vehículos, órdenes y cargas</small></div></button>'
        +'<button type="button" data-export-json role="menuitem"><span aria-hidden="true">{ }</span><div><strong>JSON técnico</strong><small>Resultado completo de la corrida</small></div></button>'
      +'</div>'
    +'</details>'
    +'<details class="assignment-dashboard-v2__menu" data-more-menu>'
      +'<summary>Más <span aria-hidden="true">···</span></summary>'
      +'<div class="assignment-dashboard-v2__menu-panel" role="menu">'
        +'<button type="button" data-rerun role="menuitem"><span aria-hidden="true">↻</span><div><strong>Reconfigurar</strong><small>Volver a configuración sin ejecutar</small></div></button>'
        +'<button type="button" data-run-details role="menuitem"><span aria-hidden="true">i</span><div><strong>Detalles de ejecución</strong><small>Motor, solver, archivos y huella</small></div></button>'
      +'</div>'
    +'</details>'
  +'</div>';
}

export function renderAssignmentShell(root,run,caseActions={}){
  const result=run.result_json||{};
  const depth=analysisDepthUi(run);
  const status=decisionStatusUi(caseActions.status);
  const rows=detailRows(run,caseActions);

  root.className='dispatch assignment-dashboard-v2';
  root.dataset.analysisDepth=depth.depth;
  root.innerHTML=
    '<header class="assignment-dashboard-v2__toolbar">'
      +'<div class="assignment-dashboard-v2__identity">'
        +'<button type="button" data-flow class="assignment-dashboard-v2__map-back" aria-label="Volver al mapa de decisiones">←</button>'
        +'<div class="assignment-dashboard-v2__identity-copy">'
          +'<span class="assignment-dashboard-v2__eyebrow">DDA LOGÍSTICA · DECISIÓN 01</span>'
          +'<div class="assignment-dashboard-v2__title-row">'
            +'<strong>Asignación de carga</strong>'
            +'<span class="assignment-dashboard-v2__badge assignment-dashboard-v2__badge--depth '+esc(depth.className)+'" data-depth-badge>'+esc(depth.label)+'</span>'
            +'<span class="assignment-dashboard-v2__badge assignment-dashboard-v2__badge--status '+esc(status.className)+'" data-status-badge>'+esc(status.label)+'</span>'
          +'</div>'
          +'<small>Corrida '+esc(shortRunId(run.id))+' · '+num(result.scenarios?.selected?.metrics?.orders||0)+' órdenes analizadas</small>'
        +'</div>'
      +'</div>'
      +toolsMarkup()
    +'</header>'
    +'<div class="assignment-dashboard-v2__rail">'+decisionRail(caseActions)+'</div>'
    +'<main class="assignment-dashboard-v2__main">'
      +'<section class="dispatch-panel assignment-dashboard-v2__section assignment-dashboard-v2__hero" id="dispatch-hero"></section>'
      +'<section class="dispatch-panel assignment-dashboard-v2__section assignment-dashboard-v2__assignment" id="dispatch-assignment"></section>'
      +'<section class="dispatch-panel assignment-dashboard-v2__section assignment-dashboard-v2__review" id="dispatch-review"><div data-review-content></div>'+approvalMarkup(caseActions)+'</section>'
      +'<section class="dispatch-panel assignment-dashboard-v2__section assignment-dashboard-v2__ai" id="dispatch-explanation"></section>'
    +'</main>'
    +'<button type="button" class="dispatch-ai-fab assignment-dashboard-v2__ai-fab" data-chat aria-expanded="false" aria-label="Abrir Dation IA"><span>✦</span><strong>Dation IA</strong></button>'
    +'<aside class="dispatch-chat dispatch-panel assignment-dashboard-v2__chat" hidden aria-label="Chat de la decisión"></aside>'
    +'<div class="assignment-dashboard-v2__drawer-backdrop" data-run-drawer-backdrop hidden></div>'
    +'<aside class="assignment-dashboard-v2__drawer" data-run-drawer hidden role="dialog" aria-modal="true" aria-labelledby="assignment-run-details-title">'
      +'<header><div><span class="assignment-dashboard-v2__eyebrow">TRAZABILIDAD TÉCNICA</span><h2 id="assignment-run-details-title">Detalles de ejecución</h2><p>Información persistida de esta corrida. No modifica la decisión.</p></div><button type="button" data-close-drawer aria-label="Cerrar detalles de ejecución">×</button></header>'
      +'<dl class="assignment-dashboard-v2__details">'
        +rows.map(([key,value])=>'<div><dt>'+esc(key)+'</dt><dd>'+esc(value)+'</dd></div>').join('')
      +'</dl>'
      +'<div class="assignment-dashboard-v2__ai-runtime"><span>Servicio de IA</span><strong data-ai-details>Consultando…</strong></div>'
    +'</aside>';

  return {
    hero:root.querySelector('#dispatch-hero'),
    assignment:root.querySelector('#dispatch-assignment'),
    review:root.querySelector('[data-review-content]'),
    explanation:root.querySelector('#dispatch-explanation'),
    chat:root.querySelector('.assignment-dashboard-v2__chat'),
  };
}

function closeMenus(root){
  root.querySelectorAll('.assignment-dashboard-v2__menu[open]').forEach(menu=>menu.removeAttribute('open'));
}

function feedback(button,working,done){
  const original=button.dataset.originalLabel||button.innerHTML;
  button.dataset.originalLabel=original;
  button.disabled=true;
  button.textContent=working;
  window.setTimeout(()=>{
    button.textContent=done;
    window.setTimeout(()=>{
      button.innerHTML=original;
      button.disabled=false;
    },1000);
  },120);
}

export function bindAssignmentShell(root,run,{onRerun,caseActions={},onOpenChat}={}){
  const result=run.result_json||{};
  const drawer=root.querySelector('[data-run-drawer]');
  const backdrop=root.querySelector('[data-run-drawer-backdrop]');
  const closeButton=root.querySelector('[data-close-drawer]');
  let restoreFocus=null;

  const closeDrawer=()=>{
    if(!drawer||drawer.hidden)return;
    drawer.hidden=true;
    backdrop.hidden=true;
    document.body.classList.remove('assignment-dashboard-drawer-open');
    restoreFocus?.focus?.();
  };
  const openDrawer=trigger=>{
    if(!drawer)return;
    restoreFocus=trigger||document.activeElement;
    drawer.hidden=false;
    backdrop.hidden=false;
    document.body.classList.add('assignment-dashboard-drawer-open');
    window.requestAnimationFrame(()=>closeButton?.focus());
  };

  if(root._assignmentDashboardKeydown){
    document.removeEventListener('keydown',root._assignmentDashboardKeydown);
  }
  root._assignmentDashboardKeydown=event=>{
    if(event.key==='Escape'&&!drawer?.hidden){
      event.preventDefault();
      closeDrawer();
    }
  };
  document.addEventListener('keydown',root._assignmentDashboardKeydown);

  backdrop?.addEventListener('click',closeDrawer);
  closeButton?.addEventListener('click',closeDrawer);
  root.querySelector('[data-run-details]')?.addEventListener('click',event=>{
    closeMenus(root);
    openDrawer(event.currentTarget);
  });

  root.querySelector('[data-export-csv]')?.addEventListener('click',event=>{
    closeMenus(root);
    try{
      exportDecision(result);
      feedback(event.currentTarget,'Preparando CSV…','✓ CSV exportado');
    }catch(error){
      event.currentTarget.textContent='No se pudo exportar';
    }
  });
  root.querySelector('[data-export-json]')?.addEventListener('click',event=>{
    closeMenus(root);
    try{
      exportDecisionJson(result,run.id);
      feedback(event.currentTarget,'Preparando JSON…','✓ JSON exportado');
    }catch(error){
      event.currentTarget.textContent='No se pudo exportar';
    }
  });
  root.querySelector('[data-rerun]')?.addEventListener('click',()=>{
    closeMenus(root);
    onRerun?.();
  });

  bindDecisionRail(root,caseActions);

  const approveButton=root.querySelector('[data-approve]');
  if(approveButton)approveButton.onclick=async()=>{
    approveButton.disabled=true;
    approveButton.textContent='Aprobando…';
    try{
      await caseActions.onApprove?.();
      approveButton.textContent='✓ Decisión aprobada';
      const statusBadge=root.querySelector('[data-status-badge]');
      if(statusBadge){
        statusBadge.textContent='Aprobada';
        statusBadge.classList.remove('is-review','is-running','is-error','is-available');
        statusBadge.classList.add('is-approved');
      }
      const block=root.querySelector('[data-approval-block]');
      block?.classList.remove('is-review');
      block?.classList.add('is-approved');
      const title=root.querySelector('[data-approval-title]');
      if(title)title.textContent='Decisión aprobada';
      const copy=root.querySelector('[data-approval-copy]');
      if(copy)copy.textContent='La asignación quedó fijada para este Decision Case. Podés continuar desde el mapa cuando quieras.';
      const continuation=root.querySelector('[data-after-approve]');
      if(continuation)continuation.hidden=false;
      caseActions.onApprovalComplete?.();
    }catch(error){
      approveButton.disabled=false;
      approveButton.textContent='Aprobar decisión →';
      alert(error.message);
    }
  };

  root.querySelector('[data-chat]')?.addEventListener('click',()=>onOpenChat?.());

  api('/api/system/llm-status')
    .then(data=>{
      const target=root.querySelector('[data-ai-details]');
      if(target)target.textContent=data.configured?(data.provider+' · '+data.model):'Sin configurar';
    })
    .catch(()=>{
      const target=root.querySelector('[data-ai-details]');
      if(target)target.textContent='No disponible';
    });

  return {openDrawer,closeDrawer};
}
