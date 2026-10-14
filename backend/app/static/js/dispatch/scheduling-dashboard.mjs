import {iconSvg} from "./decision-ui.mjs";
import {renderDashboardToolbar,bindDashboardToolbar} from './dashboard-toolbar.mjs';
import {scopeFor,disposeScope} from "./lifecycle.mjs";
import {esc,num,pct,date,chart,dispose,errorBox} from './shared.mjs';
import * as explanation from './explanation.mjs';
import {decisionRail,bindDecisionRail} from './decision-nav.mjs';


function dayDiff(from,to){
  const a=new Date(from+'T00:00:00Z');
  const b=new Date(to+'T00:00:00Z');
  return Math.round((b-a)/86400000);
}

function groupedByVehicle(trips){
  const groups=new Map();
  for(const trip of trips){
    const id=trip.vehicle_id||trip.vehicle_type||'Recurso';
    if(!groups.has(id)){
      groups.set(id,{
        id,
        vehicle_type:trip.vehicle_type,
        ownership:trip.ownership,
        trips:[],
      });
    }
    groups.get(id).trips.push(trip);
  }
  return [...groups.values()].map(group=>({
    ...group,
    trips:group.trips.sort((a,b)=>
      a.dispatch_date.localeCompare(b.dispatch_date)
      ||a.trip_id.localeCompare(b.trip_id)
    ),
  })).sort((a,b)=>a.id.localeCompare(b.id));
}

function renderTimeline(root,result){
  const trips=result.scenarios.selected.trips||[];
  const groups=groupedByVehicle(trips);
  if(!trips.length){
    root.innerHTML='<p>No hay viajes programados.</p>';
    return;
  }

  const start=result.scenarios.selected.metrics.schedule_start;
  const end=result.scenarios.selected.metrics.schedule_end;
  const days=Math.max(1,dayDiff(start,end));

  root.innerHTML=
    '<div class="dispatch-section-heading">'
      +'<div><span class="dispatch-kicker">CALENDARIO OPERATIVO</span><h2>Secuencia por vehículo</h2>'
      +'<p>Cada barra representa el período en que el vehículo queda ocupado por un viaje, incluyendo su retorno a base.</p></div>'
    +'</div>'
    +'<div class="dispatch-schedule-chart-scroll" role="region" tabindex="0" aria-label="Calendario desplazable por vehículo"><div class="dispatch-schedule-chart dispatch-chart" role="img" aria-label="Calendario por vehículo"></div></div>'
    +'<div class="dispatch-schedule-vehicles">'
      +groups.map(group=>
        '<article class="dispatch-schedule-vehicle">'
          +'<header><div><strong>'+esc(group.id)+'</strong><small>'+esc(group.vehicle_type||'Vehículo')+' · '+esc(group.ownership==='own'?'Propio':'Tercerizado')+'</small></div><span>'+num(group.trips.length)+' viaje'+(group.trips.length===1?'':'s')+'</span></header>'
          +'<div>'
          +group.trips.map(trip=>
            '<div class="dispatch-schedule-trip">'
              +'<span class="dispatch-schedule-trip__date">'+date(trip.dispatch_date)+'</span>'
              +'<div><strong>'+esc(trip.trip_id)+' · '+esc(trip.origin)+' → '+esc(trip.destination)+'</strong>'
              +'<small>Llega '+date(trip.arrival_date)+' · libre '+date(trip.resource_available_again)+' · espera '+num(trip.wait_days)+' d</small></div>'
              +'<span>'+num(trip.load_kg,0)+' kg</span>'
            +'</div>'
          ).join('')
          +'</div>'
        +'</article>'
      ).join('')
    +'</div>';

  const chartNode=root.querySelector('.dispatch-schedule-chart');
  const series=[];
  const categories=[];
  for(const group of groups){
    for(const trip of group.trips){
      categories.push(group.id+' · '+trip.trip_id);
      const offset=dayDiff(start,trip.dispatch_date);
      const duration=Math.max(1,dayDiff(trip.dispatch_date,trip.resource_available_again));
      series.push({offset,duration,trip});
    }
  }

  chartNode.style.height=Math.max(320,categories.length*28+70)+'px';
  chart(chartNode,{
    grid:{left:170,right:28,top:20,bottom:45},
    tooltip:{
      trigger:'item',
      renderMode:'richText',
      formatter:params=>{
        const item=series[params.dataIndex]?.trip;
        if(!item)return '';
        return item.trip_id
          +'\n'+item.vehicle_id
          +'\n'+item.origin+' → '+item.destination
          +'\nSalida: '+date(item.dispatch_date)
          +'\nLlegada: '+date(item.arrival_date)
          +'\nDisponible: '+date(item.resource_available_again);
      },
    },
    xAxis:{
      type:'value',
      min:0,
      max:Math.max(days,1),
      axisLabel:{
        formatter:value=>{
          const d=new Date(start+'T00:00:00Z');
          d.setUTCDate(d.getUTCDate()+Number(value));
          return date(d.toISOString().slice(0,10));
        },
      },
    },
    yAxis:{
      type:'category',
      inverse:true,
      data:categories,
      axisLabel:{width:160,overflow:'truncate'},
    },
    series:[
      {
        type:'bar',
        stack:'schedule',
        silent:true,
        itemStyle:{opacity:0},
        data:series.map(item=>item.offset),
      },
      {
        type:'bar',
        stack:'schedule',
        data:series.map(item=>item.duration),
        label:{show:false},
      },
    ],
  });

}

function renderService(root,result){
  const metrics=result.scenarios.selected.metrics;
  const outcomes=result.scenarios.selected.order_outcomes||[];
  const exceptions=result.exceptions||[];
  const sla=result.analysis?.sla_enabled;

  root.innerHTML=
    '<div class="dispatch-section-heading">'
      +'<div><span class="dispatch-kicker">NIVEL DE SERVICIO</span><h2>'+(sla?'Cumplimiento de fecha objetivo':'Calendario sin SLA')+'</h2>'
      +'<p>'+(sla?'La fecha objetivo domina la optimización antes de espera y makespan.':'delivery_due_date no participa en esta corrida; el motor minimiza espera y compacta el calendario.')+'</p></div>'
      +(sla?'<span class="dispatch-review-count '+(metrics.late_orders?'is-warning':'is-good')+'">'+pct(metrics.on_time_rate||0)+' a tiempo</span>':'')
    +'</div>'
    +'<div class="dispatch-schedule-kpis">'
      +'<div><small>Espera media</small><strong>'+num(metrics.avg_wait_days,2)+' días</strong></div>'
      +'<div><small>Calendario</small><strong>'+num(metrics.makespan_days)+' días</strong></div>'
      +'<div><small>Órdenes tardías</small><strong>'+num(metrics.late_orders)+'</strong></div>'
      +'<div><small>Días tardíos</small><strong>'+num(metrics.total_late_days)+'</strong></div>'
    +'</div>'
    +(sla
      ?'<div class="dispatch-table-wrap"><table><thead><tr><th>Orden</th><th>Ready</th><th>Primera salida</th><th>Llegada</th><th>Objetivo</th><th>Resultado</th></tr></thead><tbody>'
        +outcomes.map(item=>
          '<tr><td>'+esc(item.order_id)+'</td><td>'+date(item.ready_date)+'</td><td>'+date(item.first_dispatch_date)+'</td><td>'+date(item.arrival_date)+'</td><td>'+date(item.delivery_due_date)+'</td><td class="'+(item.late_days?'bad':'good')+'">'+(item.late_days?num(item.late_days)+' días tarde':'A tiempo')+'</td></tr>'
        ).join('')
        +'</tbody></table></div>'
      :'<p class="dispatch-model-note">'+num(outcomes.length)+' órdenes secuenciadas sin evaluación de fecha objetivo.</p>')
    +(exceptions.length
      ?'<div class="dispatch-review-card is-warning"><div><span class="dispatch-review-icon">!</span><div><strong>'+num(exceptions.length)+' excepción'+(exceptions.length===1?'':'es')+' de fecha objetivo</strong><p>La asignación upstream se mantuvo intacta. Revisá estas órdenes antes de aprobar la planificación.</p></div></div></div>'
      :'');
}

export function render(root,run,onRerun,caseActions={}){
  dispose(root);
  const result=run.result_json;
  const metrics=result.scenarios.selected.metrics;
  const {toolbar,drawer}=renderDashboardToolbar(run,caseActions);
  root.className='dispatch dispatch-dashboard dispatch-dashboard-focused dispatch-scheduling-dashboard d-decision-dashboard';
  root.innerHTML=toolbar
    +decisionRail(caseActions)
    +'<main class="dispatch-focus-main">'
      +'<section class="dispatch-panel dispatch-focus-hero">'
        +'<div class="dispatch-decision-hero">'
          +'<div class="dispatch-decision-copy"><span class="dispatch-kicker">DECISIÓN 02 · PLANIFICACIÓN RECOMENDADA</span><h1>'+num(metrics.total_trips)+' viajes secuenciados entre '+date(metrics.schedule_start)+' y '+date(metrics.schedule_end)+'</h1>'
          +'<p>Scheduling conserva la Assignment aprobada y decide únicamente cuándo puede ejecutarse cada viaje.</p></div>'
          +'<div class="dispatch-decision-status"><span class="dispatch-status-pill '+(metrics.late_orders?'is-warning':'is-good')+'">'+(metrics.late_orders?num(metrics.late_orders)+' órdenes con excepción':'Calendario factible')+'</span>'
            +'<div class="dispatch-decision-metrics">'
              +'<div><small>Espera media</small><strong>'+num(metrics.avg_wait_days,2)+' d</strong></div>'
              +'<div><small>Makespan</small><strong>'+num(metrics.makespan_days)+' d</strong></div>'
              +'<div><small>On time</small><strong>'+(metrics.on_time_rate==null?'Sin SLA':pct(metrics.on_time_rate))+'</strong></div>'
            +'</div>'
          +'</div>'
        +'</div>'
      +'</section>'
      +'<section class="dispatch-panel" id="scheduling-timeline"></section>'
      +'<section class="dispatch-panel" id="scheduling-service"></section>'
      +'<section class="dispatch-panel dispatch-focus-ai" id="dispatch-explanation"></section>'
    +'</main>'
    +'<button type="button" class="dispatch-ai-fab" data-chat aria-expanded="false" aria-label="Abrir Dation IA">'+iconSvg("sparkles","dispatch-action-icon")+'<strong>Dation IA</strong></button>'
    +'<aside class="dispatch-chat dispatch-panel" hidden aria-label="Chat de la planificación"></aside>'
    +drawer;

  renderTimeline(root.querySelector('#scheduling-timeline'),result);
  renderService(root.querySelector('#scheduling-service'),result);

  const explainRoot=root.querySelector('#dispatch-explanation');
  try{
    explanation.render(explainRoot,run);
  }catch(error){
    errorBox(explainRoot,error,()=>explanation.render(explainRoot,run));
  }

  function openChat(question=''){
    const aside=root.querySelector('.dispatch-chat');
    const fab=root.querySelector('[data-chat]');
    aside.hidden=false;
    root.classList.add('with-chat');
    fab?.setAttribute('aria-expanded','true');
    explanation.chat(aside,run,question);
  }

  scopeFor(root).listen(root,'dispatch:open-chat',event=>{
    openChat(event.detail?.question||'');
  });

  bindDecisionRail(root,caseActions);
  bindDashboardToolbar(root,run,{onRerun,caseActions});
  root.querySelector('[data-chat]').onclick=()=>{
    const aside=root.querySelector('.dispatch-chat');
    if(!aside.hidden){
      disposeScope(aside);aside.hidden=true;
      root.classList.remove('with-chat');
      root.querySelector('[data-chat]')?.setAttribute('aria-expanded','false');
      return;
    }
    openChat();
  };
}
