import {el,field,section,choices} from './forms.mjs';
import {wizardIcon} from './wizard-ui.mjs';
export const ROLES=[['SHIPPER','Generador de carga'],['LOGISTICS_PROVIDER','Proveedor logístico'],['HYBRID','Operación híbrida']];
export const DIMENSIONS=[['pallets','Pallets'],['weight_kg','Peso (kg)'],['volume_m3','Volumen (m³)'],['units','Unidades']];
export const defaultConfiguration=currency=>({version:1,operating_role:'SHIPPER',transport_pattern:'DIRECT',allowed_sources:['OWN','EXTERNAL'],
 active_dimensions:['pallets'],primary_dimension:'pallets',split_permitted:false,homogeneous_loads_declared:false,
 currency_policy:{currency:currency||'ARS',minor_units:2,rounding:'ROUND_HALF_UP'},own_cost_model:'OWN_OPERATING_CYCLE',external_cost_models:['PER_TRIP','PER_KM'],per_km_billing_bases:['ONE_WAY','ROUND_TRIP']});

export function mountModelFields(form,scope,draft,{wizard=false,version=1}={}){
 const host=el('div',undefined,wizard?'model-wizard-cards':'');form.append(host);
 const card=(title,copy,kind)=>{
  if(!wizard)return section(host,title,kind==='identity'?undefined:copy);
  const node=el('section',undefined,'model-wizard-card'),rail=el('div',undefined,'model-wizard-card__rail'),tile=el('span',undefined,'model-wizard-tile'),text=el('div'),body=el('div',undefined,'ultimate-grid model-wizard-card__fields');
  node.dataset.dationTest='model-card-'+kind;tile.append(wizardIcon(kind));text.append(el('h3',title),el('p',copy));rail.append(tile,text);node.append(rail,body);host.append(node);return body;
 };
 const identity=card(wizard?'Identidad del modelo':'Identidad del Model','Nombrá y describí el modelo que va a estructurar esta operación logística.','identity'),name=field(identity,wizard?'Nombre del modelo *':'Nombre del Model',{name:'model_name',value:draft.name,required:true,maxLength:120}),description=field(identity,wizard?'Descripción del modelo (opcional)':'Descripción del Model (opcional)',{name:'model_description',type:'textarea',value:draft.description,maxLength:1000});
  const status=field(identity,'Estado',{name:'model_status',options:[['active','Activo'],['archived','Archivado']],value:draft.status});
  if(wizard){
   const versionInfo=el('div',undefined,'d-field model-wizard-version');versionInfo.append(el('span','Versión','d-field__label'),el('p','Versión '+version,'d-input'));versionInfo.dataset.dationTest='model-version';identity.insertBefore(versionInfo,description.closest('.d-field'));status.closest('.d-field').hidden=true;description.placeholder='Describí el alcance y las características principales del modelo…';description.closest('.d-field').classList.add('model-wizard-description');
  }
  const config=draft.configuration,operation=card('Operación y recursos',wizard?'Definí cómo opera la red, qué recursos intervienen y bajo qué reglas generales.':'El rol describe la operación. Los permisos y el motor de decisión se mantienen iguales para todos los roles.','resources');
  const role=field(operation,wizard?'Rol operativo':'Operating Role',{name:'operating_role',options:ROLES,value:config.operating_role}),pattern=field(operation,'Patrón de transporte',{name:'transport_pattern',value:'Directo · origen a destino',readOnly:true});
  const sources=choices(operation,'Fuentes de recursos','sources',[['OWN','Propios'],['EXTERNAL','Externos']],config.allowed_sources);
  const dimensions=choices(operation,'Dimensiones de capacidad','dimensions',DIMENSIONS,config.active_dimensions),primary=field(operation,'Dimensión principal de reporte',{name:'primary_dimension',options:DIMENSIONS,value:config.primary_dimension});
  const split=choices(operation,'Comportamiento de carga','split',[['yes','Permitir fraccionamiento de órdenes']],config.split_permitted?['yes']:[]);
  const homogeneous=choices(operation,'Compatibilidad','homogeneous',[['yes','Declarar cargas homogéneas']],config.homogeneous_loads_declared?['yes']:[]);
  operation.append(el('p','Sin declaración de homogeneidad, la compatibilidad de consolidación debe ser explícita. Los viajes son directos; no incluyen multiparada.','d-field__help'));
  const costs=card('Moneda y reglas de costo',wizard?'Configurá cómo se expresan y calculan los costos del modelo.':'Las tarifas concretas se informan con los recursos. Un costo desconocido no se convierte en cero.','costs');
  const currency=field(costs,'Moneda',{name:'currency',value:config.currency_policy.currency,required:true,maxLength:3}),minor=field(costs,'Decimales monetarios',{name:'minor_units',options:Array.from({length:7},(_,i)=>[String(i),String(i)]),value:String(config.currency_policy.minor_units)});
  field(costs,'Costo de recursos propios',{name:'own_cost',type:wizard?'textarea':'text',value:'Costo operativo del ciclo directo',readOnly:true});
  const external=choices(costs,'Tarifas externas permitidas','external_costs',[['PER_TRIP','Por viaje'],['PER_KM','Por kilómetro']],config.external_cost_models),billing=choices(costs,'Base de facturación por km','billing',[['ONE_WAY','Sólo ida'],['ROUND_TRIP','Ida y vuelta']],config.per_km_billing_bases);
  const collect=()=>({id:draft.id,expected_revision:draft.expected_revision,name:name.value.trim(),description:description.value.trim(),status:status.value,configuration:{version:1,operating_role:role.value,transport_pattern:'DIRECT',allowed_sources:sources(),active_dimensions:dimensions(),primary_dimension:primary.value,split_permitted:split().length>0,homogeneous_loads_declared:homogeneous().length>0,currency_policy:{currency:currency.value.trim().toUpperCase(),minor_units:Number(minor.value),rounding:'ROUND_HALF_UP'},own_cost_model:'OWN_OPERATING_CYCLE',external_cost_models:external(),per_km_billing_bases:billing()}});
 const validate=()=>{const c=collect().configuration,e={};if(!c.allowed_sources.length)e.operating_role='Elegí al menos una fuente de recursos.';if(!c.active_dimensions.includes(c.primary_dimension))e.primary_dimension='La dimensión principal debe estar activa.';if(!/^[A-Z]{3}$/.test(c.currency_policy.currency))e.currency='Ingresá una moneda de tres letras, por ejemplo ARS.';if(c.allowed_sources.includes('EXTERNAL')&&!c.external_cost_models.length)e.own_cost='Elegí una tarifa externa permitida.';if(c.external_cost_models.includes('PER_KM')&&!c.per_km_billing_bases.length)e.own_cost='Elegí una base de facturación por kilómetro.';return e;};

 if(wizard){
  costs.append(el('p','Las tarifas concretas se informan con los recursos. Un costo desconocido no se convierte en cero.','d-field__help'));
  // Visual grouping only: retain checkbox semantics, including both billing bases.
  for(const box of operation.querySelectorAll('fieldset'))box.dataset.group=box.querySelector('input')?.name;
  for(const box of costs.querySelectorAll('fieldset'))box.dataset.group=box.querySelector('input')?.name;
 }
 const validateAll=()=>{const errors=validate();if(wizard){if(!name.value.trim())errors.model_name='Ingresá el nombre del Logistics Model.';for(const n of host.querySelectorAll('input,select,textarea'))if(!n.validity.valid)errors[n.name]=n.name==='model_name'?'Ingresá el nombre del Logistics Model.':n.validationMessage;}return errors;};
 const sectionValidity=()=>{const errors=validateAll();return [!errors.model_name&&!errors.model_description, !errors.operating_role&&!errors.primary_dimension, !errors.currency&&!errors.own_cost&&!errors.minor_units];};
 const showErrors=()=>{const errors=validateAll();for(const n of host.querySelectorAll('[data-error-for]')){const message=errors[n.dataset.errorFor]||'';n.textContent=message;const input=host.querySelector('[name="'+n.dataset.errorFor+'"]');if(message)input?.setAttribute('aria-invalid','true');else input?.removeAttribute('aria-invalid');}return errors;};
 const lock=()=>{for(const n of host.querySelectorAll('input,select,textarea'))n.disabled=true;};
 return {read:collect,validate:validateAll,sectionValidity,showErrors,lock};
}
