import {el,button} from './forms.mjs';
import {download} from '../shared.mjs';
import {wizardIcon} from './wizard-ui.mjs';

const ENTITIES=[['transport_demand','Órdenes / Demanda','Plantilla con los envíos u órdenes que Dation tendrá en cuenta al generar recomendaciones.','document'],['transport_resources','Flota / Recursos','Plantilla con los recursos propios o externos, sus capacidades, disponibilidad y condiciones de costo.','resources']];
// Presentation-only catalogue of exact public headers from the current compiler.
// Unknown headers remain literal; this catalogue never generates or alters CSV.
const DESCRIPTIONS={order_id:'Identificador único de la orden',origin_id:'Origen del envío',destination_id:'Destino del envío',distance_km:'Distancia entre origen y destino',ready_date:'Fecha en la que el envío está listo',delivery_due_date:'Fecha límite de entrega',priority:'Prioridad de la orden',split_allowed:'Permiso de fraccionamiento de la orden',resource_id:'Identificador único del recurso',source:'Recurso propio o externo',lanes:'Trayectos de origen y destino admitidos',units_available:'Unidades propias disponibles',base_origin_id:'Origen base del recurso propio',operating_cost_per_km:'Costo operativo por kilómetro',services_available:'Servicios externos disponibles',availability_source:'Origen de la disponibilidad declarada',cost_model:'Modalidad de tarifa del recurso externo',trip_rate:'Tarifa por viaje',per_km_rate:'Tarifa por kilómetro',billing_basis:'Base de facturación por kilómetro',compatibility_groups:'Grupos de compatibilidad declarados'};
for(const [dimension,label]of [['pallets','pallets'],['weight_kg','peso (kg)'],['volume_m3','volumen (m³)'],['units','unidades']]){
 DESCRIPTIONS['demand_'+dimension]='Demanda expresada en '+label;DESCRIPTIONS['guaranteed_'+dimension]='Capacidad garantizada en '+label;DESCRIPTIONS['maximum_'+dimension]='Capacidad máxima en '+label;
}
export const fieldDescription=field=>Object.hasOwn(DESCRIPTIONS,field.public_header)?DESCRIPTIONS[field.public_header]:'Campo «'+field.public_header+'» del contrato seleccionado';
export function fieldCondition(field){
 const conditions=Object.entries(field.applies_when),base=field.nullable?'Opcional':'Requerido';
 if(!conditions.length)return base;
 const phrases={source:{OWN:'el recurso es propio',EXTERNAL:'el recurso es externo'},cost_model:{PER_TRIP:'la tarifa es por viaje',PER_KM:'la tarifa es por kilómetro'}};
 const readable=conditions.map(([key,value])=>typeof value==='string'&&Object.hasOwn(phrases,key)&&Object.hasOwn(phrases[key],value)?phrases[key][value]:null);
 if(readable.some(value=>!value))return base+' según condición técnica';
 return base+(field.nullable?' · Aplica cuando ':' cuando ')+readable.join(' y ');
}

// Structural validation of the response, not a second contract compiler.
export function assertContractPair(data,source){
 const contracts=data?.contracts;
 if(typeof data?.provisional!=='boolean'||data.provisional!==!source.version_id||!contracts||Object.keys(contracts).length!==2)throw new Error('No se recibieron ambos contratos completos para el modelo seleccionado. Reintentá Data Contract.');
 for(const [entity]of ENTITIES){
  const c=contracts[entity];
  // Provisional responses intentionally omit the published version/hash.
  if(c?.semantic_entity!==entity||!Array.isArray(c.fields)||!c.fields.length||!c.rules||typeof c.rules!=='object'||Array.isArray(c.rules)||(!data.provisional&&(c.model_version_id!==source.version_id||typeof c.contract_hash!=='string'||!c.contract_hash)))throw new Error('El contrato no corresponde a la versión seleccionada. Reintentá Data Contract.');
  for(const f of c.fields)if(typeof f.public_header!=='string'||!f.public_header||typeof f.nullable!=='boolean'||typeof f.type!=='string'||!f.applies_when||Array.isArray(f.applies_when)||typeof f.applies_when!=='object'||!f.validation||Array.isArray(f.validation)||typeof f.validation!=='object')throw new Error('El contrato contiene campos incompletos. Reintentá Data Contract.');
 }
}

function icon(kind){
 if(['database','resources','check'].includes(kind))return wizardIcon(kind);
 const paths={document:['M5 3h9l5 5v13H5V3Z','M14 3v6h5','M8 13h8','M8 17h8'],download:['M12 3v12','m7 10 5 5 5-5','M4 16v5h16v-5'],info:['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z','M12 11v6','M12 7h.01']};
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','1.7');svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');svg.setAttribute('aria-hidden','true');svg.classList.add('data-contract-icon');
 for(const d of paths[kind]){const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',d);svg.append(path);}return svg;
}
function disclosure(label,cls){
 const details=el('details',undefined,cls),summary=el('summary',undefined,'data-contract-toggle'),chevron=el('span',undefined,'data-contract-chevron');chevron.setAttribute('aria-hidden','true');summary.append(chevron,el('span',label));details.append(summary);return details;
}

export function mountDataContractView(panel,scope,{retry:retryPreview,onContinue}){
 const {body,details}=panel;details.classList.add('data-contract-step');body.classList.add('data-contract-body');
 const summary=details.querySelector('summary'),tile=el('span',undefined,'data-contract-tile'),heading=el('span',undefined,'data-contract-heading');tile.append(icon('database'));heading.append(summary.querySelector('.ultimate-disclosure__title'),body.previousElementSibling);summary.prepend(tile,heading);
 const status=el('p','Terminá Logistics Model para preparar la estructura de datos.','data-contract-status'),retry=button('Reintentar Data Contract',retryPreview),grid=el('div',undefined,'data-contract-grid'),info=el('aside',undefined,'data-contract-info'),infoText=el('div');
 status.role='status';status.setAttribute('aria-live','polite');retry.hidden=true;grid.dataset.dationTest='contract-cards';
 infoText.append(el('h3','¿Qué es un Data Contract?'),el('p','Define la estructura esperada y las reglas de validación de los datos que Dation va a recibir. Se genera automáticamente a partir del Logistics Model seleccionado.'),el('p','Completá las plantillas con tus datos y cargalas más adelante desde el Decision Graph.','d-metadata'));info.append(icon('info'),infoText);
 const footer=el('footer',undefined,'data-contract-footer'),progress=el('div',undefined,'data-contract-progress'),ring=el('span',undefined,'data-contract-ring'),text=el('div'),title=el('strong','Estructura de datos pendiente'),copy=el('p','Terminá Logistics Model para continuar.','d-metadata'),next=button('Continuar a Decision Case',()=>{if(!next.disabled)onContinue();},'primary');
 ring.setAttribute('aria-hidden','true');ring.append(icon('check'));next.prepend(icon('check'));next.dataset.dationTest='contract-continue';next.disabled=true;text.append(title,copy);progress.append(ring,text);footer.append(progress,next);footer.dataset.dationTest='contract-footer';body.append(status,retry,grid,info,footer);
 let generation=0,cards=[],hasPair=false;
 function invalidate(){generation++;hasPair=false;for(const c of cards)c.action.disabled=true;cards=[];grid.replaceChildren();next.disabled=true;details.dataset.contractState='PENDING';title.textContent='Estructura de datos pendiente';copy.textContent='Resolviendo los contratos del modelo…';ring.dataset.ready='false';}
 scope.own(invalidate);
 function render(data,source){
  assertContractPair(data,source);invalidate();const own=generation,fragment=document.createDocumentFragment(),snapshot=structuredClone(source);
  for(const [entity,label,description,kind]of ENTITIES){
   const contract=data.contracts[entity],card=el('section',undefined,'data-contract-card'),header=el('header',undefined,'data-contract-card__header'),tile=el('span',undefined,'data-contract-tile'),heading=el('div'),name=el('h3',label),badges=el('div',undefined,'data-contract-badges');
   card.dataset.dationTest='contract-card-'+entity;tile.append(icon(kind));name.id='contract-title-'+entity;card.setAttribute('aria-labelledby',name.id);heading.append(name,el('p',description,'data-contract-description'));header.append(tile,heading);badges.append(el('span','CSV'),el('span',data.provisional?'Vista previa provisional':'Estructura generada desde Logistics Model'));
   const caption=el('span','Descargar template'),action=button('',async()=>{
    if(busy||action.disabled||own!==generation)return;busy=true;action.disabled=true;action.setAttribute('aria-busy','true');caption.textContent='Descargando…';error.hidden=true;
    try{
     const response=await fetch('/api/platform/logistics-models/contract-preview/templates/'+entity,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(snapshot),signal:scope.signal});
     if(!response.ok)throw new Error('No se pudo descargar el template. Volvé a intentarlo.');
     const csv=await response.text();if(scope.active&&own===generation)download(entity+'.csv',csv,'text/csv;charset=utf-8');
    }catch{if(scope.active&&own===generation){error.textContent='No se pudo descargar el template. Volvé a intentarlo.';error.hidden=false;}}
    finally{busy=false;if(scope.active&&own===generation){action.disabled=false;action.removeAttribute('aria-busy');caption.textContent='Descargar template';}}
   },'primary');let busy=false;action.append(icon('download'),caption);action.setAttribute('aria-label','Descargar template de '+label);action.classList.add('data-contract-download');action.dataset.dationTest='contract-download-'+entity;
   const error=el('p','','data-contract-error');error.role='alert';error.hidden=true;
   const fields=disclosure('Campos y reglas','data-contract-fields'),wrap=el('div',undefined,'data-contract-table-wrap');fields.dataset.dationTest='contract-fields-'+entity;wrap.tabIndex=0;wrap.role='region';wrap.setAttribute('aria-label','Campos y reglas de '+label);
   const table=el('table'),thead=el('thead'),titles=el('tr');for(const label of ['Campo','Descripción','Condición']){const th=el('th',label);th.scope='col';titles.append(th);}thead.append(titles);table.append(thead);const tbody=el('tbody');
   for(const f of contract.fields){const row=el('tr'),key=el('td'),condition=el('td');key.append(el('code',f.public_header));condition.append(el('span',fieldCondition(f),'data-contract-condition'));row.append(key,el('td',fieldDescription(f)),condition);tbody.append(row);}table.append(tbody);wrap.append(table);
   const technical=disclosure('Especificación técnica','data-contract-technical'),spec=el('pre',JSON.stringify(contract,null,2));spec.tabIndex=0;spec.role='region';spec.setAttribute('aria-label','Especificación técnica de '+label);technical.append(spec);fields.append(wrap,technical);card.append(header,badges,action,error,fields);fragment.append(card);cards.push({action,get busy(){return busy;}});
  }
  grid.replaceChildren(fragment);hasPair=true;status.textContent=data.provisional?'Vista previa preparatoria. Publicá y seleccioná el modelo para confirmar su estructura.':'Estructura generada para la versión publicada seleccionada.';status.role='status';
 }
 function setState({ready,compiled,pending,failed,selected,provisional}){
  if(!compiled&&hasPair)invalidate();
  const complete=!!(ready&&compiled&&hasPair&&selected&&!provisional&&!pending&&!failed);
  next.disabled=!complete;ring.dataset.ready=String(complete);status.hidden=complete;
  for(const c of cards)c.action.disabled=c.busy||!compiled||pending||failed;
  details.dataset.contractState=complete?'READY':failed?'ERROR':pending?'LOADING':compiled&&provisional?'PROVISIONAL':'PENDING';
  title.textContent=complete?'Estructura de datos lista':failed?'Revisar estructura de datos':pending?'Preparando estructura de datos':provisional&&compiled?'Vista previa preparatoria':'Estructura de datos pendiente';
  copy.textContent=complete?'2 contratos generados para el modelo seleccionado':failed?'Reintentá Data Contract para poder continuar.':pending?'Resolviendo los contratos del modelo…':provisional&&compiled?'Publicá y seleccioná el modelo para confirmar su estructura.':'Terminá Logistics Model para continuar.';
 }
 return {status,retry,render,invalidate,setState};
}
