import {el,button,confirmAction} from './forms.mjs';
import {modelField as field,radioCards,note,readout,display,statusCircle} from './guided-ui.mjs';
import {dimensionInUnit} from './cargo-presentation-values.mjs';
import {unitArt,volumeCard,volumeText,sectionHeading} from './cargo-presentation-ui.mjs';
import {createCargoState,volume,fingerprint} from './cargo-guided-state.mjs';
const TYPES=[['PALLET','Pallet','Mercadería agrupada sobre pallet.','pallet'],['BOX','Caja','Unidad transportada en cajas individuales.','box'],['CRATE','Cajón','Carga despachada en cajones o bins.','container'],['BIG_BAG','Big bag','Carga contenida en big bags flexibles.','bag'],['OTHER','Otra unidad','Configuración personalizada.','layers']];
const nameOf=type=>TYPES.find(t=>t[0]===type)?.[1]||type;
// Only this renderer owns the new three-step catalog interaction. The previous
// catalog manager is not mounted or hidden beneath it.
export function mountCargoGuidedEditor({units:one,products:two},scope,catalog,{ui={},profile}={}){
 const model=createCargoState(catalog,ui),s=model.state,originalType=s.unit.type,unitControls={},productControls={};let locked=false,busy=false,showErrors=false,previewError=false,unitChanged=false;
 const type=radioCards(one,'Tipo de unidad logística','guided_unit_type',TYPES,s.unit.type);type.root.classList.add('guided-five-columns','r5-unit-options');
 for(const input of type.root.querySelectorAll('input')){const icon=input.closest('label').querySelector('svg'),art=unitArt(input.value);delete art.node.dataset.supportArt;art.node.dataset.artSlot='option';icon.replaceWith(art.node);}
 const choiceHelp=el('p','Seleccioná la unidad principal con la que transportás la carga.','d-field__help');type.root.insertBefore(choiceHelp,type.root.querySelector('.guided-radio-grid'));
 note(one,'Elegí la unidad logística que realmente viaja en el transporte. Su composición se define en el Paso 2.');
 const unitLayout=el('div',undefined,'r4-physical-layout r5-cargo-layout'),unitForm=el('div',undefined,'r4-field-grid r5-field-form'),unitSummary=el('aside',undefined,'guided-physical-summary');unitLayout.append(unitForm,unitSummary);one.append(el('hr',undefined,'r5-section-divider'),unitLayout);
 sectionHeading(unitForm,'Dimensiones de la unidad cargada','Estas medidas describen el espacio exterior ocupado por la unidad que será asignada a los vehículos.');
 const add=(parent,label,name,key,values,options={})=>{const n=field(parent,label,{name,value:values[key],required:true,...options});n.dataset.guidedUi='true';return n;};
 unitControls.name=add(unitForm,'Nombre de la unidad *','unit_name','name',s.unit,{maxLength:120});
 unitControls.measure=add(unitForm,'Unidad de medida','unit_measure','measure',s.unit,{options:[['cm','cm'],['m','m']]});
 const unitDims=el('div',undefined,'r4-dimensions');unitForm.append(unitDims);
 for(const [key,label]of [['length','Largo *'],['width','Ancho *'],['height','Alto cargado *']])unitControls[key]=add(unitDims,label,'unit_'+key,key,s.unit,{type:'number'});
 unitControls.exteriorVolume=add(unitForm,'Volumen exterior cargado (m³) *','unit_volume','exteriorVolume',s.unit,{type:'number'});
 const unitTail=el('div',undefined,'r5-form-tail'),unitTailFields=el('div',undefined,'r5-tail-fields');unitTail.append(unitTailFields);unitForm.append(unitTail);
 unitControls.tareKg=add(unitTailFields,'Tara del soporte (kg) *','unit_tare','tareKg',s.unit,{type:'number',help:'Peso del soporte vacío. Usá 0 sólo cuando corresponda.'});
 const unitVolume=volumeCard('Volumen exterior calculado','Calculado con largo × ancho × alto exterior.');unitVolume.node.dataset.cargoMetric='volume';unitTail.append(unitVolume.node);
 one.append(el('p','Dation calcula el volumen exterior de la unidad cargada. No certifica el acomodo físico de los bultos.','d-field__help'));
 const composition=el('div',undefined,'r4-physical-layout r5-cargo-layout'),productForm=el('div',undefined,'r4-field-grid r5-field-form'),productSummary=el('aside',undefined,'guided-physical-summary');composition.append(productForm,productSummary);two.append(composition);
 sectionHeading(productForm,'Producto y tipo de bulto','Identificá el producto y la unidad mínima que compone esta carga.');
 productControls.name=add(productForm,'Nombre del producto *','product_name','name',s.form.values,{maxLength:120});
 const packages=[['caja','Caja'],['saco','Saco'],['bolsa','Bolsa'],['fardo','Fardo'],['bulto','Bulto'],['otra','Otra']];
 if(!packages.some(([id])=>id===s.form.values.packageType))packages.push([s.form.values.packageType,s.form.values.packageType]);
 productControls.packageType=add(productForm,'Tipo de bulto *','product_package','packageType',s.form.values,{options:packages});
 sectionHeading(productForm,'Dimensiones y peso del bulto','Estas medidas describen cada bulto y permiten calcular el peso bruto de la unidad cargada.');
 const productDims=el('div',undefined,'r4-dimensions');productForm.append(productDims);
 for(const [key,label]of [['length','Largo del bulto (cm) *'],['width','Ancho del bulto (cm) *'],['height','Alto del bulto (cm) *']])productControls[key]=add(productDims,label,'product_'+key,key,s.form.values,{type:'number'});
 const productTail=el('div',undefined,'r5-form-tail'),productTailFields=el('div',undefined,'r5-tail-fields');productTail.append(productTailFields);productForm.append(productTail);
 const packageVolume=volumeCard('Volumen por bulto','Derivado de las dimensiones del bulto; dato informativo.');packageVolume.node.dataset.packageVolume='';productTail.append(packageVolume.node);
 productControls.massKg=add(productTailFields,'Peso bruto por bulto (kg) *','product_mass','massKg',s.form.values,{type:'number'});
 productControls.quantity=add(productTailFields,'Bultos por unidad logística *','product_quantity','quantity',s.form.values,{type:'number'});productControls.quantity.step='1';
 note(two,'Dation calcula el peso bruto total a partir de la cantidad de bultos, su peso y la tara de la unidad logística.');
 const feedback=el('p',undefined,'d-metadata');feedback.role='status';feedback.setAttribute('aria-live','polite');const saveGuide=el('aside',undefined,'r5-save-guide');saveGuide.dataset.saveGuide='';saveGuide.append(el('strong','Tipo registrado en este borrador'),el('p','Completá nuevamente el formulario superior si necesitás registrar otro producto para esta misma unidad logística.'));two.append(saveGuide);
 const actionRow=el('div',undefined,'r4-save-row'),save=button('Guardar tipo de carga',saveType,'primary');save.dataset.saveLoadType='';actionRow.append(feedback,save);two.append(actionRow);
 const history=el('section',undefined,'r4-history'),historyHead=el('header',undefined,'r5-history-heading'),historyTitle=el('h4','Tipos de carga registrados'),counter=el('span',undefined,'d-metadata'),cards=el('div',undefined,'r4-history-cards'),limit=el('p',undefined,'guided-note');historyHead.append(historyTitle,counter);history.append(historyHead,el('p','Cada tarjeta representa una carga homogénea guardada para esta unidad logística.','d-field__help'),cards);history.dataset.loadHistory='';two.append(history,limit);
 const emptyArt=unitArt(s.unit.type),loadedArt=unitArt(s.unit.type,{loaded:true}),unitReadings=el('dl'),productReadings=el('dl'),unitBridge=note(el('div'),'En el siguiente paso vas a definir el contenido de esta unidad.');unitSummary.append(el('h4','Resumen de la unidad'),emptyArt.node,unitReadings,unitBridge);productSummary.append(el('h4','Resumen de la composición'),loadedArt.node,productReadings);
 const cardViews=new Map();let feedbackKind='state';
 for(const n of [...Object.values(unitControls),...Object.values(productControls)])if(n.type==='number'){n.step=n.name==='product_quantity'?'1':'any';n.min=n.name==='unit_tare'?'0':'0.000001';}
 function notify(){one.dispatchEvent(new Event('change',{bubbles:true}));}
 function resetForm(){for(const [key,n]of Object.entries(productControls)){if(key==='packageType'&&![...n.options].some(o=>o.value===s.form.values[key])){const o=el('option',s.form.values[key]);o.value=s.form.values[key];n.append(o);}n.value=s.form.values[key];}showErrors=false;paint({});}
 function paint(errors){for(const n of [...Object.values(unitControls),...Object.values(productControls)]){const error=errors[n.name];if(error)n.setAttribute('aria-invalid','true');else n.removeAttribute('aria-invalid');n.closest('.d-field').querySelector('.d-field__error').textContent=error||'';}}
 function values(){for(const [key,n]of Object.entries(productControls))s.form.values[key]=n.value;}
 function stats(v){const quantity=Number(v.quantity),mass=Number(v.massKg),tare=Number(s.unit.tareKg);return v.quantity!==''&&v.massKg!==''&&s.unit.tareKg!==''&&quantity>0&&mass>0?{content:quantity*mass,gross:quantity*mass+tare}:null;}
 function summarize(){
  const u=s.unit,v=s.form.values,st=stats(v),unit=nameOf(u.type),vol=model.unitVolume();unitVolume.update(vol,['BIG_BAG','OTHER'].includes(u.type)?'Volumen exterior declarado para esta unidad.':undefined);packageVolume.update(volume(v));
  emptyArt.update(u.type);loadedArt.update(u.type);unitReadings.replaceChildren();
  readout(unitReadings,'Tipo',unit);readout(unitReadings,'Dimensiones',vol===null?null:['BIG_BAG','OTHER'].includes(u.type)?volumeText(vol):[u.length,u.width,u.height].join(' × ')+' '+u.measure);readout(unitReadings,'Tara',display(u.tareKg,'kg'));readout(unitReadings,'Volumen exterior',volumeText(vol));
  productReadings.replaceChildren();readout(productReadings,'Producto',v.name||null);readout(productReadings,'Tipo de bulto',v.packageType);readout(productReadings,'Bultos por unidad',display(v.quantity));readout(productReadings,'Peso por bulto',display(v.massKg,'kg'));readout(productReadings,'Peso del contenido',display(st?.content,'kg'));readout(productReadings,'Tara',display(u.tareKg,'kg'));const total=readout(productReadings,'Peso bruto total',display(st?.gross,'kg'));total.dataset.cargoMetric='gross';total.classList.add('r5-gross-total');readout(productReadings,'Volumen exterior',volumeText(vol));if(st)readout(productReadings,'Cálculo',display(v.quantity)+' × '+display(v.massKg,'kg')+' + '+display(u.tareKg,'kg')+' = '+display(st.gross,'kg'));
 }
 function renderHistory(){
  history.hidden=s.savedTypes.length===0;counter.textContent=s.savedTypes.length+' de 2 tipos';const nodes=[];
  for(const [i,t]of s.savedTypes.entries()){
   const v=model.formFrom(t),st=stats(v),id=t.presentation.presentation_id,needsReview=s.review||s.form.target===id&&model.dirty();let view=cardViews.get(id);
   if(!view){const card=button('',async()=>{
    if(locked||busy)return;if(model.dirty()&&!await confirmAction(one.closest('form'),scope,'Conservar o descartar cambios','Hay cambios sin guardar en el formulario. Podés cancelar para conservarlos o descartarlos para abrir el tipo seleccionado.','Descartar cambios'))return;
    model.select(id);resetForm();feedbackKind='state';refresh();notify();productControls.name.focus();
   }),art=unitArt(s.unit.type,{loaded:true}),title=el('strong'),metrics=el('span'),status=el('small'),mark=el('span');card.classList.add('r4-load-card');card.dataset.loadType=id;card.append(art.node,title,metrics,status,mark);view={card,art,title,metrics,status,mark};cardViews.set(id,view);}
   view.card.disabled=locked;view.card.setAttribute('aria-pressed',String(s.form.target===id));view.card.setAttribute('aria-label','Tipo '+String(i+1).padStart(2,'0')+' · '+t.product.name+' · '+(needsReview?'Requiere revisión':'Guardado en este borrador'));
   view.art.update(s.unit.type);view.title.textContent='Tipo '+String(i+1).padStart(2,'0')+' · '+t.product.name;view.metrics.textContent=display(v.quantity)+' '+v.packageType+'s · '+display(st?.gross,'kg')+' · '+volumeText(model.unitVolume());view.status.textContent=needsReview?'Requiere revisión':'Guardado en este borrador';
   statusCircle(view.mark,needsReview?'Requiere revisión':'Guardado en este borrador',needsReview?'pending':'complete');view.mark.classList.add('r4-load-status');view.card.title=(locked?'Tipo de carga · ':'Revisar ')+t.product.name;nodes.push(view.card);
  }
  if(nodes.length!==cards.children.length||nodes.some((n,i)=>cards.children[i]!==n))cards.replaceChildren(...nodes);
 }
 function saveMessage(){
  const dirty=model.dirty(),count=s.savedTypes.length,index=s.savedTypes.findIndex(t=>t.presentation.presentation_id===s.form.target);saveGuide.hidden=locked||count!==1||dirty||!!s.form.target;
  if(feedbackKind==='error')return;
  feedback.className='d-metadata';feedback.role='status';
  const text=locked?'Configuración de solo lectura.':busy?'Guardando tipo de carga…':unitChanged?'La unidad cambió; revisá los tipos registrados.':s.form.target?(dirty?'Estás editando Tipo '+String(index+1).padStart(2,'0')+'.':'Este tipo ya está guardado.'):count===2?'2 de 2 tipos registrados.':count===1?(dirty?'Estás configurando el segundo tipo (2 de 2).':'Tipo de carga guardado. Podés completar nuevamente este formulario para registrar otro tipo de carga con la misma unidad logística.'):dirty?'':'Completá los datos para registrar el primer tipo de carga.';
  if(feedback.textContent!==text)feedback.textContent=text;
 }
 function refresh(){
  const full=!s.form.target&&s.savedTypes.length>=2,irregular=['BIG_BAG','OTHER'].includes(s.unit.type);
  for(const [key,n]of Object.entries(unitControls)){n.disabled=locked;n.closest('.d-field').hidden=irregular?['length','width','height','measure'].includes(key):key==='exteriorVolume';}
  for(const n of type.root.querySelectorAll('input'))n.disabled=locked;
  for(const n of Object.values(productControls))n.disabled=locked||full;
  unitControls.measure.closest('.d-field').hidden=irregular;unitDims.hidden=irregular;
  save.textContent=s.form.target?'Actualizar tipo de carga':'Guardar tipo de carga';save.disabled=locked||busy||full||!!s.form.target&&!model.dirty()||!s.form.target&&s.savedTypes.length>0&&!model.dirty();save.setAttribute('aria-busy',String(busy));
  limit.hidden=!locked&&!full;limit.textContent=locked?'Configuración de solo lectura. Los tipos de carga se conservan sin cambios.':full?'Ya registraste dos tipos de carga. Seleccioná una tarjeta inferior para revisar o actualizar uno.':'';
  for(const [key,label]of [['length','Largo'],['width','Ancho'],['height','Alto']])productControls[key].closest('.d-field').querySelector('label').textContent=label+' de '+s.form.values.packageType+' ('+s.form.values.unit+') *';
  if(showErrors)paint(model.formErrors());summarize();renderHistory();saveMessage();
 }
 function saveType(){
  if(locked||busy||save.disabled)return;values();busy=true;const result=model.save();busy=false;
  if(!result.ok){feedbackKind='error';showErrors=true;paint(result.errors);feedback.className='d-field__error';feedback.role='alert';feedback.textContent='Revisá los campos del tipo de carga.';const invalid=one.closest('form').querySelector('[data-pro-step] [aria-invalid=true]');invalid?.focus();return;}
  feedback.className='d-metadata';feedback.role='status';feedbackKind='state';previewError=false;unitChanged=false;resetForm();refresh();notify();
 }
 for(const [key,n]of Object.entries(unitControls))scope.listen(n,'input',()=>{if(locked)return;if(s.savedTypes.length&&s.unit[key]!==n.value)unitChanged=true;if(key==='measure'){for(const axis of ['length','width','height']){const value=dimensionInUnit(s.unit[axis],s.unit.measure,n.value);model.setUnit(axis,value);unitControls[axis].value=value;}}model.setUnit(key,n.value);feedbackKind='state';refresh();});
 for(const n of Object.values(productControls))scope.listen(n,'input',()=>{if(locked||n.disabled)return;values();feedbackKind='state';refresh();});
 scope.listen(type.root,'input',e=>e.stopPropagation());scope.listen(type.root,'change',async e=>{
  e.stopPropagation();const next=type.value,previous=s.unit.type;type.value=previous;if(locked||next===previous)return;
  if((s.savedTypes.length||Object.values(s.unit).some((v)=>v!==''&&v!==s.unit.id&&v!==s.unit.type&&v!=='cm'))&&!await confirmAction(one.closest('form'),scope,'Cambiar unidad logística','Se conservarán los tipos y sus identificadores. Revisá la geometría exterior y confirmá nuevamente la carga.','Cambiar unidad'))return;
  const priorVolume=model.unitVolume();unitChanged=s.savedTypes.length>0;model.setUnit('type',next);if(['BIG_BAG','OTHER'].includes(next)&&!s.unit.exteriorVolume&&priorVolume!==null)model.setUnit('exteriorVolume',String(priorVolume));type.value=next;unitControls.exteriorVolume.value=s.unit.exteriorVolume;refresh();notify();
 });
 refresh();
 return {read:model.read,snapshot:model.read,ui:model.snapshot,validate:model.validate,hasData:()=>s.savedTypes.length>0,dirty:model.dirty,getProfile:()=>s.unit.type===originalType&&profile?profile:s.unit.type==='PALLET'?'PALLETIZED':'PACKAGED',setActive(){},refreshProfile(){},invalidate(){},showError(message){previewError=true;feedbackKind='error';feedback.className='d-field__error';feedback.role='alert';feedback.textContent=message;},setCompiled(){if(previewError){feedbackKind='state';feedback.className='d-metadata';feedback.role='status';feedback.textContent='Contrato físico vigente.';previewError=false;}s.review=false;unitChanged=false;refresh();},lock(){locked=true;refresh();},unitName:()=>nameOf(s.unit.type),bufferSignature:()=>model.dirty()?fingerprint(s.form):'',state:model};
}
