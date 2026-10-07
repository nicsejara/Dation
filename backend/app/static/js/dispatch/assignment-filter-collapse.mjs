const STYLE_ID="assignment-filter-collapse-styles";
const ROW_SELECTOR=".assignment-config-root .assignment-filter-row:not(.is-invalid)";
const expandedKeys=new Set();
const knownKeys=new Set();
let observer=null;
let scheduled=false;

function rowKey(row){
  const label=row.querySelector(".assignment-filter-row__head strong")?.textContent?.trim();
  return label||String(row.dataset.filterIndex||"");
}

function categorySummary(row){
  const selected=[...row.querySelectorAll("[data-filter-category]:checked")]
    .map(input=>input.closest("label")?.querySelector("span")?.textContent?.trim())
    .filter(Boolean);
  if(!selected.length)return "Sin valores seleccionados";
  if(selected.length<=2)return selected.join(" · ");
  return selected.slice(0,2).join(" · ")+" +"+(selected.length-2);
}

function dateSummary(row){
  const preset=row.querySelector("[data-filter-date-preset]");
  if(preset&&preset.value!=="custom"){
    const label=preset.options[preset.selectedIndex]?.textContent?.trim();
    if(label)return label;
  }
  const from=row.querySelector("[data-filter-date-from]")?.value;
  const to=row.querySelector("[data-filter-date-to]")?.value;
  if(from&&to)return from+" → "+to;
  return "Rango de fechas aplicado";
}

function numberSummary(row){
  const min=row.querySelector("[data-filter-number-min]")?.value;
  const max=row.querySelector("[data-filter-number-max]")?.value;
  if(min!==undefined&&max!==undefined&&min!==""&&max!=="")return min+" → "+max;
  return "Rango aplicado";
}

function filterSummary(row){
  if(row.querySelector("[data-filter-category]"))return categorySummary(row);
  if(row.querySelector("[data-filter-date-preset],[data-filter-date-from]"))return dateSummary(row);
  if(row.querySelector("[data-filter-number-min],[data-filter-number-max]"))return numberSummary(row);
  return "Filtro aplicado";
}

function chevronSvg(){
  return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>';
}

function ensureStyles(){
  if(document.getElementById(STYLE_ID))return;
  const style=document.createElement("style");
  style.id=STYLE_ID;
  style.textContent=`
.assignment-config-root .assignment-filter-row.is-collapsible{padding:0;overflow:hidden;transition:border-color .18s ease,box-shadow .18s ease,background .18s ease}
.assignment-config-root .assignment-filter-row.is-collapsible:hover{border-color:#c8dadd}
.assignment-config-root .assignment-filter-row.is-collapsible .assignment-filter-row__head{margin:0;padding:13px 14px;gap:8px;background:#fbfcfd}
.assignment-config-root .assignment-filter-row.is-collapsible:not(.is-collapsed) .assignment-filter-row__head{border-bottom:1px solid #e4ebed}
.assignment-config-root .assignment-filter-row.is-collapsible .assignment-filter-row__head>div:first-child{display:grid;grid-template-columns:auto auto;gap:2px 8px;align-items:baseline;min-width:0}
.assignment-config-root .assignment-filter-row.is-collapsible .assignment-filter-row__summary{grid-column:1/-1;display:none;min-width:0;overflow:hidden;color:#5e747e;font-size:12px;font-weight:650;line-height:1.35;text-overflow:ellipsis;white-space:nowrap}
.assignment-config-root .assignment-filter-row.is-collapsible.is-collapsed .assignment-filter-row__summary{display:block}
.assignment-config-root .assignment-filter-row.is-collapsible>.assignment-filter-search{margin:12px 14px 8px!important;width:calc(100% - 28px)}
.assignment-config-root .assignment-filter-row.is-collapsible>.assignment-filter-options{margin:0 14px}
.assignment-config-root .assignment-filter-row.is-collapsible>.assignment-filter-inline-actions{margin:8px 14px 12px}
.assignment-config-root .assignment-filter-row.is-collapsible>.assignment-filter-range,
.assignment-config-root .assignment-filter-row.is-collapsible>.assignment-filter-date{margin:12px 14px 14px}
.assignment-config-root .assignment-filter-row.is-collapsible>.assignment-filter-reference{margin:0 14px 14px}
.assignment-config-root .assignment-filter-row.is-collapsible.is-collapsed>:not(.assignment-filter-row__head){display:none!important}
.assignment-config-root .assignment-filter-toggle{display:grid!important;width:32px!important;height:32px!important;min-height:32px!important;flex:0 0 32px;place-items:center;margin-left:auto;padding:0!important;border:1px solid #d6e1e4!important;border-radius:9px!important;color:#55707b!important;background:#fff!important;cursor:pointer;transition:border-color .16s ease,background .16s ease,color .16s ease!important}
.assignment-config-root .assignment-filter-toggle:hover{border-color:#8db9bc!important;color:#0b6d70!important;background:#f2f9f8!important}
.assignment-config-root .assignment-filter-toggle svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;transition:transform .18s ease}
.assignment-config-root .assignment-filter-row:not(.is-collapsed) .assignment-filter-toggle svg{transform:rotate(180deg)}
.assignment-config-root .assignment-filter-row.is-collapsed .assignment-filter-toggle svg{transform:rotate(0deg)}
.assignment-config-root .assignment-filter-row.is-collapsed{background:#fff}
.assignment-config-root .assignment-filter-row.is-collapsed .assignment-filter-row__head{background:#fff}
@media(max-width:560px){.assignment-config-root .assignment-filter-row.is-collapsible .assignment-filter-row__head>div:first-child{grid-template-columns:1fr}.assignment-config-root .assignment-filter-row.is-collapsible .assignment-filter-row__head>div:first-child small{grid-column:1}}
@media(prefers-reduced-motion:reduce){.assignment-config-root .assignment-filter-row.is-collapsible,.assignment-config-root .assignment-filter-toggle,.assignment-config-root .assignment-filter-toggle svg{transition:none!important}}
`;
  document.head.append(style);
}

function setExpanded(row,key,expanded){
  row.classList.toggle("is-collapsed",!expanded);
  if(expanded)expandedKeys.add(key);else expandedKeys.delete(key);
  const toggle=row.querySelector("[data-filter-collapse-toggle]");
  if(toggle){
    toggle.setAttribute("aria-expanded",String(expanded));
    toggle.setAttribute("aria-label",(expanded?"Cerrar":"Abrir")+" filtro "+key);
    toggle.title=expanded?"Cerrar filtro":"Abrir filtro";
  }
  const summary=row.querySelector(".assignment-filter-row__summary");
  if(summary){
    const next=filterSummary(row);
    if(summary.textContent!==next)summary.textContent=next;
  }
}

function decorateRow(row){
  const key=rowKey(row);
  if(!key)return;
  const firstSeen=!knownKeys.has(key);
  knownKeys.add(key);
  if(firstSeen)expandedKeys.add(key);

  row.classList.add("is-collapsible");
  const head=row.querySelector(".assignment-filter-row__head");
  if(!head)return;
  const copy=head.firstElementChild;
  if(copy&&!copy.querySelector(".assignment-filter-row__summary")){
    const summary=document.createElement("span");
    summary.className="assignment-filter-row__summary";
    copy.append(summary);
  }

  let toggle=head.querySelector("[data-filter-collapse-toggle]");
  if(!toggle){
    toggle=document.createElement("button");
    toggle.type="button";
    toggle.className="assignment-filter-toggle";
    toggle.dataset.filterCollapseToggle=key;
    toggle.innerHTML=chevronSvg();
    const remove=head.querySelector("[data-filter-remove]");
    head.insertBefore(toggle,remove||null);
    toggle.addEventListener("click",event=>{
      event.preventDefault();
      event.stopPropagation();
      setExpanded(row,key,!expandedKeys.has(key));
    });
  }
  setExpanded(row,key,expandedKeys.has(key));
}

function reconcileRows(){
  scheduled=false;
  const rows=[...document.querySelectorAll(ROW_SELECTOR)];
  const currentKeys=new Set();
  rows.forEach(row=>{
    const key=rowKey(row);
    if(key)currentKeys.add(key);
    decorateRow(row);
  });
  [...knownKeys].forEach(key=>{
    if(!currentKeys.has(key)){
      knownKeys.delete(key);
      expandedKeys.delete(key);
    }
  });
}

function scheduleReconcile(){
  if(scheduled)return;
  scheduled=true;
  queueMicrotask(reconcileRows);
}

function start(){
  ensureStyles();
  scheduleReconcile();
  if(observer)return;
  observer=new MutationObserver(scheduleReconcile);
  observer.observe(document.documentElement,{childList:true,subtree:true});
}

if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start,{once:true});
else start();

export {filterSummary,rowKey};
