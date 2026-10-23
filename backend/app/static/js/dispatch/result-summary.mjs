import {esc} from './shared.mjs';

/** Present persisted result values consistently without parsing or truncating business text. */
export function decisionResultSummary({parts=[],supportingText='',headlineClass='',supportClass=''}){
 return '<div class="decision-result-summary"><p class="decision-result-summary__headline '+esc(headlineClass)+'">'
  +parts.map(part=>typeof part==='string'?esc(part):'<strong>'+esc(part.value)+'</strong>').join('')+'</p>'
  +(supportingText?'<p class="decision-result-summary__support '+esc(supportClass)+'">'+esc(supportingText)+'</p>':'')+'</div>';
}
