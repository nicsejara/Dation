import {DDA_CATALOG} from './dda-catalog.mjs';
export const CENTER_FILTERS=Object.freeze({all:'Todos los estados',in_progress:'En progreso',review:'En revisión',pending_approval:'Pendientes de aprobación',approved:'Con aprobación vigente',completed:'Completados',archived:'Archivados'});
export const CENTER_KEYS=['center_filter','center_q','center_dda','center_owner','center_offset','center_case_id','center_node','center_runs_offset'];
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function readCenterResource(url){
 const q=new URL(url,'http://localhost').searchParams,value={filter:q.get('center_filter')||'all',q:q.get('center_q')||'',dda:q.get('center_dda')||'all',owner:q.get('center_owner')||'all',offset:Number(q.get('center_offset')||0),caseId:q.get('center_case_id'),nodeId:q.get('center_node'),runsOffset:Number(q.get('center_runs_offset')||0)};
 if(!Object.hasOwn(CENTER_FILTERS,value.filter)||!['all',...DDA_CATALOG.map(d=>d.id)].includes(value.dda)||!(['all','me','unassigned'].includes(value.owner)||uuid.test(value.owner))||value.q.length>120||[value.offset,value.runsOffset].some(n=>!Number.isSafeInteger(n)||n<0||n>1000000)||value.caseId&&!uuid.test(value.caseId)||value.nodeId&&(!value.caseId||!['logistics_assignment','logistics_scheduling','logistics_final_assignment'].includes(value.nodeId)))throw new Error('El enlace de Decision Center no es válido.');
 return value;
}
export function writeCenterResource(url,value={}){
 for(const key of CENTER_KEYS)url.searchParams.delete(key);
 for(const [key,field]of [['center_filter','filter'],['center_q','q'],['center_dda','dda'],['center_owner','owner'],['center_offset','offset'],['center_case_id','caseId'],['center_node','nodeId'],['center_runs_offset','runsOffset']])if(value[field]!==undefined&&value[field]!==null&&value[field]!==''&&value[field]!==0)url.searchParams.set(key,value[field]);
 readCenterResource(url);return url;
}
