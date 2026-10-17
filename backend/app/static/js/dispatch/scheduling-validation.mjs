import {esc,num,date} from './shared.mjs';
import {getSchedulingWarnings} from './scheduling-dashboard-selectors.mjs';
import {heading} from './scheduling-essential.mjs';
import {schedulingIcon as icon} from './scheduling-dashboard-shell.mjs';
export function render(root,result){
  const warnings=getSchedulingWarnings(result);
  root.innerHTML=heading('Validación humana')+(warnings.length?'<div class="scheduling-findings">'+warnings.map(w=>'<article class="is-'+esc(w.severity)+'">'+icon(w.severity==='critical'?'alertTriangle':w.severity==='warning'?'alertTriangle':'info')+'<div><h3>'+esc(w.title)+'</h3><p>'+esc(w.detail)+'</p></div></article>').join('')+'</div>':'<p class="scheduling-validation-ok">'+icon('checkCircle')+'No se detectaron conflictos de disponibilidad ni incumplimientos que requieran revisión.</p>');
  return warnings;
}
export function renderUnavailable(root,result){
  const warnings=getSchedulingWarnings(result),window=result.analysis?.planning_window||{};
  root.innerHTML='<span class="dispatch-kicker">DECISIÓN 02 · PLANIFICACIÓN DE DESPACHOS</span><h1>No existe una planificación factible</h1><p>No se puede aprobar este calendario. Revisá las restricciones publicadas y reconfigurá la planificación.</p><ul>'
    +warnings.map(w=>'<li><strong>'+esc(w.title)+':</strong> '+esc(w.detail)+'</li>').join('')+'</ul>'
    +'<p>Ventana: '+date(window.start)+' → '+date(window.end)+'. Assignment conserva '+num(result.inputs?.assignment?.trip_count)+' viajes aprobados.</p><details><summary>Ver detalle técnico</summary><pre>'+esc(JSON.stringify({solver:result.engine?.solver,decision:result.decision,exceptions:result.exceptions,planning_window:window},null,2))+'</pre></details>';
}
