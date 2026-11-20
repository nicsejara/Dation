// Identity and recovery only. No API writes, Case draft access or implicit selection.
import {defaultConfigurationV2} from './model-defaults.mjs';
import {readResource,resourceUrl,VIEWS} from '../navigation/resource.mjs';
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export const MODEL_VIEWS=['library','edit','review','history'];
const copy=value=>structuredClone(value);
function identity({workspace,user}){
 if(!uuid.test(workspace||'')||!uuid.test(user||''))throw new Error('No se pudo verificar la identidad del borrador.');
 return workspace+'.'+user;
}
export function browserIdentity(){const i=window.dationSession?.identity;return {workspace:i?.membership?.workspace_id,user:i?.profile?.id};}
export function newModelDraft(currency){
 const configuration=defaultConfigurationV2(['ARS','USD','EUR'].includes(currency)?currency:'ARS');
 configuration.active_dimensions=['weight_kg','volume_m3'];configuration.primary_dimension='weight_kg';configuration.cargo.input_mode='catalog';
 return {id:crypto.randomUUID(),name:'',description:'',status:'active',expected_revision:1,configuration,
  guided_ux:{edition:'ultimate',origin:'new-guided',confirmed:{},subconfirmed:{}}};
}
export function modelRoute(values={}){return {view:'logistics-models',caseId:null,nodeId:null,runId:null,...values};}
export function workingCopies(options){
 const storage=options.storage||localStorage,prefix='dation.models.working.v1.'+identity(options)+'.';
 const key=id=>{if(!uuid.test(id||''))throw new Error('Identidad del borrador inválida.');return prefix+id;};
 function read(id){const raw=storage.getItem(key(id));if(!raw)return null;
  let value;try{value=JSON.parse(raw);}catch{throw new Error('La copia local no se puede leer. Conservá el almacenamiento y recuperá el modelo desde el servidor.');}
  if(value.schema!==1||value.workId!==id||!uuid.test(value.draft?.id||'')||!Number.isSafeInteger(value.recordRevision))throw new Error('La copia local no tiene un formato compatible. No se reemplazó.');
  return copy(value);
 }
 return {read,list(){const result=[];for(let i=0;i<storage.length;i++){const k=storage.key(i);if(k?.startsWith(prefix))result.push(read(k.slice(prefix.length)));}return result.sort((a,b)=>b.updatedAt.localeCompare(a.updatedAt));},
  write(value,expected){const current=read(value.workId);if((current?.recordRevision||0)!==expected)throw Object.assign(new Error('El borrador cambió en otra pestaña. Se conserva tu formulario; recargá antes de guardar.'),{status:409});
   const next={...copy(value),schema:1,recordRevision:expected+1,updatedAt:new Date().toISOString()};storage.setItem(key(value.workId),JSON.stringify(next));return next;
  },remove(id,expected){const current=read(id);if(current&&current.recordRevision!==expected)throw new Error('El borrador cambió en otra pestaña.');storage.removeItem(key(id));}
 };
}
const returnsPrefix=options=>'dation.models.return.v1.'+identity(options)+'.';
export function rememberReturn(target,options){
 if(!VIEWS.includes(target?.view)||target.view==='logistics-models')throw new Error('Destino de regreso inválido.');
 const normalized=readResource(resourceUrl('https://local.invalid/app',target)),id=crypto.randomUUID();
 (options.storage||sessionStorage).setItem(returnsPrefix(options)+id,JSON.stringify(normalized));return id;
}
export function resolveReturn(id,options){
 if(!uuid.test(id||''))return null;
 try{const raw=(options.storage||sessionStorage).getItem(returnsPrefix(options)+id);if(!raw)return null;const value=JSON.parse(raw);if(!VIEWS.includes(value.view)||value.view==='logistics-models')return null;return readResource(resourceUrl('https://local.invalid/app',value));}catch{return null;}
}
export function draftContent(draft){const value=copy(draft);if(value.guided_ux)delete value.guided_ux.openBlocks;return JSON.stringify(value);}
// localStorage has no atomic compare-and-swap. Hold a browser lock for the
// mounted working copy; distinct copies still use SQL revision CAS per model.
export async function lockWorkingCopy(workId,scope){
 if(!uuid.test(workId||'')||!navigator.locks)throw new Error('Este navegador no permite proteger el borrador entre pestañas. Usá un navegador compatible.');
 const name='dation-model-copy.'+identity(browserIdentity())+'.'+workId;
 await new Promise((resolve,reject)=>{
  navigator.locks.request(name,{ifAvailable:true},async lock=>{
   if(!lock){reject(new Error('Este borrador ya está abierto en otra pestaña. Continuá allí o abrí otra copia desde la biblioteca.'));return;}
   await new Promise(release=>{scope.own(release);if(scope.active)resolve();else reject(new Error('La navegación cambió.'));});
  }).catch(reject);
 });
}
