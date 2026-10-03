import {esc,num,pct,date} from './shared.mjs';

function resourceId(value){
  return value.vehicle_id||value.fleet_pool_id||value.vehicle_type||'legacy';
}

function assignmentReview(root,result){
  const selected=result.scenarios.selected;
  const metrics=selected.metrics;
  const outsourced=selected.trips.filter(trip=>trip.ownership==='third_party');
  const includedAnomalies=(result.inputs?.anomalies||[]).filter(item=>item.decision==='include');
  const reviewCount=(outsourced.length?1:0)+(includedAnomalies.length?1:0);

  root.innerHTML=
    '<div class="dispatch-section-heading">'
      +'<div><span class="dispatch-kicker">VALIDACIÓN HUMANA</span><h2>Revisar antes de aprobar</h2>'
      +'<p>Estos son los puntos de Assignment que conviene validar antes de desbloquear Planificación.</p></div>'
      +'<span class="dispatch-review-count '+(reviewCount?'is-warning':'is-good')+'">'
        +(reviewCount?num(reviewCount)+' punto'+(reviewCount===1?'':'s')+' a revisar':'Sin observaciones críticas')
      +'</span>'
    +'</div>'
    +'<div class="dispatch-review-cards" data-review-cards></div>';

  const cards=[];
  if(outsourced.length){
    const resources=[...new Set(outsourced.map(resourceId))].sort();
    cards.push(
      '<article class="dispatch-review-card">'
        +'<div><span class="dispatch-review-icon">↗</span><div><strong>'+num(outsourced.length)+' viaje'+(outsourced.length===1?'':'s')+' asignado'+(outsourced.length===1?'':'s')+' a terceros</strong>'
        +'<p>'+pct(metrics.outsourced_weight_share)+' del peso queda en flota externa. Confirmá disponibilidad comercial antes de aprobar Assignment.</p></div></div>'
        +'<details><summary>Ver vehículos tercerizados</summary><p>'+resources.map(esc).join(' · ')+'</p></details>'
      +'</article>'
    );
  }

  if(includedAnomalies.length){
    cards.push(
      '<article class="dispatch-review-card">'
        +'<div><span class="dispatch-review-icon">i</span><div><strong>'+num(includedAnomalies.length)+' anomalía'+(includedAnomalies.length===1?'':'s')+' incluida'+(includedAnomalies.length===1?'':'s')+'</strong>'
        +'<p>Estas órdenes de tamaño atípico fueron incluidas por una decisión explícita en la configuración.</p></div></div>'
        +'<details><summary>Ver detalle</summary>'
        +includedAnomalies.map(item=>'<p><strong>'+esc(item.order_id)+'</strong> · '+esc(item.detail)+'</p>').join('')
        +'</details>'
      +'</article>'
    );
  }

  if(!cards.length){
    cards.push(
      '<article class="dispatch-review-card is-good">'
        +'<div><span class="dispatch-review-icon">✓</span><div><strong>Assignment no presenta observaciones críticas</strong>'
        +'<p>La carga completa está asignada respetando capacidad, site, ruta y unidades enteras. Las fechas se validarán recién en Planificación.</p></div></div>'
      +'</article>'
    );
  }

  root.querySelector('[data-review-cards]').innerHTML=cards.join('');
}

function legacyReview(root,result){
  const selected=result.scenarios.selected;
  const metrics=selected.metrics;
  const exceptions=result.exceptions||[];
  const outsourced=selected.trips.filter(trip=>trip.ownership==='third_party');
  const includedAnomalies=(result.inputs?.anomalies||[]).filter(item=>item.decision==='include');
  const reviewCount=(exceptions.length?1:0)+(outsourced.length?1:0)+(includedAnomalies.length?1:0);

  root.innerHTML=
    '<div class="dispatch-section-heading">'
      +'<div><span class="dispatch-kicker">CONTROL HISTÓRICO</span><h2>Revisión de la corrida temporal</h2>'
      +'<p>Esta evidencia pertenece al motor Dispatch anterior y se conserva para trazabilidad.</p></div>'
      +'<span class="dispatch-review-count '+(reviewCount?'is-warning':'is-good')+'">'+(reviewCount?num(reviewCount)+' punto'+(reviewCount===1?'':'s')+' a revisar':'Sin alertas críticas')+'</span>'
    +'</div><div class="dispatch-review-cards" data-review-cards></div>';

  const cards=[];
  if(exceptions.length){
    cards.push(
      '<article class="dispatch-review-card is-warning"><div><span class="dispatch-review-icon">!</span><div><strong>'+num(exceptions.length)+' orden'+(exceptions.length===1?'':'es')+' fuera de SLA</strong><p>Resultado histórico del modelo temporal.</p></div></div>'
      +'<details><summary>Ver órdenes</summary><div class="dispatch-table-wrap"><table><thead><tr><th>Orden</th><th>Plazo</th><th>Llegada</th><th>Tardanza</th></tr></thead><tbody>'
      +exceptions.map(item=>'<tr><td>'+esc(item.order_id)+'</td><td>'+date(item.deadline)+'</td><td>'+date(item.arrival_date)+'</td><td>'+num(item.late_days)+' días</td></tr>').join('')
      +'</tbody></table></div></details></article>'
    );
  }
  if(outsourced.length){
    cards.push('<article class="dispatch-review-card"><div><span class="dispatch-review-icon">↗</span><div><strong>'+num(outsourced.length)+' viajes tercerizados</strong><p>'+pct(metrics.outsourced_weight_share||0)+' del peso fue asignado a flota externa.</p></div></div></article>');
  }
  if(!cards.length){
    cards.push('<article class="dispatch-review-card is-good"><div><span class="dispatch-review-icon">✓</span><div><strong>Sin alertas críticas registradas</strong><p>Corrida histórica conservada sin cambios.</p></div></div></article>');
  }
  root.querySelector('[data-review-cards]').innerHTML=cards.join('');
}

export function render(root,result){
  if(result.schema_version==='assignment_v1'){
    assignmentReview(root,result);
    return;
  }
  legacyReview(root,result);
}
