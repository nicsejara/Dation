import {esc,num,money,pct} from './shared.mjs';

const OBJECTIVES={
  min_trips:{label:'Minimizar viajes',metric:'total_trips',format:num,title:'Viajes'},
  min_cost:{label:'Minimizar costo',metric:'total_cost',format:money,title:'Costo estimado'},
  max_own_fleet:{label:'Maximizar uso de flota propia',metric:'own_weight_share',format:pct,title:'Carga con flota propia'},
  min_co2:{label:'Minimizar CO₂',metric:'co2_kg',format:value=>num(value,1)+' kg',title:'CO₂ estimado'},
  balanced:{label:'Objetivo balanceado',metric:null,format:null,title:'Variables activas'},
  custom:{label:'Objetivo personalizado',metric:null,format:null,title:'Variables activas'},
  min_time:{label:'Minimizar tiempo',metric:'avg_lead_time_days',format:value=>num(value,2)+' días',title:'Tiempo medio'},
  max_utilization:{label:'Maximizar utilización propia',metric:'own_weight_share',format:pct,title:'Carga con flota propia'},
};

function renderAssignment(root,result){
  const selected=result.scenarios.selected;
  const metrics=selected.metrics;
  const objective=OBJECTIVES[result.configuration.objective]||OBJECTIVES.balanced;
  const dimensions=result.configuration.dimensions||['trips','own_fleet'];
  const metricValue=objective.metric?metrics[objective.metric]:null;
  const objectiveValue=objective.metric
    ?(metricValue==null?'Sin dato':objective.format(metricValue))
    :num(dimensions.length);

  root.innerHTML=
    '<div class="dispatch-decision-hero">'
      +'<div class="dispatch-decision-copy">'
        +'<span class="dispatch-kicker">DECISIÓN 01 · ASIGNACIÓN RECOMENDADA</span>'
        +'<h1>Distribuir '+num(metrics.orders)+' órdenes en '+num(metrics.total_trips)+' viajes</h1>'
        +'<p>La asignación responde al objetivo <strong>'+esc(objective.label)+'</strong> respetando capacidad por viaje, origen/site, ruta y unidades enteras.</p>'
        +'<div class="dispatch-decision-next"><span aria-hidden="true">→</span><div><strong>Siguiente paso</strong><p>Revisá qué vehículo toma cada viaje y aprobá Assignment. El calendario se resolverá después en Planificación.</p></div></div>'
      +'</div>'
      +'<div class="dispatch-decision-status">'
        +'<span class="dispatch-status-pill is-good">Assignment lista para validar</span>'
        +'<div class="dispatch-decision-metrics">'
          +'<div><small>'+esc(objective.title)+'</small><strong>'+esc(objectiveValue)+'</strong></div>'
          +'<div><small>Utilización media</small><strong>'+pct(metrics.load_utilization)+'</strong></div>'
          +'<div><small>Flota propia</small><strong>'+pct(metrics.own_weight_share)+'</strong></div>'
        +'</div>'
        +'<p class="dispatch-decision-mix">'+num(metrics.vehicles_used)+' vehículo'+(metrics.vehicles_used===1?'':'s')+' utilizado'+(metrics.vehicles_used===1?'':'s')
          +(metrics.outsourced_weight_share?' · '+pct(metrics.outsourced_weight_share)+' de la carga tercerizada':'')
        +'</p>'
      +'</div>'
    +'</div>';
}

function renderLegacy(root,result){
  const selected=result.scenarios.selected;
  const metrics=selected.metrics;
  const objective=OBJECTIVES[result.configuration.objective]||OBJECTIVES.balanced;
  const late=metrics.late_orders||0;
  const dimensions=result.configuration.dimensions||['cost','time','utilization','co2'];
  const objectiveValue=objective.metric&&metrics[objective.metric]!=null
    ?objective.format(metrics[objective.metric])
    :num(dimensions.length);
  const status=late
    ?'Resultado histórico con '+num(late)+' excepción'+(late===1?'':'es')+' de SLA'
    :'Resultado histórico de Dispatch';

  root.innerHTML=
    '<div class="dispatch-decision-hero">'
      +'<div class="dispatch-decision-copy">'
        +'<span class="dispatch-kicker">CORRIDA HISTÓRICA · DISPATCH</span>'
        +'<h1>Distribuir '+num(metrics.orders)+' órdenes en '+num(metrics.total_trips)+' viajes</h1>'
        +'<p>Esta corrida fue calculada con el motor temporal anterior y se conserva para trazabilidad.</p>'
      +'</div>'
      +'<div class="dispatch-decision-status">'
        +'<span class="dispatch-status-pill '+(late?'is-warning':'is-good')+'">'+esc(status)+'</span>'
        +'<div class="dispatch-decision-metrics">'
          +'<div><small>'+esc(objective.title)+'</small><strong>'+esc(objectiveValue)+'</strong></div>'
          +'<div><small>Viajes</small><strong>'+num(metrics.total_trips)+'</strong></div>'
          +'<div><small>Flota propia</small><strong>'+pct(metrics.own_weight_share||0)+'</strong></div>'
        +'</div>'
      +'</div>'
    +'</div>';
}

export function render(root,result){
  if(result.schema_version==='assignment_v1'){
    renderAssignment(root,result);
    return;
  }
  renderLegacy(root,result);
}
