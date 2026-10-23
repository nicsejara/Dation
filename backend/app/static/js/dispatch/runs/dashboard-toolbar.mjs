import {iconSvg} from "../decision-ui.mjs";
import {createScope,trapFocus} from '../lifecycle.mjs';
import {esc} from '../shared.mjs';
import {bindDashboardActions} from './dashboard-actions.mjs';
import {decisionStatusUi,shortRunId,solverStatusLabel} from '../assignment/assignment-dashboard-selectors.mjs';
import {downloadRunExport} from './export.mjs';
import {WORKFLOW_ACTION_CLASS,workflowActionLabel} from '../workflow-action-bar.mjs';

const icon=name=>iconSvg(name,"dashboard-toolbar__icon");
const actionLabel=(text,name)=>icon(name)+'<span>'+esc(text)+'</span>';

function detailRows(run,scheduling){
  const result=run.result_json||{},metrics=result.scenarios?.selected?.metrics||{},solver=result.engine?.solver||{};
  return [
    ['Run ID',run.id],['Estado',run.status],['Creada',run.created_at],['Inicio de ejecución',run.started_at],['Finalizada',run.completed_at],
    ['Motor',[result.engine?.name||run.engine_name,result.engine?.version||run.engine_version].filter(Boolean).join(' ')],
    ['Solver',solver.name||solver.method],['Estado solver',solver.status?solverStatusLabel(solver.status):null],
    ...(scheduling?[
      ['Assignment fuente',result.inputs?.assignment?.run_id||run.upstream_run_id],
      ['Viajes',metrics.total_trips],['Vehículos',metrics.vehicles_used],
      ['Inicio',metrics.schedule_start],['Fin',metrics.schedule_end],
    ]:[['Escenarios evaluados',result.analysis?.scenario_count]]),
    ['Huella',run.result_fingerprint||result.result_fingerprint],
    ['Órdenes',result.inputs?.orders?.filename||result.inputs?.orders?.label],
    ['Flota',result.inputs?.fleet?.label||result.inputs?.fleet?.filename],
  ].filter(([,value])=>value!==null&&value!==undefined&&value!=='');
}

export function renderDashboardToolbar(run,caseActions={},options={}){
  const scheduling=run.result_json?.schema_version==='scheduling_v1';
  const hero=options.placement==='hero';
  const status=decisionStatusUi(caseActions.status);
  const title=scheduling?'Planificación de despachos':'Asignación de carga';
  const approveLabel='Aprobar decisión';
  const drawerId='dashboard-run-details-'+crypto.randomUUID();
  const rows=detailRows(run,scheduling);
  const toolbar='<header class="dashboard-toolbar'+(hero?(scheduling?' scheduling-hero__actions':' assignment-hero__actions'):'')+'" data-dashboard-toolbar'+(hero?' data-toolbar-placement="hero"':'')+'>'
    +'<div class="dashboard-toolbar__identity"><span class="dashboard-toolbar__eyebrow">DDA LOGÍSTICA · DECISIÓN '+(scheduling?'02':'01')+'</span>'
      +'<div class="dashboard-toolbar__title"><strong>'+title+'</strong>'
        +'<span class="dashboard-toolbar__badge '+esc(status.className)+'" data-status-badge>'+esc(status.label)+'</span></div>'
      +'<small>Corrida '+esc(shortRunId(run.id))+'</small></div>'
    +'<div class="dashboard-toolbar__tools" aria-label="Herramientas de la decisión">'
      +(caseActions.onApprove&&caseActions.status!=='approved'?'<button type="button" data-approve-toolbar class="dashboard-toolbar__approve '+WORKFLOW_ACTION_CLASS+' d-button--primary">'+actionLabel(approveLabel,'checkCircle')+'</button>':'')
      +'<button type="button" data-after-approve class="dashboard-toolbar__continue '+WORKFLOW_ACTION_CLASS+' d-button--primary" hidden></button>'
      +'<button type="button" class="d-button d-button--secondary" data-rerun>'+actionLabel('Nueva corrida','refresh')+'</button>'
      +'<button type="button" class="d-button d-button--secondary dispatch-ai-fab" data-chat aria-expanded="false" aria-label="Abrir Dation IA">'+actionLabel('Dation IA','sparkles')+'</button>'
      +'<details class="dashboard-toolbar__menu" data-export-menu><summary aria-expanded="false">'+icon("download")+'<span>Exportar</span>'+icon("chevronDown")+'</summary>'
        +'<div class="dashboard-toolbar__menu-panel">'
          +'<button type="button" data-export-csv>'+icon("download")+'<div><strong>'+(scheduling?'Planificación CSV':'Asignación CSV')+'</strong><small>'+(scheduling?'Viajes, fechas y cargas':'Viajes, vehículos, órdenes y cargas')+'</small></div></button>'
          +'<button type="button" data-export-json>'+icon("fileJson")+'<div><strong>JSON técnico</strong><small>Resultado completo de la corrida</small></div></button>'
        +'</div></details>'
      +'<details class="dashboard-toolbar__menu" data-more-menu><summary aria-expanded="false">'+icon("moreHorizontal")+'<span>Más</span>'+icon("chevronDown")+'</summary>'
        +'<div class="dashboard-toolbar__menu-panel">'
          +'<button type="button" data-run-details aria-haspopup="dialog" aria-controls="'+drawerId+'">'+icon("info")+'<div><strong>Detalles de ejecución</strong><small>Motor, solver, archivos y huella</small></div></button>'
        +'</div></details>'
    +'</div><p class="dashboard-toolbar__status" data-next-decision-status role="status"></p>'
    +'<p class="dashboard-toolbar__error" data-approval-error role="alert" hidden></p></header>';
  const drawer='<div class="dashboard-toolbar__backdrop" data-run-drawer-backdrop hidden></div>'
    +'<aside class="dashboard-toolbar__drawer" data-run-drawer id="'+drawerId+'" hidden role="dialog" aria-modal="true" aria-labelledby="'+drawerId+'-title">'
      +'<header><div><span class="dashboard-toolbar__eyebrow">TRAZABILIDAD TÉCNICA</span><h2 id="'+drawerId+'-title">Detalles de ejecución</h2>'
        +'<p>Información persistida de esta corrida.</p></div><button type="button" data-close-drawer aria-label="Cerrar detalles de ejecución">'+icon("x")+'</button></header>'
      +'<dl class="dashboard-toolbar__details">'+rows.map(([key,value])=>'<div><dt>'+esc(key)+'</dt><dd>'+esc(value??'—')+'</dd></div>').join('')+'</dl>'
      +'</aside>';
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
    const tools=toolbar.querySelector('.dashboard-toolbar__tools').getBoundingClientRect();
    // Wrapped tools must remain reachable while either menu is open.
    const bounds=Math.max(innerHeight-tools.bottom-24,tools.top-24)>=80?tools:anchor;
    const left=Math.max(16,Math.min(innerWidth-width-16,anchor.right-width));
    const below=innerHeight-bounds.bottom-24,above=bounds.top-24;
    const up=below<180&&above>below,space=Math.max(80,up?above:below);
    panel.style.width=width+'px';panel.style.maxHeight=space+'px';
    panel.style.left=(left-anchor.left)+'px';panel.style.right='auto';
    const height=Math.min(panel.scrollHeight,space);
    panel.style.top=((up?bounds.top-height-8:bounds.bottom+8)-anchor.top)+'px';
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

  async function exportFile(event,handler){
    const button=event.currentTarget,original=button.innerHTML;
    closeMenus();button.disabled=true;button.textContent='Preparando archivo…';
    try{await handler();if(!scope.active)return;button.innerHTML=actionLabel('Exportado','check');}
    catch{if(scope.active)button.textContent='No se pudo exportar';}
    scope.timeout(()=>{button.innerHTML=original;button.disabled=false;},1200);
  }
  scope.listen(root.querySelector('[data-export-csv]'),'click',event=>exportFile(event,()=>downloadRunExport(run,'csv',{signal:scope.signal})));
  scope.listen(root.querySelector('[data-export-json]'),'click',event=>exportFile(event,()=>downloadRunExport(run,'json',{signal:scope.signal})));

  const actions=bindDashboardActions(root,caseActions);
  const approveButton=root.querySelector('[data-approve-toolbar]'),errorBox=root.querySelector('[data-approval-error]');
  const hero=toolbar.dataset.toolbarPlacement==='hero';
  const approveButtons=[...root.querySelectorAll('[data-approve-toolbar]')];
  const infeasible=Boolean(caseActions.approvalBlocked)||hero&&(run.result_json?.scenarios?.selected?.feasible===false||run.result_json?.scenarios?.selected?.solver?.status==='infeasible');
  approveButtons.forEach(button=>{button.disabled=caseActions.status==='approved'||infeasible;});
  async function approve(){
    if(!approveButton||pendingApproval||!caseActions.onApprove||!scope.active||infeasible||hero&&caseActions.status==='approved')return;
    pendingApproval=true;approveButtons.forEach(button=>button.disabled=true);errorBox.hidden=true;
    approveButton.setAttribute('aria-busy','true');
    const label=approveButton.innerHTML;approveButton.innerHTML=workflowActionLabel('Aprobando…');
    try{
      await caseActions.onApprove();
      if(!scope.active)return;
      const badge=root.querySelector('[data-status-badge]');badge.className='dashboard-toolbar__badge is-approved';badge.textContent='Aprobada';
      if(hero){
        caseActions.status='approved';
        approveButtons.forEach(button=>{button.disabled=true;button.innerHTML=actionLabel(run.result_json?.schema_version==='scheduling_v1'?'Planificación aprobada':'Decisión aprobada','checkCircle');});
        const status=root.querySelector('[data-assignment-hero-status]');
        if(status){status.className='assignment-hero__status is-consistent';status.innerHTML=actionLabel('Decisión aprobada','checkCircle');}
      }else approveButton.hidden=true;
      await caseActions.onApprovalComplete?.();if(scope.active)await actions.refresh();
    }catch(error){
      if(scope.active){
        approveButton.innerHTML=label;approveButtons.forEach(button=>button.disabled=Boolean(error.workflowGate));errorBox.textContent=error.message||'No se pudo aprobar la decisión.';errorBox.hidden=false;
        if(error.workflowGate&&caseActions.onRefresh){
          const refresh=document.createElement('button');refresh.type='button';refresh.className='d-button d-button--secondary';refresh.textContent='Actualizar decisión';
          scope.listen(refresh,'click',async()=>{refresh.disabled=true;try{await caseActions.onRefresh();}catch{if(scope.active){refresh.disabled=false;refresh.textContent='Reintentar actualización';}}});errorBox.append(refresh);
        }
      }
    }finally{pendingApproval=false;approveButton.removeAttribute('aria-busy');}
  }
  approveButtons.forEach(button=>scope.listen(button,'click',approve));
  return {openDrawer,closeDrawer};
}
