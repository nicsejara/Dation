"""Single pure server authority for Ultimate node states/actions/freshness."""
from .definitions import DEFINITIONS, GRAPH_VERSION, BINDINGS, definition_hash, validate_definitions
from .requirements import input_requirements, read_identity, hash_value

NODE_STATES=('LOCKED','DATA_REQUIRED','READY','IN_PROGRESS','COMPLETED','APPROVED','COMING_SOON','NOT_APPLICABLE')

def target(view,case_id,node_id=None,run_id=None):
    return {'view':view,'case_id':case_id,'node_id':node_id,'run_id':run_id}

def resolve_case_graph(context, model, pack, run_history, responsibilities, runtime_capabilities, *, definitions=DEFINITIONS, permissions=None):
    if context.get('workflow_version')!=2 or context['graph_definition_version'] not in BINDINGS: raise ValueError('Unsupported Ultimate graph binding')
    validate_definitions(definitions);permissions=permissions or {};nodes={};case_id=context['id'];entries=pack['entries']
    # Topological traversal is independent of registry ordering and UI position.
    def resolve(d):
        if d.id in nodes:return nodes[d.id]
        for parent in d.dependencies:resolve(next(x for x in definitions if x.id==parent))
        missing=input_requirements(d,model,entries,context['case_policy_jsonb'])
        blocked=[p for p in d.required_approvals if nodes[p]['node_state']!='APPROVED']
        runs=[r for r in run_history if r['node_id']==d.id]
        active=[r for r in runs if not r.get('superseded_at')]
        approved=[r for r in active if r.get('approved_at')]
        # Approval/lineage wins over created_at. Ambiguous active candidates fail closed.
        candidates=[r for r in active if not r.get('approved_at')]
        run=approved[0] if len(approved)==1 else candidates[0] if len(candidates)==1 else None
        reads=read_identity(d,context,entries,nodes,node_policy=run.get('node_policy_hash') if run else None)
        failure='AMBIGUOUS_CURRENT_RUN' if len(approved)>1 or not approved and len(candidates)>1 else None
        stale_reasons=[]
        if run:
            frozen=run.get('graph_snapshot') or {}
            if frozen.get('definition_hash')!=definition_hash():stale_reasons.append('DEFINITION_CHANGED')
            if frozen.get('read_set')!=reads:stale_reasons.append('CONSUMED_INPUT_CHANGED')
            if run.get('logistics_model_version_id')!=context['logistics_model_version_id'] or run.get('case_policy_hash')!=context['case_policy_hash']:stale_reasons.append('CONTEXT_CHANGED')
            if d.required_approvals and run.get('upstream_run_id')!=reads.get('approved:'+d.required_approvals[0]):stale_reasons.append('UPSTREAM_CHANGED')
            if run.get('status')=='error':failure=run.get('error') or 'TECHNICAL_FAILURE'
        fresh=not stale_reasons
        applicable=not(d.applicability=='UPSTREAM_HAS_TRIPS' and not blocked and any(nodes[p].get('trip_count')==0 for p in d.dependencies))
        state='COMING_SOON' if not d.implemented else 'LOCKED' if blocked else 'NOT_APPLICABLE' if not applicable else 'DATA_REQUIRED' if missing else 'READY'
        result_published=bool(run and run.get('result_published'))
        if d.implemented and applicable and not blocked and not missing and run and fresh:
            if run['status'] in ('queued','running'):state='IN_PROGRESS'
            elif run['status']=='completed' and result_published:state='APPROVED' if run.get('approved_at') else 'COMPLETED'
        stage=(responsibilities.get('stages') or {}).get(d.id) or {};data=(responsibilities.get('stages') or {}).get('data_owner') or {}
        gates=responsibilities.get('gates_enforced',True)
        permission_reasons=[]
        if context.get('status')=='archived':permission_reasons.append('ARCHIVED_CASE')
        if not permissions.get('can_write',False):permission_reasons.append('READ_ONLY')
        if gates and not data.get('owner_eligible'):permission_reasons.append('DATA_OWNER_REQUIRED')
        if gates and not stage.get('owner_eligible'):permission_reasons.append('DECISION_OWNER_REQUIRED')
        runtime=bool(runtime_capabilities.get(d.id,False) and d.implemented)
        can_configure=state in ('READY','COMPLETED','APPROVED') and not permission_reasons and not failure
        config=target('logistics-config',case_id,d.id)
        run_id=run['id'] if run else None
        actions={'configure':{'allowed':can_configure,'target':config,'reasons':permission_reasons},
            'execute':{'allowed':False,'reasons':['ADMISSION_NOT_IMPLEMENTED']+([] if runtime else ['RUNTIME_UNAVAILABLE'])},
            'new_run':{'allowed':can_configure,'target':config},
            'data':{'allowed':d.implemented and state=='DATA_REQUIRED','target':target('logistics-case-data',case_id)},
            'result':{'allowed':bool(run_id and (result_published or run['status'] in ('queued','running','error'))),'target':target('decision-dashboard',case_id,d.id,run_id)}}
        primary=actions['data'] if state=='DATA_REQUIRED' else actions['result'] if state in ('COMPLETED','APPROVED','IN_PROGRESS') else actions['configure'] if state=='READY' else None
        nodes[d.id]={'id':d.id,'label':d.label,'question':d.question,'definition_version':d.version,
            'node_state':state,'freshness':'STALE' if stale_reasons else 'CURRENT' if run else 'NOT_EVALUATED',
            'stale_reasons':stale_reasons,'technical_failure':failure,'runtime_available':runtime,
            'implemented':d.implemented,'requirements':missing,'blocked_by':blocked,'read_set':reads,'read_set_hash':hash_value(reads),
            'run_id':run_id,'approved_run_id':run_id if state=='APPROVED' else None,
            'upstream_run_id':reads.get('approved:logistics_assignment'),
            'trip_count':run.get('trip_count') if run and state=='APPROVED' else None,
            'actions':actions,'primary_action':primary,'owner':stage.get('owner'),
            'history_count':max([r.get('history_count',len(runs)) for r in runs],default=0), 'outputs':list(d.outputs)}
        return nodes[d.id]
    for definition in definitions:resolve(definition)
    ordered=[nodes[d.id] for d in definitions]
    focus=next((n for n in ordered if n['node_state'] not in ('APPROVED','NOT_APPLICABLE','COMING_SOON','LOCKED')),ordered[0])
    return {'schema_version':'case_graph_v1','graph_version':GRAPH_VERSION,'definition_hash':definition_hash(),
        'binding_version':context['graph_definition_version'],'case_id':case_id,'nodes':ordered,
        'resume':target('logistics-map',case_id),'attention_node_id':focus['id'],
        'approved_count':sum(n['node_state']=='APPROVED' for n in ordered),'runtime_execution_available':False}
