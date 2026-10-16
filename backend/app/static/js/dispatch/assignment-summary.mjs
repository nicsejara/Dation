import {esc,num,pct} from './shared.mjs';
import {iconSvg} from './decision-ui.mjs';
import {getAssignmentSummary,getAssignmentContext,getEssentialKpis,getDecisionNarrative,getApprovalWarnings} from './assignment-dashboard-selectors.mjs';

export const formatWeight=(value,compact=false)=>value==null?'—':value>=1000?num(value/1000,1)+(compact?' t':' toneladas'):num(value,1)+' kg';

export function render(root,result,{status}={}){
  const summary=getAssignmentSummary(result),context=getAssignmentContext(result);
  const own=getEssentialKpis(result).find(item=>item.key==='own_weight_share').value;
  const warnings=getApprovalWarnings(result),stale=['stale','superseded'].includes(status);
  const infeasible=warnings.some(item=>item.key==='infeasible');
  const attention=stale||infeasible||status!=='approved'&&warnings.length>0;
  const label=stale?'Requiere revisión: la corrida perdió vigencia':infeasible?'Escenario no factible':status==='approved'?'Decisión aprobada'
    :warnings.length?'Asignación para revisar':summary.feasible?'Decisión consistente':'Factibilidad no informada';
  root.innerHTML='<div class="assignment-hero__art" aria-hidden="true"><img src="/static/assets/assignment-hero-truck.webp" width="1659" height="948" alt="" decoding="async"></div>'
    +'<div class="assignment-hero__content"><span class="dispatch-kicker">DECISIÓN 01 · ASIGNACIÓN DE FLOTA</span>'
    +'<h1>Asignación recomendada</h1><span class="assignment-hero__status '+(infeasible?'is-error':attention?'is-review':'is-consistent')+'" data-assignment-hero-status>'
      +iconSvg(attention?'alertTriangle':'checkCircle','assignment-v2__icon')+'<span>'+esc(label)+'</span></span>'
    +'<p class="assignment-hero__headline">Mover <strong>'+esc(formatWeight(context.totalWeightKg))+'</strong> en <strong>'+num(summary.trips)+' viajes</strong>'
      +(own===null?'.':' utilizando <strong>'+pct(own).replace(' ','\u00a0')+' de flota propia</strong>.')+'</p>'
    +'<p class="assignment-hero__lead">'+esc(getDecisionNarrative(result))+'</p>'
    +'<details class="assignment-essential__objective"><summary>Objetivo de la corrida · '+esc(summary.objectiveLabel)+'</summary>'
      +'<div class="assignment-essential__objective-chips">'+(summary.objectiveWeights.length?summary.objectiveWeights.map(item=>
        '<span class="assignment-essential__objective-chip"><strong>'+esc(item.label)+'</strong><small>'+pct(item.weight)+'</small></span>'
      ).join(''):'<span>Sin ponderaciones publicadas</span>')+'</div></details></div>';
  const image=root.querySelector('img');
  image.onerror=()=>{image.hidden=true;root.querySelector('.assignment-hero__art').dataset.fallback='true';};
}
