"""Pure necessary-volume check and R4 transactions; no cloud or engine calls."""
import subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class R6VolumeTests(unittest.TestCase):
 def test_decimal_frontiers_fixtures_and_atomic_saved_types(self):
  result=subprocess.run(['node','--input-type=module','-'],cwd=ROOT,text=True,capture_output=True,input=r'''
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {evaluateCoherence as check} from './backend/app/static/js/dispatch/models/cargo-volume-coherence.mjs';
import {createCargoState} from './backend/app/static/js/dispatch/models/cargo-guided-state.mjs';
const dir='./backend/tests/browser/fixtures/r6/',records=[];
for(const file of ['fixture_A_wine_60.json','fixture_B_wine_90_over.json','fixture_C_wine_80_equal.json','fixture_D_pallet_2_52.json']){
 const f=JSON.parse(fs.readFileSync(dir+file)),u={type:f.logistic_unit.type,...f.logistic_unit.dimensions,measure:f.logistic_unit.dimensions.unit},v={...f.product.dimensions,packageType:f.product.package_type,quantity:f.product.quantity},r=check(u,v);
 for(const [key,want]of Object.entries(f.expected)){const mapped={exterior_m3:'exterior',nominal_bulto_m3:'individual',nominal_total_m3:'total',ratio:'ratio',blocking:'blocking'}[key];if(mapped)typeof want==='number'?assert(Math.abs(r[mapped]-want)<1e-14,JSON.stringify(r)):assert.equal(r[mapped],want);}
 if(f.expected.warning)assert.equal(r.status,'warning_equal');records.push({fixture:file,...r});
}
const u={type:'PALLET',length:'120',width:'100',height:'150',measure:'cm'},v={length:'30',width:'30',height:'25',unit:'cm',quantity:'60',packageType:'caja'};
assert.deepEqual(check(u,v),check({...u,length:'1.2',width:'1',height:'1.5',measure:'m'},v));
for(const packageType of ['bolsa','saco','fardo','bulto','otra']){const r=check(u,{...v,quantity:'90',packageType});assert.equal(r.blocking,false);assert.equal(r.status,'unverified');}
for(const quantity of ['',0,-1,'Infinity','1.5','9007199254740992'])assert.equal(check(u,{...v,quantity}).status,'pending');
for(const length of ['','0','-3','Infinity','NaN'])assert.equal(check({...u,length},v).status,'pending');
assert.equal(check(u,{...v,length:'3e1'}).ratio,0.75);
// Exact decimal comparison: 1e-12 relative band, no display rounding involved.
const one={type:'OTHER',exteriorVolume:'1'},base={...v,length:'100',width:'100',height:'100',quantity:'1'};
assert.equal(check(one,base).status,'warning_equal');
assert.equal(check({...one,exteriorVolume:'0.9999999999999'},base).status,'warning_equal');
assert.equal(check({...one,exteriorVolume:'0.999999999998'},base).status,'invalid_rigid');
assert.equal(check({...one,exteriorVolume:'1.000000000002'},base).status,'informational');
assert.equal(check(u,{...v,length:'30.00000000000001'}).blocking,false);
const engine=createCargoState(),s=engine.state;
Object.assign(s.unit,{type:'PALLET',name:'Pallet',tareKg:'25',length:'120',width:'100',height:'150',measure:'cm'});
Object.assign(s.form.values,{...v,name:'Vino',massKg:'12',quantity:'60'});assert.equal(engine.save().ok,true);
Object.assign(s.form.values,{...v,name:'Aceite',massKg:'8',quantity:'90'});const buffer=structuredClone(s.form),before=engine.read();assert.equal(engine.save().ok,false);assert.deepEqual(s.form,buffer);assert.deepEqual(engine.read(),before);
s.form.values.quantity='80';s.form.values.width='20';s.form.values.height='30';assert.equal(engine.save().ok,true);const ids=engine.read().presentations.map(p=>p.presentation_id);
engine.setUnit('height','115');assert.equal(engine.coherence(engine.formFrom(s.savedTypes[0])).blocking,false);assert.equal(engine.coherence(engine.formFrom(s.savedTypes[1])).blocking,true);assert.match(engine.validate(),/Aceite/);assert.deepEqual(engine.read().presentations.map(p=>p.presentation_id),ids);
engine.select(ids[1]);s.form.values.quantity='70';assert.equal(engine.save().ok,true);assert.equal(engine.validate(),'');assert.deepEqual(engine.read().presentations.map(p=>p.presentation_id),ids);assert.equal(engine.save().ok,false);
console.log(JSON.stringify({checks:'R6_EXACT_RELATIVE_1E12_FRONTIERS_FLEXIBLES_ATOMIC_BUFFER_STABLE_IDS_PASS',records},null,2));
''')
  self.assertEqual(result.returncode,0,result.stderr)
  out=Path('/tmp/dation-r6-browser');out.mkdir(exist_ok=True);(out/'volume-unit.json').write_text(result.stdout)
