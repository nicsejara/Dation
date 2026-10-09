import {esc,num} from './shared.mjs';
import {
  getApprovalWarnings,
  solverStatusLabel,
} from './assignment-dashboard-selectors.mjs?v=assignment-dashboard-phase2';

function engineEvidence(result){
  const selected=result?.scenarios?.selected||{};
  const exceptions=Array.isArray(result?.exceptions)?result.exceptions:[];
  const solverStatus=selected.solver?.status||result?.engine?.solver?.status||null;
  const items=[];

  if(selected.feasible===true){
    items.push({
      level:'good',
      label:'Persistido',
      title:'El escenario seleccionado fue publicado como factible',
      detail:'La interfaz informa el estado persistido del escenario; no replica las validaciones internas del motor.',
    });
  }else if(selected.feasible===false){
    items.push({
      level:'attention',
      label:'Atención',
      title:'El escenario seleccionado está marcado como no factible',
      detail:'Revisá la corrida antes de considerar una aprobación.',
    });
  }

  items.push({
    level:solverStatus==='infeasible'?'attention':'neutral',
    label:'Solver',
    title:'Estado del solver: '+solverStatusLabel(solverStatus),
    detail:'Se muestra el estado técnico persistido sin convertir una solución factible en “óptima”.',
  });

  items.push({
    level:exceptions.length?'attention':'good',
    label:exceptions.length?'Atención':'Persistido',
    title:exceptions.length
      ?num(exceptions.length)+' observación'+(exceptions.length===1?'':'es')+' publicada'+(exceptions.length===1?'':'s')+' por el motor'
      :'El motor no publicó observaciones adicionales en esta corrida',
    detail:exceptions.length
      ?'La corrida contiene evidencia adicional que conviene revisar antes de aprobar.'
      :'No se agrega una checklist artificial de controles que el resultado no expone explícitamente.',
  });

  return items;
}

function card(item){
  return '<article class="assignment-validation__card is-'+esc(item.level)+'">'
    +'<div class="assignment-validation__card-top"><span>'+esc(item.label)+'</span><strong>'+esc(item.title)+'</strong></div>'
    +'<p>'+esc(item.detail)+'</p>'
  +'</article>';
}

export function render(root,result){
  const engineItems=engineEvidence(result);
  const warnings=getApprovalWarnings(result).filter(item=>!['infeasible','engine_exceptions'].includes(item.key));

  root.innerHTML=
    '<div class="dispatch-section-heading assignment-validation__heading">'
      +'<div><span class="dispatch-kicker">VALIDACIÓN HUMANA</span><h2>Validá la asignación antes de aprobar</h2><p>Revisá los puntos que requieren criterio operativo. Dation muestra sólo controles y observaciones respaldados por la evidencia persistida de esta corrida.</p></div>'
      +'<span class="assignment-validation__status '+(warnings.length?'is-review':'is-good')+'">'+(warnings.length?'Revisar':'Sin observaciones')+'</span>'
    +'</div>'
    +'<div class="assignment-validation__grid">'
      +'<section aria-labelledby="assignment-engine-evidence-title">'
        +'<div class="assignment-validation__subhead"><span aria-hidden="true">✓</span><div><h3 id="assignment-engine-evidence-title">Evidencia del motor</h3><p>Estados publicados por la corrida, sin recalcular reglas en el frontend.</p></div></div>'
        +'<div class="assignment-validation__cards">'+engineItems.map(card).join('')+'</div>'
      +'</section>'
      +'<section aria-labelledby="assignment-human-review-title">'
        +'<div class="assignment-validation__subhead"><span aria-hidden="true">◎</span><div><h3 id="assignment-human-review-title">Puntos de revisión humana</h3><p>Situaciones que pueden ser válidas, pero conviene confirmar antes de congelar la asignación.</p></div></div>'
        +'<div class="assignment-validation__cards">'
          +(warnings.length
            ?warnings.map(card).join('')
            :'<article class="assignment-validation__card is-good"><div class="assignment-validation__card-top"><span>Sin observaciones</span><strong>No aparecen puntos adicionales de revisión humana</strong></div><p>No se registran viajes tercerizados, anomalías incluidas ni órdenes divididas en la evidencia seleccionada.</p></article>')
        +'</div>'
      +'</section>'
    +'</div>'
    +'<p class="assignment-validation__approval-note">Al aprobar, esta asignación queda congelada como entrada para Planificación. Dation IA puede ayudar a interpretarla, pero no es requisito para aprobar.</p>';
}
