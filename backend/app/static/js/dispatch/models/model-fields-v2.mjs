import {el} from './forms.mjs';
import {assessCargoDraft,fingerprint} from './cargo-guided-state.mjs';
import {mountCargoGuidedEditor} from './cargo-guided-editor.mjs';
import {guidedBlock,radioCards,checkboxCards,confirmFooter,stepPanel,modelField as field,note,readout} from './guided-ui.mjs';
const DIMS=[['weight_kg','Peso (kg)'],['volume_m3','Volumen (m³)']];
const CATEGORIES=[['GENERAL','Carga general'],['REFRIGERATED','Refrigerado'],['TANKER','Cisterna'],['BULK','Granel'],['FLATBED','Plataforma']];
export function mountModelFieldsV2(form,scope,draft,{published=false}={}){
 const assessment=assessCargoDraft(draft);
 if(!assessment.representable)return mountHistorical(form,draft,assessment,published);
 return mountFields(form,scope,draft,{published});
}
function mountHistorical(form,draft,assessment,published){
 const original=structuredClone(draft),c=original.configuration,g=c.cargo,host=el('div',undefined,'model-wizard-v2 model-wizard-pro');host.dataset.historicalReview='';form.append(host);
 const defs=[['Identidad del modelo','tag',{name:draft.name,description:draft.description}],['Operación logística','resources',{operating_role:c.operating_role,transport_pattern:c.transport_pattern,consolidation_permitted:c.consolidation_permitted}],['Carga y capacidad','pallet',null],['Recursos de transporte','resources',{allowed_sources:c.allowed_sources,resource_categories:c.resource_categories}],['Moneda y costos','costs',{currency_policy:c.currency_policy,own_cost_model:c.own_cost_model,external_cost_models:c.external_cost_models,per_km_billing_bases:c.per_km_billing_bases}]];
 const json=(parent,value)=>{const data=el('pre',JSON.stringify(value,null,2),'r4-contract-readonly');data.tabIndex=0;data.setAttribute('role','region');data.setAttribute('aria-label','Datos íntegros del contrato original');parent.append(data);};
 for(const [i,[title,icon,value]]of defs.entries()){
  const b=guidedBlock(host,i+1,title,'Consulta de contrato original · solo lectura',icon,{open:i===2});if(published)b.setStatus('publicado · solo lectura','complete');
  if(i===2){note(b.body,assessment.reason+' No se modifican sus datos. Para una configuración distinta utilizá Crear nuevo modelo.');
   const one=stepPanel(b.body,1,'Unidad logística original','Se conservan todas las unidades históricas.');json(one.body,g.logistic_units);
   const two=stepPanel(b.body,2,'Tipos de carga originales','Se conservan todos los productos, componentes e identificadores.');json(two.body,{products:g.products,presentations:g.presentations});if(!published&&draft.guided_ux?.catalogue&&fingerprint(draft.guided_ux.catalogue)!==fingerprint({products:g.products,logistic_units:g.logistic_units,presentations:g.presentations})){note(two.body,'Datos de borrador recuperados, todavía sin publicar.');json(two.body,draft.guided_ux.catalogue);}
   const three=stepPanel(b.body,3,'Restricciones y reglas originales','El contrato conserva su semántica física.');json(three.body,{...c,cargo:{profile:g.profile,input_mode:g.input_mode,split_policy:g.split_policy,compatibility_policy:g.compatibility_policy,co_load_pairs:g.co_load_pairs},currency_policy:undefined});
  }else json(b.body,value);
 }
 const valid=()=>Object.fromEntries(published?[]:[['cargo_catalog','Este contrato se conserva en consulta. Creá un modelo nuevo para editar sin convertir el histórico.']]);
 return {read:()=>structuredClone(original),validate:valid,sectionValidity:()=>[true,true,true,true,true],sectionCompletion:()=>Array(5).fill(published),canPublish:()=>false,showErrors:valid,showSectionErrors:valid,refreshErrors(){},invalidateCompiled(){},showServerError(){},setCompiled(){},lock(){}};
}
function mountFields(form,scope,draft,{published:immutable=false}){
 const cfg=structuredClone(draft.configuration),saved=draft.guided_ux||{},confirmed=saved.r4?{...(saved.confirmed||{})}:{};
 const host=el('div',undefined,'model-wizard-v2 model-wizard-pro');host.dataset.dationTest='model-wizard-v2';form.append(host);
 const definitions=[
  ['Identidad del modelo','Definí un nombre y describí el alcance de este modelo logístico.','tag'],
  ['Operación logística','Definí el rol de tu empresa y cómo se organizan los viajes y la consolidación de órdenes.','resources'],
  ['Carga y capacidad','Configurá qué transportás, cómo se compone la carga y qué capacidades se controlan.','pallet'],
  ['Recursos de transporte','Definí qué recursos puede utilizar tu operación y qué categorías de vehículos se admiten.','resources'],
  ['Moneda y costos','Seleccioná la moneda y las reglas de cálculo de los costos de transporte.','costs']
 ];
 const blocks=definitions.map(([title,copy,icon],i)=>guidedBlock(host,i+1,title,copy,icon,{open:saved.openBlocks?saved.openBlocks.includes(i+1):i===0}));
 const [identity,operation,cargo,resources,costs]=blocks.map(b=>b.body);
 const name=field(identity,'Nombre del modelo *',{name:'model_name',value:draft.name,required:true,maxLength:120,help:'Asigná un nombre que identifique tu operación. Ej.: Despachos de cargas regionales.'}),description=field(identity,'Descripción del modelo (opcional)',{name:'model_description',type:'textarea',value:draft.description,maxLength:1000,help:'Describí el alcance, tipo de operación y características principales.'});
 description.placeholder='Ej.: Distribución regional de bebidas con flota propia y tercerizada.';
 const role=radioCards(operation,'¿Cuál es el rol de tu empresa en la operación?','operating_role',[
  ['SHIPPER','Generador de carga','Despachás mercadería propia, usando transporte propio o contratado.','box'],
  ['LOGISTICS_PROVIDER','Proveedor logístico','Transportás mercadería o gestionás servicios logísticos para otras empresas.','resources'],
  ['HYBRID','Operación híbrida','Combinás la generación de carga con servicios logísticos a terceros.','layers']
 ],cfg.operating_role);
 note(operation,'Seleccioná cómo participa tu empresa en la logística de transporte.');
 note(operation,'Patrón de transporte: Directo · Origen a destino. Dation planifica viajes entre un origen y un destino. Las rutas multiparada y la logística inversa no forman parte de esta configuración.');
 const consolidate=radioCards(operation,'¿Cómo querés organizar las órdenes en los viajes?','consolidation_permitted',[
  ['yes','Permitir consolidación','Un viaje puede incluir varias órdenes compatibles, respetando rutas y capacidades.','layers'],
  ['no','Mantener órdenes separadas','Cada viaje transporta mercadería de una única orden.','box']
 ],cfg.consolidation_permitted?'yes':'no');consolidate.root.classList.add('guided-two-columns');
 note(operation,'Permitir consolidación no obliga a unir órdenes. Dation evalúa si compartir viaje es compatible y conveniente según las capacidades y restricciones configuradas.');
 const steps=[
  ['Definir la unidad logística','Primero definí cómo se despacha la mercadería y las dimensiones generales de la unidad que viaja en el transporte.'],
  ['Definir qué contiene esta unidad','Definí el producto, el tipo de bulto y cuántos bultos conforman cada unidad logística.'],
  ['Restricciones físicas y reglas','Definí qué límites físicos controlará Dation y cómo pueden distribuirse las órdenes entre viajes.']
 ].map(([title,copy],i)=>stepPanel(cargo,i+1,title,copy));
 const editor=mountCargoGuidedEditor({units:steps[0].body,products:steps[1].body},scope,saved.catalogue||cfg.cargo,{ui:saved.r4?.cargo||{},profile:cfg.cargo.profile});
 const rules=steps[2].body,ruleGrid=el('div',undefined,'r4-rule-grid'),capacity=el('div'),orderRule=el('div');ruleGrid.append(capacity,orderRule);rules.append(ruleGrid);
 const dimensions=checkboxCards(capacity,'¿Qué restricciones físicas debe controlar Dation?','dimensions',[
 ['weight_kg','Peso máximo','Controla que el peso bruto total no supere la capacidad declarada del vehículo.','weight'],['volume_m3','Volumen máximo','Controla que el volumen exterior total no supere la capacidad volumétrica declarada.','box']
 ],cfg.active_dimensions);dimensions.root.classList.add('guided-two-columns');
 const split=radioCards(orderRule,'¿Una orden puede distribuirse en varios viajes?','cargo_split_policy',[
 ['INDIVISIBLE','No, la orden debe viajar completa','Todas las unidades de la orden se asignan a un único viaje. Si no hay capacidad suficiente, queda sin servir.','box'],
 ['DISCRETE','Sí, puede dividirse entre viajes','Las unidades completas de una orden pueden asignarse a diferentes viajes, respetando capacidades y restricciones.','layers']
 ],cfg.cargo.split_policy);split.root.classList.add('guided-two-columns');
 const orderNote=note(rules,'');orderNote.dataset.orderUnitNote='';
 note(rules,'Cada tipo de carga contiene un único producto por unidad logística. Podés configurar hasta dos tipos, sin mezclar productos dentro de un mismo pallet.');
 note(rules,'Dation calcula peso y volumen para controlar las capacidades declaradas. No certifica el acomodamiento tridimensional ni el apilado físico.');
 const physical=el('div',undefined,'model-v2-physical');physical.dataset.dationTest='cargo-physical-preview';physical.role='status';rules.append(physical);
 const cargoErrors=el('p',undefined,'d-field__error');cargoErrors.dataset.errorFor='cargo_catalog';cargoErrors.role='alert';rules.append(cargoErrors);
 const sources=checkboxCards(resources,'¿De dónde provienen tus recursos de transporte?','sources',[
  ['OWN','Flota propia','Vehículos administrados por tu empresa, con disponibilidad y costos operativos propios.','resources'],
  ['EXTERNAL','Transporte tercerizado','Servicios contratados a operadores externos, con disponibilidad y tarifas declaradas.','resources']
 ],cfg.allowed_sources);sources.root.classList.add('guided-two-columns');
 const sourceError=el('p',undefined,'d-field__error');sourceError.dataset.modelErrorFor='sources';sourceError.id='guided-source-error-'+crypto.randomUUID();sourceError.role='alert';resources.append(sourceError);
 for(const input of resources.querySelectorAll('[name=sources]'))input.setAttribute('aria-describedby',sourceError.id);
 const categories=checkboxCards(resources,'¿Qué categorías de vehículos admite tu operación?','resource_categories',[
  ['GENERAL','Carga general','Vehículos estándar para carga seca y operaciones generales.','box'],['REFRIGERATED','Refrigerado','Recursos con control térmico declarado para mercadería sensible.','snow'],['TANKER','Cisterna','Vehículos preparados para líquidos o cargas transportadas en tanque.','tank'],['BULK','Granel','Recursos orientados a materiales sueltos o a granel.','mound'],['FLATBED','Plataforma','Vehículos abiertos para cargas sobredimensionadas o especiales.','flatbed'],
  ...cfg.resource_categories.filter(v=>!CATEGORIES.some(([key])=>key===v)).map(v=>[v,v,'Categoría histórica preservada.','resources'])
 ],cfg.resource_categories);categories.root.classList.add('guided-five-columns');const categoryValues=categories;
 note(resources,'Si no seleccionás categorías, Dation no aplicará un filtro global por tipo de vehículo. Las demás condiciones de compatibilidad y capacidad seguirán vigentes. Las categorías son filtros declarados: no certifican temperatura, peligrosidad ni condiciones técnicas.');
 const currencies=[['ARS','ARS · $','Peso argentino','costs'],['USD','USD · US$','Dólar estadounidense','costs'],['EUR','EUR · €','Euro','costs']];
 if(!currencies.some(([key])=>key===cfg.currency_policy.currency))currencies.push([cfg.currency_policy.currency,cfg.currency_policy.currency,'Moneda histórica preservada; sin conversión de divisas.','costs']);
 const currency=radioCards(costs,'¿En qué moneda opera tu modelo logístico?','currency',currencies,cfg.currency_policy.currency),currencyNote=note(costs,'');
 const own=note(costs,'Flota propia · Costo operativo por kilómetro. Dation calcula el costo considerando el recorrido de ida y regreso y el costo operativo por kilómetro declarado para cada vehículo. Este método es fijo y los importes se informan posteriormente en los datos de flota.');own.dataset.ownCostNote='';
 const external=checkboxCards(costs,'¿Qué modalidades de tarifas externas utiliza tu operación?','external_costs',[
  ['PER_TRIP','Tarifa por viaje','El transportista cobra un importe fijo por cada viaje realizado, independientemente de cómo se calcule la distancia.','clipboard'],['PER_KM','Tarifa por kilómetro','El transportista cobra en función de la distancia facturable y de la tarifa por kilómetro acordada.','route']
 ],cfg.external_cost_models);external.root.classList.add('guided-two-columns');
 const billing=checkboxCards(costs,'¿Qué distancia pueden facturar los transportistas externos?','billing',[
  ['ONE_WAY','Sólo ida','Se factura la distancia desde el origen hasta el destino.','route'],['ROUND_TRIP','Ida y vuelta','Se factura la distancia de ida más el regreso considerado.','route']
 ],cfg.per_km_billing_bases);billing.root.classList.add('guided-two-columns');
 const billingNote=note(costs,'Podés admitir ambas bases; cada recurso utiliza su modalidad, no ambas a la vez. Para 100 km de ida, se facturan 100 km en Sólo ida o 200 km en Ida y vuelta, según el modelo actual.');
 const money=el('details',undefined,'cargo-advanced');money.append(el('summary','Configuración monetaria avanzada'));const moneyBody=el('div');money.append(moneyBody);costs.append(money);
 const minor=field(moneyBody,'Decimales monetarios',{name:'minor_units',options:Array.from({length:7},(_,i)=>[String(i),String(i)]),value:String(cfg.currency_policy.minor_units),help:'Precisión 0–6, redondeo ROUND_HALF_UP. Cambiar moneda no cambia la precisión.'});
 const costError=el('p',undefined,'d-field__error');costError.dataset.modelErrorFor='costs';costError.role='alert';costs.append(costError);
 note(costs,'En este bloque definís las reglas de cálculo admitidas. Las tarifas y costos reales se informan posteriormente al cargar los recursos de transporte. Un costo desconocido no se interpreta como cero.');
 let locked=false,published=immutable,compiledKey=null,compiledData=null,serverError='',lastConfig='';
 const summary=el('aside',undefined,'model-v2-summary');summary.dataset.dationTest='model-v2-summary';host.append(summary);
 const activeDimensions=()=>{const active=dimensions();return [...cfg.active_dimensions.filter(d=>active.includes(d)),...active.filter(d=>!cfg.active_dimensions.includes(d))];};
 // Existing compatibility policy is immutable in this focused UI. New products
 // have distinct stable groups, so sharing a support never grants co-loading.
 const config=()=>({version:2,operating_role:role.value,transport_pattern:'DIRECT',consolidation_permitted:consolidate.value==='yes',allowed_sources:sources(),resource_categories:categoryValues(),active_dimensions:activeDimensions(),primary_dimension:dimensions().includes('weight_kg')?'weight_kg':'volume_m3',split_permitted:split.value==='DISCRETE',homogeneous_loads_declared:cfg.cargo.compatibility_policy==='UNIFORM_DECLARED',currency_policy:{currency:currency.value,minor_units:Number(minor.value),rounding:'ROUND_HALF_UP'},own_cost_model:'OWN_OPERATING_CYCLE',external_cost_models:sources().includes('EXTERNAL')?external():[],per_km_billing_bases:sources().includes('EXTERNAL')&&external().includes('PER_KM')?billing():[],cargo:{...cfg.cargo,profile:editor.getProfile(),input_mode:'catalog',split_policy:split.value,...editor.read()}});
 const signature=()=>fingerprint(config());
 const localSignatures=c=>[fingerprint([name.value,description.value]),fingerprint([c.operating_role,c.consolidation_permitted]),fingerprint([c.cargo,c.active_dimensions,c.primary_dimension,editor.bufferSignature()]),fingerprint([c.allowed_sources,c.resource_categories]),fingerprint([c.allowed_sources,c.currency_policy,c.external_cost_models,c.per_km_billing_bases])];
 const collect=()=>immutable?structuredClone(draft):({id:draft.id,expected_revision:draft.expected_revision,name:name.value.trim(),description:description.value.trim(),status:draft.status||'active',configuration:config(),guided_ux:{origin:saved.origin,edition:'ultimate',catalogue:editor.snapshot(),r4:{cargo:editor.ui()},confirmed:{...confirmed},openBlocks:blocks.flatMap((b,i)=>b.details.open?[i+1]:[])}});
 function validate(){
  const c=config(),e={};if(!name.value.trim())e.model_name='Ingresá el nombre del Logistics Model.';
  if(!c.allowed_sources.length)e.sources='Elegí al menos una fuente de recursos.';
  if(!c.active_dimensions.length||!c.active_dimensions.includes(c.primary_dimension))e.cargo_catalog='La dimensión principal debe estar activa.';
  if(!/^[A-Z]{3}$/.test(c.currency_policy.currency))e.currency='Ingresá una moneda de tres letras, por ejemplo ARS.';
  if(c.allowed_sources.includes('EXTERNAL')&&!c.external_cost_models.length)e.own_cost='Elegí una tarifa externa permitida.';
  if(c.allowed_sources.includes('EXTERNAL')&&c.external_cost_models.includes('PER_KM')&&!c.per_km_billing_bases.length)e.own_cost='Elegí una base de facturación por kilómetro.';
  const message=editor.validate();if(message)e.cargo_catalog=message;
  for(const n of host.querySelectorAll('input,select,textarea'))if(!n.disabled&&!n.dataset.guidedUi&&!n.validity.valid)e[n.name]=n.validationMessage;
  return e;
 }
 const belongs=(index,key)=>!!blocks[index].body.querySelector('[name="'+CSS.escape(key)+'"]')||index===2&&key==='cargo_catalog'||index===3&&key==='sources'||index===4&&key==='own_cost';
 function sectionValidity(){const errors=validate();return blocks.map((b,i)=>!Object.keys(errors).some(key=>belongs(i,key)));}
 function sectionCompletion(){const c=config(),keys=localSignatures(c),valid=sectionValidity();return keys.map((key,i)=>published||valid[i]&&confirmed[i]===key&&(i!==2||compiledKey===fingerprint(c)));}
 const shown=new Set();
 function paintErrors(index,errors){
  const body=blocks[index].body;
  if(index===3){sourceError.textContent=errors.sources||'';for(const n of body.querySelectorAll('[name=sources]')){if(errors.sources)n.setAttribute('aria-invalid','true');else n.removeAttribute('aria-invalid');}}
  if(index===4)costError.textContent=errors.own_cost||'';
  for(const box of body.querySelectorAll('[data-error-for]'))if(!box.closest('[data-pro-step="1"],[data-pro-step="2"]'))box.textContent=errors[box.dataset.errorFor]||'';
  for(const n of body.querySelectorAll('input,select,textarea'))if(!n.dataset.guidedUi){if(errors[n.name])n.setAttribute('aria-invalid','true');else if(n.name!=='sources')n.removeAttribute('aria-invalid');}
 }
 function refreshErrors(){const errors=validate();for(const index of shown)paintErrors(index,errors);}
 function showSectionErrors(index){
  const errors=Object.fromEntries(Object.entries(validate()).filter(([key])=>belongs(index,key)));shown.add(index);paintErrors(index,errors);
  if(Object.keys(errors).length){blocks[index].details.open=true;const body=blocks[index].body,target=body.querySelector('[aria-invalid=true]')||body.querySelector('.d-field__error:not(:empty)');if(target){let parent=target.parentElement;while(parent&&parent!==body){if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement;}if(!target.matches('input,select,textarea'))target.tabIndex=-1;target.focus();}}
  return errors;
 }
 function showErrors(){const errors=validate();for(let i=0;i<5;i++){shown.add(i);paintErrors(i,errors);}const first=blocks.findIndex((b,i)=>Object.keys(errors).some(key=>belongs(i,key)));if(first>=0)showSectionErrors(first);return errors;}
 const ctas=[];
 function reviewed(){host.dispatchEvent(new CustomEvent('model-review',{bubbles:true}));}
 for(let index=0;index<5;index++){
  const cta=confirmFooter(blocks[index].body,'Confirmar '+definitions[index][0].toLocaleLowerCase(),()=>{
   if(locked||cta.disabled)return;if(Object.keys(showSectionErrors(index)).length)return;
   if(index===2&&compiledKey!==signature()){cargoErrors.textContent=serverError||'La confirmación requiere el preview vigente de Dation. Revisá los datos físicos y las dependencias de recursos y costos.';cargoErrors.tabIndex=-1;cargoErrors.focus();return;}
   confirmed[index]=localSignatures(config())[index];sync();reviewed();
  });cta.dataset.confirmBlock=String(index+1);ctas.push(cta);
 }
 function sync(){
  const c=config(),key=fingerprint(c),keys=localSignatures(c);
  if(lastConfig&&key!==lastConfig){compiledKey=null;compiledData=null;serverError='';editor.invalidate();}lastConfig=key;
  for(const i of Object.keys(confirmed))if(confirmed[i]!==keys[i])delete confirmed[i];
  const hasExternal=sources().includes('EXTERNAL');for(const n of costs.querySelectorAll('[name=external_costs]')){n.disabled=locked||!hasExternal;n.closest('fieldset').hidden=!hasExternal;}
  for(const n of costs.querySelectorAll('[name=billing]')){n.disabled=locked||!hasExternal||!external().includes('PER_KM');n.closest('fieldset').hidden=!hasExternal||!external().includes('PER_KM');}own.hidden=!sources().includes('OWN');billingNote.hidden=!hasExternal||!external().includes('PER_KM');
  const complete=sectionCompletion();blocks.forEach((b,i)=>b.setStatus(published?'publicado · solo lectura':complete[i]?'validado y revisado':i===2&&serverError?'revisá el error de validación':'pendiente de revisión',complete[i]?'complete':i===2&&serverError?'error':'pending'));
  ctas.forEach((cta,i)=>{cta.disabled=locked||complete[i]||i===2&&compiledKey!==key&&!serverError&&sectionValidity().every(Boolean);cta.setAttribute('aria-disabled',String(cta.disabled));cta.dataset.confirmationState=published?'readonly':complete[i]?'confirmed':'pending';});
  ctas[2].dataset.previewCurrent=String(compiledKey===key);ctas[2].setAttribute('aria-busy',String(!locked&&compiledKey!==key&&!serverError&&sectionValidity().every(Boolean)));
  orderNote.lastChild.textContent='Unidad logística informada en órdenes: '+editor.unitName()+'. En Líneas de órdenes, Dation identifica cada tipo de carga y la cantidad de unidades completas solicitadas.';
  currencyNote.lastChild.textContent='Moneda seleccionada: '+currency.value+'. Los costos deben ingresarse en esta moneda; Dation no convierte divisas automáticamente.';
  summary.textContent='Carga homogénea · '+c.cargo.presentations.length+' tipos · '+activeDimensions().map(v=>DIMS.find(([id])=>id===v)[1]).join(' + ');
  if(!compiledData&&!serverError){physical.role='status';physical.textContent='Las propiedades físicas se muestran después de validar el contrato actual con Dation.';}
 }
 scope.listen(host,'focusout',event=>event.stopPropagation());scope.listen(host,'input',sync);scope.listen(host,'change',sync);sync();
 return {read:collect,validate,sectionValidity,sectionCompletion,showErrors,showSectionErrors,refreshErrors,canPublish:()=>!locked&&compiledKey===signature()&&sectionCompletion().every(Boolean),
  invalidateCompiled(){compiledKey=null;compiledData=null;editor.invalidate();sync();},
  showServerError(message,{focus=false}={}){compiledKey=null;compiledData=null;serverError=message;physical.textContent=message;physical.role='alert';editor.showError(message);sync();if(focus){blocks[2].details.open=true;physical.tabIndex=-1;physical.focus();}},
  lock({published:immutable=false}={}){locked=true;published=immutable;editor.lock();for(const n of host.querySelectorAll('input,select,textarea,button'))n.disabled=true;sync();},
  setCompiled(data){
   compiledKey=signature();compiledData=data;serverError='';physical.replaceChildren();physical.role='status';const catalogue=data?.contracts?.transport_demand?.rules?.catalog_snapshot;editor.setCompiled(catalogue);
   for(const [key,p]of Object.entries(catalogue||{})){const label=config().cargo.presentations.find(v=>v.presentation_id===key)?.label||'Tipo de carga',row=el('p');row.append(el('strong',label+' · '),document.createTextNode(Object.entries(p.coefficients).filter(([,v])=>v!==null).map(([d,v])=>v+' '+(DIMS.find(([id])=>id===d)?.[1]||d)).join(' · ')));row.append(el('small','Validado por Dation · '+p.allocation_increment+' presentación completa'));physical.append(row);}
   sync();refreshErrors();
  }
 };
}
