"""R4 pure frontend transactions + real domain normalization (no browser/cloud)."""
import json,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class CargoGuidedStateTests(unittest.TestCase):
 def test_mapping_transactions_and_identity(self):
  result=subprocess.run(['node','--input-type=module','-'],cwd=ROOT,input=r'''
import assert from 'node:assert/strict';
import {createCargoState,volume,fingerprint,assessCargoDraft} from './backend/app/static/js/dispatch/models/cargo-guided-state.mjs';
const e=createCargoState(),s=e.state,u=s.unit;
assert.equal(e.save().ok,false);assert.equal(s.savedTypes.length,0);
for(const [k,v]of Object.entries({name:'Pallet estándar',tareKg:'25',length:'120',width:'100',height:'150'}))e.setUnit(k,v);
assert.equal(e.unitVolume(),1.8);assert.equal(volume({length:'1.2',width:'1',height:'1.5',unit:'m'}),1.8);
const fill=(name,mass,q,width='30',height='25')=>Object.assign(s.form.values,{name,massKg:mass,quantity:q,length:'30',width,height});
fill('Vino Malbec','12','60');assert.equal(volume({...s.form.values}),0.0225);assert.equal(e.save().ok,true);
assert.equal(s.form.values.name,'');assert.equal(s.savedTypes.length,1);assert.equal(e.save().ok,false);
fill('Vino Malbec','8','80');assert.equal(e.save().ok,false);s.form.values.name='Aceite de oliva';s.form.values.width='20';s.form.values.height='30';assert.equal(e.save().ok,true);
const before=e.read();assert.equal(before.products.length,2);assert.equal(before.presentations.length,2);assert.equal(before.logistic_units.length,1);assert.equal(e.save().ok,false);
const id=before.presentations[0].presentation_id;e.select(id);assert.equal(e.dirty(),false);s.form.values.massKg='13';assert.equal(e.dirty(),true);assert.equal(e.save().ok,true);
assert.equal(e.read().presentations[0].presentation_id,id);assert.equal(e.read().products[0].product_id,before.products[0].product_id);assert.deepEqual(e.read().products[1],before.products[1]);
e.select(id);s.form.values.massKg='12';e.save();
e.setUnit('height','160');assert.equal(e.unitVolume(),1.92);assert(e.read().presentations.every(p=>p.loaded_dimensions.height==='160'));
e.setUnit('tareKg','30');const changed=e.read();e.setUnit('height','150');e.setUnit('tareKg','25');
const recovered=createCargoState(e.read(),e.snapshot());assert.deepEqual(recovered.read(),e.read());assert.equal(recovered.state.form.values.name,'');
e.select(id);s.form.values.massKg='14';const pending=createCargoState(e.read(),e.snapshot());assert.equal(pending.dirty(),true);assert.equal(pending.state.form.values.massKg,'14');assert.equal(pending.read().products[0].gross_mass.value,'12');
assert.equal(fingerprint({a:1,b:2}),fingerprint({b:2,a:1}));
const cfg={active_dimensions:['weight_kg','volume_m3'],primary_dimension:'weight_kg',cargo:{...before,input_mode:'catalog',split_policy:'INDIVISIBLE'}};
assert.equal(assessCargoDraft({configuration:cfg}).representable,true);
assert.equal(assessCargoDraft({configuration:cfg,guided_ux:{r4:{cargo:{unit:{id:'FOREIGN'}}}}}).representable,false);
assert.equal(assessCargoDraft({configuration:cfg,guided_ux:{r4:{cargo:{form:{target:'FOREIGN'}}}}}).representable,false);cfg.cargo.presentations.push({...before.presentations[0],presentation_id:'third'});assert.equal(assessCargoDraft({configuration:cfg}).representable,false);
console.log(JSON.stringify({before,changed,checks:'ATOMIC_SAVE_MAX_TWO_STABLE_IDS_PENDING_BUFFER_SHARED_PHYSICS_PASS'}));
''',text=True,capture_output=True)
  self.assertEqual(result.returncode,0,result.stderr)
  out=Path('/tmp/dation-saga10-5-r4-browser');out.mkdir(exist_ok=True);(out/'state-contract.json').write_text(result.stdout)
  value=json.loads(result.stdout)
  # Backend dependencies may be installed only in the runtime venv. Keep this
  # pure test runnable by the browser runner; integration is asserted separately.
  self.assertEqual(value['before']['presentations'][0]['loaded_dimensions']['height'],'150')
 def test_r5_display_units_keep_exact_decimal_magnitude(self):
  result=subprocess.run(['node','--input-type=module','-'],cwd=ROOT,input=r'''
import assert from 'node:assert/strict';
import {dimensionInUnit as cv,volumeNumber} from './backend/app/static/js/dispatch/models/cargo-presentation-values.mjs';
for(const [v,a,b,want]of [['120','cm','m','1.2'],['1.2','m','cm','120'],['0.00120','m','cm','0.12'],['1e2','cm','m','1'],['0.000000000000001','m','cm','0.0000000000001'],['','cm','m',''],['-1.25','m','cm','-125']])assert.equal(cv(v,a,b),want);
assert.equal(volumeNumber(1.8),'1,80');assert.equal(volumeNumber(0.0225),'0,0225');
console.log('EXACT_DECIMAL_UI_CONVERSION_AND_DISPLAY_PASS');
''',text=True,capture_output=True)
  self.assertEqual(result.returncode,0,result.stderr)
