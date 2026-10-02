import {esc,num,pct,date,vehicle} from './shared.mjs';

function poolId(value){
  return value.fleet_pool_id||value.vehicle_type||'legacy';
}

export function render(root,result){
  const selected=result.scenarios.selected;
  const metrics=selected.metrics;
  const exceptions=result.exceptions||[];
  const outsourced=selected.trips.filter(trip=>trip.ownership==='third_party');
  const includedAnomalies=(result.inputs?.anomalies||[]).filter(item=>item.decision==='include');
  const reviewCount=(exceptions.length?1:0)+(outsourced.length?1:0)+(includedAnomalies.length?1:0);

  root.innerHTML=
    '<div class="dispatch-section-heading">'
      +'<div><span class="dispatch-kicker">CONTROL</span><h2>Revisar antes de ejecutar</h2>'
      +'<p>Mostramos sólo los puntos que pueden requerir validación humana antes de usar la distribución.</p></div>'
      +'<span class="dispatch-review-count '+(reviewCount?'is-warning':'is-good')+'">'
        +(reviewCount?num(reviewCount)+' punto'+(reviewCount===1?'':'s')+' a revisar':'Sin alertas críticas')
      +'</span>'
    +'</div>'
    +'<div class="dispatch-review-cards" data-review-cards></div>';

  const container=root.querySelector('[data-review-cards]');
  const cards=[];

  if(exceptions.length){
    cards.push(
      '<article class="dispatch-review-card is-warning">'
        +'<div><span class="dispatch-review-icon">!</span><div><strong>'+num(exceptions.length)+' orden'+(exceptions.length===1?'':'es')+' fuera de SLA</strong>'
        +'<p>La distribución recomendada no logra cumplir el plazo de estas órdenes bajo las restricciones vigentes.</p></div></div>'
        +'<details><summary>Ver órdenes</summary><div class="dispatch-table-wrap"><table><thead><tr><th>Orden</th><th>Prioridad</th><th>Plazo</th><th>Llegada</th><th>Tardanza</th></tr></thead><tbody>'
        +exceptions.map(item=>'<tr><td>'+esc(item.order_id)+'</td><td>'+esc(item.priority)+'</td><td>'+date(item.deadline)+'</td><td>'+date(item.arrival_date)+'</td><td>'+num(item.late_days)+' días</td></tr>').join('')
        +'</tbody></table></div></details>'
      +'</article>'
    );
  }

  if(outsourced.length){
    const pools=[...new Set(outsourced.map(poolId))];
    cards.push(
      '<article class="dispatch-review-card">'
        +'<div><span class="dispatch-review-icon">↗</span><div><strong>'+num(outsourced.length)+' viaje'+(outsourced.length===1?'':'s')+' tercerizado'+(outsourced.length===1?'':'s')+'</strong>'
        +'<p>'+pct(metrics.outsourced_weight_share)+' del peso se asigna a flota externa. Validá disponibilidad comercial antes de ejecutar.</p></div></div>'
        +'<details><summary>Ver pools tercerizados</summary><p>'+pools.map(esc).join(' · ')+'</p></details>'
      +'</article>'
    );
  }

  if(includedAnomalies.length){
    cards.push(
      '<article class="dispatch-review-card">'
        +'<div><span class="dispatch-review-icon">i</span><div><strong>'+num(includedAnomalies.length)+' anomalía'+(includedAnomalies.length===1?'':'s')+' incluida'+(includedAnomalies.length===1?'':'s')+'</strong>'
        +'<p>Estas filas se incluyeron por una decisión explícita durante la configuración.</p></div></div>'
        +'<details><summary>Ver detalle</summary>'
        +includedAnomalies.map(item=>'<p><strong>'+esc(item.order_id)+'</strong> · '+esc(item.detail)+'</p>').join('')
        +'</details>'
      +'</article>'
    );
  }

  if(!cards.length){
    cards.push(
      '<article class="dispatch-review-card is-good">'
        +'<div><span class="dispatch-review-icon">✓</span><div><strong>La distribución no presenta excepciones críticas</strong>'
        +'<p>Todas las órdenes quedan dentro del SLA encontrado y no hay anomalías incluidas ni tercerización que requiera revisión adicional.</p></div></div>'
      +'</article>'
    );
  }

  container.innerHTML=cards.join('');
}
