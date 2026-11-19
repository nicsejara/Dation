import {el,button,confirmAction} from './forms.mjs';
import {modelField as field,radioCards,note,readout,supportArt,display,statusCircle} from './guided-ui.mjs';
import {createCargoState,volume,fingerprint} from './cargo-guided-state.mjs';
const TYPES=[['PALLET','Pallet','Mercadería agrupada sobre pallet.','pallet'],['BOX','Caja','Unidad transportada en cajas individuales.','box'],['CRATE','Cajón','Carga despachada en cajones o bins.','container'],['BIG_BAG','Big bag','Carga contenida en big bags flexibles.','bag'],['OTHER','Otra unidad','Configuración personalizada.','layers']];
const nameOf=type=>TYPES.find(t=>t[0]===type)?.[1]||type;
// Only this renderer owns the new three-step catalog interaction. The previous
// catalog manager is not mounted or hidden beneath it.
export function mountCargoGuidedEditor({units:one,products:two},scope,catalog,{ui={},profile}={}){
 const model=createCargoState(catalog,ui),s=model.state,originalType=s.unit.type,unitControls={},productControls={};let locked=false,busy=false,showErrors=false,previewError=false;
 const type=radioCards(one,'¿Cómo se despacha tu mercadería?','guided_unit_type',TYPES,s.unit.type);type.root.classList.add('guided-five-columns');
 const choiceHelp=el('p','Seleccioná la unidad logística principal que utilizás para transportar la carga.','d-field__help');type.root.insertBefore(choiceHelp,type.root.querySelector('.guided-radio-grid'));
 note(one,'Elegí la unidad logística que realmente viaja en el transporte. La composición interna se define en el Paso 2.');
 const unitLayout=el('div',undefined,'r4-physical-layout'),unitForm=el('div',undefined,'r4-field-grid'),unitSummary=el('aside',undefined,'guided-physical-summary');unitLayout.append(unitForm,unitSummary);one.append(unitLayout);
 unitForm.append(el('h4','Definí las dimensiones de esta unidad'));unitForm.append(el('p','Estas medidas representan la unidad cargada que será asignada a los vehículos.','d-field__help'));
 const add=(parent,label,name,key,values,options={})=>{const n=field(parent,label,{name,value:values[key],required:true,...options});n.dataset.guidedUi='true';return n;};
 unitControls.name=add(unitForm,'Nombre de la unidad *','unit_name','name',s.unit,{maxLength:120});
 unitControls.measure=add(unitForm,'Unidad de medida','unit_measure','measure',s.unit,{options:[['cm','cm'],['m','m']]});
 const unitDims=el('div',undefined,'r4-dimensions');unitForm.append(unitDims);
 for(const [key,label]of [['length','Largo *'],['width','Ancho *'],['height','Alto cargado *']])unitControls[key]=add(unitDims,label,'unit_'+key,key,s.unit,{type:'number'});
 unitControls.exteriorVolume=add(unitForm,'Volumen exterior cargado (m³) *','unit_volume','exteriorVolume',s.unit,{type:'number'});
 unitControls.tareKg=add(unitForm,'Tara del soporte (kg) *','unit_tare','tareKg',s.unit,{type:'number',help:'Peso del soporte vacío. Usá 0 sólo cuando corresponda.'});
 const unitVolume=el('output',undefined,'r4-calculated');unitVolume.dataset.cargoMetric='volume';unitForm.append(unitVolume);
 one.append(el('p','Dation calcula el volumen exterior de la unidad cargada. No certifica el acomodo físico de los bultos.','d-field__help'));
 const composition=el('div',undefined,'r4-physical-layout'),productForm=el('div',undefined,'r4-field-grid'),productSummary=el('aside',undefined,'guided-physical-summary');composition.append(productForm,productSummary);two.append(composition);
 productForm.append(el('h4','¿Qué contiene esta unidad logística?'));productForm.append(el('p','Describí el producto y el bulto que forma esta carga. Cada tipo contiene un único producto.','d-field__help'));
 productControls.name=add(productForm,'Nombre del producto *','product_name','name',s.form.values,{maxLength:120});
 const packages=[['caja','Caja'],['saco','Saco'],['bolsa','Bolsa'],['fardo','Fardo'],['bulto','Bulto'],['otra','Otra']];
 if(!packages.some(([id])=>id===s.form.values.packageType))packages.push([s.form.values.packageType,s.form.values.packageType]);
 productControls.packageType=add(productForm,'Tipo de bulto *','product_package','packageType',s.form.values,{options:packages});
 const productDims=el('div',undefined,'r4-dimensions');productForm.append(productDims);
 for(const [key,label]of [['length','Largo del bulto (cm) *'],['width','Ancho del bulto (cm) *'],['height','Alto del bulto (cm) *']])productControls[key]=add(productDims,label,'product_'+key,key,s.form.values,{type:'number'});
 const packageVolume=el('output',undefined,'r4-calculated');packageVolume.dataset.packageVolume='';productForm.append(packageVolume);
 productControls.massKg=add(productForm,'Peso bruto por bulto (kg) *','product_mass','massKg',s.form.values,{type:'number'});
 productControls.quantity=add(productForm,'Bultos por unidad logística *','product_quantity','quantity',s.form.values,{type:'number'});productControls.quantity.step='1';
 note(two,'Dation calcula el peso bruto total a partir de la cantidad de bultos, su peso y la tara de la unidad logística.');
 const feedback=el('p',undefined,'d-metadata');feedback.role='status';feedback.setAttribute('aria-live','polite');
 const actionRow=el('div',undefined,'r4-save-row'),save=button('Guardar tipo de carga',saveType,'primary');save.dataset.saveLoadType='';actionRow.append(feedback,save);two.append(actionRow);
 const history=el('section',undefined,'r4-history'),historyTitle=el('h4','Tipos de carga configurados'),cards=el('div',undefined,'r4-history-cards'),limit=el('p',undefined,'guided-note');history.append(historyTitle,cards);history.dataset.loadHistory='';two.append(history,limit);
 for(const n of [...Object.values(unitControls),...Object.values(productControls)])if(n.type==='number'){n.step=n.name==='product_quantity'?'1':'any';n.min=n.name==='unit_tare'?'0':'0.000001';}
 function notify(){one.dispatchEvent(new Event('change',{bubbles:true}));}
 function resetForm(){for(const [key,n]of Object.entries(productControls)){if(key==='packageType'&&![...n.options].some(o=>o.value===s.form.values[key])){const o=el('option',s.form.values[key]);o.value=s.form.values[key];n.append(o);}n.value=s.form.values[key];}showErrors=false;paint({});}
 function paint(errors){for(const n of [...Object.values(unitControls),...Object.values(productControls)]){const error=errors[n.name];if(error)n.setAttribute('aria-invalid','true');else n.removeAttribute('aria-invalid');n.closest('.d-field').querySelector('.d-field__error').textContent=error||'';}}
 function values(){for(const [key,n]of Object.entries(productControls))s.form.values[key]=n.value;}
 function stats(v){const quantity=Number(v.quantity),mass=Number(v.massKg),tare=Number(s.unit.tareKg);return v.quantity!==''&&v.massKg!==''&&s.unit.tareKg!==''&&quantity>0&&mass>0?{content:quantity*mass,gross:quantity*mass+tare}:null;}
 function summarize(){
  const u=s.unit,v=s.form.values,st=stats(v),unit=nameOf(u.type),vol=model.unitVolume();unitVolume.textContent='Volumen calculado: '+display(vol,'m³');packageVolume.textContent='Volumen por '+v.packageType+': '+display(volume(v),'m³',5);
  unitSummary.replaceChildren(el('h4','Resumen de la unidad'),supportArt(u.type));const dl=el('dl');unitSummary.append(dl);readout(dl,'Tipo',unit);readout(dl,'Dimensiones',vol===null?null:['BIG_BAG','OTHER'].includes(u.type)?display(vol,'m³'):[u.length,u.width,u.height].join(' × ')+' '+u.measure);readout(dl,'Tara',display(u.tareKg,'kg'));readout(dl,'Volumen',display(vol,'m³'));note(unitSummary,'En el siguiente paso vas a definir el contenido de esta unidad.');
  productSummary.replaceChildren(el('h4','Resumen de la composición'),supportArt(u.type,{loaded:true}));const pd=el('dl');productSummary.append(pd);readout(pd,'Producto',v.name||null);readout(pd,'Bulto',v.packageType);readout(pd,'Bultos por '+unit.toLowerCase(),display(v.quantity));readout(pd,'Peso por '+v.packageType,display(v.massKg,'kg'));readout(pd,'Peso del contenido',display(st?.content,'kg'));readout(pd,'Tara del '+unit.toLowerCase(),display(u.tareKg,'kg'));const total=readout(pd,'Peso bruto total',display(st?.gross,'kg'));total.dataset.cargoMetric='gross';readout(pd,'Volumen exterior',display(vol,'m³'));if(st)readout(pd,'Cálculo',display(v.quantity)+' × '+display(v.massKg,'kg')+' + '+display(u.tareKg,'kg')+' = '+display(st.gross,'kg'));
 }
 function renderHistory(){
  history.hidden=s.savedTypes.length===0;cards.replaceChildren();
  for(const [i,t]of s.savedTypes.entries()){
   const v=model.formFrom(t),st=stats(v),id=t.presentation.presentation_id,needsReview=s.review||s.form.target===t.presentation.presentation_id&&model.dirty(),card=button('',async()=>{
    if(locked||busy)return;if(model.dirty()&&!await confirmAction(one.closest('form'),scope,'Conservar o descartar cambios','Hay cambios sin guardar en el formulario. Podés cancelar para conservarlos o descartarlos para abrir el tipo seleccionado.','Descartar cambios'))return;
    model.select(id);resetForm();refresh();notify();productControls.name.focus();
   });card.disabled=locked;card.classList.add('r4-load-card');card.dataset.loadType=id;card.setAttribute('aria-pressed',String(s.form.target===id));
   card.append(supportArt(s.unit.type,{loaded:true}),el('strong','Tipo '+String(i+1).padStart(2,'0')+' · '+t.product.name),el('span',display(v.quantity)+' '+v.packageType+'s · '+display(st?.gross,'kg')+' · '+display(model.unitVolume(),'m³')),el('small',needsReview?'Revisar':'Guardado localmente'));
   const mark=el('span',undefined,'r4-load-status');statusCircle(mark,needsReview?'Requiere revisión':'Guardado localmente',needsReview?'pending':'complete');mark.classList.add('r4-load-status');card.append(mark);
   card.title=(locked?'Tipo de carga · ':'Revisar ')+t.product.name+' · '+(t.product.compatibility_groups||[]).join(', ');cards.append(card);
  }
 }
 function refresh(){
  const full=!s.form.target&&s.savedTypes.length>=2,irregular=['BIG_BAG','OTHER'].includes(s.unit.type);
  for(const [key,n]of Object.entries(unitControls)){n.disabled=locked;n.closest('.d-field').hidden=irregular?['length','width','height','measure'].includes(key):key==='exteriorVolume';}
  for(const n of type.root.querySelectorAll('input'))n.disabled=locked;
  for(const n of Object.values(productControls))n.disabled=locked||full;
  unitControls.measure.closest('.d-field').hidden=irregular;unitDims.hidden=irregular;
  save.textContent=s.form.target?'Actualizar tipo de carga':'Guardar tipo de carga';save.disabled=locked||busy||full||!!s.form.target&&!model.dirty()||!s.form.target&&s.savedTypes.length>0&&!model.dirty();save.setAttribute('aria-busy',String(busy));
  limit.hidden=!locked&&!full;limit.textContent=locked?'Configuración de solo lectura. Los tipos de carga se conservan sin cambios.':full?'Ya configuraste dos tipos de carga. Seleccioná una tarjeta inferior para revisar o actualizar uno.':'';
  for(const [key,label]of [['length','Largo'],['width','Ancho'],['height','Alto']])productControls[key].closest('.d-field').querySelector('label').textContent=label+' de '+s.form.values.packageType+' ('+s.form.values.unit+') *';
  if(showErrors)paint(model.formErrors());summarize();renderHistory();
 }
 function saveType(){
  if(locked||busy||save.disabled)return;values();busy=true;const result=model.save();busy=false;
  if(!result.ok){showErrors=true;paint(result.errors);feedback.className='d-field__error';feedback.role='alert';feedback.textContent='Revisá los campos del tipo de carga.';const invalid=one.closest('form').querySelector('[data-pro-step] [aria-invalid=true]');invalid?.focus();return;}
  feedback.className='d-metadata';feedback.role='status';feedback.textContent='Tipo de carga guardado localmente.';previewError=false;resetForm();refresh();notify();
 }
 for(const [key,n]of Object.entries(unitControls))scope.listen(n,'input',()=>{if(locked)return;model.setUnit(key,n.value);refresh();});
 for(const n of Object.values(productControls))scope.listen(n,'input',()=>{if(locked||n.disabled)return;values();refresh();});
 scope.listen(type.root,'input',e=>e.stopPropagation());scope.listen(type.root,'change',async e=>{
  e.stopPropagation();const next=type.value,previous=s.unit.type;type.value=previous;if(locked||next===previous)return;
  if((s.savedTypes.length||Object.values(s.unit).some((v)=>v!==''&&v!==s.unit.id&&v!==s.unit.type&&v!=='cm'))&&!await confirmAction(one.closest('form'),scope,'Cambiar unidad logística','Se conservarán los tipos y sus identificadores. Revisá la geometría exterior y confirmá nuevamente la carga.','Cambiar unidad'))return;
  const priorVolume=model.unitVolume();model.setUnit('type',next);if(['BIG_BAG','OTHER'].includes(next)&&!s.unit.exteriorVolume&&priorVolume!==null)model.setUnit('exteriorVolume',String(priorVolume));type.value=next;unitControls.exteriorVolume.value=s.unit.exteriorVolume;refresh();notify();
 });
 refresh();
 return {read:model.read,snapshot:model.read,ui:model.snapshot,validate:model.validate,hasData:()=>s.savedTypes.length>0,dirty:model.dirty,getProfile:()=>s.unit.type===originalType&&profile?profile:s.unit.type==='PALLET'?'PALLETIZED':'PACKAGED',setActive(){},refreshProfile(){},invalidate(){},showError(message){previewError=true;feedback.className='d-field__error';feedback.role='alert';feedback.textContent=message;},setCompiled(){if(previewError){feedback.className='d-metadata';feedback.role='status';feedback.textContent='Contrato físico vigente.';previewError=false;}s.review=false;refresh();},lock(){locked=true;refresh();},unitName:()=>nameOf(s.unit.type),bufferSignature:()=>model.dirty()?fingerprint(s.form):'',state:model};
}
