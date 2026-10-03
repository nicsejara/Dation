import {esc,num,pct,vehicle,chart,dispose} from './shared.mjs';

function resourceId(value){
  return value.vehicle_id||value.fleet_pool_id||value.vehicle_type||'legacy';
}

function baseLabel(value){
  if(value.base_site==='*'||value.base_location==='*')return 'Cualquier origen';
  return value.base_site||value.base_location||'Site no informado';
}

function aggregate(result){
  const groups=new Map();

  for(const trip of result.scenarios.selected.trips||[]){
    const id=resourceId(trip);
    if(!groups.has(id)){
      groups.set(id,{
        id,
        vehicle_type:trip.vehicle_type,
        ownership:trip.ownership,
        provider_name:trip.provider_name||null,
        base_site:trip.base_site||trip.base_location,
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
    label:'Viajes asignados',
    value:item=>item.trips.length,
    format:value=>num(value),
  },
  utilization:{
    label:'Utilización media',
    value:item=>item.utilization,
    format:value=>pct(value),
  },
};

export function render(root,result){
  dispose(root);
  const resources=aggregate(result);

  if(!resources.length){
    root.innerHTML='<h2>Asignación de carga</h2><p>No hay viajes para mostrar.</p>';
    return;
  }

  const isAssignment=result.schema_version==='assignment_v1';
  let metric='load';
  let selectedId=resources[0].id;

  root.innerHTML=
    '<div class="dispatch-section-heading">'
      +'<div><span class="dispatch-kicker">ASIGNACIÓN</span><h2>Qué vehículo toma cada carga</h2>'
      +'<p>Seleccioná un vehículo para revisar cuántos viajes recibe, qué productos transporta y cómo se utiliza su capacidad.</p></div>'
      +'<label class="dispatch-metric-picker">Ver por <select data-assignment-metric>'
      +Object.entries(METRICS).map(([key,item])=>'<option value="'+key+'">'+esc(item.label)+'</option>').join('')
      +'</select></label>'
    +'</div>'
    +'<div class="dispatch-assignment-layout">'
      +'<div>'
        +'<div class="dispatch-assignment-chart dispatch-chart" role="img" aria-label="Asignación de carga por vehículo"></div>'
        +'<div class="dispatch-pool-grid" data-resource-grid></div>'
      +'</div>'
      +'<aside class="dispatch-assignment-detail" data-assignment-detail></aside>'
    +'</div>'
    +(isAssignment
      ?'<p class="dispatch-model-note"><strong>Assignment no define fechas.</strong> Un mismo vehículo puede recibir varios viajes abstractos; Planificación decidirá cuándo ejecutarlos y verificará que no se superpongan.</p>'
      :'<p class="dispatch-model-note">Esta es una corrida histórica calculada con el motor temporal anterior.</p>');

  const grid=root.querySelector('[data-resource-grid]');
  const detail=root.querySelector('[data-assignment-detail]');
  const chartNode=root.querySelector('.dispatch-assignment-chart');

  function renderGrid(){
    grid.innerHTML=resources.map(resource=>{
      const active=resource.id===selectedId;
      return '<button class="dispatch-pool-card" data-resource="'+esc(resource.id)+'" aria-pressed="'+active+'">'
        +'<span class="dispatch-pool-card-top"><strong>'+esc(resource.id)+'</strong><small>'+esc(resource.ownership==='own'?'Propio':'Tercerizado')+'</small></span>'
        +'<span class="dispatch-pool-id">'+esc(vehicle(resource.vehicle_type))+' · '+esc(baseLabel(resource))+'</span>'
        +'<span class="dispatch-pool-stats">'
          +'<span><small>Carga</small><strong>'+num(resource.load_kg,0)+' kg</strong></span>'
          +'<span><small>Viajes</small><strong>'+num(resource.trips.length)+'</strong></span>'
          +'<span><small>Utilización</small><strong>'+pct(resource.utilization)+'</strong></span>'
        +'</span>'
      +'</button>';
    }).join('');

    grid.querySelectorAll('[data-resource]').forEach(button=>{
      button.onclick=()=>{
        selectedId=button.dataset.resource;
        renderGrid();
        renderDetail();
        drawChart();
      };
    });
  }

  function renderDetail(){
    const resource=resources.find(item=>item.id===selectedId)||resources[0];
    const products=resource.product_rows;

    detail.innerHTML=
      '<span class="dispatch-config-eyebrow">Vehículo seleccionado</span>'
      +'<h3>'+esc(resource.id)+'</h3>'
      +'<p>'+esc(vehicle(resource.vehicle_type))+' · '+esc(baseLabel(resource))+' · '+esc(resource.ownership==='own'?'Flota propia':'Tercerizado')
        +(resource.provider_name?' · '+esc(resource.provider_name):'')+'</p>'
      +'<div class="dispatch-assignment-summary">'
        +'<span><small>Carga</small><strong>'+num(resource.load_kg,0)+' kg</strong></span>'
        +'<span><small>Viajes</small><strong>'+num(resource.trips.length)+'</strong></span>'
        +'<span><small>Órdenes</small><strong>'+num(resource.orders.size)+'</strong></span>'
        +'<span><small>Utilización</small><strong>'+pct(resource.utilization)+'</strong></span>'
      +'</div>'
      +'<h4>Qué productos lleva</h4>'
      +'<div class="dispatch-product-list">'
        +(products.length?products.map(item=>
          '<div class="dispatch-product-row">'
            +'<div><strong>'+esc(item.product)+'</strong><small>'+num(item.orders.length)+' órdenes · '+num(item.units)+' unidades</small></div>'
            +'<span>'+num(item.kg,0)+' kg</span>'
          +'</div>'
        ).join(''):'<p>No hay detalle de producto disponible.</p>')
      +'</div>'
      +'<details class="dispatch-trip-detail"><summary>Ver viajes y órdenes</summary>'
        +'<div class="dispatch-table-wrap"><table><thead><tr><th>Viaje</th><th>Ruta</th><th>Carga</th><th>Utilización</th><th>Órdenes / productos</th></tr></thead><tbody>'
        +resource.trips.map(trip=>
          '<tr>'
            +'<td>'+esc(trip.trip_id)+'</td>'
            +'<td>'+esc(trip.origin)+' → '+esc(trip.destination)+'</td>'
            +'<td>'+num(trip.load_kg,0)+' kg</td>'
            +'<td>'+pct(trip.utilization)+'</td>'
            +'<td>'+(trip.loads||[]).map(load=>esc(load.order_id)+' · '+esc(load.product||'Producto no registrado')+' · '+num(load.units)+' un.').join('<br>')+'</td>'
          +'</tr>'
        ).join('')
        +'</tbody></table></div>'
      +'</details>';
  }

  function drawChart(){
    chartNode._dispose?.();
    const definition=METRICS[metric];
    const ordered=[...resources].sort((a,b)=>definition.value(b)-definition.value(a)||a.id.localeCompare(b.id));
    const instance=chart(chartNode,{
      grid:{left:145,right:28,top:20,bottom:30},
      tooltip:{
        trigger:'item',
        renderMode:'richText',
        formatter:params=>{
          const resource=ordered[params.dataIndex];
          return resource.id
            +'\n'+vehicle(resource.vehicle_type)
            +'\n'+definition.label+': '+definition.format(definition.value(resource))
            +'\nCarga: '+num(resource.load_kg,0)+' kg'
            +'\nViajes: '+num(resource.trips.length)
            +'\nUtilización: '+pct(resource.utilization);
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
          itemStyle:{opacity:item.id===selectedId?1:.42},
        })),
        label:{
          show:true,
          position:'right',
          formatter:params=>definition.format(params.value),
        },
      }],
    });
    instance?.on('click',params=>{
      const resource=ordered[params.dataIndex];
      if(!resource)return;
      selectedId=resource.id;
      renderGrid();
      renderDetail();
      drawChart();
    });
  }

  root.querySelector('[data-assignment-metric]').onchange=event=>{
    metric=event.target.value;
    drawChart();
  };

  renderGrid();
  renderDetail();
  drawChart();
}
