export const PLATFORM_PATHS=Object.freeze({'platform-home':'/app',inicio:'/app/ddas','platform-decisions':'/app/decisions','platform-data':'/app/data','platform-team':'/app/team',settings:'/app/settings',profile:'/app/profile','logistics-overview':'/app/ddas/logistics',overview:'/app/ddas/logistics','logistics-data':'/app/ddas/logistics/data','logistics-map':'/app/ddas/logistics/decisions','logistics-config':'/app/ddas/logistics/configure','decision-dashboard':'/app/ddas/logistics/dashboard',traceability:'/app/history',library:'/app/history'});
export const VIEWS=['platform-home','platform-decisions','platform-data','platform-team','profile','inicio','logistics-overview','traceability','overview','logistics-data','logistics-map','logistics-config','decision-dashboard','library','settings'];
export const NODES=['logistics_assignment','logistics_scheduling','logistics_final_assignment'];
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
import {HUB_KEYS,readHubResource,writeHubResource} from '../../platform/data-resource.mjs';
import {CENTER_KEYS,readCenterResource,writeCenterResource} from '../../platform/center-resource.mjs';
import {readSettingsTab,writeSettingsTab} from '../../platform/settings-resource.mjs';
export function readResource(url){
  const parsed=new URL(url,'http://localhost');
  const q=parsed.searchParams;
  const pathView=Object.entries(PLATFORM_PATHS).find(([,path])=>path===parsed.pathname.replace(/\/$/,''))?.[0];
  if(!q.has('view')&&!pathView&&parsed.pathname.startsWith('/app/'))throw new Error('La pantalla solicitada no existe.');
  const resource={view:q.get('view')||(q.has('run_id')?'decision-dashboard':pathView||'overview'),caseId:q.get('case_id'),nodeId:q.get('node_id'),runId:q.get('run_id')};
  if(resource.view==='inicio')resource.view='platform-home';
  if(!resource.nodeId&&q.get('dda')==='scheduling_v1')resource.nodeId='logistics_scheduling';
  if(!resource.nodeId&&resource.runId)resource.nodeId='logistics_assignment';
  if(!VIEWS.includes(resource.view))throw new Error('La pantalla solicitada no existe.');
  if(resource.nodeId&&!NODES.includes(resource.nodeId))throw new Error('La decisión solicitada no existe.');
  for(const id of [resource.caseId,resource.runId])if(id&&!UUID.test(id))throw new Error('El enlace contiene un identificador inválido.');
  if(resource.view!=='decision-dashboard')resource.runId=null;
  if(resource.view==='platform-data')resource.hub=readHubResource(parsed);
  if(resource.view==='platform-decisions')resource.center=readCenterResource(parsed);
  if(resource.view==='settings')resource.settingsTab=readSettingsTab(parsed);
  return resource;
}
export function resourceUrl(url,resource){
  const next=new URL(url,'http://localhost');
  for(const key of ['view','case_id','node_id','run_id','dda','settings_tab',...HUB_KEYS,...CENTER_KEYS])next.searchParams.delete(key);
  next.pathname=PLATFORM_PATHS[resource.view]||'/app';
  next.searchParams.set('view',resource.view);
  if(resource.caseId&&['overview','logistics-overview','logistics-data','logistics-map','logistics-config','decision-dashboard','traceability','library'].includes(resource.view))next.searchParams.set('case_id',resource.caseId);
  if(['logistics-config','decision-dashboard'].includes(resource.view)&&resource.nodeId)next.searchParams.set('node_id',resource.nodeId);
  if(resource.view==='decision-dashboard'&&resource.runId)next.searchParams.set('run_id',resource.runId);
  if(resource.view==='platform-data')writeHubResource(next,resource.hub);
  if(resource.view==='platform-decisions')writeCenterResource(next,resource.center);
  if(resource.view==='settings')writeSettingsTab(next,resource.settingsTab);
  return next;
}
export function runDecisionState(run,decisionCase,nodeId){
  const node=decisionCase?.nodes?.[nodeId]||{};
  if(node.status==='stale'&&String(node.approved_run_id||node.run_id)===String(run.id))return 'stale';
  if(run.superseded_at)return 'superseded';
  if(String(node.approved_run_id||'')===String(run.id))return 'approved';
  return 'review';
}

// Persisted run lineage takes precedence over the currently selected workspace.
export function runContext(run,fallbackNodeId=null){
  const result=run?.result_json||{},stored=run?.configuration_json||{};
  const meta=result.decision_case||stored.decision_case||{};
  const schema=result.schema_version||run?.schema_version;
  return {
    caseId:result.decision_case?.case_id||run?.decision_case_id||stored.decision_case?.case_id||null,
    nodeId:run?.node_id||meta.node_id||(schema==='scheduling_v1'?'logistics_scheduling':fallbackNodeId||'logistics_assignment'),
    configuration:result.configuration||stored,
    ordersId:result.inputs?.orders?.dataset_id||run?.orders_dataset_id||run?.dataset_id||null,
    fleetId:result.inputs?.fleet?.dataset_id||run?.fleet_dataset_id||null,
  };
}
