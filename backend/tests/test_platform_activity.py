"""Human attribution and CSV compatibility against the existing JS exporter."""
import base64,copy,json,subprocess,unittest
from pathlib import Path
from app.platform.activity import project
from app.platform.exports import generate
ROOT=Path(__file__).resolve().parents[1]
class ActivityProjectionTests(unittest.TestCase):
 def test_attribution_distinguishes_actor_system_and_unknown(self):
  base={'id':'event','event_type':'decision.approved','node_id':'logistics_assignment','actor':{'id':'real','name':'Juan'},'metadata':{}}
  self.assertEqual(project(base)['label'],'Juan aprobó Assignment')
  self.assertEqual(project({**base,'actor':None})['label'],'Autor no registrado aprobó Assignment')
  self.assertEqual(project({**base,'actor':None,'event_type':'decision.submitted','metadata':{'source':'system','automatic':True}})['label'],'El sistema dejó Assignment para revisión')
 def test_server_csv_matches_original_exporter_for_both_nodes_and_legacy(self):
  fixtures=json.loads((ROOT/'tests/browser/fixtures.json').read_text());runs=[copy.deepcopy(fixtures['runs'][k]) for k in ['assignment','scheduling']]
  legacy=copy.deepcopy(runs[0]);legacy['result_json']['schema_version']='dispatch_v1';runs.append(legacy)
  for run in runs:
   t=run['result_json']['scenarios']['selected']['trips'][0];t['estimated_cost']=None;t['cost']=7.5;t['provider_name']='=untrusted;"value"\nsecond line';t['loads'][0]['product']='+formula'
  js="""
import {exportDecision} from './app/static/js/dispatch/runs/export.mjs';
import {readFileSync} from 'node:fs';
let blob;globalThis.window={setTimeout:()=>{}};globalThis.document={body:{append:()=>{}},createElement:()=>({click:()=>{},remove:()=>{},style:{}})};URL.createObjectURL=b=>{blob=b;return 'blob:synthetic'};
const runs=JSON.parse(readFileSync(0,'utf8')),out=[];
for(const run of runs){const name=exportDecision(run.result_json);out.push({name,content:Buffer.from(await blob.arrayBuffer()).toString('base64')});}
process.stdout.write(JSON.stringify(out));
"""
  result=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(runs),cwd=ROOT,text=True,capture_output=True,check=True)
  for run,expected in zip(runs,json.loads(result.stdout)):
   name,content,_=generate(run,'csv');self.assertEqual(name,expected['name']);self.assertEqual(content,base64.b64decode(expected['content']))
 def test_failed_or_empty_export_is_rejected_before_audit(self):
  for run in [{'status':'error','result_json':{}},{'status':'completed','result_json':{'schema_version':'assignment_v1','scenarios':{}}}]:
   with self.assertRaises(ValueError):generate(run,'csv')
