import {esc,num,money,pct,date,vehicle,chart,dispose,csv,download} from './shared.mjs';
import {changes,filteredTrips} from './selectors.mjs';

function poolId(value){return value.fleet_pool_id||value.vehicle_type||'legacy';}
function baseLabel(value){
  if(value.base_location==='*')return 'cualquier origen';
  return value.base_location||'base no informada';
}
function poolLabel(value){
  return `${vehicle(value.vehicle_type)} · ${baseLabel(value)} · ${poolId(value)}`;
}
function nextDay(value){
  const current=new Date(value+'T00:00:00Z');
  current.setUTCDate(current.getUTCDate()+1);
  return current.toISOString().slice(0,10);
}
function availableAgain(value){
  return value.resource_available_again||nextDay(value.dispatch_date);
}
function occupiedDays(value){
  const result=[];
  for(let current=value.dispatch_date;current<availableAgain(value);current=nextDay(current))result.push(current);
  return result;
}

export function exportPlan(r){
  if(r.schema_version==='assignment_v1'){
    const headers=['Viaje','Origen','Destino','Vehicle ID','Tipo de vehículo','Propiedad','Proveedor','Site base','Orden','Producto','Unidades','Kg','Utilización','Costo estimado del viaje','CO2 estimado del viaje'];
    const rows=r.scenarios.selected.trips.flatMap(t=>t.loads.map((l,i)=>[
      t.trip_id,t.origin,t.destination,t.vehicle_id,vehicle(t.vehicle_type),
      t.ownership==='own'?'Propio':'Tercerizado',t.provider_name||'',t.base_site||'',
      l.order_id,l.product||'',l.units,l.kg,t.utilization,
      i===0?(t.estimated_cost??''):'',i===0?(t.estimated_co2_kg??''):''
    ]));
    download('assignment-recomendada.csv',csv([headers,...rows]),'text/csv;charset=utf-8');
    return;
  }
  const headers=['Viaje','Salida','Llegada','Recurso disponible','Días de ciclo','Origen','Destino','Pool de flota','Base','Camión','Propiedad','Orden','Producto','Unidades','Kg','Costo del viaje','CO2 del viaje'];
  const rows=r.scenarios.selected.trips.flatMap(t=>t.loads.map((l,i)=>[
    t.trip_id,t.dispatch_date,t.arrival_date,availableAgain(t),t.cycle_days||1,t.origin,t.destination,poolId(t),
    baseLabel(t),vehicle(t.vehicle_type),t.ownership==='own'?'Propio':'Tercerizado',
    l.order_id,l.product||'',l.units,l.kg,i===0?t.cost:'',i===0?t.co2_kg:''
  ]));
  download('distribucion-recomendada.csv',csv([headers,...rows]),'text/csv;charset=utf-8');
}

export function render(root,r){
  const change=changes(r);
  root.innerHTML=`<h2>Distribución recomendada</h2><p>${num(change.consolidated)} consolidadas · ${num(change.split)} divididas · ${num(change.postponed)} reprogramadas · ${num(change.outsourced)} tercerizadas · ${num(change.late)} fuera de SLA</p><div class="dispatch-tabs" role="tablist" aria-label="Vistas de la distribución">${['Calendario','Viajes','Por orden'].map((s,i)=>`<button role="tab" data-tab="${i}" aria-selected="${i===0}">${s}</button>`).join('')}</div><div class="dispatch-plan-body"></div>`;
  const body=root.querySelector('.dispatch-plan-body');
  function tab(index){
    dispose(body);
    root.querySelectorAll('[role=tab]').forEach(b=>b.setAttribute('aria-selected',String(+b.dataset.tab===index)));
    if(index===0)calendar(body,r);
    if(index===1)trips(body,r);
    if(index===2)orders(body,r);
  }
  root.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>tab(+b.dataset.tab));
  tab(0);
}

function calendar(root,r){
  const trips=r.scenarios.selected.trips;
  const daySet=new Set();
  trips.forEach(t=>occupiedDays(t).forEach(d=>daySet.add(d)));
  const days=[...daySet].sort();
  root.innerHTML='<p>Ocupación real por día y pool. Una unidad finita queda reservada desde la salida hasta completar ida, entrega y retorno a su base; recién vuelve a estar disponible en la fecha indicada por el motor.</p><div class="dispatch-chart" role="img" aria-label="Ocupación temporal por pool de flota"></div><div class="dispatch-table-wrap"><table><thead><tr><th>Día</th><th>Base</th><th>Pool / camión</th><th>Salidas</th><th>En uso</th><th>Disponibles</th></tr></thead><tbody>'+
    days.flatMap(d=>r.fleet.map(v=>{
      const poolTrips=trips.filter(t=>poolId(t)===poolId(v));
      const departures=poolTrips.filter(t=>t.dispatch_date===d).length;
      const inUse=poolTrips.filter(t=>t.dispatch_date<=d&&d<availableAgain(t)).length;
      return (departures||inUse)?`<tr><td>${date(d)}</td><td>${esc(baseLabel(v))}</td><td>${esc(poolId(v))}<small>${esc(vehicle(v.vehicle_type))}</small></td><td>${departures}</td><td>${inUse}</td><td>${v.units_available??'Sin límite'}</td></tr>`:'';
    })).join('')+'</tbody></table></div>';

  chart(root.querySelector('.dispatch-chart'),{
    tooltip:{trigger:'axis',renderMode:'richText'},
    legend:{type:'scroll',bottom:0},
    grid:{left:48,right:16,top:30,bottom:85},
    xAxis:{type:'category',data:days.map(date),axisLabel:{rotate:30}},
    yAxis:{type:'value',minInterval:1},
    series:r.fleet.flatMap(v=>[
      {
        name:'En uso: '+poolLabel(v),
        type:'bar',
        data:days.map(d=>trips.filter(t=>poolId(t)===poolId(v)&&t.dispatch_date<=d&&d<availableAgain(t)).length),
      },
      ...(v.units_available!=null?[{
        name:'Capacidad: '+poolId(v),
        type:'line',
        symbol:'none',
        lineStyle:{type:'dashed'},
        data:days.map(()=>v.units_available),
      }]:[])
    ])
  });
}

function trips(root,r){
  const outcomes=new Map(r.scenarios.selected.order_outcomes.map(o=>[o.order_id,o]));
  const pools=[...new Map(r.scenarios.selected.trips.map(t=>[poolId(t),t])).values()];
  const routes=[...new Set(r.scenarios.selected.trips.map(t=>t.origin+' → '+t.destination))];
  root.innerHTML=`<div class="dispatch-filters"><input name="search" placeholder="Buscar orden, viaje, pool o destino" aria-label="Buscar viajes"><select name="pool" aria-label="Pool de flota"><option value="">Todos los pools</option>${pools.map(v=>`<option value="${esc(poolId(v))}">${esc(poolLabel(v))}</option>`).join('')}</select><select name="route" aria-label="Ruta"><option value="">Todas las rutas</option>${routes.map(v=>`<option>${esc(v)}</option>`).join('')}</select><select name="sort" aria-label="Ordenar"><option value="date">Fecha de salida</option><option value="cost">Mayor costo</option></select><label><input name="outsourced" type="checkbox">Tercerizados</label><label><input name="late" type="checkbox">Con tardanzas</label><button data-export>Exportar CSV</button></div><div class="dispatch-table-wrap"><table><thead><tr><th>Viaje / carga</th><th>Salida / llegada</th><th>Ruta / recurso</th><th>Utilización</th><th>Costo</th><th>CO₂</th></tr></thead><tbody></tbody></table></div><p data-count></p>`;
  const update=()=>{
    const filters={};
    root.querySelectorAll('[name]').forEach(n=>filters[n.name]=n.type==='checkbox'?n.checked:n.value);
    const rows=filteredTrips(r,filters);
    root.querySelector('tbody').innerHTML=rows.map(t=>`<tr><td><details><summary>${esc(t.trip_id)} · ${t.loads.length} órdenes</summary>${t.loads.map(l=>`<p>${esc(l.order_id)}: ${num(l.units)} un. · ${num(l.kg)} kg · plazo ${date(outcomes.get(l.order_id)?.deadline)}${outcomes.get(l.order_id)?.late_days?' · entrega tardía':''}</p>`).join('')}</details></td><td>${date(t.dispatch_date)}<small>Llegada ${date(t.arrival_date)} · recurso libre ${date(availableAgain(t))}</small></td><td>${esc(t.origin)} → ${esc(t.destination)}<small>${esc(vehicle(t.vehicle_type))} · ${esc(poolId(t))} · base ${esc(baseLabel(t))}${t.ownership==='third_party'?' · Tercerizado':''}</small></td><td>${num(t.load_kg)} kg · ${pct(t.utilization)}<meter min="0" max="1" value="${t.utilization}" aria-label="Utilización ${pct(t.utilization)}"></meter></td><td>${money(t.cost)}</td><td>${num(t.co2_kg,1)} kg</td></tr>`).join('');
    root.querySelector('[data-count]').textContent=rows.length+' viajes encontrados';
  };
  root.querySelectorAll('[name]').forEach(n=>n.oninput=update);
  root.querySelector('[data-export]').onclick=()=>exportPlan(r);
  update();
}

function orders(root,r){
  root.innerHTML='<label>Ordenar por <select><option value="late_days">Mayor tardanza</option><option value="postponed_days">Mayor reprogramación</option><option value="order_id">Orden</option></select></label><div class="dispatch-table-wrap"><table><thead><tr><th>Orden</th><th>Viajes</th><th>Salida / llegada</th><th>Plazo</th><th>Cambios</th></tr></thead><tbody></tbody></table></div>';
  const update=()=>{
    const key=root.querySelector('select').value;
    root.querySelector('tbody').innerHTML=[...r.scenarios.selected.order_outcomes]
      .sort((a,b)=>key==='order_id'?a.order_id.localeCompare(b.order_id):b[key]-a[key]||a.order_id.localeCompare(b.order_id))
      .map(o=>`<tr><td>${esc(o.order_id)}</td><td>${esc(o.trip_ids.join(', '))}<small>${esc((o.fleet_pool_ids||[]).join(', '))}</small></td><td>${date(o.dispatch_date)}<small>${date(o.arrival_date)}</small></td><td class="${o.late_days?'bad':'good'}">${o.late_days?o.late_days+' días tarde':'A tiempo'}<small>${date(o.deadline)}</small></td><td>${o.postponed_days?o.postponed_days+' días reprogramados; ':''}${o.consolidated?'Consolidada; ':''}${o.outsourced?'Tercerizada':''}</td></tr>`).join('');
  };
  root.querySelector('select').onchange=update;
  update();
}
