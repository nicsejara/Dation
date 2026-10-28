import {iconSvg} from "./decision-ui.mjs";
import {ensureStylesheet} from "./styles.mjs";
import {bindDashboardActions} from './runs/dashboard-actions.mjs';
import {createScope,disposeScope,scopeFor} from "./lifecycle.mjs";
import {esc,num,download,dispose,errorBox,api} from './shared.mjs';
import * as hero from './hero.mjs';
import * as assignment from './assignment/assignment.mjs';
import * as review from './review.mjs';
import * as explanation from './explanation.mjs';
import * as assignmentSummary from './assignment/assignment-summary.mjs';
import * as assignmentEvidence from './assignment/assignment-evidence.mjs';
import * as assignmentValidation from './assignment/assignment-validation.mjs';
import * as assignmentEssential from './assignment/assignment-essential.mjs';
import * as assignmentAiSummary from './assignment/assignment-ai-summary.mjs';
import * as assignmentAdvanced from './assignment/assignment-advanced.mjs';
import * as comparativeUpgrade from './comparative-upgrade.mjs';
import {downloadRunExport} from './runs/export.mjs';
import * as publishedDashboard from './results/dashboard.mjs';
import {RESULT_SCHEMAS} from './results/package.mjs';
import * as schedulingDashboard from './scheduling/scheduling-dashboard.mjs';
import {decisionRail,bindDecisionRail} from './navigation/decision-nav.mjs';
import {
  renderAssignmentShell,
  bindAssignmentShell,
} from './assignment/assignment-dashboard-shell.mjs';

const ASSIGNMENT_STYLE_ID='assignment-dashboard-v2-styles';
const ASSIGNMENT_ESSENTIAL_STYLE_ID='assignment-dashboard-essential-styles';
const ASSIGNMENT_COMPARATIVE_STYLE_ID='assignment-dashboard-comparative-styles';

function ensureDashboardStyles(schema){
  const styles=[ensureStylesheet('dashboard-toolbar-styles','/static/css/dashboard-toolbar.css')];
  if(schema==='assignment_v1')styles.push(
    ensureStylesheet(ASSIGNMENT_STYLE_ID,'/static/css/assignment-dashboard-v2.css'),
    ensureStylesheet(ASSIGNMENT_ESSENTIAL_STYLE_ID,'/static/css/assignment-dashboard-essential.css'),
    ensureStylesheet(ASSIGNMENT_COMPARATIVE_STYLE_ID,'/static/css/assignment-dashboard-comparative.css'),
    ensureStylesheet('assignment-dashboard-decision-styles','/static/css/assignment-dashboard-decision.css','assignment-dashboard-v2-20261016'),
  );
  if(schema==='scheduling_v1')styles.push(ensureStylesheet('scheduling-dashboard-v21-styles','/static/css/scheduling-dashboard-v21.css','scheduling-v21-20261017'));
  return Promise.all(styles);
}

function renderModule(element,module,value){
  const draw=()=>{
    try{
      module.render(element,value);
    }catch(error){
      errorBox(element,error,draw);
    }
  };
  draw();
}

function installDecisionChat(root,run,chatNode,toggleButton){
  function openChat(question=''){
    if(!chatNode)return;
    chatNode.hidden=false;
    root.classList.add('with-chat');
    toggleButton?.setAttribute('aria-expanded','true');
    explanation.chat(chatNode,run,question);
  }

  function toggleChat(){
    if(!chatNode)return;
    if(!chatNode.hidden){
      disposeScope(chatNode);chatNode.hidden=true;
      root.classList.remove('with-chat');
      toggleButton?.setAttribute('aria-expanded','false');
      return;
    }
    openChat();
  }

  scopeFor(root).listen(root,'dispatch:open-chat',event=>{
    openChat(event.detail?.question||'');
  });

  return {openChat,toggleChat};
}

function renderAssignmentDashboard(root,run,onRerun,caseActions={}){
  const result=run.result_json;
  const nodes=renderAssignmentShell(root,run,caseActions);

  assignmentSummary.render(nodes.hero,result,caseActions);
  renderModule(nodes.context,{render:assignmentEssential.context},result);
  renderModule(nodes.kpis,{render:assignmentEssential.kpis},result);
  renderModule(nodes.insights,{render:assignmentEssential.insights},result);
  renderModule(nodes.resources,{render:assignmentEssential.resources},result);
  renderModule(nodes.assignment,assignmentEvidence,result);
  renderModule(nodes.review,assignmentValidation,result);
  const summary=assignmentAiSummary.render(nodes.explanation,run);
  let shell,comparative,evidence=result,drawnEvidence=null,advanced=null,comparativeState='available';
  function drawAdvanced(){
    if(root.dataset.visualDepth!=='advanced'||drawnEvidence===evidence)return;
    advanced=assignmentAdvanced.render(nodes.advanced,evidence);drawnEvidence=evidence;
  }
  function drawScenarios(){
    assignmentEssential.scenarios(nodes.scenarios,evidence,{state:comparativeState,onGenerate:()=>{
      shell.openAdvanced();comparative.generate();
    }});
  }

  const chatButton=root.querySelector('[data-chat]');
  const chat=installDecisionChat(root,run,nodes.chat,chatButton);

  shell=bindAssignmentShell(root,run,{
    onRerun,
    caseActions,
    onOpenChat:chat.toggleChat,
    onAdvancedOpen:()=>{if(comparative)drawAdvanced();},
  });
  assignmentEssential.preview(nodes.preview,result,{onOpen:()=>shell.openAdvanced(nodes.assignment)});
  comparative=comparativeUpgrade.render(nodes.comparative,run,{inline:true,
    onStateChange:status=>{comparativeState=status;drawScenarios();},
    onReady:artifact=>{
      evidence={...result,scenarios:{...artifact.result_json.scenarios,selected:result.scenarios.selected}};
      drawScenarios();drawAdvanced();summary.evidenceChanged(artifact);
    },
    onEvidenceReady:artifact=>{
      summary.evidenceChanged(artifact);
      nodes.chat.dispatchEvent(new CustomEvent('dispatch:evidence-changed',{detail:{id:artifact.id}}));
    },
  });
  drawAdvanced();
  scopeFor(root).listen(nodes.comparative,'assignment:reference-changed',event=>advanced?.setReference(event.detail.key));
}

function renderLegacyDashboard(root,run,onRerun,caseActions={}){
  const result=run.result_json;
  const metrics=result.scenarios.selected.metrics;
  const statusLabels={
    running:'Procesando',
    review:'En revisión',
    approved:'Aprobada',
    error:'Error',
  };
  const caseStatus=statusLabels[caseActions.status]||'Decisión disponible';
  const exportButtonLabel='Exportar decisión';

  root.className='dispatch dispatch-dashboard dispatch-dashboard-focused d-decision-dashboard';
  root.innerHTML=
    '<header class="dispatch-command dispatch-command-focused">'
      +'<div class="dispatch-command-title"><strong>DDA Logística · Assignment</strong><span class="dispatch-status" data-case-status>'+esc(caseStatus)+'</span></div>'
      +'<div class="dispatch-actions dispatch-actions--focused">'
        +(caseActions.onApprove?'<button data-approve class="dispatch-primary-action" '+(caseActions.status==='approved'?'disabled':'')+'>'+(caseActions.status==='approved'?'✓ Decisión aprobada':'Aprobar decisión')+'</button>':'')
        +'<button type="button" data-export-decision class="dispatch-export-action" title="Descargar la tabla completa de asignaciones">↓ '+esc(exportButtonLabel)+'</button>'
        +'<details class="dispatch-action-menu"><summary>Acciones ···</summary><div class="dispatch-action-menu__panel">'
          +'<button data-json>Exportar JSON técnico</button>'
          +'<button type="button" data-new-decision>Nueva decisión · cargar otros datos</button>'
          +'<button data-rerun>Nueva corrida</button>'
          +'<button data-copy>Copiar detalles técnicos</button>'
          +'<dl>'
            +Object.entries({
              'Corrida':run.id,
              'Motor':result.engine.name+' '+result.engine.version,
              'Solver':result.engine.solver.name||result.engine.solver.method||'Política heurística',
              'Estado':result.engine.solver.status,
              'Huella':result.result_fingerprint,
              'Órdenes':result.inputs.orders.filename||'Órdenes',
              'Flota':result.inputs.fleet.label||result.inputs.fleet.filename||'Flota',
              'Escenarios evaluados':result.analysis?.scenario_count??'—',
              'Órdenes incluidas':metrics.orders,
              'Kg totales':num(metrics.total_weight_kg),
            }).map(([key,value])=>'<dt>'+esc(key)+'</dt><dd>'+esc(value)+'</dd>').join('')
          +'</dl>'
          +'<p data-ai-details>Modelo de IA: consultando…</p>'
        +'</div></details>'
      +'</div>'
    +'</header>'
    +'<div class="dispatch-dashboard-continuation"><button type="button" data-after-approve hidden>Continuar con la siguiente decisión →</button><p data-next-decision-status role="status"></p></div>'
    +decisionRail(caseActions)
    +'<main class="dispatch-focus-main">'
      +'<section class="dispatch-panel dispatch-focus-hero" id="dispatch-hero"></section>'
      +'<section class="dispatch-panel dispatch-focus-assignment" id="dispatch-assignment"></section>'
      +'<section class="dispatch-panel dispatch-focus-review" id="dispatch-review"></section>'
      +'<section class="dispatch-panel dispatch-focus-ai" id="dispatch-explanation"></section>'
    +'</main>'
    +'<button type="button" class="dispatch-ai-fab" data-chat aria-expanded="false" aria-label="Abrir Dation IA">'+iconSvg("sparkles","dispatch-action-icon")+'<strong>Dation IA</strong></button>'
    +'<aside class="dispatch-chat dispatch-panel" hidden aria-label="Chat de la decisión"></aside>';

  api('/api/system/llm-status')
    .then(data=>{
      const target=root.querySelector('[data-ai-details]');
      if(target)target.textContent='IA: '+(data.configured?(data.provider+' · '+data.model):'Sin configurar');
    })
    .catch(()=>{
      const target=root.querySelector('[data-ai-details]');
      if(target)target.textContent='No se pudo consultar el modelo de IA.';
    });

  renderModule(root.querySelector('#dispatch-hero'),hero,result);
  renderModule(root.querySelector('#dispatch-assignment'),assignment,result);
  renderModule(root.querySelector('#dispatch-review'),review,result);
  renderModule(root.querySelector('#dispatch-explanation'),explanation,run);

  const chatButton=root.querySelector('[data-chat]');
  const chat=installDecisionChat(
    root,
    run,
    root.querySelector('.dispatch-chat'),
    chatButton,
  );

  function feedback(button,working,done){
    const original=button.dataset.originalLabel||button.textContent;
    button.dataset.originalLabel=original;
    button.disabled=true;
    button.textContent=working;
    window.setTimeout(()=>{
      button.textContent=done;
      window.setTimeout(()=>{
        button.textContent=original;
        button.disabled=false;
      },1200);
    },120);
  }

  root.querySelector('[data-export-decision]').onclick=async event=>{
    const exportButton=event.currentTarget;exportButton.disabled=true;
    try{
      await downloadRunExport(run,'csv');
      feedback(exportButton,'Preparando archivo…','✓ Exportado');
    }catch(error){
      exportButton.textContent='No se pudo exportar';
      window.setTimeout(()=>{
        exportButton.textContent=exportButton.dataset.originalLabel||('↓ '+exportButtonLabel);
      },1500);
    }finally{exportButton.disabled=false;}
  };
  root.querySelector('[data-rerun]').onclick=onRerun;
  bindDecisionRail(root,caseActions);
  const actions=bindDashboardActions(root,caseActions);
  const approveButton=root.querySelector('[data-approve]');
  if(approveButton)approveButton.onclick=async()=>{
    approveButton.disabled=true;
    try{
      await caseActions.onApprove?.();
      approveButton.textContent='Decisión aprobada';
      const status=root.querySelector('[data-case-status]');
      if(status)status.textContent='Aprobada';
      caseActions.onApprovalComplete?.();
      await actions.refresh();
    }catch(error){
      approveButton.disabled=false;
      alert(error.message);
    }
  };
  chatButton.onclick=chat.toggleChat;
  root.querySelector('[data-json]').onclick=async event=>{const b=event.currentTarget;b.disabled=true;try{await downloadRunExport(run,'json',{filename:'decision-'+run.id+'.json'});}catch{b.textContent='No se pudo exportar';}finally{b.disabled=false;}};
  root.querySelector('[data-copy]').onclick=async event=>{
    try{
      await navigator.clipboard.writeText(JSON.stringify({
        run_id:run.id,
        engine:result.engine,
        analysis:result.analysis,
        inputs:result.inputs,
        result_fingerprint:result.result_fingerprint,
      },null,2));
      event.target.textContent='Copiado';
    }catch{
      event.target.textContent='No se pudo copiar';
    }
  };
}

export async function render(root,run,onRerun,caseActions={}){
  const scope=createScope(root);scope.own(()=>{dispose(root);});

  dispose(root);
  const result=run.result_json;
  await ensureDashboardStyles(RESULT_SCHEMAS.has(result?.result_schema)?'assignment_v1':result?.schema_version);
  if(RESULT_SCHEMAS.has(result?.result_schema))await ensureStylesheet('ultimate-results-styles','/static/css/ultimate-results.css','ultimate-t10-v1');
  if(!scope.active)return;

  if(RESULT_SCHEMAS.has(result?.result_schema))return publishedDashboard.render(root,run,onRerun,caseActions);
  if(result?.result_schema||!['assignment_v1','scheduling_v1','dispatch_v1','dispatch_v2'].includes(result?.schema_version)){
    errorBox(root,new Error('UNSUPPORTED_RESULT_SCHEMA'),()=>caseActions.onRefresh?.());return;
  }

  if(result?.schema_version==='scheduling_v1'){
    return schedulingDashboard.render(
      root,
      run,
      onRerun,
      caseActions,
    );
  }

  if(result?.schema_version==='assignment_v1'){
    renderAssignmentDashboard(root,run,onRerun,caseActions);
    return;
  }

  renderLegacyDashboard(root,run,onRerun,caseActions);
}
