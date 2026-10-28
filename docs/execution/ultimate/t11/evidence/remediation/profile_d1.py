"""Diagnostic timings and statistical stacks for the unchanged PERF11 fixture."""
import collections,functools,hashlib,importlib,json,os,signal,sys,time
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
sys.path[:0]=['/workspace/Dation/backend']
import tests.test_ultimate_performance as perf
from ortools.sat.python import cp_model
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
modules={name:importlib.import_module('app.'+name) for name in [
 'engines.assignment.transport_plan','engines.assignment.transport_model','engines.assignment.transport_policies',
 'engines.assignment.transport_policy_result','engines.assignment.transport_validator','engines.assignment.transport_policy_validator',
 'engines.common.day_resource_feasibility','results.assembler','results.validation','results.projections','results.canonical']}
active=False;stack=[];events=[];leaves=collections.Counter();sampled=collections.Counter();sample_count=0

def sample(signum,frame):
 global sample_count
 if not active:return
 sample_count+=1;chain=[]
 while frame:
  file=frame.f_code.co_filename
  if '/backend/app/' in file:
   key=file.split('/backend/',1)[1]+':'+str(frame.f_lineno)+':'+frame.f_code.co_name;chain.append(key);sampled[key]+=1
  frame=frame.f_back
 if chain:leaves[chain[0]]+=1

def timed(label,fn):
 @functools.wraps(fn)
 def call(*a,**kw):
  global active
  outer=label in ('recommended_and_alternatives','result_assembly')
  if outer:
   rid=a[0].run_id if label=='recommended_and_alternatives' else a[0].recommended.output.core.decision.run_id
   if rid.int!=101:return fn(*a,**kw)
   active=True
  if not active:return fn(*a,**kw)
  suffix=':'+str(a[1] or 'RECOMMENDED') if label=='policy_candidate' and len(a)>1 else ''
  frame={'label':label+suffix,'children':0};start=time.perf_counter();cpu_start=time.process_time();stack.append(frame)
  try:
   result=fn(*a,**kw)
   if label=='result_assembly':
    frozen={'package_sha256':hashlib.sha256(modules['results.canonical'].canonical_bytes(result.package)).hexdigest(),
      'result_fingerprint':result.package.fingerprints.result_fingerprint,
      'artifacts':[{'id':str(p.reference.artifact_id),'sha256':hashlib.sha256(p.content).hexdigest(),'size':len(p.content)} for p in result.artifacts]}
    (out/'golden-full-publication.json').write_text(json.dumps(frozen,indent=2)+'\n')
   return result
  finally:
   seconds=time.perf_counter()-start;stack.pop();events.append({'label':frame['label'],'inclusive_seconds':seconds,'exclusive_seconds':seconds-frame['children'],'cpu_seconds':time.process_time()-cpu_start})
   if stack:stack[-1]['children']+=seconds
   if label=='policy_candidate' or outer:print(label+suffix,'wall',round(seconds,3),'CPU',round(time.process_time()-cpu_start,3),file=sys.stderr,flush=True)
   if outer:active=False
 return call

specs=[('engines.assignment.transport_policy_result','_produce','policy_candidate'),
 ('engines.assignment.transport_plan','_build_structural_plan','structural_plan_evidence'),
 ('engines.assignment.transport_model','solve_structural','candidate_generation_and_optimization'),
 ('engines.assignment.transport_validator','certify_transport_plan','independent_structural_certification'),
 ('engines.assignment.transport_policy_validator','certify_policy_result','independent_policy_certification'),
 ('engines.common.day_resource_feasibility','day_resource_feasibility','temporal_kernel'),
 ('results.projections','evidence_shards','evidence_partition_construction'),
 ('results.validation','_validated_plan_output','independent_assembly_plan_certification'),
 ('results.validation','validate_bundle','independent_bundle_certification'),
 ('results.validation','reassemble_evidence','complete_evidence_reassembly'),
 ('results.validation','_reassemble_validated_evidence','whole_evidence_merge'),
 ('results.canonical','artifact_bytes','artifact_canonical_serialization')]
with ExitStack() as contexts:
 for mod,name,label in specs:
  old=getattr(modules[mod],name);wrapped=timed(label,old)
  for module in modules.values():
   if getattr(module,name,None) is old:contexts.enter_context(patch.object(module,name,wrapped))
 contexts.enter_context(patch.object(perf,'run_transport_policy',timed('recommended_and_alternatives',perf.run_transport_policy)))
 contexts.enter_context(patch.object(perf,'assemble',timed('result_assembly',perf.assemble)))
 cls=modules['engines.assignment.transport_policies'].PolicySearch
 contexts.enter_context(patch.object(cls,'optimize',timed('optimization_formulation_and_solves',cls.optimize)))
 cls=modules['results.assembler'].ArtifactBuilder
 contexts.enter_context(patch.object(cls,'dataset',timed('dataset_artifact_preparation',cls.dataset)))
 contexts.enter_context(patch.object(cp_model.CpSolver,'solve',timed('native_solver',cp_model.CpSolver.solve)))
 signal.signal(signal.SIGPROF,sample);signal.setitimer(signal.ITIMER_PROF,.02,.02)
 before=time.perf_counter()
 try:result=perf.probe()
 finally:signal.setitimer(signal.ITIMER_PROF,0)
 wall=time.perf_counter()-before
(out/'probe.json').write_text(json.dumps(result,indent=2)+'\n')
aggregate={}
for e in events:
 v=aggregate.setdefault(e['label'],{'calls':0,'inclusive_seconds':0,'exclusive_seconds':0,'cpu_seconds':0});v['calls']+=1
 for k in ['inclusive_seconds','exclusive_seconds','cpu_seconds']:v[k]+=e[k]
report={'scope':'unchanged exact T11 PERF11 D1 fixture; observations only, no decisions altered',
 'total_probe_wall_seconds_including_separate_D2':wall,'d1_engine_assembler_seconds':result['d1_engine_seconds']+result['d1_assembler_seconds'],
 'stages':aggregate,'sample_count':sample_count,'sample_interval_cpu_seconds':.02,
 'top_sampled_leaf_locations':[{'location':k,'samples':v,'percent':100*v/sample_count} for k,v in leaves.most_common(35)],
 'top_sampled_inclusive_locations':[{'location':k,'samples':v,'percent':100*v/sample_count} for k,v in sampled.most_common(35)],
 'input_context_loading':'Existing PERF11 is in-memory typed fixtures; no DB/Storage loading in these two recorded stages. Full worker coverage must be measured separately.',
 'contract_normalization':'Frozen normalized DTO input; no CSV normalization inside engine/assembler. Request schema checks remain in measured engine.',
 'snapshot_evidence_overhead':'Golden full-publication descriptors written at outer assembly boundary; counted in diagnostic wrapper inclusive time, not benchmark engine/assembler timer.'}
(out/'profile.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'PROFILE_COMPLETE','d1_seconds':report['d1_engine_assembler_seconds'],'fingerprint':result['d1']['fingerprint']}))
