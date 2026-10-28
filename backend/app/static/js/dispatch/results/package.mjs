/** Schema-aware reader. No metric/plan/date producer lives in a consumer. */
import {api,post} from '../shared.mjs';
export const RESULT_SCHEMAS=new Set(['transport_plan_v1','day_scheduling_v1']);
export function assertBinding(value,binding){
  if(value?.run_id!==binding.run_id||value?.result_fingerprint!==binding.result_fingerprint)throw new Error('RESULT_FINGERPRINT_MISMATCH');
  return value;
}
export function readPackage(run,response){
  const p=response?.package||run.result_json;
  if(!RESULT_SCHEMAS.has(p?.result_schema)||p.result_schema_version!==1||p.package_version!==1)throw new Error('UNSUPPORTED_RESULT_SCHEMA');
  const binding={run_id:run.id,result_fingerprint:run.result_fingerprint};
  assertBinding({run_id:p.decision?.run_id,result_fingerprint:p.fingerprints?.result_fingerprint},binding);
  if(response){assertBinding(response.provenance,binding);assertBinding(response.approval_overlay,binding);}
  const expected=p.result_schema==='transport_plan_v1'?['plan','demand','resources','alternatives','exceptions','evidence']:['schedule','trips','resources','service','exceptions','evidence'];
  if(expected.some(id=>!p.details?.some(d=>d.dataset_id===id)))throw new Error('RESULT_DATASET_MISSING');
  return p;
}
export class PackageClient{
  constructor(run,{signal}={}){this.binding=Object.freeze({run_id:run.id,result_fingerprint:run.result_fingerprint});this.signal=signal;this.selectionGeneration=0;}
  url(path,query={}){const params=new URLSearchParams(query);params.set('expected_result_fingerprint',this.binding.result_fingerprint);return '/api/runs/'+encodeURIComponent(this.binding.run_id)+'/'+path+'?'+params;}
  async get(path,query={},options={}){const data=await api(this.url(path,query),{signal:this.signal,...options});assertBinding(data.provenance||data.context?.provenance,this.binding);return data;}
  result(){return this.get('result');}
  page(dataset,offset=0){return this.get('details/'+encodeURIComponent(dataset),{offset,limit:25});}
  async select(entity_type,entity_id){
    const generation=++this.selectionGeneration;
    this.selectionController?.abort();this.selectionController=new AbortController();
    const selected=Object.freeze({...this.binding,entity_type,entity_id});
    const data=await this.get('entities/'+encodeURIComponent(entity_type)+'/'+encodeURIComponent(entity_id),{},{signal:AbortSignal.any([this.signal||new AbortController().signal,this.selectionController.signal])});
    if(generation!==this.selectionGeneration)throw new DOMException('Selection superseded','AbortError');
    if(data.entity?.entity_type!==entity_type||data.entity?.entity_id!==entity_id)throw new Error('SELECTED_ENTITY_MISMATCH');
    return {selected,data};
  }
  clearSelection(){this.selectionGeneration++;this.selectionController?.abort();}
  context(mode,selected,alternative_ids=[]){
    if(selected)assertBinding(selected,this.binding);
    const query={mode,...(selected?{entity_type:selected.entity_type,entity_id:selected.entity_id}:{})};
    const params=new URLSearchParams(query);alternative_ids.forEach(id=>params.append('alternative_ids',id));
    return this.get('decision-context',params,{});
  }
  async ask(context,question,turn_id){
    assertBinding(context.provenance,this.binding);
    const intent={schema_version:'decision_intent_v2',provenance:this.binding,context_version:1,context_hash:context.context_hash,mode:context.mode,question,
      selected_entity:context.selected_entity,selected_alternative_ids:context.selected_alternative_ids,evidence_hashes:context.selected_evidence_refs.map(r=>r.content_sha256)};
    const data=await post(this.url('copilot'),{turn_id,intent},{signal:this.signal});assertBinding(data.provenance,this.binding);
    if(data.context_hash!==context.context_hash)throw new Error('CONTEXT_MISMATCH');return data;
  }
}

/** Read certified fields only; formatting ratios into percent is presentation. */
export function executiveKpis(p){
  const m=p.metrics;
  return p.result_schema==='transport_plan_v1'?[
    ['total_cost','Costo recomendado',m.total_cost,'money'],['trip_count','Viajes',m.trip_count,'count'],
    ['demand_coverage','Cobertura de demanda',m.demand_coverage.ratio,'ratio'],['capacity_utilization','Utilización de capacidad',m.capacity_utilization.weighted_ratio,'ratio'],
    ['resources_used','Recursos utilizados',m.resources_used,'count'],
  ]:[['scheduled_trips','Viajes programados',m.scheduled_trips.scheduled,'count'],['on_time_ratio','Cumplimiento esperado',m.on_time_ratio,'ratio'],
    ['average_schedule_margin_days','Margen promedio',m.average_schedule_margin_days,'days'],['peak_dispatch_day','Día pico',m.peak_dispatch_day?.date??null,'date'],['exception_count','Excepciones',m.exception_count,'count']];
}

export function sankeyLayout(projection){
  const columns=['DESTINATION','TRIP','RESOURCE'];
  const height=Math.max(200,...columns.map(type=>projection.nodes.filter(n=>n.type===type).length*56+40));
  const nodes=projection.nodes.map(n=>({...n,x:40+columns.indexOf(n.type)*310,y:40+projection.nodes.filter(a=>a.type===n.type).findIndex(a=>a.id===n.id)*56}));
  const max=Math.max(1,...projection.links.map(l=>Number(l.value)));
  return {height,nodes,links:projection.links.map(l=>({...l,width:Math.max(1,Number(l.value)/max*24)}))};
}
export function ganttLayout(projection){
  const time=date=>Date.parse(date+'T00:00:00Z');
  const start=Math.min(time(projection.planning_start),...projection.items.map(i=>time(i.dispatch_date)));
  const end=Math.max(time(projection.planning_end),...projection.items.flatMap(i=>[time(i.arrival_date),...(i.occupancy_end?[time(i.occupancy_end)]:[])]));
  const scale=date=>(time(date)-start)/Math.max(86400000,end-start)*720;
  let cursor=40;const positions=new Map();
  const rows=projection.rows.map(row=>{
    const items=projection.items.filter(item=>item.resource_id===row.resource_id);
    items.forEach((item,index)=>positions.set(item.trip_id,cursor+10+index*68));
    const projected={...row,y:cursor+26};cursor+=Math.max(1,items.length)*68+24;return projected;
  });
  // A display subrow per Trip keeps concurrent trips distinguishable. These
  // are pixel positions, never invented vehicle/unit assignments or occupancy.
  return {start,end,rows,height:Math.max(180,cursor+40),items:projection.items.map(i=>({...i,x:scale(i.dispatch_date),endX:scale(i.occupancy_end??i.arrival_date),y:positions.get(i.trip_id)}))};
}
