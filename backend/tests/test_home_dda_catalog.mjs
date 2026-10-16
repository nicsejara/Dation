import assert from 'node:assert/strict';
import test from 'node:test';
import {DDA_CATALOG,DDA_CATEGORIES,catalogCounts,filterCatalog} from '../app/static/js/home-dda-catalog.mjs';

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
