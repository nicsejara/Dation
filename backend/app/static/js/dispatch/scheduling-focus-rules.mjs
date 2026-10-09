import {esc,num} from "./shared.mjs";
import {decisionRuleCard} from "./decision-config-ui.mjs?v=scheduling-rule-editor-phase3-v1";

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
    editingRuleId:config?.editingRuleId||null,
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

function ruleFingerprint(rule){
  const values=(rule.values||[]).map(normalized).filter(Boolean).sort();
  return [
    rule.field||"",
    values.join("|"),
    rule.action||"prioritize",
    rule.action==="window"?(rule.windowStart||""):"",
    rule.action==="window"?(rule.windowEnd||""):"",
  ].join("::");
}

function hasPendingRuleDraft(config){
  const draft=config?.ruleDraft||{};
  return Boolean(
    config?.editingRuleId
    ||(draft.values||[]).length
    ||draft.action==="window"
    ||draft.windowStart
    ||draft.windowEnd
  );
}

function overlappingRules(config,trips,draft=config?.ruleDraft||{}){
  const draftIds=new Set(matchingTripIds(trips,draft.field,draft.values));
  if(!draftIds.size)return [];
  return (config?.temporalRules||[])
    .filter(rule=>rule.id!==config?.editingRuleId)
    .map(rule=>{
      const ids=matchingTripIds(trips,rule.field,rule.values);
      const shared=ids.filter(id=>draftIds.has(id));
      return {rule,shared};
    })
    .filter(item=>item.shared.length);
}

function conflictingWindowRule(config,trips,draft){
  if(draft.action!=="window"||!draft.windowStart||!draft.windowEnd)return null;
  return overlappingRules(config,trips,draft).find(({rule})=>{
    if(rule.action!=="window"||!rule.windowStart||!rule.windowEnd)return false;
    return draft.windowEnd<rule.windowStart||rule.windowEnd<draft.windowStart;
  })||null;
}

function tripPreviewLabel(trip){
  const id=trip?.trip_id||"Viaje";
  const destination=trip?.destination||"Sin destino";
  const vehicle=trip?.vehicle_id||"Sin vehículo";
  return id+" · "+destination+" · "+vehicle;
}

function draftMatchedTrips(config,trips){
  const ids=new Set(matchingTripIds(trips,config.ruleDraft?.field,config.ruleDraft?.values));
  return (trips||[]).filter(trip=>ids.has(trip.trip_id));
}

function ruleCard(rule,index,trips){
  const matched=matchingTripIds(trips,rule.field,rule.values);
  const preview=(trips||[]).filter(trip=>matched.includes(trip.trip_id)).slice(0,3);
  const body='<div class="scheduling-rule-card-v3__impact">'
      +'<span><b>'+num(matched.length)+'</b> '+(matched.length===1?'viaje afectado':'viajes afectados')+'</span>'
      +(preview.length?'<small>'+preview.map(trip=>esc(tripPreviewLabel(trip))).join(" · ")+(matched.length>preview.length?' · +'+(matched.length-preview.length):'')+'</small>':'')
    +'</div>'
    +'<div class="scheduling-rule-card-v3__actions">'
      +'<button type="button" data-scheduling-rule-edit="'+esc(rule.id)+'">Editar</button>'
      +'<button type="button" class="is-danger" data-scheduling-rule-remove="'+esc(rule.id)+'">Quitar</button>'
    +'</div>';
  return decisionRuleCard({
    index:index+1,
    title:ruleLabel(rule),
    summary:ruleActionLabel(rule)+" · "+num(matched.length)+" "+(matched.length===1?"viaje":"viajes"),
    body,
    expanded:true,
    className:"scheduling-rule-card-v3",
  });
}

function focusRulesMarkup(config,trips){
  const next=normalizeFocusConfig(config,trips);
  const draft=next.ruleDraft;
  const field=selectedField(next,trips);
  const matchedTrips=draftMatchedTrips(next,trips);
  const windowMode=draft.action==="window";
  const rules=next.temporalRules||[];
  const editing=Boolean(next.editingRuleId);
  const dirty=hasPendingRuleDraft(next);
  const overlap=overlappingRules(next,trips,draft);
  const overlapTripIds=new Set(overlap.flatMap(item=>item.shared));
  const atLimit=rules.length>=20&&!editing;
  const options=field?.options||[];
  const canSelectAll=options.length>0&&options.length<=100;
  const preview=matchedTrips.slice(0,4);

  return '<div class="scheduling-focus-rules">'
    +'<div class="scheduling-focus-rules__head">'
      +'<div><small>REGLAS POR FOCO</small><h3>Aplicá una condición temporal a un grupo de viajes</h3><p>Construí políticas específicas sin alterar la asignación aprobada. Cada regla queda trazable y puede editarse antes de ejecutar.</p></div>'
      +'<span>'+num(rules.length)+' de 20 '+(rules.length===1?'regla':'reglas')+'</span>'
    +'</div>'
    +'<div class="scheduling-rule-builder '+(editing?'is-editing':'')+'" data-scheduling-rule-builder>'
      +'<div class="scheduling-rule-builder__head">'
        +'<div><small>'+(editing?'EDITANDO REGLA':'NUEVA REGLA')+'</small><strong>'+(editing?esc(next.editingRuleId):'Definí filtro, acción e impacto')+'</strong></div>'
        +(dirty?'<button type="button" data-scheduling-rule-cancel>Cancelar</button>':'')
      +'</div>'
      +'<div class="scheduling-rule-step" data-rule-step="1">'
        +'<div class="scheduling-rule-step__head"><span>1</span><div><strong>Filtrar por</strong><small>Elegí la dimensión operativa</small></div></div>'
        +'<label class="sr-only" for="scheduling-rule-field">Campo del filtro</label>'
        +'<select id="scheduling-rule-field" data-scheduling-rule-field>'
          +filterCatalog(trips).map(item=>'<option value="'+esc(item.field)+'" '+(item.field===draft.field?'selected':'')+'>'+esc(item.label)+'</option>').join("")
        +'</select>'
        +(field?'<p>'+esc(field.help)+'</p>':'')
      +'</div>'
      +'<div class="scheduling-rule-step is-values" data-rule-step="2">'
        +'<div class="scheduling-rule-step__head"><span>2</span><div><strong>Seleccionar valores</strong><small>'+num((draft.values||[]).length)+' seleccionados</small></div></div>'
        +'<div class="scheduling-rule-values-toolbar">'
          +'<button type="button" data-scheduling-rule-select-all '+(!canSelectAll?'disabled title="La selección masiva admite hasta 100 valores"':'')+'>Seleccionar todos</button>'
          +'<button type="button" data-scheduling-rule-clear-values '+(!(draft.values||[]).length?'disabled':'')+'>Limpiar</button>'
        +'</div>'
        +'<div class="scheduling-rule-values" role="group" aria-label="Valores del filtro">'
          +options.map(option=>{
            const checked=(draft.values||[]).some(value=>normalized(value)===normalized(option.value));
            return '<label class="scheduling-rule-value '+(checked?'is-selected':'')+'">'
              +'<input type="checkbox" data-scheduling-rule-value value="'+esc(option.value)+'" '+(checked?'checked':'')+'>'
              +'<span>'+esc(displayValue(draft.field,option.value))+'</span><small>'+num(option.count)+'</small>'
            +'</label>';
          }).join("")
        +'</div>'
      +'</div>'
      +'<div class="scheduling-rule-step is-action" data-rule-step="3">'
        +'<div class="scheduling-rule-step__head"><span>3</span><div><strong>Aplicar regla</strong><small>Definí qué debe cambiar en el calendario</small></div></div>'
        +'<div class="scheduling-rule-actions">'
          +'<label class="scheduling-rule-action '+(!windowMode?'is-selected':'')+'"><input type="radio" name="scheduling-rule-action" value="prioritize" '+(!windowMode?'checked':'')+'><strong>Priorizar salida</strong><span>Este grupo se programa antes cuando comparte recurso, sin superar SLA ni restricciones físicas.</span></label>'
          +'<label class="scheduling-rule-action '+(windowMode?'is-selected':'')+'"><input type="radio" name="scheduling-rule-action" value="window" '+(windowMode?'checked':'')+'><strong>Fijar ventana específica</strong><span>Obliga a que las salidas de este grupo ocurran dentro de un rango particular.</span></label>'
        +'</div>'
        +'<div class="scheduling-rule-window '+(windowMode?'is-visible':'')+'">'
          +'<label><span>Desde</span><input type="date" data-scheduling-rule-window-start value="'+esc(draft.windowStart||"")+'"></label>'
          +'<label><span>Hasta</span><input type="date" data-scheduling-rule-window-end value="'+esc(draft.windowEnd||"")+'"></label>'
        +'</div>'
      +'</div>'
      +'<div class="scheduling-rule-preview" aria-live="polite">'
        +'<div class="scheduling-rule-preview__summary"><small>IMPACTO PREVIO</small><strong>'+num(matchedTrips.length)+' de '+num((trips||[]).length)+' viajes</strong><span>Los demás viajes siguen formando parte del calendario.</span></div>'
        +'<div class="scheduling-rule-preview__trips">'
          +(preview.length?preview.map(trip=>'<span title="'+esc(tripPreviewLabel(trip))+'">'+esc(tripPreviewLabel(trip))+'</span>').join(""):'<span class="is-empty">Seleccioná valores para ver el impacto</span>')
          +(matchedTrips.length>preview.length?'<em>+'+(matchedTrips.length-preview.length)+' más</em>':'')
        +'</div>'
        +(overlap.length?'<div class="scheduling-rule-overlap"><strong>Solapamiento detectado</strong><span>'+num(overlapTripIds.size)+' '+(overlapTripIds.size===1?'viaje también está':'viajes también están')+' alcanzado por '+num(overlap.length)+' '+(overlap.length===1?'regla existente':'reglas existentes')+'. Las restricciones se combinan.</span></div>':'')
        +'<div class="scheduling-rule-preview__actions">'
          +(dirty?'<button type="button" class="is-secondary" data-scheduling-rule-cancel>Cancelar</button>':'')
          +'<button type="button" class="is-primary" data-scheduling-rule-add '+(!matchedTrips.length||atLimit?'disabled':'')+'>'+(editing?'Guardar cambios':'Agregar regla')+'</button>'
        +'</div>'
      +'</div>'
      +'<div data-scheduling-rule-error aria-live="assertive"></div>'
      +(atLimit?'<p class="scheduling-rule-limit">Alcanzaste el máximo de 20 reglas. Editá o quitá una regla existente para continuar.</p>':'')
    +'</div>'
    +(rules.length?'<div class="scheduling-rule-list"><div class="scheduling-rule-list__title"><div><strong>Reglas aplicadas</strong><span>Forman parte de la próxima ejecución</span></div><em>'+num(rules.length)+'/20</em></div>'+rules.map((rule,index)=>ruleCard(rule,index,trips)).join("")+'</div>':'')
  +'</div>';
}

function validateRuleDraft(config,trips){
  const draft=config.ruleDraft||emptyDraft();
  const matched=matchingTripIds(trips,draft.field,draft.values);
  if(!draft.values?.length)return "Seleccioná al menos un valor para el filtro.";
  if(draft.values.length>100)return "Cada regla puede seleccionar como máximo 100 valores.";
  if(!matched.length)return "El filtro no coincide con ningún viaje de la asignación aprobada.";
  if((config.temporalRules||[]).length>=20&&!config.editingRuleId)return "Podés aplicar como máximo 20 reglas temporales por corrida.";
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

  const duplicate=(config.temporalRules||[]).find(rule=>
    rule.id!==config.editingRuleId&&ruleFingerprint(rule)===ruleFingerprint(draft)
  );
  if(duplicate)return "Ya existe una regla idéntica. Editá la existente o cambiá el filtro.";

  const conflict=conflictingWindowRule(config,trips,draft);
  if(conflict)return "La ventana elegida entra en conflicto con "+conflict.rule.id+" sobre "+conflict.shared.length+" "+(conflict.shared.length===1?"viaje":"viajes")+". Ajustá las fechas antes de guardar.";
  return null;
}

function pendingRuleProblem(config,trips){
  if(!hasPendingRuleDraft(config))return null;
  const error=validateRuleDraft(config,trips);
  if(error)return "Terminá la regla pendiente: "+error;
  if(config.editingRuleId)return "Guardá o cancelá los cambios de la regla que estás editando antes de ejecutar.";
  return "Agregá o cancelá la regla preparada antes de ejecutar.";
}

function validateFocusRules(config,trips){
  const rules=config.temporalRules||[];
  if(rules.length>20)return "Podés aplicar como máximo 20 reglas temporales por corrida.";
  const ids=new Set();
  const fingerprints=new Set();
  for(const rule of rules){
    if(!rule.id||ids.has(rule.id))return "Las reglas temporales deben tener identificadores únicos.";
    ids.add(rule.id);
    const fingerprint=ruleFingerprint(rule);
    if(fingerprints.has(fingerprint))return "Hay reglas temporales duplicadas. Consolidá las reglas antes de ejecutar.";
    fingerprints.add(fingerprint);
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
  const normalizedConfig=normalizeFocusConfig(config,trips);
  const update=(patch,after)=>{
    const next=normalizeFocusConfig({...normalizedConfig,...patch},trips);
    onChange(next);
    if(after)queueMicrotask(()=>after(root));
  };
  const resetDraft=()=>{
    const catalog=filterCatalog(trips);
    return {editingRuleId:null,ruleDraft:emptyDraft(catalog[0]?.field||"destination")};
  };
  const focusBuilder=node=>node.querySelector('[data-scheduling-rule-builder]')?.scrollIntoView({behavior:"smooth",block:"center"});

  root.querySelector('[data-scheduling-rule-field]')?.addEventListener("change",event=>{
    update({ruleDraft:{...normalizedConfig.ruleDraft,field:event.target.value,values:[]}});
  });
  root.querySelectorAll('[data-scheduling-rule-value]').forEach(input=>input.addEventListener("change",()=>{
    const values=[...root.querySelectorAll('[data-scheduling-rule-value]:checked')].map(node=>node.value);
    update({ruleDraft:{...normalizedConfig.ruleDraft,values}});
  }));
  root.querySelector('[data-scheduling-rule-select-all]')?.addEventListener("click",()=>{
    const field=selectedField(normalizedConfig,trips);
    const values=(field?.options||[]).slice(0,100).map(item=>item.value);
    update({ruleDraft:{...normalizedConfig.ruleDraft,values}});
  });
  root.querySelector('[data-scheduling-rule-clear-values]')?.addEventListener("click",()=>{
    update({ruleDraft:{...normalizedConfig.ruleDraft,values:[]}});
  });
  root.querySelectorAll('input[name="scheduling-rule-action"]').forEach(input=>input.addEventListener("change",()=>{
    update({ruleDraft:{...normalizedConfig.ruleDraft,action:input.value}});
  }));
  root.querySelector('[data-scheduling-rule-window-start]')?.addEventListener("change",event=>{
    update({ruleDraft:{...normalizedConfig.ruleDraft,windowStart:event.target.value}});
  });
  root.querySelector('[data-scheduling-rule-window-end]')?.addEventListener("change",event=>{
    update({ruleDraft:{...normalizedConfig.ruleDraft,windowEnd:event.target.value}});
  });

  root.querySelectorAll('[data-scheduling-rule-cancel]').forEach(button=>button.addEventListener("click",()=>{
    update(resetDraft());
  }));

  root.querySelector('[data-scheduling-rule-add]')?.addEventListener("click",()=>{
    const error=validateRuleDraft(normalizedConfig,trips);
    if(error){
      const node=root.querySelector('[data-scheduling-rule-error]');
      if(node)node.innerHTML='<p class="scheduling-error">'+esc(error)+'</p>';
      return;
    }
    const editingId=normalizedConfig.editingRuleId;
    const rule={
      id:editingId||nextRuleId(),
      field:normalizedConfig.ruleDraft.field,
      values:[...normalizedConfig.ruleDraft.values],
      action:normalizedConfig.ruleDraft.action,
      windowStart:normalizedConfig.ruleDraft.action==="window"?normalizedConfig.ruleDraft.windowStart:"",
      windowEnd:normalizedConfig.ruleDraft.action==="window"?normalizedConfig.ruleDraft.windowEnd:"",
    };
    const temporalRules=editingId
      ?(normalizedConfig.temporalRules||[]).map(item=>item.id===editingId?rule:item)
      :[...(normalizedConfig.temporalRules||[]),rule];
    update({temporalRules,...resetDraft()});
  });

  root.querySelectorAll('[data-scheduling-rule-edit]').forEach(button=>button.addEventListener("click",()=>{
    const rule=(normalizedConfig.temporalRules||[]).find(item=>item.id===button.dataset.schedulingRuleEdit);
    if(!rule)return;
    update({
      editingRuleId:rule.id,
      ruleDraft:{
        field:rule.field,
        values:[...(rule.values||[])],
        action:rule.action,
        windowStart:rule.windowStart||"",
        windowEnd:rule.windowEnd||"",
      },
    },focusBuilder);
  }));

  root.querySelectorAll('[data-scheduling-rule-remove]').forEach(button=>button.addEventListener("click",()=>{
    const id=button.dataset.schedulingRuleRemove;
    const patch={temporalRules:(normalizedConfig.temporalRules||[]).filter(rule=>rule.id!==id)};
    if(normalizedConfig.editingRuleId===id)Object.assign(patch,resetDraft());
    update(patch);
  }));

  root.querySelector('[data-scheduling-rule-builder]')?.addEventListener("keydown",event=>{
    if(event.key!=="Escape"||!hasPendingRuleDraft(normalizedConfig))return;
    event.preventDefault();
    update(resetDraft());
  });
}

export {
  FIELD_META,
  bindFocusRuleEvents,
  executionRules,
  filterCatalog,
  focusRulesMarkup,
  focusedTripIds,
  hasPendingRuleDraft,
  hydrateExecutionRules,
  matchingTripIds,
  normalizeFocusConfig,
  pendingRuleProblem,
  validateFocusRules,
  validateRuleDraft,
};