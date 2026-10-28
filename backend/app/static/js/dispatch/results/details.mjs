/** Tables project certified rows. Search/filter/sort are explicitly page-scoped. */
import {esc} from '../shared.mjs';
export const valueAt=(row,path)=>path.split('.').reduce((v,key)=>v?.[key],row);
export function display(value,format='text'){
  if(value==null)return 'No informado';
  if(format==='ratio')return new Intl.NumberFormat('es-AR',{style:'percent',maximumFractionDigits:2}).format(value);
  if(format==='ratios')return Object.entries(value).filter(([,v])=>v!=null).map(([key,v])=>key+': '+display(v,'ratio')).join(' · ')||'No informado';
  if(format==='money')return value.amount==null?'No informado':new Intl.NumberFormat('es-AR',{style:'currency',currency:value.currency}).format(value.amount);
  if(Array.isArray(value))return value.map(v=>typeof v==='object'?JSON.stringify(v):String(v)).join(' · ')||'Sin elementos';
  if(typeof value==='object')return Object.entries(value).filter(([,v])=>v!=null).map(([k,v])=>k+': '+(typeof v==='object'?JSON.stringify(v):String(v))).join(' · ')||'No informado';
  return String(value);
}
export function columnsFor(dataset,p){
  const d=p.context.primary_dimension;
  const timing=[['dispatch_date','Salida'],['expected_arrival_date','Llegada'],['delivery_due_date','Fecha objetivo'],['schedule_margin_days','Margen'],['status','Estado']];
  const columns={
    plan:[['trip_id','Viaje'],['orders','Órdenes'],['origin_id','Origen'],['destination_id','Destino'],['resource_id','Recurso'],['resource_source','Origen del recurso'],['total_load','Carga'],['guaranteed_capacity','Capacidad garantizada'],['utilization','Utilización'],['estimated_cost','Costo','money']],
    demand:[['entity_id','Orden'],['facts.priority','Prioridad'],['facts.requested_'+d,'Solicitado · '+d],['facts.assigned_'+d,'Asignado · '+d],['facts.trip_ids','Viajes'],['facts.resource_ids','Recursos'],['facts.coverage_ratio','Cobertura','ratio'],['facts.status','Estado'],['reason_refs','Evidencia']],
    resources:p.result_schema==='transport_plan_v1'?[['resource_id','Recurso'],['resource_source','Origen'],['services_available','Servicios disponibles'],['services_used','Usados'],['services_remaining','Restantes'],['availability_source','Fuente de disponibilidad'],['units_available','Unidades propias'],['trip_count','Viajes'],['published_capacity','Capacidad garantizada'],['total_distance_km','Distancia · km'],['total_cost','Costo total','money'],['weighted_utilization','Utilización ponderada']]:[['resource_id','Recurso'],['resource_source','Origen'],['units_available','Unidades'],['occupancy','Ocupación · fin exclusivo'],['dispatch_events','Despachos']],
    schedule:[['trip_id','Viaje'],['resource_id','Recurso'],['resource_source','Origen'],...timing,['outbound_days','Tránsito · días'],['cycle_days','Ciclo · días'],['available_again','Disponible nuevamente'],['reason_codes','Razones']],
    trips:[['entity_id','Viaje'],['facts.order_ids','Órdenes'],['facts.origin_id','Origen'],['facts.destination_id','Destino'],['facts.resource_id','Recurso'],['facts.total_load_'+d,'Carga · '+d],['facts.guaranteed_capacity_'+d,'Capacidad · '+d],['facts.dispatch_date','Salida'],['facts.expected_arrival_date','Llegada'],['facts.status','Estado']],
    service:[['trip_id','Viaje'],['status','Estado certificado'],['margin_days','Margen · días'],['dispatch_date','Salida'],['arrival_date','Llegada'],['delivery_due_date','Fecha objetivo']],
    exceptions:[['entity_id','Entidad'],['facts.category','Categoría'],['facts.code','Código'],['facts.severity','Severidad'],['facts','Hechos certificados'],['reason_refs','Evidencia']],
    evidence:[['entity_type','Tipo'],['entity_id','Entidad'],['facts','Hechos certificados'],['reason_refs','Referencias de razón']],
  };
  return columns[dataset]||[];
}
export function pageRows(rows,{search='',filter='',sort=null,direction=1}={}){
  const needle=search.toLocaleLowerCase('es');
  const result=rows.filter(r=>(!needle||JSON.stringify(r).toLocaleLowerCase('es').includes(needle))&&(!filter||JSON.stringify(r).includes(filter)));
  if(sort)result.sort((a,b)=>{const scalar=v=>v&&typeof v==='object'&&'amount'in v?v.amount:v;const x=scalar(valueAt(a,sort)),y=scalar(valueAt(b,sort));if(x==null)return y==null?0:1;if(y==null)return -1;
    const numeric=v=>typeof v==='number'||(typeof v==='string'&&/^-?\d+(\.\d+)?$/.test(v));
    const compareDecimal=(a,b)=>{const negativeA=String(a).startsWith('-'),negativeB=String(b).startsWith('-');if(negativeA!==negativeB)return negativeA?-1:1;
      const [ai,af='']=String(a).replace(/^-/,'').split('.'),[bi,bf='']=String(b).replace(/^-/,'').split('.'),sign=negativeA?-1:1;
      const left=ai.replace(/^0+(?=\d)/,''),right=bi.replace(/^0+(?=\d)/,'');
      if(left.length!==right.length)return sign*(left.length<right.length?-1:1);if(left!==right)return sign*(left<right?-1:1);
      const length=Math.max(af.length,bf.length),aa=af.padEnd(length,'0'),bb=bf.padEnd(length,'0');return sign*(aa===bb?0:aa<bb?-1:1);};
    return direction*(numeric(x)&&numeric(y)?compareDecimal(x,y):String(x).localeCompare(String(y),'es',{numeric:true}));});
  return result;
}
export function tableMarkup(dataset,p,page,options={}){
  const columns=columnsFor(dataset,p),rows=pageRows(page.rows,options);
  return '<div class="dispatch-table-wrap" role="region" tabindex="0" aria-label="Tabla desplazable de '+esc(dataset)+'"><table class="assignment-v2__table ultimate-results__table"><caption>'+esc(dataset)+' · filas publicadas de esta página</caption><thead><tr>'+columns.map(([key,label])=>'<th scope="col" aria-sort="'+(options.sort===key?(options.direction===1?'ascending':'descending'):'none')+'"><button type="button" class="d-button d-button--secondary" data-sort="'+esc(key)+'">'+esc(label)+'</button></th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+columns.map(([key,,format],index)=>{
    const value=display(valueAt(row,key),format),id=row.trip_id||(row.entity_type==='TRIP'?row.entity_id:null);
    return '<'+(index===0?'th scope="row"':'td')+'>'+(index===0&&id?'<button type="button" class="d-button d-button--secondary" data-entity-type="TRIP" data-entity-id="'+esc(id)+'">'+esc(value)+'</button>':esc(value))+'</'+(index===0?'th':'td')+'>';
  }).join('')+'</tr>').join('')+'</tbody></table></div>'+(rows.length?'':'<p role="status">Sin filas para esta selección.</p>');
}
export function factsMarkup(value){
  return '<dl class="ultimate-results__facts">'+Object.entries(value||{}).map(([key,v])=>'<div><dt>'+esc(key)+'</dt><dd>'+esc(display(v))+'</dd></div>').join('')+'</dl>';
}
export function alternativesMarkup(p,status){
  return '<p>'+esc(status)+'</p>'+p.alternatives.map(a=>'<article class="dispatch-panel ultimate-results__panel"><h3>'+esc(a.policy)+'</h3>'+factsMarkup({
    'Alternativa publicada':a.alternative_id,'Costo':display({amount:a.metrics.total_cost,currency:p.context.currency_policy.currency},'money'),
    'Viajes':a.metrics.trip_count,'Cobertura':display(a.metrics.coverage_ratio,'ratio'),'Participación propia':display(a.metrics.own_trip_ratio,'ratio'),
    'Diferencia de costo certificada':a.difference_vs_recommended.cost_delta,'Diferencia de viajes':a.difference_vs_recommended.trip_delta,
    'Diferencia de participación propia':a.difference_vs_recommended.own_share_delta,'Diferencias materiales':a.material_differences})
    +'<button type="button" class="d-button d-button--secondary" data-compare="'+esc(a.alternative_id)+'">Comparar con la recomendación</button></article>').join('');
}
