import {el,field,choices,button,collapsibleSection} from './forms.mjs';
import {mountCargoEditor} from './cargo-editor.mjs';

const ROLES=[['SHIPPER','Generador de carga'],['LOGISTICS_PROVIDER','Proveedor logístico'],['HYBRID','Operación híbrida']];
const DIMS=[['pallets','Pallets'],['weight_kg','Peso (kg)'],['volume_m3','Volumen (m³)'],['units','Unidades']];
const PROFILES=[['PALLETIZED','Carga palletizada'],['PACKAGED','Bultos y cajas'],['DRY_BULK','Granel sólido'],['LIQUID_BULK','Granel líquido'],['SPECIALIZED','Carga especializada'],['MIXED','Operación mixta']];
const CATEGORIES=[['GENERAL','Carga general'],['REFRIGERATED','Refrigerado'],['TANKER','Cisterna'],['BULK','Granel'],['FLATBED','Plataforma']];

export function mountModelFieldsV2(form,scope,draft){
 const cfg=structuredClone(draft.configuration),host=el('div',undefined,'model-wizard-v2');host.dataset.dationTest='model-wizard-v2';form.append(host);
 const blocks=[['01. Identidad del modelo','Nombrá la operación y describí su alcance.'],['02. Operación logística','Transporte directo de origen a destino, con reglas explícitas de consolidación.'],['03. Carga y capacidad','Definí cantidades directas o un catálogo reutilizable de productos y presentaciones.'],['04. Recursos de transporte','Elegí fuentes y categorías de recursos admitidas.'],['05. Moneda y costos','Las tarifas reales se informan después con la flota. Un costo desconocido no equivale a cero.']].map(([title,copy],i)=>collapsibleSection(host,title,copy,{open:i===0}));
 blocks.forEach((b,i)=>{b.details.dataset.dationTest='model-v2-block-'+(i+1);b.details.classList.add('model-v2-block');});
 const [identity,operation,cargo,resources,costs]=blocks.map(b=>b.body);
 const name=field(identity,'Nombre del modelo *',{name:'model_name',value:draft.name,required:true,maxLength:120}),description=field(identity,'Descripción del modelo (opcional)',{name:'model_description',type:'textarea',value:draft.description,maxLength:1000});
 const role=field(operation,'Rol operativo',{name:'operating_role',options:ROLES,value:cfg.operating_role});
 field(operation,'Patrón de transporte',{name:'transport_pattern',value:'Directo · origen a destino',readOnly:true,help:'No incluye rutas multiparada ni logística inversa.'});
 const consolidate=field(operation,'¿Varias órdenes pueden compartir viaje?',{name:'consolidation_permitted',options:[['yes','Sí, si cumplen compatibilidad y capacidades'],['no','No, una orden por viaje']],value:cfg.consolidation_permitted?'yes':'no'});
 const profile=field(cargo,'Perfil de carga',{name:'cargo_profile',options:PROFILES,value:cfg.cargo.profile}),mode=field(cargo,'Modo de ingreso',{name:'cargo_input_mode',options:[['direct','Datos directos · sin catálogo'],['catalog','Productos y presentaciones']],value:cfg.cargo.input_mode});
 const primary=field(cargo,'Dimensión principal de reporte',{name:'primary_dimension',options:DIMS,value:cfg.primary_dimension}),dimensions=choices(cargo,'Dimensiones de capacidad activas','dimensions',DIMS,cfg.active_dimensions);
 const split=field(cargo,'Fraccionamiento',{name:'cargo_split_policy',options:[['INDIVISIBLE','Orden completa indivisible'],['DISCRETE','Por unidades logísticas completas'],['CONTINUOUS','Granel divisible en incremento explícito']],value:cfg.cargo.split_policy});
 const compat=field(cargo,'Compatibilidad de carga',{name:'cargo_compatibility',options:[['UNIFORM_DECLARED','Uniforme declarada'],['CATEGORIZED','Por categorías explícitas']],value:cfg.cargo.compatibility_policy});
 const coLoad=field(cargo,'Pares de categorías que pueden compartir carga',{name:'cargo_co_load_pairs',type:'textarea',value:(cfg.cargo.co_load_pairs||[]).map(p=>p.join(' + ')).join('\n'),help:'Una pareja por línea: SECO + REFRIGERADO. Elegibilidad de recurso y co-carga se validan por separado.'});
 const suggestions=button('Aplicar sugerencia de dimensiones del perfil',()=>{const dims=['DRY_BULK','LIQUID_BULK'].includes(profile.value)?['weight_kg','volume_m3']:profile.value==='PACKAGED'?['units','weight_kg']:['pallets','weight_kg','volume_m3'];primary.value=dims[0];for(const n of cargo.querySelectorAll('[name=dimensions]'))n.checked=dims.includes(n.value);if(['DRY_BULK','LIQUID_BULK'].includes(profile.value))split.value='CONTINUOUS';suggestions.dispatchEvent(new Event('change',{bubbles:true}));});cargo.append(suggestions);
 const catalogue=el('div',undefined,'model-v2-catalogue');cargo.append(catalogue);
 const editor=mountCargoEditor(catalogue,scope,{products:cfg.cargo.products||[],logistic_units:cfg.cargo.logistic_units||[],presentations:cfg.cargo.presentations||[]});
 const physical=el('div',undefined,'model-v2-physical');physical.dataset.dationTest='cargo-physical-preview';physical.role='status';cargo.append(physical);
 const sources=choices(resources,'Fuentes de recursos','sources',[['OWN','Propios'],['EXTERNAL','Externos']],cfg.allowed_sources);
 const categories=choices(resources,'Categorías admitidas (opcional)','resource_categories',[...CATEGORIES,...cfg.resource_categories.filter(v=>!CATEGORIES.some(([key])=>key===v)).map(v=>[v,v])],cfg.resource_categories);
 resources.append(el('p','Refrigerado, cisterna y otras categorías son filtros declarados; no certifican temperatura, peligrosidad ni requisitos técnicos del vehículo.','d-field__help'));
 const currency=field(costs,'Moneda *',{name:'currency',value:cfg.currency_policy.currency,required:true,maxLength:3}),minor=field(costs,'Decimales monetarios',{name:'minor_units',options:Array.from({length:7},(_,i)=>[String(i),String(i)]),value:String(cfg.currency_policy.minor_units)});
 const own=field(costs,'Costo de recursos propios',{name:'own_cost',value:'Costo operativo por km · ciclo directo de ida y vuelta',readOnly:true});
 const external=choices(costs,'Tarifas externas permitidas','external_costs',[['PER_TRIP','Por viaje'],['PER_KM','Por kilómetro']],cfg.external_cost_models),billing=choices(costs,'Base de facturación por km','billing',[['ONE_WAY','Sólo ida'],['ROUND_TRIP','Ida y vuelta']],cfg.per_km_billing_bases);
 const summary=el('aside',undefined,'model-v2-summary');summary.dataset.dationTest='model-v2-summary';summary.role='status';host.append(summary);let locked=false;
 const pairs=()=>coLoad.value.split('\n').filter(s=>s.trim()).map(s=>s.split('+').map(v=>v.trim()));
 const collect=()=>({id:draft.id,expected_revision:draft.expected_revision,name:name.value.trim(),description:description.value.trim(),status:draft.status||'active',configuration:{version:2,operating_role:role.value,transport_pattern:'DIRECT',consolidation_permitted:consolidate.value==='yes',allowed_sources:sources(),resource_categories:categories(),active_dimensions:dimensions(),primary_dimension:primary.value,split_permitted:split.value!=='INDIVISIBLE',homogeneous_loads_declared:compat.value==='UNIFORM_DECLARED',currency_policy:{currency:currency.value.trim().toUpperCase(),minor_units:Number(minor.value),rounding:'ROUND_HALF_UP'},own_cost_model:'OWN_OPERATING_CYCLE',external_cost_models:sources().includes('EXTERNAL')?external():[],per_km_billing_bases:sources().includes('EXTERNAL')&&external().includes('PER_KM')?billing():[],cargo:{profile:profile.value,input_mode:mode.value,split_policy:split.value,compatibility_policy:compat.value,co_load_pairs:compat.value==='CATEGORIZED'?pairs():[],...(mode.value==='catalog'?editor.read():{products:[],logistic_units:[],presentations:[]})}}});
 function validate(){
  const value=collect(),c=value.configuration,e={};
  if(!value.name)e.model_name='Ingresá el nombre del Logistics Model.';
  if(!c.allowed_sources.length)e.operating_role='Elegí al menos una fuente de recursos.';
  if(!c.active_dimensions.includes(c.primary_dimension))e.primary_dimension='La dimensión principal debe estar activa.';
  if(!/^[A-Z]{3}$/.test(c.currency_policy.currency))e.currency='Ingresá una moneda de tres letras, por ejemplo ARS.';
  if(c.allowed_sources.includes('EXTERNAL')&&!c.external_cost_models.length)e.own_cost='Elegí una tarifa externa permitida.';
  if(c.allowed_sources.includes('EXTERNAL')&&c.external_cost_models.includes('PER_KM')&&!c.per_km_billing_bases.length)e.own_cost='Elegí una base de facturación por kilómetro.';
  if(c.cargo.co_load_pairs.some(p=>p.length!==2||p.some(v=>!v)))e.cargo_co_load_pairs='Ingresá exactamente dos categorías por pareja.';
  if(c.cargo.input_mode==='catalog'&&(!c.cargo.products.length||!c.cargo.presentations.length))e.cargo_input_mode='Agregá al menos un producto y una presentación física.';
  for(const n of host.querySelectorAll('input,select,textarea'))if(!n.disabled&&!n.validity.valid)e[n.name]=n.validationMessage;
  return e;
 }
 const sectionValidity=()=>{const errors=validate();return blocks.map((b,i)=>!Object.keys(errors).some(key=>b.body.querySelector('[name="'+key+'"]'))&&(i!==3||sources().length>0));};
 const showErrors=()=>{const errors=validate();for(const box of host.querySelectorAll('[data-error-for]')){const msg=errors[box.dataset.errorFor]||'';box.textContent=msg;const control=host.querySelector('[name="'+box.dataset.errorFor+'"]');if(msg){control?.setAttribute('aria-invalid','true');control?.closest('details.model-v2-block')?.setAttribute('open','');}else control?.removeAttribute('aria-invalid');}return errors;};
 function sync(){
  catalogue.hidden=mode.value!=='catalog';editor.setActive(!locked&&!catalogue.hidden);
  coLoad.closest('.d-field').hidden=compat.value!=='CATEGORIZED';coLoad.disabled=locked||compat.value!=='CATEGORIZED';
  const hasExternal=sources().includes('EXTERNAL'),hasOwn=sources().includes('OWN');
  for(const n of costs.querySelectorAll('[name=external_costs]')){n.disabled=locked||!hasExternal;n.closest('fieldset').hidden=!hasExternal;}
  for(const n of costs.querySelectorAll('[name=billing]')){n.disabled=locked||!hasExternal||!external().includes('PER_KM');n.closest('fieldset').hidden=!hasExternal||!external().includes('PER_KM');}
  own.closest('.d-field').hidden=!hasOwn;
  const c=collect().configuration,counts=c.cargo;summary.textContent=(PROFILES.find(p=>p[0]===profile.value)?.[1]||'Carga')+' · '+(mode.value==='direct'?'Datos directos · sin catálogo':counts.products.length+' productos · '+counts.logistic_units.length+' unidades compartidas · '+counts.presentations.length+' presentaciones')+' · '+DIMS.filter(([key])=>c.active_dimensions.includes(key)).map(([,label])=>label).join(' + ')+' · '+(split.selectedOptions[0]?.textContent||'');
  const valid=sectionValidity();blocks.forEach((b,i)=>b.setStatus(valid[i]?'Datos completos':'En configuración',valid[i]?'pending':'warning'));
  physical.textContent=mode.value==='catalog'?'Los valores físicos se muestran sólo después de validar el contrato.':'';
 }
 scope.listen(mode,'change',()=>{if(mode.value==='catalog')editor.seed();sync();});scope.listen(host,'input',sync);scope.listen(host,'change',sync);
 if(mode.value==='catalog')editor.seed();sync();
 return {read:collect,validate,sectionValidity,showErrors,showServerError(message){physical.textContent=message;physical.role='alert';},lock(){locked=true;editor.lock();for(const n of host.querySelectorAll('input,select,textarea,button'))n.disabled=true;},setCompiled(data){
  physical.role='status';const valid=sectionValidity();blocks.forEach((b,i)=>b.setStatus(valid[i]?'Validado':'En configuración',valid[i]?'complete':'warning'));const catalogue=data?.contracts?.transport_demand?.rules?.catalog_snapshot;physical.replaceChildren();if(!catalogue||mode.value!=='catalog')return;
  for(const [key,p]of Object.entries(catalogue)){const name=collect().configuration.cargo.presentations.find(p=>p.presentation_id===key)?.label||'Presentación';const row=el('p');row.append(el('strong',name+' · '),document.createTextNode(Object.entries(p.coefficients).filter(([,v])=>v!==null).map(([d,v])=>v+' '+(DIMS.find(([id])=>id===d)?.[1]||d)).join(' · ')));row.append(el('small','Incremento: '+p.allocation_increment+' '+p.quantity_unit+' · '+Object.entries(p.provenance.sources).map(([d,source])=>(DIMS.find(([id])=>id===d)?.[1]||d)+': '+({COMPONENT_GROSS_PLUS_EXPLICIT_TARE:'componentes y tara',DECLARED_GROSS_MASS:'declarado',LOADED_EXTERIOR_DIMENSIONS:'exterior cargado',DECLARED_EXTERIOR_VOLUME:'volumen declarado',EXPLICIT_DENSITY_TIMES_VOLUME:'densidad explícita × volumen',MASS_OVER_EXPLICIT_DENSITY:'peso / densidad explícita',EXPLICIT_QUANTITY_UNIT:'unidad física declarada'}[source]||source)).join(' · ')));physical.append(row);}
 }};
}
