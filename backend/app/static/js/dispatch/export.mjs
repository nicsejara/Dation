import {csv,download,vehicle} from './shared.mjs';

function assignmentRows(result){
  const headers=[
    'Viaje','Vehicle ID','Tipo de vehículo','Propiedad','Proveedor',
    'Site base','Origen','Destino','Orden','Producto',
    'Unidades asignadas','Kg asignados','Carga total viaje (kg)',
    'Capacidad viaje (kg)','Utilización viaje',
    'Costo estimado viaje','CO2 estimado viaje'
  ];
  const rows=(result.scenarios?.selected?.trips||[]).flatMap(trip=>
    (trip.loads||[]).map(load=>[
      trip.trip_id,
      trip.vehicle_id||trip.fleet_pool_id||'',
      vehicle(trip.vehicle_type),
      trip.ownership==='own'?'Propio':'Tercerizado',
      trip.provider_name||'',
      trip.base_site||trip.base_location||'',
      trip.origin,
      trip.destination,
      load.order_id,
      load.product||'',
      load.units,
      load.kg,
      trip.load_kg??'',
      trip.capacity_kg??'',
      trip.utilization??'',
      trip.estimated_cost??trip.cost??'',
      trip.estimated_co2_kg??trip.co2_kg??'',
    ])
  );
  return {
    filename:'assignment-recomendada.csv',
    rows:[headers,...rows],
  };
}

function schedulingRows(result){
  const headers=[
    'Viaje','Vehicle ID','Tipo de vehículo','Origen','Destino',
    'Ready date','Salida','Llegada','Recurso disponible',
    'Días de tránsito','Días de ciclo','Espera (días)',
    'Fecha objetivo','Orden','Producto','Unidades','Kg'
  ];
  const rows=(result.scenarios?.selected?.trips||[]).flatMap(trip=>
    (trip.loads||[]).map(load=>[
      trip.trip_id,
      trip.vehicle_id,
      vehicle(trip.vehicle_type),
      trip.origin,
      trip.destination,
      trip.ready_date,
      trip.dispatch_date,
      trip.arrival_date,
      trip.resource_available_again,
      trip.transit_days,
      trip.cycle_days,
      trip.wait_days,
      trip.delivery_due_date||'',
      load.order_id,
      load.product||'',
      load.units,
      load.kg,
    ])
  );
  return {
    filename:'planificacion-recomendada.csv',
    rows:[headers,...rows],
  };
}

function legacyRows(result){
  const headers=[
    'Viaje','Salida','Llegada','Recurso disponible','Días de ciclo',
    'Origen','Destino','Recurso','Camión','Propiedad',
    'Orden','Producto','Unidades','Kg','Costo del viaje','CO2 del viaje'
  ];
  const rows=(result.scenarios?.selected?.trips||[]).flatMap(trip=>
    (trip.loads||[]).map((load,index)=>[
      trip.trip_id,
      trip.dispatch_date||'',
      trip.arrival_date||'',
      trip.resource_available_again||'',
      trip.cycle_days||'',
      trip.origin,
      trip.destination,
      trip.fleet_pool_id||trip.vehicle_id||trip.vehicle_type||'',
      vehicle(trip.vehicle_type),
      trip.ownership==='own'?'Propio':'Tercerizado',
      load.order_id,
      load.product||'',
      load.units,
      load.kg,
      index===0?(trip.cost??trip.estimated_cost??''):'',
      index===0?(trip.co2_kg??trip.estimated_co2_kg??''):'',
    ])
  );
  return {
    filename:'distribucion-recomendada.csv',
    rows:[headers,...rows],
  };
}

export function exportDecision(result){
  if(!result||!result.schema_version){
    throw new Error('La corrida no contiene un resultado exportable.');
  }

  const payload=result.schema_version==='assignment_v1'
    ?assignmentRows(result)
    :result.schema_version==='scheduling_v1'
      ?schedulingRows(result)
      :legacyRows(result);

  if(payload.rows.length<=1){
    throw new Error('La decisión no contiene filas para exportar.');
  }

  download(
    payload.filename,
    csv(payload.rows),
    'text/csv;charset=utf-8',
  );
  return payload.filename;
}

export function exportDecisionJson(result,runId='decision'){
  if(!result){
    throw new Error('La corrida no contiene un resultado exportable.');
  }
  const name='dation-'+String(runId).slice(0,8)+'.json';
  download(
    name,
    JSON.stringify(result,null,2),
    'application/json;charset=utf-8',
  );
  return name;
}
