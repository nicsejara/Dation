"""T11-only owned certification helpers. No remote/reset CLI is exposed.

Reset requires a live, labelled disposable Sandbox and an explicit testing
workspace marker inside that sandbox. It cannot select a production connection.
"""
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import time
from uuid import UUID,uuid4

from ultimate_day_fixture import DaySandbox
from sandbox import Sandbox,jwt,wait_for
from ultimate_result_helpers import ok,row,submit,wait_run,approval,publish
from test_ultimate_d2_lineage import day_submit,day_approve
from auth_fixture import USER_A
from tests.test_ultimate_data_contracts import model

SYSTEM_TABLES={'workspace_members','workspace_ddas','workspace_invitations',
              'legacy_owners','member_responsibilities','workspace_onboarding','ultimate_pilot_workspaces'}


class CertificationSandbox(DaySandbox):
    def docker(self,*args):
        if args and args[0]=='run':args=(args[0],'--label','dation.qa.execution=T11',*args[1:])
        return super().docker(*args)


def database_command(s,*args,input=None):
    return subprocess.run(['docker','exec','-i',s.pg,*args],input=input,capture_output=True,check=True,timeout=120)


def owned(s):
    if not isinstance(s,CertificationSandbox) or not s.pg.startswith('dation-e2e-') or s.database!='dation_e2e':
        raise RuntimeError('Not a T11 disposable fixture')
    labels=json.loads(s.docker('inspect','--format','{{json .Config.Labels}}',s.pg))
    if labels.get('dation.qa.owner')!='codex-dation' or labels.get('dation.qa.execution')!='T11':
        raise RuntimeError('Owned T11 labels required')


def quote(value):return "'"+str(value).replace("'","''")+"'"


def scoped_tables(s):
    return json.loads(s.sql("""SELECT jsonb_agg(jsonb_build_array(table_schema,table_name) ORDER BY table_schema,table_name)
      FROM information_schema.columns WHERE table_schema IN('public','dation_private') AND column_name='workspace_id';"""))


def rows_digest(s,workspace_id=None):
    values={}
    for schema,table in scoped_tables(s):
        condition=' WHERE workspace_id='+quote(workspace_id) if workspace_id else ''
        data=s.sql(f'SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),\'[]\') FROM {schema}.{table} t'+condition+';')
        values[schema+'.'+table]=hashlib.sha256(data.encode()).hexdigest()
    return values


def all_rows_digest(s):
    tables=json.loads(s.sql("SELECT jsonb_agg(jsonb_build_array(schemaname,tablename) ORDER BY schemaname,tablename) FROM pg_tables WHERE schemaname IN('public','dation_private','auth');"))
    return {schema+'.'+table:hashlib.sha256(s.sql(f'SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),\'[]\') FROM {schema}.{table} t;').encode()).hexdigest() for schema,table in tables}


def effective_catalog(s,catalog_sql):
    # Pretty deparse removes redundant same-precedence CHECK parentheses that
    # PostgreSQL canonicalizes while parsing pg_dump DDL during restore.
    catalog_sql=catalog_sql.replace('pg_get_constraintdef(c.oid)',
                                    'pg_get_constraintdef(c.oid,true)').replace(
                                    'c.condeferrable,c.condeferred,',
                                    'c.condeferrable,c.condeferred,c.convalidated,')
    catalog=json.loads(s.sql(catalog_sql))
    # pg_dump legitimately omits redundant explicit owner grants. Compare all
    # non-ACL DDL exactly, then effective privileges for every non-system role;
    # never equate NULL function ACL with "no PUBLIC execute".
    for part in ['relations','functions']:
        for item in catalog[part]:item.pop('acl',None)
    acl=json.loads(s.sql("""SELECT jsonb_build_object(
      'tables',(SELECT jsonb_agg(jsonb_build_object('schema',n.nspname,'name',c.relname,'role',r.rolname,
        'select',has_table_privilege(r.oid,c.oid,'SELECT'),'insert',has_table_privilege(r.oid,c.oid,'INSERT'),
        'update',has_table_privilege(r.oid,c.oid,'UPDATE'),'delete',has_table_privilege(r.oid,c.oid,'DELETE'),
        'truncate',has_table_privilege(r.oid,c.oid,'TRUNCATE'),'references',has_table_privilege(r.oid,c.oid,'REFERENCES'),
        'trigger',has_table_privilege(r.oid,c.oid,'TRIGGER')) ORDER BY n.nspname,c.relname,r.rolname)
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN pg_roles r
        WHERE n.nspname IN('public','dation_private') AND c.relkind IN('r','p','v') AND r.rolname !~ '^pg_'),
      'functions',(SELECT jsonb_agg(jsonb_build_object('schema',n.nspname,'name',p.proname,
        'args',pg_get_function_identity_arguments(p.oid),'role',r.rolname,'execute',has_function_privilege(r.oid,p.oid,'EXECUTE'))
        ORDER BY n.nspname,p.proname,pg_get_function_identity_arguments(p.oid),r.rolname)
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace CROSS JOIN pg_roles r
        WHERE n.nspname IN('public','dation_private') AND p.prokind='f' AND r.rolname !~ '^pg_'),
      'schemas',(SELECT jsonb_agg(jsonb_build_object('name',n.nspname,'role',r.rolname,
        'usage',has_schema_privilege(r.oid,n.oid,'USAGE'),'create',has_schema_privilege(r.oid,n.oid,'CREATE')) ORDER BY n.nspname,r.rolname)
        FROM pg_namespace n CROSS JOIN pg_roles r WHERE n.nspname IN('public','dation_private','auth') AND r.rolname !~ '^pg_'),
      'sequences',(SELECT jsonb_agg(jsonb_build_object('schema',n.nspname,'name',c.relname,'role',r.rolname,
        'usage',has_sequence_privilege(r.oid,c.oid,'USAGE'),'select',has_sequence_privilege(r.oid,c.oid,'SELECT'),
        'update',has_sequence_privilege(r.oid,c.oid,'UPDATE')) ORDER BY n.nspname,c.relname,r.rolname)
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN pg_roles r
        WHERE n.nspname IN('public','dation_private') AND c.relkind='S' AND r.rolname !~ '^pg_'));
    """))
    return {'structure':catalog,'effective_privileges':acl}


def mark_testing_workspace(s,wid):
    owned(s);UUID(wid)
    if s.sql('SELECT count(*) FROM public.workspaces WHERE id='+quote(wid)+';')!='1':raise RuntimeError('Workspace absent')
    marker={'workspace_id':wid,'pg_container':s.pg,'database':s.database,'testing_only':True,'nonce':secrets.token_hex(16)}
    path=s.directory/('t11-testing-workspace-'+wid+'.json');path.write_text(json.dumps(marker))
    return marker


def reset_testing_workspace(s,marker):
    owned(s);wid=str(UUID(marker['workspace_id']))
    path=s.directory/('t11-testing-workspace-'+wid+'.json')
    if not path.is_file() or json.loads(path.read_text())!=marker or marker.get('testing_only') is not True:
        raise RuntimeError('Explicit testing workspace marker required')
    if marker.get('pg_container')!=s.pg or marker.get('database')!=s.database:raise RuntimeError('Marker binding mismatch')
    tables=[(schema,table) for schema,table in scoped_tables(s) if table not in SYSTEM_TABLES]
    for schema,table in tables:
        if not re.fullmatch('[a-z_]+',schema) or not re.fullmatch('[a-z_]+',table):raise RuntimeError('Unexpected identifier')
    # Immutable history is intentionally deletable ONLY in this marked disposable
    # test tenant. Transaction-local trigger suppression never changes schema,
    # RLS, grants or functions and never reaches a remote database.
    deletes=''.join(f'DELETE FROM {schema}.{table} WHERE workspace_id={quote(wid)};' for schema,table in tables)
    s.sql('BEGIN; SET LOCAL session_replication_role=replica;'+deletes+'COMMIT;')
    cleared=[]
    for bucket in s.storage.iterdir():
        if not bucket.is_dir():continue
        root=(bucket/wid).resolve()
        if root.parent!=bucket.resolve():raise RuntimeError('Storage path mismatch')
        if root.exists():shutil.rmtree(root);cleared.append(str(root.relative_to(s.storage)))
    remaining={schema+'.'+table:int(s.sql(f'SELECT count(*) FROM {schema}.{table} WHERE workspace_id={quote(wid)};')) for schema,table in tables}
    if any(remaining.values()):raise AssertionError(remaining)
    return {'workspace_id':wid,'remaining_business_rows':remaining,'cleared_storage_prefixes':cleared,
            'schema_or_roles_modified':False,'idempotent_scope':'explicit marked owned tenant'}


def first_user_journey(s):
    """Only HTTP business operations after reset; worker/SQL are real."""
    steps=[];a=s.api_client
    login=a.post('/auth/login',headers={'Origin':s.api_url},json={'email':'user-1@example.test','password':'dispatch-e2e-private'})
    assert login.status_code==200,login.text
    steps.append({'step':'Login','status':'PASS; real Auth fixture route and session'})
    m=ok(a.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'[T11 TEST ONLY] Operación desde cero','configuration':model()['config_jsonb']}));steps.append({'step':'Create Logistics Model','id':m['model']['id']})
    v=ok(a.post('/api/platform/logistics-models/'+m['model']['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':1}));steps.append({'step':'Publish Model Version','id':v['version']['id']})
    response=ok(a.post('/api/platform/logistics-cases',json={'id':str(uuid4()),'name':'[T11 TEST ONLY] Primera semana','logistics_model_version_id':v['version']['id'],'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':USER_A}))
    cid=response['case']['id'];base='/api/platform/logistics-cases/'+cid
    ok(a.put('/api/platform/decisions/'+cid+'/responsibilities/data_owner',json={'expected_updated_at':None,'owner_user_id':USER_A}))
    graph=ok(a.get(base+'/graph'))['graph'];assert graph['nodes'][0]['node_state']=='DATA_REQUIRED';steps.append({'step':'Decision Map D1 DATA_REQUIRED','case_id':cid})
    ok(a.get(base+'/data'))
    for entity in ['transport_demand','transport_resources']:
        template=a.get(base+'/data/templates/'+entity);assert template.status_code==200
        publish(s,cid,entity);steps.append({'step':'Download template → upload → publish '+entity})
    graph=ok(a.get(base+'/graph'))['graph'];assert graph['nodes'][0]['node_state']=='READY';steps.append({'step':'D1 READY'})
    parent,_,response=submit(s,cid);ok(response);wait_run(s,parent);steps.append({'step':'Configure and execute D1','run_id':parent})
    for rid,key,approve in [(parent,'D1',approval)]:
        consume_and_approve(s,cid,rid,key,approve,steps)
    graph=ok(a.get(base+'/graph'))['graph'];assert graph['nodes'][1]['node_state']=='READY';steps.append({'step':'D2 READY'})
    child,_,response=day_submit(s,cid);ok(response);wait_run(s,child);steps.append({'step':'Configure and execute D2','run_id':child})
    consume_and_approve(s,cid,child,'D2',day_approve,steps)
    p=row(s,parent);d=row(s,child)
    assert d['upstream_run_id']==parent and d['result_json']['source_transport_plan']['result_fingerprint']==p['result_fingerprint']
    assert [n['node_state'] for n in ok(a.get(base+'/graph'))['graph']['nodes']]==['APPROVED','APPROVED']
    return {'case_id':cid,'parent':p,'child':d,'steps':steps,'manual_business_sql':False}


def consume_and_approve(s,cid,rid,key,approve,steps):
    fp=row(s,rid)['result_fingerprint'];q={'expected_result_fingerprint':fp};base='/api/runs/'+rid
    package=ok(s.api_client.get(base+'/result',params=q))['package']
    for d in package['details']:ok(s.api_client.get(base+'/details/'+d['dataset_id'],params=q))
    context=ok(s.api_client.get(base+'/decision-context',params={**q,'mode':'REVIEW'}))['context']
    intent={'schema_version':'decision_intent_v2','provenance':context['provenance'],'context_version':1,'context_hash':context['context_hash'],'mode':context['mode'],'question':'¿Qué hechos debo revisar antes de aprobar?','selected_entity':None,'selected_alternative_ids':[],'evidence_hashes':[r['content_sha256'] for r in context['selected_evidence_refs']]}
    answer=ok(s.api_client.post(base+'/copilot',params=q,json={'turn_id':str(uuid4()),'intent':intent}))
    assert answer['provenance']['result_fingerprint']==fp
    review=ok(s.api_client.get(base+'/approval-review',params=q));assert review['approval_overlay']['approval_allowed']
    ok(approve(s,cid,rid));steps.append({'step':key+' Dashboard → Details → IA → Review → Approve','run_id':rid,'fingerprint':fp})


def storage_inventory(root):
    return {str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(root.rglob('*')) if p.is_file()}


def backup_restore(s,destination):
    """Whole DB including ACL + private object bytes, restored into a new DB."""
    owned(s);destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    for process in reversed(s.processes):s.stop(process)
    before=all_rows_digest(s);source_objects=storage_inventory(s.storage)
    dump=database_command(s,'pg_dump','-U','postgres','-d',s.database,'-Fc','--no-owner').stdout
    (destination/'database.dump').write_bytes(dump)
    private=destination/'private-objects';shutil.copytree(s.storage,private)
    restored='dation_t2_restore_'+uuid4().hex
    database_command(s,'createdb','-U','postgres',restored)
    database_command(s,'pg_restore','-U','postgres','-d',restored,'--no-owner','--exit-on-error',input=dump)
    source_db=s.database;s.database=restored
    try:after=all_rows_digest(s)
    finally:s.database=source_db
    assert before==after and source_objects==storage_inventory(private)
    report={'source_database':source_db,'restored_database':restored,'sql_metadata_equal':True,
            'workspace_table_hashes':before,'private_objects':source_objects,'private_objects_equal':True,
            'dump_sha256':hashlib.sha256(dump).hexdigest(),'acl_included':True}
    (destination/'restore.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def activate_restored(s,report,private):
    """New PostgREST/API processes read the restored DB and object directory."""
    from sandbox import POSTGREST
    owned(s)
    key=secrets.token_urlsafe(48)
    public=json.loads((s.directory/'auth-fixture-jwks.json').read_text())
    import base64
    public['keys'].append({'kty':'oct','alg':'HS256','k':base64.urlsafe_b64encode(key.encode()).rstrip(b'=').decode()})
    name=s.identifier+'-restored-rest';s.containers.append(name)
    s.docker('run','-d','--name',name,'--network',s.network,'-p','127.0.0.1::3000',
        '-e','PGRST_DB_URI=postgres://dation_e2e_authenticator@postgres:5432/'+report['restored_database'],
        '-e','PGRST_DB_ANON_ROLE=anon','-e','PGRST_JWT_SECRET='+json.dumps(public),POSTGREST)
    s.rest_url='http://'+s.docker('port',name,'3000/tcp');s.token=jwt(key,'service_role')
    s.database=report['restored_database'];s.storage=Path(private)
    s.env.update(SUPABASE_SECRET_KEY=s.token,DATION_E2E_REST=s.rest_url,DATION_E2E_STORAGE=str(s.storage))
    wait_for(lambda:s.reachable(s.rest_url+'/',{'Authorization':'Bearer '+s.token}),'restored PostgREST')
    port=s.env['SUPABASE_URL'].rsplit(':',1)[1]
    s.start_process('storage',['-m','uvicorn','storage_gateway:app','--host','127.0.0.1','--port',port],cwd=Path(__file__).parent)
    wait_for(lambda:s.reachable(s.env['SUPABASE_URL']+'/rest/v1/',{'Authorization':'Bearer '+s.token}),'restored private Storage')
    s.start_api()
