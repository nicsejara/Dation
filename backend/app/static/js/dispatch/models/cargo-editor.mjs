import {el,button,field,confirmAction} from './forms.mjs';
import {wizardIcon} from './wizard-ui.mjs';
import {note,readout,palletArt,display} from './guided-ui.mjs';

const TYPES=[['PALLET','Pallet'],['BOX','Caja'],['CRATE','Cajón'],['BIG_BAG','Big bag'],['OTHER','Otra unidad']];
const id=p=>p+'-'+crypto.randomUUID(),copy=v=>structuredClone(v);
const present=v=>v!==''&&v!==undefined&&v!==null;
const number=v=>present(v)&&Number.isFinite(Number(v))?Number(v):null;
const kg=v=>number(v?.value)===null?null:number(v.value)*(v.unit==='t'?1000:1);
const origin=(physics,dimension)=>{
 const source=physics?.provenance?.sources?.[dimension];
 if(!source)return 'Vista preliminar · pendiente de validación';
 return (source.startsWith('DECLARED_')?'Declarado':source==='EXPLICIT_QUANTITY_UNIT'?'Unidad física declarada':'Calculado')+' · validado por Dation';
};
export const productDraft=()=>({product_id:id('P'),name:'',unit_label:'unidad',units_per_package:1,compatibility_groups:[]});

// A single catalog; navigation and incomplete physical fields stay in UI draft.
export function mountCargoEditor(places,scope,initial,{profile=()=> 'PALLETIZED',categorized=()=>false,ui={},onNavigate=()=>{}}={}){
 const state=copy(initial),view={unit:ui.unit||state.logistic_units[0]?.logistic_unit_id,presentation:ui.presentation||state.presentations[0]?.presentation_id,product:ui.product||'',query:'',category:''};
 const roots={},contents={},restrictions=new Map();let active=true,locked=false,compiled=null,serverError='',projections=[];
 for(const key of ['units','products','presentations']){
  const root=el('section',undefined,'cargo-editor cargo-group');root.dataset.cargoGroup=key;places[key].append(root);roots[key]=root;
  contents[key]=el('div');root.append(contents[key]);
 }
 function refreshDisabled(){for(const root of Object.values(roots))for(const n of root.querySelectorAll('input,select,textarea,button'))n.disabled=!!((!active||locked)&&!n.dataset.guidedUi||restrictions.get(n)?.());}
 function uiControl(n){n.dataset.guidedUi='true';scope.listen(n,'input',e=>e.stopPropagation());scope.listen(n,'change',e=>e.stopPropagation());return n;}
 function notify(){compiled=null;updateViews();roots.products.dispatchEvent(new Event('change',{bubbles:true}));}
 function bind(parent,label,obj,key,options={},parse=v=>v){
  const n=field(parent,label,{name:'cargo_'+key+'_'+id('f'),value:obj[key]??'',...options});
  if(options.type==='number'){n.min='0';n.step='any';}
  if(key==='product_id'||key==='logistic_unit_id')n.dataset.catalogPicker=key==='product_id'?'products':'logistic_units';
  const edit=()=>{obj[key]=parse(n.value);compiled=null;updateViews();};scope.listen(n,'input',edit);scope.listen(n,'change',edit);return n;
 }
 function advanced(parent,title){const d=el('details',undefined,'cargo-advanced');d.dataset.editorDisclosure=title;d.append(el('summary',title));const body=el('div',undefined,'ultimate-grid');d.append(body);parent.append(d);return body;}
 function physical(parent,title,obj,key,props,units,{expanded=false,required=false}={}){
  let body;if(expanded){const box=el('fieldset',undefined,'guided-physical');box.append(el('legend',title,'d-field__label'));body=el('div',undefined,'ultimate-grid');box.append(body);parent.append(box);}else body=advanced(parent,title);
  const value=obj[key]||(obj[key]={unit:units[0][0]});
  for(const [prop,label]of props)bind(body,label,value,prop,{type:'number',required,help:props.length===3?'Los tres ejes completos o ninguno.':''});
  bind(body,'Unidad',value,'unit',{options:units,value:value.unit||units[0][0]});value.unit||=units[0][0];return body;
 }
 const mass=(parent,obj,key,title,opts)=>physical(parent,title,obj,key,[['value','Valor']],[['kg','kg'],['t','t']],opts);
 const dimensions=(parent,obj,key,title)=>physical(parent,title,obj,key,[['length','Largo'],['width','Ancho'],['height','Alto']],[['cm','cm'],['m','m']]);
 function action(text,run,{icon,blocked,reason,uiOnly=false}={}){
  const b=button('',event=>{if((locked||!active)&&!uiOnly||blocked?.())return;run(event);});if(icon)b.append(wizardIcon(icon));b.append(el('span',text));
  if(blocked)restrictions.set(b,blocked);if(reason){b.title=reason;b.setAttribute('aria-label',text+'. '+reason);}if(uiOnly)uiControl(b);return b;
 }
 function focusNew(kind){roots[kind].querySelector('.guided-product-editor:not([hidden]) input,.guided-unit-fields input,.guided-presentation input')?.focus();}
 function addControl(parent,text,run,limit,count){
  const key=parent.closest('[data-cargo-group]')?.dataset.cargoGroup;
  const b=action(text,()=>{if(count()>=limit)return;run();render();notify();if(key)focusNew(key);},{icon:'plus',blocked:()=>count()>=limit});b.title='Máximo '+limit;parent.append(b);return b;
 }
 function unique(value,items,key){
  const base=(value||'Sin nombre').slice(0,102);let result=base+' · copia',n=2;
  while(items.some(x=>String(x[key]||'').toLocaleLowerCase()===result.toLocaleLowerCase()))result=base+' · copia '+n++;return result;
 }
 async function remove(kind,item){
  if(locked||!active)return;
  if(await confirmAction(roots[kind].closest('form'),scope,'Eliminar del borrador','Se eliminará este elemento no referenciado. Las versiones publicadas no cambian.','Eliminar')){
   const key=kind==='units'?'logistic_units':kind;state[key]=state[key].filter(v=>v!==item);
   if(kind==='units')view.unit=state.logistic_units[0]?.logistic_unit_id;
   if(kind==='presentations')view.presentation=state.presentations[0]?.presentation_id;
   render();notify();roots[kind].querySelector('button:not(:disabled)')?.focus();
  }
 }
 function picker(parent,label,options,value,select,kind){
  const n=uiControl(field(parent,label,{name:'view_'+id('select'),options,value}));if(kind)n.dataset.catalogPicker=kind;
  scope.listen(n,'change',()=>{select(n.value);render();});return n;
 }
 function createPresentation(unit=null){
  const bulk=['DRY_BULK','LIQUID_BULK'].includes(profile()),p={presentation_id:id('L'),label:'',quantity_kind:bulk?'CONTINUOUS':'DISCRETE',quantity_unit:bulk?'kg':'presentation',components:[{product_id:'',quantity:'1'}]};
  if(unit&&!bulk)p.logistic_unit_id=unit.logistic_unit_id;state.presentations.push(p);view.presentation=p.presentation_id;return p;
 }
 function loadedFields(parent,p){
  dimensions(parent,p,'loaded_dimensions','Dimensiones exteriores cargadas');
  mass(parent,p,'gross_mass','Peso bruto cargado declarado (opcional si se deriva)');
  physical(parent,'Volumen exterior declarado',p,'external_volume',[['value','Valor']],[['m3','m³'],['l','litros']]);
  bind(parent,'Densidad explícita (kg/m³, opcional)',p,'density_kg_per_m3',{type:'number'});mass(parent,p,'extra_tare_mass','Tara adicional explícita');
 }
 function composition(p){
  const lines=p.components.map(c=>({c,product:state.products.find(v=>v.product_id===c.product_id)})),known=!!lines.length&&lines.every(v=>v.product&&number(v.c.quantity)>0);
  const labels=new Set(lines.map(v=>v.product?String(v.product.unit_label).trim().toLocaleLowerCase()+'|'+v.product.units_per_package:'?'));
  return {lines,comparable:known&&labels.size===1,quantity:known?lines.reduce((n,v)=>n+Number(v.c.quantity),0):null,mass:known&&lines.every(v=>kg(v.product.gross_mass)!==null)?lines.reduce((n,v)=>n+Number(v.c.quantity)*kg(v.product.gross_mass),0):null};
 }
 function summary(parent,p,unit,{support=false}={}){
  const panel=el('aside',undefined,'guided-physical-summary'),list=el('dl'),error=el('p',undefined,'d-field__error'),linked=unit||state.logistic_units.find(u=>u.logistic_unit_id===p?.logistic_unit_id);
  const art=p?.quantity_kind==='CONTINUOUS'?wizardIcon(profile()==='LIQUID_BULK'?'drop':'mound'):linked?.type==='PALLET'?palletArt():wizardIcon('box');
  error.role='alert';panel.append(el('h4',support?'Resumen de la unidad':profile()==='PALLETIZED'?'Resumen del pallet':'Resumen de la presentación'),art,list,error);parent.append(panel);
  projections.push(()=>{
   list.replaceChildren();error.textContent=serverError;const u=unit||state.logistic_units.find(u=>u.logistic_unit_id===p?.logistic_unit_id),physics=p&&compiled?.[p.presentation_id],stats=p&&composition(p);
   if(p?.quantity_kind==='CONTINUOUS'){
    readout(list,'Presentación',p.label||'Pendiente');readout(list,'Material',state.products.find(q=>q.product_id===p.components[0]?.product_id)?.name||'Pendiente');
    readout(list,'Cantidad física por unidad','1 '+p.quantity_unit,'Declarado, sin soporte anidado');
    readout(list,'Peso por unidad',physics?.coefficients?.weight_kg!=null?display(physics.coefficients.weight_kg,'kg'):'Pendiente de validación',origin(physics,'weight_kg'));
    readout(list,'Volumen por unidad',physics?.coefficients?.volume_m3!=null?display(physics.coefficients.volume_m3,'m³',6):'Pendiente de validación',origin(physics,'volume_m3'));
    if(physics)readout(list,'Incremento de asignación',physics.allocation_increment+' '+physics.quantity_unit,'Validado por Dation');
    return;
   }
   readout(list,'Soporte',u?.label||'Sin declarar');
   const empty=u?.empty_dimensions;if(support)readout(list,'Dimensiones del soporte vacío',empty&&['length','width','height'].every(k=>present(empty[k]))?[empty.length,empty.width,empty.height].join(' × ')+' '+empty.unit:'Sin declarar','Distintas del exterior cargado');
   readout(list,'Tara del soporte',display(kg(u?.tare_mass),'kg'),'Declarado');readout(list,'Límite estructural',display(u?.structural_limit_kg,'kg'),'No es capacidad del vehículo');
   if(!p){readout(list,'Composición','Todavía no se definieron productos ni composición.');return;}
   readout(list,'Presentación',p.label||'Pendiente');const d=p.loaded_dimensions;
   readout(list,'Exterior cargado',d&&['length','width','height'].every(k=>present(d[k]))?[d.length,d.width,d.height].join(' × ')+' '+d.unit:'Sin declarar');
   const localVolume=d&&['length','width','height'].every(k=>number(d[k])>0)?Number(d.length)*Number(d.width)*Number(d.height)/(d.unit==='cm'?1e6:1):null;
   const declaredVolume=number(p.external_volume?.value)===null?null:number(p.external_volume.value)/(p.external_volume.unit==='l'?1000:1),volume=physics?.coefficients?.volume_m3??localVolume??declaredVolume;
   readout(list,'Volumen exterior cargado',present(volume)?display(volume,'m³',6):'Pendiente',physics?.coefficients?.volume_m3!=null?origin(physics,'volume_m3'):localVolume!==null?'Calculado · vista preliminar':declaredVolume!==null?'Declarado · vista preliminar':'Faltan dimensiones exteriores completas');
   readout(list,'Productos',String(p.components.filter(c=>state.products.some(q=>q.product_id===c.product_id)).length));
   readout(list,'Cantidad de bultos',stats.comparable?display(stats.quantity):'No comparable','Por cantidad, no ocupación');
   readout(list,'Peso bruto de componentes',stats.mass!==null?display(stats.mass,'kg'):'Peso pendiente de declarar',physics?'Composición declarada':'Vista preliminar');
   const tare=kg(u?.tare_mass),extra=kg(p.extra_tare_mass)??0,derived=stats.mass!==null&&(!u||tare!==null)?stats.mass+(tare??0)+extra:null,total=physics?.coefficients?.weight_kg??derived;
   const gross=readout(list,'Peso bruto total',total!==null?display(total,'kg'):present(p.gross_mass?.value)?display(kg(p.gross_mass),'kg'):'Pendiente',origin(physics,'weight_kg'));gross.dataset.cargoMetric='gross';
   if(present(p.gross_mass?.value))readout(list,'Peso bruto declarado',display(kg(p.gross_mass),'kg'),'Declarado; debe ser coherente con componentes y tara');
   readout(list,'Tara adicional',display(extra,'kg'),'Si existe, se suma una sola vez');
   if(physics)readout(list,'Incremento de asignación',physics.allocation_increment+' '+physics.quantity_unit,'Validado por Dation');
  });
  note(panel,'Ilustración orientativa. El volumen es exterior y escalar: no certifica packing3D ni apilado.');
 }
 function renderUnits(){
  const root=contents.units;root.replaceChildren();const top=el('div',undefined,'guided-toolbar');root.append(top);
  const bulk=['DRY_BULK','LIQUID_BULK'].includes(profile());if(bulk)note(root,'Granel: un material por presentación continua en kg, t, m³ o litros. No requiere pallet; no se borran soportes anteriores.');
  picker(top,'Soporte activo',[['','Seleccioná un soporte'],...state.logistic_units.map(u=>[u.logistic_unit_id,u.label||'Unidad sin nombre'])],view.unit||'',v=>{view.unit=v;},'logistic_units');
  addControl(top,'Agregar unidad logística',()=>{const u={logistic_unit_id:id('U'),label:'',type:bulk?'OTHER':profile()==='PACKAGED'?'BOX':'PALLET',tare_mass:{value:'',unit:'kg'}};state.logistic_units.push(u);view.unit=u.logistic_unit_id;},50,()=>state.logistic_units.length);
  const u=state.logistic_units.find(v=>v.logistic_unit_id===view.unit);if(!u){note(root,'Todavía no hay soporte seleccionado. Agregá uno si tu carga lo utiliza.');return;}
  const layout=el('div',undefined,'guided-split'),body=el('section',undefined,'cargo-entry guided-unit-fields');layout.append(body);root.append(layout);
  body.append(el('h4','A. Soporte logístico'));const actions=el('div',undefined,'guided-actions'),refs=()=>state.presentations.filter(p=>p.logistic_unit_id===u.logistic_unit_id);body.append(actions);
  actions.append(action('Duplicar unidad',()=>{const v=copy(u);v.logistic_unit_id=id('U');v.label=unique(u.label,state.logistic_units,'label');state.logistic_units.push(v);view.unit=v.logistic_unit_id;render();notify();},{icon:'copy',blocked:()=>state.logistic_units.length>=50}),action('Eliminar unidad',()=>remove('units',u),{icon:'trash',blocked:()=>refs().length>0,reason:refs().length?'La usan: '+refs().map(p=>p.label||'Presentación sin nombre').join(', '):''}));
  if(refs().length)note(body,'Soporte compartido por '+refs().length+' presentación(es). Reasignalas antes de eliminarlo.');
  const grid=el('div',undefined,'ultimate-grid');body.append(grid);bind(grid,'Nombre de la unidad *',u,'label',{required:true,maxLength:120});bind(grid,'Tipo',u,'type',{options:TYPES});
  dimensions(grid,u,'empty_dimensions','Dimensiones del soporte vacío');mass(grid,u,'tare_mass','Tara explícita',{expanded:true,required:true});bind(grid,'Límite estructural declarado (kg, opcional)',u,'structural_limit_kg',{type:'number'});
  body.append(el('h4','B. Presentación cargada'));const associated=state.presentations.filter(p=>p.logistic_unit_id===u.logistic_unit_id),p=associated.find(p=>p.presentation_id===view.presentation);
  picker(body,'Presentación cargada a editar',[['','Seleccioná una presentación'],...associated.map(p=>[p.presentation_id,p.label||'Presentación sin nombre'])],p?.presentation_id||'',v=>{view.presentation=v;},'presentations');
  if(p){const loaded=el('div',undefined,'ultimate-grid');body.append(loaded);loadedFields(loaded,p);}else note(body,'Seleccioná una presentación o prepará un borrador. Sus medidas cargadas no se guardan dentro del soporte vacío.');
  if(!bulk)addControl(body,'Preparar presentación con este soporte',()=>createPresentation(u),200,()=>state.presentations.length);
  note(body,'Si declarás medidas del soporte vacío, completá largo, ancho y alto. La altura cargada se declara por separado.');summary(layout,p,u,{support:true});
 }
 function renderProducts(){
  const root=contents.products;root.replaceChildren();const toolbar=el('div',undefined,'guided-toolbar');root.append(toolbar);
  const search=uiControl(field(toolbar,'Buscar entre los productos de este modelo',{name:'cargo_search',type:'search',value:view.query}));search.placeholder='Buscar producto...';
  const categories=[...new Set(state.products.map(p=>p.category?.trim()).filter(Boolean))].sort();
  const filter=uiControl(field(toolbar,'Filtrar productos',{name:'cargo_filter',options:[['','Todos los productos'],...categories.map(v=>[v,v])],value:view.category}));
  addControl(toolbar,'Agregar producto',()=>{const p=productDraft();state.products.push(p);view.product=p.product_id;},100,()=>state.products.length);
  const list=el('div',undefined,'guided-product-list'),cards=[];root.append(list);if(!state.products.length)note(root,'Todavía no agregaste productos. Agregá el primero para construir una presentación.');
  for(const p of state.products){
   const card=el('section',undefined,'cargo-entry guided-product-row');card.dataset.productId=p.product_id;const header=el('header'),text=el('div',undefined,'guided-product-copy'),name=el('strong'),code=el('span',undefined,'guided-code'),meta=el('span',undefined,'guided-description'),actions=el('div',undefined,'guided-actions'),body=el('div',undefined,'ultimate-grid guided-product-editor');body.hidden=view.product!==p.product_id;
   text.append(name,code,meta);const refs=()=>state.presentations.filter(a=>a.components.some(c=>c.product_id===p.product_id));
   const edit=action('Editar '+(p.name||'producto nuevo'),()=>{view.product=body.hidden?p.product_id:'';for(const c of cards)c.body.hidden=c.p.product_id!==view.product;if(!body.hidden)body.querySelector('input')?.focus();},{icon:'edit',uiOnly:true});edit.dataset.productEdit='true';
   actions.append(edit,action('Duplicar '+(p.name||'producto'),()=>{const v=copy(p);v.product_id=id('P');v.name=unique(p.name,state.products,'name');if(p.code){let n=1;do{v.code=p.code.slice(0,105)+'-COPIA-'+n++;}while(state.products.some(q=>String(q.code||'').toLocaleLowerCase()===v.code.toLocaleLowerCase()));}state.products.push(v);view.product=v.product_id;render();notify();focusNew('products');},{icon:'copy',blocked:()=>state.products.length>=100}),action('Eliminar '+(p.name||'producto'),()=>remove('products',p),{icon:'trash',blocked:()=>refs().length>0,reason:refs().length?'Lo usan: '+refs().map(v=>v.label||'Presentación sin nombre').join(', '):''}));
   const dependency=el('small',undefined,'d-field__help');dependency.id=id('dependency');text.append(dependency);actions.children[2].setAttribute('aria-describedby',dependency.id);
   header.append(wizardIcon('box'),text,actions);card.append(header,body);list.append(card);cards.push({card,body,p});
   if(refs().length)note(body,'Producto referenciado: reasigná o quitá sus componentes antes de eliminarlo.');
   bind(body,'Nombre del producto *',p,'name',{required:true,maxLength:120});bind(body,'Código (opcional)',p,'code',{maxLength:128});bind(body,'Unidad del producto *',p,'unit_label',{required:true,maxLength:40,help:'Unidad comercial que cuenta la dimensión Unidades, por ejemplo sobre. El peso se declara por bulto transportado.'});
   const count=bind(body,'Unidades por bulto *',p,'units_per_package',{type:'number',required:true});count.min='1';count.max='1000000';count.step='1';mass(body,p,'gross_mass','Peso bruto por bulto (opcional)',{expanded:true});
   const more=advanced(body,'Datos avanzados del producto');bind(more,'Categoría descriptiva (opcional)',p,'category',{maxLength:120});
   const tags=field(categorized()?body:more,'Categorías de compatibilidad (separadas por coma)',{name:'cargo_groups_'+id('f'),value:(p.compatibility_groups||[]).join(', '),help:'Requeridas con compatibilidad por categorías. Uniformidad es una decisión de negocio.'});scope.listen(tags,'input',()=>{p.compatibility_groups=tags.value.split(',').map(s=>s.trim()).filter(Boolean);compiled=null;updateViews();});
   mass(more,p,'net_mass','Peso neto por bulto (informativo)');dimensions(more,p,'dimensions','Dimensiones del producto (informativas)');bind(more,'Densidad explícita (kg/m³, opcional)',p,'density_kg_per_m3',{type:'number'});
   projections.push(()=>{name.textContent=p.name||'Producto sin nombre';code.textContent=p.code||'Sin código';meta.textContent=display(p.units_per_package)+' '+(p.unit_label||'unidades')+' por bulto · Peso bruto: '+display(kg(p.gross_mass),'kg');edit.setAttribute('aria-label','Editar '+(p.name||'producto nuevo'));actions.children[1].setAttribute('aria-label','Duplicar '+(p.name||'producto nuevo'));dependency.hidden=!refs().length;dependency.textContent=refs().length?'Referenciado: reasigná antes de eliminar.':'';dependency.title=refs().map(q=>q.label||'Presentación sin nombre').join(', ');actions.children[2].setAttribute('aria-label','Eliminar '+(p.name||'producto nuevo')+(refs().length?'. Lo usan: '+refs().map(q=>q.label||'Presentación sin nombre').join(', '):''));});
  }
  const applyFilter=()=>{for(const {card,p}of cards)card.hidden=![p.name,p.code,p.category].join(' ').toLocaleLowerCase().includes(view.query.toLocaleLowerCase())||!!view.category&&p.category!==view.category;};
  scope.listen(search,'input',()=>{view.query=search.value;applyFilter();});scope.listen(filter,'change',()=>{view.category=filter.value;applyFilter();});applyFilter();
  let filterKey=JSON.stringify(categories);projections.push(()=>{
   const values=[...new Set(state.products.map(p=>p.category?.trim()).filter(Boolean))].sort(),key=JSON.stringify(values);
   if(key!==filterKey){filterKey=key;if(!values.includes(view.category))view.category='';filter.replaceChildren(...[['','Todos los productos'],...values.map(v=>[v,v])].map(([value,label])=>{const option=el('option',label);option.value=value;return option;}));filter.value=view.category;}applyFilter();
  });
  note(root,'Un bulto puede contener varias unidades comerciales. Esa equivalencia no crea embalajes recursivos ni certifica un volumen compartido.');
 }
 function renderPresentations(){
  const root=contents.presentations;root.replaceChildren();const toolbar=el('div',undefined,'guided-toolbar');root.append(toolbar);
  picker(toolbar,'Presentación activa',[['','Seleccioná una presentación'],...state.presentations.map(p=>[p.presentation_id,p.label||'Presentación sin nombre'])],view.presentation||'',v=>{view.presentation=v;const p=state.presentations.find(p=>p.presentation_id===v);if(p?.logistic_unit_id)view.unit=p.logistic_unit_id;},'presentations');
  addControl(toolbar,'Agregar presentación',()=>createPresentation(),200,()=>state.presentations.length);
  const p=state.presentations.find(p=>p.presentation_id===view.presentation);if(!p){note(root,'Todavía no definiste presentaciones de carga. Registrá productos reales y agregá una presentación.');return;}
  const layout=el('div',undefined,'guided-split'),body=el('section',undefined,'cargo-entry guided-presentation');body.dataset.presentationId=p.presentation_id;layout.append(body);root.append(layout);
  body.append(el('h4',profile()==='PALLETIZED'?'Composición del pallet':'Presentación de carga'));const actions=el('div',undefined,'guided-actions');body.append(actions);
  actions.append(action('Duplicar presentación',()=>{const v=copy(p);v.presentation_id=id('L');v.label=unique(p.label,state.presentations,'label');state.presentations.push(v);view.presentation=v.presentation_id;render();notify();},{icon:'copy',blocked:()=>state.presentations.length>=200}),action('Eliminar presentación',()=>remove('presentations',p),{icon:'trash'}));
  const grid=el('div',undefined,'ultimate-grid');body.append(grid);bind(grid,'Nombre de la presentación *',p,'label',{required:true,maxLength:120});
  const kind=field(grid,'Naturaleza de la cantidad',{name:'cargo_kind_'+id('f'),options:[['DISCRETE','Unidad logística completa'],['CONTINUOUS','Granel divisible']],value:p.quantity_kind});scope.listen(kind,'input',e=>e.stopPropagation());
  scope.listen(kind,'change',async e=>{
   e.stopPropagation();const next=kind.value;kind.value=p.quantity_kind;
   if(next==='CONTINUOUS'&&(p.components.length>1||p.logistic_unit_id)&&!await confirmAction(root.closest('form'),scope,'Convertir presentación a granel','El granel usa un solo material y no asocia soporte. Se quitarán esos vínculos de este borrador.','Convertir'))return;
   p.quantity_kind=next;p.quantity_unit=next==='CONTINUOUS'?'kg':'presentation';
   if(next==='CONTINUOUS'){delete p.logistic_unit_id;p.components=p.components.slice(0,1);if(p.components[0])p.components[0].quantity='1';}render();notify();
  });
  bind(grid,'Unidad de cantidad',p,'quantity_unit',{options:p.quantity_kind==='CONTINUOUS'?[['kg','kg'],['t','t'],['m3','m³'],['l','litros']]:[['presentation','Presentación completa']]});
  if(p.quantity_kind!=='CONTINUOUS'){
   const shared=bind(grid,'Unidad logística compartida',p,'logistic_unit_id',{options:[['','Sin unidad logística'],...state.logistic_units.map(u=>[u.logistic_unit_id,u.label||'Unidad sin nombre'])]});
   scope.listen(shared,'change',()=>{view.unit=p.logistic_unit_id;render();notify();});
  }
  const compositionBox=el('div',undefined,'cargo-composition');body.append(compositionBox);
  const table=el('div',undefined,'guided-composition-table');table.setAttribute('role','table');table.setAttribute('aria-label','Composición por bultos');compositionBox.append(table);
  const headings=el('div',undefined,'guided-composition-row guided-composition-head');headings.setAttribute('role','row');for(const label of ['Producto','Bultos','% por cantidad','Peso bruto de bultos','Acción']){const h=el('span',label);h.setAttribute('role','columnheader');headings.append(h);}table.append(headings);
  const percentages=[];
  for(const component of p.components){
   const row=el('div',undefined,'guided-composition-row');row.setAttribute('role','row');table.append(row);
   bind(row,'Producto *',component,'product_id',{options:[['','Elegí un producto'],...state.products.map(q=>[q.product_id,q.name||'Producto sin nombre'])],required:true});
   const qty=bind(row,p.quantity_kind==='CONTINUOUS'?'Factor de material (1)':'Bultos por presentación *',component,'quantity',{type:'number',required:true,readOnly:p.quantity_kind==='CONTINUOUS'});qty.min='1';qty.step='1';
   const share=el('span',undefined,'guided-cell'),weight=el('span',undefined,'guided-cell');share.dataset.label='% por cantidad';weight.dataset.label='Peso bruto';row.append(share,weight,action('Quitar componente',()=>{p.components=p.components.filter(v=>v!==component);render();notify();},{icon:'trash'}));percentages.push({component,share,weight});
  }
  const total=el('p',undefined,'guided-composition-total');compositionBox.append(total);
  if(p.quantity_kind!=='CONTINUOUS')addControl(compositionBox,'Agregar producto a la composición',()=>p.components.push({product_id:'',quantity:'1'}),30,()=>p.components.length);
  else if(!p.components.length)addControl(compositionBox,'Seleccionar material',()=>p.components.push({product_id:'',quantity:'1'}),1,()=>p.components.length);
  projections.push(()=>{
   const stats=composition(p);for(const v of percentages){const product=state.products.find(q=>q.product_id===v.component.product_id),mass=kg(product?.gross_mass);
    v.share.textContent=stats.comparable&&stats.quantity?display(Number(v.component.quantity)/stats.quantity*100,'%',2):'No comparable';
    v.weight.textContent=mass!==null&&number(v.component.quantity)!==null?display(mass*Number(v.component.quantity),'kg'):'Pendiente';
   }
   total.textContent='Total de componentes: '+(stats.comparable?display(stats.quantity)+' bultos':'bultos no comparables')+' · Peso bruto de componentes: '+(stats.mass!==null?display(stats.mass,'kg'):'Pendiente')+' · Vista preliminar';
  });
  if(p.logistic_unit_id)body.append(action('Editar soporte y exterior cargado',()=>{view.unit=p.logistic_unit_id;render();onNavigate(2);},{icon:'edit',uiOnly:true}));
  else loadedFields(grid,p);
  const metadata=advanced(grid,'Metadatos físicos informativos');bind(metadata,'Orientación informativa (opcional)',p,'orientation_metadata',{maxLength:120});
  bind(metadata,'Apilable (informativo)',p,'stackable_metadata',{options:[['','Sin declarar'],['yes','Sí'],['no','No']],value:p.stackable_metadata==null?'':p.stackable_metadata?'yes':'no'},v=>v===''?null:v==='yes');
  note(body,'La participación se calcula por cantidad de bultos comparables, no por peso ni volumen. Dation no arma pallets automáticamente: cada composición es una presentación declarada.');
  summary(layout,p);note(root,'Una presentación completa equivale a una unidad en las líneas de órdenes; sus bultos interiores no son pallets adicionales.');
 }
 function updateViews(){
  for(const update of projections)update();
  for(const root of Object.values(roots))for(const select of root.querySelectorAll('[data-catalog-picker]')){
   const rows=state[select.dataset.catalogPicker]||[],key=select.dataset.catalogPicker==='products'?'product_id':select.dataset.catalogPicker==='logistic_units'?'logistic_unit_id':'presentation_id';
   for(const option of select.options){const value=rows.find(v=>v[key]===option.value);if(value)option.textContent=value.name||value.label||'Sin nombre';}
  }
  refreshDisabled();
 }
 function render(){
  const open=new Set(Object.values(roots).flatMap(r=>[...r.querySelectorAll('details[open]')].map(d=>d.dataset.editorDisclosure)));
  restrictions.clear();projections=[];renderUnits();renderProducts();renderPresentations();
  for(const root of Object.values(roots))for(const d of root.querySelectorAll('details'))if(open.has(d.dataset.editorDisclosure))d.open=true;
  updateViews();
 }
 function cleanPhysical(out,key){
  const value=out[key];if(!value)return;
  const keys=key.includes('dimensions')?['length','width','height']:['value'];
  // Incomplete inputs remain in snapshot(), never a partially declared DTO.
  if(!keys.every(k=>present(value[k])))delete out[key];
 }
 function read(){
  const result=copy(state);
  for(const p of result.products){p.units_per_package=Number(p.units_per_package);for(const k of ['code','category','density_kg_per_m3'])if(!present(p[k]))delete p[k];for(const k of ['gross_mass','net_mass','dimensions'])cleanPhysical(p,k);}
  for(const u of result.logistic_units){for(const k of ['empty_dimensions','tare_mass'])cleanPhysical(u,k);if(!present(u.structural_limit_kg))delete u.structural_limit_kg;}
  for(const p of result.presentations){for(const k of ['logistic_unit_id','density_kg_per_m3','orientation_metadata'])if(!present(p[k]))delete p[k];for(const k of ['loaded_dimensions','gross_mass','external_volume','extra_tare_mass'])cleanPhysical(p,k);}
  return result;
 }
 function validate(){
  if(!state.products.length||!state.presentations.length)return 'Agregá al menos un producto y una presentación física.';
  if(state.products.length>100||state.logistic_units.length>50||state.presentations.length>200)return 'Se alcanzó el máximo permitido para esta entidad.';
  for(const p of state.products)if(!p.name.trim()||!p.unit_label.trim())return 'Completá nombre y unidad de cada producto.';
  for(const u of state.logistic_units)if(!u.label.trim()||number(u.tare_mass?.value)===null)return 'Completá nombre y tara explícita de cada soporte; declarala como cero sólo si corresponde.';
  for(const object of [...state.products,...state.logistic_units,...state.presentations])for(const key of ['empty_dimensions','loaded_dimensions','dimensions']){
   const d=object[key];if(!d)continue;const values=['length','width','height'].map(k=>d[k]);
   if(values.some(present)&&!values.every(v=>number(v)>0))return key==='empty_dimensions'?'Si declarás medidas del soporte vacío, completá largo, ancho y alto.':'Completá los tres ejes positivos de las dimensiones declaradas.';
  }
  for(const p of state.presentations){
   if(!p.label.trim()||!p.components.length)return 'Completá el nombre y la composición de cada presentación.';
   if(p.components.length>30)return 'Una presentación admite hasta30 componentes.';
   if(new Set(p.components.map(c=>c.product_id)).size!==p.components.length)return 'Cada producto aparece una sola vez por presentación; sumá sus cantidades.';
   for(const c of p.components)if(!state.products.some(q=>q.product_id===c.product_id)||!(number(c.quantity)>0)||p.quantity_kind==='DISCRETE'&&!Number.isInteger(Number(c.quantity)))return 'Seleccioná productos reales y cantidades enteras positivas para presentaciones discretas.';
  }
  return '';
 }
 for(const root of Object.values(roots))scope.listen(root,'input',refreshDisabled);
 render();
 return {read,snapshot:()=>copy(state),ui:()=>({unit:view.unit,presentation:view.presentation,product:view.product}),validate,focusNew,
  hasData:()=>Object.values(state).some(v=>v.length),setActive(v){active=v;refreshDisabled();},lock(){locked=true;refreshDisabled();},
  setCompiled(value){compiled=value;serverError='';updateViews();},invalidate(){compiled=null;serverError='';updateViews();},showError(message){compiled=null;serverError=message;updateViews();},refreshProfile(){render();}
 };
}
