import {esc,num} from "./shared.mjs";

const FIELD_META={
  destination:{label:"Destino",help:"Ciudad o destino operativo del viaje."},
  origin:{label:"Origen",help:"Punto de salida heredado de Assignment."},
  vehicle_id:{label:"Vehículo",help:"Recurso concreto ya asignado."},
  ownership:{label:"Tipo de recurso",help:"Flota propia o recurso tercerizado."},
  product:{label:"Producto",help:"Producto incluido en las cargas del viaje."},
};

function normalized(value){return String(value??"").trim().toLocaleLowerCase("es");}

function displayValue(field,value){
  if(field==="ownership"){
    if(value==="own")return "Flota propia";
    if(value==="third_party")return "Tercero";
  }
  return String(value??"—");
}

function tripValues(trip,field){
  if(field==="product")return (trip?.loads||[]).map(load=>load?.product).filter(Boolean);
  const value=trip?.[field];
  return value===undefined||value===null||value===""?[]:[value];
}

function filterCatalog(trips){
  return Object.entries(FIELD_META).map(([field,meta])=>{
    const counts=new Map();
    (trips||[]).forEach(trip=>{
      const unique=new Map();
      tripValues(trip,field).forEach(value=>unique.set(normalized(value),String(value)));
      unique.forEach((value,key)=>counts.set(key,{value,count:(counts.get(key)?.count||0)+1}));
    });
    const options=[...counts.values()]
      .sort((a,b)=>displayValue(field,a.value).localeCompare(displayValue(field,b.value),"es"));
    return {field,...meta,options};
  }).filter(item=>item.options.length);
}

function matchingTripIds(trips,field,values){
  const selected=new Set((values||[]).map(normalized).filter(Boolean));
  if(!selected.size)return [];
  return (trips||[])
    .filter(trip=>tripValues(trip,field).some(value=>selected.has(normalized(value))))
    .map(trip=>trip.trip_id)
    .filter(Boolean);
}

function emptyDraft(field="destination"){
  return {
    field,
    values:[],
    action:"prioritize",
    windowStart:"",
    windowEnd:"",
  };
}

function normalizeFocusConfig(config,trips=[]){
  const catalog=filterCatalog(trips);
  const firstField=catalog[0]?.field||"destination";
  const draft={...emptyDraft(firstField),...(config?.ruleDraft||{})};
  if(!catalog.some(item=>item.field===draft.field))draft.field=firstField;
  return {
    ...config,
    temporalRules:Array.isArray(config?.temporalRules)?config.temporalRules:[],
    ruleDraft:draft,
  };
}

function selectedField(config,trips){
  const catalog=filterCatalog(trips);
  return catalog.find(item=>item.field===config.ruleDraft?.field)||catalog[0]||null;
}

function ruleLabel(rule){
  const field=FIELD_META[rule.field]?.label||rule.field;
  const values=(rule.values||[]).map(value=>displayValue(rule.field,value));
  const valueLabel=values.length<=2?values.join(" · "):values.slice(0,2).join(" · ")+" +"+(values.length-2);
  return field+" · "+valueLabel;
}

function ruleActionLabel(rule){
  if(rule.action==="window")return (rule.windowStart||"—")+" → "+(rule.windowEnd||"—");
  return "Priorizar salida";
}

function ruleCard(rule,index,trips){
  const matched=matchingTripIds(trips,rule.field,rule.values);
  return '<article class="scheduling-rule-card">'
    +'<div class="scheduling-rule-card__index">'+esc(String(index+1).padStart(2,"0"))+'</div>'
    +'<div class="scheduling-rule-card__body">'
      +'<small>FILTRO</small><strong>'+esc(ruleLabel(rule))+'</strong>'
      +'<span>'+esc(ruleActionLabel(rule))+' · '+num(matched.length)+' '+(matched.length===1?'viaje afectado':'viajes afectados')+'</span>'
    +'</div>'
    +'<button type="button" class="scheduling-rule-remove" data-scheduling-rule-remove="'+index+'" aria-label="Quitar regla '+(index+1)+'">Quitar</button>'
  +'</article>';
}

function focusRulesMarkup(config,trips){
  const next=normalizeFocusConfig(config,trips);
  const draft=next.ruleDraft;
  const field=selectedField(next,trips);
  const matched=matchingTripIds(trips,draft.field,draft.values);
  const windowMode=draft.action==="window";
  const rules=next.temporalRules||[];

  return '<div class="scheduling-focus-rules">'
    +'<div class="scheduling-focus-rules__head">'
      +'<div><small>REGLAS POR FOCO</small><h3>Aplicá una condición temporal a un grupo de viajes</h3><p>El filtro no elimina viajes. Sólo define qué subconjunto recibe prioridad o una ventana de salida específica.</p></div>'
      +'<span>'+num(rules.length)+' '+(rules.length===1?'regla':'reglas')+'</span>'
    +'</div>'
    +'<div class="scheduling-rule-builder">'
      +'<div class="scheduling-rule-step">'
        +'<label for="scheduling-rule-field">1 · Filtrar por</label>'
        +'<select id="scheduling-rule-field" data-scheduling-rule-field>'
          +filterCatalog(trips).map(item=>'<option value="'+esc(item.field)+'" '+(item.field===draft.field?'selected':'')+'>'+esc(item.label)+'</option>').join("")
        +'</select>'
        +(field?'<p>'+esc(field.help)+'</p>':'')
      +'</div>'
      +'<div class="scheduling-rule-step is-values">'
        +'<span class="scheduling-rule-step__label">2 · Seleccionar valores</span>'
        +'<div class="scheduling-rule-values">'
          +(field?.options||[]).map(option=>{
            const checked=(draft.values||[]).some(value=>normalized(value)===normalized(option.value));
            return '<label class="scheduling-rule-value '+(checked?'is-selected':'')+'">'
              +'<input type="checkbox" data-scheduling-rule-value value="'+esc(option.value)+'" '+(checked?'checked':'')+'>'
              +'<span>'+esc(displayValue(draft.field,option.value))+'</span><small>'+num(option.count)+'</small>'
            +'</label>';
          }).join("")
        +'</div>'
      +'</div>'
      +'<div class="scheduling-rule-step is-action">'
        +'<span class="scheduling-rule-step__label">3 · Aplicar regla</span>'
        +'<div class="scheduling-rule-actions">'
          +'<label class="scheduling-rule-action '+(!windowMode?'is-selected':'')+'"><input type="radio" name="scheduling-rule-action" value="prioritize" '+(!windowMode?'checked':'')+'><strong>Priorizar salida</strong><span>Este grupo se programa antes cuando comparte recurso, sin superar SLA ni restricciones físicas.</span></label>'
          +'<label class="scheduling-rule-action '+(windowMode?'is-selected':'')+'"><input type="radio" name="scheduling-rule-action" value="window" '+(windowMode?'checked':'')+'><strong>Fijar ventana específica</strong><span>Obliga a que las salidas de este grupo ocurran dentro de un rango particular.</span></label>'
        +'</div>'
        +'<div class="scheduling-rule-window '+(windowMode?'is-visible':'')+'">'
          +'<label><span>Desde</span><input type="date" data-scheduling-rule-window-start value="'+esc(draft.windowStart||"")+'"></label>'
          +'<label><span>Hasta</span><input type="date" data-scheduling-rule-window-end value="'+esc(draft.windowEnd||"")+'"></label>'
        +'</div>'
      +'</div>'
      +'<div class="scheduling-rule-preview">'
        +'<div><small>VIAJES AFECTADOS</small><strong>'+num(matched.length)+' de '+num((trips||[]).length)+'</strong><span>Los demás viajes siguen formando parte del calendario.</span></div>'
        +'<button type="button" data-scheduling-rule-add '+(!matched.length?'disabled':'')+'>Agregar regla</button>'
      +'</div>'
      +'<div data-scheduling-rule-error aria-live="polite"></div>'
    +'</div>'
    +(rules.length?'<div class="scheduling-rule-list"><div class="scheduling-rule-list__title"><strong>Reglas aplicadas</strong><span>Se evalúan sobre la asignación aprobada</span></div>'+rules.map((rule,index)=>ruleCard(rule,index,trips)).join("")+'</div>':'')
  +'</div>';
}

function validateRuleDraft(config,trips){
  const draft=config.ruleDraft||emptyDraft();
  const matched=matchingTripIds(trips,draft.field,draft.values);
  if(!draft.values?.length)return "Seleccioná al menos un valor para el filtro.";
  if(!matched.length)return "El filtro no coincide con ningún viaje de la asignación aprobada.";
  if(draft.action==="window"){
    if(!draft.windowStart||!draft.windowEnd)return "Elegí fecha desde y fecha hasta para la ventana específica.";
    const start=new Date(draft.windowStart+"T12:00:00");
    const end=new Date(draft.windowEnd+"T12:00:00");
    if(Number.isNaN(start.getTime())||Number.isNaN(end.getTime()))return "La ventana específica no tiene fechas válidas.";
    if(end<start)return "La fecha hasta de la regla no puede ser anterior a la fecha desde.";
    if(config.windowMode==="custom"){
      if(config.windowStart&&draft.windowStart<config.windowStart)return "La regla no puede comenzar antes de la ventana global.";
      if(config.windowEnd&&draft.windowEnd>config.windowEnd)return "La regla no puede terminar después de la ventana global.";
    }
  }
  return null;
}

function validateFocusRules(config,trips){
  const rules=config.temporalRules||[];
  if(rules.length>20)return "Podés aplicar como máximo 20 reglas temporales por corrida.";
  const ids=new Set();
  for(const rule of rules){
    if(!rule.id||ids.has(rule.id))return "Las reglas temporales deben tener identificadores únicos.";
    ids.add(rule.id);
    if(!matchingTripIds(trips,rule.field,rule.values).length)return "Una regla guardada ya no coincide con viajes de la asignación aprobada.";
    if(rule.action==="window"){
      if(!rule.windowStart||!rule.windowEnd)return "Una regla guardada tiene una ventana incompleta.";
      if(rule.windowEnd<rule.windowStart)return "Una regla guardada tiene una ventana invertida.";
      if(config.windowMode==="custom"){
        if(config.windowStart&&rule.windowStart<config.windowStart)return "Una regla comienza antes de la ventana global.";
        if(config.windowEnd&&rule.windowEnd>config.windowEnd)return "Una regla termina después de la ventana global.";
      }
    }
  }
  return null;
}

function focusedTripIds(config,trips){
  const ids=new Set();
  (config.temporalRules||[]).forEach(rule=>matchingTripIds(trips,rule.field,rule.values).forEach(id=>ids.add(id)));
  return [...ids].sort();
}

function executionRules(config){
  return (config.temporalRules||[]).map(rule=>({
    id:rule.id,
    field:rule.field,
    values:[...(rule.values||[])],
    action:rule.action,
    planning_window_start:rule.action==="window"?(rule.windowStart||null):null,
    planning_window_end:rule.action==="window"?(rule.windowEnd||null):null,
  }));
}

function hydrateExecutionRules(rules){
  return (rules||[]).map(rule=>({
    id:rule.id,
    field:rule.field,
    values:[...(rule.values||[])],
    action:rule.action,
    windowStart:rule.planning_window_start||"",
    windowEnd:rule.planning_window_end||"",
  }));
}

function nextRuleId(){
  const token=globalThis.crypto?.randomUUID?.()||Math.random().toString(16).slice(2);
  return "TR-"+token.replaceAll("-","").slice(0,10).toUpperCase();
}

function bindFocusRuleEvents(root,{config,trips,onChange}){
  const update=(patch)=>onChange(normalizeFocusConfig({...config,...patch},trips));
  root.querySelector('[data-scheduling-rule-field]')?.addEventListener("change",event=>{
    update({ruleDraft:{...config.ruleDraft,field:event.target.value,values:[]}});
  });
  root.querySelectorAll('[data-scheduling-rule-value]').forEach(input=>input.addEventListener("change",()=>{
    const values=[...root.querySelectorAll('[data-scheduling-rule-value]:checked')].map(node=>node.value);
    update({ruleDraft:{...config.ruleDraft,values}});
  }));
  root.querySelectorAll('input[name="scheduling-rule-action"]').forEach(input=>input.addEventListener("change",()=>{
    update({ruleDraft:{...config.ruleDraft,action:input.value}});
  }));
  root.querySelector('[data-scheduling-rule-window-start]')?.addEventListener("change",event=>{
    update({ruleDraft:{...config.ruleDraft,windowStart:event.target.value}});
  });
  root.querySelector('[data-scheduling-rule-window-end]')?.addEventListener("change",event=>{
    update({ruleDraft:{...config.ruleDraft,windowEnd:event.target.value}});
  });
  root.querySelector('[data-scheduling-rule-add]')?.addEventListener("click",()=>{
    const error=validateRuleDraft(config,trips);
    if(error){
      const node=root.querySelector('[data-scheduling-rule-error]');
      if(node)node.innerHTML='<p class="scheduling-error">'+esc(error)+'</p>';
      return;
    }
    const rule={
      id:nextRuleId(),
      field:config.ruleDraft.field,
      values:[...config.ruleDraft.values],
      action:config.ruleDraft.action,
      windowStart:config.ruleDraft.action==="window"?config.ruleDraft.windowStart:"",
      windowEnd:config.ruleDraft.action==="window"?config.ruleDraft.windowEnd:"",
    };
    const catalog=filterCatalog(trips);
    update({
      temporalRules:[...(config.temporalRules||[]),rule],
      ruleDraft:emptyDraft(catalog[0]?.field||"destination"),
    });
  });
  root.querySelectorAll('[data-scheduling-rule-remove]').forEach(button=>button.addEventListener("click",()=>{
    const index=Number(button.dataset.schedulingRuleRemove);
    update({temporalRules:(config.temporalRules||[]).filter((_,current)=>current!==index)});
  }));
}

export {
  FIELD_META,
  bindFocusRuleEvents,
  executionRules,
  filterCatalog,
  focusRulesMarkup,
  focusedTripIds,
  hydrateExecutionRules,
  matchingTripIds,
  normalizeFocusConfig,
  validateFocusRules,
};
