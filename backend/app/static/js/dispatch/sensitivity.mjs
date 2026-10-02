import {chart,num,money,pct,metricInfo} from './shared.mjs';

function historical(root,points){
  root.innerHTML+=`
    <p class="dispatch-alert">Análisis histórico con el contrato anterior costo / viajes / tiempo.</p>
    <div class="dispatch-table-wrap">
      <table>
        <thead><tr><th>Pesos históricos</th><th>Costo</th><th>Viajes</th><th>Tiempo</th></tr></thead>
        <tbody>
          ${points.map(point=>`<tr><td>${Object.values(point.weights).map(pct).join(' / ')}</td><td>${money(point.metrics.total_cost)}</td><td>${num(point.metrics.total_trips)}</td><td>${num(point.metrics.avg_lead_time_days,2)} días</td></tr>`).join('')}
        </tbody>
      </table>
    </div>
  `;
}

export function render(root,result){
  const points=result.sensitivity.weight_sweep;
  root.innerHTML='<h2>Cómo cambian las prioridades</h2>';

  if(!points.length){
    root.innerHTML+='<p>El análisis de sensibilidad no fue solicitado.</p>';
    return;
  }

  if(result.schema_version==='dispatch_v1'){
    historical(root,points);
    return;
  }

  const robust=new Set(points.map(point=>point.plan_fingerprint)).size===1;
  if(robust){
    root.innerHTML+='<p class="dispatch-alert">Decisión robusta: la distribución no cambia entre costo, tiempo, uso propio, CO₂ y balanceado.</p>';
  }

  root.innerHTML+=`
    <p>Los cinco escenarios protegen primero el mejor SLA encontrado y luego cambian la prioridad de negocio.</p>
    <div class="dispatch-chart" data-frontier></div>
    <div class="dispatch-comparison-charts">
      ${['total_cost','avg_lead_time_days','own_weight_share','co2_kg'].map(key=>`<div><h3>${metricInfo[key][0]}</h3><div class="dispatch-chart" data-trend="${key}"></div></div>`).join('')}
    </div>
    <div class="dispatch-table-wrap">
      <table>
        <thead>
          <tr>
            <th>Objetivo</th><th>Costo</th><th>Tiempo</th><th>Uso propio</th><th>CO₂</th><th>SLA</th><th>Cambios vs decisión</th>
          </tr>
        </thead>
        <tbody>
          ${points.map(point=>`<tr><td>${point.label||point.scenario}</td><td>${money(point.metrics.total_cost)}</td><td>${num(point.metrics.avg_lead_time_days,2)} días</td><td>${pct(point.metrics.own_weight_share)}</td><td>${num(point.metrics.co2_kg,1)} kg</td><td>${pct(point.metrics.on_time_rate)}</td><td>${num(point.orders_changed_vs_selected)}</td></tr>`).join('')}
        </tbody>
      </table>
    </div>
    ${result.sensitivity.complete?'':'<p class="dispatch-alert">El presupuesto permitió evaluar sólo parte de los escenarios.</p>'}
  `;

  const selected=result.scenarios.selected.metrics;
  chart(root.querySelector('[data-frontier]'),{
    tooltip:{
      renderMode:'richText',
      formatter:params=>params.seriesName+'\nUso propio: '+pct(params.value[0])+' · '+money(params.value[1])+'\nTiempo: '+num(params.value[2],2)+' días · CO₂: '+num(params.value[3],1)+' kg',
    },
    grid:{left:75,right:20,bottom:55},
    xAxis:{name:'Uso flota propia',type:'value',min:0,max:1,axisLabel:{formatter:value=>pct(value)}},
    yAxis:{name:'Costo',type:'value',scale:true},
    series:[
      {
        name:'Alternativas',
        type:'scatter',
        data:points.map(point=>[
          point.metrics.own_weight_share,
          point.metrics.total_cost,
          point.metrics.avg_lead_time_days,
          point.metrics.co2_kg,
        ]),
        symbolSize:16,
      },
      {
        name:'Decisión elegida',
        type:'scatter',
        data:[[
          selected.own_weight_share,
          selected.total_cost,
          selected.avg_lead_time_days,
          selected.co2_kg,
        ]],
        symbol:'diamond',
        symbolSize:24,
      },
    ],
  });

  root.querySelectorAll('[data-trend]').forEach(node=>{
    const key=node.dataset.trend;
    const formatter=metricInfo[key][1];
    chart(node,{
      tooltip:{trigger:'axis',renderMode:'richText',valueFormatter:formatter},
      grid:{left:65,right:20,top:20,bottom:65},
      xAxis:{
        type:'category',
        data:points.map(point=>point.label||point.scenario),
        axisLabel:{rotate:25},
      },
      yAxis:{
        type:'value',
        scale:true,
        axisLabel:{formatter:value=>key==='own_weight_share'?pct(value):key==='total_cost'?'$ '+num(value/1e6,1)+' M':num(value,2)},
      },
      series:[{
        name:metricInfo[key][0],
        type:'line',
        data:points.map(point=>point.metrics[key]),
      }],
    });
  });
}
