import {el,choices,button,confirmAction} from './forms.mjs';
import {assessGuidedDraft,mountEditorChoice} from './model-editor-mode.mjs';
import {mountCargoEditor} from './cargo-editor.mjs';
import {guidedBlock,guidedStep,radioCards,checkboxCards,confirmFooter,stepPanel,modelField as field,note,readout} from './guided-ui.mjs';

const DIMS=[['pallets','Pallets'],['weight_kg','Peso (kg)'],['volume_m3','Volumen (m³)'],['units','Unidades']];
const PROFILES=[
 ['PALLETIZED','Carga palletizada','Mercadería agrupada en pallets, ideal para distribución y operaciones de alto volumen.','pallet'],
 ['PACKAGED','Cajas y bultos','Unidades sueltas (cajas, bultos o paquetes) sin palletizar.','box'],
 ['DRY_BULK','Granel sólido','Productos a granel en estado sólido, como granos, minerales o polvos.','mound'],
 ['LIQUID_BULK','Granel líquido','Productos a granel en estado líquido, como aceites o combustibles.','drop'],
 ['SPECIALIZED','Carga especializada','Recursos o condiciones particulares, sujetos a verificación externa.','container'],
 ['MIXED','Operación mixta','Combinación de distintos perfiles de carga dentro de una misma operación.','layers']
];
const CATEGORIES=[['GENERAL','Carga general'],['REFRIGERATED','Refrigerado'],['TANKER','Cisterna'],['BULK','Granel'],['FLATBED','Plataforma']];
const PHYSICAL_SOURCES={COMPONENT_GROSS_PLUS_EXPLICIT_TARE:'componentes y tara declarados',DECLARED_GROSS_MASS:'peso bruto declarado',LOADED_EXTERIOR_DIMENSIONS:'dimensiones exteriores cargadas',DECLARED_EXTERIOR_VOLUME:'volumen exterior declarado',EXPLICIT_DENSITY_TIMES_VOLUME:'densidad explícita por volumen',MASS_OVER_EXPLICIT_DENSITY:'peso dividido por densidad explícita',EXPLICIT_QUANTITY_UNIT:'unidad física declarada'};
const STEP_COPY=[
 ['Perfil de carga','Seleccioná cómo se transporta habitualmente tu mercadería. Esto nos permite adaptar la configuración del modelo.'],
 ['Unidad logística','Distinguí el soporte vacío de la presentación cargada. Las propiedades persistentes se configuran en Detallado.'],
 ['Nivel de detalle','Elegí cuánta información querés modelar sobre la unidad de carga.'],
 ['Productos','Registrá productos y sus propiedades físicas relevantes para la operación.'],
 ['Productos y composición','Definí qué productos y cantidades contiene cada presentación de carga.'],
 ['Capacidades y reglas','Configurá restricciones físicas, fraccionamiento y compatibilidad.'],
 ['Revisar y validar','Comprobá el modelo y sus contratos antes de guardarlo.']
];
export function mountModelFieldsV2(form,scope,draft,{published=false}={}){
 const region=el('div',undefined,'model-editor-region');form.append(region);let current,locked=false,lockOptions={};
 function mount(value){
  const saved=value.guided_ux||{},assessment=assessGuidedDraft(value),explicit=saved.editorChoice;
  const simple=assessment.representable&&(published||explicit==='guided'||explicit!=='compatible'&&saved.edition!=='compatible');
  region.replaceChildren();
  if(simple||published||explicit==='compatible')current=mountFields(region,scope,value,{simple,published,onEdition:choose});
  else current=mountEditorChoice(region,scope,value,assessment,{choose,startNew:()=>region.dispatchEvent(new CustomEvent('model-new-request',{bubbles:true}))});
  if(locked)current.lock(lockOptions);
 }
 function choose(edition){
  if(locked)return;const value=current.read();value.guided_ux={...value.guided_ux,edition:edition==='guided'?'ultimate':'compatible',editorChoice:edition};
  mount(value);region.dispatchEvent(new Event('change',{bubbles:true}));
  const target=region.querySelector('[data-dation-test=model-v2-block-3]');if(target){target.open=true;target.querySelector('summary')?.focus();}
 }
 mount(draft);
 const proxy={};for(const method of ['read','validate','sectionValidity','sectionCompletion','showErrors','showSectionErrors','refreshErrors','canPublish','invalidateCompiled','showServerError','setCompiled'])proxy[method]=(...args)=>current[method]?.(...args);
 proxy.lock=(options={})=>{locked=true;lockOptions=options;current.lock(options);};return proxy;
}
function mountFields(form,scope,draft,{simple,published:immutable=false,onEdition}){
 const cfg=structuredClone(draft.configuration),saved=draft.guided_ux||{},confirmed={...(saved.confirmed||{})},subconfirmed={...(saved.subconfirmed||{})};
 const host=el('div',undefined,'model-wizard-v2'+(simple?' model-wizard-pro':''));host.dataset.dationTest='model-wizard-v2';form.append(host);
 const definitions=[
  ['Identidad del modelo','Definí un nombre y describí el alcance de este modelo logístico.','tag'],
  ['Operación logística','Definí el rol de tu empresa y cómo se organizan los viajes y la consolidación de órdenes.','resources'],
  ['Carga y capacidad','Configurá qué transportás, cómo se presenta la carga y qué capacidades se controlan.','pallet'],
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
 const steps=simple?[
  ['Definir la unidad logística','Primero definí cómo se despacha la mercadería y las dimensiones exteriores de la unidad cargada.'],
  ['Definir qué contiene esta unidad','Declarás un producto por presentación homogénea y cuántos bultos la componen.'],
  ['Restricciones físicas y reglas','Definí qué límites físicos controlará Dation y qué reglas se aplican a las órdenes.']
 ].map(([title,copy],i)=>stepPanel(cargo,i+1,title,copy)):STEP_COPY.map(([title,copy],i)=>guidedStep(cargo,i+1,title,copy,{open:saved.openSteps?saved.openSteps.includes(i+1):i===0}));
 const profile=radioCards(steps[0].body,'Perfil de carga','cargo_profile',PROFILES,cfg.cargo.profile),recommendation=note(steps[0].body,'');
 const directGuide=el('div'),unitHost=el('div');(simple?steps[0]:steps[1]).body.append(directGuide,unitHost);
 note(directGuide,'En configuración básica, las cantidades de carga y capacidades se declaran en las plantillas de órdenes y recursos. No se guarda un soporte físico reutilizable.');
 if(!simple)directGuide.append(button('Elegir nivel de detalle',()=>go(3)));
 const mode=simple?{value:'catalog',root:el('div')}:radioCards(steps[2].body,'Nivel de detalle','cargo_input_mode',[
  ['direct','Configuración básica','Cantidades declaradas en tus plantillas, sin catálogo de productos.','box'],
  ['catalog','Configuración detallada','Catálogo completo compatible con presentaciones históricas.','layers']
 ],cfg.cargo.input_mode);
 mode.root.classList.add('guided-detail-options');
 const modeNote=el('p'),na=el('p');if(!simple){steps[2].body.append(modeNote,na);na.textContent='Pasos4 y5 · No aplica: modo básico.';}
 const initial=saved.catalogue||{products:cfg.cargo.products||[],logistic_units:cfg.cargo.logistic_units||[],presentations:cfg.cargo.presentations||[]};
 // This is local UI state only. collect().configuration excludes it in direct.
 let editor;
 const rules=steps[simple?2:5].body;
 const dimensions=simple?checkboxCards(rules,'¿Qué restricciones físicas debe controlar Dation?','dimensions',[["weight_kg","Peso máximo","Controla que el peso total no supere la capacidad del vehículo.","weight"],["volume_m3","Volumen máximo","Controla que el volumen total no supere la capacidad del vehículo.","box"]],cfg.active_dimensions):choices(rules,'Dimensiones de capacidad activas','dimensions',DIMS,cfg.active_dimensions);
 if(simple)dimensions.root.classList.add('guided-two-columns');
 rules.append(el('p','Los límites concretos se declaran en la flota del Data Contract. Dation verifica simultáneamente todos los límites seleccionados. El volumen es escalar: no certifica encaje tridimensional.','d-field__help'));
 const primary=simple?{value:cfg.primary_dimension}:field(rules,'Dimensión principal de reporte',{name:'primary_dimension',options:DIMS,value:cfg.primary_dimension,help:'Referencia para cantidades y determinados objetivos; los demás límites siguen activos.'});
 const split=simple?radioCards(rules,'¿Qué reglas se aplican a las órdenes?','cargo_split_policy',[
  ['INDIVISIBLE','Orden sin fraccionamiento','La orden completa se asigna a un único viaje o queda sin servir.','box'],
  ['DISCRETE','Fraccionable por unidades completas','La orden puede repartirse entre viajes con presentaciones completas si permite fraccionamiento.','layers']
 ],cfg.cargo.split_policy):field(rules,'Fraccionamiento',{name:'cargo_split_policy',options:[['INDIVISIBLE','Orden completa en un viaje o no servida'],['DISCRETE','Cantidades discretas completas'],['CONTINUOUS','Granel por incremento físico']],value:cfg.cargo.split_policy});
 if(simple)split.root.classList.add('guided-two-columns');
 const advanced=el('details',undefined,'cargo-advanced');advanced.append(el('summary','Compatibilidad y co-carga avanzadas'));const advancedBody=el('div',undefined,'ultimate-grid');advanced.append(advancedBody);if(simple)rules.append(advanced);
 const compat=field(simple?advancedBody:rules,'Compatibilidad de carga',{name:'cargo_compatibility',options:[['UNIFORM_DECLARED','Uniforme declarada'],['CATEGORIZED','Por categorías explícitas']],value:cfg.cargo.compatibility_policy});
 note(simple?advancedBody:rules,'Una presentación homogénea contiene un solo producto; no autoriza co-carga ni cambia la consolidación. La compatibilidad entre productos sigue siendo una decisión explícita.');
 const pairsHost=el('section',undefined,'guided-pairs'),pairRows=el('div'),pairs=structuredClone(cfg.cargo.co_load_pairs||[]);pairsHost.append(el('h4','Pares autorizados para co-carga'),pairRows);(simple?advancedBody:rules).append(pairsHost);
 const groups=el('datalist');groups.id='guided-compatibility-'+crypto.randomUUID();pairsHost.append(groups);
 function renderPairs(){
  pairRows.replaceChildren();
  pairs.forEach((pair,index)=>{
   const row=el('div',undefined,'guided-pair-row');pairRows.append(row);
   pair.forEach((value,side)=>{const input=field(row,'Categoría '+(side===0?'A':'B'),{name:'cargo_pair_'+index+'_'+side,value,required:true});input.setAttribute('list',groups.id);scope.listen(input,'input',()=>{pair[side]=input.value.trim();});});
   row.append(button('Quitar pareja',()=>{pairs.splice(index,1);renderPairs();host.dispatchEvent(new Event('change',{bubbles:true}));}));
  });
 }
 const addPair=button('Agregar pareja de co-carga',()=>{if(pairs.length>=100)return;pairs.push(['','']);renderPairs();host.dispatchEvent(new Event('change',{bubbles:true}));pairRows.lastElementChild?.querySelector('input')?.focus();});pairsHost.append(addPair);renderPairs();
 const suggestion=button('Aplicar sugerencia de dimensiones del perfil',async()=>{
  const proposed=['DRY_BULK','LIQUID_BULK'].includes(profile.value)?['weight_kg','volume_m3']:profile.value==='PACKAGED'?['units','weight_kg']:['pallets','weight_kg'];
  const proposedPrimary=proposed.includes(primary.value)?primary.value:proposed[0];
  if(JSON.stringify(dimensions())!==JSON.stringify(proposed)&&!await confirmAction(host.closest('form'),scope,'Aplicar dimensiones sugeridas','Se reemplazarán las dimensiones activas por '+proposed.map(d=>DIMS.find(([id])=>id===d)[1]).join(' + ')+'. La principal será '+DIMS.find(([id])=>id===proposedPrimary)[1]+'. Las reglas de fraccionamiento no cambian.','Aplicar sugerencia'))return;
  for(const n of rules.querySelectorAll('[name=dimensions]'))n.checked=proposed.includes(n.value);
  primary.replaceChildren(...DIMS.filter(([v])=>proposed.includes(v)).map(([v,label])=>{const option=el('option',label);option.value=v;return option;}));
  primary.value=proposedPrimary;host.dispatchEvent(new Event('change',{bubbles:true}));
 });if(!simple)rules.append(suggestion);
 const categoryHint=note(simple?advancedBody:rules,'');
 editor=mountCargoEditor({units:unitHost,products:steps[simple?1:3].body,presentations:simple?el('div'):steps[4].body},scope,initial,{guided:simple,profile:()=>profile.value,categorized:()=>compat.value==='CATEGORIZED',ui:saved.selection||{},onNavigate:go});
 const physical=el('div',undefined,'model-v2-physical');physical.dataset.dationTest='cargo-physical-preview';physical.role='status';steps[simple?2:6].body.append(physical);
 const reviewSummary=el('dl',undefined,'guided-review-summary');if(!simple)steps[6].body.append(reviewSummary);
 const review=el('input');review.type='checkbox';review.name='cargo_review';review.dataset.guidedUi='true';
 if(!simple){const reviewLabel=el('label',undefined,'d-choice guided-review-confirm');reviewLabel.append(review,el('span','Revisé la configuración y sus límites. Confirmar este borrador validado por Dation.'));steps[6].body.append(reviewLabel);}
 const cargoErrors=el('p',undefined,'d-field__error');cargoErrors.dataset.errorFor='cargo_catalog';cargoErrors.role='alert';steps[simple?2:6].body.append(cargoErrors);
 if(simple){
  note(rules,'Las líneas de órdenes cuentan presentaciones completas, no kilogramos ni bultos interiores. La referencia técnica de reporte será peso si está activo; de lo contrario, volumen.');
  note(rules,'Esta versión guiada admite presentaciones homogéneas: un producto por presentación. Las composiciones mixtas existentes se conservan en el editor compatible. El volumen es exterior y escalar: no certifica packing 3D ni apilado.');
  const legacy=button('Configuración avanzada compatible',async()=>{
   if(locked||!await confirmAction(form.closest('form')||form,scope,'Abrir configuración compatible','Se conserva el borrador completo. Podrás configurar datos directos (2 CSV), unidades comerciales, composiciones históricas o granel continuo sin conversiones automáticas.','Abrir editor compatible'))return;
   const value=collect();onEdition('compatible');
  });legacy.dataset.editorCompatible='';rules.append(legacy);
 }
 if(!simple){const banner=note(cargo,'Editor compatible seleccionado explícitamente. Se conservan el modo, las unidades, los componentes y las dimensiones del contrato original.');banner.dataset.compatibleEditor='';if(assessGuidedDraft(draft).representable&&!immutable){const guided=button('Usar vista guiada de tres pasos',()=>onEdition('guided'));guided.dataset.useGuided='';banner.append(guided);}}
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
 let locked=false,published=immutable,compiledKey=null,compiledData=null,serverError='',lastConfig='',previousMode=mode.value,activeStep=saved.activeStep||1;
 const summary=el('aside',undefined,'model-v2-summary');summary.dataset.dationTest='model-v2-summary';host.append(summary);
 const config=()=>({version:2,operating_role:role.value,transport_pattern:'DIRECT',consolidation_permitted:consolidate.value==='yes',allowed_sources:sources(),resource_categories:categoryValues(),active_dimensions:dimensions(),primary_dimension:simple?(dimensions().includes('weight_kg')?'weight_kg':'volume_m3'):primary.value,split_permitted:split.value!=='INDIVISIBLE',homogeneous_loads_declared:compat.value==='UNIFORM_DECLARED',currency_policy:{currency:currency.value.trim().toUpperCase(),minor_units:Number(minor.value),rounding:'ROUND_HALF_UP'},own_cost_model:'OWN_OPERATING_CYCLE',external_cost_models:sources().includes('EXTERNAL')?external():[],per_km_billing_bases:sources().includes('EXTERNAL')&&external().includes('PER_KM')?billing():[],cargo:{profile:profile.value,input_mode:mode.value,split_policy:split.value,compatibility_policy:compat.value,co_load_pairs:compat.value==='CATEGORIZED'?pairs:[],...(mode.value==='catalog'?editor.read():{products:[],logistic_units:[],presentations:[]})}});
 const signature=()=>JSON.stringify(config());
 const localSignatures=c=>[JSON.stringify([name.value,description.value]),JSON.stringify([c.operating_role,c.consolidation_permitted]),JSON.stringify(c),JSON.stringify([c.allowed_sources,c.resource_categories]),JSON.stringify([c.allowed_sources,c.currency_policy,c.external_cost_models,c.per_km_billing_bases])];
 function subSignatures(c){
  return [c.cargo.profile,JSON.stringify([c.cargo.logistic_units,c.cargo.presentations.map(p=>[p.presentation_id,p.loaded_dimensions,p.gross_mass])]),c.cargo.input_mode,JSON.stringify(c.cargo.products),JSON.stringify([c.cargo.products,c.cargo.logistic_units,c.cargo.presentations]),JSON.stringify([c.active_dimensions,c.primary_dimension,c.cargo.split_policy,c.cargo.compatibility_policy,c.cargo.co_load_pairs]),JSON.stringify(c)];
 }
 const collect=()=>({id:draft.id,expected_revision:draft.expected_revision,name:name.value.trim(),description:description.value.trim(),status:draft.status||'active',configuration:config(),
  guided_ux:{origin:saved.origin,edition:simple?'ultimate':'compatible',editorChoice:simple?'guided':'compatible',catalogue:editor.snapshot(),selection:editor.ui(),confirmed:{...confirmed},subconfirmed:{...subconfirmed},activeStep,openSteps:steps.flatMap((s,i)=>s.details.open?[i+1]:[]),openBlocks:blocks.flatMap((b,i)=>b.details.open?[i+1]:[])}});
 function validate(){
  const c=config(),e={};if(!name.value.trim())e.model_name='Ingresá el nombre del Logistics Model.';
  if(!c.allowed_sources.length)e.sources='Elegí al menos una fuente de recursos.';
  if(!c.active_dimensions.length||!c.active_dimensions.includes(c.primary_dimension))e[simple?'cargo_catalog':'primary_dimension']='La dimensión principal debe estar activa.';
  if(!/^[A-Z]{3}$/.test(c.currency_policy.currency))e.currency='Ingresá una moneda de tres letras, por ejemplo ARS.';
  if(c.allowed_sources.includes('EXTERNAL')&&!c.external_cost_models.length)e.own_cost='Elegí una tarifa externa permitida.';
  if(c.allowed_sources.includes('EXTERNAL')&&c.external_cost_models.includes('PER_KM')&&!c.per_km_billing_bases.length)e.own_cost='Elegí una base de facturación por kilómetro.';
  if(c.cargo.co_load_pairs.some(p=>p.length!==2||p.some(v=>!v)))e.cargo_catalog='Ingresá exactamente dos categorías por pareja.';
  if(c.cargo.input_mode==='catalog'){const message=editor.validate();if(message)e.cargo_catalog=message;}
  for(const n of host.querySelectorAll('input,select,textarea'))if(!n.disabled&&!n.dataset.guidedUi&&!n.validity.valid)e[n.name]=n.validationMessage;
  return e;
 }
 function sectionValidity(){
  const errors=validate();return blocks.map((b,i)=>!Object.keys(errors).some(key=>b.body.querySelector('[name="'+CSS.escape(key)+'"]')||(i===2&&key==='cargo_catalog')||(i===3&&key==='sources')||(i===4&&key==='own_cost')));
 }
 function sectionCompletion(){
  const c=config(),keys=localSignatures(c),valid=sectionValidity();
  return keys.map((key,i)=>valid[i]&&(published||confirmed[i]===key&&(i!==2||compiledKey===JSON.stringify(c))));
 }
 const shown=new Set();
 const belongs=(index,key)=>!!blocks[index].body.querySelector('[name="'+CSS.escape(key)+'"]')||index===2&&key==='cargo_catalog'||index===3&&key==='sources'||index===4&&key==='own_cost';
 function paintErrors(index,errors){
  const body=blocks[index].body;
  if(index===3){sourceError.textContent=errors.sources||'';for(const n of body.querySelectorAll('[name=sources]')){if(errors.sources)n.setAttribute('aria-invalid','true');else n.removeAttribute('aria-invalid');}}
  if(index===4)costError.textContent=errors.own_cost||'';
  for(const box of body.querySelectorAll('[data-error-for]'))box.textContent=errors[box.dataset.errorFor]||'';
  for(const n of body.querySelectorAll('input,select,textarea')){if(errors[n.name])n.setAttribute('aria-invalid','true');else if(n.name!=='sources')n.removeAttribute('aria-invalid');}
 }
 function refreshErrors(){const errors=validate();for(const index of shown)paintErrors(index,errors);}
 function showSectionErrors(index){
  const errors=Object.fromEntries(Object.entries(validate()).filter(([key])=>belongs(index,key)));shown.add(index);paintErrors(index,errors);
  if(Object.keys(errors).length){blocks[index].details.open=true;const body=blocks[index].body,target=body.querySelector('[aria-invalid=true]')||body.querySelector('.d-field__error:not(:empty)');
   if(target){let parent=target.parentElement;while(parent&&parent!==body){if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement;}if(!target.matches('input,select,textarea'))target.tabIndex=-1;target.focus();}}
  return errors;
 }
 function showErrors(){const errors=validate();for(let i=0;i<5;i++){shown.add(i);paintErrors(i,errors);}const first=blocks.findIndex((b,i)=>Object.keys(errors).some(key=>belongs(i,key)));if(first>=0)showSectionErrors(first);return errors;}
 function reviewed(){host.dispatchEvent(new CustomEvent('model-review',{bubbles:true}));}
 for(const index of [0,1,3,4]){
  const confirm=confirmFooter(blocks[index].body,'Confirmar '+definitions[index][0].toLocaleLowerCase(),()=>{
   const valid=sectionValidity();if(!valid[index]){showSectionErrors(index);return;}
   confirmed[index]=localSignatures(config())[index];sync();reviewed();
  });confirm.dataset.confirmBlock=String(index+1);
 }
 const flowActions=el('div',undefined,'guided-flow-actions'),back=button('Volver',()=>go(previous(activeStep))),next=button('Continuar',()=>{
  const errors=validate(),valid=activeStep===1||activeStep===3||activeStep===6&&!errors.primary_dimension&&!errors.cargo_catalog||[2,4,5].includes(activeStep)&&!errors.cargo_catalog;
  if(valid)subconfirmed[activeStep-1]=subSignatures(config())[activeStep-1];go(following(activeStep));sync();reviewed();
 });flowActions.append(back,next);if(!simple)cargo.append(flowActions);
 const cargoConfirm=simple?confirmFooter(cargo,'Confirmar carga y capacidad',()=>{
  if(locked)return;if(Object.keys(showSectionErrors(2)).length)return;
  if(compiledKey!==signature()){cargoErrors.textContent=serverError||'La confirmación requiere el preview vigente de Dation. Revisá los datos físicos y las dependencias de recursos y costos.';cargoErrors.tabIndex=-1;cargoErrors.focus();return;}confirmed[2]=signature();sync();reviewed();
 }):null;if(cargoConfirm)cargoConfirm.dataset.confirmBlock='3';
 function following(step){return mode.value==='direct'&&step===3?6:Math.min(7,step+1);}
 function previous(step){return mode.value==='direct'&&step===6?3:Math.max(1,step-1);}
 function go(step){
  activeStep=step;for(const [i,s]of steps.entries())s.details.open=i===step-1;
  const target=steps[step-1].details;target.querySelector('summary').focus();target.scrollIntoView({block:'nearest'});sync();
 }
 for(const [index,s]of (simple?[]:steps).entries())scope.listen(s.details,'toggle',()=>{if(s.details.open){activeStep=index+1;updateFlow();}});
 for(const [index,s]of (simple?[]:steps).entries())scope.listen(s.body,'focusin',()=>{activeStep=index+1;updateFlow();});
 for(const [index,s]of (simple?[]:steps).entries())scope.listen(s.details.querySelector('summary'),'focusin',()=>{activeStep=index+1;updateFlow();});
 function updateFlow(){if(simple)return;back.disabled=activeStep===1;next.hidden=activeStep===7;next.textContent=activeStep===5?'Continuar a capacidades y reglas':'Continuar a '+STEP_COPY[following(activeStep)-1][0].toLocaleLowerCase();flowActions.dataset.activeCargoStep=String(activeStep);}
 scope.listen(review,'input',e=>e.stopPropagation());scope.listen(review,'change',e=>{e.stopPropagation();if(review.checked&&compiledKey===signature())confirmed[2]=signature();else delete confirmed[2];sync();reviewed();});
 function sync(){
  const c=config(),key=JSON.stringify(c),keys=localSignatures(c),subs=subSignatures(c);
  if(lastConfig&&key!==lastConfig){compiledKey=null;compiledData=null;serverError='';editor.invalidate();}lastConfig=key;
  for(const i of Object.keys(confirmed))if(confirmed[i]!==keys[i])delete confirmed[i];
  for(const i of Object.keys(subconfirmed))if(subconfirmed[i]!==subs[i])delete subconfirmed[i];
  const catalog=mode.value==='catalog';unitHost.hidden=!catalog;directGuide.hidden=catalog;
  if(!simple)steps[3].details.hidden=steps[4].details.hidden=!catalog;na.hidden=catalog;editor.setActive(catalog&&!locked);
  recommendation.lastChild.textContent=profile.value==='PALLETIZED'?'Si transportás mercadería agrupada sobre pallets, elegí Carga palletizada. El perfil orienta la configuración; no certifica el acomodamiento físico ni modifica por sí solo el algoritmo.':'Elegiste '+(PROFILES.find(p=>p[0]===profile.value)?.[1]||'un perfil')+'. Conservamos los datos existentes; revisá las propiedades y reglas aplicables.';
  modeNote.textContent=catalog?'Configuración detallada: productos y composiciones con tres CSV, incluidos Líneas de órdenes.':'Configuración básica: dos CSV de Órdenes y Recursos, sin catálogo físico. Un catálogo anterior se conserva sólo como borrador en este navegador y no se publica.';
  pairsHost.hidden=compat.value!=='CATEGORIZED';for(const n of pairsHost.querySelectorAll('input,button'))n.disabled=locked||pairsHost.hidden;addPair.disabled=locked||pairsHost.hidden||pairs.length>=100;
  const knownGroups=[...new Set(editor.snapshot().products.flatMap(p=>p.compatibility_groups||[]))];groups.replaceChildren(...knownGroups.map(v=>{const n=el('option');n.value=v;return n;}));
  categoryHint.hidden=compat.value!=='CATEGORIZED'||!catalog;categoryHint.lastChild.textContent='Cada producto utilizado necesita categorías de compatibilidad. Declaralas en Productos; no se elige uniformidad para omitir errores.';
  const existingPrimary=primary.value,active=dimensions();if(!simple)primary.replaceChildren(...DIMS.filter(([v])=>active.includes(v)||v===existingPrimary).map(([v,label])=>{const n=el('option',label+(active.includes(v)?'':' · inactiva'));n.value=v;return n;}));primary.value=existingPrimary;
  const hasExternal=sources().includes('EXTERNAL');for(const n of costs.querySelectorAll('[name=external_costs]')){n.disabled=locked||!hasExternal;n.closest('fieldset').hidden=!hasExternal;}
  for(const n of costs.querySelectorAll('[name=billing]')){n.disabled=locked||!hasExternal||!external().includes('PER_KM');n.closest('fieldset').hidden=!hasExternal||!external().includes('PER_KM');}own.hidden=!sources().includes('OWN');billingNote.hidden=!hasExternal||!external().includes('PER_KM');
  const complete=sectionCompletion();blocks.forEach((b,i)=>b.setStatus(complete[i]?'validado y revisado':i===2&&serverError?'revisá el error de validación':'pendiente de revisión',complete[i]?'complete':i===2&&serverError?'error':'pending'));
  if(!simple)steps.forEach((s,i)=>{const local=subconfirmed[i]===subs[i]&&([0,2].includes(i)||compiledKey===key)&&!serverError,done=local||i===6&&complete[2];s.setStatus(done?'revisado':'pendiente de revisión',done?'complete':'pending');});
  if(cargoConfirm){cargoConfirm.disabled=locked;cargoConfirm.dataset.previewCurrent=String(compiledKey===key);cargoConfirm.title=compiledKey===key?'Configuración física validada por Dation':serverError||'Podés revisar los campos. La confirmación requiere el preview actual; no se publica desde aquí.';cargoConfirm.setAttribute('aria-busy',String(!locked&&compiledKey!==key&&!serverError&&sectionValidity().every(Boolean)));}
  currencyNote.lastChild.textContent='Moneda seleccionada: '+currency.value+'. Los costos deben ingresarse en esta moneda; Dation no convierte divisas automáticamente.';
  review.checked=complete[2];review.disabled=locked||compiledKey!==key||!sectionValidity().every(Boolean);
  reviewSummary.replaceChildren();readout(reviewSummary,'Perfil',PROFILES.find(p=>p[0]===profile.value)?.[1]);readout(reviewSummary,'Modo',catalog?'Configuración detallada':'Configuración básica');
  readout(reviewSummary,'Catálogo',catalog?c.cargo.products.length+' productos · '+c.cargo.logistic_units.length+' soportes · '+c.cargo.presentations.length+' presentaciones':'No aplica: cantidades desde CSV');
  readout(reviewSummary,'Dimensiones activas',DIMS.filter(([v])=>active.includes(v)).map(([,s])=>s).join(' + ')||'Pendiente');
  readout(reviewSummary,'Dimensión principal',DIMS.find(([v])=>v===primary.value)?.[1]);readout(reviewSummary,'Fraccionamiento',simple?(split.value==='INDIVISIBLE'?'Orden sin fraccionamiento':'Fraccionable por unidades completas'):split.selectedOptions[0]?.textContent);readout(reviewSummary,'Compatibilidad',compat.selectedOptions[0]?.textContent);
  readout(reviewSummary,'Recursos',sources().join(' + ')||'Pendiente');readout(reviewSummary,'Moneda',c.currency_policy.currency);
  readout(reviewSummary,'Data Contract previsto',catalog?'3 CSV: Órdenes + Líneas de órdenes + Recursos':'2 CSV: Órdenes + Recursos',compiledKey===key?'Validado por Dation para este borrador':'Pendiente de validación vigente');
  summary.textContent=(simple?'Catálogo homogéneo':PROFILES.find(p=>p[0]===profile.value)?.[1]||'Carga')+' · '+(catalog?c.cargo.products.length+' productos · '+c.cargo.presentations.length+' presentaciones':'Datos directos · sin catálogo')+' · '+active.map(v=>DIMS.find(([id])=>id===v)[1]).join(' + ');
  if(!compiledData&&!serverError){physical.role='status';physical.textContent='Las propiedades físicas se muestran después de validar el contrato actual con Dation.';}updateFlow();
 }
 scope.listen(mode.root,'input',e=>e.stopPropagation());scope.listen(mode.root,'change',async e=>{
  e.stopPropagation();const nextMode=mode.value;mode.value=previousMode;
  if(nextMode==='direct'&&editor.hasData()&&!await confirmAction(host.closest('form'),scope,'Pasar a configuración básica','El catálogo no se publicará. ¿Querés conservarlo como borrador de este navegador y continuar? Podés volver a Detallado.','Conservar y continuar'))return;
  mode.value=previousMode=nextMode;sync();host.dispatchEvent(new Event('change',{bubbles:true}));
 });
 scope.listen(profile.root,'change',()=>editor.refreshProfile());scope.listen(compat,'change',()=>editor.refreshProfile());
 scope.listen(host,'focusout',event=>event.stopPropagation());
 scope.listen(host,'input',sync);scope.listen(host,'change',sync);sync();
 return {read:collect,validate,sectionValidity,sectionCompletion,showErrors,showSectionErrors,refreshErrors,canPublish:()=>!locked&&compiledKey===signature()&&sectionCompletion().every(Boolean),
  invalidateCompiled(){compiledKey=null;compiledData=null;editor.invalidate();sync();},
  showServerError(message,{focus=false}={}){compiledKey=null;compiledData=null;serverError=message;physical.textContent=message;physical.role='alert';editor.showError(message);sync();if(focus){blocks[2].details.open=true;physical.tabIndex=-1;physical.focus();}},
  lock({published:immutable=false}={}){locked=true;published=immutable;editor.lock();for(const n of host.querySelectorAll('input,select,textarea,button'))if(!n.dataset.guidedUi)n.disabled=true;sync();},
  setCompiled(data){
   compiledKey=signature();compiledData=data;serverError='';physical.replaceChildren();physical.role='status';const catalogue=data?.contracts?.transport_demand?.rules?.catalog_snapshot;editor.setCompiled(catalogue);
   if(catalogue&&mode.value==='catalog')for(const [key,p]of Object.entries(catalogue)){
    const label=config().cargo.presentations.find(v=>v.presentation_id===key)?.label||'Presentación',row=el('p');row.append(el('strong',label+' · '),document.createTextNode(Object.entries(p.coefficients).filter(([,v])=>v!==null).map(([d,v])=>v+' '+(DIMS.find(([id])=>id===d)?.[1]||d)).join(' · ')));
    row.append(el('small','Incremento: '+p.allocation_increment+' '+(p.quantity_unit==='presentation'?'presentación completa':p.quantity_unit)+' · '+Object.entries(p.provenance.sources).map(([d,source])=>(DIMS.find(([id])=>id===d)?.[1]||d)+': '+(PHYSICAL_SOURCES[source]||source)).join(' · ')));physical.append(row);
   }else physical.textContent='Cantidades directas: contrato de dos CSV validado para este borrador.';
   sync();refreshErrors();
  }
 };
}
