import {createWorkflowActionBar} from "./workflow-action-bar.mjs";
import {scopeFor} from "./lifecycle.mjs";
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

export function decisionHero({step,decisionIndex,totalDecisions=3,title,description,panelItems=[]}){
  return '<section class="decision-config-hero dispatch-pro-hero assignment-config-hero d-page-hero">'
    +'<div class="dispatch-pro-hero-copy">'
      +'<div class="assignment-config-hero__badges">'
        +'<span class="dispatch-pro-hero-badge is-step">PASO '+esc(step?.number??3)+': '+esc(String(step?.label||"Configurar decisión").toUpperCase())+'</span>'
        +'<span class="assignment-decision-chip">DECISIÓN '+esc(String(decisionIndex).padStart(2,"0"))+' DE '+esc(totalDecisions)+'</span>'
      +'</div>'
      +'<h1>'+esc(title)+'</h1>'
      +'<p class="dispatch-pro-hero-lead">'+esc(description)+'</p>'
    +'</div>'
    +'<div class="dispatch-pro-hero-visual">'
      +'<div class="decision-config-decision-panel dispatch-pro-how-panel assignment-decision-panel">'
        +'<div class="dispatch-pro-how-title"><span>ESTA DECISIÓN</span></div>'
        +panelItems.map((item,index)=>(
          '<div class="decision-config-panel-item dispatch-pro-how-node">'
            +'<span class="dispatch-pro-how-icon">'+iconSvg(item.icon,"dispatch-pro-icon assignment-icon")+'</span>'
            +'<div><small>'+esc(item.label)+'</small><strong>'+esc(item.description)+'</strong></div>'
          +'</div>'
          +(index<panelItems.length-1?'<span class="dispatch-pro-how-connector" aria-hidden="true"></span>':'')
        )).join("")
      +'</div>'
    +'</div>'
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

export function decisionCaseCard({
  caseId,
  files=[],
  copyHook="data-config-copy-case",
  feedbackHook="data-config-copy-feedback",
  changeHook="data-config-change-data",
  status="",
  helper="",
  dataPackLabel="DATA PACK EN USO",
  validationSummary="",
  extraClass="",
}){
  const rawId=String(caseId||"");
  return '<details data-config-context class="d-data-context decision-config-case dispatch-case-card assignment-case-strip '+esc(extraClass)+'" aria-label="Decision Case y Data Pack en uso">'
    +'<summary class="decision-config-case__summary"><span>Decision Case <strong>'+esc(displayDecisionCaseId(rawId))+'</strong></span><small>Data Pack en uso</small><span class="decision-context-chevron" aria-hidden="true">⌄</span></summary>'
    +'<div class="decision-config-case__body">'
    +'<div class="assignment-case-strip__identity">'
      +'<span class="dispatch-case-identity__icon">'+iconSvg("folderOpen","dispatch-map-icon")+'</span>'
      +'<div><small class="assignment-case-strip__eyebrow">DECISION CASE</small>'
        +'<div class="dispatch-case-identity__idrow">'
          +'<strong title="'+esc(rawId)+'">'+esc(displayDecisionCaseId(rawId))+'</strong>'
          +'<button type="button" '+copyHook+' title="Copiar ID" aria-label="Copiar ID completo del caso">'+iconSvg("copy","dispatch-map-icon")+'</button>'
          +(status?'<span class="decision-config-case__status">'+esc(status)+'</span>':'')
        +'</div>'
        +(helper?'<small class="decision-config-case__helper">'+esc(helper)+'</small>':'')
        +'<span class="assignment-case-strip__feedback" '+feedbackHook+' aria-live="polite"></span>'
      +'</div>'
    +'</div>'
    +'<div class="decision-config-case__pack">'
      +'<div class="decision-config-case__pack-header">'
        +'<div class="assignment-case-strip__pack-title"><span>'+esc(dataPackLabel)+'</span>'+(validationSummary?'<em>'+esc(validationSummary)+'</em>':'')+'</div>'
        +'<button class="assignment-change-data" type="button" '+changeHook+'>'
          +iconSvg("refresh","assignment-icon")+'<span>Cambiar datos</span>'
        +'</button>'
      +'</div>'
      +'<div class="decision-config-case__files">'+files.join("")+'</div>'
    +'</div>'
  +'</div></details>';
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
  actionBars.get(root)?.dispose();
  root.querySelectorAll('dialog.d-config-dialog').forEach(dialog=>dialog.addEventListener('keydown',event=>{
    if(event.key!=="Escape"||!dialog.open)return;
    event.preventDefault();event.stopPropagation();dialog.close();
  }));
  const placeholder=root.querySelector('[data-config-summary]');
  if(!placeholder)return;
  const {ready=true,reason="",chips=[],reviewHook="data-config-review"}=JSON.parse(placeholder.dataset.configSummary);
  const {bar,button,update}=createWorkflowActionBar({label:"Tu configuración",variant:"configuration",onSelect:id=>{
    const section=root.querySelector('#'+CSS.escape(id));
    section?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:"center"});
  }});
  bar.classList.add("d-workflow-action-bar--config");
  button.setAttribute(reviewHook,"");
  update({kind:ready?"ready":"error",enabled:ready,message:ready?"Lista para revisar. Cambios guardados en esta sesión.":reason},{items:chips});
  placeholder.replaceWith(bar);
  const measure=()=>root.style.setProperty('--config-action-height',Math.ceil(bar.getBoundingClientRect().height)+'px');
  const observer=typeof ResizeObserver==='undefined'?null:new ResizeObserver(measure);
  observer?.observe(bar);measure();
  let release;
  const dispose=()=>{observer?.disconnect();release?.();root.style.removeProperty('--config-action-height');actionBars.delete(root);};
  release=scopeFor(root)?.own(dispose);
  actionBars.set(root,{dispose,update,items:chips});
}

export function updateConfigActionBar(root,{ready,reason=""}){
  const mounted=actionBars.get(root);
  mounted?.update({kind:ready?"ready":"error",enabled:ready,message:ready?"Lista para revisar. Cambios guardados en esta sesión.":reason},{items:mounted.items});
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
  const existing=[...document.querySelectorAll('link[rel="stylesheet"]')].find(link=>new URL(link.href,location.href).pathname===path);
  const link=existing||document.createElement('link');
  if(!existing){link.id=id;link.rel='stylesheet';document.head.append(link);}
  link.href=path+'?v='+version;
}
