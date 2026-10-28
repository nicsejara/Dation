import {api,post,errorBox} from '../shared.mjs';
import {scopeFor} from '../lifecycle.mjs';
import {ensureStylesheet} from '../styles.mjs';
import {loadingState} from '../../platform/components.mjs';
import {el,button,field,section,choices,pageHeader,draftStore,mountForm,confirmAction} from './forms.mjs';

export const ROLES=[['SHIPPER','Generador de carga'],['LOGISTICS_PROVIDER','Proveedor logístico'],['HYBRID','Operación híbrida']];
export const DIMENSIONS=[['pallets','Pallets'],['weight_kg','Peso (kg)'],['volume_m3','Volumen (m³)'],['units','Unidades']];
export const defaultConfiguration=currency=>({version:1,operating_role:'SHIPPER',transport_pattern:'DIRECT',allowed_sources:['OWN','EXTERNAL'],
 active_dimensions:['pallets'],primary_dimension:'pallets',split_permitted:false,homogeneous_loads_declared:false,
 currency_policy:{currency:currency||'ARS',minor_units:2,rounding:'ROUND_HALF_UP'},own_cost_model:'OWN_OPERATING_CYCLE',external_cost_models:['PER_TRIP','PER_KM'],per_km_billing_bases:['ONE_WAY','ROUND_TRIP']});

export async function mountModels(root,{route,navigate}){
 delete root.dataset.ultimateReady;
 const scope=scopeFor(root);await ensureStylesheet('ultimate-foundation-styles','/static/css/ultimate-foundation.css','t3-v1');if(!scope.active)return;
 root.className='dispatch d-platform ultimate-foundation';root.append(loadingState('Cargando Logistics Models…'));
 try{
  const caps=await api('/api/platform/ultimate-foundation/capabilities',{signal:scope.signal});if(!scope.active)return;
  if(route.modelId)await editor(caps);else await library(caps);
 }catch(error){if(scope.active)errorBox(root,error,()=>navigate('logistics-models',{modelId:route.modelId}));}
 async function library(caps){
  let offset=0,search='';root.replaceChildren();const header=pageHeader(root,'Logistics Models','Una configuración reusable de tu operación. Publicá versiones para usarlas en distintos Cases sin modificar su historia.');
  const actions=el('div',undefined,'d-page-header__actions');if(caps.can_manage_models)actions.append(button('Crear Model',()=>navigate('logistics-models',{modelId:'new'}),'primary'));
  if(caps.can_create_case)actions.append(button('Crear Decision Case',()=>navigate('logistics-case-setup',{caseId:null})));header.append(actions);
  const toolbar=el('form',undefined,'ultimate-toolbar'),q=field(toolbar,'Buscar Models',{name:'model_search',type:'search',maxLength:120});const find=button('Buscar',()=>{search=q.value;offset=0;load();});toolbar.append(find);scope.listen(toolbar,'submit',e=>{e.preventDefault();find.click();});root.append(toolbar);
  const list=el('div',undefined,'ultimate-list'),pager=el('div',undefined,'ultimate-actions');root.append(list,pager);let generation=0;
  async function load(){const own=++generation;list.replaceChildren(loadingState('Cargando Models…'));try{const result=await api('/api/platform/logistics-models?'+new URLSearchParams({q:search,limit:25,offset,include_archived:'true'}),{signal:scope.signal});if(!scope.active||own!==generation)return;
   list.replaceChildren();if(!result.items.length)list.append(el('p',search?'No hay Models que coincidan. Probá otro nombre.':'Todavía no hay Models. Un Admin puede crear y publicar la primera versión.','d-card d-body'));
   for(const m of result.items){const card=el('article',undefined,'d-card ultimate-model-card'),copy=el('div');copy.append(el('h2',m.name,'d-card-title'),el('p',m.description||'Configuración de operación logística.','d-body'),el('p',(m.status==='archived'?'Archivado · ':'')+(m.versions.length?m.versions.length+' '+(m.versions.length===1?'versión publicada':'versiones publicadas'):'Sin versiones publicadas'),'d-metadata'));
    card.append(copy,button('Abrir Model',()=>navigate('logistics-models',{modelId:m.id})));list.append(card);}
   pager.replaceChildren(button('Anterior',()=>{offset=Math.max(0,offset-25);load();}),el('span',result.total+' Models','d-metadata'),button('Siguiente',()=>{offset+=25;load();}));pager.firstChild.disabled=offset===0;pager.lastChild.disabled=offset+25>=result.total;
  }catch(error){if(scope.active&&own===generation)errorBox(list,error,load);}}await load();if(scope.active)root.dataset.ultimateReady='true';
 }
 async function editor(caps){
  const fresh=route.modelId==='new';if(fresh&&!caps.can_manage_models)throw Object.assign(new Error('Sólo un Admin puede crear Models.'),{status:403});
  const data=fresh?null:await api('/api/platform/logistics-models/'+route.modelId,{signal:scope.signal});if(!scope.active)return;
  const store=draftStore('model',route.modelId),base=data?.model,saved=store.read();
  const initial={id:base?.id||crypto.randomUUID(),name:base?.name||'',description:base?.description||'',status:base?.status||'active',expected_revision:base?.revision||1,
   configuration:base?.draft_config_jsonb||defaultConfiguration(window.dationSession.identity.workspace.currency)};
  const draft=saved||initial;let publishedIntent=saved?.publish_intent||null;
  root.replaceChildren();const header=pageHeader(root,fresh?'Crear Logistics Model':base.name,'El borrador puede cambiar. Cada publicación conserva una versión inmutable para los Cases que la utilizan.');header.append(button('Volver a Models',()=>navigate('logistics-models',{modelId:null})));
  const kit=mountForm(root,scope,{initial,store,submitLabel:fresh?'Crear Model':'Guardar borrador',onReload:()=>navigate('logistics-models',{modelId:route.modelId,replace:true}),onSave:async value=>{
   const body={name:value.name,description:value.description||null,configuration:value.configuration};let result;
   if(fresh)result=await post('/api/platform/logistics-models',{id:value.id,...body},{signal:scope.signal});
   else result=await api('/api/platform/logistics-models/'+base.id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,status:value.status,expected_revision:value.expected_revision}),signal:scope.signal});
   kit.markSaved();if(scope.active)await navigate('logistics-models',{modelId:result.model.id,replace:true});
  }});
  const form=kit.form,identity=section(form,'Identidad del Model'),name=field(identity,'Nombre del Model',{name:'model_name',value:draft.name,required:true,maxLength:120}),description=field(identity,'Descripción (opcional)',{name:'model_description',type:'textarea',value:draft.description,maxLength:1000});
  const status=field(identity,'Estado',{name:'model_status',options:[['active','Activo'],['archived','Archivado']],value:draft.status});
  const config=draft.configuration,operation=section(form,'Operación y recursos','El rol describe la operación. Los permisos y el motor de decisión se mantienen iguales para todos los roles.');
  const role=field(operation,'Operating Role',{name:'operating_role',options:ROLES,value:config.operating_role}),pattern=field(operation,'Patrón de transporte',{name:'transport_pattern',value:'Directo · origen a destino',readOnly:true});
  const sources=choices(operation,'Fuentes de recursos','sources',[['OWN','Propios'],['EXTERNAL','Externos']],config.allowed_sources);
  const dimensions=choices(operation,'Dimensiones de capacidad','dimensions',DIMENSIONS,config.active_dimensions),primary=field(operation,'Dimensión principal de reporte',{name:'primary_dimension',options:DIMENSIONS,value:config.primary_dimension});
  const split=choices(operation,'Comportamiento de carga','split',[['yes','Permitir fraccionamiento de órdenes']],config.split_permitted?['yes']:[]);
  const homogeneous=choices(operation,'Compatibilidad','homogeneous',[['yes','Declarar cargas homogéneas']],config.homogeneous_loads_declared?['yes']:[]);
  operation.append(el('p','Sin declaración de homogeneidad, la compatibilidad de consolidación debe ser explícita. Los viajes son directos; no incluyen multiparada.','d-field__help'));
  const costs=section(form,'Moneda y reglas de costo','Las tarifas concretas se informan con los recursos. Un costo desconocido no se convierte en cero.');
  const currency=field(costs,'Moneda',{name:'currency',value:config.currency_policy.currency,required:true,maxLength:3}),minor=field(costs,'Decimales monetarios',{name:'minor_units',options:Array.from({length:7},(_,i)=>[String(i),String(i)]),value:String(config.currency_policy.minor_units)});
  field(costs,'Costo de recursos propios',{name:'own_cost',value:'Costo operativo del ciclo directo',readOnly:true});
  const external=choices(costs,'Tarifas externas permitidas','external_costs',[['PER_TRIP','Por viaje'],['PER_KM','Por kilómetro']],config.external_cost_models),billing=choices(costs,'Base de facturación por km','billing',[['ONE_WAY','Sólo ida'],['ROUND_TRIP','Ida y vuelta']],config.per_km_billing_bases);
  const collect=()=>({id:draft.id,expected_revision:draft.expected_revision,name:name.value.trim(),description:description.value.trim(),status:status.value,configuration:{version:1,operating_role:role.value,transport_pattern:'DIRECT',allowed_sources:sources(),active_dimensions:dimensions(),primary_dimension:primary.value,split_permitted:split().length>0,homogeneous_loads_declared:homogeneous().length>0,currency_policy:{currency:currency.value.trim().toUpperCase(),minor_units:Number(minor.value),rounding:'ROUND_HALF_UP'},own_cost_model:'OWN_OPERATING_CYCLE',external_cost_models:external(),per_km_billing_bases:billing()}});
  kit.setCollector(collect,()=>{const c=collect().configuration,e={};if(!c.allowed_sources.length)e.operating_role='Elegí al menos una fuente de recursos.';if(!c.active_dimensions.includes(c.primary_dimension))e.primary_dimension='La dimensión principal debe estar activa.';if(!/^[A-Z]{3}$/.test(c.currency_policy.currency))e.currency='Ingresá una moneda de tres letras, por ejemplo ARS.';if(c.allowed_sources.includes('EXTERNAL')&&!c.external_cost_models.length)e.own_cost='Elegí una tarifa externa permitida.';if(c.external_cost_models.includes('PER_KM')&&!c.per_km_billing_bases.length)e.own_cost='Elegí una base de facturación por kilómetro.';return e;});
  kit.finish();if(!caps.can_manage_models){for(const n of form.querySelectorAll('input,select,textarea,button'))n.disabled=true;kit.status.textContent='Sólo un Admin puede editar o publicar el Model.';}
  if(saved)kit.status.textContent=base&&draft.expected_revision!==base.revision?'Hay un borrador de una revisión anterior. Se conserva para que puedas revisarlo.':'Borrador recuperado en este navegador.';
  if(data){
   const history=el('section',undefined,'d-card ultimate-section');history.append(el('h2','Versiones publicadas','d-section-title'),el('p','Una nueva versión no cambia los Cases que ya utilizan una anterior.','d-body'));
   if(!data.versions.length)history.append(el('p','Todavía no hay versiones publicadas.','d-metadata'));
   for(const v of data.versions){const row=el('div',undefined,'ultimate-version');row.append(el('strong','Versión '+v.version),el('span',ROLES.find(([id])=>id===v.config_jsonb.operating_role)?.[1]||v.config_jsonb.operating_role,'d-metadata'),el('span',v.config_jsonb.currency_policy?.currency||'','d-metadata'));if(caps.can_create_case&&base.status==='active')row.append(button('Crear Case con este Model',()=>navigate('logistics-case-setup',{caseId:null,modelId:base.id})));history.append(row);}
   if(caps.can_manage_models&&base.status==='active'){
    const publish=button('Publicar nueva versión',async()=>{
     if(kit.dirty){kit.status.textContent='Guardá el borrador antes de publicar.';return;}
     if(!await confirmAction(root,scope,'Publicar una nueva versión','La configuración guardada quedará inmutable. Las versiones y los Cases anteriores se conservarán.','Publicar versión'))return;
     publishedIntent ||= {version_id:crypto.randomUUID(),expected_revision:base.revision};store.write({...collect(),publish_intent:publishedIntent});publish.disabled=true;publish.setAttribute('aria-busy','true');
     try{await post('/api/platform/logistics-models/'+base.id+'/versions',publishedIntent,{signal:scope.signal});kit.markSaved();if(scope.active)await navigate('logistics-models',{modelId:base.id,replace:true});}
     catch(error){if(scope.active){if(error.status===409)kit.conflict('El Model cambió. Tu borrador se conserva. Recargá la versión guardada antes de publicar.');else{kit.status.textContent=error.message;kit.status.role='alert';}publish.disabled=false;publish.removeAttribute('aria-busy');}}
    },'primary');history.append(publish);
   }root.append(history);
  }
  if(!saved)kit.markSaved();root.dataset.ultimateReady='true';
 }
}
