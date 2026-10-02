export function delta(value,reference,direction){
  if(reference==null)return {absolute:null,percent:null,tone:'neutral'};
  const absolute=value-reference;
  return {
    absolute,
    percent:reference===0?null:absolute/Math.abs(reference),
    tone:absolute===0?'neutral':((absolute<0)===(direction==='lower_better')?'good':'bad'),
  };
}

export function changes(result){
  const rows=result.scenarios.selected.order_outcomes;
  return {
    consolidated:rows.filter(x=>x.consolidated).length,
    split:rows.filter(x=>x.split).length,
    postponed:rows.filter(x=>x.postponed_days>0).length,
    outsourced:rows.filter(x=>x.outsourced).length,
    late:rows.filter(x=>x.late_days>0).length,
  };
}

export function samePlan(a,b){
  return Boolean(a?.plan_fingerprint&&a.plan_fingerprint===b?.plan_fingerprint);
}

export function rebalance(weights,key,value){
  const names=Object.keys(weights);
  const others=names.filter(name=>name!==key);
  const remaining=100-value;
  if(!others.length)return {[key]:100};
  const currentTotal=others.reduce((sum,name)=>sum+weights[name],0);
  const raw=others.map((name,index)=>{
    const share=currentTotal
      ?remaining*weights[name]/currentTotal
      :remaining/others.length;
    return {name,index,base:Math.floor(share),fraction:share-Math.floor(share)};
  });
  let missing=remaining-raw.reduce((sum,item)=>sum+item.base,0);
  [...raw]
    .sort((a,b)=>b.fraction-a.fraction||a.index-b.index)
    .slice(0,missing)
    .forEach(item=>{item.base+=1;});
  return {
    ...weights,
    [key]:value,
    ...Object.fromEntries(raw.map(item=>[item.name,item.base])),
  };
}

export function filteredTrips(result,filters={}){
  const late=new Set(
    result.scenarios.selected.order_outcomes
      .filter(outcome=>outcome.late_days>0)
      .flatMap(outcome=>outcome.trip_ids)
  );
  return result.scenarios.selected.trips
    .filter(trip=>
      (!filters.pool||(trip.fleet_pool_id||trip.vehicle_type)===filters.pool)
      &&(!filters.vehicle||trip.vehicle_type===filters.vehicle)
      &&(!filters.route||trip.origin+' → '+trip.destination===filters.route)
      &&(!filters.outsourced||trip.ownership==='third_party')
      &&(!filters.late||late.has(trip.trip_id))
      &&(!filters.search||JSON.stringify(trip).toLocaleLowerCase('es').includes(filters.search.toLocaleLowerCase('es')))
    )
    .sort((a,b)=>filters.sort==='cost'
      ?b.cost-a.cost
      :a.dispatch_date.localeCompare(b.dispatch_date)||a.trip_id.localeCompare(b.trip_id));
}
