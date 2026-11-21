import {api,errorBox} from '../shared.mjs';
import {loadingState} from '../../platform/components.mjs';
import {el,button,field,pageHeader,collapsibleSection} from './forms.mjs';
import {mountPublishedReview} from './model-published-review.mjs';
import {assessCargoDraft} from './cargo-guided-state.mjs';
import {flattenCorePanel} from './wizard-ui.mjs';
import {browserIdentity,workingCopies,newModelDraft,resolveReturn} from './model-library-state.mjs';

export function libraryFooter(root,{back,status,notice,actions=[]}){
 const footer=el('footer',undefined,'d-card j101-footer'),previous=button('←',back),state=el('p',status,'d-metadata'),context=el('p',notice,'d-metadata'),controls=el('div',undefined,'j101-actions');
 previous.setAttribute('aria-label','Volver');previous.classList.add('j101-back');state.role='status';state.setAttribute('aria-live','polite');controls.append(...actions);footer.append(previous,state,context,controls);root.append(footer);return {footer,state,context,controls};
}
export async function mountModelLibrary(root,{route,navigate,caps,scope}){
 const identity=browserIdentity(),copies=workingCopies(identity),back=()=>navigate('logistics-models',{modelReturnId:route.modelReturnId}),go=values=>navigate('logistics-models',{modelReturnId:route.modelReturnId,...values});
 root.className='dispatch d-platform ultimate-foundation j101-library';root.dataset.modelMode=route.modelView||'library';
 const loadModel=()=>api('/api/platform/logistics-models/'+route.modelId,{signal:scope.signal});
 async function edit(modelId=null){
  if(!caps.can_manage_models)return;
  if(modelId){const saved=copies.list().find(v=>v.modelId===modelId&&!v.publishedVersionId);return go({modelId,modelView:'edit',modelWorkId:saved?.workId});}
  const workId=crypto.randomUUID();copies.write({workId,modelId:null,draft:newModelDraft(window.dationSession.identity.workspace.currency)},0);
  return go({modelId:'new',modelView:'edit',modelWorkId:workId});
 }
 function shell(title,copy){root.replaceChildren();const header=pageHeader(root,title,copy);header.querySelector('.d-eyebrow').textContent='DDA Logística · Core Configuration / 01';return header;}
 function done(){if(scope.active)root.dataset.ultimateReady='true';}
 if(route.modelView==='edit'||route.modelId==='new'){
  if(!caps.can_manage_models)throw Object.assign(new Error('No tenés permiso para editar modelos.'),{status:403});
  if(route.modelId==='new'&&!route.modelWorkId)return edit();
  const {mountLibraryEditor}=await import('./model-library-editor.mjs');if(scope.active)await mountLibraryEditor(root,{route,scope,copies,back,go,loadModel,shell});done();return;
 }
 if(route.modelId){
  const data=await loadModel();if(!scope.active)return;
  const versions=data.versions||[],model=data.model;
  if(route.modelView==='history'){
   shell('Versiones de '+model.name,'Consultá instantáneas publicadas. Abrir el historial no modifica modelos ni Cases.');
   const list=el('div',undefined,'j101-version-list');list.dataset.modelHistory=model.id;root.append(list);
   if(!versions.length)list.append(el('p','Este modelo todavía no tiene versiones publicadas.','d-card d-body'));
   for(const v of [...versions].sort((a,b)=>b.version-a.version)){
    const card=el('article',undefined,'d-card j101-version');card.append(el('h2','Versión '+v.version,'d-card-title'),el('p',publishedDate(v),'d-metadata'),el('p','Hash: '+v.config_hash,'d-metadata'),button('Revisar versión '+v.version,()=>go({modelId:model.id,modelVersionId:v.id,modelView:'review'})));list.append(card);
   }
   libraryFooter(root,{back,status:versions.length+' versiones publicadas',notice:'Las versiones publicadas son inmutables.',actions:[button('Volver a biblioteca',back)]});done();return;
  }
  if(!route.modelVersionId){
   if(!versions.length)return caps.can_manage_models&&model.status==='active'?edit(model.id):go({modelId:model.id,modelView:'history',replace:true});
   const latest=[...versions].sort((a,b)=>b.version-a.version)[0];return go({modelId:model.id,modelVersionId:latest.id,modelView:'review',replace:true});
  }
  const version=versions.find(v=>v.id===route.modelVersionId);
  if(!version)throw Object.assign(new Error('No se encontró la versión histórica solicitada. No se cambió por otra versión.'),{status:404});
  shell(model.name,'Revisando la versión '+version.version+' publicada. Esta configuración no se puede modificar directamente.');
  const panel=collapsibleSection(root,'01 Logistics Model','',{open:true});mountPublishedReview(panel,{model,model_version:version},{reviewContext:'library'});flattenCorePanel(panel);
  const actions=[button('Ver historial',()=>go({modelId:model.id,modelView:'history'}))];
  if(caps.can_manage_models&&model.status==='active'&&model.draft_config_jsonb.version===2&&assessCargoDraft({configuration:model.draft_config_jsonb}).representable)actions.push(button('Preparar nueva versión',()=>edit(model.id)));
  if(model.status==='archived')root.append(el('p','Modelo archivado · Consulta histórica.','guided-note'));
  libraryFooter(root,{back,status:'Consulta · Versión '+version.version,notice:'Consultar no selecciona ningún modelo para un Case.',actions});done();return;
 }
 shell('Logistics Models','Creá y administrá los modelos operativos que después podrás utilizar en tus casos de decisión.');
 const header=root.querySelector('.d-page-header'),actions=el('div',undefined,'d-page-header__actions');
 if(caps.can_manage_models)actions.append(button('Crear nuevo modelo',()=>edit(),'primary'));header.append(actions);
 const toolbar=el('form',undefined,'j101-toolbar'),search=field(toolbar,'Buscar por nombre',{name:'library_search',type:'search',maxLength:120}),status=field(toolbar,'Estado',{name:'library_state',value:'all',options:[['all','Todos'],['active','Activos'],['published','Publicados'],['draft','Borradores'],['archived','Archivados']]}),find=button('Buscar',()=>{page=0;load();});
 toolbar.append(find);root.append(toolbar);scope.listen(toolbar,'submit',e=>{e.preventDefault();find.click();});scope.listen(status,'change',()=>{page=0;paint();});
 const list=el('div',undefined,'j101-model-grid'),pager=el('nav',undefined,'j101-pager');pager.setAttribute('aria-label','Páginas de modelos');list.setAttribute('aria-live','polite');root.append(list,pager);
 let page=0,items=[],loaded=false,query='',generation=0;
 const target=route.modelReturnId?resolveReturn(route.modelReturnId,identity):null;
 const next=button(target?'Volver al contexto de origen':'Continuar a Decision Case',()=>{
  if(target)return navigate(target.view,target);
  return navigate('logistics-case-setup',{caseId:null,modelId:null,coreStep:1});
 });
 if(!target&&!caps.can_create_case)next.disabled=true;
 if(route.modelReturnId&&!target){next.disabled=true;next.textContent='Contexto de origen no disponible';}
 const footer=libraryFooter(root,{back:()=>navigate('logistics-overview',{caseId:null,nodeId:null,runId:null}),status:'Consultando modelos…',notice:target?'Se conserva el Case y su versión. La biblioteca no los modifica.':'La vinculación se realiza en la configuración de Case vigente; no se preselecciona un modelo.',actions:[next]});
 function paint(){
  if(!loaded)return;
  const local=caps.can_manage_models?copies.list().filter(v=>!v.modelId&&!v.publishedVersionId&&(!query||v.draft.name.toLocaleLowerCase().includes(query.toLocaleLowerCase()))).map(v=>({id:v.draft.id,name:v.draft.name||'Borrador sin nombre',description:v.draft.description,status:'active',versions:[],local:v})):[];
  const all=[...local,...items],filtered=all.filter(m=>status.value==='all'||status.value==='draft'&&m.status==='active'&&!m.versions.length||status.value==='published'&&m.status==='active'&&m.versions.length||m.status===status.value);
  page=Math.min(page,Math.max(0,Math.ceil(filtered.length/25)-1));list.replaceChildren();pager.replaceChildren();
  if(!filtered.length){const empty=el('section',undefined,'d-card j101-empty');empty.append(el('h2',query||status.value!=='all'?'No hay modelos que coincidan.':'Todavía no hay modelos logísticos.','d-card-title'),el('p',query||status.value!=='all'?'Probá otro nombre o estado.':'Creá tu primer modelo para definir la operación que después utilizarás en tus Cases.','d-body'));if(caps.can_manage_models&&!all.length)empty.append(button('Crear primer modelo',()=>edit()));list.append(empty);}
  for(const m of filtered.slice(page*25,(page+1)*25)){
   const card=el('article',undefined,'d-card j101-model-card'),copy=el('div'),badge=el('span',m.status==='archived'?'Archivado':m.versions.length?'Publicado':'Borrador','ultimate-disclosure__status'),controls=el('div',undefined,'j101-actions');card.dataset.modelId=m.id;
   badge.dataset.state=m.versions.length?'complete':'pending';copy.append(el('h2',m.name,'d-card-title'),el('p',m.description||'Sin descripción','d-body'));card.append(copy,badge,el('p',m.local?'Borrador en este navegador · No publicado':m.versions.length?m.versions.length+' '+(m.versions.length===1?'versión publicada':'versiones publicadas'):'Borrador sin publicar — todavía no disponible para vincular a un Case.','d-metadata'));
   if(m.updated_at)card.append(el('p','Última actualización: '+formatDate(m.updated_at),'d-metadata'));
   if(m.versions.length){const v=[...m.versions].sort((a,b)=>b.version-a.version)[0];controls.append(button('Revisar modelo',()=>go({modelId:m.id,modelVersionId:v.id,modelView:'review'})),button('Ver versiones',()=>go({modelId:m.id,modelView:'history'})));}
   if(caps.can_manage_models&&m.status==='active')controls.append(button(m.local?'Recuperar borrador':m.versions.length?'Abrir borrador':'Editar borrador',()=>m.local?go({modelId:'new',modelWorkId:m.local.workId,modelView:'edit'}):edit(m.id)));
   card.append(controls);list.append(card);
  }
  const previous=button('Anterior',()=>{page--;paint();}),following=button('Siguiente',()=>{page++;paint();});previous.disabled=page===0;following.disabled=(page+1)*25>=filtered.length;pager.append(previous,el('p','Página '+(page+1)+' · '+filtered.length+' modelos','d-metadata'),following);footer.state.textContent=filtered.length+' modelos · Consulta de biblioteca';
 }
 async function load(){
  const own=++generation;query=search.value.trim();loaded=false;list.setAttribute('aria-busy','true');list.replaceChildren(loadingState('Cargando modelos…'));pager.replaceChildren();
  try{const collected=[],seen=new Set();let offset=0,total;
   do{const result=await api('/api/platform/logistics-models?'+new URLSearchParams({q:query,limit:50,offset,include_archived:'true'}),{signal:scope.signal});if(!scope.active||own!==generation)return;
    if(!Array.isArray(result.items)||!Number.isInteger(result.total)||result.total<0)throw new Error('La respuesta de modelos no tiene un formato válido.');
    if(total!==undefined&&result.total!==total)throw new Error('La biblioteca cambió durante la consulta. Reintentá para actualizarla.');total=result.total;
    if(!result.items.length&&offset<total)throw new Error('La lista cambió durante la consulta. Reintentá.');
    for(const model of result.items){if(seen.has(model.id))throw new Error('La lista cambió durante la consulta. Reintentá.');seen.add(model.id);collected.push(model);}offset+=result.items.length;
   }while(offset<total);
   items=collected;loaded=true;paint();done();
  }catch(error){if(scope.active&&own===generation){footer.state.textContent='No pudimos recuperar los modelos.';errorBox(list,error,load);done();}}
  finally{if(scope.active&&own===generation)list.removeAttribute('aria-busy');}
 }
 await load();
}
function formatDate(value){const d=new Date(value);return Number.isNaN(d.getTime())?'No disponible':new Intl.DateTimeFormat('es-AR',{dateStyle:'medium',timeZone:'America/Argentina/Buenos_Aires'}).format(d);}
function publishedDate(version){return version.published_at?'Publicado el '+formatDate(version.published_at):'Fecha de publicación no disponible';}
