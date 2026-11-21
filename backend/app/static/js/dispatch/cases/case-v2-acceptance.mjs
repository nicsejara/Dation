// Read-only result evidence. This projection never enables an approval action.
import {api} from '../shared.mjs';
import {el} from '../models/forms.mjs';
import {ensureStylesheet} from '../styles.mjs';

export async function mountCaseAcceptance(parent,scope,{caseId,runId=null}){
 await ensureStylesheet('decision-case-v2-styles','/static/css/decision-case-v2.css','j102-v1');if(!scope.active)return;
 const box=el('section',undefined,'d-card j102-acceptance');box.dataset.caseAcceptance='';
 box.append(el('h2','Cobertura y aprobación','d-card-title'));parent.append(box);
 try{const value=await api('/api/platform/logistics-cases/'+caseId+'/acceptance'+(runId?'?run_id='+encodeURIComponent(runId):''),{signal:scope.signal});if(!scope.active)return;
  box.dataset.acceptanceStatus=value.status;
  box.append(el('p',({PENDING:'Pendiente de D1',MEETS:'Cumple criterio',MISSES:'Resultado factible, pero no alcanzó el criterio de aceptación del Case.',NOT_EVALUABLE:'No evaluable',NOT_CONFIGURED:'No configurado'})[value.status]||'No evaluable','d-body'),el('p',value.reason||(value.numerator+' / '+value.denominator+' '+value.unit),'d-metadata'),el('p','La aprobación sigue el workflow humano de D1/D2. Este indicador no aprueba corridas.','d-metadata'));
  if(value.critical_coverage)box.append(el('p',value.critical_coverage.status==='NOT_APPLICABLE'?'Demanda crítica: no aplica; no hay demanda HIGH.':'Demanda crítica HIGH: '+value.critical_coverage.numerator+' / '+value.critical_coverage.denominator+' '+value.critical_coverage.unit,'d-metadata'));
 }catch(error){if(scope.active){box.dataset.acceptanceStatus='UNAVAILABLE';box.append(el('p','No se pudo verificar el criterio: '+error.message,'d-metadata'));}}
 return box;
}
