const ROW_SELECTOR=".assignment-config-root .assignment-filter-row:not(.is-invalid)";


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



export function mountFilterCollapse(root){
  const expandedKeys=new Set();const knownKeys=new Set();
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
  const rows=[...root.querySelectorAll(".assignment-filter-row:not(.is-invalid)")];
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

  return {update:reconcileRows};
}
export {filterSummary,rowKey};
