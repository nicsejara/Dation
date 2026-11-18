import {el,button,field} from './forms.mjs';

const TYPES=[['PALLET','Pallet'],['BOX','Caja'],['CRATE','Cajón'],['BIG_BAG','Big bag'],['OTHER','Otra unidad']];
const id=prefix=>prefix+'-'+crypto.randomUUID();
const present=value=>value!==''&&value!==undefined&&value!==null;
const copy=value=>structuredClone(value);
export const productDraft=()=>({product_id:id('P'),name:'',unit_label:'unidad',units_per_package:1,compatibility_groups:[]});

// Only values explicitly entered by the user become physical facts. A draft is
// allowed to be incomplete; the backend compiler is the publication authority.
export function mountCargoEditor(parent,scope,initial,{changed=()=>{}}={}){
 const state=copy(initial),host=el('div',undefined,'cargo-editor');host.dataset.dationTest='cargo-editor';parent.append(host);
 const products=el('div'),units=el('div'),presentations=el('div');let locked=false,active=true;const baseRestrictions=new Map();let restrictions=new Map();
 const refreshDisabled=()=>{for(const n of host.querySelectorAll('input,select,textarea,button')){const blocked=!!restrictions.get(n)?.();n.disabled=locked||!active||blocked;const reason=n.dataset.cargoDependencyReason;if(reason){const node=document.getElementById(reason);if(node)node.hidden=!blocked;}}};
 const notify=()=>{changed();host.dispatchEvent(new Event('change',{bubbles:true}));};
 const bind=(node,label,object,key,options={})=>{const input=field(node,label,{name:'cargo_'+key+'_'+id('f'),value:object[key]??'',...options});if(options.type==='number')input.step='any';scope.listen(input,'input',()=>{object[key]=input.value;});scope.listen(input,'change',()=>{object[key]=input.value;});return input;};
 const physical=(node,title,object,key,fields,unitOptions)=>{
  const group=el('details',undefined,'cargo-advanced');group.append(el('summary',title));const grid=el('div',undefined,'ultimate-grid');group.append(grid);node.append(group);
  const value=copy(object[key]||{});object[key]=value;
  for(const [prop,label]of fields)bind(grid,label,value,prop,{type:'number'}).min='0';
  bind(grid,'Unidad',value,'unit',{options:unitOptions,value:value.unit||unitOptions[0][0]});value.unit||=unitOptions[0][0];
 };
 const mass=(node,object,key,title)=>physical(node,title,object,key,[['value','Valor']], [['kg','kg'],['t','t']]);
 const volume=(node,object)=>physical(node,'Volumen exterior declarado',object,'external_volume',[['value','Valor']],[['m3','m³'],['l','litros']]);
 const dimensions=(node,object,key,title)=>physical(node,title,object,key,[['length','Largo'],['width','Ancho'],['height','Alto']],[['cm','cm'],['m','m']]);
 const entry=(container,title,remove,blocked)=>{
  const card=el('section',undefined,'cargo-entry'),header=el('header'),body=el('div',undefined,'ultimate-grid');header.append(el('h4',title));
  const del=button('Eliminar',remove);restrictions.set(del,()=>typeof blocked==='function'?blocked():!!blocked);if(blocked){const reason=el('p','Reasigná sus referencias antes de eliminarlo.','d-field__help');reason.id=id('dependency');del.dataset.cargoDependencyReason=reason.id;del.setAttribute('aria-describedby',reason.id);card.append(reason);}header.append(del);card.append(header,body);container.append(card);return body;
 };
 function render(){
  restrictions=new Map(baseRestrictions);products.replaceChildren();units.replaceChildren();presentations.replaceChildren();
  for(const [index,p]of state.products.entries()){
   const body=entry(products,'Producto '+(index+1),()=>{state.products=state.products.filter(x=>x!==p);render();notify();products.nextElementSibling?.focus();},()=>state.presentations.some(a=>a.components.some(c=>c.product_id===p.product_id)));
   bind(body,'Nombre del producto *',p,'name',{required:true,maxLength:120});bind(body,'Código (opcional)',p,'code');bind(body,'Categoría descriptiva (opcional)',p,'category');
   bind(body,'Unidad del producto *',p,'unit_label',{required:true});bind(body,'Unidades por bulto *',p,'units_per_package',{type:'number',required:true}).min='1';
   const tags=bind(body,'Categorías de compatibilidad (separadas por coma)',p,'_tags',{value:(p.compatibility_groups||[]).join(', ')});scope.listen(tags,'input',()=>{p.compatibility_groups=tags.value.split(',').map(v=>v.trim()).filter(Boolean);});
   mass(body,p,'gross_mass','Peso bruto por bulto (opcional)');mass(body,p,'net_mass','Peso neto por bulto (informativo)');dimensions(body,p,'dimensions','Dimensiones del producto (informativas)');bind(body,'Densidad explícita (kg/m³, opcional)',p,'density_kg_per_m3',{type:'number'}).min='0';
  }
  for(const [index,u]of state.logistic_units.entries()){
   const body=entry(units,'Unidad logística compartida '+(index+1),()=>{state.logistic_units=state.logistic_units.filter(x=>x!==u);render();notify();units.nextElementSibling?.focus();},()=>state.presentations.some(p=>p.logistic_unit_id===u.logistic_unit_id));
   bind(body,'Nombre de la unidad *',u,'label',{required:true});bind(body,'Tipo',u,'type',{options:TYPES});dimensions(body,u,'empty_dimensions','Dimensiones vacías (no reemplazan el exterior cargado)');mass(body,u,'tare_mass','Tara explícita');bind(body,'Límite estructural declarado (kg, opcional)',u,'structural_limit_kg',{type:'number'}).min='0';
  }
  for(const [index,p]of state.presentations.entries()){
   const body=entry(presentations,'Presentación '+(index+1),()=>{state.presentations=state.presentations.filter(x=>x!==p);render();notify();presentations.nextElementSibling?.focus();});
   bind(body,'Nombre de la presentación *',p,'label',{required:true});
   const kind=bind(body,'Naturaleza de la cantidad',p,'quantity_kind',{options:[['DISCRETE','Unidad logística completa'],['CONTINUOUS','Granel divisible']]});
   const unit=bind(body,'Unidad de cantidad',p,'quantity_unit',{options:p.quantity_kind==='CONTINUOUS'?[['kg','kg'],['t','t'],['m3','m³'],['l','litros']]:[['presentation','Presentación completa']]});
   const shared=bind(body,'Unidad logística compartida',p,'logistic_unit_id',{options:[['','Sin unidad logística'],...state.logistic_units.map(u=>[u.logistic_unit_id,u.label||'Unidad sin nombre'])]});
   shared.closest('.d-field').hidden=p.quantity_kind==='CONTINUOUS';
   scope.listen(kind,'change',()=>{p.quantity_kind=kind.value;p.quantity_unit=kind.value==='CONTINUOUS'?'kg':'presentation';if(kind.value==='CONTINUOUS'){delete p.logistic_unit_id;p.components=p.components.slice(0,1);if(p.components[0])p.components[0].quantity='1';}render();notify();});
   const composition=el('div',undefined,'cargo-composition');composition.append(el('h5','Composición de la presentación'));body.append(composition);
   for(const component of p.components){
    const row=el('div',undefined,'ultimate-grid');composition.append(row);
    bind(row,'Producto *',component,'product_id',{options:[['','Elegí un producto'],...state.products.map(q=>[q.product_id,q.name||'Producto sin nombre'])],required:true});
    bind(row,p.quantity_kind==='CONTINUOUS'?'Factor de material (1)':'Bultos por presentación *',component,'quantity',{type:'number',required:true,readOnly:p.quantity_kind==='CONTINUOUS'}).min=p.quantity_kind==='CONTINUOUS'?'1':'1';
    const remove=button('Quitar componente',()=>{p.components=p.components.filter(x=>x!==component);render();notify();});restrictions.set(remove,()=>p.components.length<2);row.append(remove);
   }
   if(p.quantity_kind!=='CONTINUOUS'){const add=button('Agregar componente para presentación mixta',()=>{if(p.components.length>=30)return;p.components.push({product_id:'',quantity:'1'});render();notify();presentations.querySelectorAll('.cargo-entry')[index]?.querySelector('.cargo-composition>.ultimate-grid:last-of-type select')?.focus();});restrictions.set(add,()=>p.components.length>=30);add.title='Hasta 30 componentes por presentación';composition.append(add);}
   dimensions(body,p,'loaded_dimensions','Dimensiones exteriores cargadas');mass(body,p,'gross_mass','Peso bruto cargado declarado (opcional si se deriva)');volume(body,p);bind(body,'Densidad explícita (kg/m³, opcional)',p,'density_kg_per_m3',{type:'number'}).min='0';mass(body,p,'extra_tare_mass','Tara adicional explícita');
   const info=el('details',undefined,'cargo-advanced');info.append(el('summary','Metadatos físicos informativos'));const infoBody=el('div',undefined,'ultimate-grid');info.append(infoBody);body.append(info);
   bind(infoBody,'Orientación informativa (opcional)',p,'orientation_metadata');const stacking=bind(infoBody,'Apilable (informativo)',p,'_stackable',{options:[['','Sin declarar'],['yes','Sí'],['no','No']],value:p.stackable_metadata===undefined||p.stackable_metadata===null?'':p.stackable_metadata?'yes':'no'});scope.listen(stacking,'change',()=>{p.stackable_metadata=stacking.value===''?null:stacking.value==='yes';});
   body.append(el('p','El volumen exterior es una capacidad escalar. No certifica encaje 3D, apilado, temperatura, ejes ni mercancías peligrosas.','d-field__help'));
  }
  refreshDisabled();
 }
 function group(title,container,caption,add,limit,count){const section=el('section',undefined,'cargo-group');section.append(el('h3',title),container);const control=button(caption,()=>{if(count()>=limit)return;add();render();notify();container.lastElementChild?.querySelector('input,select')?.focus();});control.title='Hasta '+limit+' elementos';baseRestrictions.set(control,()=>count()>=limit);restrictions.set(control,()=>count()>=limit);section.append(control);host.append(section);return control;}
 group('Productos',products,'Agregar otro producto',()=>state.products.push(productDraft()),100,()=>state.products.length);
 group('Unidades logísticas compartidas',units,'Agregar unidad logística',()=>state.logistic_units.push({logistic_unit_id:id('U'),label:'',type:'PALLET',tare_mass:{value:'0',unit:'kg'}}),50,()=>state.logistic_units.length);
 group('Presentaciones físicas',presentations,'Agregar presentación',()=>state.presentations.push({presentation_id:id('L'),label:'',quantity_kind:'DISCRETE',quantity_unit:'presentation',components:[{product_id:state.products[0]?.product_id||'',quantity:'1'}]}),200,()=>state.presentations.length);
 const cleanPhysical=(out,key)=>{const v=out[key];if(!v)return;if(!Object.entries(v).some(([k,x])=>k!=='unit'&&present(x)))delete out[key];};
 function read(){
  const result={products:[],logistic_units:[],presentations:[]};
  for(const p of state.products){const v=copy(p);delete v._tags;v.units_per_package=Number(v.units_per_package);for(const key of ['code','category','density_kg_per_m3'])if(!present(v[key]))delete v[key];for(const key of ['gross_mass','net_mass','dimensions'])cleanPhysical(v,key);result.products.push(v);}
  for(const u of state.logistic_units){const v=copy(u);for(const key of ['empty_dimensions','tare_mass'])cleanPhysical(v,key);if(!present(v.structural_limit_kg))delete v.structural_limit_kg;result.logistic_units.push(v);}
  for(const p of state.presentations){const v=copy(p);delete v._stackable;for(const key of ['logistic_unit_id','density_kg_per_m3','orientation_metadata'])if(!present(v[key]))delete v[key];for(const key of ['loaded_dimensions','gross_mass','external_volume','extra_tare_mass'])cleanPhysical(v,key);result.presentations.push(v);}
  return result;
 }
 scope.listen(host,'input',refreshDisabled);scope.listen(host,'change',refreshDisabled);
 render();return {read,setActive(value){active=value;refreshDisabled();},lock(){locked=true;refreshDisabled();},seed(){if(!state.products.length){state.products.push(productDraft());render();}}};
}
