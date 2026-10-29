import {api,post,errorBox} from '../shared.mjs';
import {scopeFor} from '../lifecycle.mjs';
import {ensureStylesheet} from '../styles.mjs';
import {loadingState} from '../../platform/components.mjs';
import {el,button,field,section,pageHeader,draftStore,mountForm,confirmAction} from './forms.mjs';

import {mountModelFields} from './model-fields.mjs';
export {ROLES,DIMENSIONS,defaultConfiguration} from './model-fields.mjs';
import {ROLES,defaultConfiguration} from './model-fields.mjs';

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
  const form=kit.form,modelFields=mountModelFields(form,scope,draft);
  kit.setCollector(modelFields.read,modelFields.validate);
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
     publishedIntent ||= {version_id:crypto.randomUUID(),expected_revision:base.revision};store.write({...modelFields.read(),publish_intent:publishedIntent});publish.disabled=true;publish.setAttribute('aria-busy','true');
     try{await post('/api/platform/logistics-models/'+base.id+'/versions',publishedIntent,{signal:scope.signal});kit.markSaved();if(scope.active)await navigate('logistics-models',{modelId:base.id,replace:true});}
     catch(error){if(scope.active){if(error.status===409)kit.conflict('El Model cambió. Tu borrador se conserva. Recargá la versión guardada antes de publicar.');else{kit.status.textContent=error.message;kit.status.role='alert';}publish.disabled=false;publish.removeAttribute('aria-busy');}}
    },'primary');history.append(publish);
   }root.append(history);
  }
  if(!saved)kit.markSaved();root.dataset.ultimateReady='true';
 }
}
