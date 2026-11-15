import test from 'node:test';
import assert from 'node:assert/strict';
import {visualState,dependencyActive,possibleActions,checkedTarget} from '../app/static/js/dispatch/graph-ux05/status-presentation.mjs';
const cid='case-a',id='logistics_assignment';
const target=(view,run_id=null)=>({allowed:true,target:{view,case_id:cid,node_id:id,run_id}});
const node=(node_state,extra={})=>({id,node_state,freshness:'CURRENT',approved_run_id:'approved',actions:{configure:target('logistics-config'),new_run:target('logistics-config'),result:{allowed:false}},...extra});
for(const state of ['READY','DATA_REQUIRED','IN_PROGRESS','COMPLETED','UNKNOWN'])test(state+' remains pending without granting execution',()=>assert.equal(visualState(node(state)).label,'Pendiente'));
for(const state of ['LOCKED','COMING_SOON','NOT_APPLICABLE'])test(state+' is visually blocked without changing applicability',()=>assert.equal(visualState(node(state)).label,'Bloqueada'));
test('approval requires current server state and identity; permissions do not redefine it',()=>{
 assert.equal(visualState(node('APPROVED')).label,'Aprobada');
 for(const x of [{freshness:'STALE'},{freshness:'UNKNOWN'},{approved_run_id:null},{technical_failure:'ERROR'}])assert.equal(visualState(node('APPROVED',x)).label,'Pendiente');
 assert.equal(visualState(node('APPROVED',{actions:{configure:{allowed:false}}})).label,'Aprobada');
});
test('dependency activation needs the exact approved upstream',()=>{assert.equal(dependencyActive(node('APPROVED'),{upstream_run_id:'approved'}),true);assert.equal(dependencyActive(node('APPROVED'),{upstream_run_id:'other'}),false);assert.equal(dependencyActive(node('APPROVED',{freshness:'STALE'}),{upstream_run_id:'approved'}),false);});
test('targets fail closed across cases, nodes, views and absent run identities',()=>{
 assert.equal(checkedTarget(target('decision-dashboard'),cid,id),null);
 for(const x of [{case_id:'elsewhere'},{node_id:'elsewhere'},{view:'https://evil.test'}]){const a=target('decision-dashboard','run');Object.assign(a.target,x);assert.equal(checkedTarget(a,cid,id),null);}
 assert.deepEqual(checkedTarget(target('decision-dashboard','run'),cid,id),{view:'decision-dashboard',caseId:cid,nodeId:id,runId:'run'});
});
test('result CTA preserves exact run and new run only returns to configuration',()=>{
 for(const [state,label]of [['IN_PROGRESS','Ver ejecución'],['COMPLETED','Ver resultados y aprobar'],['APPROVED','Ver dashboard']]){const n=node(state);n.actions.result=target('decision-dashboard','exact');const a=possibleActions(n,cid,{canApprove:true});assert.equal(a.primary.label,label);assert.equal(a.primary.target.runId,'exact');assert.equal(a.secondary[0].target.view,'logistics-config');}
});
test('stale/errors remain historical reads and viewer receives no approval affordance',()=>{const n=node('COMPLETED',{freshness:'STALE'});n.actions.result=target('decision-dashboard','old');assert.equal(possibleActions(n,cid).primary.label,'Ver dashboard histórico');n.freshness='CURRENT';assert.equal(possibleActions(n,cid).primary.label,'Ver resultados');});
test('archived and inapplicable nodes never expose a new execution',()=>{assert.equal(possibleActions(node('READY'),cid,{archived:true}).primary,null);assert.equal(possibleActions(node('NOT_APPLICABLE'),cid).primary,null);assert.equal(possibleActions(node('LOCKED'),cid).secondary.length,0);});

test('action kinds require canonical view and blocked states keep history-only affordances',()=>{
 for(const state of ['LOCKED','NOT_APPLICABLE','COMING_SOON']){const n=node(state);n.actions.result=target('decision-dashboard','old');assert.equal(possibleActions(n,cid).primary,null);}
 const n=node('READY');n.actions.result=target('logistics-config');n.actions.configure=target('decision-dashboard','wrong');n.actions.new_run=target('decision-dashboard','wrong');assert.deepEqual(possibleActions(n,cid),{primary:null,secondary:[]});
 const archived=node('APPROVED');archived.actions.result=target('decision-dashboard','approved');assert.equal(possibleActions(archived,cid,{archived:true}).primary.target.runId,'approved');assert.equal(possibleActions(archived,cid,{archived:true}).secondary.length,0);
});
