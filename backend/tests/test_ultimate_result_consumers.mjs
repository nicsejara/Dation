import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {PackageClient,readPackage,executiveKpis,sankeyLayout,ganttLayout} from '../app/static/js/dispatch/results/package.mjs';
import {pageRows,display,tableMarkup,alternativesMarkup} from '../app/static/js/dispatch/results/details.mjs';
import {sankeyMarkup,ganttMarkup} from '../app/static/js/dispatch/results/visuals.mjs';
import {downloadRunExport} from '../app/static/js/dispatch/runs/export.mjs';
const fixture=JSON.parse(readFileSync(new URL('./fixtures/ultimate/consumers.json',import.meta.url)));
const run=key=>({id:fixture[key].package.decision.run_id,result_fingerprint:fixture[key].package.fingerprints.result_fingerprint,result_json:structuredClone(fixture[key].package)});
const binding=r=>({run_id:r.id,result_fingerprint:r.result_fingerprint});
test('schema-aware reader rejects unknown/schema mismatch/wrong Run and preserves exact values',()=>{
  const r=run('d1');assert.equal(readPackage(r).metrics.capacity_utilization.weighted_ratio,'0.5385');
  assert.throws(()=>readPackage({...r,result_json:{...r.result_json,result_schema:'unknown'}}),/UNSUPPORTED_RESULT_SCHEMA/);
  assert.throws(()=>readPackage({...r,id:'another-run'}),/RESULT_FINGERPRINT_MISMATCH/);
  assert.throws(()=>readPackage({...r,result_fingerprint:'0'.repeat(64)}),/RESULT_FINGERPRINT_MISMATCH/);
  assert.throws(()=>readPackage(r,{package:r.result_json,provenance:binding(r),approval_overlay:{...binding(r),result_fingerprint:'bad'}}),/MISMATCH/);
});
test('executive KPIs copy certified weighted utilization, cost and expected compliance without recomputation',()=>{
  const r=run('d1'),before=JSON.stringify(r.result_json),kpis=executiveKpis(readPackage(r));
  assert.equal(kpis.length,5);assert.equal(kpis.find(k=>k[0]==='capacity_utilization')[2],'0.5385');assert.deepEqual(kpis[0][2],{amount:'100',currency:'ARS'});assert.equal(JSON.stringify(r.result_json),before);
  const p=run('d2').result_json;p.metrics.on_time_ratio='1';p.summary.facts.strict_on_time_ratio='0.75';
  assert.equal(executiveKpis(p).find(k=>k[0]==='on_time_ratio')[2],'1');
});
test('null cost and zero remain distinct',()=>{const p=run('d1').result_json;p.metrics.total_cost=null;p.metrics.resources_used=0;const k=executiveKpis(p);assert.equal(k[0][2],null);assert.equal(k[4][2],0);assert.equal(display(null),'No informado');assert.equal(display(0),'0');});
test('Sankey layout preserves both backend cuts and exact flows without residual Trip or coverage derivation',()=>{
  const p=run('d1').result_json.primary_visual.projection,l=sankeyLayout(p);assert.equal(l.nodes.length,p.nodes.length);assert.equal(l.links.length,p.links.length);assert.deepEqual(l.links.map(x=>x.value),p.links.map(x=>x.value));assert.equal(l.links[0].width,l.links[1].width);assert.ok(sankeyMarkup(p).includes('Las dos capas representan la misma demanda'));assert.ok(sankeyMarkup(p).includes('Lista accesible'));
});
test('Gantt layout uses certified boundaries, exclusive own end and external arrival beyond horizon without clipping',()=>{
  const p={planning_start:'2026-11-02',planning_end:'2026-11-08',rows:[{resource_id:'OWN',label:'OWN',source:'OWN'},{resource_id:'EXT',label:'EXT',source:'EXTERNAL'}],items:[
    {trip_id:'A',resource_id:'OWN',dispatch_date:'2026-11-02',arrival_date:'2026-11-09',occupancy_start:'2026-11-02',occupancy_end:'2026-11-12',status:'ON_TIME'},
    {trip_id:'B',resource_id:'EXT',dispatch_date:'2026-11-03',arrival_date:'2026-11-10',occupancy_start:null,occupancy_end:null,status:'ON_TIME'}]};
  const before=JSON.stringify(p),l=ganttLayout(p);assert.equal(new Date(l.end).toISOString().slice(0,10),'2026-11-12');assert.equal(l.items[0].endX,720);assert.ok(l.items[1].endX<720);assert.equal(JSON.stringify(p),before);const markup=ganttMarkup(p);assert.ok(markup.includes('fin exclusivo'));assert.ok(markup.includes('sin retorno modelado'));assert.ok(markup.includes('2026-11-10'));
});
test('tables only search/filter/sort the explicit page and preserve certified status',()=>{
  const rows=[{trip_id:'B',status:'AT_RISK',margin_days:0},{trip_id:'A',status:'PRE_HORIZON_DISPATCH_REQUIRED',margin_days:-2},{trip_id:'C',status:'UNSCHEDULED',margin_days:null}],before=JSON.stringify(rows);
  assert.deepEqual(pageRows(rows,{sort:'margin_days'}).map(r=>r.trip_id),['A','B','C']);assert.equal(pageRows(rows,{search:'AT_RISK'})[0].status,'AT_RISK');assert.equal(JSON.stringify(rows),before);
});
test('client initial result is one bounded request, fingerprint bound; no details/evidence/IA preload',async()=>{
  const r=run('d1'),requests=[],old=globalThis.fetch;globalThis.fetch=async url=>{requests.push(String(url));return Response.json({package:r.result_json,provenance:binding(r),approval_overlay:binding(r)});};
  try{const client=new PackageClient(r);assert.equal(requests.length,0);readPackage(r,await client.result());assert.equal(requests.length,1);assert.ok(requests[0].includes('/result?'));assert.ok(requests[0].includes(r.result_fingerprint));}finally{globalThis.fetch=old;}
});
test('selected entity races discard late response and wrong entity/Run evidence fails closed',async()=>{
  const r=run('d1'),old=globalThis.fetch;let resolveA;
  globalThis.fetch=url=>String(url).includes('/A?')?new Promise(resolve=>{resolveA=resolve;}):Promise.resolve(Response.json({provenance:binding(r),entity:{entity_type:'TRIP',entity_id:'B'}}));
  try{const client=new PackageClient(r),a=client.select('TRIP','A');const rejected=assert.rejects(a,{name:'AbortError'});const b=await client.select('TRIP','B');assert.equal(b.selected.entity_id,'B');resolveA(Response.json({provenance:binding(r),entity:{entity_type:'TRIP',entity_id:'A'}}));await rejected;
    globalThis.fetch=async()=>Response.json({provenance:{...binding(r),run_id:'other'},entity:{entity_type:'TRIP',entity_id:'B'}});await assert.rejects(client.select('TRIP','B'),/FINGERPRINT_MISMATCH/);
    globalThis.fetch=async()=>Response.json({provenance:binding(r),entity:{entity_type:'TRIP',entity_id:'A'}});await assert.rejects(client.select('TRIP','B'),/SELECTED_ENTITY_MISMATCH/);
  }finally{globalThis.fetch=old;}
});
test('COMPARE preserves multiple published IDs and selection from another Run never sends a request',async()=>{
  const r=run('d1'),old=globalThis.fetch,requests=[];globalThis.fetch=async url=>{requests.push(String(url));return Response.json({context:{provenance:binding(r)}});};
  try{const client=new PackageClient(r);await client.context('COMPARE',null,['ALT1','ALT2']);assert.deepEqual(new URL(requests[0],'http://fixture').searchParams.getAll('alternative_ids'),['ALT1','ALT2']);assert.throws(()=>client.context('EXPLORE',{...binding(r),run_id:'other',entity_type:'TRIP',entity_id:'A'}),/MISMATCH/);assert.equal(requests.length,1);}finally{globalThis.fetch=old;}
});
test('untrusted labels are escaped in charts and details',()=>{
 const p=run('d1').result_json,v=structuredClone(p.primary_visual.projection);v.nodes[0].label='<img src=x onerror=alert(1)>';assert.ok(!sankeyMarkup(v).includes('<img'));const markup=tableMarkup('evidence',p,{rows:[{entity_type:'TRIP',entity_id:'A',facts:{label:'<script>bad</script>'},reason_refs:[]}]});assert.ok(!markup.includes('<script>'));assert.ok(markup.includes('&lt;script&gt;'));
});
test('published alternatives render only certified metrics/deltas and exact selection IDs',()=>{
  const p=JSON.parse(readFileSync(new URL('./fixtures/ultimate/consumer_alternatives.json',import.meta.url))).package;
  const before=JSON.stringify(p),markup=alternativesMarkup(p,'COMPUTED');assert.equal(p.alternatives.length,1);
  for(const alt of p.alternatives){assert.ok(markup.includes('data-compare="'+alt.alternative_id+'"'));assert.ok(markup.includes(alt.policy));assert.ok(markup.includes(String(alt.difference_vs_recommended.trip_delta)));}
  assert.equal(JSON.stringify(p),before);assert.equal((alternativesMarkup({...p,alternatives:[]},'BUDGET_LIMIT').match(/data-compare/g)||[]).length,0);
});
test('Sankey controls carry published graph IDs independently of their display labels',()=>{
  const v=structuredClone(fixture.d1.package.primary_visual.projection),trip=v.nodes.find(n=>n.type==='TRIP');trip.label='Nombre visible sin identidad de dominio';const html=sankeyMarkup(v);
  assert.equal((html.match(new RegExp('data-graph-node="'+trip.id+'"','g'))||[]).length,2);assert.ok(html.includes('Nombre visible'));
});
test('large decimal money and numeric ordering preserve certified cents and negative margins',()=>{
  assert.ok(display({amount:'9007199254740992.01',currency:'ARS'},'money').endsWith(',01'));
  const rows=[{cost:{amount:'9007199254740992.02'}},{cost:{amount:'9007199254740992.01'}}];assert.deepEqual(pageRows(rows,{sort:'cost'}).map(r=>r.cost.amount),['9007199254740992.01','9007199254740992.02']);
  assert.deepEqual(pageRows([{margin:'-1.1'},{margin:'-2'},{margin:'-1.01'}],{sort:'margin'}).map(r=>r.margin),['-2','-1.1','-1.01']);
});
test('empty and dense primary visuals retain accessible representation without manufacturing trips',()=>{
  assert.ok(sankeyMarkup({type:'SANKEY',value_dimension:'pallets',nodes:[],links:[]}).includes('No hay flujos publicados'));
  const projection={type:'SANKEY',value_dimension:'pallets',nodes:Array.from({length:120},(_,i)=>({id:'NODE-'+i,type:'TRIP',label:'T-'+String(i).padStart(126,'0')})),links:[]};
  assert.equal(sankeyLayout(projection).nodes.length,120);assert.ok(sankeyLayout(projection).height>500);assert.ok(sankeyMarkup(projection).includes('Lista accesible'));
  assert.ok(ganttMarkup({planning_start:'2026-11-02',planning_end:'2026-11-08',rows:[],items:[]}).includes('No hay barras de viajes programados'));
});
test('full JSON export failure is explicit and never downloads a partial file',async()=>{
  const old=globalThis.fetch;globalThis.fetch=async()=>Response.json({detail:'ARTIFACT_MISSING'},{status:409});
  try{await assert.rejects(downloadRunExport(run('d2'),'json'),/Falta un artifact.*No se generó el archivo completo/);}finally{globalThis.fetch=old;}
});
test('concurrent trips on the same resource remain separately visible without inventing units or dates',()=>{
  const trip={resource_id:'OWN',dispatch_date:'2026-11-02',arrival_date:'2026-11-03',occupancy_start:'2026-11-02',occupancy_end:'2026-11-06',status:'ON_TIME'};
  const p={planning_start:'2026-11-02',planning_end:'2026-11-08',rows:[{resource_id:'OWN',label:'OWN',source:'OWN'}],items:[{...trip,trip_id:'A'},{...trip,trip_id:'B'}]},before=JSON.stringify(p),layout=ganttLayout(p);
  assert.equal(layout.rows.length,1);assert.notEqual(layout.items[0].y,layout.items[1].y);assert.equal(layout.items[0].x,layout.items[1].x);assert.equal(layout.items[0].endX,layout.items[1].endX);assert.equal(JSON.stringify(p),before);
  assert.equal((ganttMarkup(p).match(/data-entity-type="TRIP"/g)||[]).length,4);
});
