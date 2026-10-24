import {ensureStylesheet} from "./styles.mjs";
import {createWorkflowActionBar,bindWorkflowActionBarLayout,WORKFLOW_ACTION_CLASS,workflowActionLabel} from "./workflow-action-bar.mjs";
import {createScope,scopeFor,trapFocus} from "./lifecycle.mjs";
import {esc} from "./shared.mjs";
import {iconSvg} from "./decision-ui.mjs";

function attr(name,value){
  if(value===false||value===null||value===undefined)return "";
  if(value===true)return " "+name;
  return " "+name+'="'+esc(String(value))+'"';
}

function attrs(values={}){
  return Object.entries(values).map(([name,value])=>attr(name,value)).join("");
}

export function displayDecisionCaseId(value){
  if(!value)return "—";
  return "DC-"+String(value).slice(0,8).toUpperCase();
}

/** Native review shell; callers own the rows, hooks, validation and execution. */
export function executionReviewDialog({title,accessibleLabel=title,rows=[],note="",dialogAttributes={},executeAttributes={},errorAttributes={}}){
  return '<dialog class="d-config-dialog d-execution-review" aria-label="'+esc(accessibleLabel)+'"'+attrs(dialogAttributes)+'><form method="dialog" class="d-execution-review__form">'
    +'<header class="d-execution-review__header"><span class="d-execution-review__eyebrow">ANTES DE EJECUTAR</span><h2>'+esc(title)+'</h2></header>'
    +'<div class="d-execution-review__rows dispatch-review-summary">'
      +rows.map(({label,value})=>'<p class="d-execution-review__row"><strong>'+esc(label)+'</strong><span>'+esc(value??"—")+'</span></p>').join("")
    +'</div>'
    +(note?'<p class="d-execution-review__note">'+esc(note)+'</p>':'')
    +'<p class="d-execution-review__error" role="alert"'+attrs({...errorAttributes,"data-config-review-error":true})+'></p>'
    +'<footer class="d-execution-review__actions"><button class="d-button d-button--secondary d-button--lg" value="cancel">Volver</button>'
      +'<button class="'+WORKFLOW_ACTION_CLASS+' d-button--primary" type="button"'+attrs(executeAttributes)+'>'+workflowActionLabel("Ejecutar decisión")+'</button></footer>'
  +'</form></dialog>';
}

export function middleEllipsis(value,max=36){
  const text=String(value||"—");
  if(text.length<=max)return text;
  const extension=text.toLowerCase().endsWith(".csv")?".csv":"";
  const stem=extension?text.slice(0,-4):text;
  const tailLength=Math.min(12,Math.max(8,Math.floor(max*.32)));
  const headLength=Math.max(10,max-tailLength-extension.length-1);
  return stem.slice(0,headLength)+"…"+stem.slice(-tailLength)+extension;
}

export function decisionSectionHeader({number,eyebrow,title,copy,icon,current}){
  return '<header class="decision-config-section__head assignment-section__head">'
    +'<span class="decision-config-section__icon assignment-section__icon">'+iconSvg(icon,"assignment-icon")+'</span>'
    +'<div class="decision-config-section__copy assignment-section__copy">'
      +'<span class="decision-config-section__eyebrow assignment-section__eyebrow">'+esc(number+' · '+eyebrow)+'</span>'
      +'<h2>'+esc(title)+'</h2>'
      +'<p>'+esc(copy)+'</p>'
    +'</div>'
    +(current?'<span class="decision-config-section__current assignment-section__current">'+esc(current)+'</span>':'')
  +'</header>';
}

export function decisionHero({step,decisionIndex,totalDecisions=3,title,description,panelItems=[],panelTitle="ESTA DECISIÓN",panelFootnote="",panelArtwork=true,className="decision-config-hero dispatch-pro-hero assignment-config-hero",reveal=false}){
  const hasDecision=decisionIndex!==undefined&&decisionIndex!==null&&decisionIndex!=="";
  const hasPanel=panelItems.length>0;
  return '<section class="'+esc(className)+' d-page-hero d-page-hero--workflow'+(hasPanel?'':' d-page-hero--copy-only')+'"'+attr("data-reveal",reveal)+'>'
    +'<div class="dispatch-pro-hero-copy">'
      +'<div class="d-hero-meta assignment-config-hero__badges">'
        +'<span class="d-hero-meta__step dispatch-pro-hero-badge is-step">PASO '+esc(step?.number??3)+' · '+esc(String(step?.label||"Configurar decisión").toUpperCase())+'</span>'
        +(hasDecision?'<span class="d-hero-meta__decision assignment-decision-chip">DECISIÓN '+esc(Number(decisionIndex))+' DE '+esc(totalDecisions)+'</span>':'')
      +'</div>'
      +'<h1>'+esc(title)+'</h1>'
      +'<p class="dispatch-pro-hero-lead">'+esc(description)+'</p>'
    +'</div>'
    +(hasPanel?'<details class="dispatch-pro-hero-visual"><summary>'+esc(panelTitle)+'</summary>'
      +(panelArtwork?'<img class="dispatch-pro-hero-watermark" src="/static/assets/dda-logistics.svg?v=workflow-hero" alt="">':'')
      +'<div class="decision-config-decision-panel dispatch-pro-how-panel assignment-decision-panel">'

        +panelItems.map((item,index)=>(
          '<div class="decision-config-panel-item dispatch-pro-how-node">'
            +'<span class="dispatch-pro-how-icon">'+iconSvg(item.icon,"dispatch-pro-icon assignment-icon")+'</span>'
            +'<div><small>'+esc(item.label)+'</small><strong>'+esc(item.description)+'</strong></div>'
          +'</div>'
          +(index<panelItems.length-1?'<span class="dispatch-pro-how-connector" aria-hidden="true"></span>':'')
        )).join("")
        +(panelFootnote?'<div class="dispatch-pro-how-history">'+iconSvg("history","dispatch-pro-icon")+'<span>'+esc(panelFootnote)+'</span></div>':'')
      +'</div>'
    +'</details>':'')
  +'</section>';
}

export function decisionDataFileCard({kind,dataset,countText,filtered=false,validated=dataset?.profile_json?.counts?.errors===0,extraClass=""}){
  const orders=kind==="orders";
  const fullName=dataset?.canonical_filename||dataset?.label||dataset?.original_filename||"Archivo sin nombre";
  return '<article class="decision-config-data-file dispatch-datapack-file is-'+esc(kind)+' assignment-case-file '+esc(extraClass)+'">'
    +'<span class="dispatch-datapack-file__accent" aria-hidden="true"></span>'
    +'<span class="dispatch-datapack-file__icon">'+iconSvg(orders?"clipboardList":"truck","dispatch-map-icon")+'</span>'
    +'<div class="dispatch-datapack-file__body">'
      +'<div class="dispatch-datapack-file__topline"><small>'+(orders?'ÓRDENES':'FLOTA')+'</small>'+(validated?'<span class="decision-config-data-file__validated">Validado</span>':'')+'</div>'
      +'<strong class="dispatch-datapack-file__name" title="'+esc(fullName)+'">'+esc(middleEllipsis(fullName))+'</strong>'
      +'<div class="dispatch-datapack-file__meta">'
        +'<span class="is-count" '+(orders&&filtered?'title="Filtros aplicados"':'')+'>'+esc(countText||"—")+'</span>'
      +'</div>'
    +'</div>'
  +'</article>';
}

export function decisionCaseCard({caseId,caseLabel='Decision Case',dataOwner='Sin asignar',files=[],copyHook="data-config-copy-case",feedbackHook="data-config-copy-feedback",changeHook="data-config-change-data",extraClass=""}){
 const rawId=String(caseId||'');
 return '<details data-config-context class="d-data-context decision-config-case dispatch-case-card assignment-case-strip '+esc(extraClass)+'" aria-label="Contexto del Case">'
  +'<summary class="decision-config-case__summary" title="Abrir contexto del Case" aria-label="Abrir contexto del Case"><span>Contexto del Case</span><span class="decision-context-chevron" aria-hidden="true">⌄</span></summary>'
  +'<div class="decision-config-case__body"><dl class="case-context-fields">'
  +'<div><dt>ID</dt><dd>'+esc(displayDecisionCaseId(rawId))+' <button type="button" '+copyHook+' aria-label="Copiar ID completo del caso">'+iconSvg('copy')+'</button><span '+feedbackHook+' aria-live="polite"></span></dd></div>'
  +'<div><dt>Nombre</dt><dd>'+esc(caseLabel||'Decision Case')+'</dd></div>'
  +'<div><dt>Data Pack</dt><dd>Órdenes + Flota</dd></div>'
  +'<div><dt>Data Owner</dt><dd>'+esc(dataOwner||'Sin asignar')+'</dd></div></dl>'
  +'<div class="decision-config-case__pack"><div class="decision-config-case__pack-header"><button class="assignment-change-data d-button d-button--secondary" type="button" '+changeHook+' title="Un Data Pack distinto inicia otro Case">'+iconSvg('refresh')+'<span>Cambiar Data Pack</span></button></div>'
  +'<div class="decision-config-case__files">'+files.join('')+'</div></div></div></details>';
}

/** Native disclosure, including keyboard interaction, shared by Map and Config. */
export function bindCaseContext(root){
  root.querySelectorAll('[data-config-context]').forEach(details=>{
    const sync=()=>{
      const label=(details.open?'Cerrar':'Abrir')+' contexto del Case';
      const summary=details.querySelector('summary');summary.title=label;summary.setAttribute('aria-label',label);
    };
    scopeFor(root)?.listen(details,'toggle',sync);sync();
  });
}

export function decisionChoiceCard({
  className="",
  icon,
  title,
  copy,
  selected=false,
  disabled=false,
  locked=false,
  tags=[],
  attributes={},
  disabledTitle="",
}){
  const classes=[
    "decision-config-option",
    "assignment-choice-card",
    className,
    selected?"is-selected":"",
    disabled?"is-disabled":"",
    locked?"is-locked":"",
  ].filter(Boolean).join(" ");
  const buttonAttrs={...attributes,"aria-pressed":String(Boolean(selected))};
  if(disabled||locked){
    buttonAttrs.disabled=true;
    buttonAttrs["aria-disabled"]="true";
  }
  if(disabledTitle)buttonAttrs.title=disabledTitle;
  return '<button type="button" class="'+esc(classes)+'"'+attrs(buttonAttrs)+'>'
    +'<span class="assignment-choice-card__icon">'+iconSvg(icon,"assignment-icon")+'</span>'
    +'<span class="assignment-choice-card__check">'+iconSvg("check","assignment-icon")+'</span>'
    +'<strong>'+esc(title)+'</strong><small>'+esc(copy)+'</small>'
    +tags.filter(Boolean).map(tag=>'<em>'+esc(tag)+'</em>').join("")
  +'</button>';
}

/** Informational only: no form names, state keys, or event hooks. */
export function decisionAdvancedOptionsSection({kind}){
  const items=kind==="scheduling"?[
    ["Buffer entre viajes","Agregá tiempo operativo mínimo entre dos usos del mismo recurso."],
    ["Ventanas por recurso","Definí calendarios específicos por vehículo o grupo."],
    ["Penalización por atraso","Controlá cuánto pesa el atraso relativo entre distintos grupos."],
  ]:[
    ["Límite de tercerización","Controlá cuánto volumen puede enviarse a terceros."],
    ["Utilización mínima por viaje","Definí un umbral mínimo de ocupación."],
    ["Reglas avanzadas por proveedor","Aplicá restricciones o penalizaciones por transportista."],
  ];
  return '<section class="assignment-section decision-advanced-options" aria-label="Opciones avanzadas">'
    +decisionSectionHeader({number:"04",eyebrow:"OPCIONES AVANZADAS",title:"Opciones avanzadas",copy:"Estas opciones estarán disponibles en próximas versiones.",icon:"slidersHorizontal"})
    +'<div class="decision-advanced-options__grid">'+items.map(([title,copy])=>
      '<button type="button" disabled aria-disabled="true" class="decision-advanced-option"><span>Próximamente</span><strong>'+esc(title)+'</strong><small>'+esc(copy)+'</small></button>'
    ).join("")+'</div></section>';
}

/** The configuration owners supply validation; the shared workflow owns the bar. */
export function configSummaryBar(options){
  return '<div data-config-summary="'+esc(JSON.stringify(options))+'"></div>';
}

const actionBars=new WeakMap();
export function mountConfigActionBar(root){
  bindCaseContext(root);
  actionBars.get(root)?.dispose();
  root.querySelectorAll('dialog.d-config-dialog').forEach(dialog=>dialog.addEventListener('keydown',event=>{
    trapFocus(event,dialog);
    if(event.key!=="Escape"||!dialog.open)return;
    event.preventDefault();event.stopPropagation();dialog.close();
  }));
  const placeholder=root.querySelector('[data-config-summary]');
  if(!placeholder)return;
  const {ready=true,blocked=false,reason="",chips=[],reviewHook="data-config-review"}=JSON.parse(placeholder.dataset.configSummary);
  const {bar,button,update}=createWorkflowActionBar({label:"Tu configuración",variant:"configuration",onSelect:id=>{
    const section=root.querySelector('#'+CSS.escape(id));
    attentionToConfig(section);
  }});
  bar.classList.add("d-workflow-action-bar--config");
  button.setAttribute(reviewHook,"");
  update({kind:ready?"ready":"error",enabled:ready,message:ready?"Lista para revisar. Cambios guardados en esta sesión.":reason},{items:chips});
  button.disabled=blocked;
  placeholder.replaceWith(bar);
  const disposeLayout=bindWorkflowActionBarLayout(root,bar);
  const measure=()=>root.style.setProperty('--config-action-height',Math.ceil(bar.getBoundingClientRect().height)+'px');
  const observer=typeof ResizeObserver==='undefined'?null:new ResizeObserver(measure);
  observer?.observe(bar);measure();
  let release;
  const dispose=()=>{disposeLayout();observer?.disconnect();release?.();root.style.removeProperty('--config-action-height');actionBars.delete(root);};
  release=scopeFor(root)?.own(dispose);
  actionBars.set(root,{dispose,update,button,items:chips});
}

export function attentionToConfig(target){
  if(!target)return;
  const scope=scopeFor(target);
  target.classList.remove('is-attention');
  void target.offsetWidth;
  target.classList.add('d-attention-target','is-attention');
  target.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'});
  scope?.timeout(()=>target.classList.remove('is-attention'),1800);
}

/** Decisions own their summaries and validation; opening review never routes. */
export function bindConfigReview({dialog,trigger,executeSelector,prepare,validate,onExecute}){
  if(!dialog||!trigger)return;
  const scope=createScope(dialog);
  let executing=false;
  scope.own(()=>{if(dialog.open)dialog.close();});
  scope.listen(dialog,'close',()=>{if(scope.active&&trigger.isConnected)trigger.focus({preventScroll:true});});
  scope.listen(trigger,'click',()=>{
    if(executing||!scope.active||validate?.())return;
    prepare?.();
    dialog.querySelector('[data-config-review-error]')?.replaceChildren();
    dialog.showModal();
  });
  scope.listen(dialog,'click',async event=>{
    const button=event.target.closest(executeSelector);
    if(!button)return;
    event.preventDefault();
    if(executing||!scope.active||validate?.())return;
    executing=true;
    button.disabled=true;
    button.setAttribute('aria-busy','true');
    dialog.close();
    try{await onExecute?.(button);}
    catch(error){
      if(!scope.active||!dialog.isConnected)return;
      executing=false;
      button.disabled=false;
      button.removeAttribute('aria-busy');
      const feedback=dialog.querySelector('[data-config-review-error]');
      if(feedback)feedback.textContent=error?.message||'No pudimos iniciar la ejecución. Volvé a intentar.';
      dialog.showModal();
    }
  });
}

export function updateConfigActionBar(root,{ready,reason="",blocked=false}){
  const mounted=actionBars.get(root);
  if(mounted)mounted.button.disabled=blocked;
  mounted?.update({kind:ready?"ready":"error",enabled:ready,message:ready?"Lista para revisar. Cambios guardados en esta sesión.":reason},{items:mounted.items});
  if(mounted)mounted.button.disabled=blocked;
}

export function decisionInfoNote({icon="info",title="",copy="",className=""}){
  return '<div class="decision-config-info-note '+esc(className)+'">'
    +'<span class="decision-config-info-note__icon">'+iconSvg(icon,"assignment-icon")+'</span>'
    +'<div>'+(title?'<strong>'+esc(title)+'</strong>':'')+(copy?'<span>'+esc(copy)+'</span>':'')+'</div>'
  +'</div>';
}

export function decisionEmptyState({icon="filter",title,copy,className=""}){
  return '<div class="decision-config-empty-state assignment-scope-empty '+esc(className)+'">'
    +iconSvg(icon,"assignment-icon")+'<div><strong>'+esc(title)+'</strong><span>'+esc(copy)+'</span></div>'
  +'</div>';
}

export function decisionRuleCard({index,title,summary="",body="",expanded=true,className=""}){
  const number=String(index).padStart(2,"0");
  return '<article class="decision-config-rule-card '+esc(className)+' '+(expanded?'is-expanded':'is-collapsed')+'">'
    +'<header><div><span>REGLA '+esc(number)+'</span><strong>'+esc(title)+'</strong>'+(summary?'<small>'+esc(summary)+'</small>':'')+'</div></header>'
    +'<div class="decision-config-rule-card__body">'+body+'</div>'
  +'</article>';
}

export function ensureDecisionConfigStyle(id,path,version="dark-config-phase4-v1"){
  return ensureStylesheet(id,path,version);
}

// Compatibility for modules already loaded before the foundation rollout.
export {decisionResultSummary} from './result-summary.mjs';
