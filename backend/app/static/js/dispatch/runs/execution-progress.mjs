function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}

/** Worker stages are evidence of progress, never an estimated percentage. */
export function executionStageLabel(stage){
 const labels={registering:'Registrando la corrida',recovering:'Recuperando la corrida',queued:'En cola de ejecución',running:'Ejecutando motor',validating:'Validando datos y configuración',constructing:'Preparando la solución',summarizing:'Generando la recomendación',completed:'Decisión lista'};
 return (String(stage).startsWith('optimizing:')?'Ejecutando motor':labels[stage]||String(stage||'Ejecución en curso')).toLocaleUpperCase('es');
}
export function executionStageIndex(stage){
 if(stage==='validating')return 0;
 if(stage==='constructing'||String(stage).startsWith('optimizing:'))return 1;
 if(stage==='summarizing')return 2;
 if(stage==='completed')return 3;
 return null; // Admission/recovery/running alone do not prove any stage completed.
}
export function renderExecutionProgress(root,stage,{runId}={}){
 let panel=root.querySelector('[data-execution-progress]');
 if(!panel){
  panel=el('section',undefined,'dispatch-panel decision-execution');panel.dataset.executionProgress='';
  panel.append(el('span','EJECUCIÓN EN CURSO','dispatch-kicker'),el('h1','Preparando tu recomendación'));
  const flow=el('ol',undefined,'decision-engine-flow');flow.setAttribute('aria-label','Decision Engine Flow');
  for(const title of ['Datos','Motor','Evidencia','Resultado']){
   const node=el('li');node.dataset.engineNode='';
   const marker=el('span',undefined,'decision-engine-flow__marker');marker.setAttribute('aria-hidden','true');
   const state=el('small','Pendiente');state.dataset.engineState='';
   node.append(marker,el('strong',title),state);flow.append(node);
  }
  panel.append(flow);
  const status=el('p',undefined,'decision-execution__stage');status.dataset.runStage='';status.setAttribute('role','status');status.setAttribute('aria-live','polite');status.setAttribute('aria-atomic','true');panel.append(status);
  panel.append(el('p','Dation está procesando esta corrida con la configuración seleccionada.','decision-execution__support'));
  panel.append(el('p','Podés recuperar esta misma corrida desde el Case si recargás la página.','d-metadata'));
  if(runId)panel.append(el('code','Run '+String(runId).slice(0,8)));
  root.replaceChildren(panel);
 }
 const index=executionStageIndex(stage),complete=stage==='completed';
 panel.querySelector('h1').textContent=complete?'Decisión lista':'Preparando tu recomendación';
 panel.querySelector('.dispatch-kicker').textContent=complete?'EJECUCIÓN COMPLETADA':'EJECUCIÓN EN CURSO';
 const label=executionStageLabel(stage),status=panel.querySelector('[data-run-stage]');
 if(status.textContent!==label)status.textContent=label;
 panel.querySelectorAll('[data-engine-node]').forEach((node,i)=>{
  const state=complete||index!==null&&i<index?'complete':i===index?'active':'pending';
  node.dataset.state=state;
  if(state==='active')node.setAttribute('aria-current','step');else node.removeAttribute('aria-current');
  node.querySelector('[data-engine-state]').textContent=state==='complete'?'Completado':state==='active'?'En curso':'Pendiente';
 });
}
