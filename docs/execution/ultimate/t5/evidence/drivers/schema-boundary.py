"""Observe only the T4→T5 migration boundary in an owned local fixture."""
from pathlib import Path
from uuid import uuid4
import sys,json
ROOT=Path('/workspace/Dation');WORK=Path('/workspace/work/dation-t5')
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'backend/tests/e2e'),str(ROOT/'backend/tests/integration')]
from ultimate_graph_fixture import GraphSandbox
from ultimate_sql_support import CATALOG_SQL

class Boundary(GraphSandbox):
    def sql(self,sql):
        if not sql.startswith('-- T5 read-only graph snapshot.'):
            return super().sql(sql)
        query=super().sql
        wid='00000000-0000-4000-8000-00000000da71';o,f,c,r=[str(uuid4()) for _ in range(4)]
        query(f"""INSERT INTO datasets(id,workspace_id,dataset_type,original_filename,storage_path) VALUES('{o}','{wid}','orders','o.csv','{wid}/{o}/o.csv'),('{f}','{wid}','fleet','f.csv','{wid}/{f}/f.csv');
        INSERT INTO decision_cases(id,workspace_id,orders_dataset_id,fleet_dataset_id,input_signature,label) VALUES('{c}','{wid}','{o}','{f}','{o}:{f}','T5 preservation fixture');
        INSERT INTO decision_runs(id,workspace_id,dataset_id,orders_dataset_id,fleet_dataset_id,decision_case_id,node_id,engine_name,engine_version,schema_version,status,result_json,approved_at,approved_by)
        VALUES('{r}','{wid}','{o}','{o}','{f}','{c}','logistics_assignment','logistics-assignment-engine','1.0.0','assignment_v1','completed','{{"schema_version":"assignment_v1","unchanged_fixture":[1,2]}}',now(),'shared_workspace:dation');
        INSERT INTO decision_approval_events(workspace_id,run_id,case_id,node_id,action,actor) VALUES('{wid}','{r}','{c}','logistics_assignment','approved','shared_workspace:dation');""")
        before=json.loads(query(CATALOG_SQL))
        tables=['datasets','decision_cases','decision_runs','decision_approval_events','dation_private.decision_definition_versions']
        def rows():return {t:json.loads(query('SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY to_jsonb(x)::text),\'[]\') FROM '+t+' x;')) for t in tables}
        old=rows();result=query(sql);after=json.loads(query(CATALOG_SQL));new=rows()
        assert all(new[t]==old[t] for t in tables[:-1])
        assert all(row in new[tables[-1]] for row in old[tables[-1]])
        assert len(new[tables[-1]])==len(old[tables[-1]])+1
        for key in ['columns','constraints','indexes','policies','relations','triggers','defaults']:assert before[key]==after[key],key
        oldfn={(v['schema_name'],v['name'],v['args']):v for v in before['functions']}
        newfn={(v['schema_name'],v['name'],v['args']):v for v in after['functions']}
        assert all(newfn[k]==v for k,v in oldfn.items())
        flags=query('SELECT ultimate_foundation_enabled::text||\',\'||ultimate_data_pack_enabled::text FROM dation_private.platform_release;')
        assert flags=='false,false',flags
        report={'phase':'T5','environment':'owned local PostgreSQL 17 fixture','migration':'20261027033128_ultimate_decision_graph.sql',
            'legacy_rows_unchanged':True,'legacy_fixture_rows':5,'prior_definition_snapshots_unchanged':True,'new_definition_rows':1,
            'no_new_node_state_table':True,'columns_constraints_indexes_policies_relations_triggers_defaults_unchanged':True,
            'existing_functions_and_ACLs_unchanged':True,'new_functions':[v for k,v in newfn.items() if k not in oldfn],
            'foundation_and_pack_flags_still_default_closed':True}
        (WORK/'schema-boundary.json').write_text(json.dumps(report,indent=2)+'\n');return result

with Boundary():pass
print('PASS: additive T5 registry/functions; prior rows/catalog/ACL/RLS and default-closed flags unchanged.')
