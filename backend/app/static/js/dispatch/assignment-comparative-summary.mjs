import {esc,num} from './shared.mjs';
import {getComparableScenarios,getAssignmentSummary,solverStatusLabel} from './assignment-dashboard-selectors.mjs';

export function render(root,result){
  const summary=getAssignmentSummary(result);
  const count=getComparableScenarios(result).length;
  root.innerHTML='<div class="assignment-comparative-summary__copy">'
    +'<span class="assignment-dashboard-v2__eyebrow">ANÁLISIS COMPARATIVO AVANZADO</span>'
    +'<h2>Profundizá la lectura de la decisión</h2>'
    +'<p>'+num(count)+' escenarios de referencia para explorar diferencias y trade-offs. La recomendación y su aprobación se conservan.</p>'
    +'<div class="assignment-comparative-summary__status">'
      +'<span><small>Objetivo original</small><strong>'+esc(summary.objectiveLabel)+'</strong></span>'
      +'<span><small>Estado del solver de la recomendación</small><strong>'+esc(solverStatusLabel(summary.solverStatus))+'</strong></span>'
    +'</div></div>';
}
