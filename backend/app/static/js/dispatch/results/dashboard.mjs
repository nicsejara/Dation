import {esc,errorBox} from '../shared.mjs';
import {scopeFor,trapFocus} from '../lifecycle.mjs';
import {PackageClient,readPackage,executiveKpis,assertBinding} from './package.mjs';
import {sankeyMarkup,ganttMarkup,highlightSankey} from './visuals.mjs';
import {display,tableMarkup,factsMarkup,alternativesMarkup} from './details.mjs';
import {decisionRail,bindDecisionRail} from '../navigation/decision-nav.mjs';
import {dashboardHeroVisual,bindDashboardHeroVisual} from '../runs/dashboard-hero.mjs';
import {renderDashboardToolbar,bindDashboardToolbar} from '../runs/dashboard-toolbar.mjs';
import {renderAssistantLauncher,bindAssistantLauncher} from '../runs/contextual-assistant.mjs';
import {downloadRunExport} from '../runs/export.mjs';
const button=(label,attrs='')=>'<button type="button" class="d-button d-button--secondary" '+attrs+'>'+esc(label)+'</button>';

export async function render(root,run,onRerun,caseActions={}){
  const scope=scopeFor(root),client=new PackageClient(run,{signal:scope.signal});
  scope.own(()=>client.clearSelection());
  root.innerHTML='<section class="dispatch-panel" role="status">Cargando resultado publicado…</section>';
  let response,p;
  try{response=await client.result();p=readPackage(run,response);}catch(error){if(scope.active)errorBox(root,error,()=>caseActions.onRefresh?.());return;}
  if(!scope.active)return;
  const scheduling=p.result_schema==='day_scheduling_v1',kind=scheduling?'scheduling':'assignment';
  const safeActions={...caseActions,onApprove:undefined};
  const {toolbar,drawer}=renderDashboardToolbar(run,safeActions,{placement:'hero'});
  const tabs=scheduling?['schedule','trips','resources','service','exceptions','evidence']:['plan','demand','resources','alternatives','exceptions','evidence'];
  const labels={plan:'Plan',demand:'Demand',resources:'Resources',alternatives:'Alternatives',exceptions:'Exceptions',evidence:'Evidence',schedule:'Schedule',trips:'Trips',service:'Service'};
  const m=p.metrics,summary=p.summary.facts;
  const recommendation=scheduling?display(m.scheduled_trips.scheduled)+' de '+display(m.scheduled_trips.total)+' viajes aprobados programados.':
    'Cubrir '+display(m.demand_coverage.assigned)+' '+p.context.primary_dimension+' mediante '+display(m.trip_count)+' viajes y '+display(m.resources_used)+' recursos.';
  root.className='dispatch assignment-dashboard-v2 d-decision-dashboard ultimate-results'+(scheduling?' dispatch-scheduling-dashboard':'');
  root.dataset.runId=run.id;root.dataset.resultFingerprint=run.result_fingerprint;
  root.innerHTML='<div class="assignment-dashboard-v2__rail">'+(caseActions.railMarkup||decisionRail(caseActions))+'</div><main class="assignment-dashboard-v2__main">'
    +'<section class="dispatch-panel assignment-dashboard-v2__section assignment-dashboard-v2__hero d-dashboard-hero" id="dispatch-hero"><div class="dashboard-hero__content"><div class="assignment-hero__content"><span class="dispatch-kicker">'+(scheduling?'DECISIÓN 02 · DAY SCHEDULING':'DECISIÓN 01 · TRANSPORT PLAN')+'</span><h1>'+(scheduling?'Programación recomendada':'Plan de transporte recomendado')+'</h1><p class="assignment-hero__headline">'+esc(recommendation)+'</p><p class="assignment-hero__lead">'+esc(p.context.case_name)+' · '+esc(p.context.node_policy.primary_goal)+' · '+esc(p.context.planning_start)+' → '+esc(p.context.planning_end)+' · Modelo v'+esc(p.context.logistics_model_version)+' · '+esc(p.decision.status)+'</p></div></div>'+dashboardHeroVisual(kind)+toolbar+'</section>'
    +'<section aria-label="Indicadores certificados"><h2 class="ultimate-results__heading">Indicadores de la decisión</h2><div class="assignment-essential__kpi-strip">'+executiveKpis(p).map(([key,label,value,format])=>'<article class="assignment-essential__kpi is-descriptive" data-executive-kpi="'+esc(key)+'"><div class="assignment-essential__kpi-top"><span>'+esc(label)+'</span></div><strong>'+esc(display(value,format))+'</strong><p>'+(format==='days'?'Días certificados':key==='on_time_ratio'?'ON_TIME + AT_RISK; no equivale a ON_TIME estricto.':'Publicado por el motor')+'</p></article>').join('')+'</div></section>'
    +'<section class="dispatch-panel ultimate-results__panel" data-primary><h2>'+(scheduling?'Programación diaria':'Flujo del plan de transporte')+'</h2><div data-chart role="status">Cargando visual certificada…</div><p data-selection-status role="status"></p></section>'
    +'<details class="dispatch-panel ultimate-results__panel" data-details><summary>Análisis detallado</summary><div class="ultimate-results__tabs" role="tablist" aria-label="Análisis de la decisión">'+tabs.map((id,i)=>'<button type="button" class="d-button d-button--secondary" role="tab" id="tab-'+id+'" aria-selected="'+(i===0)+'" aria-controls="ultimate-analysis-panel" tabindex="'+(i===0?'0':'-1')+'" data-tab="'+id+'">'+labels[id]+'</button>').join('')+'</div><div id="ultimate-analysis-panel" role="tabpanel" aria-labelledby="tab-'+tabs[0]+'" tabindex="0" data-detail-panel></div></details>'
    +'<section class="dispatch-panel ultimate-results__panel" data-review><h2>Revisión de la decisión</h2><p>'+esc(p.approval_review.decision_ready_for_review?'Resultado listo para revisión.':'El resultado requiere revisar sus bloqueos.')+'</p>'+factsMarkup({'Estado':p.approval_review.decision_ready_for_review?'Listo para revisión':'Requiere revisión','Cobertura':({FULL:'Completa',PARTIAL:'Parcial',NONE:'Sin cobertura',UNKNOWN:'No certificada'})[p.approval_review.coverage_status],'Restricciones obligatorias':p.approval_review.hard_constraints_satisfied===true?'Cumplidas':p.approval_review.hard_constraints_satisfied===false?'Incumplidas':'No certificadas','Excepciones':p.approval_review.exception_count,'Supuestos':p.approval_review.assumption_count,...(scheduling?{'Viajes programados':display(p.approval_review.scheduled_ratio,'ratio'),'Cumplimiento esperado':display(p.approval_review.expected_delivery_compliance,'ratio')}:{})})+'<p data-overlay-status></p><div class="ultimate-results__review-actions">'+button('Revisar excepciones','data-review-exceptions')+button('Consultar a Dation IA','data-review-ai')+button('Verificar para aprobar','data-check-review')+'<button type="button" class="d-button d-button--primary" data-approve-package disabled>Aprobar decisión</button></div><p data-review-feedback role="status"></p></section></main>'
    +drawer+'<div class="dashboard-toolbar__backdrop" data-entity-backdrop hidden></div><aside class="dashboard-toolbar__drawer ultimate-results__entity" role="dialog" aria-modal="true" aria-labelledby="ultimate-entity-title" tabindex="-1" data-entity-drawer hidden><header><h2 id="ultimate-entity-title">Detalle del viaje</h2>'+button('Cerrar','data-entity-close aria-label="Cerrar detalle del viaje"')+'</header><div data-entity-body></div>'+button('Consultar a Dation IA sobre este viaje','data-entity-ai')+'</aside>'
    +'<aside class="dispatch-chat dispatch-panel ultimate-results__assistant" id="assistant-'+esc(run.id)+'" role="dialog" aria-modal="true" aria-labelledby="ultimate-ai-title" tabindex="-1" hidden data-assistant><header><h2 id="ultimate-ai-title">Dation IA</h2>'+button('Cerrar','data-ai-close aria-label="Cerrar Dation IA"')+'</header><p data-ai-binding></p><p>Explica evidencia publicada. Los cambios de restricciones requieren otra corrida.</p><form><label>Modo<select name="mode"><option value="EXPLAIN">Explicar</option><option value="EXPLORE">Explorar evidencia</option><option value="COMPARE" '+(p.alternatives.length?'':'disabled')+'>Comparar alternativas publicadas</option><option value="REVIEW">Revisar para aprobar</option></select></label><label>Pregunta<textarea name="question" maxlength="4000" required></textarea></label><button class="d-button d-button--primary" type="submit">Consultar</button></form><p class="ultimate-results__answer" data-ai-answer role="status"></p></aside>'+renderAssistantLauncher(run);
  bindDashboardHeroVisual(root);bindDecisionRail(root,caseActions);bindDashboardToolbar(root,run,{onRerun,caseActions:safeActions});
  const find=selector=>root.querySelector(selector);
  const feedback=(selector,error)=>{find(selector).textContent=error?.message||String(error);};
  let projection=p.primary_visual.projection;
  try{if(projection.mode==='REFERENCE')projection=(await client.get('primary-visual')).projection;
    if(scope.active)find('[data-chart]').innerHTML=scheduling?ganttMarkup(projection):sankeyMarkup(projection);
  }catch(error){if(scope.active)feedback('[data-chart]',error);}
  if(!scope.active)return;
  let overlay=response.approval_overlay;
  function setOverlay(value){overlay=value;const freshness={CURRENT:'Vigente',STALE:'Requiere actualizar el contexto',SUPERSEDED:'Corrida reemplazada',UNKNOWN:'Vigencia no confirmada'};
    const blockers={INTEGRITY_CHECK_REQUIRED:'Verificá la integridad para revisar la aprobación',REFRESH_REQUIRED:'Actualizá la decisión antes de reintentar',STALE_CONTEXT:'El contexto cambió',NOT_OWNER:'La aprobación requiere un responsable autorizado',VIEWER:'Acceso de sólo lectura'};
    find('[data-overlay-status]').textContent=(freshness[value.freshness]||value.freshness)+' · '+(value.approval_blockers.map(code=>blockers[code]||code).join(' · ')||'Sin bloqueos actuales');find('[data-approve-package]').disabled=!value.approval_allowed||!caseActions.onApprove;}
  setOverlay(overlay);
  scope.listen(find('[data-check-review]'),'click',async event=>{const b=event.currentTarget;b.disabled=true;
    try{const review=await client.get('approval-review');if(scope.active){setOverlay(review.approval_overlay);feedback('[data-review-feedback]','Integridad verificada; permisos actualizados.');}}
    catch(error){if(scope.active)feedback('[data-review-feedback]',error);}finally{if(scope.active)b.disabled=false;}});
  scope.listen(find('[data-approve-package]'),'click',async event=>{if(!overlay.approval_allowed)return;const b=event.currentTarget;b.disabled=true;
    try{await caseActions.onApprove();if(!scope.active)return;await caseActions.onApprovalComplete?.();if(scope.active){const r=await client.get('approval-review');setOverlay(r.approval_overlay);}}
    catch(error){if(scope.active){feedback('[data-review-feedback]',error);setOverlay({...overlay,approval_allowed:false,approval_blockers:['REFRESH_REQUIRED']});}}});

  let dataset=tabs[0],offset=0,page=null,tableGeneration=0,options={search:'',filter:'',sort:null,direction:1};
  const panel=find('[data-detail-panel]'),disclosure=find('[data-details]');
  async function loadTable(){
    const generation=++tableGeneration,current=dataset;panel.innerHTML='<p role="status">Cargando datos publicados…</p>';
    try{
      if(current==='alternatives'){
        const status=await client.get('analysis-status');if(!scope.active||generation!==tableGeneration)return;
        panel.innerHTML=alternativesMarkup(p,status.status);return;
      }
      const result=await client.page(current,offset);
      if(current==='resources'&&!scheduling){const caps=await client.get('resource-capacities');result.rows=result.rows.map(r=>({...r,published_capacity:caps.capacities[r.resource_id]??null}));}
      if(!scope.active||generation!==tableGeneration)return;
      page=result;
      panel.innerHTML=(current==='evidence'?'<h3>Contexto publicado</h3>'+factsMarkup({case:p.context.case_name,horizon:p.context.planning_start+' → '+p.context.planning_end,model_version:p.context.logistics_model_version,data_pack_version:p.context.data_pack_version,case_policy:p.context.case_policy,node_policy:p.context.node_policy,engine:p.engine,solver:p.evidence.solver,policy:p.evidence.policy,transit:p.context.display_metadata?.transit_model_version||p.engine.transit_model_version}):'')
        +(current==='exceptions'?'<h3>Excepciones de negocio, factibilidad, policy y datos</h3>'+factsMarkup({business_exceptions:p.exceptions.filter(e=>e.category==='BUSINESS'),feasibility:p.exceptions.filter(e=>e.category==='FEASIBILITY'),policy:p.exceptions.filter(e=>e.category==='POLICY'),data:p.exceptions.filter(e=>e.category==='DATA'),assumptions:p.assumptions})+'<p>Los errores técnicos se muestran como errores de recuperación, no como excepciones del negocio.</p>':'')
        +'<p>Filas '+(page.total?offset+1:0)+'–'+(offset+page.rows.length)+' de '+page.total+'. Búsqueda, filtro y orden sobre esta página.</p><div class="ultimate-results__filters"><label>Buscar en esta página<input type="search" data-search maxlength="128"></label><label>Filtrar texto publicado<input data-filter maxlength="128"></label>'+button('Exportar plan completo','data-table-export')+'</div><div data-table></div><div class="ultimate-results__pagination">'+button('Anterior','data-page-prev '+(offset===0?'disabled':''))+button('Siguiente','data-page-next '+(offset+page.rows.length>=page.total?'disabled':''))+'</div>';
      find('[data-search]').value=options.search;find('[data-filter]').value=options.filter;renderTable();
    }catch(error){if(scope.active&&generation===tableGeneration)panel.innerHTML='<p role="alert">'+esc(error.message)+'</p>'+button('Reintentar','data-table-retry');}
  }
  function renderTable(){find('[data-table]').innerHTML=tableMarkup(dataset,p,page,options);}
  function activateTab(id){dataset=id;offset=0;options={search:'',filter:'',sort:null,direction:1};root.querySelectorAll('[data-tab]').forEach(b=>{b.setAttribute('aria-selected',String(b.dataset.tab===id));b.tabIndex=b.dataset.tab===id?0:-1;});panel.setAttribute('aria-labelledby','tab-'+id);loadTable();}
  scope.listen(disclosure,'toggle',()=>{disclosure.querySelector('summary').setAttribute('aria-expanded',String(disclosure.open));if(disclosure.open&&!page)loadTable();});
  scope.listen(find('[data-review-exceptions]'),'click',()=>{disclosure.open=true;activateTab('exceptions');scope.timeout(()=>panel.focus(),0);});
  scope.listen(panel,'input',event=>{if(event.target.matches('[data-search]'))options.search=event.target.value;if(event.target.matches('[data-filter]'))options.filter=event.target.value;if(page&&find('[data-table]'))renderTable();});
  scope.listen(root,'keydown',event=>{const tab=event.target.closest('[data-tab]');if(tab&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const i=tabs.indexOf(tab.dataset.tab),next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(i+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;activateTab(tabs[next]);find('[data-tab="'+tabs[next]+'"]').focus();}});

  const entityDrawer=find('[data-entity-drawer]'),entityBackdrop=find('[data-entity-backdrop]'),assistant=find('[data-assistant]');
  const assistantBackdrop=document.createElement('div');assistantBackdrop.className='dashboard-toolbar__backdrop';assistantBackdrop.hidden=true;assistant.before(assistantBackdrop);
  const historyDetails=document.createElement('details');historyDetails.innerHTML='<summary tabindex="0">Conversaciones guardadas de esta corrida</summary><div data-copilot-history></div>';assistant.append(historyDetails);
  let historyGeneration=0;
  async function loadHistory(offset=0){const generation=++historyGeneration,body=historyDetails.querySelector('[data-copilot-history]');body.textContent='Recuperando respuestas guardadas…';
    try{const history=await client.get('copilot-history',{offset});if(!scope.active||generation!==historyGeneration)return;
      for(const row of history.rows)assertBinding(row.receipt.provenance,client.binding);
      body.innerHTML=history.rows.map(row=>'<article><h3>'+esc(row.question)+'</h3><p>'+esc(row.receipt.mode)+' · '+esc(row.receipt.selected_entity?.id||'Toda la corrida')+'</p><p class="ultimate-results__answer">'+esc(row.receipt.answer)+'</p><details><summary tabindex="0">Contexto original de la respuesta</summary>'+factsMarkup({run_id:row.receipt.provenance.run_id,result_fingerprint:row.receipt.provenance.result_fingerprint,context_hash:row.receipt.context_hash,prompt_version:row.prompt_version,provider:row.provider,model:row.model})+'</details></article>').join('')||(offset?'Sin más respuestas guardadas.':'Todavía no hay respuestas guardadas.');
      if(history.next_offset!=null){const next=document.createElement('button');next.type='button';next.className='d-button d-button--secondary';next.textContent='Respuestas anteriores';next.onclick=()=>loadHistory(history.next_offset);body.append(next);}
    }catch(error){if(scope.active&&generation===historyGeneration)body.textContent=error.message;}}
  scope.listen(historyDetails,'toggle',()=>{if(historyDetails.open)loadHistory();});
  let selection=null,returnEntity=null,returnAssistant=null,assistantGeneration=0,selectedAlternatives=[],visualGeneration=0;
  const turnIds=new Map();
  function assistantBusy(busy){
    const form=assistant.querySelector('form');form.elements.mode.disabled=busy;form.elements.question.disabled=busy;form.querySelector('[type=submit]').disabled=busy;
    assistant.setAttribute('aria-busy',String(busy));root.dispatchEvent(new CustomEvent('dispatch:assistant-busy',{detail:{busy}}));
  }
  function closeEntity(){client.clearSelection();entityDrawer.hidden=true;entityBackdrop.hidden=true;document.body.classList.remove('dashboard-drawer-open');returnEntity?.isConnected&&returnEntity.focus();}
  function closeAssistant(){assistantGeneration++;assistantBusy(false);assistant.hidden=true;assistantBackdrop.hidden=true;document.body.classList.remove('dashboard-drawer-open');find('[data-chat]').setAttribute('aria-expanded','false');returnAssistant?.isConnected&&returnAssistant.focus();}
  scope.own(()=>document.body.classList.remove('dashboard-drawer-open'));
  async function selectEntity(type,id,trigger,graphNodeId=null){
    const generation=++visualGeneration;client.clearSelection();
    if(!scheduling&&projection.type==='SANKEY'){highlightSankey(root,projection,graphNodeId);feedback('[data-selection-status]',type+' · '+id);if(type!=='TRIP')return;}
    returnEntity=trigger;entityDrawer.hidden=false;entityBackdrop.hidden=false;document.body.classList.add('dashboard-drawer-open');find('[data-entity-body]').innerHTML='<p role="status">Cargando evidencia del viaje…</p>';find('[data-entity-ai]').disabled=true;find('[data-entity-close]').focus();
    try{
      if(graphNodeId){const resolved=await client.get('visual-entities/'+encodeURIComponent(graphNodeId));if(!scope.active||generation!==visualGeneration||entityDrawer.hidden)return;
        if(resolved.selection?.graph_node_id!==graphNodeId||resolved.selection.entity_type!=='TRIP')throw new Error('VISUAL_ENTITY_BINDING_MISMATCH');id=resolved.selection.entity_id;}
      const result=await client.select(type,id);if(!scope.active||generation!==visualGeneration||entityDrawer.hidden)return;selection=result.selected;
      const transport=result.data.transport;
      const trip=transport?.trip||{},schedule=result.data.schedule;
      find('[data-entity-body]').innerHTML=factsMarkup({'Viaje':id,'Órdenes':trip.orders?.map(a=>a.order_id),'Origen':trip.origin_id,'Destino':trip.destination_id,'Recurso':trip.resource_id,
        'Origen del recurso':trip.resource_source==='OWN'?'Propio':'Tercerizado','Carga':trip.total_load,'Capacidad garantizada':trip.guaranteed_capacity,'Utilización certificada':display(trip.utilization,'ratios'),
        [scheduling?'Costo heredado de D1':'Costo estimado certificado']:display(trip.estimated_cost,'money'),
        ...(schedule?{'Salida':schedule.dispatch_date,'Llegada esperada':schedule.expected_arrival_date,'Fecha objetivo':schedule.delivery_due_date,'Margen · días':schedule.schedule_margin_days,'Estado certificado':schedule.status,'Disponible nuevamente':schedule.available_again}:{}),
        'Razones publicadas':result.data.reasons.map(r=>r.code)})+'<details><summary tabindex="0">Evidencia y trazabilidad del viaje</summary>'+factsMarkup({provenance:result.data.provenance,upstream:transport?.provenance,evidence:result.data.reasons,allocations:trip.orders})+'</details>';find('[data-entity-ai]').disabled=false;
    }catch(error){if(scope.active&&generation===visualGeneration&&error.name!=='AbortError')find('[data-entity-body]').innerHTML='<p role="alert">'+esc(error.message)+'</p>';}
  }
  function openAssistant(mode='EXPLAIN',selected=null,alternatives=[]){
    if(!entityDrawer.hidden)closeEntity();assistantGeneration++;selection=selected;selectedAlternatives=alternatives;returnAssistant=document.activeElement;
    assistantBusy(false);assistant.hidden=false;assistantBackdrop.hidden=false;document.body.classList.add('dashboard-drawer-open');find('[data-chat]').setAttribute('aria-expanded','true');assistant.querySelector('[name=mode]').value=mode;
    find('[data-ai-binding]').textContent=selected?selected.entity_type+' · '+selected.entity_id:'Corrida '+run.id.slice(0,8);find('[data-ai-binding]').title='Run '+run.id+' · '+run.result_fingerprint;
    find('[data-ai-answer]').textContent='';assistant.querySelector('textarea').focus();
  }
  bindAssistantLauncher(root,()=>openAssistant(),{avoidSelector:'[data-dashboard-toolbar] .dashboard-toolbar__tools > .d-button,[data-dashboard-toolbar] .dashboard-toolbar__tools > details > summary,[data-dashboard-toolbar] .dashboard-toolbar__menu-panel button'});
  scope.listen(find('[data-review-ai]'),'click',()=>openAssistant('REVIEW'));
  scope.listen(find('[data-entity-ai]'),'click',()=>openAssistant('EXPLORE',selection));
  scope.listen(find('[data-entity-close]'),'click',closeEntity);scope.listen(entityBackdrop,'click',closeEntity);scope.listen(find('[data-ai-close]'),'click',closeAssistant);
  scope.listen(assistantBackdrop,'click',closeAssistant);
  scope.listen(assistant.querySelector('[name=mode]'),'change',()=>{assistantGeneration++;find('[data-ai-answer]').textContent='';});
  scope.listen(assistant.querySelector('[name=question]'),'input',()=>{find('[data-ai-answer]').textContent='';});
  scope.listen(document,'keydown',event=>{const dialog=!assistant.hidden?assistant:!entityDrawer.hidden?entityDrawer:null;if(!dialog)return;trapFocus(event,dialog);if(event.key==='Escape'){event.preventDefault();dialog===assistant?closeAssistant():closeEntity();}});
  scope.listen(assistant.querySelector('form'),'submit',async event=>{
    event.preventDefault();const form=event.currentTarget,question=form.elements.question.value.trim();if(!question)return;
    const generation=++assistantGeneration,mode=form.elements.mode.value,selected=selection,alt=mode==='COMPARE'?(selectedAlternatives.length?selectedAlternatives:p.alternatives.map(a=>a.alternative_id)):[];
    assistantBusy(true);find('[data-ai-answer]').textContent='Consultando evidencia publicada…';
    try{const data=await client.context(mode,selected,alt);if(!scope.active||generation!==assistantGeneration)return;const key=data.context.context_hash+'|'+question;
      if(!turnIds.has(key))turnIds.set(key,crypto.randomUUID());const answer=await client.ask(data.context,question,turnIds.get(key));
      if(!scope.active||generation!==assistantGeneration)return;
      const historical=answer.approval_overlay?.freshness!=='CURRENT';
      find('[data-ai-answer]').textContent=(answer.approval_state==='APPROVED'?(historical?'Decisión aprobada · corrida histórica.':'Decisión aprobada.'):(historical?'Recomendación histórica.':'Recomendación actual.'))+'\n'+answer.answer;
    }catch(error){if(scope.active&&generation===assistantGeneration)feedback('[data-ai-answer]',error);}finally{if(scope.active&&generation===assistantGeneration)assistantBusy(false);}
  });
  scope.listen(root,'click',event=>{
    const entity=event.target.closest('[data-entity-type]');if(entity){selectEntity(entity.dataset.entityType,entity.dataset.entityId,entity,entity.dataset.graphNode||null);return;}
    const tab=event.target.closest('[data-tab]');if(tab){activateTab(tab.dataset.tab);return;}
    const compare=event.target.closest('[data-compare]');if(compare){openAssistant('COMPARE',null,[compare.dataset.compare]);return;}
    if(event.target.closest('[data-page-prev]')){offset=Math.max(0,offset-25);loadTable();}
    if(event.target.closest('[data-page-next]')){offset+=25;loadTable();}
    const sort=event.target.closest('[data-sort]');if(sort){options.direction=options.sort===sort.dataset.sort?-options.direction:1;options.sort=sort.dataset.sort;renderTable();find('[data-sort="'+CSS.escape(options.sort)+'"]').focus();}
    if(event.target.closest('[data-table-retry]'))loadTable();
    const exportButton=event.target.closest('[data-table-export]');if(exportButton){exportButton.disabled=true;downloadRunExport(run,'csv',{signal:scope.signal}).catch(error=>feedback('[data-review-feedback]',error)).finally(()=>{if(scope.active)exportButton.disabled=false;});}
  });
  scope.listen(root,'keydown',event=>{const entity=event.target.closest('svg [data-entity-type]');if(entity&&['Enter',' '].includes(event.key)){event.preventDefault();selectEntity(entity.dataset.entityType,entity.dataset.entityId,entity,entity.dataset.graphNode||null);}});
}
