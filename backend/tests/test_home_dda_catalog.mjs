import assert from 'node:assert/strict';
import test from 'node:test';
import {DDA_CATALOG,DDA_CATEGORIES,catalogCounts,filterCatalog,catalogAccess} from '../app/static/js/home-dda-catalog.mjs';
import {ddaEnabled,logisticsView} from '../app/static/js/platform/entitlements.mjs';

test('only the available logistics capability has a destination',()=>{
  assert.deepEqual(catalogCounts(),{available:1,comingSoon:6});
  assert.equal(new Set(DDA_CATALOG.map(item=>item.id)).size,7);
  assert.deepEqual(DDA_CATALOG.filter(item=>item.status==='available').map(item=>item.targetView),['logistics-overview']);
  for(const item of DDA_CATALOG.filter(item=>item.status==='coming-soon'))assert.equal(item.targetView,undefined);
  for(const item of DDA_CATALOG){
    assert.ok(DDA_CATEGORIES.some(category=>category.id===item.category));
    assert.equal(item.capabilities.length,3);
  }
});

test('filters group real capabilities into the requested operational areas',()=>{
  const expected={all:['logistics','production','inventory','demand','procurement','maintenance','pricing'],
    'supply-chain':['logistics','inventory'],operations:['procurement'],production:['production'],
    commercial:['demand','pricing'],assets:['maintenance']};
  for(const [category,ids] of Object.entries(expected))assert.deepEqual(filterCatalog(category).map(item=>item.id),ids);
  assert.deepEqual(filterCatalog('unknown'),[]);
});

test('portfolio totals and filtering grow with the registry without fixed card counts',()=>{
  const extended=[...DDA_CATALOG,{id:'future',status:'coming-soon',category:'operations'}];
  assert.deepEqual(catalogCounts(extended),{available:1,comingSoon:7});
  assert.equal(filterCatalog('all',extended).length,8);
  assert.deepEqual(filterCatalog('operations',extended).map(item=>item.id),['procurement','future']);
  assert.deepEqual(catalogCounts([]),{available:0,comingSoon:0});
});

test('workspace entitlement cannot activate an unavailable product or another workspace',()=>{
 const identity={membership:{workspace_id:'A'},ddas:[{workspace_id:'A',dda_id:'logistics',status:'enabled'},
  {workspace_id:'A',dda_id:'production',status:'enabled'}]};
 assert.equal(catalogAccess(DDA_CATALOG[0],identity),'enabled');
 assert.equal(catalogAccess(DDA_CATALOG[1],identity),'coming_soon');
 assert.equal(ddaEnabled(identity,'production'),false);
 for(const status of ['disabled','coming_soon','trial',undefined]){
  const changed={...identity,ddas:[{workspace_id:'A',dda_id:'logistics',status}]};
  assert.equal(catalogAccess(DDA_CATALOG[0],changed),'disabled');
 }
 assert.equal(catalogAccess(DDA_CATALOG[0],{...identity,membership:{workspace_id:'B'}}),'disabled');
 assert.equal(catalogAccess(DDA_CATALOG[0],null),'disabled');
 assert.equal(DDA_CATALOG.find(item=>item.id==='procurement').entitlementId,'purchasing');
});

test('all existing business route aliases require Logistics; platform screens remain accessible',()=>{
 for(const view of ['overview','logistics-overview','logistics-map','logistics-data','logistics-config','decision-dashboard','traceability','library'])assert.equal(logisticsView(view),true,view);
 for(const view of ['platform-home','inicio','platform-decisions','platform-data','platform-team','settings','profile'])assert.equal(logisticsView(view),false,view);
});
