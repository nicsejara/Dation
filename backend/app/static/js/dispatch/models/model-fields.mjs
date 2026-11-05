import {el,field,section,choices} from './forms.mjs';
export const ROLES=[['SHIPPER','Generador de carga'],['LOGISTICS_PROVIDER','Proveedor logístico'],['HYBRID','Operación híbrida']];
export const DIMENSIONS=[['pallets','Pallets'],['weight_kg','Peso (kg)'],['volume_m3','Volumen (m³)'],['units','Unidades']];
export const defaultConfiguration=currency=>({version:1,operating_role:'SHIPPER',transport_pattern:'DIRECT',allowed_sources:['OWN','EXTERNAL'],
 active_dimensions:['pallets'],primary_dimension:'pallets',split_permitted:false,homogeneous_loads_declared:false,
 currency_policy:{currency:currency||'ARS',minor_units:2,rounding:'ROUND_HALF_UP'},own_cost_model:'OWN_OPERATING_CYCLE',external_cost_models:['PER_TRIP','PER_KM'],per_km_billing_bases:['ONE_WAY','ROUND_TRIP']});

export function mountModelFields(form,scope,draft){
 const host=el('div');form.append(host);
 const identity=section(host,'Identidad del Model'),name=field(identity,'Nombre del Model',{name:'model_name',value:draft.name,required:true,maxLength:120}),description=field(identity,'Descripción del Model (opcional)',{name:'model_description',type:'textarea',value:draft.description,maxLength:1000});
  const status=field(identity,'Estado',{name:'model_status',options:[['active','Activo'],['archived','Archivado']],value:draft.status});
  const config=draft.configuration,operation=section(host,'Operación y recursos','El rol describe la operación. Los permisos y el motor de decisión se mantienen iguales para todos los roles.');
  const role=field(operation,'Operating Role',{name:'operating_role',options:ROLES,value:config.operating_role}),pattern=field(operation,'Patrón de transporte',{name:'transport_pattern',value:'Directo · origen a destino',readOnly:true});
  const sources=choices(operation,'Fuentes de recursos','sources',[['OWN','Propios'],['EXTERNAL','Externos']],config.allowed_sources);
  const dimensions=choices(operation,'Dimensiones de capacidad','dimensions',DIMENSIONS,config.active_dimensions),primary=field(operation,'Dimensión principal de reporte',{name:'primary_dimension',options:DIMENSIONS,value:config.primary_dimension});
  const split=choices(operation,'Comportamiento de carga','split',[['yes','Permitir fraccionamiento de órdenes']],config.split_permitted?['yes']:[]);
  const homogeneous=choices(operation,'Compatibilidad','homogeneous',[['yes','Declarar cargas homogéneas']],config.homogeneous_loads_declared?['yes']:[]);
  operation.append(el('p','Sin declaración de homogeneidad, la compatibilidad de consolidación debe ser explícita. Los viajes son directos; no incluyen multiparada.','d-field__help'));
  const costs=section(host,'Moneda y reglas de costo','Las tarifas concretas se informan con los recursos. Un costo desconocido no se convierte en cero.');
  const currency=field(costs,'Moneda',{name:'currency',value:config.currency_policy.currency,required:true,maxLength:3}),minor=field(costs,'Decimales monetarios',{name:'minor_units',options:Array.from({length:7},(_,i)=>[String(i),String(i)]),value:String(config.currency_policy.minor_units)});
  field(costs,'Costo de recursos propios',{name:'own_cost',value:'Costo operativo del ciclo directo',readOnly:true});
  const external=choices(costs,'Tarifas externas permitidas','external_costs',[['PER_TRIP','Por viaje'],['PER_KM','Por kilómetro']],config.external_cost_models),billing=choices(costs,'Base de facturación por km','billing',[['ONE_WAY','Sólo ida'],['ROUND_TRIP','Ida y vuelta']],config.per_km_billing_bases);
  const collect=()=>({id:draft.id,expected_revision:draft.expected_revision,name:name.value.trim(),description:description.value.trim(),status:status.value,configuration:{version:1,operating_role:role.value,transport_pattern:'DIRECT',allowed_sources:sources(),active_dimensions:dimensions(),primary_dimension:primary.value,split_permitted:split().length>0,homogeneous_loads_declared:homogeneous().length>0,currency_policy:{currency:currency.value.trim().toUpperCase(),minor_units:Number(minor.value),rounding:'ROUND_HALF_UP'},own_cost_model:'OWN_OPERATING_CYCLE',external_cost_models:external(),per_km_billing_bases:billing()}});
 const validate=()=>{const c=collect().configuration,e={};if(!c.allowed_sources.length)e.operating_role='Elegí al menos una fuente de recursos.';if(!c.active_dimensions.includes(c.primary_dimension))e.primary_dimension='La dimensión principal debe estar activa.';if(!/^[A-Z]{3}$/.test(c.currency_policy.currency))e.currency='Ingresá una moneda de tres letras, por ejemplo ARS.';if(c.allowed_sources.includes('EXTERNAL')&&!c.external_cost_models.length)e.own_cost='Elegí una tarifa externa permitida.';if(c.external_cost_models.includes('PER_KM')&&!c.per_km_billing_bases.length)e.own_cost='Elegí una base de facturación por kilómetro.';return e;};

 const lock=()=>{for(const n of host.querySelectorAll('input,select,textarea'))n.disabled=true;};
 return {read:collect,validate,lock};
}
