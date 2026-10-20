import {FOUNDATION} from './foundation.mjs';
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const legacyFilters=['all','orders','fleet','validated','issues','archived'];
export const HUB_TYPES=Object.freeze({all:'Todos los tipos',...FOUNDATION.datasetTypes});
export const HUB_VALIDATIONS=Object.freeze({all:'Todas las validaciones',validated:'Validado',issues:'Con observaciones',unknown:'Sin registro'});
export const HUB_STATES=Object.freeze({active:'Activos',archived:'Archivados',all:'Todos los estados'});
export const HUB_KEYS=['data_tab','data_filter','data_q','data_type','data_validation','data_state','data_offset','data_cases_offset','dataset_id','pack_orders_id','pack_fleet_id'];
export function readHubResource(url){
 const q=new URL(url,'http://localhost').searchParams,old=q.get('data_filter')||'all';
 if(!['datasets','packs'].includes(q.get('data_tab')||'datasets')||!legacyFilters.includes(old))throw new Error('El enlace de datos no es válido.');
 const value={q:q.get('data_q')||'',type:q.get('data_type')||(['orders','fleet'].includes(old)?old:'all'),validation:q.get('data_validation')||(['validated','issues'].includes(old)?old:'all'),state:q.get('data_state')||(old==='archived'?'archived':'active'),offset:Number(q.get('data_offset')||0),datasetId:q.get('dataset_id'),casesOffset:Number(q.get('data_cases_offset')||0)};
 if(!Object.hasOwn(HUB_TYPES,value.type)||!Object.hasOwn(HUB_VALIDATIONS,value.validation)||!Object.hasOwn(HUB_STATES,value.state)||value.q.length>120||[value.offset,value.casesOffset].some(n=>!Number.isSafeInteger(n)||n<0||n>1000000))throw new Error('El enlace de datos no es válido.');
 if(value.datasetId&&!uuid.test(value.datasetId))throw new Error('El enlace contiene un identificador de datos inválido.');
 if(q.get('data_tab')==='packs'||q.has('pack_orders_id')||q.has('pack_fleet_id')){value.datasetId=null;value.casesOffset=0;}
 return value;
}
export function writeHubResource(url,value={}){
 for(const key of HUB_KEYS)url.searchParams.delete(key);
 for(const [key,field]of [['data_q','q'],['data_type','type'],['data_validation','validation'],['data_state','state'],['data_offset','offset'],['dataset_id','datasetId'],['data_cases_offset','casesOffset']]){
  if(value[field]!==undefined&&value[field]!==null&&value[field]!==''&&value[field]!==0)url.searchParams.set(key,value[field]);
 }
 readHubResource(url);return url;
}
