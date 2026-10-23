function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}

/** Backend stages only; this indicator deliberately has no numeric progress. */
export function executionStageLabel(stage){
 const labels={registering:'Registrando la corrida',recovering:'Recuperando la corrida',queued:'En cola de ejecución',running:'Ejecutando motor',validating:'Validando datos y configuración',constructing:'Preparando la solución',summarizing:'Generando la recomendación'};
 return (String(stage).startsWith('optimizing:')?'Ejecutando motor':labels[stage]||String(stage||'Ejecución en curso')).toLocaleUpperCase('es');
}
export function renderExecutionProgress(root,stage){
 let panel=root.querySelector('[data-execution-progress]');
 if(!panel){
  panel=el('section',undefined,'dispatch-panel decision-execution');panel.dataset.executionProgress='';
  panel.append(el('span','EJECUCIÓN EN CURSO','dispatch-kicker'),el('h1','Preparando tu decisión'));
  const status=el('p',undefined,'decision-execution__stage');status.dataset.runStage='';status.setAttribute('role','status');status.setAttribute('aria-live','polite');panel.append(status);
  const bar=el('div',undefined,'decision-execution__progress');bar.setAttribute('role','progressbar');bar.setAttribute('aria-label','Ejecución en curso');bar.append(el('span'));panel.append(bar);
  panel.append(el('p','La corrida sigue activa. Podés recuperarla en este mismo Case si recargás la página.','d-metadata'));root.replaceChildren(panel);
 }
 const label=executionStageLabel(stage),status=panel.querySelector('[data-run-stage]');
 if(status.textContent!==label)status.textContent=label;
 panel.querySelector('[role=progressbar]').setAttribute('aria-valuetext',label);
}
