// R4 local transaction state. No DOM, network, publication or engine activation.
export const clone=value=>structuredClone(value);
export function fingerprint(value){return JSON.stringify(value,(_k,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v);}
export const emptyProduct=()=>({name:'',packageType:'caja',length:'',width:'',height:'',unit:'cm',massKg:'',quantity:''});
const positive=v=>String(v??'').trim()!==''&&Number.isFinite(Number(v))&&Number(v)>0;
const nonnegative=v=>String(v??'').trim()!==''&&Number.isFinite(Number(v))&&Number(v)>=0;
const dimsValid=d=>d&&['length','width','height'].every(k=>positive(d[k]))&&['cm','m'].includes(d.unit);
export const volume=d=>dimsValid(d)?Number((Number(d.length)*Number(d.width)*Number(d.height)/(d.unit==='cm'?1e6:1)).toPrecision(15)):null;
const massKg=m=>m?m.unit==='t'?String(Number(m.value)*1000):String(m.value):'';
const volumeM3=v=>v?String(Number(v.value)/(v.unit==='l'?1000:1)):'';
const rectangular=t=>!['BIG_BAG','OTHER'].includes(t);
export function assessCargoDraft(draft){
 const c=draft.configuration,g=c.cargo,raw=draft.guided_ux?.catalogue||g,editing=draft.guided_ux?.origin==='new-guided'||draft.guided_ux?.edition==='ultimate'||draft.guided_ux?.r4;
 const no=reason=>({representable:false,reason});
 if(g.input_mode!=='catalog')return no('Contrato directo: se conserva sin convertir sus dos CSV.');
 if(c.active_dimensions.some(d=>!['weight_kg','volume_m3'].includes(d))||!editing&&!c.active_dimensions.length)return no('El contrato utiliza dimensiones históricas que deben conservarse.');
 if(c.primary_dimension!==(c.active_dimensions.includes('weight_kg')?'weight_kg':'volume_m3'))return no('La dimensión principal original requiere consulta sin reinterpretación.');
 if(!['INDIVISIBLE','DISCRETE'].includes(g.split_policy))return no('La carga continua conserva su unidad física original.');
 const ps=raw.presentations||[],us=raw.logistic_units||[],products=raw.products||[];
 if(ps.length>2||us.length>1||products.length>2)return no('El catálogo histórico excede una unidad compartida o dos tipos.');
 if(products.some(p=>Number(p.units_per_package??1)!==1))return no('El catálogo contiene unidades comerciales anidadas.');
 if(!ps.length)return editing&&!products.length?{representable:true}:no('El catálogo anterior está incompleto.');
 if(us.length!==1||products.length!==ps.length)return no('El catálogo contiene entidades que no deben descartarse.');
 const recovered=draft.guided_ux?.r4?.cargo;
 if(recovered?.unit?.id&&us[0]?.logistic_unit_id!==recovered.unit.id)return no('La metadata del borrador refiere otra unidad; se conserva para revisión.');
 if(recovered?.form?.target&&!ps.some(p=>p.presentation_id===recovered.form.target))return no('La edición recuperada refiere otro tipo de carga; se conserva sin reasignar IDs.');
 const refs=new Set();
 for(const p of ps){
  if((p.quantity_kind||'DISCRETE')!=='DISCRETE'||(p.quantity_unit||'presentation')!=='presentation'||p.components.length!==1)return no('Las composiciones mixtas o continuas se consultan sin conversión.');
  const part=p.components[0];refs.add(part.product_id);
  if(p.logistic_unit_id!==us[0].logistic_unit_id||!products.some(x=>x.product_id===part.product_id))return no('Las referencias del catálogo requieren revisión sin pérdida.');
  if(p.gross_mass||p.density_kg_per_m3||Number(p.extra_tare_mass?.value||0)!==0)return no('El contrato declara propiedades físicas adicionales que deben preservarse.');
  if(fingerprint([p.loaded_dimensions||null,p.external_volume||null])!==fingerprint([ps[0].loaded_dimensions||null,ps[0].external_volume||null]))return no('Los tipos tienen exteriores distintos; no se unifican automáticamente.');
 }
 if(refs.size!==products.length)return no('Las referencias a productos no son uno a uno.');
 const d=ps[0].loaded_dimensions,v=ps[0].external_volume;
 if(rectangular(us[0].type)&&!d||!rectangular(us[0].type)&&d)return no('La geometría histórica se conserva en consulta, sin cambiar su fuente.');
 if(d&&v&&Math.abs(volume(d)-Number(volumeM3(v)))>1e-9)return no('Hay fuentes físicas contradictorias que no pueden reinterpretarse.');
 return {representable:true};
}
export function createCargoState(catalog={},ui={},uuid=()=>crypto.randomUUID()){
 const raw=clone(catalog),unitRaw=raw.logistic_units?.[0],first=raw.presentations?.[0],cached=ui?.unit;
 const unit=cached?clone(cached):{id:unitRaw?.logistic_unit_id||uuid(),type:unitRaw?.type||'PALLET',name:unitRaw?.label||'',tareKg:massKg(unitRaw?.tare_mass),length:first?.loaded_dimensions?.length??'',width:first?.loaded_dimensions?.width??'',height:first?.loaded_dimensions?.height??'',measure:first?.loaded_dimensions?.unit||'cm',exteriorVolume:volumeM3(first?.external_volume)};
 const state={unit,savedTypes:(raw.presentations||[]).map(p=>({product:clone(raw.products.find(v=>v.product_id===p.components[0].product_id)),presentation:clone(p)})),form:ui?.form?clone(ui.form):{target:null,values:emptyProduct()},review:ui?.review===true,rawUnit:unitRaw?clone(unitRaw):null};
 function formFrom(t){const p=t.product,d=p.dimensions||{};return {name:p.name,packageType:p.unit_label,length:d.length??'',width:d.width??'',height:d.height??'',unit:d.unit||'cm',massKg:massKg(p.gross_mass),quantity:t.presentation.components[0].quantity};}
 if(state.form.target&&!state.savedTypes.some(t=>t.presentation.presentation_id===state.form.target))throw new Error('La edición recuperada refiere un tipo inexistente.');
 function dirty(){const t=state.savedTypes.find(t=>t.presentation.presentation_id===state.form.target);return fingerprint(state.form.values)!==fingerprint(t?formFrom(t):emptyProduct());}
 function unitErrors(){const u=state.unit,e={};if(!u.name.trim()||u.name.length>120)e.unit_name='Ingresá un nombre de unidad de hasta 120 caracteres.';if(!nonnegative(u.tareKg))e.unit_tare='Ingresá la tara en kg, mayor o igual a cero.';if(rectangular(u.type)){for(const k of ['length','width','height'])if(!positive(u[k]))e['unit_'+k]='Ingresá una medida mayor que cero.';}else if(!positive(u.exteriorVolume))e.unit_volume='Ingresá el volumen exterior cargado mayor que cero.';return e;}
 function formErrors(){const v=state.form.values,e={...unitErrors()};if(!v.name.trim()||v.name.length>120)e.product_name='Ingresá un nombre de producto de hasta 120 caracteres.';if(state.savedTypes.some(t=>t.presentation.presentation_id!==state.form.target&&t.product.name.trim().toLocaleLowerCase()===v.name.trim().toLocaleLowerCase()))e.product_name='Usá nombres distintos para cada producto.';if(!v.packageType.trim()||v.packageType.length>40)e.product_package='Declarar el tipo de bulto es obligatorio.';for(const k of ['length','width','height'])if(!positive(v[k]))e['product_'+k]='Ingresá una medida mayor que cero.';if(!positive(v.massKg))e.product_mass='El peso bruto por bulto debe ser mayor que cero.';if(!positive(v.quantity)||!Number.isSafeInteger(Number(v.quantity)))e.product_quantity='Ingresá una cantidad entera mayor que cero.';return e;}
 function exterior(){const u=state.unit;return rectangular(u.type)?{loaded_dimensions:{length:u.length,width:u.width,height:u.height,unit:u.measure},external_volume:null}:{loaded_dimensions:null,external_volume:positive(u.exteriorVolume)?{value:u.exteriorVolume,unit:'m3'}:null};}
 function setUnit(key,value){if(state.unit[key]===value)return;state.unit[key]=value;state.review=state.savedTypes.length>0;}
 function select(id){const t=state.savedTypes.find(t=>t.presentation.presentation_id===id);if(!t)throw new Error('Tipo inexistente.');state.form={target:id,values:formFrom(t)};}
 function save(){
  if(!state.form.target&&state.savedTypes.length>=2)return {ok:false,errors:{product_name:'Ya configuraste dos tipos de carga.'}};
  const errors=formErrors();if(Object.keys(errors).length)return {ok:false,errors};
  const old=state.savedTypes.find(t=>t.presentation.presentation_id===state.form.target),v=state.form.values,productId=old?.product.product_id||uuid(),presentationId=old?.presentation.presentation_id||uuid();
  const product={...old?.product,product_id:productId,name:v.name.trim(),unit_label:v.packageType.trim(),units_per_package:1,gross_mass:{value:v.massKg,unit:'kg'},dimensions:{length:v.length,width:v.width,height:v.height,unit:v.unit},compatibility_groups:old?.product.compatibility_groups?.length?clone(old.product.compatibility_groups):['LOAD_'+productId.replaceAll('-','')]};
  const presentation={...old?.presentation,presentation_id:presentationId,label:(state.unit.type==='PALLET'?'Pallet':state.unit.name.trim())+' de '+product.name,logistic_unit_id:state.unit.id,quantity_kind:'DISCRETE',quantity_unit:'presentation',components:[{product_id:productId,quantity:v.quantity}],...exterior()};
  const next={product,presentation};if(old)state.savedTypes[state.savedTypes.indexOf(old)]=next;else state.savedTypes.push(next);
  state.form={target:null,values:emptyProduct()};state.review=true;return {ok:true,presentationId};
 }
 function read(){
  const ext=exterior(),u=state.unit;
  return {products:state.savedTypes.map(t=>clone(t.product)),logistic_units:!state.savedTypes.length&&!state.rawUnit&&u.type==='PALLET'&&['name','tareKg','length','width','height','exteriorVolume'].every(k=>u[k]==='')?[]:[{...clone(state.rawUnit||{}),logistic_unit_id:u.id,label:u.name,type:u.type,tare_mass:state.rawUnit?.tare_mass&&u.tareKg===massKg(state.rawUnit.tare_mass)?clone(state.rawUnit.tare_mass):{value:u.tareKg,unit:'kg'}}],presentations:state.savedTypes.map(t=>({...clone(t.presentation),logistic_unit_id:u.id,...ext}))};
 }
 function validate(){if(Object.keys(unitErrors()).length)return 'Completá las medidas, el nombre y la tara de la unidad en el Paso 1.';if(!state.savedTypes.length)return 'Guardá al menos un tipo de carga en el Paso 2.';if(dirty())return 'Guardá los cambios del tipo de carga o descartalos al seleccionar una tarjeta inferior.';for(const t of state.savedTypes){const v=formFrom(t);if(!dimsValid(t.product.dimensions)||!positive(v.massKg)||!positive(v.quantity)||!Number.isSafeInteger(Number(v.quantity)))return 'Revisá los datos físicos del tipo guardado.';}return '';}
 return {state,dirty,unitErrors,formErrors,setUnit,select,save,read,validate,formFrom,exterior,snapshot:()=>({unit:clone(state.unit),form:clone(state.form),review:state.review}),unitVolume:()=>rectangular(state.unit.type)?volume({length:state.unit.length,width:state.unit.width,height:state.unit.height,unit:state.unit.measure}):positive(state.unit.exteriorVolume)?Number(state.unit.exteriorVolume):null};
}
