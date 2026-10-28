from pathlib import Path
import json,sys,importlib.util,hashlib
sys.path.insert(0,'/workspace/Dation/backend')
if '--baseline' in sys.argv:
 spec=importlib.util.spec_from_file_location('app.domain.logistics.base','/workspace/work/dation-t11-r/base-before.py');module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
if '--baseline' in sys.argv:
 spec=importlib.util.spec_from_file_location('app.results.contracts','/workspace/work/dation-t11-r/contracts-before.py');module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
from app.results import contracts as c
from app.domain.logistics import contracts as d
from app.engines.assignment.transport_contracts import TransportPlanInput
from app.models.ultimate_foundation import LogisticsModelConfigurationV1
classes=[c.EngineOutput,c.ResultContractBundle,c.ConstraintEvidence,c.EntityEvidence,c.CandidateSummary,c.SolverEvidence,c.EngineCoreResult,c.EngineEvidence,c.DecisionResultPackageV1,c.DecisionContextV1,d.FrozenCaseContext,d.LogisticsModelVersion,d.Demand,d.TransportResource,d.CasePolicy,d.NodePolicy,TransportPlanInput,LogisticsModelConfigurationV1]
values={model.__name__:hashlib.sha256(json.dumps(model.model_json_schema(),sort_keys=True,separators=(',',':')).encode()).hexdigest() for model in classes}
Path(sys.argv[1]).write_text(json.dumps(values,indent=2)+'\n')
