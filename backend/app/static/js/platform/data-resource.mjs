const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export const HUB_FILTERS=Object.freeze({all:'Todos',orders:'Órdenes',fleet:'Flota',validated:'Validados',issues:'Con problemas',archived:'Archivados'});
export const HUB_KEYS=['data_tab','data_filter','data_q','data_offset','dataset_id','pack_orders_id','pack_fleet_id'];
export function readHubResource(url){
 const q=new URL(url,'http://localhost').searchParams;
 const value={tab:q.get('data_tab')||'datasets',filter:q.get('data_filter')||'all',q:q.get('data_q')||'',offset:Number(q.get('data_offset')||0),datasetId:q.get('dataset_id'),ordersId:q.get('pack_orders_id'),fleetId:q.get('pack_fleet_id')};
 if(!['datasets','packs'].includes(value.tab)||!Object.hasOwn(HUB_FILTERS,value.filter)||value.q.length>120||!Number.isSafeInteger(value.offset)||value.offset<0||value.offset>1000000)throw new Error('El enlace de datos no es válido.');
 for(const id of [value.datasetId,value.ordersId,value.fleetId])if(id&&!uuid.test(id))throw new Error('El enlace contiene un identificador de datos inválido.');
 if(Boolean(value.ordersId)!==Boolean(value.fleetId)||value.datasetId&&value.ordersId)throw new Error('El enlace de Data Pack está incompleto.');
 return value;
}
export function writeHubResource(url,value={}){
 for(const key of HUB_KEYS)url.searchParams.delete(key);
 for(const [key,field]of [['data_tab','tab'],['data_filter','filter'],['data_q','q'],['data_offset','offset'],['dataset_id','datasetId'],['pack_orders_id','ordersId'],['pack_fleet_id','fleetId']]){
  if(value[field]!==undefined&&value[field]!==null&&value[field]!==''&&value[field]!==0)url.searchParams.set(key,value[field]);
 }
 readHubResource(url);return url;
}
