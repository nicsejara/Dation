"""Explicit T5 lifecycle metadata fixtures; not a solver or result producer."""
import json
from uuid import uuid4
from app.domain.logistics.definitions import definition_hash

def install_run(s,client,case_id,node_id='logistics_assignment',*,status='completed',approved=False,trip_count=2):
    data=client.get('/api/platform/logistics-cases/'+case_id+'/graph').json()
    node=next(n for n in data['graph']['nodes'] if n['id']==node_id)
    ctx=client.get('/api/platform/logistics-cases/'+case_id+'/context').json()
    pack=client.get('/api/platform/logistics-cases/'+case_id+'/data').json()
    demand=next(e for e in pack['entries'] if e['slot_key']=='transport_demand')
    row=ctx['case'];wid=row['workspace_id'];rid=str(uuid4());aid=str(uuid4());actor=row['created_by_user_id']
    schema='transport_plan_v1' if node_id=='logistics_assignment' else 'day_scheduling_v1'
    config={'ultimate_graph':{'definition_hash':definition_hash(),'read_set':node['read_set']}}
    descriptor={'artifact_id':aid,'workspace_id':wid,'run_id':rid,'kind':'CORE','part_key':'main','artifact_schema':'engine_core_v1','schema_version':1,'content_sha256':'a'*64,'size_bytes':2,'media_type':'application/json','core_fingerprint':'b'*64,'assembler_version':'RESULT_ASSEMBLER_V1'}
    result={'result_schema':schema,'result_schema_version':1,'assembler_version':'RESULT_ASSEMBLER_V1',
        'fingerprints':{'result_fingerprint':'c'*64,'core_result_fingerprint':'b'*64},
        'artifact_manifest':{'artifacts':[descriptor]},'metrics':{'trip_count':trip_count}}
    quote=lambda value:"'"+json.dumps(value,separators=(',',':')).replace("'","''")+"'::jsonb"
    publication_cols=',result_json,result_package_version,assembler_version,artifact_manifest_hash,core_fingerprint,result_fingerprint' if status=='completed' else ''
    publication_values=','+quote(result)+",1,'RESULT_ASSEMBLER_V1','"+'d'*64+"','"+'b'*64+"','"+'c'*64+"'" if status=='completed' else ''
    approval_cols=',approved_at,approved_by,approved_by_user_id' if approved else ''
    approval_values=",clock_timestamp(),'user:"+actor+"','"+actor+"'" if approved else ''
    source="'"+node['upstream_run_id']+"'" if node['upstream_run_id'] else 'NULL'
    sql=f"""BEGIN;
    UPDATE decision_cases SET context_frozen_at=coalesce(context_frozen_at,clock_timestamp()) WHERE id='{case_id}';
    INSERT INTO decision_runs(id,workspace_id,dataset_id,decision_case_id,node_id,workflow_version,created_by_user_id,
      logistics_model_version_id,data_pack_version_id,graph_definition_version,case_policy_hash,node_policy_hash,
      contract_hash,input_context_hash,transit_model_version,runtime_profile,result_schema_version,engine_name,engine_version,
      schema_version,status,configuration_json,upstream_run_id{publication_cols}{approval_cols})
    VALUES('{rid}','{wid}','{demand['dataset_id']}','{case_id}','{node_id}',2,'{actor}',
      '{row['logistics_model_version_id']}','{pack['version']['id']}','{row['graph_definition_version']}',
      '{row['case_policy_hash']}','{row['case_policy_hash']}','{ctx['model_version']['contract_hash']}','{'e'*64}',
      'DATION_TRANSIT_V1','{schema}',1,'{'transport_plan' if node_id=='logistics_assignment' else 'day_scheduling'}','2.0.0',
      '{schema}','{status}',{quote(config)},{source}{publication_values}{approval_values});"""
    if status=='completed':
        sql+=f"""INSERT INTO decision_result_artifacts(id,workspace_id,run_id,kind,part_key,artifact_schema,schema_version,
          content_sha256,size_bytes,media_type,storage_bucket,storage_path,assembler_version,core_fingerprint,result_fingerprint,
          publication_state,producer_lease_token,producer_generation,producer_metadata)
        VALUES('{aid}','{wid}','{rid}','CORE','main','engine_core_v1',1,'{'a'*64}',2,'application/json','dda-results',
          '{wid}/runs/{rid}/core/main/{'a'*64}.json','RESULT_ASSEMBLER_V1','{'b'*64}','{'c'*64}',
          'READY','{uuid4()}',1,'{{"fixture":"T5 controlled metadata only; no engine/output certification"}}');"""
    sql+='COMMIT;';s.sql(sql)
    return rid

if __name__=='__main__':
    import subprocess,sys,httpx
    value=json.load(sys.stdin)
    class SQL:
        def sql(self,sql):
            check=subprocess.run(['docker','--host=unix:///var/run/docker.sock','inspect','--format','{{index .Config.Labels "dation.qa.phase"}}',value['pg']],capture_output=True,text=True,timeout=10)
            if check.returncode or check.stdout.strip()!='T5':raise AssertionError('Not an owned T5 fixture')
            result=subprocess.run(['docker','--host=unix:///var/run/docker.sock','exec','-i',value['pg'],'psql','-U','postgres','-d',value['database'],'-X','-A','-t','-v','ON_ERROR_STOP=1'],input=sql,capture_output=True,text=True,timeout=30)
            if result.returncode:raise AssertionError(result.stderr)
            return result.stdout
    with httpx.Client(base_url=value['base'],headers={'Authorization':'Bearer '+value['token']},trust_env=False,timeout=30) as client:
        run_id=install_run(SQL(),client,value['case_id'],value['node_id'],**value['options'])
    print(json.dumps({'run_id':run_id}))
