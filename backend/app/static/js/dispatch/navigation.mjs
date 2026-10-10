export const VIEWS=['inicio','logistics-overview','traceability','overview','logistics-data','logistics-map','logistics-config','decision-dashboard','library','settings'];
export const NODES=['logistics_assignment','logistics_scheduling','logistics_final_assignment'];
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function readResource(url){
  const q=new URL(url,'http://localhost').searchParams;
  const resource={view:q.get('view')||(q.has('run_id')?'decision-dashboard':'overview'),caseId:q.get('case_id'),nodeId:q.get('node_id'),runId:q.get('run_id')};
  if(!resource.nodeId&&q.get('dda')==='scheduling_v1')resource.nodeId='logistics_scheduling';
  if(!resource.nodeId&&resource.runId)resource.nodeId='logistics_assignment';
  if(!VIEWS.includes(resource.view))throw new Error('La pantalla solicitada no existe.');
  if(resource.nodeId&&!NODES.includes(resource.nodeId))throw new Error('La decisión solicitada no existe.');
  for(const id of [resource.caseId,resource.runId])if(id&&!UUID.test(id))throw new Error('El enlace contiene un identificador inválido.');
  if(resource.view!=='decision-dashboard')resource.runId=null;
  return resource;
}
export function resourceUrl(url,resource){
  const next=new URL(url,'http://localhost');
  for(const key of ['view','case_id','node_id','run_id','dda'])next.searchParams.delete(key);
  next.searchParams.set('view',resource.view);
  if(resource.caseId)next.searchParams.set('case_id',resource.caseId);
  if(['logistics-config','decision-dashboard'].includes(resource.view)&&resource.nodeId)next.searchParams.set('node_id',resource.nodeId);
  if(resource.view==='decision-dashboard'&&resource.runId)next.searchParams.set('run_id',resource.runId);
  return next;
}
export function runDecisionState(run,decisionCase,nodeId){
  const node=decisionCase?.nodes?.[nodeId]||{};
  if(node.status==='stale'&&String(node.approved_run_id||node.run_id)===String(run.id))return 'stale';
  if(run.superseded_at)return 'superseded';
  if(String(node.approved_run_id||'')===String(run.id))return 'approved';
  return 'review';
}
