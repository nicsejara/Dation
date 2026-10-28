"""Prepare local synthetic pilot inputs with the unchanged certified normalizer.

Does not execute engines, call APIs, create tenants or write production data.
"""
import csv,io,json,sys
from copy import deepcopy
from pathlib import Path
from uuid import UUID,uuid5

ROOT=Path('/workspace/Dation')
sys.path.insert(0,str(ROOT/'backend'))
from app.domain.logistics.data_contracts import compile_contract
from app.domain.logistics.normalizers import normalize_input,InputValidationError
from app.services.logistics_model_service import configuration_snapshot

OUT=ROOT/'docs/execution/ultimate/t12/pilot'
OUT.mkdir(parents=True,exist_ok=True)
BASE=json.loads((ROOT/'docs/execution/ultimate/t11/evidence/restore-final/smoke-manifest.json').read_text())['pilot']['configuration']

def demand(oid='O1',quantity='70',distance='480',split=True,ready='2026-11-02',due='2026-11-08'):
 return dict(order_id=oid,origin_id='A',destination_id='B',distance_km=distance,ready_date=ready,delivery_due_date=due,priority='MEDIUM',split_allowed=str(split).lower(),demand_pallets=quantity,compatibility_groups='DRY')

def resource(rid='E1',capacity='26',count='2',source='EXTERNAL',rate='100',availability='CONFIRMED'):
 value=dict(resource_id=rid,source=source,lanes='[["A","B"]]',guaranteed_pallets=capacity,compatibility_groups='DRY')
 if source=='OWN':value.update(units_available=count,base_origin_id='A',operating_cost_per_km=rate)
 else:value.update(services_available=count,availability_source=availability,cost_model='PER_TRIP',trip_rate=rate)
 return value

cases=[
 ('A',['EXTERNAL'],True,[demand()],[resource(),resource('E2','30','1',rate='150')],
  {'coverage':'70/70 pallets','trips':3,'total_cost_ARS':'350','source':'EXTERNAL'},
  'tests.test_transport_plan_policies.TransportPlanPolicyTests.test_A_F_partial_gap_and_min_cost_never_prefers_empty'),
 ('B',['OWN','EXTERNAL'],False,[demand(quantity='1',distance='30',split=False)],[resource('OWN','2','1',source='OWN',rate='2'),resource('EXT','2','1',rate='300')],
  {'coverage':'1/1 pallets','selected_source':'OWN','total_cost_ARS':'120'},
  'tests.test_transport_plan_policies.TransportPlanPolicyTests.test_B_C_independent_literal_cost_oracles'),
 ('C',['EXTERNAL'],True,[demand()],[resource()],
  {'coverage':'52/70 pallets','unassigned_pallets':'18','trips':2,'total_cost_ARS':'200','required_reason':'CAPACITY_GAP','review':'Explicit partial coverage; no fabricated FULL'},
  'tests.test_transport_plan_policies.TransportPlanPolicyTests.test_A_F_partial_gap_and_min_cost_never_prefers_empty'),
 ('D',['OWN'],False,[demand('O0','26',split=False),demand('O1','26',split=False)],[resource('R1','26','1',source='OWN',rate='1')],
  {'trips':2,'D2_dispatch_dates':['2026-11-02','2026-11-04'],'D2_available_again':['2026-11-04','2026-11-06'],'cycle_days':2,'source_D1':'Exact approved Run + fingerprint; no reassignment'},
  'tests.test_day_scheduling_core.DaySchedulingCoreTests.test_I_own_one_unit_reuses_exclusive_cycle_end'),
 ('E',['OWN','EXTERNAL'],False,[demand(quantity='26',split=False,ready='2026-11-04',due='2026-11-04')],[resource('EXT','26','',rate='100',availability='ASSUMED')],
  {'availability':'ASSUMED, services derive to 1 with explicit provenance','D2_dispatch_date':'2026-11-04','D2_margin_days':0,'D2_status':'AT_RISK','negative_input':'duplicate order_id must be rejected before publication'},
  'tests.test_day_scheduling_core.DaySchedulingCoreTests.test_ready_delay_and_zero_margin_have_fact_backed_reasons')]

checks=[];scenarios=[]
for name,sources,split,demands,resources,expected,reference in cases:
 directory=OUT/name;directory.mkdir(exist_ok=True)
 config=deepcopy(BASE);config.update(allowed_sources=sources,split_permitted=split)
 config,config_hash=configuration_snapshot(config)
 placeholder=uuid5(UUID('b8e10dc3-09fb-4a32-8870-514e0dc32519'),'LOCAL-PREPARATION-'+name)
 version={'id':str(placeholder),'config_jsonb':config,'config_hash':config_hash}
 (directory/'model-configuration.json').write_text(json.dumps(config,indent=2)+'\n')
 for entity,rows in [('transport_demand',demands),('transport_resources',resources)]:
  contract=compile_contract(version,entity)
  def csv_bytes(items):
   buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=[f.public_header for f in contract.fields],lineterminator='\n')
   writer.writeheader();writer.writerows(items);return buffer.getvalue().encode()
  data=csv_bytes(rows);result=normalize_input(data,contract)
  (directory/(entity+'.csv')).write_bytes(data)
  checks.append({'scenario':name,'entity':entity,'result':'PASS','scope':'local CSV normalization only','report':result['report']})
  if name=='E' and entity=='transport_demand':
   negative=csv_bytes(rows+rows)
   (directory/'transport_demand-duplicate-invalid.csv').write_bytes(negative)
   try:normalize_input(negative,contract)
   except InputValidationError as error:
    checks.append({'scenario':'E-negative','result':'PASS_EXPECTED_REJECTION','scope':'local CSV normalization only','report':error.report})
   else:raise AssertionError('Duplicate input unexpectedly accepted')
 scenarios.append({'id':name,'configuration':str((directory/'model-configuration.json').relative_to(OUT)),
  'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},
  'expected_business_checks':expected,'certified_test_reference':reference,'production_execution':'NOT_RUN'})

(OUT/'scenarios.json').write_text(json.dumps({'status':'PREPARED_LOCAL_ONLY','workspace_id':None,'actor_user_id':None,'cohort_size_target':'1–3 explicitly controlled workspaces','production_write_enabled':False,'note':'Local placeholder Model Version UUIDs are used only to compile contracts. Publish real Model Versions and obtain their exact template/contract hash before upload. No synthetic production tenant or actor is invented. These inputs are not permanent production fixtures.','scenarios':scenarios},indent=2,ensure_ascii=False)+'\n')
(OUT/'input-validation.json').write_text(json.dumps({'result':'PASS','engine_executions':0,'network_requests':0,'production_writes':0,'positive_checks':10,'expected_negative_checks':1,'checks':checks},indent=2)+'\n')
print(json.dumps({'prepared_scenarios':len(scenarios),'positive_normalizations':10,'expected_duplicate_rejection':1,'production_executions':0}))
