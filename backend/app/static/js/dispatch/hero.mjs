import {esc,num,money,pct} from './shared.mjs';

const OBJECTIVES={
  min_cost:{label:'Minimizar costo',metric:'total_cost',format:money,title:'Costo de la distribución'},
  min_time:{label:'Minimizar tiempo',metric:'avg_lead_time_days',format:value=>num(value,2)+' días',title:'Tiempo medio'},
  max_utilization:{label:'Maximizar utilización propia',metric:'own_weight_share',format:pct,title:'Carga con flota propia'},
  min_co2:{label:'Minimizar CO₂',metric:'co2_kg',format:value=>num(value,1)+' kg',title:'CO₂ estimado'},
  balanced:{label:'Objetivo balanceado',metric:null,format:null,title:'Dimensiones activas'},
  custom:{label:'Objetivo personalizado',metric:null,format:null,title:'Dimensiones activas'},
  min_trips:{label:'Priorizar viajes (histórico)',metric:'total_trips',format:num,title:'Viajes'},
};

export function render(root,result){
  const selected=result.scenarios.selected;
  const metrics=selected.metrics;
  const objective=OBJECTIVES[result.configuration.objective]||OBJECTIVES.balanced;
  const late=metrics.late_orders||0;
  const dimensions=result.configuration.dimensions||['cost','time','utilization','co2'];
  const objectiveValue=objective.metric
    ?objective.format(metrics[objective.metric])
    :num(dimensions.length);
  const status=late
    ?'Requiere revisar '+num(late)+' excepción'+(late===1?'':'es')+' de SLA'
    :'Distribución dentro del SLA encontrado';

  root.innerHTML=
    '<div class="dispatch-decision-hero">'
      +'<div class="dispatch-decision-copy">'
        +'<span class="dispatch-kicker">DECISIÓN RECOMENDADA · DDA LOGÍSTICA</span>'
        +'<h1>Distribuir '+num(metrics.orders)+' órdenes en '+num(metrics.total_trips)+' viajes</h1>'
        +'<p>La distribución cumple el objetivo <strong>'+esc(objective.label)+'</strong> bajo las restricciones de capacidad, ubicación, disponibilidad y SLA configuradas.</p>'
        +'<div class="dispatch-decision-next"><span aria-hidden="true">→</span><div><strong>Siguiente paso</strong><p>Revisá la asignación de carga y las excepciones antes de exportar la distribución.</p></div></div>'
      +'</div>'
      +'<div class="dispatch-decision-status">'
        +'<span class="dispatch-status-pill '+(late?'is-warning':'is-good')+'">'+esc(status)+'</span>'
        +'<div class="dispatch-decision-metrics">'
          +'<div><small>'+esc(objective.title)+'</small><strong>'+objectiveValue+'</strong></div>'
          +'<div><small>Entregas a tiempo</small><strong>'+pct(metrics.on_time_rate)+'</strong></div>'
          +'<div><small>Viajes</small><strong>'+num(metrics.total_trips)+'</strong></div>'
        +'</div>'
        +(metrics.own_weight_share!=null
          ?'<p class="dispatch-decision-mix">'+pct(metrics.own_weight_share)+' de la carga con flota propia'
            +(metrics.outsourced_weight_share?' · '+pct(metrics.outsourced_weight_share)+' tercerizada':'')
            +'</p>'
          :'')
      +'</div>'
    +'</div>';
}
