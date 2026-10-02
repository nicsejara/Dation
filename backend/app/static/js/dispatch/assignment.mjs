import {esc,num,pct,date,vehicle,chart,dispose} from './shared.mjs';

function poolId(value){
  return value.fleet_pool_id||value.vehicle_type||'legacy';
}

function baseLabel(value){
  if(value.base_location==='*')return 'Cualquier origen';
  return value.base_location||'Base no informada';
}

function aggregate(result){
  const groups=new Map();

  for(const trip of result.scenarios.selected.trips){
    const id=poolId(trip);
    if(!groups.has(id)){
      groups.set(id,{
        id,
        vehicle_type:trip.vehicle_type,
        ownership:trip.ownership,
        base_location:trip.base_location,
        trips:[],
        load_kg:0,
        capacity_kg:0,
        orders:new Set(),
        products:new Map(),
      });
    }

    const group=groups.get(id);
    group.trips.push(trip);
    group.load_kg+=Number(trip.load_kg||0);
    group.capacity_kg+=Number(trip.capacity_kg||0);

    for(const load of trip.loads||[]){
      group.orders.add(load.order_id);
      const product=load.product||'Producto no registrado';
      const current=group.products.get(product)||{
        product,
        units:0,
        kg:0,
        orders:new Set(),
      };
      current.units+=Number(load.units||0);
      current.kg+=Number(load.kg||0);
      current.orders.add(load.order_id);
      group.products.set(product,current);
    }
  }

  return [...groups.values()]
    .map(group=>({
      ...group,
      utilization:group.capacity_kg?group.load_kg/group.capacity_kg:0,
      product_rows:[...group.products.values()]
        .map(item=>({...item,orders:[...item.orders].sort()}))
        .sort((a,b)=>b.kg-a.kg||a.product.localeCompare(b.product)),
    }))
    .sort((a,b)=>b.load_kg-a.load_kg||a.id.localeCompare(b.id));
}

const METRICS={
  load:{
    label:'Carga transportada',
    value:item=>item.load_kg,
    format:value=>num(value,0)+' kg',
  },
  trips:{
    label:'Viajes',
    value:item=>item.trips.length,
    format:value=>num(value),
  },
  utilization:{
    label:'Utilización',
    value:item=>item.utilization,
    format:value=>pct(value),
  },
};

export function render(root,result){
  dispose(root);
  const pools=aggregate(result);

  if(!pools.length){
    root.innerHTML='<h2>Asignación de carga</h2><p>No hay viajes para mostrar.</p>';
    return;
  }

  let metric='load';
  let selectedId=pools[0].id;

  root.innerHTML=
    '<div class="dispatch-section-heading">'
      +'<div><span class="dispatch-kicker">ASIGNACIÓN</span><h2>Cómo quedó distribuida la carga</h2>'
      +'<p>Seleccioná un pool para revisar qué carga toma, cuántos viajes realiza y qué productos transporta.</p></div>'
      +'<label class="dispatch-metric-picker">Ver por <select data-assignment-metric>'
      +Object.entries(METRICS).map(([key,item])=>'<option value="'+key+'">'+esc(item.label)+'</option>').join('')
      +'</select></label>'
    +'</div>'
    +'<div class="dispatch-assignment-layout">'
      +'<div>'
        +'<div class="dispatch-assignment-chart dispatch-chart" role="img" aria-label="Asignación de carga por pool de flota"></div>'
        +'<div class="dispatch-pool-grid" data-pool-grid></div>'
      +'</div>'
      +'<aside class="dispatch-assignment-detail" data-assignment-detail></aside>'
    +'</div>'
    +'<p class="dispatch-model-note">La asignación actual es por <strong>pool homogéneo de flota</strong>. Dation decide tipo/base/pool y viajes; no individualiza patente o unidad física dentro del pool.</p>';

  const grid=root.querySelector('[data-pool-grid]');
  const detail=root.querySelector('[data-assignment-detail]');
  const chartNode=root.querySelector('.dispatch-assignment-chart');
  let chartInstance=null;

  function renderGrid(){
    grid.innerHTML=pools.map(pool=>{
      const active=pool.id===selectedId;
      return '<button class="dispatch-pool-card" data-pool="'+esc(pool.id)+'" aria-pressed="'+active+'">'
        +'<span class="dispatch-pool-card-top"><strong>'+esc(vehicle(pool.vehicle_type))+'</strong><small>'+esc(pool.ownership==='own'?'Propio':'Tercerizado')+'</small></span>'
        +'<span class="dispatch-pool-id">'+esc(pool.id)+'</span>'
        +'<span class="dispatch-pool-stats">'
          +'<span><small>Carga</small><strong>'+num(pool.load_kg,0)+' kg</strong></span>'
          +'<span><small>Viajes</small><strong>'+num(pool.trips.length)+'</strong></span>'
          +'<span><small>Utilización</small><strong>'+pct(pool.utilization)+'</strong></span>'
        +'</span>'
      +'</button>';
    }).join('');

    grid.querySelectorAll('[data-pool]').forEach(button=>{
      button.onclick=()=>{
        selectedId=button.dataset.pool;
        renderGrid();
        renderDetail();
        drawChart();
      };
    });
  }

  function renderDetail(){
    const pool=pools.find(item=>item.id===selectedId)||pools[0];
    const products=pool.product_rows;

    detail.innerHTML=
      '<span class="dispatch-config-eyebrow">Detalle seleccionado</span>'
      +'<h3>'+esc(vehicle(pool.vehicle_type))+'</h3>'
      +'<p>'+esc(pool.id)+' · base '+esc(baseLabel(pool))+' · '+esc(pool.ownership==='own'?'Flota propia':'Tercerizado')+'</p>'
      +'<div class="dispatch-assignment-summary">'
        +'<span><small>Carga</small><strong>'+num(pool.load_kg,0)+' kg</strong></span>'
        +'<span><small>Viajes</small><strong>'+num(pool.trips.length)+'</strong></span>'
        +'<span><small>Órdenes</small><strong>'+num(pool.orders.size)+'</strong></span>'
        +'<span><small>Utilización</small><strong>'+pct(pool.utilization)+'</strong></span>'
      +'</div>'
      +'<h4>Qué productos lleva</h4>'
      +'<div class="dispatch-product-list">'
        +(products.length?products.map(item=>
          '<div class="dispatch-product-row">'
            +'<div><strong>'+esc(item.product)+'</strong><small>'+num(item.orders.length)+' órdenes · '+num(item.units)+' unidades</small></div>'
            +'<span>'+num(item.kg,0)+' kg</span>'
          +'</div>'
        ).join(''):'<p>No hay detalle de producto disponible para esta corrida histórica.</p>')
      +'</div>'
      +'<details class="dispatch-trip-detail"><summary>Ver viajes y órdenes</summary>'
        +'<div class="dispatch-table-wrap"><table><thead><tr><th>Viaje</th><th>Ruta</th><th>Salida</th><th>Carga</th><th>Órdenes / productos</th></tr></thead><tbody>'
        +pool.trips.map(trip=>
          '<tr>'
            +'<td>'+esc(trip.trip_id)+'</td>'
            +'<td>'+esc(trip.origin)+' → '+esc(trip.destination)+'</td>'
            +'<td>'+date(trip.dispatch_date)+'</td>'
            +'<td>'+num(trip.load_kg,0)+' kg<small>'+pct(trip.utilization)+'</small></td>'
            +'<td>'+(trip.loads||[]).map(load=>esc(load.order_id)+' · '+esc(load.product||'Producto no registrado')).join('<br>')+'</td>'
          +'</tr>'
        ).join('')
        +'</tbody></table></div>'
      +'</details>';
  }

  function drawChart(){
    chartNode._dispose?.();
    const definition=METRICS[metric];
    const ordered=[...pools].sort((a,b)=>definition.value(b)-definition.value(a)||a.id.localeCompare(b.id));
    chartInstance=chart(chartNode,{
      grid:{left:145,right:28,top:20,bottom:30},
      tooltip:{
        trigger:'item',
        renderMode:'richText',
        formatter:params=>{
          const pool=ordered[params.dataIndex];
          return vehicle(pool.vehicle_type)+' · '+pool.id
            +'\n'+definition.label+': '+definition.format(definition.value(pool))
            +'\nCarga: '+num(pool.load_kg,0)+' kg'
            +'\nViajes: '+num(pool.trips.length)
            +'\nUtilización: '+pct(pool.utilization);
        },
      },
      xAxis:{
        type:'value',
        axisLabel:{
          formatter:value=>metric==='utilization'?pct(value):num(value,0),
        },
      },
      yAxis:{
        type:'category',
        data:ordered.map(item=>item.id),
        axisLabel:{width:130,overflow:'truncate'},
      },
      series:[{
        type:'bar',
        data:ordered.map(item=>({
          value:definition.value(item),
          itemStyle:{
            opacity:itemSelected(item.id)?1:.42,
          },
        })),
        label:{
          show:true,
          position:'right',
          formatter:params=>definition.format(params.value),
        },
      }],
    });
    chartInstance?.on('click',params=>{
      const pool=ordered[params.dataIndex];
      if(!pool)return;
      selectedId=pool.id;
      renderGrid();
      renderDetail();
      drawChart();
    });
  }

  function itemSelected(id){
    return id===selectedId;
  }

  root.querySelector('[data-assignment-metric]').onchange=event=>{
    metric=event.target.value;
    drawChart();
  };

  renderGrid();
  renderDetail();
  drawChart();
}
