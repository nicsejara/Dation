import {esc,num,pct,metricInfo,chart,dispose} from './shared.mjs';
import {delta,samePlan} from './selectors.mjs';

const V2_KEYS=[
  'total_cost',
  'avg_lead_time_days',
  'own_weight_share',
  'co2_kg',
  'on_time_rate',
  'late_orders',
  'total_trips',
];

function comparableKeys(selected,comparison){
  return V2_KEYS.filter(
    key=>metricInfo[key]
      &&selected.metrics?.[key]!=null
      &&comparison.metrics?.[key]!=null
  );
}

export function render(root,result){
  const selected=result.scenarios.selected;
  const available=Object.entries(result.scenarios)
    .filter(([key,scenario])=>key!=='selected'&&scenario.metrics);

  root.innerHTML=`
    <h2>Comparar alternativas</h2>
    <p>${result.schema_version==='dispatch_v2'
      ?'Todas las alternativas de negocio se comparan después de proteger el mejor SLA encontrado.'
      :'Comparación histórica bajo el contrato de la corrida.'}</p>
    <label>Comparar contra
      <select>
        ${available.map(([key,scenario])=>`<option value="${esc(key)}">${esc(scenario.name)}${scenario.feasible?'':' (referencia no factible)'}</option>`).join('')}
      </select>
    </label>
    <div data-comparison></div>
  `;

  if(!available.length){
    root.querySelector('[data-comparison]').innerHTML='<p>No hay escenarios comparables.</p>';
    return;
  }

  const select=root.querySelector('select');
  select.value=
    available.find(([key,scenario])=>key==='baseline_direct'&&scenario.feasible&&!samePlan(scenario,selected))?.[0]
    ||available.find(([,scenario])=>scenario.feasible&&!samePlan(scenario,selected))?.[0]
    ||available[0][0];

  const body=root.querySelector('[data-comparison]');

  function update(){
    dispose(body);
    const comparison=result.scenarios[select.value];
    const keys=comparableKeys(selected,comparison);

    body.innerHTML=`
      ${samePlan(selected,comparison)?'<p class="dispatch-alert">Este escenario produce la misma distribución.</p>':''}
      ${!comparison.feasible?'<p class="dispatch-alert">Esta referencia no cumple todas las restricciones y no se presenta como alternativa ejecutable.</p>':''}
      <div class="dispatch-table-wrap">
        <table>
          <thead><tr><th>Métrica</th><th>Decisión</th><th>Comparado</th><th>Diferencia</th><th>Variación</th></tr></thead>
          <tbody>
            ${keys.map(key=>{
              const [name,formatter]=metricInfo[key];
              const d=delta(
                selected.metrics[key],
                comparison.feasible?comparison.metrics[key]:null,
                result.kpi_directions[key],
              );
              return `<tr><td>${name}</td><td>${formatter(selected.metrics[key])}</td><td>${formatter(comparison.metrics[key])}</td><td class="${d.tone}">${d.absolute==null?'—':formatter(d.absolute)}</td><td class="${d.tone}">${pct(d.percent)}</td></tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>
      <div class="dispatch-comparison-charts">
        ${keys.filter(key=>['total_cost','avg_lead_time_days','own_weight_share','co2_kg'].includes(key)).map(key=>`<div><h3>${metricInfo[key][0]}</h3><div class="dispatch-chart" data-metric="${key}"></div></div>`).join('')}
      </div>
    `;

    body.querySelectorAll('[data-metric]').forEach(node=>{
      const key=node.dataset.metric;
      const formatter=metricInfo[key][1];
      chart(node,{
        grid:{left:70,right:15,top:25,bottom:35},
        tooltip:{renderMode:'richText'},
        xAxis:{type:'category',data:['Decisión','Comparado']},
        yAxis:{type:'value',scale:true},
        series:[{
          type:'bar',
          data:[selected.metrics[key],comparison.metrics[key]],
          label:{show:true,position:'top',formatter:params=>formatter(params.value)},
        }],
      });
    });
  }

  select.onchange=update;
  update();
}
