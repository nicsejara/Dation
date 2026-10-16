import {iconSvg} from "./decision-ui.mjs";
import {createScope,trapFocus} from './lifecycle.mjs';
import {api,esc,download} from './shared.mjs';
import {bindDashboardActions} from './dashboard-actions.mjs';
import {decisionStatusUi,shortRunId,solverStatusLabel} from './assignment-dashboard-selectors.mjs';
import {exportDecision,exportDecisionJson} from './export.mjs';
import {WORKFLOW_ACTION_CLASS,workflowActionLabel} from './workflow-action-bar.mjs';

const icon=name=>iconSvg(name,"dashboard-toolbar__icon");
const actionLabel=(text,name)=>icon(name)+'<span>'+esc(text)+'</span>';

function detailRows(run,caseActions,scheduling){
  const result=run.result_json||{},metrics=result.scenarios?.selected?.metrics||{},solver=result.engine?.solver||{};
  return [
    ['Corrida',run.id],['Decision Case',caseActions.decisionCase?.id||result.decision_case?.case_id],
    ['Motor',[result.engine?.name||run.engine_name,result.engine?.version||run.engine_version].filter(Boolean).join(' ')],
    ['Solver',solver.name||solver.method],['Estado solver',solverStatusLabel(solver.status)],
    ...(scheduling?[
      ['Assignment fuente',result.inputs?.assignment?.run_id||run.upstream_run_id],
      ['Viajes',metrics.total_trips],['Vehículos',metrics.vehicles_used],
      ['Inicio',metrics.schedule_start],['Fin',metrics.schedule_end],
    ]:[['Escenarios evaluados',result.analysis?.scenario_count]]),
    ['Huella',run.result_fingerprint||result.result_fingerprint],
    ['Órdenes',result.inputs?.orders?.filename||result.inputs?.orders?.label],
    ['Flota',result.inputs?.fleet?.label||result.inputs?.fleet?.filename],
  ];
}

export function renderDashboardToolbar(run,caseActions={}){
  const scheduling=run.result_json?.schema_version==='scheduling_v1';
  const status=decisionStatusUi(caseActions.status);
  const title=scheduling?'Planificación de despachos':'Asignación de carga';
  const approveLabel=scheduling?'Aprobar planificación':'Aprobar asignación';
  const drawerId='dashboard-run-details-'+crypto.randomUUID();
  const rows=detailRows(run,caseActions,scheduling);
  const toolbar='<header class="dashboard-toolbar" data-dashboard-toolbar>'
    +'<div class="dashboard-toolbar__identity"><span class="dashboard-toolbar__eyebrow">DDA LOGÍSTICA · DECISIÓN '+(scheduling?'02':'01')+'</span>'
      +'<div class="dashboard-toolbar__title"><strong>'+title+'</strong>'
        +'<span class="dashboard-toolbar__badge '+esc(status.className)+'" data-status-badge>'+esc(status.label)+'</span></div>'
      +'<small>Corrida '+esc(shortRunId(run.id))+'</small></div>'
    +'<div class="dashboard-toolbar__tools" aria-label="Herramientas de la decisión">'
      +(caseActions.onApprove?'<button type="button" data-approve-toolbar class="dashboard-toolbar__approve '+WORKFLOW_ACTION_CLASS+' d-button--primary" '+(caseActions.status==='approved'?'hidden':'')+'>'+workflowActionLabel(approveLabel)+'</button>':'')
      +'<button type="button" data-after-approve class="dashboard-toolbar__continue '+WORKFLOW_ACTION_CLASS+' d-button--primary" hidden>'+workflowActionLabel("Continuar con la siguiente decisión")+'</button>'
      +(caseActions.onMap?'<button type="button" data-dashboard-map class="dashboard-toolbar__map">'+actionLabel("Decision Map","map")+'</button>':'')
      +'<details class="dashboard-toolbar__menu" data-export-menu><summary aria-expanded="false">'+icon("download")+'<span>Exportar</span>'+icon("chevronDown")+'</summary>'
        +'<div class="dashboard-toolbar__menu-panel">'
          +'<button type="button" data-export-csv>'+icon("download")+'<div><strong>'+(scheduling?'Planificación CSV':'Asignación CSV')+'</strong><small>'+(scheduling?'Viajes, fechas y cargas':'Viajes, vehículos, órdenes y cargas')+'</small></div></button>'
          +'<button type="button" data-export-json>'+icon("fileJson")+'<div><strong>JSON técnico</strong><small>Resultado completo de la corrida</small></div></button>'
        +'</div></details>'
      +'<details class="dashboard-toolbar__menu" data-more-menu><summary aria-expanded="false">'+icon("moreHorizontal")+'<span>Más</span>'+icon("chevronDown")+'</summary>'
        +'<div class="dashboard-toolbar__menu-panel">'
          +'<button type="button" data-rerun>'+icon("refresh")+'<div><strong>Nueva corrida</strong><small>'+(scheduling?'Misma Assignment aprobada, otra configuración temporal':'Mismos datos, otra configuración')+'</small></div></button>'
          +'<button type="button" data-new-decision>'+icon("plus")+'<div><strong>Nueva decisión</strong><small>Cargar otros datos y crear un nuevo Decision Case</small></div></button>'
          +'<button type="button" data-run-details aria-haspopup="dialog" aria-controls="'+drawerId+'">'+icon("info")+'<div><strong>Detalles de ejecución</strong><small>Motor, solver, archivos y huella</small></div></button>'
        +'</div></details>'
    +'</div><p class="dashboard-toolbar__status" data-next-decision-status role="status"></p>'
    +'<p class="dashboard-toolbar__error" data-approval-error role="alert" hidden></p></header>';
  const drawer='<div class="dashboard-toolbar__backdrop" data-run-drawer-backdrop hidden></div>'
    +'<aside class="dashboard-toolbar__drawer" data-run-drawer id="'+drawerId+'" hidden role="dialog" aria-modal="true" aria-labelledby="'+drawerId+'-title">'
      +'<header><div><span class="dashboard-toolbar__eyebrow">TRAZABILIDAD TÉCNICA</span><h2 id="'+drawerId+'-title">Detalles de ejecución</h2>'
        +'<p>Información persistida de esta corrida.</p></div><button type="button" data-close-drawer aria-label="Cerrar detalles de ejecución">'+icon("x")+'</button></header>'
      +'<dl class="dashboard-toolbar__details">'+rows.map(([key,value])=>'<div><dt>'+esc(key)+'</dt><dd>'+esc(value??'—')+'</dd></div>').join('')+'</dl>'
      +'<div class="dashboard-toolbar__ai-runtime"><span>Servicio de IA</span><strong data-ai-details>Consultando…</strong></div></aside>';
  return {toolbar,drawer};
}

export function bindDashboardToolbar(root,run,{onRerun,caseActions={}}={}){
  const toolbar=root.querySelector('[data-dashboard-toolbar]');
  const scope=createScope(toolbar);
  const drawer=root.querySelector('[data-run-drawer]'),backdrop=root.querySelector('[data-run-drawer-backdrop]');
  const closeButton=drawer.querySelector('[data-close-drawer]');
  let restoreFocus=null,pendingApproval=false;
  const menus=[...toolbar.querySelectorAll('.dashboard-toolbar__menu')];
  const closeMenus=(except=null)=>menus.forEach(menu=>{
    if(menu!==except)menu.open=false;
    menu.querySelector('summary').setAttribute('aria-expanded',String(menu.open));
  });
  function positionMenu(menu){
    if(!menu.open)return;
    const panel=menu.querySelector('.dashboard-toolbar__menu-panel');
    const anchor=menu.getBoundingClientRect(),width=Math.min(300,innerWidth-32);
    const left=Math.max(16,Math.min(innerWidth-width-16,anchor.right-width));
    const below=innerHeight-anchor.bottom-24,above=anchor.top-24;
    const up=below<180&&above>below,space=Math.max(80,up?above:below);
    panel.style.width=width+'px';panel.style.maxHeight=space+'px';
    panel.style.left=(left-anchor.left)+'px';panel.style.right='auto';
    const height=Math.min(panel.scrollHeight,space);
    panel.style.top=(up?-height-8:anchor.height+8)+'px';
  }
  for(const menu of menus){
    const summary=menu.querySelector('summary');
    scope.listen(summary,'click',event=>{
      event.preventDefault();const open=!menu.open;closeMenus();menu.open=open;
      summary.setAttribute('aria-expanded',String(open));positionMenu(menu);
    });
    scope.listen(menu,'toggle',()=>{if(menu.open){closeMenus(menu);positionMenu(menu);}else summary.setAttribute('aria-expanded','false');});
  }
  scope.listen(document,'click',event=>{if(!toolbar.contains(event.target))closeMenus();});
  const positionOpen=()=>menus.forEach(positionMenu);
  scope.listen(window,'resize',positionOpen);
  scope.listen(window,'scroll',positionOpen,{passive:true});
  const topbar=document.querySelector('.topbar');
  const measure=()=>{root.style.setProperty('--dashboard-toolbar-top',Math.ceil(topbar?.getBoundingClientRect().height||76)+'px');root.style.setProperty('--dashboard-toolbar-height',Math.ceil(toolbar.getBoundingClientRect().height)+'px');positionOpen();};
  if(typeof ResizeObserver!=='undefined'){const observer=scope.observe(new ResizeObserver(measure),toolbar);if(topbar)observer.observe(topbar);}
  scope.own(()=>{root.style.removeProperty('--dashboard-toolbar-top');root.style.removeProperty('--dashboard-toolbar-height');});
  measure();
  function closeDrawer({focus=true}={}){
    if(drawer.hidden)return;
    drawer.hidden=true;backdrop.hidden=true;document.body.classList.remove('dashboard-drawer-open');
    if(focus)restoreFocus?.focus({preventScroll:true});
  }
  function openDrawer(trigger){
    restoreFocus=trigger.closest('details')?.querySelector('summary')||trigger;
    closeMenus();drawer.hidden=false;backdrop.hidden=false;document.body.classList.add('dashboard-drawer-open');
    closeButton.focus({preventScroll:true});
  }
  scope.own(()=>closeDrawer({focus:false}));
  scope.listen(backdrop,'click',()=>closeDrawer());scope.listen(closeButton,'click',()=>closeDrawer());
  scope.listen(document,'keydown',event=>{
    if(!drawer.hidden){
      trapFocus(event,drawer);
      if(event.key==='Escape'){event.preventDefault();closeDrawer();}
    }else if(event.key==='Escape'){
      const activeMenu=root.querySelector('.dashboard-toolbar__menu[open]');
      if(activeMenu){event.preventDefault();closeMenus();activeMenu.querySelector('summary').focus();}
    }
  });
  scope.listen(root.querySelector('[data-run-details]'),'click',event=>openDrawer(event.currentTarget));
  scope.listen(root.querySelector('[data-rerun]'),'click',async event=>{
    closeMenus();const button=event.currentTarget;if(button.disabled)return;button.disabled=true;
    const feedback=root.querySelector('[data-approval-error]');feedback.hidden=true;
    try{await onRerun?.();}
    catch(error){if(scope.active){feedback.hidden=false;feedback.textContent=error.message||'No se pudo recuperar la configuración.';}}
    finally{if(scope.active)button.disabled=false;}
  });
  const mapButton=root.querySelector('[data-dashboard-map]');
  if(mapButton)scope.listen(mapButton,'click',()=>{closeMenus();caseActions.onMap();});

  function exportFile(event,handler){
    const button=event.currentTarget,original=button.innerHTML;
    closeMenus();button.disabled=true;button.textContent='Preparando archivo…';
    try{handler();button.innerHTML=actionLabel('Exportado','check');}
    catch{button.textContent='No se pudo exportar';}
    scope.timeout(()=>{button.innerHTML=original;button.disabled=false;},1200);
  }
  scope.listen(root.querySelector('[data-export-csv]'),'click',event=>exportFile(event,()=>exportDecision(run.result_json)));
  scope.listen(root.querySelector('[data-export-json]'),'click',event=>exportFile(event,()=>{
    if(run.result_json?.schema_version==='scheduling_v1')download('planificacion-'+run.id+'.json',JSON.stringify(run.result_json,null,2));
    else exportDecisionJson(run.result_json,run.id);
  }));

  const actions=bindDashboardActions(root,{...caseActions,onNewDecision:()=>{closeMenus();return caseActions.onNewDecision?.();}});
  const approveButton=root.querySelector('[data-approve-toolbar]'),errorBox=root.querySelector('[data-approval-error]');
  async function approve(){
    if(pendingApproval||!caseActions.onApprove||!scope.active)return;
    pendingApproval=true;approveButton.disabled=true;errorBox.hidden=true;
    approveButton.setAttribute('aria-busy','true');
    const label=approveButton.innerHTML;approveButton.innerHTML=workflowActionLabel('Aprobando…');
    try{
      await caseActions.onApprove();
      if(!scope.active)return;
      const badge=root.querySelector('[data-status-badge]');badge.className='dashboard-toolbar__badge is-approved';badge.textContent='Aprobada';
      approveButton.hidden=true;
      caseActions.onApprovalComplete?.();await actions.refresh();
    }catch(error){
      if(scope.active){approveButton.innerHTML=label;approveButton.disabled=false;errorBox.textContent=error.message||'No se pudo aprobar la decisión.';errorBox.hidden=false;}
    }finally{pendingApproval=false;approveButton.removeAttribute('aria-busy');}
  }
  if(approveButton)scope.listen(approveButton,'click',approve);
  api('/api/system/llm-status',{signal:scope.signal}).then(data=>{
    if(scope.active)root.querySelector('[data-ai-details]').textContent=data.configured?[data.provider,data.model].filter(Boolean).join(' · '):'Sin configurar';
  }).catch(()=>{if(scope.active)root.querySelector('[data-ai-details]').textContent='No disponible';});
  return {openDrawer,closeDrawer};
}
