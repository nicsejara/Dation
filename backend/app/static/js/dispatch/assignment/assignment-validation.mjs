import {esc,num} from '../shared.mjs';
import {getApprovalWarnings} from './assignment-dashboard-selectors.mjs';

function card(item){
  return '<article data-approval-warning="'+esc(item.key)+'" class="assignment-validation__card is-'+esc(item.level)+'">'
    +'<div class="assignment-validation__card-top"><span>'+esc(item.label)+'</span><strong>'+esc(item.title)+'</strong></div>'
    +'<p>'+esc(item.detail)+'</p>'
  +'</article>';
}

export function render(root,result){
  const warnings=getApprovalWarnings(result);
  root.innerHTML='<span class="dispatch-kicker">VALIDACIÓN HUMANA</span>'
    +(warnings.length
      ?'<h2>'+num(warnings.length)+' observación'+(warnings.length===1?' requiere':'es requieren')+' revisión</h2>'
        +'<div class="assignment-validation__cards">'+warnings.map(card).join('')+'</div>'
      :'<div class="assignment-validation__empty"><span aria-hidden="true">✓</span><div>'
        +'<h2>Sin observaciones adicionales</h2><p>No se detectaron asignaciones que requieran controles u observaciones adicionales.</p>'
        +'</div></div>');
}
