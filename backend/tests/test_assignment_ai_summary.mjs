import test from 'node:test';
import assert from 'node:assert/strict';
import {getExecutiveBrief,briefText} from '../app/static/js/dispatch/assignment-dashboard-selectors.mjs';
const explanation={executive_summary:'La recomendación conserva el resultado publicado.',why_recommended:'Las prioridades pertenecen a la corrida.',
 key_drivers:['Carga propia publicada','Utilización publicada'],tradeoffs:['El costo se compara con una referencia factible.'],
 recommendation:'Revisar la disponibilidad en Planificación.',caveats:['Assignment no calcula fechas.']};
test('POST and persisted interpretation produce the same narrative without recalculating metrics',()=>{
 const direct=getExecutiveBrief({explanation}),stored=getExecutiveBrief({explanation:{response_json:explanation}});
 assert.deepEqual(direct,stored);assert.equal(direct.lead,explanation.executive_summary);assert.equal(direct.drivers.length,2);
 assert.match(briefText(stored),/Assignment no calcula fechas/);
});
test('brief accepts historical summary names and explicit impact text, never stringifies objects',()=>{
 assert.equal(getExecutiveBrief({summary:'Resumen histórico'}).lead,'Resumen histórico');
 assert.equal(getExecutiveBrief({business_impact:{cost:'Costo informado',trips:'Viajes informados',distance:{not:'narrative'}}}).lead,'Costo informado Viajes informados');
 assert.equal(getExecutiveBrief({executive_summary:{unknown:1}}).lead,'');
});
test('narrative limits drivers and tradeoffs, deduplicates review, and leaves payload unchanged',()=>{
 const data={...explanation,key_drivers:Array.from({length:9},(_,i)=>'Evento '+i),recommendation:'Revisar',caveats:['Revisar','Límite']};
 const before=structuredClone(data),brief=getExecutiveBrief(data);assert.equal(brief.drivers.length,3);assert.deepEqual(brief.review,['Revisar','Límite']);assert.deepEqual(data,before);
});
test('empty or malformed AI responses stay empty instead of inventing an executive conclusion',()=>{
 for(const data of [null,undefined,{}, {executive_summary:null},{executive_summary:7}])assert.equal(getExecutiveBrief(data).lead,'');
});
