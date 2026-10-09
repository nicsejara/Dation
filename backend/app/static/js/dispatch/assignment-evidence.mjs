import {esc,num,money,pct,vehicle} from './shared.mjs';
import {
  getAssignmentTrips,
  getAssignmentVehicles,
  getAssignmentOrders,
} from './assignment-dashboard-selectors.mjs?v=assignment-dashboard-phase2';

function ownershipBadge(ownership){
  const thirdParty=ownership==='third_party';
  return '<span class="assignment-evidence__badge '+(thirdParty?'is-third-party':'is-own')+'">'
    +(thirdParty?'Tercerizada':'Propia')
  +'</span>';
}

function utilizationCell(value){
  const safe=Number.isFinite(Number(value))?Math.max(0,Math.min(1,Number(value))):null;
  if(safe==null)return '—';
  return '<div class="assignment-evidence__util">'
    +'<div class="assignment-evidence__util-track" aria-hidden="true"><span style="width:'+Math.round(safe*100)+'%"></span></div>'
    +'<strong>'+pct(safe)+'</strong>'
  +'</div>';
}

function tripRows(trips){
  return trips.map(trip=>
    '<tr>'
      +'<td><button type="button" class="assignment-evidence__trip-link" data-trip-detail-button="'+esc(trip.trip_id)+'">'+esc(trip.trip_id)+'</button></td>'
      +'<td><strong>'+esc(trip.resource_id)+'</strong><small>'+esc(vehicle(trip.vehicle_type||''))+'</small></td>'
      +'<td>'+esc(trip.origin||'—')+' → '+esc(trip.destination||'—')+'</td>'
      +'<td>'+num(trip.load_kg,0)+' kg</td>'
      +'<td>'+num(trip.capacity_kg,0)+' kg</td>'
      +'<td>'+utilizationCell(trip.utilization)+'</td>'
      +'<td>'+num(trip.order_count)+'</td>'
      +'<td>'+ownershipBadge(trip.ownership)+'</td>'
    +'</tr>'
  ).join('');
}

function vehicleView(vehicles){
  if(!vehicles.length)return '<p class="assignment-evidence__empty">No hay vehículos para mostrar.</p>';
  if(vehicles.length===1){
    const item=vehicles[0];
    return '<article class="assignment-evidence__single-vehicle">'
      +'<span class="dispatch-kicker">RESUMEN DE VEHÍCULO</span>'
      +'<h3>'+esc(item.id)+' concentra '+(item.load_share==null?'la carga asignada':pct(item.load_share)+' de la carga')+'</h3>'
      +'<p>'+num(item.trips)+' viaje'+(item.trips===1?'':'s')+' · '+num(item.load_kg,0)+' kg · '+(item.utilization==null?'utilización no informada':pct(item.utilization)+' de utilización media')+'</p>'
      +'<div class="assignment-evidence__single-meta">'
        +'<span><small>Órdenes</small><strong>'+num(item.orders)+'</strong></span>'
        +'<span><small>Tipo</small><strong>'+esc(vehicle(item.vehicle_type||''))+'</strong></span>'
        +'<span><small>Flota</small><strong>'+(item.ownership==='third_party'?'Tercerizada':'Propia')+'</strong></span>'
      +'</div>'
    +'</article>';
  }
  return '<div class="dispatch-table-wrap assignment-evidence__table-wrap">'
    +'<table class="assignment-evidence__table"><thead><tr><th>Vehículo</th><th>Viajes</th><th>Carga total</th><th>Utilización media</th><th>Órdenes</th><th>% de carga</th><th>Flota</th></tr></thead><tbody>'
    +vehicles.map(item=>
      '<tr>'
        +'<td><strong>'+esc(item.id)+'</strong><small>'+esc(vehicle(item.vehicle_type||''))+'</small></td>'
        +'<td>'+num(item.trips)+'</td>'
        +'<td>'+num(item.load_kg,0)+' kg</td>'
        +'<td>'+(item.utilization==null?'—':pct(item.utilization))+'</td>'
        +'<td>'+num(item.orders)+'</td>'
        +'<td>'+(item.load_share==null?'—':pct(item.load_share))+'</td>'
        +'<td>'+ownershipBadge(item.ownership)+'</td>'
      +'</tr>'
    ).join('')
    +'</tbody></table></div>';
}

function orderFlags(order){
  const flags=[];
  if(order.consolidated)flags.push('<span class="assignment-evidence__order-flag">Consolidada</span>');
  if(order.split)flags.push('<span class="assignment-evidence__order-flag is-review">Dividida</span>');
  if(order.outsourced)flags.push('<span class="assignment-evidence__order-flag is-third-party">Tercerizada</span>');
  return flags.length?flags.join(''):'<span class="assignment-evidence__order-flag">Sin observaciones</span>';
}

function orderView(orders){
  if(!orders.length)return '<p class="assignment-evidence__empty">No hay detalle por orden disponible en esta corrida.</p>';
  return '<div class="dispatch-table-wrap assignment-evidence__table-wrap">'
    +'<table class="assignment-evidence__table"><thead><tr><th>Orden</th><th>Producto</th><th>Unidades</th><th>Kg</th><th>Viaje/s</th><th>Vehículo/s</th><th>Estado</th></tr></thead><tbody>'
    +orders.map(order=>
      '<tr>'
        +'<td><strong>'+esc(order.order_id)+'</strong></td>'
        +'<td>'+esc(order.product)+'</td>'
        +'<td>'+num(order.units)+'</td>'
        +'<td>'+num(order.kg,0)+' kg</td>'
        +'<td>'+order.trip_ids.map(esc).join('<br>')+'</td>'
        +'<td>'+order.vehicle_ids.map(esc).join('<br>')+'</td>'
        +'<td><div class="assignment-evidence__order-flags">'+orderFlags(order)+'</div></td>'
      +'</tr>'
    ).join('')
    +'</tbody></table></div>';
}

function detailMetric(label,value){
  return '<div><small>'+esc(label)+'</small><strong>'+esc(value)+'</strong></div>';
}

function renderTripDetail(root,trip){
  if(!trip){
    root.innerHTML='<div class="assignment-evidence__detail-empty"><strong>Seleccioná un viaje</strong><p>Podés abrir cualquier fila para inspeccionar vehículo, ruta, carga y órdenes.</p></div>';
    return;
  }
  const cost=trip.estimated_cost==null?'':detailMetric('Costo estimado',money(trip.estimated_cost));
  const co2=trip.estimated_co2_kg==null?'':detailMetric('CO₂ estimado',num(trip.estimated_co2_kg,1)+' kg');
  const provider=trip.ownership==='third_party'&&trip.provider_name
    ?'<p class="assignment-evidence__provider"><strong>Proveedor:</strong> '+esc(trip.provider_name)+'</p>'
    :'';
  const loads=Array.isArray(trip.loads)?trip.loads:[];

  root.innerHTML=
    '<div class="assignment-evidence__detail-head">'
      +'<div><span class="dispatch-kicker">DETALLE DEL VIAJE</span><h3>'+esc(trip.trip_id)+'</h3><p>'+esc(trip.origin||'—')+' → '+esc(trip.destination||'—')+'</p></div>'
      +ownershipBadge(trip.ownership)
    +'</div>'
    +'<div class="assignment-evidence__detail-grid">'
      +detailMetric('Vehículo',trip.resource_id)
      +detailMetric('Tipo',vehicle(trip.vehicle_type||''))
      +detailMetric('Carga total',num(trip.load_kg,0)+' kg')
      +detailMetric('Capacidad',num(trip.capacity_kg,0)+' kg')
      +detailMetric('Utilización',pct(trip.utilization))
      +detailMetric('Órdenes',num(trip.order_count))
      +cost+co2
    +'</div>'
    +provider
    +'<div class="assignment-evidence__loads">'
      +'<h4>Órdenes y productos</h4>'
      +(loads.length?loads.map(load=>
        '<article><div><strong>'+esc(load.order_id||'—')+'</strong><span>'+esc(load.product||'Producto no registrado')+'</span></div><div><strong>'+num(load.kg,0)+' kg</strong><small>'+num(load.units)+' unidades</small></div></article>'
      ).join(''):'<p>No hay detalle de carga disponible.</p>')
    +'</div>';
}

export function render(root,result){
  const trips=getAssignmentTrips(result);
  const vehicles=getAssignmentVehicles(result);
  const orders=getAssignmentOrders(result);

  root.innerHTML=
    '<div class="dispatch-section-heading assignment-evidence__heading">'
      +'<div><span class="dispatch-kicker">EVIDENCIA OPERATIVA</span><h2>Asignación propuesta</h2><p>Inspeccioná la recomendación desde el viaje, el vehículo o la orden. La evidencia corresponde únicamente al escenario seleccionado.</p></div>'
      +'<div class="assignment-evidence__tabs" role="tablist" aria-label="Vistas de evidencia">'
        +'<button type="button" role="tab" aria-selected="true" data-evidence-tab="trips">Viajes</button>'
        +'<button type="button" role="tab" aria-selected="false" data-evidence-tab="vehicles">Vehículos</button>'
        +'<button type="button" role="tab" aria-selected="false" data-evidence-tab="orders">Órdenes</button>'
      +'</div>'
    +'</div>'
    +'<section role="tabpanel" data-evidence-panel="trips">'
      +(trips.length
        ?'<div class="dispatch-table-wrap assignment-evidence__table-wrap"><table class="assignment-evidence__table"><thead><tr><th>Viaje</th><th>Vehículo</th><th>Ruta</th><th>Carga</th><th>Capacidad</th><th>Utilización</th><th>Órdenes</th><th>Flota</th></tr></thead><tbody>'+tripRows(trips)+'</tbody></table></div>'
        :'<p class="assignment-evidence__empty">No hay viajes para mostrar.</p>')
      +'<aside class="assignment-evidence__trip-detail" data-trip-detail aria-live="polite"></aside>'
    +'</section>'
    +'<section role="tabpanel" data-evidence-panel="vehicles" hidden>'+vehicleView(vehicles)+'</section>'
    +'<section role="tabpanel" data-evidence-panel="orders" hidden>'+orderView(orders)+'</section>'
    +'<div class="assignment-evidence__boundary"><span aria-hidden="true">i</span><p><strong>Frontera de esta decisión.</strong> Esta decisión distribuye carga y construye viajes. Las fechas y posibles superposiciones se resolverán en Planificación.</p></div>';

  const detail=root.querySelector('[data-trip-detail]');
  renderTripDetail(detail,null);

  root.querySelectorAll('[data-evidence-tab]').forEach(button=>{
    button.addEventListener('click',()=>{
      const target=button.dataset.evidenceTab;
      root.querySelectorAll('[data-evidence-tab]').forEach(item=>item.setAttribute('aria-selected',String(item===button)));
      root.querySelectorAll('[data-evidence-panel]').forEach(panel=>{panel.hidden=panel.dataset.evidencePanel!==target;});
    });
  });

  root.querySelectorAll('[data-trip-detail-button]').forEach(button=>{
    button.addEventListener('click',()=>{
      const trip=trips.find(item=>item.trip_id===button.dataset.tripDetailButton);
      renderTripDetail(detail,trip);
      root.querySelectorAll('[data-trip-detail-button]').forEach(item=>item.setAttribute('aria-current',String(item===button)));
      detail?.scrollIntoView?.({behavior:'smooth',block:'nearest'});
    });
  });
}
